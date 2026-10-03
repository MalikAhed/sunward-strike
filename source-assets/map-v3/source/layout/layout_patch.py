"""Reference-traced Sunward ground and perimeter, callable in a loaded owned scene.

The input scene is not saved. Manager owns integration, house geometry, final collision.
apply(config_path=None, place_houses=True, remap_decor=True) replaces only owned ground,
perimeter, old paving veneer, stale exterior decorators and gameplay markers. It never
transforms the original joined collision. Units: Blender meters, Z up; all scale estimates
are PROVISIONAL, derived from an existing 10.5m shuttle span, not official game meters.
"""
import bpy,math,json,os,random
from mathutils import Vector,Matrix
from mathutils.geometry import tessellate_polygon
DIR=os.path.dirname(os.path.abspath(__file__))
OWN=('03_Layout_Ground','33_Layout_Perimeter','34_Layout_Decor','92_Layout_Anchors')
ALIASES={'grass':'V2_Ground_Moss','asphalt':'V2_Road','concrete':'V2_Limestone','concrete_light':'V2_Limestone','wood':'V3_Layout_Warm_Weathered_Timber','wood_light':'V3_Layout_Warm_Weathered_Timber'}

def prepare_layout_materials():
 name='V3_Layout_Warm_Weathered_Timber'
 if bpy.data.materials.get(name):return name
 source=bpy.data.materials.get('V2_Aged_Timber')
 if source is None:raise RuntimeError('Required packed textured material V2_Aged_Timber missing')
 mat=source.copy();mat.name=name;mat.diffuse_color=(.37,.265,.17,1)
 # Recolor only an owned copy of the source's original procedural color texture.
 # Preserve its grain and packed normal map; never mutate the shared source material.
 for node in mat.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image and node.image.colorspace_settings.name!='Non-Color':
   im=node.image.copy();im.name='V3_Layout_Warm_Fence_BaseColor';pix=list(im.pixels);factors=(.37/.135,.265/.115,.17/.088)
   for i in range(0,len(pix),4):
    for channel in range(3):pix[i+channel]=min(1.0,pix[i+channel]*factors[channel])
   im.pixels[:]=pix;os.makedirs(DIR+'/textures',exist_ok=True);im.filepath_raw=DIR+'/textures/V3_Layout_Warm_Fence_BaseColor.png';im.file_format='PNG';im.save();im.pack();node.image=im
 return name

def load(path=None):
 with open(path or DIR+'/site_frames.json')as f:return json.load(f)
def world(p,cfg,z=0):
 s=cfg['image_to_world']['uniform_m_per_crop_pixel'];u,v=cfg['image_to_world']['origin_crop_pixels'];return Vector(((p[0]-u)*s,(v-p[1])*s,z))
def collection(name):
 c=bpy.data.collections.get(name)
 if c is None:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
 return c

def remove_collection_objects(name):
 c=bpy.data.collections.get(name)
 if c:
  for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)

def mesh(name,verts,faces,material,col,collision=None):
 me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);collection(col).objects.link(o)
 if material:
  material=ALIASES.get(material,material);m=bpy.data.materials.get(material)
  if m is None:raise RuntimeError('Unresolved required visible material '+str(material))
  me.materials.append(m)
 uv=me.uv_layers.new(name='UVMap');texscale=5.6 if material=='V2_Ground_Moss' else(4.5 if material=='V2_Road'else(1.1 if material in {'V2_Aged_Timber','V3_Layout_Warm_Weathered_Timber'}else 2.7))
 for p in me.polygons:
  axis=max(range(3),key=lambda i:abs(p.normal[i]));axes=[1,2]if axis==0 else([0,2]if axis==1 else[0,1])
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/texscale,v[axes[1]]/texscale)
 o['layout_version']='layout-r3-family-corrected';o['layout_owner']='site layout';o['collision_role']=collision or 'visual only';return o

