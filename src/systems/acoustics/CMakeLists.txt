# ==============================================================================
# Acoustics System
# ==============================================================================

corona_add_system(acoustics
    SOURCES acoustics_system.cpp
    DEPENDENCIES miniaudio_headers Horizon corona::resource::manager
)
