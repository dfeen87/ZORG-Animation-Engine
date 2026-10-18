"""Full-resolution exports from exact replay, including mathematical captures."""
from pathlib import Path
import time
import numpy as np
from PIL import Image,ImageDraw
from .canonical import atomic_json,atomic_write,canonical_bytes,read_json,read_jsonl,sha256
from .field import evaluate_samples
from .raster import rasterize,measure_mask,encode_gray_png,geometry_mask
from .live_export import _player,_encode_mp4
from .morph_session import load_session,replay_runtimes
from .state import state_mapping,owned_state
from .chromatic import ALGORITHM,ChromaticState,encode_rgb_png


def pixels_for(state,scene):
    return rasterize(evaluate_samples(state,scene),scene)


def component_count(mask):
    """Four-connected components via row spans, without an extra dependency."""
    parents=[]
    def find(a):
        while parents[a]!=a:
            parents[a]=parents[parents[a]]; a=parents[a]
        return a
    previous=[]
    for row in mask:
        edges=np.diff(np.r_[False,row,False].astype(np.int8))
        current=[]
        for left,right in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1),strict=True):
            number=len(parents); parents.append(number)
            for a,b,old in previous:
                if a<right and left<b:
                    parents[find(number)]=find(old)
            current.append((left,right,number))
        previous=current
    return len({find(i) for i in range(len(parents))})


def metrics_for(pixels,scene):
    result=measure_mask(pixels,scene)
    mask=geometry_mask(pixels,scene)
    box=result['bbox']
    result['area_pixels']=int(mask.sum())
    result['components_4_connected']=component_count(mask)
    result['width']=0 if box is None else box[2]-box[0]+1
    result['height']=0 if box is None else box[3]-box[1]+1
    result['aspect_width_height']=None if box is None else result['width']/result['height']
    union=np.count_nonzero(mask | mask[:,::-1])
    result['horizontal_symmetry_iou']=None if not union else float(np.count_nonzero(mask & mask[:,::-1])/union)
    # Number of discrete local maxima of the upper silhouette, after a fixed
    # nine-pixel moving mean; diagnostic, not a semantic recognizer.
    if box is not None:
        cols=np.arange(box[0],box[2]+1)
        top=np.array([np.flatnonzero(mask[:,x])[0] for x in cols if mask[:,x].any()],dtype=float)
        smooth=np.convolve(top,np.ones(9)/9,mode='valid') if len(top)>=9 else top
        signs=np.sign(np.diff(smooth)); signs=signs[signs!=0]
        result['upper_lobes']=int(np.count_nonzero((signs[:-1]<0)&(signs[1:]>0)))
    else:
        result['upper_lobes']=0
    return result


def _append(path,row):
    with path.open('ab') as stream:
        stream.write(canonical_bytes(row))


def _artifacts(root):
    return {p.relative_to(root).as_posix():sha256(p.read_bytes()) for p in sorted(root.rglob('*'))
            if p.is_file() and p!=root/'manifest.json'}


def _color_requested(doc,color):
    if color is not None and type(color) is not bool:
        raise ValueError('color export selection must be boolean or None')
    if color is None:
        operations=[]
        for event in doc['events']:
            command=event.get('command')
            if type(command) is not dict:
                raise ValueError('invalid morph command for color export selection')
            operation=command.get('operation',command)
            if type(operation) is not dict:
                raise ValueError('invalid morph operation for color export selection')
            operations.append(operation)
        color=any(operation.get('action')=='color' and operation.get('enabled') is True
                  for operation in operations)
    if color and doc['schema_version']!='cz-morph-session-0.3':
        raise ValueError('RGB export requires a version 0.3 studio session')
    return color


def _presentation(seed):
    return {'mode':'rgb','algorithm':ALGORITHM,'seed':seed}


def _state_row(runtime,color):
    row={'state':state_mapping(runtime.state),'channels':runtime.channels(),'active_target':runtime.active_target}
    if color:
        row['chromatic']=runtime.chromatic.mapping()
    return row


def _capture_pixels(capture,scene,color):
    state=owned_state(capture['tick'],capture['state']['positions'],capture['state']['velocities'])
    coverage=pixels_for(state,scene)
    if not color:
        return coverage
    if capture['schema_version']!='cz-morph-capture-0.3':
        raise ValueError('RGB preview requires a chromatic capture snapshot')
    chromatic=ChromaticState.from_mapping(capture['chromatic'])
    return chromatic.rgb(coverage,state,scene,capture['seed'],capture['tick'])


