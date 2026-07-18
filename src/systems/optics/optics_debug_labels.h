#pragma once

namespace Corona::Systems::OpticsDetail {

[[nodiscard]] constexpr bool debug_labels_enabled(bool diagnostic_profile,
                                                  bool explicit_debug_labels) noexcept {
    (void)diagnostic_profile;
    return explicit_debug_labels;
}

}  // namespace Corona::Systems::OpticsDetail
