"""Original Sunward landmark correction, independently callable and reversible.

Load a COPY of Sunward_TestSite.blend, then call apply(site_frames_path).
This owns central vehicles, welcome sign, timber roadwork props and context clock.
No house, terrain, shared material, fence, presentation camera or old collider edits.
The manager must rebuild the joined static collider after all geometry patches.
"""
import bpy, bmesh, math, json, os, sys, argparse
from mathutils import Matrix, Vector

VERSION = 'landmarks-classic-r13'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../build/reports'))
os.makedirs(ROOT, exist_ok=True)
OLD_GROUPS = {
    'SUNLINE_Shuttle': ((4, -2.15, .03), -.035),
    'Sunward_Delivery': ((-3, 2.70, .02), .025),
    'West_Pink_Sedan': ((-21, 0, .03), .18),
}
COLLISION_PREFIXES = (
    'Shuttle_chassis', 'Shuttle_body', 'Shuttle_window_cabin', 'Shuttle_roof', 'Shuttle_hood',
    'Truck_chassis', 'Truck_cargo_floor', 'Truck_cargo_roof', 'Truck_cargo_side',
    'Truck_cargo_bulkhead', 'Truck_cab', 'Truck_cab_glazing', 'Truck_cab_roof', 'Truck_loading_ramp',
    'LM_Truck_cargo_crate',
    'Sedan_lower', 'Sedan_cabin', 'Sedan_hood', 'Sedan_trunk', 'Sign_post',
    'LM_GreenSedan_lower', 'LM_GreenSedan_cabin', 'LM_GreenSedan_hood', 'LM_GreenSedan_trunk',
    'Sunward_sign', 'LM_Jeep_body', 'LM_Jeep_hood', 'LM_Jeep_windshield',
    'LM_Jeep_rear', 'LM_Roadwork_rail', 'LM_Roadwork_post', 'LM_Sandbag',
)

def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def material(name):
    m = bpy.data.materials.get(name)
    if m is None:
        raise RuntimeError('Missing existing shared material: '+name)
    return m

def set_material(o, name):
    if o.data.users > 1:
        o.data = o.data.copy()
    o.data.materials.clear()
    o.data.materials.append(material(name))

def mesh(name, verts, faces, mat, col, bevel=0):
    o = bpy.data.objects.get(name)
    old = o.data if o and o.type == 'MESH' else None
    data = bpy.data.meshes.new(name+'_LMGeometry')
    data.from_pydata(verts, [], faces)
    data.update()
    if o is None:
        o = bpy.data.objects.new(name, data)
        col.objects.link(o)
    else:
        o.data = data
        o.modifiers.clear()
        o.parent = None
    o.matrix_world = Matrix.Identity(4)
    data.materials.append(material(mat))
    o['landmark_patch_owner'] = VERSION
    if bevel:
        m = o.modifiers.new('Landmark painted edge bevel', 'BEVEL')
        m.width = bevel
        m.segments = 1
        m = o.modifiers.new('Landmark weighted corner normals', 'WEIGHTED_NORMAL')
        m.keep_sharp = True
    if old and old.users == 0:
        bpy.data.meshes.remove(old)
    return o

def cube(name, loc, dim, mat, col, bevel=.025):
    w, d, h = [v/2 for v in dim]
    o = mesh(name, [(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),
                   (-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)],
             [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],
             mat, col, bevel)
    o.location = loc
    return o

def beam(name, a, b, width, mat, col, depth=None):
    a, b = Vector(a), Vector(b)
    o = cube(name, (a+b)/2, (width, depth or width, (b-a).length), mat, col, .012)
    o.rotation_euler = (b-a).to_track_quat('Z','Y').to_euler()
    return o

def cylinder(name, loc, radius, depth, mat, col, axis='Z', n=16):
    verts = []
    for z in (-depth/2, depth/2):
        verts.extend([(math.cos(i*2*math.pi/n)*radius, math.sin(i*2*math.pi/n)*radius, z) for i in range(n)])
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o = mesh(name, verts, faces, mat, col, .01)
    o.location = loc
    if axis == 'X': o.rotation_euler.y = math.pi/2
    if axis == 'Y': o.rotation_euler.x = math.pi/2
    return o

def sphere(name, loc, radius, mat, col, n=12, rings=6):
    verts = [(0,0,-radius)]
    for r in range(1,rings):
        lat=-math.pi/2+r*math.pi/rings
        verts.extend([(radius*math.cos(lat)*math.cos(i*2*math.pi/n),
                       radius*math.cos(lat)*math.sin(i*2*math.pi/n), radius*math.sin(lat)) for i in range(n)])
    verts.append((0,0,radius)); top=len(verts)-1
    faces=[(0,1+(i+1)%n,1+i) for i in range(n)]
    for r in range(rings-2):
        s=1+r*n;t=s+n
        faces += [(s+i,s+(i+1)%n,t+(i+1)%n,t+i) for i in range(n)]
    start=1+(rings-2)*n
    faces += [(top,start+i,start+(i+1)%n) for i in range(n)]
    o=mesh(name,verts,faces,mat,col);o.location=loc;return o

