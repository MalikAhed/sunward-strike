# Sky and cloud correction

This pass preserves the original runtime map GLB, transforms, and cloud placements. The sky uses a blue authored gradient; clouds use cream highlights/cool undersides, correct world-space normal conversion, and dithering. Exposure/tone mapping is bypassed for these display-referred atmosphere colors only.

Each cloud cluster is now one smooth signed-distance union of the five original local puffs. Its geometry is generated once and shared across 12 placements. This removes overlapping-shell shading shelves. The measured mesh budget is 3,772 triangles per cluster, 45,264 triangles across the layer, and 12 cloud draw calls. A Node measurement of one-time geometry generation was approximately 56 ms; this is not a browser or GPU benchmark.

## Reproduce the preview

Run from the repository root:

```
node docs/qa/atmosphere-review/generate-atmosphere-fixture.mjs
python3 docs/qa/atmosphere-review/render-offline.py
node --test tests/atmosphere.test.js
```

The generator writes temporary fixture data to `/tmp/sunward-atmosphere-fixture.json`; both scripts also accept an explicit fixture path. `atmosphere-offline.png` uses the actual pinned Three.js generated GLSL, cloud/sky geometry, and matrices, rendered by installed Mesa OpenGL ES 3.2 into an explicitly requested RGBA8 surfaceless EGL pbuffer. An earlier unspecified EGL color configuration selected RGB565 and caused preview-only banding; the corrected fixture verifies at least 8 bits for all four channels. Source dithering is a normal output safeguard, not a correction for that fixture issue. The image is an atmosphere-only preview, with camera (0, 3, 0), target (-30, 12, -100), 58-degree field of view, and 1365 × 768 output.

The durable regression test reads real GLB material texture flags and verifies actual renderer-generated plaster/ground shaders with low and shadowed settings, plus the sky and clouds. All 10 programs compile and link on this installed driver. A deliberate restoration of the original reserved `patch` identifier fails, establishing that the regression catches the missing-wall defect.

## Verification limits

No browser, local URL, or UI automation is used by these tests. Offline GLES compile/link and atmosphere pixels do not establish full WebGL rendering, integration with the map, reference-exact cloud fidelity, browser controls, or frame rate. Those remain live-browser checks. The original GLBs are unchanged. Standalone Blender atmosphere parity work was deferred for integration with the next map revision.
