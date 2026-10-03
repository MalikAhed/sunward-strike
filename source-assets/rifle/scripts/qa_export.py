"""Read-only Blender + binary GLB QA for an exterior, rigid-part game prop.

Run with Blender 4.3:
  blender -b -P qa_export.py -- --blend ASSET.blend --glb ASSET.glb 
      --report REPORT.json --render-dir DIRECTORY
The script never saves over the input blend or GLB. Renders inspect the reimport.
"""
import argparse
import hashlib
import json
import math
import os
import struct
import sys
from collections import Counter

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blend')
    p.add_argument('--glb', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--render-dir')
    p.add_argument('--ads-render', action='store_true',
                   help='Also render a game-view ADS check of the reimport at 1280x720')
    p.add_argument('--min-tris', type=int, default=15000)
    p.add_argument('--max-tris', type=int, default=30000)
    return p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


REPORT = {'errors': [], 'warnings': []}
SCENE_POINTS = {}


def error(message):
    REPORT['errors'].append(message)


def warning(message):
    REPORT['warnings'].append(message)


def finite(values):
    return all(math.isfinite(float(x)) for x in values)


def scene_stats(label):
    SCENE_POINTS[label] = {}
    stats = {'objects': len(bpy.context.scene.objects), 'mesh_objects': 0,
             'triangles': 0, 'vertices': 0, 'materials': [], 'uv_missing': [],
             'non_identity_scale': [], 'negative_determinant': [],
             'nonfinite_objects': [], 'degenerate_triangles': 0,
             'boundary_edges': 0, 'nonmanifold_edges': 0, 'meshes': {}, 'pbr_materials': {}}
    mats = set()
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.context.scene.objects:
        if not finite(x for row in obj.matrix_world for x in row):
            stats['nonfinite_objects'].append(obj.name)
        if obj.type != 'MESH':
            continue
        stats['mesh_objects'] += 1
        if max(abs(x - 1) for x in obj.scale) > 1e-5:
            stats['non_identity_scale'].append(obj.name)
        if obj.matrix_world.determinant() < 0:
            stats['negative_determinant'].append(obj.name)
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            stats['vertices'] += len(mesh.vertices)
            stats['triangles'] += len(mesh.loop_triangles)
            if not mesh.uv_layers:
                stats['uv_missing'].append(obj.name)
            if not finite(c for v in mesh.vertices for c in v.co):
                error(label + ': nonfinite mesh positions in ' + obj.name)
            if not finite(c for p in mesh.polygons for c in p.normal):
                error(label + ': nonfinite polygon normals in ' + obj.name)
            stats['degenerate_triangles'] += sum(t.area < 1e-12 for t in mesh.loop_triangles)
            points = [obj.matrix_world @ v.co for v in mesh.vertices]
            SCENE_POINTS[label][obj.name] = [tuple(p) for p in points]
            material_counts = Counter()
            for t in mesh.loop_triangles:
                material = mesh.materials[t.material_index] if t.material_index < len(mesh.materials) else None
                material_counts[material.name if material else '<none>'] += 1
            stats['meshes'][obj.name] = {
                'triangles': len(mesh.loop_triangles),
                'world_bounds': [[min(p[i] for p in points) for i in range(3)],
                                 [max(p[i] for p in points) for i in range(3)]],
                'material_triangle_counts': dict(material_counts),
                'zero_area_triangles': sum(t.area < 1e-12 for t in mesh.loop_triangles)}
            for layer in mesh.uv_layers:
                if not finite(c for uv in layer.data for c in uv.uv):
                    error(label + ': nonfinite UV values in ' + obj.name)
            edge_use = Counter()
            for p in mesh.polygons:
                for pair in p.edge_keys:
                    edge_use[tuple(sorted(pair))] += 1
            stats['boundary_edges'] += sum(n == 1 for n in edge_use.values())
            stats['nonmanifold_edges'] += sum(n > 2 for n in edge_use.values())
            mats.update(m.name for m in mesh.materials if m)
        finally:
            evaluated.to_mesh_clear()
    stats['materials'] = sorted(mats)
    for name in stats['materials']:
        material = bpy.data.materials[name]
        principled = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if material.node_tree else None
        if principled:
            stats['pbr_materials'][name] = {
                'base_color': list(principled.inputs['Base Color'].default_value),
                'metallic': float(principled.inputs['Metallic'].default_value),
                'roughness': float(principled.inputs['Roughness'].default_value),
                'specular_ior_level': float(principled.inputs['Specular IOR Level'].default_value)}
    if stats['nonfinite_objects']:
        error(label + ': nonfinite object matrices')
    if stats['negative_determinant']:
        warning(label + ': mirrored transforms on ' + ', '.join(stats['negative_determinant']))
    if stats['uv_missing']:
        warning(label + ': ' + str(len(stats['uv_missing'])) + ' meshes have no UV layer')
    if stats['degenerate_triangles']:
        warning(label + ': ' + str(stats['degenerate_triangles']) + ' near-zero-area triangles')
    return stats


def compare_rest_pose(doc, source, imported):
    result = {}
    for node in doc.get('nodes', []):
        if 'mesh' not in node:
            continue
        name = node.get('name', '')
        before = source['meshes'].get(name)
        after = imported['meshes'].get(name)
        if before is None or after is None:
            error('Cannot compare exported mesh to its source by node name: ' + name)
            continue
        delta = max(abs(a - b) for ra, rb in zip(before['world_bounds'], after['world_bounds'])
                    for a, b in zip(ra, rb))
        same_materials = before['material_triangle_counts'] == after['material_triangle_counts']
        def nearest_error(points_a, points_b):
            tree = KDTree(len(points_a))
            for i, point in enumerate(points_a):
                tree.insert(point, i)
            tree.balance()
            return max(tree.find(point)[2] for point in points_b)
        source_points = SCENE_POINTS['Source'][name]
        import_points = SCENE_POINTS['Reimport'][name]
        position_error = max(nearest_error(source_points, import_points),
                             nearest_error(import_points, source_points))
        result[name] = {'maximum_world_bounds_delta': delta,
                        'bidirectional_vertex_position_error': position_error,
                        'same_material_triangle_counts': same_materials,
                        'same_triangles': before['triangles'] == after['triangles']}
        if delta > 1e-5:
            error('GLB default-pose mesh differs from Blender source in world position: ' + name +
                  ' (bounds delta %.6f)' % delta)
        elif position_error > 1e-5:
            error('GLB mesh vertex positions differ from Blender source: ' + name +
                  ' (nearest-vertex error %.6f)' % position_error)
        if not same_materials:
            error('GLB material assignment triangle counts differ from source: ' + name)
    for material in doc.get('materials', []):
        name = material.get('name', '')
        before = source['pbr_materials'].get(name)
        after = imported['pbr_materials'].get(name)
        if before is None or after is None:
            error('Source/reimport Principled material missing: ' + name)
            continue
        material_delta = max([abs(a-b) for a, b in zip(before['base_color'], after['base_color'])] +
                             [abs(before[key]-after[key]) for key in ['metallic', 'roughness', 'specular_ior_level']])
        if material_delta > 1e-5:
            error('Source/reimport PBR material differs: ' + name + ' (delta %.6f)' % material_delta)
    return result


def load_glb(path):
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) < 12:
        raise ValueError('GLB shorter than header')
    magic, version, length = struct.unpack_from('<4sII', data, 0)
    if magic != b'glTF' or version != 2 or length != len(data):
        raise ValueError('Invalid GLB magic, version, or declared length')
    doc, binary = None, None
    offset = 12
    while offset < len(data):
        chunklen, kind = struct.unpack_from('<II', data, offset)
        offset += 8
        chunk = data[offset:offset + chunklen]
        if len(chunk) != chunklen:
            raise ValueError('GLB chunk exceeds file bounds')
        if kind == 0x4E4F534A:
            doc = json.loads(chunk.decode('utf8'))
        elif kind == 0x004E4942:
            binary = chunk
        offset += chunklen
    if doc is None or binary is None:
        raise ValueError('GLB requires JSON and embedded binary chunks')
    return doc, binary, len(data)


