import test from 'node:test';
import assert from 'node:assert/strict';
import {mapBudgets,mapBudgetVersion} from '../src/map-budgets.js';

test('explicit later material/image allowances preserve earlier delivery contracts',()=>{
 const old=mapBudgets('3.0'),live=mapBudgets('3.1'),next=mapBudgets('3.2');
 assert.equal(old.gzip_bytes,8000000);assert.equal(live.gzip_bytes,8500000);assert.equal(next.gzip_bytes,8500000);
 assert.equal(old.materials,80);assert.equal(live.materials,80);assert.equal(next.materials,80);
 assert.equal(old.images,24);assert.equal(live.images,24);assert.equal(next.images,25);
 for(const key of['triangles','meshes','primitives','bytes','texture_rgba_bytes'])assert.equal(next[key],old[key]);
 assert.ok(Object.isFrozen(next));assert.throws(()=>{next.images=999;},TypeError);
});

test('asset-specific audits cannot borrow another version’s larger budget',()=>{
 assert.equal(mapBudgetVersion('/tmp/sunward-v3.0.glb.gz','3.2'),'3.0');
 assert.equal(mapBudgetVersion('C:\\temp\\sunward-v3.1.glb','3.2'),'3.1');
 assert.equal(mapBudgetVersion('sunward-v3.2.glb.gz','3.0'),'3.2');
 assert.equal(mapBudgetVersion('explicit-review-candidate.glb','3.2'),'3.2');
 assert.throws(()=>mapBudgets('4.0'),RangeError);assert.throws(()=>mapBudgetVersion('sunward-v9.0.glb.gz','3.2'),RangeError);
});
