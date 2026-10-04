import test from 'node:test';
import assert from 'node:assert/strict';
import {OfflineMatch} from '../src/gameplay/match.js';
import {GameInput, INPUT_DEFAULTS} from '../src/gameplay/input-controller.js';
import {GAMEPLAY_TUNING} from '../src/gameplay/tuning.js';
import {flatWorld, idle} from './helpers/gameplay-world.js';
import {makeApp} from './helpers/main-harness.js';

const STEP = GAMEPLAY_TUNING.fixedStep;
const ACTIONS = ['sprint', 'jump', 'slide', 'crouch', 'ads', 'fire', 'reload'];
const dirty = {x: 1, z: 1, yaw: 2.3, pitch: -0.46, ...Object.fromEntries(ACTIONS.map(action => [action, true]))};
const near = (actual, expected, message) => assert.ok(Math.abs(actual - expected) < 1e-9, message ?? `${actual} != ${expected}`);
function neutral(command, yaw = 0, pitch = 0) {
  assert.equal(command.x, 0); assert.equal(command.z, 0);
  near(command.yaw, yaw); near(command.pitch, pitch);
  for (const action of ACTIONS) assert.equal(command[action], false, `${action} must not cross the life boundary`);
}
function create() {
  const match = new OfflineMatch({world: flatWorld(), friendlyBots: 1, enemyBots: 1});
  match.start(); match.actors.forEach(idle); match.drainEvents();
  return match;
}
function killPlayer(match) {
  assert.equal(match.applyDamage('player', 100, {sourceId: 'enemy-1', ignoreProtection: true}), true);
}
function recordCommands(player) {
  const calls = [], update = player.motor.update.bind(player.motor);
  player.motor.update = (dt, command) => {calls.push({life: player.life, command: {...command}}); update(dt, command);};
  return calls;
}
async function startApp(options = {}) {
  const app = await makeApp(options);
  app.click('play-offline'); app.click('start-match'); app.match.actors.forEach(idle);
  return app;
}
function finishRespawn(app, hz = 60) {
  const player = app.match.getActor('player'), life = player.life;
  for (let frame = 0; frame < hz * 3 && player.life === life; frame++) app.tick(1, 1000 / hz);
  assert.equal(player.life, life + 1); assert.equal(player.alive, true);
  assert.equal(app.window.sunwardDebug.matchPhase, 'playing');
  near(player.yaw, 0); near(player.pitch, 0);
  near(app.window.sunwardDebug.camera.yaw, 0); near(app.window.sunwardDebug.camera.pitch, 0);
  neutral(app.match.playerCommand);
}

// The command buffer is authoritative inside a fixed tick. A queued command
// from the previous life must not overwrite spawn or act during any catch-up
// ticks, even if the presentation has not consumed the respawn event yet.
test('respawn replaces all previous-life commands before movement and weapon processing', () => {
  const match = create(), player = match.getActor('player'), calls = recordCommands(player);
  match.update(STEP, {yaw: dirty.yaw, pitch: dirty.pitch});
  near(player.yaw, dirty.yaw); near(player.pitch, dirty.pitch);
  match.update(STEP / 4, dirty); // Queued edges have not reached a fixed step.
  killPlayer(match);
  const shotsBefore = player.stats.shots;
  while (match.timeElapsed + STEP < player.respawnAt - 1e-9) match.update(STEP, dirty);
  const result = match.update(0.25, dirty); // Includes respawn and multiple ticks.
  assert.equal(player.life, 2); assert.equal(player.alive, true);
  near(player.yaw, 0); near(player.pitch, 0); neutral(match.playerCommand);
  const newLifeCalls = calls.filter(call => call.life === 2);
  assert.ok(newLifeCalls.length > 1, 'The neutral buffer must survive same-frame catch-up ticks');
  newLifeCalls.forEach(call => neutral(call.command));
  assert.equal(player.weapon.ammo, player.weapon.spec.magazine);
  assert.equal(player.weapon.adsFraction, 0); assert.equal(player.weapon.reloading, false);
  assert.equal(player.stats.shots, shotsBefore);
  assert.equal(result.events.filter(event => event.type === 'respawn' && event.actorId === 'player').length, 1);
  assert.ok(!result.events.some(event => ['shot', 'reload-started'].includes(event.type) && event.actorId === 'player'));
  assert.equal(result.snapshot.actors.find(actor => actor.id === 'player').protected, true);
});

