"""Closed-artifact run publication, integrity validation and fresh-process replay.

Hashes establish the relationship to the recorded inputs and source snapshot.
Independent numerical tests and experiment profiles establish separate claims.
"""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path, PurePosixPath
import platform
import resource
import subprocess
import sys
import time
import warnings
import zlib

import numpy as np
import PIL
from PIL import Image, ImageDraw, features

from . import __version__
from .canonical import (atomic_json, atomic_write, canonical_bytes, read_json,
                        read_jsonl, sha256)
from .config import load_scene, resolved_mapping
from .field import evaluate_samples
from .guard import check_transition, validate_state
from .motion import propose_step
from .raster import encode_gray_png, geometry_mask, measure_mask, rasterize
from .state import SceneState, initial_state, owned_state, state_mapping


class ExportError(RuntimeError):
    exit_code = 4


class IntegrityError(ExportError):
    pass


class NumericalRejection(RuntimeError):
    exit_code = 3


class ReplayError(RuntimeError):
    exit_code = 5


POLICIES = {"numeric": "semi-implicit-explicit-damping-v1",
            "field": "gaussian-separable-v1", "cue": "quartic-pulse-v1",
            "raster": "uniform-grid-gray8-v1", "json": "cz-json-python-v1"}
MANIFEST_KEYS = {"schema_version", "engine_version", "scene_id", "config",
                 "element_order", "policies", "timeline", "expected", "counts",
                 "artifacts", "source", "environment", "verification", "timings",
                 "warnings", "creator_review", "contact_frames"}
FRAME_KEYS = {"index", "tick", "path", "mode", "width", "height", "file_sha256",
              "pixel_sha256", "metrics"}
METRIC_KEYS = {"occupancy", "centroid", "bbox", "clipping", "empty", "iou",
               "aligned_iou", "centroid_distance", "field_min", "field_max"}
CONTACT_KEYS = {"schema_version", "columns", "cell_width", "cell_height", "entries"}
STATUS_KEYS = {"schema_version", "scene_id", "state", "last_committed_tick", "error_code"}
ENGINE_FILES = {f"commander_zorg/{name}.py" for name in
                ("__init__", "canonical", "cli", "config", "cues", "evidence", "experiments",
                 "field", "guard", "motion", "raster", "state")}
REQUIRED_SOURCE = ENGINE_FILES | {"requirements.lock", "pyproject.toml", "scenes/e1.json",
                                "scenes/control.json"} | {
    f"scenes/e0/{name}.json" for name in ("e0_01_seed", "e0_02_wide", "e0_03_tall",
                                        "e0_04_asymmetric", "e0_05_compact", "e0_06_forked")}


def _require(condition, message):
    if not condition:
        raise IntegrityError(message)


def _keys(value, expected, path):
    _require(type(value) is dict and set(value) == set(expected),
             f"{path}: wrong object fields")


def _integer(value, expected, path):
    _require(type(value) is int and value == expected, f"{path}: wrong integer")


def pixel_hash(pixels):
    height, width = pixels.shape
    return sha256(b"cz-gray8-v1\n" + f"{width},{height}\n".encode("ascii")
                  + pixels.tobytes(order="C"))


def _state_hash(state):
    return sha256(canonical_bytes(state_mapping(state)))


def _append_row(path, row):
    # Close succeeds before the caller may commit a candidate. This is not fsync.
    with Path(path).open("ab") as file:
        file.write(canonical_bytes(row))


def _path(root, relative):
    _require(type(relative) is str and bool(relative) and "\\" not in relative,
             "artifact path must be a nonempty relative POSIX path")
    path = PurePosixPath(relative)
    _require(not path.is_absolute() and path.as_posix() == relative
             and all(p not in (".", "..") for p in path.parts), "escaping artifact path")
    result = root.joinpath(*path.parts)
    cursor = result
    while cursor != root:
        _require(not cursor.is_symlink(), "symlink artifact refused")
        cursor = cursor.parent
    _require(result.resolve().is_relative_to(root.resolve()), "escaping artifact path")
    return result


