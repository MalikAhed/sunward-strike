# Independent UI review

## Review scope and reference authority

- Art-style reference inspected directly: `ca71f0ad-ff16-4cb7-8b22-5bff8edf6139.png`, the supplied 1536 × 1024 environment collage
- Bug evidence inspected directly: `image(20261003-161724).png`, the supplied 1365 × 643 screenshot. It records the broken previous state and is not a layout or visual target
- Style guidance: warm cream/stone, muted teal and coral, saffron accents, restrained angular detail, readable scene silhouettes. The HUD should use this palette in a compact original field-instrument vocabulary
- Structural constraint: preserve the source map, placement, collision and rifle assets. This review owns only this report, with read-only access to implementation files
- Browser automation is unavailable for this review, and the cloud runtime does not provide WebGL2. No browser, live layout, pointer-lock, fullscreen, GPU or rendered visual acceptance is claimed

## Acceptance checks

1. Compact in-game entry affordance; no oversized marketing heading obscuring the scene
2. Truthful camera modes, measured telemetry and implemented actions; no invented combatants, match modes or statistics
3. Preserve the semantic IDs, camera data-mode values and input data-key bindings expected by `src/main.js`
4. Readable keyboard and touch labels, visible focus, safe-area-aware layout, and non-overlapping edge controls at desktop, phone portrait and short landscape widths
5. Coarse-pointer primary controls at least 44 × 44 CSS px; distinct movement and look instructions
6. Graphics failure explicitly labels the poster as static and hides interaction controls that cannot work; retry remains operable
7. Required map/collision/rifle source asset hashes remain unchanged

## Baseline discrepancies sent to builder

- Priority 1: the large `SMALL TOWN / WIDE OPEN` title, descriptive copy and large CTA create an unnecessary marketing layer in the game view
- Priority 1: at 641–1000px widths and heights under 600px, the old short-height rule places the centered camera switch back at top 25px beside the brand/help row. Its 460px minimum width creates overlap risk, especially near 641–800px
- Priority 1: old touch targets are 42 × 42px. The height pad contains only `+` / `−`, and its Q/E input is freefly-only. Walking touch controls currently do not implement fire, aim, reload or jump
- Priority 2: the old walk field guide becomes a tall panel near the bottom HUD in short windows
- Priority 2: dynamic mode selection has visual `selected` classes but no synchronized accessible pressed state

## Baseline semantic evidence

All 26 IDs referenced through the main runtime's `$()` helper exist once in the baseline HTML. Camera values are `fly`, `walk`, `orbit`; existing touch movement values are `KeyW`, `KeyA`, `KeyS`, `KeyD`, `KeyE`, `KeyQ`.

Source SHA-256 before the UI revision:

- Map: `5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42`
- Collision: `378d5121d97faf7ca5af615c13c0104742c59cffe77e247c32ede25fdece83ce`
- Carbine: `13f9c861adb51e8e18556a47fe60ca33d16ae65f593b979f4e3a8c1a7ac210ce`

## Paired correction cycle and source acceptance

The UI builder revised `index.html` and `src/style.css`; the manager owns the mode/help hooks in `src/main.js`. The independent reviewer read the fresh source and requested measurable corrections before this handoff. Saved source checked at 2026-10-03 16:39 UTC:

- HTML SHA-256: `22592def0ba511d988e0f4c327cc3572c0c7c242574b85f7ef78bd0776d4a253`
- CSS SHA-256: `ac713827902ada90eaed5ad418294f76014e7d6f5ed5d195d9c19615e18a4da5`
- Main runtime SHA-256: `1633e42f58f32bdff45335eae0232e5da25c8e1a6941a161f6ad994247197aac`

Closed in the correction revision:

