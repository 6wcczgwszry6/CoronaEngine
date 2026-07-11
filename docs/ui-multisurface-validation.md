# UI multi-surface validation

The `UiMultiSurfaceSmoke` CTest target is a GPU-gated harness for the SDL/Vulkan
surface lifecycle. It is marked `RUN_SERIAL`, returns CTest skip code 77 unless
`CORONA_RUN_GPU_SMOKE=1`, and exercises the requested 1/3/16-window burst,
resize/minimize/restore, 100 create/destroy cycles, and direct shutdown with
three secondary windows.

The harness owns real SDL windows and `VulkanBackend` surfaces, initializes the
production `KernelContext`/EventBus, and runs the main-surface DisplaySystem
registration/update path. Secondary registration is currently backend-local
and does not yet publish the full Display changed/removal/ack choreography, so
an enabled run remains best-effort infrastructure coverage rather than proof of
all end-to-end Display composition and teardown. A headless/default run was
recorded as skipped (exit 77):

```text
UiMultiSurfaceSmoke skipped; set CORONA_RUN_GPU_SMOKE=1 to enable
```

The CEF three-panel regression remains a manual prerequisite and was not run in
this environment. Therefore the native/GPU/CEF cleanup gate is **blocked** and
legacy Vue/native docking cleanup must not begin until those checks produce
validation, device-lost, resource-count, and teardown-timeout logs.
