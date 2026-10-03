import bpy, math, random, json, os, sys
from mathutils import Vector, Matrix
from math import sin, cos, pi
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
random.seed(44)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name != 'Collection' and c.users==0: bpy.data.collections.remove(c)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1.0
COL={}
def coll(name):
    if name not in COL:
        c=bpy.data.collections.new(name);scene.collection.children.link(c);COL[name]=c
    return COL[name]
current='00_Ground'
def register(o,name,mat=None):
    o.name=name
    for c in list(o.users_collection): c.objects.unlink(o)
    coll(current).objects.link(o)
    if mat: o.data.materials.append(mat if not isinstance(mat,str) else M[mat])
    return o
M={}
def mat(name,color,rough=.8,metal=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    M[name]=m;return m
for name,color in {'chalk':(.83,.82,.70),'ivory':(.96,.91,.72),'mint':(.18,.47,.42),'mint_light':(.33,.65,.54),'mint_dark':(.07,.24,.24),'ochre':(.78,.49,.14),'ochre_light':(.94,.65,.22),'coral':(.69,.29,.23),'coral_light':(.85,.43,.32),'rose':(.64,.35,.37),'roof':(.085,.16,.20),'roof_light':(.13,.23,.27),'glass':(.07,.21,.25),'glass_light':(.15,.35,.39),'steel':(.19,.26,.29),'tire':(.035,.047,.052),'wood':(.43,.27,.17),'wood_light':(.69,.49,.28),'concrete':(.55,.57,.52),'concrete_light':(.68,.68,.59),'asphalt':(.16,.22,.24),'asphalt_patch':(.19,.25,.26),'sand':(.64,.51,.35),'sand_light':(.77,.64,.44),'grass':(.29,.42,.23),'grass_light':(.39,.51,.28),'leaf':(.17,.32,.23),'leaf_light':(.32,.46,.26),'leaf_bright':(.45,.57,.31),'orange':(.95,.38,.09),'line':(.92,.77,.36),'interior':(.70,.72,.63),'floor':(.49,.38,.27),'pool':(.15,.51,.55)}.items(): mat(name,color)
M['glass'].node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.27
M['steel'].node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.25
mat('lamp',(.98,.78,.39),.35)
p=M['lamp'].node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(1,.55,.17,1);p.inputs['Emission Strength'].default_value=.6

def bevel(o,w=.05,segments=1):
    if w:
        m=o.modifiers.new('Edge highlights','BEVEL');m.width=w;m.segments=segments
        m.affect='EDGES'
        m=o.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=35
    return o

def cube(name,loc,scale,material,bev=.035,rot=0):
    w,d,h=(v/2 for v in scale)
    verts=[(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);coll(current).objects.link(o)
    o.location=loc;o.rotation_euler.z=rot
    if material:me.materials.append(M[material] if isinstance(material,str) else material)
    bevel(o,bev);return o

def mesh(name,verts,faces,material,bev=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);coll(current).objects.link(o)
    if material:me.materials.append(M[material] if isinstance(material,str) else material)
    bevel(o,bev);return o

def cyl(name,loc,r,depth,material,vertices=12,rot=(0,0,0),bev=.025):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=loc,rotation=rot);o=bpy.context.object;register(o,name,material);bevel(o,bev);return o

def ico(name,loc,scale,material,sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc);o=bpy.context.object;o.scale=scale;register(o,name,material);return o

def beam(name,a,b,width,material,depth=None):
    a,b=Vector(a),Vector(b);o=cube(name,(a+b)/2,(width,depth or width,(b-a).length),material,.015);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def text(name,body,loc,size,material,rotation=(pi/2,0,0),align='CENTER'):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.align_x=align;cu.size=size;cu.extrude=.005;cu.bevel_depth=.002
    o=bpy.data.objects.new(name,cu);coll(current).objects.link(o);o.location=loc;o.rotation_euler=rotation;cu.materials.append(M[material]);return o

# A compact 58 x 74m playable footprint; contextual scenery is deliberately separate.
current='00_Ground'
cube('PLAYABLE_Base_58x74m',(0,0,-.45),(58,74,.8),'sand',.18)
cube('Street_main',(0,0,-.025),(57.7,10.5,.10),'asphalt',.02)
cyl('Culdesac_west',(-20,0,-.02),9.5,.11,'asphalt',48,bev=0)
# Sidewalk shoulders, edge strips and small expansion joints.
for s in (-1,1):
    cube('Sidewalk', (0,s*6.45,.04),(56,2.1,.22),'concrete_light',.07)
    cube('Curb',(0,s*5.48,.11),(56,.20,.35),'chalk',.035)
    for x in range(-27,28,3): cube('Pavement_joint',(x,s*6.5,.16),(.025,1.9,.005),'concrete',0)
    cube('Garden_lawn',(0,s*22,.015),(52,29,.10),'grass',.08)
    # Wide setback walk and driveway aligned with paired garages.
    cube('Driveway',(-s*9.0,s*9.4,.045),(7.0,7,.20),'concrete',.04)
    cube('Entry_path',(-s*1,s*9.5,.07),(2.5,6.8,.22),'concrete_light',.03)
    cube('Backyard_terrace',(0,s*25,.055),(24,5.3,.18),'concrete',.04)
    cube('Backyard_lawn',(0,s*31.6,.05),(44,8.5,.16),'grass_light',.07)
    for xx in [-20,-17,18,21]:cube('Side_lane_paving',(xx,s*21,.055),(2.9,27,.13),'sand_light',.04)
for x in range(-23,28,7):
    cube('Street_center_dash',(x,0,.047),(2.8,.12,.014),'line',0)
for x,y,w,l in [(-13,-3,4,1.8),(15,1,5,2.8),(24,-3,3,1.3)]:cube('Road_repair',(x,y,.038),(w,l,.012),'asphalt_patch',.12)
for x in [-22,21]:
    cyl('Manhole',(x,2,.058),.46,.035,'steel',24,bev=.01)
    for i in range(-3,4):cube('Drain_grid',(x+i*.10,2,.08),(.025,.55,.012),'tire',0)

# Wall segmentation produces real passages and open windows, not fake dark rectangles.
def segmented_wall(name,center,w,h,axis,holes,material,zbase=0,thick=.25):
    # center holds x/y; horizontal local coordinate is x (axis X) or y (axis Y)
    coords=[-w/2,w/2]; zs=[zbase,zbase+h]
    for l,r,b,t in holes:coords.extend([l,r]);zs.extend([b,t])
    coords=sorted(set(coords));zs=sorted(set(zs))
    for a,b in zip(coords,coords[1:]):
        for lo,hi in zip(zs,zs[1:]):
            if b-a<.01 or hi-lo<.01:continue
            mid=(a+b)/2;zz=(lo+hi)/2
            if any(l<mid<r and bot<zz<top for l,r,bot,top in holes):continue
            loc=(center[0]+mid,center[1],zz) if axis=='X' else (center[0],center[1]+mid,zz)
            scale=(b-a,thick,hi-lo) if axis=='X' else (thick,b-a,hi-lo)
            cube(name,loc,scale,material,.025)

def house(sign):
    global current
    prefix='A_Mint' if sign==1 else 'B_Saffron';current='10_'+prefix+'_Architecture'
    start=set(bpy.data.objects)
    c1,c2=('mint','mint_light') if sign==1 else ('ochre','ochre_light')
    # Model in local coordinates, then rotate the southern plan 180 degrees.
    cube(prefix+'_foundation',(0,0,.05),(12.4,11.4,.24),'chalk',.10)
    cube(prefix+'_ground_floor',(0,0,.17),(11.65,10.65,.10),'floor',.015)
    segmented_wall(prefix+'_front', (0,-5.5),12,6.7,'X',[(-1.9,-.1,.2,2.8),(.9,4.5,1.10,2.65),(-2.6,2.6,4.25,6.2)],c1,.1)
    segmented_wall(prefix+'_rear',(0,5.5),12,6.7,'X',[(.3,2.2,.2,2.8),(-.9,1.1,3.35,5.95)],c1,.1)
    segmented_wall(prefix+'_west',(-6,0),11,6.7,'Y',[(-2.2,.2,4.35,5.95)],c1,.1)
    segmented_wall(prefix+'_east',(6,0),11,6.7,'Y',[(-1.7,.2,.2,2.7),(1.8,3.9,4.25,5.95)],c1,.1)
    # Stone skirt interrupted around all doors.
    for x0,x1 in [(-6,-1.9),(-.1,6)]:cube('Facade_stone_plinth',((x0+x1)/2,-5.66,.5),(x1-x0,.18,.65),'concrete_light',.03)
    for x in [-5.9,5.9]:
        cube('Corner_trim',(x,-5.69,3.45),(.2,.17,6.9),'ivory',.025)
        cube('Corner_trim',(x,5.69,3.45),(.2,.17,6.9),'ivory',.025)
    # Three horizontal bands maintain broad stylized color-blocks.
    for z in [3.25,6.65]:
        cube('Front_beltcourse',(0,-5.70,z),(12.3,.24,.22),'ivory',.025)
        cube('Rear_beltcourse',(0,5.70,z),(12.3,.24,.22),'ivory',.025)
        for x in [-6.1,6.1]:cube('Side_beltcourse',(x,0,z),(.23,11.3,.22),'ivory',.025)
    for z in [1.05,1.65,2.25,3.85,4.45,5.05,5.65]:
        # Thin siding accents stay only on opaque edge panels.
        for x in [-4.6,4.7]:cube('Siding_line',(x,-5.645,z),(2.1,.035,.035),c2,0)
        cube('Rear_siding',(3.8,5.645,z),(3.6,.035,.035),c2,0)
    # Window casing, open center apertures.
    def frame(cx,y,bot,w,h,open=True):
        for x in [cx-w/2,cx+w/2]:cube('Window_jamb',(x,y,bot+h/2),(.15,.22,h+.20),'ivory',.02)
        for z in [bot,bot+h]:cube('Window_lintel',(cx,y,z),(w+.25,.25,.15),'ivory',.02)
        cube('Window_sill',(cx,y-.10,bot-.05),(w+.4,.47,.13),'chalk',.025)
        if not open:cube('Window_tinted',(cx,y+.02,bot+h/2),(w-.1,.045,h-.10),'glass',.01)
    frame(0,-5.66,4.25,5.2,1.95,True)
    frame(2.7,-5.66,1.1,3.6,1.55,True)
    frame(.1,5.66,3.35,2.0,2.6,True)
    # Slim accent shutters outside front upper window.
    for xx in [-3.15,3.15]:
        cube('Shutter',(xx,-5.72,5.2),(.7,.17,2.15),'roof',.035)
        for z in [4.4,4.7,5.,5.3,5.6,5.9]:cube('Shutter_louvre',(xx,-5.83,z),(.59,.10,.09),'roof_light',.01)
    # Front porch, light, house number and canopy.
    cube('Front_porch',(-1,-6.15,.12),(3.4,1.65,.24),'concrete_light',.05)
    cube('Door_lintel',(-1,-5.69,2.83),(2.0,.23,.17),'ivory',.02)
    for xx in [-1.95,-.05]:cube('Door_jamb',(xx,-5.69,1.52),(.16,.23,2.64),'ivory',.02)
    cube('Entry_canopy',(-1.05,-6.05,3.10),(3.1,1.35,.20),'roof',.06)
    cube('Entry_canopy_trim',(-1.05,-6.73,3.13),(3.25,.1,.18),'ivory',.02)
    cube('Number_plaque',(-3,-5.72,2.4),(1.1,.12,.65),'roof',.05)
    text('Address_number','01' if sign==1 else '02',(-3,-5.795,2.2),.40,'ivory')
    cube('Porch_lamp',(.37,-5.81,2.53),(.2,.20,.38),'steel',.025)
    cube('Porch_lamp_glow',(.37,-5.93,2.53),(.13,.045,.26),'lamp',.02)
    # Upper floor deliberately leaves a 2.2m-wide stairwell on the west.
    cube('Upper_floor_main',(1.05,0,3.25),(9.7,10.65,.23),'floor',.015)
    cube('Upper_floor_front_landing',(-4.65,-4.45,3.25),(2.5,1.9,.23),'floor',.015)
    cube('Upper_floor_rear_landing',(-4.65,4.34,3.25),(2.5,2.08,.23),'floor',.015)
    # Internal stairs climb north, 18 risers at ~17cm, clear top landing.
    for i in range(18):
        z=.19+(3.06/18)*(i+1)
        cube('Interior_stair_%02d'%i,(-4.65,-3.43+i*.39,z/2),(2.05,.40,z),'wood_light',.012)
    beam('Interior_handrail',(-3.51,-3.45,1.14),(-3.51,3.43,4.20),.065,'steel')
    for y,z in [(-3.4,1.14),(-.9,2.25),(1.6,3.36),(3.45,4.20)]:beam('Interior_baluster',(-3.51,y,z-.88),(-3.51,y,z),.045,'steel')
    # Living/kitchen divider: one clear 2m passage, no blocked route.
    segmented_wall('Interior_room_divider',(0,.7),7.25,2.95,'X',[(-.4,1.75,.2,2.65)],'interior',.2,.14)
    cube('Interior_wall_accent',(3.85,.79,1.65),(3,.035,.75),c2,.015)
    # Ceiling roof underside at 6.65; no internal lights needed for game export.
    cube('Ceiling',(0,0,6.61),(11.8,10.7,.15),'interior',.025)
    # Faceted pitched roof, with a north/south ridge.
    verts=[(-6.65,-6.05,6.78),(6.65,-6.05,6.78),(0,-6.05,8.60),(-6.65,6.05,6.78),(6.65,6.05,6.78),(0,6.05,8.60)]
    mesh('Gabled_roof',verts,[(2,5,3,0),(1,4,5,2),(1,2,0),(5,4,3)],'roof',.045)
    for yy in [-6.07,6.07]:
        beam('Roof_fascia',(-6.7,yy,6.78),(0,yy,8.63),.17,'ivory')
        beam('Roof_fascia',(0,yy,8.63),(6.7,yy,6.78),.17,'ivory')
    for yy in [-5.5,-3.5,-1.5,.5,2.5,4.5]:
        beam('Metal_roof_seam',(-6.45,yy,6.86),(0,yy,8.65),.055,'roof_light')
        beam('Metal_roof_seam',(0,yy,8.65),(6.45,yy,6.86),.055,'roof_light')
    cube('Chimney',(-3.9,2.2,8.15),(1.05,1.35,3.3),'coral',.075)
    cube('Chimney_cap',(-3.9,2.2,9.78),(1.28,1.60,.20),'chalk',.035)
    for z in [7.1,7.65,8.2,8.75,9.3]:cube('Chimney_mortar',(-3.9,1.515,z),(1.06,.015,.04),'wood',0)
    # Side garage gives another covered connector to the rear yard.
    current='11_'+prefix+'_Garage'
    cube('Garage_floor',(9.4,.35,.16),(6.6,10.3,.16),'concrete',.025)
    segmented_wall('Garage_front',(9.4,-4.8),6.9,3.1,'X',[(7.0-9.4,11.8-9.4,.2,2.75)],'chalk',.1)
    segmented_wall('Garage_rear',(9.4,5.5),6.9,3.1,'X',[(8.0-9.4,10.2-9.4,.2,2.75)],'chalk',.1)
    cube('Garage_outer_wall',(12.78,.35,1.62),(.25,10.3,3.15),'chalk',.035)
    cube('Garage_flat_roof',(9.5,.35,3.32),(7.3,10.9,.30),'roof',.06)
    cube('Garage_fascia',(9.5,-5.14,3.29),(7.4,.2,.38),c2,.04)
    for xx in [6.84,11.96]:cube('Garage_frame',(xx,-4.95,1.5),(.20,.35,2.95),'ivory',.025)
    # Rolled-up door louvers above opening, no collision below 2.75m.
    for z in [2.9,3.05]:cube('Garage_door_slats',(9.4,-5.02,z),(4.8,.16,.10),'steel',.015)
    cube('Workbench',(11.8,3.15,.91),(1.35,2.4,.13),'wood_light',.03)
    for yy in [2.2,4.1]:cube('Bench_leg',(11.8,yy,.47),(.15,.15,.86),'steel',.01)
    for j in range(3):cube('Garage_storage',(12.1,-2.4+j*.6,.61),(.7,.5,1.0),'roof_light',.025)
    # Rear balcony/pergola and full external stair route.
    current='12_'+prefix+'_RearDeck'
    cube('Balcony_floor',(.45,6.75,3.25),(9.3,2.35,.25),'wood_light',.03)
    for xx in [-3.75,5.03]:
        for yy in [5.82,7.80]:cube('Pergola_post',(xx,yy,3.23),(.16,.16,6.20),'ivory',.02)
    for xx in [-3.75,5.03]:cube('Pergola_beam',(xx,6.8,6.39),(.2,2.6,.24),'wood_light',.025)
    for xx in [-3.6,-2.6,-1.6,-.6,.4,1.4,2.4,3.4,4.4]:cube('Pergola_louvre',(xx,6.8,6.55),(.11,2.65,.16),'wood_light',.02)
    beam('Balcony_toprail',(-3.78,7.8,4.25),(5.04,7.8,4.25),.11,'ivory')
    for xx in [-3.5,-2.5,-1.5,-.5,.5,1.5,2.5,3.5,4.5]:beam('Balcony_baluster',(xx,7.8,3.4),(xx,7.8,4.25),.075,'wood_light')
    # Walkable outdoor flight approaches left end, open at top.
    for i in range(18):
        z=.20+(3.05/18)*(i+1);xx=-10.85+i*.39
        cube('Exterior_stair_%02d'%i,(xx,6.75,z/2),(0.40,2.15,z),'wood_light',.018)
    for yy in [5.74,7.77]:
        beam('Stair_handrail',(-11.05,yy,1.15),(-3.85,yy,4.28),.095,'ivory')
        for i in [0,6,12,18]:
            xx=-11.05+i*.40;z=1.15+i*(3.13/18);beam('Stair_baluster',(xx,yy,z-.95),(xx,yy,z),.08,'wood_light')
    # Light but readable interior furnishings, outside navigation corridors.
    current='13_'+prefix+'_Interior'
    cube('Living_sofa',(3.95,-2.65,.60),(2.25,1.05,.72),'coral' if sign==1 else 'mint',.16)
    cube('Sofa_back',(3.95,-2.25,1.08),(2.25,.26,.90),'coral' if sign==1 else 'mint',.1)
    cube('Living_rug',(2.25,-2.65,.24),(3.6,3.2,.025),'concrete_light',.02)
    cube('Coffee_table',(1.9,-2.7,.67),(1.2,.8,.12),'wood_light',.035)
    for xx in [1.43,2.37]:cube('Coffee_leg',(xx,-2.7,.43),(.10,.6,.47),'wood',.02)
    cube('Kitchen_counter',(4.5,4.54,.74),(2.4,1.1,1.06),'ivory',.055)
    cube('Kitchen_countertop',(4.5,4.54,1.31),(2.55,1.2,.11),'roof_light',.03)
    cube('Upper_bed',(3.9,2.4,3.72),(2.05,3.25,.55),'ivory',.09)
    cube('Upper_bed_cover',(3.9,1.95,4.04),(2.07,2.20,.09),c2,.045)
    cube('Upper_pillow',(3.9,3.49,4.12),(1.55,.65,.22),'chalk',.08)
    cube('Upper_desk',(3.6,-3.8,4.08),(2.2,.9,.12),'wood_light',.04)
    for xx in [2.7,4.5]:cube('Desk_leg',(xx,-3.8,3.70),(.09,.75,.71),'steel',.02)
    bpy.context.view_layer.update()
    for o in set(bpy.data.objects)-start:
        o.matrix_world=Matrix.Diagonal((-1,1,1,1)) @ o.matrix_world
        if o.type=='FONT': o.scale.x*=-1
        if sign==-1:o.location.x=-o.location.x;o.location.y=-o.location.y;o.rotation_euler.z+=pi
        o.location.y+=sign*17
        o['building']=prefix
house(1);house(-1)

# Stylized but proportioned vehicles in the central lane.
current='20_CentralVehicles'
def wheel(name,x,y,z,r=.50,w=.32):
    cyl(name+'_tire',(x,y,z),r,w,'tire',16,(pi/2,0,0),.04)
    cyl(name+'_hub',(x,y+(w/2+.014)*(1 if y>0 else -1),z),r*.59,.045,'chalk',12,(pi/2,0,0),.02)
    cyl(name+'_hubcap',(x,y+(w/2+.045)*(1 if y>0 else -1),z),r*.26,.05,'steel',12,(pi/2,0,0),.02)
def vehicle_local(name,origin,angle,fun):
    start=set(bpy.data.objects);fun()
    for o in set(bpy.data.objects)-start:
        xx,yy=o.location.x,o.location.y;o.location.x=origin[0]+cos(angle)*xx-sin(angle)*yy;o.location.y=origin[1]+sin(angle)*xx+cos(angle)*yy;o.location.z+=origin[2];o.rotation_euler.z+=angle;o['vehicle']=name

def bus():
    cube('Shuttle_chassis',(0,0,.63),(10.5,2.73,.33),'roof',.10)
    cube('Shuttle_body',(-.38,0,1.20),(9.8,2.75,1.04),'ochre_light',.14)
    cube('Shuttle_roof',(-.43,0,3.05),(9.90,2.87,.30),'ivory',.17)
    # Window belt broad and dark; individual cream pillars articulate profile.
    cube('Shuttle_window_cabin',(-.50,0,2.30),(9.55,2.63,1.25),'glass',.12)
    for y in [-1.365,1.365]:
        cube('Shuttle_beltline',(-.45,y,1.72),(9.85,.09,.15),'roof',.025)
        cube('Shuttle_lower_stripe',(-.45,y,1.16),(9.80,.06,.15),'ochre',.015)
        cube('Shuttle_upper_trim',(-.48,y,2.88),(9.8,.12,.14),'ochre_light',.03)
        for x in [-4.75,-3.6,-2.45,-1.3,-.15,1.,2.15,3.3,4.28]:cube('Shuttle_window_pillar',(x,y,2.34),(.13,.15,1.05),'ochre_light',.025)
        for x in [-4.16,-3.0,-1.86,-.71,.44,1.59,2.74,3.78]:cube('Shuttle_window_reflection',(x,y+(.006 if y>0 else -.006),2.73),(.88,.014,.08),'glass_light',.015)
    cube('Shuttle_hood',(4.72,0,1.31),(1.20,2.62,.50),'ochre_light',.12)
    cube('Shuttle_front_grille',(5.33,0,1.09),(.055,1.35,.45),'steel',.035)
    for yy in [-.52,-.26,0,.26,.52]:cube('Shuttle_grille_slat',(5.368,yy,1.09),(.04,.045,.35),'ivory',.012)
    for yy in [-1.02,1.02]:cyl('Shuttle_headlamp',(5.34,yy,1.27),.19,.075,'lamp',16,(0,pi/2,0),.02)
    for xx in [-5.35,5.42]:cube('Shuttle_bumper',(xx,0,.80),(.18,2.96,.28),'chalk',.055)
    for xx in [-3.50,3.35]:
        for yy in [-1.39,1.39]:wheel('Shuttle',xx,yy,.65,.61,.35)
    for yy in [-1.48,1.48]:
        beam('Shuttle_mirror_arm',(4.25,yy,2.30),(4.8,yy*1.25,2.3),.05,'steel')
        cube('Shuttle_mirror',(4.8,yy*1.25,2.42),(.15,.12,.38),'roof',.025)
    cube('Shuttle_destination',(4.41,0,2.78),(.04,1.5,.22),'roof',.02)
    # Roof hatches and readable side branding, original fictional shuttle.
    for xx in [-2.2,1.0]:cube('Shuttle_roof_hatch',(xx,0,3.23),(1.25,1.0,.12),'roof_light',.05)
    text('Shuttle_label','SUNLINE',(-1.5,-1.414,1.27),.31,'ivory')
    text('Shuttle_number','07',(3.5,-1.42,1.24),.31,'roof')
vehicle_local('SUNLINE_Shuttle',(4,-2.15,.03),-.035,bus)

def truck():
    cube('Truck_chassis',(0,0,.70),(10.5,2.70,.26),'roof',.09)
    cube('Truck_cargo_floor',(-1.35,0,1.06),(7.0,3.00,.23),'wood_light',.045)
    # Open rear cargo portal gives a covered dead-end perch.
    cube('Truck_cargo_roof',(-1.35,0,4.02),(7.20,3.12,.23),'chalk',.07)
    for yy in [-1.48,1.48]:
        cube('Truck_cargo_side',(-1.25,yy,2.58),(7.08,.15,2.70),'coral',.055)
        cube('Truck_cream_stripe',(-1.25,yy+(.085 if yy>0 else -.085),2.45),(7.04,.04,.37),'ivory',.01)
        for xx in [-4.5,-2.8,-1.1,.6,2.18]:cube('Truck_rib',(xx,yy+(.1 if yy>0 else -.1),2.63),(.085,.055,2.65),'coral_light',.02)
    cube('Truck_cargo_bulkhead',(2.27,0,2.55),(.15,2.98,2.95),'coral',.035)
    cube('Truck_cab',(3.72,0,1.53),(2.65,2.76,1.65),'mint',.12)
    cube('Truck_cab_glazing',(3.56,0,2.72),(2.30,2.65,1.14),'glass',.14)
    cube('Truck_cab_roof',(3.55,0,3.35),(2.64,2.88,.24),'mint_light',.08)
    for yy in [-1.40,1.40]:
        for xx in [2.45,4.71]:cube('Truck_window_pillar',(xx,yy,2.73),(.14,.13,1.12),'mint',.02)
        cube('Truck_door_trim',(3.45,yy,2.12),(2.33,.1,.13),'ivory',.02)
        cube('Truck_handle',(3.04,yy*1.026,1.85),(.31,.06,.07),'chalk',.015)
    cube('Truck_windshield_bar',(4.78,0,2.7),(.1,.09,1.06),'mint',.02)
    cube('Truck_front_grille',(5.085,0,1.39),(.08,1.63,.63),'roof',.04)
    for zz in [1.18,1.38,1.58]:cube('Truck_grille_bar',(5.138,0,zz),(.035,1.50,.065),'chalk',.015)
    for yy in [-1.07,1.07]:cube('Truck_headlamp',(5.10,yy,1.52),(.1,.37,.34),'lamp',.06)
    cube('Truck_front_bumper',(5.18,0,.99),(.20,2.94,.32),'chalk',.055)
    for xx in [-3.35,-2.02,3.77]:
        for yy in [-1.41,1.41]:wheel('Truck',xx,yy,.67,.61,.32)
    # Rear loading ramp rises 0.95m across 3.0m, navigable slope 17.6 degrees.
    mesh('Truck_loading_ramp',[(-7.9,-1.25,.17),(-7.9,1.25,.17),(-4.85,1.25,1.17),(-4.85,-1.25,1.17),(-7.9,-1.25,.07),(-7.9,1.25,.07),(-4.85,1.25,1.07),(-4.85,-1.25,1.07)],[(3,2,1,0),(5,6,7,4),(1,5,4,0),(7,6,2,3),(2,6,5,1),(4,7,3,0)],'steel',.025)
    for xx in [-7.7,-7.1,-6.5,-5.9,-5.3]:
        zz=.17+(xx+7.9)/3.05;cube('Ramp_grip',(xx,0,zz+.015),(.065,2.43,.035),'chalk',.01)
    text('Delivery_label','SUNWARD',(-1.30,-1.58,2.75),.50,'ivory')
    text('Delivery_subtitle','FIELD LOGISTICS',(-1.30,-1.58,1.84),.22,'ivory')
vehicle_local('Sunward_Delivery',(-3,2.70,.02),.025,truck)

def sedan():
    cube('Sedan_lower',(0,0,.58),(4.8,2.04,.55),'rose',.20)
    cube('Sedan_hood',(1.4,0,.92),(1.7,1.94,.31),'coral_light',.10)
    cube('Sedan_trunk',(-1.75,0,.96),(1.1,1.94,.37),'coral_light',.10)
    # Trapezoidal cabin has crisp angled windshield silhouette.
    mesh('Sedan_cabin',[(-1.22,-.9,1),(-1.22,.9,1),(1.03,.9,1),(1.03,-.9,1),(-.83,-.75,1.77),(-.83,.75,1.77),(.50,.75,1.77),(.50,-.75,1.77)],[(4,5,1,0),(5,6,2,1),(6,7,3,2),(7,4,0,3),(7,6,5,4)],'glass',.06)
    cube('Sedan_roof',(-.16,0,1.82),(1.5,1.66,.16),'ivory',.08)
    for yy in [-.91,.91]:beam('Sedan_B_pillar',(-.20,yy,1.03),(-.20,yy*.83,1.78),.10,'ivory')
    for xx in [-1.5,1.5]:
        for yy in [-.99,.99]:wheel('Sedan',xx,yy,.43,.42,.22)
    for xx in [-2.45,2.45]:cube('Sedan_bumper',(xx,0,.55),(.13,2.1,.18),'chalk',.04)
    for yy in [-.74,.74]:cyl('Sedan_headlight',(2.43,yy,.85),.16,.06,'lamp',12,(0,pi/2,0),.02)
vehicle_local('West_Pink_Sedan',(-21,0,.03),.18,sedan)

# Yard cover, fencing, stylized planting and clearly named routes.
current='30_ExteriorProps'
def crate(loc,scale=(1.3,1.1,1.2)):
    x,y,z=loc;w,d,h=scale;cube('Supply_crate',(x,y,z+h/2),(w,d,h),'wood_light',.045)
    for zz in [z+.16,z+h-.16]:cube('Crate_band',(x,y,zz),(w+.06,d+.06,.10),'steel',.015)
    for xx in [x-w/2+.15,x+w/2-.15]:cube('Crate_brace',(xx,y-d/2-.025,z+h/2),(.12,.06,h),'wood',.02)
def planter(loc,w=3,d=1.0):
    x,y=loc;cube('Planter',(x,y,.36),(w,d,.68),'chalk',.08);cube('Planter_soil',(x,y,.72),(w-.2,d-.2,.08),'wood',.025)
    for i in range(max(2,int(w/.65))):ico('Planter_shrub',(x-w/2+.38+i*.63,y,.99),(.48,.42,.52),['leaf','leaf_light','leaf_bright'][i%3],1)
def barrier(loc,angle=0):
    x,y=loc;verts=[(-1.7,-.52,0),(1.7,-.52,0),(1.7,.52,0),(-1.7,.52,0),(-1.7,-.26,1.12),(1.7,-.26,1.12),(1.7,.26,1.12),(-1.7,.26,1.12)]
    verts=[(x+cos(angle)*a-sin(angle)*b,y+sin(angle)*a+cos(angle)*b,c+.1) for a,b,c in verts]
    mesh('Jersey_barrier',verts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7),(0,3,2,1)],'concrete_light',.065)
    o=cube('Barrier_color_panel',(x,y-.40,.75),(2.8,.055,.26),'ochre',.015,angle)
