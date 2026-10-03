import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePlayerRoutes} from '../scripts/qa/validate-player-routes.mjs';

test('gameplay motor passes all 78 certified routes, 69 perimeter walks and 23 perimeter jumps', () => {
  const {report, exitCode, stdout, stderr} = validatePlayerRoutes();
  assert.equal(exitCode, 0, stdout + '\n' + stderr);
  assert.equal(report.passed, true);
  assert.equal(report.routes.length, 78); assert.ok(report.routes.every(route => route.passed));
  assert.equal(report.perimeter.length, 69); assert.ok(report.perimeter.every(route => route.passed));
  assert.equal(report.perimeter_jumps.length, 23); assert.ok(report.perimeter_jumps.every(route => route.passed));
  assert.deepEqual(report.warnings, []);
  console.log('GAMEPLAY_MOVEMENT_ROUTE_GATE', {routes: report.routes.length, perimeter: report.perimeter.length, jumps: report.perimeter_jumps.length, controller: report.controller.sha256});
});

test('forward sprint also preserves all 78 authored routes and 69 boundary pressure samples', () => {
  const {report, exitCode, stdout, stderr} = validatePlayerRoutes({pace: 'sprint'});
  assert.equal(exitCode, 0, stdout + '\n' + stderr);
  assert.equal(report.passed, true);
  assert.equal(report.routes.length, 78); assert.ok(report.routes.every(route => route.passed));
  assert.equal(report.perimeter.length, 69); assert.ok(report.perimeter.every(route => route.passed));
  assert.deepEqual(report.warnings, []);
  assert.equal(report.controller.pace, 'sprint');
});
