import { Box3, Triangle, Vector3 } from 'three';
import { Octree } from 'three/addons/math/Octree.js';

// The source collider includes large overlapping faces. The stock Octree's
// sixteen levels duplicate these faces exponentially; all descendants must
// share the depth/leaf budget, which the stock split method doesn't propagate.
class BoundedOctree extends Octree {
  constructor(box){super(box);this.maxLevel=5;this.trianglesPerLeaf=32;}
  split(level){
    if(!this.box)return;
    const children=[],half=this.box.getSize(new Vector3()).multiplyScalar(.5);
    for(let x=0;x<2;x++)for(let y=0;y<2;y++)for(let z=0;z<2;z++){
      const min=this.box.min.clone().add(new Vector3(x,y,z).multiply(half));
      children.push(new BoundedOctree(new Box3(min,min.clone().add(half))));
    }
    for(const triangle of this.triangles)for(const child of children)if(child.box.intersectsTriangle(triangle))child.triangles.push(triangle);
    this.triangles.length=0;
    for(const child of children){if(!child.triangles.length)continue;if(child.triangles.length>this.trianglesPerLeaf&&level<this.maxLevel)child.split(level+1);this.subTrees.push(child);}
  }
}
export function buildCollisionOctree(root){
  root.updateWorldMatrix(true,true);
  const tree=new BoundedOctree();let triangleCount=0,mirroredMeshes=0;
  root.traverse(object=>{
    if(!object.isMesh)return;
    const geometry=object.geometry,position=geometry.attributes.position,index=geometry.index;
    const mirrored=object.matrixWorld.determinant()<0;if(mirrored)mirroredMeshes++;
    const count=index?index.count:position.count;
    for(let i=0;i<count;i+=3){
      const a=new Vector3().fromBufferAttribute(position,index?index.getX(i):i).applyMatrix4(object.matrixWorld);
      const b=new Vector3().fromBufferAttribute(position,index?index.getX(i+1):i+1).applyMatrix4(object.matrixWorld);
      const c=new Vector3().fromBufferAttribute(position,index?index.getX(i+2):i+2).applyMatrix4(object.matrixWorld);
      tree.addTriangle(mirrored?new Triangle(a,c,b):new Triangle(a,b,c));triangleCount++;
    }
  });
  tree.build();
  let nodes=0,references=0;const count=(t)=>{nodes++;references+=t.triangles.length;t.subTrees.forEach(count);};count(tree);
  tree.stats=Object.freeze({triangleCount,mirroredMeshes,nodes,references,maxLevel:tree.maxLevel});
  return tree;
}
