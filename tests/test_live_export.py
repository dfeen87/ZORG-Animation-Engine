"""Live recordings export full mathematical frames and truthful closed evidence."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

from commander_zorg.canonical import atomic_json, canonical_bytes, read_json, read_jsonl, sha256
from commander_zorg.evidence import IntegrityError, pixel_hash
from commander_zorg.live_motion import LiveRuntime
from commander_zorg import live_export
from commander_zorg.live_export import render_session, verify_export
from commander_zorg.session import Recorder


@pytest.fixture
def config():
    config = read_json(Path(__file__).parents[1] / "scenes/live_lab.json")
    config["scene"]["raster"].update(width=64, height=64)
    config["max_ticks"] = 120
    return config


def record(root, config, ticks=8):
    runtime = LiveRuntime(config)
    recorder = Recorder(root, config)
    recorder.record_event(runtime.accept("left"))
    for _ in range(ticks):
        runtime.step()
    return recorder.finish(runtime)


def reindex(root):
    """Update outer hashes so tests reach the intended independent check."""
    manifest = read_json(root / "manifest.json")
    for name in manifest["artifacts"]:
        manifest["artifacts"][name] = sha256((root / name).read_bytes())
    atomic_json(root / "manifest.json", manifest)


@pytest.mark.parametrize("ticks", [0, 1, 2, 3, 8, 9])
def test_timeline_includes_final_audit_excludes_terminal_frame(config, tmp_path, ticks):
    # Zero-duration recordings can legitimately have an event at initial tick.
    session = record(tmp_path / "take", config, ticks)
    out = tmp_path / "export"
    result = render_session(session, out, mp4=False)
    count = (ticks + 1) // 2
    assert result["frames"] == count
    assert result["states"] == ticks + 1
    assert result["duration_seconds"] == ticks / 60
    assert result["timeline"]["media_duration_seconds"] == count / 30
    frames = read_jsonl(out / "frames.jsonl")
    assert [row["tick"] for row in frames] == list(range(0, ticks, 2))
    assert [row["path"] for row in frames] == [f"frames/frame_{i:06d}.png" for i in range(count)]
    assert [row["tick"] for row in read_jsonl(out / "states.jsonl")] == list(range(ticks + 1))
    assert (out / "record/events.jsonl").read_bytes() == (session.parent / "events.jsonl").read_bytes()
    assert "fetch(" not in (out / "player.html").read_text()
    assert verify_export(out / "manifest.json")["passed"]


def test_equivalent_seeded_exports_have_identical_states_and_pixels(config, tmp_path):
    session = record(tmp_path / "take", config, 20)
    a, b = tmp_path / "a", tmp_path / "b"
    render_session(session, a, mp4=False)
    render_session(session, b, mp4=False)
    assert (a / "states.jsonl").read_bytes() == (b / "states.jsonl").read_bytes()
    assert (a / "frames.jsonl").read_bytes() == (b / "frames.jsonl").read_bytes()
    assert all((a / frame).read_bytes() == (b / frame).read_bytes()
               for frame in [r["path"] for r in read_jsonl(a / "frames.jsonl")])


def test_export_refuses_existing_directory_and_symlink(config, tmp_path):
    session = record(tmp_path / "take", config)
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "keep"
    marker.write_text("preserve user data")
    with pytest.raises(FileExistsError):
        render_session(session, existing, mp4=False)
    assert marker.read_text() == "preserve user data"
    dangling = tmp_path / "dangling"
    dangling.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        render_session(session, dangling, mp4=False)


@pytest.mark.parametrize("error", [KeyboardInterrupt(), OSError("simulated disk failure")])
def test_interrupted_render_retains_truthful_partial_evidence(config, tmp_path, monkeypatch, error):
    session = record(tmp_path / "take", config, 10)
    real = live_export.evaluate_samples
    calls = 0

    def interrupted(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise error
        return real(*args)

    monkeypatch.setattr(live_export, "evaluate_samples", interrupted)
    out = tmp_path / "partial"
    with pytest.raises(type(error)):
        render_session(session, out, mp4=False)
    status = read_json(out / "export_status.json")
    assert status["state"] == "failed"
    assert status["frames"] == 1
    assert status["last_tick"] == 1
    assert status["error"]["interrupted"] == isinstance(error, KeyboardInterrupt)
    assert (out / "frames/frame_000000.png").is_file()
    assert not (out / "manifest.json").exists()


def test_terminal_audit_replay_failure_is_not_hidden_when_no_frame(config, tmp_path):
    session = record(tmp_path / "take", config, 0)
    doc = read_json(session)
    doc["trajectory_sha256"] = "0" * 64
    doc["session_sha256"] = sha256(canonical_bytes({k: v for k, v in doc.items() if k != "session_sha256"}))
    atomic_json(session, doc)
    out = tmp_path / "failed"
    with pytest.raises(ValueError, match="trajectory replay"):
        render_session(session, out, mp4=False)
    assert read_json(out / "export_status.json")["state"] == "failed"
    assert not (out / "manifest.json").exists()


def test_missing_ffmpeg_preserves_portable_player(config, tmp_path, monkeypatch):
    session = record(tmp_path / "take", config)
    monkeypatch.setattr(live_export.shutil, "which", lambda _: None)
    out = tmp_path / "fallback"
    result = render_session(session, out)
    assert result["media"]["mp4"]["status"] == "unavailable"
    assert result["media"]["fallback"]["path"] == "player.html"
    assert not (out / "animation.mp4").exists()
    assert verify_export(out / "manifest.json")["passed"]


def test_encoder_failure_is_reported_without_losing_frames(config, tmp_path, monkeypatch):
    session = record(tmp_path / "take", config)
    monkeypatch.setattr(live_export.shutil, "which", lambda _: "/fake/ffmpeg")

    def failing(command, **kwargs):
        Path(command[-1]).write_bytes(b"incomplete container")
        return subprocess.CompletedProcess(command, 7, b"", b"encoder failed")

    monkeypatch.setattr(live_export.subprocess, "run", failing)
    out = tmp_path / "fallback"
    result = render_session(session, out)
    assert result["status"] == "complete"
    assert result["media"]["mp4"]["status"] == "failed"
    assert result["media"]["mp4"]["exit_code"] == 7
    assert (out / "encoder.log").read_text() == "encoder failed"
    assert not (out / "animation.mp4").exists()
    assert not (out / "animation.partial.mp4").exists()
    assert len(list((out / "frames").glob("*.png"))) == 4
    assert verify_export(out / "manifest.json")["mp4"] == "failed"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="optional local FFmpeg unavailable")
def test_real_mp4_has_compatible_codec_and_ordered_frame_count(config, tmp_path):
    session = record(tmp_path / "take", config, 12)
    out = tmp_path / "video"
    result = render_session(session, out)
    assert result["media"]["mp4"]["status"] == "complete"
    assert verify_export(out / "manifest.json")["mp4"] == "complete"
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
                                "-show_entries", "stream=codec_name,pix_fmt,nb_read_frames,r_frame_rate",
                                "-of", "json", str(out / "animation.mp4")],
                               check=True, capture_output=True)
        stream = json.loads(probe.stdout)["streams"][0]
        assert stream == {"codec_name": "h264", "pix_fmt": "yuv420p",
                          "r_frame_rate": "30/1", "nb_read_frames": "6"}


def test_cli_fresh_process_replay_and_export_reproduce_all_states_and_frames(config, tmp_path):
    session = record(tmp_path / "take", config, 13)

    def cli(*args):
        process = subprocess.run([sys.executable, "-m", "commander_zorg.cli", *map(str, args)],
                                 capture_output=True, text=True, check=False)
        assert process.returncode == 0, process.stderr
        return json.loads(process.stdout)

    assert cli("verify-session", session)["passed"]
    a, b = tmp_path / "fresh_a", tmp_path / "fresh_b"
    for out in (a, b):
        report = cli("render-session", session, "--out", out, "--no-mp4")
        assert report["frames"] == 7
        assert cli("verify-live-export", out / "manifest.json")["passed"]
    assert (a / "states.jsonl").read_bytes() == (b / "states.jsonl").read_bytes()
    assert (a / "frames.jsonl").read_bytes() == (b / "frames.jsonl").read_bytes()
    for row in read_jsonl(a / "frames.jsonl"):
        assert (a / row["path"]).read_bytes() == (b / row["path"]).read_bytes()


def test_default_scene_exports_full_resolution_supersampled_pixels(tmp_path):
    config = read_json(Path(__file__).parents[1] / "scenes/live_lab.json")
    session = record(tmp_path / "take", config, 2)
    out = tmp_path / "fullres"
    result = render_session(session, out, mp4=False)
    assert result["raster"] == {"width": 384, "height": 384, "samples_per_axis": 2, "invert": False}
    with Image.open(out / "frames/frame_000000.png") as frame:
        assert frame.size == (384, 384)
        assert frame.mode == "L"
    assert verify_export(out / "manifest.json")["passed"]


@pytest.mark.parametrize("target", ["frames/frame_000000.png", "record/events.jsonl",
                                    "source/files/commander_zorg/field.py", "states.jsonl"])
def test_artifact_tampering_is_rejected(config, tmp_path, target):
    session = record(tmp_path / "take", config)
    out = tmp_path / "export"
    render_session(session, out, mp4=False)
    with (out / target).open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        verify_export(out / "manifest.json")


@pytest.mark.parametrize("kind", ["frame_order", "state_order", "pixel_hash", "metrics", "trajectory", "source"])
def test_independent_integrity_checks_survive_outer_rehash(config, tmp_path, kind):
    session = record(tmp_path / "take", config)
    out = tmp_path / "export"
    render_session(session, out, mp4=False)
    if kind in ("frame_order", "pixel_hash", "metrics"):
        rows = read_jsonl(out / "frames.jsonl")
        if kind == "frame_order":
            rows[1]["tick"] = 0
        elif kind == "pixel_hash":
            rows[0]["pixel_sha256"] = "0" * 64
        else:
            rows[0]["metrics"]["occupancy"] = 0
        (out / "frames.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
    elif kind == "state_order":
        rows = read_jsonl(out / "states.jsonl")
        rows[1]["tick"] = 0
        (out / "states.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
    elif kind == "source":
        (out / "source/files/commander_zorg/field.py").write_text("changed source")
    else:
        rows = read_jsonl(out / "states.jsonl")
        rows[1]["positions"][0][0] += .001
        (out / "states.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
    reindex(out)
    with pytest.raises(IntegrityError):
        verify_export(out / "manifest.json")


def test_rehashed_png_must_match_mathematical_state(config, tmp_path):
    session = record(tmp_path / "take", config)
    out = tmp_path / "export"
    render_session(session, out, mp4=False)
    rows = read_jsonl(out / "frames.jsonl")
    frame = out / rows[0]["path"]
    with Image.open(frame) as image:
        pixels = np.array(image)
    pixels[0, 0] ^= 255
    Image.fromarray(pixels).save(frame)
    rows[0]["file_sha256"] = sha256(frame.read_bytes())
    rows[0]["pixel_sha256"] = pixel_hash(pixels)
    (out / "frames.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
    reindex(out)
    with pytest.raises(IntegrityError, match="mathematical state"):
        verify_export(out / "manifest.json")


@pytest.mark.parametrize("kind", ["symlink", "unindexed", "escaping_path"])
def test_unsafe_or_unindexed_artifacts_are_rejected(config, tmp_path, kind):
    session = record(tmp_path / "take", config)
    out = tmp_path / "export"
    render_session(session, out, mp4=False)
    if kind == "symlink":
        target = out / "frames/frame_000000.png"
        outside = tmp_path / "outside.png"
        target.rename(outside)
        target.symlink_to(outside)
    elif kind == "unindexed":
        (out / "extra.txt").write_text("unindexed")
    else:
        manifest = read_json(out / "manifest.json")
        manifest["artifacts"]["../escape"] = "0" * 64
        atomic_json(out / "manifest.json", manifest)
    with pytest.raises(IntegrityError):
        verify_export(out / "manifest.json")
