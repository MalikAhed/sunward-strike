# SUNWARD offline arena

SUNWARD is an original small-map browser FPS with local Team Deathmatch and Kill Confirmed matches. It uses the authored classic-layout reference map and original artwork. It is a prototype with an independent movement, recoil and damage model, not an identical reproduction of a commercial game.

## Play

Choose **Play offline**, a mode, Recruit/Regular/Veteran difficulty, and 2v2–4v4 teams. The human occupies one blue-team slot. TDM awards an objective point per enemy elimination; Kill Confirmed requires collecting an enemy tag, while friendly tags deny that point. Difficulty changes bot perception and decisions, not health or weapon damage. Normal rounds run five minutes or until 50 TDM points / 35 KC points.

- WASD: move; Shift: sprint; C: slide after building sprint speed
- X (or Ctrl): hold crouch; Space: jump
- Left mouse: fire; right mouse: ADS; R: reload; I: inspect
- F: request mouse capture; Escape/P: pause; H: controls
- Touch: drag the scene to look; hold movement/Fire/Aim/Sprint/Crouch; tap Jump/Slide/Reload
- If mouse capture fails, on-screen actions remain available with drag-to-look

All actors and explorer walking use the accepted finite-contact capsule controller. Actors share the same movement and opaque-visual cover queries, weapon rules and health pool. The simulation runs fixed ticks independently of display cadence. Capsule hits, obstruction, damage, reload, respawn, score and tags are authoritative in the local match; bot meshes, tracers, sound and HUD only present that state. Blue allies block shots and friendly fire is disabled. Spawn protection is brief and ends when the actor fires. A hit marker appears only on confirmed damage.

## Interruptions and accessibility

Mouse release, tab hiding, window blur and opening controls pause the match clock and clear held inputs. Death stops player actions while the match continues to the respawn timer. A result locks the round and offers replay or a return to the exact explorer view. Settings and results use keyboard-focusable modal controls. First Person, Freefly and Orbit exploration remain separate from gameplay.

Audio is optional, synthesized locally and never downloaded. Play/Resume/Unmute gestures are the only places that can activate audio. Fire, reload, confirmed hit, death and tag cues use a bounded voice pool; Pause and Mute stop live sources. Sound can be turned off in setup or muted from Pause.

## Repeat-play offline

Initial play does not wait for offline saving. The setup menu reports the actual cache state. A production build can save its exact shell, code and current assets with a service worker. It chooses the gzip map only when that browser supports gzip decompression; otherwise it saves the raw compatibility GLB. It does not save both representations for one client. All selected files must match the build's SHA-256 and byte count before **Saved for offline replay** appears.

A downloaded update waits. **Update & reload** checks every open SUNWARD tab, refusing activation if a match is active or a tab does not reply. A race that starts a match before activation prevents automatic reload; that page must reload before its next match. Cache quota/install failures leave online play usable. **Retry offline saving** repairs missing current-version entries. Storage can still be evicted by the browser, so this is not a guarantee against data deletion. Development mode does not install a worker.

## Verification boundary

Automated verification runs real gameplay and controller code with deterministic simulations, plus the actual main module against a tiny DOM model and a no-op renderer. It covers start/retry/repeated starts, held input, shooting/ammo, visibility and pointer-lock lifecycle, death/respawn, score/results/replay, explorer restoration, audio voice lifecycle, cache selection/integrity/failure/repair and update guards. Existing full-map traversal and shader compile/link checks are retained.

These are portable code and source checks. They do not establish browser GPU rendering, actual pointer lock, real audio playback, touch comfort, mobile layout/FPS, disconnected browser reload, or an identical commercial-game feel. Those remain device/browser acceptance work. Bot behavior is a difficulty-scaled prototype rather than a claim of human-equivalent play. Slides deliberately cancel when their supporting ground is lost, including the documented exterior ledge/drop endpoints. There is no prone, dive, mantle or online mode. Final art differences and device acceptance gaps remain separate from green portable tests.

Static opaque-cover queries use a triangle BVH over the same accepted geometry. The original cover backend remains available for exceptional numerical inputs; movement collision and match rules are unchanged. Selected deterministic CPU runs showed lower warmed update cost, at the expense of extra first-match construction and retained memory. The world remains cached across restarts. See the [exact scope, numerical regressions and measurement limits](qa/COVER_QUERY_R2.md).
