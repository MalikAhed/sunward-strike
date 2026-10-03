"""Source-faithful exterior receiver and animated game controls.
Art coordinates are traced from the supplied side photograph. No internal mechanisms.
"""
import bpy
import math
from mathutils import Vector

PX_ORIGIN_X = 349.0
PX_ORIGIN_Z = 171.0
PX_SCALE = 80.0


def get_mat(name, color, metallic, roughness):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = color
        bsdf.inputs['Metallic'].default_value = metallic
        bsdf.inputs['Roughness'].default_value = roughness
        mat.diffuse_color = color
    return mat


def _xz(p):
    return ((p[0] - PX_ORIGIN_X) / PX_SCALE,
            (PX_ORIGIN_Z - p[1]) / PX_SCALE)


def _position(px, py, y=0.0):
    x, z = _xz((px, py))
    return (x, y, z)


_OBJECTS = []
_COLLECTION = None


def _place(obj, mat=None, parent=None, bevel=0.0, segments=2):
    if _COLLECTION is not None:
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        _COLLECTION.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    if bevel > 0.0:
        mod = obj.modifiers.new('Small edge chamfers', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.affect = 'EDGES'
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(28)
        mod.harden_normals = True
        mod.profile = .5
        mod.use_clamp_overlap = True
        weighted = obj.modifiers.new('Face-weighted normals', 'WEIGHTED_NORMAL')
        weighted.keep_sharp = True
        weighted.weight = 45
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    obj['asset_part'] = 'exterior receiver/control'
    _OBJECTS.append(obj)
    return obj


def _poly(name, points, y0, y1, mat, bevel=0.018, parent=None):
    n = len(points)
    verts = []
    for y in (y0, y1):
        verts.extend([(x, y, z) for x, z in map(_xz, points)])
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    faces.extend([(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)])
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return _place(obj, mat, parent, bevel, segments=1 if bevel <= .018 else 2)


def _ring(name, outer, inner, y0, y1, mat, bevel=0.01):
    assert len(outer) == len(inner)
    n = len(outer)
    verts = []
    for y in (y0, y1):
        verts.extend([(x, y, z) for x, z in map(_xz, outer)])
        verts.extend([(x, y, z) for x, z in map(_xz, inner)])
    faces = []
    for i in range(n):
        j = (i+1) % n
        # Front/back face rings, followed by exterior/interior walls.
        faces.extend([(i, n+i, n+j, j),
                      (2*n+i, 2*n+j, 3*n+j, 3*n+i),
                      (i, j, 2*n+j, 2*n+i),
                      (n+j, n+i, 3*n+i, 3*n+j)])
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return _place(obj, mat, bevel=bevel)


def _disc(name, pixel, radius_px, y, depth, mat, parent=None, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius_px/PX_SCALE,
        depth=depth, end_fill_type='NGON', location=_position(*pixel, y),
        rotation=(math.pi/2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return _place(obj, mat, parent, bevel=min(.006, depth/4), segments=1)


def _ctrl(name, pivot):
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = 'PLAIN_AXES'
        obj.empty_display_size = .18
        bpy.context.collection.objects.link(obj)
        obj.location = _position(*pivot)
        if _COLLECTION is not None:
            for coll in list(obj.users_collection):
                coll.objects.unlink(obj)
            _COLLECTION.objects.link(obj)
    bpy.context.view_layer.update()
    obj['game_animation_control'] = True
    _OBJECTS.append(obj)
    return obj


def _mag_strip(name, rows, fraction, width_px, y0, y1, mat, parent):
    left = []
    right = []
    for py, xl, xr in rows:
        x = xl + (xr-xl)*fraction
        left.append((x-width_px/2, py))
        right.append((x+width_px/2, py))
    return _poly(name, left+list(reversed(right)), y0, y1, mat,
                 bevel=.006, parent=parent)


def build():
    global _OBJECTS, _COLLECTION
    _OBJECTS = []
    _COLLECTION = bpy.data.collections.get('Receiver_Exterior')
    if _COLLECTION is None:
        _COLLECTION = bpy.data.collections.new('Receiver_Exterior')
        bpy.context.scene.collection.children.link(_COLLECTION)
    black = get_mat('Anodized_Black', (.028,.032,.038,1), .72, .38)
    polymer = get_mat('Polymer_Charcoal', (.022,.026,.030,1), 0, .55)
    recess = get_mat('Recess_Black', (.006,.008,.010,1), .35, .6)
    steel = get_mat('Edge_Steel', (.060,.066,.070,1), .85, .3)
    # Large sculpted upper body: forward square shoulder, smooth sloping rear.
    upper = [(298,76),(448,76),(459,78),(467,81),(482,81),(490,86),
             (491,122),(486,130),(468,134),(459,132),(321,130),
             (308,127),(301,124),(298,120)]
    _poly('Receiver_Upper_Sculpted', upper, -.235, .235, black, .034)
    # Narrow upper side crown catches the horizontal source highlight.
    side_crown = [(300,84),(449,84),(463,85),(477,88),(477,96),
                  (466,101),(310,101),(300,98)]
    for side in (-1,1):
        ya, yb = sorted((side*.2345, side*.2405))
        _poly('Upper_Crown_' + ('L' if side<0 else 'R'), side_crown,
              ya, yb, black, .004)
        _poly('Upper_Lower_Edge_' + ('L' if side<0 else 'R'),
              [(305,107),(460,107),(467,110),(460,113),(309,113),(305,111)],
              *sorted((side*.2345, side*.2385)), black, .002)
    # Receiver bottom outline leaves the actual trigger opening clear.
    lower = [(304,114),(468,114),(479,119),(483,126),(478,132),
             (471,135),(466,142),(465,151),(468,159),(447,168),
             (437,163),(432,156),(433,145),(380,145),(376,174),
             (366,172),(369,137),(354,135),(350,128),(305,127)]
    _poly('Receiver_Lower_Sculpted', lower, -.231, .231, black, .026)
    magwell = [(307,115),(367,115),(376,121),(376,172),(370,174),
               (310,164),(313,145),(312,133),(307,127)]
    _poly('Magwell_Flared', magwell, -.258, .258, black, .025)
    _poly('Magwell_Base_Lip', [(311,159),(376,169),(376,176),(310,167)],
          -.272, .272, black, .015)
    # Tapered reliefs on both sides preserve the source's compact contours.
    well_panel = [(316,118),(344,118),(349,122),(349,157),(344,164),
                  (316,159),(318,145),(317,132)]
    for side in (-1,1):
        y0, y1 = sorted((side*.258, side*.263))
        _poly('Magwell_Side_Panel_' + ('L' if side<0 else 'R'),
              well_panel, y0, y1, black, .008)
    # Lower-receiver fences and exterior controls seen from the reference side.
    _poly('Bolt_Catch_Base_L', [(351,128),(372,126),(378,130),(378,136),
                              (353,137),(350,134)], -.278,-.262, black, .008)
    _poly('Bolt_Catch_Lever_L', [(378,114),(382,117),(383,127),(387,130),
                               (384,135),(378,133),(377,125)],
          -.299,-.268, black, .009)
    _disc('Bolt_Catch_Pivot_L',(380,110),4.4,-.264,.026,black)
    _disc('Bolt_Catch_Pivot_Center_L',(380,110),2.3,-.280,.011,recess,vertices=16)
    _poly('Receiver_Fence_L', [(351,118),(354,118),(354,154),(351,154)],
          -.278,-.264, black, .006)
    _poly('Receiver_Fence_Low_L', [(353,153),(372,156),(372,161),(352,157)],
          -.278,-.264, black, .006)
    for side in (-1,1):
        suffix = 'L' if side<0 else 'R'
        _disc('Receiver_Front_Pin_'+suffix,(307,120),3.5,side*.248,.024,black)
        _disc('Receiver_Front_Pin_Center_'+suffix,(307,120),1.6,side*.263,.007,recess,vertices=12)
        _disc('Receiver_Rear_Pin_'+suffix,(459,120),3.2,side*.248,.024,black)
        _disc('Receiver_Rear_Pin_Center_'+suffix,(459,120),1.4,side*.263,.007,recess,vertices=12)
        _disc('Trigger_Pin_'+suffix,(414,136),2.0,side*.246,.015,black,vertices=16)
    _disc('Selector_Hub_L',(439,129),5.1,-.251,.027,black)
    _poly('Selector_Lever_L', [(438,126),(451,126),(455,129),(452,133),
                             (439,132),(436,130)], -.284,-.258,black,.010)
    _disc('Selector_Center_L',(439,129),2.0,-.287,.010,steel,vertices=16)
    # Shallow decorative ticks are deliberately non-legible and logo-free.
    _poly('Selector_Tick_Forward',[(426,125),(429,125),(429,126),(426,126)],
          -.244,-.241,steel,0)
    _poly('Selector_Tick_Upper',[(438,117),(439,117),(439,120),(438,120)],
          -.244,-.241,steel,0)
    # Hollow rounded trigger guard, its walls are actual exterior geometry.
    guard_outer = [(375,142),(427,142),(433,148),(433,165),(429,174),
                   (420,179),(385,178),(377,173),(373,165),(373,148)]
    guard_inner = [(384,147),(423,147),(428,151),(428,164),(424,170),
                   (418,173),(386,173),(381,169),(379,163),(379,151)]
    _ring('Trigger_Guard_Rounded', guard_outer, guard_inner, -.182,.182,
          black,.014)
    trigger_ctrl = _ctrl('Trigger_CTRL',(411,145))
    trigger_ctrl['allowed_motion'] = 'small cosmetic hinge rotation for game animation'
    trigger_shape = [(406,142),(414,143),(418,149),(418,155),
                     (414,163),(409,170),(405,171),(407,165),
                     (411,158),(412,151),(409,147),(406,146)]
    _poly('Trigger_Curved',trigger_shape,-.085,.085,black,.008,trigger_ctrl)
    # Swept, slanted polymer grip has a sculpted throat and flared heel.
    grip_ctrl = _ctrl('PistolGrip_CTRL',(447,158))
    grip_shape = [(441,145),(456,144),(467,153),(475,169),(489,192),
                  (505,216),(506,225),(465,243),(457,241),(455,237),
                  (459,230),(449,207),(441,189),(439,180),(432,177),
                  (434,166),(438,158)]
    _poly('Pistol_Grip_Sculpted',grip_shape,-.2,.2,polymer,.032,grip_ctrl)
    grip_panel = [(444,164),(460,160),(470,173),(482,194),(496,215),
                  (497,222),(467,235),(462,225),(453,205),(444,186),(440,179)]
    for side in (-1,1):
        _poly('Grip_Recessed_Panel_'+('L' if side<0 else 'R'),grip_panel,
              *sorted((side*.200,side*.206)),polymer,.015,grip_ctrl)
    _poly('Grip_Heel_Base',[(458,232),(500,216),(506,220),(506,227),
                          (466,244),(457,241),(455,237)],
          -.212,.212,polymer,.018,grip_ctrl)
    # Faint molded texture strips along the front edge, restrained like source.
    for side in (-1,1):
        for k in range(6):
            py = 190 + 5.0*k
            px = 442 + (py-190)*.43
            _poly('Grip_Mold_Accent_%s_%02d'%('L' if side<0 else 'R',k),
                  [(px,py),(px+4,py-1.6),(px+4.7,py-.4),(px+.7,py+1.2)],
                  *sorted((side*.202,side*.209)),recess,.002,grip_ctrl)
    # Curved magazine body. Longitudinal ribs and seam bands follow its sweep.
    magazine_ctrl = _ctrl('Magazine_CTRL',(342,170))
    magazine_ctrl['allowed_motion'] = 'translate for reload animation; visual exterior only'
    mag_shape = [(316,166),(370,174),(370,183),(367,200),(363,216),
                 (357,235),(350,254),(342,276),(339,280),(290,266),
                 (289,262),(295,243),(302,223),(307,205),(312,185)]
    _poly('Magazine_Curved_Body',mag_shape,-.160,.160,polymer,.024,magazine_ctrl)
    rows = [(176,315,369),(198,309,366),(222,302,361),
            (244,295,354),(266,289.5,345)]
    for side in (-1,1):
        ya,yb = sorted((side*.1595,side*.166))
        for j,frac in enumerate((.15,.48,.81)):
            _mag_strip('Magazine_Long_Rib_%s_%d'%('L' if side<0 else 'R',j),
                       rows,frac,2.4,ya,yb,polymer,magazine_ctrl)
        # Transverse panel borders are separate restrained chamfered ridges.
        for j,(py,xl,xr) in enumerate(rows[1:-1]):
            # Stop each molding strip well inside the curved silhouette.
            # Their shallow relief should read as surface seams, not fins.
            band=[(xl+4,py-.6),(xr-4,py+3),
                  (xr-4.5,py+4.3),(xl+3.5,py+.7)]
            _poly('Magazine_Cross_Rib_%s_%d'%('L' if side<0 else 'R',j),
                  band,*sorted((side*.1595,side*.1645)),polymer,.002,magazine_ctrl)
        _poly('Magazine_Edge_Seam_'+('L' if side<0 else 'R'),
              [(316,176),(311,198),(304,220),(297,243),(290,264),
               (292,265),(299,243),(306,220),(313,199),(318,176)],
              *sorted((side*.160,side*.168)),recess,.004,magazine_ctrl)
    _poly('Magazine_Base_Plate',[(289,258),(345,274),(343,281),
                                 (340,284),(288,270),(287,266)],
          -.180,.180,black,.016,magazine_ctrl)
    _poly('Magazine_Base_Edge',[(290,264),(340,278),(340,282),(289,269)],
          -.185,-.178,steel,.005,magazine_ctrl)
    # Exterior-only charging latch assembly. It retracts rearward as one group.
    charging = _ctrl('ChargingHandle_CTRL',(464,78))
    charging['allowed_motion'] = 'cosmetic rearward slide along +X'
    _poly('Charging_Handle_Rear_Crown',[(447,72),(463,72),(475,74),
              (480,77),(480,81),(465,83),(447,81)],
          -.146,.146,black,.017,charging)
    for side in (-1,1):
        _poly('Charging_Handle_Latch_'+('L' if side<0 else 'R'),
              [(460,75),(474,74),(481,76),(481,80),(474,82),(460,80)],
              *sorted((side*.135,side*.275)),black,.014,charging)
        _poly('Charging_Latch_Top_Ridge_'+('L' if side<0 else 'R'),
              [(463,75),(477,76),(477,78),(463,77)],
              *sorted((side*.270,side*.279)),steel,.003,charging)
    # The unseen side is interpreted as a shallow cosmetic port and slide.
    _poly('Opposite_Port_Recess_Visual',[(328,87),(450,87),(455,91),
               (455,104),(328,104),(324,100),(324,91)],
          .236,.245,recess,.012)
    bolt = _ctrl('BoltVisual_CTRL',(392,96))
    bolt['allowed_motion'] = 'shallow exterior cosmetic slide along +X'
    _poly('Bolt_Visual_Slide',[(333,90),(446,90),(450,94),(450,101),
                             (333,101),(330,98),(330,94)],
          .245,.252,steel,.006,bolt)
    _poly('Bolt_Visual_Dark_Seam',[(342,94),(440,94),(440,96),(342,96)],
          .252,.254,black,.002,bolt)
    _poly('Opposite_Port_Lower_Lip',[(325,105),(456,105),(456,109),(325,109)],
          .235,.262,black,.007)
    # Use the side's same sober finish; no engraved brands or readable text.
    bpy.context.view_layer.update()
    return list(_OBJECTS)
