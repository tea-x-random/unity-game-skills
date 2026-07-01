# Style preset library

Choose **exactly one** primary preset (optionally one named secondary influence). Preset names below are unversioned; the per-game `style_id` written into `art-spec.yaml` is the canonical versioned form **`<preset>_v<N>`** (e.g. `cozy_toy_diorama_v1`) and must appear verbatim in every `asset-contract.yaml` and `composition.yaml`. References are **broad direction only** — never request a clone of a specific living artist, game, character, or proprietary asset; translate the intent into the project's own shape, palette, material, and lighting rules.

> Keep **style** distinct from **genre** and **camera**. Style = the visual grammar; genre = the gameplay; camera = the projection/angle.

| style_id | Reference language | Best camera | Visual grammar | Good fit |
|---|---|---|---|---|
| `painterly_cel_fantasy` | Storybook adventure | Third-person, elevated 3/4 | Watercolor gradients, soft cel shadows, rounded natural forms, saturated landmark colors | Adventure, collection, exploration |
| `heroic_handpainted_fantasy` | Hand-painted heroic fantasy | Isometric, 3/4 | Chunky silhouettes, oversized props, hand-painted color variation, warm/cool contrast | Casual RPG, town builders, card games |
| `stylized_isometric_mmo` | Readable sandbox MMO | Orthographic isometric | Practical medieval geometry, clean ground readability, low texture noise, strong player/item contrast | Social RPG, survival, simulation |
| `anime_action_rpg` | Polished anime fantasy | Third-person, 3/4 | Crisp forms, controlled highlights, expressive proportions, gradient color design, high VFX clarity | Action RPG, gacha, character collection |
| `dark_gothic_fantasy` | Dark mythic action | Third-person, isometric | Deep value range, aged metal/stone, sharp silhouettes, selective emissive accents | Roguelite, dungeon crawler |
| `cozy_toy_diorama` | Playful miniature world | Orthographic, top-down | Rounded forms, soft bevels, matte materials, pastel/earthy palette, shallow depth cues | Puzzle, farming, idle, kids/family |
| `lowpoly_atmospheric` | Graphic low-poly exploration | Third-person, top-down | Deliberate facets, broad gradients, fog, restrained detail, color-blocked terrain | Exploration, survival, relaxing games |
| `hd2d_pixel_fantasy` | Pixel art with modern depth | Side, top-down, 3/4 | Pixel grid is sacred, limited palette, sprite-first assets, modern lights only as accents | 2D RPG, tactics, roguelite |
| `clean_graphic_casual` | Premium mobile puzzle | Orthographic, fixed | Simple geometry, near-flat materials, high spacing discipline, 2–4 dominant colors | Puzzle, word, match, utility-like games |
| `soft_clay_character` | Clay / plush / tactile casual | Orthographic, close 3/4 | Soft round forms, diffuse response, subtle imperfections, large features | Casual character games, kids/family |
| `stylized_scifi` | Clean futuristic action | Third-person, isometric | Hard-surface panels, controlled emissives, dark neutral base + one accent color | Shooter, racer, strategy |
| `cinematic_pbr_realism` | Filmic realistic world | Third-person | Physically plausible materials, measured texture scale, high lighting discipline | PC/console only unless scope is very small |

## Recommended starting points (casual iOS)

- **`cozy_toy_diorama`** — puzzles, idle, social, broadly-appealing games.
- **`heroic_handpainted_fantasy`** — approachable "premium game" feel with strong UI/collectible potential.
- **`clean_graphic_casual`** — premium puzzle/word/match where one-second readability wins.
- **`stylized_isometric_mmo`** — readable 2.5D/isometric multiplayer worlds.

Avoid `cinematic_pbr_realism` for a small iOS team unless the game is intentionally sparse — highest asset, lighting, texture-memory, and animation burden.

## Default `craft.finish` per preset

`craft.finish` is ALWAYS set in the spec (skills branch on it). Defaults — override deliberately, e.g. a pure-2D game on a 3D-default preset sets `painterly_2d`:

