# R3-min Milestone 30: Cross-batch Engine Snapshot Reconciliation

The old F5 run ended with 14 entities but only 3 Game-ready entities. A focused
regression found two Runtime-side gaps that could preserve this mismatch even
after the Engine had loaded the geometry:

- Finalizer requested a late Engine snapshot only when a BatchPlan was marked
  `partial`. A historical batch marked `completed` but still carrying estimated
  bounds was not included in readiness reconciliation.
- Engine snapshot observations were merged back only by exact `actor_id`.
  Native handles that differed from Runtime identity could not update the
  existing actor, while unrelated scene actors risked being attributed to the
  current plan.

## Current Changes

- Finalizer now includes every plan batch that still contains an actor or
  environment component without `engine_actual` bounds, including historical
  completed batches.
- Snapshot reconciliation matches a unique Runtime actor by stable actor ID,
  entity ID, asset/model identity, or Runtime/native/requested name aliases.
- Runtime identity and plan/batch ownership remain authoritative. Native
  geometry, transform, bounds, and lifecycle facts are merged into that row.
- Unmatched Engine actors remain visible in `observed_actors` and the immutable
  Engine snapshot, but are not inserted into the plan's authoritative `actors`.
- Snapshot payload count describes the complete observed Engine set; the
  Runtime update set is validated separately, preventing the snapshot graph
  from failing when unrelated scene actors are present.

## Focused Automated Evidence

```text
completed historical batch + partial current batch -> one Finalizer snapshot
different native handles + matching actor names -> both Runtime actors recovered
unrelated native scene actor -> observed only, not attributed to the plan
both import facts ready_count=1 and both BatchPlans completed
Python syntax compile and existing snapshot/Finalizer regressions passed
```

## Remaining F5 Evidence

The following remains **[待 F5/实机验证]**:

- The next bedroom/forest/mixed run must show all materialized actors receiving
  `engine_actual` bounds through this reconcile path.
- `readiness_missing` must explain any remaining non-Game-ready entities; a
  remaining grounding or sync gap must not be reported as an AABB problem.
- Engine Actor, RuntimeState, Registry, Snapshot, and final report counts must
  agree for the same `plan_id + scene_version`.
