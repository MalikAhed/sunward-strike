import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {buildOpaqueCover} from '../src/gameplay/cover.js';
import {makeBvhCoverRaycast} from '../src/gameplay/cover-query-bvh.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import {MAP_CONFIG} from '../src/map-config.js';

const regressions=JSON.parse(fs.readFileSync(new URL('./fixtures/cover-bvh-regressions.json',import.meta.url)));
const decode=value=>value==='Infinity'?Infinity:value==='NaN'?NaN:value;
function plane(side=THREE.FrontSide){const root=new THREE.Group(),mesh=new THREE.Mesh(new THREE.PlaneGeometry(4,4),new THREE.MeshStandardMaterial({side}));mesh.position.z=-5;root.add(mesh);return{root,mesh};}
function assertBuildStats(stats){
 assert.equal(stats.queryBackend,'triangle-bvh');assert.equal(stats.queryIndex.backend,'triangle-bvh');
 assert.equal(stats.queryIndex.triangleCount,stats.triangleCount);assert.equal(stats.retainedLegacyOctree,true);
 assert.equal(stats.legacyOctree.backend,'bounded-octree');assert.equal(stats.legacyOctree.maxLevel,5);
 assert.equal('maxLevel' in stats,false,'Legacy depth must not masquerade as active query depth');
 assert.equal('scope' in stats.queryIndex,false,'Do not expose stale prototype labeling');
 for(const value of Object.values(stats.buildTimingsMs))assert.ok(Number.isFinite(value)&&value>=0);
 assert.equal(stats.buildMs,stats.buildTimingsMs.total);
 const {prepareSourceMeshes,legacyOctreeAndTriangles,queryIndex,bookkeeping,total}=stats.buildTimingsMs;
 assert.ok(Math.abs(prepareSourceMeshes+legacyOctreeAndTriangles+queryIndex+bookkeeping-total)<1e-6);
 assert.ok(Object.isFrozen(stats)&&Object.isFrozen(stats.queryIndex)&&Object.isFrozen(stats.legacyOctree));
}
test('production cover construction installs the corrected BVH and distinguishes total/source/index costs',()=>{
 const{root,mesh}=plane(THREE.DoubleSide),positions=Array.from(mesh.geometry.attributes.position.array),cover=buildOpaqueCover(root);
 assert.equal(cover.raycast.indexStats.typedArrayBytes,cover.stats.queryIndex.typedArrayBytes,'Public raycast must be the constructed BVH function');
 assert.equal(cover.raycast([0,0,0],[0,0,-1],5),5);assert.equal(cover.raycast([0,0,-10],[0,0,1],5),5);
 assertBuildStats(cover.stats);assert.deepEqual(Array.from(mesh.geometry.attributes.position.array),positions);
});
test('all saved synthetic tiny-vector and one-ULP review regressions pass through the production constructor',()=>{
 const sides={front:THREE.FrontSide,back:THREE.BackSide,double:THREE.DoubleSide},covers=Object.fromEntries(Object.entries(sides).map(([name,side])=>[name,buildOpaqueCover(plane(side).root)]));
 const rows=regressions.cases.filter(row=>row.kind==='synthetic-plane');assert.equal(rows.length,44);
 for(const row of rows)assert.equal(covers[row.materialSide].raycast(row.origin,row.direction,decode(row.maxDistance)),decode(row.expectedDistance),row.id);
});
test('exceptional fallback is captured before the public query is replaced and does not recurse',()=>{
 const cover=buildOpaqueCover(plane().root),previous=cover.raycast.bind(cover);let calls=0;
 cover.raycast=(...args)=>{calls++;return previous(...args);};const query=makeBvhCoverRaycast(cover);cover.raycast=query;
 assert.equal(cover.raycast([-2,0,0],[0,0,-1e-200],5),5);assert.equal(calls,1);
 assert.equal(cover.raycast([0,0,0],[0,0,-1],5),5);assert.equal(calls,1);
});
test('all saved actual-map nearest-surface and exact-cutoff regressions pass through production cover',async()=>{
 const previousSelf=globalThis.self,previousLoad=THREE.TextureLoader.prototype.load;globalThis.self=globalThis;
 THREE.TextureLoader.prototype.load=function(_url,onLoad){const texture=new THREE.Texture();texture.image={width:1,height:1};if(onLoad)queueMicrotask(()=>onLoad(texture));return texture;};
 try{
  const bytes=await decodeGlbBytes(fs.readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`,import.meta.url))),gltf=await new GLTFLoader().parseAsync(bytes,''),cover=buildOpaqueCover(gltf.scene);
  const rows=regressions.cases.filter(row=>row.kind==='actual-map');assert.equal(rows.length,15);
  for(const row of rows)assert.equal(cover.raycast(row.origin,row.direction,decode(row.maxDistance)),decode(row.expectedDistance),row.id);
  assertBuildStats(cover.stats);assert.equal(cover.stats.queryIndex.maxDepth,14);assert.equal(cover.stats.queryIndex.triangleCount,99331);
  assert.equal(cover.stats.queryIndex.typedArrayBytes,2494604);
 }finally{THREE.TextureLoader.prototype.load=previousLoad;if(previousSelf===undefined)delete globalThis.self;else globalThis.self=previousSelf;}
});
