"""Reversible vegetation-v4-r5 candidate on accepted classic layout.
Ten existing tree anchors. Standard glTF MASK leaf-cluster atlas + opaque grass/bark.
Only owned tree/lawn meshes and bindings change; all collision and other meshes remain.
Native saved restore returns exact RC1 geometry/material bindings. No runtime custom shaders.
"""
import bpy,json,math,random,os,hashlib
from mathutils import Vector,Matrix
DIR=os.path.dirname(__file__);VERSION='vegetation-v4-r5';SUN=Vector((-.55,-.36,.76)).normalized()
LEAF=[(.018,.095,.075),(.03,.16,.095),(.07,.24,.11),(.13,.32,.11),(.23,.42,.095),(.35,.53,.075),(.42,.59,.055),(.49,.65,.065)]
BARK=[(.23,.075,.023),(.42,.16,.045),(.62,.29,.075)]
GRASS=[(.045,.19,.09),(.18,.35,.06),(.38,.54,.045),(.55,.65,.075)]

def mat(name,color):
 m=bpy.data.materials.get(name)or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.95;p.inputs['Metallic'].default_value=0;return m

def leaf_atlas_material(texture_path=None):
 path=texture_path or os.path.join(DIR,'textures','sunward_broadleaf_clusters_r5.png')
 if not os.path.exists(path):raise RuntimeError('Missing original leaf atlas '+path)
 m=bpy.data.materials.get('V4R5_Canopy_LeafAtlas')or bpy.data.materials.new('V4R5_Canopy_LeafAtlas');m.use_nodes=True;m.use_backface_culling=False;m.surface_render_method='DITHERED';m.node_tree.nodes.clear()
 nt=m.node_tree;out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Roughness'].default_value=.93;bs.inputs['Metallic'].default_value=0;tex=nt.nodes.new('ShaderNodeTexImage');im=bpy.data.images.load(path,check_existing=True);im.name='V4R5_Original_Broadleaf_Cluster_Atlas';im.colorspace_settings.name='sRGB';im.pack();tex.image=im;tex.interpolation='Linear';tex.extension='EXTEND';alpha=nt.nodes.new('ShaderNodeMath');alpha.operation='ROUND'
 nt.links.new(tex.outputs['Color'],bs.inputs['Base Color']);nt.links.new(tex.outputs['Alpha'],alpha.inputs[0]);nt.links.new(alpha.outputs[0],bs.inputs['Alpha']);nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
 m['gltf_alpha_contract']='MASK cutoff0.5; doubleSided true; standard image color/alpha, no custom shader';m['vegetation_revision']=VERSION;m['original_procedural_texture']=True;m['skip_reference_palette_tint']=True;return m

def collider_hash():
 bpy.context.view_layer.update();r=[]
 for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
  if o.type=='MESH'and o.name.startswith('COL_'):r.append([o.name,[list(v.co)for v in o.data.vertices],[list(p.vertices)for p in o.data.polygons],[list(row)for row in o.matrix_world]])
 return hashlib.sha256(json.dumps(r,separators=(',',':')).encode()).hexdigest()

def segdist(p,a,b):
 d=b-a;t=max(0,min(1,(p-a).dot(d)/max(1e-12,d.length_squared)));return (p-a-t*d).length

def inside(p,poly):
 odd=False;x,y=p
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if(a[1]>y)!=(b[1]>y)and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:odd=not odd
 return odd

class Batch:
 def __init__(self):self.v=[];self.f=[];self.mi=[];self.sm=[];self.uvs=[];self.has_uvs=False
 def face(self,ids,material,smooth=False):self.f.append(tuple(ids));self.mi.append(material);self.sm.append(smooth)
 def add(self,verts,faces,materials,smooth=False,uvs=None):
  k=len(self.v);self.v.extend(verts);self.uvs.extend(uvs if uvs is not None else [(0,0)]*len(verts));self.has_uvs=self.has_uvs or uvs is not None
  for f,i in zip(faces,materials):self.face([k+j for j in f],i,smooth)
 def mesh(self,name,mats,smooth=False):
  me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.update()
  for m in mats:me.materials.append(m)
  for p,i,sm in zip(me.polygons,self.mi,self.sm):p.material_index=i;p.use_smooth=sm
  if self.has_uvs:
   uv=me.uv_layers.new(name='LeafAtlasUV')
   for loop in me.loops:uv.data[loop.index].uv=self.uvs[loop.vertex_index]
  return me

