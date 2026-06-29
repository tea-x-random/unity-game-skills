# External benchmark workflow for Unity game skills

Use this workflow when improving `unity-game-skills` from popular/official Unity pipeline practices, third-party workflows, community pain points, and shipped-game production patterns. The goal is not to copy a tool, but to convert repeated findings into deterministic skill gates, scripts, templates, or references.

## 1. Scan sources in this order

Prefer primary/official sources first, then popular community pain points:

1. Unity Manual / Scripting API / Learn / official e-books
   - Sprite Atlas, Texture Importer, Presets/Preset Manager, AssetPostprocessor, Addressables, 2D Renderer, 2D Lights, Sprite Libraries, Tilemaps.
2. Unity official Discussions / technical articles
   - Look for new best-practice guides, especially import settings, mobile optimization, Sprite Atlas, Addressables, and 2D lighting.
3. High-signal community threads
   - Repeated pain points are more useful than one-off opinions: draw calls not decreasing, import settings forgotten, addressable groups too fragmented, manual prefab setup, atlas/compression surprises.
4. Tool categories, not specific clones
   - TexturePacker/Spine/Aseprite/Addressables/AssetGraph-like tools are useful as workflow patterns: manifest, deterministic import, atlas, bake/export, validate, registry.

## 2. Capture findings as cards

For every candidate finding, write a card:

```yaml
finding_id: sprite_atlas_family_pack
source_type: official | community | tool-pattern
source_url: https://...
popularity_signal: official guide | repeated forum pain | common marketplace category
problem: many independent sprite textures increase draw calls and memory pressure
practice: pack related sprites into Sprite Atlases by family/layer/use-case
pipeline_change: add atlas_group to asset contract + registry; validate atlas membership before approval
skill_targets: [unity-asset-pipeline, unity-image-generator, unity-qa-release]
acceptance_gate: prefab's SpriteRenderer sprite is in expected atlas; frame stats show batched draw calls in BeautyCell
status: proposed | implemented | rejected
```

## 3. Promotion criteria

Promote a finding into the repo only if at least one is true:

- It is official Unity guidance.
- It prevents a failure observed in our generated output.
- It appears repeatedly in community/tool workflows.
- It converts a manual/forgotten step into an enforceable contract or validator.

Reject findings that are only aesthetic taste, too project-specific, or push every game toward a heavy pipeline when a lightweight gate is enough.

## 4. Patch pattern

Convert the finding into the narrowest durable artifact:

- **Contract field** if scene/build agents need machine-readable data.
- **Validator** if bad output can be detected automatically.
- **Editor snippet/tool** if Unity must apply or verify the setting.
- **Skill rule** if judgment/routing is required.
- **Reference file** if the details are useful only in that branch.

Then add a test or dry-run where practical.

## 5. Current benchmark backlog

Implemented in this repo:

- Sprite Atlas / atlas groups: add `atlas_group` + registry fields and validation guidance.
- Import automation: add Presets/AssetPostprocessor guidance so import settings are defaults, not manual reminders.
- Addressables metadata: add addressable group/labels to asset contracts and registry.
- 2D lighting readiness: add optional secondary textures / normal-mask map contracts for assets that use 2D lights.
- In-engine validation: BeautyCell and screenshot gates remain the final acceptance proof.

Next candidates:

- Frame Debugger / stats-based draw-call gate for BeautyCell.
- Automated SpriteAtlas existence/membership validator in Unity Editor C#.
- Addressables Analyze gate for registry groups.
- Texture-memory budget report from imported assets.
- Rendered screenshot perceptual-diff gate per device aspect.

## Seed sources used for the current pass

Use these as the first official-source checks in the next benchmark pass:

- Unity Manual — Sprite Atlas: https://docs.unity.cn/2022.1/Documentation/Manual/class-SpriteAtlas.html
- Unity Scripting API — AssetPostprocessor / OnPreprocessTexture: https://docs.unity.cn/ScriptReference/AssetPostprocessor.html and https://docs.unity.cn/ScriptReference/AssetPostprocessor.OnPreprocessTexture.html
- Unity Manual — Presets / Preset Manager: https://docs.unity.cn/2021.1/Documentation/Manual/Presets.html and https://docs.unity.cn/2022.1/Documentation/Manual/class-PresetManager.html
- Unity Addressables — Groups / labels: https://docs.unity.cn/Packages/com.unity.addressables%401.19/manual/Groups.html and https://learn.unity.com/course/get-started-with-addressables/tutorial/label-addressable-assets
- Unity Manual — URP 2D Secondary Textures: https://docs.unity.cn/6000.0/Documentation/Manual/urp/SecondaryTextures.html
