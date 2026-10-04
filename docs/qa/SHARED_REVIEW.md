# Current acceptance register: v3.2 map and cover-query r2

The v3.2 source/export and scoped gameplay changes are independently checked, with the limitations below. The follow-on [cover-query r2 review](COVER_QUERY_R2.md) records the query-only optimization; its map, native source, controls and gameplay rules are unchanged. Final deployment identity is established separately by the exact commit's CI and served-byte verification. [The v3.1 register](V31_REVIEW.md) and [RC1 review](RC1_REVIEW.md) remain historical evidence.

[V3.2 map hashes and initial refinement checks](v32-gameplay/verification.json) accompany the [overview](v32-gameplay/overview.png), [street](v32-gameplay/street.png) and [green](v32-gameplay/green-yard.png)/[yellow](v32-gameplay/yellow-yard.png) yard previews. That original record remains unchanged; the later query-only checks are documented separately.

## Current scope

- Preserved canonical classic-layout coordinates, house families, all312 collision proxies, furniture and traversal routes
- Local main-house siding/shingle/selected-timber detail and denser original short grass; 235,734 visual triangles,77 materials and25 images
- Bounded nearby KC tag commitment, with per-tick expiry/cancellation and unchanged health, damage, perception, aiming, scoring and navigation
- Authoritative respawn orientation and neutral input, plus a keyboard-repeat guard that prevents cleared actions being rearmed without a fresh press
- Existing TDM/KC, three bot difficulties, sprint/slide/crouch/jump, ADS/recoil/reload, hit detection, respawn, results/restart, touch bindings, original procedural audio and integrity-checked offline caching remain

## Measured checks

The final application test suite runs against the current map. It checks actual controller routes, boundary/perch safety, static cover, match rules, input/lifecycle wiring, asset decoding, cache logic and renderer-generated GLSL. Actual-main tests use a DOM model and no-op renderer; authored geometry is tested independently. These are not physical browser/device tests.

The exact native source preserves all non-lawn object state, original shader graphs and30 original packed/decoded images. The owned grass matches its accepted geometry, UVs and split normals. The corrected surface restoration record eagerly loads all image buffers and rejects a deliberate pixel mutation, rather than accepting an empty lazy-image snapshot.

Collision binary and node data remain unchanged from v3.1. Only three scene-level version/status annotations change its GLB container hash. No geometry or route threshold was changed to force a pass. New source/export/reimport views and actual normal-map/MASK color/depth/distance shader checks accompany the final asset identities.

The editable source is losslessly split for bounded transport, with an independently checked extractor and portable exporter. Eighteen packaging tests cover corruption, part ordering, path/link safety, no-overwrite behavior, exporter failure, report/output validation and gzip/raw equality. CI also extracts the actual native payload.

## Qualified results

KC collection improves in the tested paired seeds, while TDM events/snapshots remain identical. The stationary-human6v6 seed73 run changes from7 to17 confirms and from3–4 to4–13; other seeds also collect more, but first confirmation and team balance do not improve uniformly. Bots remain simple simulations, not humanlike tactical teammates.

Grounded slides end when support is lost, including eighteen retained auxiliary floor-drop continuity cases. All144 fast passages still traverse safely. The older controller/cover/perch qualifications remain documented in the v3.1 register.

## Visible and device limits

Repeated flat fan-shaped grass remains visible, and honey timber/vehicles/interiors are still less detailed than the style references. A roughness-only vehicle experiment was omitted after its matched A/B showed too little benefit; later experiments are not part of this release. Native AgX and browser lighting/color pipelines are not asserted identical.

The available cloud browser cannot create WebGL2. Actual browser GPU/frame rate, pointer capture, physical keyboard/touch feel, audio playback and disconnected-device reload remain unperformed. Static delivery, native renders, offscreen shader compilation and portable simulations are separate evidence. No perfection or exact commercial-game equivalence is claimed.
