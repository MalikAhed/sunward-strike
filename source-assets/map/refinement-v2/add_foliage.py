"""Original SUNWARD leaf geometry, reference-inspired V2.

Integration: import this file with importlib.util and call apply() once after
loading the source scene. It does not save, render, export, or change collision.
All new geometry is direct mesh data with ordinary glTF-compatible materials.
"""
import bpy
import math
import random
from mathutils import Vector

COLLECTION = '60_V2_Foliage'
SEED = 20261003
TREE_FALLBACK = [(-23,31,1.4),(22,32,1.3),(-22,-31,1.35),(23,-31,1.35),
                 (-25,11,1.1),(24,-13,1.1),(22,13,1),(-24,-12,1),
                 (-23,22,1.05),(24,23,1.25)]


def _material(name, rgb, roughness=.88):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    material.use_backface_culling = False
    node = material.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*rgb, 1)
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Metallic'].default_value = 0
    if 'Specular IOR Level' in node.inputs:
        node.inputs['Specular IOR Level'].default_value = .22
    return material


class _Mesh:
    def __init__(self):
        self.vertices, self.faces, self.material_indices = [], [], []

    def face(self, points, material=0):
        start = len(self.vertices)
        self.vertices.extend(tuple(p) for p in points)
        self.faces.append(tuple(range(start, start + len(points))))
        self.material_indices.append(material)

    def leaf(self, center, direction, normal, length, width, material=0, ivy=False):
        """A folded, solid-colored leaf; no opacity planes or image textures."""
        c, u, n = Vector(center), Vector(direction).normalized(), Vector(normal).normalized()
        n -= u * n.dot(u)
        if n.length < .05:
            n = u.cross(Vector((0,1,0)))
            if n.length < .05:
                n = u.cross(Vector((1,0,0)))
        n.normalize()
        v = n.cross(u).normalized()
        if ivy:
            # Three-lobed ivy silhouette, shallow raised center vein.
            outline = [c-u*length*.44,
                       c-u*length*.18-v*width*.47,
                       c+u*length*.13-v*width*.40,
                       c+u*length*.58,
                       c+u*length*.13+v*width*.40,
                       c-u*length*.18+v*width*.47]
        else:
            # A broad lanceolate silhouette with an explicit central fold.
            outline = [c-u*length*.48,
                       c-u*length*.02-v*width*.5,
                       c+u*length*.55+n*length*.018,
                       c-u*length*.02+v*width*.5]
        base = len(self.vertices)
        if not ivy:
            # Two triangles share a raised midrib. This is the same folded
            # silhouette as a four-triangle fan with half its triangle cost.
            outline[0] += n*width*.11
            outline[2] += n*width*.11
            self.vertices.extend(tuple(p) for p in outline)
            self.faces.extend([(base,base+1,base+2),(base,base+2,base+3)])
            self.material_indices.extend([material,material])
        else:
            middle = c + n*width*.12
            self.vertices.extend(tuple(p) for p in outline + [middle])
            for k in range(len(outline)):
                self.faces.append((base+k,base+(k+1)%len(outline),base+len(outline)))
                self.material_indices.append(material)

    def tube(self, points, radii, sides=7, material=0):
        """Tapered polygonal tube with curved centerline and connected rings."""
        points = [Vector(p) for p in points]
        base = len(self.vertices)
        for j, (p, r) in enumerate(zip(points,radii)):
            tangent = points[min(j+1,len(points)-1)] - points[max(0,j-1)]
            tangent.normalize()
            u = tangent.cross(Vector((0,1,0)))
            if u.length < .05:
                u = tangent.cross(Vector((1,0,0)))
            u.normalize()
            v = tangent.cross(u).normalized()
            for k in range(sides):
                angle = 2*math.pi*k/sides
                self.vertices.append(tuple(p + r*(u*math.cos(angle)+v*math.sin(angle))))
        for j in range(len(points)-1):
            for k in range(sides):
                self.faces.append((base+j*sides+k, base+j*sides+(k+1)%sides,
                                   base+(j+1)*sides+(k+1)%sides,base+(j+1)*sides+k))
                self.material_indices.append((material+(1 if k in (2,3) else 0)) % 3)
        self.faces.append(tuple(base+k for k in reversed(range(sides))))
        self.material_indices.append(material)
        self.faces.append(tuple(base+(len(points)-1)*sides+k for k in range(sides)))
        self.material_indices.append(material)

    def build(self, name, materials, collection, role):
        if not self.faces:
            return None
        mesh = bpy.data.meshes.new(name + '_Mesh')
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        for material in materials:
            mesh.materials.append(material)
        for poly, index in zip(mesh.polygons,self.material_indices):
            poly.material_index = index
        obj = bpy.data.objects.new(name,mesh)
        collection.objects.link(obj)
        obj['foliage_role'] = role
        obj['collision'] = 'decorative; exclude from collision and navmesh baking'
        obj['original_geometry'] = True
        return obj


