# Visual direction and acceptance

The current art direction is the user's supplied multi-panel environment reference from 2026-10-03. It guides materials, lighting, sky and vegetation. It does not replace the existing map's structural layout, dimensions, traversal routes or prop placements.

## Observable targets

- Clear medium blue sky, large soft cream cloud forms and cool lower cloud shading
- Warm sunlight on cream/tan masonry, cooler shaded planes, muted teal/coral/yellow paint
- Broad restrained angular surface variation rather than noisy photoreal microdetail
- Yellow-green grass and planted edges, with enough density to soften boundaries while keeping paths readable
- Strong landmark silhouettes and readable shadow separation at player height
- Original project branding and assets; no copied commercial textures or interface artwork

## Implemented in the first viewer

The original map GLB is preserved byte-for-byte. A separate reversible atmosphere module adds original procedural clouds and reference-inspired shader/material color treatment. Existing foliage receives a warmer palette. No source-scene transforms or map geometry are changed by this runtime layer.

## Still open

Dense individual grass and a full reference-matched material/lighting pass are not completed. These need live rendered comparisons from hero, street, both courtyards, interiors and player-eye views. Current project screenshots/rendered previews do not prove a WebGL runtime match.

The first publishing environment's browser reports disabled graphics and cannot create WebGL2. The live page and file delivery can be tested there; real-time rendering, responsiveness, mouse capture, visual fidelity and GPU frame time must be checked in a WebGL2-capable browser. These checks remain pending rather than being described as passed.

## Next art acceptance gate

One builder makes a versioned change, an independent reviewer compares fresh runtime screenshots with the original reference pixels, and the integrator checks the whole scene and traversal. Record concrete closed/open differences and device/frame-time measurements. Do not label the result identical or perfect based on agreement alone.
