import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {buildOfflineBundle} from '../scripts/offline/build-offline.mjs';
import {createOfflineClient,offlineStatusText,chooseMapDelivery} from '../src/gameplay/offline-client.js';
import {NodeModel} from './helpers/dom-model.js';
import {makeWorker} from './helpers/worker-harness.js';
const scope='https://example.test/subpath/';
async function fixture(){
 const outDir=await mkdtemp(path.join(tmpdir(),'sunward-offline-'));await mkdir(path.join(outDir,'assets'));
 const entries={'index.html':'<p>SUNWARD</p>','assets/app-hash.js':'export const game=1;','assets/map.glb.gz':'gzip-fixture','assets/map.glb':'raw-fixture'};
 for(const [name,content]of Object.entries(entries))await writeFile(path.join(outDir,name),content);
 const manifest=await buildOfflineBundle({outDir,builtFiles:['index.html','assets/app-hash.js'],runtimeFiles:['assets/map.glb.gz','assets/map.glb']});
 const script=await readFile(path.join(outDir,'sw.js'),'utf8'),files=new Map(Object.entries(entries).map(([name,content])=>[scope+name,content]));
 return {outDir,manifest,script,files,async dispose(){await rm(outDir,{recursive:true,force:true});}};
}
test('exact offline manifest pins built bytes, raw compatibility fallback and version changes',async()=>{
 const f=await fixture();try{
  for(const asset of f.manifest.assets){const bytes=await readFile(path.join(f.outDir,asset.url));assert.equal(asset.bytes,bytes.length);assert.equal(asset.sha256,createHash('sha256').update(bytes).digest('hex'));}
  assert.match(f.script,/const MANIFEST = \{/);assert.doesNotMatch(f.script,/__SUNWARD_MANIFEST__/);
  await writeFile(path.join(f.outDir,'assets/app-hash.js'),'new code');const next=await buildOfflineBundle({outDir:f.outDir,builtFiles:['index.html','assets/app-hash.js'],runtimeFiles:['assets/map.glb.gz','assets/map.glb']});assert.notEqual(next.version,f.manifest.version);
  await assert.rejects(buildOfflineBundle({outDir:f.outDir,builtFiles:['../secret'],runtimeFiles:[]}),/Unsafe/);
 }finally{await f.dispose();}
});
test('verified install serves a disconnected repeat navigation and only exact scoped assets',async()=>{
 const f=await fixture();try{
  const worker=makeWorker(f.script,{files:f.files});await worker.install();assert.equal(worker.skips,0,'No automatic activation over an existing match');await worker.activate();assert.equal(worker.claimed,1);
  worker.offline();const shell=await worker.request(scope,'navigate');assert.match(await shell.text(),/SUNWARD/);
  assert.equal(await worker.request(scope+'assets/map.glb'),null);assert.equal(await(await worker.request(scope+'assets/map.glb.gz?ignored=1')).text(),'gzip-fixture');
  assert.equal(await worker.request('https://other.test/assets/map.glb'),null);assert.equal(await worker.request(scope+'unlisted-personal-file'),null);assert.equal(await worker.request(scope+'assets/map.glb','cors','POST'),null);
  await worker.message({type:'SUNWARD_STATUS'});assert.equal(worker.messages.at(-1).state,'ready');
 }finally{await f.dispose();}
});
test('quota or corrupt asset failure rolls back only the new cache and never reports ready',async()=>{
 const f=await fixture();try{
  const other=new Map([['another-app',new Map()]]),quota=makeWorker(f.script,{files:f.files,existing:other,quota:true});await assert.rejects(quota.install(),/Quota/);assert.deepEqual([...other.keys()],['another-app']);assert.equal(quota.messages.some(m=>m.state==='ready'),false);
  const bad=new Map(f.files);bad.set(scope+'assets/map.glb.gz','bad bytes');const corrupt=makeWorker(f.script,{files:bad});await assert.rejects(corrupt.install(),/Build changed/);assert.equal(corrupt.storage.size,0);
 }finally{await f.dispose();}
});
test('cache eviction yields an honest repair status and a 503 while offline',async()=>{
 const f=await fixture();try{
  const worker=makeWorker(f.script,{files:f.files});await worker.install();const cache=[...worker.storage.values()][0];cache.delete(scope+'assets/map.glb.gz');worker.offline();
  await worker.message({type:'SUNWARD_STATUS'});assert.equal(worker.messages.at(-1).state,'error');const missing=await worker.request(scope+'assets/map.glb.gz');assert.equal(missing.status,503);
 }finally{await f.dispose();}
});
test('updates require safe replies from open clients; busy matches prevent activation',async()=>{
 const f=await fixture();try{
  const busy=makeWorker(f.script,{files:f.files,busy:true});await busy.message({type:'SUNWARD_ACTIVATE_IF_IDLE'});assert.equal(busy.skips,0);assert.equal(busy.messages.at(-1).state,'update-blocked');
  const idle=makeWorker(f.script,{files:f.files});await idle.message({type:'SUNWARD_ACTIVATE_IF_IDLE'});assert.equal(idle.skips,1);
 }finally{await f.dispose();}
});
test('client never reloads a running match and has graceful unsupported/registration failures',async()=>{
 const statuses=[],unsupported=createOfflineClient({environment:{},onStatus:s=>statuses.push(s)});await unsupported.start();assert.equal(statuses.at(-1).state,'unsupported');
 const serviceWorker=new NodeModel('worker-container'),active=new NodeModel('worker'),waiting=new NodeModel('worker');let busy=true,reloaded=0,posted=[];
 active.postMessage=data=>posted.push(data);waiting.postMessage=data=>posted.push(data);serviceWorker.controller=active;
 const registration=new NodeModel('registration');Object.assign(registration,{active,waiting,update:async()=>{}});serviceWorker.register=async()=>registration;
 const client=createOfflineClient({baseUrl:'./',environment:{navigator:{serviceWorker},isSecureContext:true,location:{reload(){reloaded++;}}},canUpdate:()=>!busy,onStatus:s=>statuses.push(s)});
 await client.start();assert.equal(client.requestUpdate(),false);assert.equal(statuses.at(-1).state,'update-blocked');busy=false;assert.equal(client.requestUpdate(),true);assert.equal(posted.at(-1).type,'SUNWARD_ACTIVATE_IF_IDLE');
 busy=true;serviceWorker.controller=waiting;serviceWorker.dispatch('controllerchange');assert.equal(reloaded,0);assert.equal(statuses.at(-1).state,'reload-required');serviceWorker.dispatch('message',{source:waiting,data:{type:'SUNWARD_OFFLINE',state:'ready'}});assert.equal(statuses.at(-1).state,'reload-required','Later ready status cannot dismiss the old-code reload gate');
 serviceWorker.dispatch('message',{source:waiting,data:{type:'SUNWARD_CAN_UPDATE',requestId:'v2'}});assert.equal(posted.at(-1).safe,false);client.dispose();
 assert.match(offlineStatusText({state:'ready',bytes:1048576}),/Saved.*1.0 MB/);assert.doesNotMatch(offlineStatusText({state:'error'}),/^Saved/);
});
test('explicit repair restores evicted current-version entries without requiring a new release',async()=>{
 const f=await fixture();try{
  const worker=makeWorker(f.script,{files:f.files});await worker.install();const cache=[...worker.storage.values()][0];cache.delete(scope+'assets/map.glb.gz');
  await worker.message({type:'SUNWARD_REPAIR'});assert.equal(worker.messages.at(-1).state,'ready');worker.offline();assert.equal(await(await worker.request(scope+'assets/map.glb.gz')).text(),'gzip-fixture');
 }finally{await f.dispose();}
});
test('gzip capability selects exactly one pinned representation without doubling map traffic',async()=>{
 assert.equal(chooseMapDelivery({}),'raw');assert.equal(chooseMapDelivery({DecompressionStream:class{constructor(){throw new Error('unsupported format');}}}),'raw');assert.equal(chooseMapDelivery({DecompressionStream:class{}}),'gzip');
 const f=await fixture();try{
  const gzip=makeWorker(f.script,{files:f.files,delivery:'gzip'});await gzip.install();const gzCache=[...gzip.storage.values()][0];assert.equal(gzCache.has(scope+'assets/map.glb'),false);assert.equal(gzCache.has(scope+'assets/map.glb.gz'),true);assert.equal(gzip.messages.at(-1).bytes,f.manifest.deliveryBytes.gzip);
  const raw=makeWorker(f.script,{files:f.files,delivery:'raw'});await raw.install();const rawCache=[...raw.storage.values()][0];assert.equal(rawCache.has(scope+'assets/map.glb.gz'),false);assert.equal(rawCache.has(scope+'assets/map.glb'),true);raw.offline();assert.equal(await(await raw.request(scope+'assets/map.glb')).text(),'raw-fixture');assert.equal(await raw.request(scope+'assets/map.glb.gz'),null);assert.equal(raw.messages.at(-1).bytes,f.manifest.deliveryBytes.raw);
  assert.throws(()=>makeWorker(f.script,{files:f.files,delivery:'anything'}),/Explicit gzip or raw/);
 }finally{await f.dispose();}
});
test('every same-scope tab must be idle; unrelated app tabs are excluded',async()=>{
 const f=await fixture();try{
  const blocked=makeWorker(f.script,{files:f.files});blocked.addClient({id:'second-game',safe:false});await blocked.message({type:'SUNWARD_ACTIVATE_IF_IDLE'});assert.equal(blocked.skips,0);
  const allowed=makeWorker(f.script,{files:f.files});allowed.addClient({id:'other-app',url:'https://example.test/other/',safe:false});allowed.addClient({id:'second-game',safe:true});await allowed.message({type:'SUNWARD_ACTIVATE_IF_IDLE'});assert.equal(allowed.skips,1);
 }finally{await f.dispose();}
});
test('install reuses completed HTTP cache and only reloads a stale response after integrity fails',async()=>{
 const f=await fixture();try{
  const cached=makeWorker(f.script,{files:f.files});await cached.install();assert.ok(cached.fetches.every(request=>request.cache==='force-cache'));assert.equal(cached.fetches.length,f.manifest.assets.length-1);
  const files=new Map(f.files);files.set(scope+'assets/app-hash.js',request=>request.cache==='force-cache'?'old code':'export const game=1;');const repaired=makeWorker(f.script,{files});await repaired.install();
  const attempts=repaired.fetches.filter(request=>request.url.endsWith('app-hash.js'));assert.deepEqual(attempts.map(request=>request.cache),['force-cache','reload']);assert.equal(repaired.messages.at(-1).state,'ready');
 }finally{await f.dispose();}
});
test('worker-only changes create a separate cache version and cannot overwrite active install storage',async()=>{
 const f=await fixture();try{
  const template=await readFile(new URL('../scripts/offline/service-worker.template.js',import.meta.url),'utf8'),templatePath=path.join(f.outDir,'changed-worker-template.js');await writeFile(templatePath,template+'\n// protocol-only revision\n');
  const next=await buildOfflineBundle({outDir:f.outDir,builtFiles:['index.html','assets/app-hash.js'],runtimeFiles:['assets/map.glb.gz','assets/map.glb'],templatePath});assert.notEqual(next.version,f.manifest.version);assert.notEqual(next.workerTemplateSha256,f.manifest.workerTemplateSha256);
  const old=makeWorker(f.script,{files:f.files});await old.install();const oldNames=[...old.storage.keys()];const changed=makeWorker(await readFile(path.join(f.outDir,'sw.js'),'utf8'),{files:f.files,existing:old.storage,quota:true});await assert.rejects(changed.install(),/Quota/);assert.deepEqual([...old.storage.keys()],oldNames);
 }finally{await f.dispose();}
});
test('offline update rejection preserves controller-verified readiness and still reports incomplete or absent caches',async()=>{
 for(const cacheState of ['ready','error',null]){
  const serviceWorker=new NodeModel('worker-container'),active=cacheState?new NodeModel('worker'):null,states=[];let queries=0;
  serviceWorker.controller=active;
  if(active)active.postMessage=message=>{if(message.type==='SUNWARD_STATUS'){queries++;serviceWorker.dispatch('message',{source:active,data:{type:'SUNWARD_OFFLINE',state:cacheState,message:cacheState==='error'?'Cache incomplete':undefined}});}};
  const registration=new NodeModel('registration');Object.assign(registration,{active,waiting:null,update:async()=>{throw new Error('Network is offline');}});serviceWorker.register=async()=>registration;
  const client=createOfflineClient({baseUrl:'./',environment:{navigator:{serviceWorker},isSecureContext:true,location:{reload(){}}},onStatus:state=>states.push(state)});await client.start();
  assert.equal(states.at(-1).state,cacheState??'error');if(cacheState==='ready'){assert.ok(queries>=2);assert.equal(states.some(state=>state.state==='error'),false,'Network update failure cannot revoke verified cached readiness');}client.dispose();
 }
});
