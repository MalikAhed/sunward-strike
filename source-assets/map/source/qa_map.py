"""Independent, read-only geometry route checks.

Run with: blender -b Sunward_TestSite.blend --python source/qa_map.py
Writes qa_report.json only. It never changes or saves the Blender scene.
This is a conservative geometric capsule sweep, not an engine navmesh.
"""
import bpy
import json
import math
import os
from collections import Counter
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RADIUS = .35
HEIGHT = 1.8
STEP = .30
SAMPLE_DISTANCE = .12
SUPPORT_PREFIXES = (
    'PLAYABLE_Base', 'Street_main', 'Culdesac', 'Sidewalk', 'Curb',
    'Central_culdesac', 'Curved_curb', 'Culdesac_footway',
    'Approach_sidewalk', 'Approach_curb', 'Front_grass',
    'Garden_lawn', 'Driveway', 'Entry_path', 'Backyard_terrace', 'Backyard_lawn',
    'Side_lane_paving', 'A_Mint_foundation', 'B_Saffron_foundation',
    'A_Mint_ground_floor', 'B_Saffron_ground_floor', 'Front_porch',
    'Upper_floor_', 'Interior_stair_', 'Garage_floor', 'Balcony_floor',
    'Exterior_stair_', 'Truck_cargo_floor', 'Truck_loading_ramp', 'World_desert',
)

dg = bpy.context.evaluated_depsgraph_get()
geometry = []
normal_errors = []
for ob in bpy.context.scene.objects:
    if ob.type not in {'MESH', 'CURVE', 'FONT'}:
        continue
    if any(c.name.startswith(('80_', '90_', '91_', '99_')) for c in ob.users_collection):
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    if not me or not me.polygons:
        if me:
            ev.to_mesh_clear()
        continue
    verts = [ev.matrix_world @ v.co for v in me.vertices]
    faces = [list(p.vertices) for p in me.polygons]
    if ev.matrix_world.to_3x3().determinant() < 0:
        faces = [f[::-1] for f in faces]
    edges = Counter()
    for f in faces:
        for a, b in zip(f, f[1:] + f[:1]):
            edges[tuple(sorted((a, b)))] += 1
    closed = all(n == 2 for n in edges.values())
    if closed:
        volume = 0
        for f in faces:
            for i in range(1,len(f)-1):
                volume += verts[f[0]].dot(verts[f[i]].cross(verts[f[i+1]]))/6
        if volume < -.00001:
            normal_errors.append({'object':ob.name,'signed_volume_m3':volume})
            # Normalize only the independent BVH representation so circulation
            # can still be tested. The source mesh error remains in the report.
            faces = [f[::-1] for f in faces]
    lo = Vector(tuple(min(v[i] for v in verts) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in verts) for i in range(3)))
    geometry.append({
        'name': ob.name, 'building': ob.get('building'),
        'vehicle': ob.get('vehicle'), 'lo': lo, 'hi': hi,
        'bvh': BVHTree.FromPolygons(verts, faces),
        'closed': closed,
        'support': ob.name.startswith(SUPPORT_PREFIXES),
    })
    ev.to_mesh_clear()


def support_at(x, y, hint):
    start = hint + STEP + .025
    hits = []
    footprint = [(x,y)] + [(x+.28*math.cos(i*math.pi/4),y+.28*math.sin(i*math.pi/4)) for i in range(8)]
    for g in geometry:
        if not g['support'] or not (g['lo'].x-.28 <= x <= g['hi'].x+.28 and g['lo'].y-.28 <= y <= g['hi'].y+.28):
            continue
        for px,py in footprint:
            p, n, _, d = g['bvh'].ray_cast(Vector((px, py, start)), Vector((0, 0, -1)), 8)
            if p is not None and n.z > .65:
                hits.append((p.z, g['name']))
    return max(hits) if hits else (None, None)


def capsule_blockers(x, y, z):
    blockers = []
    low = z + RADIUS
    high = z + HEIGHT - RADIUS
    n = math.ceil((high - low) / .12)
    centers = [Vector((x, y, low + (high - low) * i / n)) for i in range(n + 1)]
    for g in geometry:
        lo, hi = g['lo'], g['hi']
        if hi.x < x-RADIUS or lo.x > x+RADIUS or hi.y < y-RADIUS or lo.y > y+RADIUS:
            continue
        if hi.z < z+.01 or lo.z > z+HEIGHT:
            continue
        # A standard step-up controller clears low curbs/treads/thresholds.
        if hi.z <= z+STEP+.025:
            continue
        for c in centers:
            p, norm, _, dist = g['bvh'].find_nearest(c)
            if p is None:
                continue
            inside = g['closed'] and (c-p).dot(norm) < -.005
            if dist < RADIUS-.018 or inside:
                blockers.append(g['name'])
                break
    return blockers


