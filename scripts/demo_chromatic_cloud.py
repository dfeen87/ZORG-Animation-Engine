"""Reproduce the source-bound oval/cloud take, render RGB and verify every frame."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image, ImageDraw
from commander_zorg.canonical import read_json, atomic_json, canonical_bytes, sha256
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.morph_targets import load_targets
from commander_zorg.studio_runtime import StudioRuntime
from commander_zorg.morph_session import MorphRecorder, verify_session
from commander_zorg.morph_export import pixels_for, render_session, verify_export
from commander_zorg.chromatic import encode_rgb_png, ALGORITHM
from commander_zorg.guard import validate_state


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--no-mp4',action='store_true')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    config=read_json(ROOT/'scenes/live_lab.json');config['seed']=172026
    runtime=StudioRuntime(config,load_targets(ROOT/'morph_targets',LiveRuntime(config).scene))
    rec=MorphRecorder(args.out/'record',runtime)
    schedule={0:['color on','palette auto','wander off','morph oval .5',
                 'motion auto on','motion normal','speed normal'],
              178:['capture starting_oval'],180:['morph cloud 2'],
              240:['capture chromatic_midpoint'],300:['capture palette_endpoint'],
              418:['capture sky_blue_cloud'],420:['up'],
              600:['motion bold','up'],780:['up'],838:['capture final_cloud']}
    logs=[];checks=[];maxima={'displacement':0.,'speed':0.,'bias_force':0.}
    samples={178:'starting_oval',210:'transition_25',240:'transition_50',
             270:'transition_75',418:'sky_blue_cloud',838:'final_cloud'}
    images=[];color_checks=[]
    try:
        for tick in range(840):
            for text in schedule.get(tick,[]):
                before=canonical_bytes({'events':runtime.events,'channels':runtime.channels(),
                                        'chromatic':runtime.chromatic.mapping(),
                                        'trace':runtime.trajectory_sha256})
                old=runtime.translation.end.tolist()
                try:
                    event=runtime.accept(text)
                except ValueError as error:
                    if not (tick==780 and text=='up' and 'LIMIT REACHED' in str(error)):
                        raise
                    after=canonical_bytes({'events':runtime.events,'channels':runtime.channels(),
                                           'chromatic':runtime.chromatic.mapping(),
                                           'trace':runtime.trajectory_sha256})
                    assert before==after
                    logs.append({'tick':tick,'input':text,'previous_endpoint':old,
                                 'decision':'limit_reached','message':str(error),'mutated':False})
                else:
                    rec.record_event(event)
                    if text in ('up','motion bold'):
                        logs.append({'tick':tick,'input':text,'previous_endpoint':old,
                                     'decision':'accepted','event':event,
                                     'feedback':runtime.command_feedback(event)})
            state=runtime.state
            assert not validate_state(state,runtime.scene)
            maxima['displacement']=max(maxima['displacement'],float(np.linalg.norm(state.positions-runtime.scene.home_xy,axis=1).max()))
            maxima['speed']=max(maxima['speed'],float(np.linalg.norm(state.velocities,axis=1).max()))
            maxima['bias_force']=max(maxima['bias_force'],float(np.linalg.norm(runtime.target_offsets(tick)*runtime.scene.spring_k[:,None],axis=1).max()))
            if tick in samples:
                gray=pixels_for(state,runtime.scene)
                rgb=runtime.chromatic.rgb(gray,state,runtime.scene,config['seed'],tick)
                again=runtime.chromatic.rgb(gray,state,runtime.scene,config['seed'],tick)
                assert np.array_equal(rgb,again)
                encoded=encode_rgb_png(rgb)
                (args.out/(samples[tick]+'.png')).write_bytes(encoded)
                images.append((samples[tick],tick,Image.fromarray(rgb)))
                color_checks.append({'tick':tick,'rgb_pixels_sha256':sha256(rgb.tobytes()),
                                     'coverage_sha256':sha256(gray.tobytes()),'repeat_identical':True})
            runtime.step()
        session=rec.finish(runtime)
    except BaseException as error:
        rec.finish(runtime,status='failed',reason=str(error));raise
    replay=verify_session(session)
    exported=render_session(session,args.out/'video',mp4=not args.no_mp4)
    integrity=verify_export(args.out/'video/manifest.json')
    sheet=Image.new('RGB',(384*3,414*2),'#18212b');draw=ImageDraw.Draw(sheet)
    for i,(name,tick,img) in enumerate(images):
        x=(i%3)*384;y=(i//3)*414
        sheet.paste(img,(x,y+30));draw.text((x+10,y+8),f'{name.replace("_"," ")} / tick {tick}',fill='white')
    sheet.save(args.out/'contact_sheet.png')
    probe=None
    if exported['media']['status']=='complete':
        process=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
            '-show_entries','stream=codec_name,pix_fmt,nb_read_frames,r_frame_rate',
            '-of','json',str(args.out/'video/animation.mp4')],capture_output=True,text=True,check=True)
        probe=json.loads(process.stdout)
        stream=probe['streams'][0]
        assert stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p'
        assert int(stream['nb_read_frames'])==420 and stream['r_frame_rate']=='30/1'
    report={'baseline_commit':'a0da2378d705449d54eaeb3e73fbf402e873d385',
            'seed':config['seed'],'algorithm':ALGORITHM,'simulation_ticks':840,'states':841,
            'output_frames':420,'setup_preroll_seconds':3,'main_oval_frame_tick':178,
            'cloud_morph':{'start_tick':180,'duration_ticks':120,'seconds':2},
            'movement_log':logs,'numerical_validity':{'passed':True,'states':841,'observed_maxima':maxima,
                'limits':{'displacement':runtime.scene.max_displacement,'speed':runtime.scene.max_speed,'bias_force':runtime.scene.max_total_force}},
            'color_determinism':{'passed':True,'same_input_repeats':color_checks,'wall_clock_used':False},
            'replay':replay,'export':exported,'integrity':integrity,'ffprobe':probe,
            'creator_artistic_acceptance':'pending'}
    atomic_json(args.out/'report.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
