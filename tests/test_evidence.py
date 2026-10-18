"""V02/V07/V10/V12: closed artifacts, honest failures and hostile evidence.

Corruption fixtures deliberately recompute selected outer hashes. A checksum
alone must not make an invalid trace, PNG, metric or timeline acceptable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from commander_zorg import evidence
from commander_zorg import canonical
from commander_zorg.canonical import canonical_bytes
from commander_zorg.config import resolve_scene
from commander_zorg.state import SceneState


def _bytes(value):
    """Independent canonical oracle for these already-normalized fixtures."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False) + "\n").encode()


def _json(path):
    return json.loads(Path(path).read_bytes())


def _rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def _write_json(path, value):
    Path(path).write_bytes(_bytes(value))


def _rewrite_artifact(run, relative, payload):
    """Change an artifact AND its outer hash, preserving the invalid content."""
    path = run / relative
    path.write_bytes(payload)
    manifest = _json(run / "manifest.json")
    manifest["artifacts"][relative] = hashlib.sha256(payload).hexdigest()
    _write_json(run / "manifest.json", manifest)


@pytest.fixture
def small_doc():
    document = _json(Path(__file__).parents[1] / "scenes" / "e1.json")
    document["raster"].update(width=64, height=64)
    document["timeline"]["frame_count"] = 12
    document["cues"][0].update(start_tick=0, end_tick=20, force_xy=[4.0, 1.0])
    return document


@pytest.fixture
def completed_run(tmp_path, small_doc):
    run = tmp_path / "run"
    evidence.render_run(resolve_scene(small_doc), run)
    return run


def test_canonical_json_has_one_newline_sorted_keys_and_normalized_zero():
    assert canonical_bytes({"b": 2, "a": [-0.0, 1.0]}) == b'{"a":[0.0,1.0],"b":2}\n'
    with pytest.raises((ValueError, TypeError)):
        canonical_bytes({"bad": float("nan")})


def test_complete_schedule_frame_zero_and_terminal_audit(completed_run):
    manifest = _json(completed_run / "manifest.json")
    states = _rows(completed_run / "states.jsonl")
    decisions = _rows(completed_run / "decisions.jsonl")
    frames = _rows(completed_run / "frames.jsonl")
    assert [row["tick"] for row in states] == list(range(25))
    assert [row["attempted_tick"] for row in decisions] == list(range(1, 25))
    assert [row["tick"] for row in frames] == list(range(0, 24, 2))
    assert [row["index"] for row in frames] == list(range(12))
    assert all(row["status"] == "ACCEPT" for row in decisions)
    scene = _json(completed_run / "scene.resolved.json")
    homes = [item["home_xy"] for item in scene["elements"]]
    assert states[0]["positions"] == homes
    assert states[0]["velocities"] == [[0.0, 0.0]] * len(homes)
    assert manifest["counts"] == {"accepted": 24, "rejected": 0}
    assert manifest["expected"] == {"frames": 12, "states": 25, "transitions": 24}
    assert manifest["creator_review"] == {"status": "pending", "source": None}
    assert evidence.verify_integrity(completed_run / "manifest.json")["passed"]
    assert len(list((completed_run / "frames").glob("frame_*.png"))) == 12
    for row in frames:
        image_path = completed_run / row["path"]
        with Image.open(image_path) as image:
            image.load()
            assert image.mode == "L" and image.size == (64, 64)
            expected = hashlib.sha256(b"cz-gray8-v1\n64,64\n" + image.tobytes()).hexdigest()
            assert row["pixel_sha256"] == expected
    for index, row in enumerate(decisions):
        assert row["source_state_hash"] == hashlib.sha256(_bytes(states[index])).hexdigest()
        assert row["committed_state_hash"] == hashlib.sha256(_bytes(states[index + 1])).hexdigest()
        assert row["reasons"] == []


