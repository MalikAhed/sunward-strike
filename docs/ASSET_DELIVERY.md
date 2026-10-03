# Current asset delivery

The v3.1 authored map is committed as `public/assets/sunward-v3.1.glb.gz`.

- Gzip: 8,062,943 bytes; SHA-256 `dd1726021006f0f41d111942e972597979fd10e879078bd8ea5e92807cc32c6b`
- Decoded GLB: 17,890,616 bytes; SHA-256 `7f2c4ba9865cbb471c1d102a407bc76fc888f4bed679260cde314f328ea1b0b2`
- Collision: 585,308 bytes; SHA-256 `fc20bd6d76beac2bfbf2e84f21bd088bcac01782f68075c267094815b046ff0e`
- Two separate n5 atlases: 3,387,735 bytes combined; decoded RGBA 12,582,912 bytes before mipmaps
- Embedded map images: decoded RGBA 5,439,488 bytes before mipmaps

The map-only gzip cap was explicitly revised to 8,500,000 bytes for v3.1. Older version caps remain unchanged. Atlas, rifle, collision, poster, code and CSS bytes are separate; `dist/offline-manifest.json` provides the exact complete selected delivery totals for each build.

`npm run dev` and `npm run build` run `prepare:assets` first. Preparation decompresses the committed gzip and verifies its configured decoded SHA before creating `public/assets/sunward-v3.1.glb`. That raw compatibility artifact is ignored by Git and copied to `dist/` during build. Existing identical bytes are left unchanged. A divergent local file, invalid gzip, path traversal or symbolic-link target fails safely rather than overwriting edits.

The loader preserves LoadingManager accounting through decode and GLTF parsing. Modern clients request gzip. If constructing a gzip DecompressionStream is unsupported, the app requests raw directly without first downloading gzip. HTTP-decoded raw GLB is recognized by its magic bytes rather than filename. Corrupt/truncated payloads and network errors remain explicit errors with a user-triggered retry; they are not silently masked by a second asset path. All URLs are relative to the hosting base.

The offline worker uses the same per-browser map choice, exact byte/hash validation, HTTP-cache reuse and a separate versioned CacheStorage entry. It never eagerly saves both map representations for one client. A worker-protocol change also changes the cache version. Offline readiness is withheld until every selected dependency is validated and saved; failed installs preserve the previous working version. See [offline cache behavior](OFFLINE_CACHE.md).

The static fallback poster is the accepted v3.1 Blender overview. It is explicitly labeled a source preview when WebGL2 cannot initialize, and it does not imply that gameplay has been rendered or verified on that browser.
