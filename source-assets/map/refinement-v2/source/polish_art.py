import bpy,math,sys,os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=bpy.context.scene;sys.path.insert(0,ROOT)
import add_architecture,add_foliage_dense
add_architecture.apply();add_foliage_dense.apply()
# Road surface union: no stacked circular sheet or floating black-edged patches.
ground=bpy.data.collections['00_Ground']
for o in list(ground.objects):
 if o.name.startswith(('Street_main','Central_culdesac','Road_repair')):bpy.data.objects.remove(o,do_unlink=True)
r=10.5;half=5.25;cx=-2;xa=cx-math.sqrt(r*r-half*half);xb=cx+math.sqrt(r*r-half*half)
vv=[(-28.85,-half,.065),(xa,-half,.065)]
for i in range(1,33):
 a=math.radians(210+120*i/32);vv.append((cx+r*math.cos(a),r*math.sin(a),.065))
vv.extend([(28.85,-half,.065),(28.85,half,.065),(xb,half,.065)])
for i in range(1,33):
 a=math.radians(30+120*i/32);vv.append((cx+r*math.cos(a),r*math.sin(a),.065))
vv.append((-28.85,half,.065))
me=bpy.data.meshes.new('Continuous_Street_Surface');me.from_pydata(vv,[],[tuple(range(len(vv)))]);me.update();o=bpy.data.objects.new('Street_main_Continuous',me);ground.objects.link(o);me.materials.append(bpy.data.materials['V2_Road'])
# Texture projection used on new trim and paving, with shared low-cost normal map.
def project_uv(o,scale):
 if o.type!='MESH':return
 uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap');nm=o.matrix_world.to_3x3().inverted().transposed()
 for p in o.data.polygons:
  n=(nm@p.normal).normalized();axis=max(range(3),key=lambda i:abs(n[i]));axes=[1,2] if axis==0 else ([0,2] if axis==1 else [0,1])
  for li in p.loop_indices:
   v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/scale,v[axes[1]]/scale)
project_uv(o,4.5)
normal_image=bpy.data.images.get('V2_Warm_Plaster_Normal.png') or next(im for im in bpy.data.images if im.name.startswith('V2_Warm_Plaster_Normal'))
for m in bpy.data.materials:
 if m.name.startswith('SW2_Arch_Limestone') or m.name in ['coral','coral_light','ochre_light','mint','mint_light']:
  p=m.node_tree.nodes.get('Principled BSDF');tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=normal_image;tx.extension='REPEAT';nn=m.node_tree.nodes.new('ShaderNodeNormalMap');nn.inputs['Strength'].default_value=.16;m.node_tree.links.new(tx.outputs['Color'],nn.inputs['Color']);m.node_tree.links.new(nn.outputs[0],p.inputs['Normal'])
for o in bpy.data.collections['61_V2_Architecture'].objects:project_uv(o,2.3)
for o in bpy.data.collections['20_CentralVehicles'].objects:
 if o.type=='MESH':project_uv(o,2.4)
# Quiet the background into a distant supporting silhouette; avoid toy-like rock towers.
for o in bpy.data.collections['62_V2_Context'].objects:
 if o.name.startswith('Far_cliff'):
  for v in o.data.vertices:
   v.co.x*=1.38;v.co.y*=1.38;v.co.z=-1+(v.co.z+1)*.30
# Ground meets the map edge instead of presenting a floating diorama slab.
worldground=bpy.data.objects['World_desert'];worldground.location.z=-.30
worldground.data.materials.clear();worldground.data.materials.append(bpy.data.materials['V2_Ground_Moss']);project_uv(worldground,12.0)
# Additional player-height composition for the new material/foliage treatment.
bpy.ops.object.camera_add(location=(-20.5,8.0,1.75));cam=bpy.context.object;cam.name='Camera_Courtyard';cam.rotation_euler=(Vector((-4.5,16.0,3.05))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=27;cam.data.clip_end=400
for c in list(cam.users_collection):c.objects.unlink(cam)
bpy.data.collections['80_Presentation'].objects.link(cam)
# Remove orphan bake images before packing so exports carry only actual maps.
for im in list(bpy.data.images):
 if im.name.startswith('V2_') and im.users==0:bpy.data.images.remove(im)
for im in bpy.data.images:
 if im.name.startswith('V2_') and im.has_data:im.pack()
s['build_version']='2.1';s['art_review']='Denser foliage, corrected paving normals, single continuous road, reduced background cliffs, grounded terrain'
s.cycles.use_denoising=False;s.cycles.samples=96;s.render.resolution_x=1500;s.render.resolution_y=1000
s.camera=bpy.data.objects['Camera_Courtyard'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Polished.blend')
for key,camera in [('v2p_street','Camera_Street'),('v2p_courtyard','Camera_Courtyard'),('v2p_hero','Camera_Hero')]:
 s.camera=bpy.data.objects[camera];s.render.filepath=ROOT+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
s.camera=bpy.data.objects['Camera_Hero'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Polished.blend')
print('POLISH_COMPLETE',flush=True)
