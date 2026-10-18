"""Offline rendering and closed evidence for the versioned live extension.

Preview pixels never enter this path. Every physics tick is replayed and audited;
only ticks 0, 2, ... strictly before the terminal audit tick become video frames.
FFmpeg is an optional local encoder, not a dependency of the numerical engine.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import time

import numpy as np
from PIL import Image

from .canonical import atomic_json, atomic_write, canonical_bytes, read_json, read_jsonl, sha256
from .evidence import IntegrityError, pixel_hash
from .field import evaluate_samples
from .guard import validate_state
from .live_motion import LiveRuntime
from .raster import encode_gray_png, geometry_mask, measure_mask, rasterize
from .session import load_session, replay_states
from .state import owned_state, state_mapping


def _path(root, relative):
    if type(relative) is not str or not relative or "\\" in relative:
        raise IntegrityError("artifact path must be a relative POSIX path")
    parts = PurePosixPath(relative)
    if (parts.is_absolute() or parts.as_posix() != relative
            or any(p in (".", "..") for p in parts.parts)):
        raise IntegrityError("escaping artifact path")
    result = root.joinpath(*parts.parts)
    cursor = result
    while cursor != root:
        if cursor.is_symlink():
            raise IntegrityError("symlink artifact refused")
        cursor = cursor.parent
    if not result.resolve().is_relative_to(root.resolve()):
        raise IntegrityError("escaping artifact path")
    return result


def _require(condition, message):
    if not condition:
        raise IntegrityError(message)


def _append(path, row):
    with path.open("ab") as stream:
        stream.write(canonical_bytes(row))


def _player(count, fps):
    """Self-contained file:// player: no server, CDN, fetch, or build required."""
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width'>"
            "<title>ZORG Live Morph Lab — local playback</title>"
            "<style>body{background:#222;color:#eee;font:16px sans-serif;text-align:center}"
            "img{display:block;max-width:90vw;margin:1em auto;image-rendering:auto}"
            "input{width:70vw;max-width:500px}</style>"
            "<h1>ZORG Live Morph Lab</h1><p>Local frame playback. Creator review pending.</p>"
            "<img id='frame' alt='Recorded Gaussian silhouette'>"
            "<button id='toggle'>Pause</button> <span id='label'></span><p>"
            "<input id='scrub' type='range' min='0' value='0' aria-label='Frame'></p>"
            "<p>Space: play/pause · Arrow keys: step</p><script>"
            f"const count={count},fps={fps};"
            "let i=0,playing=count>0;const im=document.getElementById('frame'),"
            "label=document.getElementById('label'),slider=document.getElementById('scrub'),"
            "button=document.getElementById('toggle');slider.max=Math.max(0,count-1);"
            "function show(){button.textContent=playing?'Pause':'Play';slider.value=i;"
            "if(!count){im.hidden=true;label.textContent='Empty recording: no video frames.';return;}"
            "im.src='frames/frame_'+String(i).padStart(6,'0')+'.png';"
            "label.textContent='Frame '+(i+1)+' / '+count+' · '+(i/fps).toFixed(3)+' s';}"
            "function toggle(){if(count){playing=!playing;show();}}button.onclick=toggle;"
            "slider.oninput=()=>{playing=false;i=Number(slider.value);show();};"
            "document.onkeydown=e=>{if(e.code==='Space'){toggle();e.preventDefault();}"
            "if(count&&(e.code==='ArrowRight'||e.code==='ArrowLeft')){playing=false;"
            "i=(i+(e.code==='ArrowRight'?1:count-1))%count;show();e.preventDefault();}};"
            "show();setInterval(()=>{if(playing){i=(i+1)%count;show();}},1000/fps);"
            "</script></html>\n").encode("utf-8")


def _encode_mp4(root, count, fps, enabled):
    if not enabled:
        return {"status": "disabled", "reason": "MP4 encoding was disabled"}
    if not count:
        return {"status": "no_frames", "reason": "Recording has zero duration"}
    encoder = shutil.which("ffmpeg")
    if encoder is None:
        return {"status": "unavailable", "reason": "FFmpeg is not installed; open player.html"}
    partial = root / "animation.partial.mp4"
    command = [encoder, "-nostdin", "-v", "error", "-n", "-framerate", str(fps),
               "-start_number", "0", "-i", str(root / "frames/frame_%06d.png"),
               "-frames:v", str(count), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(partial)]
    try:
        result = subprocess.run(command, capture_output=True, check=False)
    except OSError as error:
        partial.unlink(missing_ok=True)
        return {"status": "failed", "reason": f"FFmpeg could not start: {error}"}
    log = result.stderr[-16000:]
    atomic_write(root / "encoder.log", log)
    if result.returncode or not partial.is_file() or not partial.stat().st_size:
        partial.unlink(missing_ok=True)
        return {"status": "failed", "reason": f"FFmpeg exited {result.returncode}; see encoder.log",
                "log": "encoder.log", "exit_code": result.returncode}
    partial.rename(root / "animation.mp4")
    return {"status": "complete", "path": "animation.mp4", "codec": "h264",
            "pixel_format": "yuv420p", "fps": fps, "frames": count, "log": "encoder.log"}


