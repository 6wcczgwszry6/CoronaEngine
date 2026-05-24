file(GLOB_RECURSE SOURCE_FILES *.c*)

vision_add_application(vision-gui SOURCES ${SOURCE_FILES})
target_compile_definitions(vision-gui PRIVATE
	VISION_INTERACTIVE_AUX_WORK=$<BOOL:${VISION_INTERACTIVE_AUX_WORK}>)