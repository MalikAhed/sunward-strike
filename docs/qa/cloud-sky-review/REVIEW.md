# Sky and cloud correction: independent review

Reviewed 2026-10-03 against the original art-direction collage `ca71f0ad-ff16-4cb7-8b22-5bff8edf6139.png`, the user's bug screenshot `image(20261003-161724).png`, the actual current source, and independently generated GLES preview pixels.

## Scoped result

**Approve the final sky/softness candidate for an incremental release.** The requested focused correction closes the harsh intersecting cloud-lobe seams and triangular shading shelves. This is not full art-reference acceptance or a live full-map/browser rendering pass.

Final reviewed `src/atmosphere.js` SHA-256: `f462f1e4d88a15148ee0b395decd804667d6d0ef0ebc855555467af162e5407b`

The approved wall-shader identifier correction and v2 program cache key remain present. Map GLB SHA-256 is unchanged: `5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42`.

## Observations and correction loop

1. Original screenshot: sky and clouds appear washed grey. The collage instead shows medium azure sky, broad warm-cream highlights and subtle cool cloud undersides. Blue-filtered reference pixel samples are recorded in `reference-color-samples.json`; these are descriptive observations, not a numeric matching tolerance.
2. First blue/cream candidate: palette was materially closer, but the actual offline GLES preview exposed separately intersecting oval puff undersides and conspicuous triangular shelves. This was rejected as a cloud shape/softness result despite successful compilation.
3. Focused correction: the five puff fields now form one smooth signed-distance union per cluster through Three MarchingCubes. All 12 original cluster positions and rotations remain unchanged. The fresh preview closes the hard overlap seams and geometry shelves.
4. Strong gradient banding in the first offline preview was caused by its EGL configuration permitting an RGB565 framebuffer. Channel samples had 5/6-bit quantization steps. An independently rendered RGBA8 preview removed that artifact without altering source geometry or palette. The final candidate also enables Three's standard dithering, which remains reasonable for actual display output.

## Independent checks actually performed

- Read current sky/cloud shader source, color-space conversion and tone-mapping flags. Display-referred sky/cloud colors bypass ACES exposure while retaining linear-to-output conversion; map lighting remains separately tone mapped.
- Read actual MarchingCubes field construction, normals, shared-geometry setup and placements.
- Re-ran the builder's real Three-generated source capture and offscreen GLES draw in reviewer-owned files. With the original framebuffer choice, the regenerated image was byte-identical to the builder's joined-cloud preview.
- Re-ran the same scene with explicitly requested RGBA8 channels. `atmosphere-offline-rgba8.png` shows the independently reproduced final candidate. This is atmosphere-only rendering with the actual authored Three shaders and geometry, not a browser or complete map scene.
- Re-ran `node --test tests/atmosphere.test.js`: 3 tests passed, zero skipped. Ten GLSL ES programs compiled and linked on installed Mesa OpenGL ES 3.2; the original reserved-word negative control was rejected. Real GLB base-color and normal-map flags are now included in the durable plaster fixtures.
- Confirmed 12 cloud meshes share one geometry. Geometry is 3,772 triangles per cluster, 45,264 cloud triangles in total. Cloud draw submissions decrease from 60 puff meshes to 12 joined meshes. This does not establish measured GPU frame time or a performance improvement.

## Open discrepancies and evidence gates

- Major, full-scene acceptance: no fresh target-browser/full-map screenshot has been captured. Verify restored walls, sky/cloud scale and placement, occlusion, street/player-eye compositions and console diagnostics on a WebGL2-capable browser.
- Moderate, appearance refinement: cloud contours are still simpler and more ellipsoidal than the collage's varied small cumulus lobes. The focused softness correction passes; literal reference silhouette fidelity remains open.
- Runtime: GPU timing, interactive frame rate and target-device rendering behavior remain unmeasured.
- Blender source parity: the standalone old-map presentation copy was explicitly deferred when the user prioritized classic-map structural correction. No presentation copy was written or opened. Future source parity belongs with the corrected map.

## Preserved source baseline for the upcoming structural rebuild

The original `/workspace/shared/stylized-nuketown-map/Sunward_TestSite.blend` and packaged `source-assets/map/Sunward_TestSite.blend` are byte-identical (SHA-256 `460d54859e29c59d809da2bd0497e40ac2c8684630826e89415771847055bfc6`). A separate headless read-only inspection captured 1,851 objects and 1,816 mesh datablocks, including transforms, collection/material bindings, geometry/topology/UV/normal hashes, material nodes and packed texture hashes in `original-scene-snapshot.json`. This baseline records the authored source and does not imply synchronization with the unsaved open Blender scene. Neither original file nor that open scene was modified by this review.
