"""Read-only baseline experiment: python scripts/diagnose_morph_motion.py.

Writes only a new evidence directory. Run against a0da2378 in the locked venv.
The budget diagnostics independently enumerate every admission corner rather
than invoking MorphRuntime._admit or its adaptive search.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from itertools import product
from pathlib import Path
import os
import subprocess
import sys
import traceback

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from commander_zorg.canonical import atomic_json, canonical_bytes, read_json, sha256
from commander_zorg.evidence import environment_info
from commander_zorg.guard import validate_state
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_commands import parse_command
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.morph_session import MorphRecorder, replay_runtimes, verify_session
from commander_zorg.morph_targets import load_targets
from commander_zorg.session import engine_sources
from commander_zorg.state import state_mapping


def snapshot(runtime):
    return {'channels': runtime.channels(), 'events': runtime.events,
            'state': state_mapping(runtime.state), 'wander': runtime.wander,
            'motion_auto': runtime.motion_auto, 'active_target': runtime.active_target,
            'captures': runtime.captures, 'trajectory_sha256': runtime.trajectory_sha256}


def phases(runtime):
    result = {}
    for name in ('shape', 'translation', 'morph', 'wander_mix'):
        blend = getattr(runtime, name)
        fraction = (runtime.state.tick - blend.tick) / blend.duration
        result[name] = {'raw_phase': float(fraction),
                        'phase': 'complete' if fraction >= 1 else 'start' if fraction <= 0 else 'in_progress',
                        'start_tick': blend.tick, 'duration_ticks': blend.duration}
    return result


def budget(runtime, translation=None):
    """Independent corner enclosure with explicit per-element radial capacity."""
    translation = runtime.translation if translation is None else translation
    relative = runtime.scene.home_xy - runtime.scene.home_xy.mean(axis=0)
    wander = .08 * max(float(runtime.wander_mix.start), float(runtime.wander_mix.end))
    maxima = np.zeros(len(relative))
    labels = [None] * len(relative)
    for si, ti, mi, sx, sy in product(range(2), range(2), range(2), (-1, 1), (-1, 1)):
        offset = ((runtime.shape.start, runtime.shape.end)[si]
                  + (translation.start, translation.end)[ti]
                  + (runtime.morph.start, runtime.morph.end)[mi] * relative * [-.5, 1.]
                  + wander * np.array([sx, sy]))
        norms = np.linalg.norm(offset, axis=1)
        for index in np.flatnonzero(norms > maxima):
            maxima[index] = norms[index]
            labels[index] = {'shape_endpoint': si, 'translation_endpoint': ti,
                             'morph_endpoint': mi, 'wander_sign': [sx, sy]}
    caps = np.minimum(runtime.scene.max_displacement,
                      runtime.scene.max_total_force / runtime.scene.spring_k)
    rows = [{'element': element.id, 'worst_corner_offset': float(maxima[index]),
             'offset_cap': float(caps[index]),
             'remaining_radial_offset': float(caps[index] - maxima[index]),
             'remaining_force': float(runtime.scene.max_total_force - maxima[index] * runtime.scene.spring_k[index]),
             'worst_corner': labels[index]}
            for index, element in enumerate(runtime.scene.elements)]
    return {'method': 'independent-exhaustive-endpoint-and-wander-box-v1',
            'meaning': 'Radial slack at all current corners; this is not additive directional travel capacity.',
            'wander_box_component': wander,
            'min_remaining_radial_offset': min(row['remaining_radial_offset'] for row in rows),
            'min_remaining_force': min(row['remaining_force'] for row in rows),
            'feasible': bool(np.all(maxima <= caps)), 'elements': rows}


def path_capacity(runtime, requested, duration):
    """Analytically solve each affine-endpoint norm constraint along old->asked.

    The fixed translation start is separately checked by budget(). With every
    other channel corner fixed, ||a + alpha*d|| <= cap gives a quadratic upper
    root; the intersection is an interval because alpha=0 was already admitted.
    This independent calculation does not use the production 48 bisections.
    """
    origin = runtime.translation.end.copy()
    delta = np.array(requested) - origin
    trial = deepcopy(runtime.translation)
    trial.set(requested, runtime.state.tick, duration)
    requested_budget = budget(runtime, trial)
    relative = runtime.scene.home_xy - runtime.scene.home_xy.mean(axis=0)
    wander = .08 * max(float(runtime.wander_mix.start), float(runtime.wander_mix.end))
    caps = np.minimum(runtime.scene.max_displacement,
                      runtime.scene.max_total_force / runtime.scene.spring_k)
    maximum = 1.
    limiting = None
    aa = float(np.dot(delta, delta))
    if aa:
        for si, mi, sx, sy in product(range(2), range(2), (-1, 1), (-1, 1)):
            fixed = ((runtime.shape.start, runtime.shape.end)[si]
                     + (runtime.morph.start, runtime.morph.end)[mi] * relative * [-.5, 1.]
                     + wander * np.array([sx, sy]) + origin)
            for index, offset in enumerate(fixed):
                bb = float(2 * np.dot(offset, delta))
                cc = float(np.dot(offset, offset) - caps[index] ** 2)
                discriminant = max(0., bb * bb - 4 * aa * cc)
                upper = (-bb + np.sqrt(discriminant)) / (2 * aa)
                if upper < maximum:
                    maximum = float(max(0., upper))
                    limiting = runtime.scene.elements[index].id
    return {'requested_endpoint_budget': requested_budget,
            'independent_max_fraction_along_prior_endpoint_segment': maximum,
            'independent_max_endpoint_delta': float(maximum * np.linalg.norm(delta)),
            'limiting_element': limiting,
            'requested_endpoint': list(requested), 'prior_endpoint': origin.tolist()}


class Experiment:
    def __init__(self, out, name, description, config, targets):
        self.name, self.description = name, description
        self.runtime = MorphRuntime(config, targets)
        self.recorder = MorphRecorder(out / name / 'record', self.runtime)
        self.commands = []
        self.numerics = {'accepted_steps': 0, 'all_committed_states_valid': True,
                         'max_displacement': 0., 'max_speed': 0., 'max_bias_force': 0.,
                         'step_rejections': []}

    def command(self, text):
        r = self.runtime
        before = deepcopy(snapshot(r))
        row = {'raw_command': text, 'tick': r.state.tick,
               'parsed_command': parse_command(text),
               'active_mode_before': 'adaptive' if r.motion_auto else 'strict',
               'active_shape_before': r.active_target, 'transition_phase_before': phases(r),
               'previous_translation_endpoint': r.translation.end.tolist(),
               'available_conservative_budget_before': budget(r),
               'requested_target': None, 'effective_accepted_target': None}
        parsed = row['parsed_command']
        if parsed['action'] == 'motion' and parsed['motion']['action'] in ('left', 'right', 'up', 'down'):
            motion = parsed['motion']
            requested = np.array({'left': [-1., 0.], 'right': [1., 0.],
                                  'up': [0., 1.], 'down': [0., -1.]}[motion['action']]) * motion['strength']
            row['requested_target'] = requested.tolist()
            row['available_requested_path_capacity'] = path_capacity(r, requested.tolist(), motion['duration_ticks'])
        elif parsed['action'] == 'morph':
            row['requested_target'] = {'shape': parsed['target'], 'offsets': r.targets[parsed['target']]['offsets']}
        try:
            event = r.accept(text)
        except Exception as error:
            frames = traceback.extract_tb(error.__traceback__)
            row['admission_decision'] = 'REJECT'
            row['rejection'] = {'type': type(error).__name__, 'message': str(error),
                                'source': [{'file': str(Path(frame.filename).relative_to(ROOT)),
                                            'line': frame.lineno, 'function': frame.name,
                                            'statement': frame.line}
                                           for frame in frames if Path(frame.filename).is_relative_to(ROOT)]}
        else:
            self.recorder.record_event(event)
            row['admission_decision'] = 'ACCEPT'
            row['event'] = event
            row['feedback'] = r.command_feedback(event)
            if row['requested_target'] is not None and parsed['action'] == 'motion':
                row['effective_accepted_target'] = r.translation.end.tolist()
            elif parsed['action'] == 'morph':
                row['effective_accepted_target'] = {'shape': r.active_target, 'offsets': r.shape.end.tolist()}
        after = snapshot(r)
        row['mutation'] = {key: canonical_bytes(before[key]) != canonical_bytes(after[key]) for key in before}
        row['endpoint_delta'] = (r.translation.end - np.array(row['previous_translation_endpoint'])).tolist()
        row['active_mode_after'] = 'adaptive' if r.motion_auto else 'strict'
        row['active_shape_after'] = r.active_target
        row['numerical_validity_immediately_after'] = validate_state(r.state, r.scene)
        row['available_conservative_budget_after'] = budget(r)
        self.commands.append(row)

    def advance(self, count):
        r = self.runtime
        for _ in range(count):
            before = snapshot(r)
            self.numerics['max_bias_force'] = max(self.numerics['max_bias_force'],
                float(np.linalg.norm(r.scene.spring_k[:, None] * r.target_offsets(r.state.tick), axis=1).max()))
            try:
                r.step()
            except Exception as error:
                self.numerics['step_rejections'].append({'tick': r.state.tick, 'error': str(error),
                                                       'mutated': canonical_bytes(before) != canonical_bytes(snapshot(r))})
                return
            self.numerics['accepted_steps'] += 1
            self.numerics['all_committed_states_valid'] &= not bool(validate_state(r.state, r.scene))
            self.numerics['max_displacement'] = max(self.numerics['max_displacement'],
                float(np.linalg.norm(r.state.positions - r.scene.home_xy, axis=1).max()))
            self.numerics['max_speed'] = max(self.numerics['max_speed'],
                float(np.linalg.norm(r.state.velocities, axis=1).max()))

    def finish(self):
        r = self.runtime
        path = self.recorder.finish(r)
        verified = verify_session(path)
        replay = None
        for replay in replay_runtimes(path):
            pass
        exact_final_snapshot = canonical_bytes(snapshot(replay)) == canonical_bytes(snapshot(r))
        result = {'name': self.name, 'description': self.description,
                  'commands': self.commands, 'numerics': self.numerics,
                  'final_tick': r.state.tick, 'final_validity_failures': validate_state(r.state, r.scene),
                  'replay': {**verified, 'full_runtime_snapshot_identical': exact_final_snapshot,
                             'session': str(path.relative_to(ROOT))},
                  'final_snapshot': snapshot(r)}
        atomic_json(path.parents[1] / 'scenario.json', result)
        return result


def main():
    expected_sources = {'commander_zorg/__init__.py': '56683f1eb67bb6ac789c5138bff0b0c09a90b20c1cb2717680ff663ee5fb4ffc', 'commander_zorg/canonical.py': 'd28df82a01fe77cdedb5191b8a9061e4f6bd39c28e5ff24de559c685c5ab5268', 'commander_zorg/cli.py': '3b14c03a2f61a8cf404b004162647864cd84b3c2cf5cd0cc5836f5a5bf1c93fe', 'commander_zorg/config.py': '54177706828d7a8b9d1a0fb016895bd1e3d64dbd3c182b9031ea88d355aca29b', 'commander_zorg/cues.py': '6df989d65ef568e145897d0c96cd81b759c0f684847e9972a8a39789dfc9cd12', 'commander_zorg/evidence.py': '4457f82067cb4976d33a2c742d345de8c02de5d8484a0830c9f87be754e92fff', 'commander_zorg/experiments.py': '265fb7bc0237b195f40187792ee67b1fe49fd2e576e819ecebd0e6dfb32b7784', 'commander_zorg/field.py': 'a1916662b54dcf3f52d8becd99210e3b670ec0d9275ab3c2df2df063450b636d', 'commander_zorg/guard.py': '6ecabf3bf1466c5d272f0212896f1cfd8bb714d5699eb7ffa371caaec64245fc', 'commander_zorg/live.py': 'cef2163167eae44005d84dc1ed3f188ee743ddab0e5bdeea29f09abc7010130f', 'commander_zorg/live_commands.py': '2fd24423b0980e0d90b6999e945677ddf4a7bfafe88ad0d18a785591d5ccc71b', 'commander_zorg/live_demo.py': 'b4b8de6e3809ba82174c0f8b925bab99619693b7e2124e40e92285f1dadd94f5', 'commander_zorg/live_export.py': 'df532d019bcbe89825dff94b2bb523a528f504093a50d838c783d7a1de15d78d', 'commander_zorg/live_motion.py': '666e0e49142a667d3bfc3637a8b7ec2dd23501b69cbc4e2900d83e83ef7d8373', 'commander_zorg/morph_commands.py': '5d52024b38de8d58453d2cf76f506553779a541b53536d6423543a54b22a686b', 'commander_zorg/morph_export.py': '3fab5b3df506fc26227634797ec7b708fbd47afb676ae3179375251b8426df9c', 'commander_zorg/morph_lab.py': 'a2861aa5b9cb1579aaafb109fe7e12e8c0e6b55586f6390a402d8e6969f76609', 'commander_zorg/morph_runtime.py': '9e747424349be876212238df459616f351e59202153882ccc5c142f6eafdaeb6', 'commander_zorg/morph_session.py': '75f0d1c991c5237a06804b2cf2a6d3c0c7c2a6fd0e28467ac2b95908acfdc5fb', 'commander_zorg/morph_targets.py': '1c43d8319398c8749d20c0e1d32d9e37787e36b1a29685aed9825516520373f7', 'commander_zorg/motion.py': 'c9e3a6390bb5245870c6de51bb7ab9fd99b3a3ffcb9edddf12e37eb9a914b54c', 'commander_zorg/raster.py': 'f01dbb7aca44317c88681f9427d790b8e2577a63e4218d7719ba5fed8712d260', 'commander_zorg/session.py': '8ff9ebe11d874d1792ffcd5493de8a14f5aab57ff3b55f258b080764cb26d723', 'commander_zorg/state.py': 'd2d0f8d75f00435e9f9c7351e5295239c06dbe37df2de58885a169d2e55ca7c6', 'commander_zorg/terminal_view.py': '7295966c0c02678e385d3bafd5651d842b3c243d2f1c0808696ccea4d9ca2e0f', 'pyproject.toml': 'f1e91ada61ca796226f67c81ea10e0fbdf46672411ddc0dd89183ea61dee4ae0', 'requirements.lock': '2d111dec6792f4d25cdf133c0eeaf8ea1b58543a6dec38ef440cf345aaa7d9c1'}
    if engine_sources() != expected_sources:
        raise SystemExit("Baseline-only probe: engine sources differ from PR #7 a0da2378. Run this script from an unchanged baseline checkout; do not use current results as baseline evidence.")
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'work/checkpoint-a/baseline-matrix')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = read_json(ROOT / 'scenes/live_lab.json')
    targets = load_targets(ROOT / 'morph_targets', LiveRuntime(config).scene)
    source_before = engine_sources()
    scenarios = []

    def experiment(name, description):
        return Experiment(args.out, name, description, config, targets)

    e = experiment('01-home-up', 'Home, adaptive on, up; settle and repeat to probe truthful success.')
    e.command('motion auto on'); e.command('up'); e.advance(360); e.command('up'); e.advance(180)
    scenarios.append(e.finish())
    e = experiment('02-cloud-up', 'Cloud settles before first adaptive up.')
    e.command('morph cloud'); e.advance(360); e.command('motion auto on'); e.command('up'); e.advance(360)
    scenarios.append(e.finish())
    e = experiment('03-cloud-up-again', 'Cloud adaptive up, settle, identical up again.')
    e.command('morph cloud'); e.advance(360); e.command('motion auto on'); e.command('up'); e.advance(360); e.command('up'); e.advance(180)
    scenarios.append(e.finish())
    e = experiment('04-oval-cloud-up-overlap', 'Oval still in progress; cloud supersedes; up during cloud blend.')
    e.command('morph oval'); e.advance(45); e.command('morph cloud'); e.advance(17); e.command('motion auto on'); e.command('up'); e.advance(360)
    scenarios.append(e.finish())
    e = experiment('05-cloud-wander-on', 'Explicit wander on with settled cloud and adaptive up.')
    e.command('morph cloud'); e.command('wander on'); e.advance(360); e.command('motion auto on'); e.command('up'); e.advance(360)
    scenarios.append(e.finish())
    e = experiment('06-cloud-wander-off', 'Explicit wander off fully settles before adaptive up.')
    e.command('morph cloud'); e.command('wander off'); e.advance(360); e.command('motion auto on'); e.command('up'); e.advance(360)
    scenarios.append(e.finish())
    e = experiment('07-cloud-up-left-up', 'Direction switches after each previous target settles.')
    e.command('morph cloud'); e.advance(360); e.command('motion auto on')
    for text in ('up', 'left', 'up'):
        e.command(text); e.advance(360)
    scenarios.append(e.finish())
    e = experiment('08-rapid-direction-changes', 'Cloud transition remains active while direction supersedes every seven ticks.')
    e.command('morph cloud'); e.advance(17); e.command('motion auto on')
    for text in ('up', 'left', 'down', 'right', 'up', 'left', 'up', 'down'):
        e.command(text); e.advance(7)
    e.advance(360); scenarios.append(e.finish())
    e = experiment('09-direction-then-morph', 'Accepted home up followed by cloud morph in adaptive mode; morph remains strict.')
    e.command('motion auto on'); e.command('up'); e.advance(360); e.command('morph cloud'); e.advance(360)
    scenarios.append(e.finish())

    pair = []
    for mode in ('strict', 'adaptive'):
        e = experiment('10-identical-start-' + mode, 'Identical settled cloud dynamics; only adaptive mode flag/event differs.')
        e.command('morph cloud'); e.advance(360)
        if mode == 'adaptive':
            e.command('motion auto on')
        e.starting_state_digest = sha256(canonical_bytes(state_mapping(e.runtime.state)))
        e.starting_channels_digest = sha256(canonical_bytes(e.runtime.channels()))
        e.command('up'); e.advance(360)
        result = e.finish()
        result['comparison_start'] = {'state_sha256': e.starting_state_digest,
                                     'channels_sha256': e.starting_channels_digest}
        pair.append(result)
    scenarios.extend(pair)
    for repeats in (1, 2):
        e = experiment(f'probe-wander-off-{repeats}', 'One versus two settled wander-off commands.')
        e.command('morph cloud'); e.advance(360)
        for _ in range(repeats):
            e.command('wander off'); e.advance(180)
        e.command('motion auto on'); e.command('up'); e.advance(360)
        scenarios.append(e.finish())
    for repeats in (1, 2):
        e = experiment(f'probe-cloud-home-{repeats}', 'Completed home blend retains old cloud endpoint.')
        e.command('morph cloud'); e.advance(360)
        for _ in range(repeats):
            e.command('morph home .5'); e.advance(360)
        e.command('motion auto on'); e.command('up'); e.advance(360)
        scenarios.append(e.finish())
    assert pair[0]['comparison_start'] == pair[1]['comparison_start']
    assert engine_sources() == source_before, 'Experiment source changed during baseline run'
    report = {'baseline_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'environment': environment_info(), 'python_executable': sys.executable,
              'module_file': str(sys.modules[MorphRuntime.__module__].__file__),
              'terminal': {key: os.environ.get(key) for key in ('TERM', 'COLORTERM', 'TERM_PROGRAM')},
              'source': source_before,
              'matrix_scenarios': 10, 'recorded_runs': len(scenarios),
              'identical_strict_adaptive_start': pair[0]['comparison_start'] == pair[1]['comparison_start'],
              'all_valid': all(not s['final_validity_failures'] and s['numerics']['all_committed_states_valid'] for s in scenarios),
              'all_exact_replay': all(s['replay']['exact_replay'] and s['replay']['full_runtime_snapshot_identical'] for s in scenarios),
              'scenarios': scenarios}
    atomic_json(args.out / 'matrix.json', report)
    print('Saved', args.out / 'matrix.json')
    print('All valid:', report['all_valid'], 'all exact replay:', report['all_exact_replay'])
    for scenario in scenarios:
        print(scenario['name'], [(row['raw_command'], row['admission_decision'], row['effective_accepted_target'])
                                 for row in scenario['commands']
                                 if row['requested_target'] is not None and row['parsed_command']['action'] == 'motion'])


if __name__ == '__main__':
    main()
