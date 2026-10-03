# SUNWARD STRIKE independent acceptance plan

Reviewer: paired runtime reviewer, read-only app/asset audit. Only this `docs/qa/` directory is reviewer-owned. No source scene or application changes made here.

## Current evidence and authority

- Environment is the exact authored v2.5 GLB at `stylized-nuketown-map/exports/Sunward_Environment.glb`, SHA-256 `5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42`
- Rifle is the exact revision-2 GLB at `blender-game-rifle/exports/compact_carbine.glb`, SHA-256 `13f9c861adb51e8e18556a47fe60ca33d16ae65f593b979f4e3a8c1a7ac210ce`
- Source scene/documentation and existing hero/top-down/ADS render pixels were independently inspected. These are asset evidence, not browser-runtime evidence
- New user art authority: `sunward-ref/ca71f0ad-ff16-4cb7-8b22-5bff8edf6139.png` contact sheet, actual pixels independently opened. This is shader/texture/color/feel and sky/grass authority; existing map geometry remains structural authority. It supersedes exact original palette matching
- `asset-inspection.json` and `inspect_glb.py` document direct GLB inspection
- Environment: 207,294 triangles; 133 meshes/nodes; 151 primitives; 57 materials; 11 embedded PNGs; no external URIs, cameras or lights
- Rifle: 25,225 triangles; 5 meshes; 14 nodes; 19 primitives; 10 materials; no textures; Fire, Reload, Charge and Inspect object clips
- Full map bounds are X/Z ±150 m because the authored terrain/backdrop extends beyond the 58 × 74 m playable footprint. Map must remain unit scale and at its authored origin
- Blender `(x,y,z)` maps to standard glTF `(x,z,-y)`. Mint is north/glTF negative Z; its garage is west/negative X. Saffron is positive Z; its garage is east/positive X
- Rifle muzzle is -X and up +Y in glTF. A separate placement wrapper rotated Y=-π/2 maps the muzzle to camera -Z while retaining the animated Rifle_ROOT hierarchy. Its authored dimensions are approximately 7.9655 × 3.0403 × 0.702 arbitrary art units; one uniform scale about 0.1–0.12 is an initial fit, subject to fresh visual review
- 76 environment nodes have authored negative-determinant transforms. Preserve complete loader transforms and materials; no centering, transform-zeroing or asset regeneration
- root `stylized-nuketown-map/package_manifest.json` describes older V1 sizes and is not authoritative for this integration

## Acceptance matrix