def _capture_document(capture,encoded,color):
    doc={'capture':capture,'preview_sha256':sha256(encoded)}
    if color:
        doc['presentation']=_presentation(capture['seed'])
    return doc


def _contact_sheet(scene,selected):
    sheet=Image.new('RGB',(scene.width*len(selected),scene.height+30),'#222222')
    draw=ImageDraw.Draw(sheet)
    for i,(tick,target,img) in enumerate(selected):
        sheet.paste(img,(i*scene.width,30))
        draw.text((i*scene.width+8,8),f'tick {tick}: {target}',fill='white')
    return encode_rgb_png(np.asarray(sheet))


def render_session(path,out,mp4=True,color=None):
    doc=load_session(path)
    color=_color_requested(doc,color)
    encode=encode_rgb_png if color else encode_gray_png
    root=Path(out); root.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    atomic_json(root/'status.json',{'state':'running'})
    try:
        atomic_json(root/'session.json',doc)
        (root/'frames').mkdir(); (root/'captures').mkdir()
        (root/'states.jsonl').touch(); (root/'frames.jsonl').touch()
        frame=0; previous=None; max_control_step=0.; max_centroid_step=0.; last_center=None
        selected=[]; captured=set(); scene=None
        for runtime in replay_runtimes(root/'session.json'):
            scene=runtime.scene; state=runtime.state
            _append(root/'states.jsonl',_state_row(runtime,color))
            if previous is not None:
                max_control_step=max(max_control_step,float(np.linalg.norm(state.positions-previous,axis=1).max()))
            previous=state.positions.copy()
            for capture in runtime.captures:
                if capture['id'] in captured: continue
                captured.add(capture['id'])
                name=capture['label']
                pixels=_capture_pixels(capture,scene,color)
                encoded=encode(pixels)
                atomic_write(root/'captures'/f'{name}.png',encoded)
                atomic_json(root/'captures'/f'{name}.json',_capture_document(capture,encoded,color))
            if state.tick<doc['final_tick'] and state.tick%2==0:
                coverage=pixels_for(state,scene); metrics=metrics_for(coverage,scene)
                pixels=runtime.chromatic.rgb(coverage,state,scene,runtime.config['seed'],state.tick) if color else coverage
                if metrics['empty'] or metrics['clipping']:
                    raise ValueError(f'empty or clipped morph frame at tick {state.tick}')
                center=np.array(metrics['centroid'])
                if last_center is not None: max_centroid_step=max(max_centroid_step,float(np.linalg.norm(center-last_center)))
                last_center=center
                relative=f'frames/frame_{frame:06d}.png'; encoded=encode(pixels)
                atomic_write(root/relative,encoded)
                frame_row={'index':frame,'tick':state.tick,'path':relative,
                    'sha256':sha256(encoded),'pixels_sha256':sha256(pixels.tobytes()),'metrics':metrics,'active_target':runtime.active_target}
                if color:
                    frame_row.update(coverage_sha256=sha256(coverage.tobytes()),chromatic=runtime.chromatic.mapping())
                _append(root/'frames.jsonl',frame_row)
                # Same-scale contact sheet samples immediately before demo changes.
                if state.tick in (0,178,358,538,778,958,1198):
                    selected.append((state.tick,runtime.active_target,Image.fromarray(pixels).convert('RGB')))
                frame+=1
        if not selected:
            coverage=pixels_for(runtime.state,scene)
            pixels=runtime.chromatic.rgb(coverage,runtime.state,scene,runtime.config['seed'],runtime.state.tick) if color else coverage
            selected=[(runtime.state.tick,runtime.active_target,Image.fromarray(pixels).convert('RGB'))]
        atomic_write(root/'contact_sheet.png',_contact_sheet(scene,selected))
        atomic_write(root/'player.html',_player(frame,30).replace(b'ZORG Live Morph Lab',b'ZORG Semantic Morph Lab'))
        media=_encode_mp4(root,frame,30,mp4)
        atomic_json(root/'measurements.json',{'max_control_step':max_control_step,'max_centroid_frame_step':max_centroid_step,
            'simulation_hz':60,'output_fps':30,'creator_review':'pending'})
        atomic_json(root/'status.json',{'state':'complete','frames':frame,'final_tick':doc['final_tick']})
        manifest={'schema_version':'cz-morph-export-0.1','status':'complete','session_sha256':doc['session_sha256'],
            'frames':frame,'states':doc['final_tick']+1,'final_tick':doc['final_tick'],
            'trajectory_sha256':doc['trajectory_sha256'],'media':media,'creator_review':'pending',
            'elapsed_seconds':time.perf_counter()-started,'artifacts':_artifacts(root)}
        if color:
            manifest.update(schema_version='cz-morph-export-0.3',presentation=_presentation(doc['config']['seed']))
        atomic_json(root/'manifest.json',manifest)
        return {'passed':True,'frames':frame,'states':doc['final_tick']+1,'manifest':str(root/'manifest.json'),'media':media}
    except BaseException as error:
        atomic_json(root/'status.json',{'state':'failed','error':type(error).__name__,'message':str(error)})
        raise


