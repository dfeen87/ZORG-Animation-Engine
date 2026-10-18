"""Explicit E0 gallery, independent cadence study and Build 0 profile gates."""
from __future__ import annotations

from copy import deepcopy
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .canonical import atomic_json, canonical_bytes, read_json, read_jsonl, sha256
from .config import load_scene, resolved_mapping
from .raster import encode_gray_png


class ProfileError(ValueError):
    """An experiment's linked evidence is malformed, missing or inconsistent."""
    exit_code = 6


_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ID = re.compile(r"[a-z][a-z0-9_]{0,31}\Z", re.ASCII)
_METRICS = {"occupancy", "centroid", "bbox", "clipping", "empty", "iou",
            "aligned_iou", "centroid_distance", "field_min", "field_max"}


def _keys(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ProfileError(f"{label}: expected exactly {sorted(expected)}")


def _number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _digest(value, label):
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ProfileError(f"{label}: expected lowercase SHA-256 digest")


def _strings(value, label):
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ProfileError(f"{label}: expected array of strings")


def _review(value):
    _keys(value, {"status", "source"}, "creator_review")
    if value["status"] != "pending" or value["source"] is not None:
        raise ProfileError("creator review must remain pending without separately supplied human evidence")


def _metric_types(metrics):
    _keys(metrics, _METRICS, "gallery candidate metrics")
    for key in ("occupancy", "field_min", "field_max"):
        if not _number(metrics[key]):
            raise ProfileError(f"metrics.{key}: expected finite real, not boolean")
    if not 0 <= metrics["occupancy"] <= 1 or metrics["field_min"] > metrics["field_max"]:
        raise ProfileError("metrics: invalid occupancy or field extrema")
    if type(metrics["clipping"]) is not bool or type(metrics["empty"]) is not bool:
        raise ProfileError("metrics clipping and empty must be booleans")
    for key in ("iou", "aligned_iou"):
        if metrics[key] is not None and (not _number(metrics[key]) or not 0 <= metrics[key] <= 1):
            raise ProfileError(f"metrics.{key}: expected null or finite similarity in [0,1]")
    if metrics["centroid_distance"] is not None and (not _number(metrics["centroid_distance"]) or metrics["centroid_distance"] < 0):
        raise ProfileError("metrics.centroid_distance: expected null or nonnegative finite real")
    centroid, bbox = metrics["centroid"], metrics["bbox"]
    if centroid is not None and (type(centroid) is not list or len(centroid) != 2 or not all(_number(x) for x in centroid)):
        raise ProfileError("metrics.centroid: expected null or two finite reals")
    if bbox is not None and (type(bbox) is not list or len(bbox) != 4 or not all(type(x) is int and x >= 0 for x in bbox)):
        raise ProfileError("metrics.bbox: expected null or four nonnegative integer indices")
    if metrics["empty"] != (centroid is None and bbox is None) or (centroid is None) != (bbox is None):
        raise ProfileError("metrics: empty status, centroid and bbox disagree")


def _reference(base: Path, ref: dict) -> Path:
    _keys(ref, {"path", "sha256"}, "artifact reference")
    _digest(ref["sha256"], "artifact reference.sha256")
    name = ref["path"]
    if type(name) is not str or "\\" in name or "\x00" in name:
        raise ProfileError("reference path must be a normalized relative POSIX path")
    rel = PurePosixPath(name)
    if rel.is_absolute() or not rel.parts or any(p in {".", ".."} for p in rel.parts) or str(rel) != name:
        raise ProfileError("reference path must not escape the experiment directory")
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ProfileError(f"missing or escaping artifact: {name}")
    if sha256(path.read_bytes()) != ref["sha256"]:
        raise ProfileError(f"artifact hash differs: {name}")
    return path


def _file_ref(base: Path, path: Path) -> dict:
    return {"path": path.relative_to(base).as_posix(), "sha256": sha256(path.read_bytes())}


def _e0_policy(mapping: dict) -> dict:
    """Only scene ID, frame count, cues, homes and sigma vary in our E0 study."""
    policy = deepcopy(mapping)
    policy.pop("scene_id")
    policy.pop("cues")
    policy["timeline"].pop("frame_count")
    for element in policy["elements"]:
        element.pop("home_xy")
        element.pop("sigma")
    return policy


def gallery(preset_directory: Path, out: Path) -> dict:
    """Render all six explicit presets, retaining every failed-gate candidate."""
    from .evidence import render_run, verify_integrity
    files = sorted(Path(preset_directory).glob("*.json"))
    if len(files) != 6:
        raise ProfileError("E0 requires exactly six explicit JSON presets")
    scenes = [(path, load_scene(path)) for path in files]
    mappings = [resolved_mapping(scene) for _, scene in scenes]
    weights = {element["id"]: element["weight"] for element in mappings[0]["elements"]}
    threshold = mappings[0]["field"]["threshold"]
    for mapping in mappings:
        if _e0_policy(mapping) != _e0_policy(mappings[0]):
            raise ProfileError("E0 preset changes a parameter outside home geometry or sigma")
        if not 5 <= len(mapping["elements"]) <= 12:
            raise ProfileError("every delivered E0 preset requires 5 through 12 elements")
        if mapping["timeline"]["frame_count"] != 1 or mapping["cues"]:
            raise ProfileError("E0 presets must be static, one-frame, cue-disabled scenes")
        if mapping["field"]["threshold"] != threshold or {e["id"]: e["weight"] for e in mapping["elements"]} != weights:
            raise ProfileError("E0 threshold and per-ID weights must remain fixed")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    atomic_json(out / "run_status.json", {"state": "running"})
    candidates = []
    images = []
    for index, (path, scene) in enumerate(scenes):
        name = f"candidate_{index + 1:02d}"
        directory = out / name
        try:
            render_run(scene, directory)
            verify_integrity(directory / "manifest.json")
            records = read_jsonl(directory / "frames.jsonl")
            record = records[0]
            metrics = record["metrics"]
            failed = []
            if not all(math.isfinite(metrics[key]) for key in ("field_min", "field_max")):
                failed.append("nonfinite_field")
            if not .03 <= metrics["occupancy"] <= .65:
                failed.append("occupancy")
            if metrics["clipping"]:
                failed.append("clipping")
            candidate = {"scene_id": mappings[index]["scene_id"], "manifest": _file_ref(out, directory / "manifest.json"),
                         "pixel_sha256": record["pixel_sha256"], "metrics": metrics,
                         "usable": not failed, "failed_gates": failed, "error": None}
            with Image.open(directory / record["path"]) as image:
                images.append(image.copy())
        except Exception as error:
            candidate = {"scene_id": mappings[index]["scene_id"], "manifest": None,
                         "pixel_sha256": None, "metrics": None, "usable": False,
                         "failed_gates": ["render_or_integrity_failure"], "error": str(error)}
            images.append(Image.new("L", (384, 384), 0))
        candidates.append(candidate)
    contact = _gallery_contact(candidates, images)
    (out / "contact_sheet.png").write_bytes(contact)
    hashes = {candidate["pixel_sha256"] for candidate in candidates if candidate["pixel_sha256"] is not None}
    complete = all(candidate["manifest"] is not None for candidate in candidates)
    passed = complete and len(hashes) >= 4 and any(candidate["usable"] for candidate in candidates)
    atomic_json(out / "run_status.json", {"state": "complete" if complete else "failed"})
    report = {"schema_version": "cz-gallery-0.3", "status": "complete" if complete else "failed",
              "passed": passed, "candidate_count": 6, "distinct_decoded_images": len(hashes),
              "candidates": candidates, "artifacts": {
                  "contact_sheet.png": sha256((out / "contact_sheet.png").read_bytes()),
                  "run_status.json": sha256((out / "run_status.json").read_bytes())},
              "creator_review": {"status": "pending", "source": None}}
    atomic_json(out / "manifest.json", report)
    return report


def _gallery_contact(candidates, images):
    tile, label = 256, 38
    sheet = Image.new("L", (tile * 3, (tile + label) * 2), 16)
    draw = ImageDraw.Draw(sheet)
    for index, (candidate, image) in enumerate(zip(candidates, images)):
        x, y = (index % 3) * tile, (index // 3) * (tile + label)
        image.thumbnail((tile, tile), Image.Resampling.NEAREST)
        sheet.paste(image, (x + (tile - image.width) // 2, y))
        draw.text((x + 5, y + tile + 2), candidate["scene_id"], fill=255)
        draw.text((x + 5, y + tile + 17), "usable" if candidate["usable"] else "FAILED GATES", fill=255)
    return encode_gray_png(np.asarray(sheet, dtype=np.uint8))


def verify_gallery(path: Path) -> dict:
    """Recheck child runs and derive E0 gates from the actual closed artifacts."""
    from .evidence import verify_integrity
    data = read_json(path)
    base = Path(path).parent
    _keys(data, {"schema_version", "status", "passed", "candidate_count", "distinct_decoded_images",
                 "candidates", "artifacts", "creator_review"}, "gallery")
    if data["schema_version"] != "cz-gallery-0.3" or data["status"] != "complete":
        raise ProfileError("gallery is not complete")
    if type(data["passed"]) is not bool or type(data["candidate_count"]) is not int or data["candidate_count"] != 6:
        raise ProfileError("gallery count and pass status types differ from schema")
    if type(data["distinct_decoded_images"]) is not int or not 0 <= data["distinct_decoded_images"] <= 6:
        raise ProfileError("gallery distinct count must be an integer in [0,6]")
    if type(data["candidates"]) is not list or len(data["candidates"]) != 6:
        raise ProfileError("gallery must contain exactly six candidates")
    _review(data["creator_review"])
    _keys(data["artifacts"], {"contact_sheet.png", "run_status.json"}, "gallery.artifacts")
    scene_ids = []
    for candidate in data["candidates"]:
        _keys(candidate, {"scene_id", "manifest", "pixel_sha256", "metrics", "usable", "failed_gates", "error"}, "gallery candidate")
        if type(candidate["scene_id"]) is not str or _ID.fullmatch(candidate["scene_id"]) is None:
            raise ProfileError("gallery candidate scene_id is malformed")
        scene_ids.append(candidate["scene_id"])
        _digest(candidate["pixel_sha256"], "gallery candidate pixel_sha256")
        _metric_types(candidate["metrics"])
        if type(candidate["usable"]) is not bool or candidate["error"] is not None:
            raise ProfileError("complete gallery candidate requires a boolean usability and null error")
        _strings(candidate["failed_gates"], "gallery candidate failed_gates")
        if any(g not in {"nonfinite_field", "occupancy", "clipping"} for g in candidate["failed_gates"]):
            raise ProfileError("gallery candidate has an unknown failed gate")
    if len(set(scene_ids)) != 6:
        raise ProfileError("gallery scene IDs must be unique")
    for name, digest in data["artifacts"].items():
        _reference(base, {"path": name, "sha256": digest})
    status = read_json(base / "run_status.json")
    _keys(status, {"state"}, "gallery run_status")
    if status["state"] != "complete":
        raise ProfileError("gallery run status is not complete")
    with Image.open(base / "contact_sheet.png") as sheet:
        if sheet.mode != "L" or sheet.size != (768, 588):
            raise ProfileError("gallery contact sheet has wrong mode or dimensions")
    seen = set()
    mappings = []
    images = []
    for candidate in data["candidates"]:
        child = _reference(base, candidate["manifest"])
        verify_integrity(child)
        mapping = read_json(child.parent / "scene.resolved.json")
        mappings.append(mapping)
        if mapping["scene_id"] != candidate["scene_id"] or len(mapping["elements"]) not in range(5, 13):
            raise ProfileError("gallery scene identity or influence count differs")
        if mapping["cues"] or mapping["timeline"]["frame_count"] != 1:
            raise ProfileError("gallery candidate is not static")
        frame = read_jsonl(child.parent / "frames.jsonl")[0]
        metrics = frame["metrics"]
        usable = math.isfinite(metrics["field_min"]) and math.isfinite(metrics["field_max"]) and .03 <= metrics["occupancy"] <= .65 and not metrics["clipping"]
        if frame["pixel_sha256"] != candidate["pixel_sha256"] or metrics != candidate["metrics"] or usable != candidate["usable"]:
            raise ProfileError("gallery candidate evidence differs from its run")
        expected_failed = []
        if not all(math.isfinite(metrics[k]) for k in ("field_min", "field_max")):
            expected_failed.append("nonfinite_field")
        if not .03 <= metrics["occupancy"] <= .65:
            expected_failed.append("occupancy")
        if metrics["clipping"]:
            expected_failed.append("clipping")
        if candidate["failed_gates"] != expected_failed:
            raise ProfileError("gallery failed-gate labels differ from measured evidence")
        seen.add(frame["pixel_sha256"])
        with Image.open(child.parent / frame["path"]) as image:
            images.append(image.copy())
    if _gallery_contact(data["candidates"], images) != (base / "contact_sheet.png").read_bytes():
        raise ProfileError("gallery contact sheet differs from candidate images or labels")
    first = mappings[0]
    for mapping in mappings[1:]:
        if _e0_policy(mapping) != _e0_policy(first):
            raise ProfileError("gallery changes a parameter outside the recorded E0 study")
        if mapping["field"] != first["field"] or {e["id"]: e["weight"] for e in mapping["elements"]} != {e["id"]: e["weight"] for e in first["elements"]}:
            raise ProfileError("gallery weight or threshold policy differs")
    passed = len(seen) >= 4 and any(c["usable"] for c in data["candidates"])
    if data.get("distinct_decoded_images") != len(seen) or data.get("passed") != passed:
        raise ProfileError("gallery gate claims differ from measured results")
    return {"passed": passed, "distinct_decoded_images": len(seen), "creator_review": data["creator_review"],
            "usable_scenes": [m for m, c in zip(mappings, data["candidates"]) if c["usable"]]}


def _numeric_state(state, count):
    for key in ("positions", "velocities"):
        table = state.get(key)
        if type(table) is not list or len(table) != count:
            return False
        if any(type(row) is not list or len(row) != 2 or not all(_number(v) for v in row) for row in table):
            return False
    return True


def profile_metrics(scene: dict, states: list[dict], frames: list[dict],
                    control_scene: dict, control_states: list[dict], control_frames: list[dict]) -> dict:
    """Measure the exact E1 profile; callers verify artifact integrity first."""
    gates = {}
    def gate(name: str, passed: bool, measured: Any = None):
        gates[name] = {"passed": bool(passed), "measured": measured}
    nominal = (scene["raster"] == {"width": 384, "height": 384, "samples_per_axis": 2, "invert": scene["raster"]["invert"]}
               and scene["timeline"] == {"sim_hz": 60, "fps_out": 30, "frame_count": 180})
    gate("nominal_settings", nominal)
    gate("state_schedule", all(type(s.get("tick")) is int for s in states) and [s.get("tick") for s in states] == list(range(361)))
    gate("frame_schedule", all(type(f.get("index")) is int and type(f.get("tick")) is int for f in frames) and [(f.get("index"), f.get("tick")) for f in frames] == [(i, i * 2) for i in range(180)])
    home = np.asarray([e["home_xy"] for e in scene["elements"]], dtype=np.float64)
    try:
        positions = np.asarray([s["positions"] for s in states], dtype=np.float64)
        velocities = np.asarray([s["velocities"] for s in states], dtype=np.float64)
        proper = positions.shape == (361, len(home), 2) and velocities.shape == positions.shape
        finite = proper and all(_numeric_state(s, len(home)) for s in states) and bool(np.isfinite(positions).all() and np.isfinite(velocities).all())
    except (ValueError, TypeError, KeyError):
        finite = False
    gate("finite_states", finite)
    if finite:
        displacement = np.linalg.norm(positions - home, axis=2)
        speeds = np.linalg.norm(velocities, axis=2)
        gate("state_bounds", bool(np.all(displacement <= scene["limits"]["max_displacement"]) and np.all(speeds <= scene["limits"]["max_speed"])))
        groups = {c["group"] for c in scene["cues"]}
        targets = [i for i, e in enumerate(scene["elements"]) if e["group"] in groups]
        peak = float(displacement[:, targets].max()) if targets else 0.0
        gate("excitation", peak >= .05, peak)
        tail_position, tail_speed = float(displacement[330:361].max()), float(speeds[330:361].max())
        gate("numeric_recovery", tail_position <= .01 and tail_speed <= .02,
             {"position_max": tail_position, "speed_max": tail_speed, "first_tick": 330, "last_tick": 360})
    else:
        for name in ("state_bounds", "excitation", "numeric_recovery"):
            gate(name, False)
    metrics = [f.get("metrics", {}) for f in frames]
    visibility = all(_number(m.get("occupancy")) and .03 <= m["occupancy"] <= .65 and m.get("clipping") is False and m.get("empty") is False for m in metrics)
    gate("visibility", len(metrics) == 180 and visibility)
    gate("finite_fields", len(metrics) == 180 and all(all(_number(m.get(k)) for k in ("field_min", "field_max")) for m in metrics))
    disturbed = [f["metrics"].get("aligned_iou") for f in frames if 0 < f.get("tick", 0) < 330]
    disturbed = [v for v in disturbed if _number(v)]
    minimum = min(disturbed) if disturbed else None
    gate("morphology", minimum is not None and minimum <= .90, minimum)
    distinct = len({f.get("pixel_sha256") for f in frames if isinstance(f.get("pixel_sha256"), str)})
    gate("temporal_variation", distinct >= 10, distinct)
    tail_frames = [f for f in frames if 330 <= f.get("tick", -1) <= 360]
    gate("image_recovery", len(tail_frames) == 15 and all(
        _number(f["metrics"].get("iou")) and f["metrics"]["iou"] >= .98
        and _number(f["metrics"].get("centroid_distance")) and f["metrics"]["centroid_distance"] <= .01
        for f in tail_frames))
    cue_off = deepcopy(scene)
    cue_off["cues"] = []
    cue_off["scene_id"] = control_scene.get("scene_id")
    gate("control_configuration", cue_off == control_scene and scene["scene_id"] != control_scene.get("scene_id"))
    gate("control_schedule", all(type(s.get("tick")) is int for s in control_states) and all(type(f.get("index")) is int and type(f.get("tick")) is int for f in control_frames) and [s.get("tick") for s in control_states] == list(range(361)) and
         [(f.get("index"), f.get("tick")) for f in control_frames] == [(i, i * 2) for i in range(180)])
    control_state_invariant = False
    if control_states:
        initial_p = canonical_bytes(control_states[0]["positions"])
        initial_v = canonical_bytes(control_states[0]["velocities"])
        control_state_invariant = all(_numeric_state(s, len(home)) and canonical_bytes(s["positions"]) == initial_p and canonical_bytes(s["velocities"]) == initial_v for s in control_states)
        control_state_invariant = control_state_invariant and np.array_equal(np.asarray(control_states[0]["positions"]), home) and bool(np.all(np.asarray(control_states[0]["velocities"]) == 0))
    gate("control_state_invariance", control_state_invariant)
    gate("control_frame_invariance", len(control_frames) == 180 and len({f.get("pixel_sha256") for f in control_frames}) == 1 and bool(control_frames) and bool(frames) and control_frames[0].get("pixel_sha256") == frames[0].get("pixel_sha256"))
    return {"passed": all(v["passed"] for v in gates.values()), "gates": gates}


def _verify_test_report(path, tests, source_digest):
    _keys(tests, {"schema_version", "passed", "exit_code", "families", "source_digest", "command", "summary", "artifacts", "counts"}, "tests")
    if tests["schema_version"] != "cz-tests-0.3" or type(tests["passed"]) is not bool:
        raise ProfileError("tests schema version or passed type differs")
    if type(tests["exit_code"]) is not int or tests["exit_code"] < 0:
        raise ProfileError("tests.exit_code must be a nonnegative integer")
    _digest(tests["source_digest"], "tests.source_digest")
    families = {f"V{i:02d}" for i in range(1, 13)}
    _keys(tests["families"], families, "tests.families")
    if any(type(v) is not bool for v in tests["families"].values()):
        raise ProfileError("test family flags must be booleans")
    _strings(tests["command"], "tests.command")
    if not tests["command"] or any(not part for part in tests["command"]) or type(tests["summary"]) is not str:
        raise ProfileError("tests command must be nonempty strings and summary must be a string")
    _keys(tests["counts"], {"passed", "failed", "errors", "skipped"}, "tests.counts")
    if any(type(v) is not int or v < 0 for v in tests["counts"].values()):
        raise ProfileError("test counts must be nonnegative integers, not booleans")
    _keys(tests["artifacts"], {"test-output.txt", "junit.xml"}, "tests.artifacts")
    artifacts = {name: _reference(path.parent, {"path": name, "sha256": digest})
                 for name, digest in tests["artifacts"].items()}
    if not artifacts["test-output.txt"].read_text(encoding="utf-8").strip():
        raise ProfileError("test output is empty")
    try:
        root = ET.fromstring(artifacts["junit.xml"].read_bytes())
    except ET.ParseError as error:
        raise ProfileError(f"malformed JUnit XML: {error}") from None
    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites" and all(child.tag == "testsuite" for child in root):
        suites = list(root)
    else:
        raise ProfileError("expected pytest JUnit testsuite or testsuites root")
    actual = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        if any(child.tag == "testsuite" for child in suite):
            raise ProfileError("nested JUnit suites are unsupported by the recorded pytest contract")
        cases = suite.findall("testcase")
        measured = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        for case in cases:
            statuses = [name for name in ("failure", "error", "skipped") if case.find(name) is not None]
            if len(statuses) > 1 or any(len(case.findall(name)) > 1 for name in ("failure", "error", "skipped")):
                raise ProfileError("ambiguous JUnit testcase status")
            status = {"failure": "failed", "error": "errors", "skipped": "skipped"}.get(statuses[0], "passed") if statuses else "passed"
            measured[status] += 1
        for attribute, value in {"tests": len(cases), "failures": measured["failed"], "errors": measured["errors"], "skipped": measured["skipped"]}.items():
            encoded = suite.get(attribute)
            if encoded is None or re.fullmatch(r"0|[1-9][0-9]*", encoded) is None or int(encoded) != value:
                raise ProfileError(f"JUnit {attribute} counter differs from actual testcase records")
        for key in actual:
            actual[key] += measured[key]
    if actual != tests["counts"]:
        raise ProfileError("test report counts differ from the linked JUnit testcase records")
    return (actual["passed"] > 0 and actual["failed"] == actual["errors"] == actual["skipped"] == 0
            and tests["passed"] is True and tests["exit_code"] == 0
            and all(tests["families"].values()) and tests["source_digest"] == source_digest)


def check_profile(experiment_path: Path) -> dict:
    """Verify linked evidence before applying unchanged v0.3 release gates."""
    from .evidence import verify_integrity
    path = Path(experiment_path)
    experiment = read_json(path)
    keys = {"schema_version", "e0", "e1", "control", "cadence", "replay", "tests", "creator_review", "tuning"}
    _keys(experiment, keys, "experiment")
    if experiment["schema_version"] != "cz-experiment-0.3":
        raise ProfileError("unsupported or malformed experiment manifest")
    _review(experiment["creator_review"])
    _strings(experiment["tuning"], "experiment.tuning")
    refs = {name: _reference(path.parent, experiment[name]) for name in ("e0", "e1", "control", "cadence", "replay", "tests")}
    for name in ("e1", "control"):
        verify_integrity(refs[name])
    e0 = verify_gallery(refs["e0"])
    base, control_base = refs["e1"].parent, refs["control"].parent
    e1_scene = read_json(base / "scene.resolved.json")
    report = profile_metrics(e1_scene, read_jsonl(base / "states.jsonl"), read_jsonl(base / "frames.jsonl"),
                             read_json(control_base / "scene.resolved.json"), read_jsonl(control_base / "states.jsonl"), read_jsonl(control_base / "frames.jsonl"))
    def geometry_mapping(doc):
        selected = deepcopy(doc)
        for key in ("scene_id", "cues", "timeline"):
            selected.pop(key)
        return selected
    report["gates"]["provisional_baseline"] = {"passed": any(geometry_mapping(e1_scene) == geometry_mapping(m) for m in e0["usable_scenes"]), "measured": None}
    cadence, replay, tests = (read_json(refs[k]) for k in ("cadence", "replay", "tests"))
    run = read_json(refs["e1"])
    # Rerun both cadences and the independent scalar/analytic references in the
    # current process. A self-consistent edited report cannot establish a gate.
    fresh_cadence = cadence_study(base / "scene.resolved.json")
    _keys(cadence, set(fresh_cadence), "cadence")
    cadence_pass = (canonical_bytes(cadence) == canonical_bytes(fresh_cadence)
                    and fresh_cadence["passed"] is True
                    and cadence["scene_resolved_sha256"] == run["config"]["resolved_sha256"])
    _keys(replay, {"schema_version", "passed", "original_manifest_sha256", "replayed_manifest_sha256",
                   "comparisons", "environment_match", "source_match"}, "replay")
    _keys(replay["comparisons"], {"states", "decisions", "pixels", "png_files"}, "replay.comparisons")
    for key in ("passed", "environment_match", "source_match"):
        if type(replay[key]) is not bool:
            raise ProfileError(f"replay.{key} must be a boolean")
    if any(type(v) is not bool for v in replay["comparisons"].values()):
        raise ProfileError("replay comparison flags must be booleans")
    for key in ("original_manifest_sha256", "replayed_manifest_sha256"):
        _digest(replay[key], f"replay.{key}")
    comparisons = {"states": True, "decisions": True, "pixels": True, "png_files": True}
    replay_pass = (replay.get("schema_version") == "cz-replay-0.3" and replay.get("passed") is True and replay.get("comparisons") == comparisons and
                   replay.get("environment_match") is True and replay.get("source_match") is True and
                   replay.get("original_manifest_sha256") == experiment["e1"]["sha256"])
    # The replay report is not sufficient alone: independently verify its closed replay run.
    if replay_pass:
        replay_manifest = refs["replay"].parent / "manifest.json"
        replay_pass = replay_manifest.is_file() and sha256(replay_manifest.read_bytes()) == replay.get("replayed_manifest_sha256")
        if replay_pass:
            verify_integrity(replay_manifest)
            regenerated = read_json(replay_manifest)
            replay_pass = (regenerated["environment"] == run["environment"]
                           and regenerated["source"] == run["source"]
                           and regenerated["config"] == run["config"])
            for trace in ("states.jsonl", "decisions.jsonl"):
                replay_pass = replay_pass and (base / trace).read_bytes() == (replay_manifest.parent / trace).read_bytes()
            original_frames, replay_frames = read_jsonl(base / "frames.jsonl"), read_jsonl(replay_manifest.parent / "frames.jsonl")
            replay_pass = replay_pass and [(f["pixel_sha256"], f["file_sha256"]) for f in original_frames] == [(f["pixel_sha256"], f["file_sha256"]) for f in replay_frames]
    tests_pass = _verify_test_report(refs["tests"], tests, run["source"]["digest"])
    for name, value in (("e0", e0["passed"]), ("cadence", cadence_pass), ("replay", replay_pass), ("tests", tests_pass)):
        report["gates"][name] = {"passed": bool(value), "measured": None}
    report.update(schema_version="cz-profile-0.3", passed=all(v["passed"] for v in report["gates"].values()),
                  creator_review=experiment["creator_review"], experiment_sha256=sha256(path.read_bytes()))
    return report


def cadence_study(scene_path: Path, out: Path | None = None) -> dict:
    """Execute independent scalar and analytic comparisons at 60 and 120 Hz.

    Velocity differences are reported separately: v0.3 imposes the cadence
    threshold on positions only. No numerical cadence threshold is invented.
    """
    from .config import resolve_scene
    from .guard import check_transition
    from .motion import propose_step
    from .state import initial_state, owned_state
    scene = load_scene(scene_path)
    mapping = resolved_mapping(scene)
    if mapping["timeline"] != {"sim_hz": 60, "fps_out": 30, "frame_count": 180}:
        raise ProfileError("cadence study requires the nominal E1 60 Hz scene")
    if out is not None:
        out = Path(out)
        if out.exists():
            raise FileExistsError(f"refusing existing cadence report: {out}")
    fast = deepcopy(mapping)
    fast["timeline"]["sim_hz"] = 120
    for cue in fast["cues"]:
        cue["start_tick"] *= 2
        cue["end_tick"] *= 2
    scene120 = resolve_scene(fast)

    def actual(config, initial=None, stop=None):
        state = initial_state(config) if initial is None else initial
        positions, velocities = [state.positions.copy()], [state.velocities.copy()]
        for _ in range(config.terminal_tick if stop is None else stop):
            candidate = propose_step(state, config)
            decision = check_transition(state, candidate, config)
            if decision.status != "ACCEPT":
                raise ProfileError(f"cadence transition rejected at {candidate.tick}")
            state = candidate
            positions.append(state.positions.copy())
            velocities.append(state.velocities.copy())
        return np.asarray(positions), np.asarray(velocities)

    def scalar_reference(config):
        """Separate loops and Python scalar arithmetic; no production cue/update."""
        doc = resolved_mapping(config)
        controls = doc["elements"]
        positions = [[float(v) for v in e["home_xy"]] for e in controls]
        velocities = [[0.0, 0.0] for _ in controls]
        result_p, result_v = [deepcopy(positions)], [deepcopy(velocities)]
        step = 1.0 / doc["timeline"]["sim_hz"]
        for tick in range(config.terminal_tick):
            next_positions, next_velocities = [], []
            for i, element in enumerate(controls):
                force = [0.0, 0.0]
                for cue in doc["cues"]:
                    if cue["group"] != element["group"]:
                        continue
                    fraction = ((tick + 0.5) - cue["start_tick"]) / (cue["end_tick"] - cue["start_tick"])
                    envelope = 0.0
                    if 0 < fraction < 1:
                        envelope = 16.0 * fraction * fraction * (1.0 - fraction) * (1.0 - fraction)
                    for axis in range(2):
                        force[axis] += envelope * cue["force_xy"][axis]
                p, v = [], []
                for axis in range(2):
                    offset = positions[i][axis] - element["home_xy"][axis]
                    acceleration = (-element["spring_k"] * offset - element["damping_c"] * velocities[i][axis] + force[axis]) / element["mass"]
                    velocity = velocities[i][axis] + step * acceleration
                    v.append(velocity)
                    p.append(positions[i][axis] + step * velocity)
                next_positions.append(p)
                next_velocities.append(v)
            positions, velocities = next_positions, next_velocities
            result_p.append(deepcopy(positions))
            result_v.append(deepcopy(velocities))
        return np.asarray(result_p), np.asarray(result_v)

    p60, v60 = actual(scene)
    p120, v120 = actual(scene120)
    ref60p, ref60v = scalar_reference(scene)
    ref120p, ref120v = scalar_reference(scene120)
    common60 = np.arange(0, 361, 2)
    common120 = common60 * 2
    forced_position = float(np.linalg.norm(p60[common60] - p120[common120], axis=2).max())
    forced_velocity = float(np.linalg.norm(v60[common60] - v120[common120], axis=2).max())

    def analytic_error(hz):
        # The documented unforced default m=1,k=14,c=5 test is independent of
        # scene tuning. Every coordinate starts with z=.2,v=0 at tick zero.
        doc = deepcopy(mapping)
        doc["cues"] = []
        doc["timeline"]["sim_hz"] = hz
        for element in doc["elements"]:
            element.update(mass=1.0, spring_k=14.0, damping_c=5.0)
        config = resolve_scene(doc)
        p0 = config.home_xy.copy()
        p0[:, 0] += .2
        initial = owned_state(0, p0, np.zeros_like(p0))
        numerical, _ = actual(config, initial, stop=2 * hz)
        alpha = 2.5
        omega = math.sqrt(14.0 - alpha * alpha)
        expected = np.asarray([.2 * math.exp(-alpha * tick / hz) * (math.cos(omega * tick / hz) + alpha / omega * math.sin(omega * tick / hz)) for tick in range(2 * hz + 1)])
        return float(np.abs((numerical[:, :, 0] - config.home_xy[:, 0]) - expected[:, None]).max())

    analytic60, analytic120 = analytic_error(60), analytic_error(120)
    reference_position = float(max(np.abs(p60 - ref60p).max(), np.abs(p120 - ref120p).max()))
    reference_velocity = float(max(np.abs(v60 - ref60v).max(), np.abs(v120 - ref120v).max()))
    passed = (forced_position <= .01 and analytic60 <= .01 and analytic120 < analytic60 and
              reference_position <= 1e-12 and reference_velocity <= 1e-12)
    report = {"schema_version": "cz-cadence-0.3", "passed": passed,
              "scene_resolved_sha256": sha256(canonical_bytes(mapping)),
              "forced_position_max": forced_position, "forced_velocity_max": forced_velocity,
              "analytic_position_max_60": analytic60, "analytic_position_max_120": analytic120,
              "reference_position_max": reference_position, "reference_velocity_max": reference_velocity,
              "thresholds": {"forced_position_max": .01, "analytic_position_max_60": .01},
              "algorithm": "independent-scalar-reference-v1",
              "common_ticks_60": common60.tolist(), "common_ticks_120": common120.tolist(),
              "analytic_fixture": {"mass": 1.0, "spring_k": 14.0, "damping_c": 5.0,
                                   "initial_displacement": .2, "initial_velocity": 0.0, "duration_seconds": 2}}
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(out, report)
    return report
