# Editable source assets

The packaged `.blend` scenes are the current editable source of truth. Open them in Blender 4.3 or newer. They contain materials, textures and relevant actions. Runtime GLBs under `public/assets/` are unchanged copies of their accepted exports.

- `map-v3/Sunward_ClassicLayout_v3.blend`: current v3 structural map, source-side sky/lighting and packed textures; see its portable build instructions
- `map/Sunward_TestSite.blend`: preserved v2.5 baseline; all 11 textures packed; corrected ground/doorway treatment
- `rifle/compact_carbine.blend`: revision2 visual game prop with Fire, Reload, Inspect and Charge animation data
- `rifle/checkpoints/rifle_working.blend`: modular authoring checkpoint used by the build scripts
- `MANIFEST.json`: exact source file sizes and SHA-256 values

The map scripts retain their original relative folder structure. The final authoring sequence was the base build/refinement/normals/boundary work followed by `refine_art`, `polish_art`, `final_art_treatment`, `delivery_art`, `export_final`, and `fix_ground_overlap`. The last step produces v2.5. Scripts may retain original local working paths and depend on earlier intermediate stages: inspect and adapt those paths before a new build. Opening the packaged final Blender files is the reliable starting point; full clean procedural regeneration is not yet a CI-tested promise.

Do not overwrite these originals for a new visual iteration. Work from a versioned copy, preserve approved coordinate contracts and pivots, then export/re-import and check traversal, materials, animation and bounds. Reference images are not included as redistributable assets.