for s in [-1,1]:
    for x in [-15.3,16.8]:planter((x,s*10),3.2,1.1)
    planter((s*5,s*8.5),3.1,.9)
    for x,y in [(-16,29),(16,32),(-18,16)]:
        crate((s*x,s*y,.16),(1.5,1.4,1.30));crate((s*x+.2,s*y+.12,1.46),(1.05,1.1,.80))
    cube('Garden_shed',(s*13,s*33.6,1.7),(5.4,4.6,3.25),'rose' if s==1 else 'mint_dark',.08)
    cube('Shed_roof',(s*13,s*33.6,3.40),(5.8,5,.25),'roof',.075)
    cube('Shed_door',(s*13,s*31.26,1.36),(1.7,.12,2.6),'wood_light',.035)
    cube('Shed_door_inlay',(s*13,s*31.18,1.6),(1.25,.045,1.95),'wood',.025)
    # Decorative rear garden beds leave broad cross-yard paths.
    for xx in [-8,-2,4]:
        cube('Garden_raised_bed',(s*xx,s*34.4,.40),(4.6,2.5,.70),'wood_light',.06)
        cube('Garden_soil',(s*xx,s*34.4,.78),(4.35,2.28,.06),'wood',.02)
        for dx in [-1.5,-.5,.5,1.5]:
            for dy in [-.6,.6]:ico('Garden_plant',(s*xx+dx,s*34.4+dy,1.06),(.35,.32,.4),'leaf_light',1)
    # Chest-height utility cover, no oversized head-height clutter in main lanes.
    cube('Utility_cover',(s*17,s*23,.95),(2.4,1.4,1.8),'mint_dark',.055)
    cube('Utility_cover_lid',(s*17,s*23,1.91),(2.5,1.5,.14),'chalk',.035)
    for i in range(5):cube('Utility_vent',(s*17+.75,s*23-.73,.68+i*.2),(.58,.025,.04),'roof',.005)
