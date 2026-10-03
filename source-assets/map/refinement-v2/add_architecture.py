"""SUNWARD V2 additive stonework and eave detailing.

Usage in an already-loaded SUNWARD scene:
    import add_architecture
    report = add_architecture.apply()

No input asset is modified. All geometry is deliberately shallow and visual-only,
inside 61_V2_Architecture. Constant Principled materials are glTF-friendly.
"""
import bpy
import math
import random
from mathutils import Vector

COLLECTION = '61_V2_Architecture'
PREFIX = 'SW2_Arch_'
SEED = 26487


class MeshBatch:
    def __init__(self, name, materials):
        self.name, self.materials = name, materials
        self.vertices, self.faces, self.indices = [], [], []
        self.pieces = 0

    def face(self, ids, mat=0):
        self.faces.append(tuple(ids))
        self.indices.append(mat)

    def block(self, center, dim, mat=0, transform=None):
        x,y,z=center; w,d,h=[v/2 for v in dim]
        vv=[(x-w,y-d,z-h),(x+w,y-d,z-h),(x+w,y+d,z-h),(x-w,y+d,z-h),
            (x-w,y-d,z+h),(x+w,y-d,z+h),(x+w,y+d,z+h),(x-w,y+d,z+h)]
        if transform: vv=[transform(p) for p in vv]
        k=len(self.vertices); self.vertices.extend(vv)
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face([k+i for i in (f[::-1] if transform else f)],mat)
        self.pieces += 1

    def beam(self, a, b, width, depth, mat=0, transform=None):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized()
        ref=Vector((0,1,0))
        if abs(axis.dot(ref))>.9:ref=Vector((1,0,0))
        u=axis.cross(ref).normalized()*(width/2);v=axis.cross(u).normalized()*(depth/2)
        vv=[tuple(p+s*u+t*v) for p in (a,b) for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        if transform:vv=[transform(p) for p in vv]
        k=len(self.vertices);self.vertices.extend(vv)
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face([k+i for i in (f[::-1] if transform else f)],mat)
        self.pieces += 1

    def stone(self, poly, z, mat, rng, uplift=.003):
        """Eight-corner stone with narrow, actual sloped bevel, not a shader seam."""
        k=len(self.vertices);n=len(poly)
        cx=sum(p[0] for p in poly)/n;cy=sum(p[1] for p in poly)/n
        inset=.012
        # Small height variation stays in a millimeter range: no traversal change.
        height=uplift+rng.uniform(-.00035,.00035)
        self.vertices.extend([(x,y,z+.00055) for x,y in poly])
        top=[]
        for x,y in poly:
            dx,dy=cx-x,cy-y;dd=math.hypot(dx,dy)
            top.append((x+inset*dx/dd,y+inset*dy/dd,z+height))
        self.vertices.extend(top)
        self.face(range(k+n,k+2*n),mat)
        for i in range(n):
            j=(i+1)%n
            self.face((k+i,k+j,k+n+j,k+n+i),mat)
        self.pieces+=1

    def prism_xz(self, poly, y, thickness, mat, transform):
        # Normalize the XZ outline so outward normals survive the reflected plan.
        if sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))>0:poly=list(reversed(poly))
        k=len(self.vertices);n=len(poly)
        self.vertices.extend([transform((x,y-thickness/2,z)) for x,z in poly])
        self.vertices.extend([transform((x,y+thickness/2,z)) for x,z in poly])
        self.face(tuple(range(k+n-1,k-1,-1)),mat)
        self.face(tuple(range(k+n,k+2*n)),mat)
        for i in range(n):
            j=(i+1)%n;self.face((k+i,k+j,k+n+j,k+n+i),mat)
        self.pieces+=1
        # tr() mirrors the original local house plan, so correct winding explicitly.
        if transform:
            for i in range(len(self.faces)-n-2,len(self.faces)):
                self.faces[i]=self.faces[i][::-1]

    def finish(self, collection, bevel=0):
        if not self.vertices:return None
        me=bpy.data.meshes.new(self.name+'_Mesh')
        me.from_pydata(self.vertices,[],self.faces);me.update()
        for m in self.materials:me.materials.append(m)
        for i,p in enumerate(me.polygons):p.material_index=self.indices[i]
        o=bpy.data.objects.new(self.name,me);collection.objects.link(o)
        o['art_detail']='visual-only; no collision or layout change'
        o['piece_count']=self.pieces
        if bevel:
            mod=o.modifiers.new('Restrained edge bevel','BEVEL');mod.width=bevel;mod.segments=1
            mod.affect='EDGES';mod.limit_method='ANGLE'
            normals=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');normals.keep_sharp=True
        return o


