"""Reversible source-only native atmosphere, native-style-n2.
Only copied World, owned cloud meshes and owned lights are changed.
All cloud/light objects use 99_ collections and native_source_only=True.
The approved browser atmosphere remains the runtime owner; exclude these from GLB.
"""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
VERSION='native-style-n2'
CLOUD_MESH_FILE='cloud-mesh-web-parity-n2.json'
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
    w=s.world.copy() if s.world else bpy.data.worlds.new('NativeStyleWorld');w.name='NativeStyleWorld_n2';w.use_nodes=True;nt=w.node_tree;nt.nodes.clear()
    out=add_node(nt,'ShaderNodeOutputWorld','Native World Output');lp=add_node(nt,'ShaderNodeLightPath','Camera versus illumination rays');tex=add_node(nt,'ShaderNodeTexCoord','Sky direction');sep=add_node(nt,'ShaderNodeSeparateXYZ','Sky elevation');rng=add_node(nt,'ShaderNodeMapRange','Sky gradient range');rng.interpolation_type='SMOOTHSTEP';rng.clamp=True;rng.inputs['From Min'].default_value=-.08;rng.inputs['From Max'].default_value=.72
    nt.links.new(tex.outputs['Normal'],sep.inputs[0]);nt.links.new(sep.outputs['Z'],rng.inputs['Value'])
    mix=add_node(nt,'ShaderNodeMix','Blue sky color gradient');mix.data_type='RGBA';mix.inputs[6].default_value=(.06,.29,1.05,1);mix.inputs[7].default_value=(.012,.12,.74,1);nt.links.new(rng.outputs[0],mix.inputs[0])
    bg=add_node(nt,'ShaderNodeBackground','Camera blue sky');bg.inputs['Strength'].default_value=1.0;nt.links.new(mix.outputs[2],bg.inputs['Color'])
    env=add_node(nt,'ShaderNodeBackground','Cool neutral ambient');env.inputs['Color'].default_value=(.64,.69,.76,1);env.inputs['Strength'].default_value=.6
    blend=add_node(nt,'ShaderNodeMixShader','Camera sky only');nt.links.new(lp.outputs['Is Camera Ray'],blend.inputs[0]);nt.links.new(env.outputs[0],blend.inputs[1]);nt.links.new(bg.outputs[0],blend.inputs[2]);nt.links.new(blend.outputs[0],out.inputs[0]);s.world=w
    return w

def cloud_material():
    m=bpy.data.materials.new('NativeSource_CreamCloud_n2');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear();out=add_node(nt,'ShaderNodeOutputMaterial','Output');geom=add_node(nt,'ShaderNodeNewGeometry','World normal');sep=add_node(nt,'ShaderNodeSeparateXYZ','Daylight normal');nt.links.new(geom.outputs['Normal'],sep.inputs[0])
    daylight=add_node(nt,'ShaderNodeMapRange','Daylight hemisphere');daylight.clamp=True;daylight.interpolation_type='SMOOTHSTEP';daylight.inputs['From Min'].default_value=-.55;daylight.inputs['From Max'].default_value=.35;nt.links.new(sep.outputs['Z'],daylight.inputs[0])
    dot=add_node(nt,'ShaderNodeVectorMath','Sun-facing normal');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=Vector((-.6,-.25,.8)).normalized();nt.links.new(geom.outputs['Normal'],dot.inputs[0])
    sunshine=add_node(nt,'ShaderNodeMapRange','Sunlight lobe');sunshine.clamp=True;sunshine.interpolation_type='SMOOTHSTEP';sunshine.inputs['From Min'].default_value=-.2;sunshine.inputs['From Max'].default_value=.9;nt.links.new(dot.outputs['Value'],sunshine.inputs[0])
    a=add_node(nt,'ShaderNodeMath','80percent daylight');a.operation='MULTIPLY';a.inputs[1].default_value=.8;nt.links.new(daylight.outputs[0],a.inputs[0]);b=add_node(nt,'ShaderNodeMath','20percent sunlight');b.operation='MULTIPLY';b.inputs[1].default_value=.2;nt.links.new(sunshine.outputs[0],b.inputs[0]);summ=add_node(nt,'ShaderNodeMath','Cloud tone weight');summ.operation='ADD';nt.links.new(a.outputs[0],summ.inputs[0]);nt.links.new(b.outputs[0],summ.inputs[1])
    colors=add_node(nt,'ShaderNodeMix','Cream tops cool undersides');colors.data_type='RGBA';colors.inputs[6].default_value=(1.10,1.35,1.85,1);colors.inputs[7].default_value=(3.20,3.10,2.85,1);nt.links.new(summ.outputs[0],colors.inputs[0]);em=add_node(nt,'ShaderNodeEmission','Source-only cloud shading');nt.links.new(colors.outputs[2],em.inputs['Color']);em.inputs['Strength'].default_value=1;nt.links.new(em.outputs[0],out.inputs[0]);m['native_source_only']=True;return m

