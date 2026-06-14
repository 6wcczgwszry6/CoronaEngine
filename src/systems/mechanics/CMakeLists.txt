# ==============================================================================
# Mechanics System
# ==============================================================================

corona_add_system(mechanics
    SOURCES
        mechanics_system.cpp
        mechanics_lifecycle.cpp
        mechanics_internal.h
    DEPENDENCIES
        Horizon
        corona::resource::manager
)
