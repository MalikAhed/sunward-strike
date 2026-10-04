# Current asset delivery

The v3.2 authored map is committed as `public/assets/sunward-v3.2.glb.gz`.

- Gzip: 6,984,537 bytes; SHA-256 `396c46f365c6e55130128cec024ac2acedae947655785d671384c3d527a01d0c`
- Decoded GLB: 19,934,724 bytes; SHA-256 `0c7e6578c0975900dcfbdfdae7d2f20f017a690ae1ea87946310361aba8342aa`
- Collision: 585,316 bytes; SHA-256 `1065c56be640845db92fb96293ddc60667eaccd1904c5272054e3a3111735949`
- Two separate n5 atlases: 3,387,735 bytes combined; decoded RGBA 12,582,912 bytes before mipmaps
- Embedded map images: 25 images, decoded RGBA 6,881,280 bytes before mipmaps; 9,175,012 bytes including complete mip chains
- Map geometry: 235,734 triangles, 123 meshes, 138 primitives, 77 materials; 18,054,030 referenced vertex/index bytes

Compared with v3.1, the gzip is smaller while the raw geometry/texture allocation is larger. Neither result establishes GPU speed or device frame rate. The collision binary and nodes are unchanged; its new container hash reflects only three approved version/status annotations.

The map-only gzip cap remains 8,500,000 bytes, as in v3.1. The 80-material cap is unchanged; the image cap explicitly increases from 24 to 25 for one original 512×256 lawn atlas. Version-specific contracts live in `src/map-budgets.js`, so older caps remain unchanged. Atlas, rifle, collision, poster, code and CSS bytes are separate; `dist/offline-manifest.json` provides the exact complete selected delivery totals for each build.

`npm run dev` and `npm run build` run `prepare:assets` first. Preparation decompresses the committed gzip and verifies its configured decoded SHA before creating `public/assets/sunward-v3.2.glb`. That raw compatibility artifact is ignored by Git and copied to `dist/` during build. Existing identical bytes are left unchanged. A divergent local file, invalid gzip, path traversal or symbolic-link target fails safely rather than overwriting edits.

The loader preserves LoadingManager accounting through decode and GLTF parsing. Modern clients request gzip. If constructing a gzip DecompressionStream is unsupported, the app requests raw directly without first downloading gzip. HTTP-decoded raw GLB is recognized by its magic bytes rather than filename. Corrupt/truncated payloads and network errors remain explicit errors with a user-triggered retry; they are not silently masked by a second asset path. All URLs are relative to the hosting base.

The offline worker uses the same per-browser map choice, exact byte/hash validation, HTTP-cache reuse and a separate versioned CacheStorage entry. It never eagerly saves both map representations for one client. A worker-protocol change also changes the cache version. Offline readiness is withheld until every selected dependency is validated and saved; failed installs preserve the previous working version. See [offline cache behavior](OFFLINE_CACHE.md).

The static fallback poster is the accepted v3.2 Blender overview. It is explicitly labeled a source preview when WebGL2 cannot initialize, and it does not imply that gameplay has been rendered or verified on that browser.
