"""Read-only whole-scene render and stale/duplicate-geometry checks."""
import bpy,json,sys,pathlib,hashlib,math
from mathutils import Vector
OUT=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');s=bpy.context.scene
frames=json.loads(pathlib.Path('/workspace/shared/sunward-structure-build/integration/inputs/candidate-r2/layout/site_frames.json').read_text())
root=lambda hid:bpy.data.objects.get('HOUSE_ROOT_'+hid)
proxies=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('COL_')]
report={'source':bpy.data.filepath,'source_sha256':hashlib.sha256(pathlib.Path(bpy.data.filepath).read_bytes()).hexdigest(),'scene_version':s.get('build_version'),'house_versions':{h:root(h).get('house_version') if root(h) else None for h in frames['house_frames']},'landmark_version':s.get('landmark_patch_version'),'legacy_joined_collider_present':'COL_Sunward_Static' in bpy.data.objects,'duplicate_visible_exit_gate_present':'LAYOUT_East_Roadwork_Gate' in bpy.data.objects,'detailed_exit_rail_count':sum(o.name.startswith('LM_Roadwork_rail') and not o.name.startswith('COL_') for o in bpy.data.objects),'floor_clip_present':'COL_V3_LAYOUT_OutlineClips' in bpy.data.objects,'proxy_mesh_count':len(proxies),'original_source_sha256':hashlib.sha256(pathlib.Path('/workspace/shared/stylized-nuketown-map/Sunward_TestSite.blend').read_bytes()).hexdigest(),'saved_source_not_modified':True,'scope':'Independent saved-source geometry and Blender renders; not live browser/capsule validation'}
for o in proxies:o.hide_render=True
report['root_transforms']={h:[list(row) for row in root(h).matrix_world] for h in frames['house_frames']}
report['old_house_visual_names_remaining']=[o.name for o in bpy.data.objects if o.type=='MESH' and (o.name.startswith(('A_Mint_','B_Saffron_','Gabled_roof','Garage_flat_roof')) or any(c.name in ['10_A_Mint_Architecture','10_B_Saffron_Architecture','11_A_Mint_Garage','11_B_Saffron_Garage','12_A_Mint_Interior','12_B_Saffron_Interior','13_A_Mint_Upper','13_B_Saffron_Upper'] for c in o.users_collection))]
report['family_order_correct']=root('A_Mint').matrix_world.translation.y<0 and root('B_Saffron').matrix_world.translation.y>0
report['family_roof_names']={h:sorted(set(o.get('part_id','') for o in bpy.data.objects if o.get('house_id')==h and 'Roof' in o.get('part_id',''))) for h in frames['house_frames']}
report['root_transform_max_error']={}
for h,frame in frames['house_frames'].items():
 from mathutils import Matrix
 expected=Matrix.Translation(Vector(frame['position_blender']))@Matrix.Rotation(frame['yaw_radians'],4,'Z')
 report['root_transform_max_error'][h]=max(abs(root(h).matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))
report['grass_vertices_in_house_components']=0
grass=bpy.data.objects.get('V3_Layout_Edge_Grass')
if grass:
 for h,frame in frames['house_frames'].items():
  inv=root(h).matrix_world.inverted()
  for v in grass.data.vertices:
   p=inv@grass.matrix_world@v.co
   if any(q['local_bbox_m'][0][0]<p.x<q['local_bbox_m'][1][0] and q['local_bbox_m'][0][1]<p.y<q['local_bbox_m'][1][1] for q in frame['components'].values()):report['grass_vertices_in_house_components']+=1
report['grass_source_vertex_count']=len(grass.data.vertices) if grass else 0
(OUT/'integrated-diagnostic-r2.json').write_text(json.dumps(report,indent=2)+'\n')
cam=bpy.data.objects.new('REVIEW_Integrated_Camera',bpy.data.cameras.new('REVIEW_Integrated_Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.clip_end=1000
s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
# Primary-source street comparison. All actual visible map geometry retained.
cam.location=(32,-10,8);target=Vector((-5,2,3));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=38
s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=1500;s.render.resolution_y=1000;s.render.filepath=str(OUT/'integrated-diagnostic-r2-street.png');bpy.ops.render.render(write_still=True)
# Exact-source overhead composition; hide only non-playable context ground/scenery.
for c in bpy.data.collections:
 if c.name=='40_ContextScenery':c.hide_render=True
cam.location=((420-550)*frames['image_to_world']['uniform_m_per_crop_pixel'],(475-480)*frames['image_to_world']['uniform_m_per_crop_pixel'],100);cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=960*frames['image_to_world']['uniform_m_per_crop_pixel']
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='FLAT';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=840;s.render.resolution_y=960;s.render.film_transparent=True;s.render.filepath=str(OUT/'integrated-diagnostic-r2-overhead.png');bpy.ops.render.render(write_still=True)
print('INTEGRATED_REVIEW',json.dumps(report))
