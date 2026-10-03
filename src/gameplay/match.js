import {GAMEPLAY_TUNING,matchSettings} from './tuning.js';
import {SeededRandom,hashSeed} from './random.js';
import {WeaponState,traceShot,damageAtRange} from './combat.js';
import {BotBrain} from './bots.js';
import {distance,add,finitePoint,clamp} from './vectors.js';
const order=(a,b)=>a.id<b.id?-1:a.id>b.id?1:0;
const emptyStats=()=>({kills:0,deaths:0,assists:0,confirms:0,denies:0,shots:0,hits:0});
function sanitized(command={}){return {x:clamp(Number.isFinite(command.x)?command.x:0,-1,1),z:clamp(Number.isFinite(command.z)?command.z:0,-1,1),yaw:Number.isFinite(command.yaw)?command.yaw:0,pitch:clamp(Number.isFinite(command.pitch)?command.pitch:0,-1.5,1.5),...Object.fromEntries(['sprint','jump','slide','crouch','ads','fire','reload'].map(key=>[key,!!command[key]]))};}
export class OfflineMatch{
  constructor({world,...settings}={}){
    for(const name of['createMotor','raycast','hasLineOfSight','spawnPoints','canTraverse'])if(typeof world?.[name]!=='function')throw new TypeError('World adapter requires '+name);
    this.world=world;this.settings=matchSettings(settings);this.round=0;this.events=[];this.restart();this.status='ready';this.events=[];
  }
  emit(type,detail={},time=this.timeElapsed){const event={type,time,round:this.round,...detail};this.events.push(event);return event;}
  restart(settings={}){
    this.settings=matchSettings({...this.settings,...settings});this.round++;this.status='playing';this.timeElapsed=0;this.accumulator=0;this.scores=[0,0];this.tags=[];this.winner=null;this.reason=null;this.events=[];this.actors=[];this.droppedWallTime=0;this.playerCommand=sanitized();this.sequence=0;
    this.addActor('player',0,false);
    for(let i=1;i<=this.settings.friendlyBots;i++)this.addActor('ally-'+i,0,true);
    for(let i=1;i<=this.settings.enemyBots;i++)this.addActor('enemy-'+i,1,true);
    this.actors.sort(order);this.emit('match-started',{mode:this.settings.mode});return this.snapshot();
  }
  start(){if(this.status==='ready'){this.status='playing';this.emit('match-started',{mode:this.settings.mode});}return this.snapshot();}
  pause(){if(this.status==='playing'){this.status='paused';this.accumulator=0;this.playerCommand=sanitized({yaw:this.playerCommand.yaw,pitch:this.playerCommand.pitch});this.emit('paused');}}
  resume(){if(this.status==='paused'){this.status='playing';this.accumulator=0;this.emit('resumed');}}
  setInput(id,command){
    if(id!=='player')throw new Error('External commands belong to the human actor only');
    const next=sanitized(command);
    if(this.status!=='playing'){this.playerCommand=sanitized({yaw:next.yaw,pitch:next.pitch});return;}
    // Render frames can arrive more often than fixed ticks. Preserve one-shot
    // edges until the simulation consumes them; held inputs still update now.
    for(const action of['jump','slide','reload'])next[action] ||= this.playerCommand[action];
    this.playerCommand=next;
  }
  setDifficulty(difficulty){this.settings=matchSettings({...this.settings,difficulty});for(const actor of this.actors)actor.brain?.setDifficulty(difficulty);this.emit('difficulty-changed',{difficulty});}
  getActor(id){return this.actors.find(actor=>actor.id===id)||null;}
  addActor(id,team,isBot){
    const seed=hashSeed(this.settings.seed,id),weapon=new WeaponState(this.settings.weaponId,new SeededRandom(hashSeed(seed,'weapon')));
    const actor={id,team,isBot,life:0,alive:false,health:GAMEPLAY_TUNING.actor.health,position:[0,0,0],eye:[0,1.64,0],height:1.8,radius:.35,yaw:team===0?0:Math.PI,pitch:0,weapon,stats:emptyStats(),damageHistory:new Map(),brain:isBot?new BotBrain({difficulty:this.settings.difficulty,random:new SeededRandom(hashSeed(seed,'brain'))}):null,respawnAt:null,lastDamageAt:-Infinity,protectionUntil:0};
    actor.motor=this.world.createMotor({id,position:this.world.spawnPoints(team)[0]});this.actors.push(actor);this.spawn(actor,0);
  }
  chooseSpawn(actor){
    const candidates=this.world.spawnPoints(actor.team);if(!candidates.length||!candidates.every(finitePoint))throw new Error('Spawn candidates must be finite feet positions');
    return candidates.map((point,index)=>{let visible=0,nearest=100,occupied=0;for(const other of this.actors){if(!other.alive||other.id===actor.id)continue;const range=distance(point,other.position);if(range<1.2)occupied++;if(other.team!==actor.team){nearest=Math.min(nearest,range);if(this.world.hasLineOfSight(add(point,[0,1.64,0]),other.eye))visible++;}}return {point,index,value:nearest-visible*45-occupied*100+(index===(actor.life+hashSeed(this.settings.seed,actor.id))%candidates.length?.01:0)};}).sort((a,b)=>b.value-a.value||a.index-b.index)[0].point;
  }
  spawn(actor,time){
    actor.life++;actor.alive=true;actor.health=GAMEPLAY_TUNING.actor.health;actor.damageHistory.clear();actor.weapon.reset();actor.brain?.reset();actor.respawnAt=null;actor.lastDamageAt=-Infinity;actor.protectionUntil=time+GAMEPLAY_TUNING.actor.spawnProtection;actor.yaw=actor.team===0?0:Math.PI;actor.pitch=0;actor.motor.spawn(this.chooseSpawn(actor));Object.assign(actor,actor.motor.state());this.emit('respawn',{actorId:actor.id,team:actor.team,position:[...actor.position],life:actor.life},time);
  }
  applyDamage(targetId,amount,{sourceId=null,time=this.timeElapsed,headshot=false,ignoreProtection=false}={}){
    const actor=this.getActor(targetId),source=sourceId?this.getActor(sourceId):null;
    if(this.status!=='playing'||!actor?.alive||!Number.isFinite(amount)||amount<=0||(!ignoreProtection&&time<actor.protectionUntil)||(source&&source.team===actor.team))return false;
    const damage=Math.min(amount,actor.health);actor.health-=damage;actor.lastDamageAt=time;if(source)actor.damageHistory.set(source.id,{amount:(actor.damageHistory.get(source.id)?.amount||0)+damage,time});this.emit('damage',{actorId:actor.id,sourceId,amount:damage,health:actor.health,headshot},time);
    if(actor.health<=0)this.kill(actor,source,time);return true;
  }
  kill(actor,killer,time){
    if(!actor.alive)return;actor.alive=false;actor.motor.setAlive?.(false);actor.health=0;actor.stats.deaths++;actor.respawnAt=time+GAMEPLAY_TUNING.actor.respawnDelay;actor.deathId=`${this.round}:${actor.id}:${actor.life}`;
    if(killer&&killer.team!==actor.team){killer.stats.kills++;for(const [id,hit]of actor.damageHistory){const assistant=this.getActor(id);if(id!==killer.id&&assistant&&assistant.team!==actor.team&&time-hit.time<=GAMEPLAY_TUNING.actor.assistWindow)assistant.stats.assists++;}}
    this.emit('death',{actorId:actor.id,killerId:killer?.id??null,deathId:actor.deathId,position:[...actor.position],respawnAt:actor.respawnAt},time);
    if(this.settings.mode==='tdm'){if(killer&&killer.team!==actor.team)this.addScore(killer.team,time);}
    else if(killer&&killer.team!==actor.team){const tag={id:'tag:'+actor.deathId,deathId:actor.deathId,victimTeam:actor.team,position:add(actor.position,[0,.15,0]),createdAt:time,expiresAt:time+GAMEPLAY_TUNING.modes['kill-confirmed'].tagLifetime,resolved:false};this.tags.push(tag);this.emit('tag-spawned',{tag:{...tag,position:[...tag.position]}},time);}
  }
  addScore(team,time){if(this.status!=='playing')return;this.scores[team]++;this.emit('score',{team,score:this.scores[team],scores:[...this.scores]},time);if(this.scores[team]>=this.settings.scoreLimit)this.end('score-limit',time);}
  end(reason,time=this.timeElapsed){if(this.status==='ended')return;this.status='ended';this.reason=reason;this.winner=this.scores[0]===this.scores[1]?null:this.scores[0]>this.scores[1]?0:1;this.accumulator=0;this.emit('match-ended',{winner:this.winner,reason,scores:[...this.scores]},time);}
  collectTags(time){
    const pickup=GAMEPLAY_TUNING.modes['kill-confirmed'].tagPickupRadius;
    for(const tag of this.tags){
      if(tag.resolved)continue;
      if(time>=tag.expiresAt){tag.resolved=true;this.emit('tag-expired',{tagId:tag.id},time);continue;}
      const actor=this.actors.filter(a=>a.alive&&distance(a.position,tag.position)<=pickup&&this.world.hasLineOfSight(a.eye,tag.position)).sort(order)[0];
      if(!actor)continue;tag.resolved=true;const confirmed=actor.team!==tag.victimTeam;actor.stats[confirmed?'confirms':'denies']++;this.emit('tag-collected',{actorId:actor.id,tagId:tag.id,kind:confirmed?'confirm':'deny',team:actor.team,deathId:tag.deathId},time);if(confirmed)this.addScore(actor.team,time);if(this.status!=='playing')break;
    }
    this.tags=this.tags.filter(tag=>!tag.resolved);
  }
  step(dt){
    const start=this.timeElapsed,end=Math.min(start+dt,this.settings.timeLimitSeconds),duration=end-start,commands=new Map(),shots=[];
    for(const actor of this.actors){if(!actor.alive&&actor.respawnAt<=start+1e-9)this.spawn(actor,start);}
    // All brains observe the same pre-movement world snapshot each fixed step.
    for(const actor of this.actors){if(!actor.alive)continue;const command=actor.isBot?actor.brain.think({time:start,dt:duration,self:actor,actors:this.actors,tags:this.tags,world:this.world}):this.playerCommand;commands.set(actor.id,sanitized(command));}
    for(const actor of this.actors){
      if(!actor.alive)continue;const command=commands.get(actor.id);actor.yaw=command.yaw;actor.pitch=command.pitch;
      actor.motor.update(duration,{...command,reloading:actor.weapon.reloading,alive:true});Object.assign(actor,actor.motor.state(command));
      if(!finitePoint(actor.position)||actor.position[1]<-8){this.applyDamage(actor.id,actor.health,{time:start,ignoreProtection:true});continue;}
      if(start-actor.lastDamageAt>=GAMEPLAY_TUNING.actor.regenDelay)actor.health=Math.min(GAMEPLAY_TUNING.actor.health,actor.health+GAMEPLAY_TUNING.actor.regenPerSecond*duration);
      const weaponEvents=actor.weapon.step(start,end,command,{alive:actor.alive,sprinting:actor.sprinting,moving:actor.horizontalSpeed>.1,airborne:!actor.onFloor,sliding:actor.sliding});
      for(const event of weaponEvents){if(event.type==='shot-request')shots.push({actor,event});else this.emit(event.type,{actorId:actor.id,...event},event.time);}
    }
    shots.sort((a,b)=>a.event.time-b.event.time||order(a.actor,b.actor));
    for(const {actor,event}of shots){
      if(!actor.alive||this.status!=='playing')continue;actor.protectionUntil=event.time;actor.stats.shots++;
      const impact=traceShot({origin:actor.eye,direction:event.direction,range:actor.weapon.spec.maxRange,shooterId:actor.id,actors:this.actors,world:this.world});
      this.emit('shot',{actorId:actor.id,weaponId:actor.weapon.id,origin:[...actor.eye],direction:[...event.direction],endPoint:impact.point,hitActorId:impact.actor?.id??null,hitWorld:impact.hitWorld,ammo:event.ammo},event.time);
      for(const listener of this.actors)if(listener.alive&&listener.brain&&listener.id!==actor.id)listener.brain.hear({position:actor.position,team:actor.team},listener,event.time);
      if(impact.actor&&impact.actor.team!==actor.team){const hit=this.applyDamage(impact.actor.id,damageAtRange(actor.weapon.spec,impact.distance,impact.zone),{sourceId:actor.id,time:event.time,headshot:impact.zone==='head'});if(hit)actor.stats.hits++;}
    }
    this.timeElapsed=end;
    if(this.status==='playing'&&this.settings.mode==='kill-confirmed')this.collectTags(end);
    if(this.status==='playing'&&end>=this.settings.timeLimitSeconds-1e-9)this.end('time-limit',end);
    for(const action of['jump','slide','reload'])this.playerCommand[action]=false;
  }
  advance(frameDelta){
    if(!Number.isFinite(frameDelta)||frameDelta<0)throw new RangeError('Frame delta must be finite and nonnegative');
    if(this.status!=='playing')return 0;
    if(frameDelta>GAMEPLAY_TUNING.maxFrameDelta){this.droppedWallTime+=frameDelta;this.accumulator=0;return 0;}
    this.accumulator+=frameDelta;let count=0;
    while(this.accumulator+1e-10>=GAMEPLAY_TUNING.fixedStep&&this.status==='playing'){this.accumulator-=GAMEPLAY_TUNING.fixedStep;this.step(GAMEPLAY_TUNING.fixedStep);count++;}
    return count;
  }
  update(dt,command){if(command)this.setInput('player',command);this.advance(dt);return {snapshot:this.snapshot(),events:this.drainEvents()};}
  drainEvents(){return this.events.splice(0);}
  snapshot(){return {status:this.status,mode:this.settings.mode,settings:{...this.settings},timeElapsed:this.timeElapsed,timeRemaining:Math.max(0,this.settings.timeLimitSeconds-this.timeElapsed),scores:[...this.scores],scoreLimit:this.settings.scoreLimit,winner:this.winner,reason:this.reason,round:this.round,droppedWallTime:this.droppedWallTime,actors:this.actors.map(actor=>({id:actor.id,team:actor.team,isBot:actor.isBot,life:actor.life,position:[...actor.position],eye:[...actor.eye],yaw:actor.yaw,pitch:actor.pitch,height:actor.height,radius:actor.radius,health:actor.health,alive:actor.alive,respawnAt:actor.respawnAt,protected:actor.alive&&this.timeElapsed<actor.protectionUntil,sprinting:!!actor.sprinting,sliding:!!actor.sliding,crouched:!!actor.crouched,weapon:actor.weapon.snapshot(),stats:{...actor.stats},brain:actor.brain?.snapshot()??null})),tags:this.tags.map(tag=>({...tag,position:[...tag.position]}))};}
}
