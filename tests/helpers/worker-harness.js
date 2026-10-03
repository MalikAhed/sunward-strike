import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
export function makeWorker(script,{files,existing=new Map(),quota=false,busy=false,scope='https://example.test/subpath/',delivery='gzip'}={}){
 const handlers=new Map(),messages=[],fetches=[],storage=existing;let network=true,skips=0,claimed=0;
 const clients=[];
 const client={id:'client-1',url:scope,postMessage(message){messages.push(message);if(message.type==='SUNWARD_CAN_UPDATE')dispatchMessage({type:'SUNWARD_UPDATE_REPLY',requestId:message.requestId,safe:!busy});}};clients.push(client);
 const cacheAPI={async keys(){return [...storage.keys()];},async delete(name){return storage.delete(name);},async open(name){
  if(!storage.has(name))storage.set(name,new Map());const cache=storage.get(name);
  return {async match(url){return cache.get(typeof url==='string'?url:url.url)?.clone();},async put(url,response){if(quota)throw new Error('Quota exceeded');cache.set(typeof url==='string'?url:url.url,response.clone());}};
 }};
 const self={location:{href:scope+'sw.js?map='+delivery},registration:{scope,active:null},clients:{async matchAll(){return clients;},async claim(){claimed++;}},async skipWaiting(){skips++;},addEventListener(type,handler){handlers.set(type,handler);}};
 vm.runInNewContext(script,{self,caches:cacheAPI,crypto:webcrypto,fetch:async request=>{
  fetches.push({url:request.url,cache:request.cache});if(!network)throw new Error('offline');const entry=files.get(request.url),value=typeof entry==='function'?entry(request):entry;if(value===undefined)return new Response('missing',{status:404});return new Response(value);
 },Request,Response,URL,Uint8Array,Map,Set,Date,setTimeout,clearTimeout});
 function event(type,detail={}){const pending=[];const data={...detail,waitUntil(promise){pending.push(promise);}};handlers.get(type)?.(data);return Promise.all(pending);}
 function dispatchMessage(data,source=client){return event('message',{data,source});}
 return {storage,messages,fetches,cacheAPI,self,client,addClient({id,url=scope,safe=true,reply=true}){const extra={id,url,postMessage(message){if(reply&&message.type==='SUNWARD_CAN_UPDATE')dispatchMessage({type:'SUNWARD_UPDATE_REPLY',requestId:message.requestId,safe},extra);}};clients.push(extra);return extra;},get skips(){return skips;},get claimed(){return claimed;},offline(){network=false;},online(){network=true;},
  install:()=>event('install'),activate:()=>event('activate'),message:dispatchMessage,
  async request(url,mode='cors',method='GET'){let response=null;handlers.get('fetch')?.({request:{url,mode,method},respondWith(promise){response=promise;}});return response?await response:null;},
 };
}
