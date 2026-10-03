"""Independent read-only saved furniture/proxy fit and aperture audit."""
import bpy,json,pathlib,hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');source=pathlib.Path(bpy.data.filepath)
contract=json.loads(pathlib.Path('/workspace/shared/sunward-structure-build/houses/house-route-contract-r7.json').read_text())
proxies=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('COL_V3_D3_')];visuals=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('D3_')];bad=[];groups=[]
for o in proxies:
 vv=[o.matrix_world@v.co for v in o.data.vertices];faces=[list(p.vertices) for p in o.data.polygons];volume=sum(vv[f[0]].dot(vv[f[i]].cross(vv[f[i+1]]))/6 for f in faces for i in range(1,len(f)-1))
 if volume<=0:bad.append(o.name)
 names=list(o.get('source_visuals',[]));parents=[bpy.data.objects[n] for n in names if n in bpy.data.objects];pv=[v.co for v in o.data.vertices];av=[o.matrix_world.inverted()@p.matrix_world@v.co for p in parents for v in p.data.vertices]
 # Proxy fills undersides to floor. All visible group vertices must be contained.
 bbox=[[min(v[i] for v in pv) for i in range(3)],[max(v[i] for v in pv) for i in range(3)]];outside=sum(any(v[i]<bbox[0][i]-1e-5 or v[i]>bbox[1][i]+1e-5 for i in range(3)) for v in av)
 groups.append({'proxy':o.name,'volume':volume,'visual_names':names,'contained_visual_vertex_count':len(av)-outside,'outside_vertices':outside,'proxy_bbox':bbox,'visual_bbox':[[min(v[i] for v in av) for i in range(3)],[max(v[i] for v in av) for i in range(3)]]})
portals=[]
for hid,h in contract['houses'].items():
 root=bpy.data.objects['HOUSE_ROOT_'+hid];trs=[(o.name,BVHTree.FromPolygons([root.matrix_world.inverted()@o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]))for o in proxies if hid in o.name]
 for pid,p in h['portals'].items():
  aa=p['negative_axis_approach']['local_blender'];bb=p['positive_axis_approach']['local_blender'];a=Vector(aa);b=Vector(bb);direction=b-a;length=direction.length;direction.normalize();tangent=Vector((-direction.y,direction.x,0));blocks=[]
  for offset in [-.55,0,.55]:
   for height in [.15,.4,1,1.7]:
    origin=a+tangent*offset+Vector((0,0,height))
    for name,t in trs:
     hit,_,_,_=t.ray_cast(origin,direction,length)
     if hit is not None:blocks.append({'proxy':name,'offset':offset,'height':height})
  portals.append({'house':hid,'portal':pid,'blocks':blocks})
r={'source_name':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'visual_meshes':len(visuals),'proxies':len(proxies),'nonpositive_proxy_volumes':bad,'groups':groups,'portal_samples':portals,'passed':not bad and all(not g['outside_vertices'] for g in groups) and all(not p['blocks'] for p in portals),'scope':'Actual saved furniture/proxy geometry and 1.1m portal corridor ray samples; complete controller routes remain separate'}
(OUT/'interiors-r3-independent.json').write_text(json.dumps(r,indent=2)+'\n');print('INTERIOR_REVIEW',json.dumps({k:v for k,v in r.items() if k not in ['groups','portal_samples']}));assert r['passed']
