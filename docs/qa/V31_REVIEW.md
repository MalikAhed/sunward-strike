# Current acceptance register: v3.1 offline arena

The integrated source/export, gameplay core, controller and opaque-cover scopes are accepted with the limits below. This record does not certify actual browser/device behavior or exact reference identity. [Exact hashes and measured gates](v31-gameplay/verification.json) accompany the [overview](v31-gameplay/overview.png), [street](v31-gameplay/street.png) and both [green](v31-gameplay/green-yard.png) / [yellow](v31-gameplay/yellow-yard.png) yard previews. The prior [RC1 review](RC1_REVIEW.md) is historical.

## Closed portable gates

- Exact native source, protected structure, all original collision geometry, and evaluated containment of all16 added furniture proxies
- Clean source/export/reimport and matching street/interior renders; baked materials remain untinted and all161 material/sky assertions and156 actual GLES program variants pass
-78 walking and78 sprinting routes,69 perimeter samples per pace,23 ground jumps, and900 elevated no-escape attempts from50 reachable anchors, including22 proven furniture/vehicle perches
- True capsule/finite-triangle contacts fix a reproduced stair-edge launch without a displacement clamp; the old stock-solver negative control still demonstrates the original defect
-3,905 actual opaque-visual cover rays agree, preserving open windows while blocking rails, frames, bark and solid stair details; decorative grass/leaf cutouts stay out of hard cover
- Both modes at all three difficulties on the real final map, deterministic30/60/144Hz replay, and a full300-second6v6 stress round
- Actual composed application logic against a DOM model/no-op renderer, including start/retry, held/mixed input, camera ownership, pause, death/respawn, results/restart, explorer restoration, bounded audio and exact-version offline-cache logic
- Full aggregate tests, lint and production build; exact count is in the verification JSON

## Qualified results retained

Grounded slides intentionally end when support is lost. Eighteen auxiliary “remain sliding until the endpoint” probes therefore failed across exterior floor drops, while every passage remained traversable and dedicated drop-safety tests passed. No route or geometry threshold was relaxed to force continuity.

A one-minute6v6 Kill Confirmed probe produced a valid0–0 draw with denials but no confirms. The full300-second same-seed round produced96 deaths,7 confirms and75 denials, ending3–4 without physical anomalies. This is denial-heavy initial bot behavior, not broken scoring or an assertion of humanlike tactics. Eleven additional perch searches did not establish reachability and are not claimed inaccessible.

The earlier generic lamp-box audit compared a rotated box world AABB with a round lamp world AABB. A narrow qualified audit instead tests every evaluated visual vertex in proxy-local bounds at0.00001m tolerance, while separately checking the exact frozen box geometry. No proxy was enlarged to hide a failure.

## Open browser and appearance checks

The cloud browser cannot create WebGL2. Actual browser rendering, pointer capture, mouse/touch feel, real audio, disconnected-device cache behavior, mobile alpha overdraw and GPU frame time remain unperformed. CPU simulation, offscreen GLES and DOM tests are distinct evidence; no GPU FPS claim is made.

The current lawn still has visible sparse/angular patches and surfaces are simpler than the richer painted references. A denser-lawn candidate has a far-view artifact and is deliberately excluded from this release. Native AgX and web display-referred sky use different color pipelines. No literal perfection or exact commercial-game equivalence is claimed.
