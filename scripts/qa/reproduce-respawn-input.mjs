// Portable actual-main/real-core reproduction. No browser, GPU or device claim.
// Run from any checkout: node scripts/qa/reproduce-respawn-input.mjs
// Optional first argument selects another checkout without modifying it.
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root = process.argv[2] ? pathToFileURL(resolve(process.argv[2]) + '/') : new URL('../../', import.meta.url);
const {makeApp} = await import(new URL('tests/helpers/main-harness.js', root));
const app = await makeApp(); app.click('play-offline'); app.click('start-match');
for (const actor of app.match.actors) if (actor.isBot) actor.brain.think = () => ({yaw: actor.yaw, pitch: actor.pitch});
const player = app.match.getActor('player');
app.canvas.dispatch('pointermove', {movementX: -1000, movementY: 200}); app.tick(2);
const before = {life: player.life, yaw: player.yaw, pitch: player.pitch};
app.canvas.dispatch('pointerdown', {button: 0}); app.canvas.dispatch('pointerdown', {button: 2});
for (const code of ['Space', 'KeyC', 'KeyR']) app.key(code);
app.tick(1, 1);
app.match.applyDamage('player', 100, {sourceId: 'enemy-1', ignoreProtection: true}); app.tick(); app.tick(130);
const after = {life: player.life, alive: player.alive, yaw: player.yaw, pitch: player.pitch,
  ammo: player.weapon.ammo, adsFraction: player.weapon.adsFraction, movementMode: player.motor.controller.movementMode,
  command: {...app.match.playerCommand}, camera: app.window.sunwardDebug.camera};
app.window.dispatch('keydown', {code: 'Space', repeat: true, target: app.canvas}); app.tick(8);
const repeatAfterRespawn = {movementMode: player.motor.controller.movementMode, feetY: player.position[1]};
const pass = repeatAfterRespawn.movementMode === 'idle' && after.life === before.life + 1 && after.alive && after.yaw === 0 && after.pitch === 0 &&
  after.camera.yaw === 0 && after.camera.pitch === 0 && after.ammo === player.weapon.spec.magazine &&
  after.adsFraction === 0 && after.movementMode === 'idle';
console.log(JSON.stringify({scope: 'Actual main + real core + real motor, DOM model/no-op renderer; no browser or device claim',
  mainSha256: createHash('sha256').update(await readFile(new URL('src/main.js', root))).digest('hex'),
  matchSha256: createHash('sha256').update(await readFile(new URL('src/gameplay/match.js', root))).digest('hex'),
  before, after, repeatAfterRespawn, pass}, null, 2));
process.exitCode = pass ? 0 : 1;