- `pixel`: **hd2d_pixel_fantasy**
- `vector_flat`: **clean_graphic_casual**
- `realistic_3d`: **cinematic_pbr_realism**
- `stylized_3d`: all other presets (`painterly_cel_fantasy`, `heroic_handpainted_fantasy`, `stylized_isometric_mmo`, `anime_action_rpg`, `dark_gothic_fantasy`, `cozy_toy_diorama`, `lowpoly_atmospheric`, `soft_clay_character`, `stylized_scifi`)

## Per-style generation notes

**painterly_cel_fantasy** — broad color gradients and simplified planes; avoid black comic outlines unless globally enabled. 3D forms moderately smooth, not dense. Let terrain/sky/fog carry the painterly feel; don't bake sky lighting into every prop.

**heroic_handpainted_fantasy** — exaggerate primary shapes (weapons, roofs, doors, foliage, creature heads). Warm/cool painted variation inside broad color blocks. Economy/rarity items must read from a 96px icon.

**stylized_isometric_mmo** — protect readability of click targets and player silhouettes. Reserve high chroma for players, objectives, loot, danger; keep ground materials quieter than interactables. Test under the orthographic camera, not a beauty camera.

**anime_action_rpg** — lock face/eye/hair proportions in character sheets (don't rely on prompt text alone). Use an approved 2D turnaround before 3D. Favor clean separations between hair/skin/clothing/accessories for animation.

**dark_gothic_fantasy** — use value contrast, not indiscriminate blackness. One restrained magical accent color per faction/biome. Enemies and hazards must never disappear into the background.

**cozy_toy_diorama** — gentle bevels and simple material gradients; matte roughness + subtle AO. Tiny crafted asymmetries sparingly to avoid a sterile procedural feel.

**lowpoly_atmospheric** — low poly count must be intentional; silhouette and lighting do the work. Keep facets visible and coherent; never pair low-poly geometry with photoreal/noisy textures.

**hd2d_pixel_fantasy** — image models for concept/reference, not raw production sprites without pixel cleanup. Enforce sprite scale, palette, and nearest-neighbor sampling globally. 3D only for background depth, lighting proxies, or pre-rendered sprites.

**clean_graphic_casual** — every object must communicate in under a second. Reduce materials, gradients, VFX, and palette until the primary interaction is unmistakable. Often the strongest style for a small iOS puzzle title.

**soft_clay_character** — soft round forms, diffuse light response, subtle surface imperfections; large readable features.

**stylized_scifi** — strong hard-surface panels, controlled emissives, dark neutral base plus a single accent color.

## Production prompts (copy/adapt)

**Create a new visual family**
```
Create the initial production art pack for {family_name}.
First read Assets/<Game>/Art/_ArtDirection/art-spec.yaml (probe legacy roots Assets/GameArt/ and Assets/Art/
if absent) and inspect existing golden assets (conditioning.golden_assets). Do not generate
production assets until you state the style, camera, palette, material grammar, and mobile budget you will preserve.
Deliver in order: (1) a concise AssetFamilyBrief, (2) a Gemini style-anchor reference sheet, (3) one golden-asset
beauty concept, (4) one golden-asset orthographic turnaround, (5) a Tripo-ready generation brief, (6) an optimized
Unity prefab plan, (7) ArtValidationScene screenshots + a quality-gate score.
Avoid direct imitation of a named game/artist — translate intent into the project's own rules.
```

**Create a production asset**
```
Create {asset_id} as a production-ready Unity asset. Read and obey art-spec.yaml and the golden asset for
{asset_family}; reuse its silhouette grammar, material vocabulary, texture density, lighting response, scale, and
camera readability. Do not change the global visual language. Follow Gemini concept -> approved multi-view -> Tripo
-> cleanup -> Unity prefab -> ArtValidationScene QA. Reject if it exceeds the mobile budget, exceeds the allowed
material slots, or fails the 96px silhouette test.
```

**Review an existing Unity art scene**
```
Review this Unity scene strictly against art-spec.yaml. Check silhouette readability, palette drift, material
inconsistency, excessive texture noise, lighting mismatch, VFX overuse, camera framing, UI hierarchy, draw-call /
material proliferation, texture-memory risk, and mobile performance risk.
Return: critical pre-ship fixes; consistency improvements; asset-by-asset changes; the smallest set of shared
shader/lighting/palette changes that fixes the most problems; a screenshot QA plan. Prioritize in-game readability
over beauty-render polish.
```
