import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Scene} from 'three';
import {MatchFlow,formatClock,resultTitle} from '../src/gameplay/match-flow.js';
import {MatchUI} from '../src/gameplay/match-ui.js';
import {MatchRenderer} from '../src/gameplay/match-renderer.js';
import {GameInput} from '../src/gameplay/input-controller.js';
import {bindTouchActions} from '../src/gameplay/touch-controls.js';
import {parseDOM} from './helpers/dom-model.js';
const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const ready=flow=>{flow.setAsset('map','ready');flow.setAsset('collision','ready');};

test('readiness, error, retry and repeated start never implicitly enter play',()=>{
 const flow=new MatchFlow();flow.openSetup();assert.equal(flow.start(),false);
 flow.setAsset('map','ready');flow.setAsset('collision','error','fetch failed');assert.equal(flow.ready,false);
 flow.setAsset('collision','loading');assert.equal(flow.phase,'setup');flow.setAsset('collision','ready');assert.equal(flow.phase,'setup');
 assert.equal(flow.start({mode:'tdm'}),true);const run=flow.runId;assert.equal(flow.start(),false);assert.equal(flow.runId,run);
 assert.equal(flow.pause('blur'),true);assert.equal(flow.pause('again'),false);assert.equal(flow.simulating,false);assert.equal(flow.resume(),true);assert.equal(flow.acceptsInput,true);
});
test('death, interrupted respawn, finish/restart and stale events are guarded',()=>{
 const flow=new MatchFlow();ready(flow);flow.openSetup();flow.start();const old=flow.runId;
 flow.died();assert.equal(flow.simulating,true);assert.equal(flow.acceptsInput,false);
 flow.pause('hidden');flow.respawned();assert.equal(flow.phase,'paused');flow.resume();assert.equal(flow.phase,'playing');
 flow.finish({winner:0});assert.equal(flow.simulating,false);assert.equal(flow.died(),false);
 flow.start();assert.equal(flow.died(old),false);flow.leave();assert.equal(flow.phase,'explore');assert.equal(flow.respawned(),false);
 flow.openSetup();assert.equal(flow.phase,'setup');assert.equal(flow.result,null);
});
test('clock and results have unambiguous boundaries',()=>{
 assert.equal(formatClock(60),'1:00');assert.equal(formatClock(.01),'0:01');assert.equal(formatClock(-1),'0:00');assert.equal(formatClock(NaN),'0:00');
 assert.equal(resultTitle(null,0),'DRAW');assert.equal(resultTitle(0,0),'VICTORY');assert.equal(resultTitle(1,0),'DEFEAT');
});
test('actual HTML IDs satisfy HUD, settings, readiness and result bindings',()=>{
 const document=parseDOM(html),ui=new MatchUI(document),flow=new MatchFlow();
 flow.openSetup();ui.renderFlow(flow);assert.equal(document.getElementById('start-match').disabled,true);assert.equal(document.activeElement.attrs.id,'match-mode');
 flow.setAsset('collision','error','missing');ui.renderFlow(flow);assert.equal(document.getElementById('retry-match-assets').classList.contains('hidden'),false);
 ready(flow);ui.renderFlow(flow);assert.equal(document.getElementById('start-match').disabled,false);
 assert.deepEqual(ui.settings(),{mode:'tdm',difficulty:'regular',teamSize:3,duration:300});
 flow.start();ui.renderFlow(flow);assert.equal(document.getElementById('match-menu').classList.contains('hidden'),true);assert.equal(document.getElementById('app').dataset.match,'playing');
 ui.render({player:{health:19,alive:true,kills:4,deaths:2},score:[8,5],remaining:61,mode:'kill-confirmed',weapon:{ammo:7,reserve:Infinity},movement:{sliding:true}});
 assert.equal(document.getElementById('match-ammo').textContent,'7');assert.equal(document.getElementById('match-reserve').textContent,'/ ∞');assert.equal(document.getElementById('match-timer').textContent,'1:01');
 assert.equal(document.getElementById('player-health').textContent,'19');assert.equal(document.getElementById('weapon-status').textContent,'SLIDING');assert.equal(document.getElementById('match-kd').textContent,'4 K / 2 D');
 assert.match(document.getElementById('match-objective').textContent,/confirm/);assert.equal(document.getElementById('app').classList.contains('low-health'),true);
 flow.died();ui.renderFlow(flow);assert.equal(document.getElementById('match-death').classList.contains('hidden'),false);assert.equal(document.getElementById('match-touch').classList.contains('hidden'),true);
 flow.pause('window');ui.renderFlow(flow);assert.equal(document.activeElement.attrs.id,'resume-match');
 flow.finish({winner:0});ui.renderFlow(flow);ui.showResult({mode:'tdm',player:{team:0,kills:4,deaths:2},score:[50,49]},0);assert.equal(document.getElementById('result-title').textContent,'VICTORY');
 flow.leave();ui.renderFlow(flow);assert.equal(document.activeElement.attrs.id,'play-offline');ui.dispose();
});
test('touch action edges, multiple fingers, cancel, hidden and disposal clear input',()=>{
 const document=parseDOM(html),input=new GameInput(),root=document.getElementById('match-touch');let enabled=true;
 const controls=bindTouchActions(root,input,{enabled:()=>enabled}),fire=root.querySelector('[data-action="fire"]'),jump=root.querySelector('[data-action="jump"]');
 fire.dispatch('pointerdown',{pointerId:1});fire.dispatch('pointerdown',{pointerId:2});assert.equal(input.consumeCommand().fire,true);
 fire.dispatch('pointercancel',{pointerId:1});assert.equal(input.consumeCommand().fire,true);fire.dispatch('lostpointercapture',{pointerId:2});assert.equal(input.consumeCommand().fire,false);
 jump.dispatch('pointerdown');assert.equal(input.consumeCommand().jump,true);assert.equal(input.consumeCommand().jump,false);jump.dispatch('pointercancel');
 fire.dispatch('pointerdown');controls.clear();assert.equal(input.consumeCommand().fire,false);
 jump.dispatch('keydown',{key:'Enter'});assert.equal(input.consumeCommand().jump,true);jump.dispatch('keyup',{key:'Enter'});fire.dispatch('keydown',{key:' '});assert.equal(input.consumeCommand().fire,true);fire.dispatch('blur');assert.equal(input.consumeCommand().fire,false);
 enabled=false;fire.dispatch('pointerdown');assert.equal(input.consumeCommand().fire,false);controls.dispose();enabled=true;fire.dispatch('pointerdown');assert.equal(input.consumeCommand().fire,false);
});
test('renderer mirrors real actor/tag snapshots without owning simulation and cleans effects',()=>{
 const scene=new Scene(),renderer=new MatchRenderer(scene);
 const snapshot={actors:[{id:'player',team:0,position:[0,0,0]},{id:'enemy-1',team:1,position:[1,0,3],height:1.8,alive:true,yaw:1}],tags:[{id:'tag-1',position:[2,0,3],victimTeam:1}]};
 renderer.update(snapshot,1/60);assert.equal(renderer.actors.size,1);assert.equal(renderer.tags.size,1);assert.equal(renderer.root.visible,true);
 assert.deepEqual(renderer.actors.get('enemy-1').group.position.toArray(),[1,0,3]);
 snapshot.actors[1].alive=false;renderer.update(snapshot,1/60);assert.equal(renderer.actors.get('enemy-1').group.visible,false);
 renderer.shot({actorId:'player',origin:[0,1,0],endPoint:[0,1,-20]});assert.equal(renderer.effects.length,1);renderer.update(snapshot,.1);assert.equal(renderer.effects.length,0);
 snapshot.tags=[];renderer.update(snapshot,0);assert.equal(renderer.tags.size,0);renderer.clear();assert.equal(renderer.actors.size,0);renderer.dispose();assert.equal(scene.children.length,0);
});
test('delivery preserves relative gzip assets and accessible mobile/interrupt controls',()=>{
 assert.match(html,/data-match="off"/);assert.match(html,/aria-modal="true"/);assert.match(html,/Touch controls/);assert.match(html,/data-action="(fire|ads|jump|slide|reload)"/);
 const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);assert.equal(new Set(ids).size,ids.length,'No duplicate IDs');
});
