"""Optional reversible source-owned interior transplant for corrected house-r6.

apply(config_path=None) appends only protected baseline furniture meshes, places groups
in new local rooms, adds simple source-linked COL_V3_D3_* group boxes, and returns route
clearance evidence. It never saves/exports or edits the baseline/house/layout modules.
remove() removes only D3_* objects. Apply AFTER houses/layout. Coordinates are local
Blender X façade-right/Yrear/Zup under the existing HOUSE_ROOT/parent collider root.
"""
import bpy,os,json,math,hashlib
from mathutils import Vector,Matrix
DIR=os.path.dirname(__file__);BASE='/workspace/shared/stylized-nuketown-map/Sunward_TestSite.blend';CFG=os.path.dirname(DIR)+'/site_frames.json';COL='56_V3_Interior_Dressing';PREF='D3_';CPREF='COL_V3_D3_'
GROUPS={'Sofa':('Living_sofa','Sofa_back'),'Rug':('Living_rug',),'Coffee':('Coffee_table','Coffee_leg'),'Kitchen':('Kitchen_counter','Kitchen_countertop'),'Bed':('Upper_bed','Upper_bed_cover','Upper_pillow'),'Desk':('Upper_desk','Desk_leg'),'Workbench':('Workbench','Bench_leg'),'Storage':('Garage_storage',)}

def collection(name):
 c=bpy.data.collections.get(name)
 if c is None:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
 return c

def remove():
 names=[]
 for o in list(bpy.data.objects):
  if o.name.startswith((PREF,CPREF)):
   names.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
 return names

def parent_root(name,parent,col,matrix_world):
 o=bpy.data.objects.new(name,None);collection(col).objects.link(o)
 if parent:o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
 else:o.matrix_world=matrix_world
 o['dressing_owner']='optional source-owned interior transplant';return o

def worldbounds(objects,local=False):
 p=[(o.matrix_local if local else o.matrix_world)@Vector(v)for o in objects for v in o.bound_box]
 return [[min(v[i]for v in p)for i in range(3)],[max(v[i]for v in p)for i in range(3)]]

def bounds_in_parent(objects,parent):
 # Read after dependency evaluation and convert actual world vertices into the proxy
 # parent's space. Never rely on a freshly parented object's cached matrix_local.
 bpy.context.view_layer.update()
 inv=parent.matrix_world.inverted();points=[inv@(o.matrix_world@v.co)for o in objects for v in o.data.vertices]
 return [[min(p[i]for p in points)for i in range(3)],[max(p[i]for p in points)for i in range(3)]]

def intersect_segment_box(a,b,lo,hi,margin):
 # Slab clipping in2D; furniture is axis-aligned after the authored90deg group turns.
 t0,t1=0,1
 for i in range(2):
  d=b[i]-a[i];l=lo[i]-margin;h=hi[i]+margin
  if abs(d)<1e-10:
   if a[i]<l or a[i]>h:return False
  else:
   u,v=(l-a[i])/d,(h-a[i])/d
   if u>v:u,v=v,u
   t0=max(t0,u);t1=min(t1,v)
   if t0>t1:return False
 return True

def routes_for_house(data,floor):
 out=[]
 for id,p in data['portals'].items():
  a=p['negative_axis_approach']['local_blender'];b=p['positive_axis_approach']['local_blender']
  if abs(a[2]-floor)<.25:out.append((id,a,b,.55))
 r=data['routes']
 if abs(floor-data['floor_ground_z'])<.2:
  p=data['portals'];out.extend([('front_to_room',p['front_door']['positive_axis_approach']['local_blender'],p['room_passage']['negative_axis_approach']['local_blender'],.55),('room_to_rear',p['room_passage']['positive_axis_approach']['local_blender'],p['rear_door']['negative_axis_approach']['local_blender'],.55),('front_to_stairs',p['front_door']['positive_axis_approach']['local_blender'],r['interior_stairs']['bottom']['local_blender'],.55),('garage_through',p['garage_front']['positive_axis_approach']['local_blender'],p['garage_rear']['negative_axis_approach']['local_blender'],.55),('stairs_ground',r['interior_stairs']['bottom']['local_blender'],r['interior_ramp_support']['start']['local_blender'],.85)])
 else:
  q=r['upper_rooms'];out.extend([('front_room_to_passage',q['front_room']['local_blender'],q['passage']['local_blender'],.55),('passage_to_rear',q['passage']['local_blender'],q['rear_room']['local_blender'],.55),('rear_to_balcony',q['rear_room']['local_blender'],q['balcony_door']['local_blender'],.55),('upper_stairs_to_frontroom',r['interior_stairs']['top']['local_blender'],q['front_room']['local_blender'],.55)])
 return out

