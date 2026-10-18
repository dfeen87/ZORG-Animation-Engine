"""Live extension foundation: fixed ticks, genuine geometry, and exact replay."""
from pathlib import Path

import numpy as np
import pytest

from commander_zorg.canonical import read_json
from commander_zorg.field import evaluate_samples
from commander_zorg.live_commands import parse_command
from commander_zorg.live_motion import LiveRuntime, LiveNumericalError
from commander_zorg.raster import rasterize, measure_mask
from commander_zorg.session import Recorder, verify_session


@pytest.fixture
def live_config():
    return read_json(Path(__file__).parents[1]/'scenes/live_lab.json')


def test_seeded_autonomous_and_left_checkpoint(live_config,tmp_path):
    a,b = LiveRuntime(live_config),LiveRuntime(live_config)
    recorder = Recorder(tmp_path/'record',live_config)
    first = rasterize(evaluate_samples(a.state,a.scene),a.scene)
    for tick in range(240):
        if tick == 60:
            event = a.accept('left')
            recorder.record_event(event)
            b.apply_event(event)
        a.step()
        b.step()
        assert np.array_equal(a.state.positions,b.state.positions)
    last = rasterize(evaluate_samples(a.state,a.scene),a.scene)
    assert not np.array_equal(first,last)
    assert measure_mask(last,a.scene)['centroid'][0] < -.20
    assert a.state.tick == 240
    assert a.events[0]['effective_tick'] == 60
    path = recorder.finish(a)
    assert verify_session(path)['states'] == 241


@pytest.mark.parametrize('text',['left nan','left inf','left -1','left .4','left .3 0','left .3 11','unknown','left .3 2 extra'])
def test_invalid_input(text):
    with pytest.raises(ValueError):
        parse_command(text)


def test_force_rejection_preserves_owned_state(live_config):
    runtime = LiveRuntime(live_config)
    old = runtime.state
    runtime.target_offsets = lambda tick: np.full_like(old.positions,10.)
    with pytest.raises(LiveNumericalError,match='force limit'):
        runtime.step()
    assert runtime.state is old
    assert not old.positions.flags.writeable


def test_autonomous_seed_and_smoothness(live_config):
    a,b = LiveRuntime(live_config),LiveRuntime({**live_config,'seed':1})
    initial = a.state.positions.copy()
    for _ in range(360):
        old = a.state
        a.step(); b.step()
        assert np.max(np.linalg.norm(a.state.positions-old.positions,axis=1)) < .004
        assert np.isfinite(a.state.positions).all()
    assert not np.array_equal(a.state.positions,initial)
    assert not np.array_equal(a.state.positions,b.state.positions)
