# Editable map source v3.1

This package contains the exact editable native scene for the accepted v3.1 art increment: turquoise/yellow/honey palette, fine turf base, broadleaf trees, short grass, furnished interiors, and distant cloud/mountain scenery. The classic map structure is unchanged from the separately retained v3 source.

## Open the native scene

From the repository root, run:

```sh
python source-assets/map-v31/extract_source.py
```

Open `source-assets/map-v31/build/Sunward_ClassicLayout_v3_1.blend` in Blender 4.3 or later. The extractor uses only Python's standard library, verifies the archive and decoded hashes, and refuses to overwrite a different local file. An XZ-capable archive program can also extract the `.blend.xz` file.

The archive is a lossless packaging of the exact uncompressed Blender bytes. It retains the editable meshes, materials, textures, cameras, lights, and reversible source backups. This packaging keeps a single GitHub upload within the available transport limit; it does not simplify geometry or recompress image pixels. The originally saved Zstandard-compressed authoring file and this extracted native file have different container hashes but identical decoded Blender bytes; both hashes are in `MANIFEST.json`.

## Authoring modules

`source/` contains the exact accepted module snapshots and their original texture assets. Apply in this order to a recoverable copy of `../map-v3/Sunward_ClassicLayout_v3.blend`:

1. `palette/material_palette_patch.py`, then `palette/lawn_finish_patch.py`
2. `vegetation/vegetation_patch_v4_r5.py`, using the packaged frame JSON and leaf atlas
3. `furniture/interior_dressing_patch.py`, using the packaged frame/route JSON; set its `BASE` to the verified `../map/Sunward_TestSite.blend`
4. `sky/native_atmosphere.py`, keeping its parity, radiance JSON and asset folder together

Use a copied working module folder when applying these authoring operations: palette and native-sky routines generate textures beside their module unless given an explicit working output folder. Do not run them over the only original scene. The native camera helper must be called after selecting a different render camera; it does not install an automatic handler. Native atmosphere and interior point lights are source-only, while runtime sky is implemented by the application's atmosphere module.

The native file above is the ready-to-edit source; these scripts are authoring components, not a promise that a manual rebuild with changed paths or Blender versions produces an identical binary container.

## Review scope

The exact source/export passed independent protected-geometry, proxy containment, export/reimport, material/shader and controller checks. Full browser GPU/input behavior remains unverified. Lawn density and painterly surface richness remain visible differences from the style references; later revisions are separate. Supplied reference images are not included.
