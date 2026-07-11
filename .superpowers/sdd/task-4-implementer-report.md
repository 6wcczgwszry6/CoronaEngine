# Task 4 implementation report

Implemented `corona_ui_multisurface_smoke` and registered it as `UiMultiSurfaceSmoke`
with `RUN_SERIAL`, a 180-second timeout, and skip return code 77. The executable
uses real SDL3 windows, `VulkanBackend` registration/rebuild/presentation paths,
and a `DisplaySystem` initialize/shutdown cycle without CEF.

The smoke now submits a solid `QuadDraw` on every exercised surface before
`present_surface()`, so the presentation path is not a frame-ready no-op. The
SDL main-window adoption path also computes the new window ID before checking
retirement state, avoiding stale-main ABA behavior.

Verification:

- Default invocation exits 77 with the expected opt-in message.
- The target compiles/links when the existing incremental build is available;
  the current branch also contains small namespace/SDL window-id compile fixes
  required by the preceding lifecycle work.
- GPU execution was not available in this environment, so no Vulkan validation,
  device-lost, image-count, or teardown-timeout evidence is claimed.
- The three-concurrent-CEF-panel manual regression was not performed.

Gate status: **blocked**. Do not start Tasks 5 or 6 until an enabled GPU run and
the CEF regression both complete with clean evidence.
