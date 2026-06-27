# iOS Build Checklist

All via `manage_build` / `execute_code` through MCP. Output is an **Xcode project folder, not an `.ipa`**.

## Settings
- [ ] Active platform switched: `manage_build(action="platform", target="ios")`.
- [ ] `bundle_id` set and matches App Store Connect + provisioning profile.
- [ ] `product_name`, `company_name`, `version` set.
- [ ] Build number set (here or later in Xcode).

## Backend / pipeline
- [ ] `scripting_backend = il2cpp` confirmed (iOS **requires** IL2CPP; Mono not allowed).
- [ ] Deployment target >= **iOS 13** (Unity 6 minimum).
- [ ] Build Profile `profile` param used **only on Unity 6+**; omitted on older Unity.

## Scenes
- [ ] All needed scenes added via `manage_build(action="scenes", ...)`.
- [ ] First enabled scene is the intended launch scene; order correct.

## Textures (known compression bug)
- [ ] **ASTC verified** for iOS via `execute_code` / `TextureImporter` overrides — do NOT trust defaults.
- [ ] ASTC verification log read and saved as evidence.

## Stripping
- [ ] `Assets/link.xml` preserves reflection/serialization-used types.
- [ ] Stripped build tested, not just the Editor.

## Build
- [ ] `manage_build(action="build", target="ios", output_path="Builds/iOS/<name>")` run.
- [ ] `manage_build(action="status")` polled to finished, no errors.
- [ ] Output Xcode project folder exists at the path.

## Truth check
- [ ] Reported as "Xcode project generated", NOT "app built/signed/shipped" (those are manual macOS steps).