def color_normal(n):
 dot=n.dot(SUN)
 if n.z<-.25 or dot<-.22:return 0
 if n.z>.35 and dot>.40:return 3
 if dot>.18:return 2
 return 1

def sphere(c,r,n=12,rings=6):
 v=[]
 for j in range(rings+1):
  th=math.pi*j/rings
  for i in range(n):a=2*math.pi*i/n;v.append(Vector((c.x+r.x*math.sin(th)*math.cos(a),c.y+r.y*math.sin(th)*math.sin(a),c.z+r.z*math.cos(th))))
 f=[]
 for j in range(rings):
  for i in range(n):
   k=j*n+i;kk=j*n+(i+1)%n;a=(k,kk,k+n);b=(kk,kk+n,k+n)
   if j>0:f.append(a)
   if j<rings-1:f.append(b)
 mi=[]
 for idx,q in enumerate(f):
  pa,pb,pc=[v[k]for k in q];normal=(pb-pa).cross(pc-pa);center=(pa+pb+pc)/3
  if normal.dot(center-c)<0:f[idx]=tuple(reversed(q));normal=-normal
  mi.append(color_normal(normal.normalized()))
 return v,f,mi

def leaf(c,n,rng,length=None,width=None,base_index=None):
 # Four triangles per shallow-curved card, carrying five small original rounded
 # leaf silhouettes. The packed matte atlas supplies fine scalloped edges; this
 # avoids expensive oversized polygon plates and never copies reference pixels.
 down=Vector((0,0,-1));long=down-n*down.dot(n)
 if long.length<.15:long=Vector((1,0,0))-n*n.x
 long.normalize();wide=n.cross(long).normalized();a=rng.uniform(-1.1,1.1)
 long,wide=long*math.cos(a)+wide*math.sin(a),wide*math.cos(a)-long*math.sin(a)
 length=length or rng.uniform(.66,.94);width=width or length*rng.uniform(.86,1.04);idx=base_index or 0;col=idx%4;row=idx//4;v=[];uv=[]
 for yy,bend in [(-.5,0),(0,.07),(.5,-.02)]:
  for xx in[-.5,.5]:
   v.append(c+long*(yy*length)+wide*(xx*width)+n*bend)
   uv.append(((col+xx+.5)/4,1-(row+yy+.5)/2))
 f=[(0,1,2),(1,3,2),(2,3,4),(3,5,4)]
 for j,q in enumerate(f):
  if (v[q[1]]-v[q[0]]).cross(v[q[2]]-v[q[0]]).dot(n)<0:f[j]=tuple(reversed(q))
 return v,f,[0]*4,uv

def keep_triangle(points,houses,upper_routes):
 # Keep new foliage outside occupied house prisms and off upper walking/head space.
 for p in points:
  if p.z<2.25:return False
  for h in houses:
   if p.z<8.9 and inside((p.x,p.y),h):return False
  if 3.0<p.z<5.35:
   if any(segdist(Vector((p.x,p.y)),a,b)<.80 for a,b in upper_routes):return False
 return True

