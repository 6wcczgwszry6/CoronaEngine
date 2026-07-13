# Native Optics Latency Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound Native rendering to two unfinished submissions, release Scene/Camera locks before heavy rendering, and remove debug-label work from normal frames.

**Architecture:** Horizon exposes a token-specific CPU wait for `SubmitReceipt`; Optics owns a two-entry FIFO and waits before consuming the newest camera state or recording another camera. Storage values are copied through small internal snapshot helpers, and label formatting short-circuits unless profiling is enabled.

**Tech Stack:** C++20, Horizon Vulkan timeline semaphores, Corona `Storage`, CMake/CTest, Ninja Multi-Config/MSVC.

## Global Constraints

- Preserve all existing dirty-worktree changes in CoronaEngine and the populated Horizon checkout.
- Keep shadows, deferred compute, SSAO, exposure, resolution, and source meshes unchanged.
- Never use queue-wide `wait_idle()` for the steady-state two-frame limiter.
- Maximum unfinished Native submissions is exactly 2.
- Do not create git commits unless the user explicitly requests them.

---

### Task 1: Exact Horizon Receipt Completion

**Files:**
- Modify: `build/_deps/horizon-src/include/horizon.h`
- Modify: `build/_deps/horizon-src/src/hardware_wrapper_vulkan/hardware/execution.cpp`
- Create: `misc/patches/horizon-wait-until-complete.patch`
- Modify: `misc/cmake/corona_third_party.cmake`
- Create: `src/systems/optics/tests/test_horizon_receipt_completion.cpp`
- Modify: `src/systems/optics/CMakeLists.txt`

**Interfaces:**
- Produces: `HardwareExecutor& wait_until_complete(const SubmitReceipt& receipt)`.
- Consumes: existing `Queue::wait_for(const SubmissionToken&)` and `Queue::retire_completed()`.

- [ ] **Step 1: Add a failing fake-queue test**

Create two fake queue submissions, build a receipt containing only token 1, call `wait_until_complete`, and assert `in_flight_count()==1`. The compilation must initially fail because the public method does not exist.

- [ ] **Step 2: Run the focused test and verify RED**

Run the configured test target. Expected failure: MSVC reports that `HardwareExecutor` has no member named `wait_until_complete`.

- [ ] **Step 3: Implement token-specific waiting**

Declare the public method next to `wait_idle`. In the implementation, resolve every non-zero token exactly as existing `wait_idle` does, call `queue->wait_for(token)`, then `queue->retire_completed()`; do not call `queue->wait_idle()`.

- [ ] **Step 4: Persist the dependency delta**

Record only the method declaration and implementation in an idempotently applied FetchContent patch. The patch command must accept an already-applied checkout and fail on any unrelated context mismatch.

- [ ] **Step 5: Run the focused test and verify GREEN**

Expected: waiting for token 1 retires only submission 1 while submission 2 remains in flight.

### Task 2: Native Two-Frame Limiter

**Files:**
- Create: `src/systems/optics/native_frame_limiter.h`
- Create: `src/systems/optics/native_frame_limiter.cpp`
- Create: `src/systems/optics/tests/test_native_frame_limiter.cpp`
- Modify: `src/systems/optics/CMakeLists.txt`
- Modify: `include/corona/systems/optics/optics_system.h`
- Modify: `src/systems/optics/optics_system.cpp`

**Interfaces:**
- Produces: `NativeFrameLimiter::at_capacity()`, `oldest()`, `track()`, `retire_oldest()`, `empty()`, and `size()`.
- Consumes: `Horizon::SubmitReceipt` and Task 1 `wait_until_complete`.

- [ ] **Step 1: Write failing FIFO and capacity tests**

Assert empty receipts are ignored, two serials are accepted in order, capacity is reported at 2, the third receipt is rejected until the oldest is retired, and drain order is FIFO.

- [ ] **Step 2: Run the focused test and verify RED**

Expected failure: the limiter type/header is absent.

- [ ] **Step 3: Implement the minimal limiter**

Use `std::deque<SubmitReceipt>` with `static constexpr std::size_t kMaxFramesInFlight = 2`. `track` returns `false` for a non-empty receipt when already full and never silently discards a GPU receipt.

- [ ] **Step 4: Integrate with Optics update/commit/shutdown**

Add an Optics helper that waits and retires FIFO entries until capacity is available. Call it before pending camera commands are applied and before each Native camera is recorded. Track only successful non-empty commits and drain all tracked receipts before GPU resources are destroyed.

- [ ] **Step 5: Run limiter and existing Optics tests**

