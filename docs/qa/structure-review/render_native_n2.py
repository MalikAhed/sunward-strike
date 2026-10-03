import bpy,pathlib
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=1200;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.filepath='/workspace/shared/sunward-strike/docs/qa/structure-review/native-n2-independent-street.png';bpy.ops.render.render(write_still=True)
