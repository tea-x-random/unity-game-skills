# Test Recipes (Unity Test Framework via MCP)

Author EditMode + PlayMode tests and run them through `unity-mcp-bridge`. Tests are real evidence; a green run with counts is what lets you say "passes".

## Enable the testing group

`run_tests` and `get_test_job` do not exist until the group is enabled:

```text
manage_tools(action="enable_group", group="testing")
```

## EditMode vs PlayMode

- **EditMode** — pure logic, no scene, no frames. Fast. Use for scoring math, save/load serialization, config validation, state machines.
- **PlayMode** — runs in a live scene with frames/coroutines/physics. Use for spawning cadence, collisions, win/lose triggers, input-driven behavior. Use `[UnityTest]` + `yield return null` to advance frames.

## Test assembly setup

Tests live in a folder with an **asmdef** that references `UnityEngine.TestRunner` and `UnityEditor.TestRunner` (and your gameplay asmdef). Conventionally `Assets/Tests/EditMode/` and `Assets/Tests/PlayMode/`, each with its own asmdef (PlayMode asmdef includes platforms; EditMode is Editor-only). Create scripts via `create_script` / `apply_text_edits`, then wait for compile and `read_console(types=["error"])` clean before running.

## Example EditMode test (scoring)

```csharp
using NUnit.Framework;
using MyGame;

public class ScoreTests
{
    [Test]
    public void AddScore_Accumulates()
    {
        var s = new ScoreModel();
        s.Add(10);
        s.Add(5);
        Assert.AreEqual(15, s.Total);
    }

    [Test]
    public void HighScore_PersistsBest()
    {
        var s = new ScoreModel();
        s.Add(30);
        s.CommitRun();
        s.Reset();
        s.Add(10);
        s.CommitRun();
        Assert.AreEqual(30, s.BestScore);
    }
}
```

## Example PlayMode test (spawning / win)

```csharp
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

public class SpawnTests
{
    [UnityTest]
    public IEnumerator Spawner_ProducesObstacleWithinInterval()
    {
        var go = new GameObject("spawner");
        var spawner = go.AddComponent<Spawner>();
        spawner.interval = 0.1f;

        yield return new WaitForSeconds(0.25f);   // advance real frames

        Assert.GreaterOrEqual(GameObject.FindObjectsByType<Obstacle>(
            FindObjectsSortMode.None).Length, 1);
        Object.Destroy(go);
    }
}
```

## Run + poll (async — never assume synchronous)

`run_tests` returns a **job id**; results come from polling `get_test_job`:

```text
run_tests(mode="PlayMode")                 # or mode="EditMode"
-> { job_id: "..." }

get_test_job(job_id="...", wait_timeout=120)
# if status is still running, call get_test_job again
# when finished, read passed / failed / skipped counts and failure messages
```

- First run after a compile triggers a **domain reload** (~5s connection drop) — wait and retry the poll.
- PlayMode runs enter/exit Play Mode; don't issue scene edits during the run.
- "Tests green" in a report **must** include counts (e.g. "12 passed, 0 failed") and the `job_id`. A run that errored to start, or that you didn't poll to completion, is not a pass.

## What to test in a casual game (priority order)

1. **Scoring** — add/multiply, high-score persists across runs.
2. **Spawning** — cadence, positions, object pooling reuses instead of leaking.
3. **Win/lose** — triggers fire at the right thresholds; both paths reachable.
4. **Save/load** — PlayerPrefs / serialized state round-trips and survives a reload.

Keep tests deterministic: inject seeds, avoid wall-clock dependence beyond short `WaitForSeconds`, and don't depend on frame-perfect timing.