def _unit(rng):
    while True:
        v = Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-1,1)))
        if .01 < v.length_squared <= 1:
            return v.normalized()


def _tree(x,y,scale,index,rng,collection,leaves,barks):
    bark, leafmesh = _Mesh(), _Mesh()
    def p(a,b,c):
        return Vector((x+a*scale,y+b*scale,c*scale))
    leanx, leany = rng.uniform(-.22,.22), rng.uniform(-.18,.18)
    base, low, fork, top = p(0,0,.06), p(leanx*.4,leany*.4,1.25), p(leanx,leany,2.65), p(leanx-.07,leany+.10,4.7)
    bark.tube([base,low,fork,top], [.25*scale,.17*scale,.12*scale,.04*scale],8)
    # Ground-root flare stays within the original trunk's narrow decorative footprint.
    for k in range(4):
        a = k*math.pi/2 + rng.uniform(-.22,.22)
        root = p(math.cos(a)*.37,math.sin(a)*.37,.09)
        bark.tube([root,base+p(0,0,.02)-Vector((x,y,0)),low], [.015*scale,.09*scale,.08*scale],5)
    centers = []
    phase = rng.uniform(0,math.pi*2)
    for k in range(6):
        a = phase + k*math.pi*2/6 + rng.uniform(-.19,.19)
        radius = rng.uniform(1.02,1.36)
        h = rng.uniform(3.75,4.35)
        end = p(leanx+math.cos(a)*radius,leany+math.sin(a)*radius,h)
        elbow = fork.lerp(end,.44) + Vector((0,0,.10*scale))
        bark.tube([fork,elbow,end], [.105*scale,.069*scale,.022*scale],7,k%3)
        for j in (-1,1):
            angle = a+j*.48
            tip = end+Vector((math.cos(angle)*.38*scale,math.sin(angle)*.38*scale,rng.uniform(.15,.45)*scale))
            bark.tube([elbow.lerp(end,.70),tip], [.037*scale,.008*scale],5,(k+1)%3)
            centers.append((tip,Vector((.73*scale,.64*scale,.61*scale))))
    centers.extend([(top,Vector((.82*scale,.77*scale,.66*scale))),
                    (p(leanx+.12,leany-.09,4.22),Vector((1.0*scale,.87*scale,.60*scale)))])
    # 120 sprigs x 8 individually folded leaves: broad leaf clumps rather than
    # a visible shell, sphere, billboard or faceted canopy volume.
    for j in range(120):
        center, radius = centers[j % len(centers)]
        d = _unit(rng)
        offset = Vector((d.x*radius.x,d.y*radius.y,d.z*radius.z))*rng.random()**.32
        pos = center+offset
        axis = Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.35,.7))).normalized()
        side = axis.cross(Vector((0,0,1)))
        if side.length < .05:
            side = Vector((1,0,0))
        side.normalize()
        sprig_length = rng.uniform(.45,.70)*scale
        for pair in range(4):
            t = (pair-.95)*sprig_length/3
            for sign in (-1,1):
                length = rng.uniform(.24,.35)*scale
                width = length*rng.uniform(.43,.64)
                direction = (axis*.50+side*sign*.90+Vector((0,0,rng.uniform(-.10,.20)))).normalized()
                leafpos = pos+axis*t+side*sign*length*.25
                normal = Vector((rng.uniform(-.52,.52),rng.uniform(-.52,.52),rng.uniform(.40,1))).normalized()
                bright = (offset.z/radius.z)*.8 + rng.uniform(-1,1)
                material = rng.choices([0,1,2,3,4],weights=([1,3,3,2,1] if bright>.1 else [2,4,3,1,0]))[0]
                leafmesh.leaf(leafpos,direction,normal,length,width,material)
    bark.build('V2_Tree_%02d_Branching'%index,barks,collection,'irregular tapered tree trunk and branching')
    leafmesh.build('V2_Tree_%02d_LeafClumps'%index,leaves,collection,'dense original folded-leaf crown')


