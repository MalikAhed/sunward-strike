"""Reversible SUNWARD p1r5 surface palette; geometry, UVs and lighting unchanged.

All targets are scene-linear reflectance. Byte-backed Blender image buffers hold
sRGB encoded samples: encode exactly once before saving, reload those PNG bytes,
and pack the same image for glTF. Original materials/images are never modified.
"""
import bpy, json, hashlib, re
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
VERSION = 'material-palette-p1r5'
SUFFIX = 'p1r5'
ORIGINAL_KEY = 'palette_p1_original_slot_'
# Source name -> role, linear RGB, retained source-luminance variation.
TEXTURE_TARGETS = {
 'V2_Warm_Plaster': ('Cream_Plaster', (.78,.74,.65), .40),
 'V2_Sage_Plaster': ('Turquoise_Plaster', (.065,.56,.42), .32),
 'V2_Saffron_Plaster': ('SunnyYellow_Plaster', (.86,.67,.12), .34),
 'V2_Weathered_Roof': ('BlueLavender_Roof', (.16,.18,.30), .50),
 'V2_Ground_Moss': ('Warm_GrassBase', (.38,.49,.075), .85),
 'V2_Limestone': ('Cream_Limestone', (.65,.59,.46), .45),
 'V2_Aged_Timber': ('Honey_GrainedTimber', (.58,.29,.09), .65),
 'V2_Road': ('Lavender_Asphalt', (.16,.155,.205), .70),
}
ALIASES = {'V3_B_Cream_Plaster':'V2_Warm_Plaster',
 'V3_B_Coral_Plaster':'V2_Saffron_Plaster',
 'V3_Layout_Warm_Weathered_Timber':'V2_Aged_Timber'}
CONSTANT_TARGETS = {
 'ivory': ('Warm_Ivory', (.86,.81,.70)),
 'chalk': ('Warm_Chalk', (.78,.71,.57)),
 'wood_light': ('Honey_Timber', (.68,.36,.105)),
 'wood': ('Brown_Timber', (.39,.18,.055)),
 'concrete_light': ('Cream_Concrete', (.65,.61,.51)),
 'concrete': ('Warm_Concrete', (.56,.54,.46)),
 'mint': ('Rich_Teal', (.12,.34,.28)),
 'mint_light': ('Sunlit_Teal', (.26,.53,.42)),
 'mint_dark': ('Deep_Teal', (.055,.22,.25)),
 'coral': ('Warm_RedAccent', (.69,.12,.09)),
 'coral_light': ('Sunlit_RedAccent', (.82,.23,.16)),
 'roof': ('Lavender_Trim', (.13,.16,.24)),
 'roof_light': ('Blue_GarageDoor', (.20,.27,.33)),
 'steel': ('BlueGrey_Steel', (.19,.215,.25)),
 'SW2_Arch_TimberEdge': ('Timber_Edge', (.43,.24,.075)),
 'SW2_Arch_WeatheredTimber': ('Weathered_Timber', (.29,.15,.055)),
}

def canonical_name(name): return re.sub(r'\.\d{3}$', '', name)
def srgb_to_linear(a): return np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)
def linear_to_srgb(a): return np.where(a <= .0031308, 12.92*a, 1.055*np.maximum(a,0)**(1/2.4)-.055)
def pixels(im):
 a=np.empty(len(im.pixels),dtype=np.float32); im.pixels.foreach_get(a); return a.reshape(-1,4)
