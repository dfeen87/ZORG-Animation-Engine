"""Record and verify a cloud movement with requested-versus-applied evidence."""
import argparse
from pathlib import Path
import sys

# Like other repository study scripts, support direct execution from checkout.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from commander_zorg.canonical import read_json, atomic_json
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_runtime import MorphRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.morph_session import MorphRecorder, verify_session
from commander_zorg.morph_export import render_session, verify_export
from commander_zorg.guard import validate_state

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--render',action='store_true',help='also export full-resolution PNG/HTML (no MP4)')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    config=read_json(ROOT/'scenes/live_lab.json')
    targets=load_targets(ROOT/'morph_targets',LiveRuntime(config).scene)
    runtime=MorphRuntime(config,targets)
    recorder=MorphRecorder(args.out/'record',runtime)
    requested_event=None
    observed_force=observed_displacement=0.
    schedule={0:['morph cloud .5'],180:['capture before','motion auto on','up'],538:['capture after']}
    try:
        for tick in range(540):
            for text in schedule.get(tick,[]):
                before=runtime.channels()
                event=runtime.accept(text);recorder.record_event(event)
                if text=='up':
                    requested_event=event
                    for k in ('shape','morph','wander_mix'):
                        assert runtime.channels()[k]==before[k]
                    assert runtime.active_target=='cloud' and runtime.wander
                    feedback=runtime.command_feedback(event)
                    (args.out/'feedback.txt').write_text(feedback+'\n')
            observed_force=max(observed_force,float(np.linalg.norm(
                runtime.target_offsets(tick)*runtime.scene.spring_k[:,None],axis=1).max()))
            runtime.step()
            assert not validate_state(runtime.state,runtime.scene)
            observed_displacement=max(observed_displacement,float(np.linalg.norm(
                runtime.state.positions-runtime.scene.home_xy,axis=1).max()))
        session=recorder.finish(runtime)
    except BaseException as error:
        recorder.finish(runtime,status='failed',reason=str(error))
        raise
    report={'event':requested_event,'feedback':feedback,'shape':'cloud','wander_preserved':True,
        'max_observed_force':observed_force,'max_observed_displacement':observed_displacement,
        'force_limit':runtime.scene.max_total_force,'displacement_limit':runtime.scene.max_displacement,
        'session_sha256':read_json(session)['session_sha256'],
        'replay':verify_session(session),'creator_review':'pending'}
    if args.render:
        report['export']=render_session(session,args.out/'video',mp4=False)
        report['export_verification']=verify_export(args.out/'video/manifest.json')
    atomic_json(args.out/'report.json',report)
    print(feedback)
    print('Exact replay verified; report:',args.out/'report.json')


if __name__=='__main__':main()
