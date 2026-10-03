import {Vector3,Ray} from 'three';
import {Capsule} from 'three/addons/math/Capsule.js';
import {WalkController} from '../physics.js';
import {MAP_CONFIG} from '../map-config.js';
import {MAP_NAVIGATION} from './map-navigation.js';
import {WaypointNavigation} from './navigation.js';
import {buildOpaqueCover} from './cover.js';
import {CapsuleContacts} from './capsule-contacts.js';
import {distance,normalize,sub,finitePoint} from './vectors.js';

// Same static collision and injected controller for every actor. No bot teleport
// or through-wall movement path exists; respawn is the only placement operation.
export function createThreeWorld({tree,Controller=WalkController,mapConfig=MAP_CONFIG,spawnPoints,navigation,coverRoot=null,opaqueCover=null}={}){
  if(!tree?.rayIntersect||!tree?.capsuleIntersect)throw new TypeError('A ready collision octree is required');
  const ray=new Ray(),normal=new Vector3(),contacts=new CapsuleContacts();
  const cover=opaqueCover||(coverRoot?buildOpaqueCover(coverRoot):null);
  const world={
    raycast(origin,direction,maxDistance=Infinity){ray.origin.fromArray(origin);ray.direction.fromArray(direction).normalize();const hit=tree.rayIntersect(ray),physical=hit&&hit.distance<=maxDistance?hit.distance:Infinity;return Math.min(physical,cover?.raycast(origin,direction,Math.min(maxDistance,physical))??Infinity);},
    hasLineOfSight(from,to){const length=distance(from,to);return length<1e-7||world.raycast(from,normalize(sub(to,from)),length)>=length-.025;},
    groundPoint(point){ray.origin.set(point[0],point[1]+.6,point[2]);ray.direction.set(0,-1,0);const hit=tree.rayIntersect(ray);if(!hit||hit.distance>1.2||hit.triangle.getNormal(normal).y<.45)return null;return[point[0],ray.origin.y-hit.distance,point[2]];},
    canStand(point){const foot=world.groundPoint(point);if(!foot)return false;const capsule=new Capsule(new Vector3(foot[0],foot[1]+.36,foot[2]),new Vector3(foot[0],foot[1]+1.46,foot[2]),.35),hit=contacts.intersect(tree,capsule);return !hit||hit.depth<.025||(hit.normal.y>.65&&hit.depth<.08);},
    canTraverse(from,to){const length=distance(from,to);if(length>150)return false;const samples=Math.max(1,Math.ceil(length/.3));for(let i=0;i<=samples;i++){const t=i/samples,point=from.map((v,a)=>v+(to[a]-v)*t),ground=world.groundPoint(point);if(!ground||Math.abs(ground[1]-point[1])>.38||!world.canStand(ground))return false;}return true;},
    createMotor({position}){
      const controller=new Controller(tree,{adsSeconds:.18,sprintToFire:.12}),eye=new Vector3();
      return {
        controller,
        setAlive(alive){controller.setAlive?.(alive);},
        spawn(feet){controller.spawn(new Vector3(feet[0],feet[1]+1.64,feet[2]));},
        update(dt,command){controller.update(dt,command);},
        state(command={}){const {collider}=controller,feet=collider.start.clone();feet.y-=collider.radius;controller.cameraPosition(eye);return {position:feet.toArray(),eye:eye.toArray(),height:collider.end.distanceTo(collider.start)+2*collider.radius,radius:collider.radius,onFloor:controller.onFloor,sprinting:controller.sprinting??(!!command.sprint&&!!controller.onFloor),sliding:!!controller.sliding,crouched:!!controller.crouched,horizontalSpeed:Math.hypot(controller.velocity.x,controller.velocity.z)};},
      };
    },
  };
  const anchors=spawnPoints||[mapConfig.spawns.green_backyard.map((v,i)=>i===1?v-1.64:v),mapConfig.spawns.yellow_backyard.map((v,i)=>i===1?v-1.64:v)];
  const candidates=anchors.map(value=>{const seeds=Array.isArray(value[0])?value:[value],result=[];for(const seed of seeds){if(!finitePoint(seed))throw new TypeError('Spawn points must be finite feet coordinates');for(const [x,z]of[[0,0],[1.6,0],[-1.6,0],[0,1.6],[0,-1.6],[1.6,1.6],[-1.6,-1.6]]){const point=world.groundPoint([seed[0]+x,seed[1],seed[2]+z]);if(point&&world.canStand(point))result.push(point);}}if(!result.length)throw new Error('No safe spawn floor candidates for team');return result;});
  if(candidates.length!==2)throw new Error('Two team spawn lists required');
  world.coverStats=cover?.stats??null;
  world.spawnPoints=team=>candidates[team].map(point=>[...point]);
  world.navigation=navigation||new WaypointNavigation(MAP_NAVIGATION,{canTraverse:(a,b)=>world.canTraverse(a,b),connectRadius:12});
  return world;
}
