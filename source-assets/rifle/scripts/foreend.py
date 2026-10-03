"""Exterior foreend and folding sights for the reference-inspired game prop.

All dimensions are arbitrary scene coordinates. No operational internals are modeled.
"""
import bpy
import math
import bmesh
from mathutils import Vector

_OBJECTS = []
_COLLECTION = None


def _mat(name, color, metal=0.0, rough=0.5):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.diffuse_color = color
        material.use_nodes = True
        shader = material.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = color
        shader.inputs['Metallic'].default_value = metal
        shader.inputs['Roughness'].default_value = rough
    return material


def _link(obj, mat):
    if mat:
        obj.data.materials.append(mat)
    if _COLLECTION not in obj.users_collection:
        _COLLECTION.objects.link(obj)
    for coll in tuple(obj.users_collection):
        if coll != _COLLECTION:
            coll.objects.unlink(obj)
    _OBJECTS.append(obj)
    return obj


def _bevel(obj, width=0.008, segments=1, smooth=False):
    if width:
        bevel = obj.modifiers.new('Soft machined edge', 'BEVEL')
        bevel.width = width
        bevel.segments = segments
        bevel.limit_method = 'ANGLE'
        bevel.angle_limit = 0.46
        bevel.harden_normals = True
    for polygon in obj.data.polygons:
        polygon.use_smooth = smooth
    normals = obj.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
    normals.keep_sharp = True
    normals.weight = 35
    return obj


def _mesh(name, verts, faces, material, bevel=0.0, smooth=False):
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.000001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    _link(obj, material)
    _bevel(obj, bevel, 1, smooth)
    return obj


def _box(name, loc, size, material, bevel=0.0, segments=1):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _link(obj, material)
    _bevel(obj, bevel, segments)
    return obj


def _px(x):
    return (x - 349.0) / 80.0


def _pz(y):
    return (171.0 - y) / 80.0


def _prism_px(name, points, y0, y1, material, bevel=0.008):
    profile = [(_px(x), _pz(z)) for x, z in points]
    verts = [(x, y0, z) for x, z in profile] + [(x, y1, z) for x, z in profile]
    n = len(profile)
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces.extend((i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n))
    return _mesh(name, verts, faces, material, bevel)


