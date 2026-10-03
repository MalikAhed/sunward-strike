import bpy,bmesh,json,os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=bpy.context.scene;cc=bpy.data.collections['91_Collision_Proxies'];cc.hide_viewport=False;cc.hide_render=False
co=bpy.data.objects['COL_Sunward_Static']
# Thin invisible perimeter clips close only the outer footprint; decorative fence detail remains visual.
for name,loc,dim in [('E',(28.9,0,2),(0.2,74,4)),('W',(-28.9,0,2),(0.2,74,4)),('N',(0,36.9,2),(58,.2,4)),('S',(0,-36.9,2),(58,.2,4))]:
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name='COL_Clip_'+name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for c in list(o.users_collection):c.objects.unlink(o)
 cc.objects.link(o)
bpy.ops.object.select_all(action='DESELECT')
for o in cc.objects:o.select_set(True)
bpy.context.view_layer.objects.active=co;bpy.ops.object.join();co=bpy.context.object
bm=bmesh.new();bm.from_mesh(co.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(co.data);bm.free()
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/Sunward_Collision.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
tri=sum(len(p.vertices)-2 for p in co.data.polygons)
cc.hide_render=True;cc.hide_viewport=True;s['build_version']='1.3';s['boundary_collision']='58 x 74m outer clip walls; invisible in render'
s.render.resolution_x=1500;s.render.resolution_y=1000;s.camera=bpy.data.objects['Camera_Hero']
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   sp=a.spaces.active;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.shading.show_cavity=True;sp.overlay.show_overlays=False;sp.region_3d.view_perspective='CAMERA';sp.region_3d.view_camera_zoom=25
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
p=ROOT+'/exports/resource_stats.json';st=json.load(open(p));st['build_version']='1.3';st['collision_triangles']=tri;st['perimeter_clip_walls']=4;json.dump(st,open(p,'w'),indent=2)
print('BOUNDARY_COMPLETE',tri,flush=True)
