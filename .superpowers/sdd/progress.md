# UI Surface Lifecycle / Docking Cleanup Progress

## Branch

- Worktree: `D:/CoronaEngine/.worktrees/ui_surface_lifecycle`
- Branch: `refactor/ui-surface-lifecycle`
- Base: `dc6c1a8f`

## Baseline evidence

- 2026-07-11: `VisionModelNormalizationTests`, `VisionActorMaterialBridgeTests`, and `VisionActorTransformBridgeTests` passed before branch creation.
- 2026-07-11: `corona_engine` RelWithDebInfo incremental build passed before branch creation.

## Task status

- Task 1 — completed and approved (`06f61753`, `8a581a89`).
- Task 2 — completed and approved (`8b915d86`, `83334f3f`, `a7d23ce6`): callback/forward-completion fences, resource-safe terminal ack ordering, value-owned frame acquisition, production-linked smoke, and deterministic teardown/exception tests; focused 2/2 and linked Display build pass.
- Task 3 — completed and approved (`066b41cb`, `6f2de26c`, `17a3a8fe`): hidden registration/first-present reveal, bounded two-phase removal, producer/consumer drain, main+secondary shutdown ordering, and non-destructive failure retention.
- Task 4 — harness implemented and reviewed, validation blocked (`db30fd51`, `eac2cf43`, `1a4a2347`, `44b7c48f`, `bdc47890`, `d29803ca`): default skip 77 works; opt-in GPU run timed out and CEF three-panel regression was unavailable.
- Task 5 — blocked by Task 4 gate: Vue cleanup.
- Task 6 — blocked by Task 4 gate: native docking cleanup/Camera isolation.
- Task 7 — pending: docs and final verification.

## Review ledger

| Task | Implementer | Commit | Spec review | Quality review | Verification |
| --- | --- | --- | --- | --- | --- |
| 1 | task1_lifecycle | 06f61753, 8a581a89 | approved | approved | controller build warning-free; 1/1 test passed; implementer 20/20 clean |
| 2 | task2_display | 8b915d86, 83334f3f, a7d23ce6 | approved | approved | focused build warning-free; 2/2 passed; production-linked smoke; linked Display build warning-free |
| 3 | task3_ui_ordering | 066b41cb, 6f2de26c, 17a3a8fe | approved | approved | focused build warning-free; UiSurfaceLifecycle/RemovalRace 2/2 passed |
| 4 | task4_multisurface_gate | db30fd51, eac2cf43, 1a4a2347, 44b7c48f, bdc47890, d29803ca | approved with gate blocked | approved with gate blocked | target build passed; default skip 77; opt-in GPU timeout; CEF unavailable |
| 5 | pending | pending | pending | pending | pending |
| 6 | pending | pending | pending | pending | pending |
| 7 | pending | pending | pending | pending | pending |

## Gates and blockers

- Legacy docking deletion is gated on native unit tests, GPU smoke, and current CEF multi-window regression evidence.
- The worktree was moved to an underscore-only path and its path-bound build cache repaired; linked Display verification now passes.
- No product-code or worktree/tooling blocker is recorded for Task 2 or Task 3.
- Task 4 gate evidence is recorded in `docs/ui-multisurface-validation.md`; Tasks 5-6 remain blocked until enabled GPU and CEF checks pass.
Task 3 implementation committed as 066b41cb. Focused build was deferred because another ninja build held the shared worktree; rerun by controller after lock clears.