def _cross_extrude(name, x0, x1, yz, material, bevel=0.006):
    verts = [(_px(x0), y, z) for y,z in yz] + [(_px(x1), y,z) for y,z in yz]
    n=len(yz)
    faces=[tuple(range(n-1,-1,-1)), tuple(range(n,n*2))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return _mesh(name,verts,faces,material,bevel)


def _cylinder(name, loc, radius, length, axis, material, vertices=20, bevel=0.005):
    rotation = (0,math.pi/2,0) if axis=='X' else (math.pi/2,0,0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length,
                                        end_fill_type='NGON', location=loc, rotation=rotation)
    obj=bpy.context.object
    obj.name=name
    _link(obj,material)
    _bevel(obj,bevel,1,True)
    return obj


def _revolve_x(name, profile, zcenter, material, sides=24, cap=True):
    """Profile of exterior decorative barrel sleeves, with scene-unit radii."""
    verts=[]
    for x,r in profile:
        for i in range(sides):
            angle=2*math.pi*i/sides
            verts.append((_px(x), math.cos(angle)*r, zcenter+math.sin(angle)*r))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(sides):
            ni=(i+1)%sides
            faces.append((j*sides+i,j*sides+ni,(j+1)*sides+ni,(j+1)*sides+i))
    if cap:
        if cap != 'BACK':
            faces.append(tuple(range(sides-1,-1,-1)))
        last=(len(profile)-1)*sides
        faces.append(tuple(last+i for i in range(sides)))
    return _mesh(name,verts,faces,material,0.0015,True)


def _perforated_band(name, xleft, xright, top_px, bottom_px, holes, side, material):
    """Thin exterior side wall with actual stadium cutouts, without Boolean debris."""
    top,bottom=_pz(top_px),_pz(bottom_px)
    center=(top+bottom)/2
    # Slots are (left pixel, right pixel, height pixels).
    samples=[(_px(xleft),center,center,False)]
    intervals=[]
    for left,right,height in holes:
        radius=height/160.0
        l=_px(left)+radius
        r=_px(right)-radius
        start=_px(left)
        if samples[-1][0] < start-1e-6:
            samples.append((start,center,center,False))
            intervals.append(False)
        # Increasing X stations on two semicircle ends, with the straight middle.
        stations=[]
        for j in range(7):
            a=math.pi-(math.pi/2)*j/6
            stations.append((l+radius*math.cos(a),center+radius*math.sin(a),center-radius*math.sin(a)))
        stations.append((r,center+radius,center-radius))
        for j in range(1,7):
            a=math.pi/2-(math.pi/2)*j/6
            stations.append((r+radius*math.cos(a),center+radius*math.sin(a),center-radius*math.sin(a)))
        # Replace the first endpoint to keep watertight strips.
        samples[-1]=(stations[0][0],center,center,False)
        for station in stations[1:]:
            samples.append((*station,True))
            intervals.append(True)
    if samples[-1][0] < _px(xright)-1e-6:
        samples.append((_px(xright),center,center,False))
        intervals.append(False)
    outer=side*.284
    inner=side*.250
    verts=[]
    index={}
    faces=[]
    def vi(co):
        key=tuple(round(v,7) for v in co)
        if key not in index:
            index[key]=len(verts)
            verts.append(co)
        return index[key]
    def face(coords):
        ids=[]
        for c in coords:
            v=vi(c)
            if not ids or ids[-1]!=v:
                ids.append(v)
        if len(ids)>2 and ids[0]==ids[-1]:
            ids.pop()
        if len(set(ids))>=3:
            faces.append(tuple(ids))
    for j in range(len(samples)-1):
        a,b=samples[j],samples[j+1]
        xa,ua,la,_=a
        xb,ub,lb,_=b
        for yy in (outer,inner):
            face([(xa,yy,top),(xb,yy,top),(xb,yy,ub),(xa,yy,ua)])
            face([(xa,yy,la),(xb,yy,lb),(xb,yy,bottom),(xa,yy,bottom)])
        face([(xa,inner,top),(xb,inner,top),(xb,outer,top),(xa,outer,top)])
        face([(xa,inner,bottom),(xb,inner,bottom),(xb,outer,bottom),(xa,outer,bottom)])
        if intervals[j]:
            face([(xa,outer,ua),(xb,outer,ub),(xb,inner,ub),(xa,inner,ua)])
            face([(xa,outer,la),(xb,outer,lb),(xb,inner,lb),(xa,inner,la)])
    for s in (samples[0],samples[-1]):
        x,u,l,_=s
        face([(x,outer,top),(x,inner,top),(x,inner,center),(x,outer,center)])
        face([(x,outer,center),(x,inner,center),(x,inner,bottom),(x,outer,bottom)])
    return _mesh(name,verts,faces,material,0.0,False)


def _end_ring(name, px, thickness, material):
    zcenter=_pz(101)
    # An eight-sided shell rim, open around the visually exposed barrel.
    outside=[(-.20,_pz(75)),(.20,_pz(75)),(.284,_pz(84)),(.284,_pz(117)),
             (.19,_pz(126)),(-.19,_pz(126)),(-.284,_pz(117)),(-.284,_pz(84))]
    inside=[]
    for y,z in outside:
        direction=Vector((y,z-zcenter)).normalized()
        inside.append((direction.x*.17,zcenter+direction.y*.17))
    verts=[]
    for x in (_px(px),_px(px)+thickness):
        verts += [(x,y,z) for y,z in outside] + [(x,y,z) for y,z in inside]
    n=8
    faces=[]
    for i in range(n):
        k=(i+1)%n
        faces += [(i,k,n+k,n+i),(16+i,16+k,24+k,24+i),
                  (i,k,16+k,16+i),(n+i,n+k,24+k,24+i)]
    return _mesh(name,verts,faces,material,.004)


def _rail(name, x0, x1, material):
    # The upper silhouette's continuous base and narrow transverse ridges.
    yz=[(-.148,_pz(75)),(.148,_pz(75)),(.170,_pz(71)),(.170,_pz(68)),
        (-.170,_pz(68)),(-.170,_pz(71))]
    _cross_extrude(name+'_Base',x0,x1,yz,material,.003)
    n=math.floor((x1-x0)/10.5)
    for i in range(n+1):
        x=x0+3.0+i*10.5
        if x+6.0>x1:
            continue
        # Low teeth: the original has a fine comb rather than giant raised blocks.
        _box(name+f'_Tooth_{i:02}',(_px(x+2.8),0,_pz(66.45)),(.070,.340,.029),material,.003)


def _screw(name, px, pz, side, material, dark, radius=.026):
    y=side*.344
    _cylinder(name,(_px(px),y,_pz(pz)),radius,.010,'Y',material,16,.002)
    _cylinder(name+'_Socket',(_px(px),y+side*.006,_pz(pz)),radius*.38,.002,'Y',dark,6,0)


# Art-space gameplay alignment. These are visual coordinates, not weapon specifications.
ADS_LINE_Z = 1.48
ADS_FRONT_X = (137.0 - 349.0) / 80.0
ADS_REAR_X = (402.7 - 349.0) / 80.0


def _rounded_yz_loop(half_width, half_height, radius, zcenter, corner_segments=6):
    loop=[]
    for cy,cz,start in ((half_width-radius,half_height-radius,0),
                        (-half_width+radius,half_height-radius,90),
                        (-half_width+radius,-half_height+radius,180),
                        (half_width-radius,-half_height+radius,270)):
        for j in range(corner_segments+1):
            angle=math.radians(start+90*j/corner_segments)
            loop.append((cy+radius*math.cos(angle),zcenter+cz+radius*math.sin(angle)))
    return loop


def _open_sight_frame(name,xcenter,material):
    # A thin, genuinely empty rounded-rectangle frame in the viewing YZ plane.
    # The opening has no transparent fill, crossbar, lens, or hidden center panel.
    outer=_rounded_yz_loop(.166,.152,.061,ADS_LINE_Z)
    inner=_rounded_yz_loop(.147,.132,.043,ADS_LINE_Z)
    n=len(outer)
    verts=[]
    for x in (xcenter-.034,xcenter+.034):
        verts.extend((x,y,z) for y,z in outer)
        verts.extend((x,y,z) for y,z in inner)
    faces=[]
    for i in range(n):
        k=(i+1)%n
        faces.extend(((i,k,n+k,n+i),
                      (2*n+i,2*n+k,3*n+k,3*n+i),
                      (i,k,2*n+k,2*n+i),
                      (n+i,n+k,3*n+k,3*n+i)))
    return _mesh(name,verts,faces,material,.0025,False)


def _visual_muzzle_mouth(zcenter,black,recess,steel):
    # A bevelled exterior lip and shallow closed shadow cup create the open look.
    # Nothing continues into the barrel or models a working internal component.
    sides=24
    rings=[(31.0,.113),(30.96,.088),(32.0,.079),(36.0,.075)]
    verts=[]
    for x,r in rings:
        for i in range(sides):
            a=2*math.pi*i/sides
            verts.append((_px(x),math.cos(a)*r,zcenter+math.sin(a)*r))
    faces=[]
    indices=[]
    for j in range(len(rings)-1):
        for i in range(sides):
            ni=(i+1)%sides
            faces.append((j*sides+i,j*sides+ni,(j+1)*sides+ni,(j+1)*sides+i))
            indices.append(0 if j==0 else (2 if j==1 else 1))
    faces.append(tuple((len(rings)-1)*sides+i for i in range(sides)))
    indices.append(1)
    mouth=_mesh('Muzzle_Open_Looking_Mouth',verts,faces,black,0,False)
    mouth.data.materials.append(recess)
    mouth.data.materials.append(steel)
    for p,index in zip(mouth.data.polygons,indices):
        p.material_index=index
        p.use_smooth=index != 0
    return mouth


def build():
    global _COLLECTION,_OBJECTS
    _OBJECTS=[]
    _COLLECTION=bpy.data.collections.get('Foreend')
    if _COLLECTION is None:
        _COLLECTION=bpy.data.collections.new('Foreend')
        bpy.context.scene.collection.children.link(_COLLECTION)
    black=_mat('Anodized_Black',(.028,.032,.038,1),.72,.38)
    polymer=_mat('Polymer_Charcoal',(.022,.026,.030,1),0,.55)
    recess=_mat('Recess_Black',(.006,.008,.010,1),.35,.6)
    steel=_mat('Edge_Steel',(.060,.066,.070,1),.85,.3)
    ribs=_mat('Foreend_Rib_Shade',(.017,.021,.025,1),0,.58)
    sight_tip=_mat('Sight_Tip_Pale_Ivory',(.72,.76,.63,1),0,.44)
    rear_marks=_mat('Sight_Reference_Subtle_Ivory',(.34,.38,.32,1),0,.50)
    muzzle_shadow=_mat('Muzzle_Shadow_Cup',(.001,.002,.003,1),0,.98)
    shader=muzzle_shadow.node_tree.nodes.get('Principled BSDF')
    if shader and 'Specular IOR Level' in shader.inputs:
        shader.inputs['Specular IOR Level'].default_value=.02

    # The roof/floor and rims form a closed exterior tube with honest open vents.
    _cross_extrude('HG_Top_Shoulder',149,302,
        [(-.20,_pz(75)),(.20,_pz(75)),(.281,_pz(78)),(.281,_pz(77)),
         (.20,_pz(73)),(-.20,_pz(73)),(-.281,_pz(77)),(-.281,_pz(78))],black,.003)
    _cross_extrude('HG_Bottom_Chamfer',150,302,
        [(-.282,_pz(123)),(-.19,_pz(126)),(.19,_pz(126)),(.282,_pz(123)),
         (.252,_pz(121)),(.17,_pz(124)),(-.17,_pz(124)),(-.252,_pz(121))],black,.003)
    _end_ring('HG_Front_Rim',149,.048,black)
    _end_ring('HG_Rear_Rim',299,.038,black)
    _box('HG_Visual_Shadow_Liner',(_px(225),0,_pz(100)),(1.79,.395,.590),recess,0)
    top_slots=[(164,185,5.2),(191,213,5.2),(219,237,5.2),(242,256,5.2),(262,281,5.2)]
    low_slots=[(164,187,5),(192,219,5),(224,251,5),(256,282,5)]
    for side,label in ((-1,'L'),(1,'R')):
        _perforated_band('HG_Upper_Vented_Wall_'+label,151,300,76,88,top_slots,side,steel)
        _perforated_band('HG_Lower_Vented_Wall_'+label,153,299,112,124,low_slots,side,black)
        _prism_px('HG_Ribbed_Rail_Cover_'+label,
            [(152,89),(157,87),(296,87),(300,91),(300,110),(297,112),(156,112),(152,109)],
            side*.288,side*.333,polymer,.009)
        # Narrow valleys give the wide fitted covers their restrained rib rhythm.
        for i in range(19):
            px=162+i*6.65
            height=17.4 if i%3 else 18.8
            _box('HG_Cover_Valley_'+label+f'_{i:02}',
                 (_px(px),side*.334,_pz(99.7)),(.015,.007,height/80),ribs,0)
            # A small raised shoulder beside every valley catches soft edge light.
            _box('HG_Cover_Rib_'+label+f'_{i:02}',
                 (_px(px+1.55),side*.336,_pz(99.7)),(.016,.008,(height-1.0)/80),polymer,.003)
        _screw('HG_Cover_Rear_Fastener_'+label,292.0,100.3,side,steel,recess,.032)
        for j in range(3):
            _box('HG_Cover_Front_Dimple_'+label+str(j),
                (_px(157.1),side*.334,_pz(95+j*4)),(.028,.006,.019),recess,.004)
    # Serrated lower-edge silhouette, kept subdued in the source image.
    for i in range(14):
        x=153+i*10.5
        _box('HG_Lower_Rail_Tooth_'+str(i),(_px(x+3.7),0,_pz(125.5)),
             (.092,.375,.038),black,.004)
    _rail('Top_Picatinny',151,475,black)

    # Exterior barrel, clamp rings and a short stepped muzzle device.
    z=_pz(101.5)
    _revolve_x('Exposed_Barrel',[(80,.087),(118,.087),(120,.101),(151,.101)],z,black,24)
    _revolve_x('Front_Clamp_Lower_Rings',[(119,.157),(122,.165),(131,.165),
                                        (133,.147),(140,.147),(142,.165),(149,.165)],z,black,24)
    muzzle = _revolve_x('Muzzle_Device_Exterior',[(31,.113),(32,.134),(35,.140),
                                        (60,.140),(65,.128),(71,.128),(72,.143),(75,.143)],z,black,24,cap='BACK')
    _revolve_x('Muzzle_Rear_Collar',[(76,.124),(77,.148),(81,.148),(83,.129)],z,black,24)
    _visual_muzzle_mouth(z,black,muzzle_shadow,steel)
    # Shallow cosmetic side cuts with genuine lips and dark back faces.
    for side,label in ((-1,'L'),(1,'R')):
        # A shallow side-pocket gives the visible black notch a real lip.
        cutter = _box('Temporary_Muzzle_Recess_Cutter_'+label,
                      (_px(46.5),side*.158,_pz(98)),(.245,.108,.062),None,.015,2)
        bpy.context.view_layer.objects.active = cutter
        cutter.select_set(True)
        for modifier in tuple(cutter.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.context.view_layer.objects.active = muzzle
        pocket = muzzle.modifiers.new('Shallow exterior side notch '+label,'BOOLEAN')
        pocket.operation = 'DIFFERENCE'
        pocket.solver = 'EXACT'
        pocket.object = cutter
        # Put the notch ahead of the edge bevel for a small readable recess lip.
        bpy.ops.object.modifier_move_up(modifier=pocket.name)
        bpy.ops.object.modifier_move_up(modifier=pocket.name)
        bpy.ops.object.modifier_apply(modifier=pocket.name)
        _OBJECTS.remove(cutter)
        bpy.data.objects.remove(cutter,do_unlink=True)
        _box('Muzzle_Side_Recess_'+label,(_px(46.5),side*.107,_pz(98)),
             (.224,.002,.047),recess,.010,1)
    _revolve_x('Muzzle_Collar_Separator',[(72.8,.145),(74.4,.145)],z,recess,24)

    # Front aiming assembly: a separate narrow center post and two open wings.
    _prism_px('Front_Sight_Pedestal',[(120,88),(120,75),(124,71),(143,71),
                                     (148,76),(148,89),(143,92),(123,92)],
              -.173,.173,black,.008)
    # The base is entirely below the aiming line and joins the existing mount.
    _box('Front_Sight_Open_Head_Base',(ADS_FRONT_X,0,1.335),(.123,.353,.032),black,.005)
    post_profile=[(-.014,1.348),(.014,1.348),(.012,ADS_LINE_Z),(-.012,ADS_LINE_Z)]
    _cross_extrude('Front_Sight_Slim_Aiming_Post',134.75,139.25,post_profile,black,.0015)
    # Painted upper rear face, legible from the player's view but small in silhouette.
    _box('Front_Sight_Pale_Tip',(ADS_FRONT_X+.033,0,ADS_LINE_Z-.012),
         (.010,.023,.024),sight_tip,.001)
    wing_profile=[(.119,1.335),(.112,1.401),(.125,1.497),(.154,1.571),
                  (.180,1.568),(.168,1.487),(.154,1.393),(.162,1.335)]
    for side,label in ((-1,'L'),(1,'R')):
        profile=[(side*y,zp) for y,zp in wing_profile]
        _cross_extrude('Front_Sight_Separated_Wing_'+label,132.7,141.3,profile,black,.003)
        _cylinder('Front_Sight_Hinge_'+label,(_px(137),side*.180,_pz(80.5)),.057,.014,'Y',steel,20,.003)
        _cylinder('Front_Sight_Hinge_Socket_'+label,(_px(137),side*.190,_pz(80.5)),.021,.005,'Y',recess,6,.001)
    _box('Front_Sight_Clamp_Gap',(_px(134.0),-.172,_pz(92)),(.18,.01,.022),recess,.002)

    # Rear aiming assembly: thin actual negative-space aperture, with a lowered base.
    # Clear inside dimensions: .294 wide and .264 high at art-space z=1.48.
    _prism_px('Rear_Sight_Low_Base',[(393,74),(393,67),(397,64.2),(430,64.2),
                                   (443,66),(443,70),(437,73),(431,74)],
              -.161,.161,black,.006)
    _open_sight_frame('Rear_Sight_Open_Aperture_Frame',ADS_REAR_X,black)
    _box('Rear_Sight_Frame_Foot',(ADS_REAR_X,0,1.329),(.097,.175,.029),black,.004)
    _box('Rear_Sight_Forward_Arm',(_px(424.7),0,1.329),(.395,.257,.035),black,.003)
    for side,label in ((-1,'L'),(1,'R')):
        # Two quiet marks sit on the frame, outside the genuinely clear opening.
        _box('Rear_Sight_Aperture_Reference_'+label,
             (ADS_REAR_X+.039,side*.158,ADS_LINE_Z),(.008,.010,.025),rear_marks,.001)
        _cylinder('Rear_Sight_Hinge_'+label,(_px(402.7),side*.166,_pz(68.4)),.055,.015,'Y',black,20,.003)
        _cylinder('Rear_Sight_Hinge_Center_'+label,(_px(402.7),side*.177,_pz(68.4)),.020,.005,'Y',steel,16,.001)
        _cylinder('Rear_Sight_Adjustment_'+label,(_px(432),side*.166,_pz(68)),.032,.022,'Y',black,16,.003)
        _cylinder('Rear_Sight_Adjustment_Socket_'+label,(_px(432),side*.182,_pz(68)),.012,.003,'Y',recess,6,0)
    return list(_OBJECTS)
