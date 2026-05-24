file(GLOB_RECURSE HEADER_FILES *.h*)
file(GLOB_RECURSE SOURCE_FILES *.c*)

list(FILTER SOURCE_FILES EXCLUDE REGEX [[.*/GUI/window\.cpp$]])

add_library(vision-window-base STATIC GUI/window.cpp)
target_link_libraries(vision-window-base PUBLIC
        ocarina-core
        ocarina-include)
set_target_properties(vision-window-base PROPERTIES
        FOLDER "vision")

add_library(vision-window SHARED ${HEADER_FILES} ${SOURCE_FILES})
target_link_libraries(vision-window PUBLIC
        ocarina
        vision-window-base
        ocarina-include)
target_link_libraries(vision-window PUBLIC
        vision-window-ext)

set_target_properties(vision-window PROPERTIES
        PUBLIC_HEADER "${HEADER_FILES}"
        LIBRARY_OUTPUT_DIRECTORY ${CMAKE_LIBRARY_OUTPUT_DIRECTORY}
        RUNTIME_OUTPUT_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}
        WINDOWS_EXPORT_ALL_SYMBOLS ON)