def poly(name,xy,z,material,col='03_Layout_Ground',collision='floor'):
 vv=[Vector((p[0],p[1],z))for p in xy]
 if sum(vv[i].x*vv[(i+1)%len(vv)].y-vv[(i+1)%len(vv)].x*vv[i].y for i in range(len(vv)))<0:vv.reverse()
 tri=tessellate_polygon([vv]);faces=[tuple(p if isinstance(p,int) else vv.index(p) for p in t)for t in tri];return mesh(name,vv,faces,material,col,collision)

class Batch:
 def __init__(self,name,material,col):self.name=name;self.material=material;self.col=col;self.v=[];self.f=[];self.pieces=0
 def cube(self,center,dim,yaw=0):
  cx,cy,cz=center;dx,dy,dz=[a/2 for a in dim];c,s=math.cos(yaw),math.sin(yaw);k=len(self.v)
  self.v.extend([(cx+c*x-s*y,cy+s*x+c*y,cz+z)for x,y,z in [(-dx,-dy,-dz),(dx,-dy,-dz),(dx,dy,-dz),(-dx,dy,-dz),(-dx,-dy,dz),(dx,-dy,dz),(dx,dy,dz),(-dx,dy,dz)]])
  self.f.extend([tuple(k+i for i in f)for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]]);self.pieces+=1
 def finish(self,collision='visual only'):
  o=mesh(self.name,self.v,self.f,self.material,self.col,collision);o['piece_count']=self.pieces;return o

def arc_band(name,ri,ro,a0,a1,z,mat,col='03_Layout_Ground',n=96,collision='floor'):
 vv=[];ff=[]
 for i in range(n+1):
  a=a0+(a1-a0)*i/n;vv.extend([(ri*math.cos(a),ri*math.sin(a),z),(ro*math.cos(a),ro*math.sin(a),z)])
 for i in range(n):ff.append((i*2,i*2+1,i*2+3,i*2+2))
 return mesh(name,vv,ff,mat,col,collision)

def build_terrain(cfg):
 s=cfg['image_to_world']['uniform_m_per_crop_pixel'];outline=[world(p,cfg)for p in cfg['outline_crop_pixels']]
 poly('LAYOUT_Playable_Grass_Outline',outline,.015,'grass')
 # Court road and eastern exit form one overlapping silhouette; .006m layer separation
 # keeps the preserved textured grass visible outside the street without coplanar fighting.
 r=cfg['court']['curb_radius_m']
 ytop=world([681,405],cfg).y-1.35;ybottom=world([680,535],cfg).y+1.35;xend=world([680.5,470],cfg).x
 atop=math.asin(ytop/r);abottom=math.asin(ybottom/r)
 # True road union outline eliminates any coplanar circle/rectangle duplicate surface.
 road=[(xend,ybottom),(xend,ytop),(math.sqrt(r*r-ytop*ytop),ytop)]
 for i in range(1,129):
  a=atop+(2*math.pi+abottom-atop)*i/128;road.append((r*math.cos(a),r*math.sin(a)))
 poly('LAYOUT_Central_Court_And_Sole_East_Exit',road,.026,'asphalt')
 # White driveway approaches are traced from BO1 overhead, transferred to official anchors.
 for name,pix in [('North_Lot_Garage_Driveway',[[434,347],[484,338],[511,425],[466,440]]),('South_Lot_Garage_Driveway',[[526,582],[580,600],[553,687],[498,668]]),('West_Pink_Court_Driveway',[[345,479],[412,453],[440,506],[366,543]])]:
  poly('LAYOUT_'+name,[world(p,cfg)for p in pix],.034,'concrete_light')
 # Curbed sidewalk ring, interrupted by sole east street mouth. 66deg mouth preserves
 # reference road-exit breadth, whose measured bbox includes the sidewalks.
 mouth=math.asin(min(.99,max(abs(ytop),abs(ybottom))/(r+1.45)));arc_band('LAYOUT_Court_Curb',r,r+.20,mouth,2*math.pi-mouth,.14,'chalk',collision='curb')
 arc_band('LAYOUT_Court_Footway',r+.20,r+1.45,mouth,2*math.pi-mouth,.11,'concrete_light')
 joints=Batch('LAYOUT_Court_Expansion_Joints','concrete','03_Layout_Ground')
 for i in range(47):
  a=mouth+(2*math.pi-2*mouth)*i/46
  joints.cube(((r+.82)*math.cos(a),(r+.82)*math.sin(a),.112),(1.21,.020,.004),a)
 joints.finish()
 for y,sgn in [(ytop,1),(ybottom,-1)]:
  poly('LAYOUT_Street_Shoulder_'+str(sgn),[(r-1,y),(xend,y),(xend,y+sgn*1.35),(r-1,y+sgn*1.35)],.11,'concrete_light')
 # Site-specific rear patio and short entry ribbons align to each house local frame.
 for id,h in cfg['house_frames'].items():
  a=h['yaw_radians'];c,t=math.cos(a),math.sin(a);cx,cy,_=h['position_blender'];b=h['components']['main_body']['local_bbox_m'];x0,y0=b[0];x1,y1=b[1]
  def tr(x,y):return (cx+c*x-t*y,cy+t*x+c*y)
  poly('LAYOUT_'+id+'_RearPatio',[tr(x0+.4,y1+.2),tr(x1-.4,y1+.2),tr(x1-.4,y1+2.5),tr(x0+.4,y1+2.5)],.04,'concrete')
  poly('LAYOUT_'+id+'_Entry_Ribbon',[tr(-1.15,y0),tr(1.15,y0),tr(1.15,y0-3.25),tr(-1.15,y0-3.25)],.05,'concrete_light')
 # No old full-width road, opposite exit, or rectangle foundation survives.
 return {'ground_objects':len(collection('03_Layout_Ground').objects),'court_radius_m_provisional':r}