def _ivy_patch(name,origin,horizontal,normal,width,height,count,rng,collection,leaves,barks):
    """Flush facade patch with sparse tapered edges, maximum projection ~0.15m."""
    o, u, n = Vector(origin),Vector(horizontal),Vector(normal)
    z = Vector((0,0,1))
    mesh, stems = _Mesh(),_Mesh()
    for j in range(4):
        x = rng.uniform(-width*.28,width*.28)
        points = [o+u*(x+math.sin(k*.7+j)*width*.10)+z*(height*k/5)+n*.035 for k in range(6)]
        stems.tube(points,[.016,.013,.012,.01,.007,.003],4,0)
    for j in range(count):
        zz = rng.uniform(.02,height)
        envelope = width*(.48 - .24*(zz/height)**1.8)
        xx = rng.uniform(-envelope,envelope)
        if zz>height*.8 and rng.random()<.22:
            continue
        c = o+u*xx+z*zz+n*rng.uniform(.04,.075)
        direction = (z*rng.uniform(.55,1.0)+u*rng.uniform(-.55,.55)).normalized()
        length = rng.uniform(.15,.23)
        mesh.leaf(c,direction,n,length,length*rng.uniform(.86,1.06),rng.choices(range(5),[2,4,4,2,1])[0],ivy=True)
    mesh.build('V2_Ivy_'+name,leaves,collection,'restrained wall-bound ivy; clear of openings and routes')
    stems.build('V2_IvyStems_'+name,barks,collection,'wall-bound ivy stems')


def _planters(rng,collection,leaves):
    # Added silhouette detail stays inside the existing planter and garden bed
    # bounds. No existing planter, shrub, path, door, or collision is changed.
    mesh = _Mesh()
    planters = [(-15.3,-10,3.2,1.1),(16.8,-10,3.2,1.1),(-5,-8.5,3.1,.9),
                (-15.3,10,3.2,1.1),(16.8,10,3.2,1.1),(5,8.5,3.1,.9)]
    for x,y,w,d in planters:
        for j in range(240):
            tuft = j % 4
            centerx = x-w/2+.38+tuft*.63
            a = rng.uniform(0,math.pi*2)
            radius = rng.random()**.5
            pos = Vector((centerx+math.cos(a)*radius*.40,y+math.sin(a)*radius*.36,1.12+rng.uniform(-.25,.39)*(1-radius*.55)))
            direction = _unit(rng)
            direction.z = abs(direction.z)*.6
            normal = Vector((rng.uniform(-.5,.5),rng.uniform(-.5,.5),1))
            length = rng.uniform(.15,.23)
            mesh.leaf(pos,direction,normal,length,length*.64,rng.choices(range(5),[1,4,4,2,1])[0])
        # Little ivy spill over the two end lips, never across the walkway.
        for sign in (-1,1):
            for j in range(24):
                pos = Vector((x+sign*(w*.47+rng.uniform(-.045,.045)),y+rng.uniform(-d*.32,d*.32),rng.uniform(.37,.98)))
                mesh.leaf(pos,(0,rng.uniform(-.6,.6),-.9),(sign,0,.12),.17,.16,rng.choice([1,2,3]),ivy=True)
    mesh.build('V2_Planter_LeafyGrowth',leaves,collection,'leaf and ivy detail confined to existing planters')
    beds = _Mesh()
    for sign in (-1,1):
        for xx in (-8,-2,4):
            for dx in (-1.5,-.5,.5,1.5):
                for dy in (-.6,.6):
                    c = Vector((sign*xx+dx,sign*34.4+dy,1.12))
                    for k in range(28):
                        a = k*math.pi*2/28+rng.uniform(-.4,.4)
                        d = Vector((math.cos(a),math.sin(a),rng.uniform(.30,.65)))
                        pos = c+Vector((math.cos(a)*rng.uniform(.06,.18),math.sin(a)*rng.uniform(.06,.18),rng.uniform(-.05,.16)))
                        length = rng.uniform(.18,.25)
                        beds.leaf(pos,d,(0,0,1),length,length*.55,rng.choice([1,2,3]))
    beds.build('V2_GardenBed_LeafyGrowth',leaves,collection,'original herb leaves confined to existing raised beds')


