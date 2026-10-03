# Visual direction and acceptance

The latest four references supplied on 2026-10-03 have distinct roles: sky tone/cloud forms; tree mesh/tones and grass; object surface finishes; and distant full-map color tone. The finish collage is not a mandatory object checklist. The distant view is not structural authority. Actual classic Nuketown imagery is the separate structural authority; see [the structural brief](MAP_STRUCTURE_PLAN.md). The collage is not a dimensional survey.

## Observable targets

- Medium-blue sky, large soft cream clouds and cool undersides
- Warm cream/tan masonry in sunlight, cooler shaded planes, readable teal/coral/yellow paint
- Broad restrained painted surface variation, avoiding noisy photoreal microdetail
- Yellow-green folded grass, denser planted edges and clear traversal routes
- Readable furnished interiors with warm surfaces and unobstructed stairs/doors
- Original branding and owned geometry/materials; no extracted commercial assets

## Implementation boundaries

The map's editable source and packed textures are versioned separately from its runtime GLBs. The web atmosphere adds original procedural sky/cloud meshes and scoped paint/foliage shaders without changing the source transforms. A Blender presentation world is a source-side approximation, not a live synchronization of browser shaders.

The v3 structural candidate adds corrected house families and a reversible coral material treatment, plus 3,000 folded grass tufts. Source-only presentation scenery must stay excluded from gameplay collision and map GLB exports; the browser owns its atmosphere layer.

## Acceptance evidence

Fresh full-scene comparisons are required at the street, both house fronts/rears, yards and furnished interiors. Check warm highlights/cool shadows, sky hue, cloud silhouette, material warmth and vegetation density independently of structural correctness. Scoped geometry or material approval does not establish full art-direction acceptance. Concrete open differences belong in [the shared acceptance register](qa/SHARED_REVIEW.md).

The cloud browser reports disabled graphics and cannot create WebGL2. Static public delivery, saved Blender renders and offline shader tests are useful but do not establish real-time browser fidelity, mouse/touch behavior or GPU frame time. Those remain pending until measured in a supported rendering browser. No exact-match or perfection claim is made.
