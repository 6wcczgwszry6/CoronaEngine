# =============================================================================
# CoronaResource FFmpeg integration
#
# FFmpeg is resolved by Conan. This module gathers the libav* component targets
# behind the existing corona::ffmpeg aggregate.
# =============================================================================

include_guard(GLOBAL)

set(_CORONA_FFMPEG_COMPONENTS avutil avcodec avformat swscale swresample)
set(_corona_ffmpeg_targets)
set(CORONA_RESOURCE_HAVE_FFMPEG TRUE CACHE INTERNAL "FFmpeg targets are available")

foreach(_comp IN LISTS _CORONA_FFMPEG_COMPONENTS)
    if(TARGET ffmpeg::${_comp})
        list(APPEND _corona_ffmpeg_targets ffmpeg::${_comp})
    else()
        set(CORONA_RESOURCE_HAVE_FFMPEG FALSE CACHE INTERNAL "FFmpeg targets are available" FORCE)
        message(WARNING "[FFmpeg] Missing Conan target ffmpeg::${_comp}; video/audio FFmpeg support disabled")
    endif()
endforeach()

if(CORONA_RESOURCE_HAVE_FFMPEG)
    add_library(corona_ffmpeg INTERFACE)
    target_link_libraries(corona_ffmpeg INTERFACE ${_corona_ffmpeg_targets})
    add_library(corona::ffmpeg ALIAS corona_ffmpeg)
endif()

function(corona_resource_copy_runtime_dlls target_name)
    if(NOT WIN32)
        return()
    endif()
    add_custom_command(TARGET ${target_name} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "$<TARGET_RUNTIME_DLLS:${target_name}>" "$<TARGET_FILE_DIR:${target_name}>"
        COMMAND_EXPAND_LISTS
        VERBATIM)
endfunction()

unset(_CORONA_FFMPEG_COMPONENTS)
unset(_corona_ffmpeg_targets)