def build_fences(cfg):
 pts=[world(p,cfg)for p in cfg['outline_crop_pixels']];boards=Batch('LAYOUT_Perimeter_Weathered_Boards','wood_light','33_Layout_Perimeter');posts=Batch('LAYOUT_Perimeter_Posts','wood','33_Layout_Perimeter');rails=Batch('LAYOUT_Perimeter_Rails','wood','33_Layout_Perimeter');gate=Batch('LAYOUT_East_Roadwork_Gate','mint','33_Layout_Perimeter')
 for idx,(a,b)in enumerate(zip(pts,pts[1:]+pts[:1])):
  d=b-a;l=d.length;ang=math.atan2(d.y,d.x);road=idx==4
  h=1.15 if road else 1.85
  n=max(1,math.ceil(l/2.1))
  for i in range(n+1):
   p=a+d*i/n;(gate if road else posts).cube((p.x,p.y,h/2),(.14,.14,h+.1),ang)
  for z in ([.40,.92]if road else [.40,1.50]):
   p=(a+b)/2;(gate if road else rails).cube((p.x,p.y,z),(l,.12,.12),ang)
  if not road:
   n=max(1,math.floor(l/.39))
   for i in range(n):
    p=a+d*(i+.5)/n;boards.cube((p.x,p.y,h/2),(.34,.075,h),ang)
 for batch in [boards,posts,rails,gate]:batch.finish('boundary wall')
 return {'boundary_board_pieces':boards.pieces,'boundary_post_pieces':posts.pieces}

def place_house_frames(cfg):
 report={}
 for id,h in cfg['house_frames'].items():
  roots=[o for o in bpy.context.scene.objects if o.get('house_id')==id and o.parent is None]
  if not roots:
   report[id]='No tagged prefab root found; manager must apply house patch before placement';continue
  transform=Matrix.Translation(Vector(h['position_blender']))@Matrix.Rotation(h['yaw_radians'],4,'Z')
  for o in roots:
   # House module uses one local assembly root; setting world transform is idempotent.
   o.matrix_world=transform;o['global_frame_version']=cfg['version']
  report[id]=[o.name for o in roots]
 return report