def _mat(name,color,roughness=.86):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=0
    m.diffuse_color=(*color,1)
    return m


def _rect_stone(xa,xb,ya,yb,rng,gap=.025):
    xa+=gap/2;xb-=gap/2;ya+=gap/2;yb-=gap/2
    # Corner cuts have deliberately varied sizes, without random spikes or overlaps.
    lim=min(xb-xa,yb-ya)
    cuts=[rng.uniform(.018,.068)*lim for i in range(4)]
    a,b,c,d=cuts
    return [(xa+a,ya),(xb-b,ya),(xb,ya+b),(xb,yb-c),
            (xb-c,yb),(xa+d,yb),(xa,yb-d),(xa,ya+a)]


def _divisions(a,b,mean,rng):
    n=max(1,round((b-a)/mean))
    weights=[rng.uniform(.75,1.3) for _ in range(n)]
    scale=(b-a)/sum(weights)
    out=[a]
    for w in weights:out.append(out[-1]+w*scale)
    out[-1]=b
    return out


def _floor_rect(obj,materials,mortar,collection,rng,report):
    bb=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    xa,xb=min(p.x for p in bb),max(p.x for p in bb)
    ya,yb=min(p.y for p in bb),max(p.y for p in bb)
    z=max(p.z for p in bb)
    # All veneers sit inside the source footprint. Broad slabs make stones readable.
    xa+=.018;xb-=.018;ya+=.018;yb-=.018
    name=PREFIX+'Paving_'+obj.name
    batch=MeshBatch(name,materials)
    bed=MeshBatch(name+'_RecessedJoints',[mortar])
    k=len(bed.vertices);bed.vertices.extend([(xa,ya,z+.00025),(xb,ya,z+.00025),(xb,yb,z+.00025),(xa,yb,z+.00025)])
    bed.face((0,1,2,3));bed.finish(collection)
    if obj.name.startswith('Side_lane_paving'):
        rowmean,cellmean=1.40,1.03
    elif obj.name.startswith('Driveway'):
        rowmean,cellmean=1.18,1.39
    elif obj.name.startswith('Backyard_terrace'):
        rowmean,cellmean=1.08,1.22
    elif obj.name.startswith('Entry_path'):
        rowmean,cellmean=.90,.85
    else:
        rowmean,cellmean=1.04,1.20
    ys=_divisions(ya,yb,rowmean,rng)
    for row,(y0,y1) in enumerate(zip(ys,ys[1:])):
        xs=_divisions(xa,xb,cellmean,rng)
        for x0,x1 in zip(xs,xs[1:]):
            poly=_rect_stone(x0,x1,y0,y1,rng,gap=rng.uniform(.023,.035))
            # Mild brightness differences read as sandstone wear rather than checkers.
            mat=rng.choices(range(len(materials)),weights=[2,3,4,4,3,2,1,1])[0]
            batch.stone(poly,z,mat,rng)
    out=batch.finish(collection)
    out['source_floor']=obj.name
    report['paving_stones']+=batch.pieces
    report['floor_surfaces'].append(obj.name)


def _floor_arc(obj,materials,mortar,collection,rng,report):
    """Clip to each of the original 32 source quads. Never leaks onto the road."""
    batch=MeshBatch(PREFIX+'Paving_'+obj.name,materials)
    bed=MeshBatch(PREFIX+'Paving_'+obj.name+'_RecessedJoints',[mortar])
    # Original source pairs an inner and outer vertex at each angular station.
    vv=[obj.matrix_world@v.co for v in obj.data.vertices]
    for i in range(0,len(vv)-2,2):
        a,b,c,d=vv[i],vv[i+1],vv[i+3],vv[i+2]
        k=len(bed.vertices);bed.vertices.extend([(p.x,p.y,p.z+.00025)for p in [a,b,c,d]])
        bed.face((k,k+1,k+2,k+3))
        # Two radial bands use quarter-cell staggered stone seams at alternate stations.
        for band in range(2):
            t0=band/2+.013;t1=(band+1)/2-.013
            p0=a.lerp(b,t0);p1=d.lerp(c,t0);p2=d.lerp(c,t1);p3=a.lerp(b,t1)
            poly=[(p0.x,p0.y),(p3.x,p3.y),(p2.x,p2.y),(p1.x,p1.y)]
            # Inset laterally from source station by ~1cm to create recessed joints.
            cen=Vector((sum(p[0]for p in poly)/4,sum(p[1]for p in poly)/4))
            pp=[]
            for x,y in poly:
                p=Vector((x,y));q=p+(cen-p).normalized()*.009;pp.append((q.x,q.y))
            batch.stone(pp,a.z,rng.randrange(1,7),rng)
    bed.finish(collection);out=batch.finish(collection);out['source_floor']=obj.name
    report['paving_stones']+=batch.pieces
    report['floor_surfaces'].append(obj.name)


