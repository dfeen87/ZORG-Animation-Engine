"""Local Build 0 renderer and separately versioned Live Morph Lab commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import load_scene


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="commander-zorg", description="ZORG mathematical renderer and Live Morph Lab")
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
    live = commands.add_parser("live", help="interactive terminal Live Morph Lab")
    live.add_argument("--scene", type=Path, default=Path(__file__).resolve().parent.parent/"scenes/live_lab.json")
    live.add_argument("--seed", type=int)
    live.add_argument("--record", required=True, type=Path)
    live.add_argument("--mono", action="store_true", help="force monochrome terminal rendering")
    live.add_argument("--preview-fps", type=float, default=15.)
    live.add_argument("--max-seconds", type=float, help="optional simulation duration limit")
    live.add_argument("--no-mp4", action="store_true", help="use PNG/HTML export only on save")
    demo = commands.add_parser("live-demo", help="record and export the 15-second command demonstration")
    demo.add_argument("--scene", type=Path, default=Path(__file__).resolve().parent.parent/"scenes/live_lab.json")
    demo.add_argument("--seed", type=int)
    demo.add_argument("--out", required=True, type=Path)
    demo.add_argument("--no-mp4", action="store_true")
    session = commands.add_parser("render-session", help="replay a live session into full-resolution media")
    session.add_argument("session", type=Path)
    session.add_argument("--out", required=True, type=Path)
    session.add_argument("--no-mp4", action="store_true")
    replay = commands.add_parser("verify-session", help="check live recording integrity and exact numerical replay")
    replay.add_argument("session", type=Path)
    export = commands.add_parser("verify-live-export", help="check live export artifacts and timeline")
    export.add_argument("manifest", type=Path)
    for name in ('morph-lab','morph-demo'):
        morph = commands.add_parser(name, help='versioned position-only semantic morph extension')
        morph.add_argument('--scene', type=Path, default=Path(__file__).resolve().parent.parent/'scenes/live_lab.json')
        morph.add_argument('--targets', type=Path, default=Path(__file__).resolve().parent.parent/'morph_targets')
        morph.add_argument('--seed', type=int)
        morph.add_argument('--no-mp4', action='store_true')
        if name == 'morph-lab':
            morph.add_argument('--record', required=True, type=Path)
            morph.add_argument('--mono', action='store_true')
            morph.add_argument('--preview-fps', type=float, default=15.)
            morph.add_argument('--max-seconds', type=float)
        else:
            morph.add_argument('--out', required=True, type=Path)
    for name in ('verify-morph-session','render-morph-session','verify-morph-export'):
        morph = commands.add_parser(name, help='verify or export versioned morph evidence')
        morph.add_argument('path', type=Path)
        if name == 'render-morph-session':
            morph.add_argument('--out', required=True, type=Path)
            morph.add_argument('--no-mp4', action='store_true')
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command in ('morph-lab','morph-demo'):
            from .canonical import read_json
            from .live_motion import LiveRuntime
            from .morph_targets import load_targets
            from .morph_lab import run_lab, run_demo
            config = read_json(arguments.scene)
            if arguments.seed is not None:
                config['seed'] = arguments.seed
            targets = load_targets(arguments.targets, LiveRuntime(config).scene)
            if arguments.command == 'morph-demo':
                report = run_demo(config, targets, arguments.out, mp4=not arguments.no_mp4)
            else:
                report = run_lab(config, targets, arguments.record, mono=arguments.mono,
                    preview_fps=arguments.preview_fps, max_seconds=arguments.max_seconds)
                if report['save_requested']:
                    from .morph_export import render_session
                    report['export'] = render_session(report['session'], arguments.record/'export', mp4=not arguments.no_mp4)
        elif arguments.command == 'verify-morph-session':
            from .morph_session import verify_session
            report = verify_session(arguments.path)
        elif arguments.command == 'render-morph-session':
            from .morph_export import render_session
            report = render_session(arguments.path, arguments.out, mp4=not arguments.no_mp4)
        elif arguments.command == 'verify-morph-export':
            from .morph_export import verify_export
            report = verify_export(arguments.path)
        elif arguments.command in ("live", "live-demo"):
            from .canonical import read_json
            config = read_json(arguments.scene)
            if arguments.seed is not None:
                config['seed'] = arguments.seed
            if arguments.command == 'live-demo':
                from .live_demo import run_demo
                report = run_demo(config,arguments.out,mp4=not arguments.no_mp4)
            else:
                from .live import run_live
                report = run_live(config,arguments.record,mono=arguments.mono,
                                  preview_fps=arguments.preview_fps,max_seconds=arguments.max_seconds)
                if report['save_requested']:
                    from .live_export import render_session
                    export = render_session(Path(report['session']),arguments.record/'export',mp4=not arguments.no_mp4)
                    report['export_manifest'] = str(arguments.record/'export/manifest.json')
                    report['media'] = export['media']
        elif arguments.command == 'render-session':
            from .live_export import render_session
            report = render_session(arguments.session,arguments.out,mp4=not arguments.no_mp4)
        elif arguments.command == 'verify-session':
            from .session import verify_session
            report = verify_session(arguments.session)
        elif arguments.command == 'verify-live-export':
            from .live_export import verify_export
            report = verify_export(arguments.manifest)
        elif arguments.command == "validate":
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
    except KeyboardInterrupt:
        print(json.dumps({"error":"KeyboardInterrupt","message":"interrupted; partial evidence retained"}),file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as error:
        code = getattr(error, "exit_code", 2)
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, allow_nan=False), file=sys.stderr)
        return code


if __name__ == "__main__":
    raise SystemExit(main())
