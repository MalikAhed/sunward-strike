"""Owned portable interior color/decor layer; no shared material or house edits.
Original geometric rug/art, yellow fabric, warm cabinet/mint backsplash, simple lamps.
Source-only lamp point lights are explicitly excluded from GLB; emissive lamp meshes stay.
"""
import bpy,math
from mathutils import Vector,Matrix
COL='56_V3_Interior_Dressing'
def material(name,color,emission=0):
 m=bpy.data.materials.get(name)or bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.88;p.inputs['Metallic'].default_value=0
 if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 return m

def mesh(name,v,f,mat,col,parent,indices=None):
 me=bpy.data.meshes.new(name+'_Mesh');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);col.objects.link(o);o.parent=parent;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_local=Matrix.Identity(4)
 for m in mat if isinstance(mat,list)else[mat]:me.materials.append(m)
 if indices:
  for p,i in zip(me.polygons,indices):p.material_index=i
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co.y,co.z)
 o['dressing_version']='interior-dressing-r2-style';o['original_geometry']=True;o['collision_role']='owned interior decoration';return o

def box(name,c,d,m,col,parent):
 x,y,z=c;a,b,h=[v/2 for v in d];v=[(x-a,y-b,z-h),(x+a,y-b,z-h),(x+a,y+b,z-h),(x-a,y+b,z-h),(x-a,y-b,z+h),(x+a,y-b,z+h),(x+a,y+b,z+h),(x-a,y+b,z+h)];f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)];return mesh(name,v,f,m,col,parent)

def cylinder(name,c,r0,r1,h,m,col,parent,n=8,open_caps=False):
 x,y,z=c;v=[]
 for r,zz in [(r0,z-h/2),(r1,z+h/2)]:
  for i in range(n):a=2*math.pi*i/n;v.append((x+r*math.cos(a),y+r*math.sin(a),zz))
 f=([(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)] if open_caps else [tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n)for i in range(n)]);return mesh(name,v,f,m,col,parent)

