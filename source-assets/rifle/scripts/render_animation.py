import bpy,os,math
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); bpy.ops.wm.open_mainfile(filepath=ROOT+'/exports/compact_carbine.blend')
s=bpy.context.scene; s.render.engine='CYCLES'; s.cycles.samples=32; s.cycles.use_denoising=False
s.render.resolution_x=960;s.render.resolution_y=600;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
cam=s.camera;cam.location=(-5.5,-15,5);cam.rotation_euler=(Vector((0,0,-.30))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=10.5
bpy.data.objects['Studio_Floor'].hide_render=True
for clip,end in [('Fire',12),('Reload',90),('Charge',24),('Inspect',60)]:
    folder=ROOT+'/renders/animation/'+clip;os.makedirs(folder,exist_ok=True)
    for ob in s.objects:
        if ob.animation_data:
            for tr in ob.animation_data.nla_tracks:tr.mute=tr.name!=clip
    for frame in range(1,end+1,2):
        s.frame_set(frame);s.render.filepath=folder+'/%04d.png'%((frame+1)//2);bpy.ops.render.render(write_still=True)
print('ANIMATION_RENDERED')
