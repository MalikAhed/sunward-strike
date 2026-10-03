import bpy,math,os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=bpy.context.scene
cream=bpy.data.materials['V2_Warm_Plaster']
def project_uv(o,scale=2.6):
 uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap');nm=o.matrix_world.to_3x3().inverted().transposed()
 for p in o.data.polygons:
  n=(nm@p.normal).normalized();axis=max(range(3),key=lambda i:abs(n[i]));axes=[1,2] if axis==0 else ([0,2] if axis==1 else [0,1])
  for li in p.loop_indices:
   v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/scale,v[axes[1]]/scale)
def box(name,minimum,maximum,col,mat):
 x0,y0,z0=minimum;x1,y1,z1=maximum
 verts=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
 faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o);me.materials.append(mat)
 mod=o.modifiers.new('Quiet edge highlight','BEVEL');mod.width=.018;mod.segments=1
 mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 project_uv(o);return o
wallprefixes=('A_Mint_front','A_Mint_rear','A_Mint_west','A_Mint_east','B_Saffron_front','B_Saffron_rear','B_Saffron_west','B_Saffron_east')
for o in list(bpy.data.objects):
 if o.type!='MESH' or not o.name.startswith(wallprefixes):continue
 coords=[o.matrix_world@Vector(v) for v in o.bound_box];lo=Vector([min(v[i] for v in coords) for i in range(3)]);hi=Vector([max(v[i] for v in coords) for i in range(3)])
 if hi.z<=3.27:
  o.data.materials.clear();o.data.materials.append(cream)
 elif lo.z<3.25 and hi.z>3.25:
  topmat=o.data.materials[0];col=o.users_collection[0];name=o.name
  box(name+'_LowerPlaster',lo,(hi.x,hi.y,3.25),col,cream)
  box(name+'_UpperPlaster',(lo.x,lo.y,3.25),hi,col,topmat)
  bpy.data.objects.remove(o,do_unlink=True)
# Composition: street identity plus an unobstructed, eye-height materials/foliage view.
cam=bpy.data.objects['Camera_Street'];cam.data.lens=28;cam.rotation_euler=(Vector((1,12,2.1))-cam.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects['Camera_Courtyard'];cam.location=(16,7.3,1.75);cam.rotation_euler=(Vector((2,15,2.4))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=27
sun=bpy.data.objects['Warm_afternoon_sun'];sun.data.energy=3.15;sun.data.color=(1,.91,.77);sun.data.angle=math.radians(4)
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.61
s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.46,.63,.82,1)
s.view_settings.exposure=.05
presentation=bpy.data.collections['80_Presentation']
for sign in [-1,1]:
 for label,loc,energy,size in [('UpperFill',(0,sign*17,6.2),90,5),('GarageFill',(-sign*9.4,sign*17,3.0),65,4)]:
  data=bpy.data.lights.new('V2_'+label+'_'+str(sign),'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=(.76,.85,1)
  o=bpy.data.objects.new(data.name,data);presentation.objects.link(o);o.location=loc
s['build_version']='2.2';s['art_review']='Warm lower plaster, colored upper houses, preserved layout, layered foliage, timber/stone detail, readable shade and clean road surface'
s.cycles.samples=64;s.cycles.use_denoising=False;s.render.resolution_x=1350;s.render.resolution_y=900
s.camera=bpy.data.objects['Camera_Courtyard'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Final.blend')
for key,c in [('v2f_courtyard','Camera_Courtyard'),('v2f_street','Camera_Street'),('v2f_hero','Camera_Hero')]:
 s.camera=bpy.data.objects[c];s.render.filepath=ROOT+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
s.camera=bpy.data.objects['Camera_Hero'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Final.blend')
print('FINAL_TREATMENT_COMPLETE',flush=True)
