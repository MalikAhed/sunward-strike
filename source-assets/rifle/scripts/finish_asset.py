import bpy, math, os, json
from mathutils import Vector, Quaternion, Matrix
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=ROOT+'/checkpoints/rifle_working.blend')
scene=bpy.context.scene
scene.name='GAME_READY'
root=bpy.data.objects['Rifle_ROOT']
# Match source's quiet matte charcoal finish across the whole object.
bpy.data.lights['Fill_Softbox'].energy=170
bpy.data.objects['Fill_Softbox'].location=(0,-4,2)
bpy.data.lights['Key_Softbox'].energy=1050
bpy.data.objects['Key_Softbox'].location=(-1,-4.8,6)
bpy.data.lights['Rim_Softbox'].energy=950
scene.cycles.samples=64
scene.render.resolution_x=1600; scene.render.resolution_y=800
# Preserve editable modular source independently, then bake non-destructive bevels for robust GLB.
movements=['Magazine_CTRL','Trigger_CTRL','ChargingHandle_CTRL','BoltVisual_CTRL']
controls={n:bpy.data.objects.get(n) for n in movements}
def find_control(obj):
    p=obj.parent
    while p:
        if p.name in movements: return p.name
        p=p.parent
    return 'Body'
meshes=[o for o in scene.objects if o.type=='MESH' and o.name!='Studio_Floor']
groups={n:[] for n in ['Body']+movements}
for ob in meshes: groups[find_control(ob)].append(ob)
dg=bpy.context.evaluated_depsgraph_get()
for ob in meshes:
    baked=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
    ob.modifiers.clear(); ob.data=baked
# Triangulate explicitly and drop bevel-collapse faces while preserving corner shading.
def clean_mesh(ob):
    src=ob.data; src.calc_loop_triangles(); keep=[t for t in src.loop_triangles if t.area>=1e-10]
    coords=[tuple(v.co) for v in src.vertices]
    faces=[tuple(t.vertices) for t in keep]
    normals=[tuple(src.corner_normals[i].vector) for t in keep for i in t.loops]
    uv_data={uv.name:[tuple(uv.data[i].uv) for t in keep for i in t.loops] for uv in src.uv_layers}
    mats=list(src.materials); indices=[t.material_index for t in keep]; smooth=[src.polygons[t.polygon_index].use_smooth for t in keep]
    cleaned=bpy.data.meshes.new(ob.name+'_Clean'); cleaned.from_pydata(coords,[],faces); cleaned.update()
    for m in mats: cleaned.materials.append(m)
    for i,p in enumerate(cleaned.polygons): p.material_index=indices[i]; p.use_smooth=smooth[i]
    for name,uvs in uv_data.items():
        layer=cleaned.uv_layers.new(name=name)
        for i,uv in enumerate(uvs):layer.data[i].uv=uv
    if len(normals)==len(cleaned.loops):cleaned.normals_split_custom_set(normals)
    ob.data=cleaned
for ob in meshes: clean_mesh(ob)
# A reusable UV layout exists even though final materials use no bitmap textures.
for ob in meshes:
    if len(ob.data.uv_layers)==0:
        bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.012); bpy.ops.object.mode_set(mode='OBJECT')
for key,items in groups.items():
    if not items: continue
    bpy.ops.object.select_all(action='DESELECT')
    for ob in items:
        ob.hide_set(False); world=ob.matrix_world.copy(); ob.parent=None; ob.matrix_world=world; ob.select_set(True)
    bpy.context.view_layer.objects.active=items[0]; bpy.ops.object.join(); joined=bpy.context.object; joined.name='Rifle_Body' if key=='Body' else key.replace('_CTRL','_Mesh'); clean_mesh(joined); joined.data.name=joined.name+'_Geometry'
    par=root if key=='Body' else controls[key]; world=joined.matrix_world.copy(); joined.parent=par; joined.matrix_world=world
# Remove redundant static attachment empties, while preserving needed root and motion controls.
for ob in list(scene.objects):
    if ob.type=='EMPTY' and ob.name not in movements+['Rifle_ROOT','Original_Left_Reference']:
        bpy.data.objects.remove(ob,do_unlink=True)
