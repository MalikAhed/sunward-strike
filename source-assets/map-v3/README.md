# SUNWARD v3 editable source

Open `Sunward_ClassicLayout_v3.blend` in Blender 4.3.2 or newer. Textures are packed. This is independently authored geometry guided by classic Nuketown imagery and the supplied art-direction collage. Original game meters are unverified; dimensions use a provisional bus-anchored calibration.

## Safe rebuild

Keep the preserved baseline at `../map/Sunward_TestSite.blend`. From the repository root run:

```sh
python3 source-assets/map-v3/build.py --export
```

Pass `--blender /path/to/blender` when needed. The command refuses to overwrite an existing rebuilt scene and writes into `build/`. It never replaces the packaged editable source or baseline. Source-only sky/cloud/light objects live in 99_ collections and are intentionally excluded from map/collision GLBs; the browser renders its own atmosphere.

`source/` contains the frozen house/layout/landmark/grass/interior/lighting modules and canonical coordinate contract. The thin packaging changes replace local authoring paths with package-relative paths. ORIGINAL_INPUT_HASHES.json records the unmodified authoring inputs; MANIFEST.json records the packaged files. This structural increment intentionally retains empty house shells while corrected furnishing and richer foliage work continues. Generated file byte hashes can differ because Blender metadata is not promised byte-reproducible; compare geometry, bounds, material counts and traversal evidence.

The repository's `npm test` exercises runtime geometry and controller regressions. A Blender export/reimport check is a separate source gate; neither proves live browser GPU performance or complete visual equivalence. See `../../docs/qa/SHARED_REVIEW.md` from the repository root for the published evidence.
