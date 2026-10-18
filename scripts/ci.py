"""Standard-library CI evidence recorder; never changes pytest outcomes or engine state.

Loaded as a passive pytest plugin only in CI, and invoked as a small CLI by the
workflows. Each child retains its real exit code and streams its complete log.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BASELINE_TESTS = 716  # Independently collected on main cc9d563; reductions need review.
RESULTS = Path(os.environ.get('ZORG_CI_RESULTS', 'ci-results'))
PHASES = {}
DESELECTED = []
COLLECTION_PROBLEMS = []
HELP_COMMANDS = ('validate', 'live', 'live-demo', 'morph-lab', 'morph-demo',
                 'render-morph-session', 'verify-morph-session')
COMMON_STAGES = ('locked-dependencies', 'editable-install', 'dependency-check', 'diagnostics')


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


# Passive hooks: observe the actual collection and setup/call/teardown reports.
def pytest_deselected(items):
    DESELECTED.extend(item.nodeid for item in items)


def pytest_collectreport(report):
    if report.failed or report.skipped:
        COLLECTION_PROBLEMS.append({'nodeid': report.nodeid, 'outcome': report.outcome,
                                    'detail': str(report.longrepr)})


def pytest_runtest_logreport(report):
    PHASES.setdefault(report.nodeid, []).append({
        'phase': report.when, 'outcome': report.outcome,
        'wasxfail': getattr(report, 'wasxfail', None)})


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get('ZORG_CI_PYTEST_REPORT')
    if not destination:
        return
    tests = []
    for item in session.items:
        phases = PHASES.get(item.nodeid, [])
        call = next((p for p in phases if p['phase'] == 'call'), None)
        if any(p['outcome'] == 'failed' and p['phase'] != 'call' for p in phases):
            outcome = 'error'
        elif any(p['outcome'] == 'failed' for p in phases):
            outcome = 'failed'
        elif any(p['wasxfail'] is not None for p in phases):
            outcome = 'xpassed' if call and call['outcome'] == 'passed' else 'xfailed'
        elif any(p['outcome'] == 'skipped' for p in phases):
            outcome = 'skipped'
        else:
            outcome = 'passed' if call and call['outcome'] == 'passed' else 'not_executed'
        tests.append({'nodeid': item.nodeid, 'outcome': outcome,
                      'call_executed': call is not None, 'phases': phases})
    write_json(destination, {'collected': len(session.items) + len(DESELECTED),
        'selected': len(session.items), 'deselected': DESELECTED,
        'collection_problems': COLLECTION_PROBLEMS, 'pytest_exit_status': int(exitstatus),
        'call_executed': sum(t['call_executed'] for t in tests),
        'counts': dict(Counter(t['outcome'] for t in tests)), 'tests': tests})


def run_stage(name, command, pytest_report=None):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
        raise ValueError('invalid CI stage name')
    RESULTS.mkdir(parents=True, exist_ok=True)
    status_path = RESULTS / f'{name}.json'
    if status_path.exists():
        raise FileExistsError(f'CI stage already executed: {name}')
    info = {'stage': name, 'command': command, 'status': 'running', 'exit_code': None}
    environment = os.environ.copy()
    if pytest_report:
        report_path = RESULTS / pytest_report
        if report_path.exists():
            raise FileExistsError('refusing stale pytest evidence')
        environment['PYTEST_PLUGINS'] = 'scripts.ci'
        environment['ZORG_CI_PYTEST_REPORT'] = str(report_path.resolve())
        info['pytest_report'] = str(report_path)
        info['pytest_plugin'] = 'scripts.ci (observation only)'
    write_json(status_path, info)
    started = time.monotonic()
    try:
        with (RESULTS / f'{name}.log').open('wb') as log:
            child = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            try:
                for line in child.stdout:
                    log.write(line)
                    log.flush()
                    sys.stdout.buffer.write(line)
                    sys.stdout.buffer.flush()
                code = child.wait()
            except BaseException:
                child.terminate()
                child.wait(timeout=10)
                raise
            finally:
                child.stdout.close()
        info.update(status='passed' if code == 0 else 'failed', exit_code=code)
    except BaseException as error:
        info.update(status='error', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        info['elapsed_seconds'] = time.monotonic() - started
        write_json(status_path, info)
    # Keep the actual child status in JSON; normalize signals for shell exit only.
    return code if code >= 0 else 128 - code


def diagnostics():
    versions = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}
    data = {'runner_os': os.environ.get('RUNNER_OS', 'local'), 'platform': platform.platform(),
        'machine': platform.machine(), 'python': sys.version,
        'commit_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'event_sha': os.environ.get('GITHUB_SHA'), 'event': os.environ.get('GITHUB_EVENT_NAME'),
        'dependencies': dict(sorted(versions.items())),
        'optional_ffmpeg': 'available' if shutil.which('ffmpeg') else 'unavailable',
        'deep_media_policy': 'MP4 disabled explicitly; PNG/HTML and mathematical checks remain required'}
    write_json(RESULTS / 'environment.json', data)
    print(json.dumps(data, indent=2))
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Python 3.12 is required')
    if data['event_sha'] and data['event_sha'] != data['commit_sha']:
        raise ValueError('checkout differs from the event commit')


def audit_tests(junit):
    report = json.loads((RESULTS / 'pytest-outcomes.json').read_text())
    cases = list(ET.parse(junit).iter('testcase'))
    junit_counts = Counter('error' if case.find('error') is not None else
        'failed' if case.find('failure') is not None else
        'skipped' if case.find('skipped') is not None else 'passed' for case in cases)
    # Pytest can emit two JUnit rows for a test with a teardown error. Such a
    # run fails below; do not misreport those rows as additional collected tests.
    problems = []
    if report['selected'] < BASELINE_TESTS:
        problems.append(f"selected {report['selected']} tests, below baseline {BASELINE_TESTS}")
    if report['deselected'] or report['collection_problems']:
        problems.append('deselection or collection errors/skips occurred')
    if report['pytest_exit_status'] != 0:
        problems.append(f"pytest exited {report['pytest_exit_status']}")
    if report['call_executed'] != report['selected']:
        problems.append('some selected test bodies did not execute')
    if report['counts'].get('passed', 0) != report['selected']:
        problems.append('not all selected tests passed; skipped/xfail/xpass are not acceptance')
    if dict(junit_counts) != {'passed': report['selected']}:
        problems.append('JUnit does not independently confirm all selected tests passed')
    result = {'baseline_minimum': BASELINE_TESTS, 'collected': report['collected'],
        'selected': report['selected'], 'call_executed': report['call_executed'],
        'outcomes': report['counts'], 'junit_rows': len(cases),
        'junit_outcomes': dict(junit_counts), 'problems': problems, 'passed': not problems}
    write_json(RESULTS / 'test-audit-report.json', result)
    print(json.dumps(result, indent=2))
    return 1 if problems else 0


def smoke():
    codes = [run_stage(f'help-{name}', ['commander-zorg', name, '--help'])
             for name in HELP_COMMANDS]
    codes += [run_stage(f'validate-{name}', ['commander-zorg', 'validate', f'scenes/{name}.json'])
              for name in ('e1', 'control')]
    return int(any(code != 0 for code in codes))


def compact_evidence(take):
    """Copy bounded reports/manifests only; never publish frames, traces or source."""
    names = {'manifest.json', 'experiment_manifest.json', 'experiment_status.json',
        'profile_report.json', 'cadence.json', 'operation_timings.json', 'replay_report.json',
        'test_report.json', 'junit.xml', 'test-output.txt', 'check_report.json',
        'measurements.json', 'export_status.json', 'status.json', 'run_status.json'}
    destination = RESULTS / 'deep'
    copied = []; total = 0
    for path in sorted(Path(take).rglob('*')):
        relative = path.relative_to(take)
        if (not path.is_file() or path.is_symlink() or
            any(part in ('source', 'frames', 'captures') for part in relative.parts)):
            continue
        if path.name not in names and not path.name.endswith('_integrity.json'):
            continue
        total += path.stat().st_size
        if total > 20 * 1024 * 1024:
            raise ValueError('compact report budget exceeded (20 MiB); do not silently omit evidence')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied.append(str(relative))
    write_json(RESULTS / 'deep-index.json', {'take': str(take), 'bytes': total, 'files': copied})


def summary(mode):
    required = list(COMMON_STAGES)
    if mode == 'fast':
        required += ['pytest', 'test-audit'] + [f'help-{name}' for name in HELP_COMMANDS]
        required += ['validate-e1', 'validate-control']
    else:
        required += ['build0', 'test-audit', 'morph-demo', 'morph-check', 'live-demo', 'live-check', 'compact-reports']
    rows = []
    for name in required:
        path = RESULTS / f'{name}.json'
        rows.append(json.loads(path.read_text()) if path.exists() else
                    {'stage': name, 'status': 'not_executed', 'exit_code': None})
    complete = all(row['status'] == 'passed' and row['exit_code'] == 0 for row in rows)
    lines = [f'# ZORG {mode} validation', '',
        'Mandatory stages: ' + ('passed' if complete else 'FAILED / incomplete'), '',
        '| Stage | Outcome | Exit status |', '| --- | --- | --- |']
    lines += [f"| {r['stage']} | {r['status']} | {r['exit_code'] if r['exit_code'] is not None else 'not available'} |" for r in rows]
    for filename, title in (('environment.json', 'Environment'), ('test-audit-report.json', 'Test inventory')):
        path = RESULTS / filename
        if path.exists():
            lines += ['', f'## {title}', '', '```json', path.read_text(), '```']
    outcomes = RESULTS / 'pytest-outcomes.json'
    if outcomes.exists():
        data = json.loads(outcomes.read_text())
        lines += ['', '## Tests requiring attention', '']
        attention = [f"- `{test['nodeid']}`: {test['outcome']}" for test in data['tests'] if test['outcome'] != 'passed']
        attention += [f"- Collection `{p['nodeid']}`: {p['outcome']}" for p in data['collection_problems']]
        lines += attention or ['None.']
    lines += ['', 'See JUnit and stage logs for complete tracebacks. Missing stages are not passes.',
              'Deep MP4 encoding is explicitly disabled; optional FFmpeg availability is diagnostic only.']
    RESULTS.mkdir(parents=True, exist_ok=True)
    content = '\n'.join(lines) + '\n'
    (RESULTS / 'summary.md').write_text(content, encoding='utf-8')
    write_json(RESULTS / 'stages.json', {'mode': mode, 'passed': complete, 'stages': rows})
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(content)
    print(content)
    return 0 if complete else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    run = sub.add_parser('run')
    run.add_argument('--pytest-report')
    run.add_argument('stage')
    run.add_argument('command', nargs=argparse.REMAINDER)
    sub.add_parser('diagnostics')
    audit = sub.add_parser('audit-tests'); audit.add_argument('--junit', type=Path, required=True)
    sub.add_parser('smoke')
    compact = sub.add_parser('compact'); compact.add_argument('take', type=Path)
    report = sub.add_parser('summary'); report.add_argument('mode', choices=('fast', 'deep'))
    args = parser.parse_args()
    if args.action == 'run':
        command = args.command[1:] if args.command[:1] == ['--'] else args.command
        if not command: parser.error('a child command is required')
        return run_stage(args.stage, command, args.pytest_report)
    if args.action == 'diagnostics': diagnostics(); return 0
    if args.action == 'audit-tests': return audit_tests(args.junit)
    if args.action == 'smoke': return smoke()
    if args.action == 'compact': compact_evidence(args.take); return 0
    return summary(args.mode)


if __name__ == '__main__':
    raise SystemExit(main())
