"""OPTIONAL original folded-blade grass; no collider/layout/shader changes.
apply(config_path=None, target_tufts=3000, seed=20261003) can be called after final layout.
One batched mesh / four constant Principled materials; parameterized added-triangle budget; final combined-map budget is reviewed separately. Routes,
street, driveways, patios, house footprints and solid prop bases stay clear.
"""
import bpy,os,json,random,math
from mathutils import Vector
D=os.path.dirname(__file__);COL='35_Layout_Grass';NAME='V3_Layout_Edge_Grass';PALETTE=[(.24,.29,.075),(.36,.42,.11),(.48,.50,.13),(.18,.23,.06)]
def inside(p,poly):
 x,y=p;odd=False
 for (ax,ay),(bx,by)in zip(poly,poly[1:]+poly[:1]):
  if (ay>y)!=(by>y)and x<(bx-ax)*(y-ay)/(by-ay)+ax:odd=not odd
 return odd

def segdist(p,a,b):
 x,y=p;ax,ay=a;bx,by=b;dx,dy=bx-ax,by-ay;l=dx*dx+dy*dy;t=0 if l==0 else max(0,min(1,((x-ax)*dx+(y-ay)*dy)/l));return math.hypot(x-ax-t*dx,y-ay-t*dy)
def edgedist(p,poly):return min(segdist(p,a,b)for a,b in zip(poly,poly[1:]+poly[:1]))