for y in [-3,1.5]:barrier((26,y),pi/2)
for x in [20,23]:barrier((x,-5.0),0)
# A warm original sign makes the fan-inspired scene its own place.
for x in [-19.0,-14.0]:cube('Sign_post',(x,8.4,1.55),(.18,.18,3.0),'steel',.025)
cube('Sunward_sign',(-16.5,8.4,2.15),(5.5,.27,2.05),'ivory',.10)
cube('Sunward_sign_inset',(-16.5,8.23,2.16),(5.16,.09,1.70),'mint_dark',.07)
text('Map_title','SUNWARD',(-16.5,8.165,2.32),.58,'ivory')
text('Map_subtitle','TEST SITE  /  07',(-16.5,8.16,1.81),.28,'ochre_light')
# Back fencing defines playable boundary; side-lane passage remains at least 2.5m.
current='31_Boundary'
def fence(a,b,height=2.0):
    a,b=Vector(a),Vector(b);length=(b-a).length;n=max(1,int(length/2.3));direction=(b-a).normalized();angle=math.atan2(direction.y,direction.x)
    for i in range(n+1):
        p=a+(b-a)*i/n;cube('Fence_post',(p.x,p.y,height/2),(.18,.18,height+.20),'ivory',.025)
    mid=(a+b)/2
    for zz in [.42,height-.28]:cube('Fence_rail',(mid.x,mid.y,zz),(length,.10,.14),'wood_light',.015,angle)
    nboard=int(length/.42)
    for i in range(nboard):
        p=a+(b-a)*(i+.5)/nboard;cube('Fence_board',(p.x,p.y,height/2),(.36,.075,height),'wood_light' if i%4 else 'chalk',.02,angle)