# Fixed rest-pose pivots sit outside animated channels. This keeps GLB rest pose
# correct even in viewers which never activate an animation.
for name,ctrl in controls.items():
    if ctrl is None:continue
    world=ctrl.matrix_world.copy()
    anchor=bpy.data.objects.new(name.replace('_CTRL','_PIVOT'),None);scene.collection.objects.link(anchor);anchor.parent=root;anchor.matrix_world=world
    ctrl.parent=anchor;ctrl.matrix_parent_inverse=Matrix.Identity(4);ctrl.matrix_world=world
    bpy.context.view_layer.update()
# Establish object-transform game clips. These visual timings are not a weapon simulation.
for ob in [root]+list(controls.values()):
    if ob: ob.animation_data_clear()
base={ob.name:(ob.location.copy(),ob.rotation_euler.copy()) for ob in [root]+list(controls.values()) if ob}
def make_track(ob,clip,keyposes,end):
    if ob is None: return
    ob.animation_data_create(); action=bpy.data.actions.new(clip+'__'+ob.name); ob.animation_data.action=action
    loc,rot=base[ob.name]
    for frame,dl,dr in keyposes:
        ob.location=loc+Vector(dl); ob.rotation_euler=tuple(rot[i]+dr[i] for i in range(3))
        ob.keyframe_insert(data_path='location',frame=frame,group=ob.name); ob.keyframe_insert(data_path='rotation_euler',frame=frame,group=ob.name)
    for fc in action.fcurves:
        for k in fc.keyframe_points: k.interpolation='LINEAR'
    action.use_fake_user=True; tr=ob.animation_data.nla_tracks.new(); tr.name=clip; strip=tr.strips.new(clip,1,action); strip.action_frame_start=1; strip.action_frame_end=end; strip.blend_type='REPLACE'; strip.extrapolation='NOTHING'
    ob.animation_data.action=None; ob.location=loc; ob.rotation_euler=rot; return tr
z=(0,0,0)
make_track(root,'Fire',[(1,z,z),(3,(.16,0,.05),(0,.055,0)),(6,(.05,0,.015),(0,.02,0)),(12,z,z)],12)
make_track(controls['Trigger_CTRL'],'Fire',[(1,z,z),(3,z,(0,.22,0)),(7,z,(0,.22,0)),(12,z,z)],12)
make_track(controls['BoltVisual_CTRL'],'Fire',[(1,z,z),(3,(.28,0,0),z),(6,z,z),(12,z,z)],12)
make_track(controls['Magazine_CTRL'],'Reload',[(1,z,z),(8,z,z),(20,(.08,0,-1.2),(0,.12,0)),(36,(.55,0,-1.6),(0,.32,0)),(49,(.1,0,-1.1),(0,.08,0)),(61,z,z),(90,z,z)],90)
make_track(controls['ChargingHandle_CTRL'],'Reload',[(1,z,z),(65,z,z),(73,(.26,0,0),z),(80,(.26,0,0),z),(86,z,z),(90,z,z)],90)
make_track(controls['BoltVisual_CTRL'],'Reload',[(1,z,z),(65,z,z),(73,(.26,0,0),z),(80,(.26,0,0),z),(86,z,z),(90,z,z)],90)
make_track(controls['ChargingHandle_CTRL'],'Charge',[(1,z,z),(8,(.26,0,0),z),(14,(.26,0,0),z),(20,z,z),(24,z,z)],24)
make_track(controls['BoltVisual_CTRL'],'Charge',[(1,z,z),(8,(.26,0,0),z),(14,(.26,0,0),z),(20,z,z),(24,z,z)],24)
# Subtle non-combat inspect presentation clip.
make_track(root,'Inspect',[(1,z,z),(18,(0,0,.06),(.06,-.10,.08)),(40,(0,0,.05),(-.06,.07,-.08)),(60,z,z)],60)
# Action clips share NLA track names across all rigid parts for merged exports.
scene.frame_set(1)
for ob in [root]+list(controls.values()):
    if ob and ob.animation_data:
        for tr in ob.animation_data.nla_tracks: tr.mute=False
