import bpy, math, sys, os, json, importlib
from mathutils import Vector, Quaternion
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT+'/scripts')
# Clean scene and construct artist-modeled exterior only.
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):
    if col.name != 'Collection': bpy.data.collections.remove(col)
asset=bpy.data.collections.get('Collection'); asset.name='GAME_ASSET'
bpy.context.scene.collection.children.get('GAME_ASSET')
root=bpy.data.objects.new('Rifle_ROOT', None); asset.objects.link(root); root.empty_display_type='PLAIN_AXES'; root.empty_display_size=.45
for modname in ['receiver','foreend','stock']:
    try:
        module=importlib.import_module(modname); importlib.reload(module); module.build(); print('BUILT',modname)
    except ModuleNotFoundError: print('NOT_READY',modname)
for o in list(bpy.context.scene.objects):
    if o != root and o.parent is None: o.parent=root
for o in bpy.context.scene.objects:
    if o.type=='MESH': o.select_set(False)
root['asset_purpose']='Exterior-only visual game prop, source-matched visible left side. Hidden surfaces are artist inferred.'
root['units']='Arbitrary game units. Long axis X, muzzle -X, up +Z, source-facing side -Y. Not real manufacturing dimensions.'
root['reference']='User supplied left-side raster. No functional weapon internals.'
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=False
scene.render.resolution_x=1400; scene.render.resolution_y=700; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.world.color=(.45,.45,.45)
scene.world.use_nodes=True; scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.65,.68,.73,1); scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.45
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
studio=bpy.data.collections.new('STUDIO_NotExported'); scene.collection.children.link(studio)
def studio_move(obj):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    studio.objects.link(obj)
def area(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA'); data.energy=power; data.shape='DISK'; data.size=size; data.color=color
    ob=bpy.data.objects.new(name,data); studio.objects.link(ob); ob.location=loc; ob.rotation_euler=(Vector((0,0,.3))-ob.location).to_track_quat('-Z','Y').to_euler(); return ob
area('Key_Softbox',(-2.3,-4.8,6.5),1300,6,(.9,.94,1))
area('Rim_Softbox',(1.5,2.2,5.5),1600,5,(1,.95,.86))
area('Fill_Softbox',(4,-3,1.6),620,5,(.8,.9,1))
area('Muzzle_Edge',(-5,1.1,2.5),650,3,(.92,.96,1))
camdata=bpy.data.cameras.new('Camera_Left'); cam=bpy.data.objects.new('Camera_Left',camdata); studio.objects.link(cam)
cam.location=(0,-20,.23); cam.rotation_euler=(Vector((0,0,.23))-cam.location).to_track_quat('-Z','Y').to_euler(); camdata.type='ORTHO'; camdata.ortho_scale=8.9; scene.camera=cam
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-1.47)); ground=bpy.context.object; ground.name='Studio_Floor'; studio_move(ground)
m=bpy.data.materials.new('Studio_Gray'); m.diffuse_color=(.45,.47,.50,1); m.use_nodes=True; m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.45,.47,.50,1); m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.83; ground.data.materials.append(m)
scene.render.fps=30; scene.frame_start=1; scene.frame_end=90
# Add source image as a disabled reference object, packed for inspection.
ref_path=ROOT+'/reference/source.png'
if os.path.exists(ref_path):
    ref=bpy.data.images.load(ref_path,check_existing=True); ref.pack()
    refs=bpy.data.collections.new('REFERENCE_SourceOnly'); scene.collection.children.link(refs)
    ob=bpy.data.objects.new('Original_Left_Reference',None); refs.objects.link(ob); ob.empty_display_type='IMAGE'; ob.data=ref; ob.empty_display_size=9.025; ob.location=(.025,.7,.2875); ob.rotation_euler=(math.pi/2,0,0); ob.hide_render=True; ob.hide_viewport=True
for ob in bpy.context.selected_objects: ob.select_set(False)
root.select_set(True); bpy.context.view_layer.objects.active=root
for scr in bpy.data.screens:
    for ar in scr.areas:
        if ar.type=='VIEW_3D':
            sp=ar.spaces.active; sp.clip_end=500; sp.overlay.show_floor=False; sp.overlay.show_axis_x=False; sp.overlay.show_axis_y=False; sp.shading.type='SOLID'; sp.shading.color_type='MATERIAL'; sp.shading.light='STUDIO'; sp.shading.studiolight_rotate_z=.5; sp.shading.show_cavity=True; sp.shading.cavity_type='BOTH'; sp.shading.curvature_ridge_factor=1.3; sp.shading.curvature_valley_factor=1.0
            sp.region_3d.view_distance=10.7; sp.region_3d.view_location=(0,0,.28); sp.region_3d.view_rotation=Quaternion((1,0,0), math.radians(75)); sp.region_3d.view_perspective='ORTHO'
# Studio hidden in viewport only: uncluttered inspection.
for ob in studio.objects: ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/checkpoints/rifle_working.blend')
# Left orthographic has no distracting perspective floor.
ground.hide_render=True
scene.render.filepath=ROOT+'/renders/left_iteration.png'
if os.environ.get('RIFLE_SKIP_RENDERS')!='1': bpy.ops.render.render(write_still=True)
print('ASSEMBLY_READY')
