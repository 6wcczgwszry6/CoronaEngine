
# ==============================================================================
# Vision sub-project (integrated into CoronaEngine)
#
# This file is meant to be included via `add_subdirectory(vision)` from the
# CoronaEngine root, gated by `CORONA_BUILD_VISION`. It no longer issues its
# own `project()` call or overrides global output directories. Third-party
# dependencies (assimp, glfw, cxxopts, Horizon) are fetched at the root level
# (see misc/cmake/corona_third_party.cmake) and reused here.
# ==============================================================================

# Vision sources require C++20 and depend on CUDA.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(CUDAToolkit 11.0 REQUIRED)

add_compile_definitions(_SILENCE_STDEXT_ARR_ITERS_DEPRECATION_WARNING)

# Bridge legacy Vision option names to the new CoronaEngine-controlled options.
# Vision sub-CMake scripts still test these legacy names; aliasing here means
# we do not have to mass-rewrite the deeper tree.
set(OIDN_ON           ${VISION_BUILD_OIDN}  CACHE INTERNAL "Vision OIDN toggle (alias of VISION_BUILD_OIDN)")
set(OCARINA_BUILD_TESTS ${VISION_BUILD_TESTS} CACHE INTERNAL "Vision test toggle (alias of VISION_BUILD_TESTS)")

# Allow Vision sources to find their own headers via `src/...`.
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/src)

if (MSVC)
    add_compile_options(/wd4996)
    add_compile_options(/MP)
endif ()

function(vision_add_application name)
    cmake_parse_arguments(APP "" "" "SOURCES" ${ARGN})
    add_executable(${name} ${APP_SOURCES})
    target_compile_features(${name} PRIVATE c_std_11 cxx_std_20)
    target_link_libraries(${name} PRIVATE vision-all_libs ${STDCXX_EXTRA_LIBS})
    set_target_properties(${name} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/")
endfunction()

message(STATUS "[Vision] CUDAToolkit found, integrating Vision sources")
message(STATUS "[Vision] VISION_BUILD_APPS  = ${VISION_BUILD_APPS}")
message(STATUS "[Vision] VISION_BUILD_TESTS = ${VISION_BUILD_TESTS}")
message(STATUS "[Vision] VISION_BUILD_OIDN  = ${VISION_BUILD_OIDN}")

add_subdirectory(src)

if (VISION_BUILD_OIDN)
    add_custom_target(CP_OIDN_CUDA ALL
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    $<TARGET_FILE_DIR:OpenImageDenoise_device_cuda>/OpenImageDenoise_device_cuda.dll
                    ${CMAKE_BINARY_DIR}/bin/
            DEPENDS OpenImageDenoise_device_cuda
    )
endif ()
