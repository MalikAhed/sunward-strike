// Structural collider regressions against the current map config.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {Capsule} from 'three/addons/math/Capsule.js';
import {BoxGeometry,Group,Mesh,MeshBasicMaterial,PlaneGeometry,Ray,Vector3} from 'three';
import {buildCollisionOctree} from '../src/collision.js';
import {WalkController} from '../src/physics.js';
import {MAP_CONFIG} from '../src/map-config.js';

const bytes=fs.readFileSync(new URL('../public/assets/'+MAP_CONFIG.assets.collision,import.meta.url));
const metadata=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
const collision=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const started=performance.now(),tree=buildCollisionOctree(collision.scene),buildMs=performance.now()-started;
const radius=MAP_CONFIG.player.radius;
const foot=player=>player.collider.start.clone().add(new Vector3(0,-radius,0));
function inside(x,z){let c=false;const p=MAP_CONFIG.outline;for(let i=0,j=p.length-1;i<p.length;j=i++){const a=p[i],b=p[j];if(((a[1]>z)!==(b[1]>z))&&(x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]))c=!c;}return c;}
function spawn(position,octree=tree){const p=new WalkController(octree);p.spawn(new Vector3(...position));for(let i=0;i<120;i++)p.update(1/60);return p;}

test('current GLB collider identity is v3-only and budget stays bounded',()=>{
 let meshes=0;collision.scene.traverse(o=>{if(o.isMesh){meshes++;assert.ok(o.name.startsWith('COL_V3_'),o.name);}});
 assert.ok(meshes>0);assert.ok(!(metadata.nodes||[]).some(n=>n.name==='COL_Sunward_Static'));
 const triangles=metadata.meshes.flatMap(m=>m.primitives).reduce((sum,p)=>sum+metadata.accessors[p.indices??p.attributes.POSITION].count/3,0);
 assert.equal(tree.stats.triangleCount,triangles);assert.ok(triangles>0&&triangles<=20000);assert.ok(tree.stats.nodes<40000);assert.ok(tree.stats.references<200000);assert.ok(buildMs<5000);
 assert.equal(metadata.scenes[metadata.scene||0].extras.build_version,MAP_CONFIG.version);
});

test('all six synthetic box faces retain outward collision, mirrored and unmirrored',()=>{
 const faces=[{name:'+X',start:[1.34,.5,0],end:[1.34,1.6,0],normal:[1,0,0]},{name:'-X',start:[-1.34,.5,0],end:[-1.34,1.6,0],normal:[-1,0,0]},{name:'+Y',start:[0,4.34,0],end:[0,5.44,0],normal:[0,1,0]},{name:'-Y',start:[0,-1.44,0],end:[0,-.34,0],normal:[0,-1,0]},{name:'+Z',start:[0,.5,1.34],end:[0,1.6,1.34],normal:[0,0,1]},{name:'-Z',start:[0,.5,-1.34],end:[0,1.6,-1.34],normal:[0,0,-1]}];
 for(const scale of [1,-1]){const root=new Group(),box=new Mesh(new BoxGeometry(2,4,2),new MeshBasicMaterial());box.position.y=2;box.scale.x=scale;root.add(box);const octree=buildCollisionOctree(root);assert.equal(octree.stats.mirroredMeshes,scale<0?1:0);assert.ok(octree.stats.nodes<100&&octree.stats.references<100);
  for(const face of faces){const capsule=new Capsule(new Vector3(...face.start),new Vector3(...face.end),.35),hit=octree.capsuleIntersect(capsule);assert.ok(hit,`missing${face.name} face, scale${scale}`);assert.ok(hit.normal.dot(new Vector3(...face.normal))>.9,`wrong${face.name} winding, scale${scale}`);assert.ok(hit.depth<.05);}
 }
});