def environment_info():
    build = io.StringIO()
    with contextlib.redirect_stdout(build), warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Install `pyyaml` for better output", category=UserWarning)
        np.show_config()
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "numpy": np.__version__, "pillow": PIL.__version__,
            "zlib": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
            "pillow_zlib": features.version_codec("zlib"),
            "system": platform.system(), "release": platform.release(),
            "machine": platform.machine(), "byteorder": sys.byteorder,
            "numpy_build": build.getvalue()}


def _source_files():
    package = Path(__file__).resolve().parent
    project = package.parent
    result = {f"commander_zorg/{p.name}": p.read_bytes()
              for p in sorted(package.glob("*.py"))}
    for name in ("requirements.lock", "pyproject.toml"):
        if (project / name).is_file():
            result[name] = (project / name).read_bytes()
    for p in sorted((project / "scenes").rglob("*.json")):
        result[p.relative_to(project).as_posix()] = p.read_bytes()
    for directory in ("tests", "scripts"):
        for p in sorted((project / directory).rglob("*.py")):
            result[p.relative_to(project).as_posix()] = p.read_bytes()
    return result


def source_digest():
    return sha256(canonical_bytes({p: sha256(data) for p, data in _source_files().items()}))


def _snapshot(root):
    files = _source_files()
    index = {path: sha256(data) for path, data in files.items()}
    for path, data in files.items():
        destination = root / "source/files" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(destination, data)
    atomic_json(root / "source/index.json", index)
    return {"digest": sha256(canonical_bytes(index)), "index_path": "source/index.json"}


def _contact_indices(rows):
    fixed = (0, 23, 38, 50, 60, 90, 120, 165, 179)
    indices = {i for i in fixed if i < len(rows)}
    if rows:
        indices.add(len(rows) - 1)
        eligible = [r for r in rows if r["metrics"]["aligned_iou"] is not None]
        if eligible:
            indices.add(min(eligible, key=lambda r: r["metrics"]["aligned_iou"])["index"])
    return sorted(indices)


def _contact_index(rows, scene):
    return {"schema_version": "cz-contact-index-0.3", "columns": 3,
            "cell_width": 192, "cell_height": 220,
            "entries": [{"index": i, "path": rows[i]["path"],
                         "cell": n, "label": f"frame {i}  t={i / scene.fps_out:.3f}s"}
                        for n, i in enumerate(_contact_indices(rows))]}


