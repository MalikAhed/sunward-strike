# Missing house walls: independent rendering review

Reviewed 2026-10-03, against the actual supplied bug screenshot `image(20261003-161724).png` and art-direction collage `ca71f0ad-ff16-4cb7-8b22-5bff8edf6139.png`.

## Result

**Approve the minimal v2 wall-shader hotfix for publication.** The source/compiler evidence identifies a shader compile failure affecting plaster wall materials. This is not fresh target-browser visual sign-off or full art-reference acceptance.

Reviewed `src/atmosphere.js` SHA-256: `030cb2c63a505ebf74532ccdc075e4d52552436ea4827232b38223bcb66e20e1`

Reviewed map GLB SHA-256: `5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42`

## Evidence

- The screenshot exposes house floor slabs, stair flight, window and door frames, roofs, and the chimney, while painted wall surfaces disappear across the foreground house and the opposite house. The disappearance is material-selective, rather than a whole-object visibility or camera clipping failure.
- The unmodified `sunward-v2.5.glb` contains 57 materials and 133 meshes. The three runtime paint-injected materials bind to seven mesh nodes with 11,836 triangles: five warm-plaster meshes (both houses, both garages, and context scenery), one sage-plaster mesh (house A), and one saffron-plaster mesh (house B). Each material is OPAQUE and double-sided; the map has no external image or buffer URIs. Normals and UV attributes exist on the affected bindings. See `material-bindings.json` for exact nodes, accessor counts, textures, and bounds.
- The previous paint fragment contained `float patch`. In [Khronos GLSL ES 3.00, section 3.8](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf), `patch` is a future-reserved keyword whose use is a compile error. Three 0.180.0's installed `WebGLProgram` emits `#version 300 es` for built-in materials, so this rule applies to the injected material program.
- Independent installed Mesa 25.0.7, surfaceless EGL 1.5 and llvmpipe compiled two GLSL ES 300 fragment reproductions. The original identifier failed with `illegal use of reserved word patch`; the corrected `artPaintVariation` compiled successfully without diagnostic. The reproducible source and full output are in `independent_keyword_compile.py` and `keyword-compiler-results.json`.
- Independently ran the builder’s full Three source-generation regression tests: 2/2 tests passed with zero skips; nine generated low/shadowed material and cloud variants compiled and linked in OpenGL ES 3.2 Mesa, while the reserved-word negative control failed. The initial fixture omitted texture flags, so that result alone was not treated as complete plaster coverage.
- Closed that gap with a separate independent generator that reads the actual GLB plaster material metadata, includes base-color textures and tangent-space normal textures, preserves double-sided flags, roughness 0.88 and normal scale 0.32, and uses the pinned real Three WebGLProgram generator. All six textured plaster low/shadowed variants compiled and linked with no errors. A textured negative control restoring `patch` failed at fragment line 2864. See `generate-textured-shaders.mjs` and `textured-program-compiler-results.json`. Texture sampling/appearance itself is not exercised by a compilation test.

## Correction review

The v2 diff renames the local paint variables to `artCell`, `artDiagonal`, and `artPaintVariation`; it leaves the variation calculation and its 0.965–1.035 brightness range unchanged. It advances `customProgramCacheKey` from v1 to v2 so the corrected material variant has a distinct cache key. It does not alter map geometry, material opacity, texture bindings, normals, positions, collision, culling, or source assets.

A paint-overlay rollback to the stock Three MeshStandardMaterial would be a valid conservative recovery if a later target-device program error remains, but current evidence supports the narrow identifier fix. No asset rebuild or wall reconstruction is warranted for this bug.

## Remaining verification

1. Load the published hotfix in the user's WebGL2-capable browser and acquire a fresh hero-view screenshot. Both house bodies and garages must show continuous opaque painted surfaces with their original openings; floors, roofs, frames, and street props must remain unchanged.
2. Check browser console or renderer shader diagnostics for compile/link failures, then inspect street/player-eye and courtyard views.
3. Whole-program compiler coverage is now independently passing for the six textured plaster variants and reserved-word negative control. Durable renderer tests should preserve the GLB texture-flag coverage. This verifies the shader source and program linkage, not actual rendered wall pixels.
4. Source/compiler validation uses the installed Mesa compiler, not the user's browser ANGLE/GPU. Fresh target-browser pixels remain unverified because the cloud browser lacks WebGL2 and browser UI access for the attempted route was rejected.
5. Palette, vegetation density, blue sky, cream clouds, and warm/cool light response versus the supplied art collage remain separate visual acceptance work. The current screenshot does not establish that those reference criteria pass.
