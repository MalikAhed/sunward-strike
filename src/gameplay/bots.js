import {GAMEPLAY_TUNING} from './tuning.js';
import {add,sub,scale,dot,distance,normalize,forward,angles,wrapAngle,clamp} from './vectors.js';
const rad=Math.PI/180;
// The match clock accumulates fixed steps; ignore only floating-point residue
// at a deadline so it cannot buy one extra simulation tick of priority.
const beforeDeadline=(time,deadline)=>time+1e-9<deadline;
const liveTag=(tag,time)=>!!tag&&!tag.resolved&&beforeDeadline(time,tag.expiresAt);
export class BotBrain{
  constructor({difficulty='regular',random}={}){this.random=random;this.setDifficulty(difficulty);this.reset();}
  setDifficulty(name){if(!GAMEPLAY_TUNING.difficulty[name])throw new RangeError('Unknown bot difficulty');this.difficulty=name;this.profile=GAMEPLAY_TUNING.difficulty[name];this.memory=null;this.visible=false;}
  reset(){this.memory=null;this.visible=false;this.acquiredAt=Infinity;this.readyAt=Infinity;this.nextPerception=0;this.nextDecision=0;this.goal=null;this.path=[];this.pathIds=[];this.blocked=new Map();this.lastPosition=null;this.stuckTime=0;this.state='patrol';this.burstLeft=0;this.lastShotCount=0;this.nextBurstAt=0;this.aimError=[0,0];this.errorTarget=[0,0];this.nextErrorAt=0;this.strafeSign=this.random.next()<.5?-1:1;this.noise=null;this.replans=0;this.nextPathAt=0;this.tagCommit=null;this.tagRetryAt=new Map();this.objectiveTagId=null;}
  hear({position,team},self,time){if(team===self.team||distance(position,self.position)>this.profile.hearingRange)return;const uncertainty=.7+distance(position,self.position)*.08,angle=this.random.range(0,Math.PI*2),radius=this.random.range(.4,1)*uncertainty;this.noise={position:[position[0]+Math.cos(angle)*radius,position[1],position[2]+Math.sin(angle)*radius],time,uncertainty};}
  perceive(self,actors,world,time){
    const view=forward(self.yaw,self.pitch),candidates=[];
    for(const other of actors){
      if(!other.alive||other.team===self.team||other.id===self.id)continue;
      const point=add(other.position,[0,other.height*.60,0]),delta=sub(point,self.eye),range=distance(point,self.eye);
      if(range>this.profile.sightRange||dot(view,normalize(delta))<Math.cos(this.profile.fovDegrees*rad*.5))continue;
      const samples=[point,add(other.position,[0,other.height*.88,0]),add(other.position,[0,other.height*.35,0])];
      if(!samples.some(target=>world.hasLineOfSight(self.eye,target)))continue;
      candidates.push({other,point,range:range*(this.memory?.id===other.id? .8:1)});
    }
    candidates.sort((a,b)=>a.range-b.range||(a.other.id<b.other.id?-1:1));
    const found=candidates[0];
    if(!found){this.visible=false;return;}
    const old=this.memory,newAcquisition=!old||old.id!==found.other.id||old.life!==found.other.life||!this.visible;
    let velocity=[0,0,0];if(old&&old.id===found.other.id&&old.life===found.other.life&&time>old.seenAt){velocity=scale(sub(found.point,old.position),1/(time-old.seenAt));const speed=Math.hypot(...velocity);if(speed>12)velocity=scale(velocity,12/speed);}
    this.memory={id:found.other.id,life:found.other.life,position:[...found.point],feet:[...found.other.position],velocity,seenAt:time};
    this.visible=true;
    if(newAcquisition){this.acquiredAt=time;this.readyAt=time+this.random.range(...this.profile.reaction);const error=this.random.range(...this.profile.aimErrorDegrees)*rad;this.errorTarget=[this.random.range(-error,error),this.random.range(-error,error)];this.aimError=[...this.errorTarget];this.nextErrorAt=time+.3;this.burstLeft=0;this.nextBurstAt=this.readyAt;}
  }
  currentTagCommitment(self,tags,world,time){
    if(!this.tagCommit)return null;
    const policy=GAMEPLAY_TUNING.botObjectives,tag=tags.find(tag=>tag.id===this.tagCommit.id&&liveTag(tag,time));
    return tag&&beforeDeadline(time,this.tagCommit.until)&&self.health>=policy.minHealth&&!self.weapon.reloading&&distance(self.position,tag.position)<=policy.commitRange+1.5&&world.hasLineOfSight(self.eye,tag.position)?tag:null;
  }
  nearbyTagCommitment(self,tags,world,time){
    const policy=GAMEPLAY_TUNING.botObjectives;
    for(const[id,until]of this.tagRetryAt)if(time>=until)this.tagRetryAt.delete(id);
    if(this.tagCommit){
      const tag=this.currentTagCommitment(self,tags,world,time);
      if(tag)return tag;
      this.tagRetryAt.set(this.tagCommit.id,time+policy.retryDelay);this.tagCommit=null;
    }
    if(self.health<policy.minHealth||self.weapon.reloading)return null;
    const candidates=tags.filter(tag=>liveTag(tag,time)&&!this.tagRetryAt.has(tag.id)&&distance(self.position,tag.position)<=policy.commitRange&&Math.abs(tag.position[1]-self.position[1])<1)
      .map(tag=>({tag,score:distance(self.position,tag.position)+(tag.victimTeam===self.team?policy.denialDistancePenalty:0)}))
      .sort((a,b)=>a.score-b.score||(a.tag.id<b.tag.id?-1:1));
    for(const {tag}of candidates.slice(0,4))if(world.hasLineOfSight(self.eye,tag.position)&&world.canTraverse(self.position,tag.position)){
      this.tagCommit={id:tag.id,until:time+policy.commitSeconds};return tag;
    }
    return null;
  }
  chooseGoal(self,tags,world,time){
    const previousState=this.state,committedTag=this.nearbyTagCommitment(self,tags,world,time);
    this.objectiveTagId=null;
    const patrol=world.navigation?.patrolPoints?.()||world.spawnPoints(self.team);
    const usefulTags=tags.filter(tag=>liveTag(tag,time)&&distance(tag.position,self.position)<35).sort((a,b)=>distance(a.position,self.position)-distance(b.position,self.position));
    if(self.weapon.reloading||self.health<35){this.state='retreat';const known=this.memory?.position;const choices=patrol.filter(p=>distance(p,self.position)<18);this.goal=known?choices.sort((a,b)=>distance(b,known)-distance(a,known))[0]:this.random.pick(choices);}
    else if(committedTag){this.objectiveTagId=committedTag.id;this.state=committedTag.victimTeam===self.team?'deny':'confirm';this.goal=[...committedTag.position];}
    else if(this.visible&&this.memory){this.state='engage';this.goal=[...this.memory.feet];}
    else if(usefulTags.length){this.objectiveTagId=usefulTags[0].id;this.state=usefulTags[0].victimTeam===self.team?'deny':'confirm';this.goal=[...usefulTags[0].position];}
    else if(this.memory&&time-this.memory.seenAt<this.profile.memorySeconds){this.state='search';this.goal=[...this.memory.feet];}
    else if(this.noise&&time-this.noise.time<3){this.state='investigate';this.goal=[...this.noise.position];}
    else{this.state='patrol';if(previousState!=='patrol'||!this.goal||distance(self.position,this.goal)<1||this.stuckTime>.8||!world.canTraverse(this.goal,this.goal))this.goal=this.random.pick(patrol);this.memory=null;}
  }
  think({time,dt,self,actors,tags,world}){
    if(!self.alive)return {x:0,z:0,fire:false};
    if(time>=this.nextPerception){this.perceive(self,actors,world,time);this.nextPerception=time+this.profile.perceptionInterval;}
    if(this.memory&&time-this.memory.seenAt>this.profile.memorySeconds){this.memory=null;this.visible=false;}
    // Lifetimes and cancellation are checked every simulation tick. Decision
    // cadence cannot prolong priority for an expired commitment or stale tag.
    const invalidCommit=this.tagCommit&&!this.currentTagCommitment(self,tags,world,time);
    const staleObjective=this.objectiveTagId!==null&&!tags.some(tag=>tag.id===this.objectiveTagId&&liveTag(tag,time));
    if(time>=this.nextDecision||invalidCommit||staleObjective){this.chooseGoal(self,tags,world,time);this.nextDecision=time+this.profile.decisionInterval;}
    let yaw=self.yaw,pitch=self.pitch;
    if(this.memory){
      if(time>=this.nextErrorAt){const error=this.random.range(...this.profile.aimErrorDegrees)*rad;this.errorTarget=[this.random.range(-error,error),this.random.range(-error,error)];this.nextErrorAt=time+.35;}
      const blend=1-Math.exp(-dt*4);this.aimError=this.aimError.map((value,i)=>value+(this.errorTarget[i]-value)*blend);
      const aim=add(this.memory.position,scale(this.memory.velocity,this.visible?this.profile.prediction:0)),desired=angles(sub(aim,self.eye));
      const dy=wrapAngle(desired.yaw+this.aimError[1]-yaw),dp=desired.pitch+this.aimError[0]-pitch,mag=Math.hypot(dy,dp),factor=Math.min(1,this.profile.turnDegrees*rad*dt/Math.max(mag,1e-9));yaw+=dy*factor;pitch=clamp(pitch+dp*factor,-1.5,1.5);
    }else if(this.goal){const desired=angles(sub(this.goal,self.position)),delta=wrapAngle(desired.yaw-yaw);yaw+=clamp(delta,-this.profile.turnDegrees*rad*dt,this.profile.turnDegrees*rad*dt);pitch*=Math.exp(-dt*5);}
    let move=[0,0,0];
    if(this.goal){
      for(const [id,expires]of this.blocked)if(expires<=time)this.blocked.delete(id);
      if((!this.path.length&&time>=this.nextPathAt)||!this.pathGoal||distance(this.goal,this.pathGoal)>2||this.stuckTime>.8){
        if(this.stuckTime>.8&&this.pathIds[0])this.blocked.set(this.pathIds[0],time+3);
        const path=world.navigation?.findPath(self.position,this.goal,{blocked:new Set(this.blocked.keys())})||{points:world.canTraverse(self.position,this.goal)?[[...this.goal]]:[],nodeIds:[]};
        this.path=path.points.map(point=>[...point]);this.pathIds=[...(path.nodeIds||[])];this.pathGoal=[...this.goal];this.stuckTime=0;this.nextPathAt=time+.45;this.replans++;
      }
      while(this.path.length&&Math.hypot(self.position[0]-this.path[0][0],self.position[2]-this.path[0][2])<.18&&Math.abs(self.position[1]-this.path[0][1])<.3){this.path.shift();this.pathIds.shift();}
      if(this.path.length){move=normalize(sub(this.path[0],self.position));move[1]=0;}
      if(!['confirm','deny'].includes(this.state)&&this.visible&&this.memory&&world.canTraverse(self.position,this.memory.feet)){
        const range=distance(self.position,this.memory.feet),toward=normalize(sub(this.memory.feet,self.position));const forwardAmount=range>20?.7:range<7?-.6:0;
        move=[toward[0]*forwardAmount-toward[2]*this.strafeSign*.55,0,toward[2]*forwardAmount+toward[0]*this.strafeSign*.55];
      }
    }
    // Short-range physical avoidance uses only adjacent living bodies. It is not
    // used for target acquisition or aiming and never teleports either actor.
    for(const other of actors){if(other.id===self.id||!other.alive)continue;if(other.team!==self.team&&!world.hasLineOfSight(self.eye,other.eye))continue;const delta=sub(self.position,other.position),range=Math.hypot(delta[0],delta[2]);if(range>.01&&range<.9&&Math.abs(delta[1])<1){move[0]+=delta[0]/range*(.9-range);move[2]+=delta[2]/range*(.9-range);}}
    if(this.lastPosition&&Math.hypot(move[0],move[2])>.1)this.stuckTime=distance(self.position,this.lastPosition)<.006?this.stuckTime+dt:0;this.lastPosition=[...self.position];
    const deltaShots=Math.max(0,self.weapon.shotCount-this.lastShotCount);this.lastShotCount=self.weapon.shotCount;this.burstLeft=Math.max(0,this.burstLeft-deltaShots);
    if(deltaShots&&this.burstLeft===0)this.nextBurstAt=time+this.random.range(...this.profile.burstPause);
    const visibleNow=this.visible&&this.memory&&world.hasLineOfSight(self.eye,this.memory.position);
    const aimed=visibleNow&&dot(forward(yaw,pitch),normalize(sub(this.memory.position,self.eye)))>Math.cos(Math.max(6,this.profile.aimErrorDegrees[1]*2)*rad);
    if(aimed&&time>=this.readyAt&&time>=this.nextBurstAt&&this.burstLeft===0)this.burstLeft=this.random.integer(...this.profile.burstShots);
    const reload=self.weapon.ammo===0||(self.weapon.ammo<8&&!visibleNow);
    return {x:Math.cos(yaw)*move[0]-Math.sin(yaw)*move[2],z:-Math.sin(yaw)*move[0]-Math.cos(yaw)*move[2],yaw,pitch,sprint:!visibleNow&&!self.weapon.reloading&&['patrol','confirm','deny'].includes(this.state),ads:!!visibleNow,fire:!!aimed&&time>=this.readyAt&&this.burstLeft>0&&!reload,reload,jump:false,slide:false,crouch:false};
  }
  snapshot(){return {state:this.state,difficulty:this.difficulty,visible:this.visible,memory:this.memory?{id:this.memory.id,position:[...this.memory.position],seenAt:this.memory.seenAt}:null,readyAt:Number.isFinite(this.readyAt)?this.readyAt:null,replans:this.replans,goal:this.goal?[...this.goal]:null};}
}