def text(name, body, loc, size, mat, col, rot=(math.pi/2,0,0)):
    o=bpy.data.objects.get(name)
    if o is None:
        cu=bpy.data.curves.new(name,'FONT');o=bpy.data.objects.new(name,cu);col.objects.link(o)
    cu=o.data;cu.body=body;cu.align_x='CENTER';cu.size=size;cu.extrude=.003;cu.bevel_depth=.001
    o.location=loc;o.rotation_euler=rot;o.scale=(1,1,1);set_material(o,mat)
    o['landmark_patch_owner']=VERSION
    return o

def tag_group(objects, name):
    for o in objects:
        o['vehicle']=name
        o['landmark_group']=name
        o['landmark_patch_owner']=VERSION

def localize_group(name):
    origin, angle=OLD_GROUPS[name]
    old=(Matrix.Translation(Vector(origin)) @ Matrix.Rotation(angle,4,'Z')).inverted()
    objects=[o for o in bpy.data.objects if o.get('vehicle')==name]
    if not objects: raise RuntimeError('Required baseline group absent: '+name)
    for o in objects:
        o.matrix_world=old @ o.matrix_world
        o['landmark_group']=name
        o['landmark_patch_owner']=VERSION
    bpy.context.view_layer.update()
    return objects

def oriented_bounds(objects):
    # Object.location setters do not immediately refresh matrix_world for new
    # objects in background Blender. Evaluate before measuring or placing.
    bpy.context.view_layer.update()
    points=[o.matrix_world @ Vector(p) for o in objects if o.type=='MESH' for p in o.bound_box]
    return Vector([min(p[i] for p in points) for i in range(3)]),Vector([max(p[i] for p in points) for i in range(3)])

def marker_frame(crop, yaw, scale, origin):
    x=(crop[0]-origin[0])*scale;y=(origin[1]-crop[1])*scale
    return Matrix.Translation(Vector((x,y,.035))) @ Matrix.Rotation(yaw,4,'Z')

def place_group(objects, name, crop, yaw, site_scale, origin, dim_scale=(1,1,1), center_bounds=True, root_z=.035):
    lo,hi=oriented_bounds(objects)
    center=(lo+hi)/2 if center_bounds else Vector((0,0,0))
    center.z=0
    frame=marker_frame(crop,yaw,site_scale,origin);frame.translation.z=root_z
    mat=frame @ Matrix.Diagonal(Vector((*dim_scale,1))) @ Matrix.Translation(-center)
    for o in objects:
        o['landmark_local_matrix']=[v for row in o.matrix_world for v in row]
        o.matrix_world=mat @ o.matrix_world
        o['landmark_group']=name
    forward_local=Vector((0,-1,0)) if name in {'Welcome_Sign','Context_Clock'} else Vector((1,0,0))
    forward_world=Matrix.Rotation(yaw,4,'Z') @ forward_local
    return {'group':name,'anchor_crop_pixel':list(crop),'anchor_world':list(frame.translation),
            'yaw_degrees':math.degrees(yaw),'forward_local':list(forward_local),
            'forward_world':list(forward_world),
            'source_center_offset_local':list(center),'geometry_scale':list(dim_scale),
            'group_local_to_world':[list(row) for row in mat],
            'original_names_preserved':True, 'object_count':len(objects)}

def refine_bus(objects):
    col=collection('20_CentralVehicles')
    # A low polygon barrel roof silhouette, rather than a flat slab.
    section=[(-1.435,2.94),(-1.39,3.17),(-1.15,3.38),(-.68,3.49),(0,3.52),
             (.68,3.49),(1.15,3.38),(1.39,3.17),(1.435,2.94)]
    verts=[(x,y,z) for x in (-5.36,5.38) for y,z in section]
    n=len(section);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,i+n,i+n+1,i+1) for i in range(n-1)]
    faces += [(n-1,2*n-1,n,0)]
    mesh('Shuttle_roof',verts,faces,'ochre_light',col,.035)
    # The structural primary shows a cab-over bus. Extend cabin/body to the
    # established nose plane and retain only a shallow face cap under the glass.
    cube('Shuttle_body',(.03,0,1.20),(10.62,2.75,1.04),'ochre_light',col,.13)
    cube('Shuttle_window_cabin',(0,0,2.30),(10.60,2.63,1.25),'glass',col,.10)
    # Keep this historical object ID behind the flat nose face. It must not
    # cover the preserved grille/headlamp planes or project as an engine hood.
    cube('Shuttle_hood',(5.275,0,1.31),(.12,2.70,.50),'ochre_light',col,.045)
    # Two windshield panes, yellow center mullion, visible bus face and marker lamps.
    for i,yy in enumerate((-.68,.68)):
        cube('LM_Bus_windshield_'+str(i),(5.325,yy,2.43),(.075,1.19,.88),'glass',col,.05)
    cube('LM_Bus_windshield_mullion',(5.375,0,2.43),(.10,.095,.98),'ochre_light',col)
    for side in (-1,1):
        cube('LM_Bus_front_corner_'+str(side),(5.335,side*1.35,2.34),(.15,.15,1.14),'ochre_light',col)
    cube('Shuttle_destination',(5.425,0,3.035),(.09,1.8,.25),'roof',col)
    # Keep fictional project branding in the recognizable school-bus form.
    text('LM_Bus_front_label','SCHOOL BUS',(5.479,0,3.027),.13,'ivory',col,(math.pi/2,0,math.pi/2))
    for i,yy in enumerate((-.96,-.48,0,.48,.96)):
        cylinder('LM_Bus_marker_'+str(i),(5.425,yy,3.265),.066,.065,'lamp',col,'X',12)
    for o in objects:
        if o.name.startswith('Shuttle_roof_hatch'):
            o.location.z=3.555
        if o.name.startswith('Shuttle_bumper'):set_material(o,'steel')
        if o.name.startswith('Shuttle_hub'):set_material(o,'steel')
    for i,yy in enumerate((-1.02,1.02)):
        cylinder('LM_Bus_rear_stop_'+str(i),(-5.34,yy,1.42),.115,.05,'coral',col,'X')
        cylinder('LM_Bus_rear_indicator_'+str(i),(-5.35,yy,1.72),.10,.05,'ochre_light',col,'X')
    # Add rear framing and safety rub rails using the project's existing palette.
    cube('LM_Bus_rear_band',(-5.35,0,2.66),(.08,2.48,.16),'ochre_light',col)
    for side in (-1,1):
        for i,z in enumerate((1.00,1.41)):
            cube('LM_Bus_rubrail_'+str(side)+'_'+str(i),(-.48,side*1.417,z),(9.65,.055,.085),'roof',col,.012)
    new=[o for o in col.objects if o.name.startswith('LM_Bus_')]
    tag_group(new,'SUNLINE_Shuttle')
    return [o for o in bpy.data.objects if o.get('vehicle')=='SUNLINE_Shuttle']

