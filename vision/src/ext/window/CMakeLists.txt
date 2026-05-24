set(VISION_WINDOW_IMGUI_DIR ${CMAKE_CURRENT_SOURCE_DIR}/imgui)

add_library(vision-window-glfw INTERFACE)
target_link_libraries(vision-window-glfw INTERFACE glfw)

set(VISION_WINDOW_IMGUI_SOURCES
        ${VISION_WINDOW_IMGUI_DIR}/glad/glad.c
        ${VISION_WINDOW_IMGUI_DIR}/gizmo/ImGuizmo.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui_draw.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui_tables.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui_widgets.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui_impl_glfw.cpp
        ${VISION_WINDOW_IMGUI_DIR}/imgui_impl_opengl3.cpp)

add_library(vision-window-imgui STATIC ${VISION_WINDOW_IMGUI_SOURCES})
target_include_directories(vision-window-imgui PUBLIC
        ${VISION_WINDOW_IMGUI_DIR}
        ${VISION_WINDOW_IMGUI_DIR}/glad
        ${VISION_WINDOW_IMGUI_DIR}/gizmo)
target_link_libraries(vision-window-imgui PUBLIC
        vision-window-glfw)

if(UNIX)
    target_compile_options(vision-window-imgui PRIVATE "-fPIC")
endif()

set_target_properties(vision-window-imgui PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}
        WINDOWS_EXPORT_ALL_SYMBOLS ON)

add_library(vision-window-ext INTERFACE)
target_link_libraries(vision-window-ext INTERFACE
        vision-window-glfw
        vision-window-imgui)