import './style.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { buildCollisionOctree } from './collision.js';
import {loadGlbAsset} from './asset-loader.js';
import {createClouds, createScenery, createSky, applyReferencePalette} from './atmosphere.js';
import {PlayerController} from './gameplay/player-controller.js';
import {GameInput, KEY_ACTIONS} from './gameplay/input-controller.js';
import {OfflineMatch} from './gameplay/match.js';
import {createThreeWorld} from './gameplay/three-world.js';
import {MatchFlow} from './gameplay/match-flow.js';
import {MatchUI} from './gameplay/match-ui.js';
import {MatchRenderer} from './gameplay/match-renderer.js';
import {MatchAudio} from './gameplay/match-audio.js';
import {createOfflineClient, offlineStatusText, chooseMapDelivery} from './gameplay/offline-client.js';
import {bindTouchActions} from './gameplay/touch-controls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { MAP_CONFIG } from './map-config.js';
import { clamp, damp, normalizedInput, rotationFromLook, fittedOverviewPosition, overviewFrameOnResize, overviewFrameAfterModeChange, VIEWPOINTS } from './math.js';

const $ = (id) => document.getElementById(id);
const canvas = $('scene');
for(const option of $('viewpoint').options){option.textContent=MAP_CONFIG.viewpoints[option.value].label;}
$('position').title=MAP_CONFIG.scaleNotice;
const state = { ready:false, mode:'fly', viewpoint:'hero', quality:'balanced', mapVersion:MAP_CONFIG.version, rifleVersion:'revision2', fps:0, pointerLocked:false, collisionReady:false, rifleReady:false, ammo:30, reloading:false, shots:0, lastError:null, drawCalls:0, triangles:0, frame:0 };
function showGraphicsFallback(error){
  state.lastError=String(error);state.fallback=true;
  for(const selector of ['.mode-switch','#intro','#loading','#controls','#bottombar','.bottombar','#telemetry','#crosshair','#weapon-hud','#lock-hint','.touch-controls','#help-toggle','#fullscreen','#error','#play-offline','#pause-match','#match-menu','#match-hud','#match-touch','#match-death'])document.querySelector(selector)?.classList.add('hidden');
  const fallback=document.createElement('section');fallback.className='graphics-fallback';
  const poster=document.createElement('img');poster.src=`${import.meta.env.BASE_URL}assets/map-poster.png`;poster.alt='Static Blender-rendered overview of the SUNWARD source environment';poster.className='fallback-poster';fallback.append(poster);
  const card=document.createElement('div');card.className='fallback-card';card.setAttribute('role','status');
  const label=document.createElement('p');label.className='eyebrow';label.textContent='STATIC SOURCE PREVIEW';
  const title=document.createElement('h1');title.textContent='THE SITE IS HERE.';
  const explanation=document.createElement('p');explanation.textContent='Interactive 3D couldn’t start because this browser did not provide WebGL 2. The image behind this message is a static Blender preview of the source map.';
  const next=document.createElement('p');next.className='fallback-next';next.textContent='Try a current browser with graphics acceleration enabled, then reload.';
  const retry=document.createElement('button');retry.className='primary';retry.textContent='RETRY PAGE';retry.addEventListener('click',()=>location.reload());
  card.append(label,title,explanation,next,retry);fallback.append(card);$('app').append(fallback);
  Object.defineProperty(window,'sunwardDebug',{configurable:false,get:()=>Object.freeze({...state,renderer:Object.freeze({webgl2:false}),assets:Object.freeze({...MAP_CONFIG.assets,poster:'map-poster.png'})})});
  console.warn('SUNWARD graphics fallback:',error.message);
}
function start(){
let renderer;
try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:false, powerPreference:'high-performance'}); }
catch (error) {showGraphicsFallback(error);return;}
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.setClearColor(0xb5d7e3);
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xb8d3d5, .0025);
const camera = new THREE.PerspectiveCamera(58,1,.05,500);
camera.rotation.order = 'YXZ';
const hemisphere = new THREE.HemisphereLight(0xd3e9ff,0x718559,1.75);
scene.add(hemisphere);
const sunlight = new THREE.DirectionalLight(0xffedcc,3.0);
sunlight.position.set(-42,68,30);
sunlight.castShadow = true;
sunlight.shadow.mapSize.set(2048,2048);
sunlight.shadow.camera.left=-57; sunlight.shadow.camera.right=57;
sunlight.shadow.camera.top=62; sunlight.shadow.camera.bottom=-62;
sunlight.shadow.camera.near=1; sunlight.shadow.camera.far=180;
sunlight.shadow.normalBias=.035; sunlight.shadow.bias=-.00015;
sunlight.target.position.set(0,0,0); scene.add(sunlight,sunlight.target);
const sky = createSky(); scene.add(sky);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(),.04).texture;
scene.environmentIntensity=.28;
const orbit = new OrbitControls(camera,canvas);
orbit.enabled=false; orbit.enableDamping=true; orbit.dampingFactor=.08;
orbit.minDistance=4; orbit.maxDistance=320; orbit.maxPolarAngle=Math.PI*.49;
orbit.target.fromArray(MAP_CONFIG.orbitTarget);
let octree = null;
const flow = new MatchFlow();
const gameInput = new GameInput({enabled: false});
const matchView = new MatchRenderer(scene);
const matchAudio = new MatchAudio();
const mapDelivery=chooseMapDelivery(window);
let match = null, matchSnapshot = null, explorerBookmark = null;
let cachedMatchWorld=null,worldMapRoot=null,worldTree=null;
let hitMarkerTimer = 0, damageFlash = 0, announcementTimer = 0;
const killFeed = [];
let offlineClient=null,offlineState={state:'caching'};
const walker = new PlayerController();
const velocity = new THREE.Vector3();
let yaw=0,pitch=0,drag=null,aim=false,fireHeld=false,shotCooldown=0,reloadTimer=0,toastTimer=0,weaponKick=0;
let map=null,rifle=null,mixer=null,currentAction=null,clips={},weaponSway=0;
const keys = new Set();
let explorerJumpQueued=false;
let preserveOverviewFrame=false;
orbit.addEventListener('start',()=>{preserveOverviewFrame=false;});
const weaponScene = new THREE.Scene();
const weaponCamera = new THREE.PerspectiveCamera(58,1,.01,10);
weaponScene.add(new THREE.HemisphereLight(0xeaf5ff,0x75806e,2.1));
const gunKey=new THREE.DirectionalLight(0xffefd0,3.8);gunKey.position.set(-2,4,3);weaponScene.add(gunKey);
weaponScene.environment=scene.environment; weaponScene.environmentIntensity=1.3;
const weaponAnchor = new THREE.Group();
const weaponBasis = new THREE.Group();
weaponBasis.rotation.y=-Math.PI/2;
weaponBasis.scale.setScalar(.15);
weaponAnchor.add(weaponBasis); weaponScene.add(weaponAnchor);
weaponAnchor.position.set(.26,-.39,-.89);