def box_proxy(name,bbox,col,parent,visuals,floor):
 lo,hi=bbox;x0,y0,z0=lo;x1,y1,z1=hi
 # Fill the furniture group tofloor rather than making unreachable gaps under tabletops.
 z0=min(z0,floor)
 v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)];f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
 me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);collection(col).objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4);o.display_type='WIRE';o.hide_render=True;o['collision_role']='solid furniture group';o['source_visuals']=visuals;o['proxy_type']='group oriented bounding box; fills table/bed underside to floor; no walking underneath';o['dressing_version']='interior-dressing-r1';return o

def apply(config_path=None,route_contract_path=None,include_style=True):
 cfg=json.load(open(config_path or CFG));routes=json.load(open(route_contract_path))if route_contract_path else cfg.get('final_house_route_contract');cfg['final_house_route_contract']=routes
 if not routes or routes.get('layout_version')!=cfg['version']:raise RuntimeError('Matching corrected-family final house route contract required')
 for id in cfg['house_frames']:
  if not bpy.data.objects.get('HOUSE_ROOT_'+id):raise RuntimeError('Apply after local house patch and global layout: missing HOUSE_ROOT_'+id)
 before=hashlib.sha256(open(BASE,'rb').read()).hexdigest();remove();c=collection(COL);cc=collection('V3_COLLISION');cc.hide_render=True
 inventory=json.load(open(DIR+'/source_furniture_inventory.json'));names=[q['name']for q in inventory];lookup={q['name']:q for q in inventory};existing_mats={m.name:m for m in bpy.data.materials}
 with bpy.data.libraries.load(BASE,link=False)as(src,dst):dst.objects=list(names)
 src_objects={n:o for n,o in zip(names,dst.objects)if o is not None};buckets={id:{k:[]for k in GROUPS}for id in cfg['house_frames']}
 for old,o in src_objects.items():
  id=lookup[old]['properties']['building'];base=old.split('.')[0];key=next(k for k,parts in GROUPS.items()if base in parts)
  # Data-library append can create duplicate materials. Reuse only exact source slots,
  # never alter existing shared nodes/colors or source mesh/UV data.
  for i,m in enumerate(o.data.materials):
   name=lookup[old]['materials'][i]
   if name in existing_mats:o.data.materials[i]=existing_mats[name]
  for col in list(o.users_collection):col.objects.unlink(o)
  c.objects.link(o);o.name=PREF+id+'_'+old;o.hide_render=False;o.hide_viewport=False;o['baseline_source_object']=old;o['baseline_source_sha256']=before;o['dressing_owner']='optional source-owned interior transplant';o['dressing_group']=key;o['dressing_house']=id;o['dressing_version']='interior-dressing-r1';buckets[id][key].append(o)
 report={'version':'interior-dressing-r1','canonical_frame_version':cfg['version'],'house_route_version':routes['version'],'protected_source':BASE,'protected_source_sha256':before,'scope':'source sofa/rug/coffee/kitchen/bed/desk/workbench/storage only; no house/layout edits','groups':[],'unresolved_route_overlaps':[],'collision_proxies':[],'visual_objects':40}
 for id,h in cfg['house_frames'].items():
  data=routes['houses'][id];root=parent_root(PREF+'ROOT_'+id,bpy.data.objects['HOUSE_ROOT_'+id],COL,None);cro=parent_root(CPREF+'ROOT_'+id,bpy.data.objects.get('COL_HOUSE_ROOT_'+id),'V3_COLLISION',Matrix.Translation(Vector(h['position_blender']))@Matrix.Rotation(h['yaw_radians'],4,'Z'))
  m=h['components']['main_body']['local_bbox_m'];g=h['components']['garage']['local_bbox_m'];x0,y0=m[0];x1,y1=m[1];gx0,gy0=g[0];gx1,gy1=g[1];fg=data['floor_ground_z'];fu=data['floor_upper_z'];sofax=x0+.525+.35;sofay=y0+3.2
  plan={'Sofa':(sofax,sofay,fg,math.pi/2),'Rug':(x0+1.6+.20,sofay,fg+.007,math.pi/2),'Coffee':(sofax+1.30,sofay,fg,math.pi/2),'Kitchen':(x0+1.275+.3,y1-.60-.30,fg,0),'Bed':(x0+1.025+.35,y1-1.625-.35,fu,0),'Desk':(x0+1.10+.35,y0+2.3,fu,0),'Workbench':(gx0+.675+.25,gy0+1.2+.35,fg,0),'Storage':(gx0+.35+.25,gy1-.85-.35,fg,0)}
  srcroot=Vector(h['source_baseline_root']);srcyaw=math.radians(h['source_baseline_yaw_degrees']);unwind=Matrix.Rotation(-srcyaw,4,'Z')@Matrix.Translation(-srcroot)
  for group,objects in buckets[id].items():
   if not objects:continue
   local_matrices={o.name:unwind@o.matrix_world.copy()for o in objects};verts=[local_matrices[o.name]@Vector(p)for o in objects for p in o.bound_box];lo=[min(p[i]for p in verts)for i in range(3)];hi=[max(p[i]for p in verts)for i in range(3)];center=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]));x,y,z,a=plan[group];T=Matrix.Translation(Vector((x,y,z)))@Matrix.Rotation(a,4,'Z')@Matrix.Translation(-center)
   for o in objects:o.parent=root;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=T@local_matrices[o.name]
   bpy.context.view_layer.update();bb=bounds_in_parent(objects,cro);floor=fu if group in {'Bed','Desk'}else fg;solid=group!='Rug';test=[]
   if solid:
    for label,aa,b,margin in routes_for_house(data,floor):
     if intersect_segment_box(aa,b,bb[0],bb[1],margin):test.append(label)
    if test:
     report['unresolved_route_overlaps'].append({'house':id,'group':group,'routes':test,'bbox_local':bb})
    proxy=box_proxy(CPREF+id+'_'+group,bb,'V3_COLLISION',cro,[o.name for o in objects],floor);report['collision_proxies'].append(proxy.name)
    for o in objects:o['collision_proxy']=proxy.name
   else:
    for o in objects:o['collision_role']='flat rug decoration; excludes collision'
   report['groups'].append({'house_id':id,'group':group,'source_objects':[o['baseline_source_object']for o in objects],'visual_objects':[o.name for o in objects],'proxy':CPREF+id+'_'+group if solid else None,'bbox_local':bb,'floor_z':floor,'pose_source':'repositioned by corrected local room/garage bounds; bottom anchored to new floor; preserved source geometry/material/UV','route_envelope_clear':not test,'route_overlaps':test})
 if include_style:
  import sys
  if DIR not in sys.path:sys.path.insert(0,DIR)
  import interior_style
  interior_style.apply(cfg,buckets,report,sys.modules[__name__]);report['version']='interior-dressing-r3-proxyfixed';report['style_component_version']='interior-style-r2';report['proxy_component_version']='r3-evaluated-world-to-parent-space'
 after=hashlib.sha256(open(BASE,'rb').read()).hexdigest();report['baseline_unchanged']=after==before;report['complete']=not report['unresolved_route_overlaps'];dg=bpy.context.evaluated_depsgraph_get();tri=0
 for o in c.objects:
  if o.type=='MESH':ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();tri+=len(me.loop_triangles);ev.to_mesh_clear()
 report['original_source_visual_objects']=40;report['visual_objects']=sum(o.type=='MESH'for o in c.objects);report['evaluated_visual_triangles']=tri;report['collision_triangles']=len(report['collision_proxies'])*12;bpy.context.view_layer.update();return report
