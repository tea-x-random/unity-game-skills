# C# Patterns for Casual iOS Games

Firm rules with minimal, copy-able snippets. On Unity 6 (6000.x), verify any API you are unsure of with `unity_reflect` / `unity_docs` before writing — the model's default knowledge is ~2022.3 and the Input System / UI Toolkit have moved.

## The rules (why they matter on mobile)

| Rule | Reason |
|------|--------|
| Cache `GetComponent` in `Awake`/`Start`, never in `Update` | Each call is a lookup; per-frame lookups stack up on weak phones |
| No `Find` / `FindObjectOfType` / `SendMessage` in production | Scene-wide scans + reflection; wire via serialized refs / singletons / events |
| `[SerializeField] private` over `public` | Inspector access without breaking encapsulation |
| Pool instead of `Instantiate`/`Destroy` per frame | Avoids allocations and GC spikes (frame hitches) |
| `RaycastNonAlloc` / `OverlapNonAlloc`, no LINQ/`new` in hot paths | Zero managed allocation in `Update`/`FixedUpdate` |
| `== null`, not `is null`, for `UnityEngine.Object` | Unity overloads `==` to detect destroyed objects |
| One `.asmdef` per feature folder | Fast incremental compile, shorter domain reloads, enforced deps |
| Physics in `FixedUpdate`, input/visuals in `Update` | Stable simulation; move rigidbodies with `MovePosition`/forces |

### Caching components

```csharp
public class PlayerController : MonoBehaviour
{
    [SerializeField] private float speed = 6f;
    private Rigidbody _rb;            // cached, not re-fetched

    void Awake() => _rb = GetComponent<Rigidbody>();

    void FixedUpdate()
    {
        _rb.MovePosition(_rb.position + transform.forward * (speed * Time.fixedDeltaTime));
    }
}
```

### NonAlloc raycast (no per-frame garbage)

```csharp
private readonly RaycastHit[] _hits = new RaycastHit[8];   // reused buffer

bool Grounded()
{
    int n = Physics.RaycastNonAlloc(transform.position, Vector3.down, _hits, 0.2f, _groundMask);
    return n > 0;
}
```

## Object pooling

Generic pool — keep one per prefab type. Reset state on `Get`, not on `Release`, so released objects don't hold references.

```csharp
using System.Collections.Generic;
using UnityEngine;

public interface IPooled { void OnSpawn(); void OnDespawn(); }

public class GenericPool<T> where T : Component, IPooled
{
    private readonly T _prefab;
    private readonly Transform _parent;
    private readonly Stack<T> _free = new();

    public GenericPool(T prefab, Transform parent, int prewarm)
    {
        _prefab = prefab; _parent = parent;
        for (int i = 0; i < prewarm; i++) { var o = New(); o.gameObject.SetActive(false); _free.Push(o); }
    }
    private T New() => Object.Instantiate(_prefab, _parent);

    public T Get(Vector3 pos, Quaternion rot)
    {
        var o = _free.Count > 0 ? _free.Pop() : New();
        o.transform.SetPositionAndRotation(pos, rot);
        o.gameObject.SetActive(true);
        o.OnSpawn();
        return o;
    }
    public void Release(T o) { o.OnDespawn(); o.gameObject.SetActive(false); _free.Push(o); }
}
```

`UnityEngine.Pool.ObjectPool<T>` is the built-in equivalent if you prefer no custom class.

## Input System action (Action-based)

Prefer an `InputActionAsset` / `PlayerInput`, but a code-defined action is fine for a slice. Verify `InputAction` / callback signatures with `unity_reflect` on Unity 6.

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

public class TapToJump : MonoBehaviour
{
    private InputAction _tap;

    void Awake()
    {
        _tap = new InputAction("Tap", InputActionType.Button, "<Touchscreen>/primaryTouch/tap");
        _tap.AddBinding("<Mouse>/leftButton");      // Editor iteration
        _tap.performed += _ => Jump();
    }
    void OnEnable()  => _tap.Enable();
    void OnDisable() => _tap.Disable();
    void Jump() { /* ... */ }
}
```

Swipe: track `<Touchscreen>/primaryTouch/position` from press to release, then threshold the delta into Up/Down/Left/Right.

## State machine (board / player states)

A tiny explicit machine beats scattered booleans for puzzles, turn flow, and player modes.

```csharp
public enum GameState { Boot, Ready, Playing, Resolving, GameOver }

public class GameStateMachine
{
    public GameState Current { get; private set; } = GameState.Boot;
    public event System.Action<GameState, GameState> OnChanged;

    public void Set(GameState next)
    {
        if (next == Current) return;
        var prev = Current; Current = next;
        OnChanged?.Invoke(prev, next);
    }
}
```

Drive transitions from one place; let systems subscribe to `OnChanged` rather than poll.

## Singleton manager (sparingly)

Use for one true global (GameManager, AudioManager, ScoreManager). Avoid turning every system into a singleton — it hides dependencies.

```csharp
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }
}
```

## Event / observer (decoupling)

Let gameplay raise events; HUD, audio, and VFX subscribe. Keeps scoring/feedback out of movement code.

```csharp
public static class GameEvents
{
    public static event System.Action<int> ScoreChanged;
    public static event System.Action GameOver;

    public static void RaiseScore(int v) => ScoreChanged?.Invoke(v);
    public static void RaiseGameOver()    => GameOver?.Invoke();
}

// HUD:
void OnEnable()  => GameEvents.ScoreChanged += UpdateLabel;
void OnDisable() => GameEvents.ScoreChanged -= UpdateLabel;   // always unsubscribe
```

Always unsubscribe in `OnDisable`/`OnDestroy` to avoid leaks and calls into destroyed objects.

## Coroutine hygiene

```csharp
private static readonly WaitForSeconds OneSecond = new(1f);   // cache, don't new() per call

IEnumerator Tick()
{
    while (true) { /* ... */ yield return OneSecond; }
}
```

## Assembly definitions

- One `Game.asmdef` per feature folder (`Player`, `Spawning`, `UI`, `Core`).
- A separate `Game.Editor.asmdef` (with `includePlatforms: ["Editor"]`) for `[MenuItem]`/importer scripts so they never ship.
- Reference the Input System / TMP / test asmdefs explicitly. Fewer cross-references = shorter domain reloads after each compile.
