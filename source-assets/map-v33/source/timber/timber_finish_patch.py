"""P5: replace only the already qualified P2 honey timber material, reversibly."""
import bpy,json,hashlib
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
VERSION='timber-finish-p5r3'
SOURCE_MATERIAL='V3_Tone_Surface_Honey_V_p2r4'
OWN_MATERIAL='V3_Tone_Timber_Honey_p5r3'
STATE='sunward_timber_finish_p5_state'

def h(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def image_state(im):
 n=len(im.pixels)
 if n==0:raise RuntimeError('Empty original image: '+im.name)
 a=np.empty(n,np.float32);im.pixels.foreach_get(a)
 return {'pixels':hashlib.sha256(a.tobytes()).hexdigest(),'packed':hashlib.sha256(bytes(im.packed_file.data)).hexdigest() if im.packed_file else None,'size':list(im.size),'colorspace':im.colorspace_settings.name}
def images():return {im.name:image_state(im) for im in bpy.data.images if im.type!='RENDER_RESULT'}
def flags():return {'materials':{m.name:m.use_fake_user for m in bpy.data.materials},'images':{im.name:im.use_fake_user for im in bpy.data.images}}
def bindings():return {o.name:{'slots':[[s.link,s.material.name if s.material else None] for s in o.material_slots],'polygons':[p.material_index for p in o.data.polygons]} for o in bpy.data.objects if o.type=='MESH'}
def geometry():
 bpy.context.view_layer.update();q=hashlib.sha256()
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  data={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'matrix':[list(r) for r in o.matrix_world],'basis':[list(r) for r in o.matrix_basis],'hide_render':o.hide_render,'collections':sorted(c.name for c in o.users_collection)}
  q.update(json.dumps(data,sort_keys=True).encode())
  if o.type=='MESH':
   for col,prop,n,dtype in [(o.data.vertices,'co',3,np.float32),(o.data.edges,'vertices',2,np.int32),(o.data.loops,'vertex_index',1,np.int32)]:
    a=np.empty(len(col)*n,dtype=dtype);col.foreach_get(prop,a);q.update(a.tobytes())
   q.update(json.dumps([(list(p.vertices),p.material_index,p.use_smooth) for p in o.data.polygons]).encode())
   for uv in o.data.uv_layers:
    a=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',a);q.update(uv.name.encode());q.update(a.tobytes())
   q.update(json.dumps([(m.name,m.type,m.show_viewport,m.show_render,getattr(m,'width',None),getattr(m,'segments',None)) for m in o.modifiers]).encode())
 return q.hexdigest()

def apply_timber_finish():
 if STATE in bpy.data.texts:
  s=json.loads(bpy.data.texts[STATE].as_string());assert s['version']==VERSION;return {'idempotent':True,'changed_slots':0}
 if OWN_MATERIAL in bpy.data.materials:raise RuntimeError('Unmanaged P5 material exists')
 source=bpy.data.materials.get(SOURCE_MATERIAL)
 if source is None:raise RuntimeError('Expected accepted P2 timber material is missing; do not reapply P2')
 targets=[]
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  for i,slot in enumerate(o.material_slots):
   if slot.material!=source:continue
   if not o.name.startswith('H3_') or o.get('house_id') not in ['A_Mint','B_Saffron'] or o.get('part_id','').startswith('Interior'):raise RuntimeError('Unexpected shared timber target: '+o.name)
   spans=[max(v.co[k] for v in o.data.vertices)-min(v.co[k] for v in o.data.vertices) for k in range(3)]
   if spans.index(max(spans))!=2 or not o.data.uv_layers or o.data.users!=1:raise RuntimeError('Timber UV qualification changed: '+o.name)
   targets.append((o.name,i))
 if len(targets)!=210:raise RuntimeError('Expected210 qualified targets, got '+str(len(targets)))
 before={'geometry':geometry(),'bindings':bindings(),'images':images(),'flags':flags()}
 manifest=json.loads((P/'texture-manifest.json').read_text());loaded=[]
 for r in manifest['images']:
  f=P/'textures'/r['file'];assert hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
  im=bpy.data.images.load(str(f),check_existing=False);im.name='V3_Tone_'+r['name'];im.colorspace_settings.name='sRGB' if r['role']=='baseColor' else 'Non-Color';im.use_fake_user=False;im.pack();loaded.append((r['role'],im))
 m=source.copy();m.name=OWN_MATERIAL;m.use_fake_user=False;m['timber_finish_revision']=VERSION;m['palette_baked']=True;m['skip_reference_palette_tint']=True
 source_normal_strength=[]
 for node in list(m.node_tree.nodes):
  if node.type=='TEX_IMAGE' and node.image:
   role='baseColor' if node.image.colorspace_settings.name=='sRGB' else 'normal';node.image=dict(loaded)[role]
   if role=='baseColor':
    incoming=node.inputs['Vector'].links[0].from_socket
    mapping=m.node_tree.nodes.new('ShaderNodeMapping');mapping.name='P5 color-only lengthwise fiber repeat';mapping.vector_type='POINT';mapping.inputs['Scale'].default_value=(3,1,1)
    m.node_tree.links.new(incoming,mapping.inputs['Vector']);m.node_tree.links.new(mapping.outputs['Vector'],node.inputs['Vector'])
  if node.type=='NORMAL_MAP':source_normal_strength.append(node.inputs['Strength'].default_value)
 assert len(source_normal_strength)==1 and abs(source_normal_strength[0]-.30)<1e-6
 source.use_fake_user=True
 # Keep every pre-existing ID recoverable, changing only flags actually needed.
 for mat in bpy.data.materials:
  if mat.name in before['flags']['materials'] and mat.users==0:mat.use_fake_user=True
 for im in bpy.data.images:
  if im.name in before['flags']['images'] and im.type!='RENDER_RESULT' and im.users==0:im.use_fake_user=True
 for name,i in targets:bpy.data.objects[name].material_slots[i].material=m
 assert geometry()==before['geometry']
 now=images();assert all(now[n]==v for n,v in before['images'].items())
 state={'version':VERSION,'before':before,'targets':targets,'created_material':m.name,'created_images':[im.name for role,im in loaded],'original_image_count':len(before['images'])}
 t=bpy.data.texts.new(STATE);t.use_fake_user=True;t.write(json.dumps(state,sort_keys=True,separators=(',',':')))
 return {'version':VERSION,'changed_slots':len(targets),'original_image_count':len(before['images']),'geometry_unchanged':True,'original_decoded_and_packed_images_unchanged':True,'source_material':source.name,'new_material':m.name,'normal_strength':source_normal_strength[0],'textures':manifest,'state':state}

def restore_timber_finish():
 if STATE not in bpy.data.texts:return {'already_restored':True}
 s=json.loads(bpy.data.texts[STATE].as_string());b=s['before'];assert s['original_image_count']>0
 for name,i in s['targets']:bpy.data.objects[name].material_slots[i].material=bpy.data.materials[b['bindings'][name]['slots'][i][1]]
 mat=bpy.data.materials[s['created_material']];assert mat.users==0;bpy.data.materials.remove(mat)
 for name in s['created_images']:
  im=bpy.data.images[name];assert im.users==0;bpy.data.images.remove(im)
 for name,value in b['flags']['materials'].items():bpy.data.materials[name].use_fake_user=value
 for name,value in b['flags']['images'].items():bpy.data.images[name].use_fake_user=value
 bpy.data.texts.remove(bpy.data.texts[STATE])
 result={'original_images_checked':s['original_image_count'],'bindings_exact':bindings()==b['bindings'],'geometry_exact':geometry()==b['geometry'],'decoded_and_packed_images_exact':images()==b['images'],'flags_exact':flags()==b['flags']}
 assert all(v for k,v in result.items() if k.endswith('_exact')),result
 return result
