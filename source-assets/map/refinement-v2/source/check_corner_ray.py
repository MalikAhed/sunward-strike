import bpy
from mathutils import Vector
s=bpy.context.scene;cam=bpy.data.objects['Camera_Courtyard'];dg=bpy.context.evaluated_depsgraph_get();f=cam.data.view_frame(scene=s)
for x,y in [(883,750),(890,760),(878,790),(869,768),(900,760)]:
 u=x/1500;v=1-y/1000
 xmin=min(a.x for a in f);xmax=max(a.x for a in f);ymin=min(a.y for a in f);ymax=max(a.y for a in f)
 d=Vector((xmin+(xmax-xmin)*u,ymin+(ymax-ymin)*v,f[0].z));direction=(cam.matrix_world.to_3x3()@d).normalized()
 hit,loc,n,idx,o,m=s.ray_cast(dg,cam.location,direction)
 print('CORNER_RAY',x,y,hit,tuple(loc),o.name if o else None,tuple(n))