def apply(cfg,buckets,report,P):
 col=bpy.data.collections[COL];yellow=material('D3_Fabric_Warm_Yellow',(.53,.31,.055));teal=material('D3_Fabric_Muted_Teal',(.19,.37,.30));cabinet=material('D3_Warm_Cabinet',(.53,.34,.17));counter=material('D3_Countertop_Cream',(.72,.65,.50));mint=material('D3_Mint_Kitchen',(.23,.40,.32));sand=material('D3_Rug_Warm_Border',(.40,.28,.16));wood=material('D3_Frame_Aged_Wood',(.22,.125,.062));cream=material('D3_Artwork_Cream',(.69,.61,.45));coral=material('D3_Artwork_Coral',(.57,.235,.12));gold=material('D3_Artwork_Ochre',(.57,.405,.19));shade=material('D3_Lamp_Cream_Shade',(.68,.52,.285));glow=material('D3_Lamp_Warm_Glow',(1,.55,.19),.85)
 rugm=[material('D3_Rug_Pattern_'+str(i),p)for i,p in enumerate([(.52,.36,.19),(.71,.61,.43),(.40,.19,.085),(.59,.27,.14),(.28,.16,.07)])]
 native=bpy.data.collections.get('99_D3_NATIVE_INTERIOR_LIGHTS')
 if not native:native=bpy.data.collections.new('99_D3_NATIVE_INTERIOR_LIGHTS');bpy.context.scene.collection.children.link(native)
 native['native_source_only']=True;native['exclude_from_glb']=True;style=[]
 for id,h in cfg['house_frames'].items():
  root=bpy.data.objects['D3_ROOT_'+id];cro=bpy.data.objects['COL_V3_D3_ROOT_'+id];data=cfg['final_house_route_contract']['houses'][id];fg=data['floor_ground_z'];fu=data['floor_upper_z'];x0,y0=h['components']['main_body']['local_bbox_m'][0];x1,y1=h['components']['main_body']['local_bbox_m'][1]
  for o in buckets[id]['Sofa']:o.data.materials.clear();o.data.materials.append(yellow if id=='A_Mint'else teal)
  for o in buckets[id]['Kitchen']:o.data.materials.clear();o.data.materials.append(counter if'countertop'in o['baseline_source_object']else cabinet)
  for o in buckets[id]['Rug']:o.data.materials.clear();o.data.materials.append(sand)
  rb=P.worldbounds(buckets[id]['Rug'],True);rx0,ry0,z=rb[0];rx1,ry1,rz=rb[1];v=[];f=[];mi=[]
  # Authored angular3x4 patchwork; no sampled reference pixels or copied artwork.
  for iy in range(4):
   for ix in range(3):
    xa=rx0+.13+(rx1-rx0-.26)*ix/3;xb=rx0+.13+(rx1-rx0-.26)*(ix+1)/3;ya=ry0+.13+(ry1-ry0-.26)*iy/4;yb=ry0+.13+(ry1-ry0-.26)*(iy+1)/4;k=len(v);v.extend([(xa,ya,rz+.0015),(xb,ya,rz+.0015),(xb,yb,rz+.0015),(xa,yb,rz+.0015)])
    f.extend([(k,k+1,k+2),(k,k+2,k+3)]if(ix+iy)%2 else[(k,k+1,k+3),(k+1,k+2,k+3)]);mi.extend([(ix+iy*2)%5,(ix*2+iy+1)%5])
  rug=mesh('D3_'+id+'_Authored_Geometric_Rug',v,f,rugm,col,root,mi);rug['collision_role']='flat carpet pattern; decorative floor layer'
  kb=P.worldbounds(buckets[id]['Kitchen'],True);box('D3_'+id+'_Mint_Kitchen_Backsplash',((kb[0][0]+kb[1][0])/2,y1-.16,fg+1.58),(kb[1][0]-kb[0][0],.032,.86),mint,col,root)['collision_role']='wall-bound backsplash behind solid counter; unreachable narrow gap'
  # Two modest wall prints, located above/behind occupied sofa and bed footprints.
  frames=[('Living',y0+3.2,fg+1.95,.96,.82),('Bedroom',y1-2.0,fu+1.52,.76,.62)]
  for label,cy,cz,w,hh in frames:
   xx=x0+.19
   for n,cc,dd in [('Top',(xx,cy,cz+hh/2),(.07,w+.08,.06)),('Bottom',(xx,cy,cz-hh/2),(.07,w+.08,.06)),('Left',(xx,cy-w/2,cz),(.07,.06,hh)),('Right',(xx,cy+w/2,cz),(.07,.06,hh))]:box('D3_'+id+'_Frame_'+label+'_'+n,cc,dd,wood,col,root)['collision_role']='wall decoration above furniture, excluded'
   box('D3_'+id+'_Canvas_'+label,(xx+.013,cy,cz),(.025,w-.05,hh-.05),cream,col,root)['collision_role']='wall decoration above furniture, excluded'
   p=[(xx+.028,cy-w*.38,cz-hh*.36),(xx+.028,cy+w*.35,cz-hh*.32),(xx+.028,cy+w*.05,cz+hh*.35),(xx+.028,cy-w*.36,cz+hh*.33),(xx+.028,cy+w*.38,cz+hh*.15),(xx+.028,cy+w*.12,cz-hh*.15)];art=mesh('D3_'+id+'_Original_Abstract_Print_'+label,p,[(0,1,2),(2,3,0),(3,4,5)],[coral,mint,gold],col,root,[0,1,2]);art['collision_role']='wall decoration above furniture, excluded'
  lx=x0+.46;ly=y0+1.02;parts=[]
  parts.append(cylinder('D3_'+id+'_Lamp_Base',(lx,ly,fg+.018),.16,.16,.036,wood,col,root))
  parts.append(cylinder('D3_'+id+'_Lamp_Stem',(lx,ly,fg+.605),.025,.025,1.14,wood,col,root))
  parts.append(cylinder('D3_'+id+'_Lamp_Shade',(lx,ly,fg+1.31),.26,.16,.30,shade,col,root,open_caps=True))
  parts.append(cylinder('D3_'+id+'_Lamp_Glow',(lx,ly,fg+1.154),.218,.218,.006,glow,col,root))
  bpy.context.view_layer.update();bb=P.bounds_in_parent(parts,cro);proxy=P.box_proxy('COL_V3_D3_'+id+'_Lamp',bb,'V3_COLLISION',cro,[o.name for o in parts],fg);report['collision_proxies'].append(proxy.name)
  for o in parts:o['collision_proxy']=proxy.name
  overlaps=[label for label,a,b,margin in P.routes_for_house(data,fg)if P.intersect_segment_box(a,b,bb[0],bb[1],margin)]
  if overlaps:report['unresolved_route_overlaps'].append({'house':id,'group':'Lamp','routes':overlaps,'bbox_local':bb})
  light=bpy.data.lights.new('D3_'+id+'_Native_Warm_Lamp','POINT');light.energy=32;light.color=(1,.62,.30);light.shadow_soft_size=.16;lo=bpy.data.objects.new(light.name,light);native.objects.link(lo);lo.parent=root;lo.location=(lx,ly,fg+1.155);lo['native_source_only']=True;lo['exclude_from_glb']=True
  style.append({'house':id,'sofa':'warm yellow'if id=='A_Mint'else'muted teal','rug':'original angular warm5color3x4patchwork','kitchen':'owned warm cabinet/cream top/mint backsplash','wall_art':'two original abstract geometric framed prints; no reference image copy','lamp':'low-poly warm-emissive fixture, native-only32W pointlight','added_native_light_export':'EXCLUDED','lamp_route_envelope_clear':not overlaps})
 report['style']=style;report['style_scope']='owned material assignments on transplanted copies + modest original rug/art/lamps; no shared materials/house geometry/global lighting edits';return report
