# Sunward Strike

An original browser arena FPS and map explorer, with local Team Deathmatch and Kill Confirmed matches on the stylized SUNWARD neighborhood.

[Open Sunward Strike](https://malikahed.github.io/sunward-strike/)

## Current milestone

- v3.2 environment: the approved classic-layout structure, turquoise/yellow baked palette, furnished interiors, denser short grass, clearer house siding/shingles and distant n5 cloud/mountain atlases
- Local TDM and Kill Confirmed, Recruit/Regular/Veteran bots, 2v2–4v4 team presets, scores, clock, death/respawn and restart
- Shared fixed-step player/bot movement with sprint, grounded slide, crouch, ADS, real hitscan damage, recoil, reload and recovery
- Bounded nearby tag commitment improves bot KC collection; clean respawn look/input prevents stale held actions
- Movement collision plus opaque visual cover for bullets and bot sight; open windows remain open
- Compact match HUD, mouse capture or drag fallback, touch action controls, keyboard menus and optional original synthesized sound
- Preserved Freefly, First Person and Orbit exploration with six viewpoints and three quality settings
- Bundled dependencies, relative-base static hosting and versioned, integrity-checked repeat-play offline caching

The offline match is a prototype with independent tuning. It is not an identical implementation of a commercial game's mechanics. Bots are difficulty-scaled simulations, not a claim of human-equivalent play. Online multiplayer and battle royale are not implemented.

The accepted v3.2 artwork still has disclosed reference-matching gaps, including repeated fan-shaped grass and restrained timber/vehicle detail. Visual matching, device feel and performance remain review work; no “perfect match” claim is made. See [art direction](docs/ART_DIRECTION.md) and [match behavior and verification boundaries](docs/OFFLINE_MATCHES.md).

## Controls

| Action | Match input |
| --- | --- |
| Move / look | WASD / mouse; drag look if capture is unavailable |
| Sprint / slide | Shift / C after building sprint speed |
| Crouch / jump | X (or Ctrl) / Space |
| Fire / aim | Left / right mouse |
| Reload / inspect | R / I |
| Capture mouse / pause | F / Escape or P |
| Touch | Drag look; hold movement/Fire/Aim/Sprint/Crouch; tap Jump/Slide/Reload |

X avoids browser-reserved Ctrl shortcuts. Mouse release, tab hiding and window blur pause matches and clear held input. Slides cancel when support is lost, including exterior floor-drop endpoints. There is no prone, dive or mantle.

In the explorer, 1/2/3 select Freefly/First Person/Orbit, Q/E change freeflight height, and R resets freeflight or reloads the cosmetic explorer carbine. Freeflight deliberately passes through geometry. Start a match for combat targets and damage.

## Run locally

```sh
npm ci
npm run dev
```

Requires Node.js 22 and a current WebGL2 browser. `npm test`, `npm run lint` and `npm run build` run the portable regression gates and produce the production `dist/` folder. The map is committed as an 6,984,537-byte gzip; dev/build prepare its exact raw compatibility fallback. A differing local raw file is never silently overwritten. See [asset delivery](docs/ASSET_DELIVERY.md).

A production build can cache the complete current game after initial assets settle. Gzip-capable browsers save only the gzip map; others save only raw. Initial play does not wait for saving. The setup menu reports readiness, repair and update status. Updates require every open match to be idle and never automatically reload an active match. Browser storage can still be cleared. [Offline cache details](docs/OFFLINE_CACHE.md).

Dependencies and assets are same-origin. There is no account, analytics, multiplayer server, purchase flow or external asset CDN.

## Publish and verify

The GitHub Actions workflow tests/builds main-branch pushes and deploys `dist/` to GitHub Pages. Pull requests run checks without publishing. See [contribution guidance](CONTRIBUTING.md), [runtime QA](docs/qa/QA_PLAN.md) and [gameplay research](docs/GAMEPLAY_RESEARCH.md).

Portable verification covers authored collision routes, perimeter walks/jumps, real-map gameplay/cover, shader compile/link, full main-module lifecycle, input, HUD, audio graph lifetime, offline cache integrity and update races. Main-module tests use a DOM model/no-op renderer, with authored geometry tested separately from placeholder textures. These are not actual browser GPU, touch-layout, audio playback, disconnected browser reload or device-FPS acceptance. The review browser currently cannot provide WebGL2; the app shows an honest static source preview in that case.

## Map proportions and provenance

Structure is traced from the publisher's classic Nuketown minimap and checked against original-game views. House families, roofs, garages, rear stairs and street landmarks are independently authored. [The structural brief](docs/MAP_STRUCTURE_PLAN.md) separates image proportions from inferred details. Displayed meters use a provisional 10.5m bus calibration, not an authenticated game survey. Canonical frames, spawns, outline and viewpoint coordinates are preserved in this gameplay/style increment.

All included map, rifle and atmospheric art was created for this project. Call of Duty and VALORANT are design references; the project is not affiliated with their publishers and contains no extracted commercial game assets. User reference images are visual direction, not redistributed textures. No open-source art license is assigned by this repository. Third-party dependency licenses remain with their authors.

## Editable v3.2 source

The [native source package](source-assets/map-v32/README.md) preserves the full editable scene and original module/texture snapshots. Its safe Python extractor recreates the exact native Blender bytes without overwriting different local edits.