fence((-27,-36.5),(27,-36.5));fence((-27,36.5),(27,36.5))
for xx in [-27,27]:
    fence((xx,-36.5),(xx,-7.5));fence((xx,7.5),(xx,36.5))
# Outer west pink house: non-playable landmark beyond the loop.
current='40_ContextScenery'
cube('West_pink_house',(-34,0,3.2),(9,15,6.5),'rose',.12)
cube('West_roof',(-34,0,6.7),(10,16,.55),'roof',.10)
for yy in [-4,0,4]:
    cube('Context_window',(-29.42,yy,3.45),(.09,2.5,2.6),'glass',.04)
    for z in [2.1,4.8]:cube('Context_window_frame',(-29.32,yy,z),(.15,2.7,.15),'ivory',.03)
cube('West_fascia',(-29.2,0,6.1),(.2,15.3,.25),'ivory',.035)
# Low-poly trees with intentional clustered facets and trunks.
def tree(x,y,size=1):
    cyl('Tree_trunk',(x,y,1.9*size),.17*size,3.8*size,'wood',7,bev=.015)
    for dx,dy,dz,sc in [(-.65,.0,3.4,1.4),(.70,.18,3.6,1.35),(.05,.2,4.3,1.55),(.0,-.60,3.65,1.25)]:
        beam('Tree_branch',(x,y,2.1*size),(x+dx*size,y+dy*size,(dz-.5)*size),.12*size,'wood')
        ico('Tree_canopy',(x+dx*size,y+dy*size,dz*size),(sc*size,sc*.86*size,sc*.90*size),random.choice(['leaf','leaf_light','leaf_bright']),1)
