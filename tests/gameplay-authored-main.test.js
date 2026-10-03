import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Texture} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MAP_CONFIG} from '../src/map-config.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import {withinPlayBounds} from '../src/math.js';
import {makeApp} from './helpers/main-harness.js';

// Actual authored geometry/material flags and collision, actual composed main
// and game core. Embedded images use blank Texture objects solely to avoid
// browser image decoding; there is no GPU renderer or visual acceptance claim.
test('composed main wires authored map cover and fixed capsule world into play/restart/exploration',async()=>{
 const loader=new GLTFLoader();loader.register(()=>({name:'SUNWARD_CPU_TEXTURE_PLACEHOLDERS',loadTexture(){return Promise.resolve(new Texture());}}));
 const visualBytes=await decodeGlbBytes(await readFile(new URL('../public/assets/'+MAP_CONFIG.assets.map,import.meta.url)));
 const collisionBytes=await readFile(new URL('../public/assets/'+MAP_CONFIG.assets.collision,import.meta.url));
 const visual=await loader.parseAsync(visualBytes,''),collision=await new GLTFLoader().parseAsync(collisionBytes.buffer.slice(collisionBytes.byteOffset,collisionBytes.byteOffset+collisionBytes.byteLength),'');
 const app=await makeApp({visualScene:visual.scene,collisionScene:collision.scene});app.click('play-offline');app.click('start-match');
 assert.equal(app.window.sunwardDebug.matchPhase,'playing');assert.ok(app.world.coverStats.sourceTriangles>1000);assert.equal(app.match.world,app.world);
 app.key('KeyW');app.tick(30);app.key('KeyW','keyup');app.canvas.dispatch('pointerdown',{button:0});app.tick(8);app.window.dispatch('pointerup',{button:0});
 const player=app.match.getActor('player');assert.ok(player.weapon.ammo<30);assert.ok(player.position.every(Number.isFinite));assert.ok(withinPlayBounds(player.position[0],player.position[2]));
 assert.deepEqual(app.window.sunwardDebug.camera.position,player.eye,'View follows the core eye, not a second moving player');
 const world=app.world;app.click('pause-match');app.click('restart-match');assert.equal(app.world,world);assert.equal(app.worldBuilds,1);app.click('pause-match');app.click('leave-match');assert.equal(app.window.sunwardDebug.mode,'fly');
});
