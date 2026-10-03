import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {Vector3, Triangle} from 'three';
import {Capsule} from 'three/addons/math/Capsule.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {CapsuleContacts} from '../src/gameplay/capsule-contacts.js';
import {PlayerController} from '../src/gameplay/player-controller.js';
import {buildCollisionOctree} from '../src/collision.js';

const v = a => new Vector3().fromArray(a);
const near = (a, b, tolerance = 1e-9) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);

test('finite-triangle closest contacts retain exact floor, wall and ceiling penetration', () => {
  const contacts = new CapsuleContacts();
  const cases = [
    {triangle: [[-10,0,-10],[-10,0,10],[10,0,10]], start: [0,.32,0], end: [0,1.42,0], normal: [0,1,0]},
    {triangle: [[-10,1.77,-10],[10,1.77,10],[-10,1.77,10]], start: [0,.35,0], end: [0,1.45,0], normal: [0,-1,0]},
    {triangle: [[0,-10,-10],[0,10,-10],[0,10,10]], start: [.32,.35,0], end: [.32,1.45,0], normal: [1,0,0]},
  ];
  for (const data of cases) {
    const hit = contacts.triangleContact(new Capsule(v(data.start), v(data.end), .35), new Triangle(...data.triangle.map(v)));
    assert.ok(hit); near(hit.depth, .03);
    for (let axis = 0; axis < 3; axis++) near(hit.normal.getComponent(axis), data.normal[axis]);
  }
});

test('parallel finite triangle edge and zero-length capsule axis use stable closest points', () => {
  const contacts = new CapsuleContacts();
  const wall = new Triangle(v([0,0,0]), v([0,2,0]), v([0,0,2]));
  const edgeHit = contacts.triangleContact(new Capsule(v([.34,.35,0]), v([.34,1.45,0]), .35), wall);
  assert.ok(edgeHit); near(edgeHit.depth, .01); near(edgeHit.normal.x, 1);
  const sphereHit = contacts.triangleContact(new Capsule(v([.32,.5,.5]), v([.32,.5,.5]), .35), wall);
  assert.ok(sphereHit); near(sphereHit.depth, .03); near(sphereHit.normal.x, 1);
});

test('distant and wholly back-facing capsule axes do not create contacts', () => {
  const contacts = new CapsuleContacts();
  const wall = new Triangle(v([0,0,0]), v([0,2,0]), v([0,0,2]));
  assert.equal(contacts.triangleContact(new Capsule(v([1,.35,.5]), v([1,1.45,.5]), .35), wall), false);
  assert.equal(contacts.triangleContact(new Capsule(v([-.1,.35,.5]), v([-.1,1.45,.5]), .35), wall), false);
});

test('actual face-straddling overlap is resolved geometrically rather than hidden by a displacement clamp', () => {
  const contacts = new CapsuleContacts();
  const floor = new Triangle(v([-10,0,-10]), v([-10,0,10]), v([10,0,10]));
  const hit = contacts.triangleContact(new Capsule(v([0,-.2,0]), v([0,.9,0]), .35), floor);
  assert.ok(hit); near(hit.depth, .55); near(hit.normal.y, 1);
});

test('independent KC ramp-side command replay is continuous; stock narrow phase remains a failing negative control', async () => {
  const fixture = JSON.parse(fs.readFileSync(new URL('./fixtures/player-ramp-side-contact.json', import.meta.url), 'utf8'));
  const bytes = fs.readFileSync(new URL('../public/assets/sunward-collision-v3.0.glb', import.meta.url));
  const scene = (await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')).scene;
  const tree = buildCollisionOctree(scene);
  function replay(stock) {
    const motor = new PlayerController(tree);
    motor.spawn(new Vector3());
    for (const [key, value] of Object.entries(fixture.initial.motor)) {
      if (motor[key]?.isVector3) motor[key].fromArray(value);
      else if (value !== null) motor[key] = value;
    }
    motor.collider.start.fromArray(fixture.initial.collider.start);
    motor.collider.end.fromArray(fixture.initial.collider.end);
    if (stock) motor._contacts.intersect = (source, capsule) => source.capsuleIntersect(capsule);
    let previous = motor.feetPosition(), maximum = 0, largestRise = 0, largestFrame = null;
    for (const step of fixture.steps) {
      motor.update(step.dt, step.command);
      const next = motor.feetPosition(), displacement = next.distanceTo(previous);
      if (displacement > maximum) { maximum = displacement; largestFrame = step.frame; }
      largestRise = Math.max(largestRise, next.y - previous.y);
      previous = next;
    }
    return {maximum, largestRise, largestFrame};
  }
  const stock = replay(true), exact = replay(false);
  near(stock.maximum, fixture.baseline.max, 1e-6);
  assert.equal(stock.largestFrame, 3751);
  assert.ok(stock.maximum > .72 && stock.largestRise > .69, 'negative control must reproduce the reported defect');
  assert.ok(exact.maximum < .15, JSON.stringify(exact));
  assert.ok(exact.largestRise < .08, JSON.stringify(exact));
  console.log('RAMP_SIDE_CONTACT_REGRESSION', {stock, exact});
});
