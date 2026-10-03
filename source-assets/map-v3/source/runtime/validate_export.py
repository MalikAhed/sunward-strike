"""Read-only source audit and recoverable GLB export/reimport validation.

blender -b INTEGRATED.blend -P validate_export.py -- --out OUTPUT --export
Exports never write the loaded .blend. Only the manager should invoke --export.
"""
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
DEFAULT_FRAMES = ROOT.parent / 'layout/site_frames.json'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit_object(obj, depsgraph):
    ev = obj.evaluated_get(depsgraph)
    mesh = ev.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    mesh.calc_loop_triangles()
    vertices = [obj.matrix_world @ v.co for v in mesh.vertices]
    lo = [min((v[a] for v in vertices), default=0) for a in range(3)]
    hi = [max((v[a] for v in vertices), default=0) for a in range(3)]
    local_lo=[min((v.co[a] for v in mesh.vertices),default=0) for a in range(3)]
    local_hi=[max((v.co[a] for v in mesh.vertices),default=0) for a in range(3)]
    degenerate = 0
    signed_volume = 0
    up_triangles = 0
    down_triangles = 0
    for face in mesh.loop_triangles:
        a, b, c = [vertices[i] for i in face.vertices]
        n = (b-a).cross(c-a)
        if n.length_squared < 1e-14:
            degenerate += 1
        signed_volume += a.dot(b.cross(c))/6
        if n.length_squared > 1e-14:
            normal = n.normalized()
            if normal.z > .45: up_triangles += 1
            if normal.z < -.45: down_triangles += 1
    result = dict(name=obj.name, type=obj.type, vertices=len(vertices),
        triangles=len(mesh.loop_triangles), bounds_blender=[lo, hi],
        bounds_local=[local_lo,local_hi],dimensions_local=[b-a for a,b in zip(local_lo,local_hi)],
        finite=all(math.isfinite(x) for v in vertices for x in v),
        determinant=obj.matrix_world.determinant(), degenerate_triangles=degenerate,
        signed_volume_m3=signed_volume, upward_support_triangles=up_triangles,
        downward_triangles=down_triangles, materials=[m.name for m in mesh.materials if m],
        collections=[c.name for c in obj.users_collection],
        source_id=obj.get('collision_source_id', obj.get('source_visual_id',obj.get('source_visual'))),
        source_ids=list(obj.get('source_visuals',[])),
        proxy_type=obj.get('proxy_type'),
        matrix_world=[list(row) for row in obj.matrix_world])
    ev.to_mesh_clear()
    return result

def is_visual(obj):
    if obj.type not in {'MESH', 'CURVE', 'FONT'} or obj.name.startswith(('COL_', 'LAYOUT_ANCHOR_')):
        return False
    if obj.hide_render or any(c.hide_render or c.name.startswith(('80_', '90_', '91_', '92_', '99_', 'V3_COLLISION')) for c in obj.users_collection):
        return False
    return True

def combined_bounds(records):
    if not records: return None
    return [[min(r['bounds_blender'][0][a] for r in records) for a in range(3)],
            [max(r['bounds_blender'][1][a] for r in records) for a in range(3)]]

def compare_bounds(a, b):
    return max(abs(x-y) for aa, bb in zip(a,b) for x,y in zip(aa,bb))

def export_selected(path, objects, collision=False):
    bpy.ops.object.select_all(action='DESELECT')
    # Hidden collections need to be enabled for selection, only in this disposable process.
    for obj in objects:
        obj.hide_set(False)
        obj.hide_viewport=False
        for col in obj.users_collection: col.hide_viewport=False
        obj.select_set(True)
    if objects: bpy.context.view_layer.objects.active=objects[0]
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_extras=True, export_yup=True,
        export_materials='NONE' if collision else 'EXPORT')

