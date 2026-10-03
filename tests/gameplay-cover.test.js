import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import * as THREE from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {buildOpaqueCover,isOpaqueCoverMaterial} from '../src/gameplay/cover.js';
import {decodeGlbBytes} from '../src/asset-loader.js';import {MAP_CONFIG} from '../src/map-config.js';

function plane(name,material,z=0){const object=new THREE.Mesh(new THREE.PlaneGeometry(4,4),material);object.name=name;object.position.z=z;return object;}
test('cover preserves exact transformed front/back/double sided triangles without changing source geometry',()=>{
 const root=new THREE.Group(),material=new THREE.MeshBasicMaterial({side:THREE.DoubleSide}),object=plane('solid timber',material);object.position.set(3,2,-5);object.rotation.y=.37;object.scale.x=-2;root.add(object);root.updateMatrixWorld(true,true);
 const original=Array.from(object.geometry.attributes.position.array),center=object.getWorldPosition(new THREE.Vector3()),normal=new THREE.Vector3(0,0,1).transformDirection(object.matrixWorld),cover=buildOpaqueCover(root);
 for(const sign of[-1,1]){const origin=center.clone().addScaledVector(normal,sign*3),direction=normal.clone().multiplyScalar(-sign);assert.ok(Math.abs(cover.raycast(origin.toArray(),direction.toArray(),10)-3)<1e-6);}
 assert.equal(cover.stats.triangleCount,2,'double-sided geometry is not duplicated');assert.deepEqual(Array.from(object.geometry.attributes.position.array),original);
});
test('decorative OPAQUE grass, MASK leaves, blended layers and sky are excluded; bark and timber stay solid',()=>{
 for(const name of['V4R5_Lawn_Blade_0','V3_Grass_YellowGreen_0','V2_Leaf_Olive']){const material=new THREE.MeshStandardMaterial({name});assert.equal(isOpaqueCoverMaterial(material,new THREE.Mesh()),false);}
 const masked=new THREE.MeshStandardMaterial({name:'leaf',alphaTest:.5});assert.equal(isOpaqueCoverMaterial(masked,new THREE.Mesh()),false);
 assert.equal(isOpaqueCoverMaterial(new THREE.MeshStandardMaterial({transparent:true,opacity:.8}),new THREE.Mesh()),false);
 for(const name of['V4R5_Warm_Bark_0','V3_Tone_Honey_Timber_p1r5'])assert.equal(isOpaqueCoverMaterial(new THREE.MeshStandardMaterial({name}),new THREE.Mesh()),true);
 const group=new THREE.Group();group.add(plane('grass',new THREE.MeshStandardMaterial({name:'V4R5_Lawn_Blade_0'})));assert.equal(buildOpaqueCover(group).raycast([0,0,2],[0,0,-1],10),Infinity);
});
test('single-sided cover respects front/back material policy and skips invisible parents',()=>{
 for(const side of[THREE.FrontSide,THREE.BackSide]){const group=new THREE.Group(),mesh=plane('thin solid',new THREE.MeshBasicMaterial({side}));group.add(mesh);const cover=buildOpaqueCover(group);assert.equal(Number.isFinite(cover.raycast([0,0,2],[0,0,-1],10)),side===THREE.FrontSide);assert.equal(Number.isFinite(cover.raycast([0,0,-2],[0,0,1],10)),side===THREE.BackSide);}
 const root=new THREE.Group(),hidden=new THREE.Group();hidden.visible=false;hidden.add(plane('hidden',new THREE.MeshBasicMaterial({side:THREE.DoubleSide})));root.add(hidden);assert.equal(buildOpaqueCover(root).stats.triangleCount,0);
});

test('actual visual house stairs/mullion stop rays while adjacent authored upper windows remain open',async()=>{
 const previousSelf=globalThis.self,previousLoad=THREE.TextureLoader.prototype.load;globalThis.self=globalThis;
 THREE.TextureLoader.prototype.load=function(_url,onLoad){const texture=new THREE.Texture();texture.image={width:1,height:1};if(onLoad)queueMicrotask(()=>onLoad(texture));return texture;};
 try{
  const bytes=await decodeGlbBytes(fs.readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`,import.meta.url))),gltf=await new GLTFLoader().parseAsync(bytes,'');
  const cover=buildOpaqueCover(gltf.scene);
  const cases=[
   {name:'A stair side',from:[-11.214773370862341,1.4633333333333334,14.956899710512701],to:[-12.73482456768887,1.4633333333333334,14.457455660566922],blocked:true},
   {name:'A narrow mullion',from:[-13.187569150973303,4.82,17.11680247994024],to:[-15.467645946213095,4.82,16.367636405021575],blocked:true},
   {name:'A upper window',from:[-5.570517002470218,4.82,13.94311165938967],to:[-2.6831060887211953,1.654,5.155315677736304],blocked:false},
   {name:'A window beside mullion',from:[-13.109531018169276,4.82,16.879294480436094],to:[-15.389607813409068,4.82,16.13012840551743],blocked:false},
  ];
  for(const sample of cases){const delta=new THREE.Vector3(...sample.to).sub(new THREE.Vector3(...sample.from)),length=delta.length(),hit=cover.raycast(sample.from,delta.normalize().toArray(),length-.025);assert.equal(Number.isFinite(hit),sample.blocked,sample.name);}
  assert.ok(cover.stats.triangleCount<120000);assert.ok(cover.stats.excluded.some(item=>/Lawn_Blade/.test(item.material)),'Actual baked lawn materials are excluded');assert.ok(cover.stats.accepted.every(item=>!/Lawn_Blade|Canopy_Leaf/.test(item.material)),'No decorative lawn or canopy enters hard cover');
 }finally{THREE.TextureLoader.prototype.load=previousLoad;if(previousSelf===undefined)delete globalThis.self;else globalThis.self=previousSelf;}
});
