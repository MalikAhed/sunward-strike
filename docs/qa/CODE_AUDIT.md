# Independent code and static QA

## Checks performed

- Opened current source assets and actual source/reference pixels; exact GLB copy hashes verified
- Opened final editable map read-only in Blender; confirmed packed images and scene v2.5 metadata
- Verified all 33 copied editable-source files (9,221,092 bytes) against source-assets manifest; zero SHA-256 or size mismatches
- Ran npm test: 10/10 pass (5 math checks and 5 bounded-collision/actual-controller checks)
- Ran production build: pass; bundled JavaScript about 634 KB / 164 KB gzip, Vite emitted its normal >500 KB chunk warning
- Ran docs/qa/verify_static.py after build: all checks pass for current exact GLBs, current version/triangle/material/clip retention, self-contained assets, relative HTML and GLB paths, and absence of localhost/CDN runtime dependencies
- Ran independent Node import and capsule-controller reproduction using exact collision GLB. Bounded tree constructs at ~0.21 seconds in this container, with 8,342 nodes / 108,408 triangle references; heap ~28 MB after build, process RSS ~101 MB. These are Node/container measurements, not browser timing or FPS
- Independent capsule traversal: street spawn floor, mint rear doorway without jumping, saffron rear doorway without jumping and solid-wall stopping pass

## Corrections verified statically

1. Initial optional assets were coupled to mandatory map readiness via Promise.all. Current loader makes map ready independently and catches optional collision/rifle failures, retaining freefly
2. Initial mandatory-map error was text-only. Current error panel supplies a Retry Load button
3. Initial pointerlock loss, blur and hidden-tab events left some input state held. Current clearInput resets movement/fire/aim/drag on those events and pointercancel
4. Initial mobile Help could not reopen after being closed. Current mobile toggle removes .hidden before toggling .mobile-open
5. Stock Octree construction exhausted about 2 GB Node heap in independent testing. Current bounded tree propagates depth/leaf limits to descendants and corrects mirrored collider triangle winding. It builds without OOM and resolves upward street-floor contact
6. Current first-person spawn was moved from intersecting west scenery to clear street X=-15

## Current findings

- Walk mode jump fails while forward is held against the mint rear solid wall. Reproduced with start [0,1.84,-31], yaw π, 120 settle frames +220 forward frames, then 30 forward+jump frames. Capsule stops correctly at Z≈-22.975, cameraY≈1.785; peak cameraY does not rise. Combined wall/floor contact yields onFloor=false. Suggested correction is a separate short downward grounded probe. Freefly is unaffected. Recorded in capsule-results.json; test_capsule.mjs exits nonzero while this finding remains
- New art reference's dense individual grass is not established by the current palette-only ground-moss overlay. A fresh render must show actual density and silhouettes before that requirement passes
- Cloud shader normal correction now uses normalMatrix inverse-transpose and converts view-normal back to world space. Static inspection accepts that correction; cloud shape/color still needs fresh visual signoff
- Controls currently offer a fixed FOV/sensitivity and a quality selector. Extended settings and persistence are not implemented. Do not imply those features exist
- Touch supports freefly movement/height plus canvas drag. First-person jump/fire/aim controls are desktop-oriented; full mobile first-person gameplay has not been established

## Evidence boundary and remaining required gates

Browser review is pending. The manager reported cloud-browser local preview access denied, so no alternate local browser route was attempted. Real desktop/touch interactions, pointerlock recovery, rendering/material/sky/grass appearance, error/retry interaction, WebGL context recovery, browser FPS and public GitHub Pages loading remain unverified. Successful static or Node tests do not count as those browser passes. Public repository creation/deployment is manager-owned and awaits required user authorization.
