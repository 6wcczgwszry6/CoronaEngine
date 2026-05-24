file(GLOB_RECURSE SOURCE_FILES *.c*)

vision_add_application(vision-sampler-viewer SOURCES ${SOURCE_FILES})