for(const[name,position]of Object.entries(MAP_CONFIG.spawns))test(`actual controller ${name} spawn settles on its authored support surface`,()=>{
 assert.ok(inside(position[0],position[2]));const ray=new Ray(new Vector3(...position),new Vector3(0,-1,0)),surface=tree.rayIntersect(ray);assert.ok(surface);assert.ok(surface.triangle.getNormal(new Vector3()).y>.45);
 const expected=position[1]-surface.distance,player=spawn(position),feet=foot(player);assert.equal(player.onFloor,true);assert.ok(Math.abs(feet.y-expected)<.03);assert.ok(Math.abs(feet.x-position[0])<.1&&Math.abs(feet.z-position[2])<.1);
 const probe=new Capsule(new Vector3(feet.x,expected+radius-.01,feet.z),new Vector3(feet.x,expected+MAP_CONFIG.player.height-radius-.01,feet.z),radius),hit=tree.capsuleIntersect(probe);assert.ok(hit&&hit.normal.y>.9);assert.ok(hit.depth<.05);
});

test('actual street spawn walks westward while retaining floor contact',()=>{
 const player=spawn(MAP_CONFIG.spawns.street),before=foot(player);for(let i=0;i<30;i++)player.update(1/60,{x:-1,z:0});const after=foot(player);assert.ok(after.x<before.x-1);assert.ok(Math.abs(after.y-before.y)<.1);assert.equal(player.onFloor,true);assert.ok(inside(after.x,after.z));
});

test('all canonical perimeter segments block actual controller on isolated floor/outline',()=>{
 const root=new Group();collision.scene.updateWorldMatrix(true,true);collision.scene.traverse(o=>{if(o.isMesh&&['COL_V3_LAYOUT_PlayableFloor','COL_V3_LAYOUT_OutlineClips'].includes(o.name)){const cp=o.clone();cp.matrixAutoUpdate=false;cp.matrix.copy(o.matrixWorld);root.add(cp);}});
 assert.equal(root.children.length,2);const octree=buildCollisionOctree(root),outline=MAP_CONFIG.outline;
 for(let i=0;i<outline.length;i++){
  const a=outline[i],b=outline[(i+1)%outline.length],mid=new Vector3((a[0]+b[0])/2,MAP_CONFIG.floorY,(a[1]+b[1])/2),inward=new Vector3(-(b[1]-a[1]),0,b[0]-a[0]).normalize();
  if(!inside(mid.x+inward.x*.9,mid.z+inward.z*.9))inward.negate();const feet=mid.clone().addScaledVector(inward,.9);assert.ok(inside(feet.x,feet.z),`edge${i} test origin`);
  const player=spawn([feet.x,feet.y+MAP_CONFIG.player.eyeHeight,feet.z],octree);for(let j=0;j<150;j++)player.update(1/60,{x:-inward.x,z:inward.z,yaw:0});const final=foot(player);assert.ok(inside(final.x,final.z),`escaped edge${i}`);assert.ok(final.clone().sub(mid).dot(inward)>=.30,`crossed wall safe center margin at edge${i}`);assert.equal(player.onFloor,true,`lost floor at edge${i}`);
 }
});

test('synthetic wall/floor corner keeps ground contact and permits a jump',()=>{
 const root=new Group(),floor=new Mesh(new PlaneGeometry(10,10),new MeshBasicMaterial()),wall=new Mesh(new BoxGeometry(.2,4,10),new MeshBasicMaterial());floor.rotation.x=-Math.PI/2;wall.position.set(2,2,0);root.add(floor,wall);
 const player=spawn([0,1.64,0],buildCollisionOctree(root));for(let i=0;i<120;i++)player.update(1/60,{x:1});assert.equal(player.onFloor,true);assert.ok(foot(player).x<1.56);
 const startY=foot(player).y;let peakY=startY;for(let i=0;i<30;i++){player.update(1/60,{x:1,jump:i===0});peakY=Math.max(peakY,foot(player).y);}assert.ok(peakY>startY+.5);assert.ok(foot(player).x<1.56);
});
console.log('COLLISION_BUILD_STATS',{...tree.stats,buildMs,mapVersion:MAP_CONFIG.version});