- Oversized marketing title replaced with a 23px compact scene-entry card; below 340px height only the working Enter scene button remains
- Intermediate/short layouts retain a separate mode row instead of placing it beside the brand. Safe-area variables drive header, mode/secondary rows, entry card, guide, telemetry, weapon HUD and fallback
- Coarse mode and native select targets now have a 44px minimum height. Movement buttons are 46 × 46px; height buttons are 60 × 52px with visible Up/Down labels; close/help/fullscreen targets are 44px
- Short coarse touch pad raised to bottom 106px to clear the taller native-select footer. At 568 × 320 with zero safe insets, the entry CTA spans approximately y170–214, while mode navigation is y78–130 and footer begins around y227. These are CSS-box calculations, not browser measurements
- Short coarse ammo repositioning is restricted to widths >=481px; narrow coarse portrait keeps it at bottom 226px instead of colliding with top telemetry
- Dark-teal focus replaced the low-contrast saffron-on-cream outline. Essential small mode/control/selector labels now measure 5.60–5.74:1 on worst-case cream glass composited over black; telemetry mode text measures 5.37:1 over white-backed dark glass; selected decorative camera index measures 5.34:1
- First-person hides freefly-only vertical controls; orbit hides movement and capture controls. A separate keyboard/mouse heading makes the touch guide's limitations clear
- Help starts hidden with `aria-expanded=false`; mode selection starts `fly` with exclusive `aria-pressed`, and actual manager-owned functions synchronize these states after interaction

Independent checks actually performed:

1. HTML parsed with lxml: all 26 runtime IDs exist exactly once; camera button values remain fly/walk/orbit, their initial pressed values are true/false/false, and all six existing touch keys remain unchanged
2. CSS parsed successfully with PostCSS
3. Actual `setMode` and `toggleHelp` functions tested in a mock-DOM VM: exclusive pressed state, app dataset, button-only mode selector, ORBIT label and open/close help state passed
4. Actual graphics-failure/start source tested in a mock-DOM VM: renderer setup returns after failure; STATIC SOURCE PREVIEW and truthful poster alt/description remain; dead HUD/interaction controls hide; retry reloads; debug reports unavailable WebGL2
5. Independent `npm test`: 14/14 passed, including offline full generated shader compile/link, collision and math tests. These do not prove browser behavior or UI visual fidelity
6. Map/collision/carbine asset SHA-256 values match the baseline exactly. No UI review changed source geometry

## Remaining gates and handoff

Static functional/source acceptance is satisfied for this revision; visual/runtime acceptance remains open.

- Highest priority: fresh WebGL2 browser screenshots and actual desktop/phone portrait/short-landscape interaction tests have not been performed. No screenshot of the revised UI exists from this review; only the original reference and bug pixels were inspected
- Test actual 320 × 568, 390 × 844, 568 × 320, 844 × 390, 1024 × 768 and desktop layouts, including safe insets, native dropdown behavior, open help, walk ammo, pointer lock, fullscreen, touch movement/look and error fallback
- Touch supports movement/look and freefly height only. Fire/aim/jump/reload remain keyboard/mouse actions; no fabricated touch controls were added
- The final two worst-case normal-text contrast discrepancies were closed by the manager before publication: guide note `#485a51` now measures 5.41:1, and entry fine print `#4e594e` measures 5.40:1 on the .95 cream glass composited over pure black. The continuing shared reviewer independently recomputed both from sRGB relative luminance at 2026-10-03 16:46 UTC. Final CSS SHA-256: `6307b803dfb17afcd1f07e1e52ca06ccebc176b9a89bf2b1de1f80a561a6aa08`
- Review the actual scene through the HUD against the art reference. A palette/source review does not establish the final rendered 3D match

The continuing shared independent reviewer receives this artifact/version and retains the unresolved runtime gates. This report does not claim browser-responsive, WebGL-rendered or pixel-match sign-off.

## Shared reviewer publication recheck

At 2026-10-03 16:46 UTC, the continuing independent reviewer verified the final two text-color deltas, re-read their actual CSS selectors, and independently ran `npm test` (14/14 passing, zero skips) and `npm run lint` (passing). CI now requires the installed EGL shader compiler through `REQUIRE_SHADER_COMPILER=1`; the actual test rejects missing compiler capability when that flag is set. This is a source/validation recheck, not a new browser or rendered UI pass. All visual/runtime gates above remain open.