def refine_truck(objects):
    col=collection('20_CentralVehicles')
    for o in objects:
        if o.name.startswith(('Truck_cargo_side','Truck_cargo_bulkhead')):set_material(o,'ivory')
        if o.name.startswith(('Truck_cab','Truck_window_pillar','Truck_handle')) and not 'glazing' in o.name:set_material(o,'coral')
        if o.name.startswith('Truck_rib'):set_material(o,'chalk')
        if o.name.startswith('Truck_cream_stripe'):set_material(o,'chalk')
        if o.name.startswith('Truck_hub'):set_material(o,'steel')
    # The sides remain a continuous real wall. Red lower painted panels are thin overlays.
    for side in (-1,1):
        cube('LM_Truck_red_lower_'+str(side),(-1.27,side*1.582,1.62),(6.93,.035,1.01),'coral',col,.006)
        for i,z in enumerate((1.20,1.47,1.74,2.92,3.22,3.52)):
            cube('LM_Truck_siding_'+str(side)+'_'+str(i),(-1.27,side*1.605,z),(6.93,.025,.026),
                 'coral_light' if z<2 else 'chalk',col,0)
    # Tall tractor radiator and smaller squared cab cap improve the classic silhouette.
    cube('Truck_front_grille',(5.085,0,1.61),(.10,1.47,1.01),'roof',col,.045)
    for i,zz in enumerate((1.20,1.40,1.60,1.80,2.00)):
        cube('LM_Truck_radiator_'+str(i),(5.16,0,zz),(.035,1.36,.055),'steel',col,.012)
    for side in (-1,1):
        # Reuse both original headlamp IDs as round lamps rather than leaving
        # their square predecessors visibly stacked behind new lamps.
        lampname='Truck_headlamp'+('' if side==-1 else '.001')
        cylinder(lampname,(5.17,side*1.035,1.69),.19,.075,'lamp',col,'X')
        beam('LM_Truck_mirrorarm_'+str(side),(4.48,side*1.43,2.8),(4.34,side*1.88,2.8),.045,'steel',col)
        cube('LM_Truck_mirror_'+str(side),(4.31,side*1.87,2.88),(.13,.15,.47),'steel',col)
        cylinder('LM_Truck_exhaust_'+str(side),(2.54,side*1.39,3.63),.082,.79,'steel',col,'Z',12)
    # Remove cream stripe through the lower red panel; original branding remains.
    for o in objects:
        if o.name.startswith('Truck_cream_stripe'):o.location.z=2.185;o.scale.z=.27
        if o.name=='Delivery_label':o.location.z=2.98;o.location.y=-1.645;set_material(o,'coral')
        if o.name=='Delivery_subtitle':o.location.z=2.56;o.location.y=-1.645;set_material(o,'roof')
        # Baseline rear tire tops protruded through the cargo floor. Their
        # authored visual radius/center are adjusted below the unchanged deck.
        if o.name.startswith(('Truck_tire','Truck_hub')) and o.location.x<0:
            o.location.z=.60;o.scale.x*=.57/.61;o.scale.y*=.57/.61
    # Robust squared rear portal matches cream piers, red taillights and open ramp.
    for side in (-1,1):
        cube('LM_Truck_rear_portal_'+str(side),(-4.89,side*1.425,2.52),(.12,.24,2.86),'chalk',col)
        cube('LM_Truck_tail_lamp_'+str(side),(-4.963,side*1.425,1.64),(.035,.12,.36),'coral',col,.01)
    # Three authored cases against one wall dress the cargo view without
    # obstructing the centerline ramp-to-perch route.
    for i,(x,y,z,w,d,h) in enumerate([(-1.85,.99,1.565,.92,.65,.78),
                                     (-.72,.99,1.575,.96,.65,.80),
                                     (-.72,.99,2.30,.72,.58,.65)]):
        cube('LM_Truck_cargo_crate_'+str(i),(x,y,z),(w,d,h),'wood_light',col,.035)
        for j,dz in enumerate((-h*.32,h*.32)):
            cube('LM_Truck_cargo_band_'+str(i)+'_'+str(j),(x,y,z+dz),(w+.02,d+.025,.046),'wood',col,.008)
    new=[o for o in col.objects if o.name.startswith('LM_Truck_')]
    tag_group(new,'Sunward_Delivery')
    return [o for o in bpy.data.objects if o.get('vehicle')=='Sunward_Delivery']