def apply():
    """Apply to loaded scene; return a JSON-serializable integration report."""
    rng = random.Random(SEED)
    # Read old positions before deletion; avoid hard-coding moved root locations.
    roots = sorted((o for o in bpy.data.objects if o.name=='Tree_trunk' or o.name.startswith('Tree_trunk.')),key=lambda o:o.name)
    trees = [(o.matrix_world.translation.x,o.matrix_world.translation.y,o.matrix_world.translation.z/1.9) for o in roots]
    if not trees:
        trees = TREE_FALLBACK
    old_collection = bpy.data.collections.get(COLLECTION)
    if old_collection:
        for obj in list(old_collection.objects):
            bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(old_collection)
    removed = []
    for obj in list(bpy.data.objects):
        if any(obj.name == prefix or obj.name.startswith(prefix+'.') for prefix in ('Tree_canopy','Tree_branch','Tree_trunk','Planter_shrub','Garden_plant')):
            removed.append(obj.name)
            bpy.data.objects.remove(obj,do_unlink=True)
    collection = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    collection['purpose'] = 'decorative original leaf meshes; do not generate collision'
    palette = [(.105,.175,.062),(.185,.275,.105),(.265,.365,.185),(.355,.450,.245),(.420,.500,.275)]
    leaves = [_material('V2_Leaf_'+name,color) for name,color in zip(('DeepOlive','Olive','Sage','SunlitSage','WarmTips'),palette)]
    barks = [_material('V2_Bark_'+name,color) for name,color in zip(('WarmBrown','LightRidge','DarkCrease'),[(.235,.135,.065),(.325,.205,.11),(.155,.088,.044)])]
    for i,(x,y,scale) in enumerate(trees,1):
        _tree(x,y,scale,i,rng,collection,leaves,barks)
    # Symmetric front corners: opening envelopes are x < 4.5; patches stay >5.2.
    # Side corner patches are below and forward of upper side windows.
    for sign in (-1,1):
        _ivy_patch(('A' if sign==1 else 'B')+'_FrontCorner',
                   (sign*5.64,sign*11.32,.25),(1,0,0),(0,-sign,0),.78,3.15,112,rng,collection,leaves,barks)
        _ivy_patch(('A' if sign==1 else 'B')+'_SideCorner',
                   (sign*6.16,sign*12.05,.25),(0,sign,0),(sign,0,0),.72,3.75,116,rng,collection,leaves,barks)
        _ivy_patch(('A' if sign==1 else 'B')+'_ShedRear',
                   (sign*15.08,sign*35.97,.18),(1,0,0),(0,sign,0),.70,2.85,88,rng,collection,leaves,barks)
        _ivy_patch(('A' if sign==1 else 'B')+'_ShedSide',
                   (sign*15.83,sign*35.15,.18),(0,1,0),(sign,0,0),.72,2.6,82,rng,collection,leaves,barks)
    _planters(rng,collection,leaves)
    triangles = 0
    for obj in collection.objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    if triangles > 40000:
        raise RuntimeError('Foliage exceeds the 40,000 triangle budget: %d' % triangles)
    report = {'collection':COLLECTION,'new_objects':len(collection.objects),'new_triangles':triangles,
              'trees':len(trees),'removed_original_tree_and_plant_objects':len(removed),'texture_images':0,
              'collision_changed':False,'layout_changed':False,'deterministic_seed':SEED,
              'materials':[m.name for m in leaves+barks]}
    bpy.context.scene['v2_foliage_triangles'] = triangles
    print('V2_FOLIAGE_REPORT',report,flush=True)
    return report


if __name__ == '__main__':
    apply()