def apply(config_path=None,target_tufts=3000,seed=20261003,max_added_triangles=120000):
 cfg=json.load(open(config_path or D+'/site_frames.json'));rng=random.Random(seed);s=bpy.context.scene
 c=bpy.data.collections.get(COL)
 if c:
  for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
 else:c=bpy.data.collections.new(COL);s.collection.children.link(c)
 mats=[]
 for i,color in enumerate(PALETTE):
  name='V3_Grass_YellowGreen_'+str(i);m=bpy.data.materials.get(name)or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);pr=m.node_tree.nodes.get('Principled BSDF');pr.inputs['Base Color'].default_value=(*color,1);pr.inputs['Roughness'].default_value=.95;pr.inputs['Metallic'].default_value=0;mats.append(m)
 outline=[p[:2]for p in cfg['outline_blender']];mask=[]
 for h in cfg['house_frames'].values():
  for q in h['components'].values():
   mask.append([p[:2]for p in q['blender']]);b=q['local_bbox_m'];a=h['yaw_radians'];co,si=math.cos(a),math.sin(a);cx,cy,_=h['position_blender'];mask.append([(cx+co*x-si*y,cy+si*x+co*y)for x,y in [(b[0][0],b[0][1]),(b[1][0],b[0][1]),(b[1][0],b[1][1]),(b[0][0],b[1][1])]])
 ground=bpy.data.collections.get('03_Layout_Ground')
 if ground:
  for o in ground.objects:
   if o.type!='MESH'or o.name=='LAYOUT_Playable_Grass_Outline'or o.name=='LAYOUT_Court_Expansion_Joints':continue
   if o.name.startswith('LAYOUT_Court_'):continue # separately masked by circle radius below
   mask.append([(o.matrix_world@v.co).to_2d()[:]for v in o.data.vertices])
 routes=[];route_points=[]
 for id,a in cfg['traversal_anchors'].items():
  if id=='three_lanes':
   for lane,q in a.items():routes.append((q['start'][:2],q['end'][:2]))
  else:
   for p in a.values():
    if isinstance(p,list):route_points.append(p[:2])
 for h in cfg.get('final_house_route_contract',{}).get('houses',{}).values():
  for portal in h['portals'].values():routes.append((portal['negative_axis_approach']['world_blender'][:2],portal['positive_axis_approach']['world_blender'][:2]))
  for q in h['routes'].values():
   if 'bottom'in q and'top'in q:routes.append((q['bottom']['world_blender'][:2],q['top']['world_blender'][:2]))
   if 'waypoints'in q:
    p=[a['world_blender'][:2]for a in q['waypoints']];routes.extend(zip(p,p[1:]))
 route_points.extend(p[:2]for p in cfg['walk_spawns'].values())
 props=[]
 old=bpy.data.collections.get('30_ExteriorProps')
 if old:
  for o in old.objects:
   if o.type=='MESH'and o.name.split('.')[0]in {'Garden_shed','Supply_crate','Utility_cover'}:
    bb=[o.matrix_world@Vector(p)for p in o.bound_box];props.append((min(p.x for p in bb)-.3,max(p.x for p in bb)+.3,min(p.y for p in bb)-.3,max(p.y for p in bb)+.3))
 xmin,xmax=min(p[0]for p in outline),max(p[0]for p in outline);ymin,ymax=min(p[1]for p in outline),max(p[1]for p in outline);r=cfg['court']['curb_radius_m']+1.7
 def allowed(p):
  if not inside(p,outline)or edgedist(p,outline)<.40:return False
  if math.hypot(*p)<r:return False
  for poly in mask:
   if len(poly)>2 and(inside(p,poly)or edgedist(p,poly)<.40):return False
  if any(segdist(p,a,b)<1.85 for a,b in routes):return False
  if any(math.dist(p,a)<1.85 for a in route_points):return False
  if any(a<=p[0]<=b and c<=p[1]<=d for a,b,c,d in props):return False
  return True
 v=[];f=[];mi=[];points=[];attempts=0;target_tufts=min(max_added_triangles//30,int(target_tufts))
 while len(points)<target_tufts and attempts<200000:
  attempts+=1;p=(rng.uniform(xmin,xmax),rng.uniform(ymin,ymax))
  if not allowed(p):continue
  edge=edgedist(p,outline);house=min(edgedist(p,q)for q in mask)if mask else 99
  # Concentrate tufts near fence/yard edges, with a few calm interior patchlets.
  if edge>2.7 and house>1.1 and rng.random()>.10:continue
  if any(math.dist(p,a)<.17 for a in points):continue
  points.append(p)
  for i in range(6):
   a=rng.uniform(0,2*math.pi);ca,sa=math.cos(a),math.sin(a);nx,ny=-sa,ca;h=rng.uniform(.16,.42);w=rng.uniform(.035,.065);lean=rng.uniform(.055,.15);spread=rng.uniform(0,.12);x=p[0]+ca*spread;y=p[1]+sa*spread;z=.019;k=len(v)
   v.extend([(x-nx*w,y-ny*w,z),(x+nx*w,y+ny*w,z),(x+ca*lean*.5-nx*w*.65,y+sa*lean*.5-ny*w*.65,z+h*.58),(x+ca*lean*.50,y+sa*lean*.50,z+h*.64),(x+ca*lean*.5+nx*w*.65,y+sa*lean*.5+ny*w*.65,z+h*.58),(x+ca*lean,y+sa*lean,z+h)])
   f.extend([(k,k+1,k+3),(k,k+3,k+2),(k+1,k+4,k+3),(k+2,k+3,k+5),(k+3,k+4,k+5)]);mat=rng.choices(range(4),weights=[4,4,1,2])[0];mi.extend([mat]*5)
 me=bpy.data.meshes.new(NAME+'_Mesh');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(NAME,me);c.objects.link(o)
 for m in mats:me.materials.append(m)
 for p,i in zip(me.polygons,mi):p.material_index=i
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co.x,co.y)
 o['collision_role']='visual grass; EXCLUDE collision';o['art_authority']='User collage grass/yard panel only; never used as layout source';o['route_clearance_m']=1.5;o['max_blade_height_m']=.42;o['seed']=seed;o['original_geometry']=True;o['grass_version']='grass-r2-dense'
 me.calc_loop_triangles();tri=len(me.loop_triangles)
 if tri>max_added_triangles:raise RuntimeError('Optional grass budget exceeded')
 report={'version':'grass-r2-dense','triangles':tri,'tufts':len(points),'blades':len(points)*6,'mesh_objects':1,'materials':4,'estimated_material_draw_groups':4,'measured_runtime_draw_calls':'not measured','maximum_blade_height_m':.42,'requested_tuft_count':target_tufts,'max_added_triangle_budget':max_added_triangles,'scene_total_triangle_budget_provisional':400000,'scene_glb_limit_mb_provisional':32,'route_buffers_m':1.5,'tuft_center_route_buffer_m':1.85,'maximum_tuft_blade_horizontal_reach_m':.335,'layout_or_collider_modified':False,'position_samples':points,'palette_linear_rgb':PALETTE,'source_palette_notes':'Collage lawn panel crop(1110..1530,535..688) yellow-olive SRGB samples q25(104,106,48),median(126,125,55),q75(151,146,61); palette art-tuned for neutral daylight, not direct RGB identity','all_tuft_centers_mask_valid':all(allowed(p)for p in points),'sampling_attempts':attempts}
 return report

if __name__=='__main__':
 report=apply();json.dump(report,open(D+'/grass_r2_report.json','w'),indent=2);bpy.ops.wm.save_as_mainfile(filepath=D+'/layout_grass_r2_dense.blend');print('GRASS_OPTIONAL',report['triangles'],report['tufts'])
