function(corona_dev_bootstrap)
    if(NOT DEFINED CORONA_DEV_CONFIGURATION OR CORONA_DEV_CONFIGURATION STREQUAL "")
        set(CORONA_DEV_CONFIGURATION "RelWithDebInfo" CACHE STRING "CoronaEngine developer configuration")
    endif()
    string(TOLOWER "${CORONA_DEV_CONFIGURATION}" _corona_configuration_slug)
    set(_corona_toolchain
        "${CMAKE_CURRENT_SOURCE_DIR}/build/conan/${_corona_configuration_slug}/generators/conan_toolchain.cmake")
    set(_corona_build_environment
        "${CMAKE_CURRENT_SOURCE_DIR}/build/conan/${_corona_configuration_slug}/generators/dev_build_environment.cmake")
    if(NOT DEFINED ENV{CORONA_DEV_BOOTSTRAP_ACTIVE})
        find_program(_corona_uv uv REQUIRED)
        execute_process(
            COMMAND "${_corona_uv}" run --frozen python tools/dev.py _bootstrap
                    --configuration "${CORONA_DEV_CONFIGURATION}"
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            RESULT_VARIABLE _corona_bootstrap_result
            OUTPUT_VARIABLE _corona_bootstrap_stdout
            ERROR_VARIABLE _corona_bootstrap_stderr
        )
        if(NOT _corona_bootstrap_result EQUAL 0)
            message(FATAL_ERROR
                "CoronaEngine dependency bootstrap failed (${_corona_bootstrap_result}).\n"
                "${_corona_bootstrap_stdout}\n${_corona_bootstrap_stderr}")
        endif()
    endif()
    if(NOT EXISTS "${_corona_toolchain}")
        message(FATAL_ERROR "CoronaEngine Conan toolchain was not generated: ${_corona_toolchain}")
    endif()
    if(NOT EXISTS "${_corona_build_environment}")
        message(FATAL_ERROR "CoronaEngine build environment was not generated: ${_corona_build_environment}")
    endif()
    include("${_corona_build_environment}")
    set(CMAKE_TOOLCHAIN_FILE "${_corona_toolchain}" CACHE FILEPATH "Conan toolchain" FORCE)
endfunction()
