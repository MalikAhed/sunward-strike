"""Reversible source-only native atmosphere, native-style-n5 proposal.
Only copied World, owned cloud meshes and owned lights are changed.
All cloud/light objects use 99_ collections and native_source_only=True.
The approved browser atmosphere remains the runtime owner; exclude these from GLB.
"""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
VERSION='native-style-n5'
CLOUD_MESH_FILE='atmosphere-parity-n5.json'
PLACEMENTS=[[-120,62,-160,29],[-38,73,-205,36],[62,48,-168,24],[153,79,-101,35],[184,67,20,32],[115,60,133,26],[26,87,203,37],[-78,54,161,26],[-165,78,80,34],[-194,60,-23,24],[-84,113,-235,32],[108,127,192,28]]

def geometry_fingerprint():
    bpy.context.view_layer.update();rows=[]
    for o in bpy.data.objects:
        if o.type!='MESH' or o.get('native_source_only'):continue
        rows.append({'name':o.name,'vertices':[list(v.co) for v in o.data.vertices],'faces':[list(p.vertices) for p in o.data.polygons],'matrix':[list(r) for r in o.matrix_world],'materials':[m.name if m else None for m in o.data.materials],'uv':[[list(q.uv) for q in u.data] for u in o.data.uv_layers]})
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def owned_collection(name):
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    c['native_source_only']=True;c['exclude_from_glb']=True;return c

def add_node(nt,kind,name):
    n=nt.nodes.new(kind);n.name=name;return n

def restore_native_style():
    s=bpy.context.scene;backup=s.get('native_style_backup')
    for o in list(bpy.data.objects):
        if o.get('native_source_only'):bpy.data.objects.remove(o,do_unlink=True)
        elif 'native_style_original_hide_render' in o:o.hide_render=o['native_style_original_hide_render'];del o['native_style_original_hide_render']
    for c in list(bpy.data.collections):
        if c.get('native_source_only'):bpy.data.collections.remove(c)
    if backup:
        b=json.loads(backup);s.world=bpy.data.worlds.get(b['world']) if b.get('world') else None;s.view_settings.view_transform=b['view_transform'];s.view_settings.look=b['look'];s.view_settings.exposure=b['exposure'];s.view_settings.gamma=b['gamma'];del s['native_style_backup']
    if 'native_style_revision'in s:del s['native_style_revision']