def crown(old,anchor,oldbbox,houses,upper_routes,rng,mats):
 lo,hi=oldbbox;w=(hi.x-lo.x)*1.20;d=(hi.y-lo.y)*1.18;height=(hi.z-lo.z)*1.35;cz=(lo.z+hi.z)/2;lobes=[]
 # Same inherited envelope and anchor as r1, revised into a tiered rounded crown.
 # Lobes are sampling volumes only; removing their closed surfaces eliminates the
 # visibly naked mushroom cores and allows the branch forks to read through gaps.
 # Uneven primary limb fans and smaller drooping perimeter clusters; no ring
 # with equal-size balls and no repeated topiary pod silhouette.
 primary=[(-.28,-.13,-.17),(-.12,-.28,-.10),(.15,-.25,-.17),(.31,-.07,-.10),(.26,.19,-.035),(.02,.27,-.12),(-.23,.23,-.08),(-.31,.065,-.12),(-.12,-.09,.17),(.16,-.08,.23),(.13,.15,.27),(-.14,.13,.21),(-.015,.02,.39)]
 phase=rng.uniform(-.22,.22);cp,sp=math.cos(phase),math.sin(phase)
 for i,(xx,yy,zz)in enumerate(primary):
  xx,yy=xx*cp-yy*sp,xx*sp+yy*cp;ss=rng.uniform(.78,1.18);rx=rng.uniform(.145,.19);ry=rng.uniform(.145,.21);rz=rng.uniform(.22,.30)
  lobes.append((Vector((anchor.x+(xx+rng.uniform(-.023,.023))*w,anchor.y+(yy+rng.uniform(-.023,.023))*d,cz+(zz+rng.uniform(-.035,.035))*height)),Vector((w*rx*ss,d*ry*ss,height*rz*ss))))
 # Drooping tips hang from selected outer limbs, at unequal heights and depths.
 for i in [0,2,3,5,7]:
  c,r=lobes[i];out=Vector((c.x-anchor.x,c.y-anchor.y,0)).normalized();lobes.append((c+out*w*.048-Vector((0,0,height*rng.uniform(.12,.20))),Vector((r.x*.65,r.y*.70,r.z*.70))))
 batch=Batch();pruned=0;exposed_samples=0;attempts=0;desired=1700
 def kept_add(v,f,mi,uv):
  nonlocal pruned
  pairs=[(face,idx)for face,idx in zip(f,mi)if keep_triangle([v[j]for j in face],houses,upper_routes)];pruned+=sum(max(0,len(face)-2)for face,idx in zip(f,mi)if not keep_triangle([v[j]for j in face],houses,upper_routes))
  used=sorted(set(j for face,idx in pairs for j in face));remap={j:i for i,j in enumerate(used)}
  batch.add([v[j]for j in used],[tuple(remap[j]for j in face)for face,idx in pairs],[idx for face,idx in pairs],True,[uv[j]for j in used])
 while exposed_samples<desired and attempts<desired*30:
  attempts+=1;ci=rng.randrange(len(lobes));c,r=lobes[ci];z=rng.uniform(-1,1);a=rng.uniform(0,2*math.pi);rr=math.sqrt(1-z*z);u=Vector((rr*math.cos(a),rr*math.sin(a),z));inner=exposed_samples>=1500;point=c+Vector((u.x*r.x,u.y*r.y,u.z*r.z))*(.72 if inner else 1)
  # Spend triangles on visible shell instead of overlapping interior lobe walls.
  if not inner and any(sum(((point[j]-cc[j])/r2[j])**2 for j in range(3))<.94**2 for jj,(cc,r2)in enumerate(lobes)if jj!=ci):continue
  n=Vector((u.x/r.x,u.y/r.y,u.z/r.z)).normalized();point+=n*rng.uniform(-.12,.26);n=(n+Vector((rng.uniform(-.40,.40),rng.uniform(-.40,.40),rng.uniform(-.25,.32)))).normalized()
  light=.46+.37*n.dot(SUN)+.13*(point.z-cz)/max(height,.1)+rng.uniform(-.14,.14)
  idx=rng.choice([1,2,3])if inner else max(0,min(len(LEAF)-1,int(light*(len(LEAF)-1)+.5)))
  scale=max(.78,min(1.13,w/6.3));length=rng.uniform(.66,.94)*scale;width=length*rng.uniform(.86,1.04)
  v,f,mi,uv=leaf(point,n,rng,length,width,idx);kept_add(v,f,mi,uv);exposed_samples+=1
 me=batch.mesh('V4R5_DenseBroadleaf_'+old.name,mats);old.data=me;old.matrix_world=Matrix.Identity(4);old['vegetation_version']=VERSION;old['collision_role']='visual canopy; exclude collision';old['uv_contract']='packed original8cell atlas;5leaf silhouettes per curved card; no reference imagery'
 if'no_uv_reason'in old:del old['no_uv_reason']
 me.calc_loop_triangles()
 return {'name':old.name,'triangles':len(me.loop_triangles),'pruned_house_or_upper_route_triangles':pruned,'target_width_m':w,'rounded_sampling_lobes':len(lobes),'solid_core_triangles':0,'curved_cluster_cards':exposed_samples,'leaf_silhouettes_per_card':5,'outer_cluster_cards':min(1500,exposed_samples),'inner_deep_teal_cluster_cards':max(0,exposed_samples-1500),'sampling_attempts':attempts,'bounds_world':[[min(v.co[j]for v in me.vertices)for j in range(3)],[max(v.co[j]for v in me.vertices)for j in range(3)]]}

