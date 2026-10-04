import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {MAP_CONFIG} from '../src/map-config.js';
import {mapBudgets} from '../src/map-budgets.js';

test('complete authored map routes, perimeter walking and jumps remain traversable',()=>{
 const project=fileURLToPath(new URL('../',import.meta.url)),temporary=fs.mkdtempSync(path.join(os.tmpdir(),'sunward-map-qa-')),reportPath=path.join(temporary,'report.json');
 try{
  const result=spawnSync(process.execPath,[path.join(project,'scripts/qa/validate-map-runtime.mjs'),'--visual',path.join(project,'public/assets',MAP_CONFIG.assets.map),'--collision',path.join(project,'public/assets',MAP_CONFIG.assets.collision),'--out',reportPath],{cwd:project,encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024});
  assert.equal(result.status,0,result.stdout+'\n'+result.stderr);const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
  assert.equal(report.passed,true);assert.equal(report.routes.length,78);assert.ok(report.routes.every(r=>r.passed));assert.equal(report.perimeter.length,MAP_CONFIG.outline.length*3);assert.ok(report.perimeter.every(r=>r.passed));assert.equal(report.perimeter_jumps.length,MAP_CONFIG.outline.length);assert.ok(report.perimeter_jumps.every(r=>r.passed));assert.deepEqual(report.warnings,[]);assert.equal(report.visual.sha256,MAP_CONFIG.decodedMapSha256);assert.ok(report.visual.delivery_bytes<mapBudgets(MAP_CONFIG.version).gzip_bytes);
  console.log('FULL_MAP_RUNTIME_GATE',{routes:report.routes.length,walkBoundarySamples:report.perimeter.length,jumpBoundarySamples:report.perimeter_jumps.length,octree:report.octree});
 }finally{fs.rmSync(temporary,{recursive:true,force:true});}
});
