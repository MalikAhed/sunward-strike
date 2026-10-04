import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {LoadingManager} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MAP_CONFIG} from '../src/map-config.js';
import {decodeGlbBytes, loadGlbBytes, loadGlbAsset, rawGlbFallbackUrl} from '../src/asset-loader.js';

function tinyGlb() {
  const json = Buffer.from(JSON.stringify({asset: {version: '2.0'}, scene: 0, scenes: [{nodes: []}]}));
  const length = Math.ceil(json.length / 4) * 4;
  const bytes = Buffer.alloc(20 + length, 0x20);
  bytes.write('glTF');bytes.writeUInt32LE(2,4);bytes.writeUInt32LE(bytes.length,8);
  bytes.writeUInt32LE(length,12);bytes.writeUInt32LE(0x4e4f534a,16);json.copy(bytes,20);
  return bytes;
}
const raw = tinyGlb();
const gz = gzipSync(raw);
const asBuffer = bytes => Buffer.from(bytes);
const response = bytes => new Response(bytes, {headers: {'content-length': String(bytes.length)}});
const code = expected => error => error.name === 'GlbAssetError' && error.code === expected;

test('committed gzip decodes through the native decoder to the exact accepted current map', async () => {
  const gzip = readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`, import.meta.url));
  const bytes = asBuffer(await decodeGlbBytes(gzip));
  assert.equal(gzip.length, 6_961_481);
  assert.equal(createHash('sha256').update(gzip).digest('hex'), '5863c77258fff6c35a26000d89f8dc82b37995442276d47017492b97bec3d5a1');
  assert.equal(bytes.length, 19_913_252);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), MAP_CONFIG.decodedMapSha256);
  assert.equal(MAP_CONFIG.decodedMapSha256, 'd0a1e19862b9d0a614dd484e8686b052bbcdeb796622a63f272ca343e1081a7b');
});

test('already-decoded GLB passes through without invoking a decompressor', async () => {
  const bytes = Uint8Array.from(raw).buffer;
  class DoNotConstruct {constructor() {assert.fail('raw bytes must not be decompressed');}}
  assert.equal(await decodeGlbBytes(bytes, {decompressionStream: DoNotConstruct}), bytes);
  assert.deepEqual(asBuffer(await decodeGlbBytes(bytes, {decompressionStream: null})), raw);
});

test('typed-array and DataView slices exclude unrelated backing-buffer bytes', async () => {
  const padded = Buffer.concat([Buffer.from('before'), raw, Buffer.from('after')]);
  for (const view of [padded.subarray(6,6 + raw.length), new DataView(padded.buffer,padded.byteOffset + 6,raw.length)]) {
    const decoded = await decodeGlbBytes(view);
    assert.equal(decoded.byteLength, raw.length);
    assert.deepEqual(asBuffer(decoded), raw);
  }
  await assert.rejects(decodeGlbBytes('not binary'), TypeError);
});

test('malformed or truncated transport bytes are rejected with precise error codes', async () => {
  for (const bytes of [Buffer.alloc(0), Buffer.from('<html>Not found</html>'), Buffer.from([0x1f])]) {
    await assert.rejects(decodeGlbBytes(bytes), code('INVALID_PAYLOAD'));
  }
  await assert.rejects(decodeGlbBytes(gz.subarray(0,gz.length - 4)), code('INVALID_GZIP'));
  const damaged = Buffer.from(gz);damaged[damaged.length - 8] ^= 0xff;
  await assert.rejects(decodeGlbBytes(damaged), code('INVALID_GZIP'));
  await assert.rejects(decodeGlbBytes(gzipSync(Buffer.from('not GLB'))), code('INVALID_GLB'));
  await assert.rejects(decodeGlbBytes(gz, {decompressionStream: null}), code('GZIP_UNAVAILABLE'));
});

test('GLB version, size, chunk alignment, chunk bounds and duplicate JSON are validated', async () => {
  const mutations = [
    b => b.writeUInt32LE(1,4),
    b => b.writeUInt32LE(b.length + 4,8),
    b => b.writeUInt32LE(b.length,12),
    b => b.writeUInt32LE(b.readUInt32LE(12) - 1,12),
    b => b.writeUInt32LE(0x004e4942,16),
  ];
  for (const mutate of mutations) {const bytes = Buffer.from(raw);mutate(bytes);await assert.rejects(decodeGlbBytes(bytes),code('INVALID_GLB'));}
  await assert.rejects(decodeGlbBytes(Buffer.from('glTF')),code('INVALID_GLB'));
  const duplicate = Buffer.concat([raw,raw.subarray(12)]);duplicate.writeUInt32LE(duplicate.length,8);
  await assert.rejects(decodeGlbBytes(duplicate),code('INVALID_GLB'));
  const trailing = Buffer.concat([raw,Buffer.alloc(4)]);trailing.writeUInt32LE(trailing.length,8);
  await assert.rejects(decodeGlbBytes(trailing),code('INVALID_GLB'));
});

test('fallback URL strips only the pathname suffix and preserves relative base, query and fragment', () => {
  for (const [input,expected] of [
    ['./assets/map.glb.gz','./assets/map.glb'],
    ['/sunward-strike/assets/map.glb.gz?v=1#scene','/sunward-strike/assets/map.glb?v=1#scene'],
    ['https://example.test/nested/map.glb.GZ?q=abc.gz','https://example.test/nested/map.glb?q=abc.gz'],
    ['assets/map.glb?asset=elsewhere.gz#file.gz','assets/map.glb?asset=elsewhere.gz#file.gz'],
    ['map.glb#scene.gz','map.glb#scene.gz'],
  ]) assert.equal(rawGlbFallbackUrl(input),expected);
});

test('compressed fetch reports transfer progress then decode and forwards AbortSignal', async () => {
  const events = [],stages = [],controller = new AbortController();
  let fetched;
  const bytes = await loadGlbBytes('./assets/map.glb.gz?v=1',{
    signal: controller.signal,
    fetcher: async (url,options) => {fetched = {url,options};return new Response(new ReadableStream({start(c) {c.enqueue(gz.subarray(0,16));c.enqueue(gz.subarray(16));c.close();}}),{headers: {'content-length': String(gz.length)}});},
    onProgress: event => events.push(event),onStage: stage => stages.push(stage),
  });
  assert.deepEqual(asBuffer(bytes),raw);
  assert.equal(fetched.url,'./assets/map.glb.gz?v=1');assert.equal(fetched.options.signal,controller.signal);
  assert.deepEqual(stages,['download','decode']);assert.deepEqual(events.map(event => event.loaded),[16,gz.length]);
  assert.ok(events.every(event => event.total === gz.length && event.lengthComputable));
});

test('HTTP-decoded GLB uses magic, not content-type or filename; encoded totals are indeterminate', async () => {
  const events = [];
  const decoded = await loadGlbBytes('map.glb.gz',{
    fetcher: async () => new Response(raw,{headers: {'content-type': 'application/gzip','content-encoding':'gzip','content-length':'3'}}),
    onProgress: event => events.push(event),
  });
  assert.deepEqual(asBuffer(decoded),raw);
  assert.ok(events.length);assert.ok(events.every(event => !event.lengthComputable && event.total === 0));
});

test('missing native decompressor fetches raw fallback directly without downloading gzip first', async () => {
  const requests = [];
  assert.deepEqual(asBuffer(await loadGlbBytes('/project/assets/map.glb.gz?rev=1#scene',{
    decompressionStream: null,fetcher: async url => {requests.push(url);return response(raw);},
  })),raw);
  assert.deepEqual(requests,['/project/assets/map.glb?rev=1#scene']);
  requests.length = 0;
  await loadGlbBytes('map.glb.gz',{decompressionStream:null,rawFallbackUrl:'./legacy/asset.glb',fetcher:async url => {requests.push(url);return response(raw);}});
  assert.deepEqual(requests,['./legacy/asset.glb']);
});

test('raw response and arrayBuffer-only response work without a native decompressor or stream reader', async () => {
  const events = [];
  const bytes = await loadGlbBytes('map.glb.gz',{decompressionStream:null,rawFallbackUrl:null,onProgress:event => events.push(event),fetcher:async () => ({ok:true,arrayBuffer:async () => Uint8Array.from(raw).buffer})});
  assert.deepEqual(asBuffer(bytes),raw);assert.deepEqual(events,[{loaded:raw.length,total:raw.length,lengthComputable:true}]);
});

test('HTTP, corrupt gzip, unavailable fetch, network and cancellation errors do not trigger hidden retries', async () => {
  let calls = 0;
  await assert.rejects(loadGlbBytes('map.glb.gz',{fetcher:async () => {calls++;return new Response('no',{status:404,statusText:'Not Found'});}}),error => code('HTTP_ERROR')(error) && /404 Not Found/.test(error.message));
  assert.equal(calls,1);calls = 0;
  await assert.rejects(loadGlbBytes('map.glb.gz',{fetcher:async () => {calls++;return response(gz.subarray(0,12));}}),code('INVALID_GZIP'));
  assert.equal(calls,1);
  await assert.rejects(loadGlbBytes('map.glb.gz',{fetcher:null}),code('FETCH_UNAVAILABLE'));
  for (const error of [new TypeError('network failed'),new DOMException('Aborted','AbortError')]) {
    await assert.rejects(loadGlbBytes('map.glb.gz',{fetcher:async () => {throw error;}}),error);
  }
});

test('GLTFLoader.parseAsync accepts decoded bytes with no browser/GPU and preserves relative resource base', async () => {
  const manager = new LoadingManager(),loader = new GLTFLoader(manager),stages = [];
  const model = await loadGlbAsset(loader,'./assets/map.glb.gz?version=1',{
    fetcher:async () => response(gz),onStage:stage => stages.push(stage),
  });
  assert.ok(model.scene.isGroup);assert.equal(model.parser.options.path,'./assets/');
  assert.deepEqual(stages,['download','decode','parse']);
  const explicit = await loadGlbAsset(loader,'map.glb.gz',{resourcePath:'/project/assets/',fetcher:async () => response(raw)});
  assert.equal(explicit.parser.options.path,'/project/assets/');
});

test('LoadingManager retains root item through parse and embedded resources, and ends once', async () => {
  let releases,completed = 0,parsed = false;
  const manager = new LoadingManager(() => {completed++;});
  const loader = {manager,parseAsync:async (bytes,base) => {
    assert.deepEqual(asBuffer(bytes),raw);assert.equal(base,'./assets/');parsed = true;
    manager.itemStart('embedded-texture');manager.itemEnd('embedded-texture');
    await new Promise(resolve => {releases=resolve;});
    return {scene:'parsed'};
  }};
  const promise = loadGlbAsset(loader,'./assets/map.glb.gz',{fetcher:async () => response(raw)});
  while (!parsed) await new Promise(resolve => setImmediate(resolve));
  assert.equal(completed,0);releases();assert.deepEqual(await promise,{scene:'parsed'});assert.equal(completed,1);
});

test('download and parser failures balance manager errors, and a subsequent explicit retry succeeds', async () => {
  for (const failure of ['download','parse']) {
    const errors = [],progress = [];let attempt = 0;
    const manager = new LoadingManager(undefined,(_url,loaded,total) => progress.push([loaded,total]),url => errors.push(url));
    const loader = {manager,parseAsync:async () => {if(failure==='parse' && attempt===1)throw new Error('parse failure');return {scene:'ok'};}};
    const options = {fetcher:async () => {attempt++;if(failure==='download' && attempt===1)throw new Error('download failure');return response(raw);}};
    await assert.rejects(loadGlbAsset(loader,'./assets/map.glb.gz',options),new RegExp(failure+' failure'));
    assert.deepEqual(errors,['./assets/map.glb.gz']);assert.deepEqual(progress,[[1,1]]);
    assert.deepEqual(await loadGlbAsset(loader,'./assets/map.glb.gz',options),{scene:'ok'});
    assert.deepEqual(progress,[[1,1],[2,2]]);assert.equal(errors.length,1);
  }
});

test('main loading source keeps single-flight retry, clears stale errors and reserves completion for parsed map', () => {
  const source = readFileSync(new URL('../src/main.js',import.meta.url),'utf8');
  assert.match(source,/if\(mapLoading\|\|state.ready\)return/);
  assert.match(source,/mapLoading=true;mapParsing=false;mapProgress=0;state.lastError=null/);
  assert.match(source,/finally\{mapLoading=false;mapParsing=false;\}/);
  assert.match(source,/retry.addEventListener\('click',\(\)=>loadMap\(\)\)/);
  assert.match(source,/resourcePath:asset\(''\)/);
  assert.match(source,/Math.min\(percent,95\)/);
  assert.match(source,/state.ready=true;state.lastError=null;\$\('load-progress'\).style.width='100%'/);
});
