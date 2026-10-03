"""Read-only independent saved-house geometry and targeted render check."""
import bpy,json,pathlib,sys,hashlib,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');source=pathlib.Path(bpy.data.filepath);hid=next(o['house_id'] for o in bpy.data.objects if o.name.startswith('HOUSE_ROOT_'));contract=json.loads((source.parent/(hid+'-report-r7.json')).read_text());s=bpy.context.scene
root=bpy.data.objects['HOUSE_ROOT_'+hid];verts=lambda o:[o.matrix_world@v.co for v in o.data.vertices]
parts=[o for o in bpy.data.objects if o.type=='MESH' and o.get('house_id')==hid and not o.name.startswith('COL_')];colliders=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('COL_V3_H3_')]
connector=next(o for o in parts if o.get('part_id')=='RearStairSideConnector');cv=verts(connector);support_width=max(v.y for v in cv)-min(v.y for v in cv)
trees=[];badvol=[]
for o in colliders:
 vv=verts(o);ff=[list(p.vertices) for p in o.data.polygons];volume=sum(vv[f[0]].dot(vv[f[i]].cross(vv[f[i+1]]))/6 for f in ff for i in range(1,len(f)-1))
 if volume<=0:badvol.append({'name':o.name,'volume':volume})
 trees.append((o.name,BVHTree.FromPolygons(vv,ff)))
portals=[]
for name,p in contract['portals'].items():
 normal=Vector((1,0,0)) if name=='garage_connector' else Vector((0,1,0));tangent=Vector((0,1,0)) if name=='garage_connector' else Vector((1,0,0));blockers=[]
 for offset in [-.30,0,.30]:
  for height in [.4,1,1.7,1.8]:
   origin=Vector(p['center'])+tangent*offset+Vector((0,0,height))-normal*.36
   for collider,t in trees:
    hit,_,_,_=t.ray_cast(origin,normal,.72)
    if hit is not None:blockers.append({'offset':offset,'height':height,'collider':collider})
 portals.append({'name':name,'sample_offsets_m':[-.30,0,.30],'sample_heights_m':[.4,1,1.7,1.8],'blockers':blockers,'pass':not blockers})
pad=next(o for o in parts if o.get('part_id')=='RearStairBottomLanding');pv=verts(pad);pad_bbox=[[min(v[i] for v in pv) for i in range(3)],[max(v[i] for v in pv) for i in range(3)]]
report={'rear_bottom_pad_bbox':pad_bbox,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'house_id':hid,'version':root.get('house_version'),'expected_frame_version':contract['layout_frame_version'],'root_identity':all(abs(root.matrix_world[i][j]-(1 if i==j else 0))<1e-6 for i in range(4) for j in range(4)),'visual_objects':len(parts),'collision_objects':len(colliders),'rear_side_connector_support_width_m':support_width,'canonical_minimum_route_width_m':1.1,'negative_or_zero_proxy_volume':badvol,'portal_cross_section_ray_samples':portals,'scope':'saved local prefab geometry and grid-ray aperture checks; actual controller sweeps remain separate'}
(OUT/(hid+'-r7-independent-geometry.json')).write_text(json.dumps(report,indent=2)+'\n');assert report['root_identity'] and support_width>=1.1 and not badvol
cam=s.camera;cx=(contract['main_body_bbox_local_m'][0][0]+contract['main_body_bbox_local_m'][1][0])/2;y1=contract['main_body_bbox_local_m'][1][1];cam.location=(18,y1+25,9);cam.rotation_euler=(Vector((cx,y1,3.1))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=46
for o in colliders:o.hide_render=True
s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=1100;s.render.resolution_y=750;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.filepath=str(OUT/(hid+'-r7-independent-rear.png'));bpy.ops.render.render(write_still=True)
print('HOUSE_REVIEW',json.dumps({k:v for k,v in report.items() if k!='portal_cross_section_ray_samples'}))
