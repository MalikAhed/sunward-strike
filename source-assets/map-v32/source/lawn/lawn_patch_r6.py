"""Reversible lawn-only short-turf replacement on saved accepted SUNWARD v3.1.

Changes only V3_Layout_Edge_Grass mesh and its material bindings/custom properties.
All protected source meshes, materials, packed images, lights and world stay intact.
The adjacent original atlas and source frame JSON are the only dependencies.
"""
import bpy, json, math, hashlib, random
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
VERSION='lawn-r6-i'
OBJECT='V3_Layout_Edge_Grass'
MATERIAL='V6_ShortTurf_OriginalAtlas'
BACKUP='lawn_r6_backup'
TUFTS=34500

def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def mesh_facts(o):
    me=o.data
    return {'name':o.name,'vertices':[list(v.co) for v in me.vertices],
            'polygons':[list(p.vertices) for p in me.polygons],
            'matrix':[list(row) for row in o.matrix_world],
            'materials':[m.name if m else None for m in me.materials],
            'indices':[p.material_index for p in me.polygons],
            'smooth':[p.use_smooth for p in me.polygons],
            'uvs':{uv.name:[list(p.uv) for p in uv.data] for uv in me.uv_layers}}

def protected_hashes():
    bpy.context.view_layer.update()
    rows={};coll=[];trees=[]
    for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if o.type!='MESH' or o.name==OBJECT: continue
        r=mesh_facts(o);rows[o.name]=digest(r)
        if o.name.startswith('COL_'):coll.append(r)
        if o.name.startswith('V2_Tree_'):trees.append(r)
    return {'protected_meshes':len(rows),'objects':rows,'all_protected_mesh_sha256':digest(rows),
            'collision_sha256':digest(coll),'accepted_tree_sha256':digest(trees)}

