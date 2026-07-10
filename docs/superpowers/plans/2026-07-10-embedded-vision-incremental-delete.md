# Embedded Vision Incremental Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete actors from editor-imported embedded Vision scenes without reloading the JSON scene or recreating the Vision runtime.

**Architecture:** Persist the deletion in the embedded document as before, but let the Optics external-live synchronizer remove the active shape incrementally. A small removal-policy helper distinguishes embedded JSON runtimes from ordinary external-live scenes so the latter keep their original-shape protection.

**Tech Stack:** C++20, Vision scene integration, Python `unittest`, CMake/Ninja Multi-Config, MSVC RelWithDebInfo.

## Global Constraints

- Apply only to editor-imported embedded Vision scenes.
- Do not change external Vision file or ordinary external-live behavior.
- Do not recreate Vision pipeline, framebuffer, denoiser, or view contexts on actor deletion.
- Persist the embedded document so deleted actors remain deleted after reopening.
- Follow TDD: observe each new regression test fail before editing production code.

---

### Task 1: Stop editor deletion from submitting a full embedded scene reload

**Files:**
- Modify: `editor/plugins/SceneTools/tests/test_native_screenshot_rpc.py:3306`
- Modify: `src/systems/ui/cef/cef_editor_native_api_handlers.cpp:3530`

**Interfaces:**
- Consumes: `persist_embedded_vision_document(NativeEditorScene&, nlohmann::json&) -> bool`
- Produces: `remove_native_actor_from_embedded_vision_document(...)` persists deletion without calling `refresh_embedded_vision_view()`.

- [ ] **Step 1: Write the failing editor regression assertion**

Extract `remove_native_actor_from_embedded_vision_document()` in
`test_embedded_vision_actor_operations_update_document_without_reload` and add:

```python
        document_remove_body = re.search(
            r"bool remove_native_actor_from_embedded_vision_document\(.*?\n\}",
            source,
            re.S,
        )
        self.assertIsNotNone(document_remove_body)
        self.assertIn("persist_embedded_vision_document", document_remove_body.group(0))
        self.assertNotIn("refresh_embedded_vision_view", document_remove_body.group(0))
        self.assertNotIn("load_vision_scene_from_json", document_remove_body.group(0))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m unittest editor.plugins.SceneTools.tests.test_native_screenshot_rpc.NativeSceneToolsRpcTests.test_embedded_vision_actor_operations_update_document_without_reload
```

Expected: FAIL because the helper currently contains `refresh_embedded_vision_view(scene, document)`.

- [ ] **Step 3: Remove the full refresh from the deletion helper**

Replace:

```cpp
        const bool persisted = removed && persist_embedded_vision_document(scene, document);
        if (persisted) {
            refresh_embedded_vision_view(scene, document);
        }
        return persisted;
```

with:

```cpp
        return removed && persist_embedded_vision_document(scene, document);
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: `OK`.

---

### Task 2: Permit incremental removal of original embedded shapes only

**Files:**
- Modify: `include/corona/systems/optics/vision_scene_resource.h:137`
- Modify: `src/systems/optics/tests/test_vision_scene_resource.cpp:413`
- Modify: `src/systems/optics/optics_system.cpp:5133`

**Interfaces:**
- Produces: `Vision::external_live_shape_is_removable(const ExternalLiveShapeRecord&, bool embedded_runtime) -> bool`
- Consumes: `VisionPipelineRuntime::scene_json`, `ExternalLiveShapeRecord::dynamically_added`

- [ ] **Step 1: Write the failing removal-policy test**

Add this test and invoke it from `main()`:

```cpp
void embedded_original_shapes_are_incrementally_removable() {
    ExternalLiveShapeRecord original{.dynamically_added = false};
    ExternalLiveShapeRecord appended{.dynamically_added = true};

    expect(external_live_shape_is_removable(original, true),
           "embedded original shapes should be incrementally removable");
    expect(!external_live_shape_is_removable(original, false),
           "ordinary external-live original shapes must remain protected");
    expect(external_live_shape_is_removable(appended, false),
           "dynamically appended shapes should remain removable");
}
```

- [ ] **Step 2: Build the test and verify RED**

Run through `VsDevCmd.bat`:

```powershell
cmake --build D:/CoronaEngine/build --config RelWithDebInfo --target corona_vision_scene_resource_tests -- --quiet
```

Expected: compile failure because `external_live_shape_is_removable` is not defined.

- [ ] **Step 3: Add the minimal removal-policy helper**

Immediately after `ExternalLiveShapeRecord`, add:

```cpp
[[nodiscard]] constexpr bool external_live_shape_is_removable(
    const ExternalLiveShapeRecord& record,
    bool embedded_runtime) noexcept {
    return record.dynamically_added || embedded_runtime;
}
```

- [ ] **Step 4: Use the policy in the Optics synchronizer**

In `sync_external_live_vision_transforms()`, compute:

```cpp
    const bool embedded_runtime = !runtime.scene_json.empty();
```

Then replace the current `!record->dynamically_added` guard with:

```cpp
        if (!Vision::external_live_shape_is_removable(*record, embedded_runtime)) {
            scene_resource->erase_external_live_shape(actor_handle);
            return;
        }
```

- [ ] **Step 5: Build and run the focused C++ test and verify GREEN**

Build with the command from Step 2, then run:

```powershell
& 'D:\CoronaEngine\build\src\systems\optics\RelWithDebInfo\corona_vision_scene_resource_tests.exe'
```

Expected: exit code `0`.

---

### Task 3: Regression verification

**Files:**
- Verify: `editor/plugins/SceneTools/tests/test_native_screenshot_rpc.py`
- Verify: `src/systems/optics/tests/test_vision_scene_resource.cpp`
- Verify: `src/systems/ui/cef/cef_editor_native_api_handlers.cpp`
- Verify: `src/systems/optics/optics_system.cpp`

**Interfaces:**
- Consumes: completed behavior from Tasks 1 and 2.
- Produces: build and test evidence for the embedded-only incremental deletion.

- [ ] **Step 1: Run the complete SceneTools source regression suite**

```powershell
python -m unittest editor.plugins.SceneTools.tests.test_native_screenshot_rpc
```

Expected: all tests pass.

- [ ] **Step 2: Run the complete Vision scene-resource test executable**

```powershell
& 'D:\CoronaEngine\build\src\systems\optics\RelWithDebInfo\corona_vision_scene_resource_tests.exe'
```

Expected: exit code `0`.

- [ ] **Step 3: Build the engine incrementally**

Run through `VsDevCmd.bat`:

```powershell
cmake --build D:/CoronaEngine/build --config RelWithDebInfo --target corona_engine -- --quiet
```

Expected: build succeeds with no compiler or linker errors.

- [ ] **Step 4: Inspect the scoped diff**

```powershell
git diff --check
git diff -- editor/plugins/SceneTools/tests/test_native_screenshot_rpc.py include/corona/systems/optics/vision_scene_resource.h src/systems/optics/tests/test_vision_scene_resource.cpp src/systems/optics/optics_system.cpp src/systems/ui/cef/cef_editor_native_api_handlers.cpp
```

Expected: no whitespace errors and no changes outside the approved embedded deletion behavior.
