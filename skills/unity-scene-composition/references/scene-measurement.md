# Deterministic scene measurement (MCP)

How to compute the `measured_acceptance` gates from live Unity scene data. Run via `unity-mcp-bridge` `execute_code`, or wrap in a `[MenuItem]` editor script for crash-safe re-runs. Output is JSON — compare it against `composition.yaml` budgets agent-side and record it with the QA evidence.

## Step 1 — build the registry map (agent-side)

Parse `Assets/<Game>/Art/Approved/registry.yaml` + each `asset-contract.yaml` into a map:
`prefab/asset name → { density_cost, visual_weight, composition.layer, role, target_screen_height_percent, camera_contract }`.

## Step 2 — walk visible renderers (C# via MCP)

```csharp
using System.Text;
using UnityEngine;

var cam = Camera.main;
var planes = GeometryUtility.CalculateFrustumPlanes(cam);
var sb = new StringBuilder();
sb.Append("{\"camera\":{\"orthographic\":" + (cam.orthographic ? "true" : "false")
    + ",\"orthographic_size\":" + cam.orthographicSize.ToString("F2")
    + ",\"yaw\":" + cam.transform.eulerAngles.y.ToString("F1")
    + ",\"pitch\":" + cam.transform.eulerAngles.x.ToString("F1") + "},\"renderers\":[");
bool first = true;
foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
{
    if (!r.enabled || !GeometryUtility.TestPlanesAABB(planes, r.bounds)) continue;
    var b = r.bounds;
    // viewport-space AABB from the 8 bounds corners
    float minX = 1f, maxX = 0f, minY = 1f, maxY = 0f;
    for (int i = 0; i < 8; i++)
    {
        var c = b.center + Vector3.Scale(b.extents,
            new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
        var v = cam.WorldToViewportPoint(c);
        if (v.z < 0) continue; // behind camera
        minX = Mathf.Min(minX, Mathf.Clamp01(v.x)); maxX = Mathf.Max(maxX, Mathf.Clamp01(v.x));
        minY = Mathf.Min(minY, Mathf.Clamp01(v.y)); maxY = Mathf.Max(maxY, Mathf.Clamp01(v.y));
    }
    if (!first) sb.Append(",");
    first = false;
    sb.Append("{\"name\":\"" + r.gameObject.name + "\",\"root\":\"" + r.transform.root.name
        + "\",\"screen_height_pct\":" + ((maxY - minY) * 100f).ToString("F1")
        + ",\"viewport_rect\":[" + minX.ToString("F3") + "," + minY.ToString("F3") + ","
        + maxX.ToString("F3") + "," + maxY.ToString("F3") + "]}");
}
sb.Append("]}");
Debug.Log(sb.ToString());
```

## Step 3 — join and gate (agent-side)

- **no_unapproved_assets:** every renderer's name/root must resolve to a registry entry or a ledger-flagged placeholder. Unresolved visible renderer = FAIL.
- **density_within_budget:** sum resolved `density_cost` ≤ `density_budget.max_density_cost_per_screen`; count interesting objects and distinct families vs their caps.
- **screen_heights_within_role_ranges:** each renderer's `screen_height_pct` inside `shape_rhythm.target_screen_height_percent[role]`.
- **occlusion_within_budget:** for renderers whose contract layer is `foreground`, sum viewport-rect area intersecting the gameplay area (viewport minus UI margins) ≤ `occlusion_budget.gameplay_area_max_percent`. (Summed AABBs ignore overlap — conservative, which is the right direction for a gate.)
- **camera_contracts_match:** the reported camera block equals `camera_profile` (projection/yaw/pitch/ortho size within 0.5 tolerance); each visible asset's `camera_contract` matches or is marked UI/background.

## Step 4 — one-pixel-density check (sprite/2.5D scenes)

```csharp
using UnityEngine;
// Set groundName before running; target PPU comes from art-spec craft.pixels_per_unit.
var groundName = "Ground";
var mr = GameObject.Find(groundName).GetComponent<Renderer>();
var mat = mr.sharedMaterial;
var tex = mat.mainTexture;
float texelsPerUnit = tex.width * mat.mainTextureScale.x / mr.bounds.size.x;
Debug.Log("{\"ground\":\"" + groundName + "\",\"texels_per_unit\":" + texelsPerUnit.ToString("F1")
    + ",\"filter\":\"" + tex.filterMode + "\",\"mipmaps\":" + (tex.mipmapCount > 1 ? "true" : "false") + "}");
```

Gate: `|texels_per_unit − craft.pixels_per_unit| / PPU ≤ pixel_density.texel_tolerance_percent`; pixel track additionally requires `filter == Point` and no mipmaps on ground AND sprites, and the `pixel_density.light_model` (unlit sprites ⇒ unlit ground).

## Recording

Store the raw JSON from steps 2/4 plus the per-gate pass/fail verdict alongside the screenshot in the BeautyCell/scene QA artifact. These numbers are the gate; the VLM scene critique (screenshot-acceptance.md Pass 2) never overrides them.
