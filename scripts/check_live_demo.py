"""Measure the automated live take; artistic approval remains independent.

Usage: python scripts/check_live_demo.py outputs/TAKE/video/manifest.json --report NEW.json
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from commander_zorg.canonical import atomic_json, read_json, read_jsonl
from commander_zorg.live_export import verify_export
from commander_zorg.live_motion import LiveRuntime


def check_demo(manifest):
    manifest = Path(manifest)
    integrity = verify_export(manifest)
    root = manifest.parent
    frames = read_jsonl(root/'frames.jsonl')
    states = read_jsonl(root/'states.jsonl')
    session = read_json(root/'record/session.json')
    events = read_jsonl(root/'record/events.jsonl')
    by_tick = {f['tick']:f['metrics'] for f in frames}
    def aspect(tick):
        x0,y0,x1,y1 = by_tick[tick]['bbox']
        return (y1-y0+1)/(x1-x0+1)
    positions = np.array([s['positions'] for s in states])
    jumps = np.linalg.norm(np.diff(positions,axis=0),axis=2)
    centroids = np.array([f['metrics']['centroid'] for f in frames])
    reference = LiveRuntime(session['config']).scene.home_xy
    metrics = {'right_centroid_delta':by_tick[238]['centroid'][0]-by_tick[120]['centroid'][0],
               'left_centroid_delta':by_tick[478]['centroid'][0]-by_tick[360]['centroid'][0],
               'stretch_aspect_ratio':aspect(358)/aspect(240),
               'squash_aspect_ratio':aspect(598)/aspect(480),
               'distinct_pixel_frames':len({f['pixel_sha256'] for f in frames}),
               'autonomous_distinct_frames':len({f['pixel_sha256'] for f in frames if f['tick']<120}),
               'max_control_step':float(jumps.max()),
               'max_centroid_frame_step':float(np.linalg.norm(np.diff(centroids,axis=0),axis=1).max()),
               'closing_home_error':float(np.linalg.norm(positions[-1]-reference,axis=1).max())}
    gates = {'full_15_seconds':session['final_tick']==900 and len(frames)==450 and len(states)==901,
             'demo_commands':[(e['effective_tick'],e['action']) for e in events]==
                             [(120,'right'),(240,'stretch'),(360,'left'),(480,'squash'),(600,'reset')],
             'autonomous_visible':metrics['autonomous_distinct_frames']>15,
             'right_response':metrics['right_centroid_delta']>.15,
             'left_response':metrics['left_centroid_delta']<-.30,
             'stretch_morphology':metrics['stretch_aspect_ratio']>1.15,
             'squash_morphology':metrics['squash_aspect_ratio']<.75,
             'no_disappearance_or_clipping':all(not f['metrics']['empty'] and not f['metrics']['clipping'] for f in frames),
             'smooth_control_steps':metrics['max_control_step']<.02,
             'smooth_image_centroid':metrics['max_centroid_frame_step']<.03,
             'stable_closing_pose':metrics['closing_home_error']<.005}
    return {'schema_version':'cz-live-demo-check-0.1','passed':all(gates.values()),
            'integrity':integrity,'gates':gates,'measurements':metrics,'creator_review':'pending'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError(f'refusing existing report: {args.report}')
    report = check_demo(args.manifest)
    atomic_json(args.report,report)
    print(report)
    return 0 if report['passed'] else 6


if __name__=='__main__':
    raise SystemExit(main())