def spreading_branches(trunk,anchor,oldbbox,houses,upper_routes,rng,mats):
 b=json.loads(trunk['v4_vegetation_backup']);src=bpy.data.meshes[b['mesh']];M=Matrix(b['matrix']);batch=Batch();batch.add([M@v.co for v in src.vertices],[tuple(p.vertices)for p in src.polygons],[p.material_index for p in src.polygons]);lo,hi=oldbbox;w=(hi.x-lo.x)*1.20;d=(hi.y-lo.y)*1.18;top=hi.z;added=0;skipped=0;new_min_z=[]
 def tube(a,b,r0,r1):
  nonlocal added,skipped
  z=(b-a).normalized();x=z.cross(Vector((0,0,1)))
  if x.length<.1:x=z.cross(Vector((1,0,0)))
  x.normalize();y=z.cross(x).normalized();v=[]
  for center,radius in [(a,r0),(b,r1)]:
   for i in range(8):ang=2*math.pi*i/8;v.append(center+radius*(math.cos(ang)*x+math.sin(ang)*y))
  f=[(i,(i+1)%8,(i+1)%8+8,i+8)for i in range(8)]+[tuple(range(7,-1,-1)),tuple(range(8,16))];mi=[]
  for q in f:
   nn=(v[q[1]]-v[q[0]]).cross(v[q[2]]-v[q[0]]).normalized();mi.append(1 if nn.dot(SUN)>.45 else(2 if nn.dot(SUN)<-.30 else 0))
  if min(p.z for p in v)<3.05 or not all(keep_triangle([p],houses,upper_routes)for p in v):skipped+=1;return
  batch.add(v,f,mi);added+=1;new_min_z.append(min(p.z for p in v))
 for j in range(5):
  a=2*math.pi*j/5+.34+rng.uniform(-.1,.1);dz=max(3.30,top*.44);base=Vector((anchor.x,anchor.y,dz));mid=Vector((anchor.x+math.cos(a)*w*.13,anchor.y+math.sin(a)*d*.13,max(3.60,top*.71)));end=Vector((anchor.x+math.cos(a)*w*.285,anchor.y+math.sin(a)*d*.285,max(3.85,top*.89+rng.uniform(-.22,.18))));scale=w/7.4;tube(base,mid,.22*scale,.15*scale);tube(mid,end,.15*scale,.045*scale)
 me=batch.mesh('V4R5_Spreading_'+trunk.name,mats);trunk.data=me;trunk.matrix_world=Matrix.Identity(4);trunk['vegetation_version']=VERSION;me.calc_loop_triangles();return{'name':trunk.name,'triangles':len(me.loop_triangles),'added_branch_segments':added,'skipped_route_or_house_segments':skipped,'original_geometry_preserved':True,'new_branch_min_z_m':min(new_min_z)if new_min_z else None,'protected_ground_jump_head_m':.18+1.8+5.5*5.5/(2*19),'scope':'visual branch silhouette above3.05m ground-jump envelope and outside upper routes only; no new colliders'}

