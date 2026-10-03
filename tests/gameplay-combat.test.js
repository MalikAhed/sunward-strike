import test from 'node:test';
import assert from 'node:assert/strict';
import {GAMEPLAY_TUNING,matchSettings} from '../src/gameplay/tuning.js';
import {SeededRandom} from '../src/gameplay/random.js';
import {WeaponState,damageAtRange,idealTimeToKill,rayActor,traceShot} from '../src/gameplay/combat.js';
import {flatWorld} from './helpers/gameplay-world.js';

const weapon=overrides=>new WeaponState('carbine',new SeededRandom(42),{hipSpreadDegrees:0,adsSpreadDegrees:0,recoilPitchDegrees:0,recoilYawDegrees:0,...overrides});
const fire=(gun,start,end,extra={},context={})=>gun.step(start,end,{fire:true,yaw:0,pitch:0,...extra},{alive:true,...context});
test('tuning owns honest original near/far damage, head multiplier and ideal TTK',()=>{
 const ar=GAMEPLAY_TUNING.weapons.carbine,smg=GAMEPLAY_TUNING.weapons.smg;
 assert.equal(damageAtRange(ar,0),34);assert.equal(damageAtRange(ar,31),29.5);assert.equal(damageAtRange(ar,200),25);assert.equal(damageAtRange(ar,0,'head'),51);
 assert.ok(Math.abs(idealTimeToKill(ar)-.181818181818)<1e-10);assert.equal(idealTimeToKill(smg),.2);assert.ok(Object.isFrozen(ar));
 assert.throws(()=>matchSettings({mode:'battle-royale'}),/Unknown/);assert.throws(()=>matchSettings({friendlyBots:8,enemyBots:8}),/At most/);assert.throws(()=>matchSettings({timeLimitSeconds:Infinity}),/Time limit/);
});
test('absolute shot scheduling is identical at30/60/120Hz with no render-rate RPM advantage',()=>{
 const records=[];for(const fps of[30,60,120]){const gun=weapon(),times=[];for(let n=0;n<fps;n++)times.push(...fire(gun,n/fps,(n+1)/fps).filter(e=>e.type==='shot-request').map(e=>e.time));records.push(times);}
 assert.deepEqual(records[0],records[1]);assert.deepEqual(records[1],records[2]);assert.equal(records[0].length,12);
 for(let i=1;i<records[0].length;i++)assert.ok(Math.abs(records[0][i]-records[0][i-1]-60/660)<1e-10);
});
test('weapon ammo, finite reserve, tactical/empty reload and full-mag no-op are enforced',()=>{
 const gun=weapon({infiniteReserve:false,reserveAmmo:7});const noop=[];assert.equal(gun.beginReload(0,noop),false);fire(gun,0,.19);assert.equal(gun.ammo,27);
 const begin=gun.step(.2,.21,{reload:true},{alive:true});assert.equal(begin[0].type,'reload-started');assert.ok(Math.abs(gun.reloadEndsAt-1.75)<1e-9);
 assert.equal(fire(gun,.3,1).filter(e=>e.type==='shot-request').length,0);gun.step(1.74,1.76,{},{});assert.equal(gun.ammo,30);assert.equal(gun.reserve,4);
 gun.ammo=0;gun.step(2,2.01,{reload:true},{});assert.equal(gun.reloadEndsAt,3.95);gun.step(3.94,3.96,{},{});assert.equal(gun.ammo,4);assert.equal(gun.reserve,0);gun.ammo=0;assert.equal(gun.beginReload(4,[]),false);
});
test('sprint-to-fire, ADS transition and dead-state shot denial are shared eligibility gates',()=>{
 const gun=weapon();assert.equal(fire(gun,0,.1,{ads:true},{sprinting:true}).filter(e=>e.type==='shot-request').length,0);assert.ok(gun.adsFraction>0&&gun.adsFraction<1);
 assert.equal(fire(gun,.1,.21).filter(e=>e.type==='shot-request').length,0);const shot=fire(gun,.21,.23).find(e=>e.type==='shot-request');assert.ok(Math.abs(shot.time-.22)<1e-9);
 assert.equal(fire(gun,.3,.5,{}, {alive:false}).filter(e=>e.type==='shot-request').length,0);
});
test('seeded spread/recoil affect ballistic directions and recover without mutating input',()=>{
 const one=new WeaponState('carbine',new SeededRandom(9)),two=new WeaponState('carbine',new SeededRandom(9)),command={fire:true,yaw:.2,pitch:.1};
 const a=one.step(0,.3,command,{alive:true}),b=two.step(0,.3,command,{alive:true});assert.deepEqual(a,b);assert.deepEqual(command,{fire:true,yaw:.2,pitch:.1});assert.ok(one.recoil[0]>0);assert.notDeepEqual(a[0].direction,a[1].direction);
 const before=one.recoil[0];one.step(1,1.2,{fire:false},{});assert.ok(one.recoil[0]<before);
});
test('hitscan intersects actual capsule caps/body, handles inside origins and nearest obstruction',()=>{
 const actor={id:'target',alive:true,position:[0,0,-10],height:1.8,radius:.35};const body=rayActor([0,1,0],[0,0,-1],actor);assert.ok(Math.abs(body.distance-9.65)<1e-6);assert.equal(body.zone,'body');assert.equal(rayActor([0,1.6,-10],[1,0,0],actor).distance,0);
 assert.equal(rayActor([2,1,0],[0,0,-1],actor),null);
 const hit=traceShot({origin:[0,1,0],direction:[0,0,-1],range:100,shooterId:'p',actors:[actor],world:flatWorld()});assert.equal(hit.actor.id,'target');
 const blocked=traceShot({origin:[0,1,0],direction:[0,0,-1],range:100,shooterId:'p',actors:[actor],world:flatWorld({wallZ:-5})});assert.equal(blocked.actor,null);assert.equal(blocked.distance,5);assert.equal(blocked.hitWorld,true);
});