def camera_sky_world(s):
    w=s.world.copy() if s.world else bpy.data.worlds.new('NativeStyleWorld');w.name='NativeStyleWorld_n5';w.use_nodes=True;nt=w.node_tree;nt.nodes.clear()
    out=add_node(nt,'ShaderNodeOutputWorld','Native World Output');lp=add_node(nt,'ShaderNodeLightPath','Camera versus illumination rays');tex=add_node(nt,'ShaderNodeTexCoord','Sky direction');sep=add_node(nt,'ShaderNodeSeparateXYZ','Sky elevation');nt.links.new(tex.outputs['Normal'],sep.inputs[0])
    # Blender World normal is the incoming ray, opposite the browser direction.
    invert=add_node(nt,'ShaderNodeMath','World incoming ray to gradient UV');invert.operation='MULTIPLY_ADD';invert.inputs[1].default_value=-.5;invert.inputs[2].default_value=.5;nt.links.new(sep.outputs['Z'],invert.inputs[0]);uv=add_node(nt,'ShaderNodeCombineXYZ','Gradient UV');uv.inputs['X'].default_value=.5;nt.links.new(invert.outputs[0],uv.inputs['Y'])
    calibration=json.loads((HERE/'native-sky-radiance-n5.json').read_text());samples=calibration['samples_positive_elevation'];pixels=[]
    # Float scene-linear LUT retains HDR radiance; fixed manager AgX settings.
    for i in range(1024):
        elevation=-1+2*(i+.5)/1024
        if elevation>=0:
            pos=min(len(samples)-1,max(0,elevation*(len(samples)-1)));lo=int(pos);hi=min(len(samples)-1,lo+1);t=pos-lo;rgb=[samples[lo][j]*(1-t)+samples[hi][j]*t for j in range(3)]
        else:
            t=max(0,min(1,(elevation+.15)/.15));t=t*t*(3-2*t);rgb=[calibration['nadir_radiance'][j]*(1-t)+samples[0][j]*t for j in range(3)]
        pixels.extend(rgb+[1])
    lut=bpy.data.images.new('NativeSource_CalibratedSkyRadiance_n5',width=1,height=1024,alpha=True,float_buffer=True);lut.colorspace_settings.name='Non-Color';lut.pixels=pixels;lut.file_format='OPEN_EXR';lut.filepath_raw=str(HERE/'assets/native-sky-radiance-n5.exr');lut.save();lut.pack()
    lookup=add_node(nt,'ShaderNodeTexImage','Calibrated shared-color sky lookup');lookup.image=lut;lookup.interpolation='Linear';lookup.extension='EXTEND';nt.links.new(uv.outputs[0],lookup.inputs['Vector'])
    bg=add_node(nt,'ShaderNodeBackground','Camera azure sky');bg.inputs['Strength'].default_value=1;nt.links.new(lookup.outputs['Color'],bg.inputs['Color'])
    env=add_node(nt,'ShaderNodeBackground','Cool neutral ambient');env.inputs['Color'].default_value=(.64,.69,.76,1);env.inputs['Strength'].default_value=.6
    blend=add_node(nt,'ShaderNodeMixShader','Camera sky only');nt.links.new(lp.outputs['Is Camera Ray'],blend.inputs[0]);nt.links.new(env.outputs[0],blend.inputs[1]);nt.links.new(bg.outputs[0],blend.inputs[2]);nt.links.new(blend.outputs[0],out.inputs[0]);s.world=w
    return w

def atlas_material(filename):
    # Treat authored display-referred RGB as inverse base AgX input. This keeps
    # atlas tones close to the untone-mapped web layer while retaining the
    # manager's AgX/high-contrast presentation for lit map materials.
    # Original PNG bytes and alpha are retained; no generated art is repainted.
    m=bpy.data.materials.new('NativeSource_'+Path(filename).stem);m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
    out=add_node(nt,'ShaderNodeOutputMaterial','Output')
    tex=add_node(nt,'ShaderNodeTexImage','Original display-referred atlas')
    tex.image=bpy.data.images.load(str(HERE/'assets'/filename),check_existing=True)
    tex.image.colorspace_settings.name='AgX Base sRGB';tex.image.alpha_mode='STRAIGHT';tex.image.pack();tex.interpolation='Linear';tex.extension='EXTEND'
    em=add_node(nt,'ShaderNodeEmission','Display referred distant scenery');nt.links.new(tex.outputs['Color'],em.inputs['Color']);em.inputs['Strength'].default_value=2**(-bpy.context.scene.view_settings.exposure)
    transparent=add_node(nt,'ShaderNodeBsdfTransparent','Transparent surrounding sky');mix=add_node(nt,'ShaderNodeMixShader','Original alpha');nt.links.new(tex.outputs['Alpha'],mix.inputs[0]);nt.links.new(transparent.outputs[0],mix.inputs[1]);nt.links.new(em.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs[0])
    if hasattr(m,'surface_render_method'):m.surface_render_method='DITHERED'
    m.use_transparency_overlap=False;m['native_source_only']=True;m['original_atlas']=filename;m['alpha_preserved']=True
    return m