def backup(o):
 if not o.get('v4_vegetation_backup'):
  if o.type=='MESH':o.data.use_fake_user=True
  o['v4_vegetation_backup']=json.dumps({'mesh':o.data.name if o.type=='MESH'else None,'matrix':[list(r)for r in o.matrix_world],'materials':[m.name for m in o.data.materials]if o.type=='MESH'else[]})
 # Original trunk mesh material slots were revised in early checkpoints. Retain
 # every saved material explicitly so SAVE->reload->restore remains real.
 b=json.loads(o['v4_vegetation_backup'])
 for name in b['materials']:
  original=bpy.data.materials.get(name)
  if original is None:raise RuntimeError('Missing original restore material '+name+'; repair checkpoint from immutable RC1 before applying')
  original.use_fake_user=True

def restore():
 for o in bpy.context.scene.objects:
  s=o.get('v4_vegetation_backup')
  if not s:continue
  b=json.loads(s)
  if o.type=='MESH':
   o.data=bpy.data.meshes[b['mesh']];indices=[p.material_index for p in o.data.polygons];o.data.materials.clear();[o.data.materials.append(bpy.data.materials[n])for n in b['materials']]
   for polygon,index in zip(o.data.polygons,indices):polygon.material_index=index
  o.matrix_world=Matrix(b['matrix']);del o['v4_vegetation_backup']

