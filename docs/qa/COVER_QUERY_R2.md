# Static-cover query r2

This query-only increment retains the exact v3.2 map and native source from [94a236b](https://github.com/MalikAhed/sunward-strike/commit/94a236b588db32d13fa65df625f609abc7124e97). It changes how static opaque-cover rays find candidate triangles, not the authored geometry, material exclusions, sidedness, movement collision, navigation validation, weapons, bot decisions or scoring.

## Correctness

The [query helper](../../src/gameplay/cover-query-bvh.js) indexes the existing transformed triangles. It retains Three's exact triangle-intersection routine and inclusive final distance cutoff. The original cover backend is bound before replacement and handles exceptional direction-normalization results. Conservative broadphase bounds admit floating-point edge cases without relaxing the final hit test.

An independent 72,887-query audit passes with bit-exact returned distances. An earlier prototype failed 59 cases, including 15 actual-map surface or cutoff cases; that prototype was rejected. All 59 are retained in the [portable regression fixture](../../tests/fixtures/cover-bvh-regressions.json) and exercised through normal production construction. Focused checks also cover material sides, exclusions, mirrored geometry, zero/parallel rays, extreme finite directions and non-recursive fallback.

Three 120-second scenarios were independently run with both backends: 4v4 TDM, 4v4 Kill Confirmed and a 6v6 KC stress case. Every emitted event, every per-step snapshot and the final state match in all six runs. The 4v4 cases use a deterministic ordinary-input test driver; the stress-case human is stationary. These are selected simulations, not exhaustive gameplay or balance proof.

The composed application suite contains 224 passing tests with no skips, including the retained route, lifecycle, cache and shader checks. Native-source packaging and asset identities remain unchanged.

## Measured CPU cost and tradeoff

One independent baseline/candidate pair per scenario, on a shared EPYC VM with Node 24.19, produced these warmed update wall-time means. The first 15 simulated seconds are excluded; each row has 6,300 measured updates per backend. Additional author repetitions are separate evidence.

| Scenario | Original mean | BVH r2 mean | Reduction |
|---|---:|---:|---:|
| 4v4 TDM | 2.598 ms | 1.624 ms | 37.5% |
| 4v4 KC | 2.592 ms | 1.514 ms | 41.6% |
| 6v6 KC stress | 5.113 ms | 3.051 ms | 40.3% |

The index adds about 279 ms to construction in a separate probe. It retains exactly 2,494,604 bytes of typed index storage, plus about 1.89 MB of additional settled JavaScript heap: about 4.39 MB of live payload in that experiment. RSS rose by about 12 MB, and construction has larger temporary allocations. RSS, retained data and temporary allocation are different measurements. Forced garbage collection was used only in the separate memory probe, never during timed updates.

The original cover octrees remain for triangle ownership and exceptional-input fallback. Their depth is 5; the active query BVH depth is 14. Runtime statistics report the legacy backend and active index separately, and total construction includes source preparation, both index stages and bookkeeping. The existing world cache avoids rebuilding them on every restart; changing the map/collision identity invalidates it.

## Limits

These are CPU measurements on one shared host. They do not establish browser or GPU frame rate, physical input feel, audio playback, mobile behavior, service-worker installation or disconnected reload. Wall-time outliers include scheduling/collection uncertainty. No universal speedup or device-FPS guarantee is claimed. The visual-reference and traversal qualifications in the [acceptance register](SHARED_REVIEW.md) still apply.
