import test from 'node:test';
import assert from 'node:assert/strict';
import {makeApp} from './helpers/main-harness.js';

// The actual composed main module is executed with real physics/gameplay and a
// minimal DOM plus a no-op renderer. These cover wiring, not GPU/browser layout.
test('composed app starts, focuses input, moves, fires and pauses on unlock',async()=>{
 const app=await makeApp();assert.equal(app.window.sunwardDebug.ready,true);assert.equal(app.window.sunwardDebug.collisionReady,true);
 app.click('play-offline');assert.equal(app.window.sunwardDebug.matchPhase,'setup');app.click('start-match');
 assert.equal(app.window.sunwardDebug.matchPhase,'playing');assert.equal(app.document.activeElement,app.canvas);
 const before=[...app.match.getActor('player').position];app.key('KeyW');app.tick(30);app.key('KeyW','keyup');
 assert.ok(app.match.getActor('player').position[2]<before[2]-.5,'Keyboard actually moves the human capsule');
 app.canvas.dispatch('pointerdown',{button:0});app.tick(10);app.window.dispatch('pointerup',{button:0});
 assert.ok(app.match.getActor('player').weapon.ammo<30);assert.notEqual(app.document.getElementById('match-ammo').textContent,'30');
 app.document.exitPointerLock();assert.equal(app.window.sunwardDebug.matchPhase,'paused');const time=app.match.timeElapsed;app.tick(60);assert.equal(app.match.timeElapsed,time);
 app.click('resume-match');app.tick(10);assert.ok(app.match.timeElapsed>time);assert.equal(app.match.playerCommand.fire,false);
});
test('repeated start and restart leave only one round and preserve explorer camera',async()=>{
 const app=await makeApp(),before=app.window.sunwardDebug.camera.position;
 app.click('play-offline');app.document.getElementById('match-mode').value='kill-confirmed';app.document.getElementById('match-difficulty').value='veteran';app.document.getElementById('match-size').value='2';app.click('start-match');
 const first=app.match;assert.equal(first.settings.mode,'kill-confirmed');assert.equal(first.settings.difficulty,'veteran');assert.equal(first.actors.length,4);
 app.click('start-match');assert.equal(app.match,first);app.click('pause-match');app.click('restart-match');assert.notEqual(app.match,first);assert.equal(app.match.settings.mode,'kill-confirmed');assert.equal(app.worldBuilds,1,'Round restart reuses the validated navigation/cover world');
 app.click('pause-match');app.click('leave-match');assert.equal(app.window.sunwardDebug.match,null);assert.equal(app.window.sunwardDebug.mode,'fly');assert.deepEqual(app.window.sunwardDebug.camera.position,before);
 app.click('play-offline');app.click('setup-close');assert.equal(app.window.sunwardDebug.matchPhase,'explore');
});
test('actual death, delayed respawn, result and replay produce correct HUD lifecycle',async()=>{
 const app=await makeApp();app.click('play-offline');app.click('start-match');app.tick(2);
 app.match.applyDamage('player',100,{sourceId:'enemy-1',ignoreProtection:true});app.tick();assert.equal(app.window.sunwardDebug.matchPhase,'dead');assert.equal(app.document.getElementById('match-touch').classList.contains('hidden'),true);
 app.window.dispatch('blur');assert.equal(app.window.sunwardDebug.matchPhase,'paused');const time=app.match.timeElapsed;app.tick(150);assert.equal(app.match.timeElapsed,time);
 app.click('resume-match');assert.equal(app.window.sunwardDebug.matchPhase,'dead');app.tick(125);assert.equal(app.window.sunwardDebug.matchPhase,'playing');assert.equal(app.match.getActor('player').health,100);
 app.match.scores=[50,11];app.match.end('score-limit');app.tick();assert.equal(app.window.sunwardDebug.matchPhase,'ended');assert.equal(app.document.getElementById('result-title').textContent,'VICTORY');
 app.click('play-again');assert.equal(app.window.sunwardDebug.matchPhase,'playing');assert.deepEqual(app.match.scores,[0,0]);assert.equal(app.document.getElementById('match-death').classList.contains('hidden'),true);
});
test('failed assets retry independently and never auto-start a match',async()=>{
 const app=await makeApp({failMap:true,failCollision:true});app.click('play-offline');assert.equal(app.document.getElementById('start-match').disabled,true);app.click('start-match');assert.equal(app.match,undefined);
 app.click('retry-match-assets');app.click('retry-match-assets');await app.settle();assert.equal(app.mapCalls,2);assert.equal(app.collisionCalls,2);assert.equal(app.window.sunwardDebug.matchPhase,'setup');assert.equal(app.document.getElementById('start-match').disabled,false);
 app.click('start-match');assert.equal(app.window.sunwardDebug.matchPhase,'playing');
});
test('pointer-lock failure and touch paths expose functional fire and clear canceled actions',async()=>{
 const app=await makeApp({failLock:true});app.click('play-offline');app.click('start-match');await app.settle();assert.equal(app.document.getElementById('app').classList.contains('drag-match'),true);
 const fire=app.document.getElementById('match-touch').querySelector('[data-action="fire"]');fire.dispatch('pointerdown');app.tick(8);assert.ok(app.match.getActor('player').weapon.ammo<30);fire.dispatch('pointercancel');const ammo=app.match.getActor('player').weapon.ammo;app.tick(8);assert.equal(app.match.getActor('player').weapon.ammo,ammo);
 const mobile=await makeApp({coarse:true});mobile.click('play-offline');mobile.click('start-match');assert.equal(mobile.document.pointerLockElement,undefined);assert.equal(mobile.window.sunwardDebug.matchPhase,'playing');
});
test('missing WebGL shows the honest static preview and does not expose match controls',async()=>{
 const app=await makeApp({failGL:true});assert.equal(app.window.sunwardDebug.fallback,true);assert.equal(app.window.sunwardDebug.renderer.webgl2,false);assert.equal(app.document.getElementById('play-offline').classList.contains('hidden'),true);assert.equal(app.match,undefined);
});
test('explorer remains keyboard usable immediately after choosing a camera button',async()=>{
 const app=await makeApp();app.click('explore');assert.equal(app.document.activeElement,app.canvas);const start=app.window.sunwardDebug.camera.position;
 app.key('KeyW');app.tick(10);app.key('KeyW','keyup');assert.notDeepEqual(app.window.sunwardDebug.camera.position,start);
 const firstPerson=app.document.querySelector('button[data-mode="walk"]');firstPerson.dispatch('click');assert.equal(app.window.sunwardDebug.mode,'walk');assert.equal(app.document.activeElement,app.canvas);
});
test('keyboard and touch hold the same action independently across a visibility pause',async()=>{
 const app=await makeApp({coarse:true});app.click('play-offline');app.click('start-match');
 const forward=app.document.getElementById('match-touch').querySelector('[data-action="forward"]');app.key('KeyW');forward.dispatch('pointerdown',{pointerId:3});app.key('KeyW','keyup');app.tick(2);assert.equal(app.match.playerCommand.z,1);
 app.document.hidden=true;app.document.dispatch('visibilitychange');assert.equal(app.window.sunwardDebug.matchPhase,'paused');app.document.hidden=false;app.click('resume-match');app.tick(2);assert.equal(app.match.playerCommand.z,0);
});
test('completed result can change settings, cancel and return to the original explorer repeatedly',async()=>{
 const app=await makeApp();const original=app.window.sunwardDebug.camera.position;app.click('play-offline');app.click('start-match');
 app.match.end('time-limit');app.tick();assert.equal(app.window.sunwardDebug.matchPhase,'ended');app.click('change-match');assert.equal(app.window.sunwardDebug.matchPhase,'setup');app.click('setup-close');assert.deepEqual(app.window.sunwardDebug.camera.position,original);
 app.click('play-offline');app.click('setup-close');assert.equal(app.window.sunwardDebug.matchPhase,'explore');assert.equal(app.window.sunwardDebug.match,null);
});
test('explorer uses shared finite-contact motor and jump remains single-press across display rates',async()=>{
 for(const rate of [30,60,120]){
  const app=await makeApp();app.document.querySelector('button[data-mode="walk"]').dispatch('click');app.tick(rate,1000/rate);const standing=app.window.sunwardDebug.camera.position[1];
  app.key('Space');let peak=standing;for(let i=0;i<rate;i++){app.tick(1,1000/rate);peak=Math.max(peak,app.window.sunwardDebug.camera.position[1]);}
  assert.ok(peak>standing+.5,`${rate}Hz jump rises`);assert.ok(Math.abs(app.window.sunwardDebug.camera.position[1]-standing)<.04,`${rate}Hz held jump does not repeat`);app.key('Space','keyup');
  app.click('play-offline');app.click('setup-close');assert.equal(app.window.sunwardDebug.mode,'walk');assert.ok(Math.abs(app.window.sunwardDebug.camera.position[1]-standing)<.04);
 }
});
test('explorer OS-repeat Space cannot bunny-hop and a down/up between frames remains latched',async()=>{
 const app=await makeApp();app.document.querySelector('button[data-mode="walk"]').dispatch('click');app.tick(90);const standing=app.window.sunwardDebug.camera.position[1];
 app.key('Space');let launches=0,above=false;
 for(let frame=0;frame<240;frame++){
  if(frame>10&&frame%5===0)app.window.dispatch('keydown',{code:'Space',repeat:true,target:app.canvas});
  app.tick();const next=app.window.sunwardDebug.camera.position[1]>standing+.15;if(next&&!above)launches++;above=next;
 }
 assert.equal(launches,1,'One physical hold produces exactly one launch despite OS repeat');assert.ok(Math.abs(app.window.sunwardDebug.camera.position[1]-standing)<.04);
 app.key('Space','keyup');app.tick();app.key('Space');app.key('Space','keyup');app.tick(12);assert.ok(app.window.sunwardDebug.camera.position[1]>standing+.4,'Sub-frame tap reaches the motor');app.tick(60);assert.ok(Math.abs(app.window.sunwardDebug.camera.position[1]-standing)<.04);
});
