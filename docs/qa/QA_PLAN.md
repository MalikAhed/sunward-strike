# SUNWARD STRIKE independent QA plan

Updated 2026-10-04 for the v3.2 offline arena. The current accepted scopes and exact hashes are in the acceptance register; earlier RC1 evidence remains historical.

## Current contract

The V3 map replaces the old generated rectangular layout with reference-traced classic Nuketown proportions. Original source is retained as a protected baseline, not as current structural authority. [Structural brief](../MAP_STRUCTURE_PLAN.md) defines primary sources, coordinate conventions, uncertainty and family corrections. [Acceptance register](SHARED_REVIEW.md) records exact passed revisions and open gates.

- Canonical frame: `layout-r3-family-corrected`, one uniform image-to-world scale
- Green/gable family: lower/south/bus-side; sunny-yellow shed-roof house: upper/north/truck-side
- 23-vertex playable outline, round central court, sole road-mouth extension, near-parallel staggered bus/truck
- Prototype scale from a presumed 10.5m bus; no claim of original authenticated meters
- Blender `(x,y,z)` → Three/glTF `(x,z,-y)`; do not apply a second family/root transform
- Current assets/configuration are named in `src/map-config.js`; final source/export manifest and deployed digests must agree
- Rifle revision2 and original Fire/Reload/Charge/Inspect hierarchy remain preserved
- Appearance authority: latest five in-map images emphasize distant clouds/mountains, vivid lawns, honey timber and turquoise/cream plus sunny-yellow siding; preceding sky/tree/object references support detail. None authorizes replacing measured structure

## Final saved-source and export gates

1. Freeze immutable module/config SHA manifest. Independently open that exact integrated `.blend` and compare overhead, exit-side street and both rear views with primary structure pixels.
2. Verify correct house families, yaws, asymmetric garages and component proportions; no second-floor inset buildings or surviving old walls.
3. Verify every source/proxy transform, outward closed volume, slope normal, floor support and portal aperture. Retain detailed roadwork only and invisible outline clip.
4. Preserve ≥1.1m usable stair/landing/rail clearance, human-height door passage and safe first-step rises. Test source geometry separately from point-contact traversal.
5. Export visual/collision GLBs, excluding proxies from visual exports. Re-import into a clean scene; verify materials, packed images, normals, units, transforms and bounds survive.
6. Measure visual triangles, transfer bytes, primitives/materials and octree nodes/references. Geometry/transfer budgets are 400,000 visual map triangles and 32MB map GLB; GPU time needs actual target rendering.
7. Package editable final source plus relative rebuild/export CLI; retain previous source, omit reference screenshot pixels and temporary caches.

## Actual controller gates

- Full authored route set: three lanes, spawns, all front/rear/garage portals, both floors, both exterior and interior stairs, balcony turns, vehicle gaps, truck ramp/cargo floor and furnished-room approaches
- Continuous walk/sprint stair contact at 30/60Hz, including first lips and top transitions. Endpoint-only success cannot hide unrequested launches
- All 23 boundary segments: three walking samples each and one jump check each
- Collision at all six faces for mirrored/unmirrored geometry, preserving bounded octree complexity
- Grounded velocity reset must preserve explicit jump, ramp jump and wall-corner jump; a one-meter ledge remains a real fall
- Preserve original failure logs. Driver precision can be tightened; arrival gates must not be widened and goal coordinates must not be teleported

## App source and deployment gates

- Configured asset names/spawns/outline agree with the final export; all prescribed viewpoints have finite matrices and sensible targets
- Untouched overview fits on portrait/wide presets and wide→portrait resize; manually flown/orbited cameras are not reset by resizing
- Orbit→fly maintains yaw/pitch continuity; walk reset uses the canonical spawn
- Input state clears on blur, hide, pointer cancellation and unlock; form inputs isolate shortcuts
- Load/error/retry, optional collision/rifle failures and truthful WebGL2 fallback stay recoverable
- Run lint, unit/config/shader/controller tests and production subpath build
- Verify actual public commit, exact-SHA CI/Pages deployment, served application/worker/manifest/assets, gzip/raw decoding and selected offline-cache hashes after publication. Passing local tests alone does not establish a deployed release.

## Appearance comparison gates

- Sky: distant layered banks behind roofs, rich azure, warm cream clouds/cool lavender-blue underforms, irregular painterly scallops and thin broken wisps; peach/lavender mountain horizon
- Trees: full rounded broadleaf crowns, layered scalloped leaf masses, golden-lime light and deep teal shade; warm readable branch/trunk planes
- Grass: bright yellow-green lawn texture across open centers and denser border clusters, with clear circulation rather than only edge decoration
- Materials: warm cream masonry, turquoise/cream and sunny-yellow siding, honey timber, golden bus, ivory/red truck and restrained faceted/painterly finish variation
- Interiors: warm mustard/wood/geometric-rug palette, readable kitchen/garage dressing and lighting without obstructing routes
- Compare fresh integrated renders against the original four references; separate geometry, illumination and color-management differences. No whole-scene match follows solely from a compiler pass or isolated close-up

## Live browser/device sequence, still open

Cloud Chromium cannot create WebGL2 because graphics are disabled. Offline GLSL compilation, Blender renders and actual-controller Node simulations are valid narrower evidence, not live browser passes.

When an authorized WebGL2-capable browser is available:

1. Cold-load the deployed subpath; verify progress, actual map and console state
2. Compare street/overhead/backyard/interior views and hipfire/ADS/rest animations
3. Exercise freefly/walk/orbit, reset, yaw-relative movement, sprint, stairs and vehicle ramps
4. Test capture/Escape/resume, blur/hide cleanup, fullscreen and native selectors
5. Check 320×568, 390×844, 568×320, 844×390, 1024×768 and desktop, including safe insets/help/ammo/fallback and two-touch move/look
6. Test missing-map retry, optional asset failures and context loss
7. Measure actual loading/GPU frame time on target devices and record deployed digests

Touch and keyboard/mouse mappings now cover match movement, look, firing, aim, sprint, jump, slide, crouch and reload. Combat and local TDM/Kill Confirmed bots are implemented and portably tested; online multiplayer is not implemented. Actual device input and offline replay remain the browser gates above.

## Offline-match regression gates

- Both modes and all three difficulties on exact final map/cover geometry; no hidden-target tracking or difficulty-based health/damage advantage
- True finite-triangle capsule contacts, original failing stair-edge replay, reachable furniture/vehicle jumps, ceiling recovery and bounded slide transitions
- Separate opaque-visual cover rays with open windows retained and decorative foliage excluded
- Deterministic render-cadence replay, respawn/protection, damage/ammo/reload/ADS/recoil, tags, score/time endings and restart
- Actual composed main logic with OS autorepeat, short taps, mixed pointer/touch input, pause/focus/death and explorer restoration
- Integrity-checked gzip/raw cache selection, quota/incomplete-cache failures, existing-ready status during offline update checks, and idle-tab update guards
- Audio gesture gating, bounded voices, mute/pause cleanup and optional unsupported-audio fallback
