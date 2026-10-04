# Sol 6.1 tree and grass candidate

This is a review artifact for the local Sol 6.1 tree/grass candidate. It is intentionally not wired into the runtime build yet.

- Candidate scope: existing V2 tree leaf meshes and existing V3 lawn mesh
- Trees changed: 10
- Grass groups: 34,500
- Object IDs preserved: yes
- Collision digest preserved relative to the V34 source: yes
- Triangle count: 187,167 before and after
- GLB export: 20,874,456 bytes
- Matched preview: Workbench texture render from V3_Presentation_Hero

Astra review status:
- Native/visual review: conditional pass for the tree/grass appearance
- Runtime integration: blocked pending filtered export, gzip budget, and collision/source-baseline reconciliation
- Do not treat this preview as the live game build

The public runtime remains the prior verified release while this candidate is reviewed.
