# Animation recipes (Unity, via unity-mcp-bridge)

Concrete wiring for both tracks. Run these through `execute_code` after the assets are imported; confirm the Editor is reachable and compiles clean first.

## A. 2D sprite animation

### 1. Slice a frame strip into sprites
Import the strip with `spriteImportMode = Multiple`, then slice by cell count (set in the Sprite Editor, or via `ISpriteEditorDataProvider`). Keep a **consistent pivot** (usually bottom-center for characters) so frames don't jitter.

```csharp
var path = "Assets/Art/Sprites/archer_fire.png";
var ti = (UnityEditor.TextureImporter)UnityEditor.AssetImporter.GetAtPath(path);
ti.textureType = UnityEditor.TextureImporterType.Sprite;
ti.spriteImportMode = UnityEditor.SpriteImportMode.Multiple;
ti.filterMode = UnityEngine.FilterMode.Bilinear;   // Point for pixel art
ti.SaveAndReimport();
// Then slice: Sprite Editor → Slice → Grid by Cell Count (e.g. 8x1), pivot Bottom.
```

### 2. Build an Animation Clip from the sliced frames
```csharp
// Build a looping/one-shot clip from an ordered sprite array.
var clip = new UnityEngine.AnimationClip { frameRate = 12f };
var settings = UnityEditor.AnimationUtility.GetAnimationClipSettings(clip);
settings.loopTime = false; // true for idle/walk
UnityEditor.AnimationUtility.SetAnimationClipSettings(clip, settings);

var binding = new UnityEditor.EditorCurveBinding {
    type = typeof(UnityEngine.SpriteRenderer), path = "", propertyName = "m_Sprite" };
var sprites = /* load the sliced Sprite[] in frame order via AssetDatabase.LoadAllAssetsAtPath */ null;
var keys = new UnityEditor.ObjectReferenceKeyframe[sprites.Length];
for (int i = 0; i < sprites.Length; i++)
    keys[i] = new UnityEditor.ObjectReferenceKeyframe { time = i / clip.frameRate, value = sprites[i] };
UnityEditor.AnimationUtility.SetObjectReferenceCurve(clip, binding, keys);
UnityEditor.AssetDatabase.CreateAsset(clip, "Assets/Art/Anim/archer_fire.anim");
```

Build one clip per state (`idle`, `aim`, `fire`, …). Loop idle/walk; one-shot attack/death.

### 3. Frame-rate & frame-count guidance
- Casual sprite anim reads well at **10–14 fps**. Idle/bob: 2–6 frames. Walk: 6–8. Attack/fire: 5–10.
- Ease in-betweens (more frames around the key pose) rather than uniform spacing — gives anticipation/snap.

## B. 3D skeletal animation
- Rig + generate cycles with Tripo (`unity-3d-generator`), import the FBX/GLB, set **Rig → Humanoid** (retargetable) or **Generic**, configure the Avatar.
- One clip per state; set Loop Time on idle/walk/run; bake root motion off for top-down/TD turrets.
- Reuse one Animator Controller across same-rig characters; retarget shared humanoid clips.

## C. Animator Controller + parameters (both tracks)
```csharp
var ac = UnityEditor.Animations.AnimatorController.CreateAnimatorControllerAtPath(
    "Assets/Art/Anim/Archer.controller");
ac.AddParameter("Fire", UnityEngine.AnimatorControllerParameterType.Trigger);
ac.AddParameter("Aiming", UnityEngine.AnimatorControllerParameterType.Bool);

var sm = ac.layers[0].stateMachine;
var idle = sm.AddState("Idle");  idle.motion = /* idle clip */ null;
var aim  = sm.AddState("Aim");   aim.motion  = /* aim clip  */ null;
var fire = sm.AddState("Fire");  fire.motion = /* fire clip */ null;
sm.defaultState = idle;

var toAim = idle.AddTransition(aim);  toAim.AddCondition(UnityEditor.Animations.AnimatorConditionMode.If, 0, "Aiming");
var toFire = aim.AddTransition(fire); toFire.AddCondition(UnityEditor.Animations.AnimatorConditionMode.If, 0, "Fire");
var fireBack = fire.AddTransition(aim); fireBack.hasExitTime = true; // return after the loose
```
Drive at runtime: `animator.SetBool("Aiming", true); animator.SetTrigger("Fire");`. Use a **blend tree** for locomotion (`Speed` float blending idle↔walk↔run).

## D. Animation Events — fire gameplay on the right frame (critical)
Add an event to the `fire`/`attack` clip at the **release/contact frame** that calls a method on a component on the same GameObject. The projectile spawns/damage applies when the motion says so — never on input.

```csharp
// MonoBehaviour on the archer; the Animation Event calls OnFireFrame by name.
public class ArcherView : MonoBehaviour {
    public System.Action FireReleased;            // gameplay subscribes
    public void OnFireFrame() => FireReleased?.Invoke();   // <- Animation Event target
}
```
Add the event programmatically:
```csharp
var clip = /* the fire AnimationClip */;
var evt = new UnityEngine.AnimationEvent {
    time = releaseFrame / clip.frameRate,   // e.g. frame 4 of an 8-frame loose
    functionName = "OnFireFrame" };
UnityEditor.AnimationUtility.SetAnimationEvents(clip, new[] { evt });
```
Gameplay subscribes to `FireReleased` to spawn the arrow — so visuals and mechanics are always in sync. Same pattern for melee (`OnHitFrame` → apply damage on contact) and footstep SFX.

## E. Mobile performance checklist
- 2D: pack frames into a **Sprite Atlas**; share clips across similar enemies; cap frame counts.
- 3D: **animation compression** (Optimal / keyframe reduction) on import; modest bone counts; consider **GPU skinning** (Player Settings); reuse controllers + retargeted clips.
- Cull offscreen Animators: `animator.cullingMode = AnimatorCullingMode.CullCompletely;` and/or disable when not visible.
- Verify in Play Mode + a screenshot/short capture that loops are seamless and events fire on-frame (read the console for the gameplay hook firing).