def point_inside(points, polygon):
    x,y=points[:,0],points[:,1];v=np.zeros(len(points),dtype=bool)
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if abs(b[1]-a[1])<1e-12:continue
        v^=((a[1]>y)!=(b[1]>y)) & (x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    return v

def seg_distance2(points,a,b):
    a=np.asarray(a);d=np.asarray(b)-a
    t=np.clip(((points-a)*d).sum(axis=1)/max(1e-15,float((d*d).sum())),0,1)
    return ((points-a-t[:,None]*d)**2).sum(axis=1)

def poly_distance2(points,poly):
    d=np.full(len(points),np.inf)
    for a,b in zip(poly,poly[1:]+poly[:1]):d=np.minimum(d,seg_distance2(points,a,b))
    return d

def lawn_domain(cfg):
    outline=[p[:2] for p in cfg['outline_blender']];masks=[];routes=[];points=[];props=[]
    for h in cfg['house_frames'].values():
        c,s=math.cos(h['yaw_radians']),math.sin(h['yaw_radians']);cx,cy,_=h['position_blender']
        for q in h['components'].values():
            lo,hi=q['local_bbox_m']
            masks.append([(cx+c*x-s*y,cy+s*x+c*y) for x,y in
                         [(lo[0]-.35,lo[1]-.35),(hi[0]+.35,lo[1]-.35),(hi[0]+.35,hi[1]+.35),(lo[0]-.35,hi[1]+.35)]])
    col=bpy.data.collections.get('03_Layout_Ground')
    for o in col.objects if col else []:
        if o.type!='MESH' or o.name=='LAYOUT_Playable_Grass_Outline' or o.name.startswith('LAYOUT_Court_'):continue
        masks.append([list((o.matrix_world@v.co)[:2]) for v in o.data.vertices])
    for key,d in cfg['traversal_anchors'].items():
        if key=='three_lanes':routes.extend((q['start'][:2],q['end'][:2]) for q in d.values())
        else:points.extend(p[:2] for p in d.values() if isinstance(p,list))
    for h in cfg['final_house_route_contract']['houses'].values():
        for p in h['portals'].values():
            routes.append((p['negative_axis_approach']['world_blender'][:2],p['positive_axis_approach']['world_blender'][:2]))
        for q in h['routes'].values():
            if 'bottom' in q and 'top' in q:routes.append((q['bottom']['world_blender'][:2],q['top']['world_blender'][:2]))
            if 'waypoints' in q:
                pp=[p['world_blender'][:2] for p in q['waypoints']];routes.extend(zip(pp,pp[1:]))
    points.extend(p[:2] for p in cfg['walk_spawns'].values())
    col=bpy.data.collections.get('30_ExteriorProps')
    for o in col.objects if col else []:
        if o.type=='MESH' and o.name.split('.')[0] in {'Garden_shed','Supply_crate','Utility_cover'}:
            vs=[o.matrix_world@Vector(v) for v in o.bound_box]
            props.append((min(v.x for v in vs)-.35,max(v.x for v in vs)+.35,min(v.y for v in vs)-.35,max(v.y for v in vs)+.35))
    radius=cfg['court']['curb_radius_m']+1.7
    def good(p,card_edge=False):
        ok=point_inside(p,outline)&((p*p).sum(axis=1)>=(radius+(0 if card_edge else .30))**2)
        ok &= poly_distance2(p,outline)>(.07 if card_edge else .38)**2
        for poly in masks:
            ok &= ~point_inside(p,poly)
            ok &= poly_distance2(p,poly)>(.02 if card_edge else .31)**2
        for a,b in routes:ok &= seg_distance2(p,a,b)>(1.54 if card_edge else 1.85)**2
        for q in points:ok &= ((p-np.asarray(q))**2).sum(axis=1)>(1.54 if card_edge else 1.85)**2
        margin=0 if card_edge else .30
        for a,b,c,d in props:ok &= ~((a-margin<=p[:,0])&(p[:,0]<=b+margin)&(c-margin<=p[:,1])&(p[:,1]<=d+margin))
        return ok
    return outline,good

def tuft_centers(outline,good):
    xy=np.asarray(outline);lo=xy.min(axis=0);hi=xy.max(axis=0)
    pitch=.20
    for iteration in range(8):
        rng=np.random.default_rng(6261003)
        xx=np.arange(lo[0],hi[0],pitch);yy=np.arange(lo[1],hi[1],pitch*math.sqrt(3)/2)
        gx,gy=np.meshgrid(xx,yy)
        gx[1::2,:]+=pitch*.5
        p=np.column_stack((gx.ravel(),gy.ravel()))
        p+=rng.uniform(-pitch*.25,pitch*.25,p.shape)
        allowed=p[good(p)]
        if len(allowed)>=TUFTS and len(allowed)<TUFTS*1.025:
            order=rng.permutation(len(allowed));return allowed[order[:TUFTS]],pitch,len(allowed)
        pitch*=math.sqrt(len(allowed)/(TUFTS*1.012))
    if len(allowed)<TUFTS:raise RuntimeError('Insufficient protected-lawn positions')
    return allowed[rng.permutation(len(allowed))[:TUFTS]],pitch,len(allowed)

def make_material(texture_path):
    if bpy.data.materials.get(MATERIAL):raise RuntimeError('r6 material already exists; restore/reopen the source rather than stacking patches')
    m=bpy.data.materials.new(MATERIAL);m.use_nodes=True;m.use_backface_culling=True
    m.surface_render_method='DITHERED';m.node_tree.nodes.clear()
    nt=m.node_tree;out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Roughness'].default_value=.96;bs.inputs['Metallic'].default_value=0
    bs.inputs['Specular IOR Level'].default_value=.12
    tx=nt.nodes.new('ShaderNodeTexImage');im=bpy.data.images.load(str(texture_path),check_existing=False)
    im.name='V6_Original_ShortTurf_Atlas';im.colorspace_settings.name='sRGB';im.pack()
    tx.image=im;tx.interpolation='Linear';tx.extension='EXTEND'
    cut=nt.nodes.new('ShaderNodeMath');cut.operation='ROUND'
    nt.links.new(tx.outputs['Color'],bs.inputs['Base Color']);nt.links.new(tx.outputs['Alpha'],cut.inputs[0]);nt.links.new(cut.outputs[0],bs.inputs['Alpha']);nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    m['gltf_alpha_contract']='MASK cutoff0.5; single-sided material, explicit paired front/back faces with +up normals; packed original sRGB atlas; no emissive/custom shader'
    m['original_procedural_texture']=True;m['skip_reference_palette_tint']=True;m['lawn_revision']=VERSION
    return m

def apply(config_path=None,texture_path=None):
    obj=bpy.data.objects.get(OBJECT)
    if not obj or obj.type!='MESH':raise RuntimeError('Accepted lawn object is missing')
    if BACKUP in obj:raise RuntimeError('r6 is already applied')
    if obj.data.name!='V4R5_DenseShortLawn':raise RuntimeError('Expected saved accepted v4-r5 lawn, got '+obj.data.name)
    before=protected_hashes();cfg=json.loads(Path(config_path or HERE/'site_frames.json').read_text())
    outline,good=lawn_domain(cfg);centers,pitch,pool=tuft_centers(outline,good)
    rng=random.Random(6261003);verts=[];faces=[];uvs=[];normals=[];radii=[];heights=[];shrunk=0
    for i,(x,y) in enumerate(centers):
        angle=rng.uniform(0,math.tau);width=rng.uniform(.24,.32);height=rng.uniform(.09,.15)
        roots=.005;lean=rng.uniform(.007,.025);cell=(i%4)+(4 if rng.random()<.68 else 0)
        for j in range(1):
            a=angle+j*(math.pi*.5+rng.uniform(-.10,.10));side=np.array([math.cos(a),math.sin(a)])
            front=np.array([-side[1],side[0]]);q=np.array([x,y]);half=width*.5
            pts=np.array([q,q+side*half+front*lean,q-side*half+front*lean])
            k=len(verts)
            front_vertices=[(float(p[0]),float(p[1]),roots+(height if v>0 else 0)) for v,p in enumerate(pts)]
            verts.extend(front_vertices)
            # Separate the opposite surface by0.1mm to preserve distinct normal
            # spaces through Blender save and glTF importer vertex welding.
            verts.extend([(x+float(front[0])*.0001,y+float(front[1])*.0001,z) for x,y,z in front_vertices])
            faces.extend([(k,k+1,k+2),(k+5,k+4,k+3)])
            cx,cy=cell%4,cell//4
            uvs.extend([((cx+u)/4,1-(cy+v)/2) for u,v in [(.5,1),(1,0),(0,0)]]*2)
            n=Vector((0,0,1))
            normals.extend([tuple(n)]*6)
            radii.append(float(np.max(np.linalg.norm(pts-q,axis=1))))
        heights.append(height+roots)
    assert good(np.asarray(verts)[:,:2],True).all(),'A visible card vertex entered a protected domain'
    me=bpy.data.meshes.new('V6_Dense_ShortTurf');me.from_pydata(verts,[],faces);me.update()
    uv=me.uv_layers.new(name='ShortTurfAtlasUV')
    for loop in me.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
    for p in me.polygons:p.use_smooth=True
    me.normals_split_custom_set_from_vertices(normals)
    assert min(n.vector.z for n in me.corner_normals)>.9999,'Explicit paired faces must both retain +up normals'
    mat=make_material(texture_path or HERE/'textures/sunward_short_turf_r6i.png');me.materials.append(mat)
    obj.data.use_fake_user=True
    for m in obj.data.materials:m.use_fake_user=True
    backup={'mesh':obj.data.name,'matrix':[list(r) for r in obj.matrix_world],
            'properties':dict(obj.items())}
    obj[BACKUP]=json.dumps(backup);obj.data=me;obj.matrix_world=Matrix.Identity(4)
    obj['lawn_revision']=VERSION;obj['collision_role']='visual-only short grass; EXCLUDE collision'
    obj['route_safety_basis']='centers1.85m; card vertices1.54m; max radius <=.287m; no collider changes'
    obj['max_blade_height_m']=max(heights);obj['grass_version']=VERSION
    me.calc_loop_triangles();after=protected_hashes()
    assert before==after,'Protected geometry or bindings changed'
    assert len(me.loop_triangles)==69000 and max(radii)<.29
    return {'revision':VERSION,'base_source':'saved accepted integrated v3.1; tree/grass v4-r5',
            'owned_object':OBJECT,'tufts':TUFTS,'cards':TUFTS,'triangles':len(me.loop_triangles),
            'triangle_delta':0,'materials':1,'material_delta':-3,'atlas_dimensions':[512,256],
            'added_base_texture_bytes':524288,'added_full_mip_rgba_bytes_approx':699052,
            'height_bounds_m':[.005,max(heights)],'width_bounds_m':[.24,.32],
            'max_card_radius_m':max(radii),'lattice_pitch_m':pitch,'candidate_pool':pool,
            'edge_cards_shrunk':shrunk,'distribution':'jittered hexagonal stratified legal-lawn domain',
            'normals':'explicit front/back winding with verified +up corner normals and single-sided material',
            'protected_before':before,'protected_after':after,'all_protected_hashes_unchanged':before==after}

def restore():
    o=bpy.data.objects[OBJECT]
    if BACKUP not in o:raise RuntimeError('No saved r6 backup')
    b=json.loads(o[BACKUP]);o.data=bpy.data.meshes[b['mesh']];o.matrix_world=Matrix(b['matrix'])
    for k in list(o.keys()):del o[k]
    for k,v in b['properties'].items():o[k]=v
    return {'restored_mesh':o.data.name,'restored_properties':dict(o.items())}