def lawn(cfg,mats,rng):
 old=bpy.data.objects.get('V3_Layout_Edge_Grass')
 if old is None:return {'status':'no grass source object found'}
 backup(old);outline=[Vector(p[:2])for p in cfg['outline_blender']];mask=[];routes=[];points=[]
 for h in cfg['house_frames'].values():
  c,s=math.cos(h['yaw_radians']),math.sin(h['yaw_radians']);cx,cy,_=h['position_blender']
  for q in h['components'].values():
   lo,hi=q['local_bbox_m'];mask.append([Vector((cx+c*x-s*y,cy+s*x+c*y))for x,y in [(lo[0]-.35,lo[1]-.35),(hi[0]+.35,lo[1]-.35),(hi[0]+.35,hi[1]+.35),(lo[0]-.35,hi[1]+.35)]])
 c=bpy.data.collections.get('03_Layout_Ground')
 if c:
  for o in c.objects:
   if o.type!='MESH'or o.name=='LAYOUT_Playable_Grass_Outline'or o.name.startswith('LAYOUT_Court_'):continue
   mask.append([(o.matrix_world@v.co).to_2d()for v in o.data.vertices])
 for id,d in cfg['traversal_anchors'].items():
  if id=='three_lanes':routes.extend((Vector(q['start'][:2]),Vector(q['end'][:2]))for q in d.values())
  else:points.extend(Vector(p[:2])for p in d.values()if isinstance(p,list))
 for h in cfg['final_house_route_contract']['houses'].values():
  for p in h['portals'].values():routes.append((Vector(p['negative_axis_approach']['world_blender'][:2]),Vector(p['positive_axis_approach']['world_blender'][:2])))
  for q in h['routes'].values():
   if'bottom'in q and'top'in q:routes.append((Vector(q['bottom']['world_blender'][:2]),Vector(q['top']['world_blender'][:2])))
   if'waypoints'in q:
    pp=[Vector(p['world_blender'][:2])for p in q['waypoints']];routes.extend(zip(pp,pp[1:]))
 points.extend(Vector(p[:2])for p in cfg['walk_spawns'].values());prop=[]
 c=bpy.data.collections.get('30_ExteriorProps')
 if c:
  for o in c.objects:
   if o.type=='MESH'and o.name.split('.')[0]in {'Garden_shed','Supply_crate','Utility_cover'}:
    p=[o.matrix_world@Vector(v)for v in o.bound_box];prop.append((min(v.x for v in p)-.35,max(v.x for v in p)+.35,min(v.y for v in p)-.35,max(v.y for v in p)+.35))
 radius=cfg['court']['curb_radius_m']+1.7
 def good(p):
  if not inside(p,outline)or p.length<radius:return False
  if min(segdist(p,a,b)for a,b in zip(outline,outline[1:]+outline[:1]))<.35:return False
  if any(inside(p,q)or min(segdist(p,a,b)for a,b in zip(q,q[1:]+q[:1]))<.25 for q in mask):return False
  if any(segdist(p,a,b)<1.85 for a,b in routes)or any((p-q).length<1.85 for q in points):return False
  if any(a<=p.x<=b and c<=p.y<=d for a,b,c,d in prop):return False
  return True
 xmin,xmax=min(p.x for p in outline),max(p.x for p in outline);ymin,ymax=min(p.y for p in outline),max(p.y for p in outline);centers=[];grid={};attempts=0;spacing=.075
 while len(centers)<15750 and attempts<350000:
  attempts+=1;p=Vector((rng.uniform(xmin,xmax),rng.uniform(ymin,ymax)))
  if not good(p):continue
  key=(int((p.x-xmin)/spacing),int((p.y-ymin)/spacing));near=[q for dx in[-1,0,1]for dy in[-1,0,1]for q in grid.get((key[0]+dx,key[1]+dy),[])]
  if any((p-q).length<spacing for q in near):continue
  grid.setdefault(key,[]).append(p);centers.append(Vector((p.x,p.y,.019)))
 batch=Batch();broad_clumps=0
 for i,p in enumerate(centers):
  # Fine curved narrow blades rather than repeated triangular pyramids.
  for j in range(2):
   a=rng.uniform(0,2*math.pi);fwd=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0));h=rng.uniform(.065,.15);w=rng.uniform(.011,.022);root=p+fwd*rng.uniform(0,.035);mid=root+fwd*.027+Vector((0,0,h*.64));tip=root+fwd*rng.uniform(.042,.085)+Vector((0,0,h));v=[root-side*w,root+side*w,mid-side*w*.65,tip];idx=rng.choices(range(3),weights=[1,4,3])[0];batch.add(v,[(0,1,2),(1,3,2)],[idx,min(3,idx+1)])
  if i%63 in(0,31):
   broad_clumps+=1
   for j in range(6):
    a=2*math.pi*j/6+rng.uniform(-.24,.24);fwd=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0));length=rng.uniform(.21,.36);h=rng.uniform(.12,.23);w=rng.uniform(.035,.060)
    mid=p+fwd*(length*.50)+Vector((0,0,h*.72));tip=p+fwd*length+Vector((0,0,h));v=[p,mid-side*w,mid+side*w,tip];batch.add(v,[(0,1,2),(1,3,2)],[(i+j)%4,(i+j+1)%4])
 me=batch.mesh('V4R5_DenseShortLawn',mats);old.data=me;old.matrix_world=Matrix.Identity(4);old['vegetation_version']=VERSION;old['collision_role']='visual grass; EXCLUDE collision';old['route_safety_basis']='full lawn samples preserve1.85m centers and <=0.36m tips';me.calc_loop_triangles()
 return {'masked_centers':len(centers),'short_clusters':len(centers),'short_blades':len(centers)*2,'broad_edge_clumps':broad_clumps,'triangles':len(me.loop_triangles),'sampling_attempts':attempts,'distribution':'denser short blade coverage over allowable lawn; occasional outward lanceolate tufts','height_range_m':[.019,.249],'center_route_clearance_m':1.85,'max_broad_leaf_reach_m':.36}

