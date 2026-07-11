# UI Surface Lifecycle and Legacy Docking Cleanup

**Goal:** Make SDL/Vulkan/Display multi-surface creation and teardown deterministic, validate it under concurrency and real GPU use, then remove the legacy native docking paths for ordinary Vue panels while retaining Camera View as an isolated overlay compatibility path.

**Scope boundary:** This plan does not implement Vue drag-out, a product-facing standalone panel API, drag-back, or layout persistence.

**Execution gate:** Tasks 5 and 6 may start only after Tasks 1-4 pass their native lifecycle tests, GPU smoke (when explicitly enabled), and the current CEF multi-window regression. If the manual CEF gate cannot be completed in this environment, stop before deleting the old docking paths and report the gate as pending.

### Task 1: Add the surface lifecycle protocol and pure C++ tests

**Files:**
- Create: `include/corona/systems/ui/ui_surface_lifecycle.h`
- Create: `src/systems/ui/ui_surface_lifecycle.cpp`
- Create: `src/systems/ui/tests/test_ui_surface_lifecycle.cpp`
- Modify: `include/corona/events/display_system_events.h`
- Modify: `include/corona/events/ui_system_events.h`
- Modify: `src/systems/ui/CMakeLists.txt`

**Steps:**
1. Write failing tests for `Registering -> WaitingFirstPresent -> Active -> Removing -> Retired/Failed`, idempotent completion, delayed acknowledgement, skipped first frame, removal before first present, duplicate requests, timeout retention, and main plus three secondary drain.
2. Add `DisplaySurfaceResult { Succeeded, Failed, Cancelled }`, immutable completion payload, and a copyable `SurfaceCompletionTicket` whose completion is thread-safe and idempotent.
3. Add `UiSurfaceState` and `UiSurfaceLifecycle`, including monotonic trace IDs and deadline-aware waits without owning SDL, Vulkan, Display, or CEF objects.
4. Extend surface-changed, UI-frame-ready, and surface-removed events with optional registration, first-present, and removal tickets while retaining source compatibility for existing publishers.
5. Build and run the focused lifecycle tests.

### Task 2: Integrate lifecycle acknowledgements into Display and close the removal race

**Files:**
- Modify: `include/corona/systems/display/display_system.h`
- Modify: `src/systems/display/display_system.cpp`
- Create: `src/systems/display/tests/test_ui_surface_removal_race.cpp`
- Modify: `src/systems/display/CMakeLists.txt`

**Steps:**
1. Write a deterministic test hook/fake seam that pauses Display after taking its state snapshot, requests removal from UI, resumes Display, and asserts no retired image handle is accessed.
2. Carry registration, first-present, and removal tickets through Display pending state.
3. Complete registration only after `HardwareDisplayer` creation succeeds; complete first-present only after a real successful `compose_and_present`; complete removal only after displayer and composite resources are destroyed.
4. On initialization failure, device lost, present exception, removal before first present, duplicate removal, and shutdown, complete every outstanding ticket exactly once with a terminal result and useful error.
5. Make snapshot iteration re-check retirement or otherwise serialize retirement so a removal cannot invalidate an image handle still referenced by a Display snapshot.
6. Ensure `DisplaySystem::shutdown()` destroys displayers, swapchains, and composite resources before completing residual tickets.
7. Build and run Display/lifecycle race tests.

### Task 3: Fix SDL/Vulkan/UiSystem creation, removal, and shutdown ordering

**Files:**
- Modify: `include/corona/systems/ui/sdl_window_manager.h`
- Modify: `src/systems/ui/sdl_window_manager.cpp`
- Modify: `include/corona/systems/ui/vulkan_backend.h`
- Modify: `src/systems/ui/vulk/vulkan_backend.cpp`
- Modify: `src/systems/ui/ui_frame_runner.cpp`
- Modify: `include/corona/systems/ui/ui_system.h`
- Modify: `src/systems/ui/ui_system.cpp`
- Add/update focused tests under `src/systems/ui/tests/`

**Steps:**
1. Extend tests/fakes for hidden-window registration, first-present reveal, timeout-without-destroy, duplicate close, and global shutdown order.
2. Make `SdlWindowManager` own only SDL windows and their per-window drag regions/trace metadata; separate create, mark-retired, and final destroy APIs.
3. Create secondary windows hidden, register their Vulkan UI surface, publish Display changed, wait registration, render, wait first-present, then reveal.
4. On removal, stop input/new frames, publish remove and wait up to five seconds, wait the producer and Display `consumed_receipt`, unregister/deallocate Vulkan image state, close CEF/business resources, then destroy SDL.
5. If removal acknowledgement times out or fails, leave the SDL window hidden in `RemovalFailed` and do not destroy/reuse its native handle.
6. Make `VulkanBackend::unregister_surface()` obey the same producer/consumer receipt draining rules as resize/rebuild.
7. Make `UiSystem::stop()` request main and all secondary removals while Display still runs, use one ten-second global deadline, and allow `shutdown()` to destroy SDL/CEF only after successful drain.
8. Add lifecycle trace logging containing trace ID, SDL ID, native handle, image handle, extent, thread, and phase.
9. Run focused lifecycle/removal tests and an incremental `corona_engine` build.

### Task 4: Add and run multi-surface validation gates

**Files:**
- Create: `src/systems/ui/tests/ui_multisurface_smoke.cpp`
- Modify: `src/systems/ui/CMakeLists.txt`
- Modify: CTest properties in the relevant CMake files
- Add validation notes/log references under `docs/`

