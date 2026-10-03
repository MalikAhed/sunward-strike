# Sunward Strike

A lightweight original browser FPS project with a stylized SUNWARD arena. The first milestone is a playable scene viewer for inspecting the current map and rifle while the offline game is developed.

[Open the public map explorer](https://malikahed.github.io/sunward-strike/)

## Current milestone

- SUNWARD v3 environment with a reference-traced irregular arena, corrected angled house families, original textures and denser grass
- Unrestricted freeflight, orbit overview and six named viewpoints
- First-person capsule collision, gravity, jumping and bounded grounded ramp adhesion
- Revision2 carbine with cosmetic fire, reload, inspect and aim-down-sights
- Three graphics settings and touch movement controls
- Bundled Three.js and relative asset paths for static hosting

Combat damage, enemies, sliding, TDM and Kill Confirmed match rules are **not implemented in this first viewer**. Offline bots, adjustable difficulty and mode rules are specified in [the gameplay research and plan](docs/GAMEPLAY_RESEARCH.md). Battle royale is a later phase.

Visual direction follows warm faceted painted surfaces, blue sky with cream clouds, and yellow-green vegetation. Folded grass tufts soften the yard edges while preserving circulation routes. Full visual matching and device-specific performance remain review goals. This structural increment still has empty house shells; corrected furnishings and richer tree/lawn art are the next visual increments. See [art direction and review gates](docs/ART_DIRECTION.md).

## Controls

| Action | Input |
| --- | --- |
| Fly or walk | W / A / S / D |
| Ascend / descend in freeflight | E / Q |
| Move faster | Shift |
| Look | Drag scene; F captures mouse |
| Release mouse | Escape |
| First person / freeflight / overview | 2 / 1 / 3 |
| Jump in first person | Space |
| Cosmetic fire / aim | Left / right mouse while captured |
| Reload / inspect | R / I |
| Reset freeflight camera | R or Reset view |

Freeflight intentionally passes through objects. First-person mode uses the collision export. Browser pointer capture is optional; drag-look remains available.

## Run locally

```sh
npm ci
npm run dev
```

The map is committed as a 6.12 MB gzip asset. Both `npm run dev` and `npm run build` first prepare an exact raw GLB compatibility fallback; a differing local raw export stops preparation instead of being overwritten. See [asset loading and fallback behavior](docs/ASSET_DELIVERY.md).

Requires Node.js 22 and a current WebGL2 browser. `npm test` runs deterministic movement, exported collision, boundary and shader regression checks; `npm run build` produces `dist/`. Dependencies are bundled and assets are served from the same origin; there is no analytics, login, multiplayer server, purchase flow or external asset CDN.

## Publish

The included GitHub Actions workflow builds and tests every main-branch push, then deploys `dist/` to GitHub Pages. Enable **Settings → Pages → Source: GitHub Actions** on this repository. Pull requests run build/tests without publishing.

See [contribution and verification guidance](CONTRIBUTING.md), [runtime QA](docs/qa/QA_PLAN.md), and [gameplay research](docs/GAMEPLAY_RESEARCH.md).

## Map proportions and validation

Structure is traced from the publisher’s classic Nuketown minimap and checked against original-game views. House families, roof types, garages, rear stairs and street landmarks are independently authored. [The structural reference brief](docs/MAP_STRUCTURE_PLAN.md) distinguishes measured image proportions from inferred details. Absolute original game dimensions are unavailable: displayed meters use a provisional 10.5m bus calibration, not an authenticated survey.

The cloud test browser cannot create WebGL2. Export/re-import checks, actual capsule simulations, offline GLSL compilation and static delivery checks do not prove a live browser render or a particular GPU frame rate. [The acceptance register](docs/qa/SHARED_REVIEW.md) records the evidence and remaining checks.

## Art and provenance

All included map and rifle assets were created for this project. Call of Duty and VALORANT are design references only; the project is not affiliated with their publishers and contains no extracted commercial game assets. User reference images are visual direction, not redistributable game textures. No open-source license is assigned to project art by this repository. Third-party dependency licenses remain with their authors.
