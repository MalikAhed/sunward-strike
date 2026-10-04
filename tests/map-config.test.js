import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {MAP_CONFIG} from '../src/map-config.js';
import {mapBudgets} from '../src/map-budgets.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import {PerspectiveCamera,Vector3} from 'three';
import {withinPlayBounds,fittedOverviewPosition,overviewFrameOnResize,overviewFrameAfterModeChange} from '../src/math.js';

test('WebGL fallback poster is the accepted current-source overview, not a stale map',()=>{
  const version='v'+MAP_CONFIG.version.replaceAll('.','');
  const poster=readFileSync(new URL('../public/assets/map-poster.png',import.meta.url));
  const accepted=readFileSync(new URL(`../docs/qa/${version}-gameplay/overview.png`,import.meta.url));
  assert.deepEqual(poster,accepted);
});

test('canonical outline and spawns replace the old rectangular map contract',()=>{
  assert.equal(MAP_CONFIG.outline.length,23);
  for(const point of MAP_CONFIG.outline){assert.equal(point.length,2);assert.ok(point.every(Number.isFinite));assert.equal(withinPlayBounds(...point),false);}
  for(const [name,p] of Object.entries(MAP_CONFIG.spawns)){assert.ok(withinPlayBounds(p[0],p[2],.35),`${name} must be inside the playable outline`);}
  assert.equal(withinPlayBounds(100,100),false);
  assert.equal(withinPlayBounds(0,0),true);
  assert.match(MAP_CONFIG.scaleNotice,/not an authenticated game survey/);
});

test('configured public assets decode to real GLB2 files within delivery and decoded budgets',async()=>{
  for(const [kind,name] of Object.entries(MAP_CONFIG.assets)){
    assert.match(name,/^[\w.-]+\.glb(?:\.gz)?$/);
    const delivery=readFileSync(new URL(`../public/assets/${name}`,import.meta.url));
    const bytes=Buffer.from(await decodeGlbBytes(delivery));
    assert.ok(delivery.length<(kind==='map'?(mapBudgets(MAP_CONFIG.version).gzip_bytes):3_000_000),`${kind} transfer budget`);
    assert.equal(bytes.readUInt32LE(0),0x46546c67,name);
    assert.equal(bytes.readUInt32LE(4),2,name);
    assert.equal(bytes.readUInt32LE(8),bytes.length,name);
    assert.ok(bytes.length<(kind==='collision'?3_000_000:32_000_000),`${kind} byte budget`);
  }
});

test('overview presets frame the full outline at portrait and wide aspect ratios',()=>{
  for(const aspect of [390/844,844/390,16/9,32/9])for(const key of ['hero','topdown']){
    const view=MAP_CONFIG.viewpoints[key],camera=new PerspectiveCamera(58,aspect,.05,500);
    camera.position.fromArray(fittedOverviewPosition(view,aspect));camera.lookAt(...view.target);camera.updateMatrixWorld();
    for(const [x,z] of MAP_CONFIG.outline)for(const y of [0,12]){
      const p=new Vector3(x,y,z).project(camera);
      assert.ok(Math.abs(p.x)<=.860001&&Math.abs(p.y)<=.780001&&p.z<1,`${key}/${aspect} outline projection`);
    }
  }
});

test('untouched overview refits on wide-to-portrait resize without resetting manual cameras',()=>{
  for(const key of ['hero','topdown']){
    const wide=overviewFrameOnResize(key,16/9,{active:true,mode:'fly'});
    const portrait=overviewFrameOnResize(key,390/844,{active:true,mode:'fly'});
    assert.ok(wide&&portrait);
    const camera=new PerspectiveCamera(58,390/844,.05,500);camera.position.fromArray(portrait);camera.lookAt(...MAP_CONFIG.viewpoints[key].target);camera.updateMatrixWorld();
    for(const [x,z]of MAP_CONFIG.outline)for(const y of [0,12]){const p=new Vector3(x,y,z).project(camera);assert.ok(Math.abs(p.x)<=.860001&&Math.abs(p.y)<=.780001);}
    assert.equal(overviewFrameOnResize(key,390/844,{active:false,mode:'fly'}),null);
    assert.equal(overviewFrameOnResize(key,390/844,{active:false,mode:'orbit'}),null);
    assert.equal(overviewFrameOnResize(key,390/844,{active:true,mode:'walk'}),null);
  }
});

test('walk then fly keeps manual camera ownership across a later resize',()=>{
  let active=true;
  active=overviewFrameAfterModeChange(active,'walk');assert.equal(active,false);
  active=overviewFrameAfterModeChange(active,'fly');assert.equal(active,false);
  assert.equal(overviewFrameOnResize('hero',390/844,{active,mode:'fly'}),null);
});
