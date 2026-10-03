import {Group,Mesh,BufferGeometry,DoubleSide,BackSide,Ray,Vector3} from 'three';
import {buildCollisionOctree} from '../collision.js';

// Hard-cover queries are distinct from capsule movement. Decorative leaf/grass
// cards and blended/sky layers are not turned into invisible solid cover.
export function isOpaqueCoverMaterial(material,object){
  if(!material||material.visible===false||material.transparent||material.opacity<.999||material.alphaTest>0)return false;
  if(object.userData?.exclude_from_glb||object.userData?.native_source_only||object.userData?.nonSolidVegetation)return false;
  if(/Leaf|Lawn_Blade|GrassBlade|GrassTuft|^V3_Grass_/i.test(material.name)||/^35_Layout_Grass/.test(object.name))return false;
  if(material.isShaderMaterial||/Sky|Cloud|Horizon/.test(material.name))return false;
  return true;
}
export function buildOpaqueCover(root,{filter=isOpaqueCoverMaterial}={}){
  if(!root?.traverse)throw new TypeError('Visual cover needs the actual loaded map root');
  root.updateWorldMatrix(true,true);
  const groups=[new Group(),new Group()],accepted=[],excluded=[];let sourceTriangles=0;
  root.traverse(object=>{
    if(!object.isMesh)return;
    for(let parent=object;parent;parent=parent.parent){if(parent.visible===false)return;if(parent===root)break;}
    const geometry=object.geometry,positions=geometry.attributes.position,index=geometry.index,total=index?index.count:positions.count,drawStart=geometry.drawRange.start||0,drawEnd=Math.min(total,drawStart+geometry.drawRange.count),indices=[[],[]];
    for(const group of geometry.groups.length?geometry.groups:[{start:0,count:total,materialIndex:0}]){
      const material=Array.isArray(object.material)?object.material[group.materialIndex]:object.material;
      if(!filter(material,object)){excluded.push({object:object.name,material:material?.name||'',reason:'not static opaque hard cover'});continue;}
      if(object.isSkinnedMesh||object.isInstancedMesh)throw new Error('Cover source must contain resolved static meshes: '+object.name);
      const start=Math.max(group.start,drawStart),end=Math.min(group.start+group.count,drawEnd),side=material.side===DoubleSide?1:0;
      if(start%3!==0||end%3!==0)throw new Error('Cover geometry must use complete triangle groups');
      let count=0;
      for(let i=start;i<end;i+=3){const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2;
        if(material.side===BackSide)indices[side].push(a,c,b);else indices[side].push(a,b,c);count++;
      }
      sourceTriangles+=count;accepted.push({object:object.name,material:material.name,sourceTriangles:count,doubleSided:side===1});
    }
    for(let side=0;side<2;side++)if(indices[side].length){const copied=new BufferGeometry();copied.setAttribute('position',positions);copied.setIndex(indices[side]);const mesh=new Mesh(copied);mesh.name=object.name;mesh.matrixAutoUpdate=false;mesh.matrix.copy(object.matrixWorld);groups[side].add(mesh);}
  });
  const start=performance.now(),trees=groups.map((group,index)=>group.children.length?{tree:buildCollisionOctree(group),backfaceCulling:index===0}:null).filter(Boolean),buildMs=performance.now()-start;
  const stats={triangleCount:0,mirroredMeshes:0,nodes:0,references:0,maxLevel:5,sourceTriangles,meshes:groups.reduce((sum,group)=>sum+group.children.length,0),buildMs,accepted,excluded};
  for(const {tree}of trees)for(const key of['triangleCount','mirroredMeshes','nodes','references'])stats[key]+=tree.stats[key];
  const ray=new Ray(new Vector3(),new Vector3()),point=new Vector3(),boxPoint=new Vector3(),seen=new Set();
  return {
    trees,
    stats:Object.freeze(stats),
    raycast(origin,direction,maxDistance=Infinity){
      ray.origin.fromArray(origin);ray.direction.fromArray(direction).normalize();seen.clear();let closest=maxDistance,found=false;
      // Reuse the bounded spatial partition, but avoid Octree's quadratic
      // indexOf de-duplication and duplicated triangles for double-sided faces.
      function visit(node,backfaceCulling){
        if(node.box){const hit=ray.intersectBox(node.box,boxPoint);if(!hit)return;if(!node.box.containsPoint(ray.origin)&&hit.distanceToSquared(ray.origin)>closest*closest)return;}
        for(const triangle of node.triangles){if(seen.has(triangle))continue;seen.add(triangle);const hit=ray.intersectTriangle(triangle.a,triangle.b,triangle.c,backfaceCulling,point);if(hit){const distance=hit.distanceTo(ray.origin);if(distance<=closest){closest=distance;found=true;}}}
        for(const child of node.subTrees)visit(child,backfaceCulling);
      }
      for(const {tree,backfaceCulling}of trees)visit(tree,backfaceCulling);
      return found?closest:Infinity;
    },
  };
}
