"""Read-only source integrity snapshot for the versioned presentation copy."""
import bpy,json,sys,hashlib,array,pathlib
args=sys.argv[sys.argv.index('--')+1:]
def hashed(items,field,code,count):
 a=array.array(code,[0])*count
 items.foreach_get(field,a)
 return hashlib.sha256(a.tobytes()).hexdigest()
def matlist(m):return [[round(v,10) for v in row] for row in m]
def val(v):
 if isinstance(v,(str,int,float,bool)):return v
 if hasattr(v,'__len__'):
  try:return [val(x) for x in v]
  except:return str(v)
 return str(v)
def material(m):
 nodes=[];links=[]
 if m.node_tree:
  for n in m.node_tree.nodes:
   nodes.append({'name':n.name,'type':n.bl_idname,'inputs':{i.name:val(i.default_value) for i in n.inputs if hasattr(i,'default_value')},'image':getattr(getattr(n,'image',None),'name',None)})
  links=sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links)
 return {'diffuse':list(m.diffuse_color),'use_nodes':m.use_nodes,'nodes':sorted(nodes,key=lambda x:x['name']),'links':links}
meshes={}
for m in bpy.data.meshes:
 r={'verts':len(m.vertices),'edges':len(m.edges),'polygons':len(m.polygons),'loops':len(m.loops),
 'vertex_co_sha256':hashed(m.vertices,'co','f',len(m.vertices)*3),'edge_indices_sha256':hashed(m.edges,'vertices','i',len(m.edges)*2),'loop_vertex_indices_sha256':hashed(m.loops,'vertex_index','i',len(m.loops)),
 'polygon_material_indices_sha256':hashed(m.polygons,'material_index','i',len(m.polygons)), 'polygon_smooth_sha256':hashed(m.polygons,'use_smooth','b',len(m.polygons)), 'uv_layers':{},'materials':[x.name if x else None for x in m.materials]}
 for layer in m.uv_layers:
  r['uv_layers'][layer.name]={'active_render':layer.active_render,'uv_sha256':hashed(layer.data,'uv','f',len(layer.data)*2)}
 try:r['corner_normals_sha256']=hashed(m.corner_normals,'vector','f',len(m.corner_normals)*3)
 except Exception as e:r['corner_normals_error']=str(e)
 meshes[m.name]=r
objects={}
for o in bpy.data.objects:
 objects[o.name]={'type':o.type,'data_name':getattr(o.data,'name',None),'matrix_world':matlist(o.matrix_world),'matrix_local':matlist(o.matrix_local),'parent':o.parent.name if o.parent else None,'collections':sorted(c.name for c in o.users_collection),'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'modifiers':[(m.name,m.type) for m in o.modifiers],'material_slots':[s.material.name if s.material else None for s in o.material_slots]}
s=bpy.context.scene
r={'file':bpy.data.filepath,'file_sha256':hashlib.sha256(pathlib.Path(bpy.data.filepath).read_bytes()).hexdigest(),'mesh_count':len(meshes),'object_count':len(objects),'meshes':meshes,'objects':objects,'materials':{m.name:material(m) for m in bpy.data.materials},'packed_images':{i.name:hashlib.sha256(i.packed_file.data).hexdigest() if i.packed_file else None for i in bpy.data.images},'scene':{'name':s.name,'camera':s.camera.name if s.camera else None,'world':s.world.name if s.world else None,'render_engine':s.render.engine,'color_management':{'view_transform':s.view_settings.view_transform,'look':s.view_settings.look,'exposure':s.view_settings.exposure,'gamma':s.view_settings.gamma}}}
pathlib.Path(args[0]).write_text(json.dumps(r,indent=2,default=str)+'\n')
print('SNAPSHOT_COMPLETE',len(objects),len(meshes),args[0])