test('direct human spawn invalidates pending old-life edges without clearing ordinary input every frame', () => {
  const match = create(), player = match.getActor('player'), calls = recordCommands(player);
  match.update(STEP / 4, dirty); assert.equal(calls.length, 0);
  match.spawn(player, match.timeElapsed); neutral(match.playerCommand);
  match.update(STEP / 4, {yaw: -0.7, pitch: 0.2, jump: true, slide: true, reload: true});
  match.update(STEP / 4, {yaw: -0.8, pitch: 0.3});
  assert.equal(calls.length, 0);
  match.update(STEP / 4, {yaw: -0.9, pitch: 0.4});
  assert.equal(calls.length, 1); near(calls[0].command.yaw, -0.9); near(calls[0].command.pitch, 0.4);
  for (const edge of ['jump', 'slide', 'reload']) assert.equal(calls[0].command[edge], true);
  match.update(STEP, {yaw: -1, pitch: 0.5});
  for (const edge of ['jump', 'slide', 'reload']) assert.equal(calls[1].command[edge], false);
  near(player.yaw, -1); near(player.pitch, 0.5);
});

test('bot respawns retain team-facing orientation without erasing the human command buffer', () => {
  const match = create(); match.setInput('player', dirty);
  const before = {...match.playerCommand};
  for (const id of ['ally-1', 'enemy-1']) {
    const actor = match.getActor(id); actor.yaw = -1.8; actor.pitch = 0.4;
    match.spawn(actor, match.timeElapsed);
    near(actor.yaw, actor.team === 0 ? 0 : Math.PI); near(actor.pitch, 0);
    assert.deepEqual(match.playerCommand, before);
  }
});

for (const hz of [30, 60, 120, 144, 240]) {
  test(`disabled input look resets across three deaths at ${hz} Hz; fresh look and short taps survive`, () => {
    const match = create(), player = match.getActor('player'), input = new GameInput();
    const calls = recordCommands(player);
    for (let cycle = 0; cycle < 3; cycle++) {
      input.setLook(2.3 - cycle * 0.5, -0.46 + cycle * 0.1);
      match.update(STEP, input.consumeCommand());
      const oldYaw = player.yaw, oldPitch = player.pitch;
      input.press('fire'); input.press('ads'); input.press('jump'); input.press('slide');
      match.update(0, input.consumeCommand()); killPlayer(match); input.setEnabled(false);
      const oldLife = player.life;
      for (let frame = 0; frame < hz * 3 && player.life === oldLife; frame++) {
        const command = input.consumeCommand();
        near(command.yaw, oldYaw); near(command.pitch, oldPitch);
        match.update(1 / hz, command);
      }
      assert.equal(player.life, oldLife + 1); near(player.yaw, 0); near(player.pitch, 0);
      calls.filter(call => call.life === player.life).forEach(call => neutral(call.command));
      neutral(match.playerCommand); assert.equal(player.weapon.ammo, player.weapon.spec.magazine);
      // The composed main adopts the authoritative snapshot on this event.
      input.setLook(player.yaw, player.pitch).setEnabled(true).addLookDelta(-50, 20);
      input.press('jump'); input.release('jump');
      const firstNewLifeCommand = calls.length;
      match.update(STEP / 4, input.consumeCommand());
      match.update(STEP, input.consumeCommand());
      near(player.yaw, 50 * INPUT_DEFAULTS.sensitivity); near(player.pitch, -20 * INPUT_DEFAULTS.sensitivity);
      assert.equal(calls[firstNewLifeCommand].command.jump, true, 'A fresh quick tap must survive until a fixed tick');
      assert.equal(match.playerCommand.jump, false);
    }
  });
}

