# UI System 配置 (ImGui removed — Phase 6 of the ImGui-removal plan).
# The frame loop is now ui_frame_runner.cpp (raw SDL + quad compositor); there is no
# longer an imgui or imgui_backends (imgui_impl_sdl3) target. The imgui.vert/frag GLSL
# shaders are still used by the quad compositor and remain compiled below.
file(GLOB IMGUI_SYSTEM_SOURCES
    ui_system.cpp
    vulk/vulkan_backend.cpp
    vulk/quad_compositor.cpp
    vulk/browser_manager_vulkan.cpp
    ui_frame_runner.cpp

    camera_viewport_manager.cpp
    panel_layout.cpp
    cef/browser_manager.cpp
    cef/browser_ui.cpp
    cef/cef_client.cpp
    cef/cef_native_rpc.cpp
    cef/cef_native_rpc_handlers.cpp
    cef/cef_query_bridge.cpp
    cef/cef_realtime_bridge.cpp
    cef/cef_py_bind.cpp
    sdl/sdl_utils.cpp
    sdl/sdl_window_manager.cpp
    sdl/sdl_input_router.cpp
)

list(APPEND IMGUI_SYSTEM_SOURCES
    ${PROJECT_SOURCE_DIR}/include/corona/systems/ui/vulkan_backend.h
)


corona_add_system(ui
    SOURCES ${IMGUI_SYSTEM_SOURCES}
    DEPENDENCIES
        Horizon
        corona::system::network
        libcef_dll_wrapper
        debug "${CEF_LIBCEF_DEBUG}"
        optimized "${CEF_LIBCEF_RELEASE}"
        SDL3::SDL3-static
        ws2_32
        shlwapi
        dbghelp
        psapi
        version
        winmm
        Python::Python
        nanobind-static
        corona::resource::manager
        nlohmann_json::nlohmann_json
    INCLUDE_DIRS
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/cef
        ${CEF_INCLUDE_DIR}
        ${CEF_ROOT}
)

target_compile_definitions(corona_ui_system PUBLIC VK_NO_PROTOTYPES)

helicon_compile_shaders(corona_ui_system
    OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_shaders"
)

target_include_directories(corona_ui_system BEFORE PUBLIC
    "${CMAKE_CURRENT_BINARY_DIR}/generated_shaders"
)
