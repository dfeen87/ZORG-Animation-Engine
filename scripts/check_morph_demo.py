"""Audit the 20-second morph film; creator artistic approval stays pending."""
from pathlib import Path
import argparse
import numpy as np
from commander_zorg.canonical import read_json,read_jsonl,atomic_json
from commander_zorg.morph_export import verify_export,metrics_for,pixels_for,load_capture
from commander_zorg.morph_session import load_session
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.state import owned_state
from commander_zorg.raster import geometry_mask,aligned_iou


def check_demo(manifest):
    manifest=Path(manifest); root=manifest.parent
    integrity=verify_export(manifest)
    doc=load_session(root/'session.json'); runtime=MorphRuntime(doc['config'],doc['targets'])
    frames=read_jsonl(root/'frames.jsonl'); rows=read_jsonl(root/'states.jsonl')
    per_target={}; masks={}; gates={}
    for capture in doc['captures']:
        name=capture['label']
        curated,state=load_capture(root/'captures'/f'{name}.json',doc['config'])
        target='home' if name in ('original','returned_home') else name
        expected=runtime.scene.home_xy+np.array(runtime.targets[target]['offsets'])
        pixels=pixels_for(state,runtime.scene); metrics=metrics_for(pixels,runtime.scene)
        masks[name]=geometry_mask(pixels,runtime.scene)
        error=float(np.linalg.norm(state.positions-expected,axis=1).max())
        metrics.update(tick=state.tick,max_target_position_error=error,
            assessment='numerically valid; creator review pending')
        per_target[name]=metrics
        if name!='original': gates[f'{name}_settled_within_two_pixels']=error<2*(2/runtime.scene.height)
    gates.update(full_sequence=doc['final_tick']==1200 and len(frames)==600 and len(rows)==1201,
        capture_order=[c['label'] for c in doc['captures']]==['original','circle','oval','cloud','hill','returned_home'],
        no_empty_or_clipped_frames=all(not f['metrics']['empty'] and not f['metrics']['clipping'] for f in frames),
        connected_frames=all(f['metrics']['components_4_connected']==1 for f in frames),
        circle_round=abs(per_target['circle']['aspect_width_height']-1)<.04,
        oval_elongated=per_target['oval']['aspect_width_height']<.65,
        cloud_upper_lobes=per_target['cloud']['upper_lobes']>=3,
        hill_broad=per_target['hill']['aspect_width_height']>1.6)
    differences={f'{a}:{b}':aligned_iou(masks[a],masks[b]) for a in ('circle','oval','cloud','hill') for b in ('circle','oval','cloud','hill') if a<b}
    # Less than .90 excludes nearly identical masks, not semantic proof.
    gates['pairwise_distinct']=all(value<.90 for value in differences.values())
    measurements=read_json(root/'measurements.json')
    gates['bounded_control_steps']=measurements['max_control_step']<runtime.scene.max_speed/60
    gates['small_centroid_frame_steps']=measurements['max_centroid_frame_step']<.03
    return {'schema_version':'cz-morph-demo-check-0.1','passed':all(gates.values()),'gates':gates,
        'integrity':integrity,'per_target':per_target,'pairwise_aligned_iou':differences,
        'continuity':measurements,'performance':doc['metrics'],'creator_review':'pending',
        'tolerance_rationale':'Endpoint error < two 384px world pixels after spring settling. Circle bbox aspect within 4%; oval width/height < .65; hill >1.6. Cloud >=3 upper-contour peaks after fixed nine-column smoothing. Pairwise aligned IoU < .90 excludes near duplicates. These measure geometry, not artistic meaning.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path);parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args()
    if args.report.exists(): raise FileExistsError('report must be new')
    report=check_demo(args.manifest);atomic_json(args.report,report)
    print(report)
    raise SystemExit(0 if report['passed'] else 6)
