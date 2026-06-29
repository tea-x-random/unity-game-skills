# Pre-render 3D → non-pixel 2D sprites (Unity, via unity-mcp-bridge)

Render a Tripo-generated model from the game camera into transparent PNG sprites for **non-pixel** static sprites, sprite-sheet animation frames, or N-direction rotation sets. Run through `execute_code` after the model is imported and a prefab/instance exists. For pixel-art final assets, do **not** render 3D and downscale; use `unity-pixel-art` / PixelLab instead.

## Camera + lighting setup (match the game's angle)
- **Orthographic camera** (no perspective distortion for 2D), `clearFlags = SolidColor`, `backgroundColor` with **alpha 0** for transparency.
- Angle to match the game: top-down (look straight down), 3/4 (~30–45° tilt), or side (look along Z).
- A simple key + fill light matching the project's `art-spec.yaml` lighting so rendered sprites match the rest of the set.
- Frame the model so it fills the target sprite cell consistently (same camera distance/ortho size for every frame/angle so frames don't jitter).

## Render one frame to a transparent PNG
```csharp
// camGO: an orthographic Camera looking at the model; target: the model instance.
int W = 512, H = 512;
var rt = new UnityEngine.RenderTexture(W, H, 24, UnityEngine.RenderTextureFormat.ARGB32);
var cam = camGO.GetComponent<UnityEngine.Camera>();
cam.clearFlags = UnityEngine.CameraClearFlags.SolidColor;
cam.backgroundColor = new UnityEngine.Color(0,0,0,0);   // transparent
cam.targetTexture = rt;
cam.Render();
UnityEngine.RenderTexture.active = rt;
var tex = new UnityEngine.Texture2D(W, H, UnityEngine.TextureFormat.RGBA32, false);
tex.ReadPixels(new UnityEngine.Rect(0,0,W,H), 0, 0);
tex.Apply();
System.IO.File.WriteAllBytes(
    UnityEngine.Application.dataPath + "/Art/Sprites/archer_idle_0.png", tex.EncodeToPNG());
cam.targetTexture = null; UnityEngine.RenderTexture.active = null;
return "rendered frame";
```

## Sprite-sheet animation (render each frame of a cycle)
Drive the model's Animator/clip to successive normalized times and render each into a frame, then assemble into a strip (or write numbered PNGs and slice).
```csharp
// animator: Animator on the model; clip: the AnimationClip; frames: e.g. 8
for (int i = 0; i < frames; i++) {
    float t = (float)i / frames;
    animator.Play(stateName, 0, t);
    animator.Update(0f);                  // force the pose at time t
    // ... render as above to archer_fire_{i}.png ...
}
```
Then import the numbered PNGs (or a packed strip) as sprites and build clips via `unity-animation`. Because every frame is the *same model*, identity is perfectly consistent — no drift.

## N-direction set (top-down / isometric)
Rotate the model (or orbit the camera) by `360/N` each step and render — e.g. 8-direction for a top-down character.
```csharp
for (int d = 0; d < 8; d++) { target.transform.rotation = UnityEngine.Quaternion.Euler(0, d*45f, 0); /* render */ }
```

## Tips
- Keep the camera ortho size + distance **identical** across all frames/angles so sprites align.
- Render at 2× the on-screen size, then let ASTC/mip handle downscale for non-pixel crispness. This is not a pixel-art workflow.
- Pack the resulting frames into a **Sprite Atlas** (mobile draw calls).
- Match render lighting to `art-spec.yaml` so pre-rendered sprites sit in the same world as Gemini-generated 2D (UI, textures). Pixel-art sprites instead follow the `unity-pixel-art` import/profile contract.
