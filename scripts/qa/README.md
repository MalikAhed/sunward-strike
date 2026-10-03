# Portable map runtime QA

`npm test` runs `tests/map-runtime.test.js`, which invokes the actual application controller/octree against the configured visual/collision GLBs and committed route fixture. It writes a fresh temporary report, checks it, then deletes only that temporary directory.

Standalone use:

`node scripts/qa/validate-map-runtime.mjs --out report.json`

Optional arguments: `--visual FILE`, `--collision FILE`, `--routes FILE`, `--project DIR`, `--source-audit FILE`. Defaults are relative to this repository and `src/map-config.js`. No Blender, browser, GPU, or display is required.

The complete fixture covers house/garage/interior portals in both directions, front-to-rear through paths, internal/external stairs, upper rooms and balconies, ±0.20m rear L-turn offset sweeps, three capsule-clear lane corridors, spawn routes, truck ramp/cargo traversal, exact ramp support rays, each irregular perimeter segment at three walk positions, and a base-ground jump test on every segment. The validator also measures GLB geometry/material/embedded-texture budgets, bounded-octree build time/heap/node/reference counts, and finite camera matrices. Floor-contact gaps lasting ≥0.5 seconds fail this gate.

Use a route fixture generated from the same accepted map frame and author revision as the assets. The fixture stores provenance hashes and coordinate calibration caveats. It does not claim surveyed original-game meters. Changing a fixture must not mask a geometry or movement defect; test intended author-approved paths and preserve source clearance requirements.

This is headless geometric/controller verification. It does not test browser input, pointer lock, touch/resize behavior, actual WebGL rendering, device performance or independent visual-reference fidelity. Those are separate release checks. The optional source audit is the separate Blender export/reimport gate; Node CI does not need Blender.

## Compressed map delivery

The visual map is read through the same magic-byte gzip/raw decoder as the application. The validator records both transfer and decoded lengths/hashes and checks the configured map against its pinned accepted decoded SHA-256. It runs from a clean checkout with only the committed gzip; it does not need a generated raw fallback.

`tests/asset-loader.test.js` covers native decompression, exact accepted bytes, already HTTP-decoded raw GLB, typed-array slices, corrupt gzip/header/chunks, direct raw fallback without a decompressor, relative query/fragment URLs, progress, cancellation, HTTP failures, real GLTF parsing and balanced LoadingManager retries. `tests/prepare-map-assets.test.js` covers clean preparation, matching reuse, divergent edit protection, non-regular paths, concurrent atomic creation and lifecycle hooks. The main retry guard is a source-level check, not a browser interaction claim.

`npm run prepare:assets` verifies/creates the generated raw copy. This also runs as `predev` and `prebuild`. Existing raw bytes must exactly match gzip output; do not delete a differing artist export just to make this check pass. The source export and committed gzip must be reconciled deliberately after asset review.
