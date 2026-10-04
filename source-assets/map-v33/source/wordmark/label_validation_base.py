"""Non-vacuous source preservation; deterministic hashes and complete UV flags."""
import bpy,json,hashlib,numpy as np

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def simple(v):
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 if isinstance(v,bpy.types.ID):return {'id_type':type(v).__name__,'name':v.name}
 try:return [simple(x) for x in v]
 except:return str(v)
def properties(v,exclude=()):
 r={}
 for p in v.bl_rna.properties:
  if p.identifier in {'rna_type',*exclude} or p.type in {'COLLECTION','POINTER'}:continue
  try:r[p.identifier]=simple(getattr(v,p.identifier))
  except (TypeError,AttributeError,ValueError):pass
 return r
EXCLUDE={'users','is_updated','is_updated_data','is_updated_transform','tag','original','session_uid','is_embedded_data'}
def shader(tree):
 if tree is None:return None
 return {'active_node':tree.nodes.active.name if tree.nodes.active else None,'nodes':{n.name:{'type':n.bl_idname,'props':properties(n,{'dimensions'}),'inputs':{i.identifier:simple(i.default_value) for i in n.inputs if hasattr(i,'default_value')},'outputs':{i.identifier:simple(i.default_value) for i in n.outputs if hasattr(i,'default_value')},'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None,'tree':n.node_tree.name if hasattr(n,'node_tree') and n.node_tree else None} for n in tree.nodes},'links':sorted([[l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier] for l in tree.links])}
def material(m):return {'props':properties(m,EXCLUDE),'custom':{k:simple(v) for k,v in m.items()},'tree':shader(m.node_tree)}
def arrhash(data,attr,width,dtype=np.float32):
 a=np.empty(len(data)*width,dtype=dtype);data.foreach_get(attr,a);return hashlib.sha256(a.tobytes()).hexdigest()
def uvs(m):
 return {'active_index':m.uv_layers.active_index,'clone_index':m.uv_layer_clone_index,'stencil_index':m.uv_layer_stencil_index,'layers':[{'name':u.name,'active':u.active,'active_render':u.active_render,'active_clone':u.active_clone,'count':len(u.data),'float32_sha256':arrhash(u.data,'uv',2)} for u in m.uv_layers]}
def mesh(m):
 return {'props':properties(m,EXCLUDE|{'total_vert_sel','total_edge_sel','total_face_sel','uv_layer_clone_index','uv_layer_stencil_index'}),'custom':{k:simple(v) for k,v in m.items()},'vertices':arrhash(m.vertices,'co',3),'edges':arrhash(m.edges,'vertices',2,np.int32),'loops':arrhash(m.loops,'vertex_index',1,np.int32),'faces':digest([(list(p.vertices),p.material_index,p.use_smooth) for p in m.polygons]),'counts':[len(m.vertices),len(m.edges),len(m.loops),len(m.polygons)],'materials':[x.name if x else None for x in m.materials]}
def objects():
 bpy.context.view_layer.update();r={}
 for o in sorted(bpy.data.objects,key=lambda x:x.name):
  d={'type':o.type,'data':o.data.name if o.data else None,'parent':o.parent.name if o.parent else None,'world':[list(x) for x in o.matrix_world],'basis':[list(x) for x in o.matrix_basis],'parent_inverse':[list(x) for x in o.matrix_parent_inverse],'collections':sorted(c.name for c in o.users_collection),'hide_render':o.hide_render,'hide_viewport':o.hide_viewport,'modifiers':[(m.name,m.type,properties(m,{'execution_time'})) for m in o.modifiers],'custom':{k:simple(v) for k,v in o.items()},'slots':[(s.link,s.material.name if s.material else None) for s in o.material_slots]}
  if o.type=='MESH':d['mesh']=mesh(o.data)
  elif o.type=='FONT':d['label']={'text':o.data.body,'props':properties(o.data,EXCLUDE)}
  elif o.type in {'LIGHT','CAMERA'}:d['data_props']=properties(o.data,EXCLUDE)
  r[o.name]=d
 return r
def images():
 r={}
 for i in bpy.data.images:
  if i.type=='RENDER_RESULT':continue
  packed=[]
  if i.packed_file:packed=[hashlib.sha256(i.packed_file.data).hexdigest()]
  elif i.packed_files:packed=[hashlib.sha256(p.packed_file.data).hexdigest() for p in i.packed_files]
  # len(pixels) forces lazy packed data to decode. Never test has_data here.
  n=len(i.pixels);assert n>0,(i.name,'image decode empty')
  a=np.empty(n,dtype=np.float32);i.pixels.foreach_get(a)
  r[i.name]={'packed_sha256':packed,'float32_rgba_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'float_count':n,'size':list(i.size),'source':i.source,'type':i.type,'colorspace':i.colorspace_settings.name,'alpha_mode':i.alpha_mode,'fake_user':bool(i.use_fake_user),'filepath':i.filepath}
 assert len(r)>0,'Image proof cannot be empty'
 return r
def globals():
 s=bpy.context.scene
 return {'world':{'name':s.world.name,'color':list(s.world.color),'tree':shader(s.world.node_tree)},'view':properties(s.view_settings),'display':properties(s.display_settings),'render':properties(s.render),'camera':s.camera.name,'scene_custom':{k:simple(v) for k,v in s.items()},'collections':{c.name:{'objects':sorted(o.name for o in c.objects),'children':sorted(x.name for x in c.children),'hide_viewport':c.hide_viewport,'hide_render':c.hide_render} for c in bpy.data.collections}}
def snapshot():
 o=objects();return {'objects':o,'uvs':{m.name:uvs(m) for m in bpy.data.meshes},'materials':{m.name:material(m) for m in bpy.data.materials},'images':images(),'globals':globals(),'texts':{t.name:{'body_sha256':hashlib.sha256(t.as_string().encode()).hexdigest(),'fake_user':t.use_fake_user} for t in bpy.data.texts},'collision_hash':digest({k:v for k,v in o.items() if k.startswith('COL_')})}