def test_raw_input_hash_differs_from_semantic_hash(tmp_path, small_doc):
    raw = json.dumps(small_doc, indent=4).encode() + b"\n\n"
    scene = resolve_scene(small_doc, raw_bytes=raw)
    run = tmp_path / "raw"
    manifest = evidence.render_run(scene, run)
    assert (run / "scene.input.json").read_bytes() == raw
    assert manifest["config"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["config"]["resolved_sha256"] == hashlib.sha256(
        (run / "scene.resolved.json").read_bytes()).hexdigest()
    assert manifest["config"]["raw_sha256"] != manifest["config"]["resolved_sha256"]


def test_manifest_is_published_last_after_closed_complete_status(tmp_path, small_doc, monkeypatch):
    original = evidence.atomic_write
    writes = []

    def observe(path, payload, *args, **kwargs):
        path = Path(path)
        if path.name == "manifest.json":
            assert _json(path.parent / "run_status.json")["state"] == "complete"
            for name in ("states.jsonl", "decisions.jsonl", "frames.jsonl", "contact_sheet.png"):
                assert (path.parent / name).is_file()
                with (path.parent / name).open("rb") as closed_artifact:
                    assert closed_artifact.read(1)
        result = original(path, payload, *args, **kwargs)
        writes.append(path.name)
        return result

    monkeypatch.setattr(evidence, "atomic_write", observe)
    monkeypatch.setattr(canonical, "atomic_write", observe)
    evidence.render_run(resolve_scene(small_doc), tmp_path / "atomic")
    assert writes[-1] == "manifest.json"


def test_existing_output_is_refused_without_touching_user_file(tmp_path, small_doc):
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("owned by caller\n")
    with pytest.raises(evidence.ExportError):
        evidence.render_run(resolve_scene(small_doc), existing)
    assert marker.read_text() == "owned by caller\n"
    assert list(existing.iterdir()) == [marker]


def test_failed_decision_log_never_commits_candidate(tmp_path, small_doc, monkeypatch):
    original = evidence._append_row

    def fail_decision(path, row, *args, **kwargs):
        if Path(path).name == "decisions.jsonl":
            raise OSError("injected decision close failure")
        return original(path, row, *args, **kwargs)

    monkeypatch.setattr(evidence, "_append_row", fail_decision)
    run = tmp_path / "log_failure"
    with pytest.raises(evidence.ExportError):
        evidence.render_run(resolve_scene(small_doc), run)
    assert not (run / "manifest.json").exists()
    status = _json(run / "run_status.json")
    assert status["state"] == "failed" and status["last_committed_tick"] == 0
    assert [row["tick"] for row in _rows(run / "states.jsonl")] == [0]


def test_numeric_rejection_retains_previous_state_and_json_safe_reason(tmp_path, small_doc, monkeypatch):
    captured = []

    def nan_candidate(previous, scene):
        before = previous.positions.copy()
        positions = before.copy()
        positions[0, 0] = np.nan
        captured.append((previous, before))
        return SceneState(previous.tick + 1, positions, previous.velocities.copy())

    monkeypatch.setattr(evidence, "propose_step", nan_candidate)
    run = tmp_path / "rejected"
    with pytest.raises(evidence.NumericalRejection):
        evidence.render_run(resolve_scene(small_doc), run)
    assert not (run / "manifest.json").exists()
    assert _json(run / "run_status.json")["last_committed_tick"] == 0
    states = _rows(run / "states.jsonl")
    assert len(states) == 1 and states[0]["tick"] == 0
    rejected = _rows(run / "decisions.jsonl")
    assert len(rejected) == 1 and rejected[0]["status"] == "REJECT"
    assert "committed_state_hash" not in rejected[0]
    assert any(reason["code"] == "NONFINITE_POSITION" and reason["detail"] == "nan"
               for reason in rejected[0]["reasons"])
    json.loads((run / "decisions.jsonl").read_bytes(),
               parse_constant=lambda value: pytest.fail(f"illegal JSON constant {value}"))
    assert np.array_equal(captured[0][0].positions, captured[0][1])


def test_frame_export_failure_retains_failed_take(tmp_path, small_doc, monkeypatch):
    original = evidence.atomic_write

    def fail_frame(path, data, *args, **kwargs):
        if Path(path).name == "frame_000000.png":
            raise OSError("injected PNG publication failure")
        return original(path, data, *args, **kwargs)

    monkeypatch.setattr(evidence, "atomic_write", fail_frame)
    run = tmp_path / "png_failure"
    with pytest.raises(evidence.ExportError):
        evidence.render_run(resolve_scene(small_doc), run)
    assert not (run / "manifest.json").exists()
    assert _json(run / "run_status.json")["state"] == "failed"


@pytest.mark.parametrize("damage", ["missing", "truncated", "rgb", "extra"])
def test_missing_malformed_wrong_mode_and_extra_png_rejected(completed_run, damage):
    frame = completed_run / "frames" / "frame_000001.png"
    if damage == "missing":
        frame.unlink()
    elif damage == "truncated":
        _rewrite_artifact(completed_run, "frames/frame_000001.png", frame.read_bytes()[:20])
    elif damage == "rgb":
        with Image.open(frame) as image:
            image.convert("RGB").save(frame)
        _rewrite_artifact(completed_run, "frames/frame_000001.png", frame.read_bytes())
    else:
        extra = frame.with_name("frame_000012.png")
        extra.write_bytes(frame.read_bytes())
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("damage", ["duplicate_tick", "gap", "unknown_field", "broken_hash", "metric", "status"])
def test_rewritten_outer_hash_cannot_spoof_trace_or_metric(completed_run, damage):
    if damage in {"duplicate_tick", "gap", "unknown_field"}:
        name = "states.jsonl"
        rows = _rows(completed_run / name)
        if damage == "duplicate_tick":
            rows[4]["tick"] = 3
        elif damage == "gap":
            rows.pop(4)
        else:
            rows[4]["surprise"] = True
    elif damage == "broken_hash":
        name = "decisions.jsonl"
        rows = _rows(completed_run / name)
        rows[4]["source_state_hash"] = "0" * 64
    elif damage == "metric":
        name = "frames.jsonl"
        rows = _rows(completed_run / name)
        rows[4]["metrics"]["occupancy"] = 0.999
    else:
        name = "run_status.json"
        status = _json(completed_run / name)
        status["state"] = "running"
        _rewrite_artifact(completed_run, name, _bytes(status))
        with pytest.raises(evidence.IntegrityError):
            evidence.verify_integrity(completed_run / "manifest.json")
        return
    _rewrite_artifact(completed_run, name, b"".join(_bytes(row) for row in rows))
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("damage", ["unknown_field", "duplicate_key", "escaping_path", "symlink"])
def test_manifest_strict_schema_and_path_policy(completed_run, damage, tmp_path):
    path = completed_run / "manifest.json"
    manifest = _json(path)
    if damage == "unknown_field":
        manifest["unrecognized"] = "reject"
    elif damage == "duplicate_key":
        payload = path.read_bytes()
        path.write_bytes(b'{"creator_review":"accepted",' + payload[1:])
    elif damage == "escaping_path":
        manifest["artifacts"]["../outside.json"] = "0" * 64
    else:
        frame = completed_run / "frames" / "frame_000001.png"
        outside = tmp_path / "outside.png"
        outside.write_bytes(frame.read_bytes())
        frame.unlink()
        frame.symlink_to(outside)
    if damage not in {"duplicate_key", "symlink"}:
        _write_json(path, manifest)
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(path)


def test_missing_final_manifest_cannot_validate_complete_status(completed_run):
    (completed_run / "manifest.json").unlink()
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


def test_contact_sheet_references_are_checked_after_rehash(completed_run):
    relative = "contact_sheet.index.json"
    index = _json(completed_run / relative)
    index["entries"][0]["index"] = 1
    index["entries"][0]["path"] = "frames/frame_000001.png"
    _rewrite_artifact(completed_run, relative, _bytes(index))
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


def test_source_snapshot_bytes_are_checked_independently_of_outer_hash(completed_run):
    relative = "source/files/commander_zorg/motion.py"
    _rewrite_artifact(completed_run, relative,
                      (completed_run / relative).read_bytes() + b"\n# injected source change\n")
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("removed", ["commander_zorg/config.py", "requirements.lock", "scenes/e1.json"])
def test_source_snapshot_cannot_omit_required_executed_content(completed_run, removed):
    index = _json(completed_run / "source/index.json")
    del index[removed]
    (completed_run / "source/files" / removed).unlink()
    manifest = _json(completed_run / "manifest.json")
    del manifest["artifacts"][f"source/files/{removed}"]
    payload = _bytes(index)
    (completed_run / "source/index.json").write_bytes(payload)
    manifest["artifacts"]["source/index.json"] = hashlib.sha256(payload).hexdigest()
    manifest["source"]["digest"] = hashlib.sha256(payload).hexdigest()
    _write_json(completed_run / "manifest.json", manifest)
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("relative", ["states.jsonl", "decisions.jsonl", "frames.jsonl"])
def test_noncanonical_trace_rows_rejected_even_after_artifact_rehash(completed_run, relative):
    rows = _rows(completed_run / relative)
    payload = b"".join((json.dumps(row, sort_keys=True) + "\n").encode() for row in rows)
    _rewrite_artifact(completed_run, relative, payload)
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


def test_flipped_png_cannot_pass_by_rewriting_all_container_hashes_and_metrics(completed_run):
    from commander_zorg.config import load_scene
    from commander_zorg.raster import measure_mask
    scene = load_scene(completed_run / "scene.input.json")
    rows = _rows(completed_run / "frames.jsonl")
    relative = rows[5]["path"]
    with Image.open(completed_run / rows[0]["path"]) as baseline_image:
        baseline = np.asarray(baseline_image, dtype=np.uint8) >= 128
    with Image.open(completed_run / relative) as image:
        changed = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        changed.save(completed_run / relative, compress_level=6, optimize=False)
        pixels = np.asarray(changed, dtype=np.uint8)
    payload = (completed_run / relative).read_bytes()
    rows[5]["file_sha256"] = hashlib.sha256(payload).hexdigest()
    rows[5]["pixel_sha256"] = hashlib.sha256(b"cz-gray8-v1\n64,64\n" + pixels.tobytes()).hexdigest()
    rows[5]["metrics"].update(measure_mask(pixels, scene, baseline))
    _rewrite_artifact(completed_run, relative, payload)
    _rewrite_artifact(completed_run, "frames.jsonl", b"".join(_bytes(row) for row in rows))
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


def test_frozen_trajectory_with_consistent_decision_links_cannot_pass(completed_run):
    states = _rows(completed_run / "states.jsonl")
    for state in states[1:]:
        state["positions"] = states[0]["positions"]
        state["velocities"] = states[0]["velocities"]
    hashes = [hashlib.sha256(_bytes(state)).hexdigest() for state in states]
    decisions = _rows(completed_run / "decisions.jsonl")
    for index, decision in enumerate(decisions):
        decision["source_state_hash"] = hashes[index]
        decision["committed_state_hash"] = hashes[index + 1]
    _rewrite_artifact(completed_run, "states.jsonl", b"".join(_bytes(row) for row in states))
    _rewrite_artifact(completed_run, "decisions.jsonl", b"".join(_bytes(row) for row in decisions))
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("field", ["index", "cell"])
def test_contact_sheet_boolean_cannot_alias_integer_reference(completed_run, field):
    relative = "contact_sheet.index.json"
    index = _json(completed_run / relative)
    assert index["entries"][0][field] == 0
    index["entries"][0][field] = False
    _rewrite_artifact(completed_run, relative, _bytes(index))
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(completed_run / "manifest.json")


@pytest.mark.parametrize("section,key,value", [
    ("timings", "field_s", False), ("timings", "raster_s", -.01),
    ("timings", "peak_rss_kib", True), ("timings", "peak_rss_method", None),
    ("environment", "python", 312), ("environment", "numpy", ""),
    ("warnings", None, [False]),
])
def test_operational_metadata_has_strict_types(completed_run, section, key, value):
    path = completed_run / "manifest.json"
    manifest = _json(path)
    if key is None:
        manifest[section] = value
    else:
        manifest[section][key] = value
    _write_json(path, manifest)
    with pytest.raises(evidence.IntegrityError):
        evidence.verify_integrity(path)
