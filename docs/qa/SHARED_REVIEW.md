# Current acceptance register: v3.3 map finish

This increment composes the independently reviewed timber P5r3 and bus-wordmark P6r1 changes over v3.2. Gameplay rules and the shipped cover-query r2 implementation are unchanged. Final deployment identity is established separately by exact-commit CI and served-byte verification. The [v3.2 register](V32_REVIEW.md), [v3.1 register](V31_REVIEW.md) and [RC1 review](RC1_REVIEW.md) remain historical evidence.

[Current map hashes and checks](v33-gameplay/verification.json) accompany the [overview](v33-gameplay/overview.png), [street](v33-gameplay/street.png) and [green](v33-gameplay/green-yard.png)/[yellow](v33-gameplay/yellow-yard.png) yard previews. They are saved native-source views, not gameplay screenshots.

## Bounded visual changes

- Clearer lengthwise grain on exactly 210 previously UV-qualified honey-timber bindings. Color repeats three times horizontally while the normal texture keeps its original transform and strength. Original native UVs are unchanged
- The original SUNLINE label now fits between its bus trims. Only its placement and planar scale change; text, font, ivory material, rotation, depth and the rest of the bus are preserved
- No additional triangles, runtime materials, embedded image count or decoded texture allocation. Three deduplicated export vertices are added by the label adjustment; the map gzip is 23,056 bytes smaller than v3.2
- Canonical layout, house families, all 312 collision proxies, routes, furniture, atmosphere, foliage and the accepted r6i lawn remain unchanged

## Source and runtime evidence

All 39 original v3.2 packed/decoded images, 127 material graphs, 1,966 mesh datablocks and 12 font shapes are retained. The complete native source has 41 images and 128 materials, including protected inactive authoring data. Scoped reverse restoration returns to exact v3.2 after reversing the two manager version annotations, then P6 followed by P5. A deliberate original-image corruption is rejected.

The collision binary and nodes are byte-identical to v3.2. Only map_version and integrated_style_revision change in its scene extras; validation_state is unchanged. All non-label exported geometry/UVs/normals remain exact. The intended label move has a disclosed maximum 0.008112° normal rounding difference, not a relaxed tolerance for other geometry.

The application test suite loads the current map and checks authored routes and boundaries, cover, match rules, input/lifecycle wiring, asset decoding, offline cache logic and renderer-generated GLSL. The timber material is explicitly selected for actual offscreen shader compilation, with independent color/normal transforms checked through GLTFLoader. Actual-main tests use a DOM model and no-op renderer; they are not physical browser/device tests.

The native package uses lossless split-XZ delivery and an independently checked extractor/exporter. Eighteen packaging tests cover corruption, ordered parts, path/link safety, no-overwrite behavior, exporter failure, report/output validation and gzip/raw equality. CI also extracts the actual native payload.

The [cover-query r2 review](COVER_QUERY_R2.md) contains CPU measurements made on the preceding v3.2 asset set. Its implementation is unchanged here. The separate cold-start experiment is not included, and no new speedup or browser-FPS claim follows from this art increment.

## Known gaps

Grass still repeats flat fan-shaped clusters. A finer triangle diagnostic removed those fans but remained too flat/sparse against the reference carpet and is not included. Timber improvement is local: regular grain streaks and unchanged UV-ambiguous/cream/garage surfaces remain. Vehicle paint and some interiors are still less rich than the style references; held paint experiments are excluded. Existing native-to-GLB bus/glass response differences remain disclosed. Still images cannot establish temporal shimmer or browser lighting parity.

The previously documented movement/perch and bot-balance qualifications remain. Selected KC cases improve collection, but not every seed or team balance improves uniformly; bots are not humanlike tactical teammates.

The available cloud browser cannot create WebGL2. Actual browser GPU/frame rate, pointer capture, physical keyboard/touch feel, audio playback and disconnected-device reload remain unperformed. Native renders, offscreen compilation and CPU simulations are separate evidence. No perfection or exact commercial-game equivalence is claimed.
