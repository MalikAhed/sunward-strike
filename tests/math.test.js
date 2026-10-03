// Camera and movement math regressions against canonical map config.
import test from 'node:test';
import assert from 'node:assert/strict';
import {PerspectiveCamera} from 'three';
import {clamp,damp,normalizedInput,yawPitchDirection,rotationFromLook,VIEWPOINTS} from '../src/math.js';
import {MAP_CONFIG} from '../src/map-config.js';
test('diagonal input cannot increase movement speed',()=>{assert.ok(Math.abs(Math.hypot(...normalizedInput(1,1,1))-1)<1e-12);assert.deepEqual(normalizedInput(0,0,0),[0,0,0]);});
test('look orientation matches Three YXZ forward',()=>{assert.deepEqual(yawPitchDirection(0,0),[-0,0,-1]);const rotation=rotationFromLook([0,0,0],[1,1,0]),direction=yawPitchDirection(rotation.yaw,rotation.pitch);assert.ok(Math.abs(direction[0]-Math.SQRT1_2)<1e-12);assert.ok(Math.abs(direction[1]-Math.SQRT1_2)<1e-12);});
test('camera pitch clamp remains finite',()=>{assert.equal(clamp(2,-1.5,1.5),1.5);assert.ok(Number.isFinite(clamp(-2,-1.5,1.5)));});
test('damping is frame-rate independent',()=>{assert.ok(Math.abs(damp(damp(0,1,8,.1),1,8,.1)-damp(0,1,8,.2))<1e-12);});
test('UI viewpoints share canonical config and far camera matrices remain finite',()=>{
 assert.deepEqual(VIEWPOINTS,MAP_CONFIG.viewpoints);assert.deepEqual(Object.keys(VIEWPOINTS).sort(),['hero','street','mint','saffron','rooftop','topdown'].sort());const camera=new PerspectiveCamera(58,16/9,.05,500);
 for(const view of Object.values(VIEWPOINTS)){assert.ok([...view.position,...view.target].every(Number.isFinite));assert.ok(Math.hypot(...view.position)<500);camera.position.fromArray(view.position);camera.lookAt(...view.target);camera.updateMatrixWorld();camera.updateProjectionMatrix();assert.ok(camera.matrixWorld.elements.every(Number.isFinite));assert.ok(camera.projectionMatrix.elements.every(Number.isFinite));}
 for(const p of [[140,90,-140],[-140,90,140],[0,160,0]]){camera.position.fromArray(p);camera.lookAt(0,0,0);camera.updateMatrixWorld();assert.ok(camera.matrixWorld.elements.every(Number.isFinite));}
});