function toast(message){$('toast').textContent=message;$('toast').classList.remove('hidden');toastTimer=3.5;}
function dismissIntro(){ $('intro').classList.add('dismissed'); }
function applyLook(){camera.rotation.set(pitch,yaw,0,'YXZ');}
function setLook(position,target){ camera.position.fromArray(position); const angles=rotationFromLook(position,target);yaw=angles.yaw;pitch=angles.pitch;applyLook(); }
function setViewpoint(name){if(flow.active||flow.phase==='ended')return;const view=VIEWPOINTS[name]||VIEWPOINTS.hero;state.viewpoint=name;preserveOverviewFrame=['hero','topdown'].includes(name);$('viewpoint').value=name;if(state.mode==='walk')setMode('fly',false);setLook(['hero','topdown'].includes(name)?fittedOverviewPosition(view,window.innerWidth/window.innerHeight):view.position,view.target);orbit.target.fromArray(view.target);velocity.set(0,0,0);}
function spawnWalk(position=MAP_CONFIG.spawns.street,target=MAP_CONFIG.viewpoints.street.target){explorerJumpQueued=false;preserveOverviewFrame=false;setLook(position,target);walker.spawn(camera.position);velocity.set(0,0,0);}
function setMode(mode,reset=true){if(flow.active||flow.phase==='ended')return;preserveOverviewFrame=overviewFrameAfterModeChange(preserveOverviewFrame,mode);if(state.mode==='orbit'&&mode!=='orbit'){yaw=camera.rotation.y;pitch=camera.rotation.x;}state.mode=mode;$('app').dataset.mode=mode;orbit.enabled=mode==='orbit';orbit.autoRotate=false;keys.clear();explorerJumpQueued=false;aim=false;fireHeld=false;document.querySelectorAll('button[data-mode]').forEach(button=>{const selected=button.dataset.mode===mode;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));});$('mode-label').textContent={fly:'FREEFLY',walk:'FIRST PERSON',orbit:'ORBIT'}[mode];$('crosshair').classList.toggle('hidden',mode!=='walk');$('walk-controls').classList.toggle('hidden',mode!=='walk');$('weapon-hud').classList.toggle('hidden',mode!=='walk');$('lock-hint').classList.toggle('hidden',mode!=='walk'||state.pointerLocked);$('vertical-label').textContent=mode==='walk'?'Freefly only':'Descend / ascend';$('mouse-label').textContent=mode==='orbit'?'Drag / scroll to orbit':'Drag to look';$('guide-note').textContent=mode==='walk'?'Capsule collision + gravity. Cosmetic firing; no combat targets.':mode==='orbit'?'Drag to orbit. Scroll to zoom. Right-drag to pan.':'Freefly passes through geometry. No boundaries.';if(mode==='walk'&&reset)spawnWalk();if(mode==='orbit'){document.exitPointerLock?.();if(reset)setViewpoint('hero');orbit.target.fromArray(MAP_CONFIG.orbitTarget);orbit.update();}if(mode!=='walk')state.reloading=false;if(!flow.modal){canvas.tabIndex=0;canvas.focus({preventScroll:true});}}
function setQuality(value){state.quality=value;const dpr=window.devicePixelRatio||1;renderer.setPixelRatio(Math.min(dpr,{high:2,balanced:1.5,low:1}[value]));renderer.shadowMap.enabled=value!=='low';sunlight.shadow.mapSize.set(value==='high'?4096:2048,value==='high'?4096:2048);if(sunlight.shadow.map){sunlight.shadow.map.dispose();sunlight.shadow.map=null;}sunlight.shadow.needsUpdate=true;scene.traverse(obj=>{if(obj.isMesh){for(const mat of Array.isArray(obj.material)?obj.material:[obj.material])mat.needsUpdate=true;}});resize();}
function resize(){const w=window.innerWidth,h=window.innerHeight;camera.aspect=w/h;camera.updateProjectionMatrix();weaponCamera.aspect=w/h;weaponCamera.updateProjectionMatrix();renderer.setSize(w,h,false);const position=overviewFrameOnResize(state.viewpoint,w/h,{active:preserveOverviewFrame,mode:state.mode});if(position){setLook(position,VIEWPOINTS[state.viewpoint].target);if(orbit.enabled)orbit.update();}}
function enableDragControls(){if(flow.active){$('app').classList.add('drag-match');toast('Drag the scene to look. Hold the on-screen Fire / Aim buttons, or press F to retry mouse capture.');}else toast('Mouse capture was unavailable. Drag the scene to look instead.');}
function requestLock(){if(state.mode==='orbit'||matchMedia('(pointer: coarse)').matches)return;try{const result=canvas.requestPointerLock?.();if(!canvas.requestPointerLock){enableDragControls();return;}result?.catch?.(enableDragControls);}catch{enableDragControls();}}
function animateWeapon(name,duration){if(!mixer||!clips[name])return;currentAction?.stop();currentAction=mixer.clipAction(clips[name]);currentAction.reset().setLoop(THREE.LoopOnce,1);currentAction.setEffectiveTimeScale(duration>0?clips[name].duration/duration:1);currentAction.clampWhenFinished=false;currentAction.play();}
function updateAmmo(){ $('ammo').innerHTML=`${state.reloading?'··':state.ammo}<span>/ ∞</span>`; }
function reload(){if(state.mode!=='walk'||state.reloading||state.ammo===30)return;state.reloading=true;reloadTimer=3;animateWeapon('Reload');updateAmmo();}
function fire(){if(state.mode!=='walk'||state.reloading||shotCooldown>0)return;if(!state.ammo){reload();return;}state.ammo--;state.shots++;shotCooldown=.13;weaponKick=.05;animateWeapon('Fire');updateAmmo();}

