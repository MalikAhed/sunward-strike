"""Extend the exact source audit with every mesh attribute payload and selection."""
import label_validation_base as core
from label_validation_base import *
import bpy,numpy as np,hashlib

def attribute_state(mesh):
 r={'active_index':mesh.attributes.active_index,'items':{}}
 kinds={'FLOAT':('value',1,np.float32),'INT':('value',1,np.int32),'INT8':('value',1,np.int8),'BOOLEAN':('value',1,np.bool_),'FLOAT_VECTOR':('vector',3,np.float32),'FLOAT2':('vector',2,np.float32),'FLOAT_COLOR':('color',4,np.float32),'BYTE_COLOR':('color',4,np.float32),'QUATERNION':('value',4,np.float32),'INT32_2D':('value',2,np.int32),'FLOAT4X4':('value',16,np.float32)}
 for a in mesh.attributes:
  meta={'type':a.data_type,'domain':a.domain,'count':len(a.data),'internal':a.is_internal,'required':a.is_required}
  if a.data_type in kinds:
   field,width,dtype=kinds[a.data_type];v=np.empty(len(a.data)*width,dtype=dtype);a.data.foreach_get(field,v);meta['payload_sha256']=hashlib.sha256(v.tobytes()).hexdigest()
  else:meta['payload_sha256']=digest([properties(d) for d in a.data])
  r['items'][a.name]=meta
 return r

def snapshot():
 s=core.snapshot();s['attributes']={m.name:attribute_state(m) for m in bpy.data.meshes};return s
