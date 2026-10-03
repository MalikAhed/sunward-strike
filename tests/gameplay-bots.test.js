import test from 'node:test';
import assert from 'node:assert/strict';
import {BotBrain} from '../src/gameplay/bots.js';
import {WeaponState} from '../src/gameplay/combat.js';
import {SeededRandom} from '../src/gameplay/random.js';
import {GAMEPLAY_TUNING} from '../src/gameplay/tuning.js';
import {WaypointNavigation} from '../src/gameplay/navigation.js';
import {flatWorld} from './helpers/gameplay-world.js';
function actor(id,team,position){return{id,team,position:[...position],eye:[position[0],position[1]+1.64,position[2]],height:1.8,life:1,health:100,alive:true,yaw:0,pitch:0,weapon:new WeaponState('carbine',new SeededRandom(4))};}
function tick(brain,self,target,world,time,dt=1/60){const command=brain.think({time,dt,self,actors:[self,target],tags:[],world});self.yaw=command.yaw;self.pitch=command.pitch;return command;}

test('hidden opponents without visual/noise history cannot be acquired or fired upon',()=>{
 const world=flatWorld({wallZ:-5}),self=actor('bot',0,[0,0,0]),target=actor('target',1,[0,0,-10]),brain=new BotBrain({random:new SeededRandom(7)});
 for(let n=0;n<300;n++){const command=tick(brain,self,target,world,n/60);assert.equal(command.fire,false);assert.equal(brain.memory,null);}
});
test('occluded live movement never refreshes last-seen position and memory decays',()=>{
 const world=flatWorld(),self=actor('bot',0,[0,0,0]),target=actor('target',1,[0,0,-10]),brain=new BotBrain({difficulty:'regular',random:new SeededRandom(9)});
 tick(brain,self,target,world,0);const known=[...brain.memory.position];world.hasLineOfSight=()=>false;target.position=[9,0,-20];target.eye=[9,1.64,-20];
 for(let n=1;n<120;n++){const command=tick(brain,self,target,world,n/60);assert.equal(command.fire,false);assert.deepEqual(brain.memory.position,known);}
 for(let n=120;n<330;n++)tick(brain,self,target,world,n/60);assert.equal(brain.memory,null);
});
test('different hidden trajectories produce identical commands with no secret steering advantage',()=>{
 const histories=[];for(const destination of[[2,0,-7],[-20,0,-30]]){const world=flatWorld({wallZ:-5}),self=actor('bot',0,[0,0,0]),target=actor('target',1,destination),brain=new BotBrain({random:new SeededRandom(11)}),commands=[];for(let n=0;n<90;n++)commands.push(tick(brain,self,target,world,n/60));histories.push(commands);}
 assert.deepEqual(histories[0],histories[1]);
});
test('all difficulty profiles respect reaction delays and angular turn-rate caps',()=>{
 for(const difficulty of['recruit','regular','veteran']){const world=flatWorld(),self=actor('bot',0,[0,0,0]),target=actor('target',1,[3,0,-10]),brain=new BotBrain({difficulty,random:new SeededRandom(33)}),profile=GAMEPLAY_TUNING.difficulty[difficulty];let firstFire=null;
  for(let n=0;n<180;n++){const previous=[self.yaw,self.pitch],command=tick(brain,self,target,world,n/60);const angularStep=Math.hypot(Math.atan2(Math.sin(command.yaw-previous[0]),Math.cos(command.yaw-previous[0])),command.pitch-previous[1]);assert.ok(angularStep<=profile.turnDegrees*Math.PI/180/60+1e-10);if(command.fire&&firstFire===null)firstFire=n/60;}
  assert.notEqual(firstFire,null);assert.ok(firstFire>=profile.reaction[0]);assert.ok(brain.readyAt>=brain.acquiredAt+profile.reaction[0]);
 }
});
test('hearing supplies an uncertain fixed search location rather than hidden live aim',()=>{
 const world=flatWorld({wallZ:-5}),self=actor('bot',0,[0,0,0]),target=actor('target',1,[0,0,-10]),brain=new BotBrain({random:new SeededRandom(5)});brain.hear({position:target.position,team:1},self,0);assert.notDeepEqual(brain.noise.position,target.position);const heard=[...brain.noise.position];target.position=[20,0,-30];for(let n=0;n<60;n++){const command=tick(brain,self,target,world,n/60);assert.equal(command.fire,false);assert.equal(brain.memory,null);}assert.deepEqual(brain.noise.position,heard);
});
test('waypoint A* routes around blocked direct segments and respects per-bot blacklists',()=>{
 const nodes=[[0,0,0],[0,0,-2],[2,0,-2],[2,0,0]],nav=new WaypointNavigation({nodes,edges:[[0,1],[1,2],[2,3]]},{connectRadius:.1,canTraverse:(a,b)=>Math.hypot(a[0]-b[0],a[2]-b[2])<.1});
 const path=nav.findPath(nodes[0],nodes[3]);assert.deepEqual(path.nodeIds,['0','1','2','3']);assert.equal(nav.findPath(nodes[0],nodes[3],{blocked:new Set(['2'])}).points.length,0);
});
