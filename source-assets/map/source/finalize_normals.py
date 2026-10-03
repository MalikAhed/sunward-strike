import bpy,bmesh,os,json
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene;M=bpy.data.materials
for o in list(bpy.data.objects):
 if o.type!='MESH' or not o.name.startswith(('Truck_loading_ramp','Gabled_roof','Sedan_cabin')):continue
 upward=sum(p.normal.z for p in o.data.polygons)
 if upward<0 or (o.name.startswith('Truck_loading_ramp') and o.data.polygons[0].normal.z<0):o.data.flip_normals()
 o['normals_checked']='Outward shell winding'
cc=bpy.data.collections['91_Collision_Proxies'];cc.hide_viewport=False;cc.hide_render=False
collider=bpy.data.objects['COL_Sunward_Static']
bm=bmesh.new();bm.from_mesh(collider.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(collider.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');collider.select_set(True);bpy.context.view_layer.objects.active=collider
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/Sunward_Collision.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
ctri=sum(len(p.vertices)-2 for p in collider.data.polygons)
cc.hide_render=True;cc.hide_viewport=True
s['build_version']='1.2';s.cycles.samples=128;s.cycles.use_denoising=False
cam=bpy.data.objects['Camera_Hero'];s.camera=cam
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
# Same deterministic grouped export routine as the refinement pass.
code=open(ROOT+'/source/refine_export.py').read().split('# Evaluate and join export copies by material within semantic spatial collections.\n',1)[1]
code=code.replace("'build_version':'1.1'","'build_version':'1.2'")
exec(compile(code,'grouped_export','exec'))