def create_clouds():
    raw=json.loads((HERE/CLOUD_MESH_FILE).read_text());p=raw['three_positions'];n=raw['three_normals'];verts=[(p[i],-p[i+2],p[i+1]) for i in range(0,len(p),3)];norm=[tuple(Vector((n[i],-n[i+2],n[i+1])).normalized()) for i in range(0,len(n),3)];faces=[(i,i+1,i+2) for i in range(0,len(verts),3)]
    me=bpy.data.meshes.new('NativeSource_ApprovedWebCloudUnion');me.from_pydata(verts,[],faces);me.update();me.materials.append(cloud_material())
    for poly in me.polygons:poly.use_smooth=True
    if hasattr(me,'normals_split_custom_set_from_vertices'):me.normals_split_custom_set_from_vertices(norm)
    c=owned_collection('99_NATIVE_STYLE_SKY');root=bpy.data.objects.new('NativeSource_CloudRing',None);c.objects.link(root);root['native_source_only']=True;root['exclude_from_glb']=True
    for i,(x,zheight,yweb,size) in enumerate(PLACEMENTS):
        o=bpy.data.objects.new('NativeSource_Cloud_%02d'%i,me);c.objects.link(o);o.parent=root;o.location=(x,-yweb,zheight);o.rotation_euler.z=i*.93;o.scale=(size,size,size);o['native_source_only']=True;o['exclude_from_glb']=True;o.visible_shadow=False
    return {'instances':len(PLACEMENTS),'shared_mesh_triangles':raw['triangle_count'],'shape_version':raw.get('shape_version'),'lobes':raw.get('lobe_count'),'parity_json_sha256':hashlib.sha256((HERE/CLOUD_MESH_FILE).read_bytes()).hexdigest(),'source':'Exact current runtime joined cumulus and ring placements; coordinate conversion Three(x,y,z) to Blender(x,-z,y)'}

def create_lights():
    c=owned_collection('99_NATIVE_STYLE_LIGHTING');sun=bpy.data.lights.new('NativeSource_WarmSun_n2','SUN');sun.energy=4.0;sun.color=(1,.88,.72);sun.angle=math.radians(3.2);o=bpy.data.objects.new(sun.name,sun);c.objects.link(o);o.location=(-42,-30,68);o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler();o['native_source_only']=True;o['exclude_from_glb']=True
    fill=bpy.data.lights.new('NativeSource_CoolFill_n2','AREA');fill.energy=42000;fill.color=(.83,.91,1.0);fill.shape='DISK';fill.size=85;fo=bpy.data.objects.new(fill.name,fill);c.objects.link(fo);fo.location=(38,-5,45);fo.rotation_euler=(-fo.location).to_track_quat('-Z','Y').to_euler();fo['native_source_only']=True;fo['exclude_from_glb']=True
    return {'sun_energy':sun.energy,'sun_rgb_linear':list(sun.color),'sun_angle_degrees':3.2,'sun_direction_source_blender':list(o.location),'cool_fill_energy_W':fill.energy,'cool_fill_size_m':fill.size,'cool_fill_rgb_linear':list(fill.color),'cool_fill_position_blender':list(fo.location)}

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
    world=camera_sky_world(s);clouds=create_clouds();lights=create_lights();s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.10;s.view_settings.gamma=1;s['native_style_revision']=VERSION
    presentation=configure_presentation(s)
    after=geometry_fingerprint()
    if before!=after:raise AssertionError('Protected map geometry/material assignments changed')
    return {'version':VERSION,'geometry_sha256_before':before,'geometry_sha256_after':after,'geometry_unchanged':before==after,'world_copy':world.name,'recovered_missing_prior_world':recovered_world,'hidden_outdoor_lights':hidden,'clouds':clouds,'lights':lights,'color_management':{'view':'AgX','look':'Medium High Contrast','exposure':.10},'source_only_collections':['99_NATIVE_STYLE_SKY','99_NATIVE_STYLE_LIGHTING'],'presentation':presentation,'runtime_cloud_geometry_revision':'fluffy-cumulus-n2','web_paint_sky_and_material_code_unchanged':True,'uncertainties':['Source-only lighting/sky approximation; exact collage art identity not assumed','Whole-scene cream/teal/coral/grass balance requires actual pixel review']}
