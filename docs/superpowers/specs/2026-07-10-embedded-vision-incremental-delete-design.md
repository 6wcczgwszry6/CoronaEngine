# Embedded Vision Incremental Delete

## Goal

Deleting an actor imported from an embedded Vision document must update the
active Vision scene without reloading the JSON scene or replacing its runtime,
pipeline, framebuffer, denoiser, or view contexts.

This change applies only to editor-imported embedded Vision scenes. External
Vision files and ordinary external-live scenes retain their current behavior.

## Current Behavior

The editor removes the actor from the native scene and embedded Vision document,
then `remove_native_actor_from_embedded_vision_document()` calls
`refresh_embedded_vision_view()`. That refresh submits the complete document via
`load_vision_scene_from_json()`, which releases and recreates the embedded Vision
runtime.

Optics already detects removed external-live actor bindings and has an
incremental geometry update path. It does not currently remove shapes loaded as
part of the original Vision document because their records have
`dynamically_added == false`. This protection is correct for ordinary
external-live files but prevents embedded scenes from using the incremental
path.

## Design

The editor will continue removing the shape from the embedded JSON document and
persisting it to the scene file. It will stop refreshing the active Vision view
after a successful deletion.

Optics will distinguish an embedded live runtime from an ordinary external-live
runtime by the presence of `runtime.scene_json`. During external-live geometry
synchronization, a removed actor may delete its original Vision shape when the
runtime is embedded. For ordinary external-live scenes, an original
`dynamically_added == false` shape remains protected exactly as before.

The existing removal path will:

1. Remove the matching Vision shape group.
2. Remap later shape indices and update their actor bindings.
3. Rebuild Vision geometry GPU resources and acceleration structures.
4. Refresh logical transform versions and invalidate accumulation.

It will not reload JSON or recreate the pipeline/session-level render state.

## Failure Handling

If document persistence fails, the helper returns failure as it does today. If
the incremental Optics removal cannot find or remove a matching shape, it clears
stale tracking and logs the existing synchronization error path; it does not
fall back to a hidden full scene reload.

The persisted embedded document remains the source of truth for the next scene
open, so a successfully deleted actor cannot reappear after restart.

## Tests

- Update the editor source-level regression test to assert that embedded actor
  deletion persists the document without calling
  `refresh_embedded_vision_view()` or `load_vision_scene_from_json()`.
- Add a focused Vision scene-resource/removal-policy test proving that original
  shapes are removable for embedded JSON runtimes.
- Preserve a regression assertion that original shapes remain protected for
  ordinary external-live scenes.
- Build and run the relevant SceneTools and Optics tests, then build the
  `corona_engine` RelWithDebInfo target.

## Non-Goals

- Incremental addition or replacement behavior beyond the existing path.
- Changes to external Vision file reload semantics.
- A general JSON patch protocol for Vision.
- Reclaiming every orphaned material immediately; existing Vision tidy-up owns
  geometry cleanup, while full scene teardown remains responsible for complete
  resource reclamation.