// Executes actual main.js, GameInput, OfflineMatch and PlayerController against
// the existing DOM model and no-op renderer. This is not browser/device testing.
test('composed main resets camera and held mouse/keyboard controls through repeated death, pause and respawn', async () => {
  const app = await startApp(), player = app.match.getActor('player');
  for (let cycle = 0; cycle < 3; cycle++) {
    app.canvas.dispatch('pointermove', {movementX: -1000, movementY: 200}); app.tick(2);
    assert.ok(Math.abs(player.yaw) > 2); assert.ok(player.pitch < -0.4);
    app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2});
    for (const code of ['KeyW', 'ShiftLeft', 'Space', 'KeyC', 'KeyR']) app.key(code);
    app.tick(1, 1); // Short render frame: queued actions, no fixed tick.
    killPlayer(app.match); app.tick();
    assert.equal(app.window.sunwardDebug.matchPhase, 'dead');
    const frozenLook = {yaw: player.yaw, pitch: player.pitch};
    app.canvas.dispatch('pointermove', {movementX: 999, movementY: -400});
    app.canvas.dispatch('pointerdown', {button: 0}); app.key('Space'); app.tick();
    near(player.yaw, frozenLook.yaw); near(player.pitch, frozenLook.pitch);
    if (cycle === 1) {
      app.window.dispatch('blur'); const time = app.match.timeElapsed;
      app.tick(150); assert.equal(app.match.timeElapsed, time); app.click('resume-match');
      assert.equal(app.window.sunwardDebug.matchPhase, 'dead');
    }
    finishRespawn(app);
    const spawnPosition = [...player.position], shots = player.stats.shots;
    app.tick(20);
    assert.deepEqual(player.position, spawnPosition); assert.equal(player.stats.shots, shots);
    assert.equal(player.weapon.adsFraction, 0); assert.equal(player.weapon.ammo, player.weapon.spec.magazine);
    assert.equal(player.motor.controller.movementMode, 'idle');
    assert.equal(player.motor.controller.sliding, false); assert.equal(player.weapon.reloading, false);
    // Late releases from the dead life do not create a new action.
    app.window.dispatch('pointerup', {button: 0}); app.window.dispatch('pointerup', {button: 2});
    for (const code of ['KeyW', 'ShiftLeft', 'Space', 'KeyC', 'KeyR']) app.key(code, 'keyup');
    app.canvas.dispatch('pointermove', {movementX: -50, movementY: 20}); app.tick();
    near(player.yaw, 50 * INPUT_DEFAULTS.sensitivity); near(player.pitch, -20 * INPUT_DEFAULTS.sensitivity);
    near(app.window.sunwardDebug.camera.yaw, player.yaw); near(app.window.sunwardDebug.camera.pitch, player.pitch);
  }
  app.key('Space'); app.key('Space', 'keyup'); app.tick(8);
  assert.ok(player.position[1] > 0.4, 'Fresh post-spawn quick jump still works');
  app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2}); app.tick(8);
  assert.ok(player.weapon.ammo < player.weapon.spec.magazine); assert.ok(player.weapon.adsFraction > 0);
});

test('composed touch holders and dead-life taps clear before respawn; fresh post-spawn touch remains usable', async () => {
  const app = await startApp({coarse: true}), player = app.match.getActor('player');
  const root = app.document.getElementById('match-touch');
  const button = action => root.querySelector(`[data-action="${action}"]`);
  for (const [index, action] of ['forward', 'sprint', 'fire', 'ads', 'jump', 'slide', 'reload'].entries()) {
    button(action).dispatch('pointerdown', {pointerId: index + 2});
  }
  killPlayer(app.match); app.tick();
  for (const element of root.querySelectorAll('[data-action]')) assert.equal(element.classList.contains('held'), false);
  button('jump').dispatch('pointerdown', {pointerId: 77}); button('fire').dispatch('pointerdown', {pointerId: 78});
  finishRespawn(app, 144); app.tick(20);
  neutral(app.match.playerCommand); assert.equal(player.weapon.ammo, player.weapon.spec.magazine);
  assert.equal(player.weapon.adsFraction, 0); assert.equal(player.motor.controller.movementMode, 'idle');
  button('fire').dispatch('pointerdown', {pointerId: 90}); button('ads').dispatch('pointerdown', {pointerId: 91}); app.tick(8);
  assert.ok(player.weapon.ammo < player.weapon.spec.magazine); assert.ok(player.weapon.adsFraction > 0);
  button('fire').dispatch('pointercancel', {pointerId: 90}); button('ads').dispatch('pointercancel', {pointerId: 91});
});

test('OS-repeat from dead-life holds cannot re-arm controls after any respawn; release and fresh press work', async () => {
  const app = await startApp(), player = app.match.getActor('player');
  const codes = ['KeyW', 'KeyD', 'ShiftLeft', 'Space', 'KeyC', 'KeyX', 'KeyR'];
  const repeat = () => codes.forEach(code => app.window.dispatch('keydown', {code, repeat: true, target: app.canvas}));
  for (let cycle = 0; cycle < 3; cycle++) {
    app.canvas.dispatch('pointermove', {movementX: -1000, movementY: 200}); app.tick(2);
    codes.forEach(code => app.key(code));
    app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2});
    killPlayer(app.match); app.tick(); repeat();
    finishRespawn(app);
    const position = [...player.position], shots = player.stats.shots;
    for (let frame = 0; frame < 60; frame++) {repeat(); app.tick();}
    neutral(app.match.playerCommand); assert.deepEqual(player.position, position);
    assert.equal(player.stats.shots, shots); assert.equal(player.weapon.adsFraction, 0);
    assert.equal(player.motor.controller.movementMode, 'idle');
    near(app.window.sunwardDebug.camera.yaw, 0); near(app.window.sunwardDebug.camera.pitch, 0);
    codes.forEach(code => app.key(code, 'keyup'));
    app.window.dispatch('pointerup', {button: 0}); app.window.dispatch('pointerup', {button: 2});
    // A real release/new press and even a sub-frame jump tap remain responsive.
    app.canvas.dispatch('pointermove', {movementX: -80, movementY: -30});
    app.key('Space'); app.key('Space', 'keyup'); app.tick(8);
    near(player.yaw, 80 * INPUT_DEFAULTS.sensitivity); near(player.pitch, 30 * INPUT_DEFAULTS.sensitivity);
    assert.ok(player.position[1] > position[1] + 0.4);
    app.tick(60);
  }
  app.key('KeyW'); app.key('ShiftLeft'); app.tick(20);
  assert.equal(player.sprinting, true);
  app.key('KeyC'); app.key('KeyC', 'keyup'); app.tick(2);
  assert.equal(player.sliding, true, 'A fresh post-respawn slide still enters after building sprint speed');
});

