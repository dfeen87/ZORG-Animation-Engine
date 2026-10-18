import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from commander_zorg.canonical import read_json,atomic_json,sha256
from commander_zorg.live_motion import LiveRuntime
from commander_zorg.state import owned_state
from commander_zorg.field import evaluate_samples
from commander_zorg.raster import rasterize,measure_mask,encode_gray_png,geometry_mask,aligned_iou
r=LiveRuntime(read_json(Path('scenes/live_lab.json'))); s=r.scene
ids=[e.id for e in s.elements]
# Explicit identity assignments; unequal sigmas and weights remain unchanged.
layouts={
'home':{e.id:list(e.home_xy) for e in s.elements},
'circle':{i:[0.,0.] for i in ids},
'oval':{'accent_left':[-.04,.05],'accent_right':[.04,.05],'base_left':[-.03,-.30],'base_right':[.03,-.30],'core_00':[0.,-.18],'core_01':[0.,.10],'head_00':[0.,.30],'head_01':[0.,.35]},
'cloud':{'accent_left':[-.38,.19],'accent_right':[.38,.19],'base_left':[-.10,-.08],'base_right':[.10,-.08],'core_00':[-.38,.09],'core_01':[.38,.09],'head_00':[0.,.22],'head_01':[0.,.26]},
'hill':{'accent_left':[-.40,-.13],'accent_right':[.40,-.13],'base_left':[-.25,-.18],'base_right':[.25,-.18],'core_00':[-.27,-.09],'core_01':[.27,-.09],'head_00':[0.,.03],'head_01':[0.,.10]},
'head_base':{'accent_left':[-.10,.10],'accent_right':[.10,.10],'base_left':[-.04,-.22],'base_right':[.04,-.22],'core_00':[0.,-.10],'core_01':[0.,.08],'head_00':[0.,.22],'head_01':[0.,.24]}}
mechanisms={'home':'Original immutable home coordinates.','circle':'Co-locate all eight radial kernels at the origin: exactly radial field before sampling.','oval':'Place controls along a vertical spine; retain bilateral pairing for small kernels.','cloud':'Two separated broad lobes, a smaller middle lobe and raised shoulder controls.','hill':'Separate broad kernels horizontally with a lower base and shallow central crest.','head_base':'Shorter vertical spine with a tapered lower pair; semantic interpretation is ambiguous.'}
Path('docs/morph/study').mkdir(parents=True,exist_ok=True)
metrics={}; masks={}; sheet=Image.new('RGB',(384*3,414*2),'#222222'); d=ImageDraw.Draw(sheet)
for n,(name,layout) in enumerate(layouts.items()):
 p=np.array([layout[i] for i in ids]); off=p-s.home_xy
 pixels=rasterize(evaluate_samples(owned_state(0,p,np.zeros_like(p)),s),s)
 png=encode_gray_png(pixels); Path(f'docs/morph/study/{name}.png').write_bytes(png)
 m=measure_mask(pixels,s); box=m['bbox']; m['aspect_width_height']=(box[2]-box[0]+1)/(box[3]-box[1]+1)
 m['max_offset']=float(np.linalg.norm(off,axis=1).max()); m['max_bias_force']=float(np.linalg.norm(s.spring_k[:,None]*off,axis=1).max()); m['png_sha256']=sha256(png)
 mask=geometry_mask(pixels,s); masks[name]=mask
 m['horizontal_symmetry_iou']=float(np.count_nonzero(mask & mask[:,::-1])/np.count_nonzero(mask | mask[:,::-1]))
 metrics[name]=m
 recipe={'schema_version':'cz-morph-target-0.1','id':name,'basis':'home-relative-world-half-height','element_ids':ids,'offsets':off.tolist(),'field_sha256':sha256(__import__('commander_zorg.canonical',fromlist=['canonical_bytes']).canonical_bytes({'elements':[{'id':e.id,'sigma':e.sigma,'weight':e.weight,'home_xy':list(e.home_xy)} for e in s.elements],'threshold':s.threshold})),'description':mechanisms[name],'attribution':'ZORG Build 0.2 explicit mathematical construction; creator artistic review pending'}
 if name!='head_base': atomic_json(Path('morph_targets')/(name+'.json'),recipe)
 sheet.paste(Image.fromarray(pixels).convert('RGB'),((n%3)*384,(n//3)*414+30)); d.text(((n%3)*384+10,(n//3)*414+8),name,fill='white')
metrics['pairwise_aligned_iou']={f'{a}:{b}':aligned_iou(masks[a],masks[b]) for a in layouts for b in layouts if a<b}
atomic_json(Path('docs/morph/study/measurements.json'),metrics)
sheet.save('docs/morph/study/contact_sheet.png')
print(json.dumps(metrics,indent=2))
