---
name: unity-audio-generator
description: "Generate, convert, clean, and import audio for Unity casual games using ElevenLabs, then import as AudioClips with mobile-correct settings. Use for sound effects, looping ambience/music beds, UI sounds (tap/win/coin/level-up), impact/collectible/power-up audio, announcer/voice/TTS lines, voice conversion, and audio cleanup/isolation. Covers Unity AudioClip import: compression (Vorbis), load type by clip length, force-to-mono, and mobile memory budgeting."
---

# Unity Audio Generator

Generate game audio with ElevenLabs, then import it as Unity AudioClips with settings tuned for mobile.

## API key & script

Key resolution: `--api-key`, then `ELEVENLABS_API_KEY`. Probe / built-in probe:
```bash
bash ~/.claude/skills/unity-game-director/scripts/probe_asset_credentials.sh   # ELEVENLABS_API_KEY=SET|MISSING
python3 ~/.claude/skills/unity-audio-generator/scripts/unity_audio_asset.py probe
```
Subcommands: `sfx` (effects/ambience from a prompt), `tts` (spoken line), `isolate` (clean/isolate speech), `voice-change` (convert a performance to a target voice). Write outputs under `Assets/Audio/`.

```bash
# UI / gameplay SFX
python3 ~/.claude/skills/unity-audio-generator/scripts/unity_audio_asset.py sfx \
  --prompt "bright cheerful coin pickup blip, short, casual mobile game" \
  --out-dir Assets/Audio/SFX

# Looping music/ambience bed
python3 ~/.claude/skills/unity-audio-generator/scripts/unity_audio_asset.py sfx \
  --prompt "upbeat seamless looping casual puzzle music, light marimba and claps" \
  --out-dir Assets/Audio/Music

# Announcer / voice line
python3 ~/.claude/skills/unity-audio-generator/scripts/unity_audio_asset.py tts \
  --text "Level complete!" --out-dir Assets/Audio/VO
```

## What to generate for casual games

- **Core feedback SFX:** tap/select, success/win, fail, coin/collectible, combo/streak, level-up, button — short, punchy, distinct. These carry most of the "juice."
- **Music:** one or two short seamless loops (menu + gameplay); keep files small.
- **Ambience:** optional looping bed for theme.
- **Voice:** announcer stingers or tutorial VO via `tts`; clean recordings with `isolate`.

## Import into Unity (via unity-mcp-bridge)

After writing under `Assets/Audio/`, `refresh_unity(scope="assets", wait_for_ready=true)`, then set `AudioImporter` settings with `execute_code` by clip role:

```csharp
var p = "Assets/Audio/SFX/coin.wav";
var ai = (UnityEditor.AudioImporter)UnityEditor.AssetImporter.GetAtPath(p);
var s = ai.defaultSampleSettings;
s.compressionFormat = UnityEditor.AudioCompressionFormat.Vorbis; // good size/quality on mobile
s.quality = 0.7f;
// Short SFX: decompress on load (cheap CPU, tiny). Music/ambience: streaming or compressed-in-memory.
s.loadType = UnityEngine.AudioClipLoadType.DecompressOnLoad;     // music -> .Streaming
ai.defaultSampleSettings = s;
ai.forceToMono = true;        // mono for SFX saves memory; keep music stereo (forceToMono=false)
ai.SaveAndReimport();
return "imported clip";
```

Guidance by role:
- **Short SFX (<1s):** Vorbis, `DecompressOnLoad`, force-to-mono.
- **Music / long loops:** `Streaming` (or `CompressedInMemory`), stereo, lower quality is fine.
- **VO:** `CompressedInMemory`, mono.

Then wire playback: an `AudioSource` per role (SFX one-shots via `PlayOneShot`, a looping music source), or a small `AudioManager` singleton. Keep concurrent voices low on mobile.

## Mobile rules

- Favor Vorbis; avoid uncompressed PCM for anything but tiny critical SFX.
- Force-to-mono for SFX/VO; reserve stereo for music.
- Cap total audio memory; stream music rather than loading it whole.
- Report prompts, output paths, import settings per clip, and where each clip triggers.
