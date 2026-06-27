# Casual Game Feel — Juice Checklist

Casual games are sold on feedback. Aim for short, snappy effects on every core action; nothing should feel dead. Tune values in Play Mode and confirm with a screenshot/recording.

## On the core action (tap / match / collect / land)
- [ ] **Squash & stretch** — quick non-uniform scale punch (~0.1–0.2s), eases back.
- [ ] **Pop / scale tween** — DOTween or a coroutine; overshoot then settle.
- [ ] **Particle burst** — pooled particle pop at the contact point.
- [ ] **Score popup** — pooled world/screen-space `+N` that rises and fades.
- [ ] **Sound hook** — emit an audio event (assets via `unity-audio-generator`).
- [ ] **Haptic (iOS)** — light tap on collect, medium/heavy on big hits; behind a setting.

## On impact / fail
- [ ] **Screen shake** — small camera offset that decays back; scale by impact, never nauseating.
- [ ] **Hit-stop** — brief `Time.timeScale` dip (~0.05s) on heavy hits, then restore.
- [ ] **Flash / color punch** — quick tint or material flash on the hit object.
- [ ] **Clear fail feedback** — readable game-over moment, then a fast restart.

## Motion & camera
- [ ] **Smoothed follow** (`SmoothDamp`/Lerp), not a rigid snap; a little look-ahead in the move direction.
- [ ] **Anticipation/follow-through** on jumps/launches (squash before, stretch during).
- [ ] **Easing**, not linear, on UI and object tweens.

## Pacing
- [ ] **Difficulty ramps** (speed / spawn density) so early seconds are easy and forgiving.
- [ ] **Reward cadence** — frequent small wins (coins, combos, pops) keep the loop satisfying.
- [ ] **Snappy restart** — back into play in well under a second; no long screens.

## Guardrails
- [ ] Effects are **pooled** and allocation-free in the run loop.
- [ ] Shake / hit-stop / haptics are **subtle and tunable**; respect a reduce-motion / haptics-off setting.
- [ ] Feedback never blocks input or hides the next decision.
