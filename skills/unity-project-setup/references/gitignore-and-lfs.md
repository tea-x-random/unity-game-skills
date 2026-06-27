# Source control: `.gitignore`, `.gitattributes` + Git LFS, and Editor settings

Copyable, correct configuration for a Unity 6 / iOS project. Add all of this **before the first asset commit**. Replace `<Game>` with your project's root folder name where noted.

---

## 1. `.gitignore` (repo root)

Ignores the regenerable/local stuff. **Never** add `Assets/`, `ProjectSettings/`, `Packages/manifest.json`, `Packages/packages-lock.json`, or `*.meta` to this list.

```gitignore
# ---- Unity generated / local caches (regenerable — never commit) ----
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]serSettings/
[Mm]emoryCaptures/

# Asset meta data should only be ignored when the corresponding asset is also ignored
!/[Aa]ssets/**/*.meta

# Recordings / crash reports / Burst output
[Rr]ecordings/
crashlytics-build.properties
sysinfo.txt
*.[Cc]rash
[Aa]ssets/[Aa]ddressableAssetsData/*/*.bin*

# ---- IDE / OS ----
.vs/
.vscode/
.idea/
.gradle/
*.csproj
*.unityproj
*.sln
*.suo
*.tmp
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# ---- iOS / Xcode export & native build artifacts ----
*.app
*.ipa
*.dSYM.zip
*.dSYM
DerivedData/
Pods/

# ---- Secrets / per-environment config (NEVER commit) ----
# keep a committed *.example template; ignore the real files
secrets.json
*.secrets.json
.env
.env.*
!.env.example
!*.example
fastlane/.env*
*.p8
*.p12
*.mobileprovision
*.cer
GoogleService-Info.plist        # if it carries keys you treat as secret; inject in CI otherwise

# ---- Unity package manager temp ----
.[Cc]onsulo/
```

> Note: `Packages/packages-lock.json` is intentionally **committed** — do not ignore it.

---

## 2. `.gitattributes` (repo root) — line endings + Git LFS

`text=auto` normalizes line endings; everything below the LFS block stores large binaries via Git LFS so the repo stays clone-able. Commit this file **before** adding the binaries it matches.

```gitattributes
# Auto-detect text files, normalize to LF in the repo
* text=auto

# Unity YAML text assets — keep as text, never LFS, never CRLF-munged
*.cs        text diff=csharp
*.cginc     text
*.shader    text
*.uxml      text
*.uss       text
*.json      text
*.md        text

# Unity serialized assets are text (with Force Text) — keep mergeable, NOT in LFS
*.meta      -text merge=unityyamlmerge eol=lf
*.unity     -text merge=unityyamlmerge eol=lf
*.prefab    -text merge=unityyamlmerge eol=lf
*.asset     -text merge=unityyamlmerge eol=lf
*.mat       -text merge=unityyamlmerge eol=lf
*.anim      -text merge=unityyamlmerge eol=lf
*.controller -text merge=unityyamlmerge eol=lf
*.physicMaterial -text merge=unityyamlmerge eol=lf

# ============================================================
# Git LFS — large binary assets
# ============================================================

# Textures / images
*.png   filter=lfs diff=lfs merge=lfs -text
*.jpg   filter=lfs diff=lfs merge=lfs -text
*.jpeg  filter=lfs diff=lfs merge=lfs -text
*.gif   filter=lfs diff=lfs merge=lfs -text
*.bmp   filter=lfs diff=lfs merge=lfs -text
*.tga   filter=lfs diff=lfs merge=lfs -text
*.tiff  filter=lfs diff=lfs merge=lfs -text
*.tif   filter=lfs diff=lfs merge=lfs -text
*.psd   filter=lfs diff=lfs merge=lfs -text
*.exr   filter=lfs diff=lfs merge=lfs -text
*.hdr   filter=lfs diff=lfs merge=lfs -text

# 3D models
*.fbx   filter=lfs diff=lfs merge=lfs -text
*.obj   filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text
*.dae   filter=lfs diff=lfs merge=lfs -text
*.3ds   filter=lfs diff=lfs merge=lfs -text
*.glb   filter=lfs diff=lfs merge=lfs -text
*.gltf  filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav   filter=lfs diff=lfs merge=lfs -text
*.mp3   filter=lfs diff=lfs merge=lfs -text
*.ogg   filter=lfs diff=lfs merge=lfs -text
*.aif   filter=lfs diff=lfs merge=lfs -text
*.aiff  filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4   filter=lfs diff=lfs merge=lfs -text
*.mov   filter=lfs diff=lfs merge=lfs -text
*.webm  filter=lfs diff=lfs merge=lfs -text

# Fonts
*.ttf   filter=lfs diff=lfs merge=lfs -text
*.otf   filter=lfs diff=lfs merge=lfs -text

# Packaged / native binaries
*.unitypackage filter=lfs diff=lfs merge=lfs -text
*.a     filter=lfs diff=lfs merge=lfs -text
*.dll   filter=lfs diff=lfs merge=lfs -text
*.so    filter=lfs diff=lfs merge=lfs -text
*.bundle filter=lfs diff=lfs merge=lfs -text
*.aar   filter=lfs diff=lfs merge=lfs -text
*.zip   filter=lfs diff=lfs merge=lfs -text
```

