"""Read-only structural and collision check of a SAVED landmark revision."""
import bpy, os, json, math
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
ROOT='/workspace/shared/sunward-structure-build/landmarks'
OUTPUT='/workspace/shared/sunward-strike/docs/qa/structure-review/landmarks-r13-independent-qa.json'
s=bpy.context.scene;version=s.get('landmark_patch_version')
if not version:raise RuntimeError('Actual landmark candidate required')
r=json.load(open(ROOT+'/'+version+'-report.json'))
out={'candidate':bpy.data.filepath,'version':version,'protected_geometry_changes':r['protected_geometry_changes'],
     'groups':{},'proxy_checks':[],'truck_surface_checks':[],'proxy_closed_volume_errors':[]}
bpy.context.view_layer.update()
for row in r['groups']:
    name=row['group'];angle=math.radians(row['yaw_degrees'])
    inv=Matrix.Rotation(-angle,4,'Z')
    objs=[o for o in s.objects if o.get('landmark_group')==name and o.type=='MESH' and not o.name.startswith('COL_')]
    pts=[inv @ o.matrix_world @ Vector(p) for o in objs for p in o.bound_box]
    lo=[min(p[i] for p in pts) for i in range(3)];hi=[max(p[i] for p in pts) for i in range(3)]
    world=[o.matrix_world @ Vector(p) for o in objs for p in o.bound_box]
    out['groups'][name]={'yaw_degrees':row['yaw_degrees'],'dimensions_oriented':[hi[i]-lo[i] for i in range(3)],
        'world_bounds':[[min(p[i] for p in world) for i in range(3)],[max(p[i] for p in world) for i in range(3)]],
        'objects':len(objs),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objs)}
col=bpy.data.collections['92_LandmarkCollision'];trees=[]
for cp in col.objects:
    source=bpy.data.objects[cp['collision_source_id']]
    proxy_mat=cp.matrix_basis
    same=max(abs(proxy_mat[i][j]-source.matrix_world[i][j]) for i in range(4) for j in range(4))<1e-5
    same_geom=len(cp.data.vertices)==len(source.data.vertices) and all((a.co-b.co).length<1e-6 for a,b in zip(cp.data.vertices,source.data.vertices))
    out['proxy_checks'].append({'proxy':cp.name,'source':source.name,'world_transform_match':same,'unbeveled_geometry_match':same_geom})
    vv=[proxy_mat @ v.co for v in cp.data.vertices];ff=[list(p.vertices) for p in cp.data.polygons]
    trees.append((cp.name,BVHTree.FromPolygons(vv,ff)))
    edges={}
    for f in ff:
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b)));edges[e]=edges.get(e,0)+1
    closed=all(n==2 for n in edges.values())
    volume=sum(vv[f[0]].dot(vv[f[i]].cross(vv[f[i+1]]))/6 for f in ff for i in range(1,len(f)-1)) if closed else None
    if not closed or volume is None or volume<=0:
        out['proxy_closed_volume_errors'].append({'proxy':cp.name,'closed':closed,'signed_volume':volume})
for name,a in r['truck_traversal'].items():
    if not isinstance(a,dict) or 'world_xyz' not in a or name=='ramp_approach':continue
    p=Vector(a['world_xyz']);best=None
    for n,tree in trees:
        hit,normal,_,distance=tree.ray_cast(p+Vector((0,0,.3)),Vector((0,0,-1)),.65)
        if hit is not None and (best is None or hit.z>best[0].z):best=(hit,normal,n)
    out['truck_surface_checks'].append({'anchor':name,'expected_world':list(p),
        'surface_found':best is not None,'height_error_m':abs(best[0].z-p.z) if best else None,
        'normal':list(best[1]) if best else None,'proxy':best[2] if best else None,
        'pass':bool(best and abs(best[0].z-p.z)<.04 and best[1].z>.90)})
out['bus_truck_heading_difference_degrees']=abs(r['options']['bus_yaw_degrees']-r['options']['truck_yaw_degrees'])
out['bus_truck_center_distance_m']=(Vector(r['groups'][0]['anchor_world'])-Vector(r['groups'][1]['anchor_world'])).length
out['all_proxy_geometry_matches']=all(v['world_transform_match'] and v['unbeveled_geometry_match'] for v in out['proxy_checks'])
out['truck_sampled_floor_surfaces_pass']=all(v['pass'] for v in out['truck_surface_checks'])
rear_tires=[o for o in s.objects if o.name.startswith('Truck_tire') and o.get('landmark_local_matrix') and o['landmark_local_matrix'][3]<0]
out['truck_rear_tire_clearance']=[{'name':o.name,
    'top_world_z':max((o.matrix_world@Vector(p)).z for p in o.bound_box),
    'floor_world_z':r['truck_traversal']['floor_surface_world_z']} for o in rear_tires]
out['truck_tires_below_cargo_deck']=all(row['top_world_z']<row['floor_world_z'] for row in out['truck_rear_tire_clearance'])
out['family_ground_alignment']={
    'green_car_tire_bottom_z':out['groups']['Green_Driveway_Sedan']['world_bounds'][0][2],
    'green_car_driveway_top_z':r['options']['green_car_driveway_top_z'],
    'clock_foot_min_z':out['groups']['Context_Clock']['world_bounds'][0][2],
    'clock_context_ground_z':r['options']['clock_context_ground_z'],
}
a=out['family_ground_alignment']
out['family_ground_alignment_pass']=abs(a['green_car_tire_bottom_z']-a['green_car_driveway_top_z'])<.001 and abs(a['clock_foot_min_z']-a['clock_context_ground_z'])<.001
out['technical_pass']=out['all_proxy_geometry_matches'] and out['truck_sampled_floor_surfaces_pass'] and out['truck_tires_below_cargo_deck'] and out['family_ground_alignment_pass'] and not out['proxy_closed_volume_errors'] and not out['protected_geometry_changes']
out['scope']='Read-only source/proxy equality, positive closed volumes and selected downward surface rays; full runtime capsule sweeps remain integrator QA.'
json.dump(out,open(OUTPUT,'w'),indent=2)
print('LANDMARK_QA',json.dumps(out),flush=True)
