# Working on Sunward Strike

The default branch is `main`. GitHub Pages publishes its tested production build. Changes on a branch can be reviewed before merging; do not merge or publish work without the project owner's authorization.

## Before a push

1. Preserve editable asset sources and stable filenames. Record new export hashes and triangle/material counts.
2. Run `npm ci`, `npm test`, and `npm run build`.
3. Check changed controls, relative asset paths, loading failures, small screens, and graphics settings in a real browser. Record tests actually run; never label pending checks as passes.
4. Commit source, required GLBs, documentation and the lockfile. Exclude caches, `node_modules`, temporary credentials, logs and local artifacts.
5. Push only the intended branch. Verify its remote commit SHA, then inspect CI for that same SHA.
6. For an authorized production update, verify the Pages deployment succeeded and inspect the live app. A local build alone is not a completed deployment.

## Ownership and visual authority

Keep original editable scenes recoverable. One integrator owns the live map export and shared rendering/material settings. Each changed asset needs a builder and independent source/render review, using the current reference rather than the preceding iteration. Do not change layout, scale, traversal geometry or prop placement merely to match a color/style reference.

## Gameplay direction

See [the research and implementation plan](docs/GAMEPLAY_RESEARCH.md). Runtime code is the authority for implemented values. Research defaults are proposals until explicitly adopted into a single tuning module. Do not claim exact Call of Duty equivalence or humanlike bot behavior without the relevant measurements and playtests.

## Local development

Use Node.js 22, `npm ci`, and `npm run dev`. When an environment disallows a wildcard listener, use `npm run dev -- --host 127.0.0.1`. Static previews must be served over HTTP; double-clicking `index.html` does not support GLB module loading.
