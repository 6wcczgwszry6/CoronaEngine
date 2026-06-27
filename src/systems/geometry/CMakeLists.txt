# ==============================================================================
# Geometry System
# ==============================================================================

corona_add_system(geometry
    SOURCES
        geometry_system.cpp
        geometry_queries.cpp
        geometry_lod.cpp
        geometry_builder.cpp
        geometry_internal.h
        frustum.cpp
        actor_cache.cpp
    DEPENDENCIES
        Horizon
        corona::resource::manager
        nlohmann_json::nlohmann_json
)
