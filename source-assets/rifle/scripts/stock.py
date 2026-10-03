"""Exterior stock for a source-matched game prop. Arbitrary image-space units.
No mechanical internals. The narrow side slot is a visual through-opening.
"""
import bpy
from math import cos, sin, pi

_CREATED = []
_COL = None


def _mat(name, color, metallic=0.0, roughness=0.55):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = color
        p.inputs['Metallic'].default_value = metallic
        p.inputs['Roughness'].default_value = roughness
        m.diffuse_color = color
    return m


def _xz(p):
    return ((p[0] - 349.0) / 80.0, (171.0 - p[1]) / 80.0)


def _mesh(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name + '_Mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _COL.objects.link(obj)
    if material is not None:
        mesh.materials.append(material)
    _CREATED.append(obj)
    return obj


def _bevel(obj, width=0.015, segments=2):
    if width:
        mod = obj.modifiers.new('Soft polymer edge', 'BEVEL')
        mod.width = width
        mod.segments = segments
        mod.affect = 'EDGES'
        mod.use_clamp_overlap = True
        mod.harden_normals = True
    normal = obj.modifiers.new('Weighted edge normals', 'WEIGHTED_NORMAL')
    normal.keep_sharp = True
    normal.weight = 35
    return obj


def _profile(name, pixels, y_min, y_max, material, bevel=0.014, segments=2):
    points = [_xz(p) for p in pixels]
    # CCW in XZ guarantees outward-facing front (-Y), back, and side walls.
    area = sum(points[i][0] * points[(i + 1) % len(points)][1]
               - points[(i + 1) % len(points)][0] * points[i][1]
               for i in range(len(points)))
    if area < 0:
        points.reverse()
    n = len(points)
    verts = [(x, y_min, z) for x, z in points] + [(x, y_max, z) for x, z in points]
    faces = [tuple(range(n)), tuple(range(2*n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, n + i, n + j, j))
    obj = _mesh(name, verts, faces, material)
    if bevel:
        _bevel(obj, bevel, segments)
    return obj


def _box(name, center, dimensions, material, bevel=0.01, segments=2):
    x, y, z = center
    a, b, c = [v / 2 for v in dimensions]
    verts = [(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
             (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
    faces = [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    obj = _mesh(name, verts, faces, material)
    _bevel(obj, bevel, segments)
    return obj


def _cyl_x(name, x1, x2, pixel_z, radius, material, sides=24, bevel=0.006):
    z = (171 - pixel_z) / 80
    a, b = (x1 - 349) / 80, (x2 - 349) / 80
    verts = []
    for x in (a, b):
        verts.extend((x, radius*cos(2*pi*i/sides), z+radius*sin(2*pi*i/sides))
                     for i in range(sides))
    faces = [tuple(range(sides-1,-1,-1)), tuple(range(sides,2*sides))]
    faces.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
    obj = _mesh(name, verts, faces, material)
    for poly in obj.data.polygons[2:]:
        poly.use_smooth = True
    _bevel(obj, bevel, 1)
    return obj


def _pin(name, px, pz, side_y, radius, material, sides=12):
    x, z = _xz((px, pz))
    # Low-poly shallow discs on the visible side, with flat recessed centers.
    depth = 0.006
    a, b = side_y, side_y + (depth if side_y < 0 else -depth)
    verts = []
    for y in (a, b):
        verts.extend((x+radius*cos(2*pi*i/sides), y, z+radius*sin(2*pi*i/sides))
                     for i in range(sides))
    faces = [tuple(range(sides-1,-1,-1)),tuple(range(sides,2*sides))]
    faces.extend((i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides))
    obj = _mesh(name, verts, faces, material)
    # Pins stay flat-shaded; silhouette is below two pixels in the full asset.
    return obj


def _capsule_pixels(left, right, top, bottom, count=6):
    radius = (bottom-top)/2
    cy = (top+bottom)/2
    pts = []
    for i in range(count+1):
        ang = -pi/2+pi*i/count
        pts.append((right-radius+radius*cos(ang), cy+radius*sin(ang)))
    for i in range(count+1):
        ang = pi/2+pi*i/count
        pts.append((left+radius+radius*cos(ang), cy+radius*sin(ang)))
    return pts


def _uv(obj):
    if obj.type != 'MESH':
        return
    mesh = obj.data
    layer = mesh.uv_layers.new(name='UVMap') if not mesh.uv_layers else mesh.uv_layers.active
    verts = [v.co for v in mesh.vertices]
    mins = [min(v[a] for v in verts) for a in range(3)]
    spans = [max(v[a] for v in verts)-mins[a] or 1 for a in range(3)]
    for poly in mesh.polygons:
        normal = poly.normal
        drop = max(range(3), key=lambda a: abs(normal[a]))
        axes = [a for a in range(3) if a != drop]
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            layer.data[li].uv = tuple((co[a]-mins[a])/spans[a] for a in axes)


def build():
    global _CREATED, _COL
    _CREATED = []
    _COL = bpy.data.collections.get('Rifle_Stock')
    if _COL is None:
        _COL = bpy.data.collections.new('Rifle_Stock')
        bpy.context.scene.collection.children.link(_COL)
    metal = _mat('Anodized_Black', (.028,.032,.038,1), .72, .38)
    polymer = _mat('Polymer_Charcoal', (.022,.026,.030,1), 0, .55)
    black = _mat('Recess_Black', (.006,.008,.010,1), .35, .6)
    steel = _mat('Edge_Steel', (.060,.066,.070,1), .85, .3)
    panel = _mat('Stock_Panel_Charcoal', (.026,.030,.034,1), 0, .52)
    rubber = _mat('Stock_Buttpad_Rubber', (.014,.017,.020,1), 0, .73)

    # Exposed connection behind the receiver. The receiver hides the forward cap.
    _cyl_x('STK_Buffer_Exposed', 493, 532, 104, .167, metal, 16)
    _cyl_x('STK_Buffer_Collar', 489, 496, 104, .202, metal, 16)
    _cyl_x('STK_Buffer_Collar_Seam', 496, 497.3, 104, .182, black, 16, .002)
    _profile('STK_Front_Tube_Support',
             [(516,111),(528,110),(535,123),(527,129),(524,128)], -.18,.18, polymer,.014)

    # The chamfered cheekrest sweeps upward at the front and wraps the buffer rail.
    _profile('STK_Cheekrest_Shell',
             [(524,87),(528,84),(649,84),(653,89),(652,106),(647,115),
              (550,116),(545,111),(538,106),(531,101),(524,93)],
             -.227,.227,polymer,.022,1)
    cheek_panel = [(530,87),(646,87),(647,98),(643,104),(636,108),
                   (554,108),(547,105),(541,100),(535,94)]
    # Slight relief catches key light without breaking the silhouette.
    for sign, label in ((-1,'L'),(1,'R')):
        ys = sorted((sign*.229, sign*.242))
        _profile('STK_Cheekrest_Raised_'+label,cheek_panel,*ys,panel,.009,1)
        ys = sorted((sign*.2425,sign*.245))
        _profile('STK_Cheekrest_Mould_Line_'+label,
                 [(550,106.2),(636,106.2),(643,100.4),(642.6,102.4),(636.3,108),(553,108)],
                 *ys,polymer,.002,1)
        _pin('STK_Cheekrest_Front_Pin_'+label,558,112,sign*.234,.018,black)
        _pin('STK_Cheekrest_Rear_Pin_'+label,635,111.3,sign*.234,.018,black)

    _profile('STK_Under_Cheek_Rail',
             [(529,113),(650,112),(650,128),(552,128),(549,131),(530,125)],
             -.198,.198,polymer,.010,1)
    # Three shallow elongated dark reliefs, not functional internals.
    for sign,label in ((-1,'L'),(1,'R')):
        ys=sorted((sign*.1985,sign*.202))
        _profile('STK_Long_Underside_Recess_'+label,
                 [(548,115.3),(646,115.3),(646,124.2),(551,124.2),(548,122.4)],
                 *ys,black,.003,1)
        for i,(left,right) in enumerate(((552,577),(580,607),(611,637))):
            ys=sorted((sign*.202,sign*.207))
            _profile('STK_Vent_Rim_%s_%02d'%(label,i),
                     [(left,116.4),(right,116.4),(right,121.2),(left+2,121.2),(left,120)],
                     *ys,polymer,.003,1)
            ys=sorted((sign*.2072,sign*.209))
            _profile('STK_Vent_Dark_%s_%02d'%(label,i),
                     [(left+2,117.4),(right-1,117.4),(right-1,119.8),(left+2,119.8)],
                     *ys,black,0,1)
        ys=sorted((sign*.211,sign*.202))
        _profile('STK_Under_Rail_Lip_'+label,
                 [(550,123.6),(645,123.6),(645,126),(552,126)],*ys,panel,.003,1)

    # Thin filled triangular side web, with the narrow source-visible through-slot.
    web = _profile('STK_Angular_Lower_Web',
             [(550,125.5),(648,125.5),(649,133),(647,196),(644,207),
              (639,209),(635,205),(633,196),(611,169),(597,151),(586,139),(550,139)],
             -.18,.18,polymer,0)
    cutter = _profile('STK_TEMP_Slot_Cutter',_capsule_pixels(608.7,639.3,129.8,136.1),
                      -.35,.35,None,0)
    mod=web.modifiers.new('Reference horizontal opening','BOOLEAN')
    mod.operation='DIFFERENCE'
    mod.solver='EXACT'
    mod.object=cutter
    bpy.context.view_layer.objects.active=web
    web.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    web.select_set(False)
    _CREATED.remove(cutter)
    bpy.data.objects.remove(cutter,do_unlink=True)
    _bevel(web,.008,1)

    for sign,label in ((-1,'L'),(1,'R')):
        ys=sorted((sign*.181,sign*.189))
        # Recessed triangular field lives below the opening and stays inside the web.
        _profile('STK_Lower_Triangular_Field_'+label,
                 [(610,140.5),(642,140.5),(640.7,184.5),(635.5,188.5),(615,164.2)],
                 *ys,black,.006,1)
        ys=sorted((sign*.189,sign*.194))
        _profile('STK_Lower_Triangular_Inset_'+label,
                 [(614,143),(639,143),(638,182),(635,185),(618,163)],
                 *ys,polymer,.005,1)
        ys=sorted((sign*.193,sign*.201))
        _profile('STK_Diagonal_Web_Rib_'+label,
                 [(587,136.8),(590.1,136.8),(642.9,196.8),(641.9,200.7)],
                 *ys,panel,.006,1)
        # Small moulded ribs close to the rear spine.
        for i,zpix in enumerate((143.5,149,155)):
            ys=sorted((sign*.194,sign*.203))
            _profile('STK_Rear_Mould_Rib_%s_%02d'%(label,i),
                     [(638.8,zpix),(642,zpix),(642,zpix+2.6),(638.8,zpix+2.6)],
                     *ys,polymer,.002,1)
        _pin('STK_Lower_Lug_Disc_'+label,640,195.5,sign*.206,.045,black,12)
        _pin('STK_Lower_Lug_Center_'+label,640,195.5,sign*.213,.014,steel,8)

    # Forward adjustment silhouette with a short down-facing stem. Solid exterior.
    _profile('STK_Adjustment_Lever',
             [(546,129.1),(577,129.1),(586.5,133.6),(607.5,157.5),
              (612,163.2),(612,176.1),(607.4,177.7),(602.4,173.2),
              (581,149.2),(574,147.1),(550,147.1),(546,145)],
             -.218,.218,polymer,.013,1)
    for sign,label in ((-1,'L'),(1,'R')):
        ys=sorted((sign*.219,sign*.227))
        _profile('STK_Adjustment_Lever_Panel_'+label,
                 [(550.5,132),(576.5,132),(583.5,135),(606.9,161.9),
                  (608.8,166),(608.8,172.6),(604.5,170.3),(582.5,146.7),
                  (574.5,143.8),(550.5,143.8)],*ys,panel,.007,1)
    cx,cz=_xz((568,150))
    _box('STK_Adjustment_Short_Stem',(cx,0,cz),(.095,.20,.12),black,.011,2)

    # Broad vertically curved rubber buttpad. Rear surface grooves remain subtle.
    _profile('STK_Curved_Buttpad',
             [(650,84),(662.7,84),(666.8,88.8),(668.2,96),(667.1,197.8),
              (665.4,206.4),(661.5,211),(648.8,211),(644,207.2),
              (645.7,197.2),(647.6,194),(649.1,108.5)],
             -.242,.242,rubber,.028,2)
    for sign,label in ((-1,'L'),(1,'R')):
        ys=sorted((sign*.2425,sign*.248))
        _profile('STK_Buttpad_Shoulder_'+label,
                 [(650.5,85),(653,88.5),(653,199),(650.2,207),(647.2,206),
                  (648.4,195),(650.4,104)],*ys,polymer,.005,1)
    for i,pz in enumerate((100,116,132,148,164,180,196)):
        x,z=_xz((667.4,pz))
        _box('STK_Buttpad_Rear_Groove_%02d'%i,(x,0,z),(.014,.396,.014),black,0,1)

    for obj in _CREATED:
        _uv(obj)
        obj['asset_section']='Adjustable stock exterior'
        obj['source_coordinates']='X=(pixel_x-349)/80; Z=(171-pixel_y)/80'
    return list(_CREATED)


if __name__ == '__main__':
    build()
