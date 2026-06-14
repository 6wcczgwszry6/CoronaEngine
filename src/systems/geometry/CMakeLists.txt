# ==============================================================================
# Geometry System
# ==============================================================================

corona_add_system(geometry
    SOURCES
        geometry_system.cpp
        geometry_queries.cpp
        geometry_lod.cpp
        geometry_internal.h
        frustum.cpp
    DEPENDENCIES
        Horizon
        corona::resource::manager
)