for x,y,size in [(-23,31,1.4),(22,32,1.3),(-22,-31,1.35),(23,-31,1.35),(-25,11,1.1),(24,-13,1.1),(22,13,1.0),(-24,-12,1.0),(-23,22,1.05),(24,23,1.25)]:tree(x,y,size)
# Planar sandstone formations and far mesas are scenery only.
cube('World_desert',(0,0,-1.0),(300,300,.50),'sand',.1)
for i in range(32):
    theta=i*2*pi/32;rr=random.uniform(65,95);x,y=cos(theta)*rr,sin(theta)*rr
    sc=(random.uniform(9,19),random.uniform(7,13),random.uniform(5,13))
    ico('Distant_sandstone',(x,y,sc[2]*.25-1),sc,random.choice(['sand','sand_light','coral']),1)
for s in [-1,1]:
    for x in [-21,-11,1,13,23]:
        # Outside fencing small angular stone clusters.
        ico('Boundary_rock',(x,s*40,.0),(2.0,1.5,1.1),'sand_light',1)
# Sparse architectural utility poles at edges; lines stay high above walk paths.
for x,y in [(-26,-8),(25,8),(-26,30),(25,-30)]:
    cyl('Utility_pole',(x,y,4.7),.14,9.4,'wood',10,bev=.025)
    cube('Utility_crossbar',(x,y,8.6),(3.1,.18,.18),'wood_light',.03)
    for dx in [-1.25,0,1.25]:cyl('Pole_insulator',(x+dx,y,8.85),.13,.30,'chalk',8,bev=.01)
