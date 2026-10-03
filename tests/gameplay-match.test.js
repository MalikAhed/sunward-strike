import test from 'node:test';
import assert from 'node:assert/strict';
import {OfflineMatch} from '../src/gameplay/match.js';
import {flatWorld,place,idle,run} from './helpers/gameplay-world.js';
const create=options=>{const match=new OfflineMatch({world:flatWorld(),friendlyBots:0,enemyBots:1,...options});match.start();for(const actor of match.actors)idle(actor);match.drainEvents();return match;};
const kill=(match,id='enemy-1')=>match.applyDamage(id,100,{sourceId:'player',ignoreProtection:true});

test('TDM scores once per enemy death, rejects friendly damage and respawns after2s',()=>{
 const match=create({friendlyBots:1});assert.equal(match.applyDamage('ally-1',100,{sourceId:'player',ignoreProtection:true}),false);
 assert.equal(kill(match),true);assert.equal(kill(match),false);assert.deepEqual(match.scores,[1,0]);assert.equal(match.getActor('player').stats.kills,1);assert.equal(match.getActor('enemy-1').stats.deaths,1);
 run(match,1.9);assert.equal(match.getActor('enemy-1').alive,false);run(match,.2);assert.equal(match.getActor('enemy-1').alive,true);assert.equal(match.getActor('enemy-1').health,100);assert.equal(match.getActor('enemy-1').weapon.ammo,30);
});
test('kill confirmed separates kills from objective confirmations and creates exactly one tag',()=>{
 const match=create({mode:'kill-confirmed'});place(match.getActor('enemy-1'),[0,0,-4]);kill(match);assert.deepEqual(match.scores,[0,0]);assert.equal(match.tags.length,1);assert.equal(kill(match),false);assert.equal(match.tags.length,1);
 place(match.getActor('player'),[0,0,-4]);const events=run(match,1/60);assert.deepEqual(match.scores,[1,0]);assert.equal(match.tags.length,0);assert.equal(match.getActor('player').stats.confirms,1);assert.equal(events.filter(e=>e.type==='tag-collected').length,1);run(match,.1);assert.deepEqual(match.scores,[1,0]);
});
test('friendly tag denial and simultaneous pickup resolve deterministically without extra scores',()=>{
 const match=create({mode:'kill-confirmed',enemyBots:2});place(match.getActor('enemy-1'),[0,0,0]);place(match.getActor('enemy-2'),[0,0,0]);kill(match);run(match,1/60);assert.deepEqual(match.scores,[0,0]);assert.equal(match.getActor('enemy-2').stats.denies,1);
 const race=create({mode:'kill-confirmed',friendlyBots:1});place(race.getActor('enemy-1'),[0,0,0]);kill(race);place(race.getActor('player'),[0,0,0]);place(race.getActor('ally-1'),[0,0,0]);run(race,1/60);assert.equal(race.getActor('ally-1').stats.confirms,1);assert.equal(race.getActor('player').stats.confirms,0);assert.deepEqual(race.scores,[1,0]);
});
test('tags cannot be collected through walls, expire without score and dead actors cannot collect',()=>{
 const match=create({mode:'kill-confirmed',world:flatWorld({wallZ:0})});place(match.getActor('enemy-1'),[0,0,-.3]);place(match.getActor('player'),[0,0,.3]);kill(match);match.getActor('enemy-1').respawnAt=Infinity;run(match,.1);assert.equal(match.tags.length,1);assert.deepEqual(match.scores,[0,0]);
 run(match,20);assert.equal(match.tags.length,0);assert.deepEqual(match.scores,[0,0]);
});
test('score/time endings lock results and tied time limits explicitly draw',()=>{
 const score=create({scoreLimit:1});kill(score);assert.equal(score.status,'ended');assert.equal(score.winner,0);assert.equal(score.applyDamage('player',100,{sourceId:'enemy-1',ignoreProtection:true}),false);score.advance(.2);assert.deepEqual(score.scores,[1,0]);
 const timer=create({timeLimitSeconds:.1});run(timer,.2);assert.equal(timer.status,'ended');assert.equal(timer.reason,'time-limit');assert.equal(timer.winner,null);assert.ok(Math.abs(timer.timeElapsed-.1)<1e-9);
});
test('pause/resume and dropped wall-time never fast-forward the match',()=>{
 const match=create();run(match,.5);const before=match.timeElapsed;match.pause();match.advance(30);assert.equal(match.timeElapsed,before);match.resume();match.advance(30);assert.equal(match.timeElapsed,before);assert.equal(match.droppedWallTime,30);match.advance(1/60);assert.ok(match.timeElapsed>before);
});
test('health regeneration waits for delay, restarts on damage and never exceeds100',()=>{
 const match=create();match.applyDamage('player',60,{sourceId:'enemy-1',ignoreProtection:true});run(match,3.9);assert.equal(match.getActor('player').health,40);run(match,.2);assert.ok(match.getActor('player').health>40);match.applyDamage('player',5,{sourceId:'enemy-1',ignoreProtection:true});const hurt=match.getActor('player').health;run(match,3);assert.equal(match.getActor('player').health,hurt);run(match,4);assert.equal(match.getActor('player').health,100);
});
test('restart clears stale tags, scores, held input, deaths and event identities',()=>{
 const match=create({mode:'kill-confirmed'});kill(match);const oldId=match.tags[0].id;match.setInput('player',{fire:true});match.restart({enemyBots:2,difficulty:'veteran'});assert.deepEqual(match.scores,[0,0]);assert.equal(match.tags.length,0);assert.equal(match.timeElapsed,0);assert.equal(match.playerCommand.fire,false);assert.equal(match.actors.length,3);for(const actor of match.actors)idle(actor);kill(match);assert.notEqual(match.tags[0].id,oldId);
});
test('fixed-tick full matches replay identically at30/60/120 display Hz',()=>{
 const states=[];for(const fps of[30,60,120]){const match=new OfflineMatch({world:flatWorld(),friendlyBots:1,enemyBots:2,seed:41,timeLimitSeconds:2});match.start();run(match,2,fps,{yaw:0,pitch:0,fire:true});states.push(match.snapshot());}
 assert.deepEqual(states[0],states[1]);assert.deepEqual(states[1],states[2]);
});
test('all difficulty levels keep identical actor health, damage, RPM and reload rules',()=>{
 for(const difficulty of['recruit','regular','veteran']){const match=create({difficulty});for(const actor of match.actors){assert.equal(actor.health,100);assert.equal(actor.weapon.spec.damageNear,34);assert.equal(actor.weapon.spec.rpm,660);assert.equal(actor.weapon.spec.reloadTactical,1.55);}}
});

test('jump/slide/reload edges survive render frames with no fixed tick and consume exactly once',()=>{
 const match=create({enemyBots:0}),player=match.getActor('player'),calls=[],oldUpdate=player.motor.update;
 player.motor.update=(dt,command)=>{calls.push({...command});oldUpdate(dt,command);};
 match.update(1/144,{jump:true,slide:true,reload:true,yaw:.3});assert.equal(calls.length,0);
 match.update(1/144,{jump:false,slide:false,reload:false,yaw:.4});assert.equal(calls.length,0);
 match.update(1/144,{yaw:.5});assert.equal(calls.length,1);assert.equal(calls[0].jump,true);assert.equal(calls[0].slide,true);assert.equal(calls[0].reload,true);assert.equal(calls[0].yaw,.5);
 match.update(1/60,{yaw:.5});assert.equal(calls[1].jump,false);assert.equal(calls[1].slide,false);assert.equal(calls[1].reload,false);
});