**Steps:**
1. Add `corona_ui_multisurface_smoke` using real SDL, `VulkanBackend`, and `DisplaySystem`, drawing a simple quad without CEF.
2. Cover 1/3/16 windows, same-frame bursts, resize/minimize/restore, 100 create/destroy cycles, and direct shutdown with three live secondaries.
3. Return CTest skip code 77 unless `CORONA_RUN_GPU_SMOKE=1`; mark the test `RUN_SERIAL`.
4. Run pure native lifecycle and race tests.
5. With GPU smoke enabled, run `UiMultiSurfaceSmoke`; capture validation, device-lost, resource-count, and teardown-timeout diagnostics.
6. Before deleting legacy commands, exercise the current `createDetachedPanel` path with three concurrent CEF panels and repeated closure. Save the validation/device-lost/resource-count evidence.
7. Record whether all cleanup gates passed. Do not proceed to Tasks 5-6 if any required gate failed or could not be performed.

### Task 5: Remove ordinary-panel native floating state from Vue

**Files:**
- Modify: `editor/Frontend/package.json`
- Add/update Node tests under `editor/Frontend/`
- Delete: `editor/Frontend/src/**/panelWindows.js` (locate exact path)
- Modify: tool manifest files under `editor/Frontend/src/`
- Modify: DockPanel/MainPage/dock store/bridge sources under `editor/Frontend/src/`

**Steps:**
1. Add a deterministic `npm test` command and failing source-contract tests asserting: manifests have no external default mode, DockPanel has no pop-out action, MainPage does not auto-open external windows, dockStore has no external state, and the bridge has no ordinary-panel window commands.
2. Delete `panelWindows.js`, external startup initialization, and tool manifest `defaultOpenMode/defaultFloatPosition/minFloat*` fields.
3. Reduce dock store state to `open/dockZone/order/width/height`; remove `mode`, `externalTabId`, `setExternal`, `markExternalClosed`, and `popIn`.
4. Preserve Vue-internal sorting, cross-zone moves, close behavior, and current `autoInit` semantics; remove ordinary-panel native pop-out UI and handlers.
5. Remove ordinary-panel wrappers for `createPanelTab`, `createDetachedPanel`, `detachPanel`, `redockPanel`, and `closePanelTab`; retain Camera View, cross-tab broadcast, drag regions, and required `closeThisTab` compatibility.
6. Run frontend tests, lint, and build.

### Task 6: Remove native ordinary-panel docking and isolate Camera overlay

**Files:**
- Modify: `src/systems/ui/cef/browser_manager.h`
- Modify: `src/systems/ui/cef/browser_manager.cpp`
- Modify: `src/systems/ui/cef/cef_realtime_bridge.cpp`
- Modify: `src/systems/ui/ui_frame_runner.cpp`
- Modify/remove old layout/docking sources and CMake entries under `src/systems/ui/`
- Add/update native contract/layout tests under `src/systems/ui/tests/`

**Steps:**
1. Add failing tests for a `BrowserTabKind { MainEditor, CameraOverlay }` model, one fullscreen main editor quad, explicit Camera overlay rectangles, and absence of ordinary-panel native commands/state.
2. Replace string-based general tab construction with `create_main_tab()` and `create_camera_tab()`.
3. Delete handlers for `createPanelTab`, `createDetachedPanel`, `detachPanel`, `redockPanel`, and `closePanelTab`.
4. Remove ordinary docking/floating/detach fields and stale drag/resize/reposition bookkeeping from `BrowserTab`.
5. Rename Camera geometry to `viewport_x/y/width/height`; preserve Camera commands and current overlay behavior.
6. Delete fixed-zone `panel_layout`, main-window floating move/resize, temporary z-order, native panel hit-testing, and `reconcile_detach_states()`.
7. Move Camera placement into an explicit `camera_overlay_layout` module with no docking vocabulary or anchor strings.
8. Keep the repaired standalone SDL surface infrastructure independent of BrowserManager/tab IDs; store drag regions on `ManagedWindow`.
9. Update CMake and delete unreferenced docking files.
10. Run native tests and the full incremental build.

### Task 7: Documentation and final verification

**Files:**
- Modify/create Editor window-management documentation under `docs/`
- Modify: relevant `README*` files

**Steps:**
1. Document ordinary panels as Vue-Dock-only, Camera View as a temporary native overlay, and standalone SDL panels as infrastructure not exposed to products yet.
2. Remove obsolete ImGui, Qt `QDockWidget`, and legacy floating descriptions.
3. Run bundled npm `test`, `lint`, and `build` for `editor/Frontend`.
4. Run CTest filters for `UiSurfaceLifecycle` and `UiSurfaceRemovalRace`.
5. With `CORONA_RUN_GPU_SMOKE=1`, run `UiMultiSurfaceSmoke` serially.
6. Incrementally build `corona_engine` RelWithDebInfo from the `ninja-msvc` tree; do not use `--fresh`.
7. Check logs for teardown timeout, stale/unoccupied image handles, Vulkan validation/SYNC hazards, device lost, and leaked SDL/Display/Vulkan resource counts.
8. Record manual acceptance status: Vue-only ordinary panels and cross-zone moves; no pop-out/automatic external window; Camera regression-free; no per-window two-second shutdown delay; all surface counts return to baseline.

## Acceptance criteria

- Every surface reaches exactly one terminal lifecycle result.
- No SDL/native window is destroyed or reused before Display and Vulkan consumers retire it.
- Runtime removal has a five-second deadline and non-destructive failure; global shutdown has one ten-second deadline.
- Native lifecycle/race tests and enabled GPU smoke pass with zero validation/SYNC/device-lost/stale-handle errors.
- Ordinary panels expose no native docking/window API or state after the gate passes.
- Camera Overlay is the only remaining native main-window overlay path.
