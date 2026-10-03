"""Independent read-only saved-layout review; rendered QA plates are explicit."""
import bpy,sys,json,math,hashlib,pathlib
from mathutils import Vector
D=pathlib.Path('/workspace/shared/sunward-structure-build/layout');OUT=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review')
sys.path.insert(0,str(D));import layout_patch as L
cfg=json.loads((D/'site_frames.json').read_text());s=bpy.context.scene
expected=[Vector(p) for p in cfg['outline_blender']]
floor=bpy.data.objects['LAYOUT_Playable_Grass_Outline'];actual=[floor.matrix_world@v.co for v in floor.data.vertices]
max_error=max(min(math.hypot(p.x-q.x,p.y-q.y) for q in expected) for p in actual)
poly_area=abs(sum(expected[i].x*expected[(i+1)%len(expected)].y-expected[(i+1)%len(expected)].x*expected[i].y for i in range(len(expected)))/2)
report={'source_file':bpy.data.filepath,'source_sha256':hashlib.sha256(pathlib.Path(bpy.data.filepath).read_bytes()).hexdigest(),'frames_version':cfg['version'],'scale_is_provisional':True,'outline_vertex_count':len(actual),'expected_vertex_count':len(expected),'max_outline_vertex_error_m':max_error,'upward_normals':all(p.normal.z>.99 for p in floor.data.polygons),'floor_polygon_area_m2':sum(p.area for p in floor.data.polygons),'expected_polygon_area_m2':poly_area,'old_full_width_street_present':'Street_main_Continuous' in bpy.data.objects,'original_world_desert_present':'World_desert' in bpy.data.objects,'new_floor_collider_present':'COL_V3_LAYOUT_PlayableFloor' in bpy.data.objects,'original_joined_collider_present':'COL_Sunward_Static' in bpy.data.objects,'saved_source_not_modified':True,'render_scope':'saved terrain and perimeter, with explicitly added reference house/vehicle QA plates; not final integrated geometry'}
assert len(actual)==len(expected) and max_error<1e-5 and report['upward_normals'] and not report['old_full_width_street_present']
(OUT/'layout-r2-independent-results.json').write_text(json.dumps(report,indent=2)+'\n')
# Isolate terrain and perimeter in memory. Do not save this scene.
for c in bpy.data.collections:c.hide_render=c.name not in ['03_Layout_Ground','33_Layout_Perimeter']
for id,h in cfg['house_frames'].items():
 for component,p in h['components'].items():L.poly('REVIEW_QA_FOOTPRINT_'+id+'_'+component,p['blender'],.22,'mint'if id=='A_Mint'else'ochre','REVIEW_QA_PLATES',collision='QA only')
for id,h in cfg['landmark_frames'].items():
 if 'footprint_blender' in h:L.poly('REVIEW_QA_FOOTPRINT_'+id,h['footprint_blender'],.25,'ochre_light'if id=='SUNLINE_Shuttle'else'ivory','REVIEW_QA_PLATES',collision='QA only')
bpy.data.collections['REVIEW_QA_PLATES'].hide_render=False
cam=bpy.data.objects.new('REVIEW_QA_Camera',bpy.data.cameras.new('REVIEW_QA_Camera'));s.collection.objects.link(cam);cam.location=L.world([420,480],cfg,100);cam.rotation_euler=(0,0,0);cam.data.type='ORTHO';cam.data.ortho_scale=960*cfg['image_to_world']['uniform_m_per_crop_pixel'];s.camera=cam
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='FLAT';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=False;s.display.shading.background_type='WORLD';s.world.color=(.04,.04,.04);s.render.film_transparent=True;s.render.resolution_x=840;s.render.resolution_y=960;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(OUT/'layout-r2-independent-topdown.png');bpy.ops.render.render(write_still=True)
print('INDEPENDENT_LAYOUT_REVIEW',json.dumps(report))
