import test from 'node:test';
import assert from 'node:assert/strict';
import {GameInput, INPUT_DEFAULTS, KEY_ACTIONS} from '../src/gameplay/input-controller.js';

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test('input normalizes diagonals and analog/key combinations without a speed bonus', () => {
  const input = new GameInput(); input.press('forward'); input.press('right');
  let command = input.consumeCommand(); near(Math.hypot(command.x, command.z), 1);
  input.setMove(0.5, 1); command = input.consumeCommand(); near(Math.hypot(command.x, command.z), 1);
  input.clear(); input.setMove(0.2, 0.3); command = input.consumeCommand(); near(command.x, 0.2); near(command.z, 0.3);
});

test('jump, slide and reload use one edge per physical press and survive a quick release before consumption', () => {
  const input = new GameInput();
  for (const action of ['jump', 'slide', 'reload']) { input.press(action); input.press(action); input.release(action); }
  let command = input.consumeCommand();
  for (const action of ['jump', 'slide', 'reload']) assert.equal(command[action], true);
  command = input.consumeCommand();
  for (const action of ['jump', 'slide', 'reload']) assert.equal(command[action], false);
  input.press('jump'); assert.equal(input.consumeCommand().jump, true); assert.equal(input.consumeCommand().jump, false);
});

test('independent binding sources do not clear the other Shift or Ctrl on release', () => {
  const input = new GameInput();
  input.press(KEY_ACTIONS.ShiftLeft, 'ShiftLeft'); input.press(KEY_ACTIONS.ShiftRight, 'ShiftRight');
  input.release(KEY_ACTIONS.ShiftLeft, 'ShiftLeft'); assert.equal(input.consumeCommand().sprint, true);
  input.release(KEY_ACTIONS.ShiftRight, 'ShiftRight'); assert.equal(input.consumeCommand().sprint, false);
});

test('X provides a crouch binding without browser Ctrl shortcuts and coexists with held Ctrl', () => {
  const input = new GameInput();
  assert.equal(KEY_ACTIONS.KeyX, 'crouch');
  input.press(KEY_ACTIONS.KeyX, 'KeyX'); input.press(KEY_ACTIONS.ControlLeft, 'ControlLeft');
  assert.equal(input.consumeCommand().crouch, true);
  input.release(KEY_ACTIONS.KeyX, 'KeyX'); assert.equal(input.consumeCommand().crouch, true);
  input.release(KEY_ACTIONS.ControlLeft, 'ControlLeft'); assert.equal(input.consumeCommand().crouch, false);
});

test('mouse look, ADS sensitivity and recoil use the same controllable angles', () => {
  const input = new GameInput();
  input.addLookDelta(10, 10); near(input.yaw, -10 * INPUT_DEFAULTS.sensitivity); near(input.pitch, -10 * INPUT_DEFAULTS.sensitivity);
  input.setLook(0, 0).addLookDelta(10, 10, 1); near(input.yaw, -10 * INPUT_DEFAULTS.sensitivity * INPUT_DEFAULTS.adsSensitivityScale);
  input.setLook(0, 0).applyLookOffset(0.01, 0.02);
  input.addLookDelta(0.01 / INPUT_DEFAULTS.sensitivity, 0.02 / INPUT_DEFAULTS.sensitivity);
  near(input.yaw, 0); near(input.pitch, 0);
  input.addLookDelta(0, -100000); near(input.pitch, INPUT_DEFAULTS.pitchLimit);
  input.setLook(0, 0); const inverted = new GameInput({invertY: true}); inverted.addLookDelta(0, 10); assert.ok(inverted.pitch > 0);
});

test('focus/menu/death disabling clears held and queued controls without changing the camera look', () => {
  const input = new GameInput({yaw: 0.4, pitch: 0.2});
  for (const action of ['forward', 'sprint', 'ads', 'fire', 'jump', 'slide', 'reload']) input.press(action);
  input.setMove(0.2, 0.2).setEnabled(false); input.press('fire'); input.addLookDelta(100, 100); input.setMove(1, 1);
  let command = input.consumeCommand();
  near(command.x, 0); near(command.z, 0); near(command.yaw, 0.4); near(command.pitch, 0.2);
  for (const action of ['sprint', 'ads', 'fire', 'jump', 'slide', 'reload']) assert.equal(command[action], false);
  input.setEnabled(true); command = input.consumeCommand();
  assert.equal(command.fire, false); assert.equal(command.jump, false); near(command.z, 0);
});

test('malformed axes/look are ignored; settings and action names are validated', () => {
  const input = new GameInput(); input.setMove(NaN, Infinity).setLook(NaN, Infinity).addLookDelta(Infinity, NaN);
  const command = input.consumeCommand(); near(command.x, 0); near(command.z, 0); near(command.yaw, 0); near(command.pitch, 0);
  assert.throws(() => input.press('unknown'), RangeError); assert.throws(() => input.release('unknown'), RangeError);
  assert.throws(() => new GameInput({sensitivity: 0}), RangeError); assert.throws(() => new GameInput({pitchLimit: Math.PI}), RangeError);
});
