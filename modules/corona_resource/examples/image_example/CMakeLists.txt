# =============================================================================
# Image Example
# =============================================================================

corona_add_example(
    NAME ImageExample
    SOURCES image_example.cpp
    LIBRARIES corona::resource::manager
    NEEDS_ASSIMP ON
)

