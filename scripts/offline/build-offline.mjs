import {readFile,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export async function buildOfflineBundle({outDir,builtFiles,runtimeFiles,templatePath=new URL('./service-worker.template.js',import.meta.url)}) {
  const filenames=[...new Set([...builtFiles,...runtimeFiles])].sort();
  const assets=[];
  for(const filename of filenames){
    if(!filename||filename.includes('..')||path.isAbsolute(filename)||filename.includes('\\'))throw new Error('Unsafe offline asset path: '+filename);
    const bytes=await readFile(path.join(outDir,filename));
    assets.push({url:filename,bytes:bytes.byteLength,sha256:sha256(bytes)});
  }
  if(!assets.some(asset=>asset.url==='index.html'))throw new Error('Offline bundle requires the generated index.html');
  const template=await readFile(templatePath,'utf8'),workerTemplateSha256=sha256(template);
  const version=sha256(JSON.stringify({assets,workerTemplateSha256})).slice(0,20);
  const gzipMap=runtimeFiles.find(name=>name.endsWith('.glb.gz')),rawMap=gzipMap?.slice(0,-3);
  if(!gzipMap||!runtimeFiles.includes(rawMap))throw new Error('Offline delivery requires both pinned map representations');
  const allBytes=assets.reduce((sum,asset)=>sum+asset.bytes,0),size=name=>assets.find(asset=>asset.url===name).bytes;
  const manifest={schema:1,version,workerTemplateSha256,bytes:allBytes,mapAssets:{gzip:gzipMap,raw:rawMap},deliveryBytes:{gzip:allBytes-size(rawMap),raw:allBytes-size(gzipMap)},assets};
  if(!template.includes('/*__SUNWARD_MANIFEST__*/null'))throw new Error('Offline worker template placeholder missing');
  await writeFile(path.join(outDir,'offline-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
  await writeFile(path.join(outDir,'sw.js'),template.replace('/*__SUNWARD_MANIFEST__*/null',JSON.stringify(manifest)));
  return manifest;
}
export function offlineBundlePlugin(runtimeFiles) {
  let config,builtFiles=[];
  return {name:'sunward-offline-manifest',apply:'build',configResolved(value){config=value;},
    generateBundle(_options,bundle){builtFiles=[...Object.keys(bundle).filter(name=>!name.endsWith('.map')),'index.html'];},
    async closeBundle(){await buildOfflineBundle({outDir:path.resolve(config.root,config.build.outDir),builtFiles,runtimeFiles,templatePath:path.resolve(config.root,'scripts/offline/service-worker.template.js')});},
  };
}
