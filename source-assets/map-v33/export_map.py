"""Export a disposable Blender session without saving over its editable source.

blender -b build/Sunward_ClassicLayout_v3_3.blend -t 2 -P export_map.py
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import bpy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_visual(obj):
    # Exact accepted source/export filter: atmosphere cards and helper/proxy
    # collections are source-only. The runtime supplies its own distant sky.
    if obj.type not in {'MESH', 'CURVE', 'FONT'} or obj.name.startswith(('COL_', 'LAYOUT_ANCHOR_')):
        return False
    if obj.hide_render or any(c.hide_render or c.name.startswith(('80_', '90_', '91_', '92_', '99_', 'V3_COLLISION')) for c in obj.users_collection):
        return False
    return True


def unhide_tree(layer):
    layer.exclude = False
    layer.hide_viewport = False
    for child in layer.children:
        unhide_tree(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent / 'build' / 'exports')
    parser.add_argument('--version', default='3.3')
    arguments = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    args = parser.parse_args(arguments)
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', args.version):
        raise ValueError('Version must contain only dot-separated numbers')
    source = Path(bpy.data.filepath)
    if not source.is_file():
        raise ValueError('Open a saved native source before exporting')
    source_hash = sha(source)
    output = args.output_dir.resolve()
    visual_path = output / f'sunward-v{args.version}.glb'
    collision_path = output / f'sunward-collision-v{args.version}.glb'
    gzip_path = visual_path.with_suffix('.glb.gz')
    report_path = output / 'export-report.json'
    for path in (visual_path, collision_path, gzip_path, report_path):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'Refusing to overwrite an existing export: {path}')
    output.mkdir(parents=True, exist_ok=True)
    for collection in bpy.data.collections:
        collection.hide_viewport = False
    unhide_tree(bpy.context.view_layer.layer_collection)
    for obj in bpy.data.objects:
        obj.hide_viewport = False
        obj.hide_set(False)
    bpy.context.view_layer.update()
    visuals = [obj for obj in bpy.data.objects if is_visual(obj)]
    colliders = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.name.startswith('COL_V3_')]
    if not visuals or not colliders:
        raise ValueError('Expected visual objects and V3 collision proxies')
    graph = bpy.context.evaluated_depsgraph_get()
    copies = bpy.data.collections.new('99_V3_OptimizedExport')
    bpy.context.scene.collection.children.link(copies)
    groups = {}
    for obj in visuals:
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph), preserve_all_data_layers=True, depsgraph=graph)
        copy = bpy.data.objects.new(obj.name + '_Export', mesh)
        copies.objects.link(copy)
        copy.matrix_world = obj.matrix_world.copy()
        owner = sorted(collection.name for collection in obj.users_collection)[0]
        materials = tuple(material.name if material else 'none' for material in mesh.materials)
        groups.setdefault((owner, materials), []).append(copy)
    for (owner, materials), objects in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        if len(objects) > 1:
            bpy.ops.object.join()
        bpy.context.object.name = owner + '__' + '_'.join(materials or ['default'])

    def export(path, objects, collision=False):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.context.view_layer.update()
        bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                                  export_apply=True, export_extras=True, export_yup=True,
                                  export_materials='NONE' if collision else 'EXPORT')

    export(visual_path, list(copies.objects))
    export(collision_path, colliders, collision=True)
    with gzip_path.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', compresslevel=9, mtime=0) as compressed:
        compressed.write(visual_path.read_bytes())
    if sha(source) != source_hash:
        raise RuntimeError('The loaded source changed on disk during export')
    report = {
        'source': source.name, 'source_sha256': source_hash, 'source_bytes_unchanged': True,
        'visual_source_objects': len(visuals), 'optimized_visual_meshes': len(copies.objects),
        'collider_objects': len(colliders), 'blender_version': bpy.app.version_string,
        'outputs': [{'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}
                    for path in (visual_path, collision_path, gzip_path)],
        'scope': 'Native-source export only; source is never saved. Separate source/reimport/runtime checks remain required.',
    }
    with report_path.open('x') as file:
        json.dump(report, file, indent=2)
        file.write('\n')
    print('SUNWARD_EXPORT_COMPLETE', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
