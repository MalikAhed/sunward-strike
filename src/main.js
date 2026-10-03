import './style.css';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { buildCollisionOctree } from './collision.js';
import {loadGlbAsset} from './asset-loader.js';
import {createClouds, createSky, applyReferencePalette} from './atmosphere.js';
import {WalkController} from './physics.js';
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
  for(const selector of ['.mode-switch','#intro','#loading','#controls','#bottombar','.bottombar','#telemetry','#crosshair','#weapon-hud','#lock-hint','.touch-controls','#help-toggle','#fullscreen','#error'])document.querySelector(selector)?.classList.add('hidden');
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
const sky = createSky(); scene.add(sky,createClouds());
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(),.04).texture;
scene.environmentIntensity=.28;
const orbit = new OrbitControls(camera,canvas);
orbit.enabled=false; orbit.enableDamping=true; orbit.dampingFactor=.08;
orbit.minDistance=4; orbit.maxDistance=320; orbit.maxPolarAngle=Math.PI*.49;
orbit.target.fromArray(MAP_CONFIG.orbitTarget);
let octree = null;
const walker = new WalkController();
const velocity = new THREE.Vector3();
let yaw=0,pitch=0,drag=null,aim=false,fireHeld=false,shotCooldown=0,reloadTimer=0,toastTimer=0,weaponKick=0;
let map=null,rifle=null,mixer=null,currentAction=null,clips={},weaponSway=0;
const keys = new Set();
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
function setViewpoint(name){const view=VIEWPOINTS[name]||VIEWPOINTS.hero;state.viewpoint=name;preserveOverviewFrame=['hero','topdown'].includes(name);$('viewpoint').value=name;if(state.mode==='walk')setMode('fly',false);setLook(['hero','topdown'].includes(name)?fittedOverviewPosition(view,window.innerWidth/window.innerHeight):view.position,view.target);orbit.target.fromArray(view.target);velocity.set(0,0,0);}
function spawnWalk(position=MAP_CONFIG.spawns.street,target=MAP_CONFIG.viewpoints.street.target){preserveOverviewFrame=false;setLook(position,target);walker.spawn(camera.position);velocity.set(0,0,0);}
function setMode(mode,reset=true){preserveOverviewFrame=overviewFrameAfterModeChange(preserveOverviewFrame,mode);if(state.mode==='orbit'&&mode!=='orbit'){yaw=camera.rotation.y;pitch=camera.rotation.x;}state.mode=mode;$('app').dataset.mode=mode;orbit.enabled=mode==='orbit';orbit.autoRotate=false;keys.clear();aim=false;fireHeld=false;document.querySelectorAll('button[data-mode]').forEach(button=>{const selected=button.dataset.mode===mode;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));});$('mode-label').textContent={fly:'FREEFLY',walk:'FIRST PERSON',orbit:'ORBIT'}[mode];$('crosshair').classList.toggle('hidden',mode!=='walk');$('walk-controls').classList.toggle('hidden',mode!=='walk');$('weapon-hud').classList.toggle('hidden',mode!=='walk');$('lock-hint').classList.toggle('hidden',mode!=='walk'||state.pointerLocked);$('vertical-label').textContent=mode==='walk'?'Freefly only':'Descend / ascend';$('mouse-label').textContent=mode==='orbit'?'Drag / scroll to orbit':'Drag to look';$('guide-note').textContent=mode==='walk'?'Capsule collision + gravity. Cosmetic firing; no combat targets.':mode==='orbit'?'Drag to orbit. Scroll to zoom. Right-drag to pan.':'Freefly passes through geometry. No boundaries.';if(mode==='walk'&&reset)spawnWalk();if(mode==='orbit'){document.exitPointerLock?.();if(reset)setViewpoint('hero');orbit.target.fromArray(MAP_CONFIG.orbitTarget);orbit.update();}if(mode!=='walk')state.reloading=false;}
function setQuality(value){state.quality=value;const dpr=window.devicePixelRatio||1;renderer.setPixelRatio(Math.min(dpr,{high:2,balanced:1.5,low:1}[value]));renderer.shadowMap.enabled=value!=='low';sunlight.shadow.mapSize.set(value==='high'?4096:2048,value==='high'?4096:2048);if(sunlight.shadow.map){sunlight.shadow.map.dispose();sunlight.shadow.map=null;}sunlight.shadow.needsUpdate=true;scene.traverse(obj=>{if(obj.isMesh){for(const mat of Array.isArray(obj.material)?obj.material:[obj.material])mat.needsUpdate=true;}});resize();}
function resize(){const w=window.innerWidth,h=window.innerHeight;camera.aspect=w/h;camera.updateProjectionMatrix();weaponCamera.aspect=w/h;weaponCamera.updateProjectionMatrix();renderer.setSize(w,h,false);const position=overviewFrameOnResize(state.viewpoint,w/h,{active:preserveOverviewFrame,mode:state.mode});if(position){setLook(position,VIEWPOINTS[state.viewpoint].target);if(orbit.enabled)orbit.update();}}
function requestLock(){if(state.mode==='orbit')return;try{const result=canvas.requestPointerLock();result?.catch?.(()=>toast('Mouse capture was unavailable. Drag the scene to look instead.'));}catch{toast('Drag the scene to look. Mouse capture is unavailable here.');}}
function animateWeapon(name){if(!mixer||!clips[name])return;currentAction?.stop();currentAction=mixer.clipAction(clips[name]);currentAction.reset().setLoop(THREE.LoopOnce,1);currentAction.clampWhenFinished=false;currentAction.play();}
function updateAmmo(){ $('ammo').innerHTML=`${state.reloading?'··':state.ammo}<span>/ ∞</span>`; }
function reload(){if(state.mode!=='walk'||state.reloading||state.ammo===30)return;state.reloading=true;reloadTimer=3;animateWeapon('Reload');updateAmmo();}
function fire(){if(state.mode!=='walk'||state.reloading||shotCooldown>0)return;if(!state.ammo){reload();return;}state.ammo--;state.shots++;shotCooldown=.13;weaponKick=.05;animateWeapon('Fire');updateAmmo();}

