import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {buildCollisionOctree} from '../src/collision.js';
import {MAP_CONFIG} from '../src/map-config.js';
import {createThreeWorld,OfflineMatch,traceShot} from '../src/gameplay/index.js';
import {PlayerController} from '../src/gameplay/player-controller.js';
import {withinPlayBounds} from '../src/math.js';

const bytes=fs.readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.collision}`,import.meta.url));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
const tree=buildCollisionOctree(gltf.scene);
const world=createThreeWorld({tree,Controller:PlayerController});

test('real-map navigation connects both yards and only assigns standable patrol endpoints',()=>{
 assert.ok(world.navigation.nodes.length>250);
 const path=world.navigation.findPath(world.spawnPoints(0)[0],world.spawnPoints(1)[0]);assert.ok(path.points.length>4,'yard-to-yard route must exist');
 const patrol=world.navigation.patrolPoints();assert.ok(patrol.length>250);for(const point of patrol)assert.equal(world.canStand(point),true);
 for(const team of[0,1])for(const point of world.spawnPoints(team)){assert.ok(withinPlayBounds(point[0],point[2]));assert.equal(world.canStand(point),true);}
});
test('six actors run a complete actual-map TDM with collision movement, fair shots and respawns',()=>{
 const match=new OfflineMatch({world,seed:44,friendlyBots:2,enemyBots:3,timeLimitSeconds:60});match.start();let shots=0,deaths=0,damage=0,firstShot=null,maxBodyStep=0;const maxTravel=new Map(),origins=new Map(match.actors.map(a=>[a.id,[...a.position]])),prior=new Map(match.actors.map(a=>[a.id,{life:a.life,position:[...a.position]}]));
 for(let frame=0;frame<3600;frame++){
  const {snapshot,events}=match.update(1/60,{yaw:0,pitch:0});
  shots+=events.filter(e=>e.type==='shot').length;deaths+=events.filter(e=>e.type==='death').length;damage+=events.filter(e=>e.type==='damage').length;
  if(firstShot===null&&events.some(e=>e.type==='shot'))firstShot=events.find(e=>e.type==='shot').time;
  for(const actor of snapshot.actors){assert.ok(actor.position.every(Number.isFinite));assert.ok(actor.position[1]>-1);assert.ok(withinPlayBounds(actor.position[0],actor.position[2]));const before=prior.get(actor.id);if(before.life===actor.life){const step=Math.hypot(...actor.position.map((v,i)=>v-before.position[i]));maxBodyStep=Math.max(maxBodyStep,step);assert.ok(step<.5,'movement must resolve through shared motor, not teleport');}prior.set(actor.id,{life:actor.life,position:actor.position});maxTravel.set(actor.id,Math.max(maxTravel.get(actor.id)||0,Math.hypot(...actor.position.map((v,i)=>v-origins.get(actor.id)[i]))));}
 }
 assert.equal(match.status,'ended');assert.equal(match.reason,'time-limit');assert.ok(shots>50);assert.ok(deaths>3);assert.ok(damage>deaths);assert.ok(firstShot<30);
 for(const actor of match.actors.filter(a=>a.isBot))assert.ok(maxTravel.get(actor.id)>10,actor.id+' should actually traverse the map');
 assert.equal(match.scores[0]+match.scores[1],deaths);console.log('ACTUAL_MAP_MATCH_SMOKE',{mode:'tdm',actors:6,simulatedSeconds:60,shots,deaths,damage,firstShot,scores:match.scores,maxBodyStep,scope:'Node CPU/controller evidence only; no browser/GPU/input claim'});
});


test('real house wall blocks bidirectional visibility and a target capsule hitscan',()=>{
 const wall=gltf.scene.getObjectByName('COL_V3_H3_A_Mint_EastLower');assert.ok(wall);
 wall.geometry.computeBoundingBox();const box=wall.geometry.boundingBox,extent=box.getSize(new Vector3()),center=box.getCenter(new Vector3()).applyMatrix4(wall.matrixWorld);
 const axes=[extent.x,extent.y,extent.z],thin=axes.indexOf(Math.min(...axes)),normal=new Vector3().setComponent(thin,1).transformDirection(wall.matrixWorld);
 assert.ok(Math.abs(normal.y)<.1,'test requires a vertical wall');
 const from=center.clone().addScaledVector(normal,2).toArray(),to=center.clone().addScaledVector(normal,-2).toArray(),direction=normal.clone().negate().toArray();
 assert.equal(world.hasLineOfSight(from,to),false);assert.equal(world.hasLineOfSight(to,from),false);
 const target={id:'occluded-target',alive:true,position:[to[0],to[1]-1.1,to[2]],height:1.8,radius:.35};
 const shot=traceShot({origin:from,direction,range:10,shooterId:'test-shooter',actors:[target],world});assert.equal(shot.actor,null);assert.equal(shot.hitWorld,true);assert.ok(shot.distance<3.5);
});