def accessor(doc, binary, index):
    a = doc['accessors'][index]
    components = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4,
                  'MAT2': 4, 'MAT3': 9, 'MAT4': 16}[a['type']]
    fmt, size = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
                 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}[a['componentType']]
    if 'sparse' in a:
        raise ValueError('Sparse accessors are not supported by this QA script')
    if 'bufferView' not in a:
        return [(0,) * components] * a['count']
    view = doc['bufferViews'][a['bufferView']]
    if view.get('buffer', 0) != 0:
        raise ValueError('Accessor refers to a non-embedded buffer')
    start = view.get('byteOffset', 0) + a.get('byteOffset', 0)
    step = view.get('byteStride', components * size)
    end = start + max(0, a['count'] - 1) * step + components * size
    view_end = view.get('byteOffset', 0) + view['byteLength']
    if end > len(binary) or end > view_end:
        raise ValueError('Accessor exceeds its buffer view or BIN chunk')
    return [struct.unpack_from('<' + fmt * components, binary, start + i * step)
            for i in range(a['count'])]


def raw_glb_stats(doc, binary, byte_count):
    result = {'bytes': byte_count, 'mesh_count': len(doc.get('meshes', [])),
              'node_count': len(doc.get('nodes', [])), 'primitive_count': 0,
              'triangles': 0, 'material_count': len(doc.get('materials', [])),
              'materials': [m.get('name', '') for m in doc.get('materials', [])],
              'skins': len(doc.get('skins', [])), 'animations': []}
    def json_finiteness(value, path='glTF'):
        if isinstance(value, float) and not math.isfinite(value):
            error('GLB JSON contains nonfinite value at ' + path)
        elif isinstance(value, dict):
            for key, item in value.items():
                json_finiteness(item, path + '.' + key)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                json_finiteness(item, path + '[' + str(idx) + ']')
    json_finiteness(doc)
    # All floating point buffers, including UVs/normals/tangents and clip data.
    for i, a in enumerate(doc.get('accessors', [])):
        values = accessor(doc, binary, i)
        if a['componentType'] == 5126 and not finite(c for row in values for c in row):
            error('GLB accessor %d contains NaN or infinity' % i)
    for mesh in doc.get('meshes', []):
        for primitive in mesh.get('primitives', []):
            result['primitive_count'] += 1
            if primitive.get('mode', 4) != 4:
                error('GLB has a primitive that is not TRIANGLES')
            attrs = primitive.get('attributes', {})
            if 'POSITION' not in attrs or 'NORMAL' not in attrs:
                error('GLB primitive lacks positions or normals')
                continue
            count = doc['accessors'][attrs['POSITION']]['count']
            for semantic, idx in attrs.items():
                if doc['accessors'][idx]['count'] != count:
                    error('GLB primitive attribute counts differ: ' + semantic)
            if 'TEXCOORD_0' not in attrs:
                warning('GLB primitive lacks UV0 in mesh ' + mesh.get('name', '?'))
            if 'indices' in primitive:
                idx = [row[0] for row in accessor(doc, binary, primitive['indices'])]
                if len(idx) % 3 or any(i < 0 or i >= count for i in idx):
                    error('GLB primitive has invalid triangle indices')
                result['triangles'] += len(idx) // 3
            else:
                if count % 3:
                    error('GLB unindexed primitive count is not divisible by 3')
                result['triangles'] += count // 3
    for buffer in doc.get('buffers', []):
        if 'uri' in buffer and not buffer['uri'].startswith('data:'):
            error('GLB has external buffer dependency')
    for im in doc.get('images', []):
        if 'uri' in im and not im['uri'].startswith('data:'):
            error('GLB has external image dependency: ' + im['uri'])
    if result['material_count'] > 16:
        warning('GLB uses more than 16 materials')
    for anim in doc.get('animations', []):
        channels = []
        moving_channels = 0
        duration = 0.0
        for ch in anim.get('channels', []):
            s = anim['samplers'][ch['sampler']]
            times = [row[0] for row in accessor(doc, binary, s['input'])]
            values = accessor(doc, binary, s['output'])
            if any(a > b for a, b in zip(times, times[1:])):
                error('GLB clip time keys are not sorted')
            if times:
                duration = max(duration, times[-1] - times[0])
            if s.get('interpolation') == 'CUBICSPLINE':
                values = values[1::3]
            spread = max((max(c) - min(c) for c in zip(*values)), default=0.0)
            moving = spread > 1e-6
            moving_channels += int(moving)
            nodeidx = ch['target'].get('node')
            node = doc.get('nodes', [])[nodeidx] if nodeidx is not None else {}
            channels.append({'node': node.get('name', str(nodeidx)),
                             'path': ch['target']['path'], 'keys': len(times),
                             'maximum_component_range': spread, 'moving': moving})
        result['animations'].append({'name': anim.get('name', ''),
            'duration_seconds': duration, 'channels': channels,
            'moving_channels': moving_channels})
        if not moving_channels:
            error('GLB animation has no changing channel: ' + anim.get('name', '?'))
    return result


