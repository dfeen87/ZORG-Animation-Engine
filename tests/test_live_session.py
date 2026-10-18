"""Closed live recordings validate events, hashes, chronology and exact replay."""
from pathlib import Path

import pytest

from commander_zorg import session
from commander_zorg.canonical import atomic_json, canonical_bytes, read_json, sha256
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.state import state_mapping


@pytest.fixture
def config():
    return read_json(Path(__file__).parents[1] / "scenes/live_lab.json")


@pytest.fixture(autouse=True)
def source_inventory(monkeypatch):
    # These unit tests may run while other contributors edit files. Real-source
    # fresh-process acceptance is performed separately after the source settles.
    inventory = session.engine_sources()
    monkeypatch.setattr(session, "engine_sources", lambda: inventory.copy())
    return inventory


def _record(tmp_path, config, *, status="complete", count=180):
    runtime = LiveRuntime(config)
    recorder = session.Recorder(tmp_path / "take", config)
    planned = {0: ["right .3 .5", "stretch .6 .5"], 30: ["left .1 .5"],
               60: ["wander off"], 90: ["reset"], 120: ["wander on"],
               140: ["down .05 .5"], 150: ["squash .3 .5"]}
    states = [canonical_bytes(state_mapping(runtime.state))]
    for tick in range(count):
        for text in planned.get(tick, []):
            recorder.record_event(runtime.accept(text))
        runtime.step()
        states.append(canonical_bytes(state_mapping(runtime.state)))
    return recorder.finish(runtime, status=status), runtime, states


def _publish_metadata(path, doc):
    doc = {key: value for key, value in doc.items() if key != "session_sha256"}
    doc["session_sha256"] = sha256(canonical_bytes(doc))
    atomic_json(path, doc)


def _replace_events(path, events):
    data = b"".join(canonical_bytes(event) for event in events)
    (path.parent / "events.jsonl").write_bytes(data)
    doc = read_json(path)
    doc["events_sha256"] = sha256(data)
    doc["event_count"] = len(events)
    _publish_metadata(path, doc)


def test_complete_recording_replays_every_numerical_state(config, tmp_path):
    path, runtime, expected = _record(tmp_path, config)
    replayed = [canonical_bytes(state_mapping(state)) for state in session.replay_states(path)]
    assert replayed == expected
    report = session.verify_session(path)
    assert report["passed"] and report["states"] == 181
    assert report["trajectory_sha256"] == runtime.trajectory_sha256
    doc, events = session.load_session(path)
    assert doc["duration_seconds"] == 3.0
    assert doc["event_count"] == 8
    assert [event["sequence"] for event in events] == list(range(8))
    assert [event["effective_tick"] for event in events[:2]] == [0, 0]


def test_recording_owns_input_config_and_accepted_events(config, tmp_path):
    runtime = LiveRuntime(config)
    recorder = session.Recorder(tmp_path / "take", config)
    config["seed"] += 1
    event = runtime.accept("left .3 .5")
    recorder.record_event(event)
    event["strength"] = .1
    for _ in range(60):
        runtime.step()
    path = recorder.finish(runtime)
    doc, events = session.load_session(path)
    assert doc["config"]["seed"] != config["seed"]
    assert events[0]["strength"] == .3
    assert session.verify_session(path)["passed"]


def test_interrupted_recording_is_replayable(config, tmp_path):
    path, _, expected = _record(tmp_path, config, status="interrupted", count=41)
    assert read_json(path)["status"] == "interrupted"
    assert len(list(session.replay_states(path))) == len(expected)
    assert session.verify_session(path)["final_tick"] == 41


@pytest.mark.parametrize("artifact", ["config.json", "events.jsonl", "session.json"])
def test_artifact_tampering_is_rejected(config, tmp_path, artifact):
    path, _, _ = _record(tmp_path, config, count=40)
    target = path.parent / artifact
    if artifact == "session.json":
        doc = read_json(target)
        doc["final_tick"] += 1
        atomic_json(target, doc)  # Deliberately do not refresh its digest.
    else:
        target.write_bytes(target.read_bytes() + b" \n")
    with pytest.raises(ValueError, match="integrity"):
        session.load_session(path)


@pytest.mark.parametrize("field,value,message", [
    ("final_tick", True, "final tick"), ("final_tick", -1, "final tick"),
    ("final_tick", 216001, "final tick"),
    ("duration_seconds", 999, "duration"), ("event_count", True, "event count"),
    ("event_count", 999, "event count"), ("events", "../events.jsonl", "artifact path"),
])
def test_valid_hashes_do_not_excuse_invalid_session_semantics(config, tmp_path, field, value, message):
    path, _, _ = _record(tmp_path, config, count=40)
    doc = read_json(path)
    doc[field] = value
    _publish_metadata(path, doc)
    with pytest.raises(ValueError, match=message):
        session.load_session(path)