def _artifacts(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes())
            for p in sorted(root.rglob("*")) if p.is_file() and p.name != "manifest.json"}


def render_session(path, out, mp4=True):
    """Replay into a new directory and publish a manifest only after full audit.

    Encoder failures are recorded in ``media.mp4`` while PNG and HTML export
    succeeds. Physics, replay, filesystem and interruption failures leave a
    failed status and their partial evidence, then propagate to the caller.
    """
    path, root = Path(path), Path(out)
    if path.is_symlink():
        raise ValueError("symlink session refused")
    doc, _ = load_session(path)
    # mkdir itself is the exclusive ownership check, including dangling symlinks.
    root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    status = {"schema_version": "cz-live-export-status-0.1", "state": "running",
              "last_tick": None, "frames": 0, "error": None}
    try:
        atomic_json(root / "export_status.json", status)
        (root / "record").mkdir()
        atomic_write(root / "record/session.json", path.read_bytes())
        for name in ("config.json", "events.jsonl"):
            atomic_write(root / "record" / name, (path.parent / name).read_bytes())
        project = Path(__file__).resolve().parent.parent
        for name, digest in doc["source"].items():
            source = _path(project, name).read_bytes()
            _require(sha256(source) == digest, "source changed during export")
            destination = _path(root, "source/files/" + name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(destination, source)
        (root / "frames").mkdir()
        for name in ("states.jsonl", "frames.jsonl"):
            (root / name).touch(exist_ok=False)
        scene = LiveRuntime(doc["config"]).scene
        baseline = None
        state_count = 0
        # Exhaustion is essential: replay_states checks its audit hash after yield.
        for state in replay_states(root / "record/session.json"):
            _append(root / "states.jsonl", state_mapping(state))
            state_count += 1
            if state.tick < doc["final_tick"] and state.tick % 2 == 0:
                samples = evaluate_samples(state, scene)
                pixels = rasterize(samples, scene)
                if baseline is None:
                    baseline = geometry_mask(pixels, scene)
                metrics = measure_mask(pixels, scene, baseline)
                metrics.update(field_min=float(samples.min()), field_max=float(samples.max()))
                encoded = encode_gray_png(pixels)
                relative = f"frames/frame_{status['frames']:06d}.png"
                atomic_write(root / relative, encoded)
                _append(root / "frames.jsonl", {
                    "index": status["frames"], "tick": state.tick, "path": relative,
                    "mode": "L", "width": scene.width, "height": scene.height,
                    "file_sha256": sha256(encoded), "pixel_sha256": pixel_hash(pixels),
                    "metrics": metrics})
                status["frames"] += 1
            status["last_tick"] = state.tick
        expected = (doc["final_tick"] + 1) // 2
        _require(status["frames"] == expected and state_count == doc["final_tick"] + 1,
                 "export timeline count mismatch")
        atomic_write(root / "player.html", _player(expected, 30))
        media = {"mp4": _encode_mp4(root, expected, 30, mp4),
                 "fallback": {"status": "complete", "path": "player.html", "kind": "html-sequence"}}
        # Retain source binding across the full render, including long exports.
        load_session(root / "record/session.json")
        status["state"] = "complete"
        atomic_json(root / "export_status.json", status)
        manifest = {
            "schema_version": "cz-live-export-0.1", "status": "complete",
            "session": {"path": "record/session.json", "session_sha256": doc["session_sha256"],
                        "file_sha256": sha256((root / "record/session.json").read_bytes())},
            "source": {"files": doc["source"], "digest": sha256(canonical_bytes(doc["source"])),
                       "root": "source/files"},
            "environment": doc["environment"],
            "timeline": {"sim_hz": 60, "fps_out": 30, "frame_step_ticks": 2,
                         "first_frame_tick": 0 if expected else None,
                         "last_frame_tick": 2 * (expected - 1) if expected else None,
                         "terminal_audit_rendered": False, "media_duration_seconds": expected / 30},
            "frames": expected, "states": state_count, "final_tick": doc["final_tick"],
            "duration_seconds": doc["duration_seconds"],
            "raster": {"width": scene.width, "height": scene.height,
                       "samples_per_axis": scene.samples_per_axis, "invert": scene.invert},
            "trajectory_sha256": doc["trajectory_sha256"],
            "final_state_sha256": doc["final_state_sha256"],
            "media": media, "verification": {"numerical_replay": "passed", "creator_review": "pending"},
            "elapsed_seconds": time.perf_counter() - started, "artifacts": _artifacts(root)}
        atomic_json(root / "manifest.json", manifest)
        return manifest
    except BaseException as error:
        status.update(state="failed", error={"type": type(error).__name__, "message": str(error),
                                           "interrupted": isinstance(error, KeyboardInterrupt)})
        atomic_json(root / "export_status.json", status)
        raise


def verify_export(manifest_path):
    """Check closed artifacts, source/session binding, every state and frame.

    This is integrity validation of saved evidence. ``render_session`` separately
    performs exact numerical replay against the current source and environment.
    """
    path = Path(manifest_path)
    try:
        _require(path.name == "manifest.json" and not path.is_symlink(), "expected manifest.json")
        root = path.parent
        manifest = read_json(path)
        _require(path.read_bytes() == canonical_bytes(manifest), "noncanonical manifest")
        expected_keys = {"schema_version", "status", "session", "source", "environment", "timeline",
                         "frames", "states", "final_tick", "duration_seconds", "raster",
                         "trajectory_sha256", "final_state_sha256", "media", "verification",
                         "elapsed_seconds", "artifacts"}
        _require(type(manifest) is dict and set(manifest) == expected_keys, "manifest fields differ")
        _require(manifest["schema_version"] == "cz-live-export-0.1" and manifest["status"] == "complete",
                 "incomplete or unsupported live export")
        artifacts = manifest["artifacts"]
        _require(type(artifacts) is dict and bool(artifacts), "empty artifact index")
        _require(not any(p.is_symlink() for p in root.rglob("*")), "symlink artifact refused")
        for name, digest in artifacts.items():
            artifact = _path(root, name)
            _require(artifact.is_file() and sha256(artifact.read_bytes()) == digest,
                     f"{name}: artifact hash mismatch")
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != path}
        _require(actual == set(artifacts), "unindexed or missing artifacts")
        binding = manifest["session"]
        _require(type(binding) is dict and set(binding) == {"path", "session_sha256", "file_sha256"}
                 and binding["path"] == "record/session.json", "session binding differs")
        session_path = _path(root, binding["path"])
        doc, _ = load_session(session_path, check_environment=False)
        _require(binding["session_sha256"] == doc["session_sha256"]
                 and binding["file_sha256"] == sha256(session_path.read_bytes()), "session digest mismatch")
        _require(manifest["source"] == {"files": doc["source"],
                 "digest": sha256(canonical_bytes(doc["source"])), "root": "source/files"},
                 "source/session binding mismatch")
        for name, digest in doc["source"].items():
            snapshot = _path(root, "source/files/" + name)
            _require(sha256(snapshot.read_bytes()) == digest, "source snapshot mismatch")
        _require(manifest["environment"] == doc["environment"], "environment/session binding mismatch")
        final_tick = doc["final_tick"]
        count = (final_tick + 1) // 2
        for key, value in (("frames", count), ("states", final_tick + 1), ("final_tick", final_tick)):
            _require(type(manifest[key]) is int and manifest[key] == value, f"wrong {key}")
        _require(manifest["duration_seconds"] == doc["duration_seconds"], "duration mismatch")
        expected_timeline = {"sim_hz": 60, "fps_out": 30, "frame_step_ticks": 2,
                             "first_frame_tick": 0 if count else None,
                             "last_frame_tick": 2 * (count - 1) if count else None,
                             "terminal_audit_rendered": False, "media_duration_seconds": count / 30}
        _require(canonical_bytes(manifest["timeline"]) == canonical_bytes(expected_timeline), "timeline mismatch")
        scene = LiveRuntime(doc["config"]).scene
        _require(manifest["raster"] == {"width": scene.width, "height": scene.height,
                 "samples_per_axis": scene.samples_per_axis, "invert": scene.invert}, "raster mismatch")
        states = read_jsonl(_path(root, "states.jsonl"))
        _require((root / "states.jsonl").read_bytes() == b"".join(canonical_bytes(row) for row in states),
                 "noncanonical state trace")
        _require(len(states) == final_tick + 1, "state trace count mismatch")
        trace = hashlib.sha256()
        owned = []
        for tick, row in enumerate(states):
            _require(type(row) is dict and set(row) == {"tick", "positions", "velocities"}
                     and type(row["tick"]) is int and row["tick"] == tick, "state tick chronology mismatch")
            state = owned_state(tick, row["positions"], row["velocities"])
            _require(not validate_state(state, scene), "invalid saved numerical state")
            _require(canonical_bytes(state_mapping(state)) == canonical_bytes(row), "state representation mismatch")
            trace.update(canonical_bytes(row))
            owned.append(state)
        _require(trace.hexdigest() == doc["trajectory_sha256"] == manifest["trajectory_sha256"],
                 "state trajectory/session binding mismatch")
        _require(sha256(canonical_bytes(states[-1])) == doc["final_state_sha256"]
                 == manifest["final_state_sha256"], "final state/session binding mismatch")
        frames = read_jsonl(_path(root, "frames.jsonl"))
        _require((root / "frames.jsonl").read_bytes() == b"".join(canonical_bytes(row) for row in frames),
                 "noncanonical frame log")
        _require(len(frames) == count, "frame count mismatch")
        frame_keys = {"index", "tick", "path", "mode", "width", "height", "file_sha256",
                      "pixel_sha256", "metrics"}
        baseline = None
        for index, row in enumerate(frames):
            relative = f"frames/frame_{index:06d}.png"
            _require(type(row) is dict and set(row) == frame_keys, "frame fields differ")
            _require(type(row["index"]) is int and row["index"] == index
                     and type(row["tick"]) is int and row["tick"] == 2 * index
                     and row["path"] == relative, "frame chronology mismatch")
            frame_path = _path(root, relative)
            _require(sha256(frame_path.read_bytes()) == row["file_sha256"], "frame file hash mismatch")
            with Image.open(frame_path) as image:
                image.load()
                _require(image.format == "PNG" and image.mode == row["mode"] == "L"
                         and image.size == (scene.width, scene.height)
                         and row["width"] == scene.width and row["height"] == scene.height,
                         "frame mode/dimensions mismatch")
                pixels = np.array(image)
            _require(pixel_hash(pixels) == row["pixel_sha256"], "decoded frame pixel hash mismatch")
            samples = evaluate_samples(owned[2 * index], scene)
            expected = rasterize(samples, scene)
            _require(np.array_equal(pixels, expected), "frame differs from saved mathematical state")
            if baseline is None:
                baseline = geometry_mask(pixels, scene)
            metrics = measure_mask(pixels, scene, baseline)
            metrics.update(field_min=float(samples.min()), field_max=float(samples.max()))
            _require(canonical_bytes(metrics) == canonical_bytes(row["metrics"]), "frame metrics mismatch")
        _require(_path(root, "player.html").read_bytes() == _player(count, 30), "local player mismatch")
        media = manifest["media"]
        _require(type(media) is dict and set(media) == {"mp4", "fallback"}, "media fields differ")
        _require(media["fallback"] == {"status": "complete", "path": "player.html", "kind": "html-sequence"},
                 "fallback player unavailable")
        mp4 = media["mp4"]
        _require(type(mp4) is dict and mp4.get("status") in
                 {"complete", "failed", "disabled", "unavailable", "no_frames"}, "invalid MP4 status")
        if mp4["status"] == "complete":
            _require(mp4 == {"status": "complete", "path": "animation.mp4", "codec": "h264",
                     "pixel_format": "yuv420p", "fps": 30, "frames": count, "log": "encoder.log"}
                     and count > 0, "MP4 metadata mismatch")
            _require(b"ftyp" in _path(root, "animation.mp4").read_bytes()[:64], "invalid MP4 container header")
        else:
            _require(not (root / "animation.mp4").exists(), "unreported MP4 artifact")
        status = read_json(_path(root, "export_status.json"))
        _require(status == {"schema_version": "cz-live-export-status-0.1", "state": "complete",
                 "last_tick": final_tick, "frames": count, "error": None}, "incomplete export status")
        _require(manifest["verification"] == {"numerical_replay": "passed", "creator_review": "pending"},
                 "verification policy mismatch")
        return {"schema_version": "cz-live-export-integrity-0.1", "passed": True,
                "frames": count, "states": len(states), "final_tick": final_tick,
                "trajectory_sha256": trace.hexdigest(), "mp4": mp4["status"]}
    except IntegrityError:
        raise
    except Exception as error:
        raise IntegrityError(f"invalid live export: {error}") from error
