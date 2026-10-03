# Editable asset provenance

Verified by read-only source inspection and SHA-256 comparison. The current browser GLBs are copied byte-for-byte from the accepted source exports; no model regeneration was needed for viewer integration.

## Current authoritative map

- Native source: `stylized-nuketown-map/Sunward_TestSite.blend`
- Size: 2,559,452 bytes (native compressed Blender format)
- SHA-256: `460d54859e29c59d809da2bd0497e40ac2c8684630826e89415771847055bfc6`
- Read-only Blender 4.3.2 open confirms scene build_version `2.5`, the final coplanar-ground removal note, the old `PLAYABLE_Base_58x74m` visual object absent, and all 11 portable surface images packed
- Exact same hash as the final staging `sunward-delivery-v2/Sunward_TestSite.blend` and the entry in `Sunward_Editable_Map_and_Walkthrough.zip`
- The older `refinement-v2/Sunward_v2_Delivery.blend` was a v2.3 intermediate. The authoritative final source is the root `Sunward_TestSite.blend`
- Environment export SHA-256: `5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42`
- Collision export SHA-256: `378d5121d97faf7ca5af615c13c0104742c59cffe77e247c32ede25fdece83ce`
- Final source metadata, `exports/resource_stats.json`, current environment GLB extras and final delivery manifest agree on v2.5 and 207,294 environment triangles
- Existing `godot_doorway_v25.log` records a without-jump rear-doorway pass. This is prior source-runtime evidence, not proof of the new browser controller

### Source scripts to preserve

Retain project-relative nesting so each script's root calculation remains valid:

- `source/build_map.py`, `refine_export.py`, `finalize_normals.py`, `add_boundary.py`, `render_views.py`, `qa_map.py`, `qa_collision.py`
- `refinement-v2/add_architecture.py`, `add_foliage.py`, `add_foliage_dense.py`
- `refinement-v2/source/refine_art.py`, `polish_art.py`, `final_art_treatment.py`, `delivery_art.py`, `export_final.py`, `fix_ground_overlap.py`, `render_delivery.py`
- `README.md`, `REFERENCES.md`, current `exports/resource_stats.json`, `qa_report.json`, `qa_collision_report.json`
- Optional standalone Godot reference walkthrough: `preview/project.godot`, `main.tscn`, `main.gd`, `player.gd`, `README.md`, `refresh_assets.sh`

The base creation passes are build_map → refine_export → finalize_normals → add_boundary. The final-art passes are refine_art → polish_art → final_art_treatment → delivery_art → export_final → fix_ground_overlap. The four art passes save Working/Polished/Final/Delivery intermediates respectively; open the preceding output before each next pass. export_final writes root source/export as v2.4; fix_ground_overlap is the final v2.5 writer. Work from a disposable project copy because generation passes are intentionally destructive and not idempotent. Ensure the needed `exports`, `renders`, `refinement-v2/renders`, and `refinement-v2/textures` folders exist. The simplest editable starting point is the final root Blend; no full rebuild is required to use or edit it.

## Current authoritative rifle

- Native final source: `blender-game-rifle/exports/compact_carbine.blend`
- SHA-256: `3901563e7dd3f85408d4457d92117b66cd31919ce0d63408d1bee93492416b8b`
- Revision-2 GLB SHA-256: `13f9c861adb51e8e18556a47fe60ca33d16ae65f593b979f4e3a8c1a7ac210ce`
- These hashes exactly match `exports/qa-report.json` input_sha256
- Preserve `scripts/*.py` including current modular `foreend.py`, `receiver.py`, `stock.py`, build/finish and QA scripts, plus `checkpoints/rifle_working.blend` for fine-grained modular editable construction
- Include `exports/README.txt` and current QA report. `revision2/ads_review.blend` is an optional fixed-camera inspection scene, not the game-ready source
- Older `revision2/before/` Blend/GLB files are V1 comparisons and must not be mislabeled as current

## Scope of runtime art adaptation

New user reference colors, shader feel, clouds and grass are browser presentation work. This does not make the source asset structurally identical to that contact sheet, and it does not alter this native-source provenance. The original game-art rifle is a nonfunctional visual exterior prop.
