#pragma once

namespace Corona::Systems::OpticsDetail {

[[nodiscard]] constexpr bool debug_labels_enabled(bool diagnostic_profile) noexcept {
    return diagnostic_profile;
}

}  // namespace Corona::Systems::OpticsDetail
