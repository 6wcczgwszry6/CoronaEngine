# ==============================================================================
# Display System
# ==============================================================================

corona_add_system(display
    SOURCES
        display_system.cpp
    DEPENDENCIES
        Horizon
)

helicon_compile_shaders(corona_display_system
    OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_shaders"
)

if(BUILD_CORONA_TESTING OR BUILD_TESTING)
    add_executable(corona_ui_surface_removal_race_tests
        tests/test_ui_surface_removal_race.cpp
        ${PROJECT_SOURCE_DIR}/src/systems/ui/ui_surface_lifecycle.cpp
    )
    target_include_directories(corona_ui_surface_removal_race_tests
        PRIVATE ${PROJECT_SOURCE_DIR}/include
    )
    add_test(NAME UiSurfaceRemovalRaceTests
             COMMAND corona_ui_surface_removal_race_tests)
endif()