def make_sign():
    col=collection('22_ClassicLandmarks')
    names=['Sign_post','Sign_post.001','Sunward_sign','Sunward_sign_inset','Map_title','Map_subtitle']
    # Existing IDs are reused even when geometry is replaced.
    for i,x in enumerate((-2.36,2.36)):
        cube('Sign_post'+('' if i==0 else '.001'),(x,0,1.57),(.38,.40,3.14),'ivory',col,.04)
        cube('LM_Sign_pier_foot_'+str(i),(x,0,.12),(.61,.65,.24),'chalk',col,.04)
        cube('LM_Sign_pier_cap_'+str(i),(x,0,3.15),(.61,.62,.15),'chalk',col,.03)
        sphere('LM_Sign_finial_'+str(i),(x,0,3.47),.29,'ivory',col)
    cube('Sunward_sign',(0,0,1.64),(4.72,.27,2.75),'ivory',col,.045)
    cube('Sunward_sign_inset',(0,-.171,1.98),(4.18,.055,1.93),'coral',col,.02)
    cube('LM_Sign_civic_strip',(0,-.17,.71),(4.18,.065,.49),'roof',col,.015)
    cube('LM_Sign_lower_rail',(0,-.215,1.03),(4.53,.07,.13),'chalk',col)
    text('LM_Sign_welcome','Welcome to',(0,-.21,2.58),.29,'ivory',col)
    text('Map_title','SUNWARD',(0,-.215,1.97),.59,'ivory',col)
    text('Map_subtitle','TEST SITE  /  07',(0,-.215,1.43),.24,'ivory',col)
    text('LM_Sign_civic_text','TESTING A BRIGHTER TOMORROW',(-.34,-.219,.66),.133,'ivory',col)
    cylinder('LM_Sign_atom_disc',(1.70,-.221,.70),.175,.025,'ochre_light',col,'Y',24)
    # Original stylized atomic symbol, no imported graphic texture.
    for i in range(3):
        a=i*2*math.pi/3
        verts=[(1.70,-.24,.70),(1.70+math.cos(a+.15)*.15,-.24,.70+math.sin(a+.15)*.15),
               (1.70+math.cos(a+1.1)*.15,-.24,.70+math.sin(a+1.1)*.15)]
        mesh('LM_Sign_atom_'+str(i),verts,[(0,1,2)],'roof',col)
    return [bpy.data.objects[n] for n in names]+[o for o in col.objects if o.name.startswith('LM_Sign_')]

def make_jeep():
    col=collection('22_ClassicLandmarks');names=[]
    def add(o):names.append(o.name);return o
    add(cube('LM_Jeep_body',(-.10,0,.71),(3.26,1.62,.42),'mint_dark',col,.06))
    add(cube('LM_Jeep_hood',(.99,0,1.11),(1.30,1.57,.33),'mint',col,.07))
    add(cube('LM_Jeep_rear',(-1.24,0,1.02),(.81,1.70,.62),'mint_dark',col,.035))
    for side in (-1,1):
        add(cube('LM_Jeep_sill_'+str(side),(-.25,side*.79,.99),(1.18,.10,.36),'mint',col))
        add(cube('LM_Jeep_front_fender_'+str(side),(.95,side*.87,.96),(1.52,.32,.16),'mint_dark',col))
        add(cube('LM_Jeep_rear_fender_'+str(side),(-1.22,side*.87,.96),(.95,.32,.16),'mint_dark',col))
        add(cube('LM_Jeep_seat_'+str(side),(-.29,side*.43,1.05),(.60,.56,.22),'wood',col,.08))
        add(cube('LM_Jeep_seat_back_'+str(side),(-.64,side*.43,1.36),(.14,.56,.53),'wood',col,.07))
    add(cube('LM_Jeep_windshield',(.36,0,1.72),(.065,1.57,.80),'glass',col,.03))
    for side in (-1,1):
        add(beam('LM_Jeep_windshield_pillar_'+str(side),(.38,side*.79,1.27),(.38,side*.79,2.14),.06,'mint',col))
    add(cube('LM_Jeep_windshield_top',(.39,0,2.15),(.075,1.65,.07),'mint',col))
    add(cube('LM_Jeep_windshield_middle',(.40,0,1.74),(.075,.055,.80),'mint',col))
    add(cube('LM_Jeep_front_face',(1.68,0,1.02),(.12,1.58,.65),'mint_dark',col))
    for i,y in enumerate((-.36,-.24,-.12,0,.12,.24,.36)):
        add(cube('LM_Jeep_grille_'+str(i),(1.75,y,1.03),(.03,.045,.41),'roof',col,.012))
    for side in (-1,1):
        add(cylinder('LM_Jeep_headlight_'+str(side),(1.76,side*.58,1.12),.17,.06,'lamp',col,'X'))
    for i,x in enumerate((-1.16,1.00)):
        for side in (-1,1):
            add(cylinder('LM_Jeep_tire_'+str(i)+'_'+str(side),(x,side*.91,.51),.47,.28,'tire',col,'Y'))
            add(cylinder('LM_Jeep_hub_'+str(i)+'_'+str(side),(x,side*1.067,.51),.25,.045,'mint',col,'Y',12))
    add(cylinder('LM_Jeep_spare',(-1.84,0,1.17),.45,.26,'tire',col,'X'))
    add(cylinder('LM_Jeep_spare_hub',(-1.99,0,1.17),.24,.04,'mint',col,'X',12))
    add(cube('LM_Jeep_bumper',(1.86,0,.64),(.15,2.0,.16),'steel',col))
    add(cube('LM_Jeep_rear_bumper',(-1.72,0,.61),(.15,1.88,.16),'steel',col))
    objects=[bpy.data.objects[n] for n in names];tag_group(objects,'Entrance_Jeep');return objects

