# SUNWARD STRIKE — Gameplay research and implementation specification

**Research date:** 3 October 2026 (UTC)  
**Scope:** Original browser FPS; offline Team Deathmatch and Kill Confirmed; fast engagements, controllable recoil, sprint/slide movement, readable stylized low-poly art, scalable opponents; Battle Royale later  
**Status:** Research and proposed design. Numeric targets and acceptance checks below are not measurements of Call of Duty, and do not establish that the current prototype implements or passes them. Runtime configuration and test reports are the authority for implemented behavior.

## 1. Decision and fidelity boundary

Build an original small-map arena shooter with **Modern Warfare III (2023) core multiplayer as the movement/mode comparison baseline**. Use **Black Ops 6 (2024) as a separate directional-movement and HUD reference**. The initial target is a convincing, fast, responsive feel, not a claim of identical proprietary mechanics.

“Call of Duty” is not one stable tuning specification. Exact comparison needs a title, platform, patch date, mode, weapon, attachments, hit location, distance, input settings, and movement state. Even published damage/recoil values do not specify all animation curves, randomness, camera behavior, input handling, bullet simulation, or networking. An initial browser build cannot credibly be certified “100% the same.” Official MWIII patch notes demonstrate that damage, ranges, sprint-to-fire, and recoil values changed between updates. [MWIII Season 6 patch notes, including 18 September 2024 balance changes](https://www.callofduty.com/patchnotes/2024/09/call-of-duty-modern-warfare-iii-season-6-patch-notes)

**Important tension:** MWIII announced 150 core HP expressly to lengthen TTK. A fast-TTK project should tune damage and fire rate against its own desired kill time rather than copy health in isolation. [MWIII worldwide reveal, 17 August 2023](https://www.callofduty.com/blog/2023/08/call-of-duty-modern-warfare-III-worldwide-full-reveal-announcement)

The references below are historical, explicit baselines. They are not assertions about the newest Call of Duty release or live playlist balance on the research date.

## 2. Primary-source evidence and its limited use

| Official source | Dated or accessed | Supported concept | SUNWARD use |
| --- | --- | --- | --- |
| [MWIII worldwide reveal](https://www.callofduty.com/blog/2023/08/call-of-duty-modern-warfare-III-worldwide-full-reveal-announcement) | Published 17 Aug 2023; accessed 3 Oct 2026 | Cancelable slides; cancel does not refill Tactical Sprint; firing during/after sliding; sprint recharge; unsuppressed-fire minimap pings | Responsive slide/cancel state transitions and time-limited gunfire pings; our own movement values |
| [BO6 movement guide](https://www.callofduty.com/guides/blackops6/training/call-of-duty-guides-black-ops-6-multiplayer-training-movement) | Published 23 Oct 2024; accessed 3 Oct 2026 | Slide starts from sprint, slows over time, can be canceled; omnidirectional regular sprint/slide/dive, but Tactical Sprint is forward-only | Optional any-direction slide, not a claim of full BO6 Omnimovement; diving/supine need separate implementation |
| [MWIII weapons detail](https://www.callofduty.com/blog/2023/11/call-of-duty-modern-warfare-III-launch-comms-weapons-detail) | Published 3 Nov 2023; accessed 3 Oct 2026 | Damage depends on hit region/range; fire rate, recoil, accuracy, mobility, and handling are separate attributes | Separate data for ballistic damage, shot cadence, spread, camera kick, recoil, ADS, reload, and movement |
| [MWIII Team Deathmatch guide](https://www.callofduty.com/guides/multiplayer-modes/call-of-duty-modern-warfare-iii-play-modes-team-deathmatch) | Page has no publication date shown; accessed 3 Oct 2026 | Unlimited lives; enemy eliminations score; assists do not raise team score; score/time victory | TDM rules, with our configurable score/time limits |
| [MWIII Kill Confirmed guide](https://www.callofduty.com/guides/multiplayer-modes/call-of-duty-modern-warfare-iii-play-modes-guides-kill-confirmed) | Page has no publication date shown; accessed 3 Oct 2026 | Eliminations drop tags; enemy tags confirm score; friendly tags deny it; score/time victory | Exact conceptual distinction between kill statistics and objective scoring |
| [BO6 worldwide reveal](https://www.callofduty.com/blog/2024/06/call-of-duty-black-ops-6-worldwide-reveal-announcement) | Published 9 Jun 2024; accessed 3 Oct 2026 | Clean configurable HUD presets; minimap, ammo, notifications; compact maps/quick time to engagement | Original readable HUD and small-map pacing; no copied artwork or layout assets |
| [Riot: The Art of VALORANT Map Environments](https://playvalorant.com/en-us/news/dev/the-art-of-valorant-map-environments/) | Published 16 Nov 2020; accessed 3 Oct 2026 | Greybox/playtest before art; accurate collision; simple sightlines, restrained value contrast and detail | Art follows proven arena layout; bold landmarks and uncluttered combat space |
| [Riot: VALORANT Shaders and Gameplay Clarity](https://www.riotgames.com/en/news/valorant-shaders-and-gameplay-clarity) | Published 30 Jun 2020; accessed 3 Oct 2026 | Balance art, performance, competitive clarity; distant character readability; quality changes should preserve gameplay information | Bright readable original silhouettes, stable visibility at every quality setting |

No source above supplies a complete recoil pattern or a full movement simulation that can be reproduced from the article alone. Our values are deliberately independent. Use original SUNWARD architecture, materials, weapon silhouettes, characters, UI marks, and sounds. Do not import ripped franchise assets, commercial map files, branded skins, logos, or audio. The later structural brief explicitly selects classic Nuketown as a layout/proportion reference; all delivered geometry, materials and branding are independently authored.

## 3. Proposed tuning contract

**All values in this section are candidate design targets, not COD facts and not a current-runtime inventory.** Keep the implemented configuration in one versioned module. Generate the in-game weapon stats and test expectations from that module; do not silently maintain a second copy of live tuning here.

### Combat candidates

| Attribute | AR candidate | SMG candidate | Purpose |
| --- | ---: | ---: | --- |
| Player/bot health | 100 | 100 | Same pool on every difficulty |
| Near-range body damage | 34 | 25 | Three AR or four SMG body hits |
| Fire rate | 660 RPM | 900 RPM | Distinct controllable and rapid-fire roles |
| Ideal near-range body TTK | 181.8 ms | 200.0 ms | First damaging shot to lethal shot, no misses |
| Head multiplier | 1.5× | 1.5× | Reward precision without one-shot automatic rifles |
| Full-damage range | 0–22 m | 0–12 m | SMG remains a close-range role |
| Far body damage | 25 beyond 40 m | 18 beyond 28 m | Longer engagements demand more accuracy |
| ADS transition | 180 ms | 140 ms | Fast, observable transition |
| Sprint-to-fire | 120 ms | 100 ms | A decision cost for aggressive sprinting |
| Magazine | 30 | 32 | Reload windows matter |
| Tactical / empty reload | 1.55 / 1.95 s | 1.35 / 1.75 s | Empty is meaningfully slower |

For constant damage, `shotsToKill = ceil(health / damage)` and `idealTTK = (shotsToKill - 1) × 60,000 / RPM` milliseconds. The first shot occurs at time zero. ADS, sprint-to-fire, misses, flinch, target acquisition, travel time (if projectiles are added), and reload are outside this ideal number. Measure input-to-kill separately. Mixed head/body hits need a sum of individual damage events rather than this simple formula.

Proposed recovery: begin regenerating after 4.0 seconds without damage at 35 HP/s. Any new damage restarts the delay. No armor for arena modes initially. Difficulty does not increase enemy HP or damage.

### Movement candidates

- Walk 4.6 m/s; sprint 7.6 m/s; crouch 2.5 m/s; grounded jump impulse 5.0 m/s
- Slide enters only while grounded, moving, and sprinting above a minimum speed; starts at 10.0 m/s and decelerates to 4.6 m/s over 0.65 s
- Slide intent uses horizontal movement direction, not forced camera direction; turning the camera does not teleport velocity
- Shrink collision height for the slide, not only camera height; restore standing height only after a ceiling-clearance test
- Crouch or jump may cancel after a short 0.12 s commitment window; cancel preserves existing velocity limits and does not refill a sprint resource
- A new slide needs renewed sprint speed and 0.45 s recovery, preventing stationary slide spam; grounded friction and air control are independent
- Sliding permits firing with 1.7× hip spread; ADS reduces spread after its transition, with its own slide handling penalty
- Normalize diagonal inputs; use swept collision/substeps at speed; camera lean/FOV/kick are presentation, not authoritative actor position

Forward-only sprint is the simpler MWIII-oriented initial option. Any-direction sprint/slide is a consciously selected BO6-inspired extension. “Slide available” does not establish diving, prone, supine, mantling, or full Omnimovement.

### Recoil and gun feel

Separate four effects: shot-direction recoil, visual weapon kick, camera kick, and random spread. A decorative weapon animation alone is not recoil. Start with an original seeded per-shot vertical-biased pattern, bounded horizontal variation, and spring recovery after the burst. Apply the accumulated aiming offset to subsequent shot direction, so a player can counter it with mouse movement. Avoid automatic return that undoes the player's manual compensation.

Give AR bursts lower horizontal variation and SMG bursts a larger spread envelope. ADS tightens spread; walking, jumping, and sliding widen it. Show recoil debug traces at a fixed wall distance and log aim/shot direction separately. Never copy a proprietary gun name or describe an arbitrary spring constant as a measured COD recoil value.

## 4. Offline browser architecture

These are implementation recommendations, not descriptions of Call of Duty's engine.

1. **Local authoritative simulation:** one world owns actors, health, collision, weapon cooldowns, deaths, tags, scoring, and clock. Rendering, HUD, sound, and input consume events/snapshots. A future multiplayer server can take over this interface; local authority is not online anti-cheat.
2. **Shared actor controller:** player and bots both emit an input command (`move`, `look`, `fire`, `ads`, `reload`, `jump`, `slide`). The same movement and weapon code enforces every rule.
3. **Fixed simulation step:** proposed 60 Hz initially, with interpolation for display and absolute simulation-time shot scheduling. Do not make speed, reaction, recoil recovery, or shot cadence depend on render FPS. A 60 Hz step quantizes observed events; logged TTK should allow one tick or use sub-tick shot timestamps. Evaluate 120 Hz only after profiling.
4. **Seeded randomness:** separate streams for recoil/spread and bot decisions. Record seed, commands, settings, and events for repeatable regression matches.
5. **Pause by explicit policy:** clear held input on focus loss; stop the match clock and simulation when the menu/pointer unlock pauses play; discard large wall-time deltas when resuming. `requestAnimationFrame` generally follows display refresh and may pause in background tabs, so it cannot define gameplay time by itself. [MDN: requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
6. **Pointer lock:** request it from the player's Start/Resume gesture, handle both change/error events, and expose an Escape pause/visible Resume flow. The browser may require a fresh engagement gesture after unlocking. [MDN: Pointer Lock API](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_Lock_API)
7. **True offline packaging:** bundle dependencies and art locally. “No server required during a match” is distinct from “cold-start offline.” Cache the app shell and every runtime asset with a versioned service worker on HTTPS/localhost, or provide a local-served distributable. Test a disconnected reload after install; browser storage eviction can still remove cached content. Service workers support request interception/caching and require secure contexts. [MDN: Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)

Use an event pipeline: `ShotFired → HitResolved → DamageApplied → ActorKilled → TagCreated/TeamScoreChanged → MatchEnded`. Death and tag pickup must be idempotent: an event/entity can be resolved once. A dead actor cannot fire or collect, even if a render animation still runs.

## 5. Humanlike bot model

“Humanlike” is a behavioral goal requiring tests and playtesting, not something established by random strafing or instantly pointing at the player.

### Perception and fairness

- Maintain a bot-local perception snapshot. Read opponents only through range, field-of-view, and occlusion checks from the bot eye position to multiple target points
- A gunshot or footstep produces a perceived event with attenuated range and position uncertainty; it does not reveal an exact live actor position through every wall
- Store a last-seen position, velocity estimate, confidence, and timestamp. On occlusion, chase/search that memory; decay it instead of continuously reading the hidden target
- Require target acquisition plus reaction delay before firing. Cap angular turn rate/acceleration; use lagged tracking, correlated aim error, bursts, imperfect recoil compensation, and occasional over/undershoot
- Use the same obstruction ray, spread, magazine, reload, sprint-to-fire, damage, and slide rules as the player. No hits through solid walls; no spawning or teleporting to rescue navigation
- Difficulty changes skill and decision quality, never secret visibility, increased bullet damage, or invulnerability

### Decision states and goals

A compact hierarchical state machine is enough for the first arena:

`Spawn → Patrol/Regroup → Investigate → Engage → Flank/Reposition → Retreat/Reload → Search → Patrol`; death interrupts all states and enters `Dead → Respawn` where the mode permits.

Use utility scores for available goals: confirm enemy tag, deny friendly tag, seek cover, recover health, reload, support ally, investigate noise, or take a flank. Switch only when the new goal exceeds the current one by a margin, with a minimum commitment time to avoid frantic oscillation. Assign route/role variation once per life; enemies should not all pick the shortest identical path.

### Navigation and sliding

Start with a validated waypoint graph or a walkable grid inflated by actor radius. Use A* for route planning, local avoidance for neighbors, and collision-aware segment following. Mark cover/peek points, safe reload positions, routes, jump/slide-clearance links, and spawn exclusion zones. If a bot fails to make route progress for 0.8 s, replan; after repeated failure, blacklist the link briefly and choose a reachable goal. Do not push the bot through a wall.

For more complex or vertical maps, use a baked navmesh. Recast handles generation; Detour provides pathfinding/queries; DetourCrowd handles movement/avoidance. The C++ project is a future architecture option, not a browser dependency assumed to be installed. [Official Recast Navigation repository](https://github.com/recastnavigation/recastnavigation)

A bot should slide for a reason: cross a short exposed lane, reach cover, enter a contested tag area, or reposition during a close-range fight. Check entry speed, swept path, endpoint, recovery/cooldown, and tactical benefit before choosing it. Predict slide overshoot and avoid initiating at a wall, ledge, or blocked doorway. Use the same movement controller as the player. Add debug state/goal/path/LOS overlays, hidden by default.

### Proposed difficulty profiles

All values are our initial targets. Angular error is correlated tracking error, not a per-frame independent jitter.

| Difficulty | Acquisition reaction | Typical angular aim error | Max turn rate | Behavior |
| --- | ---: | ---: | ---: | --- |
| Recruit | 450–700 ms | 3.0–5.0° | 240°/s | Short bursts, obvious routes, infrequent slides |
| Regular | 280–450 ms | 1.5–2.8° | 360°/s | Uses cover, opportunistic tags, occasional flanks/slides |
| Veteran | 180–300 ms | 0.7–1.6° | 520°/s | Better prediction, controlled bursts, cover-to-cover slides |

Sample values per encounter/personality; do not give every bot an identical rhythm. Reacquisition, target switching, surprise direction, and low confidence may add delay. A cap is not permission for instant turns. Veteran still loses visibility behind cover and still misses. Keep bot count separate from skill; expose both to the player.

### Scalability

Spatially index actors and colliders; stagger LOS checks and path replans. Suggested initial rates: close combat perception 10–15 Hz, far perception 3–5 Hz, utility decisions 5 Hz, path replans only on goal/obstacle changes. Motor, collision, and weapon simulation stay on the fixed tick. Preserve minimum reaction delay while throttling AI. Pool short-lived particles/tags, instance repeated scenery, and profile before claiming a supported bot count.

## 6. Modes and HUD contract

### Team Deathmatch

- Two teams; initially one human plus a configurable number of friendly/enemy bots
- Exactly one team point per enemy elimination; assists tracked separately; friendly fire off for the first build
- Respawn after a proposed 2.0 s delay; health/magazine reset; choose among candidates outside recent enemy LOS and with safe distance
- End on configured score limit or timer; explicit draw if tied; lock all scoring after match end
- Suggested prototype match: 50 eliminations or 5 minutes, independently configurable

The official guide's typical public limits are contextual examples, not a mandate to copy them. [MWIII TDM guide](https://www.callofduty.com/guides/multiplayer-modes/call-of-duty-modern-warfare-iii-play-modes-team-deathmatch)

### Kill Confirmed

- Enemy elimination increments kill statistics and creates one tag; it does **not** increment team objective score
- Opposing team collecting that tag gains one confirmation; victim's team collecting it records a denial and removes it without an objective point
- Store `victimTeam`, death ID, location, creation time, and resolution state on each tag; color/icons are relative to the viewing team
- Proposed pickup radius 1.25 m; no pickup through a solid wall; tag expires after 20 s without score
- Resolve simultaneous pickup deterministically (simulation tick then actor ID); only one recipient and at most one score change
- Bots value confirmations and denials, assess exposed tags, and sometimes guard or flank an unsafe pickup instead of blindly rushing it
- Suggested prototype match: 35 confirmations or 5 minutes; clear draw rule

These values are ours; the source supports the confirm/deny objective distinction. [MWIII Kill Confirmed guide](https://www.callofduty.com/guides/multiplayer-modes/call-of-duty-modern-warfare-iii-play-modes-guides-kill-confirmed)

### Original readable HUD

Show team score/limit, timer, mode, ammo/reserve, reload, health, crosshair, hit confirmation, short killfeed, and respawn/result states. KC additionally needs distinct confirm/deny tag markers and totals. Minimap shows teammates and public objective information; enemy blips are short-lived gunfire or actual perception events, not an unexplained omniscient radar. Add high-contrast/colorblind-friendly icons and shape differences, not color alone. Keep important center-screen cues readable over both bright sky and dark interiors. Recoil/motion accessibility settings can reduce cosmetic shake without silently changing bullet mechanics.

## 7. Arena/art plan

Greybox three connected combat routes with cross-links, at least one safe rotation, staggered cover, and no universal uninterrupted spawn-to-spawn sightline. The initial pacing target is roughly 5–12 seconds from a safe spawn to a plausible encounter, measured in playtests rather than assumed from map size.

Use an original sunlit coastal/solar-industrial identity: warm masonry, teal/turquoise structural accents, solar machinery, broad sky shapes, readable route landmarks. Restrict fine detail at head/weapon height; spend visual richness above combat sightlines and outside playable boundaries. Simple materials need purposeful color/value design and silhouette work, not only box geometry. Use team-distinct character regions/outlines with sufficient contrast at distance. Visual mesh, ballistic occluder, and physical collision must agree. Review both standing and sliding eye heights.

## 8. Milestones and acceptance gates

The checklist is a validation plan; passing requires a saved test/QA report against the actual build.

1. **Movement/combat range:** mouse look, focus/escape/resume, collision, sprint, slide/cancel, ADS, fire, reload, recoil, damage, regeneration. Gate: repeatable movement and shot traces at 30/60/120 display FPS; no diagonal speed bonus; no slide tunneling; no firing during invalid states
2. **Arena TDM:** player, teams, simple fair bots, spawns, HUD, match clock/results. Gate: an entire match ends correctly; restart resets every actor/event/timer; scores increment once; spawn safety is exercised under pressure
3. **Kill Confirmed:** tags, confirmations, denials, bot tag goals. Gate: enemy/friendly pickup, expiration, wall separation, simultaneous pickup, death/restart races, and match-end lockout all have deterministic tests
4. **Bot believability:** perception memory, turn/reaction limits, utility states, cover, sliding, navigation recovery, difficulty profiles. Gate: bots lose hidden targets, miss plausibly, reload, collect/deny tags, use multiple routes, and slide without collision shortcuts
5. **Polish/offline/performance:** art, sound, impact clarity, accessibility, cache/install path. Gate: disconnected reload succeeds after installation; zero runtime CDN calls; paused sessions do not advance; named test device sustains target frame time at each documented bot count
6. **BR vertical slice later:** separate elimination rules, streamed larger map, loot/inventory, shrinking safe zone, squad lifecycle, spectator/end states. Gate: an offline small-population match reaches a single winning player/team without arena respawn rules leaking in

### Concrete regression tests and metrics

- **Ballistics/TTK:** range and hit-zone damage, actual shot intervals, fixed-health kill sequence, ADS/sprint-to-fire elapsed times, recoil trace under fixed seed. Ideal TTK agrees with configured values within one simulation tick
- **Walls/fairness:** place the human behind a solid wall with no recent sight/noise; bot cannot acquire/fire an exact solution. If previously seen, last-known-position search is allowed, live tracking is not
- **Motor fairness:** replay identical commands for player/bot controllers and compare velocity, collision, slide duration, reload, and shot eligibility
- **Reaction/aim:** log first valid perception to first shot, angular speeds, hit rate by range, and target-switch delay. Assert no negative/instant reaction or angular jumps above configured limits
- **Navigation:** all authored spawns/objectives mutually reachable; random reachable goals do not remain stuck; slides stop at obstacles without penetration; bot recovery replans rather than teleporting
- **Modes:** 100 synthetic death/tag events score correctly once; friendly denials never raise objective score; restart removes stale tags; results cannot change after end
- **Pacing:** record spawn-to-first-contact, encounter duration, deaths in first two seconds after spawn, route heatmap, tag objective participation, slides per life, and time spent stuck/reloading
- **Performance:** profile 6, 10, then 16 total actors on a named device; target p95 frame time ≤16.7 ms for a 60 FPS tier, with separate simulation/AI/render costs. This is a target, not a claim of present performance
- **Playtest:** three short sessions per difficulty; ask whether deaths felt explainable, aim felt controllable, movement rewarded intent, and bots used believable information. “Humanlike” requires this qualitative evidence alongside logs

## 9. Later Battle Royale boundary

A BR mode is a new lifecycle rather than TDM on a larger map. The historical Warzone guide supports the broad concepts of last player/squad surviving, loot, and a phased shrinking playable zone. Its specific Gulag, economy, map, and redeploy details are not requirements for SUNWARD. [Official Warzone how-to-play guide, accessed 3 October 2026](https://www.callofduty.com/guides/training/call-of-duty-guides-warzone-how-to-play)

Reserve clean interfaces now: `ModeRules`, actor inventory, damage sources, spatial chunks, squad membership, world hazards, and spectator state. Later add original loot and scarcity, zone transitions/telegraphing, armor policy, team elimination/optional revival, and bot rotation/looting decisions. Budget streaming and AI relevance independently from combat skill. Start with a modest offline population; do not promise 100 bots, vehicles, networking, or proprietary Warzone equivalence before a measured vertical slice.

## 10. If closer reference matching is requested

Freeze the precise title/patch/mode/loadout and obtain lawful original reference recordings or user-supplied measurements. Measure movement distance over time, slide entry/exit speed, cancel timings, ADS/sprint-to-fire/reload, fixed-distance shot intervals, hit-region/range damage, recoil wall traces, and cosmetic camera curves. Document resolution/FOV/sensitivity/frame rate and uncertainty. Compare distributions across repeated trials, not one clip. Keep our independent art and branding. Promise only the tolerances measured and passed; “100% identical” remains unsupported without exhaustive coverage of the unspecified system.