def _contact_png(root, index):
    columns, cell_w, cell_h = index["columns"], index["cell_width"], index["cell_height"]
    sheet = Image.new("L", (columns * cell_w,
                           ((len(index["entries"]) + columns - 1) // columns) * cell_h), 32)
    draw = ImageDraw.Draw(sheet)
    for item in index["entries"]:
        x = (item["cell"] % columns) * cell_w
        y = (item["cell"] // columns) * cell_h
        with Image.open(_path(root, item["path"])) as image:
            image.load()
            thumb = image.copy()
            thumb.thumbnail((cell_w, cell_h - 28), Image.Resampling.NEAREST)
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y))
        draw.text((x + 4, y + cell_h - 24), item["label"], fill=255)
    return encode_gray_png(np.asarray(sheet))


def _player(scene):
    # Local artifact viewer only; never served or deployed by the engine.
    return ("<!doctype html><meta charset='utf-8'><title>ZORG local frame review</title>"
            "<p>Space: pause/play. Arrow keys: step. Creator review is pending.</p>"
            "<img id='frame' alt='ZORG frame'><p id='label'></p><script>"
            f"const count={scene.frame_count},fps={scene.fps_out};"
            "let i=0,play=true;const im=document.getElementById('frame');"
            "function show(){im.src='frames/frame_'+String(i).padStart(6,'0')+'.png';"
            "document.getElementById('label').textContent='frame '+i+' / '+count;}"
            "document.onkeydown=e=>{if(e.code==='Space'){play=!play;e.preventDefault();}"
            "if(e.code==='ArrowRight'){play=false;i=(i+1)%count;show();}"
            "if(e.code==='ArrowLeft'){play=false;i=(i+count-1)%count;show();}};"
            "show();setInterval(()=>{if(play){i=(i+1)%count;show();}},1000/fps);</script>\n").encode()


def render_run(scene, new_output_directory):
    """Render a fully validated scene into a new directory; publish manifest last."""
    # Revalidate raw and semantic configuration before mkdir, even for API callers.
    from .config import resolve_scene
    checked = resolve_scene(resolved_mapping(scene))
    from .canonical import strict_json
    raw_scene = resolve_scene(strict_json(scene.raw_bytes))
    if canonical_bytes(resolved_mapping(checked)) != canonical_bytes(resolved_mapping(raw_scene)):
        raise ExportError("raw and resolved scene disagree")
    root = Path(new_output_directory)
    if root.exists() or root.is_symlink():
        raise ExportError("output directory already exists; choose a new take")
    try:
        root.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        raise ExportError(f"cannot create output directory: {error}") from error
    started = time.perf_counter()
    timings = {"field_s": 0.0, "raster_s": 0.0, "png_s": 0.0, "log_s": 0.0}
    state = initial_state(scene)
    status = {"schema_version": "cz-run-status-0.3", "scene_id": scene.scene_id,
              "state": "running", "last_committed_tick": 0, "error_code": None}
    published = False
    try:
        atomic_json(root / "run_status.json", status)
        atomic_write(root / "scene.input.json", scene.raw_bytes)
        atomic_json(root / "scene.resolved.json", resolved_mapping(scene))
        source = _snapshot(root)
        (root / "frames").mkdir()
        for name in ("states.jsonl", "decisions.jsonl", "frames.jsonl"):
            (root / name).touch(exist_ok=False)
        if validate_state(state, scene):
            raise NumericalRejection("invalid initial state")
        _append_row(root / "states.jsonl", state_mapping(state))
        rows = []
        baseline = None

        def frame(current):
            nonlocal baseline
            at = time.perf_counter()
            samples = evaluate_samples(current, scene)
            timings["field_s"] += time.perf_counter() - at
            at = time.perf_counter()
            pixels = rasterize(samples, scene)
            if baseline is None:
                baseline = geometry_mask(pixels, scene)
            metrics = measure_mask(pixels, scene, baseline)
            metrics.update(field_min=float(samples.min()), field_max=float(samples.max()))
            timings["raster_s"] += time.perf_counter() - at
            i = len(rows)
            relative = f"frames/frame_{i:06d}.png"
            at = time.perf_counter()
            data = encode_gray_png(pixels)
            atomic_write(root / relative, data)
            timings["png_s"] += time.perf_counter() - at
            row = {"index": i, "tick": current.tick, "path": relative, "mode": "L",
                   "width": scene.width, "height": scene.height,
                   "file_sha256": sha256(data), "pixel_sha256": pixel_hash(pixels),
                   "metrics": metrics}
            at = time.perf_counter()
            _append_row(root / "frames.jsonl", row)
            timings["log_s"] += time.perf_counter() - at
            rows.append(row)

        frame(state)  # MUST precede any simulation update.
        output_ticks = set(scene.frame_ticks[1:])
        for _ in range(scene.terminal_tick):
            candidate = propose_step(state, scene)
            decision = check_transition(state, candidate, scene)
            row = {"attempted_tick": decision.attempted_tick, "status": decision.status,
                   "source_state_hash": _state_hash(state), "reasons": list(decision.reasons)}
            if decision.status == "ACCEPT":
                row["committed_state_hash"] = _state_hash(candidate)
            at = time.perf_counter()
            _append_row(root / "decisions.jsonl", row)
            timings["log_s"] += time.perf_counter() - at
            if decision.status == "REJECT":
                raise NumericalRejection(f"transition {decision.attempted_tick}: {decision.reasons}")
            state = candidate  # only after successful decision close
            _append_row(root / "states.jsonl", state_mapping(state))
            if state.tick in output_ticks:
                frame(state)
        index = _contact_index(rows, scene)
        atomic_json(root / "contact_sheet.index.json", index)
        atomic_write(root / "contact_sheet.png", _contact_png(root, index))
        atomic_write(root / "player.html", _player(scene))
        artifacts = {p.relative_to(root).as_posix(): sha256(p.read_bytes())
                     for p in sorted(root.rglob("*")) if p.is_file()
                     and p.name != "run_status.json"}
        manifest = {"schema_version": "cz-run-manifest-0.3", "engine_version": __version__,
                    "scene_id": scene.scene_id,
                    "config": {"raw_sha256": sha256(scene.raw_bytes),
                               "resolved_sha256": sha256(canonical_bytes(resolved_mapping(scene)))},
                    "element_order": list(scene.element_order), "policies": dict(POLICIES),
                    "timeline": {"sim_hz": scene.sim_hz, "fps_out": scene.fps_out,
                                 "frame_count": scene.frame_count,
                                 "stride": scene.sim_hz // scene.fps_out,
                                 "terminal_tick": scene.terminal_tick},
                    "expected": {"frames": scene.frame_count, "states": scene.terminal_tick + 1,
                                 "transitions": scene.terminal_tick},
                    "counts": {"accepted": scene.terminal_tick, "rejected": 0},
                    "artifacts": artifacts, "source": source, "environment": environment_info(),
                    "verification": {"closed_artifacts": "passed"}, "timings": timings,
                    "warnings": [], "creator_review": {"status": "pending", "source": None},
                    "contact_frames": _contact_indices(rows)}
        # No final manifest exists here. Check all closed evidence in memory.
        _verify_closed(root, manifest, prospective=True)
        status.update(state="complete", last_committed_tick=state.tick)
        atomic_json(root / "run_status.json", status)
        artifacts["run_status.json"] = sha256((root / "run_status.json").read_bytes())
        timings["wall_s"] = time.perf_counter() - started
        timings["peak_rss_kib"] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        timings["peak_rss_method"] = "getrusage process lifetime high-water; Linux KiB, macOS bytes"
        atomic_json(root / "manifest.json", manifest)
        published = True
        verify_integrity(root / "manifest.json")
        return manifest
    except Exception as error:
        # Never rewrite a hashed complete status after final publication.
        if not published:
            with contextlib.suppress(Exception):
                status.update(state="failed", last_committed_tick=state.tick,
                              error_code="NUMERICAL_REJECTION" if isinstance(error, NumericalRejection)
                              else "EXPORT_FAILURE")
                atomic_json(root / "run_status.json", status)
        if isinstance(error, (NumericalRejection, ExportError)):
            raise
        raise ExportError(f"run failed at committed tick {state.tick}: {error}") from error


def _decode(path, scene):
    with Image.open(path) as image:
        _require(image.mode == "L" and image.size == (scene.width, scene.height),
                 "frame mode/dimensions differ")
        image.load()  # force full decode after bounded header validation
        return np.array(image, dtype=np.uint8, copy=True)


def _verify_closed(root, manifest, *, prospective=False):
    _keys(manifest, MANIFEST_KEYS, "manifest")
    _require(manifest["schema_version"] == "cz-run-manifest-0.3"
             and manifest["engine_version"] == __version__, "manifest version")
    _keys(manifest["config"], {"raw_sha256", "resolved_sha256"}, "config")
    _keys(manifest["source"], {"digest", "index_path"}, "source")
    _keys(manifest["creator_review"], {"status", "source"}, "creator_review")
    _require(manifest["creator_review"]["status"] in ("pending", "accepted", "rejected"),
             "unknown creator review status")
    _require(manifest["creator_review"]["status"] == "pending"
             and manifest["creator_review"]["source"] is None,
             "Build 0 exporter requires separately supplied human review evidence")
    _require(manifest["policies"] == POLICIES, "unknown numerical policy")
    _require(manifest["verification"] == {"closed_artifacts": "passed"}, "verification schema")
    _require(type(manifest["warnings"]) is list
             and all(type(w) is str for w in manifest["warnings"]), "warnings schema")
    base_timings = {"field_s", "raster_s", "png_s", "log_s"}
    _keys(manifest["timings"], base_timings if prospective else
          base_timings | {"wall_s", "peak_rss_kib", "peak_rss_method"}, "timings")
    for key in base_timings | (set() if prospective else {"wall_s"}):
        value = manifest["timings"][key]
        _require(type(value) is float and np.isfinite(value) and value >= 0.0,
                 "timing must be a finite nonnegative float")
    if not prospective:
        _require(type(manifest["timings"]["peak_rss_kib"]) is int
                 and manifest["timings"]["peak_rss_kib"] >= 0
                 and type(manifest["timings"]["peak_rss_method"]) is str, "RSS metadata schema")
    scene = load_scene(root / "scene.input.json")
    resolved = resolved_mapping(scene)
    _require(manifest["scene_id"] == scene.scene_id, "scene identity mismatch")
    _require((root / "scene.resolved.json").read_bytes() == canonical_bytes(resolved),
             "resolved scene differs from validated input")
    _require(manifest["config"] == {"raw_sha256": sha256(scene.raw_bytes),
                                    "resolved_sha256": sha256(canonical_bytes(resolved))},
             "configuration hash mismatch")
    _require(manifest["element_order"] == list(scene.element_order), "element mapping differs")
    _keys(manifest["timeline"], {"sim_hz", "fps_out", "frame_count", "stride", "terminal_tick"}, "timeline")
    for name, value in {"sim_hz": scene.sim_hz, "fps_out": scene.fps_out,
                        "frame_count": scene.frame_count, "stride": scene.sim_hz // scene.fps_out,
                        "terminal_tick": scene.terminal_tick}.items():
        _integer(manifest["timeline"][name], value, name)
    _keys(manifest["expected"], {"frames", "states", "transitions"}, "expected")
    for key, count in {"frames": scene.frame_count, "states": scene.terminal_tick + 1,
                       "transitions": scene.terminal_tick}.items():
        _integer(manifest["expected"][key], count, key)
    _keys(manifest["counts"], {"accepted", "rejected"}, "counts")
    _integer(manifest["counts"]["accepted"], scene.terminal_tick, "accepted")
    _integer(manifest["counts"]["rejected"], 0, "rejected")
    _keys(manifest["environment"], set(environment_info()), "environment")
    _require(all(type(value) is str and bool(value) for value in manifest["environment"].values()),
             "environment values must be nonempty version/build strings")
    artifacts = manifest["artifacts"]
    _require(type(artifacts) is dict, "artifacts must be a hash mapping")
    required = {"scene.input.json", "scene.resolved.json", "states.jsonl", "decisions.jsonl",
                "frames.jsonl", "contact_sheet.png", "contact_sheet.index.json", "player.html",
                "source/index.json"} | {f"frames/frame_{i:06d}.png" for i in range(scene.frame_count)}
    if not prospective:
        required.add("run_status.json")
    _require(required <= artifacts.keys(), "missing required artifact reference")
    _require("manifest.json" not in artifacts, "manifest cannot hash itself")
    for path, digest in artifacts.items():
        _require(path in required or path.startswith("source/files/"), "unexpected artifact reference")
        _require(type(digest) is str and len(digest) == 64
                 and all(c in "0123456789abcdef" for c in digest), "malformed SHA-256")
        file = _path(root, path)
        _require(file.is_file() and sha256(file.read_bytes()) == digest,
                 f"artifact hash mismatch or missing: {path}")
    source_index = read_json(_path(root, manifest["source"]["index_path"]))
    _require(manifest["source"]["index_path"] == "source/index.json", "source index path")
    _require(type(source_index) is dict and bool(source_index), "empty source snapshot")
    _require((root / "source/index.json").read_bytes() == canonical_bytes(source_index),
             "noncanonical source index")
    _require(REQUIRED_SOURCE <= source_index.keys(), "missing executed engine, dependency lock or scene fixture")
    _require(sha256(canonical_bytes(source_index)) == manifest["source"]["digest"], "source digest")
    _require({f"source/files/{p}" for p in source_index}
             == {p for p in artifacts if p.startswith("source/files/")}, "source snapshot membership")
    for relative, digest in source_index.items():
        _require(sha256(_path(root, f"source/files/{relative}").read_bytes()) == digest,
                 "source snapshot hash mismatch")
    _require({p.relative_to(root / "source/files").as_posix()
              for p in (root / "source/files").rglob("*") if p.is_file()} == set(source_index),
             "unindexed source snapshot files")
    states = read_jsonl(root / "states.jsonl")
    decisions = read_jsonl(root / "decisions.jsonl")
    frames = read_jsonl(root / "frames.jsonl")
    for name, rows in (("states", states), ("decisions", decisions), ("frames", frames)):
        _require((root / f"{name}.jsonl").read_bytes() == b"".join(canonical_bytes(row) for row in rows),
                 f"noncanonical {name} trace")
    _require(len(states) == scene.terminal_tick + 1 and len(decisions) == scene.terminal_tick
             and len(frames) == scene.frame_count, "trace record counts")
    committed = []
    state_hashes = []
    for tick, row in enumerate(states):
        _keys(row, {"tick", "positions", "velocities"}, "state")
        _integer(row["tick"], tick, "state.tick")
        for field in ("positions", "velocities"):
            _require(type(row[field]) is list and len(row[field]) == len(scene.elements), "state shape")
            _require(all(type(pair) is list and len(pair) == 2
                         and all(type(n) is float for n in pair) for pair in row[field]), "state real arrays")
        state = owned_state(tick, row["positions"], row["velocities"])
        _require(not validate_state(state, scene), "invalid accepted state")
        committed.append(state)
        state_hashes.append(sha256(canonical_bytes(row)))
    _require(canonical_bytes(states[0]) == canonical_bytes(state_mapping(initial_state(scene))),
             "initial state is not home and zero velocity")
    for i, row in enumerate(decisions):
        _keys(row, {"attempted_tick", "status", "source_state_hash", "committed_state_hash", "reasons"}, "decision")
        _integer(row["attempted_tick"], i + 1, "attempted_tick")
        _require(row["status"] == "ACCEPT" and row["reasons"] == [], "complete trace contains rejection")
        _require(row["source_state_hash"] == state_hashes[i]
                 and row["committed_state_hash"] == state_hashes[i + 1], "decision state link mismatch")
        _require(check_transition(committed[i], committed[i + 1], scene).status == "ACCEPT", "transition guard")
        # Stronger than hashes: ensure this trajectory belongs to the declared solver/cues.
        expected_state = propose_step(committed[i], scene)
        _require(canonical_bytes(state_mapping(expected_state)) == canonical_bytes(states[i + 1]),
                 "trajectory differs from numerical policy")
    numbered = {p.name for p in (root / "frames").iterdir() if p.is_file()}
    _require(numbered == {f"frame_{i:06d}.png" for i in range(scene.frame_count)},
             "missing or extra numbered frames")
    baseline = None
    for i, row in enumerate(frames):
        _keys(row, FRAME_KEYS, "frame")
        _integer(row["index"], i, "frame.index")
        _integer(row["tick"], scene.frame_ticks[i], "frame.tick")
        _integer(row["width"], scene.width, "frame.width")
        _integer(row["height"], scene.height, "frame.height")
        _require(row["mode"] == "L" and row["path"] == f"frames/frame_{i:06d}.png", "frame path/mode")
        path = _path(root, row["path"])
        pixels = _decode(path, scene)
        _require(row["file_sha256"] == sha256(path.read_bytes())
                 and row["pixel_sha256"] == pixel_hash(pixels), "frame hash mismatch")
        samples = evaluate_samples(committed[row["tick"]], scene)
        expected_pixels = rasterize(samples, scene)
        _require(np.array_equal(pixels, expected_pixels), "pixels differ from recorded state geometry")
        _require(path.read_bytes() == encode_gray_png(pixels), "PNG encoder settings/metadata differ")
        if baseline is None:
            baseline = geometry_mask(pixels, scene)
        actual = measure_mask(pixels, scene, baseline)
        actual.update(field_min=float(samples.min()), field_max=float(samples.max()))
        _keys(row["metrics"], METRIC_KEYS, "frame.metrics")
        _require(canonical_bytes(actual) == canonical_bytes(row["metrics"]), "frame metrics differ")
    index = read_json(root / "contact_sheet.index.json")
    _keys(index, CONTACT_KEYS, "contact index")
    _require(canonical_bytes(index) == canonical_bytes(_contact_index(frames, scene)),
             "contact sheet references/labels differ")
    _require(canonical_bytes(manifest["contact_frames"]) == canonical_bytes(_contact_indices(frames)),
             "contact frame selection")
    _require((root / "contact_sheet.png").read_bytes() == _contact_png(root, index), "contact sheet pixels differ")
    _require((root / "player.html").read_bytes() == _player(scene), "local viewer differs")
    status = read_json(root / "run_status.json")
    _require((root / "run_status.json").read_bytes() == canonical_bytes(status), "noncanonical status")
    _keys(status, STATUS_KEYS, "status")
    _require(status["schema_version"] == "cz-run-status-0.3" and status["scene_id"] == scene.scene_id,
             "status version/scene")
    _require(status["state"] == ("running" if prospective else "complete")
             and status["error_code"] is None, "incomplete/failed run status")
    if not prospective:
        _integer(status["last_committed_tick"], scene.terminal_tick, "status tick")
    return {"schema_version": "cz-integrity-0.3", "passed": True,
            "frames": len(frames), "states": len(states), "decisions": len(decisions),
            "source_digest": manifest["source"]["digest"],
            "creator_review": manifest["creator_review"]["status"]}


def verify_integrity(manifest_path):
    path = Path(manifest_path)
    try:
        _require(path.name == "manifest.json" and not path.is_symlink(), "expected manifest.json")
        manifest = read_json(path)
        _require(path.read_bytes() == canonical_bytes(manifest), "noncanonical manifest")
        return _verify_closed(path.parent, manifest)
    except IntegrityError:
        raise
    except Exception as error:
        raise IntegrityError(f"invalid evidence: {error}") from error


def verify_replay(manifest_path, new_output_directory):
    verify_integrity(Path(manifest_path))
    original = Path(manifest_path).resolve()
    manifest = read_json(original)
    if manifest["source"]["digest"] != source_digest():
        raise ReplayError("executed source/lock/fixtures differ from recorded source; exact replay unavailable")
    if manifest["environment"] != environment_info():
        raise ReplayError("environment differs; exact replay unavailable")
    out = Path(new_output_directory).absolute()
    if out.exists() or out.is_symlink():
        raise ReplayError("replay destination already exists")
    command = [sys.executable, "-m", "commander_zorg.cli", "render",
               str(original.parent / "scene.input.json"), "--out", str(out)]
    # Inherit the active Python installation. Never execute recorded source or shell text.
    result = subprocess.run(command, capture_output=True, text=True, check=False,
                            cwd=Path(__file__).resolve().parent.parent)
    if result.returncode != 0:
        raise ReplayError(f"fresh process exited {result.returncode}: {result.stderr[-2000:]}")
    verify_integrity(out / "manifest.json")
    replay = read_json(out / "manifest.json")
    before = read_jsonl(original.parent / "frames.jsonl")
    after = read_jsonl(out / "frames.jsonl")
    comparisons = {
        "states": (original.parent / "states.jsonl").read_bytes() == (out / "states.jsonl").read_bytes(),
        "decisions": (original.parent / "decisions.jsonl").read_bytes() == (out / "decisions.jsonl").read_bytes(),
        "pixels": [r["pixel_sha256"] for r in before] == [r["pixel_sha256"] for r in after],
        "png_files": [r["file_sha256"] for r in before] == [r["file_sha256"] for r in after]}
    report = {"schema_version": "cz-replay-0.3", "passed": all(comparisons.values()),
              "original_manifest_sha256": sha256(original.read_bytes()),
              "replayed_manifest_sha256": sha256((out / "manifest.json").read_bytes()),
              "comparisons": comparisons, "environment_match": manifest["environment"] == replay["environment"],
              "source_match": manifest["source"] == replay["source"]}
    report["passed"] = report["passed"] and report["environment_match"] and report["source_match"]
    atomic_json(out / "replay_report.json", report)
    if not report["passed"]:
        raise ReplayError("fresh-process exact replay mismatch; report retained")
    return report
