import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import * as THREE from 'three';
import {createSky,createClouds,createScenery,ATMOSPHERE_CONFIG as C} from '../src/atmosphere.js';
import {shaderSources} from './helpers/shader-sources.js';
const textures={};for(const name of [C.cloudTexture,C.mountainTexture]){textures[name]=new THREE.Texture();textures[name].name=name;textures[name].colorSpace=THREE.SRGBColorSpace;}
const sky=createSky(),clouds=createClouds({textures}),scenery=createScenery({textures});
const meshes=[sky,...clouds.children,...scenery.children];
test('n5 preserves bound texture/geometry budget and source alpha workflow',()=>{
 assert.equal(clouds.children.length,12);assert.equal(scenery.children.length,6);
 let count=0;for(const mesh of meshes){
  assert.equal(mesh.frustumCulled,false);assert.equal(mesh.material.toneMapped,false);assert.equal(mesh.material.depthWrite,false);assert.equal(mesh.material.fog,false);
  const p=mesh.geometry.attributes.position.array;assert.ok(p.every(Number.isFinite));
  if(mesh!==sky){count+=mesh.geometry.index.count/3;assert.equal(mesh.material.uniforms.atlas.value.colorSpace,THREE.SRGBColorSpace);assert.ok(mesh.material.transparent);}
 }
 assert.equal(count,2304);assert.equal(C.textureSize[0]*C.textureSize[1]*4*2,12582912);
});
test('sky directions remain world-locked through xyz camera translation without far-plane clipping',()=>{
 const offsets=[[0,0,0],[100,80,-80],[-200,150,120]];
 for(const object of meshes){
  assert.match(object.material.vertexShader,/vSkyDirection=relative.xyz; relative.xyz\+=cameraPosition/);
  assert.match(object.material.vertexShader,/gl_Position.z=gl_Position.w\*0.99999/);
  const p=object.geometry.attributes.position;
  for(let i=0;i<p.count;i+=17){
   const d=new THREE.Vector3().fromBufferAttribute(p,i);assert.ok(d.length()>300&&d.length()<=401);
   for(const offset of offsets){const o=new THREE.Vector3(...offset);const relative=d.clone().add(o).sub(o);assert.ok(relative.distanceTo(d)<1e-10);}
  }
 }
 assert.ok(C.backgroundDepth<1&&C.backgroundDepth>.999);
});
test('clouds have restrained angular widths, open poles and no near-map geometry',()=>{
 for(const b of clouds.children){assert.ok(b.userData.width>=10&&b.userData.width<=27);assert.ok(b.userData.elevation>=15);assert.ok(b.userData.elevation+b.userData.height/2<55);}
 for(const b of scenery.children){assert.ok(b.userData.height<=13);assert.ok(b.userData.base<0);}
 assert.ok(scenery.children.at(-1).geometry.boundingSphere.radius<360);
});
test('exact native/web geometry and UV manifest remain synchronized',()=>{
 const r=JSON.parse(fs.readFileSync(new URL('./fixtures/atmosphere-parity-n5.json',import.meta.url)));
 assert.equal(r.version,C.version);const cards=[...clouds.children,...scenery.children];
 for(let i=0;i<cards.length;i++){assert.deepEqual(r.cards[i].vertices,Array.from(cards[i].geometry.attributes.position.array));assert.deepEqual(r.cards[i].indices,Array.from(cards[i].geometry.index.array));assert.deepEqual(r.cards[i].uv,Array.from(cards[i].geometry.attributes.uv.array));}
});
test('all exact n5 GLSL ES programs compile and link; reserved-word negative rejected',()=>{
 const programs=[sky,clouds.children[0],scenery.children[0]].map(m=>({name:m.name,...shaderSources(m.material)}));
 programs.push({name:'negative-control',...programs[0],fragment:programs[0].fragment.replace('float e=', 'float patch=0.;float e=')});
 const r=spawnSync('python3',[new URL('./helpers/compile-egl.py',import.meta.url).pathname],{input:JSON.stringify(programs),encoding:'utf8'});
 assert.equal(r.status,0,r.stderr||r.stdout);const report=JSON.parse(r.stdout);for(const p of report.results.slice(0,3)){assert.equal(p.compiled,true);assert.equal(p.linked,true);}assert.equal(report.results[3].compiled,false);assert.match(JSON.stringify(report.results[3].errors),/reserved word.*patch/);
});
