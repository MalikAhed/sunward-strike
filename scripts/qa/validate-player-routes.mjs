#!/usr/bin/env node
// Reuse every approved map assertion against the new game motor, without
// modifying the frozen explorer solver or weakening/re-authoring route data.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const defaultProject = fileURLToPath(new URL('../../', import.meta.url));

export function validatePlayerRoutes({project = defaultProject, out, pace = 'walk', collision, visual} = {}) {
  if (!['walk', 'sprint'].includes(pace)) throw new RangeError('Route pace must be walk or sprint');
  const sourcePath = path.join(project, 'scripts/qa/validate-map-runtime.mjs');
  const source = fs.readFileSync(sourcePath, 'utf8');
  const marker = "const {WalkController}=await mod(path.join(opts.project,'src/physics.js'));";
  if (source.split(marker).length !== 2) throw new Error('Approved route harness import changed; review the adapter before continuing');
  let adapted = source.replace(marker,
    "const {PlayerController:WalkController}=await mod(path.join(opts.project,'src/gameplay/player-controller.js'));");
  if (pace === 'sprint') {
    const drive = 'input={x:dx/norm,z:-dz/norm,yaw:0}';
    if (adapted.split(drive).length !== 2) throw new Error('Approved route drive command changed; review the sprint adapter before continuing');
    // Same target, analogue approach, route plan, timings and assertions; turn
    // toward the target so the command exercises forward-only sprint for real.
    adapted = adapted.replace(drive, 'input={x:0,z:dist/norm,yaw:Math.atan2(-dx,-dz),sprint:true}');
  }
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'sunward-player-routes-'));
  const scriptPath = path.join(temporary, 'validate.mjs');
  const reportPath = out ? path.resolve(out) : path.join(temporary, 'report.json');
  try {
    fs.writeFileSync(scriptPath, adapted);
    const args = [scriptPath, '--project', project,
      '--routes', path.join(project, 'tests/fixtures/map-v3-routes.json'), '--out', reportPath];
    if (collision) args.push('--collision', path.resolve(collision));
    if (visual) args.push('--visual', path.resolve(visual));
    const result = spawnSync(process.execPath, args,
    {cwd: project, encoding: 'utf8', timeout: 120000, maxBuffer: 4 * 1024 * 1024});
    if (!fs.existsSync(reportPath)) throw new Error(`Player route harness failed before report: ${result.error || result.stderr || result.stdout}`);
    const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
    report.scope = 'Actual shared PlayerController and accepted bounded ThreeOctree through every frozen map route/boundary assertion; no browser input or GPU claims';
    report.controller = {
      path: 'src/gameplay/player-controller.js',
      sha256: createHash('sha256').update(fs.readFileSync(path.join(project, 'src/gameplay/player-controller.js'))).digest('hex'),
      contactsSha256: createHash('sha256').update(fs.readFileSync(path.join(project, 'src/gameplay/capsule-contacts.js'))).digest('hex'),
      routeHarnessSha256: createHash('sha256').update(source).digest('hex'),
      pace,
      adapter: pace === 'walk'
        ? 'Only the WalkController import is substituted in a temporary harness; every assertion and route fixture is unchanged'
        : 'PlayerController import and forward-facing sprint intent are substituted; every assertion, route fixture and target is unchanged. Boundary jump tests retain their original commands',
    };
    if (out) { fs.mkdirSync(path.dirname(reportPath), {recursive: true}); fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n'); }
    return {report, exitCode: result.status, stdout: result.stdout, stderr: result.stderr};
  } finally { fs.rmSync(temporary, {recursive: true, force: true}); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const options = {};
  for (let i = 2; i < process.argv.length; i += 2) options[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
  const result = validatePlayerRoutes(options);
  const report = result.report;
  console.log(JSON.stringify({passed: report.passed, routes: report.routes.length,
    boundaryWalks: report.perimeter.length, boundaryJumps: report.perimeter_jumps.length,
    failedRoutes: report.routes.filter(route => !route.passed),
    failedTests: report.tests.filter(check => !check.passed), warnings: report.warnings,
    controller: report.controller, out: options.out || null}, null, 2));
  process.exitCode = result.exitCode === 0 && report.passed ? 0 : 1;
}