def create_clouds():
    raw=json.loads((HERE/CLOUD_MESH_FILE).read_text());c=owned_collection('99_NATIVE_STYLE_SKY');root=bpy.data.objects.new('NativeSource_DistantSkyRoot',None);c.objects.link(root);root['native_source_only']=True;root['exclude_from_glb']=True
    if bpy.context.scene.camera:
        follow=root.constraints.new('COPY_LOCATION');follow.name='Camera translation only, infinite distance';follow.target=bpy.context.scene.camera
    root['camera_centered']=True;materials={}
    for item in raw['cards']:
        p=item['vertices'];idx=item['indices'];uv=item['uv'];verts=[(p[i],-p[i+2],p[i+1]) for i in range(0,len(p),3)];faces=[tuple(idx[i:i+3]) for i in range(0,len(idx),3)]
        me=bpy.data.meshes.new('NativeSource_'+item['name']);me.from_pydata(verts,[],faces);me.update();layer=me.uv_layers.new(name='AtlasUV')
        for poly in me.polygons:
            for loop_i in poly.loop_indices:
                vertex_i=me.loops[loop_i].vertex_index;layer.data[loop_i].uv=(uv[2*vertex_i],uv[2*vertex_i+1])
        filename=item['texture']
        if filename not in materials:materials[filename]=atlas_material(filename)
        me.materials.append(materials[filename]);o=bpy.data.objects.new(me.name,me);c.objects.link(o);o.parent=root;o['native_source_only']=True;o['exclude_from_glb']=True;o['atmosphere_profile']=item['metadata']['profile'];o.visible_shadow=False
        # Shared parity geometry already contains tiny deterministic radial
        # offsets, preventing coplanar Eevee alpha-depth interference.
    return {'cards':len(raw['cards']),'cloud_banks':len(raw['config']['clouds']),'mountain_ranges':len(raw['config']['mountains']),'triangles':sum(len(item['indices'])//3 for item in raw['cards']),'parity_json_sha256':hashlib.sha256((HERE/CLOUD_MESH_FILE).read_bytes()).hexdigest(),'camera_centered':True,'camera_follow_axes':'translation xyz only','radius_m':raw['config']['radius'],'native_clip_end_m':bpy.context.scene.camera.data.clip_end,'source':'Exact n5 web spherical card vertices/indices/UV/placements; Three(x,y,z) -> Blender(x,-z,y); original alpha preserved','texture_color_space_native':'AgX Base sRGB inverse base display transform, exposure compensated; high-contrast look remains','sky_color_calibration':'native-sky-radiance-n5.json, measured positive-radiance fit to shared browser gradient; no lit-map view transform change'}

def retarget_camera(camera=None):
    """Explicit safe hook after scene.camera changes; no handlers/auto-exec."""
    camera=camera or bpy.context.scene.camera
    if camera is None:raise ValueError('A render camera is required for distant sky')
    root=bpy.data.objects.get('NativeSource_DistantSkyRoot')
    if root is None:raise ValueError('Apply native atmosphere before retargeting')
    follow=next((c for c in root.constraints if c.type=='COPY_LOCATION'),None)
    if follow is None:follow=root.constraints.new('COPY_LOCATION')
    follow.target=camera;follow.use_x=follow.use_y=follow.use_z=True
    camera.data.clip_end=max(1000,camera.data.clip_end)
    return {'camera':camera.name,'root':root.name,'clip_end':camera.data.clip_end}

def create_lights():
    c=owned_collection('99_NATIVE_STYLE_LIGHTING');sun=bpy.data.lights.new('NativeSource_WarmSun_n3','SUN');sun.energy=4.0;sun.color=(1,.86,.67);sun.angle=math.radians(3.2);o=bpy.data.objects.new(sun.name,sun);c.objects.link(o);o.location=(-42,-30,68);o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler();o['native_source_only']=True;o['exclude_from_glb']=True
    fill=bpy.data.lights.new('NativeSource_WarmCameraFill_n3','AREA');fill.energy=35000;fill.color=(1,.94,.79);fill.shape='DISK';fill.size=85;fo=bpy.data.objects.new(fill.name,fill);c.objects.link(fo);fo.location=(38,-5,45);fo.rotation_euler=(-fo.location).to_track_quat('-Z','Y').to_euler();fo['native_source_only']=True;fo['exclude_from_glb']=True
    bounce=bpy.data.lights.new('NativeSource_CoolSkyBounce_n3','SUN');bounce.energy=.45;bounce.color=(.62,.78,1);bounce.use_shadow=False;bo=bpy.data.objects.new(bounce.name,bounce);c.objects.link(bo);bo.location=(-10,25,60);bo.rotation_euler=(-bo.location).to_track_quat('-Z','Y').to_euler();bo['native_source_only']=True;bo['exclude_from_glb']=True
    return {'sun_energy':sun.energy,'sun_rgb_linear':list(sun.color),'sun_angle_degrees':3.2,'sun_direction_source_blender':list(o.location),'camera_fill_energy_W':fill.energy,'camera_fill_size_m':fill.size,'camera_fill_rgb_linear':list(fill.color),'camera_fill_position_blender':list(fo.location),'sky_bounce_energy':bounce.energy,'sky_bounce_rgb_linear':list(bounce.color)}

def configure_presentation(s):
    s.render.engine='BLENDER_EEVEE_NEXT'
    if hasattr(s,'eevee'):
        if hasattr(s.eevee,'taa_render_samples'):s.eevee.taa_render_samples=32
        if hasattr(s.eevee,'taa_samples'):s.eevee.taa_samples=16
        if hasattr(s.eevee,'use_raytracing'):s.eevee.use_raytracing=False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                sp=area.spaces.active;sp.shading.type='RENDERED'
                if hasattr(sp.shading,'use_scene_lights_render'):sp.shading.use_scene_lights_render=True
                if hasattr(sp.shading,'use_scene_world_render'):sp.shading.use_scene_world_render=True
                sp.overlay.show_overlays=False;sp.region_3d.view_perspective='CAMERA'
    return {'engine':'BLENDER_EEVEE_NEXT','render_samples':32,'viewport_samples':16,'raytracing':False,'saved_viewport':'Rendered camera with scene World/lights'}

def apply_native_style():
    s=bpy.context.scene
    if s.get('native_style_backup'):restore_native_style()
    if s.camera:s.camera.data.clip_end=max(1000,s.camera.data.clip_end)
    # An older native checkpoint did not retain its zero-user original World.
    # Recover a neutral source World and retain it for reversible future passes.
    recovered_world=False
    if s.world is None:
        s.world=bpy.data.worlds.new('NativeSource_RecoveredBaseWorld');s.world.use_nodes=True
        bg=s.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.64,.69,.76,1);bg.inputs['Strength'].default_value=.6;recovered_world=True
    s.world.use_fake_user=True
    before=geometry_fingerprint();s['native_style_backup']=json.dumps({'world':s.world.name,'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma})
    hidden=[]
    # Replace outdoor lighting only; interior dressing/lighting stays independently owned.
    for o in bpy.data.objects:
        if o.type=='LIGHT' and(o.data.type=='SUN' or o.name=='Sky_fill'):
            o['native_style_original_hide_render']=o.hide_render;o.hide_render=True;hidden.append(o.name)
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.10;s.view_settings.gamma=1
    world=camera_sky_world(s);clouds=create_clouds();lights=create_lights();s['native_style_revision']=VERSION
    presentation=configure_presentation(s)
    after=geometry_fingerprint()
    if before!=after:raise AssertionError('Protected map geometry/material assignments changed')
    return {'version':VERSION,'geometry_sha256_before':before,'geometry_sha256_after':after,'geometry_unchanged':before==after,'world_copy':world.name,'recovered_missing_prior_world':recovered_world,'hidden_outdoor_lights':hidden,'clouds':clouds,'lights':lights,'color_management':{'view':'AgX','look':'Medium High Contrast','exposure':.10},'source_only_collections':['99_NATIVE_STYLE_SKY','99_NATIVE_STYLE_LIGHTING'],'presentation':presentation,'proposed_runtime_cloud_geometry_revision':'distant-painted-banks-n5','web_paint_code_unchanged':True,'web_sky_cloud_palette_proposal':'original cream cloud and peach/lavender ridge atlas; rich azure sky','live_repo_n2_untouched':True,'uncertainties':['Native AgX high-contrast look differs slightly from untone-mapped browser sprites; geometry/UV placement exact','Whole-scene cream/teal/coral/grass balance requires actual pixel review']}
