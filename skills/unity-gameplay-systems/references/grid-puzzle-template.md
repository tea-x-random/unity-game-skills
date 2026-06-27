# Grid / number-puzzle template (Sudoku-style)

A reusable blueprint for casual grid puzzles (Sudoku, Killer, nonogram, number-link, match-grid).
Proven on a shipped 9×9 Sudoku slice. Adjust grid size/rules; the architecture holds.

## Assembly layout (keep logic engine-free)

```
Scripts/Core/   <Puzzle>.Core.asmdef  noEngineReferences: true   (System only — unit-testable)
  Grid.cs        Size/Cells/Index/RowOf/ColOf/BoxOf + IsSafe + TryFindEmpty + Clone
  Solver.cs      Solve(grid) backtracking; CountSolutions(grid, cap=2) for uniqueness
  Generator.cs   GenerateSolved(rng); Generate(difficulty) -> Puzzle (seeded -> reproducible)
  Puzzle.cs      immutable { Givens[], Solution[], Difficulty }
  BoardState.cs  player values + note bitmask + undo stack + IsCorrect/IsConflicting/IsSolved
Scripts/Game/   <Puzzle>.Game.asmdef   (MonoBehaviours over Core)
```

A no-engine Core means `run_tests(mode="EditMode")` validates generation/solving without a scene.

## Generation with a uniqueness guarantee (the part people get wrong)

```
solution = randomized-backtracking fill of an empty grid
givens   = clone(solution)
for each cell in random order (optionally remove 180°-symmetric pairs for the classic look):
    remove the clue(s)
    if CountSolutions(givens) != 1: restore   // keep only proper puzzles
    stop when given-count reaches the difficulty target
```

`CountSolutions` is a backtracking counter that early-exits at 2 — you only need "is it unique",
not the total. Difficulty = target given-count (more givens = easier) + hint budget.

## BoardState essentials

- `int[]` values (givens pre-filled), `int[]` note bitmasks (bit `v-1`), `Stack<Move>` undo.
- `SetValue/ClearCell/ToggleNote` are no-ops on givens and record undo.
- `IsConflicting(i)`: temporarily clear the cell, test `IsSafe`, restore.
- `IsCorrect(i)`: value equals `Solution[i]`. `IsSolved()`: every cell filled and equals solution.

## View layer (runtime-built, low-wiring)

- **Board:** `GridLayoutGroup` with `FixedColumnCount = N`; instantiate `N*N` cell prefabs at runtime
  and `Init(index, board, theme)` each. The scene stores only the grid parent + cell prefab.
- **Cell:** uGUI `Image` + value `TMP_Text` + notes `TMP_Text`; implement `IPointerClickHandler` to
  report taps. Tint by highlight (selected / peer / same-number / conflict).
- **Input:** EventSystem + `InputSystemUIInputModule` (Input System), never legacy `Input`.
- **Number pad:** build digit buttons at runtime; show remaining count per digit and fade/disable
  when a digit is fully placed. Plus erase / notes-toggle / hint / undo.

## Game feel (makes it read as premium)

Peer + same-number highlighting, scale-pop on a correct placement, shake on a wrong one, mistakes/
lives, hint (reveal a correct cell from the solution), undo, count-up score, win/lose overlay with a
difficulty picker, haptics on iOS. Generate the solved grid off the main thread (`Task.Run`) so hard
puzzles don't hitch the frame.

## No-MCP assembly

If you can't drive the Editor live, ship a `[MenuItem]` scene-builder that creates the prefabs,
theme asset and wired scene from code (see the director's no-Editor fallback) instead of hand-editing
`.unity`/`.prefab` YAML.