def apply(config_path=None,texture_path=None):
 cfg=json.load(open(config_path or os.path.dirname(DIR)+'/site_frames.json'));before=collider_hash();rng=random.Random(40261003);leafm=[leaf_atlas_material(texture_path)];barkm=[mat('V4R5_Warm_Bark_'+str(i),c)for i,c in enumerate(BARK)];grassm=[mat('V4R5_Lawn_Blade_'+str(i),c)for i,c in enumerate(GRASS)];houses=[];upper=[]
 for h in cfg['house_frames'].values():
  c,s=math.cos(h['yaw_radians']),math.sin(h['yaw_radians']);cx,cy,_=h['position_blender']
  for q in h['components'].values():
   lo,hi=q['local_bbox_m'];houses.append([(cx+c*x-s*y,cy+s*x+c*y)for x,y in [(lo[0]-.22,lo[1]-.22),(hi[0]+.22,lo[1]-.22),(hi[0]+.22,hi[1]+.22),(lo[0]-.22,hi[1]+.22)]])
 for h in cfg['final_house_route_contract']['houses'].values():
  for r in h['routes'].values():
   if'waypoints'in r:
    p=[q['world_blender']for q in r['waypoints']]
    for a,b in zip(p,p[1:]):
     if a[2]>3 or b[2]>3:upper.append((Vector(a[:2]),Vector(b[:2])))
 report={'version':VERSION,'authority':'new tree+grass image2; overall image4 tone only','canonical_frame_version':cfg['version'],'route_version':cfg['final_house_route_contract']['version'],'tree_anchors':{},'canopies':[],'branches':[],'collision_sha256_before':before,'original_reference_pixels_copied':False}
 for i in range(1,11):
  key='%02d'%i;trunk=bpy.data.objects.get('V2_Tree_'+key+'_Branching');old=bpy.data.objects.get('V2_Tree_'+key+'_LeafClumps')
  if not trunk or not old:continue
  tb=json.loads(trunk['v4_vegetation_backup'])if trunk.get('v4_vegetation_backup')else None;tm=Matrix(tb['matrix'])if tb else trunk.matrix_world;td=bpy.data.meshes[tb['mesh']]if tb else trunk.data;verts=[tm@v.co for v in td.vertices];low=sorted(verts,key=lambda p:p.z)[:8];anchor=Vector((sum(p.x for p in low)/8,sum(p.y for p in low)/8,0));b=json.loads(old['v4_vegetation_backup'])if old.get('v4_vegetation_backup')else None;source_matrix=Matrix(b['matrix'])if b else old.matrix_world;source_mesh=bpy.data.meshes[b['mesh']]if b else old.data;pts=[source_matrix@v.co for v in source_mesh.vertices];lo=Vector([min(p[j]for p in pts)for j in range(3)]);hi=Vector([max(p[j]for p in pts)for j in range(3)]);backup(old);backup(trunk)
  for j,m in enumerate(trunk.data.materials):
   original=json.loads(trunk['v4_vegetation_backup'])['materials'][j];trunk.data.materials[j]=barkm[0 if'Dark'in original else(2 if'Light'in original else 1)]
  report['tree_anchors'][key]=list(anchor);report['canopies'].append(crown(old,anchor,[lo,hi],houses,upper,rng,leafm));report['branches'].append(spreading_branches(trunk,anchor,[lo,hi],houses,upper,rng,[barkm[1],barkm[2],barkm[0]]))
 report['budget']={'canopy_triangles_max':108000,'lawn_triangles_max':69000,'trunk_and_branches_triangles_max':10000,'tree_anchor_count':10,'texture_bytes_added':512*256*4,'texture_definition':'base decoded RGBA only, mip allocation excluded','alpha_mode':'MASK','alpha_cutoff':.5,'double_sided':True};report['ground_material']='UNCHANGED, palette worker owns base terrain material';report['lawn']=lawn(cfg,grassm,rng);report['new_canopy_triangles']=sum(r['triangles']for r in report['canopies']);report['collision_sha256_after']=collider_hash();report['all_colliders_byte_identical']=before==report['collision_sha256_after']
 if not report['all_colliders_byte_identical']:raise AssertionError('Protected collision changed')
 report['trunk_and_branches_triangles']=sum(q['triangles']for q in report['branches'])
 if report['new_canopy_triangles']>108000 or report['lawn']['triangles']>69000 or report['trunk_and_branches_triangles']>10000:raise AssertionError('Vegetation triangle budget exceeded')
 bpy.context.view_layer.update();return report
