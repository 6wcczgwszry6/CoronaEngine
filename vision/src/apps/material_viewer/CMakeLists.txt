file(GLOB_RECURSE SOURCE_FILES *.c*)

vision_add_application(vision-material-viewer SOURCES ${SOURCE_FILES})
add_dependencies(vision-material-viewer vision-sampler-independent)