def make_roadwork():
    col=collection('22_ClassicLandmarks');names=[]
    def add(o):names.append(o.name);return o
    # Cross-road construction rails, green-painted timber and stone/sandbag feet.
    for i,y in enumerate((-4.8,-2.4,0,2.4,4.8)):
        add(cube('LM_Roadwork_post_'+str(i),(0,y,.67),(.16,.17,1.32),'mint',col))
        add(sphere('LM_Sandbag_'+str(i),(0,y,.29),.46,'concrete_light',col))
        bpy.data.objects[names[-1]].scale=(1.30,.75,.62)
    for i,y in enumerate((-3.6,-1.2,1.2,3.6)):
        for j,z in enumerate((.54,1.02)):
            add(cube('LM_Roadwork_rail_'+str(i)+'_'+str(j),(0,y,z),(.085,2.37,.17),'mint_light',col))
    add(cube('LM_Roadwork_notice',(0.062,.0,.83),(.085,1.00,.45),'ochre_light',col))
    add(text('LM_Roadwork_text','ROAD WORK',(0.118,0,.83),.14,'roof',col,(math.pi/2,0,math.pi/2)))
    objects=[bpy.data.objects[n] for n in names]
    for o in objects:o['landmark_group']='Exit_Roadwork';o['landmark_patch_owner']=VERSION
    return objects

def make_clock():
    col=collection('23_ContextClock');names=[]
    def add(o):names.append(o.name);return o
    # A narrow steel four-leg tapered tower, deliberately outside the playable lot.
    def corner(side,z):return side*(1.31-.062*z)
    for xsign in (-1,1):
        for ysign in (-1,1):
            add(beam('LM_Clock_leg_'+str(xsign)+'_'+str(ysign),
                     (corner(xsign,0),corner(ysign,0),0),
                     (corner(xsign,13),corner(ysign,13),13),.115,'steel',col))
    for j,z in enumerate((1.3,4.1,6.9,9.7,12.5)):
        w=1.31-.062*z
        for side in (-1,1):
            add(beam('LM_Clock_crossx_'+str(j)+'_'+str(side),(-w,side*w,z),(w,side*w,z),.085,'steel',col))
            add(beam('LM_Clock_crossy_'+str(j)+'_'+str(side),(side*w,-w,z),(side*w,w,z),.085,'steel',col))
        if j<4:
            zz=z+2.8;ww=1.31-.062*zz
            for side in (-1,1):
                add(beam('LM_Clock_bracex_'+str(j)+'_'+str(side),(-w,side*w,z),(ww,side*ww,zz),.07,'steel',col))
                add(beam('LM_Clock_bracexb_'+str(j)+'_'+str(side),(w,side*w,z),(-ww,side*ww,zz),.07,'steel',col))
                add(beam('LM_Clock_bracey_'+str(j)+'_'+str(side),(side*w,-w,z),(side*ww,ww,zz),.07,'steel',col))
    # Mount the disc ahead of the front tower frame so braces cannot cross its face.
    add(cylinder('LM_Clock_face',(0,-.68,13.0),1.12,.12,'ivory',col,'Y',48))
    add(cylinder('LM_Clock_rim',(0,-.59,13.0),1.18,.10,'steel',col,'Y',48))
    for i in range(12):
        a=i*math.pi/6;x=math.sin(a);z=math.cos(a)
        add(beam('LM_Clock_tick_'+str(i),(x*.92,-.77,13+z*.92),(x*1.03,-.77,13+z*1.03),.038,'steel',col))
    add(beam('LM_Clock_hand_minute',(0,-.80,13.0),(-.12,-.80,13.81),.047,'roof',col))
    add(beam('LM_Clock_hand_hour',(0,-.83,13.0),(.53,-.83,13.29),.074,'roof',col))
    add(cylinder('LM_Clock_hub',(0,-.87,13.0),.088,.055,'steel',col,'Y',16))
    add(cube('LM_Clock_plaque',(0,-1.19,5.24),(2.84,.13,1.3),'ivory',col,.035))
    add(text('LM_Clock_title','SUNWARD',(0,-1.271,5.48),.38,'roof',col))
    add(text('LM_Clock_motto','TESTING A BRIGHTER\nTOMORROW',(0,-1.272,4.99),.165,'roof',col))
    objects=[bpy.data.objects[n] for n in names]
    for o in objects:o['landmark_group']='Context_Clock';o['landmark_patch_owner']=VERSION;o['collision']='none: context beyond playable perimeter'
    return objects

