import test from 'node:test';import assert from'node:assert/strict';import fs from'node:fs';
import{BotBrain}from'../src/gameplay/bots.js';import{GAMEPLAY_TUNING}from'../src/gameplay/tuning.js';import{WeaponState}from'../src/gameplay/combat.js';import{SeededRandom}from'../src/gameplay/random.js';
import{flatWorld}from'./helpers/gameplay-world.js';
const BASE=JSON.parse(fs.readFileSync(new URL('./fixtures/kc-objective-baseline-tuning.json',import.meta.url),'utf8'));
function setup(difficulty='regular'){const self={id:'bot',team:0,alive:true,life:1,health:100,position:[0,0,0],eye:[0,1.64,0],height:1.8,yaw:0,pitch:0,weapon:new WeaponState('carbine',new SeededRandom(4))},enemy={...self,id:'enemy',team:1,position:[0,0,-12],eye:[0,1.64,-12]},world=flatWorld(),brain=new BotBrain({difficulty,random:new SeededRandom(19)});return{self,enemy,world,brain};}
const tag=(id,x,team=1)=>({id,position:[x,.15,0],victimTeam:team,resolved:false,expiresAt:20});
test('nearby confirmation commitment wins movement priority without bypassing reaction or aiming gates',()=>{
 const{self,enemy,world,brain}=setup(),objective=tag('enemy-tag',3);const command=brain.think({time:0,dt:1/60,self,actors:[self,enemy],tags:[objective],world});assert.equal(brain.state,'confirm');assert.deepEqual(brain.goal,objective.position);assert.ok(Math.cos(command.yaw)*command.x-Math.sin(command.yaw)*command.z>.5);assert.equal(command.fire,false);assert.ok(brain.readyAt>=BASE.difficulty.regular.reaction[0]);
});
test('commitment is bounded and cannot renew the same tag immediately after expiration',()=>{
 const{self,world,brain}=setup(),objective=tag('tag',3);assert.equal(brain.nearbyTagCommitment(self,[objective],world,0),objective);assert.equal(brain.nearbyTagCommitment(self,[objective],world,2.4),objective);assert.equal(brain.nearbyTagCommitment(self,[objective],world,2.6),null);assert.equal(brain.nearbyTagCommitment(self,[objective],world,3),null);assert.equal(brain.nearbyTagCommitment(self,[objective],world,4.7),objective);
});
test('blocked/distant tag geometry, low health and active reload never force an objective commitment',()=>{
 const{self,world,brain}=setup();assert.equal(brain.nearbyTagCommitment(self,[tag('far',12)],world,0),null);world.hasLineOfSight=()=>false;assert.equal(brain.nearbyTagCommitment(self,[tag('wall',3)],world,0),null);world.hasLineOfSight=()=>true;world.canTraverse=()=>false;assert.equal(brain.nearbyTagCommitment(self,[tag('blocked',3)],world,0),null);world.canTraverse=()=>true;self.health=40;assert.equal(brain.nearbyTagCommitment(self,[tag('hurt',3)],world,0),null);self.health=100;self.weapon.reloading=true;assert.equal(brain.nearbyTagCommitment(self,[tag('reload',3)],world,0),null);
});
test('a small distance utility favors a close confirmation but retains much nearer denial choices',()=>{
 const{self,world,brain}=setup();assert.equal(brain.nearbyTagCommitment(self,[tag('friendly',2,0),tag('enemy',3.5,1)],world,0).id,'enemy');const other=setup();assert.equal(other.brain.nearbyTagCommitment(other.self,[tag('friendly',2,0),tag('enemy',7,1)],other.world,0).id,'friendly');
});
test('objective policy preserves the accepted weapon, health, difficulty and scoring baseline',()=>{
 for(const key of['weapons','actor','difficulty','modes'])assert.deepEqual(GAMEPLAY_TUNING[key],BASE[key]);
});
test('expired but unresolved tags are excluded from new commitments and ordinary tag goals',()=>{
 for(const time of[20,21]){
  const{self,world,brain}=setup(),expired=tag('expired',3);
  assert.equal(brain.nearbyTagCommitment(self,[expired],world,time),null);
  brain.chooseGoal(self,[expired],world,time);
  assert.equal(brain.state,'patrol');assert.equal(brain.objectiveTagId,null);
  const valid={...tag('valid',4),expiresAt:30};
  assert.equal(brain.nearbyTagCommitment(self,[expired,valid],world,time),valid);
 }
});
test('a commitment cannot retain its own expired tag, including at exact expiry',()=>{
 for(const time of[.4,.5]){
  const{self,world,brain}=setup(),objective={...tag('short',3),expiresAt:.4};
  assert.equal(brain.nearbyTagCommitment(self,[objective],world,0),objective);
  assert.equal(brain.nearbyTagCommitment(self,[objective],world,time),null);
  assert.equal(brain.tagCommit,null);assert.equal(brain.tagRetryAt.get(objective.id),time+GAMEPLAY_TUNING.botObjectives.retryDelay);
 }
});
for(const difficulty of['recruit','regular','veteran']){
 test(difficulty+': accumulated fixed-step clocks cannot prolong commitment or tag lifetime by one tick',()=>{
  for(const kind of['commitment','tag'])for(const start of[0,.7,61.3]){
   const{self,enemy,world,brain}=setup(difficulty),ticks=kind==='commitment'?150:21,objective={...tag('tag',3),expiresAt:start+(kind==='commitment'?20:ticks/60)};let time=start;
   for(let frame=0;frame<=ticks;frame++){
    const command=brain.think({time,dt:1/60,self,actors:[self,enemy],tags:[objective],world});self.yaw=command.yaw;self.pitch=command.pitch;
    assert.equal(brain.state,frame<ticks?'confirm':'engage',kind+' from '+start+' at tick '+frame);
    time+=1/60;
   }
   assert.equal(brain.tagCommit,null);assert.equal(brain.objectiveTagId,null);
  }
 });
 test(difficulty+': actual think cadence ends enemy-overriding commitment on the 2.5-second tick',()=>{
  const{self,enemy,world,brain}=setup(difficulty),objective=tag('tag',3);let until;
  for(let frame=0;frame<=150;frame++){
   const time=frame/60,command=brain.think({time,dt:1/60,self,actors:[self,enemy],tags:[objective],world});
   self.yaw=command.yaw;self.pitch=command.pitch;
   if(frame===0)until=brain.tagCommit.until;
   assert.equal(brain.state,time<until?'confirm':'engage','state at '+time);
   if(time<brain.readyAt)assert.equal(command.fire,false);
  }
  assert.equal(until,2.5);assert.equal(brain.tagCommit,null);assert.equal(brain.tagRetryAt.get(objective.id),4.5);
 });
 test(difficulty+': tag lifetime cancels priority on the first tick at expiry between decisions',()=>{
  for(const deadline of[21/60,.355]){
   const{self,enemy,world,brain}=setup(difficulty),objective={...tag('tag',3),expiresAt:deadline};
   for(let frame=0;frame<=Math.ceil(deadline*60);frame++){
    const time=frame/60,command=brain.think({time,dt:1/60,self,actors:[self,enemy],tags:[objective],world});self.yaw=command.yaw;self.pitch=command.pitch;
    assert.equal(brain.state,time<deadline?'confirm':'engage','deadline '+deadline+' at '+time);
   }
   assert.equal(brain.tagCommit,null);assert.equal(brain.objectiveTagId,null);
  }
 });
 test(difficulty+': uncommitted distant tag goal is discarded at expiry without waiting for a decision',()=>{
  const{self,world,brain}=setup(difficulty),objective={...tag('distant',12),expiresAt:21/60};
  for(let frame=0;frame<=21;frame++){
   const time=frame/60,command=brain.think({time,dt:1/60,self,actors:[self],tags:[objective],world});self.yaw=command.yaw;self.pitch=command.pitch;
   assert.equal(brain.state,time<objective.expiresAt?'confirm':'patrol');assert.equal(brain.tagCommit,null);
  }
  assert.equal(brain.objectiveTagId,null);
 });
 test(difficulty+': active commitment cancellation runs before the next command without resetting reaction',()=>{
  for(const cause of['resolved','removed','health','reload','range','line-of-sight']){
   const{self,enemy,world,brain}=setup(difficulty),objective=tag('tag',3);let tags=[objective];
   brain.think({time:0,dt:1/60,self,actors:[self,enemy],tags,world});
   const{readyAt,acquiredAt,nextPerception}=brain;assert.equal(brain.state,'confirm');
   if(cause==='resolved')objective.resolved=true;
   if(cause==='removed')tags=[];
   if(cause==='health')self.health=40;
   if(cause==='reload')self.weapon.reloading=true;
   if(cause==='range')self.position=[20,0,0];
   if(cause==='line-of-sight')world.hasLineOfSight=(_from,to)=>to!==objective.position;
   const time=1/60,command=brain.think({time,dt:1/60,self,actors:[self,enemy],tags,world});
   assert.equal(brain.state,cause==='reload'?'retreat':'engage',cause);assert.equal(brain.tagCommit,null,cause);
   assert.equal(brain.objectiveTagId,null,cause);assert.equal(brain.tagRetryAt.get(objective.id),time+2,cause);
   assert.equal(brain.readyAt,readyAt,cause);assert.equal(brain.acquiredAt,acquiredAt,cause);assert.equal(brain.nextPerception,nextPerception,cause);assert.equal(command.fire,false,cause);
  }
 });
}