test('pause/resume clears cannot be undone by OS-repeat, while fresh held input and preserved look still work', async () => {
  const app = await startApp(), player = app.match.getActor('player');
  const codes = ['KeyW', 'ShiftLeft', 'Space', 'KeyC', 'KeyX', 'KeyR'];
  app.canvas.dispatch('pointermove', {movementX: -200, movementY: 90}); app.tick(2);
  const look = {yaw: player.yaw, pitch: player.pitch};
  for (let cycle = 0; cycle < 3; cycle++) {
    codes.forEach(code => app.key(code));
    app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2});
    app.click('pause-match'); const time = app.match.timeElapsed;
    app.tick(20); assert.equal(app.match.timeElapsed, time); app.click('resume-match');
    const position = [...player.position], shots = player.stats.shots;
    for (let frame = 0; frame < 30; frame++) {
      codes.forEach(code => app.window.dispatch('keydown', {code, repeat: true, target: app.canvas})); app.tick();
    }
    neutral(app.match.playerCommand, look.yaw, look.pitch);
    assert.deepEqual(player.position, position); assert.equal(player.stats.shots, shots);
    assert.equal(player.weapon.adsFraction, 0); assert.equal(player.motor.controller.movementMode, 'idle');
    codes.forEach(code => app.key(code, 'keyup'));
    app.window.dispatch('pointerup', {button: 0}); app.window.dispatch('pointerup', {button: 2});
  }
  app.key('KeyW'); app.tick(8); assert.equal(app.match.playerCommand.z, 1);
  app.window.dispatch('keydown', {code: 'KeyW', repeat: true, target: app.canvas}); app.tick();
  assert.equal(app.match.playerCommand.z, 1, 'Ignoring repeats does not release a genuine active hold');
  app.key('KeyW', 'keyup'); app.tick(); assert.equal(app.match.playerCommand.z, 0);
  app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2}); app.tick(8);
  assert.ok(player.weapon.ammo < player.weapon.spec.magazine); assert.ok(player.weapon.adsFraction > 0);
});

test('composed respawn stops already-active fire/ADS, airborne jump and sprint slide without inherited state', async () => {
  const app = await startApp(), player = app.match.getActor('player'); app.tick(2);
  for (const active of ['fire-and-ads', 'jump', 'slide']) {
    if (active === 'fire-and-ads') {
      app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2}); app.tick(15);
      assert.ok(player.weapon.ammo < player.weapon.spec.magazine); assert.equal(player.weapon.adsFraction, 1);
    } else if (active === 'jump') {
      app.key('Space'); app.tick(8); assert.ok(player.position[1] > 0.4);
    } else {
      app.key('KeyW'); app.key('ShiftLeft'); app.tick(20); app.key('KeyC'); app.tick(2);
      assert.equal(player.sliding, true);
    }
    killPlayer(app.match); app.tick(); finishRespawn(app); app.tick(15);
    neutral(app.match.playerCommand); assert.equal(player.weapon.ammo, player.weapon.spec.magazine);
    assert.equal(player.weapon.adsFraction, 0); assert.equal(player.weapon.reloading, false);
    assert.equal(player.motor.controller.movementMode, 'idle'); near(player.position[1], 0);
    assert.equal(player.motor.controller._jumpQueuedUntil, -Infinity);
    assert.equal(player.motor.controller._slideQueued, false);
    app.window.dispatch('pointerup', {button: 0}); app.window.dispatch('pointerup', {button: 2});
    for (const code of ['Space', 'KeyW', 'ShiftLeft', 'KeyC']) app.key(code, 'keyup');
  }
});
