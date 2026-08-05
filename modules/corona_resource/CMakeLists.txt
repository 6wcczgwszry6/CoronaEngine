set(CORONA_RESOURCE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}")

message(STATUS "[CoronaResource] Configuring resource libraries inside ${PROJECT_NAME}")

# Include configuration modules
include(CoronaResourceOptions)
include(CoronaResourceCompiler)
include(CoronaResourceDependencies)
include(CoronaResourceFFmpeg)
include(CoronaResourceExamples)

# Add subdirectories
add_subdirectory(src)

if(CORONA_RESOURCE_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

if(CORONA_RESOURCE_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