export_objs=[root]+list(root.children_recursive)
bpy.ops.object.select_all(action='DESELECT')
for ob in export_objs: ob.hide_set(False); ob.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/compact_carbine.glb',export_format='GLB',use_selection=True,export_apply=False,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_frame_step=1,export_force_sampling=True,export_extras=True,export_yup=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
# Timeline defaults to reload for immediate visible movement; all clips retained and documented.
for ob in [root]+list(controls.values()):
    if ob and ob.animation_data:
        for tr in ob.animation_data.nla_tracks: tr.mute=(tr.name!='Reload')
scene.frame_set(1); scene.frame_start=1; scene.frame_end=90
for ob in export_objs: ob.select_set(False)
root.select_set(True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            sp=area.spaces.active; sp.overlay.show_extras=False; sp.overlay.show_relationship_lines=False
            sp.region_3d.view_distance=8.5; sp.region_3d.view_location=(0,0,.3); sp.region_3d.view_rotation=Quaternion((1,0,0),math.radians(77)); sp.region_3d.view_perspective='ORTHO'
# A named first-person inspection camera is part of the Blender studio only.
if not bpy.data.objects.get('Camera_ADS'):
    adsdata=bpy.data.cameras.new('Camera_ADS');adscam=bpy.data.objects.new('Camera_ADS',adsdata);bpy.data.collections['STUDIO_NotExported'].objects.link(adscam)
    adsdata.type='PERSP';adsdata.lens=32;adsdata.sensor_width=36;adsdata.clip_start=.02
    adscam.location=(1.85,0,1.48);adscam.rotation_euler=Vector((-1,0,0)).to_track_quat('-Z','Y').to_euler();adscam.hide_set(True)
# Human-readable in-file guide.
text=bpy.data.texts.get('START_HERE') or bpy.data.texts.new('START_HERE')
text.write('COMPACT CARBINE / GAME-ART ASSET\n\nExterior only. Source-facing left side is image-matched; unseen sides artist-inferred.\nNo real dimensions or functional internal mechanisms.\n\nReady GLB: compact_carbine.glb\nBlender axes: muzzle -X, up +Z, reference-facing -Y. Arbitrary game units.\nGLB has standard glTF +Y up. Position attachment by Rifle_ROOT.\n\nCLIPS (30fps): Fire 1-12; Reload 1-90; Charge 1-24; Inspect 1-60.\nRigid object animations. NLA track names merge matching part motions.\nTo preview: unmute only the same named track on all controls in NLA Editor.\nSaved timeline previews Reload by default. Press Space to play.\n\nMoving pivots: magazine, trigger, charging handle, shallow visual bolt.\nNo firing/projectile/audio/input game code is included.\nMaterials: flat PBR charcoal/anodized black, no texture dependency.\nSource image packed under hidden REFERENCE_SourceOnly collection.\nModular editable pre-optimization mesh is in checkpoints/rifle_working.blend.\n')
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/exports/compact_carbine.blend')
# Stills, consistent neutral studio lighting.
for ob in [root]+list(controls.values()):
    if ob and ob.animation_data:
        for tr in ob.animation_data.nla_tracks: tr.mute=True
    if ob: ob.location=base[ob.name][0]; ob.rotation_euler=base[ob.name][1]
scene.frame_set(1); cam=scene.camera; ground=bpy.data.objects['Studio_Floor']
def render(name,loc,target,ortho,ground_on):
    cam.location=loc; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.ortho_scale=ortho; ground.hide_render=not ground_on; scene.render.filepath=ROOT+'/renders/'+name+'.png'; bpy.ops.render.render(write_still=True)
render('left_final',(0,-20,.23),(0,0,.23),8.9,False)
render('hero',(-7,-13,6.0),(0,0,.22),9.4,True)
render('right_inferred',(0,20,.23),(0,0,.23),8.9,False)
render('top',(0,-.01,20),(0,0,.2),8.9,False)
print('FINISH_READY')
