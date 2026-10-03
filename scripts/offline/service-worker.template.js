/* Generated per build. Do not hand edit the delivered worker. */
const MANIFEST = /*__SUNWARD_MANIFEST__*/null;
const SCOPE = self.registration.scope;
const PREFIX = `sunward-offline:${new URL(SCOPE).pathname}:`;
const MAP_DELIVERY = new URL(self.location.href).searchParams.get('map');
if (!['gzip', 'raw'].includes(MAP_DELIVERY)) throw new Error('Explicit gzip or raw map delivery is required');
const CACHE = PREFIX + MANIFEST.version + ':' + MAP_DELIVERY;
const MARKER = new URL('__sunward_offline_complete__', SCOPE).href;
const alternateMap = MANIFEST.mapAssets[MAP_DELIVERY === 'gzip' ? 'raw' : 'gzip'];
const ASSETS = new Map(MANIFEST.assets.filter(asset => asset.url !== alternateMap).map(asset => [new URL(asset.url, SCOPE).href, asset]));
const pendingUpdates = new Map();
const hex = bytes => [...new Uint8Array(bytes)].map(value => value.toString(16).padStart(2, '0')).join('');
async function tell(message, target) {
  const data = {type: 'SUNWARD_OFFLINE', version: MANIFEST.version, bytes: MANIFEST.deliveryBytes[MAP_DELIVERY], mapDelivery: MAP_DELIVERY, ...message};
  if (target) { try { target.postMessage(data); } catch { /* tab closed */ } return; }
  for (const client of await self.clients.matchAll({type: 'window', includeUncontrolled: true}))
    if (client.url.startsWith(SCOPE)) try { client.postMessage(data); } catch { /* tab closed */ }
}
async function verifiedFetch(url, asset) {
  // Reuse the browser's completed app load instead of downloading the map a
  // second time. Cached bytes are never trusted without exact build integrity.
  for (const policy of ['force-cache', 'reload']) {
    const response = await fetch(new Request(url, {cache: policy, credentials: 'same-origin'}));
    if (response.ok && response.type !== 'opaque') {
      const buffer = await response.clone().arrayBuffer();
      if (buffer.byteLength === asset.bytes && hex(await crypto.subtle.digest('SHA-256', buffer)) === asset.sha256) return response;
    }
    if (policy === 'reload') throw new Error(`Build changed or unavailable while saving ${asset.url}; retry when the update is complete`);
  }
}
async function complete(cache) {
  if (!await cache.match(MARKER)) return false;
  for (const url of ASSETS.keys()) if (!await cache.match(url)) return false;
  return true;
}
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      let completed = 0;
      for (const [url, asset] of ASSETS) {
        // Sequential downloads keep only one large asset buffer alive at once.
        await cache.put(url, await verifiedFetch(url, asset)); completed++;
        await tell({state: 'caching', completed, total: ASSETS.size});
      }
      await cache.put(MARKER, new Response(JSON.stringify({version: MANIFEST.version, created: Date.now()}), {headers: {'Content-Type': 'application/json'}}));
      await tell({state: self.registration.active ? 'update-ready' : 'ready'});
      // An existing game is never replaced just because a new build arrived.
    } catch (error) {
      await caches.delete(CACHE);
      await tell({state: 'error', message: String(error.message || error)});
      throw error;
    }
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    if (!await complete(cache)) { await tell({state: 'error', message: 'Offline cache is incomplete; connect and retry'}); return; }
    // Retain one previous complete build for tabs finishing an older session.
    // Never remove another app's cache or another deployment's path scope.
    const old = [];
    for (const name of await caches.keys()) {
      if (!name.startsWith(PREFIX) || name === CACHE) continue;
      const previous = await caches.open(name), marker = await previous.match(MARKER);
      const created = marker ? (await marker.json()).created ?? 0 : 0;
      old.push({name, created});
    }
    old.sort((a, b) => b.created - a.created);
    for (const entry of old.slice(1)) await caches.delete(entry.name);
    await self.clients.claim(); await tell({state: 'ready'});
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== new URL(SCOPE).origin) return;
  url.hash = ''; url.search = '';
  if (request.mode === 'navigate' && (url.href === SCOPE || url.href === new URL('index.html', SCOPE).href)) url.href = new URL('index.html', SCOPE).href;
  const asset = ASSETS.get(url.href);
  if (!asset) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE), cached = await cache.match(url.href);
    if (cached) return cached;
    try {
      const response = await verifiedFetch(url.href, asset);
      try { await cache.put(url.href, response.clone()); } catch { await tell({state: 'error', message: 'Storage is full; online play still works'}); }
      return response;
    } catch {
      await tell({state: 'error', message: 'An offline file is missing. Reconnect to repair the cache'});
      return new Response('SUNWARD offline file unavailable. Reconnect and reload.', {status: 503, headers: {'Content-Type': 'text/plain'}});
    }
  })());
});
async function activateWhenIdle(source) {
  const clients = (await self.clients.matchAll({type: 'window', includeUncontrolled: true})).filter(client => client.url.startsWith(SCOPE));
  if (!clients.length) return self.skipWaiting();
  const requestId = `${MANIFEST.version}:${Date.now()}`;
  const ready = await new Promise(resolve => {
    const pending = {ids: new Set(clients.map(client => client.id)), resolve, safe: true};
    pendingUpdates.set(requestId, pending);
    pending.timer = setTimeout(() => { pendingUpdates.delete(requestId); resolve(false); }, 3000);
    for (const client of clients) client.postMessage({type: 'SUNWARD_CAN_UPDATE', requestId});
  });
  if (ready) await self.skipWaiting();
  else await tell({state: 'update-blocked', message: 'Finish matches in every Sunward tab before updating'}, source);
}
self.addEventListener('message', event => {
  const data = event.data;
  if (!data || !event.source?.url?.startsWith(SCOPE)) return;
  if (data.type === 'SUNWARD_UPDATE_REPLY') {
    const pending = pendingUpdates.get(data.requestId);
    if (!pending || !pending.ids.delete(event.source.id)) return;
    pending.safe = pending.safe && data.safe === true;
    if (!pending.ids.size) { clearTimeout(pending.timer); pendingUpdates.delete(data.requestId); pending.resolve(pending.safe); }
  }
  if (data.type === 'SUNWARD_STATUS') event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await tell({state: await complete(cache) ? 'ready' : 'error', message: 'Offline cache is incomplete; reconnect and retry'}, event.source);
  })());
  if (data.type === 'SUNWARD_REPAIR') event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      let completed = 0;
      for (const [url, asset] of ASSETS) {
        if (!await cache.match(url)) await cache.put(url, await verifiedFetch(url, asset));
        completed++; await tell({state: 'caching', completed, total: ASSETS.size}, event.source);
      }
      await cache.put(MARKER, new Response(JSON.stringify({version: MANIFEST.version, created: Date.now()}), {headers: {'Content-Type': 'application/json'}}));
      await tell({state: 'ready'}, event.source);
    } catch (error) { await tell({state: 'error', message: String(error.message || error)}, event.source); }
  })());
  if (data.type === 'SUNWARD_ACTIVATE_IF_IDLE') event.waitUntil(activateWhenIdle(event.source));
});