def remap_decor(cfg):
 """Move preserved individual art to reference lots. Old world-baked multi-lot batches
 are removed from the owned working copy because no single rigid transform can fit them.
 No foliage or crates are permitted to float outside the traced playable polygon.
 """
 report={'moved_trees':0,'removed_stranded_decor':[],'policy':'preserve tree meshes/materials; replace obsolete wide rectangular-yard batches; exact secondary garden dressing remains inferred'}
 old_collection=bpy.data.collections.get('30_ExteriorProps')
 protected=('Sign_post','Sunward_sign','Map_title','Map_subtitle','Clock','Nuketown','Welcome')
 # Only core classic sheds and utility props survive as grouped scenery; arbitrary old
 # six raised beds and six front planters are removed, not globally squeezed into lanes.
 if old_collection:
  for o in list(old_collection.objects):
   if o.name.startswith(protected):continue
   if o.name.startswith(('Garden_shed','Shed_roof','Shed_door','Utility_cover','Utility_vent','Supply_crate','Crate_')):continue
   report['removed_stranded_decor'].append(o.name);bpy.data.objects.remove(o,do_unlink=True)
 # Source south shed centered(-13,-33.6), north(+13,+33.6) are fixed groups; place at
 # visible tactical end-yard landmarks while keeping their original human scale.
 groups=[('shed_B',(-13,-33.6),[376,245],18.208,('Garden_shed','Shed_roof','Shed_door'),False),('shed_A',(13,33.6),[433,816],161.811,('Garden_shed.001','Shed_roof.001','Shed_door.001','Shed_door_inlay.001'),True)]
 if old_collection:
  for label,src,pix,yaw,prefix,north in groups:
   dst=world(pix,cfg);a=math.radians(yaw);oldyaw=math.pi if not north else 0;delta=a-oldyaw;T=Matrix.Translation(dst)@Matrix.Rotation(delta,4,'Z')@Matrix.Translation(Vector((-src[0],-src[1],0)))
   for o in list(old_collection.objects):
    base=o.name.split('.')[0]
    if base not in ('Garden_shed','Shed_roof','Shed_door','Shed_door_inlay'):continue
    is_north='.'in o.name
    if is_north!=north:continue
    o.matrix_world=T@o.matrix_world;o['layout_decor_group']=label
  # Other yard props move with their source house frame in a narrower normalized lot.
  for o in list(old_collection.objects):
   if o.name.startswith(protected)or o.get('layout_decor_group'):continue
   if o.type not in {'MESH','FONT','CURVE'}:continue
   bb=[o.matrix_world@Vector(p)for p in o.bound_box];cx=sum(v.x for v in bb)/8;cy=sum(v.y for v in bb)/8
   if abs(cy)<7:continue
   id='A_Mint'if cy>0 else'B_Saffron';h=cfg['house_frames'][id];sgn=1 if cy>0 else-1;scale_x=.42
   src=Vector((0,sgn*17,0));T=Matrix.Translation(Vector(h['position_blender']))@Matrix.Rotation(h['yaw_radians']-(0 if sgn>0 else math.pi),4,'Z')@Matrix.Diagonal((scale_x,1,1,1))@Matrix.Translation(-src)
   # Apply narrower placement to position, not shape; preserve source-sized props.
   p=T@o.matrix_world.translation;rot=Matrix.Rotation(h['yaw_radians']-(0 if sgn>0 else math.pi),4,'Z');o.matrix_world=rot@o.matrix_world;o.matrix_world.translation=p
   o['layout_decor_group']=id
 trees={'01':([425,159],0),'02':([538,133],0),'03':([362,766],0),'04':([556,747],0),'05':([391,384],0),'06':([566,591],0),'07':([588,340],0),'08':([407,615],0),'09':([370,280],0),'10':([573,240],0)}
 c=bpy.data.collections.get('60_V2_Foliage')
 if c:
  for tid,(pix,_)in trees.items():
   grp=[o for o in c.objects if o.name.startswith('V2_Tree_'+tid+'_')]
   if not grp:continue
   trunk=next((o for o in grp if'Branching'in o.name),grp[0]);verts=[trunk.matrix_world@v.co for v in trunk.data.vertices];low=sorted(verts,key=lambda p:p.z)[:8];src=Vector((sum(v.x for v in low)/len(low),sum(v.y for v in low)/len(low),0));dst=world(pix,cfg)
   for o in grp:o.matrix_world=Matrix.Translation(dst-src)@o.matrix_world;o['layout_decor_group']='tree_'+tid
   report['moved_trees']+=1
  for o in list(c.objects):
   if o.name.startswith(('V2_Planter_LeafyGrowth','V2_GardenBed_LeafyGrowth')) or 'Shed'in o.name:
    report['removed_stranded_decor'].append(o.name);bpy.data.objects.remove(o,do_unlink=True)
 return report

