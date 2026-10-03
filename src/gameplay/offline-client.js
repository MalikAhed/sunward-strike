export function chooseMapDelivery(environment=window) {
  if(typeof environment.DecompressionStream!=='function')return 'raw';
  try { new environment.DecompressionStream('gzip');return 'gzip'; } catch { return 'raw'; }
}

// Optional browser cache. Failure does not block loading or a local match.
// Dependency injection supports deterministic tests without registering a real
// service worker, using a browser or changing a user's storage settings.
export function createOfflineClient({baseUrl,enabled=true,onStatus=()=>{},canUpdate=()=>true,environment=window}={}) {
  const navigator=environment.navigator,serviceWorker=navigator?.serviceWorker;
  const mapDelivery=chooseMapDelivery(environment);
  let registration=null,disposed=false,starting=false,hadController=Boolean(serviceWorker?.controller),reloadRequested=false,needsReload=false;
  const watched=new Set(),watchedRegistrations=new Set(),disposers=[];
  const report=state=>{if(!disposed)onStatus(needsReload?{...state,state:'reload-required',message:'An update was installed. Reload before starting the next match.'}:state);};
  const listen=(target,type,callback)=>{target.addEventListener(type,callback);disposers.push(()=>target.removeEventListener(type,callback));};
  const status=()=>{const worker=registration?.active??serviceWorker?.controller;if(!worker)return false;worker.postMessage({type:'SUNWARD_STATUS'});return true;};
  const watch=worker=>{
    if(!worker||watched.has(worker))return;watched.add(worker);let activated=worker.state==='activated';
    const changed=()=>{
      if(worker.state==='installed')report({state:serviceWorker.controller?'update-ready':'caching'});
      if(worker.state==='activated'){activated=true;status();}
      if(worker.state==='redundant'&&!activated)report({state:'error',message:'Offline saving was interrupted. Connect and retry'});
    };
    listen(worker,'statechange',changed);
  };
  if(enabled&&serviceWorker){
    listen(serviceWorker,'message',event=>{
      const allowed=[serviceWorker.controller,registration?.active,registration?.waiting,registration?.installing].filter(Boolean);
      if(!allowed.includes(event.source)&&!allowed.some(worker=>worker.scriptURL&&worker.scriptURL===event.source?.scriptURL))return;
      if(event.data?.type==='SUNWARD_CAN_UPDATE'){
        event.source.postMessage({type:'SUNWARD_UPDATE_REPLY',requestId:event.data.requestId,safe:Boolean(canUpdate())});return;
      }
      if(event.data?.type==='SUNWARD_OFFLINE')report(event.data);
    });
    listen(serviceWorker,'controllerchange',()=>{
      const previous=hadController;hadController=Boolean(serviceWorker.controller);status();
      if(previous){
        const requested=reloadRequested;reloadRequested=false;
        if(requested&&canUpdate())environment.location.reload();
        else {needsReload=true;report({state:'reload-required',message:'An update was installed. Reload before starting the next match.'});}
      }
    });
  }
  async function start(repair=false){
    if(disposed||starting)return;
    if(!enabled){report({state:'development',message:'Offline saving is available in the production build'});return;}
    if(!serviceWorker||!environment.isSecureContext){report({state:'unsupported',message:'Offline saving is unavailable here. Connect to load the arena'});return;}
    starting=true;report({state:'caching'});
    try{
      registration=await serviceWorker.register(`${baseUrl}sw.js?map=${mapDelivery}`,{scope:baseUrl,updateViaCache:'none'});
      if(disposed)return;
      if(!watchedRegistrations.has(registration)){watchedRegistrations.add(registration);listen(registration,'updatefound',()=>watch(registration.installing));}watch(registration.installing);
      if(registration.waiting)report({state:'update-ready'});
      else if(registration.active){if(repair)registration.active.postMessage({type:'SUNWARD_REPAIR'});else status();}
      // Retry a previously failed install and check for a changed build. The
      // browser retains a working active worker if any new install fails.
      await registration.update();
    }catch(error){
      // A failed network update says nothing about an already-installed cache.
      // The trusted active worker checks its marker and every selected file;
      // its ready/error reply remains the authority, including while offline.
      if(!status())report({state:'error',message: String(error.message||error)});
    }
    finally{starting=false;}
  }
  function requestUpdate(){
    if(!canUpdate()){report({state:'update-blocked',message:'Finish the current match before updating'});return false;}
    if(!registration?.waiting){status();return false;}
    reloadRequested=true;registration.waiting.postMessage({type:'SUNWARD_ACTIVATE_IF_IDLE'});return true;
  }
  return {start,requestUpdate,status,dispose(){disposed=true;disposers.forEach(dispose=>dispose());}};
}

export function offlineStatusText(status={}) {
  const megabytes=status.bytes?` (${(status.bytes/1048576).toFixed(1)} MB)`:'';
  if(status.state==='ready')return `Saved for offline replay${megabytes}. Browser storage can still be cleared.`;
  if(status.state==='caching')return status.total?`Saving for offline replay: ${status.completed} / ${status.total} files…`:'Preparing offline replay…';
  if(status.state==='update-ready')return 'An update is downloaded. Finish any open matches, then update and reload.';
  if(status.state==='update-blocked'||status.state==='reload-required')return status.message;
  if(status.state==='development'||status.state==='unsupported')return status.message;
  return 'Offline saving is not ready. Online play still works; reconnect or free browser storage, then retry.';
}