def imported_motion(clips):
    objects = list(bpy.context.scene.objects)
    result = []
    for clip in clips:
        clipname = clip['name']
        matches = []
        for obj in objects:
            ad = obj.animation_data
            if not ad:
                continue
            # glTF importer stashes clips in NLA tracks under their export name.
            for track in ad.nla_tracks:
                track.mute = True
                if track.name == clipname or track.name.startswith(clipname + '.'):
                    matches.extend((obj, strip.action) for strip in track.strips if strip.action)
            ad.action = None
        if not matches:
            # Diagnostic fallback for importers that leave action names only.
            for obj in objects:
                candidates = [a for a in bpy.data.actions
                              if a.name == clipname + '_' + obj.name
                              or a.name == clipname + '|' + obj.name]
                matches.extend((obj, a) for a in candidates)
        for obj, action in matches:
            obj.animation_data.action = action
        if not matches:
            error('Reimport could not activate animation clip: ' + clipname)
            result.append({'name': clipname, 'activated': False})
            continue
        first = min(float(action.frame_range[0]) for _, action in matches)
        last = max(float(action.frame_range[1]) for _, action in matches)
        samples = [first + (last - first) * i / 16 for i in range(17)]
        world = {obj.name: [] for obj in objects if obj.type == 'MESH'}
        for frame in samples:
            whole = math.floor(frame)
            bpy.context.scene.frame_set(whole, subframe=frame - whole)
            deps = bpy.context.evaluated_depsgraph_get()
            for obj in objects:
                if obj.type == 'MESH':
                    matrix = obj.evaluated_get(deps).matrix_world
                    values = [x for row in matrix for x in row]
                    if not finite(values):
                        error('Reimport clip produces nonfinite matrix: ' + clipname)
                    world[obj.name].append(values)
        movement = {}
        for name, matrices in world.items():
            delta = max((max(c) - min(c) for c in zip(*matrices)), default=0.0)
            if delta > 1e-6:
                movement[name] = delta
        result.append({'name': clipname, 'activated': True,
                       'frame_range': [first, last], 'samples': len(samples),
                       'animated_objects': sorted(set(o.name for o, _ in matches)),
                       'visibly_moving_meshes': movement})
        if not movement:
            error('Reimport clip does not move any visible mesh: ' + clipname)
        for obj, _ in matches:
            obj.animation_data.action = None
    bpy.context.scene.frame_set(0)
    return result


