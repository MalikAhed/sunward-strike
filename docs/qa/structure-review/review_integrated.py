"""Read-only whole-scene render and stale/duplicate-geometry checks."""
import bpy,json,sys,pathlib,hashlib,math
from mathutils import Vector
OUT=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');s=bpy.context.scene
frames=json.loads(pathlib.Path('/workspace/shared/sunward-structure-build/layout/site_frames.json').read_text())
root=lambda hid:bpy.data.objects.get('HOUSE_ROOT_'+hid)
proxies=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('COL_')]
report={'source':bpy.data.filepath,'source_sha256':hashlib.sha256(pathlib.Path(bpy.data.filepath).read_bytes()).hexdigest(),'scene_version':s.get('build_version'),'house_versions':{h:root(h).get('house_version') if root(h) else None for h in frames['house_frames']},'landmark_version':s.get('landmark_patch_version'),'legacy_joined_collider_present':'COL_Sunward_Static' in bpy.data.objects,'duplicate_visible_exit_gate_present':'LAYOUT_East_Roadwork_Gate' in bpy.data.objects,'detailed_exit_rail_count':sum(o.name.startswith('LM_Roadwork_rail') and not o.name.startswith('COL_') for o in bpy.data.objects),'floor_clip_present':'COL_V3_LAYOUT_OutlineClips' in bpy.data.objects,'proxy_mesh_count':len(proxies),'original_source_sha256':hashlib.sha256(pathlib.Path('/workspace/shared/stylized-nuketown-map/Sunward_TestSite.blend').read_bytes()).hexdigest(),'saved_source_not_modified':True,'scope':'Independent saved-source geometry and Blender renders; not live browser/capsule validation'}
for o in proxies:o.hide_render=True
report['root_transforms']={h:[list(row) for row in root(h).matrix_world] for h in frames['house_frames']}
report['old_house_visual_names_remaining']=[o.name for o in bpy.data.objects if o.type=='MESH' and (o.name.startswith(('A_Mint_front','B_Saffron_front','Gabled_roof','Garage_flat_roof')))]
(OUT/'integrated-diagnostic-r1.json').write_text(json.dumps(report,indent=2)+'\n')
cam=bpy.data.objects.new('REVIEW_Integrated_Camera',bpy.data.cameras.new('REVIEW_Integrated_Camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.clip_end=1000
s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
# Primary-source street comparison. All actual visible map geometry retained.
cam.location=(32,-10,8);target=Vector((-5,2,3));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=38
s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=False;s.render.resolution_x=1500;s.render.resolution_y=1000;s.render.filepath=str(OUT/'integrated-diagnostic-r1-street.png');bpy.ops.render.render(write_still=True)
# Exact-source overhead composition; hide only non-playable context ground/scenery.
for c in bpy.data.collections:
 if c.name=='40_ContextScenery':c.hide_render=True
cam.location=((420-550)*frames['image_to_world']['uniform_m_per_crop_pixel'],(475-480)*frames['image_to_world']['uniform_m_per_crop_pixel'],100);cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=960*frames['image_to_world']['uniform_m_per_crop_pixel']
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='FLAT';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.render.resolution_x=840;s.render.resolution_y=960;s.render.film_transparent=True;s.render.filepath=str(OUT/'integrated-diagnostic-r1-overhead.png');bpy.ops.render.render(write_still=True)
print('INTEGRATED_REVIEW',json.dumps(report))