def collision_proxies():
    col=collection('92_LandmarkCollision')
    for o in list(col.objects):bpy.data.objects.remove(o,do_unlink=True)
    for o in list(bpy.data.objects):
        if o.type!='MESH' or o.get('landmark_patch_owner')!=VERSION:continue
        if not any(o.name.startswith(p) for p in COLLISION_PREFIXES):continue
        cp=bpy.data.objects.new('COL_V3_LM_'+o.name,o.data.copy());col.objects.link(cp)
        cp.matrix_world=o.matrix_world.copy();cp.data.materials.clear();cp.display_type='WIRE'
        cp['collision']='static triangle mesh';cp['collision_source_id']=o.name;cp['landmark_patch_owner']=VERSION
    col.hide_render=True;col.hide_viewport=True
    return col

def parse_frames(path):
    data=json.load(open(path)) if path else {}
    rule=data.get('image_to_world',{})
    scale=rule.get('uniform_m_per_crop_pixel',data.get('meters_per_crop_pixel',data.get('scale_m_per_px',.1269490642060507)))
    origin=rule.get('origin_crop_pixels',data.get('origin_crop_pixels',data.get('court_origin_crop_pixels',[550,475])))
    # Canonical coordinate contract is mandatory; no second global rotation.
    return data,float(scale),origin