def _tr(sign):
    def f(p):
        x,y,z=p
        x=-x
        if sign==-1:x,y=-x,-y
        return (x,y+sign*17,z)
    return f


def _masonry_span(batch,axis,side,a,b,z0,z1,rng,transform,matcount,report):
    # Broken-course shallow stones have real bevel rims but no wasteful backfaces.
    zz=_divisions(z0,z1,.30,rng)
    # Recessed backing panel. Openings are excluded by the caller's exact spans.
    if axis=='X':batch.block(((a+b)/2,side,(z0+z1)/2),(b-a,.001,z1-z0),matcount,transform)
    else:batch.block((side,(a+b)/2,(z0+z1)/2),(.001,b-a,z1-z0),matcount,transform)
    for row,(za,zb) in enumerate(zip(zz,zz[1:])):
        div=_divisions(a,b,1.02 if row else .86,rng)
        for u0,u1 in zip(div,div[1:]):
            if u1-u0<.06:continue
            poly=_rect_stone(u0,u1,za,zb,rng,gap=.023)
            vstart=len(batch.vertices);fstart=len(batch.faces)
            batch.stone(poly,0,rng.randrange(matcount),rng,uplift=.016)
            outward=1 if side>0 else -1
            for i in range(vstart,len(batch.vertices)):
                u,z,h=batch.vertices[i]
                if axis=='X':p=(u,side+outward*h,z)
                else:p=(side+outward*h,u,z)
                batch.vertices[i]=transform(p)
            # XY->XZ gives -Y; XY->YZ gives +X. tr() adds one reflection.
            needflip = (axis=='X' and outward<0) or (axis=='Y' and outward>0)
            if needflip:
                for i in range(fstart,len(batch.faces)):batch.faces[i]=batch.faces[i][::-1]
            report['masonry_blocks']+=1


def _building(sign,materials,timber,cream,collection,rng,report):
    label='Mint' if sign==1 else 'Saffron';tr=_tr(sign)
    mortar=_mat(PREFIX+'MasonryJoints',(.35,.36,.303),.95)
    masonry=MeshBatch(PREFIX+label+'_WeatheredStoneBase',materials+[mortar])
    ledges=MeshBatch(PREFIX+label+'_StoneCoping',[cream])
    wood=MeshBatch(PREFIX+label+'_TimberEaves',[timber[0],timber[1],cream])
    # Doors: front [-1.9,-.1], rear [.3,2.2], east side [-1.7,.2].
    for a,b in [(-5.90,-1.99),(-.01,5.90)]:
        _masonry_span(masonry,'X',-5.754,a,b,.19,.815,rng,tr,len(materials),report)
        ledges.block(((a+b)/2,-5.777,.85),(b-a,.11,.065),0,tr)
    for a,b in [(-5.90,.20),(2.30,5.90)]:
        _masonry_span(masonry,'X',5.629,a,b,.20,.82,rng,tr,len(materials),report)
        ledges.block(((a+b)/2,5.675,.855),(b-a,.085,.055),0,tr)
    _masonry_span(masonry,'Y',-6.129,-5.38,5.38,.20,.82,rng,tr,len(materials),report)
    for a,b in [(-5.38,-1.80),(.30,5.38)]:
        _masonry_span(masonry,'Y',6.129,a,b,.20,.82,rng,tr,len(materials),report)
    # Garage side/solid ends; rolled-up door and backyard garage exit are untouched.
    _masonry_span(masonry,'Y',12.909,-4.68,5.38,.20,.82,rng,tr,len(materials),report)
    for a,b in [(6.06,6.71),(12.09,12.74)]:
        _masonry_span(masonry,'X',-4.929,a,b,.20,.82,rng,tr,len(materials),report)
    for a,b in [(6.06,7.90),(10.30,12.74)]:
        _masonry_span(masonry,'X',5.629,a,b,.20,.82,rng,tr,len(materials),report)
    # Pitched eave underside and front/rear gable shadow band.
    for side in [-1,1]:
        wood.block((side*6.58,0,6.688),(.17,12.16,.20),0,tr)
        wood.block((side*6.592,0,6.590),(.115,12.16,.085),1,tr)
        for y in [-5.15,-3.85,-2.55,-1.25,.05,1.35,2.65,3.95,5.25]:
            # Narrow visible rafter end; its depth is a deliberate Haven-inspired detail.
            wood.block((side*6.33,y,6.575),(.52,.115,.15),0,tr)
        for y in [-4.55,-1.55,1.55,4.55]:
            poly=[(side*6.12,6.22),(side*6.12,6.62),(side*6.57,6.62),
                  (side*6.43,6.50),(side*6.31,6.45)]
            if side<0:poly.reverse()
            wood.prism_xz(poly,y,.13,1,tr)
    for y in [-6.08,6.08]:
        wood.beam((-6.68,y,6.665),(0,y,8.515),.09,.125,0,tr)
        wood.beam((0,y,8.515),(6.68,y,6.665),.09,.125,0,tr)
    # Garage fascia gets just a crisp shadow band below the broad original colored fascia.
    wood.block((9.5,-5.247,3.045),(7.35,.095,.10),0,tr)
    wood.block((9.5,5.814,3.225),(7.35,.095,.12),0,tr)
    wood.block((13.173,.35,3.225),(.09,10.98,.12),0,tr)
    for x in [6.2,7.7,9.2,10.7,12.2]:
        wood.block((x,-5.143,3.053),(.125,.35,.15),1,tr)
    masonry.finish(collection)
    ledges.finish(collection,bevel=.008)
    wood.finish(collection,bevel=.012)
    report['buildings'].append(label)


