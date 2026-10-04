# Editable map source v3.3

This package contains the complete v3.2 classic-layout source plus P5r3 timber finish and P6r1 bus-wordmark placement, in that order. P4 vehicle-paint and R7 grass experiments are excluded. Earlier native packages remain available alongside it.

## Open and export

From the repository root:

```sh
python3 source-assets/map-v33/build.py
python3 source-assets/map-v33/build.py --export
```

Open `source-assets/map-v33/build/Sunward_ClassicLayout_v3_3.blend` in Blender 4.3.2. The extractor uses Python's standard library, verifies every ordered XZ part and the complete decoded Blender hash, and refuses to overwrite different files or links. An identical existing extraction can be reused. The parts form one lossless XZ stream; splitting does not change native scene data. The stream decodes to 57,507,844 exact native bytes, SHA-256 `f91f85249a1e87e430cc450dcced2836f28fceb9e4323b69115e72e15ce9b1f1`. The original saved container has a different hash, recorded separately in `MANIFEST.json`.

Use `--blender /path/to/blender` when needed and `--output-dir /new/empty/folder` to choose a fresh export destination. The default is `build/exports/` within this package. Existing outputs are not overwritten.

The unchanged v3.2 export procedure runs in a disposable background session with two threads, groups evaluated copies, and writes separate visual GLB, collision GLB and deterministic gzip files. It does not save over the source. The wrapper requires a successful Python exit, a fresh export report, matching asset hashes, valid GLB headers and exact gzip/raw identity. Authoring changes still require separate visual, collision and gameplay checks.

Run the portable checks without Blender:

```sh
python3 -m unittest discover -s source-assets/map-v33 -p 'test_*.py'
```

## Original incremental modules

The full native scene is the ready-to-edit source of truth. `source/timber/` and `source/wordmark/` hold byte-exact snapshots of the accepted original modules and their dependencies. Apply them only to a recoverable copy of the extracted [v3.2 native source](../map-v32/README.md):

1. Run `timber_finish_patch.apply_timber_finish()`. It replaces exactly 210 already UV-qualified timber material slots, preserves the honey mean, uses color-only U repeat 3 and keeps normal strength 0.30. Its two 256px maps replace the corresponding active export maps; all original native images and materials remain recoverable, including inactive packed/decoded images and original retention flags.
2. Verify that the live scene contains 41 non-Render-Result image IDs, then call `wordmark_patch.apply_wordmark(expected_image_count=41)`. Its default of 30 is for the earlier authoring baseline and must not be used for this composition. P6 changes only `Shuttle_label` placement and planar scale, retaining its text, font, material, rotation and depth.

Procedural reapplication from a relocated package does not promise byte-identical Blender-container regeneration; the full native archive is authoritative.

The modules require Blender's `bpy`, `mathutils` and bundled NumPy. P6's two `label_validation*.py` files must stay beside its module. Its empty, writable `reports/` directory is reserved for a locally generated restore-failure diagnostic; no private reports are included. Regenerating the original timber PNGs with `generate_pixel_sources.py --output-directory /new/folder` additionally requires NumPy and Pillow; use the bundled exact PNGs for the accepted bytes.

Restore in reverse order: `wordmark_patch.restore_wordmark()` first, then `timber_finish_patch.restore_timber_finish()`. P6 stores the post-P5 snapshot, so reversing this order is invalid. These functions are scoped restoration checks, not a general undo of arbitrary later edits. Before those calls, restore the two changed manager annotations `map_version` and `integrated_style_revision` to the original values stored in `wordmark_patch.read_state()["baseline"]["globals"]["scene_custom"]`. `validation_state` was reassigned its identical prior value and needs no change. First undo unrelated later edits as well, and never globally purge orphan data. Reopening the preserved v3.2 source is the simplest complete recovery path. Do not reapply P2 to this already patched scene.

## Budgets and limits

The v3.2 ceilings are unchanged: 400,000 triangles, 1,500 meshes, 1,800 primitives, 80 materials, 25 exported images, 32,000,000 raw map bytes, 8,500,000 gzip map bytes and 128 MiB decoded texture allocation. The composed runtime allocation is 77 materials, 25 images and 6,881,280 base RGBA bytes. Exact native/archive/runtime identities are in the manifest.

P5 is a bounded near-range timber improvement; static yard views stay calm, but temporal shimmer is unverified. P6 fixes trim overlap on the existing wordmark; the distant word remains small. The richer reference finish is not fully matched, and the retained lawn still repeats stylized fan-shaped clusters. Supplied reference pixels and private QA reports are not redistributed.

Native-source/export checks do not establish actual browser/device rendering, input, audio, disconnected reload or GPU frame-time performance. Those checks remain separate. No literal reference identity or performance equivalence is claimed.
