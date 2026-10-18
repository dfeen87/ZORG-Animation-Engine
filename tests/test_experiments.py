"""V12 experiment claims: verify linked facts rather than stored pass flags."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from commander_zorg import evidence, experiments
from commander_zorg.config import load_scene, resolved_mapping


def _json(path):
    return json.loads(Path(path).read_bytes())


def _write(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")


def _ref(base, path):
    return {"path": Path(path).relative_to(base).as_posix(),
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


@pytest.fixture
def test_report(tmp_path):
    xml = (b'<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0">'
           b'<testcase name="independent_one"/><testcase name="independent_two"/>'
           b'</testsuite></testsuites>')
    (tmp_path / "junit.xml").write_bytes(xml)
    (tmp_path / "test-output.txt").write_text("2 passed in 0.10s\n")
    report = {"schema_version": "cz-tests-0.3", "passed": True, "exit_code": 0,
              "families": {f"V{i:02d}": True for i in range(1, 13)},
              "source_digest": "a" * 64, "command": ["python", "-m", "pytest"],
              "summary": "2 passed", "counts": {"passed": 2, "failed": 0, "errors": 0, "skipped": 0},
              "artifacts": {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
                            for name in ("junit.xml", "test-output.txt")}}
    return tmp_path / "tests.json", report


def test_linked_junit_records_are_required_for_a_passing_test_report(test_report):
    path, report = test_report
    assert experiments._verify_test_report(path, report, "a" * 64) is True
    assert experiments._verify_test_report(path, report, "b" * 64) is False


@pytest.mark.parametrize("damage", ["suite_count", "hidden_failure", "report_count", "truncated_xml", "stale_hash"])
def test_junit_counts_and_actual_testcases_cannot_disagree(test_report, damage):
    path, report = test_report
    xml_path = path.parent / "junit.xml"
    payload = xml_path.read_bytes()
    if damage == "suite_count":
        payload = payload.replace(b'tests="2"', b'tests="200"')
    elif damage == "hidden_failure":
        payload = payload.replace(b'name="independent_one"/>', b'name="independent_one"><failure>bad</failure></testcase>')
    elif damage == "report_count":
        report["counts"]["passed"] = 200
    elif damage == "truncated_xml":
        payload = payload[:35]
    else:
        payload += b"\n"
    xml_path.write_bytes(payload)
    if damage != "stale_hash":
        report["artifacts"]["junit.xml"] = hashlib.sha256(payload).hexdigest()
    with pytest.raises(experiments.ProfileError):
        experiments._verify_test_report(path, report, "a" * 64)


@pytest.mark.parametrize("damage", ["exit_bool", "count_bool", "passed_int", "family_int", "unknown", "bad_command"])
def test_test_report_rejects_boolean_numerics_and_unknown_metadata(test_report, damage):
    path, report = test_report
    if damage == "exit_bool":
        report["exit_code"] = False
    elif damage == "count_bool":
        report["counts"]["failed"] = False
    elif damage == "passed_int":
        report["passed"] = 1
    elif damage == "family_int":
        report["families"]["V12"] = 1
    elif damage == "unknown":
        report["unverified_claim"] = True
    else:
        report["command"] = ["python", False]
    with pytest.raises(experiments.ProfileError):
        experiments._verify_test_report(path, report, "a" * 64)


@pytest.fixture(scope="module")
def small_gallery(tmp_path_factory):
    directory = tmp_path_factory.mktemp("small_gallery")
    presets = directory / "presets"
    presets.mkdir()
    for original in sorted((Path(__file__).parents[1] / "scenes/e0").glob("*.json")):
        scene = _json(original)
        scene["raster"].update(width=64, height=64)
        _write(presets / original.name, scene)
    out = directory / "gallery"
    generated = experiments.gallery(presets, out)
    assert generated["passed"] is True
    assert experiments.verify_gallery(out / "manifest.json")["passed"] is True
    return out


@pytest.mark.parametrize("damage", ["unknown", "candidate_unknown", "bool_metric", "review", "status", "count_bool"])
def test_gallery_schema_and_recomputed_claims_are_strict(small_gallery, tmp_path, damage):
    out = tmp_path / "gallery"
    shutil.copytree(small_gallery, out)
    path = out / "manifest.json"
    report = _json(path)
    if damage == "unknown":
        report["extra_claim"] = True
    elif damage == "candidate_unknown":
        report["candidates"][0]["extra_claim"] = True
    elif damage == "bool_metric":
        report["candidates"][0]["metrics"]["field_min"] = False
    elif damage == "review":
        report["creator_review"] = {"status": "accepted", "source": None}
    elif damage == "status":
        _write(out / "run_status.json", {"state": "running"})
        report["artifacts"]["run_status.json"] = hashlib.sha256((out / "run_status.json").read_bytes()).hexdigest()
    else:
        report["distinct_decoded_images"] = True
    _write(path, report)
    with pytest.raises(experiments.ProfileError):
        experiments.verify_gallery(path)


def test_profile_recomputes_cadence_instead_of_trusting_forged_small_errors(tmp_path, monkeypatch):
    # Isolate cadence orchestration from other already-tested release links;
    # the actual 60/120 Hz scalar/analytic study still runs, with no raster work.
    scene_path = tmp_path / "e1/scene.resolved.json"
    scene = resolved_mapping(load_scene(Path(__file__).parents[1] / "scenes/e1.json"))
    _write(scene_path, scene)
    for relative in ("e1/states.jsonl", "e1/frames.jsonl", "control/states.jsonl", "control/frames.jsonl"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    control = copy.deepcopy(scene)
    control.update(scene_id="isolated_control", cues=[])
    _write(tmp_path / "control/scene.resolved.json", control)
    config_hash = hashlib.sha256(scene_path.read_bytes()).hexdigest()
    run = {"config": {"resolved_sha256": config_hash}, "source": {"digest": "a" * 64}}
    _write(tmp_path / "e1/manifest.json", run)
    _write(tmp_path / "control/manifest.json", {})
    _write(tmp_path / "gallery/manifest.json", {})
    cadence = experiments.cadence_study(scene_path)
    assert cadence["passed"] is True
    assert cadence["forced_position_max"] > 0
    cadence["forced_position_max"] = 0.0  # Claimed perfect numerical agreement.
    _write(tmp_path / "cadence.json", cadence)
    _write(tmp_path / "tests.json", {})
    replay = {"schema_version": "cz-replay-0.3", "passed": False,
              "original_manifest_sha256": "a" * 64, "replayed_manifest_sha256": "b" * 64,
              "comparisons": {"states": False, "decisions": False, "pixels": False, "png_files": False},
              "environment_match": False, "source_match": False}
    _write(tmp_path / "replay/replay_report.json", replay)
    experiment = {"schema_version": "cz-experiment-0.3", "creator_review": {"status": "pending", "source": None}, "tuning": []}
    for name, relative in {"e0": "gallery/manifest.json", "e1": "e1/manifest.json", "control": "control/manifest.json",
                           "cadence": "cadence.json", "replay": "replay/replay_report.json", "tests": "tests.json"}.items():
        experiment[name] = _ref(tmp_path, tmp_path / relative)
    _write(tmp_path / "experiment.json", experiment)
    monkeypatch.setattr(evidence, "verify_integrity", lambda path: {"passed": True})
    monkeypatch.setattr(experiments, "verify_gallery", lambda path: {"passed": True, "usable_scenes": [scene]})
    monkeypatch.setattr(experiments, "profile_metrics", lambda *args: {"passed": True, "gates": {}})
    monkeypatch.setattr(experiments, "_verify_test_report", lambda *args: True)
    result = experiments.check_profile(tmp_path / "experiment.json")
    assert result["gates"]["cadence"]["passed"] is False
    assert result["passed"] is False
