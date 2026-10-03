# Independent code and static QA

## Checks performed

- Opened current source assets and actual source/reference pixels; exact GLB copy hashes verified
- Opened final editable map read-only in Blender; confirmed packed images and scene v2.5 metadata
- Verified all 33 copied editable-source files (9,221,092 bytes) against source-assets manifest; zero SHA-256 or size mismatches
- Ran npm test: 11/11 pass (5 math checks and 6 bounded-collision/actual-controller checks)
- Ran production build: pass; bundled JavaScript about 640 KB / 166 KB gzip, Vite emitted its normal >500 KB chunk warning
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
7. Confirmed wall-contact jump suppression was corrected with a short downward floor-contact ray in actual WalkController. Independent wall+jump retest passes with onFloor=true at wall and camera rising from ~1.792 to ~2.596 (+0.805 m); both doorway and solid-wall regressions retain pass

## Current findings

- The earlier wall-contact jump defect is closed. Current `test_capsule.mjs` imports actual WalkController and all five independent scenarios pass. Node/controller checks still do not replace a browser playtest
- New art reference's dense individual grass is not established by the current palette-only ground-moss overlay. A fresh render must show actual density and silhouettes before that requirement passes
- Cloud shader normal correction now uses normalMatrix inverse-transpose and converts view-normal back to world space. Static inspection accepts that correction; cloud shape/color still needs fresh visual signoff
- Controls currently offer a fixed FOV/sensitivity and a quality selector. Extended settings and persistence are not implemented. Do not imply those features exist
- Touch supports freefly movement/height plus canvas drag. First-person jump/fire/aim controls are desktop-oriented; full mobile first-person gameplay has not been established

## Public delivery evidence

Manager-reported verified public delivery:

- Public repository: https://github.com/malikahed/sunward-strike
- Remote commit prefix `37acccc` verified after public-repository approval
- GitHub Actions run `37135659835`: build and deploy succeeded
- Pages URL: https://malikahed.github.io/sunward-strike/
- Actual public HTML, JavaScript and CSS requests succeeded
- All three public GLBs returned HTTP 200 and exactly matched the source SHA-256 values documented in ASSET_PROVENANCE.md

These public checks were performed by the manager and reported to this independent reviewer. They establish repository/deployment and asset-delivery success, not visual/gameplay correctness. A later final QA/fallback commit must be checked against its own remote SHA and deployment run before those statements are extended to it.

## Evidence boundary and remaining required gates

The manager attempted the actual public Pages app in cloud Chromium. That browser logged `GL_VENDOR/GL_RENDERER: Disabled`, `BindToCurrentSequence failed` and WebGL2 renderer creation failure. The verified test environment therefore cannot render the 3D scene. This does not establish how the app renders on a different browser with working WebGL2. The same desktop/browser instance offers no legitimate alternate route, and no restriction bypass was attempted.

The public page and exact GLB delivery are verified, but live map/rifle appearance, freefly movement, pointerlock Escape/resume, touch gestures, responsive layout, settings interaction, slow-load/error-retry interactions, WebGL context-loss recovery and browser FPS remain unverified. No appearance acceptance or working-runtime-control claim is made from static, Node or public HTTP success. The clearer non-WebGL fallback is being completed by the builder and needs its own actual failure-path check. Dense individual yellow-green grass remains an open art requirement beyond the current source coverage/palette overlay.

## Precise future browser gates

On an authorized browser with working WebGL2:

1. Confirm real v2.5 geometry renders, then compare street/overhead/rear-yard and rifle hipfire/ADS views against structural and current art authorities
2. Verify freefly move/look/height/sprint/reset, then Escape/unlock, focus loss and explicit reacquisition without stuck movement/fire/ADS
3. Exercise first-person floors, both rear doors, ramps, boundary stops and held-forward wall+jump after the grounded-contact correction
4. Check portrait 360×640 and landscape 844×390 touch move/look/height/reset, cancel/release cleanup and Help close/reopen
5. Change quality and viewpoints; exercise cold/slow load, mandatory-map retry and optional-rifle/collision failures
6. Compare bright-blue sky, cream/cloud undersides, warm/cool facade detail and actual grass silhouettes/density. Do not treat recoloring a flat lawn as dense tuft coverage
7. Record measured browser frame time/FPS and errors; static triangle/draw-call budgets and Node timings are not browser benchmarks
8. Repeat public HTML/bundle/GLB delivery checks for the final deployed commit SHA
