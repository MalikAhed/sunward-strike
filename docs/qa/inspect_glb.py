"""Read-only independent GLB inspection. Does not modify assets."""
from pathlib import Path
import json,struct,hashlib
import numpy as np

SOURCES={
 'map':Path('/workspace/shared/stylized-nuketown-map/exports/Sunward_Environment.glb'),
 'rifle':Path('/workspace/shared/blender-game-rifle/exports/compact_carbine.glb'),
}

def load(path):
 b=path.read_bytes();magic,version,total=struct.unpack_from('<III',b)
 assert magic==0x46546c67 and version==2 and total==len(b)
 n,tag=struct.unpack_from('<II',b,12);assert tag==0x4e4f534a
 j=json.loads(b[20:20+n]);pos=20+n
 n,tag=struct.unpack_from('<II',b,pos);assert tag==0x004e4942
 return j,b[pos+8:pos+8+n],b

def matrix(node):
 if 'matrix' in node:return np.array(node['matrix']).reshape((4,4),order='F')
 x,y,z,w=node.get('rotation',[0,0,0,1]);m=np.eye(4)
 m[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
             [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
             [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
 m[:3,:3]@=np.diag(node.get('scale',[1,1,1]))
 m[:3,3]=node.get('translation',[0,0,0]);return m

def report(path):
 j,bb,b=load(path);bounds=[];meshes=[];negative=[];triangles=0
 def visit(i,parent):
  nonlocal triangles
  node=j['nodes'][i];world=parent@matrix(node)
  if np.linalg.det(world[:3,:3])<0:negative.append(node.get('name',str(i)))
  if 'mesh' in node:
   mb=[]
   for p in j['meshes'][node['mesh']]['primitives']:
    a=j['accessors'][p['attributes']['POSITION']]
    mn=np.array(a['min']);mx=np.array(a['max'])
    corners=np.array([[x,y,z,1] for x in [mn[0],mx[0]] for y in [mn[1],mx[1]] for z in [mn[2],mx[2]]])
    transformed=(world@corners.T).T[:,:3];mb.extend(transformed)
    triangles+=(j['accessors'][p['indices']]['count'] if 'indices' in p else a['count'])//3
   mb=np.array(mb);bounds.extend(mb)
   meshes.append({'name':node.get('name'), 'bounds':[mb.min(axis=0).tolist(),mb.max(axis=0).tolist()]})
  for child in node.get('children',[]):visit(child,world)
 for i in j['scenes'][j.get('scene',0)]['nodes']:visit(i,np.eye(4))
 bounds=np.array(bounds)
 return {'path':str(path),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),
  'build_version':j.get('scenes',[{}])[j.get('scene',0)].get('extras',{}).get('build_version'),
  'world_bounds':[bounds.min(axis=0).tolist(),bounds.max(axis=0).tolist()],
  'dimensions':(bounds.max(axis=0)-bounds.min(axis=0)).tolist(),
  'triangles':triangles,'mesh_count':len(j.get('meshes',[])),
  'node_count':len(j.get('nodes',[])),'primitives':sum(len(m['primitives']) for m in j.get('meshes',[])),
  'materials':len(j.get('materials',[])),'images':len(j.get('images',[])),
  'external_uris':[x['uri'] for kind in ['images','buffers'] for x in j.get(kind,[]) if 'uri' in x and not x['uri'].startswith('data:')],
  'negative_determinant_nodes':negative, 'meshes':meshes,
  'animations':[a.get('name') for a in j.get('animations',[])],
  'extensions':j.get('extensionsUsed',[])}

if __name__=='__main__':
 results={k:report(p) for k,p in SOURCES.items()}
 out=Path(__file__).parent/'asset-inspection.json';out.write_text(json.dumps(results,indent=2)+'\n')
 for k,v in results.items():print(k,{x:y for x,y in v.items() if x not in ['meshes','negative_determinant_nodes']});print('negative transforms',len(v['negative_determinant_nodes']))
