# Exact offline delivery

The Vite build creates `dist/offline-manifest.json` and `dist/sw.js`. The manifest pins every delivered shell/code/current-art dependency by relative path, byte count and SHA-256. Its version also includes the worker-template hash, so a cache-protocol-only update never overwrites the active version's cache during installation. Historical maps are not cache dependencies. Both current gzip and raw compatibility GLBs stay available in the distribution.

`createOfflineClient` verifies gzip capability by constructing `DecompressionStream('gzip')` and registers the same-scope worker with the enumerated `?map=gzip` or `?map=raw` parameter. The map loader makes the same choice. The worker excludes the alternate map representation; unknown parameter values fail before installation. The manifest reports separate `deliveryBytes.gzip` and `deliveryBytes.raw` totals. These are exact asset-byte inventories, not claims of browser storage overhead or over-the-wire HTTP compression.

Initial play never waits for registration, installation or cache filling. Automatic saving begins after the shared asset LoadingManager settles. It first reuses HTTP-cached responses, validates every byte, and retries from the network only when a cached response is stale/mismatched. Sequential verified reads limit simultaneous large buffers and avoid deliberately downloading a second copy of the map during startup. A complete marker is written only after every selected asset has been saved. A partial install is removed on corruption/quota failure while an existing working version remains available. The UI says offline saving is unavailable/incomplete until readiness is confirmed. Cache eviction can be repaired explicitly without a new release.

Updates do not call `skipWaiting()` during installation. An explicit Update & reload request asks every same-scope open tab whether it is outside a live/paused/dead match. Missing or negative replies block activation. Another deployment path's tabs and caches are untouched. The worker retains one prior complete build. If a tab starts a match during the update handshake, controller replacement does not reload that running match; a sticky reload requirement prevents its next match from starting on mixed code. Other idle tabs receive the same reload requirement instead of an unrequested reload.

The unit suite exercises the actual generated worker in an isolated standards-object harness. It checks exact hashes, path constraints, disconnected shell/assets, gzip/raw selection, quota and corruption rollback, missing-file repair, scoped cache behavior, all-tab update gating and reload races. Browser registration, browser storage quotas/eviction, and real disconnected browser reload have not been verified in the WebGL-disabled review environment.

## v3.1 checkpoint budgets

The accepted p1r5 / vegetation-r5 / furniture-r3 / n5 checkpoint has an 8,062,943-byte map gzip, with a 17,890,616-byte decoded GLB. The map-only provisional gzip cap was explicitly revised to 8,500,000 bytes for v3.1; earlier versions retain their existing cap. This is separate from the two n5 sky atlases, totaling 3,387,735 file bytes.

The map's embedded images occupy 5,439,488 decoded RGBA bytes. The two 1536×1024 sky atlases add 12,582,912 RGBA bytes, for 18,022,400 bytes before mipmaps, runtime render targets, the rifle, and GPU-driver overhead. The current generated manifest is the authority for each final build's selected total; it includes the poster, rifle, collision, code and CSS as well as the map and sky. A later art checkpoint must refresh these measurements and hashes before publication.

## Primary API references

- [Service worker lifecycle, secure contexts and caches](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- [Checking a worker registration for updates](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/update)
- [Cache response requirements and failure behavior](https://developer.mozilla.org/en-US/docs/Web/API/Cache/addAll)