def build_site_collision(cfg):
 col=collection('V3_COLLISION')
 for o in list(col.objects):
  if o.name.startswith('COL_V3_LAYOUT_'):bpy.data.objects.remove(o,do_unlink=True)
 floor=poly('COL_V3_LAYOUT_PlayableFloor',[world(p,cfg)for p in cfg['outline_crop_pixels']],.014,None,'V3_COLLISION','floor')
 clips=Batch('COL_V3_LAYOUT_OutlineClips',None,'V3_COLLISION');pts=[world(p,cfg)for p in cfg['outline_crop_pixels']]
 for a,b in zip(pts,pts[1:]+pts[:1]):
  d=b-a;p=(a+b)/2;clips.cube((p.x,p.y,2.0),(d.length,.14,4.0),math.atan2(d.y,d.x))
 wall=clips.finish('invisible boundary clip');created=[floor,wall]
 # Retained solid garden props remain physical after the obsolete joined collider is
 # removed. Preserve their oriented visible bounding box, not a world-axis inflated box.
 c=bpy.data.collections.get('30_ExteriorProps')
 if c:
  for source in c.objects:
   base=source.name.split('.')[0]
   if source.type!='MESH' or base not in {'Garden_shed','Supply_crate','Utility_cover'}:continue
   vv=[Vector(p)for p in source.bound_box];lo=[min(p[i]for p in vv)for i in range(3)];hi=[max(p[i]for p in vv)for i in range(3)]
   x0,y0,z0=lo;x1,y1,z1=hi
   raw=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
   verts=[source.matrix_world@Vector(p)for p in raw];faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
   o=mesh('COL_V3_LAYOUT_Prop_'+source.name,verts,faces,None,'V3_COLLISION','solid retained prop');o['source_visual']=source.name;o['proxy_type']='oriented bounding box';source['collision_proxy']=o.name;created.append(o)
 # Tree trunks alone block the capsule; branches and folded leaves are explicitly
 # decorative. A tight base radius prevents the old large branch bbox from closing lanes.
 c=bpy.data.collections.get('60_V2_Foliage')
 if c:
  for source in c.objects:
   if source.type!='MESH'or not source.name.startswith('V2_Tree_')or 'Branching'not in source.name:continue
   verts=[source.matrix_world@v.co for v in source.data.vertices];low=sorted(verts,key=lambda p:p.z)[:8];cx=sum(v.x for v in low)/len(low);cy=sum(v.y for v in low)/len(low);z0=min(p.z for p in low)
   radius=max(.12,min(.30,max(math.hypot(v.x-cx,v.y-cy)for v in low)));n=12;v=[]
   for z in [min(.014,z0),2.2]:
    for i in range(n):a=2*math.pi*i/n;v.append((cx+radius*math.cos(a),cy+radius*math.sin(a),z))
   f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]
   o=mesh('COL_V3_LAYOUT_Trunk_'+source.name.split('_')[2],v,f,None,'V3_COLLISION','solid tree trunk');o['source_visual']=source.name;o['proxy_type']='12-sided tight trunk cylinder; decorative branches excluded';source['collision_proxy']=o.name;created.append(o)
 for o in created:o.display_type='WIRE';o.hide_render=True
 col.hide_render=True
 return [o.name for o in created]

