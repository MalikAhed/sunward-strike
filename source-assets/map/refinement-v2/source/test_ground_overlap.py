import bpy
s=bpy.context.scene
for o in list(bpy.data.objects):
 if o.name=='PLAYABLE_Base_58x74m':bpy.data.objects.remove(o,do_unlink=True)
s.camera=bpy.data.objects['Camera_Hero'];s.cycles.samples=16;s.cycles.use_denoising=False;s.render.resolution_x=900;s.render.resolution_y=600;s.render.filepath='/workspace/shared/stylized-nuketown-map/refinement-v2/renders/ground_overlap_test.png';bpy.ops.render.render(write_still=True)
