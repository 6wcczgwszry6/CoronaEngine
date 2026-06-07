# =============================================================================
# Scene Example
# =============================================================================

corona_add_example(
    NAME SceneExample
    SOURCES scene_example.cpp
    LIBRARIES corona::resource::manager corona::resource::scene
    NEEDS_ASSIMP ON
)