def apply():
    bpy.context.view_layer.update()
    scene=bpy.context.scene
    # Idempotent reruns replace only this module's own collection.
    old=bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(old)
    collection=bpy.data.collections.new(COLLECTION);scene.collection.children.link(collection)
    colors=[(.48,.49,.425),(.535,.535,.462),(.58,.56,.480),(.625,.605,.518),
            (.65,.625,.530),(.565,.575,.512),(.68,.65,.560),(.595,.565,.455)]
    limestone=[_mat(PREFIX+'Limestone_%02d'%(i+1),c,.89) for i,c in enumerate(colors)]
    mortar=_mat(PREFIX+'RecessedStoneJoints',(.255,.282,.251),.96)
    timber=[_mat(PREFIX+'WeatheredTimber',(.16,.195,.183),.90),
            _mat(PREFIX+'TimberEdge',(.235,.26,.232),.88)]
    cream=_mat(PREFIX+'LimestoneCoping',(.735,.710,.605),.87)
    rng=random.Random(SEED)
    report={'collection':COLLECTION,'seed':SEED,'paving_stones':0,'masonry_blocks':0,
            'floor_surfaces':[],'buildings':[],'collision':'No collider geometry added',
            'materials':'constant ordinary Principled PBR, no procedural texture dependency'}
    floors=[o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('COL_') and
            any(o.name.startswith(p)for p in ['Approach_sidewalk','Culdesac_footway',
            'Backyard_terrace','Side_lane_paving','Driveway','Entry_path'])]
    for o in sorted(floors,key=lambda x:x.name):
        if o.name.startswith('Culdesac_footway'):_floor_arc(o,limestone,mortar,collection,rng,report)
        else:_floor_rect(o,limestone,mortar,collection,rng,report)
    for sign in [1,-1]:_building(sign,limestone,timber,cream,collection,rng,report)
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    counts=[]
    for o in collection.objects:
        ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
        counts.append({'object':o.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices)})
        ev.to_mesh_clear()
    report['objects']=len(counts);report['evaluated_triangles']=sum(x['triangles']for x in counts)
    report['evaluated_vertices']=sum(x['vertices']for x in counts)
    report['object_counts']=counts
    report['budget_ok']=report['evaluated_triangles']<=35000
    collection['evaluated_triangles']=report['evaluated_triangles']
    collection['art_detail']='Shallow irregular limestone, masonry skirt, weathered timber eaves'
    scene['v2_architecture_report']='%d paving stones, %d masonry blocks, %d evaluated triangles'%(report['paving_stones'],report['masonry_blocks'],report['evaluated_triangles'])
    if not report['budget_ok']:
        raise RuntimeError('Architecture detail triangle budget exceeded: %d'%report['evaluated_triangles'])
    return report


if __name__=='__main__':
    import json
    print('ARCHITECTURE_REPORT='+json.dumps(apply(),indent=2))