const matchUI = new MatchUI(document, {
  setup: openMatchSetup, start: () => startMatch(false), pause: () => pauseMatch('The match clock is paused'),
  toggleSound: () => {matchAudio.setEnabled(!matchAudio.enabled);if(matchAudio.enabled)matchAudio.activate();$('match-sound').value=matchAudio.enabled?'on':'off';updateSoundControl();},
  resume: resumeMatch, restart: () => startMatch(true), leave: leaveMatch,
  retry: () => { if(!state.ready)loadMap(); if(!state.collisionReady)loadCollision(); },
});
function updateSoundControl(){const button=$('toggle-match-sound');button.textContent=matchAudio.enabled?'Mute sound':'Unmute sound';button.setAttribute('aria-pressed',String(!matchAudio.enabled));}
const matchTouch = bindTouchActions($('match-touch'), gameInput, {enabled: () => flow.acceptsInput});
function syncMatchFlow(){
  const wasEnabled=gameInput.enabled;gameInput.setEnabled(flow.acceptsInput);
  if(flow.acceptsInput&&!wasEnabled){canvas.tabIndex=0;canvas.focus({preventScroll:true});}
  if(!flow.acceptsInput){gameInput.clear();matchTouch.clear();drag=null;}
  matchUI.renderFlow(flow);
  state.matchPhase=flow.phase;
  $('update-offline').disabled=flow.active;
}
function bookmarkExplorer(){
  if(explorerBookmark)return;
  explorerBookmark={mode:state.mode,viewpoint:state.viewpoint,position:camera.position.toArray(),yaw,pitch,
    orbitTarget:orbit.target.toArray(),preserveOverviewFrame};
}
function openMatchSetup(){
  if(flow.active){pauseMatch('Match options');return;}
  bookmarkExplorer();dismissIntro();clearInput();
  if(flow.phase==='ended'){matchView.clear();match=null;matchSnapshot=null;}
  flow.openSetup();document.exitPointerLock?.();syncMatchFlow();
}
function invalidateMatchWorld(){cachedMatchWorld=null;worldMapRoot=null;worldTree=null;}
function getMatchWorld(){
  if(!cachedMatchWorld||worldMapRoot!==map||worldTree!==octree){
    cachedMatchWorld=createThreeWorld({tree:octree,Controller:PlayerController,mapConfig:MAP_CONFIG,coverRoot:map});
    worldMapRoot=map;worldTree=octree;
  }
  return cachedMatchWorld;
}
function startMatch(restart=false){
  if(offlineState.state==='reload-required'){toast('Reload the downloaded update from the match menu before playing again.');return;}
  if(!flow.ready){toast('The map and collision must finish loading before a match can start.');return;}
  if(flow.simulating)return;
  const settings=restart&&flow.settings?{...flow.settings}:matchUI.settings();
  bookmarkExplorer();clearInput();
  // The shared core owns every motor and weapon. No second player controller
  // is stepped by the presentation loop.
  try{
    const world=getMatchWorld();
    const next=new OfflineMatch({world,mode:settings.mode,difficulty:settings.difficulty,
      friendlyBots:settings.teamSize-1,enemyBots:settings.teamSize,seed:7,
      timeLimitSeconds:settings.duration});
    next.start();
    const snapshot=next.snapshot();
    if(flow.phase==='paused'||flow.phase==='ended')flow.phase='setup';
    setMode('walk',false);
    if(!flow.start(settings))return;
    match=next;matchSnapshot=snapshot;matchView.clear();killFeed.length=0;
    hitMarkerTimer=damageFlash=announcementTimer=0;matchUI.announce('');
    $('match-hit').classList.add('hidden');$('app').classList.remove('low-health','drag-match');
    $('controls').classList.add('hidden');$('help-toggle').setAttribute('aria-expanded','false');
    const player=matchSnapshot.actors.find(actor=>actor.id==='player');
    if(player){gameInput.setLook(player.yaw,player.pitch);camera.position.fromArray(player.eye);}
    matchAudio.setEnabled($('match-sound').value!=='off');matchAudio.activate();updateSoundControl();
    syncMatchFlow();match.drainEvents();requestLock();
    if(matchMedia('(pointer: coarse)').matches)$('app').classList.remove('drag-match');
    updateMatchPresentation(0);
  }catch(error){
    state.lastError=String(error);flow.phase='setup';flow.reason='';syncMatchFlow();
    toast(`Could not start the match. ${error.message||String(error)}`);console.error(error);
  }
}
function pauseMatch(reason){
  if(!flow.pause(reason))return;
  match?.pause();matchAudio.stopAll();clearInput();syncMatchFlow();document.exitPointerLock?.();
}
function resumeMatch(){
  if(!flow.resume())return;
  clearInput();match?.resume();$('controls').classList.add('hidden');$('help-toggle').setAttribute('aria-expanded','false');syncMatchFlow();matchAudio.activate();requestLock();
}
function leaveMatch(){
  match?.pause();matchAudio.stopAll();flow.leave();match=null;matchSnapshot=null;matchView.clear();clearInput();
  document.exitPointerLock?.();$('app').classList.remove('low-health','drag-match');syncMatchFlow();
  if(explorerBookmark){
    const saved=explorerBookmark;explorerBookmark=null;
    setMode(saved.mode,false);state.viewpoint=saved.viewpoint;$('viewpoint').value=saved.viewpoint;
    camera.position.fromArray(saved.position);yaw=saved.yaw;pitch=saved.pitch;applyLook();
    orbit.target.fromArray(saved.orbitTarget);preserveOverviewFrame=saved.preserveOverviewFrame;
    if(saved.mode==='walk')walker.spawn(camera.position);
  }
  camera.fov=58;camera.updateProjectionMatrix();state.ammo=30;state.reloading=false;updateAmmo();
}
function actorLabel(id){return id==='player'?'You':id?.startsWith('ally')?`Blue ${id.split('-')[1]}`:id?.startsWith('enemy')?`Orange ${id.split('-')[1]}`:'Arena';}
function handleMatchEvents(events){
  for(const event of events){
    if(event.type==='shot'){
      matchView.shot(event);matchAudio.shot(event.actorId==='player');
      if(event.actorId==='player'){weaponKick=.05;state.shots++;animateWeapon('Fire');}
    }
    if(event.type==='damage'){
      if(event.actorId==='player')damageFlash=.75;
      if(event.sourceId==='player'){
        hitMarkerTimer=.13;$('match-hit').classList.remove('hidden','kill');matchAudio.hit();
      }
    }
    if(event.type==='death'){
      killFeed.push(`${actorLabel(event.killerId)}  ›  ${actorLabel(event.actorId)}`);if(killFeed.length>3)killFeed.shift();
      if(event.actorId==='player'){matchAudio.death();flow.died();syncMatchFlow();}
      if(event.killerId==='player'){$('match-hit').classList.add('kill');hitMarkerTimer=.27;matchUI.announce('ELIMINATION');announcementTimer=1.1;}
    }
    if(event.type==='respawn'&&event.actorId==='player'){
      flow.respawned();gameInput.clear();const player=matchSnapshot.actors.find(actor=>actor.id==='player');
      if(player)gameInput.setLook(player.yaw,player.pitch);syncMatchFlow();
    }
    if(event.type==='tag-collected'&&event.actorId==='player'){
      matchUI.announce(event.confirmed||event.kind==='confirm'?'KILL CONFIRMED':'TAG DENIED');announcementTimer=1.3;matchAudio.tag(event.kind==='confirm');
    }
    if(event.type==='reload-started'&&event.actorId==='player'){animateWeapon('Reload',event.endsAt-event.time);matchAudio.reload();}
    if(event.type==='reload-completed'&&event.actorId==='player')matchAudio.reload(true);
    if(event.type==='match-ended'){
      flow.finish({winner:event.winner});matchAudio.stopAll();clearInput();syncMatchFlow();document.exitPointerLock?.();
    }
  }
}
function hudSnapshot(){
  const player=matchSnapshot?.actors.find(actor=>actor.id==='player')??{};
  return {player:{...player,...player.stats},score:matchSnapshot?.scores??[0,0],mode:matchSnapshot?.mode,
    remaining:matchSnapshot?.timeRemaining??300,scoreLimit:matchSnapshot?.scoreLimit,
    weapon:{...player.weapon,reserve:player.weapon?.infiniteReserve?Infinity:player.weapon?.reserve},
    movement:{sprinting:player.sprinting,sliding:player.sliding,crouched:player.crouched,adsFraction:player.weapon?.adsFraction??0,spreadMultiplier:player.sliding?1.7:player.sprinting?1.4:1},
    respawn:player.alive===false?Math.max(0,(player.respawnAt??0)-(matchSnapshot?.timeElapsed??0)):0,killFeed};
}
function updateMatchPresentation(dt){
  if(!matchSnapshot)return;
  const player=matchSnapshot.actors.find(actor=>actor.id==='player');
  if(player){
    camera.position.fromArray(player.eye);
    const recoil=player.weapon?.recoil??[0,0];
    yaw=player.yaw+recoil[1];pitch=clamp(player.pitch+recoil[0],-1.5,1.5);applyLook();
    aim=(player.weapon?.adsFraction??0)>.5;
    state.ammo=player.weapon?.ammo??0;state.reloading=player.weapon?.reloading??false;
    const ads=player.weapon?.adsFraction??0;
    camera.fov=damp(camera.fov,75-ads*17+(player.sprinting?5:0),12,Math.max(dt,.001));camera.updateProjectionMatrix();
  }
  matchView.update(matchSnapshot,flow.simulating?dt:0);
  const hud=hudSnapshot();matchUI.render(hud);
  if(flow.phase==='ended')matchUI.showResult(hud,matchSnapshot.winner);
  hitMarkerTimer=Math.max(0,hitMarkerTimer-dt);if(!hitMarkerTimer)$('match-hit').classList.add('hidden');
  damageFlash=Math.max(0,damageFlash-dt*2);$('damage-flash').style.opacity=String(damageFlash);
  if(announcementTimer>0){announcementTimer-=dt;if(announcementTimer<=0)matchUI.announce('');}
}

