"""Local, noninteractive command line for the mathematical Build 0 engine."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import load_scene


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="commander-zorg", description="ZORG Build 0 mathematical renderer")
    commands = result.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="strictly validate a scene without creating outputs")
    validate.add_argument("scene", type=Path)
    gallery = commands.add_parser("gallery", help="render all six explicit E0 presets")
    gallery.add_argument("presets", type=Path)
    gallery.add_argument("--out", required=True, type=Path)
    render = commands.add_parser("render", help="render a complete new run")
    render.add_argument("scene", type=Path)
    render.add_argument("--out", required=True, type=Path)
    verify = commands.add_parser("verify", help="verify integrity or replay in a fresh process")
    verify.add_argument("manifest", type=Path)
    mode = verify.add_mutually_exclusive_group(required=True)
    mode.add_argument("--integrity", action="store_true")
    mode.add_argument("--replay", action="store_true")
    verify.add_argument("--out", type=Path)
    profile = commands.add_parser("check-profile", help="verify linked E0/E1, control, cadence, tests and replay evidence")
    profile.add_argument("experiment", type=Path)
    profile.add_argument("--report", type=Path, help="write a new JSON profile report")
    cadence = commands.add_parser("cadence", help="independent 60/120 Hz and analytic numerical study")
    cadence.add_argument("scene", type=Path)
    cadence.add_argument("--out", required=True, type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "validate":
            scene = load_scene(arguments.scene)
            report = {"valid": True, "scene_id": scene.scene_id, "elements": len(scene.elements),
                      "terminal_tick": scene.terminal_tick}
        elif arguments.command == "render":
            from .evidence import render_run
            report = render_run(load_scene(arguments.scene), arguments.out)
            report = {"completed": True, "manifest": str(arguments.out / "manifest.json")}
        elif arguments.command == "gallery":
            from .experiments import gallery
            result = gallery(arguments.presets, arguments.out)
            report = {"completed": result["status"] == "complete", "passed": result["passed"],
                      "distinct_decoded_images": result["distinct_decoded_images"], "manifest": str(arguments.out / "manifest.json")}
            print(json.dumps(report, allow_nan=False, sort_keys=True))
            return 0 if result["passed"] else 6
        elif arguments.command == "verify":
            from .evidence import verify_integrity, verify_replay
            if arguments.replay:
                if arguments.out is None:
                    raise ValueError("--replay requires --out NEW_REPLAY")
                report = verify_replay(arguments.manifest, arguments.out)
            else:
                if arguments.out is not None:
                    raise ValueError("--out is only used with --replay")
                report = verify_integrity(arguments.manifest)
        elif arguments.command == "cadence":
            from .experiments import cadence_study
            report = cadence_study(arguments.scene, arguments.out)
            print(json.dumps(report, allow_nan=False, sort_keys=True))
            return 0 if report["passed"] else 6
        else:
            from .canonical import atomic_json
            from .experiments import check_profile
            report = check_profile(arguments.experiment)
            if arguments.report is not None:
                if arguments.report.exists():
                    raise FileExistsError(f"refusing existing report: {arguments.report}")
                atomic_json(arguments.report, report)
            print(json.dumps(report, allow_nan=False, sort_keys=True))
            return 0 if report["passed"] else 6
        print(json.dumps(report, allow_nan=False, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        code = getattr(error, "exit_code", 2)
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, allow_nan=False), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
