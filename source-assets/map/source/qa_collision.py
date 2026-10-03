"""Read-only component-aware check of the final hidden static triangle collider.

Run: blender -b Sunward_TestSite.blend --python source/qa_collision.py
Runs visual QA first, then separately sweeps the same routes on collider geometry.
"""
import bpy
import json
import math
import os
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scope={'__file__':os.path.join(ROOT,'source','qa_map.py')}
exec(compile(open(scope['__file__']).read(),scope['__file__'],'exec'),scope)
visual_report=scope['report']
ob=bpy.data.objects.get('COL_Sunward_Static')
if ob is None:
    raise RuntimeError('No COL_Sunward_Static mesh found')
me=ob.data
# Hidden collections are omitted by the evaluated dependency graph. On a fresh
# background load their matrix_world can stay identity despite nonzero location.
# This collider is unparented, so matrix_basis is its authoritative transform.
matrix=ob.matrix_basis if ob.parent is None else ob.matrix_world
verts=[matrix @ v.co for v in me.vertices]
faces=[list(p.vertices) for p in me.polygons]
if matrix.to_3x3().determinant()<0:
    faces=[f[::-1] for f in faces]
# Connected components retain the primitive-level low-step distinction lost by
# a single joined-mesh bounding box. No source or collider objects are changed.
parent=list(range(len(verts)))
def root(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]]
        a=parent[a]
    return a
def union(a,b):
    a,b=root(a),root(b)
    if a!=b:parent[b]=a
for face in faces:
    for vi in face[1:]:union(face[0],vi)
parts={}
for face in faces:
    parts.setdefault(root(face[0]),[]).append(face)
geometry=[]
errors=[]
for number,part in enumerate(parts.values()):
    indices=sorted({vi for face in part for vi in face})
    lookup={vi:i for i,vi in enumerate(indices)}
    vv=[verts[vi] for vi in indices]
    ff=[[lookup[vi] for vi in face] for face in part]
    edge=Counter()
    for face in ff:
        for a,b in zip(face,face[1:]+face[:1]):edge[tuple(sorted((a,b)))]+=1
    closed=all(n==2 for n in edge.values())
    vol=sum(vv[f[0]].dot(vv[f[i]].cross(vv[f[i+1]]))/6
            for f in ff for i in range(1,len(f)-1)) if closed else None
    lo=Vector(tuple(min(v[i] for v in vv) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in vv) for i in range(3)))
    name='COL_component_%04d'%number
    if vol is not None and vol<-.00001:
        errors.append({'component':name,'signed_volume_m3':vol,'lo':list(lo),'hi':list(hi)})
    geometry.append({'name':name,'lo':lo,'hi':hi,'closed':closed,
                     'support':True,'bvh':BVHTree.FromPolygons(vv,ff)})
scope['geometry']=geometry
routes=[scope['sample_path'](r['route'],r['waypoints_xy'],r['initial_floor_m'])
        for r in visual_report['routes']]

# Spot-check the upward normals and support on the proxy flights at mid-flight.
ramp_samples=[]
for sign in [1,-1]:
    for label,lx,ly,hint in [('interior',-4.65,0,1.94),('exterior',-7.5,6.75,1.96)]:
        x,y=scope['local_to_world'](sign,[(lx,ly)])[0]
        floor,support=scope['support_at'](x,y,hint)
        hit=None
        for g in geometry:
            if not (g['lo'].x<=x<=g['hi'].x and g['lo'].y<=y<=g['hi'].y):continue
            p,n,_,distance=g['bvh'].ray_cast(Vector((x,y,hint+.325)),Vector((0,0,-1)),3)
            if p is not None and (hit is None or p.z>hit[0]):hit=(p.z,list(n),g['name'])
        ramp_samples.append({'flight':label,'house':sign,'position_xy':[x,y],
                             'support_height':floor,'support_component':support,
                             'highest_hit':hit,'upward':bool(hit and hit[1][2]>.65)})
report={'method':'Connected-component evaluated static triangle mesh capsule sweep; not a runtime engine controller test.',
        'collider':ob.name,'components':len(geometry),'mesh_triangles':sum(len(f)-2 for f in faces),
        'inward_closed_components':errors,'ramp_normal_samples':ramp_samples,
        'routes':routes,'all_sampled_routes_pass':all(r['pass'] for r in routes),
        'all_sampled_ramps_upward':all(r['upward'] for r in ramp_samples)}
with open(os.path.join(ROOT,'qa_collision_report.json'),'w') as f:json.dump(report,f,indent=2)
print('COLLISION_QA',json.dumps(report,indent=2))
