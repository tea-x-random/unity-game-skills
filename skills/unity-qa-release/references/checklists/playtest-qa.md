# Playtest QA Checklist (pre-release)

Walk this before any release work. Each item needs evidence (screenshot, test, or console output) — not a guess.

## Core loop
- [ ] Game launches into the right scene; no errors on load.
- [ ] Core loop reachable by **touch only**: input → objective → win/lose → restart.
- [ ] Win path reachable and shows a win/result screen.
- [ ] Lose path reachable and shows a lose/result screen.
- [ ] Restart / next returns to a clean playable state (no carried-over bugs).

## Stability
- [ ] `read_console(types=["error","warning"])` — no errors, no warnings of note.
- [ ] No soft-locks: no state the player enters and can't leave (stuck menus, frozen input, dead result screen).
- [ ] No NullRef / MissingReference during a full playthrough.
- [ ] Pause/resume and app-backgrounding don't corrupt state.

## Input / touch
- [ ] Taps, drags, swipes all register.
- [ ] Touch targets reachable and >= ~44pt; thumb-zone friendly.
- [ ] No keyboard/mouse-only path required to progress.

## Resolution / display
- [ ] Plays and reads on tall/notched (~19.5:9), classic (~16:9), and short (SE-class) portrait.
- [ ] Screenshot per aspect ratio captured via `manage_scene(action="screenshot")`.
- [ ] Safe area respected: HUD/buttons clear of notch + home indicator; nothing clipped.
- [ ] Text fits (no overflow/truncation) at each aspect.

## Performance
- [ ] Frame rate stable across the loop; no obvious hitches.
- [ ] No runaway memory / spawning leak (pooling reuses).
- [ ] Deep profiling → route to `unity-debug-profiler` (`profiling` group); link results, don't hand-wave.

## Tests
- [ ] EditMode + PlayMode tests authored for scoring, spawning, win/lose, save/load.
- [ ] `run_tests` → `get_test_job` polled to completion; report counts + `job_id`.
