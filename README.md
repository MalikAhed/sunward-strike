# Sunward Strike

A lightweight original browser FPS project with a stylized SUNWARD arena. The first milestone is a playable scene viewer for inspecting the current map and rifle while the offline game is developed.

[Open the public map explorer](https://malikahed.github.io/sunward-strike/)

## Current milestone

- SUNWARD v2.5 environment with embedded textures and unchanged source layout
- Unrestricted freeflight, orbit overview and six named viewpoints
- First-person capsule collision, gravity and jumping
- Revision2 carbine with cosmetic fire, reload, inspect and aim-down-sights
- Three graphics settings and touch movement controls
- Bundled Three.js and relative asset paths for static hosting

Combat damage, enemies, sliding, TDM and Kill Confirmed match rules are **not implemented in this first viewer**. Offline bots, adjustable difficulty and mode rules are specified in [the gameplay research and plan](docs/GAMEPLAY_RESEARCH.md). Battle royale is a later phase.

Visual direction follows warm faceted painted surfaces, blue sky with cream clouds, and yellow-green vegetation. Existing foliage is preserved; a denser grass pass remains open. See [art direction and review gates](docs/ART_DIRECTION.md).

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

Requires Node.js 22 and a current WebGL2 browser. `npm test` runs deterministic movement math checks; `npm run build` produces `dist/`. Dependencies are bundled and assets are served from the same origin; there is no analytics, login, multiplayer server, purchase flow or external asset CDN.

## Publish

The included GitHub Actions workflow builds and tests every main-branch push, then deploys `dist/` to GitHub Pages. Enable **Settings → Pages → Source: GitHub Actions** on this repository. Pull requests run build/tests without publishing.

See [contribution and verification guidance](CONTRIBUTING.md), [runtime QA](docs/qa/QA_PLAN.md), and [gameplay research](docs/GAMEPLAY_RESEARCH.md).

## Art and provenance

All included map and rifle assets were created for this project. Call of Duty and VALORANT are design references only; the project is not affiliated with their publishers and contains no extracted commercial game assets. User reference images are visual direction, not redistributable game textures. No open-source license is assigned to project art by this repository. Third-party dependency licenses remain with their authors.
