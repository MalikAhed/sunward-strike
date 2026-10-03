import bpy,json,sys,pathlib,hashlib,struct
from mathutils import Vector
out=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');source=pathlib.Path(bpy.data.filepath);hid=source.name.split('-houses-')[0];ver=source.stem.split('-')[-1];root=bpy.data.objects['HOUSE_ROOT_'+hid]
result={'source_name':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'version':root.get('house_version'),'parts':{}}
for o in bpy.data.objects:
 if o.type!='MESH' or not o.name.startswith(('H3_','COL_V3_H3_')):continue
 h=hashlib.sha256()
 for v in o.data.vertices:h.update(struct.pack('<fff',*v.co))
 for p in o.data.polygons:h.update(struct.pack('<'+'I'*len(p.vertices),*p.vertices))
 vv=[o.matrix_world@v.co for v in o.data.vertices]
 result['parts'][o.name]={'part_id':o.get('part_id'), 'hash':h.hexdigest(),'matrix':[list(r) for r in o.matrix_world],'bbox':[[min(v[i] for v in vv) for i in range(3)],[max(v[i] for v in vv) for i in range(3)]]}
(out/(hid+'-'+ver+'-support-source.json')).write_text(json.dumps(result,indent=2)+'\n')