# Modelled cable splines, static and optional scenery.
def cable(a,b):
    cu=bpy.data.curves.new('Cable','CURVE');cu.dimensions='3D';cu.bevel_depth=.022;cu.resolution_u=12;cu.bevel_resolution=0
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(2)
    for p,co in zip(sp.bezier_points,[a,((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2-1.2),b]):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new('Overhead_cable',cu);coll(current).objects.link(o);cu.materials.append(M['roof'])
for dx in [-1.25,1.25]:cable((-26+dx,-8,8.95),(-26+dx,30,8.95));cable((25+dx,-30,8.95),(25+dx,8,8.95))

# Explicit gameplay metadata and route markers kept non-rendering.
current='90_Gameplay'
for name,loc in [('Spawn_A',(0,31,.2)),('Spawn_B',(0,-31,.2)),('Mid_Lane',(0,0,.2)),('West_Flank',(-18,0,.2)),('East_Flank',(18,0,.2)),('Upper_A',(0,13,3.4)),('Upper_B',(0,-13,3.4))]:
    o=bpy.data.objects.new(name,None);coll(current).objects.link(o);o.location=loc;o.empty_display_type='ARROWS';o.empty_display_size=1;o['purpose']='integration marker; not a navmesh'
scene['map_title']='SUNWARD / TEST SITE 07'
scene['layout_reference']='Classic Nuketown structure inspired; original geometry; estimated dimensions'
scene['playable_footprint_m']='58 x 74'
scene['player_reference']='1.8m tall; 0.35m capsule radius; 0.30m step height'

# Render rig uses a warm graphic sun, blue skylight and restrained contrast.
current='80_Presentation'
world=bpy.data.worlds.new('Desert_sky') if not bpy.data.worlds else bpy.data.worlds[0];scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.46,.65,.76,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(25,-35,60));sun=bpy.context.object;register(sun,'Warm_afternoon_sun');sun.data.energy=2.5;sun.data.angle=math.radians(12);sun.rotation_euler=(math.radians(26),math.radians(-18),math.radians(-25))
sun.data.color=(1.0,.85,.69)
bpy.ops.object.light_add(type='AREA',location=(0,0,45));o=bpy.context.object;register(o,'Sky_fill');o.data.energy=1900;o.data.shape='DISK';o.data.size=60
# Soft fill near rooms ensures open portals read in renders without emissive fakery.
for s in [-1,1]:
    bpy.ops.object.light_add(type='AREA',location=(0,s*17,2.9));o=bpy.context.object;register(o,'Interior_fill');o.data.energy=70;o.data.shape='DISK';o.data.size=6
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False;scene.cycles.max_bounces=5
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.5