def relocate_front_crate_stacks(config_path=None):
 """Route-safe correction callable on already integrated copies; idempotent per object."""
 cfg=load(config_path);moved=[]
 for source in list(bpy.context.scene.objects):
  name=source.name;house_id=None
  if name in {'Supply_crate.004','Supply_crate.005'}:house_id='B_Saffron'
  elif name in {'Supply_crate.010','Supply_crate.011'}:house_id='A_Mint'
  elif name.startswith(('Crate_band.','Crate_brace.')):
   try:i=int(name.rsplit('.',1)[1])
   except ValueError:continue
   if 8<=i<=11:house_id='B_Saffron'
   elif 20<=i<=23:house_id='A_Mint'
  if house_id is None or source.get('front_crate_relocated_r1'):continue
  yaw=cfg['house_frames'][house_id]['yaw_radians'];delta=Vector((-math.sin(yaw)*16.8,math.cos(yaw)*16.8,0));source.matrix_world=Matrix.Translation(delta)@source.matrix_world;source['front_crate_relocated_r1']=True;source['route_clearance_reason']='inherited front-garage stack moved16.8m along house local rear axis to clear authored garage approaches';moved.append(name)
 return moved

def create_markers(cfg):
 col=collection('92_Layout_Anchors');report=[]
 def marker(name,pos,props):
  o=bpy.data.objects.new('LAYOUT_ANCHOR_'+name,None);col.objects.link(o);o.location=pos;o.empty_display_size=.25;o['purpose']='integration anchor only; not visual export or collider';o['layout_version']=cfg['version']
  for k,v in props.items():o[k]=v
  report.append(o.name)
 for name,p in cfg['walk_spawns'].items():marker('Spawn_'+name,p,{'anchor_type':'spawn','height_includes_player_eye':True})
 for id,anchors in cfg['traversal_anchors'].items():
  if id=='three_lanes':
   for lane,seg in anchors.items():
    for end,p in seg.items():marker(lane+'_'+end,p,{'anchor_type':'lane'})
  else:
   for k,p in anchors.items():
    if isinstance(p,list):marker(id+'_'+k,p,{'anchor_type':'house route','provisional':True})
 return report

def apply(config_path=None,place_houses=True,remap_decorations=True,build_collision=True):
 cfg=load(config_path);scene=bpy.context.scene;prepare_layout_materials()
 if scene.get('canonical_layout_patch')==cfg['version']:
  return {'status':'already applied','version':cfg['version']}
 for name in OWN:remove_collection_objects(name)
 # Old ground and boundary are exclusively this worker's owned surfaces.
 for name in ['00_Ground','31_Boundary','90_Gameplay']:remove_collection_objects(name)
 c=bpy.data.collections.get('61_V2_Architecture')
 if c:
  for o in list(c.objects):
   if o.name.startswith('SW2_Arch_Paving_'):bpy.data.objects.remove(o,do_unlink=True)
 report={'version':cfg['version'],'scale_assumption':cfg['scale_assumption'],'source_geometry_preserved':'all original scene files untouched; this patch mutates only caller-owned scene','collision':'original joined collision left untouched and must be regenerated by manager','terrain':build_terrain(cfg),'boundary':build_fences(cfg)}
 if place_houses:report['house_placement']=place_house_frames(cfg)
 if remap_decorations:
  report['decor']=remap_decor(cfg);report['front_crate_route_correction']=relocate_front_crate_stacks(config_path)
 report['markers']=create_markers(cfg)
 if build_collision:report['collision_proxies']=build_site_collision(cfg)
 scene['canonical_layout_patch']=cfg['version'];scene['layout_reference']='Official classic Nuketown uniform traced outline; meter calibration provisional';scene['playable_footprint_m']='irregular traced outline; provisional scale bus10.5m';scene['boundary_collision']='Regenerate from LAYOUT perimeter meshes; old joined collider obsolete';scene['build_version']='3.0-structure-working';scene['layout_scale_m_per_crop_pixel']=cfg['image_to_world']['uniform_m_per_crop_pixel'];bpy.context.view_layer.update();return report

if __name__=='__main__':
 import sys
 cfg=load();report=apply(place_houses=False);out=DIR+'/layout_ground_r3_family.blend';bpy.ops.wm.save_as_mainfile(filepath=out);json.dump(report,open(DIR+'/layout_patch_report.json','w'),indent=2);print('LAYOUT_PATCH_DONE',out)