def verify_export(path):
    path=Path(path); root=path.parent; manifest=read_json(path)
    keys={'schema_version','status','session_sha256','frames','states','final_tick','trajectory_sha256','media','creator_review','elapsed_seconds','artifacts'}
    color=type(manifest) is dict and manifest.get('schema_version')=='cz-morph-export-0.3'
    if color:
        keys.add('presentation')
    if path.name!='manifest.json' or path.is_symlink() or type(manifest) is not dict or set(manifest)!=keys or manifest['schema_version'] not in ('cz-morph-export-0.1','cz-morph-export-0.3') or manifest['status']!='complete':
        raise ValueError('invalid/incomplete morph export')
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('symlink export artifact refused')
    # Compare inventory without following any manifest-supplied path.
    if manifest['artifacts']!=_artifacts(root):
        raise ValueError('morph export artifact integrity mismatch')
    doc=load_session(root/'session.json')
    _color_requested(doc,color)
    encode=encode_rgb_png if color else encode_gray_png
    if color and canonical_bytes(manifest['presentation'])!=canonical_bytes(_presentation(doc['config']['seed'])):
        raise ValueError('incompatible RGB presentation metadata')
    if (manifest['session_sha256']!=doc['session_sha256'] or manifest['final_tick']!=doc['final_tick']
        or manifest['trajectory_sha256']!=doc['trajectory_sha256'] or manifest['creator_review']!='pending'):
        raise ValueError('export/session binding mismatch')
    rows=read_jsonl(root/'states.jsonl'); frames=read_jsonl(root/'frames.jsonl')
    expected=(doc['final_tick']+1)//2
    if manifest['frames']!=expected or len(frames)!=expected or manifest['states']!=doc['final_tick']+1 or len(rows)!=doc['final_tick']+1:
        raise ValueError('export timeline count mismatch')
    previous=None; max_control_step=0.; max_centroid_step=0.; last_center=None; selected=[]
    for runtime in replay_runtimes(root/'session.json'):
        state=runtime.state; tick=state.tick; scene=runtime.scene
        if previous is not None:
            max_control_step=max(max_control_step,float(np.linalg.norm(state.positions-previous,axis=1).max()))
        previous=state.positions.copy()
        expected_row=_state_row(runtime,color)
        if canonical_bytes(rows[tick])!=canonical_bytes(expected_row):
            raise ValueError('saved intermediate state/channel differs from replay')
        if tick<doc['final_tick'] and tick%2==0:
            index=tick//2; relative=f'frames/frame_{index:06d}.png'; coverage=pixels_for(state,scene)
            pixels=runtime.chromatic.rgb(coverage,state,scene,runtime.config['seed'],tick) if color else coverage
            encoded=encode(pixels); metrics=metrics_for(coverage,scene)
            expected_frame={'index':index,'tick':tick,'path':relative,'sha256':sha256(encoded),
                'pixels_sha256':sha256(pixels.tobytes()),'metrics':metrics,'active_target':runtime.active_target}
            if color:
                expected_frame.update(coverage_sha256=sha256(coverage.tobytes()),chromatic=runtime.chromatic.mapping())
            if canonical_bytes(frames[index])!=canonical_bytes(expected_frame) or (root/relative).read_bytes()!=encoded:
                raise ValueError('frame/metrics/chronology differs from mathematical replay')
            if color and tick in (0,178,358,538,778,958,1198):
                selected.append((tick,runtime.active_target,Image.fromarray(pixels)))
            if metrics['empty'] or metrics['clipping']:
                raise ValueError('invalid silhouette')
            center=np.array(metrics['centroid'])
            if last_center is not None: max_centroid_step=max(max_centroid_step,float(np.linalg.norm(center-last_center)))
            last_center=center
    if color:
        if not selected:
            coverage=pixels_for(runtime.state,scene)
            pixels=runtime.chromatic.rgb(coverage,runtime.state,scene,runtime.config['seed'],runtime.state.tick)
            selected=[(runtime.state.tick,runtime.active_target,Image.fromarray(pixels))]
        if (root/'contact_sheet.png').read_bytes()!=_contact_sheet(scene,selected):
            raise ValueError('RGB contact sheet differs from replay')
    measurements={'max_control_step':max_control_step,'max_centroid_frame_step':max_centroid_step,
        'simulation_hz':60,'output_fps':30,'creator_review':'pending'}
    if canonical_bytes(read_json(root/'measurements.json'))!=canonical_bytes(measurements):
        raise ValueError('continuity measurements differ from replay')
    media=manifest['media']
    if type(media) is not dict or media.get('status') not in ('complete','failed','disabled','unavailable','no_frames'):
        raise ValueError('invalid optional MP4 status')
    if media['status']=='complete':
        expected_media={'status':'complete','path':'animation.mp4','codec':'h264','pixel_format':'yuv420p',
            'fps':30,'frames':expected,'log':'encoder.log'}
        if media!=expected_media or not expected or b'ftyp' not in (root/'animation.mp4').read_bytes()[:64]:
            raise ValueError('invalid MP4 container/metadata')
    elif (root/'animation.mp4').exists():
        raise ValueError('unreported MP4 artifact')
    for capture in doc['captures']:
        name=capture['label']
        encoded=encode(_capture_pixels(capture,scene,color))
        expected_capture=_capture_document(capture,encoded,color)
        if (read_json(root/'captures'/f'{name}.json')!=expected_capture or (root/'captures'/f'{name}.png').read_bytes()!=encoded):
            raise ValueError('capture state or preview differs from replay')
    if read_json(root/'status.json')!={'state':'complete','frames':expected,'final_tick':doc['final_tick']}:
        raise ValueError('incomplete export status')
    if (root/'player.html').read_bytes()!=_player(expected,30).replace(b'ZORG Live Morph Lab',b'ZORG Semantic Morph Lab'):
        raise ValueError('player differs')
    return {'passed':True,'frames':expected,'states':len(rows),'captures':len(doc['captures']),'exact_replay':True}


