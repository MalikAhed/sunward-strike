# Independent RC1 gzip release review

Accepted for incremental structural publication, 2026-10-03. The reviewer personally inspected the saved RC1 source, actual style/structural reference pixels, latest RC1 preview pixels, loader/prebuild code, and the exact source/export bytes.

Independent full gate: lint PASS; 73/73 tests PASS, zero skips; production build PASS; 12 Mesa GLES production programs compiled and linked; reserved-word negative control rejected. Fresh actual-controller runtime: 78 routes, 69 walking boundary samples, 23 jump samples, no warnings. Input hashes were captured before these gates and rechecked unchanged afterward.

Gzip 6,124,741 bytes SHA-256 03990a99e4e89d0b4441808f7578dc86faf2496af2b0c7dc34937f4e7155407c decodes exactly to accepted GLB 18,167,416 bytes SHA-256 004106c1d0dd9660db9e94d003898f19d41e5341c33f27719395e00e98d6c004. Generated dist raw fallback and gzip have those exact hashes. Packaged .blend matches immutable RC1 e1abb8d3a107daae0020e8dff8057e2a7eda3e8c4dfd1a17d01e039ebf3cd1ce. Live atmosphere remains frozen n2.

Source inspection retained both r7 house families at canonical roots (maximum numerical transform error 5.97e-8), no stale house visuals, no legacy joined collider, and no grass vertices inside house components. No model or source file was edited.

This accepts the structural/transport increment with explicit unresolved art and browser-device limitations. It is not full latest-reference art acceptance, gameplay-complete acceptance, or a live WebGL/input/FPS claim. Vite warns about a >500kB JS chunk; output remains successful. See [asset delivery](../../ASSET_DELIVERY.md), [release verification](verification.json), and the checked-in regression tests. Public CI and served-byte verification are checked after publishing.
