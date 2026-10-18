"""Reproduce the complete Build 0 evidence in a fresh, nonoverwritten directory.

Run from the checkout after installing its locked dependencies and package:
    python scripts/run_build0.py --out outputs/build0_take_01
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from commander_zorg.canonical import atomic_json, atomic_write, canonical_bytes, sha256
from commander_zorg.config import load_scene
from commander_zorg.evidence import render_run, source_digest, verify_integrity, verify_replay
from commander_zorg.experiments import cadence_study, check_profile, gallery


FAMILIES = {
    "V01": ("test_config",), "V02": ("test_state", "test_evidence"),
    "V03": ("test_field",), "V04": ("test_raster",),
    "V05": ("test_motion", "test_state"), "V06": ("test_motion",),
    "V07": ("test_guard", "test_evidence"), "V08": ("test_profiles",),
    "V09": ("test_profiles", "test_raster"), "V10": ("test_evidence",),
    "V11": ("test_replay",), "V12": ("test_evidence",),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    out = args.out.absolute()
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    operations = {}

    def measured(name, function, *arguments):
        begin = time.perf_counter()
        try:
            return function(*arguments)
        finally:
            operations[name] = time.perf_counter() - begin

    atomic_json(out / "experiment_status.json", {"state": "running"})
    try:
        print("Running independent V01–V12 tests", flush=True)
        testdir = out / "tests"
        testdir.mkdir()
        command = [sys.executable, "-m", "pytest", "-q", "--junitxml", str(testdir / "junit.xml")]
        result = subprocess.run(command, cwd=project, capture_output=True, text=True, check=False)
        atomic_write(testdir / "test-output.txt", (result.stdout + result.stderr).encode())
        xml = ET.parse(testdir / "junit.xml")
        cases = list(xml.iter("testcase"))
        counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        modules = {}
        for case in cases:
            outcome = ("failed" if case.find("failure") is not None else
                       "errors" if case.find("error") is not None else
                       "skipped" if case.find("skipped") is not None else "passed")
            counts[outcome] += 1
            name = case.attrib.get("classname", "").split(".")[-1]
            modules.setdefault(name, []).append(outcome)
        families = {key: all(module in modules and all(s == "passed" for s in modules[module])
                             for module in names) for key, names in FAMILIES.items()}
        passed = result.returncode == 0 and counts["passed"] > 0 and not any(
            counts[k] for k in ("failed", "errors", "skipped")) and all(families.values())
        test_report = {"schema_version": "cz-tests-0.3", "passed": passed,
                       "exit_code": result.returncode, "families": families,
                       "source_digest": source_digest(),
                       "command": command,
                       "summary": f"{counts['passed']} passed; {counts['failed']} failed; "
                                  f"{counts['errors']} errors; {counts['skipped']} skipped",
                       "counts": counts,
                       "artifacts": {name: sha256((testdir / name).read_bytes())
                                     for name in ("junit.xml", "test-output.txt")}}
        atomic_json(testdir / "test_report.json", test_report)
        if not passed:
            raise RuntimeError(f"tests did not pass: {test_report['summary']}")
        print(test_report["summary"], flush=True)
        print("Rendering six E0 candidates", flush=True)
        e0 = measured("e0_wall_s", gallery, project / "scenes/e0", out / "e0")
        if not e0["passed"]:
            raise RuntimeError("E0 failed; all candidate evidence retained")
        print("Rendering E1 (180 frames; 361 states)", flush=True)
        measured("e1_wall_s", render_run, load_scene(project / "scenes/e1.json"), out / "e1")
        print("Rendering independent cue-off control (180 frames)", flush=True)
        measured("control_wall_s", render_run, load_scene(project / "scenes/control.json"), out / "control")
        print("Independent numerical cadence and analytic study", flush=True)
        measured("cadence_wall_s", cadence_study, project / "scenes/e1.json", out / "cadence.json")
        print("Fresh-process exact replay", flush=True)
        measured("replay_wall_s", verify_replay, out / "e1/manifest.json", out / "replay")

        def ref(relative):
            return {"path": relative, "sha256": sha256((out / relative).read_bytes())}

        experiment = {"schema_version": "cz-experiment-0.3", "e0": ref("e0/manifest.json"),
                      "e1": ref("e1/manifest.json"), "control": ref("control/manifest.json"),
                      "cadence": ref("cadence.json"), "replay": ref("replay/replay_report.json"),
                      "tests": ref("tests/test_report.json"),
                      "creator_review": {"status": "pending", "source": None},
                      "tuning": ["Exact v0.3 E1 seed, unchanged; provisional E0 seed geometry.",
                                 "Six explicit E0 home/sigma variants: docs/scene-decisions.md."]}
        atomic_json(out / "experiment_manifest.json", experiment)
        print("Cross-file integrity and complete experiment profile", flush=True)
        profile = measured("profile_wall_s", check_profile, out / "experiment_manifest.json")
        atomic_json(out / "profile_report.json", profile)
        for name in ("e1", "control", "replay"):
            atomic_json(out / f"{name}_integrity.json", verify_integrity(out / name / "manifest.json"))
        if not profile["passed"]:
            raise RuntimeError("experiment profile failed; retained full measured report")
        atomic_json(out / "operation_timings.json", {"method": "perf_counter around actual API call, including public integrity verification",
                                                   "seconds": operations})
        atomic_json(out / "experiment_status.json", {"state": "complete", "automated_gates": "passed",
                                                    "creator_review": "pending",
                                                    "operation_timings_sha256": sha256((out / "operation_timings.json").read_bytes()),
                                                    "wall_s": time.perf_counter() - start})
        print(f"Automated Build 0 gates passed; creator review pending. Evidence: {out}", flush=True)
        return 0
    except Exception as error:
        atomic_json(out / "experiment_status.json", {"state": "failed", "error": str(error),
                                                    "wall_s": time.perf_counter() - start})
        print(f"Build 0 incomplete: {error}", file=sys.stderr, flush=True)
        return getattr(error, "exit_code", 1)


if __name__ == "__main__":
    raise SystemExit(main())
