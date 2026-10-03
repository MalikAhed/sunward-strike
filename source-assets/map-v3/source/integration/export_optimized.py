"""Export evaluated disposable copies; never save over the loaded editable scene."""
import bpy, sys, json, hashlib, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'runtime'))
from validate_export import is_visual
source = Path(bpy.data.filepath)
source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
out = ROOT.parent / 'build/exports'
out.mkdir(parents=True, exist_ok=True)

def unhide_tree(layer):
    layer.exclude = False
    layer.hide_viewport = False
    for child in layer.children:
        unhide_tree(child)

for col in bpy.data.collections:
    col.hide_viewport = False
unhide_tree(bpy.context.view_layer.layer_collection)
for obj in bpy.data.objects:
    obj.hide_viewport = False
    obj.hide_set(False)
bpy.context.view_layer.update()
visuals = [o for o in bpy.data.objects if is_visual(o)]
colliders = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('COL_V3_')]
assert visuals and colliders
dg = bpy.context.evaluated_depsgraph_get()
col = bpy.data.collections.new('99_V3_OptimizedExport')
bpy.context.scene.collection.children.link(col)
groups = {}
for obj in visuals:
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    copy = bpy.data.objects.new(obj.name + '_Export', mesh)
    col.objects.link(copy)
    copy.matrix_world = obj.matrix_world.copy()
    owner = sorted(c.name for c in obj.users_collection)[0]
    mats = tuple(m.name if m else 'none' for m in mesh.materials)
    groups.setdefault((owner, mats), []).append(copy)
for (owner, mats), objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    bpy.context.object.name = owner + '__' + '_'.join(mats or ['default'])

def export(path, objects, collision=False):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_extras=True, export_yup=True,
        export_materials='NONE' if collision else 'EXPORT')

visual_path = out / 'sunward-v3.0.glb'
collision_path = out / 'sunward-collision-v3.0.glb'
export(visual_path, list(col.objects))
export(collision_path, colliders, collision=True)
report = {'source': str(source), 'source_sha256': source_sha, 'visual_source_objects': len(visuals),
    'optimized_visual_meshes': len(col.objects), 'collider_objects': len(colliders),
    'outputs': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in [visual_path, collision_path]]}
(out / 'export-report.json').write_text(json.dumps(report, indent=2))
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha
print('V3_EXPORT_COMPLETE', json.dumps(report), flush=True)
