import {distance,normalize,sub} from '../../src/gameplay/vectors.js';
export function flatWorld({wallZ=null,spawns=[[[0,0,8],[3,0,8],[-3,0,8]],[[0,0,-12],[3,0,-12],[-3,0,-12]]]}={}){
 const world={
  raycast(origin,direction,range=Infinity){if(wallZ===null||Math.abs(direction[2])<1e-9)return Infinity;const t=(wallZ-origin[2])/direction[2];return t>=0&&t<=range?t:Infinity;},
  hasLineOfSight(a,b){const d=distance(a,b);return d<1e-8||world.raycast(a,normalize(sub(b,a)),d)>=d-.025;},
  canTraverse(a,b){return world.hasLineOfSight(a,b);},spawnPoints:team=>spawns[team].map(p=>[...p]),
  createMotor(){let position=[0,0,0],state={};return{
   spawn(point){position=[...point];state={};},
   update(dt,command){const n=Math.max(1,Math.hypot(command.x,command.z)),speed=command.sprint?7.1:4.4,dx=(Math.cos(command.yaw)*command.x-Math.sin(command.yaw)*command.z)/n*speed*dt,dz=(-Math.sin(command.yaw)*command.x-Math.cos(command.yaw)*command.z)/n*speed*dt;const proposed=[position[0]+dx,0,position[2]+dz];if(world.canTraverse(position,proposed))position=proposed;state={sprinting:!!command.sprint,sliding:false,crouched:false,horizontalSpeed:Math.hypot(dx,dz)/dt};},
   state(){return{position:[...position],eye:[position[0],position[1]+1.64,position[2]],height:1.8,radius:.35,onFloor:true,...state};},
  };},
 };
 world.navigation={patrolPoints:()=>spawns.flat().map(p=>[...p]),findPath:(a,b)=>({points:world.canTraverse(a,b)?[[...b]]:[],nodeIds:[]})};return world;
}
export function place(actor,position){actor.motor.spawn(position);Object.assign(actor,actor.motor.state());}
export function idle(actor){if(actor.brain)actor.brain.think=()=>({x:0,z:0,yaw:actor.yaw,pitch:actor.pitch,fire:false});}
export function run(match,seconds,fps=60,command={}){const events=[];for(let i=0;i<Math.round(seconds*fps);i++)events.push(...match.update(1/fps,command).events);return events;}