### Git LFS setup commands

```bash
git lfs install                 # once per machine (installs the LFS filters)
# add .gitignore + .gitattributes FIRST, then:
git add .gitignore .gitattributes
git commit -m "Source control: Unity .gitignore + LFS .gitattributes"
# now add assets — LFS captures matched files from this point on
```

**If binaries are already committed** (LFS added too late), rewrite history so the blobs move into LFS:

```bash
git lfs migrate import --include="*.png,*.fbx,*.wav,*.psd,*.mp4"  # adjust patterns
# coordinate with the team: this rewrites history and requires a force-push
```

---

## 3. Editor settings to set (and commit `ProjectSettings/`)

These three live in `Edit ▸ Project Settings ▸ Editor` and are stored in `ProjectSettings/EditorSettings.asset` (committed). Set them on day zero.

| Setting | Path | Value | Why |
|---|---|---|---|
| **Asset Serialization** | Editor ▸ Asset Serialization ▸ Mode | **Force Text** | Scenes/prefabs/assets become YAML → diffable + mergeable; required for Smart Merge. Binary is unmergeable. |
| **Version Control** | Editor ▸ Version Control ▸ Mode | **Visible Meta Files** | Every asset gets a tracked `.meta` (GUID + import settings). Commit them always. |
| **Line Endings (Windows teams)** | Editor ▸ Asset Serialization ▸ Line Endings For New Scripts | **Unix** (or OS Native) | Avoids CRLF/LF churn alongside `.gitattributes`. |

After Force Text, the relevant `ProjectSettings/EditorSettings.asset` keys read:

```yaml
EditorSettings:
  m_SerializationMode: 2          # 2 = Force Text
  m_SerializeInlineMappingsOnOneLine: 1
  m_ExternalVersionControlSupport: Visible Meta Files
```

---

## 4. Smart Merge (UnityYAMLMerge) configuration

Unity ships `UnityYAMLMerge`, a semantic merge tool for `.unity` / `.prefab` (and other YAML assets) that resolves structural conflicts instead of corrupting the file. Register it with Git.

**Tool location (macOS Unity Hub install):**

```
/Applications/Unity/Hub/Editor/<version>/Unity.app/Contents/Tools/UnityYAMLMerge
```

**Per-repo (or global) Git config** — add to `.git/config` or `~/.gitconfig`:

```ini
[merge]
    tool = unityyamlmerge

[mergetool "unityyamlmerge"]
    trustExitCode = false
    cmd = '/Applications/Unity/Hub/Editor/6000.0.0f1/Unity.app/Contents/Tools/UnityYAMLMerge' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```

> Update the version path to your installed Unity 6 (`6000.x`). The `merge=unityyamlmerge` attributes in `.gitattributes` (section 2) tell Git which files use it; on a conflict run `git mergetool`.

**Still minimize concurrent scene edits.** Smart Merge is a safety net, not a license for two people to edit one `.unity` at once — split work into prefabs and additive scenes so conflicts are rare in the first place.

---

## 5. Quick verification

```bash
git lfs ls-files          # should list your textures/models/audio as LFS pointers
git check-attr -a Assets/<Game>/Art/some.png   # shows filter=lfs for a tracked binary
git status                # adding an asset should show its .meta alongside it
```

If a newly added `.png` does **not** show as LFS, the `.gitattributes` was added after it — migrate (section 2). If an asset appears without its `.meta` (or vice-versa), fix before committing — a meta/asset mismatch breaks references.