def render_reimport(directory, ads=False):
    os.makedirs(directory, exist_ok=True)
    scene = bpy.context.scene
    # Rest state matrices recorded before animation activation are restored by main.
    points = [obj.matrix_world @ Vector(corner)
              for obj in scene.objects if obj.type == 'MESH' for corner in obj.bound_box]
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center, extent = (lo + hi) / 2, hi - lo
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('QA Studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .58, .63, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    span = max(extent)
    for name, rel, power, size in [('Key', (-.4, -1, 1.5), 1500, 1.4),
                                  ('Fill', (.5, -.7, .3), 800, 1.2),
                                  ('Rim', (.4, 1, 1), 2000, 1.2)]:
        data = bpy.data.lights.new('QA ' + name, 'AREA')
        data.energy = power * (span / 8) ** 2
        data.shape = 'DISK'
        data.size = span * size
        obj = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(rel) * span
        obj.rotation_euler = (center - obj.location).to_track_quat('-Z', 'Y').to_euler()
    camdata = bpy.data.cameras.new('QA Camera')
    cam = bpy.data.objects.new('QA Camera', camdata)
    scene.collection.objects.link(cam)
    scene.camera = cam
    camdata.type = 'ORTHO'
    camdata.ortho_scale = max(extent.x * 1.08, extent.z * 1500 / 700 * 1.08)
    views = [('qa-left-broadside.png', Vector((0, -1.5, 0))),
             ('qa-right-broadside.png', Vector((0, 1.5, 0))),
             ('qa-three-quarter.png', Vector((.65, -1.5, .55)))]
    files = []
    for filename, rel in views:
        cam.location = center + rel * span
        cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.abspath(os.path.join(directory, filename))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        files.append(path)
    if ads:
        # Fixed revision-2 game camera; this is visual clarity QA, not sight calibration.
        camdata.type = 'PERSP'
        camdata.sensor_fit = 'HORIZONTAL'
        camdata.sensor_width = 36
        camdata.lens = 32
        camdata.clip_start = .02
        cam.location = (1.85, 0, 1.48)
        cam.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
        scene.render.resolution_x = 1280
        scene.render.resolution_y = 720
        def stage_box(name, location, dimensions, color):
            bpy.ops.mesh.primitive_cube_add(size=1, location=location)
            obj = bpy.context.object
            obj.name = name
            obj.dimensions = dimensions
            material = bpy.data.materials.new(name + ' Material')
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get('Principled BSDF')
            bsdf.inputs['Base Color'].default_value = (*color, 1)
            bsdf.inputs['Roughness'].default_value = .85
            obj.data.materials.append(material)
            return obj
        stage_box('QA ADS Wall', (-18, 0, 2), (.1, 22, 10), (.44, .55, .60))
        stage_box('QA ADS Center Marker', (-17.75, 0, 1.48), (.18, .8, .8), (.85, .60, .24))
        for y in [-8, -4, 4, 8]:
            stage_box('QA ADS Vertical Line', (-17.9, y, 2), (.14, .12, 7), (.15, .28, .34))
        for z in [-.4, 3.2, 5.2]:
            stage_box('QA ADS Horizontal Line', (-17.9, 0, z), (.14, 20, .05), (.15, .28, .34))
        path = os.path.abspath(os.path.join(directory, 'qa-ads-reimport.png'))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        files.append(path)
    return files


def main():
    args = arguments()
    REPORT['blender_version'] = bpy.app.version_string
    REPORT['inputs'] = {'blend': args.blend, 'glb': args.glb}
    def checksum(path):
        if not path:
            return None
        with open(path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    initial_hashes = {name: checksum(path) for name, path in REPORT['inputs'].items()}
    REPORT['input_sha256'] = initial_hashes
    if args.blend:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args.blend))
        REPORT['source_scene'] = scene_stats('Source')
    doc, binary, byte_count = load_glb(args.glb)
    REPORT['glb'] = raw_glb_stats(doc, binary, byte_count)
    REPORT['glb']['triangle_target'] = [args.min_tris, args.max_tris]
    REPORT['glb']['triangle_target_met'] = args.min_tris <= REPORT['glb']['triangles'] <= args.max_tris
    if not REPORT['glb']['triangle_target_met']:
        warning('GLB triangle count %d is outside requested %d–%d target' %
                (REPORT['glb']['triangles'], args.min_tris, args.max_tris))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(args.glb))
    bpy.context.scene.frame_set(0)
    rest = {obj.name: obj.matrix_basis.copy() for obj in bpy.context.scene.objects}
    REPORT['reimport'] = scene_stats('Reimport')
    if args.blend:
        REPORT['source_reimport_comparison'] = compare_rest_pose(doc, REPORT['source_scene'], REPORT['reimport'])
    if REPORT['reimport']['triangles'] != REPORT['glb']['triangles']:
        error('Reimport triangle count does not match GLB data')
    REPORT['animation_motion'] = imported_motion(REPORT['glb']['animations'])
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data.action = None
            for track in obj.animation_data.nla_tracks:
                track.mute = True
        obj.matrix_basis = rest[obj.name]
    bpy.context.view_layer.update()
    if args.render_dir:
        REPORT['renders'] = render_reimport(args.render_dir, args.ads_render)
    for name, path in REPORT['inputs'].items():
        if checksum(path) != initial_hashes[name]:
            error('Input file changed during QA: ' + str(path))
    REPORT['passed'] = not REPORT['errors']
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, 'w') as f:
        json.dump(REPORT, f, indent=2)
    print('QA_REPORT', os.path.abspath(args.report))
    print('QA_RESULT', json.dumps({'passed': REPORT['passed'], 'triangles': REPORT['glb']['triangles'],
                                  'materials': REPORT['glb']['material_count'],
                                  'clips': len(REPORT['glb']['animations']),
                                  'errors': REPORT['errors'], 'warnings': REPORT['warnings']}))
    if not REPORT['passed']:
        raise RuntimeError('GLB QA failed; inspect report')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        REPORT['passed'] = False
        REPORT['exception'] = repr(exc)
        try:
            args = arguments()
            with open(args.report, 'w') as f:
                json.dump(REPORT, f, indent=2)
        except Exception:
            pass
        raise
