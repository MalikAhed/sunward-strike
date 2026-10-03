# Classic Nuketown structural correction

## Authority and scope

Rebuild the prototype's structure against **original 2010 Nuketown**, using the faithful BO6 classic remaster as the principal current pixel reference. Preserve the editable baseline and versioned backups. The prior generated reference collage controls materials, sky and grass only. It is not a survey or a layout reference.

Primary publisher authority: [Call of Duty, October 29, 2024](https://www.callofduty.com/blog/2024/10/call-of-duty-black-ops-6-new-maps-modes-updates-announcement). The announcement identifies the remaster as retaining the original design, including parked-vehicle placement. Its [official composite image 004](https://imgs.callofduty.com/content/dam/atvi/callofduty/cod-touchui/blog/body/bo6/COD-BO6-S0-ANNOUNCEMENT-004.jpg) contains a tactical minimap, street overview, truck and interior views. Images [002](https://imgs.callofduty.com/content/dam/atvi/callofduty/cod-touchui/blog/body/bo6/COD-BO6-S0-ANNOUNCEMENT-002.jpg) and [003](https://imgs.callofduty.com/content/dam/atvi/callofduty/cod-touchui/blog/body/bo6/COD-BO6-S0-ANNOUNCEMENT-003.jpg) supply additional yellow-front and truck-opening views.

No Warhead, Cold War '84, Nuketown 2025/2065, Zombies or other remakes are structural authorities for this correction. `original-layout-reference.jpg` is visibly branded Call of Duty: Mobile. It corroborates the green rear architecture but is not the primary footprint/scale source.

## Actual reference pixels and provenance

Research images remain outside the public source repository. No screenshot pixels, ripped meshes or game textures are to be embedded in the delivered scene.

- `COD-BO6-S0-ANNOUNCEMENT-004.jpg`: publisher's 1920×1080 composite
- `official-bo6-minimap-crop.png`: minimap crop enlarged 2× for analysis, 840×960
- `official-measurement-overlay.png`: hand-measured outline/landmark overlay; a measurement aid, not additional source authority
- `classic-nuketown-landmarks.json`: pixel coordinates, normalization, uncertainty, source URLs and scale caveat
- `bo1-overhead-large.jpg`: [2010 tactical-plan capture](https://www.flickr.com/photos/segmentnext/5229665976), uploaded December 3, 2010
- `bo1-bird-eye-wikia.png`: [original Black Ops spectator capture](https://static.wikia.nocookie.net/callofduty/images/c/ce/Bird%27s_Eye_View_Nuketown_BO.png); useful for roofs, green rear structures and actual neighboring scenery; its perspective is unsuitable for direct horizontal dimensions
- `bo1-thesis-houses-p130.png`: actual original-game rear screenshots of both houses, Figures 13-36 and 13-37, printed page 130 / PDF page 144 of Terry Hon-Tai Sin's 2012 University of Waterloo [Architecture at Play thesis](https://dspacemainprd01.lib.uwaterloo.ca/server/api/core/bitstreams/bec4fe6d-9009-4a03-8b0d-1ab4ff17fea1/content)
- `bo1-thesis-plan-p128.png`: the same thesis's diagram explicitly labels detached rectangles as **second-floor insets**. They are not additional houses or playable land. The diagram is labeled N.T.S.; it is not a metric survey

The thesis's Nuketown section, printed pages 123–144, provides no scale bar, metric dimensions, grid spacing or quantitative survey method. Absolute original meters remain unknown. Its plans are rotated approximately 180° relative to the official BO6 graphic: match landmarks, not compass labels.

## Coordinate contract and scale

For the official crop, full-image pixels are `raw_x = 1450 + u/2`, `raw_y = 210 + v/2`. Crop +u points right, +v down. Normalized research distances use 811 crop pixels as the long bounding-box extent.

**The sole world-coordinate authority is the versioned `site_frames.json` included with the v3 source package.** It uses court origin `(u,v) = (550,475)`, Blender +X image-right, +Y image-up, +Z vertical. Runtime coordinates use Three X = Blender X, Three Y = Blender Z, Three Z = −Blender Y. Use one uniform scale; never stretch X and Y independently to preserve the old bounds.

The accepted prototype calibration is `s = 0.1269490642 m/crop-pixel`, based on retaining an assumed 10.5m SUNLINE shuttle body against an 82.7103-pixel bus marker span. This is a **gameplay prototype assumption, not an official Nuketown dimension**. Earlier 74m and 90m long-axis proposals are superseded. The traced terrain's approximately 44.05×102.32m world AABB derives entirely from this assumption. The broader hand-measurement bbox gives approximately 45.45×102.96m.

Measured outline aspect is approximately **0.43–0.44**, versus the old rectangular 58/74 = **0.784**. Thus the old rectangle cannot be retained as a faithful footprint. The corrected outline is two differently angled rear lots joined through a round cul-de-sac with a short road-mouth extension. Its yard corners, setbacks, notches and fences must shape the playable boundary.

## Footprints and orientation

Pixel coordinates are approximate, normally ±5–6 enlarged crop pixels; orientation uncertainty is about ±3°. Use canonical rectified house components from `site_frames.json` and independently check them against the actual pixels.

- Upper/north, truck-side lot is the original yellow house family, rendered coral in SUNWARD. Main-body corners approximately `(465,278), (541,253), (571,360), (497,375)`; the garage attaches to crop-left
- Lower/south, bus-side lot is the original green/gable family, rendered teal in SUNWARD. Main-body corners approximately `(456,558), (526,581), (489,679), (421,656)`; its shallow rear-offset garage attaches to crop-right
- Rectified house yaws are green **161.811°**, yellow/coral **18.208°**. They are not identical boxes placed at 0°/180°
- Both main bodies are narrow/deep: rectified width/depth about **0.72–0.73**. Current source main floor dimensions are approximately 11.65×10.65m, ratio 1.09, so simply moving the old shells cannot correct their proportions
- Yellow/coral main portion is approximately 78×111 crop pixels; its garage portion about 47×61. Green main portion is about 74×104; its garage is about 55×43. Do not mirror one oversized deep garage to both sides

The first research draft misassigned the house color families to the traced lots. The original BO1 aerial and official east-exit street view resolved this: green belongs on the lower lot, yellow on the upper. The corrected canonical contract records physical lot IDs separately from house-family names.

Street photographs distinguish the green street-facing gable from yellow's very low asymmetric roof and prominent stone chimney. Green garage roof orientation differs from the main roof. Retain readable two-bay front openings where the source shows them; rear openings, door/window placement and awnings should follow the actual views.

## Interior and rear circulation

The original tactical floorplan and gameplay screenshots support front living room → interior stair / rear kitchen, a house-to-garage link, backyard exits, two upstairs rooms, front window sightline and rear balcony route. The second-floor inset contours can guide room placement but must not be placed outside the physical map.

Both original rear screenshots show pergola-like balcony structures with railings, diagonal exterior stairs and under-balcony ground space. Match their silhouettes and landing/stair direction from the screenshots rather than inventing identical broad porches. Maintain the existing 1.8m player reference, 0.35m capsule, plausible door height and navigable stair tread/landing widths; the screenshots do not authenticate exact vertical meters.

## Street landmarks and routes

- Court center approximately `(550,475)`; curb radius about **83 ±6 crop pixels**, corroborated by the original overhead. Do not make the entire central street a rectangle
- Road mouth lies near `u = 681`, `v = 405–535`; preserve its fence/barrier endpoint and the playable end of the street
- Moving truck rear→front axis: `(462,467)` → `(563,438)`
- Bus rear→front axis: `(535,505)` → `(615,484)`
- Both front toward the road entrance, established by street photographs. Their staggered positions and roughly 15–16° long-axis yaw produce separate cover islands, with an accessible open truck rear/ramp
- Right-road marker around `(650,468)` is the entrance jeep; the slender strip around `(466,520)` is the Welcome sign; left-court car around `(410,487)` is the yellow car beside the pink-house cul-de-sac
- The green driveway car is visible in the street photograph but has no unambiguous separate tactical marker. Its placement needs photo/driveway corroboration; do not reuse the initially mislabeled court marker

Preserve two exterior flank routes, central gaps around vehicles, house/garage through-routes and upstairs-to-yard routes. Tactical gray strips are not measured clear walking widths: fences, foliage and props consume some of that space. Verify collision and the actual capsule in all routes. Peripheral shed, bunker, garden and fence positions require separate source-matched review; an invented garden must not silently become a surveyed claim.

## Acceptance gates

1. Compare a fresh orthographic render to official 004: outline aspect, house yaw, footprints, garage offsets, court, road mouth, vehicle staggering and landmark identities
2. Reject inset rooms accidentally modeled as outside buildings, a rectangular clip boundary, 0°/180° house twins or identical deep garages
3. Compare street, both house fronts, both rear views and upstairs sightlines to the actual reference pixels
4. Test all three lanes, front/rear/garage portals, interior/exterior stairs, truck ramp and every boundary with the runtime player capsule
5. Keep measured pixel evidence separate from inferred meters and unresolved details. Report observable agreement and tests actually run; do not claim 100% accuracy
