# Editable map source v3.2

This package contains the complete editable native scene: the preserved classic layout, furnished interiors, original distant scenery, denser short lawn and locally refined main-house siding, roofs and selected timber. Earlier native packages remain available alongside it.

## Open the scene

From the repository root:

```sh
python3 source-assets/map-v32/build.py
```

Open `source-assets/map-v32/build/Sunward_ClassicLayout_v3_2.blend` in Blender 4.3.2, the version used for verification. The extractor uses Python's standard library, verifies every ordered archive part and the full decoded native hash, and refuses to overwrite different files or links. An identical existing extraction can be reused.

The two `.blend.xz.partNN` files form one lossless XZ stream. They decode to 56,232,484 exact native Blender bytes, SHA-256 `9a29102a227498f2360054b2fccbf0f68feb1441f4fa139017d71ee01e4d1526`. Splitting only keeps transport requests bounded. It does not simplify meshes, alter textures or change the scene. The originally saved Zstandard container has a different hash, recorded in `MANIFEST.json`, but identical decoded content.

## Export fresh runtime assets

With Blender available on `PATH`:

```sh
python3 source-assets/map-v32/build.py --export
```

Use `--blender /path/to/blender` when needed, and `--output-dir /new/empty/folder` to choose a different export destination. The default is `source-assets/map-v32/build/exports/`. Existing exports are not overwritten.

The exporter works in a disposable background session, groups evaluated copies, excludes collision/helper/native-scenery objects from the visual GLB, and writes separate visual, collision and deterministic gzip files. It never saves over the loaded native source. The wrapper requires an explicit successful Python exit, a fresh export report, exact file hashes and valid GLB headers, and matching gzip/raw bytes. Export is not a substitute for the separate visual, collision and gameplay checks after authoring changes.

Run the portable packaging checks with:

```sh
python3 -m unittest discover -s source-assets/map-v32 -p 'test_*.py'
```

## Incremental authoring modules

`source/surfaces/` and `source/lawn/` contain the original editable module and texture snapshots. They are applied, in that order, to a recoverable copy of the extracted [v3.1 native source](../map-v31/README.md). Each module preserves the other scene objects and stores its scoped restoration state. Do not run a patch over your only original.

Restoration is scoped, not a general undo of arbitrary later edits. The lawn module retains unused owned authoring IDs; a whole-scene reverse restoration must remove only those exact zero-user lawn IDs before restoring the surface module. Never purge all orphan data. Reopening the preserved v3.1 package is the straightforward way to recover the complete earlier scene.

The full native scene is the ready-to-edit source of truth. Historical modules in earlier packages are retained for provenance, not a promise of binary-identical procedural regeneration on arbitrary Blender versions. Native camera-dependent scenery uses the unchanged helper in `../map-v31/source/sky/`; retarget it when selecting a different presentation camera. The browser supplies its own atmosphere layer.

## Known limits

The short lawn still repeats stylized fan-shaped clusters, and timber, vehicle and some interior detail remain simpler than the richer style references. The negligible roughness-only vehicle experiment and later grass/paint experiments are not included. Supplied reference pixels are not redistributed.

Native-source and export checks are distinct from actual browser/device rendering, input, audio, disconnected reload and GPU frame-time validation. Those device checks remain open; no literal reference identity or performance equivalence is claimed.
