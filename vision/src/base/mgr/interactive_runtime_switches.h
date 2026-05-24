#pragma once

/**
 * Compile-time switch for optional non-render work in the interactive frame loop.
 *
 * The canonical value comes from the build system. This fallback is only used
 * for translation units that are built outside the CMake targets.
 */

#ifndef VISION_INTERACTIVE_AUX_WORK
#define VISION_INTERACTIVE_AUX_WORK 0
#endif
