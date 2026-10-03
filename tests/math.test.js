import test from 'node:test';
import assert from 'node:assert/strict';
import {clamp,damp,normalizedInput,yawPitchDirection,rotationFromLook,withinPlayBounds,VIEWPOINTS} from '../src/math.js';
test('diagonal input cannot increase movement speed',()=>{assert.ok(Math.abs(Math.hypot(...normalizedInput(1,1,1))-1)<1e-12);assert.deepEqual(normalizedInput(0,0,0),[0,0,0]);});
test('look orientation matches Three YXZ forward',()=>{assert.deepEqual(yawPitchDirection(0,0),[-0,0,-1]);const rotation=rotationFromLook([0,0,0],[1,1,0]);const direction=yawPitchDirection(rotation.yaw,rotation.pitch);assert.ok(Math.abs(direction[0]-Math.SQRT1_2)<1e-12);assert.ok(Math.abs(direction[1]-Math.SQRT1_2)<1e-12);});
test('camera pitch clamp and bounds remain finite',()=>{assert.equal(clamp(2,-1.5,1.5),1.5);assert.equal(withinPlayBounds(0,0),true);assert.equal(withinPlayBounds(29,0),false);});
test('damping is frame-rate independent',()=>{assert.ok(Math.abs(damp(damp(0,1,8,.1),1,8,.1)-damp(0,1,8,.2))<1e-12);});
test('named viewpoints are finite and outside neither extreme backdrop nor near-plane',()=>{assert.equal(Object.keys(VIEWPOINTS).length,6);for(const view of Object.values(VIEWPOINTS)){assert.ok([...view.position,...view.target].every(Number.isFinite));assert.ok(Math.hypot(...view.position)<100);}});