def image_hash(im): return hashlib.sha256(pixels(im).tobytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def geometry_hash(collision_only=False):
 """Includes all native/export/collision mesh data, transforms, UVs and face bindings."""
 bpy.context.view_layer.update(); rows=[]
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  if o.type!='MESH' or (collision_only and not o.name.startswith('COL_')): continue
  rows.append((o.name, o.data.name, o.parent.name if o.parent else None,
   [list(v.co) for v in o.data.vertices], [list(e.vertices) for e in o.data.edges],
   [(list(p.vertices),p.material_index,p.use_smooth) for p in o.data.polygons],
   [list(r) for r in o.matrix_world],
   [(uv.name,[list(q.uv) for q in uv.data]) for uv in o.data.uv_layers],
   len(o.material_slots),[(m.name,m.type) for m in o.modifiers]))
 return digest(rows)

def bindings():
 return {o.name:[s.material.name if s.material else None for s in o.material_slots]
         for o in bpy.data.objects if o.type=='MESH'}

def color_texture(mat):
 return next((n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image
              and n.image.colorspace_settings.name=='sRGB'),None)

def recolored_image(source,name,target,strength,texture_dir=None):
 existing=bpy.data.images.get(name)
 if existing and existing.get('palette_revision')==VERSION:
  return existing, {'reused':True,'source':source.name}
 original=pixels(source)
 # Loaded byte PNG buffers expose encoded values. Float images expose linear.
 linear=original[:,:3] if source.is_float else srgb_to_linear(np.clip(original[:,:3],0,1))
 lum=linear @ np.array([.2126,.7152,.0722])
 variation=1+strength*(lum/max(float(lum.mean()),1e-8)-1)
 rgb=np.clip(variation[:,None]*np.array(target)[None,:],0,.985)
 encoded=linear_to_srgb(rgb)
 rgba=np.concatenate((encoded,original[:,3,None]),axis=1).astype(np.float32)
 im=bpy.data.images.new(name,width=source.size[0],height=source.size[1],alpha=True,float_buffer=False)
 im.colorspace_settings.name='sRGB'; im.pixels.foreach_set(rgba.ravel()); im.update()
 folder=Path(texture_dir) if texture_dir else HERE/'textures'; folder.mkdir(exist_ok=True,parents=True)
 path=folder/(name+'.png'); im.filepath_raw=str(path); im.file_format='PNG'; im.save()
 bpy.data.images.remove(im); im=bpy.data.images.load(str(path),check_existing=False); im.name=name
 im['palette_revision']=VERSION; im['source_image']=source.name; im['palette_encoding']='sRGB, encoded once from scene-linear'; im.pack()
 decoded=srgb_to_linear(pixels(im)[:,:3]); err=float(np.max(np.abs(decoded-rgb)))
 if err>.0045: raise AssertionError('Portable sRGB round-trip exceeds 8-bit quantization bound: '+str(err))
 return im, {'source':source.name,'target_linear_rgb':list(target),
  'retained_luminance_variation':strength,'mean_decoded_linear_rgb':decoded.mean(axis=0).tolist(),
  'mean_stored_srgb':pixels(im)[:,:3].mean(axis=0).tolist(),
  'encoding_roundtrip_max_error':err,'packed':bool(im.packed_file),
  'png_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'new_image':im.name}

def owned_material(src,role,target,texture=True,strength=.4,texture_dir=None):
 name='V3_Tone_'+role+'_'+SUFFIX; existing=bpy.data.materials.get(name)
 if existing and existing.get('palette_revision')==VERSION:
  return existing, {'reused':True,'material':name}
 m=src.copy(); m.name=name
 if 'palette_p1_original_fake_user' in m:del m['palette_p1_original_fake_user']
 m.use_fake_user=False; m['palette_revision']=VERSION; m['palette_source_material']=src.name
 m['palette_baked']=True; m['skip_reference_palette_tint']=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 report={'material':name,'source':src.name,'target_linear_rgb':list(target),'source_material_unmodified':True}
 if texture:
  tx=color_texture(m)
  if not tx: raise RuntimeError('No portable sRGB base-color image for '+src.name)
  image,detail=recolored_image(tx.image,name+'_BaseColor',target,strength,texture_dir); tx.image=image
  for link in list(p.inputs['Base Color'].links): m.node_tree.links.remove(link)
  m.node_tree.links.new(tx.outputs['Color'],p.inputs['Base Color']); report['texture']=detail
 else:
  for link in list(p.inputs['Base Color'].links): m.node_tree.links.remove(link)
  p.inputs['Base Color'].default_value=(*target,1)
 # Soften source plaster grain on copied materials, retaining standard portable normal maps.
 for n in m.node_tree.nodes:
  if n.type=='NORMAL_MAP':
   factor=.65 if any(x in role for x in ['Roof','Timber','Asphalt']) else .40
   prior=float(n.inputs['Strength'].default_value); n.inputs['Strength'].default_value=prior*factor
   report['normal_strength']={'before':prior,'after':prior*factor}
 m.diffuse_color=(*target,1)
 return m,report

def apply_material_palette(texture_dir=None):
 revisions={s.material.get('palette_revision') for o in bpy.data.objects if o.type=='MESH'
            for s in o.material_slots if s.material and s.material.name.startswith('V3_Tone_') and s.material.get('palette_revision')}
 if revisions and not revisions.issubset({VERSION,'lawn-finish-p1r5'}):
  raise RuntimeError('Restore the previous reversible palette before applying '+VERSION+': '+str(revisions))
 before=geometry_hash(); collision_before=geometry_hash(True); original_bindings=bindings()
 original_images={im.name:image_hash(im) for im in bpy.data.images if im.has_data and not im.name.startswith('V3_Tone_')}
 replacements={}; reports=[]; originals=list(bpy.data.materials)
 # Retain every source material, including source orphans, so a saved authoring copy loses no assets.
 for original in originals:
  if original.name.startswith('V3_Tone_'):continue
  if 'palette_p1_original_fake_user' not in original:original['palette_p1_original_fake_user']=original.use_fake_user
  original.use_fake_user=True
 # Resolve aliases from the actual material even if the canonical source was removed.
 for src in originals:
  canon=canonical_name(src.name); key=ALIASES.get(canon,canon)
  if key in TEXTURE_TARGETS:
   role,target,strength=TEXTURE_TARGETS[key]
   m,r=owned_material(src,role,target,True,strength,texture_dir); replacements[src.name]=m; reports.append(r)
  elif key in CONSTANT_TARGETS:
   role,target=CONSTANT_TARGETS[key]
   m,r=owned_material(src,role,target,False,texture_dir=texture_dir); replacements[src.name]=m; reports.append(r)
  elif key.startswith('SW2_Arch_Limestone'):
   m,r=owned_material(src,key.replace('SW2_Arch_','Warm_'),(.54,.49,.40),False,texture_dir=texture_dir)
   replacements[src.name]=m; reports.append(r)
 def special(src,role,target,texture=False,strength=.35):
  found=next((m for m in originals if canonical_name(m.name)==src),None)
  if not found:return None
  m,r=owned_material(found,role,target,texture,strength,texture_dir); reports.append(r);return m
 bus_light=special('ochre_light','Golden_Bus',(.95,.61,.115))
 bus_dark=special('ochre','Golden_BusShade',(.71,.41,.065))
 cream_shutter=special('mint_dark','Cream_Shutters',(.78,.75,.68))
 desert=special('V2_Ground_Moss','Warm_SandGround',(.63,.39,.19),True,.60)
 lower_family={h:special('V2_Warm_Plaster',role,target,True,.32) for h,role,target in [
  ('A_Mint','Turquoise_LowerSiding',(.065,.56,.42)),
  ('B_Saffron','SunnyYellow_LowerSiding',(.86,.67,.12))]}
 changes=[]
 for o in bpy.data.objects:
  if o.type!='MESH' or o.name.startswith('COL_') or o.get('native_source_only') or any(c.name.startswith(('91_','99_')) for c in o.users_collection):continue
  bus=o.get('vehicle')=='SUNLINE_Shuttle' or o.name.startswith(('Shuttle_','LM_Bus_'))
  for i,slot in enumerate(o.material_slots):
   if not slot.material:continue
   old=slot.material.name; canon=canonical_name(old); new=replacements.get(old)
   external_lower=o.get('part_id') in ['FrontLower','RearLower','GarageConnectorLower','EastLower']
   if external_lower and o.get('house_id') in lower_family and canon in ['V2_Warm_Plaster','V3_B_Cream_Plaster']:new=lower_family[o['house_id']]
   if o.name=='World_desert' and canon=='V2_Ground_Moss':new=desert
   elif bus and canon=='ochre_light':new=bus_light
   elif bus and canon=='ochre':new=bus_dark
   elif bus and canon=='ivory' and o.name.startswith('Shuttle_roof'):new=bus_light
   elif canon=='mint_dark' and o.get('house_id')=='A_Mint' and any(k in o.name for k in ['Shutter','Louvre']):new=cream_shutter
   if new:
    key=ORIGINAL_KEY+str(i)
    if key not in o:o[key]=old
    original=slot.material
    if 'palette_p1_original_fake_user' not in original:original['palette_p1_original_fake_user']=original.use_fake_user
    original.use_fake_user=True
    slot.material=new; changes.append({'object':o.name,'slot':i,'old':old,'new':new.name})
 after=geometry_hash(); collision_after=geometry_hash(True)
 mutated=[name for name,d in original_images.items() if image_hash(bpy.data.images[name])!=d]
 if before!=after or collision_before!=collision_after or mutated:raise AssertionError('Protected scene data changed')
 return {'version':VERSION,'geometry_sha256_before':before,'geometry_sha256_after':after,
  'collision_sha256_before':collision_before,'collision_sha256_after':collision_after,
  'geometry_unchanged':before==after,'collision_unchanged':collision_before==collision_after,
  'original_images_unchanged':not mutated,'original_materials_retained_for_save':True,'bindings_sha256_before':digest(original_bindings),
  'material_reports':reports,'material_slot_changes':changes,
  'runtime_policy':'V3_Tone_* names and palette_baked markers bypass legacy tint callbacks. Do not multiply a second tint.',
  'authority':'Latest in-map references specify turquoise/cream, sunny yellow, honey timber, lavender-blue roofs/asphalt, golden bus. Classic Nuketown structure remains authoritative.',
  'limits':'No lighting, sky, vegetation, structure or route edits. Full integrated/runtime review remains required.'}

def restore_material_palette():
 count=0
 for o in bpy.data.objects:
  if o.type!='MESH':continue
  for i,slot in enumerate(o.material_slots):
   key=ORIGINAL_KEY+str(i)
   if key in o:
    original=bpy.data.materials.get(o[key])
    if not original:raise RuntimeError('Missing original material '+o[key])
    slot.material=original; del o[key];count+=1
 for mat in bpy.data.materials:
  if 'palette_p1_original_fake_user' in mat:
   mat.use_fake_user=bool(mat['palette_p1_original_fake_user']);del mat['palette_p1_original_fake_user']
 return count
