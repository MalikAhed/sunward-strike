import {Ray,Vector3} from 'three';

// Candidate-only static index over the exact production cover triangles.
// It never changes mesh transforms, material sidedness or movement collision.
export function makeBvhCoverRaycast(cover,{leafSize=8}={}){
 if(!Number.isInteger(leafSize)||leafSize<1)throw new RangeError('Positive integer leaf size required');
 // Bind before the owner replaces cover.raycast; fallback must never recurse.
 const baselineRaycast=cover.raycast.bind(cover);
 const triangles=[],sides=[],seen=new Set();
 function collect(node,backfaceCulling){for(const triangle of node.triangles)if(!seen.has(triangle)){seen.add(triangle);triangles.push(triangle);sides.push(backfaceCulling);}for(const child of node.subTrees)collect(child,backfaceCulling);}
 for(const {tree,backfaceCulling}of cover.trees)collect(tree,backfaceCulling);
 seen.clear();
 const count=triangles.length,indices=Uint32Array.from({length:count},(_,i)=>i);let triangleBounds=new Float64Array(count*6),centers=new Float64Array(count*3);
 for(let i=0;i<count;i++){
  const {a,b,c}=triangles[i];
  for(let axis=0;axis<3;axis++){const key=['x','y','z'][axis],lo=Math.min(a[key],b[key],c[key]),hi=Math.max(a[key],b[key],c[key]);triangleBounds[i*6+axis]=lo;triangleBounds[i*6+axis+3]=hi;centers[i*3+axis]=(lo+hi)/2;}
 }
 let bounds=new Float64Array(Math.max(1,count*2)*6),left=new Int32Array(Math.max(1,count*2)),right=new Int32Array(Math.max(1,count*2)),starts=new Uint32Array(Math.max(1,count*2)),sizes=new Uint32Array(Math.max(1,count*2)),nodes=0,maxDepth=0;
 function build(start,end,depth){
  const node=nodes++,offset=node*6;maxDepth=Math.max(maxDepth,depth);let cmin=[Infinity,Infinity,Infinity],cmax=[-Infinity,-Infinity,-Infinity];
  bounds.fill(Infinity,offset,offset+3);bounds.fill(-Infinity,offset+3,offset+6);
  for(let j=start;j<end;j++){const id=indices[j];for(let axis=0;axis<3;axis++){bounds[offset+axis]=Math.min(bounds[offset+axis],triangleBounds[id*6+axis]);bounds[offset+axis+3]=Math.max(bounds[offset+axis+3],triangleBounds[id*6+axis+3]);cmin[axis]=Math.min(cmin[axis],centers[id*3+axis]);cmax[axis]=Math.max(cmax[axis],centers[id*3+axis]);}}
  // Triangle arithmetic can accept a point one ULP outside its exact AABB.
  // Expand only the broadphase conservatively; keep final triangle/cutoff
  // comparisons exact. Scale the slack for translated/scaled coordinates.
  for(let axis=0;axis<3;axis++){const padding=1e-9+8*Number.EPSILON*Math.max(1,Math.abs(bounds[offset+axis]),Math.abs(bounds[offset+axis+3]));bounds[offset+axis]-=padding;bounds[offset+axis+3]+=padding;}
  if(end-start<=leafSize){starts[node]=start;sizes[node]=end-start;left[node]=right[node]=-1;return node;}
  let axis=0;for(let a=1;a<3;a++)if(cmax[a]-cmin[a]>cmax[axis]-cmin[axis])axis=a;
  indices.subarray(start,end).sort((a,b)=>centers[a*3+axis]-centers[b*3+axis]||a-b);
  const middle=(start+end)>>>1;left[node]=build(start,middle,depth+1);right[node]=build(middle,end,depth+1);return node;
 }
 if(count)build(0,count,0);
 bounds=bounds.slice(0,nodes*6);left=left.slice(0,nodes);right=right.slice(0,nodes);starts=starts.slice(0,nodes);sizes=sizes.slice(0,nodes);
 // Build-only buffers must not stay reachable through the query closure.
 triangleBounds=null;centers=null;
 const ray=new Ray(new Vector3(),new Vector3()),point=new Vector3(),stack=new Int32Array(Math.max(1,maxDepth+2)),entries=new Float64Array(stack.length),originValues=[0,0,0],inverse=[0,0,0];
 function entry(node,limit){
  let near=0,far=limit+1e-9;const offset=node*6;
  for(let axis=0;axis<3;axis++){
   const origin=originValues[axis],inv=inverse[axis],lo=bounds[offset+axis],hi=bounds[offset+axis+3];
   if(!Number.isFinite(inv)){if(origin<lo||origin>hi)return Infinity;continue;}
   let a=(lo-origin)*inv,b=(hi-origin)*inv;if(a>b){const swap=a;a=b;b=swap;}near=Math.max(near,a);far=Math.min(far,b);if(near>far)return Infinity;
  }
  return near;
 }
 const raycast=function(origin,direction,maxDistance=Infinity){
  if(!count)return Infinity;
  ray.origin.fromArray(origin);ray.direction.fromArray(direction).normalize();
  // Three's squared-length normalization can underflow/overflow for finite
  // extreme vectors. Then slab parameters are not world distances. Preserve
  // the original backend for those exceptional normalized directions.
  const normalizedLengthSquared=ray.direction.lengthSq();
  if(!Number.isFinite(normalizedLengthSquared)||Math.abs(normalizedLengthSquared-1)>1e-12)return baselineRaycast(origin,direction,maxDistance);
  originValues[0]=ray.origin.x;originValues[1]=ray.origin.y;originValues[2]=ray.origin.z;inverse[0]=1/ray.direction.x;inverse[1]=1/ray.direction.y;inverse[2]=1/ray.direction.z;
  let closest=maxDistance,found=false,length=0;const first=entry(0,closest);if(!Number.isFinite(first))return Infinity;stack[length]=0;entries[length++]=first;
  while(length){const slot=--length,node=stack[slot];if(entries[slot]>closest+1e-9)continue;
   if(sizes[node]){
    const end=starts[node]+sizes[node];for(let j=starts[node];j<end;j++){const id=indices[j],triangle=triangles[id],hit=ray.intersectTriangle(triangle.a,triangle.b,triangle.c,sides[id],point);if(hit){const distance=hit.distanceTo(ray.origin);if(distance<=closest){closest=distance;found=true;}}}
   }else{
    const a=left[node],b=right[node],da=entry(a,closest),db=entry(b,closest);
    if(da<=db){if(Number.isFinite(db)){stack[length]=b;entries[length++]=db;}if(Number.isFinite(da)){stack[length]=a;entries[length++]=da;}}
    else{if(Number.isFinite(da)){stack[length]=a;entries[length++]=da;}if(Number.isFinite(db)){stack[length]=b;entries[length++]=db;}}
   }
  }
  return found?closest:Infinity;
 };
 raycast.indexStats=Object.freeze({triangleCount:count,nodes,maxDepth,leafSize,typedArrayBytes:bounds.byteLength+left.byteLength+right.byteLength+starts.byteLength+sizes.byteLength+indices.byteLength+stack.byteLength+entries.byteLength,triangleReferenceCount:triangles.length,scope:'Additional index; production octree is retained in this isolated experiment'});
 return raycast;
}
