# Checklist — UI Readability

Pass every item before claiming a UI screen is done. Verify against a phone-resolution screenshot.

- [ ] **Legible sizes from the scale** — body/labels not tiny; sizes come from the named typography scale (not per-label literals — see `ui-consistency.md`); numbers that grow (score/coins) use auto-size within a sane min/max. No text below readable thresholds on a phone.
- [ ] **Crisp text** — uGUI uses TextMeshPro (SDF), not legacy `Text`; UI Toolkit fonts render sharp at panel scale.
- [ ] **Contrast** — text stands out from panel and from the world behind it (shadow/outline/scrim where needed); not light-on-light or dark-on-dark.
- [ ] **Consistent icons** — one icon family, consistent stroke/corner/palette; no mismatched placeholder art (generate with `unity-image-generator` if needed).
- [ ] **No overlap** — labels, icons, and buttons do not collide or stack; padding/spacing between elements.
- [ ] **Fits content** — longest expected values (big scores, long labels, localized text) fit without clipping or truncation; containers flex or auto-size.
- [ ] **Visual hierarchy** — most important readout (score/objective) is largest/most prominent; flavor is subordinate.
- [ ] **Art cohesion** — palette, corner radius, and font match the game's art direction.
- [ ] **Verified by screenshot** — readability confirmed on an actual phone-resolution capture, not assumed.