def load_capture(path,config):
    """Reload a curated mathematical state; never infer a recipe from its label."""
    from .guard import validate_state
    from .live_motion import LiveRuntime
    from .session import engine_sources
    from .morph_targets import label
    path=Path(path)
    if path.is_symlink(): raise ValueError('symlink capture refused')
    doc=read_json(path)
    if type(doc) is not dict or set(doc) not in ({'capture','preview_sha256'}, {'capture','preview_sha256','presentation'}):
        raise ValueError('invalid capture document')
    capture=doc['capture']
    keys={'schema_version','label','tick','active_target','state','channels','seed',
        'config_sha256','source_sha256','field','validation','id'}
    chromatic=type(capture) is dict and capture.get('schema_version')=='cz-morph-capture-0.3'
    if chromatic:
        keys.add('chromatic')
    if type(capture) is not dict or set(capture)!=keys or capture['schema_version'] not in ('cz-morph-capture-0.1','cz-morph-capture-0.3'):
        raise ValueError('invalid capture contract')
    if chromatic:
        ChromaticState.from_mapping(capture['chromatic'])
    color='presentation' in doc
    if color and (not chromatic or canonical_bytes(doc['presentation'])!=canonical_bytes(_presentation(capture['seed']))):
        raise ValueError('incompatible capture presentation metadata')
    label(capture['label'])
    if path.stem!=capture['label'] or capture['id']!=sha256(canonical_bytes({k:v for k,v in capture.items() if k!='id'})):
        raise ValueError('capture ID/label mismatch')
    runtime=LiveRuntime(config)
    if (capture['source_sha256']!=sha256(canonical_bytes(engine_sources())) or
        capture['config_sha256']!=sha256(canonical_bytes(runtime.config)) or capture['seed']!=runtime.config['seed']):
        raise ValueError('capture provenance differs')
    state=owned_state(capture['tick'],capture['state']['positions'],capture['state']['velocities'])
    expected_field={'threshold':runtime.scene.threshold,'elements':[
        {'id':e.id,'sigma':e.sigma,'weight':e.weight} for e in runtime.scene.elements]}
    if (capture['state']!=state_mapping(state) or validate_state(state,runtime.scene)
        or capture['validation']!='passed' or capture['field']!=expected_field):
        raise ValueError('invalid captured mathematical state')
    pixels=_capture_pixels(capture,runtime.scene,color)
    encoded=encode_rgb_png(pixels) if color else encode_gray_png(pixels)
    preview=path.with_suffix('.png')
    if preview.is_symlink() or doc['preview_sha256']!=sha256(encoded) or preview.read_bytes()!=encoded:
        raise ValueError('capture preview differs from state')
    return capture,state
