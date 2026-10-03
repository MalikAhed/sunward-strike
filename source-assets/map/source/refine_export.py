import bpy,math,json,os
from mathutils import Vector,Matrix
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene
M=bpy.data.materials
C=bpy.data.collections['00_Ground']
def mesh(name,verts,faces,mat='asphalt',collection=C):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);collection.objects.link(o);me.materials.append(M[mat]);return o
def cube(name,loc,dim,mat='concrete_light',collection=C):
 w,d,h=[v/2 for v in dim];o=mesh(name,[(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,collection);o.location=loc;return o
def remove_prefix(prefixes):
 for o in list(C.objects):
  if any(o.name.startswith(p) for p in prefixes):bpy.data.objects.remove(o,do_unlink=True)
# Correct the defining cul-de-sac: one round central court containing both staggered vehicles.
remove_prefix(['Culdesac_west','Sidewalk','Curb','Pavement_joint','Garden_lawn','Street_center_dash'])
n=72;r=10.5;verts=[(-2,0,.064)]+[(-2+r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n),.064) for i in range(n)]
mesh('Central_culdesac',verts,[(0,i+1,(i+1)%n+1) for i in range(n)])
# Curved curb and concrete footway, interrupted where the road exits the loop.
for sign in [-1,1]:
 a0=.50 if sign==1 else math.pi+.50;a1=math.pi-.50 if sign==1 else 2*math.pi-.50
 for ri,ro,z,name,mat in [(10.5,10.7,.23,'Curved_curb','chalk'),(10.7,11.9,.155,'Culdesac_footway','concrete_light')]:
  vv=[];ff=[]
  for i in range(33):
   a=a0+(a1-a0)*i/32;vv.extend([(-2+ri*math.cos(a),ri*math.sin(a),z),(-2+ro*math.cos(a),ro*math.sin(a),z)])
  for i in range(32):ff.append((2*i,2*i+1,2*i+3,2*i+2))
  mesh(name,vv,ff,mat)
 # Rectangular back lawn; front islands align with curb arcs instead of covering the circle.
 cube('Garden_lawn',(0,sign*24.3,.015),(52,24.6,.10),'grass')
 for xa,xb in [(-28,-11.2),(7.2,28)]:
  cube('Approach_sidewalk',((xa+xb)/2,sign*6.45,.04),(xb-xa,2.1,.22),'concrete_light')
  cube('Approach_curb',((xa+xb)/2,sign*5.48,.11),(xb-xa,.20,.35),'chalk')
  for x in range(math.ceil(xa),math.floor(xb),3):cube('Expansion_joint',(x,sign*6.45,.155),(.025,1.95,.005),'concrete')
  cube('Front_grass_island',((xa+xb)/2,sign*9.7,.015),(xb-xa,4.4,.10),'grass')
for x in [-24,-18,14,21,27]:cube('Approach_lane_mark',(x,0,.074),(2.8,.12,.014),'line')
# Reduce sun washout and separate cool/warm team palettes.
s.view_settings.exposure=-.05
s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.48
bpy.data.objects['Warm_afternoon_sun'].data.energy=2.35
bpy.data.objects['Warm_afternoon_sun'].data.color=(1,.90,.78)
for name,col in {'mint':(.10,.38,.33),'mint_light':(.23,.56,.44),'ochre':(.71,.40,.075),'ochre_light':(.93,.61,.13),'grass':(.19,.30,.14),'grass_light':(.25,.37,.16),'leaf':(.105,.25,.14),'leaf_light':(.19,.35,.16),'leaf_bright':(.29,.43,.20),'coral':(.65,.22,.14),'rose':(.57,.25,.29),'asphalt':(.12,.17,.19),'roof':(.055,.12,.16)}.items():
 m=M[name];m.diffuse_color=(*col,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1)
# Camera composition includes the full footprint rather than cropping the rear fence.
cam=bpy.data.objects['Camera_Hero'];cam.location=(65,-75,61);cam.rotation_euler=(Vector((0,0,1.3))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=46
s.cycles.use_denoising=False;s.cycles.samples=128
# Gameplay metadata corrected after route review.
s['build_version']='1.1';s['cargo_access']='Open rear loading ramp gives a dead-end covered perch; no forward exit'
s['collision_note']='Separate simplified static triangle collision GLB includes stair ramps; engine navmesh must be baked and tested'
# A separate proxy set for STATIC triangle-mesh collision. Small decorative details excluded.
cc=bpy.data.collections.new('91_Collision_Proxies');s.collection.children.link(cc)
includes=['PLAYABLE_Base','Street_main','Central_culdesac','Sidewalk','Approach_sidewalk','Culdesac_footway','Garden_lawn','Garden_lawn','Front_grass','Driveway','Entry_path','Backyard_terrace','Backyard_lawn','Side_lane_paving','A_Mint_foundation','B_Saffron_foundation','A_Mint_ground_floor','B_Saffron_ground_floor','A_Mint_front','B_Saffron_front','A_Mint_rear','B_Saffron_rear','A_Mint_west','B_Saffron_west','A_Mint_east','B_Saffron_east','Upper_floor','Interior_room_divider','Ceiling','Gabled_roof','Garage_floor','Garage_front','Garage_rear','Garage_outer_wall','Garage_flat_roof','Balcony_floor','Garden_shed','Shed_roof','Supply_crate','Utility_cover','Jersey_barrier','Fence_board','Living_sofa','Sofa_back','Kitchen_counter','Upper_bed','Shuttle_chassis','Shuttle_body','Shuttle_window_cabin','Shuttle_roof','Shuttle_hood','Truck_chassis','Truck_cargo_floor','Truck_cargo_roof','Truck_cargo_side','Truck_cargo_bulkhead','Truck_cab','Truck_cab_glazing','Truck_cab_roof','Truck_loading_ramp','Sedan_lower','Sedan_cabin','Sedan_hood','Sedan_trunk','Planter']
for o in list(bpy.data.objects):
 if o.type!='MESH' or not any(o.name.startswith(p) for p in includes):continue
 proxy=bpy.data.objects.new('COL_'+o.name,o.data.copy());cc.objects.link(proxy);proxy.matrix_world=o.matrix_world.copy();proxy['collision']='static triangle mesh';proxy.data.materials.clear();proxy.data.materials.append(M['coral']);proxy.display_type='WIRE'
# Smooth stair ramps preserve first-person traversal; rail details remain visual.
def ramp(name,points):
 verts=points+[(x,y,z-.14) for x,y,z in points];return mesh(name,verts,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'coral',cc)
for sign in [1,-1]:
 def tr(p):
  x,y,z=p;x=-x
  if sign==-1:x,y=-x,-y
  return (x,y+sign*17,z)
 ramp('COL_InteriorRamp_'+str(sign),[tr(p) for p in [(-5.675,-3.65,.36),(-3.625,-3.65,.36),(-3.625,3.41,3.365),(-5.675,3.41,3.365)]])
 ramp('COL_ExteriorRamp_'+str(sign),[tr(p) for p in [(-11.05,5.675,.37),(-11.05,7.825,.37),(-4.02,7.825,3.375),(-4.02,5.675,3.375)]])
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for o in cc.objects:o.select_set(True)
bpy.context.view_layer.objects.active=list(cc.objects)[0];bpy.ops.object.join();collider=bpy.context.object;collider.name='COL_Sunward_Static';collider['collision']='Use static non-convex triangle mesh, never one convex hull';collider.display_type='WIRE'
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/Sunward_Collision.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
ctri=sum(len(p.vertices)-2 for p in collider.data.polygons)
cc.hide_render=True;cc.hide_viewport=True
# Save editable blend with originals and optional hidden collision proxies.
s.camera=cam
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.shading.light='STUDIO';sp.overlay.show_overlays=False;sp.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
# Evaluate and join export copies by material within semantic spatial collections.
ex=bpy.data.collections.new('99_TemporaryExport');s.collection.children.link(ex);groups={};dg=bpy.context.evaluated_depsgraph_get()
for col in list(bpy.data.collections):
 if col.name.startswith(('80_','90_','91_','99_')):continue
 for o in list(col.objects):
  if o.type not in {'MESH','CURVE','FONT'}:continue
  ev=o.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
  cp=bpy.data.objects.new(o.name+'_EXPORT',me);ex.objects.link(cp);cp.matrix_world=o.matrix_world.copy()
  key=col.name+'__'+(me.materials[0].name if me.materials else 'default');groups.setdefault(key,[]).append(cp)
for key,objects in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 if len(objects)>1:bpy.ops.object.join()
 bpy.context.object.name=key
bpy.ops.object.select_all(action='DESELECT')
for o in ex.objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/Sunward_Environment.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
tri=0
for o in ex.objects:o.data.calc_loop_triangles();tri+=len(o.data.loop_triangles)
stats={'name':'SUNWARD / TEST SITE 07','build_version':'1.1','playable_bounds_m':[58,74],'units':'meters','environment_triangles':tri,'optimized_mesh_objects':len(ex.objects),'materials':len(M),'texture_images':0,'collision_triangles':ctri,'player_capsule_m':{'height':1.8,'radius':.35,'step':.30},'validation_scope':'Geometric clearances and selected routes; not an engine playtest','approximate_dimensions':True}
with open(ROOT+'/exports/resource_stats.json','w') as f:json.dump(stats,f,indent=2)
for o in list(ex.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(ex)
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
print('REFINEMENT_EXPORT_COMPLETE',stats,flush=True)
