#pragma once

#ifdef CORONA_ENABLE_VISION

#include <ktm/ktm.h>

#include "math/basic_types.h"

namespace Corona::Systems::Vision {

[[nodiscard]] inline auto corona_to_vision_point(const ktm::fvec3& value) -> ktm::fvec3 {
    return {value.x, value.y, -value.z};
}

[[nodiscard]] inline auto corona_to_vision_vector(const ktm::fvec3& value) -> ktm::fvec3 {
    return {value.x, value.y, -value.z};
}

inline void copy_corona_o2w_to_vision(const ktm::fmat4x4& corona, ::vision::float4x4& vision) {
    // Corona/Native uses a left-handed +Z-forward world. Vision uses the common
    // -Z-forward camera convention. Convert object transforms by F * M * F,
    // where F = diag(1, 1, -1, 1).
    for (int col = 0; col < 4; ++col) {
        for (int row = 0; row < 4; ++row) {
            float value = corona[col][row];
            if (row == 2) value = -value;
            if (col == 2) value = -value;
            vision[col][row] = value;
        }
    }
}

}  // namespace Corona::Systems::Vision

#endif  // CORONA_ENABLE_VISION
