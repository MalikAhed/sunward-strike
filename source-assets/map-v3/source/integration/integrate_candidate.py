"""Manager-owned integration. Run on the untouched v2.5 input; write a new copy only."""
import bpy, sys, json, hashlib, time, argparse
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--inputs', default=str(ROOT))
parser.add_argument('--output', default=str(ROOT / 'integration/Sunward_ClassicLayout_v3_candidate.blend'))
parser.add_argument('--coral', action='store_true')
parser.add_argument('--grass', action='store_true')
parser.add_argument('--dressing', action='store_true')
parser.add_argument('--native-style', action='store_true')
parser.add_argument('--version', default='3.0-candidate')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
INPUTS = Path(args.inputs)
BASE = ROOT.parent.parent / 'map/Sunward_TestSite.blend'
BASE_SHA = '460d54859e29c59d809da2bd0497e40ac2c8684630826e89415771847055bfc6'
OUT = ROOT.parent / 'build'
OUT.mkdir(parents=True, exist_ok=True)
assert Path(bpy.data.filepath).resolve() == BASE.resolve(), 'Run on baseline, never a progress blockout'
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
for folder in ['houses', 'layout', 'landmarks']:
    sys.path.insert(0, str(INPUTS / folder))
import house_patch, layout_patch, landmark_patch

frames_path = INPUTS / 'layout/site_frames.json'
frames = json.loads(frames_path.read_text())
report = {'baseline_sha256': BASE_SHA, 'started': time.time(), 'frame_version': frames['version'],
          'input_hashes': {str(p.relative_to(INPUTS)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in INPUTS.rglob('*') if p.is_file() and p.suffix in ['.py', '.json']}}
report['removed_old_house_visuals'] = house_patch.remove_old_house_visuals()
report['houses'] = {}
for house_id in ['A_Mint', 'B_Saffron']:
    _, house_report = house_patch.build_house(house_id, frames=frames['house_frames'])
    report['houses'][house_id] = house_report
report['layout'] = layout_patch.apply(str(frames_path), place_houses=True, remap_decorations=True, build_collision=True)
report['landmarks'] = landmark_patch.apply(str(frames_path))
if args.coral:
    import coral_material_patch
    report['coral'] = coral_material_patch.apply_coral_material_patch()
if args.grass:
    import grass_patch
    report['grass'] = grass_patch.apply(str(frames_path))

if args.dressing:
    sys.path.insert(0, str(INPUTS / 'layout/interior-dressing'))
    import interior_dressing_patch
    report['interiors'] = interior_dressing_patch.apply(str(frames_path))

# One visible exit treatment. The detailed landmark barrier wins; boundary clipping remains.
gate = bpy.data.objects.get('LAYOUT_East_Roadwork_Gate')
had_gate = gate is not None
if gate:
    bpy.data.objects.remove(gate, do_unlink=True)
report['removed_duplicate_gate'] = had_gate
legacy = []
for obj in list(bpy.data.objects):
    if obj.type == 'MESH' and obj.name.startswith('COL_') and not obj.name.startswith('COL_V3_'):
        legacy.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
report['removed_legacy_collision'] = legacy

collision = bpy.data.collections.get('V3_COLLISION')
assert collision is not None
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name.startswith('COL_V3_'):
        if obj.name not in collision.objects:
            collision.objects.link(obj)
        obj.hide_render = True
        obj.display_type = 'WIRE'
        obj.hide_set(False)
        obj.hide_viewport = False
        for collection in obj.users_collection:
            collection.hide_viewport = False
bpy.context.view_layer.update()

scene = bpy.context.scene
scene['build_version'] = args.version
scene['layout_authority'] = 'Official classic Nuketown minimap and original gameplay references; independently authored geometry'
scene['metric_dimensions'] = 'Provisional uniform calibration from 10.5m prototype bus span; not authenticated game meters'
scene['scale_m_per_reference_pixel'] = frames['image_to_world']['uniform_m_per_crop_pixel']
scene['structural_reference_version'] = frames['version']
scene['validation_state'] = 'Candidate awaiting independent integrated geometry, collision, export and traversal checks'
scene['original_branding'] = 'SUNWARD / TEST SITE 07'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1

# The presentation camera is deliberately separate from any browser camera settings.
camera = bpy.data.objects.get('V3_Presentation_Hero')
if camera is None:
    camera = bpy.data.objects.new('V3_Presentation_Hero', bpy.data.cameras.new('V3_Presentation_Hero'))
    scene.collection.objects.link(camera)
camera.location = (65, -82, 73)
target = Vector((-6, 0, 1.5))
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 116
camera.data.clip_end = 1000
scene.camera = camera
scene.render.resolution_x = 1500
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
            area.spaces.active.shading.type = 'SOLID'
            area.spaces.active.shading.color_type = 'MATERIAL'

if args.native_style:
    sys.path.insert(0, str(INPUTS / 'houses/native-style'))
    import native_atmosphere
    report['native_style'] = native_atmosphere.apply_native_style()

for image in bpy.data.images:
    if image.source == 'FILE' and image.has_data and not image.packed_file:
        try:
            image.pack()
        except RuntimeError:
            pass
for obj in collision.objects:
    obj.hide_set(True)
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
report['candidate_path'] = str(path)
report['finished'] = time.time()
(OUT / 'integration-report.json').write_text(json.dumps(report, indent=2))
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
print('CANDIDATE_SAVED', path, flush=True)
