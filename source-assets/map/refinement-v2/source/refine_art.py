import bpy, math, random, os, sys, json
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT=os.path.dirname(ROOT)
random.seed(20261003)
scene=bpy.context.scene
M=bpy.data.materials
# Procedural maps are authored from Blender nodes and baked to portable UV textures.
# They contain no lighting or reference-image pixels.
def material_from_maps(name,base,kind,im,nm):
    im.pack();nm.pack()
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*base,1);nd=mat.node_tree.nodes;ln=mat.node_tree.links;pr=nd.get('Principled BSDF');pr.inputs['Roughness'].default_value=.88
    tx=nd.new('ShaderNodeTexImage');tx.image=im;tx.extension='REPEAT';ln.new(tx.outputs['Color'],pr.inputs['Base Color'])
    tx2=nd.new('ShaderNodeTexImage');tx2.image=nm;tx2.extension='REPEAT';nn=nd.new('ShaderNodeNormalMap');nn.inputs['Strength'].default_value=.32 if kind!='roof' else .65;ln.new(tx2.outputs['Color'],nn.inputs['Color']);ln.new(nn.outputs[0],pr.inputs['Normal'])
    return mat

def bake_surface(name,base,kind='plaster',resolution=256):
    colorpath=ROOT+'/textures/'+name+'_BaseColor.png'
    normalname=name if kind in ('wood','roof') else 'V2_Warm_Plaster'
    normalpath=ROOT+'/textures/'+normalname+'_Normal.png'
    if os.path.exists(colorpath) and os.path.exists(normalpath):
        im=bpy.data.images.load(colorpath,check_existing=True)
        if im.size[0]!=256:im.scale(256,256);im.save()
        nm=bpy.data.images.load(normalpath,check_existing=True);nm.colorspace_settings.name='Non-Color'
        if nm.size[0]!=128:nm.scale(128,128);nm.save()
        return material_from_maps(name,base,kind,im,nm)
    original=bpy.context.window.scene
    bs=bpy.data.scenes.new('TextureBake_'+name);bpy.context.window.scene=bs
    bs.render.engine='CYCLES';bs.cycles.samples=1;bs.cycles.use_denoising=False
    bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object
    material=bpy.data.materials.new('_Bake_'+name);material.use_nodes=True;plane.data.materials.append(material)
    nt=material.node_tree;nt.nodes.clear();n=nt.nodes;l=nt.links
    out=n.new('ShaderNodeOutputMaterial');emit=n.new('ShaderNodeEmission');l.new(emit.outputs[0],out.inputs['Surface'])
    coord=n.new('ShaderNodeTexCoord')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5;noise.inputs['Detail'].default_value=4;noise.inputs['Roughness'].default_value=.72;l.new(coord.outputs['UV'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(*[v*.76 for v in base],1);ramp.color_ramp.elements[1].position=.79;ramp.color_ramp.elements[1].color=(*[min(1,v*1.13) for v in base],1);l.new(noise.outputs['Fac'],ramp.inputs[0])
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=145;fine.inputs['Detail'].default_value=2;fine.inputs['Roughness'].default_value=.75;l.new(coord.outputs['UV'],fine.inputs['Vector'])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.13;l.new(ramp.outputs[0],mix.inputs[1]);l.new(fine.outputs['Color'],mix.inputs[2])
    height=fine.outputs['Fac']
    if kind=='roof':
        brick=n.new('ShaderNodeTexBrick');l.new(coord.outputs['UV'],brick.inputs['Vector']);brick.inputs['Scale'].default_value=5;brick.inputs['Mortar Size'].default_value=.013;brick.inputs['Mortar Smooth'].default_value=.004;brick.inputs['Brick Width'].default_value=.65;brick.inputs['Row Height'].default_value=.28
        brick.inputs['Color1'].default_value=(*[v*.85 for v in base],1);brick.inputs['Color2'].default_value=(*[v*1.13 for v in base],1);brick.inputs['Mortar'].default_value=(*[v*.50 for v in base],1)
        l.new(brick.outputs['Color'],mix.inputs[1]);height=brick.outputs['Fac']
    if kind=='wood':
        wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='X';wave.inputs['Scale'].default_value=12;wave.inputs['Distortion'].default_value=7;wave.inputs['Detail'].default_value=4;l.new(coord.outputs['UV'],wave.inputs['Vector']);l.new(wave.outputs['Color'],mix.inputs[2]);mix.inputs[0].default_value=.20;height=wave.outputs['Color']
    l.new(mix.outputs[0],emit.inputs['Color'])
    target=n.new('ShaderNodeTexImage');im=bpy.data.images.new(name+'_BaseColor',width=resolution,height=resolution,alpha=False);target.image=im;nt.nodes.active=target
    bpy.ops.object.bake(type='EMIT',margin=4)
    im.filepath_raw=ROOT+'/textures/'+name+'_BaseColor.png';im.file_format='PNG';im.save();im.pack()
    # Tangent normal map derived from the same procedural height, always exported with Normal Map node.
    normal=n.new('ShaderNodeTexImage');nm=bpy.data.images.new(name+'_Normal',width=resolution,height=resolution,alpha=False);nm.colorspace_settings.name='Non-Color';normal.image=nm
    p=n.new('ShaderNodeBsdfPrincipled');bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.26 if kind!='roof' else .32;bump.inputs['Distance'].default_value=.035 if kind!='roof' else .065;l.new(height,bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal']);l.new(p.outputs[0],out.inputs['Surface']);nt.nodes.active=normal
    bpy.ops.object.bake(type='NORMAL',margin=4)
    nm.filepath_raw=ROOT+'/textures/'+name+'_Normal.png';nm.file_format='PNG';nm.save();nm.pack()
    bpy.context.window.scene=original;bpy.data.objects.remove(plane,do_unlink=True);bpy.data.scenes.remove(bs);bpy.data.materials.remove(material)
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*base,1);nd=mat.node_tree.nodes;ln=mat.node_tree.links;pr=nd.get('Principled BSDF');pr.inputs['Roughness'].default_value=.88
    tx=nd.new('ShaderNodeTexImage');tx.image=im;tx.extension='REPEAT';ln.new(tx.outputs['Color'],pr.inputs['Base Color'])
    tx2=nd.new('ShaderNodeTexImage');tx2.image=nm;tx2.extension='REPEAT';normalnode=nd.new('ShaderNodeNormalMap');normalnode.inputs['Strength'].default_value=.42 if kind!='roof' else .65;ln.new(tx2.outputs['Color'],normalnode.inputs['Color']);ln.new(normalnode.outputs[0],pr.inputs['Normal'])
    return mat
surfaces={
'plaster_cream':bake_surface('V2_Warm_Plaster',(.65,.58,.45)),
'plaster_mint':bake_surface('V2_Sage_Plaster',(.24,.43,.34)),
'plaster_saffron':bake_surface('V2_Saffron_Plaster',(.70,.48,.23)),
'roof':bake_surface('V2_Weathered_Roof',(.075,.105,.105),'roof'),
'wood':bake_surface('V2_Aged_Timber',(.135,.115,.088),'wood',256),
'grass':bake_surface('V2_Ground_Moss',(.18,.25,.11),'plaster',256),
'concrete':bake_surface('V2_Limestone',(.48,.46,.38),'plaster',256),
'road':bake_surface('V2_Road',(.115,.14,.145),'plaster',256),
}
# World-space box UV projection keeps texture scale consistent across modular walls.
def assign(o,mat,scale=2.6):
    if o.type!='MESH':return
    if o.data.users>1:o.data=o.data.copy()
    o.data.materials.clear();o.data.materials.append(mat)
    uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap')
    normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
    for p in o.data.polygons:
        normal=(normal_matrix@p.normal).normalized();axis=max(range(3),key=lambda i:abs(normal[i]))
        for li in p.loop_indices:
            v=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
            axes=[1,2] if axis==0 else ([0,2] if axis==1 else [0,1])
            uv.data[li].uv=(v[axes[0]]/scale,v[axes[1]]/scale)
for o in list(bpy.data.objects):
    if o.type!='MESH' or any(c.name.startswith('91_') for c in o.users_collection):continue
    name=o.name
    if name.startswith(('A_Mint_front','A_Mint_rear','A_Mint_west','A_Mint_east')):assign(o,surfaces['plaster_mint'])
    elif name.startswith(('B_Saffron_front','B_Saffron_rear','B_Saffron_west','B_Saffron_east')):assign(o,surfaces['plaster_saffron'])
    elif name.startswith(('Garage_front','Garage_rear','Garage_outer_wall','Interior_room_divider','West_pink_house')):assign(o,surfaces['plaster_cream'])
    elif name.startswith(('Gabled_roof','Garage_flat_roof','Shed_roof','West_roof')):assign(o,surfaces['roof'],2.6)
    elif name.startswith(('Window_jamb','Window_lintel','Door_jamb','Door_lintel','Garage_frame','Pergola_beam','Pergola_louvre','Shutter')):assign(o,surfaces['wood'],1.1)
    elif name.startswith(('Garden_lawn','Backyard_lawn','Front_grass')):assign(o,surfaces['grass'],5.6)
    elif name.startswith(('Approach_sidewalk','Culdesac_footway','Backyard_terrace','Side_lane_paving','Entry_path','Driveway','Facade_stone_plinth','Planter')):assign(o,surfaces['concrete'],2.7)
    elif name.startswith(('Street_main','Central_culdesac','Road_repair')):assign(o,surfaces['road'],4.5)
# Reduce toy-like saturated plastic on vehicles/trim while keeping team color landmarks.
for name,color in {'ivory':(.74,.68,.55),'chalk':(.66,.63,.53),'roof_light':(.12,.16,.15),'wood_light':(.48,.36,.22),'wood':(.27,.20,.12),'coral':(.49,.24,.16),'coral_light':(.64,.36,.22),'mint':(.14,.30,.25),'mint_light':(.29,.47,.37),'ochre_light':(.72,.50,.20),'steel':(.135,.18,.17),'sand':(.36,.39,.28),'sand_light':(.52,.53,.40),'glass':(.07,.15,.16),'rose':(.45,.27,.26)}.items():
    if name in M:
        m=M[name];m.diffuse_color=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
# Remove oversized toy-rock ring; replace with quiet, layered blue-gray cliff silhouettes.
for o in list(bpy.data.objects):
    if o.name.startswith(('Distant_sandstone','Boundary_rock')):bpy.data.objects.remove(o,do_unlink=True)
context=bpy.data.collections.new('62_V2_Context');scene.collection.children.link(context)
def material(name,c):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*c,1);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.92;return m
cliffmats=[material('V2_Distant_Cliff_'+str(i),col) for i,col in enumerate([(.24,.30,.30),(.31,.36,.34),(.37,.40,.36),(.29,.34,.31)])]
for i,(cx,cy,w,d,h) in enumerate([(-61,58,24,20,33),(-39,79,28,21,43),(-13,87,23,19,33),(18,91,25,19,41),(49,77,24,21,34),(72,59,24,20,38),(-70,-65,26,20,27),(68,-67,25,20,29)]):
    verts=[];n=9
    for z,rr in [(-1,1.12),(h*.38,1),(h*.70,.75),(h,.48)]:
        for j in range(n):
            a=2*math.pi*j/n;v=1+random.uniform(-.16,.16);verts.append((cx+math.cos(a)*w*.5*rr*v,cy+math.sin(a)*d*.5*rr*v,z+random.uniform(-1,1)))
    faces=[]
    for k in range(3):
        for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    faces.append(tuple(range(3*n,4*n)))
    me=bpy.data.meshes.new('Layered_cliff');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Far_cliff_'+str(i),me);context.objects.link(o)
    for m in cliffmats:me.materials.append(m)
    for p in me.polygons:p.material_index=random.randrange(len(cliffmats))
# Subtle ground transitions and warm/cool daylight, inspired by the photographs' value hierarchy.
world=scene.world;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.50,.66,.80,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.62
sun=bpy.data.objects['Warm_afternoon_sun'];sun.data.energy=2.65;sun.data.color=(1.0,.93,.83);sun.data.angle=math.radians(4.0);sun.rotation_euler=(math.radians(37),math.radians(-24),math.radians(-35))
bpy.data.objects['Sky_fill'].data.energy=1200
for o in bpy.data.objects:
    if o.name.startswith('Interior_fill'):o.data.energy=105;o.data.color=(.78,.87,1.0)
scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.10
scene.cycles.samples=64;scene.cycles.use_denoising=False
scene['build_version']='2.0_ArtRefinement';scene['art_direction']='User references: warm textured plaster and stone, aged timber, layered foliage, neutral daylight with warm/cool separation'
# Parent controls imports so geometry helpers can complete independently.
sys.path.insert(0,ROOT)
for module_name in ['add_architecture','add_foliage']:
    try:
        module=__import__(module_name);module.apply();print('APPLIED',module_name,flush=True)
    except ImportError:print('PENDING',module_name,flush=True)
for im in bpy.data.images:
    if im.name.startswith('V2_') and im.has_data:im.pack()
scene.camera=bpy.data.objects['Camera_Street'];scene.render.resolution_x=1500;scene.render.resolution_y=1000
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Working.blend')
for key,cam in [('v2_street','Camera_Street'),('v2_backyard','Camera_Backyard'),('v2_hero','Camera_Hero')]:
    scene.camera=bpy.data.objects[cam];scene.render.filepath=ROOT+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['Camera_Hero'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Working.blend')
print('ART_PASS_COMPLETE',flush=True)
