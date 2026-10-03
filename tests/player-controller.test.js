import test from 'node:test';
import assert from 'node:assert/strict';
import {Vector3, Group, Mesh, PlaneGeometry, BoxGeometry, BufferGeometry, Float32BufferAttribute, MeshBasicMaterial} from 'three';
import {buildCollisionOctree} from '../src/collision.js';
import {PlayerController, MOVEMENT_CONFIG as C} from '../src/gameplay/player-controller.js';

const material = new MeshBasicMaterial();
const near = (actual, expected, tolerance = 1e-7) => assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} != ${expected} ± ${tolerance}`);
function plane(root, width = 200, depth = 200, x = 0, y = 0, z = 0) {
  const mesh = new Mesh(new PlaneGeometry(width, depth), material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(x, y, z);
  root.add(mesh);
}
function box(root, width, height, depth, x, y, z) {
  const mesh = new Mesh(new BoxGeometry(width, height, depth), material);
  mesh.position.set(x, y, z);
  root.add(mesh);
}
function flatTree() { const root = new Group(); plane(root); return buildCollisionOctree(root); }
function spawn(tree = flatTree(), x = 0, y = 0, z = 0) {
  const motor = new PlayerController(tree);
  motor.spawn(new Vector3(x, y + 1.64, z));
  run(motor, 0.2, {});
  assert.equal(motor.onFloor, true);
  return motor;
}
function run(motor, seconds, command, dt = 1 / 60) {
  for (let i = 0; i < Math.round(seconds / dt); i++) motor.update(dt, typeof command === 'function' ? command(i) : command);
  return motor;
}
function rampTree(yaw = 0, lip = 0.18, lowerFloor = 0.18) {
  const root = new Group();
  plane(root, 12, 8, -6, lowerFloor); plane(root, 12, 8, 12, 3.18);
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new Float32BufferAttribute([0,lip,-2, 0,lip,2, 6,3.18,2, 6,3.18,-2], 3));
  geometry.setIndex([0,1,2, 0,2,3]);
  root.add(new Mesh(geometry, material)); root.rotation.y = yaw;
  return buildCollisionOctree(root);
}
const orient = (x, y, yaw) => new Vector3(Math.cos(yaw) * x, y, -Math.sin(yaw) * x);

test('standing capsule and camera preserve the accepted route dimensions', () => {
  const p = spawn();
  near(p.collider.radius, 0.35); near(p.bodyHeight, 1.8);
  near(p.collider.start.distanceTo(p.collider.end) + 2 * p.collider.radius, 1.8);
  near(p.cameraPosition().y - p.feetPosition().y, 1.64);
  assert.equal(p.movementMode, 'idle');
});

test('walk, diagonal input and forward-only sprint have bounded independent speeds', () => {
  const p = spawn();
  run(p, 0.3, {z: 1}); near(p.horizontalSpeed, C.walkSpeed);
  run(p, 0.3, {x: 1, z: 1}); near(p.horizontalSpeed, C.walkSpeed);
  run(p, 0.3, {z: 1, sprint: true}); near(p.horizontalSpeed, C.sprintSpeed); assert.equal(p.sprinting, true);
  run(p, 0.3, {z: -1, sprint: true}); near(p.horizontalSpeed, C.walkSpeed); assert.equal(p.sprinting, false);
  run(p, 0.3, {x: 1, sprint: true}); near(p.horizontalSpeed, C.walkSpeed); assert.equal(p.sprinting, false);
});

test('ADS and held fire interrupt sprint; full ADS and release recover predictably', () => {
  const p = spawn();
  run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, ads: true});
  assert.equal(p.sprinting, false); assert.equal(p.canFire, false);
  assert.ok(p.adsFraction > 0 && p.adsFraction < 0.1);
  run(p, 0.2, {z: 1, sprint: true, ads: true});
  near(p.adsFraction, 1); near(p.horizontalSpeed, C.walkSpeed * C.adsMoveScale); assert.equal(p.canFire, true);
  run(p, 0.3, {z: 1, sprint: true}); assert.equal(p.sprinting, true); near(p.adsFraction, 0);
  run(p, 0.2, {z: 1, sprint: true, fire: true}); assert.equal(p.sprinting, false); assert.equal(p.canFire, true);
  run(p, 0.3, {z: 1, sprint: true, reloading: true}); assert.equal(p.sprinting, false);
});

test('a slide requires grounded sprint speed; entry is bounded, lowers the real capsule and recovers', () => {
  const p = spawn();
  p.update(1 / 60, {slide: true}); assert.equal(p.sliding, false);
  run(p, 0.35, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  assert.equal(p.sliding, true); assert.equal(p.sprinting, false); near(p.bodyHeight, C.slideHeight);
  near(p.collider.start.distanceTo(p.collider.end) + 2 * p.collider.radius, C.slideHeight);
  near(p.horizontalSpeed, C.slideStartSpeed); near(p.cameraPosition().y - p.feetPosition().y, C.slideHeight - C.eyeFromTop);
  const start = p.feetPosition();
  run(p, C.slideDuration, {z: 1, sprint: true, slide: true}, 1 / 120);
  assert.equal(p.sliding, false); assert.equal(p.lastSlideEnd, 'duration');
  assert.ok(p.feetPosition().distanceTo(start) < 5.0);
  assert.ok(p.snapshot().slideRecoveryRemaining > 0.4);
  p.update(1 / 120, {z: 1, sprint: true, slide: false});
  p.update(1 / 120, {z: 1, sprint: true, slide: true}); assert.equal(p.sliding, false);
  run(p, 0.5, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true}); assert.equal(p.sliding, true);
});

test('slide direction follows momentum and has bounded steering when the view turns', () => {
  const p = spawn(); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  const before = Math.atan2(p.velocity.x, p.velocity.z);
  p.update(1 / 120, {z: 1, yaw: Math.PI / 2});
  const after = Math.atan2(p.velocity.x, p.velocity.z);
  const difference = Math.abs(Math.atan2(Math.sin(after - before), Math.cos(after - before)));
  assert.ok(difference <= C.slideSteerRate / 120 + 1e-8);
  assert.ok(p.velocity.z < -9); assert.ok(Math.abs(p.velocity.x) < 0.1);
});

test('slide jump cancel obeys commitment and does not retain the slide speed boost', () => {
  const p = spawn(); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  run(p, 0.15, {z: 1, sprint: true}, 1 / 120);
  p.update(1 / 120, {z: 1, sprint: true, jump: true});
  assert.equal(p.sliding, false); assert.equal(p.onFloor, false); assert.equal(p.lastSlideEnd, 'jump');
  assert.ok(p.velocity.y > 5); assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9);
  assert.ok(p.snapshot().slideRecoveryRemaining > 0.4);
  run(p, 0.3, {x: 1, z: 1, sprint: true}); assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9);
});

test('an early jump is buffered through slide commitment, without an early cancel', () => {
  const p = spawn(); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  p.update(1 / 120, {z: 1, jump: true});
  assert.equal(p.sliding, true); assert.equal(p.onFloor, true);
  for (let i = 0; i < 10; i++) p.update(1 / 120, {z: 1});
  assert.equal(p.sliding, true);
  for (let i = 0; i < 5; i++) p.update(1 / 120, {z: 1});
  assert.equal(p.sliding, false); assert.equal(p.lastSlideEnd, 'jump'); assert.equal(p.onFloor, false);
  assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9);
});

test('crouch cancels after slide commitment; simultaneous jump/slide gives jump priority', () => {
  const p = spawn(); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  run(p, 0.2, {z: 1, crouch: true}, 1 / 120);
  assert.equal(p.sliding, false); assert.equal(p.lastSlideEnd, 'cancel'); near(p.bodyHeight, C.crouchHeight);
  const q = spawn(); run(q, 0.3, {z: 1, sprint: true});
  q.update(1 / 120, {z: 1, sprint: true, slide: true, jump: true});
  assert.equal(q.sliding, false); assert.equal(q.onFloor, false); assert.ok(q.horizontalSpeed <= C.sprintSpeed);
});

test('sub-tick jump input is latched until simulation consumes it', () => {
  const p = spawn();
  p.update(1 / 240, {jump: true}); assert.equal(p.onFloor, true);
  p.update(1 / 240, {jump: false}); assert.equal(p.onFloor, false); assert.ok(p.velocity.y > 5);
});

test('a held jump fires once, lands normally and cannot become an air speed exploit', () => {
  const p = spawn(); let peak = 0, takeoffs = 0, grounded = p.onFloor;
  for (let i = 0; i < 240; i++) {
    p.update(1 / 120, {jump: true, z: 1, sprint: true});
    if (grounded && !p.onFloor) takeoffs++;
    grounded = p.onFloor; peak = Math.max(peak, p.feetPosition().y);
    assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-8);
  }
  assert.equal(takeoffs, 1); assert.equal(p.onFloor, true); assert.ok(peak > 0.7 && peak < 0.85);
  p.update(1 / 120, {jump: false}); p.update(1 / 120, {jump: true});
  assert.equal(p.onFloor, false);
});

test('a slide cannot tunnel through a thin wall or instantly restart against it', () => {
  const root = new Group(); plane(root); box(root, 10, 4, 0.03, 0, 2, -4);
  const p = spawn(buildCollisionOctree(root)); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 60, {z: 1, sprint: true, slide: true});
  for (let i = 0; i < 30; i++) {
    p.update(1 / 30, {z: 1, sprint: true, slide: true});
    assert.ok(p.feetPosition().z > -3.641); assert.ok(p.onFloor);
  }
  assert.equal(p.sliding, false); assert.equal(p.lastSlideEnd, 'blocked');
  for (let i = 0; i < 30; i++) {
    p.update(1 / 30, {z: 1, sprint: true, slide: i % 2 === 0});
    assert.equal(p.sliding, false); assert.ok(p.feetPosition().z > -3.641);
  }
});

test('standing expansion checks capsule volume under a ceiling and restores when clear', () => {
  const root = new Group(); plane(root); box(root, 4, 0.3, 4, 0, 1.4, 0);
  const p = spawn(buildCollisionOctree(root), 0, 0, 4);
  run(p, 0.8, {z: 1, crouch: true});
  assert.equal(p.crouched, true); assert.equal(p.canStand(), false);
  const feet = p.feetPosition();
  p.update(1 / 60, {}); assert.equal(p.crouched, true); near(p.bodyHeight, C.crouchHeight);
  near(p.feetPosition().y, feet.y); assert.ok(p.collider.end.y + p.collider.radius < 1.251);
  run(p, 1.1, {z: -1});
  run(p, 0.2, {}); assert.equal(p.canStand(), true); assert.equal(p.crouched, false); near(p.bodyHeight, C.standHeight);
});

test('a 1.1 m route remains navigable at standing, crouching and slide height', () => {
  const root = new Group(); plane(root);
  box(root, 0.1, 4, 50, -0.6, 2, 0); box(root, 0.1, 4, 50, 0.6, 2, 0);
  const p = spawn(buildCollisionOctree(root), 0, 0, 10);
  run(p, 0.5, {z: 1, sprint: true});
  p.update(1 / 60, {z: 1, sprint: true, slide: true});
  run(p, 0.75, {z: 1}); run(p, 1, {z: 1, crouch: true});
  assert.ok(p.feetPosition().z < 0); assert.ok(Math.abs(p.feetPosition().x) < 0.001); assert.equal(p.onFloor, true);
});

for (const yaw of [0, Math.PI / 2]) for (const lip of [0.1807, 0.3467]) {
  test(`ramp lip ${lip} at yaw ${yaw} preserves grounded ascent and explicit jump impulse`, () => {
    const feet = orient(-0.55, 0.014, yaw);
    const p = spawn(rampTree(yaw, lip, 0.014), feet.x, feet.y, feet.z);
    let samples = 0;
    for (let i = 0; i < 140; i++) {
      p.update(1 / 60, {z: 1, yaw: yaw - Math.PI / 2, sprint: true});
      const localX = p.feetPosition().x * Math.cos(yaw) - p.feetPosition().z * Math.sin(yaw);
      if (localX > 0.6 && localX < 5.4) { assert.equal(p.onFloor, true); samples++; }
      if (localX > 4.2) break;
    }
    assert.ok(samples > 0);
    p.update(1 / 120, {jump: true, z: -1, yaw: yaw - Math.PI / 2});
    assert.ok(p.velocity.y > 5.2 && p.velocity.y <= C.jumpSpeed); assert.equal(p.onFloor, false);
  });
}

test('ramp descent keeps contact, while a one-metre ledge really falls', () => {
  const p = spawn(rampTree(), 7, 3.18, 0);
  let supportedSamples = 0;
  for (let i = 0; i < 90; i++) {
    p.update(1 / 60, {z: 1, yaw: Math.PI / 2, sprint: true});
    if (p.feetPosition().x > 0.6 && p.feetPosition().x < 5.4) { assert.equal(p.onFloor, true); supportedSamples++; }
  }
  assert.ok(supportedSamples > 0);
  const root = new Group(); plane(root, 10, 8, 5, 1); plane(root, 12, 8, -6, 0);
  const q = spawn(buildCollisionOctree(root), 1.5, 1, 0);
  let airborne = 0, maximumDrop = 0, previous = 1;
  for (let i = 0; i < 150; i++) {
    q.update(1 / 60, {x: -1}); const y = q.feetPosition().y;
    maximumDrop = Math.max(maximumDrop, previous - y); previous = y;
    if (!q.onFloor) airborne++;
  }
  assert.ok(airborne > 5); assert.ok(maximumDrop < 0.22); assert.equal(q.onFloor, true); near(q.feetPosition().y, 0, 0.025);
});

test('a steep landing cannot convert vertical fall speed into an unbounded horizontal boost', () => {
  const p = new PlayerController(rampTree());
  p.spawn(new Vector3(3, 12, 0));
  let landed = false;
  for (let i = 0; i < 360; i++) {
    p.update(1 / 120, {z: 1, yaw: Math.PI / 2, sprint: true});
    assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9);
    if (p.onFloor) landed = true;
  }
  assert.ok(landed);
});

test('sliding off a ledge ends the slide and clamps air speed', () => {
  const root = new Group(); plane(root, 10, 10, 0, 1, 5); plane(root, 30, 30, 0, 0, -15);
  const p = spawn(buildCollisionOctree(root), 0, 1, 2.2);
  run(p, 0.2, {z: 1, sprint: true});
  p.update(1 / 120, {z: 1, sprint: true, slide: true});
  let fell = false;
  for (let i = 0; i < 80; i++) {
    p.update(1 / 120, {z: 1, sprint: true});
    if (!p.onFloor) { fell = true; assert.equal(p.sliding, false); assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9); }
  }
  assert.ok(fell); assert.equal(p.lastSlideEnd, 'airborne');
});

for (const hz of [30, 60, 120]) test(`a 0.166 m exterior floor drop safely ends a slide through a doorway at ${hz} Hz`, () => {
  const root = new Group();
  plane(root, 8, 8, 0, .18, 4); plane(root, 8, 12, 0, .014, -6);
  box(root, .2, 2.6, .2, -.7, 1.3, 0); box(root, .2, 2.6, .2, .7, 1.3, 0);
  box(root, 1.2, .3, .2, 0, 2.35, 0);
  const p = spawn(buildCollisionOctree(root), 0, .18, 1.15);
  let entered = false, dropped = false, previousY = .18, largestRise = 0;
  for (let frame = 0; frame < hz; frame++) {
    const slide = !entered && p.sprinting && p.horizontalSpeed >= C.slideEntrySpeed;
    p.update(1 / hz, {z: 1, sprint: true, slide});
    if (p.sliding) entered = true;
    if (entered && !p.sliding) dropped = true;
    const feet = p.feetPosition();
    largestRise = Math.max(largestRise, feet.y - previousY); previousY = feet.y;
    assert.ok(feet.y >= -.011 && feet.y <= .181);
    if (dropped) assert.ok(p.horizontalSpeed <= C.sprintSpeed + 1e-9);
  }
  assert.ok(entered && dropped); assert.equal(p.lastSlideEnd, 'airborne');
  assert.ok(p.feetPosition().z < -1.15, 'must traverse beyond the whole doorway');
  assert.ok(largestRise < .003, 'support loss must not create a launch');
  assert.equal(p.onFloor, true); near(p.feetPosition().y, .014, .002);
});

test('30/60/120 Hz render deltas produce the same replay, including stance and jump transitions', () => {
  const replay = dt => {
    const p = spawn();
    run(p, 0.5, {z: 1, sprint: true}, dt);
    p.update(dt, {z: 1, sprint: true, slide: true});
    run(p, 0.5 - dt, {z: 1, sprint: true}, dt);
    p.update(dt, {z: 1, jump: true});
    run(p, 0.5 - dt, {z: 1, ads: true}, dt);
    run(p, 0.5, {x: 1, crouch: true}, dt);
    run(p, 0.5, {}, dt);
    return p.snapshot();
  };
  const a = replay(1 / 30), b = replay(1 / 60), c = replay(1 / 120);
  for (const item of [a, b]) {
    for (let i = 0; i < 3; i++) near(item.feet[i], c.feet[i], 1e-7);
    near(item.adsFraction, c.adsFraction); assert.equal(item.movementMode, c.movementMode);
  }
});

test('death freezes movement and respawn clears slide/jump/ADS/cooldowns without inherited impulse', () => {
  const p = spawn(); run(p, 0.3, {z: 1, sprint: true});
  p.update(1 / 60, {z: 1, sprint: true, slide: true});
  const start = p.feetPosition();
  p.setAlive(false); run(p, 2, {z: 1, jump: true, slide: true, ads: true});
  near(p.feetPosition().distanceTo(start), 0); assert.equal(p.movementMode, 'dead'); assert.equal(p.canFire, false);
  p.spawn(new Vector3(5, 1.64, 5), {yaw: 1}); run(p, 0.2, {});
  assert.equal(p.alive, true); assert.equal(p.onFloor, true); assert.equal(p.sliding, false); assert.equal(p.crouched, false);
  near(p.horizontalSpeed, 0); near(p.adsFraction, 0); near(p.bodyHeight, C.standHeight); near(p.yaw, 1);
  assert.equal(p.canFire, true); near(p.feetPosition().x, 5); near(p.feetPosition().z, 5);
});

test('large wall-time gaps are bounded and invalid dt/config/commands cannot poison the actor', () => {
  const p = spawn(); p.update(60, {z: 1, sprint: true});
  assert.ok(p.feetPosition().length() < 1); near(p.droppedTime, 59.9);
  p.update(1 / 60, {x: Infinity, z: NaN, yaw: Infinity});
  assert.ok(p.collider.start.toArray().every(Number.isFinite));
  for (const dt of [-1, Infinity, NaN]) assert.throws(() => p.update(dt), RangeError);
  assert.throws(() => new PlayerController(null, {radius: 0.2}), RangeError);
  assert.throws(() => new PlayerController(null, {fixedStep: 1}), RangeError);
});