offlineClient=createOfflineClient({baseUrl:import.meta.env.BASE_URL,enabled:import.meta.env.PROD,canUpdate:()=>!flow.active,
  onStatus:status=>{offlineState=status;$('offline-status').textContent=offlineStatusText(status);$('retry-offline').classList.toggle('hidden',!['error','unsupported'].includes(status.state));$('update-offline').classList.toggle('hidden',!['update-ready','update-blocked','reload-required'].includes(status.state));}});
$('retry-offline').addEventListener('click',()=>offlineClient.start(true));
$('update-offline').addEventListener('click',()=>{if(offlineState.state==='reload-required'&&!flow.active)location.reload();else offlineClient.requestUpdate();});
setViewpoint('hero');setQuality('balanced');syncMatchFlow();
window.addEventListener('resize',resize);
function clearInput(){walker.resetInput();explorerJumpQueued=false;keys.clear();fireHeld=false;aim=false;drag=null;gameInput.clear();matchTouch.clear();}
window.addEventListener('pagehide',()=>{pauseMatch('Page hidden');matchAudio.stopAll();});
window.addEventListener('blur',()=>{clearInput();pauseMatch('Window lost focus');});
document.addEventListener('visibilitychange',()=>{if(document.hidden){clearInput();pauseMatch('The tab was hidden');}});
document.addEventListener('pointerlockchange',()=>{
  const wasLocked=state.pointerLocked;state.pointerLocked=document.pointerLockElement===canvas;clearInput();
  $('lock-hint').classList.toggle('hidden',state.mode!=='walk'||state.pointerLocked);
  if(state.pointerLocked)$('app').classList.remove('drag-match');
  else if(wasLocked&&flow.simulating)pauseMatch('Mouse released. The match clock is paused');
});
document.addEventListener('pointerlockerror',enableDragControls);
window.addEventListener('keydown',(event)=>{
  if(flow.modal){
    if(event.code==='Escape'&&!event.repeat){event.preventDefault();if(flow.phase==='paused')resumeMatch();else if(flow.phase==='setup')leaveMatch();}
    return;
  }
  if(flow.active){
    if(event.code==='Escape'||event.code==='KeyP'){event.preventDefault();pauseMatch('The match clock is paused');return;}
    if(event.code==='KeyH'&&!event.repeat){toggleHelp();return;}
    if(!flow.acceptsInput||['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target.tagName))return;
    const action=KEY_ACTIONS[event.code];
    if(action){event.preventDefault();gameInput.press(action,event.code);}
    if(event.code==='KeyF'&&!event.repeat)requestLock();
    if(event.code==='KeyI'&&!event.repeat&&!state.reloading)animateWeapon('Inspect');
    return;
  }
  if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target.tagName))return;
  if(event.code==='Space'&&event.repeat){event.preventDefault();return;}
  const movement=['KeyW','KeyA','KeyS','KeyD','KeyE','KeyQ','Space','ShiftLeft','ShiftRight'];
  if(movement.includes(event.code)){event.preventDefault();if(event.code==='Space'&&!keys.has('Space'))explorerJumpQueued=true;keys.add(event.code);dismissIntro();}
  if(event.repeat)return;
  if(event.code==='KeyF')requestLock();if(event.code==='KeyH')toggleHelp();
  if(event.code==='KeyR')state.mode==='walk'?reload():setViewpoint('hero');
  if(event.code==='KeyI'&&state.mode==='walk')animateWeapon('Inspect');
  if(event.code==='Digit1')setMode('fly');if(event.code==='Digit2')setMode('walk');if(event.code==='Digit3')setMode('orbit');
});
window.addEventListener('keyup',event=>{keys.delete(event.code);if(KEY_ACTIONS[event.code])gameInput.release(KEY_ACTIONS[event.code],event.code);});
canvas.addEventListener('contextmenu',event=>event.preventDefault());
canvas.addEventListener('pointerdown',event=>{
  if(flow.modal||flow.phase==='ended'||(flow.active&&!flow.acceptsInput)||state.mode==='orbit')return;
  dismissIntro();
  if(state.pointerLocked){
    if(flow.active){if(event.button===0)gameInput.press('fire','mouse');if(event.button===2)gameInput.press('ads','mouse');}
    else{if(event.button===0){fireHeld=true;fire();}if(event.button===2)aim=true;}
    return;
  }
  if(flow.active&&event.button===2)gameInput.press('ads','mouse');
  if(drag)return; // Leave the first looking finger in control until it ends.
  drag={id:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY};
  canvas.setPointerCapture?.(event.pointerId);
});
canvas.addEventListener('pointermove',event=>{
  if(flow.modal||(flow.active&&!flow.acceptsInput)||state.mode==='orbit')return;
  let dx=0,dy=0;
  if(state.pointerLocked){dx=event.movementX;dy=event.movementY;}
  else if(drag?.id===event.pointerId){dx=event.clientX-drag.x;dy=event.clientY-drag.y;drag.x=event.clientX;drag.y=event.clientY;}
  else return;
  if(flow.active){const player=matchSnapshot?.actors.find(actor=>actor.id==='player');gameInput.addLookDelta(dx,dy,player?.weapon?.adsFraction??0);return;}
  if(dx||dy)preserveOverviewFrame=false;
  const sensitivity=aim?.00135:.0023;yaw-=dx*sensitivity;pitch=clamp(pitch-dy*sensitivity,-1.5,1.5);applyLook();
});
window.addEventListener('pointerup',event=>{
  if(event.button===0){fireHeld=false;gameInput.release('fire','mouse');}
  if(event.button===2){aim=false;gameInput.release('ads','mouse');}
  if(drag?.id===event.pointerId){
    const click=Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<6;drag=null;
    if(click&&state.mode==='walk'&&event.pointerType!=='touch'&&!flow.modal)requestLock();
  }
});
canvas.addEventListener('pointercancel',clearInput);
canvas.addEventListener('lostpointercapture',event=>{if(drag?.id===event.pointerId)drag=null;});
$('explore').addEventListener('click',()=>{dismissIntro();setMode('fly');toast('WASD to fly · Q / E for height · drag to look · F to capture mouse');});
document.querySelectorAll('button[data-mode]').forEach(button=>button.addEventListener('click',()=>{dismissIntro();setMode(button.dataset.mode);}));
$('viewpoint').addEventListener('change',event=>{dismissIntro();setViewpoint(event.target.value);});
$('quality').addEventListener('change',event=>setQuality(event.target.value));
$('reset').addEventListener('click',()=>{if(flow.active)return;if(state.mode==='walk')spawnWalk();else setViewpoint('hero');canvas.focus({preventScroll:true});toast('View reset');});
function toggleHelp(){
  if(flow.active){pauseMatch('WASD move · Shift sprint · C slide · X crouch · Space jump · mouse fire / aim · R reload · Esc pause');return;}
  const panel=$('controls');const opening=$('help-toggle').getAttribute('aria-expanded')!=='true';
  panel.classList.toggle('hidden',!opening);panel.classList.toggle('mobile-open',opening);$('help-toggle').setAttribute('aria-expanded',String(opening));
}
$('help-toggle').addEventListener('click',toggleHelp);
$('controls-close').addEventListener('click',()=>{$('controls').classList.add('hidden');$('controls').classList.remove('mobile-open');$('help-toggle').setAttribute('aria-expanded','false');if(!flow.modal)canvas.focus({preventScroll:true});});
$('fullscreen').addEventListener('click',()=>{if(document.fullscreenElement)document.exitFullscreen?.();else $('app').requestFullscreen?.().catch(()=>toast('Fullscreen is unavailable in this browser.'));});
document.querySelectorAll('[data-key]').forEach(button=>{
  button.addEventListener('pointerdown',event=>{if(flow.active||flow.modal)return;event.preventDefault();dismissIntro();keys.add(button.dataset.key);button.setPointerCapture(event.pointerId);});
  for(const type of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(type,()=>keys.delete(button.dataset.key));
});

const manager = new THREE.LoadingManager();
let mapLoading=false,mapParsing=false,mapProgress=0;
function updateMapProgress(percent){mapProgress=Math.max(mapProgress,Math.min(percent,95));$('load-progress').style.width=`${Math.round(mapProgress)}%`;}
manager.onLoad=()=>offlineClient.start();
manager.onProgress=(_url,loaded,total)=>{if(mapParsing&&!state.ready)updateMapProgress(80+loaded/total*15);};
const loader = new GLTFLoader(manager);
const atmosphereOptions={loadingManager:manager,onError:()=>toast('Distant scenery could not load. The map is still usable.')};
scene.add(createClouds(atmosphereOptions),createScenery(atmosphereOptions));
const asset=(name)=>`${import.meta.env.BASE_URL}assets/${name}`;
async function loadMap(){
  if(mapLoading||state.ready)return;
  mapLoading=true;mapParsing=false;mapProgress=0;state.lastError=null;invalidateMatchWorld();flow.setAsset('map','loading');syncMatchFlow();
  $('load-progress').style.width='0%';$('error').classList.add('hidden');$('loading').classList.remove('completed');
  try{
    const environment=await loadGlbAsset(loader,asset(MAP_CONFIG.assets.map),{
      resourcePath:asset(''),
      decompressionStream:mapDelivery==='gzip'?window.DecompressionStream:null,
      onProgress:({loaded,total,lengthComputable})=>{if(lengthComputable)updateMapProgress(loaded/total*80);},
      onStage:stage=>{if(stage==='decode')updateMapProgress(80);if(stage==='parse'){mapParsing=true;updateMapProgress(85);}},
    });
    map=environment.scene;map.name=`SUNWARD_v${MAP_CONFIG.version}`;map.traverse(obj=>{if(obj.isMesh){obj.castShadow=!/^0[03]_/.test(obj.name);obj.receiveShadow=true;for(const material of Array.isArray(obj.material)?obj.material:[obj.material]){material.envMapIntensity=.25;}}});applyReferencePalette(map);scene.add(map);
    state.ready=true;state.lastError=null;$('load-progress').style.width='100%';$('loading').classList.add('completed');flow.setAsset('map','ready');syncMatchFlow();
  }catch(error){
    state.lastError=String(error);flow.setAsset('map','error',error.message);syncMatchFlow();$('loading').classList.add('completed');const panel=$('error');
    panel.textContent=`Could not load the map. ${error.message||String(error)} Run this project through a web server, or check your connection. `;
    const retry=document.createElement('button');retry.textContent='RETRY LOAD';retry.className='primary';retry.addEventListener('click',()=>loadMap());panel.append(retry);panel.classList.remove('hidden');console.error(error);
  }finally{mapLoading=false;mapParsing=false;}
}
let collisionLoading=false;
async function loadCollision(){
  if(collisionLoading||state.collisionReady)return;
  collisionLoading=true;invalidateMatchWorld();flow.setAsset('collision','loading');syncMatchFlow();
  try{
    const collision=await loader.loadAsync(asset(MAP_CONFIG.assets.collision));
    octree=buildCollisionOctree(collision.scene);walker.tree=octree;state.collisionReady=true;state.collisionStats=octree.stats;
    flow.setAsset('collision','ready');
  }catch(error){
    flow.setAsset('collision','error',error.message);console.warn('Collision unavailable',error);
    toast('Collision could not load. Retry in Play offline; freefly and overview still work.');
  }finally{collisionLoading=false;syncMatchFlow();}
}
async function loadRifle(){
  try{const gun=await loader.loadAsync(asset(MAP_CONFIG.assets.rifle));rifle=gun.scene;weaponBasis.add(rifle);rifle.traverse(obj=>{if(obj.isMesh)obj.frustumCulled=false;});mixer=new THREE.AnimationMixer(rifle);clips=Object.fromEntries(gun.animations.map(clip=>[clip.name,clip]));state.rifleReady=true;}
  catch(error){console.warn('Optional carbine unavailable',error);toast('Carbine art could not load. Gameplay and hit detection still work.');}
}
loadMap();loadCollision();loadRifle();

const direction=new THREE.Vector3(),right=new THREE.Vector3(),up=new THREE.Vector3(0,1,0),move=new THREE.Vector3();
function updateFly(dt){const axis=normalizedInput((keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0),(keys.has('KeyE')?1:0)-(keys.has('KeyQ')?1:0),(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0));if(axis.some(value=>value!==0))preserveOverviewFrame=false;camera.getWorldDirection(direction);right.crossVectors(direction,up).normalize();move.set(0,0,0).addScaledVector(right,axis[0]).addScaledVector(up,axis[1]).addScaledVector(direction,axis[2]);const speed=keys.has('ShiftLeft')||keys.has('ShiftRight')?22:9;camera.position.addScaledVector(move,speed*dt);}
function updateWalk(dt){if(!state.collisionReady)return;walker.update(dt,{x:(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0),z:(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0),yaw,sprint:keys.has('ShiftLeft')||keys.has('ShiftRight'),jump:keys.has('Space')||explorerJumpQueued});explorerJumpQueued=false;walker.cameraPosition(camera.position);if(camera.position.y<-8||Math.abs(camera.position.x)>180||Math.abs(camera.position.z)>180)spawnWalk();}
let previous=performance.now(),fpsStart=previous,frameCount=0;
function frame(now){
  requestAnimationFrame(frame);const elapsed=Math.max(0,(now-previous)/1000),dt=Math.min(elapsed,.05);previous=now;state.frame++;
  if(state.ready){
    if(match&&flow.simulating){const result=match.update(elapsed,gameInput.consumeCommand());matchSnapshot=result.snapshot;handleMatchEvents(result.events);}
    if(match&&(flow.active||flow.phase==='ended'))updateMatchPresentation(dt);
    else if(!flow.modal){if(state.mode==='orbit')orbit.update();else if(state.mode==='fly')updateFly(dt);else updateWalk(dt);}
    mixer?.update(match&&!flow.simulating?0:dt);
    if(!match&&!flow.modal){
      shotCooldown=Math.max(0,shotCooldown-dt);
      if(state.reloading){reloadTimer-=dt;if(reloadTimer<=0){state.reloading=false;state.ammo=30;updateAmmo();}}
      if(fireHeld)fire();
    }
    weaponKick=damp(weaponKick,0,14,dt);weaponSway+=dt*((flow.active?(matchSnapshot?.actors.find(actor=>actor.id==='player')?.sprinting?1:0):keys.size)?9:1.5);
    const scale=.15,adsBlend=match?(matchSnapshot?.actors.find(actor=>actor.id==='player')?.weapon.adsFraction??0):(aim?1:0);
    const target=[.26*(1-adsBlend),-.39+(-1.48*scale+.39)*adsBlend,-.89+(-1.85*scale+.89)*adsBlend];
    weaponAnchor.position.x=damp(weaponAnchor.position.x,target[0]+(aim?0:Math.sin(weaponSway)*.003),12,dt);
    weaponAnchor.position.y=damp(weaponAnchor.position.y,target[1]+(aim?0:Math.cos(weaponSway*2)*.004),12,dt);
    weaponAnchor.position.z=damp(weaponAnchor.position.z,target[2]+weaponKick,12,dt);
    if(!match){camera.fov=damp(camera.fov,aim?48:58,10,dt);camera.updateProjectionMatrix();}
    weaponCamera.fov=camera.fov;weaponCamera.updateProjectionMatrix();
  }
  renderer.autoClear=true;renderer.render(scene,camera);state.drawCalls=renderer.info.render.calls;state.triangles=renderer.info.render.triangles;
  const playerAlive=!match||matchSnapshot?.actors.find(actor=>actor.id==='player')?.alive;
  if(state.mode==='walk'&&state.rifleReady&&playerAlive){renderer.autoClear=false;renderer.clearDepth();renderer.render(weaponScene,weaponCamera);renderer.autoClear=true;}
  if(toastTimer>0){toastTimer-=dt;if(toastTimer<=0)$('toast').classList.add('hidden');}
  frameCount++;if(now-fpsStart>700){state.fps=Math.round(frameCount*1000/(now-fpsStart));$('fps').textContent=`${state.fps} FPS`;$('position').textContent=`X ${camera.position.x.toFixed(1)}  Y ${camera.position.y.toFixed(1)}  Z ${camera.position.z.toFixed(1)} / PROTOTYPE M`;fpsStart=now;frameCount=0;}
}
requestAnimationFrame(frame);
Object.defineProperty(window,'sunwardDebug',{configurable:false,get:()=>Object.freeze({...state,offlineCache:offlineState.state,match:matchSnapshot?Object.freeze({status:matchSnapshot.status,mode:matchSnapshot.mode,scores:[...matchSnapshot.scores],remaining:matchSnapshot.timeRemaining,actors:matchSnapshot.actors.length}):null,onFloor:walker.onFloor,aiming:aim,fireHeld,camera:Object.freeze({position:camera.position.toArray(),yaw,pitch,fov:camera.fov}),assets:Object.freeze({...MAP_CONFIG.assets}),clips:Object.keys(clips),mapMeshes:map?(()=>{let n=0;map.traverse(o=>{if(o.isMesh)n++;});return n;})():0,renderer:Object.freeze({webgl2:true,pixelRatio:renderer.getPixelRatio(),width:canvas.width,height:canvas.height})})});

}
start();