def sample_path(name, points, initial_floor=.2):
    foot = initial_floor
    samples = []
    failures = []
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0]-a[0], b[1]-a[1])
        n = max(1, math.ceil(length / SAMPLE_DISTANCE))
        for i in range(n):
            t = i/n
            x = a[0] + t*(b[0]-a[0])
            y = a[1] + t*(b[1]-a[1])
            floor, support = support_at(x, y, foot)
            if floor is None:
                failures.append({'kind':'no_support', 'position':[x,y,foot]})
                continue
            if floor-foot > STEP+.025 or foot-floor > .50:
                failures.append({'kind':'height_discontinuity', 'position':[x,y,floor], 'delta':floor-foot, 'support':support})
            blockers = capsule_blockers(x, y, floor)
            if blockers:
                failures.append({'kind':'capsule_overlap', 'position':[x,y,floor], 'objects':blockers})
            samples.append((x,y,floor))
            foot = floor
    return {'route':name, 'waypoints_xy':points, 'initial_floor_m':initial_floor,
            'samples':len(samples), 'pass':not failures,
            'failure_count':len(failures), 'first_failures':failures[:8]}


def local_to_world(sign, points):
    # Builder first mirrors local X, then rotates the southern house 180 degrees.
    return [(-sign*x, sign*(y+17)) for x,y in points]


routes = []
for s, title in [(1,'mint'),(-1,'saffron')]:
    # Rear doorway local X=+1.25, front doorway local X=-1.
    house_route = [(0,14),(0,9),(1.25,6.4),(1.25,4),(.7,1.7),
                   (.65,-.1),(0,-2),(-1,-3.6),(-1,-4.6),(-1,-6.5),(-1,-9.5)]
    routes.append(sample_path(title+'_spawn_through_house_to_front',local_to_world(s,house_route)))
    garage_route = [(0,14),(8.8,9),(9.1,6.4),(9.1,4),(9.1,-3),
                    (9.4,-5.9),(9.4,-9.5)]
    routes.append(sample_path(title+'_spawn_through_garage_to_front',local_to_world(s,garage_route)))
    for x in [-20,20]:
        routes.append(sample_path(title+('_west' if -s*x<0 else '_east')+'_outer_flank',
                                  local_to_world(s,[(0,14),(0,10),(x,10),(x,-9.5),
                                                  (math.copysign(17.5,x),-10.8),
                                                  (math.copysign(17.5,x),-17)])))
    interior_stair = [(-4.65,-3.75),(-4.65,-3.43),(-4.65,3.2),(-4.65,4.5),
                      (-3,4.5),(0,4.5),(.1,5.5),(.1,6.6)]
    routes.append(sample_path(title+'_interior_stair_to_balcony',local_to_world(s,interior_stair)))
    exterior_stair = [(-11.4,6.75),(-10.85,6.75),(-4.22,6.75),
                      (-3.3,6.75),(.1,6.75),(.1,4.5)]
    routes.append(sample_path(title+'_exterior_stair_to_upper_room',local_to_world(s,exterior_stair)))

routes.append(sample_path('mint_front_to_mid',[(1,7.5),(3.7,6),(3.7,.10),(0,0)]))
routes.append(sample_path('saffron_front_to_mid',[(-1,-7.5),(-3,-5),(-3,-.05),(0,0)]))
routes.append(sample_path('central_vehicle_gap',[(-14,0),(-7,0),(0,0),(13,0)]))
routes.append(sample_path('truck_ramp_to_cargo',[(-11.2,2.5),(-10.95,2.5),(-7.86,2.58),(-5.5,2.64)]))

report = {
    'method':'Read-only evaluated-mesh BVH capsule sweep. Geometry-only conservative check; not a navmesh or runtime controller test.',
    'capsule':{'height':HEIGHT,'radius':RADIUS,'step_height':STEP},
    'mesh_objects_tested':len(geometry), 'routes':routes,
    'inward_closed_meshes':normal_errors,
    'all_sampled_routes_pass':all(r['pass'] for r in routes),
}
with open(os.path.join(ROOT,'qa_report.json'),'w') as f:
    json.dump(report,f,indent=2)
print('GEOMETRY_QA',json.dumps(report,indent=2))
