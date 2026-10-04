"""Reversible portable main-house surface detail on accepted SUNWARD v3.1.

Changes only explicitly scoped material slots and adds owned material/image IDs.
Original pixels, shader graphs, UVs, geometry, transforms and collision stay intact.
Original affected materials are retained with recorded fake-user state for reopening.
"""
import bpy,json,hashlib
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
VERSION='surface-detail-p2r4'
VERIFICATION_REVISION='surface-state-p2r5'
STATE_KEY='sunward_surface_detail_p2_state'
PREFIX='V3_Tone_Surface_'

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def image_hash(im):
 # Accessing the pixel collection eagerly decodes packed/lazy file images. Never
 # predicate this on has_data: a freshly reopened valid image may report False.
 count=len(im.pixels)
 if count==0:raise RuntimeError('Cannot verify an empty original image buffer: '+im.name)
 a=np.empty(count,dtype=np.float32);im.pixels.foreach_get(a);return hashlib.sha256(a.tobytes()).hexdigest()
def bindings():return {o.name:{'slots':[(s.link,s.material.name if s.material else None) for s in o.material_slots],'polygon_material_indices':[p.material_index for p in o.data.polygons]} for o in bpy.data.objects if o.type=='MESH'}
def fake_users():return {'materials':{m.name:bool(m.use_fake_user) for m in bpy.data.materials},'images':{i.name:bool(i.use_fake_user) for i in bpy.data.images}}
def pixels():return {i.name:image_hash(i) for i in bpy.data.images if i.type!='RENDER_RESULT'}
def geometry_hash(collision=False):
 bpy.context.view_layer.update();h=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o.type!='MESH' or (collision and not o.name.startswith('COL_')):continue
  h.update(o.name.encode());h.update(o.data.name.encode())
  h.update(json.dumps({'parent':o.parent.name if o.parent else None,'matrix':[list(r) for r in o.matrix_world],'basis':[list(r) for r in o.matrix_basis],'hide_render':o.hide_render,'modifiers':[(m.name,m.type,bool(m.show_viewport),bool(m.show_render),getattr(m,'width',None),getattr(m,'segments',None)) for m in o.modifiers]},sort_keys=True).encode())
  for name,data,prop,size,dtype in [('vertices',o.data.vertices,'co',3,np.float32),('edges',o.data.edges,'vertices',2,np.int32),('loops',o.data.loops,'vertex_index',1,np.int32)]:
   a=np.empty(len(data)*size,dtype=dtype);data.foreach_get(prop,a);h.update(name.encode());h.update(a.tobytes())
  h.update(json.dumps([(list(p.vertices),p.use_smooth) for p in o.data.polygons]).encode())
  for uv in o.data.uv_layers:
   a=np.empty(len(uv.data)*2,dtype=np.float32);uv.data.foreach_get('uv',a);h.update(uv.name.encode());h.update(a.tobytes())
 return h.hexdigest()

SPECS={
 'Turquoise_H':('Turquoise_Siding_H','Siding_H_Normal',(.065,.56,.42),.38,.79),
 'Yellow_V':('SunnyYellow_Siding_V','Siding_V_Normal',(.86,.67,.12),.38,.79),
 'Roof_V':('Lavender_Shingle_V','Shingle_V_Normal',(.16,.18,.30),.45,.86),
 'Honey_V':('Honey_Grain_V','Grain_V_Normal',(.68,.36,.105),.30,.77),
}

# Explicit construction labels and local outward normals, checked against source builder.
# No world-position heuristic or ambiguous face guess is used.
WALL_OUTWARD={
 'FrontLower':(0,-1,0),'FrontUpper':(0,-1,0),'RearLower':(0,1,0),'RearUpper':(0,1,0),
 'GarageConnectorLower':(-1,0,0),'WestUpper':(-1,0,0),'EastLower':(1,0,0),'EastUpper':(1,0,0),
 'GarageFront':(0,-1,0),'GarageRear':(0,1,0),'GarageOuter':(-1,0,0),
}

