import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {prepareMapAssets} from '../scripts/prepare-map-assets.mjs';

const raw = Buffer.alloc(24,0x20);raw.write('glTF');raw.writeUInt32LE(2,4);raw.writeUInt32LE(24,8);raw.writeUInt32LE(4,12);raw.writeUInt32LE(0x4e4f534a,16);raw.write('{}',20);
const compressed = gzipSync(raw);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
async function fixture(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(),'sunward-prepare-'));
  t.after(() => fs.rm(directory,{recursive:true,force:true}));
  const gzipPath=path.join(directory,'map.glb.gz'),rawPath=path.join(directory,'map.glb');
  await fs.writeFile(gzipPath,compressed);
  return {directory,gzipPath,rawPath,options:{assetsDirectory:directory,mapFilename:'map.glb.gz',expectedDecodedSha256:sha(raw)}};
}

test('clean checkout preparation creates byte-identical raw fallback without altering gzip', async t => {
  const f=await fixture(t);const result=await prepareMapAssets(f.options);
  assert.equal(result.action,'created');assert.deepEqual(await fs.readFile(f.rawPath),raw);assert.deepEqual(await fs.readFile(f.gzipPath),compressed);
  assert.equal(result.decodedSha256,sha(raw));assert.equal(result.gzipBytes,compressed.length);assert.equal(result.decodedBytes,raw.length);
});

test('matching existing raw fallback is verified without rewriting its timestamp', async t => {
  const f=await fixture(t);await fs.writeFile(f.rawPath,raw);await fs.utimes(f.rawPath,946684800,946684800);
  const before=await fs.stat(f.rawPath),result=await prepareMapAssets(f.options),after=await fs.stat(f.rawPath);
  assert.equal(result.action,'verified-existing');assert.equal(after.mtimeMs,before.mtimeMs);assert.deepEqual(await fs.readFile(f.rawPath),raw);
});

test('divergent same-size or different-size raw edits are never overwritten', async t => {
  const f=await fixture(t);
  for (const changed of [Buffer.from(raw),Buffer.from('author edits')]) {
    changed[changed.length-1]^=1;await fs.writeFile(f.rawPath,changed);
    await assert.rejects(prepareMapAssets(f.options),/differs from the committed gzip.*not overwritten/);
    assert.deepEqual(await fs.readFile(f.rawPath),changed);
  }
});

test('concurrent preparation uses exclusive creation and both callers see identical raw bytes', async t => {
  const f=await fixture(t);const results=await Promise.all([prepareMapAssets(f.options),prepareMapAssets(f.options)]);
  assert.ok(results.some(r=>r.action==='created'));assert.deepEqual(await fs.readFile(f.rawPath),raw);
});

test('non-regular raw path and symbolic links are refused', async t => {
  const f=await fixture(t);await fs.mkdir(f.rawPath);
  await assert.rejects(prepareMapAssets(f.options),/non-regular raw asset/);
  await fs.rmdir(f.rawPath);const external=path.join(f.directory,'keep.glb');await fs.writeFile(external,raw);await fs.symlink(external,f.rawPath);
  await assert.rejects(prepareMapAssets(f.options),/non-regular raw asset/);assert.deepEqual(await fs.readFile(external),raw);
});

test('bad gzip, wrong decoded hash and non-gzip bytes fail before writing a fallback', async t => {
  const f=await fixture(t);
  await assert.rejects(prepareMapAssets({...f.options,expectedDecodedSha256:'0'.repeat(64)}),/SHA-256 differs/);
  await assert.rejects(fs.stat(f.rawPath),{code:'ENOENT'});
  await fs.writeFile(f.gzipPath,compressed.subarray(0,10));await assert.rejects(prepareMapAssets(f.options),{code:'INVALID_GZIP'});
  await fs.writeFile(f.gzipPath,raw);await assert.rejects(prepareMapAssets(f.options),/Expected gzip bytes/);
  await assert.rejects(fs.stat(f.rawPath),{code:'ENOENT'});
});

test('preparation rejects path traversal and uncompressed filenames', async t => {
  const f=await fixture(t);
  for (const mapFilename of ['../map.glb.gz','/tmp/map.glb.gz','map.glb'])await assert.rejects(prepareMapAssets({...f.options,mapFilename}),/filename without directory/);
});

test('npm dev and production build prepare the raw fallback, while test requires only committed gzip', async () => {
  const packageJson=JSON.parse(await fs.readFile(new URL('../package.json',import.meta.url),'utf8'));
  assert.equal(packageJson.scripts.predev,'npm run prepare:assets');assert.equal(packageJson.scripts.prebuild,'npm run prepare:assets');
  assert.equal(packageJson.scripts['prepare:assets'],'node scripts/prepare-map-assets.mjs');assert.equal(packageJson.scripts.pretest,undefined);
  const ignores=await fs.readFile(new URL('../.gitignore',import.meta.url),'utf8');assert.ok(ignores.split('\n').includes('public/assets/sunward-v3.0.glb'));
});
