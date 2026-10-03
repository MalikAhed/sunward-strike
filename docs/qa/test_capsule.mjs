// Independent Node GLB/Octree smoke checks. This is not browser/playtest evidence.
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { buildCollisionOctree } from '../../src/collision.js';
import { performance } from 'node:perf_hooks';
import { WalkController } from '../../src/physics.js';
const root=path.resolve(import.meta.dirname,'../..');
const data=fs.readFileSync(path.join(root,'public/assets/sunward-collision.glb'));
const asset=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');
asset.scene.updateMatrixWorld(true);
const buildStart=performance.now();const octree=buildCollisionOctree(asset.scene);const buildMs=performance.now()-buildStart;const memoryAfterBuild=process.memoryUsage();
function controller(position,yaw){
 const walker=new WalkController(octree);walker.spawn(new THREE.Vector3(...position));const cameraVector=new THREE.Vector3();
 return {tick(dt,input=0,jump=false){walker.update(dt,{z:input,yaw,jump});},camera(){return walker.cameraPosition(cameraVector).toArray();},get onFloor(){return walker.onFloor;}};
}
const results=[];
function test(name,position,yaw,moveTicks,accept){const c=controller(position,yaw);for(let i=0;i<120;i++)c.tick(1/60);const start=c.camera();for(let i=0;i<moveTicks;i++)c.tick(1/60,1);const end=c.camera();const result={name,start,end,onFloor:c.onFloor,pass:accept(start,end,c.onFloor)};results.push(result);console.log(JSON.stringify(result));}
test('street spawn settles on ground',[-15,1.84,0],0,0,(_s,e,f)=>f&&e[1]>1.5&&e[1]<2.1);
test('north rear doorway without jumping',[-1.25,1.84,-26],Math.PI,90,(s,e,f)=>f&&e[2]>-20.2);
test('south rear doorway without jumping',[1.25,1.84,26],0,90,(s,e,f)=>f&&e[2]<20.2);
test('north spawn cannot walk through rear solid wall',[0,1.84,-31],Math.PI,220,(s,e,f)=>e[1]>1.6&&e[1]<2.1&&e[2]>s[2]+2&&e[2]<-22);
const jumpController=controller([0,1.84,-31],Math.PI);
for(let i=0;i<120;i++)jumpController.tick(1/60);
for(let i=0;i<220;i++)jumpController.tick(1/60,1);
const wallGround=jumpController.camera();let peak=wallGround[1];
for(let i=0;i<30;i++){jumpController.tick(1/60,1,true);peak=Math.max(peak,jumpController.camera()[1]);}
const jumpResult={name:'jump works while holding forward into rear wall',start:wallGround,end:jumpController.camera(),peakCameraY:peak,pass:peak>wallGround[1]+.25};results.push(jumpResult);console.log(JSON.stringify(jumpResult));
const out={buildMs,memoryAfterBuild,collisionStats:octree.stats,method:'Node import of exact collision GLB using Three Octree and imported current src/physics.js WalkController. No browser or visual QA inferred; Node timings are not browser FPS.',passed:results.every(r=>r.pass),results};
fs.writeFileSync(path.join(root,'docs/qa/capsule-results.json'),JSON.stringify(out,null,2)+'\n');
process.exitCode=out.passed?0:1;