setViewpoint('hero');setQuality('balanced');
window.addEventListener('resize',resize);
function clearInput(){keys.clear();fireHeld=false;aim=false;drag=null;}
window.addEventListener('blur',clearInput);
document.addEventListener('visibilitychange',()=>{if(document.hidden)clearInput();});
document.addEventListener('pointerlockchange',()=>{state.pointerLocked=document.pointerLockElement===canvas;clearInput();$('lock-hint').classList.toggle('hidden',state.mode!=='walk'||state.pointerLocked);});
document.addEventListener('pointerlockerror',()=>toast('Mouse capture unavailable. Drag to look instead.'));
window.addEventListener('keydown',(event)=>{if(['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName))return;const movement=['KeyW','KeyA','KeyS','KeyD','KeyE','KeyQ','Space','ShiftLeft','ShiftRight'];if(movement.includes(event.code)){event.preventDefault();keys.add(event.code);dismissIntro();}if(event.repeat)return;if(event.code==='KeyF')requestLock();if(event.code==='KeyH')toggleHelp();if(event.code==='KeyR')state.mode==='walk'?reload():setViewpoint('hero');if(event.code==='KeyI'&&state.mode==='walk')animateWeapon('Inspect');if(event.code==='Digit1')setMode('fly');if(event.code==='Digit2')setMode('walk');if(event.code==='Digit3')setMode('orbit');});
window.addEventListener('keyup',event=>keys.delete(event.code));
canvas.addEventListener('contextmenu',event=>event.preventDefault());
canvas.addEventListener('pointerdown',event=>{if(state.mode==='orbit')return;dismissIntro();if(state.pointerLocked){if(event.button===0){fireHeld=true;fire();}if(event.button===2)aim=true;return;}drag={id:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY};canvas.setPointerCapture?.(event.pointerId);});
canvas.addEventListener('pointermove',event=>{if(state.mode==='orbit')return;let dx=0,dy=0;if(state.pointerLocked){dx=event.movementX;dy=event.movementY;}else if(drag?.id===event.pointerId){dx=event.clientX-drag.x;dy=event.clientY-drag.y;drag.x=event.clientX;drag.y=event.clientY;}else return;if(dx||dy)preserveOverviewFrame=false;const sensitivity=aim?.00135:.0023;yaw-=dx*sensitivity;pitch=clamp(pitch-dy*sensitivity,-1.5,1.5);applyLook();});
window.addEventListener('pointerup',event=>{if(state.pointerLocked){if(event.button===0)fireHeld=false;if(event.button===2)aim=false;}if(drag?.id===event.pointerId){const click=Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)<6;drag=null;if(click&&state.mode==='walk'&&event.pointerType!=='touch')requestLock();}});
canvas.addEventListener('pointercancel',clearInput);
$('explore').addEventListener('click',()=>{dismissIntro();setMode('fly');toast('WASD to fly · Q / E for height · drag to look · F to capture mouse');});
document.querySelectorAll('button[data-mode]').forEach(button=>button.addEventListener('click',()=>{dismissIntro();setMode(button.dataset.mode);}));
$('viewpoint').addEventListener('change',event=>{dismissIntro();setViewpoint(event.target.value);});
$('quality').addEventListener('change',event=>setQuality(event.target.value));
$('reset').addEventListener('click',()=>{if(state.mode==='walk')spawnWalk();else setViewpoint('hero');toast('View reset');});
function toggleHelp(){const panel=$('controls');const opening=$('help-toggle').getAttribute('aria-expanded')!=='true';panel.classList.toggle('hidden',!opening);panel.classList.toggle('mobile-open',opening);$('help-toggle').setAttribute('aria-expanded',String(opening));}
$('help-toggle').addEventListener('click',toggleHelp);$('controls-close').addEventListener('click',()=>{$('controls').classList.add('hidden');$('controls').classList.remove('mobile-open');$('help-toggle').setAttribute('aria-expanded','false');});
$('fullscreen').addEventListener('click',()=>{if(document.fullscreenElement)document.exitFullscreen?.();else $('app').requestFullscreen?.().catch(()=>toast('Fullscreen is unavailable in this browser.'));});
document.querySelectorAll('[data-key]').forEach(button=>{button.addEventListener('pointerdown',event=>{event.preventDefault();dismissIntro();keys.add(button.dataset.key);button.setPointerCapture(event.pointerId);});for(const type of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(type,()=>keys.delete(button.dataset.key));});

const manager = new THREE.LoadingManager();
let mapLoading=false,mapParsing=false,mapProgress=0;
function updateMapProgress(percent){mapProgress=Math.max(mapProgress,Math.min(percent,95));$('load-progress').style.width=`${Math.round(mapProgress)}%`;}
manager.onProgress=(_url,loaded,total)=>{if(mapParsing&&!state.ready)updateMapProgress(80+loaded/total*15);};
const loader = new GLTFLoader(manager);
const asset=(name)=>`${import.meta.env.BASE_URL}assets/${name}`;
async function loadMap(){
  if(mapLoading||state.ready)return;
  mapLoading=true;mapParsing=false;mapProgress=0;state.lastError=null;
  $('load-progress').style.width='0%';$('error').classList.add('hidden');$('loading').classList.remove('completed');
  try{
    const environment=await loadGlbAsset(loader,asset(MAP_CONFIG.assets.map),{
      resourcePath:asset(''),
      onProgress:({loaded,total,lengthComputable})=>{if(lengthComputable)updateMapProgress(loaded/total*80);},
      onStage:stage=>{if(stage==='decode')updateMapProgress(80);if(stage==='parse'){mapParsing=true;updateMapProgress(85);}},
    });
    map=environment.scene;map.name=`SUNWARD_v${MAP_CONFIG.version}`;map.traverse(obj=>{if(obj.isMesh){obj.castShadow=!/^0[03]_/.test(obj.name);obj.receiveShadow=true;for(const material of Array.isArray(obj.material)?obj.material:[obj.material]){material.envMapIntensity=.25;}}});applyReferencePalette(map);scene.add(map);
    state.ready=true;state.lastError=null;$('load-progress').style.width='100%';$('loading').classList.add('completed');
  }catch(error){
    state.lastError=String(error);$('loading').classList.add('completed');const panel=$('error');
    panel.textContent=`Could not load the map. ${error.message||String(error)} Run this project through a web server, or check your connection. `;
    const retry=document.createElement('button');retry.textContent='RETRY LOAD';retry.className='primary';retry.addEventListener('click',()=>loadMap());panel.append(retry);panel.classList.remove('hidden');console.error(error);
  }finally{mapLoading=false;mapParsing=false;}
}
async function loadOptional(){
  try{const collision=await loader.loadAsync(asset(MAP_CONFIG.assets.collision));octree=buildCollisionOctree(collision.scene);walker.tree=octree;state.collisionReady=true;state.collisionStats=octree.stats;}
  catch(error){console.warn('Collision unavailable',error);toast('Walking collision unavailable. Freefly and overview still work.');}
  try{const gun=await loader.loadAsync(asset(MAP_CONFIG.assets.rifle));rifle=gun.scene;weaponBasis.add(rifle);rifle.traverse(obj=>{if(obj.isMesh)obj.frustumCulled=false;});mixer=new THREE.AnimationMixer(rifle);clips=Object.fromEntries(gun.animations.map(clip=>[clip.name,clip]));state.rifleReady=true;}
  catch(error){console.warn('Optional carbine unavailable',error);toast('Carbine unavailable. You can still explore the map.');}
}
loadMap();loadOptional();

const direction=new THREE.Vector3(),right=new THREE.Vector3(),up=new THREE.Vector3(0,1,0),move=new THREE.Vector3();
function updateFly(dt){const axis=normalizedInput((keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0),(keys.has('KeyE')?1:0)-(keys.has('KeyQ')?1:0),(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0));if(axis.some(value=>value!==0))preserveOverviewFrame=false;camera.getWorldDirection(direction);right.crossVectors(direction,up).normalize();move.set(0,0,0).addScaledVector(right,axis[0]).addScaledVector(up,axis[1]).addScaledVector(direction,axis[2]);const speed=keys.has('ShiftLeft')||keys.has('ShiftRight')?22:9;camera.position.addScaledVector(move,speed*dt);}
function updateWalk(dt){if(!state.collisionReady)return;walker.update(dt,{x:(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0),z:(keys.has('KeyW')?1:0)-(keys.has('KeyS')?1:0),yaw,sprint:keys.has('ShiftLeft')||keys.has('ShiftRight'),jump:keys.has('Space')});if(keys.has('Space'))keys.delete('Space');walker.cameraPosition(camera.position);if(camera.position.y<-8||Math.abs(camera.position.x)>180||Math.abs(camera.position.z)>180)spawnWalk();}
let previous=performance.now(),fpsStart=previous,frameCount=0;
function frame(now){requestAnimationFrame(frame);const dt=Math.min((now-previous)/1000,.04);previous=now;state.frame++;if(state.ready){if(state.mode==='orbit')orbit.update();else if(state.mode==='fly')updateFly(dt);else updateWalk(dt);mixer?.update(dt);shotCooldown=Math.max(0,shotCooldown-dt);if(state.reloading){reloadTimer-=dt;if(reloadTimer<=0){state.reloading=false;state.ammo=30;updateAmmo();}}if(fireHeld)fire();weaponKick=damp(weaponKick,0,14,dt);weaponSway+=dt*(keys.size?9:1.5);const scale=.15;const target=aim?[0,-1.48*scale,-1.85*scale]:[.26,-.39,-.89];weaponAnchor.position.x=damp(weaponAnchor.position.x,target[0]+(aim?0:Math.sin(weaponSway)*.003),12,dt);weaponAnchor.position.y=damp(weaponAnchor.position.y,target[1]+(aim?0:Math.cos(weaponSway*2)*.004),12,dt);weaponAnchor.position.z=damp(weaponAnchor.position.z,target[2]+weaponKick,12,dt);camera.fov=damp(camera.fov,aim?48:58,10,dt);camera.updateProjectionMatrix();weaponCamera.fov=camera.fov;weaponCamera.updateProjectionMatrix();}
renderer.autoClear=true;renderer.render(scene,camera);state.drawCalls=renderer.info.render.calls;state.triangles=renderer.info.render.triangles;if(state.mode==='walk'&&state.rifleReady){renderer.autoClear=false;renderer.clearDepth();renderer.render(weaponScene,weaponCamera);renderer.autoClear=true;}
if(toastTimer>0){toastTimer-=dt;if(toastTimer<=0)$('toast').classList.add('hidden');}frameCount++;if(now-fpsStart>700){state.fps=Math.round(frameCount*1000/(now-fpsStart));$('fps').textContent=`${state.fps} FPS`;$('position').textContent=`X ${camera.position.x.toFixed(1)}  Y ${camera.position.y.toFixed(1)}  Z ${camera.position.z.toFixed(1)} / PROTOTYPE M`;fpsStart=now;frameCount=0;}}
requestAnimationFrame(frame);
Object.defineProperty(window,'sunwardDebug',{configurable:false,get:()=>Object.freeze({...state,onFloor:walker.onFloor,aiming:aim,fireHeld,camera:Object.freeze({position:camera.position.toArray(),yaw,pitch,fov:camera.fov}),assets:Object.freeze({...MAP_CONFIG.assets}),clips:Object.keys(clips),mapMeshes:map?(()=>{let n=0;map.traverse(o=>{if(o.isMesh)n++;});return n;})():0,renderer:Object.freeze({webgl2:true,pixelRatio:renderer.getPixelRatio(),width:canvas.width,height:canvas.height})})});

}
start();
