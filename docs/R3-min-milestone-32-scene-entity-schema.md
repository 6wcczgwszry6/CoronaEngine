# R3-min Milestone 32: Scene entity schema normalization

## Scope

This milestone closes two schema gaps found by the indoor, outdoor, and mixed-scene Runtime slices before F5.

## Changes

- Normalize every successfully imported actor at the Runtime tool boundary with the downstream SceneEntity contract fields.
- Keep unknown interaction and gameplay capabilities empty instead of inventing abilities.
- Preserve empty physics facts and stable Runtime script bindings across custom and default import providers.
- Treat environment/substrate descriptions that do not require an Engine write as `not_applicable` for grounding.
- Keep materialized floors and terrain grounded, and room shells as enclosures.

## Verification

- Indoor room framework and shared bounds tests pass.
- Mixed scene terrain, room shell, floor, and transition foundation test passes.
- Forest substrate routing and the Chinese F5 forest-camp slice pass.
- Game-ready Snapshot, Registry, Finalizer, and consistency tests pass.

Real rendering, Engine AABB/grounding facts, and downstream multiplayer Snapshot equality remain `[待 F5/实机验证]`.
