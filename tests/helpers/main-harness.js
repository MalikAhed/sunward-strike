import {readFile} from 'node:fs/promises';
import * as Three from 'three';
import {parseDOM,NodeModel} from './dom-model.js';
import {buildCollisionOctree} from '../../src/collision.js';
import {WalkController} from '../../src/physics.js';
import {PlayerController} from '../../src/gameplay/player-controller.js';
import {GameInput,KEY_ACTIONS} from '../../src/gameplay/input-controller.js';
import {OfflineMatch} from '../../src/gameplay/match.js';
import {createThreeWorld} from '../../src/gameplay/three-world.js';
import {MatchFlow} from '../../src/gameplay/match-flow.js';
import {MatchUI} from '../../src/gameplay/match-ui.js';
import {MatchRenderer} from '../../src/gameplay/match-renderer.js';
import {MatchAudio} from '../../src/gameplay/match-audio.js';
import {createOfflineClient,offlineStatusText,chooseMapDelivery} from '../../src/gameplay/offline-client.js';
import {bindTouchActions} from '../../src/gameplay/touch-controls.js';
import {MAP_CONFIG} from '../../src/map-config.js';
import * as math from '../../src/math.js';

const html=await readFile(new URL('../../index.html',import.meta.url),'utf8');
const code=(await readFile(new URL('../../src/main.js',import.meta.url),'utf8')).replace(/^import .*;\n/gm,'').replaceAll('import.meta.env.BASE_URL',JSON.stringify('/test/subpath/')).replaceAll('import.meta.env.PROD','false');
export async function makeApp({failMap=false,failCollision=false,failLock=false,coarse=false,failGL=false,collisionScene=null,visualScene=null}={}){
 const document=parseDOM(html),window=new NodeModel('window'),canvas=document.getElementById('scene');
 Object.assign(window,{innerWidth:1280,innerHeight:720,devicePixelRatio:1});
 let now=0,frameCallback,latestMatch,mapCalls=0,collisionCalls=0,worldBuilds=0,latestWorld=null;
 const errors=[];
 const floor=collisionScene??new Three.Group();if(!collisionScene){const mesh=new Three.Mesh(new Three.BoxGeometry(240,1,240),new Three.MeshBasicMaterial());mesh.position.y=-.5;floor.add(mesh);}
 const tree=buildCollisionOctree(floor);
 class Renderer {constructor(){if(failGL)throw new Error('WebGL unavailable');this.shadowMap={};this.info={render:{calls:0,triangles:0}};this.ratio=1;}setClearColor(){}setPixelRatio(v){this.ratio=v;}getPixelRatio(){return this.ratio;}setSize(w,h){canvas.width=w;canvas.height=h;}render(){this.info.render.calls++;}clearDepth(){}}
 class PMREM {fromScene(){return {texture:new Three.Texture()};}}
 class Orbit {constructor(){this.target=new Three.Vector3();}addEventListener(){}update(){}}
 class Loader {async loadAsync(url){
   if(url.includes('collision')){collisionCalls++;if(failCollision){failCollision=false;throw new Error('test collision failure');}return {scene:floor.clone()};}
   return {scene:new Three.Group(),animations:[]};
 }}
 class CapturedMatch extends OfflineMatch {constructor(settings){super(settings);latestMatch=this;}}
 const loadGlbAsset=async(_loader,url,options)=>{mapCalls++;if(failMap){failMap=false;throw new Error('test map failure');}options?.onProgress?.({loaded:1,total:1,lengthComputable:true});return {scene:visualScene?.clone()??new Three.Group(),url};};
 document.exitPointerLock=()=>{if(document.pointerLockElement){document.pointerLockElement=null;document.dispatch('pointerlockchange');}};
 canvas.requestPointerLock=()=>{if(failLock)return Promise.reject(new Error('test pointer lock failure'));document.pointerLockElement=canvas;document.dispatch('pointerlockchange');return Promise.resolve();};
 const bindings={THREE:{...Three,WebGLRenderer:Renderer,PMREMGenerator:PMREM},GLTFLoader:Loader,OrbitControls:Orbit,
  buildCollisionOctree:()=>tree,loadGlbAsset,createClouds:()=>new Three.Group(),createScenery:()=>new Three.Group(),createSky:()=>new Three.Group(),applyReferencePalette:()=>{},
  WalkController,PlayerController,GameInput,KEY_ACTIONS,OfflineMatch:CapturedMatch,createThreeWorld:options=>{worldBuilds++;latestWorld=createThreeWorld(options);return latestWorld;},MatchFlow,MatchUI,MatchRenderer,MatchAudio,bindTouchActions,
  createOfflineClient:options=>createOfflineClient({...options,environment:window}),offlineStatusText,chooseMapDelivery,RoomEnvironment:Three.Scene,MAP_CONFIG,...math,document,window,matchMedia:()=>({matches:coarse}),location:{reload(){}},
  performance:{now:()=>now},requestAnimationFrame:callback=>{frameCallback=callback;},console:{warn:(...args)=>errors.push(args),error:(...args)=>errors.push(args)},
 };
 new Function(...Object.keys(bindings),code)(...Object.values(bindings));
 await settle();
 const app={document,window,canvas,errors,get match(){return latestMatch;},get mapCalls(){return mapCalls;},get collisionCalls(){return collisionCalls;},get worldBuilds(){return worldBuilds;},get world(){return latestWorld;},
  click:id=>document.getElementById(id).dispatch('click'),
  key:(code,type='keydown')=>window.dispatch(type,{code,repeat:false,target:document.activeElement??canvas}),
  tick:(frames=1,step=1000/60)=>{for(let i=0;i<frames;i++){now+=step;frameCallback?.(now);}},
  async settle(){await settle();},
 };
 return app;
}
async function settle(){for(let i=0;i<6;i++)await Promise.resolve();}
