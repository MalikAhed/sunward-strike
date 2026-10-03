import bpy,os,json
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));PROJECT=os.path.dirname(ROOT);s=bpy.context.scene
# Match front plinth returns to the actual +/-6.125m outer side-wall faces.
for o in bpy.data.objects:
 if o.type=='MESH' and o.name.startswith('Facade_stone_plinth'):
  inv=o.matrix_world.inverted()
  for v in o.data.vertices:
   w=o.matrix_world@v.co
   if abs(abs(w.x)-6)<.005:w.x=6.15 if w.x>0 else -6.15;v.co=inv@w
s['build_version']='2.4';s['notes']='Reference-inspired art pass; original layout/collision preserved; compact baked maps and original foliage geometry'
s.camera=bpy.data.objects['Camera_Hero'];s.render.resolution_x=1500;s.render.resolution_y=1000;s.cycles.use_denoising=False;s.cycles.samples=192
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=PROJECT+'/Sunward_TestSite.blend')
# Preserve editable objects; evaluated export copies are grouped spatially by collection/material.
ex=bpy.data.collections.new('99_V2Export');s.collection.children.link(ex);groups={};dg=bpy.context.evaluated_depsgraph_get()
for col in list(bpy.data.collections):
 if col.name.startswith(('80_','90_','91_','99_')):continue
 for o in list(col.objects):
  if o.type not in {'MESH','CURVE','FONT'}:continue
  me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
  cp=bpy.data.objects.new(o.name+'_Export',me);ex.objects.link(cp);cp.matrix_world=o.matrix_world.copy();key=col.name+'__'+(me.materials[0].name if me.materials else 'default');groups.setdefault(key,[]).append(cp)
for key,objects in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 if len(objects)>1:bpy.ops.object.join()
 bpy.context.object.name=key
bpy.ops.object.select_all(action='DESELECT')
for o in ex.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=PROJECT+'/exports/Sunward_Environment.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
tri=0;mats=set();images=set()
for o in ex.objects:
 o.data.calc_loop_triangles();tri+=len(o.data.loop_triangles)
 for m in o.data.materials:
  if m:
   mats.add(m.name)
   if m.use_nodes:
    for n in m.node_tree.nodes:
     if n.type=='TEX_IMAGE' and n.image:images.add(n.image.name)
stats={'name':'SUNWARD / TEST SITE 07','build_version':'2.4','playable_bounds_m':[58,74],'units':'meters','environment_triangles':tri,'optimized_mesh_objects':len(ex.objects),'materials':len(mats),'texture_images':len(images),'texture_names':sorted(images),'collision_triangles':11286,'player_capsule_m':{'height':1.8,'radius':.35,'step':.30},'validation_scope':'16 sampled geometry and collision routes; limited Godot runtime physics checks','approximate_dimensions':True,'perimeter_clip_walls':4,'collision_preserved':True}
json.dump(stats,open(PROJECT+'/exports/resource_stats.json','w'),indent=2)
for o in list(ex.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(ex);bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=PROJECT+'/Sunward_TestSite.blend')
print('V2_EXPORT_COMPLETE',json.dumps(stats),flush=True)