def camera(name,loc,target,lens=45,ortho=None):
    bpy.ops.object.camera_add(location=loc);o=bpy.context.object;register(o,name);o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens;o.data.clip_end=500
    if ortho:o.data.type='ORTHO';o.data.ortho_scale=ortho
    return o
cams={
'01_hero':camera('Camera_Hero',(58,-63,49),(0,0,1.5),45),
'02_reverse':camera('Camera_Reverse',(-52,53,37),(0,0,1.5),46),
'03_street':camera('Camera_Street',(-19,-8.6,1.75),(1,12,3.25),23),
'04_backyard':camera('Camera_Backyard',(-18,34,2.2),(0,22.5,3.6),28),
'05_topdown':camera('Camera_Topdown',(0,0,95),(0,0,0),45,83),
'06_upper_sightline':camera('Camera_UpperSightline',(0,12.8,4.94),(0,-14,3.1),28),
'07_ground_route':camera('Camera_GroundRoute',(1,21.4,1.80),(-1,10.2,1.50),22),
}
scene.camera=cams['01_hero']
# Convenient material preview opening, full map framed and no distracting camera/light outlines.
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False
        area.spaces.active.region_3d.view_distance=90;area.spaces.active.region_3d.view_location=(0,0,1)
print('GEOMETRY_READY',len(bpy.data.objects),flush=True)
# Save editable source scene before exports.
os.makedirs(ROOT+'/exports',exist_ok=True);os.makedirs(ROOT+'/renders',exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
# glTF: export environment only, preserve spatial object names and extras. Presentation is Blender-only.
bpy.ops.object.select_all(action='DESELECT')
for c in COL.values():
    if c.name.startswith(('80_','90_')):continue
    for o in c.objects:
        if o.type in {'MESH','CURVE','FONT'}:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=ROOT+'/exports/Sunward_Environment.glb',export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_yup=True)
