import bpy,math,os,sys,random
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=bpy.context.scene;sys.path.insert(0,ROOT)
# Give all curved sidewalk and curb ribbons real downward thickness.
for o in bpy.data.collections['00_Ground'].objects:
 if o.name.startswith(('Culdesac_footway','Curved_curb')):
  m=o.modifiers.new('Grounded stone depth','SOLIDIFY');m.thickness=.235 if o.name.startswith('Culdesac_footway') else .31;m.offset=-1;m.use_even_offset=True
# Warm, dark timber reads independently from blue-gray roofing.
for name,col in [('SW2_Arch_WeatheredTimber',(.105,.078,.052)),('SW2_Arch_TimberEdge',(.235,.175,.108))]:
 if name in bpy.data.materials:
  m=bpy.data.materials[name];m.diffuse_color=(*col,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*col,1)
# Restrained upper-edge greenery evokes the reference without obstructing openings.
import add_foliage_dense as foliage
leaves=[bpy.data.materials['V2_Leaf_'+name] for name in ['DeepOlive','Olive','Sage','SunlitSage','WarmTips']]
barks=[bpy.data.materials['V2_Bark_'+name] for name in ['WarmBrown','LightRidge','DarkCrease']]
col=bpy.data.collections['60_V2_Foliage'];rng=random.Random(2048)
foliage._ivy_patch('Garage_A_Header',(-12.35,12.0,2.92),(1,0,0),(0,-1,0),5.7,.62,145,rng,col,leaves,barks)
foliage._ivy_patch('Garage_B_Header',(12.35,-12.0,2.92),(-1,0,0),(0,1,0),5.7,.62,145,rng,col,leaves,barks)
cam=bpy.data.objects['Camera_Courtyard'];cam.location=(-12.8,8.5,1.75);cam.rotation_euler=(Vector((-.5,15.5,2.7))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=26
# Orthographic overview keeps the entire footprint centered and minimizes empty margins.
hero=bpy.data.objects['Camera_Hero'];hero.location=(65,-75,70);hero.rotation_euler=(Vector((0,0,2.0))-hero.location).to_track_quat('-Z','Y').to_euler();hero.data.type='ORTHO';hero.data.ortho_scale=100
s['build_version']='2.3';s['art_direction_notes']='Reference-inspired warm plaster, irregular limestone, aged timber, leafy overgrowth and neutral daylight. Original footprint and routes preserved.'
s.cycles.samples=96;s.cycles.use_denoising=False;s.render.resolution_x=1500;s.render.resolution_y=1000
s.camera=hero
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   sp=area.spaces.active;sp.shading.type='SOLID';sp.shading.color_type='MATERIAL';sp.shading.show_cavity=True;sp.overlay.show_overlays=False;sp.region_3d.view_perspective='CAMERA';sp.region_3d.view_camera_zoom=20
bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Delivery.blend')
for key,c in [('final_courtyard','Camera_Courtyard'),('final_hero','Camera_Hero'),('final_street','Camera_Street')]:
 s.camera=bpy.data.objects[c];s.render.filepath=ROOT+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
s.camera=hero;bpy.ops.wm.save_as_mainfile(filepath=ROOT+'/Sunward_v2_Delivery.blend')
print('DELIVERY_ART_COMPLETE',flush=True)
