import bpy,sys,os
PROJECT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
s=bpy.context.scene
args=sys.argv[sys.argv.index('--')+1:]
cams={'01_hero':'Camera_Hero','02_reverse':'Camera_Reverse','03_street':'Camera_Street','04_backyard':'Camera_Backyard','05_topdown':'Camera_Topdown','06_upper_sightline':'Camera_UpperSightline','07_ground_route':'Camera_GroundRoute','08_courtyard':'Camera_Courtyard'}
s.render.image_settings.file_format='PNG';s.cycles.use_denoising=False
for key in args:
 s.camera=bpy.data.objects[cams[key]];s.cycles.samples=192 if key=='08_courtyard' else 96
 s.render.resolution_x=1400 if key=='05_topdown' else 1500;s.render.resolution_y=1700 if key=='05_topdown' else 1000
 s.render.filepath=PROJECT+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
 s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=95;bpy.data.images['Render Result'].save_render(filepath=PROJECT+'/renders/'+key+'.jpg',scene=s);s.render.image_settings.file_format='PNG'
print('GALLERY_COMPLETE',args,flush=True)