# Measure evaluated triangles and object/material resources.
dg=bpy.context.evaluated_depsgraph_get();triangles=0;meshes=0
for o in bpy.context.selected_objects:
    if o.type in {'MESH','CURVE','FONT'}:
        ev=o.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();triangles+=len(me.loop_triangles);meshes+=1;ev.to_mesh_clear()
with open(ROOT+'/exports/resource_stats.json','w') as f:json.dump({'name':'SUNWARD / TEST SITE 07','playable_bounds_m':[58,74],'units':'meters','evaluated_triangles':triangles,'renderable_objects':meshes,'materials':len(M),'texture_images':0,'player_capsule_m':{'height':1.8,'radius':.35,'step':.30},'build_version':'1.0'},f,indent=2)
bpy.ops.object.select_all(action='DESELECT')
scene.camera=cams['01_hero'];bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_TestSite.blend')
# First-pass images; optional camera list supplied after --.
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['01_hero','03_street','04_backyard','05_topdown']
for key in args:
    if key not in cams:continue
    scene.camera=cams[key];scene.render.filepath=ROOT+'/renders/'+key+'.png'
    if key=='05_topdown':scene.render.resolution_x=1400;scene.render.resolution_y=1700
    else:scene.render.resolution_x=1600;scene.render.resolution_y=1100
    bpy.ops.render.render(write_still=True)
print('BUILD_COMPLETE',triangles,meshes)
