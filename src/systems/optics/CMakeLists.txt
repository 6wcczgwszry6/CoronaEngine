# ==============================================================================
# Optics System
# ==============================================================================

corona_add_system(optics
    SOURCES
        optics_system.cpp
        hardware.h
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_material_adapter.cpp>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_material_adapter.h>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_geometry_adapter.cpp>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_geometry_adapter.h>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_camera_adapter.cpp>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_camera_adapter.h>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_light_adapter.cpp>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_light_adapter.h>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_output_bridge.cpp>
        $<$<BOOL:${CORONA_BUILD_VISION}>:vision/vision_output_bridge.h>
    DEPENDENCIES
        Horizon
        corona::resource::manager
    INCLUDE_DIRS
    	$<$<BOOL:${CORONA_BUILD_VISION}>:${CMAKE_SOURCE_DIR}/vision/src>
)

# vision-all_libs is linked PRIVATEly here on purpose: vision bundles its own
# copy of Dear ImGui v1.80 under vision/src/ext/window/imgui and exposes it via
# PUBLIC include directories on vision-window-imgui. If propagated transitively
# to CoronaEngine, that include path is searched before build/_deps/imgui-src
# (v1.92.5), causing <imgui.h> to resolve to the old bundled copy and breaking
# headers that depend on newer types such as ImGuiViewport (C2061). The optics
# system's public headers do not use any vision symbols, so PRIVATE linkage is
# sufficient.
if(CORONA_BUILD_VISION)
    target_link_libraries(corona_optics_system PRIVATE vision-all_libs)
endif()

# ------------------------------------------------------------------------------
# CUDA <-> Vulkan zero-copy interop smoke test (OFF by default)
# When enabled (and Vision is built), OpticsSystem runs a one-shot self-check the
# first time it brings up the Vision/CUDA device: it allocates a small exportable
# CUDA buffer, writes a known pattern, exports the OS handle, imports the SAME
# memory as a Vulkan HardwareBuffer, copies it back and verifies the bytes match.
# This isolates and proves the single unknown (CUDA<->Vulkan external-memory
# aliasing on this machine) before committing to the full zero-copy integration,
# without touching Vision's FrameBuffer or the render path. Result is logged as
# [INTEROP-SMOKE] PASS/FAIL.
# ------------------------------------------------------------------------------
option(CORONA_VISION_INTEROP_SMOKETEST "Run a one-shot CUDA<->Vulkan external-memory aliasing self-check in OpticsSystem" OFF)
if(CORONA_BUILD_VISION AND CORONA_VISION_INTEROP_SMOKETEST)
    target_compile_definitions(corona_optics_system PRIVATE CORONA_VISION_INTEROP_SMOKETEST)
endif()


helicon_compile_shaders(corona_optics_system
    OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_shaders"
)