def apply(site_frames_path=None, overrides=None):
    s=bpy.context.scene
    if s.get('landmark_patch_version'):
        raise RuntimeError('Landmark revision '+s['landmark_patch_version']+' is already applied. Reload a pristine pre-landmark integration checkpoint before applying '+VERSION+'.')
    frames,scale,origin=parse_frames(site_frames_path)
    options={
        'bus_crop':[575,494.5], 'truck_crop':[512.5,452.5],
        'bus_yaw_degrees':14.708303899682749, 'truck_yaw_degrees':16.020292302071223,
        'bus_length_m':10.5, 'truck_length_m':13.339924612104413,
        'yellow_car_crop':[410,487], 'yellow_car_yaw_degrees':26.0,
        'green_car_crop':[451,392], 'green_car_yaw_degrees':-71.792,
        # The marker's unsigned axis is -56.31 degrees. Add 180 so the sign's
        # authored -Y front normal faces the road exit (+world X).
        'sign_crop':[466,520], 'sign_yaw_degrees':123.69006752597979,
        'jeep_crop':[650,468], 'jeep_yaw_degrees':90.0,
        'roadwork_crop':[677,469], 'roadwork_yaw_degrees':0.0,
        'clock_crop':[520,-20], 'clock_yaw_degrees':18.208,
        'clock_anchor_status':'approximate non-playable backdrop beyond the green rear boundary; not a measured tactical-map landmark',
    }
    options.update(frames.get('landmarks',{}))
    for group,prefix in [('SUNLINE_Shuttle','bus'),('Sunward_Delivery','truck')]:
        frame=frames.get('landmark_frames',{}).get(group,{})
        if frame:
            options[prefix+'_crop']=frame['position_crop_pixels']
            options[prefix+'_yaw_degrees']=frame['yaw_degrees']
            options[prefix+'_length_m']=frame['target_reference_axis_length_m']
    # Family-dependent approximate landmarks follow the canonical GREEN
    # family, not an assumed north/south label. The corrected family contract
    # is mandatory for this revision; all measured central landmarks stay fixed.
    green_frame=frames.get('house_frames',{}).get('A_Mint',{})
    if green_frame.get('geometric_lot_id')!='south':
        raise RuntimeError('Landmarks r11 requires the family-corrected canonical A_Mint south/green frame.')
    gyaw=math.radians(green_frame['yaw_degrees']);groot=Vector(green_frame['position_blender'])
    grot=Matrix.Rotation(gyaw,4,'Z')
    closed_bay_local=Vector((-10.061026,-2.487918,.18))
    closed_bay_world=groot+grot @ closed_bay_local
    front=grot @ Vector((0,-1,0));car_world=closed_bay_world+front*3.2
    options['green_car_crop']=[origin[0]+car_world.x/scale,origin[1]-car_world.y/scale]
    options['green_car_yaw_degrees']=math.degrees(math.atan2(front.y,front.x))
    options['green_car_root_z']=.0248
    options['green_car_driveway_top_z']=.034
    rear=-front
    outline=[Vector(p) for p in frames['outline_blender']]
    rear_projection=max((p-groot).dot(rear) for p in outline)
    clock_world=groot+rear*(rear_projection+11.0)
    options['clock_crop']=[origin[0]+clock_world.x/scale,origin[1]-clock_world.y/scale]
    options['clock_yaw_degrees']=green_frame['yaw_degrees']
    desert=bpy.data.objects.get('World_desert')
    desert_matrix=desert.matrix_basis if desert and desert.parent is None else (desert.matrix_world if desert else Matrix.Identity(4))
    clock_ground=max((desert_matrix@Vector(p)).z for p in desert.bound_box) if desert else -.05
    options['clock_context_ground_z']=clock_ground;options['clock_root_z']=clock_ground+.005023
    options['clock_anchor_status']='approximate backdrop11m beyond corrected lower green rear support line; not a measured tactical landmark'
    options['green_car_anchor_status']='approximate3.2m outside the actual lower green closed outer garage bay; local bay point supplied by house r6 contract'
    if overrides:options.update(overrides)
    protected={o.name:tuple(v for row in o.matrix_world for v in row) for o in bpy.data.objects
               if any(c.name.startswith(('00_','10_','11_','12_','13_','31_')) for c in o.users_collection)}
    reports=[]
    bus=refine_bus(localize_group('SUNLINE_Shuttle'))
    lo,hi=oriented_bounds(bus);sx=options['bus_length_m']/(hi.x-lo.x)
    reports.append(place_group(bus,'SUNLINE_Shuttle',options['bus_crop'],math.radians(options['bus_yaw_degrees']),scale,origin,(sx,.94,.98)))
    truck=refine_truck(localize_group('Sunward_Delivery'))
    lo,hi=oriented_bounds(truck);sx=options['truck_length_m']/(hi.x-lo.x)
    reports.append(place_group(truck,'Sunward_Delivery',options['truck_crop'],math.radians(options['truck_yaw_degrees']),scale,origin,(sx,.90,.95)))
    car=localize_group('West_Pink_Sedan')
    # The old glass cabin lacked a bottom cap. Close that hidden underside
    # before duplication so both visible/collision meshes are outward solids.
    cabin=bpy.data.objects['Sedan_cabin']
    if cabin.data.users>1:cabin.data=cabin.data.copy()
    bm=bmesh.new();bm.from_mesh(cabin.data);bm.verts.ensure_lookup_table()
    bm.faces.new([bm.verts[i] for i in (0,1,2,3)])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(cabin.data);bm.free();cabin.data.update()
    # Preserve the original west-court sedan identity, and duplicate its authored
    # geometry for the separately photo-visible green driveway car.
    green=[]
    for o in car:
        cp=o.copy();cp.data=o.data.copy();cp.name='LM_Green'+o.name
        collection('22_ClassicLandmarks').objects.link(cp)
        cp['vehicle']='Green_Driveway_Sedan';cp['landmark_patch_owner']=VERSION;green.append(cp)
        if o.name.startswith(('Sedan_lower','Sedan_hood','Sedan_trunk')):set_material(cp,'mint_light')
    for o in car:
        if o.name.startswith(('Sedan_lower','Sedan_hood','Sedan_trunk')):set_material(o,'ochre_light')
    reports.append(place_group(car,'West_Pink_Sedan',options['yellow_car_crop'],math.radians(options['yellow_car_yaw_degrees']),scale,origin,(.85,.84,.92)))
    reports.append(place_group(green,'Green_Driveway_Sedan',options['green_car_crop'],math.radians(options['green_car_yaw_degrees']),scale,origin,(.85,.84,.92),root_z=options['green_car_root_z']))
    sign=make_sign();reports.append(place_group(sign,'Welcome_Sign',options['sign_crop'],math.radians(options['sign_yaw_degrees']),scale,origin,(.80,.9,.9),center_bounds=False))
    jeep=make_jeep();reports.append(place_group(jeep,'Entrance_Jeep',options['jeep_crop'],math.radians(options['jeep_yaw_degrees']),scale,origin,center_bounds=False))
    roadwork=make_roadwork();reports.append(place_group(roadwork,'Exit_Roadwork',options['roadwork_crop'],math.radians(options['roadwork_yaw_degrees']),scale,origin,center_bounds=False))
    # Replace only the four baseline road-end Jersey barriers and their color overlays.
    removed=[]
    for o in list(bpy.data.objects):
        if o.name.startswith(('Jersey_barrier','Barrier_color_panel')) and any(c.name=='30_ExteriorProps' for c in o.users_collection):
            removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
    clock=make_clock();reports.append(place_group(clock,'Context_Clock',options['clock_crop'],math.radians(options['clock_yaw_degrees']),scale,origin,center_bounds=False,root_z=options['clock_root_z']))
    # These are painted labels, not high-poly beveled metal lettering. Font
    # defaults otherwise inflate a few signs into hundreds of thousands of
    # triangles. Keep editable curves with a tiny printed surface thickness.
    for o in bpy.data.objects:
        if o.type=='FONT' and o.get('landmark_patch_owner')==VERSION:
            if o.data.users>1:o.data=o.data.copy()
            o.data.resolution_u=2;o.data.render_resolution_u=2
            o.data.bevel_resolution=0;o.data.bevel_depth=0;o.data.extrude=.0005
    bpy.context.view_layer.update()
    collision=collision_proxies()
    changed_protected=[name for name,mat in protected.items() if name not in bpy.data.objects or tuple(v for row in bpy.data.objects[name].matrix_world for v in row)!=mat]
    if changed_protected:raise RuntimeError('Protected object changes: '+repr(changed_protected))
    s['landmark_patch_version']=VERSION
    report={'version':VERSION,'site_frames':site_frames_path,'meters_per_crop_pixel':scale,'origin_crop_pixels':origin,
        'canonical_frame_version':frames.get('version'),
        'metric_scale_status':'Common canonical bus-anchored gameplay scale; original map meters unverified',
        'groups':reports,'options':options,'removed_inaccurate_road_barriers':removed,
        'protected_geometry_changes':changed_protected,'proxy_objects':len(collision.objects),
        'collision_integration':'Discard old joined COL_Sunward_Static; merge regenerated whole scene collision and these landmark proxies. Avoid duplicate bus/truck/car proxies.',
        'uncertain_anchors':['clock exact surveyed anchor','green driveway car interpolated spacing','sign yaw endpoint reading'],
        'jeep_signed_heading_evidence':'Primary official004 has rear bed/wheel image-left and hood/grille/front axle image-right; confirmed world+Y front by independent reviewer',
        'original_text_preserved':True,'commercial_assets_imported':False}
    report['family_dependent_anchors']={
        'family':'A_Mint green','geometric_lot_id':green_frame['geometric_lot_id'],
        'closed_outer_bay_local':list(closed_bay_local),'closed_outer_bay_world':list(closed_bay_world),
        'garage_outward_front_world':list(front),'car_center_world':next(g['anchor_world'] for g in reports if g['group']=='Green_Driveway_Sedan'),
        'car_outside_spacing_m':3.2,
        'car_driveway_top_z':options['green_car_driveway_top_z'],
        'clock_center_world':next(g['anchor_world'] for g in reports if g['group']=='Context_Clock'),'clock_rear_boundary_spacing_m':11.0,
        'clock_context_ground_z':options['clock_context_ground_z'],
        'status':'geometry-derived anchors with deliberately approximate exterior spacing; not authenticated original-map positions',
        'bay_source':'houses/green-closed-bay-anchor-r6.json, exact local front-center point from house worker',
    }
    truck_transform=Matrix(next(g['group_local_to_world'] for g in reports if g['group']=='Sunward_Delivery'))
    def anchor(local):return {'local_xyz':local,'world_xyz':list(truck_transform @ Vector(local))}
    report['truck_traversal']={
        'ramp_approach':anchor([-8.45,0,.17]),
        'ramp_lower_surface':anchor([-7.78,0,.20934]),
        'ramp_middle_surface':anchor([-6.36,0,.67492]),
        'ramp_upper_surface':anchor([-4.89,0,1.157]),
        'cargo_portal_inside':anchor([-4.45,0,1.175]),
        'cargo_middle_floor':anchor([-1.5,0,1.175]),
        'cargo_bulkhead_stop':anchor([1.70,0,1.175]),
        'interior_clear_width_m':2.81*.90,
        'floor_surface_world_z':.035+1.175*.95,
        'roof_clearance_m':(3.905-1.175)*.95,
        'ramp_clear_width_m':2.5*.90,
        'intended_route':'rear ramp enters a covered dead-end cargo perch, no cab-end exit',
    }
    report['sign_orientation']={
        'estimated_marker_endpoints_crop_pixels':[[456,508],[474,535]],
        'yaw_degrees':options['sign_yaw_degrees'],
        'front_normal_world':[math.sin(math.radians(options['sign_yaw_degrees'])),-math.cos(math.radians(options['sign_yaw_degrees'])),0],
        'heading_evidence':'thin-bar footprint and front face toward road exit in official street image',
        'uncertainty':'marker endpoint reading +/-4 crop pixels; sign geometry has primary photo evidence',
    }
    report['proxy_shapes']=[]
    for cp in collision.objects:
        # Hidden collections can have stale matrix_world on a fresh load; the
        # unparented matrix_basis is the authoritative proxy transform.
        points=[cp.matrix_basis @ Vector(p) for p in cp.bound_box]
        report['proxy_shapes'].append({'name':cp.name,'source_id':cp['collision_source_id'],
            'world_bounds':[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]],
            'matrix_world':[list(row) for row in cp.matrix_basis],
            'triangles':sum(len(p.vertices)-2 for p in cp.data.polygons)})
    with open(os.path.join(ROOT,'landmark_patch_report.json'),'w')as f:json.dump(report,f,indent=2)
    with open(os.path.join(ROOT,VERSION+'-report.json'),'w')as f:json.dump(report,f,indent=2)
    print('LANDMARK_PATCH_COMPLETE',json.dumps(report),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frames');p.add_argument('--out');p.add_argument('--overrides')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    apply(args.frames,json.load(open(args.overrides)) if args.overrides else None)
    if args.out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