def classify(o,material):
 if o.type!='MESH' or not o.name.startswith('H3_') or o.get('house_id') not in ['A_Mint','B_Saffron'] or o.hide_render:return None,None
 name=material.name;part=o.get('part_id','')
 if name in ['V3_Tone_Turquoise_Plaster_p1r5','V3_Tone_Turquoise_LowerSiding_p1r5']:
  return ('Turquoise_H',None) if part in WALL_OUTWARD else (None,'Thin siding accents/gable faces retain accepted material; no ambiguous exterior classification')
 if name in ['V3_Tone_SunnyYellow_Plaster_p1r5','V3_Tone_SunnyYellow_LowerSiding_p1r5']:
  return ('Yellow_V',None) if part in WALL_OUTWARD else (None,'Thin siding accents/clerestory faces retain accepted material; no ambiguous exterior classification')
 if name=='V3_Tone_BlueLavender_Roof_p1r5':
  return (None,'Opposite-axis green garage roof retained to respect four-material increment cap') if part.startswith('GreenGarageRoof') else ('Roof_V',None)
 if name=='V3_Tone_Honey_Timber_p1r5':
  if part.startswith('Interior'):return None,'Interior timber outside bounded exterior pass'
  spans=[max(v.co[i] for v in o.data.vertices)-min(v.co[i] for v in o.data.vertices) for i in range(3)]
  axis=max(range(3),key=lambda i:spans[i])
  if axis==1:return None,'Local-Y timber box has incompatible top/side grain directions in protected shared UV/material slot'
  if axis==0:return None,'Horizontal timber retained to respect four-material increment cap'
  return 'Honey_V',None
 return None,None

