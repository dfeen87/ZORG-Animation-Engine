"""V11: real process isolation and configuration metamorphisms."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from commander_zorg import evidence
from commander_zorg.config import resolve_scene


def _json(path):
    return json.loads(Path(path).read_bytes())


def _rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def _small_document():
    doc = _json(Path(__file__).parents[1] / "scenes" / "e1.json")
    doc["raster"].update(width=64, height=64)
    doc["timeline"]["frame_count"] = 12
    doc["cues"][0].update(start_tick=0, end_tick=20, force_xy=[4.0, 1.0])
    return doc


def _pixel_hashes(run):
    return [row["pixel_sha256"] for row in _rows(run / "frames.jsonl")]


def test_two_fresh_processes_reproduce_traces_pixels_and_png_bytes(tmp_path):
    scene_file = tmp_path / "scene.json"
    scene_file.write_text(json.dumps(_small_document()))
    commands = []
    runs = [tmp_path / "process_one", tmp_path / "process_two"]
    for run in runs:
        command = [sys.executable, "-c",
                   "import sys; from commander_zorg.cli import main; sys.exit(main())",
                   "render", str(scene_file), "--out", str(run)]
        commands.append(command)
        result = subprocess.run(command, capture_output=True, text=True, check=False,
                                cwd=Path(__file__).parents[1])
        assert result.returncode == 0, result.stdout + result.stderr
        assert evidence.verify_integrity(run / "manifest.json")["passed"]
    assert commands[0][-1] != commands[1][-1]
    for name in ("states.jsonl", "decisions.jsonl"):
        assert (runs[0] / name).read_bytes() == (runs[1] / name).read_bytes()
    assert _pixel_hashes(runs[0]) == _pixel_hashes(runs[1])
    for index in range(12):
        name = f"frames/frame_{index:06d}.png"
        assert (runs[0] / name).read_bytes() == (runs[1] / name).read_bytes()


def test_replay_api_starts_subprocess_and_retains_comparison_report(tmp_path, monkeypatch):
    run = tmp_path / "original"
    replay = tmp_path / "replay"
    evidence.render_run(resolve_scene(_small_document()), run)
    calls = []
    original = evidence.subprocess.run

    def observe(*args, **kwargs):
        calls.append(args[0] if args else kwargs.get("args"))
        return original(*args, **kwargs)

    monkeypatch.setattr(evidence.subprocess, "run", observe)
    report = evidence.verify_replay(run / "manifest.json", replay)
    assert calls, "replay must execute a new engine process"
    assert report["passed"] is True
    saved = _json(replay / "replay_report.json")
    assert saved["passed"] is True
    assert (run / "states.jsonl").read_bytes() == (replay / "states.jsonl").read_bytes()
    assert (run / "decisions.jsonl").read_bytes() == (replay / "decisions.jsonl").read_bytes()
    assert _pixel_hashes(run) == _pixel_hashes(replay)


def test_active_cue_change_alters_config_trajectory_and_decoded_image(tmp_path):
    document = _small_document()
    changed = copy.deepcopy(document)
    changed["cues"][0]["force_xy"] = [-4.0, 1.0]
    before, after = tmp_path / "before", tmp_path / "after"
    first = evidence.render_run(resolve_scene(document), before)
    second = evidence.render_run(resolve_scene(changed), after)
    assert first["config"]["resolved_sha256"] != second["config"]["resolved_sha256"]
    original_states = _rows(before / "states.jsonl")
    changed_states = _rows(after / "states.jsonl")
    assert original_states[0] == changed_states[0]
    assert any(a["positions"] != b["positions"]
               for a, b in zip(original_states[1:], changed_states[1:]))
    assert _pixel_hashes(before) != _pixel_hashes(after)


def test_provenance_seed_changes_hash_without_randomizing_motion_or_pixels(tmp_path):
    document = _small_document()
    changed = copy.deepcopy(document)
    changed["seed"] += 1
    before, after = tmp_path / "seed_one", tmp_path / "seed_two"
    first = evidence.render_run(resolve_scene(document), before)
    second = evidence.render_run(resolve_scene(changed), after)
    assert first["config"]["resolved_sha256"] != second["config"]["resolved_sha256"]
    assert (before / "states.jsonl").read_bytes() == (after / "states.jsonl").read_bytes()
    assert (before / "decisions.jsonl").read_bytes() == (after / "decisions.jsonl").read_bytes()
    assert _pixel_hashes(before) == _pixel_hashes(after)
    for index in range(12):
        name = f"frames/frame_{index:06d}.png"
        assert (before / name).read_bytes() == (after / name).read_bytes()


def test_replay_refuses_existing_destination(tmp_path):
    run, replay = tmp_path / "original", tmp_path / "exists"
    evidence.render_run(resolve_scene(_small_document()), run)
    replay.mkdir()
    (replay / "keep").write_text("keep")
    with pytest.raises((evidence.ExportError, evidence.ReplayError)):
        evidence.verify_replay(run / "manifest.json", replay)
    assert (replay / "keep").read_text() == "keep"


def test_exact_replay_refuses_changed_environment_without_claiming_tolerance_pass(tmp_path):
    run = tmp_path / "original"
    evidence.render_run(resolve_scene(_small_document()), run)
    manifest = _json(run / "manifest.json")
    manifest["environment"]["numpy"] = "different-backend-build"
    (run / "manifest.json").write_bytes(
        (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
    # Container integrity and replay environment equivalence are distinct claims.
    assert evidence.verify_integrity(run / "manifest.json")["passed"]
    with pytest.raises(evidence.ReplayError, match="environment"):
        evidence.verify_replay(run / "manifest.json", tmp_path / "replay")
    assert not (tmp_path / "replay").exists()


def test_replay_subprocess_failure_does_not_create_success_report(tmp_path, monkeypatch):
    run, replay = tmp_path / "original", tmp_path / "replay"
    evidence.render_run(resolve_scene(_small_document()), run)

    def failed_process(command, **kwargs):
        return subprocess.CompletedProcess(command, 4, stdout="", stderr="injected export error")

    monkeypatch.setattr(evidence.subprocess, "run", failed_process)
    with pytest.raises(evidence.ReplayError, match="exited 4"):
        evidence.verify_replay(run / "manifest.json", replay)
    assert not (replay / "replay_report.json").exists()


def test_exact_replay_requires_actual_current_source_match(tmp_path):
    run, replay = tmp_path / "original", tmp_path / "replay"
    evidence.render_run(resolve_scene(_small_document()), run)
    manifest = _json(run / "manifest.json")
    index = _json(run / "source/index.json")
    relative = "commander_zorg/motion.py"
    source_path = run / "source/files" / relative
    source_path.write_bytes(source_path.read_bytes() + b"\n# different recorded source\n")
    changed_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    index[relative] = changed_hash
    manifest["artifacts"]["source/files/" + relative] = changed_hash
    index_payload = (json.dumps(index, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (run / "source/index.json").write_bytes(index_payload)
    manifest["artifacts"]["source/index.json"] = hashlib.sha256(index_payload).hexdigest()
    manifest["source"]["digest"] = hashlib.sha256(index_payload).hexdigest()
    (run / "manifest.json").write_bytes(
        (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
    assert evidence.verify_integrity(run / "manifest.json")["passed"]
    with pytest.raises(evidence.ReplayError, match="source"):
        evidence.verify_replay(run / "manifest.json", replay)
    assert not replay.exists()
