# Current asset delivery

The v3.3 authored map is committed as `public/assets/sunward-v3.3.glb.gz`.

- Gzip: 6,961,481 bytes; SHA-256 `5863c77258fff6c35a26000d89f8dc82b37995442276d47017492b97bec3d5a1`
- Decoded GLB: 19,913,252 bytes; SHA-256 `d0a1e19862b9d0a614dd484e8686b052bbcdeb796622a63f272ca343e1081a7b`
- Collision: 585,320 bytes; SHA-256 `a00bb2353fd639ca09f4783f969f55bfe3bae3996f9e7f7240c4f0c0b6655f75`
- Two separate n5 atlases: 3,387,735 bytes combined; decoded RGBA 12,582,912 bytes before mipmaps
- Embedded map images: 25 images, decoded RGBA 6,881,280 bytes before mipmaps; 9,175,012 bytes including complete mip chains
- Map geometry: 235,734 triangles, 123 meshes, 138 primitives, 77 materials

Compared with v3.2, the map gzip is 23,056 bytes smaller. The timber substitution retains the same decoded texture allocation; the wordmark correction adds three deduplicated export vertices, with no triangle/material/image growth. Neither result establishes GPU speed or device frame rate. The collision binary and nodes are unchanged; its new container hash reflects only two changed version annotations.

Every v3.2 budget is unchanged: the map-only gzip cap remains 8,500,000 bytes, the material cap is 80 and the image cap is 25. Version-specific contracts live in `src/map-budgets.js`, so older caps remain unchanged. Atlas, rifle, collision, poster, code and CSS bytes are separate; `dist/offline-manifest.json` provides the exact complete selected delivery totals for each build.

`npm run dev` and `npm run build` run `prepare:assets` first. Preparation decompresses the committed gzip and verifies its configured decoded SHA before creating `public/assets/sunward-v3.3.glb`. That raw compatibility artifact is ignored by Git and copied to `dist/` during build. Existing identical bytes are left unchanged. A divergent local file, invalid gzip, path traversal or symbolic-link target fails safely rather than overwriting edits.

The loader preserves LoadingManager accounting through decode and GLTF parsing. Modern clients request gzip. If constructing a gzip DecompressionStream is unsupported, the app requests raw directly without first downloading gzip. HTTP-decoded raw GLB is recognized by its magic bytes rather than filename. Corrupt/truncated payloads and network errors remain explicit errors with a user-triggered retry; they are not silently masked by a second asset path. All URLs are relative to the hosting base.

The offline worker uses the same per-browser map choice, exact byte/hash validation, HTTP-cache reuse and a separate versioned CacheStorage entry. It never eagerly saves both map representations for one client. A worker-protocol change also changes the cache version. Offline readiness is withheld until every selected dependency is validated and saved; failed installs preserve the previous working version. See [offline cache behavior](OFFLINE_CACHE.md).

The static fallback poster is the accepted v3.3 Blender overview. It is explicitly labeled a source preview when WebGL2 cannot initialize, and it does not imply that gameplay has been rendered or verified on that browser.
