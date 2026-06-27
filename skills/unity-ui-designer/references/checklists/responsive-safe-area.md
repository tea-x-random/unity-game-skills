# Checklist — Responsive & Safe Area (iOS portrait)

Pass every item before claiming UI is responsive and device-safe. Verify with screenshots at multiple resolutions.

- [ ] **Safe area respected** — no interactive or critical UI under the notch / Dynamic Island or behind the home indicator. uGUI: a `SafeArea` component drives a RectTransform from `Screen.safeArea`. UI Toolkit: root padding from `Screen.safeArea` (or USS safe-area padding).
- [ ] **Scales across aspect ratios** — verified on a tall phone (~19.5:9, e.g. 1170x2532) and a short one (~4:3, e.g. 1536x2048); no clipping, overlap, or off-screen elements.
- [ ] **No absolute pixel layout** — uGUI uses Canvas Scaler (Scale With Screen Size, ref 1080x1920, Match ~0.5) with edge/corner anchors; UI Toolkit uses flexbox + percentage sizing, not fixed-px containers.
- [ ] **Touch targets >= ~44pt** — every tappable element is at least ~44x44 pt (~88x88 px @2x); hit area padded even when the icon is smaller.
- [ ] **Spacing** — adjacent buttons spaced so a thumb cannot hit two at once.
- [ ] **Thumb-reachable** — primary actions sit in the bottom reachable zone for one-handed portrait play; passive readouts up top.
- [ ] **Orientation/resolution change handled** — layout recomputes when `Screen.safeArea`/resolution changes (no stale anchors).
- [ ] **Portrait verified by screenshot** — `manage_scene(action="screenshot")` at real phone resolution confirms the layout, not an assumption.