@pytest.mark.parametrize("change", [
    "future", "decreasing", "duplicate_sequence", "bad_scope", "huge_duration", "boolean_tick",
])
def test_hashed_events_must_still_satisfy_order_and_contract(config, tmp_path, change):
    path, _, _ = _record(tmp_path, config, count=40)
    _, events = session.load_session(path)
    if change == "future":
        events[0]["effective_tick"] = 41
    elif change == "decreasing":
        events[0]["effective_tick"], events[1]["effective_tick"] = 20, 10
    elif change == "duplicate_sequence":
        events[1]["sequence"] = 0
    elif change == "bad_scope":
        events[0]["scope"] = "head"
    elif change == "huge_duration":
        events[0]["duration_ticks"] = 10**1000
    elif change == "boolean_tick":
        events[0]["effective_tick"] = False
    _replace_events(path, events)
    with pytest.raises(ValueError):
        session.load_session(path)


@pytest.mark.parametrize("field,message", [
    ("trajectory_sha256", "trajectory replay"), ("final_state_sha256", "final state replay"),
])
def test_replay_recomputes_numerical_hashes(config, tmp_path, field, message):
    path, _, _ = _record(tmp_path, config, count=40)
    doc = read_json(path)
    doc[field] = "0" * 64
    _publish_metadata(path, doc)
    session.load_session(path)  # Container integrity is distinct from replay.
    with pytest.raises(ValueError, match=message):
        session.verify_session(path)


def test_changed_environment_and_sources_refuse_exact_replay(config, tmp_path, monkeypatch, source_inventory):
    path, _, _ = _record(tmp_path, config, count=40)
    original_environment = session.environment_info()
    monkeypatch.setattr(session, "environment_info", lambda: {**original_environment, "numpy": "different"})
    with pytest.raises(ValueError, match="environment differs"):
        session.load_session(path)
    monkeypatch.setattr(session, "environment_info", lambda: original_environment)
    changed = {**source_inventory, "commander_zorg/live_motion.py": "0" * 64}
    monkeypatch.setattr(session, "engine_sources", lambda: changed)
    with pytest.raises(ValueError, match="source differs"):
        session.load_session(path)


def test_dependency_manifests_are_in_source_inventory(source_inventory):
    assert {"requirements.lock", "pyproject.toml", "commander_zorg/live_motion.py", "commander_zorg/session.py"} <= source_inventory.keys()


def test_new_recording_never_overwrites_existing_take(config, tmp_path):
    path, _, _ = _record(tmp_path, config, count=40)
    before = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()}
    with pytest.raises(FileExistsError):
        session.Recorder(path.parent, config)
    assert {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("artifact", ["config.json", "events.jsonl"])
def test_symlink_artifacts_are_rejected(config, tmp_path, artifact):
    path, _, _ = _record(tmp_path, config, count=40)
    original = path.parent / artifact
    replacement = tmp_path / "relocated"
    replacement.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(replacement)
    with pytest.raises(ValueError, match="integrity"):
        session.load_session(path)


def test_running_and_failed_recordings_are_never_successful_replays(config, tmp_path):
    recorder = session.Recorder(tmp_path / "take", config)
    path = recorder.out / "session.json"
    with pytest.raises(ValueError, match="incomplete or failed"):
        session.load_session(path)
    runtime = LiveRuntime(config)
    recorder.finish(runtime, status="failed", reason="injected numerical rejection")
    assert read_json(path)["status"] == "failed"
    with pytest.raises(ValueError, match="incomplete or failed"):
        session.verify_session(path)


@pytest.mark.parametrize("torn", [False, True])
def test_failed_event_recording_saves_truthful_failed_status(config, tmp_path, torn):
    recorder = session.Recorder(tmp_path / "take", config)
    runtime = LiveRuntime(config)
    runtime.accept("left")  # Simulate a failure before this event is captured.
    if torn:
        recorder.events_path.write_bytes(b'{"truncated":')
    with pytest.raises(ValueError, match="mismatch"):
        recorder.finish(runtime, status="complete")
    path = recorder.finish(runtime, status="failed", reason="injected disk failure")
    doc = read_json(path)
    assert doc["status"] == "failed"
    assert "incomplete" in doc["reason"]
    with pytest.raises(ValueError, match="incomplete or failed"):
        session.verify_session(path)

