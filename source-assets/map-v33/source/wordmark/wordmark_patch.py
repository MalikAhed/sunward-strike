"""Reversible placement/planar-scale correction for the original SUNLINE label.
Only Shuttle_label location and scale X/Y change. No paint patch is imported.
"""
import sys
sys.dont_write_bytecode=True
import bpy,json,zlib,base64,textwrap,hashlib
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
if str(P) not in sys.path:sys.path.insert(0,str(P))
import label_validation as qa
VERSION='wordmark-legibility-p6r1';STATE='SUNWARD_WORDMARK_LEGIBILITY_P6_STATE';ENCODING='P6_ZLIB85_V1';LABEL='Shuttle_label';SCALE=.72

def visible_bounds(o):
 bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);m=ev.to_mesh(preserve_all_data_layers=True,depsgraph=dg);pts=[o.matrix_world@v.co for v in m.vertices];r=[[min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)]];ev.to_mesh_clear();return r

def center(bounds):return Vector([(a+b)/2 for a,b in zip(*bounds)])
def read_state():
 s=bpy.data.texts[STATE].as_string();assert s.startswith(ENCODING+'\n');return json.loads(zlib.decompress(base64.b85decode(''.join(s.splitlines()[1:]))))

def apply_wordmark(expected_image_count=30):
 if STATE in bpy.data.texts:
  assert read_state()['version']==VERSION;return {'version':VERSION,'idempotent':True}
 before=qa.snapshot();assert len(before['images'])==expected_image_count and expected_image_count>0
 o=bpy.data.objects[LABEL];assert o.type=='FONT' and o.data.body=='SUNLINE' and o.parent is None
 assert [s.material.name for s in o.material_slots]==['ivory']
 old={'location':list(o.location),'scale':list(o.scale),'rotation_euler':list(o.rotation_euler),'rotation_mode':o.rotation_mode,'matrix_basis':[list(x) for x in o.matrix_basis],'matrix_world':[list(x) for x in o.matrix_world]};bounds_before=visible_bounds(o);old_center=center(bounds_before)
 bottom=visible_bounds(bpy.data.objects['LM_Bus_rubrail_-1_1'])[1][2];top=visible_bounds(bpy.data.objects['Shuttle_beltline'])[0][2];assert .18<top-bottom<.20
 o.scale=(old['scale'][0]*SCALE,old['scale'][1]*SCALE,old['scale'][2]);bpy.context.view_layer.update();new_center=center(visible_bounds(o));desired=old_center.copy();desired.z=(bottom+top)/2;o.location+=desired-new_center;bpy.context.view_layer.update();bounds_after=visible_bounds(o)
 assert bounds_after[0][2]-bottom>.017 and top-bounds_after[1][2]>.017
 assert max(abs(center(bounds_after)[i]-old_center[i]) for i in [0,1])<1e-6
 assert list(o.rotation_euler)==old['rotation_euler'] and o.rotation_mode==old['rotation_mode'] and o.scale.z==old['scale'][2]
 retained=[]
 for im in bpy.data.images:
  if im.type!='RENDER_RESULT' and not im.users and not im.use_fake_user:retained.append(im.name);im.use_fake_user=True
 after=qa.snapshot();expected=json.loads(json.dumps(before['objects']));expected[LABEL]['world']=after['objects'][LABEL]['world'];expected[LABEL]['basis']=after['objects'][LABEL]['basis'];assert qa.digest(expected)==qa.digest(after['objects'])
 for key in ['materials','uvs','attributes','globals','collision_hash','texts']:assert before[key]==after[key],key
 for name,d in before['images'].items():
  a=dict(after['images'][name]);a['fake_user']=d['fake_user'];assert a==d,(name,'image changed')
 assert len(before['images'])==len(after['images'])
 change={'object':LABEL,'text':o.data.body,'original':old,'new_location':list(o.location),'new_scale':list(o.scale),'new_matrix_world':[list(x) for x in o.matrix_world],'original_visible_bounds':bounds_before,'new_visible_bounds':bounds_after,'clear_band_z':[bottom,top],'lower_clearance':bounds_after[0][2]-bottom,'upper_clearance':top-bounds_after[1][2],'planar_scale_factor':SCALE,'ink_center_xy_preserved':True}
 st={'version':VERSION,'baseline':before,'change':change,'retained_orphan_images':retained,'module_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};raw=json.dumps(st,sort_keys=True,separators=(',',':')).encode();s=base64.b85encode(zlib.compress(raw,6)).decode();t=bpy.data.texts.new(STATE);t.use_fake_user=True;t.write(ENCODING+'\n'+'\n'.join(textwrap.wrap(s,1000,break_on_hyphens=False)))
 return {'version':VERSION,'idempotent':False,'changed_objects':[LABEL],'change':change,'original_images_verified':len(before['images']),'new_materials':0,'new_images':0,'new_native_uv_layers':0,'original_materials_uvs_attributes_collision_globals_exact':True,'all_other_objects_exact':True,'original_font_text_material_rotation_and_depth_exact':True,'retained_orphan_images':retained,'original_snapshot_sha256':qa.digest(before)}

def restore_wordmark():
 if STATE not in bpy.data.texts:return {'already_restored':True}
 st=read_state();o=bpy.data.objects[LABEL];old=st['change']['original'];o.location=old['location'];o.scale=old['scale'];bpy.context.view_layer.update()
 for name in st['retained_orphan_images']:bpy.data.images[name].use_fake_user=st['baseline']['images'][name]['fake_user']
 bpy.data.texts.remove(bpy.data.texts[STATE]);after=qa.snapshot();checks={k:qa.digest(v)==qa.digest(after[k]) for k,v in st['baseline'].items()}
 if not all(checks.values()):(P/'reports/restore-difference.json').write_text(json.dumps({'before':st['baseline'],'after':after,'checks':checks},indent=2))
 assert all(checks.values()),checks
 return {'exact':checks,'object_count':len(after['objects']),'material_count':len(after['materials']),'image_count':len(after['images']),'mesh_uv_attribute_inventories':len(after['uvs']),'snapshot_sha256':qa.digest(after)}