| ID | Priority | Area | Procedure and expected result | Required evidence | Current status |
|---|---|---|---|---|---|
| A01 | Blocker | Exact current assets | Compare deployed/runtime GLB hashes with the two source hashes above. Assets retain complete hierarchy/materials and map build_version 2.5 | SHA-256 and GLB inspection | Source and public copy pass; deployed check pending |
| A02 | Blocker | Real browser scene | Start app, enter Flythrough, wait for load. It renders the current map, not poster/fallback geometry, with no uncaught console errors | Fresh browser screenshot and runtime state | Pending |
| A03 | Blocker | Axes and landmark placement | Compare overhead and both house views. Mint is negative Z, west garage; saffron positive Z, east garage; two staggered east-facing vehicles, rear gardens, side routes, truck ramp and blockade stay placed as source | Fresh overhead/street/backyard views | Pending |
| A04 | Major | Material fidelity | Compare new art reference: medium-bright blue sky; puffy cream clouds with cool lower shading; warm cream/tan sunlit masonry and cooler shadow planes; muted teal/coral/yellow paint; subtle broad faceted/painterly variation; dense yellow-green edge/bed grass. Preserve source geometry and readable embedded surface detail. Avoid neon greens, featureless surfaces, blue/black interiors, or grass covering doorways/roads | Fresh daylight and material close-up views | Pending |
| A05 | Major | Gun orientation and hierarchy | Camera sees rear of rifle, muzzle points forward, +Y remains up. Loaded revision2 sight frame is actually open; muzzle is recessed. Animation does not overwrite wrapper placement/scale | Fresh hipfire, ADS and animation/rest views; hierarchy audit | Pending |
| F01 | Blocker | Fly movement | WASD or arrows move relative to yaw; ascend/descend work; sprint multiplier applies; no forced ground collision in freefly; delta-time stable; reset returns to viewable authored map | Before/after coordinates and screenshots | Pending |
| F02 | Major | Freefly bounds/recovery | Deliberately leave playable area or descend below ground; user can regain sensible view through reset. No arbitrary full-model auto-fit spawn 150 m away | Runtime test | Pending |
| F03 | Major | Input isolation | Movement/shooting/zoom shortcuts do not activate while typing or changing controls/settings; UI clicks do not fire or force pointerlock; movement keys clear on blur/hide/unlock | Input audit and runtime checks | Pending |
| P01 | Blocker | Pointer lock | A deliberate start/canvas gesture locks; mouse turns view; Escape unlocks and displays usable resume overlay; resume click reacquires; lock error/rejection shows actionable fallback, not frozen blank screen | Desktop browser interaction | Pending |
| P02 | Major | Focus/visibility | Hold movement then switch focus or hide tab; return without stuck movement. Escape on locked gameplay does not immediately relock. Fullscreen failure remains recoverable | Desktop interaction and event audit | Static clearInput correction accepted; browser pending |
| T01 | Major | Touch controls | At phone viewport, movement stick/buttons and look drag are visible and usable without pointerlock; two independent touches move/look together; up/down/reset accessible; release/cancel clears state | Mobile/emulated touch gestures; screenshot | Pending |
| T02 | Major | Responsive UI | Check 360×640 and landscape 844×390. Menus/settings fit or scroll; safe area respected; no horizontal overflow; important buttons remain reachable; canvas resizes with correct aspect | Fresh screenshots | Pending |
| S01 | Major | Settings | FOV, sensitivity/invert, speed/quality/audio controls if present update the actual runtime; preserve valid values on reload; invalid/corrupt localStorage does not crash; ranges clamp | Runtime/state audit | Pending |
| L01 | Blocker | Slow loading | Empty cache/slower network: visible progress/phase, controls disabled until map ready, error/loading cannot be mistaken for playable. Progress does not show 100% while dependent assets still pending | Throttled load or controlled loader test | Pending |
| L02 | Major | Load error/retry | Simulate missing map, missing optional rifle, WebGL unavailable, context lost. Show clear state and working retry/fallback for map failure; optional gun failure does not prevent map flythrough | Controlled tests and code audit | Static retry/independent-load correction accepted; browser/context-loss pending |
| D01 | Blocker | Relative static deployment | Production build loads under `/sunward-strike/` or arbitrary subpath. JS/CSS/GLB/poster URLs stay base-relative; no localhost/API/build-source dependency, history fallback assumption or CDN runtime import | Build audit, live Pages load | Production static paths pass; live Pages pending |
| D02 | Blocker | Public delivery | Verify actual GitHub repository exists with source/history, Pages deployment succeeds, URL opens current app and loads current GLBs | Authorized GitHub/Pages evidence | Manager-owned; pending |
| G01 | Major | Honest mode scope | Flythrough works now. Future offline TDM/KC/bots are clearly future planned work unless functioning; no claim of multiplayer/online service | UI/documentation audit | Pending |

## Evidence boundaries

Static analysis and prior Blender/Godot checks cannot prove browser controls, responsiveness, frame rate, rendered material fidelity, or public hosting success. No browser runtime pass is claimed until the corresponding fresh runtime evidence is recorded. Input/UI owner is the manager unless a designated review window is granted.

## Visual reference sheet

Current source render checks inspected `renders/01_hero.jpg`, `renders/05_topdown.jpg`, and rifle `exports/ads_view.png`. Important large-scale landmarks: paired mint/saffron two-story houses, opposite-side garages, truck and bus staggered through the street, exterior stairs behind both houses, small rear-yard sheds and rectangular planters, perimeter fencing, west pink/car landmark, east white barriers. Original landscape/paving proportions and structural foliage locations remain authoritative. New shader/color/texture/sky/grass treatment follows the supplied contact sheet. The image is a style reference, not permission to replace map geometry or add copied game logos. Web engine lighting may differ, but visible warm-sun/cool-shade hue hierarchy, material detail and cream clouds must remain readable. Exact visual equivalence is not claimed.

## Recommended browser review sequence

1. Cold load under published-style subpath; capture entry menu and load state
2. Enter Flythrough; capture street and overhead landmark views; traverse/reposition into a house, rear yard and upper floor
3. Test W/A/S/D, ascend/descend, sprint, reset; capture coordinate or view change
4. Escape/resume, focus loss, movement-release cleanup, settings then resume
5. Hipfire/ADS and one-shot animations/rest pose if those controls are implemented
6. Phone portrait and landscape menus, two-finger move/look, reset and release/cancel
7. Controlled error/retry and optional rifle failure; inspect production paths
8. Load actual Pages URL and record repository/deployment evidence

## New art-reference acceptance notes

The latest contact sheet mixes sunny exterior scenes and warm interior scenes. Outdoor sky is clear medium blue with chunky soft cream cloud silhouettes; lower cloud shading is lavender/cool rather than uniformly white. Sunlit plaster, posts and vehicle trim are warm cream/tan, with visible angular tonal variation and restrained edge weathering. Teal and coral paints and the yellow bus are saturated enough to read without becoming fluorescent. Grass is dense and varied yellow-green, with individual tufts, taller leaves at borders and dark green shadows. Interiors are still readable in warm reflected/lamplight. These are observables to compare against fresh browser frames, not claims that the current viewer has already met them.
