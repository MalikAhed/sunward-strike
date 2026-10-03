# Map loading and compatibility

The accepted v3 map is committed as `public/assets/sunward-v3.0.glb.gz` (6,124,741 bytes). Native `DecompressionStream('gzip')` restores the original 18,167,416-byte GLB, then `GLTFLoader.parseAsync` loads that scene. Compression changes only transport; geometry, materials, textures and collision behavior are unchanged.

- Gzip SHA-256: `03990a99e4e89d0b4441808f7578dc86faf2496af2b0c7dc34937f4e7155407c`
- Decoded GLB SHA-256: `004106c1d0dd9660db9e94d003898f19d41e5341c33f27719395e00e98d6c004`

The loader inspects payload magic. If the host has already applied HTTP content decoding, raw GLB bytes pass through directly. Content type and the `.gz` filename do not determine decoding. Invalid/truncated gzip, GLB header/chunks, failed requests and parser errors are surfaced to the map error panel. They do not silently trigger another download.

## Browsers without a native decompressor

The client chooses `sunward-v3.0.glb` before fetching when `DecompressionStream` is absent. This avoids downloading both versions. `npm run dev` and `npm run build` automatically run `scripts/prepare-map-assets.mjs` first, and Vite includes both the gzip and generated raw fallback in the served/build output.

Only gzip belongs in Git. The raw fallback is ignored and generated from accepted gzip. Preparation checks the decoded hash in `src/map-config.js`, then either:

1. Reuses an existing regular raw file after an exact byte comparison, preserving its timestamp
2. Creates a complete temporary file and atomically links it into the still-absent raw destination without overwrite
3. Fails clearly if any existing raw file differs or is not a regular file

A differing raw file may contain newer authoring work. Preserve it and reconcile that change with the approved gzip/config after review; never blindly overwrite or delete it to pass a build. The generated raw file is not an editable source. Source scenes and reproducible exports remain in `source-assets/`.

Manual preparation is `npm run prepare:assets`. Tests run directly from committed gzip, so CI does not require the raw file until the build step. Direct `vite`/`vite build` commands bypass npm lifecycle hooks; use the npm scripts, or run preparation explicitly first.

## Progress, retry and static hosting

Byte progress occupies the download portion of the loading bar; a server-encoded response with an unreliable `Content-Length` uses indeterminate byte counts. Parsing and embedded resources remain tracked by Three.js LoadingManager. The bar only reaches 100% after the map has parsed and been added to the scene. Optional collision/rifle completion cannot mark the map complete.

Download and parser failures balance the manager's top-level item and expose an explicit retry button. A retry clears stale errors and progress. A single-flight guard prevents duplicate retry loads. Query strings and fragments are retained in raw fallback URLs, and map-relative resource bases continue to use Vite's relative base so a nested GitHub Pages path works.

## Verification limits

The regression suite verifies native WHATWG decompression in Node, bytes, GLTF parsing, loader accounting, source-level retry wiring and the actual collision/walk-controller gates. Offline GLES shader compilation is separate. This environment cannot create browser WebGL2; none of those checks establishes browser GPU rendering, touch/pointer-lock behavior or a measured device frame rate. The application retains its static source-preview fallback for browsers where WebGL2 cannot start.