def enable_collision_evaluation(objects):
    """Enable evaluation before reading matrices, only in this disposable process."""
    cols=set()
    for obj in objects:
        chain=obj
        while chain:
            chain.hide_viewport=False
            chain.hide_set(False)
            for col in chain.users_collection:
                col.hide_viewport=False
                cols.add(col.name)
            chain=chain.parent
    def visit(layer):
        contains=layer.collection.name in cols
        for child in layer.children:
            if visit(child): contains=True
        if contains: layer.exclude=False;layer.hide_viewport=False
        return contains
    visit(bpy.context.view_layer.layer_collection)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get();dg.update()
    return dg

def reimport_audit(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    dg=bpy.context.evaluated_depsgraph_get()
    records=[audit_object(o,dg) for o in bpy.data.objects if o.type=='MESH']
    return dict(meshes=len(records), triangles=sum(o['triangles'] for o in records),
                bounds_blender=combined_bounds(records), objects=records)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--frames',default=str(DEFAULT_FRAMES));ap.add_argument('--export',action='store_true');ap.add_argument('--prefix',default='sunward-v3');ap.add_argument('--visual');ap.add_argument('--collision')
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    source=Path(bpy.data.filepath);source_hash=digest(source)
    started=time.monotonic();frames=json.loads(Path(args.frames).read_text())
    visuals=[o for o in bpy.data.objects if is_visual(o)]
    colliders=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('COL_V3_')]
    dg=enable_collision_evaluation(colliders)
    vr=[audit_object(o,dg) for o in visuals];cr=[audit_object(o,dg) for o in colliders]
    defects=[]
    if abs(bpy.context.scene.unit_settings.scale_length-1)>1e-9: defects.append('scene.unit_settings.scale_length is not 1')
    if not cr: defects.append('no COL_V3_ colliders found')
    old=bpy.data.objects.get('COL_Sunward_Static')
    for r in cr:
        if 'V3_COLLISION' not in r['collections']: defects.append(r['name']+' is outside dedicated V3_COLLISION collection')
        if not r['finite']: defects.append(r['name']+' has nonfinite vertices')
        if r['degenerate_triangles']: defects.append(r['name']+' has degenerate triangles')
        if abs(r['determinant'])<1e-9: defects.append(r['name']+' has singular transform')
        if r['signed_volume_m3'] < -1e-4: defects.append(r['name']+' is a closed or near-closed inward-wound solid')
    floor=next((r for r in cr if r['name']=='COL_V3_LAYOUT_PlayableFloor'),None)
    if not floor: defects.append('COL_V3_LAYOUT_PlayableFloor is missing')
    elif floor['downward_triangles'] or not floor['upward_support_triangles']: defects.append('layout floor has wrong support winding')
    parity=[];visual_by_name={r['name']:r for r in vr}
    textures={}
    for obj in visuals:
        if not hasattr(obj.data,'materials'): continue
        for mat in obj.data.materials:
            if not mat or not mat.use_nodes: continue
            for node in mat.node_tree.nodes:
                if node.type!='TEX_IMAGE' or not node.image: continue
                im=node.image
                packed=bool(im.packed_file or im.packed_files)
                external_path=Path(bpy.path.abspath(im.filepath)) if im.filepath else None
                exists=bool(external_path and external_path.is_file())
                textures[im.name]=dict(name=im.name,source=im.source,size=list(im.size),packed=packed,external_file_exists=exists)
                if im.source=='FILE' and not packed and not exists: defects.append('missing unpacked texture '+im.name)
    for r in cr:
        if r['source_ids']:
            group=[visual_by_name[n] for n in r['source_ids'] if n in visual_by_name]
            if len(group)!=len(r['source_ids']): defects.append(r['name']+' has missing source group visual(s)')
            if group:
                error=compare_bounds(r['bounds_blender'],combined_bounds(group))
                parity.append(dict(collider=r['name'],visual_group=r['source_ids'],bounds_max_error_m=error,scope='intentional solid group bounding box; table/bed underside blocked'))
                if error>.08: defects.append(r['name']+' furniture group AABB mismatch exceeds .08m')
            continue
        source_id=r['source_id']
        if not source_id:
            candidates=[r['name'].replace('COL_V3_','',1),r['name'].replace('COL_V3_LM_','',1)]
            source_id=next((n for n in candidates if n in visual_by_name),None)
        if source_id and source_id in visual_by_name:
            error=compare_bounds(r['bounds_blender'],visual_by_name[source_id]['bounds_blender'])
            partial='trunk' in str(r['proxy_type']).lower()
            parity.append(dict(collider=r['name'],visual=source_id,bounds_max_error_m=error,scope='tight trunk only; branches/leaves decorative' if partial else 'exact solid counterpart'))
            if not partial and error>.08: defects.append(r['name']+' visual/collision AABB mismatch exceeds .08m')
            if partial:
                vb=visual_by_name[source_id]['bounds_blender'];cb=r['bounds_blender']
                if any(cb[0][a]<vb[0][a]-.12 or cb[1][a]>vb[1][a]+.12 for a in range(3)):
                    defects.append(r['name']+' tight trunk proxy extends outside linked tree visual bounds')
    report=dict(schema_version=1,scope='Source geometry, export, clean Blender reimport; no browser input or GPU-frame tests',
        source=str(source),source_sha256=source_hash,frames_sha256=digest(args.frames),
        tool_sha256=digest(__file__),blender_version=bpy.app.version_string,
        frames_version=frames['version'],scale_assumption=frames['scale_assumption'],
        units=dict(system=bpy.context.scene.unit_settings.system,scale_length=bpy.context.scene.unit_settings.scale_length),
        axes=frames['axes'],player_reference=frames['player_reference'],
        scene_extras=dict(bpy.context.scene.items()),legacy_collider_present=bool(old),legacy_collider_excluded=True,
        visual=dict(objects=vr,meshes=len(vr),triangles=sum(r['triangles'] for r in vr),bounds_blender=combined_bounds(vr)),
        collision=dict(objects=cr,meshes=len(cr),triangles=sum(r['triangles'] for r in cr),bounds_blender=combined_bounds(cr)),
        visual_collision_parity=parity,textures=list(textures.values()),defects=defects,unverified=['Browser pointer-lock/keyboard/touch input','Browser WebGL rendering/frame-rate','Visual-reference acceptance belongs to independent reviewer'])
    visual_path=Path(args.visual) if args.visual else out/(args.prefix+'.glb')
    collision_path=Path(args.collision) if args.collision else out/(args.prefix+'-collision.glb')
    if args.export:
        if old and old in colliders: raise RuntimeError('legacy collider entered export selection')
        export_selected(visual_path,visuals)
        export_selected(collision_path,colliders,True)
    for label,path,records in [('visual',visual_path,vr),('collision',collision_path,cr)]:
        if path.is_file():
            imported=reimport_audit(path)
            report[label]['reimport']=dict(path=str(path),sha256=digest(path),bytes=path.stat().st_size,
                meshes=imported['meshes'],triangles=imported['triangles'],bounds_blender=imported['bounds_blender'])
            error=compare_bounds(combined_bounds(records),imported['bounds_blender'])
            report[label]['reimport']['bounds_max_error_m']=error
            if error>.003: defects.append(label+' reimport bounds differ by >.003m')
            if imported['triangles'] != sum(r['triangles'] for r in records): defects.append(label+' reimport triangle count changed')
    report['source_hash_preserved']=digest(source)==source_hash
    if not report['source_hash_preserved']: defects.append('loaded source file hash changed')
    report['elapsed_seconds']=round(time.monotonic()-started,3);report['passed']=not defects
    path=out/'export-audit.json';path.write_text(json.dumps(report,indent=2,default=str))
    print('V3_EXPORT_AUDIT',json.dumps(dict(path=str(path),passed=report['passed'],defects=defects,visual_triangles=report['visual']['triangles'],collision_triangles=report['collision']['triangles'],source_hash_preserved=report['source_hash_preserved'])),flush=True)
    if defects: raise RuntimeError('Source/export gate has defects; see '+str(path))

if __name__=='__main__': main()
