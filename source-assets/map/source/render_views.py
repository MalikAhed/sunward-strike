import bpy,os,sys
root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));s=bpy.context.scene
s.cycles.use_denoising=False;s.cycles.samples=128
s.render.resolution_x=1500;s.render.resolution_y=1000
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['01_hero','02_reverse','03_street','04_backyard','05_topdown','06_upper_sightline','07_ground_route']
cams={'01_hero':'Camera_Hero','02_reverse':'Camera_Reverse','03_street':'Camera_Street','04_backyard':'Camera_Backyard','05_topdown':'Camera_Topdown','06_upper_sightline':'Camera_UpperSightline','07_ground_route':'Camera_GroundRoute'}
for key in args:
 s.camera=bpy.data.objects[cams[key]]
 if key=='05_topdown':s.render.resolution_x=1400;s.render.resolution_y=1700
 else:s.render.resolution_x=1500;s.render.resolution_y=1000
 s.render.filepath=root+'/renders/'+key+'.png';bpy.ops.render.render(write_still=True)
s.camera=bpy.data.objects['Camera_Hero'];bpy.ops.wm.save_as_mainfile(filepath=root+'/Sunward_TestSite.blend')
