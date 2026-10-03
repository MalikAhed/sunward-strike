import bpy,os
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=96
s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
s.camera=bpy.data.objects['Camera_Courtyard'];s.render.filepath='/workspace/shared/stylized-nuketown-map/refinement-v2/renders/eevee_test.png'
bpy.ops.render.render(write_still=True)