def apply_surface_detail(texture_dir=None):
 scene=bpy.context.scene
 if STATE_KEY in bpy.data.texts:
  state=json.loads(bpy.data.texts[STATE_KEY].as_string());assert state['version']==VERSION
  if state.get('verification_revision')!=VERIFICATION_REVISION:raise RuntimeError('Older verification record must be rebuilt from accepted source; refusing an empty/lazy original pixel baseline')
  return {'version':VERSION,'idempotent':True,'changed_slots':0,'state':state}
 if any(m.name.startswith(PREFIX) for m in bpy.data.materials) or any(i.name.startswith(PREFIX) for i in bpy.data.images):raise RuntimeError('Unmanaged surface-detail IDs already exist')
 folder=Path(texture_dir) if texture_dir else HERE/'textures'
 manifest=json.loads((HERE/'texture-manifest.json').read_text())
 for r in manifest['images']:
  if hashlib.sha256((folder/r['file']).read_bytes()).hexdigest()!=r['sha256']:raise RuntimeError('Texture checksum mismatch: '+r['file'])
 before_geometry=geometry_hash();before_collision=geometry_hash(True);before_pixels=pixels();before_fake=fake_users();before_bind=bindings()
 changes=[];skipped=[];sources={}
 for o in sorted(bpy.data.objects,key=lambda o:o.name):
  if o.type!='MESH':continue
  for i,slot in enumerate(o.material_slots):
   if slot.material is None:continue
   role,reason=classify(o,slot.material)
   if reason:skipped.append({'object':o.name,'reason':reason})
   if role:
    if not o.data.uv_layers:raise RuntimeError('Missing protected UVs: '+o.name)
    if o.data.users!=1:raise RuntimeError('Shared mesh requires explicit scope review: '+o.name)
    ch={'object':o.name,'slot':i,'link':slot.link,'source':slot.material.name,'role':role,'mode':'replace_slot'}
    if role in ['Turquoise_H','Yellow_V']:
     outward=WALL_OUTWARD[o.get('part_id')]
     exterior=[p.index for p in o.data.polygons if p.material_index==i and sum(p.normal[k]*outward[k] for k in range(3))>.99999]
     if len(exterior)!=1 or len(o.data.polygons)!=6:raise RuntimeError('Unexpected wall topology/outward face: '+o.name)
     ch.update(mode='exterior_polygon_split',outward_local=outward,polygon_indices=exterior,original_polygon_material_indices=[p.material_index for p in o.data.polygons],original_slot_count=len(o.material_slots))
    changes.append(ch)
    sources.setdefault(role,slot.material)
 if not changes:raise RuntimeError('No accepted-v3.1 house slots found')
 material_map={};image_map={}
 def load(name,role):
  if name in image_map:return image_map[name]
  im=bpy.data.images.load(str(folder/(name+'.png')),check_existing=False);im.name=PREFIX+name+'_p2r4'
  im.colorspace_settings.name='sRGB' if role=='baseColor' else 'Non-Color';im.use_fake_user=False
  im['surface_detail_revision']=VERSION;im['surface_original_analytic_art']=True;im.pack();image_map[name]=im;return im
 for role,source in sources.items():
  color_name,normal_name,target,strength,roughness=SPECS[role]
  m=source.copy();m.name=PREFIX+role+'_p2r4';m.use_fake_user=False
  m['surface_detail_revision']=VERSION;m['surface_source_material']=source.name;m['palette_baked']=True;m['skip_reference_palette_tint']=True
  m.use_nodes=True;m.node_tree.nodes.clear();nodes=m.node_tree.nodes;links=m.node_tree.links
  p=nodes.new('ShaderNodeBsdfPrincipled');p.inputs['Base Color'].default_value=(1,1,1,1);p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=0
  out=nodes.new('ShaderNodeOutputMaterial');links.new(p.outputs['BSDF'],out.inputs['Surface'])
  uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UVMap'
  color=nodes.new('ShaderNodeTexImage');color.image=load(color_name,'baseColor');color.interpolation='Linear';color.extension='REPEAT';links.new(uv.outputs['UV'],color.inputs['Vector']);links.new(color.outputs['Color'],p.inputs['Base Color'])
  tex=nodes.new('ShaderNodeTexImage');tex.image=load(normal_name,'normal');tex.interpolation='Linear';tex.extension='REPEAT';links.new(uv.outputs['UV'],tex.inputs['Vector'])
  normal=nodes.new('ShaderNodeNormalMap');normal.space='TANGENT';normal.uv_map='UVMap';normal.inputs['Strength'].default_value=strength;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
  m.diffuse_color=(*target,1);material_map[role]=m
 # Preserve even source-orphan IDs across save/reopen; v3.1 contains one orphan normal image.
 # Restore every original fake-user flag exactly after removing this reversible increment.
 for name in before_fake['materials']:bpy.data.materials[name].use_fake_user=True
 for name in before_fake['images']:
  if bpy.data.images[name].type!='RENDER_RESULT':bpy.data.images[name].use_fake_user=True
 for ch in changes:
  original=bpy.data.materials[ch['source']];original.use_fake_user=True
  obj=bpy.data.objects[ch['object']]
  if ch['mode']=='exterior_polygon_split':
   ch['added_slot']=len(obj.material_slots);obj.data.materials.append(material_map[ch['role']])
   for pi in ch['polygon_indices']:obj.data.polygons[pi].material_index=ch['added_slot']
  else:obj.material_slots[ch['slot']].material=material_map[ch['role']]
 after_geometry=geometry_hash();after_collision=geometry_hash(True)
 assert before_geometry==after_geometry and before_collision==after_collision
 assert all(n in bpy.data.images and image_hash(bpy.data.images[n])==d for n,d in before_pixels.items())
 assert before_pixels and len(before_pixels)==len([n for n in before_fake['images'] if bpy.data.images[n].type!='RENDER_RESULT'])
 state={'version':VERSION,'verification_revision':VERIFICATION_REVISION,'original_image_count':len(before_pixels),'geometry_hash':before_geometry,'collision_hash':before_collision,'original_bindings_hash':digest(before_bind),'original_pixels':before_pixels,'original_fake_users':before_fake,'changes':changes,'created_materials':[m.name for m in material_map.values()],'created_images':[im.name for im in image_map.values()]}
 text=bpy.data.texts.new(STATE_KEY);text.use_fake_user=True;text.write(json.dumps(state,sort_keys=True,separators=(',',':')))
 report={'version':VERSION,'verification_revision':VERIFICATION_REVISION,'original_image_count':len(before_pixels),'changed_slots':len(changes),'created_materials':state['created_materials'],'created_images':state['created_images'],'geometry_unchanged':before_geometry==after_geometry,'collision_unchanged':before_collision==after_collision,'original_pixels_unchanged':True,'scoped_objects':len({ch['object'] for ch in changes}),'skipped_objects':skipped,'image_manifest':manifest,'state':state,'known_limits':['Only unambiguous exterior box-wall faces receive the approved material-index split; interior faces and ambiguous thin siding/gable/clerestory faces retain accepted materials.','Local-Y timber boxes are left untouched where existing top/side grain axes conflict.','Cream siding, green garage roofs and horizontal timber stay accepted v3.1 to keep the increment at four materials/eight images.','This pass does not refine vehicles, non-main houses, furniture, terrain, foliage or sky.']}
 return report