Expected: focused tests pass and existing Vision Optics tests remain green.

### Task 3: Scene and Camera Snapshot Lock Release

**Files:**
- Create: `src/systems/optics/optics_storage_snapshot.h`
- Create: `src/systems/optics/tests/test_optics_storage_snapshot.cpp`
- Modify: `src/systems/optics/CMakeLists.txt`
- Modify: `src/systems/optics/optics_system.cpp`

**Interfaces:**
- Produces: `OpticsDetail::snapshot_storage<T, Capacity, Buffers>()` and `snapshot_storage_value<T, Capacity, Buffers>()`.
- Consumes: Corona `Kernel::Utils::Storage` read iterators/handles.

- [ ] **Step 1: Write failing snapshot tests**

Allocate a test value, take a collection and single-value snapshot, mutate the original through `try_acquire_write`, and assert both snapshots retain the old value. Assert write acquisition succeeds immediately after each helper returns.

- [ ] **Step 2: Run the focused test and verify RED**

Expected failure: snapshot helpers are not defined.

- [ ] **Step 3: Implement scoped-copy helpers**

Copy values inside the helper scope and return only owning `std::vector<T>`/`std::optional<T>` values; never return an iterator, read handle, pointer, or reference.

- [ ] **Step 4: Render from snapshots**

Snapshot all scenes before entering heavy work. For every camera handle, take a `CameraDevice` snapshot and release its handle before render-target allocation, instance collection, command recording, exact waiting, or commit. Keep Vision behavior unchanged.

- [ ] **Step 5: Run lock regression and Optics tests**

Expected: snapshot tests pass and all prior focused tests remain green.

### Task 4: Profile-Only Debug Labels

**Files:**
- Create: `src/systems/optics/optics_debug_labels.h`
- Create: `src/systems/optics/optics_debug_labels.cpp`
- Create: `src/systems/optics/tests/test_optics_debug_labels.cpp`
- Modify: `src/systems/optics/CMakeLists.txt`
- Modify: `src/systems/optics/optics_system.cpp`

**Interfaces:**
- Produces: `OpticsDetail::make_draw_label(bool enabled, ...)` and `make_dispatch_label(bool enabled, ...)`.
- Consumes: `OpticsDiagConfig::profile`.

- [ ] **Step 1: Write failing label-policy tests**

Assert disabled draw/dispatch calls return empty strings. Assert enabled calls contain pass, frame, instance/material counts, and draw resource identifiers.

- [ ] **Step 2: Run the focused test and verify RED**

Expected failure: the policy functions do not exist.

- [ ] **Step 3: Implement early-return formatting**

Return `{}` before constructing `std::ostringstream` when disabled. Preserve the current enabled label text.

- [ ] **Step 4: Route every label callsite through the policy**

Pass `optics_diag_config().profile` for Native scene, shadow, UI, cursor, composite, actor-pick, debug-resolve, SSAO, lighting, sky, and tonemap labels. Empty labels rely on Horizon's existing marker short-circuit.

- [ ] **Step 5: Run the focused and full Optics test set**

Expected: policy tests and all prior tests pass.

### Task 5: Build and Runtime Verification

**Files:**
- Modify only if verification exposes a defect in Tasks 1-4.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: build/test logs and a 30-second runtime comparison.

- [ ] **Step 1: Configure the existing preset without a fresh build tree**

Run `cmake --preset ninja-msvc -DCMAKE_LINKER=link -DCMAKE_AR=lib -DCMAKE_RANLIB=:` through `VsDevCmd.bat` so newly registered tests are generated.

- [ ] **Step 2: Run focused CTest targets**

Run receipt completion, limiter, snapshot, and debug-label tests with `--output-on-failure`.

- [ ] **Step 3: Build `corona_engine` RelWithDebInfo**

Use the repository's documented incremental Ninja Multi-Config command and retain the full build log outside the response.

- [ ] **Step 4: Launch with diagnostics inherited by the process**

Set `HORIZON_TRACE_TIMELINE=1` and `CORONA_OPTICS_DIAG_PROFILE=1` in the same PowerShell process that starts `corona_engine.exe`. Keep all normal render passes enabled.

- [ ] **Step 5: Verify the target scene for 30 seconds**

Move the camera continuously. Confirm Native tracked receipts never exceed 2, no descriptor/device-lost errors occur, and Geometry cadence no longer stretches to multi-second intervals because of a held Scene lock.

- [ ] **Step 6: Review the complete diff**

Confirm no shader, LOD, scene asset, or unrelated dirty-worktree changes were modified by this phase.
