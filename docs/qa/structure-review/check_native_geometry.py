import bpy,json,hashlib,struct,pathlib
out=pathlib.Path('/workspace/shared/sunward-strike/docs/qa/structure-review');p=pathlib.Path(bpy.data.filepath);rows={}
for o in bpy.data.objects:
 if o.type!='MESH' or o.get('native_source_only'):continue
 h=hashlib.sha256()
 for v in o.data.vertices:h.update(struct.pack('<fff',*v.co))
 for f in o.data.polygons:h.update(struct.pack('<'+'I'*len(f.vertices),*f.vertices))
 rows[o.name]={'mesh':h.hexdigest(),'matrix':[list(r) for r in o.matrix_world],'materials':[m.name if m else None for m in o.data.materials]}
r={'source_name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'protected_meshes':rows,'native_revision':bpy.context.scene.get('native_style_revision'),'native_clouds':[o.name for o in bpy.data.objects if o.type=='MESH' and o.get('native_source_only')],'scope':'Read-only protected geometry, transforms and material binding comparison'}
(out/(p.stem+'-native-preservation.json')).write_text(json.dumps(r,indent=2)+'\n')