def restore_surface_detail():
 scene=bpy.context.scene
 if STATE_KEY not in bpy.data.texts:return {'restored_slots':0,'already_restored':True}
 state=json.loads(bpy.data.texts[STATE_KEY].as_string())
 if state.get('verification_revision')!=VERIFICATION_REVISION or not state.get('original_pixels'):raise RuntimeError('Older empty/lazy pixel verification record is not accepted; use the rebuilt p2r5 verification candidate')
 for ch in state['changes']:
  o=bpy.data.objects.get(ch['object']);m=bpy.data.materials.get(ch['source'])
  if o is None or m is None:raise RuntimeError('Missing restoration dependency: '+str(ch))
  if ch['mode']=='exterior_polygon_split':
   for p,idx in zip(o.data.polygons,ch['original_polygon_material_indices']):p.material_index=idx
   if len(o.material_slots)!=ch['original_slot_count']+1:raise RuntimeError('Unexpected material slot change on '+o.name)
   o.data.materials.pop(index=ch['added_slot'])
  slot=o.material_slots[ch['slot']];slot.link=ch['link'];slot.material=m
 for name,value in state['original_fake_users']['materials'].items():
  if name not in bpy.data.materials:raise RuntimeError('Missing original material '+name)
  bpy.data.materials[name].use_fake_user=value
 for name,value in state['original_fake_users']['images'].items():
  if name not in bpy.data.images:raise RuntimeError('Missing original image '+name)
  bpy.data.images[name].use_fake_user=value
 for name in state['created_materials']:
  m=bpy.data.materials.get(name)
  if m:
   if m.users:raise RuntimeError('Owned material unexpectedly remains in use: '+name)
   bpy.data.materials.remove(m)
 for name in state['created_images']:
  im=bpy.data.images.get(name)
  if im:
   if im.users:raise RuntimeError('Owned image unexpectedly remains in use: '+name)
   bpy.data.images.remove(im)
 bpy.data.texts.remove(bpy.data.texts[STATE_KEY])
 report={'verification_revision':VERIFICATION_REVISION,'original_images_checked':len(state['original_pixels']),'restored_slots':len(state['changes']),'bindings_exact':digest(bindings())==state['original_bindings_hash'],'geometry_exact':geometry_hash()==state['geometry_hash'],'collision_exact':geometry_hash(True)==state['collision_hash'],'original_pixels_exact':pixels()==state['original_pixels'],'fake_users_exact':fake_users()==state['original_fake_users']}
 assert all(v for k,v in report.items() if k.endswith('_exact')),report
 return report
