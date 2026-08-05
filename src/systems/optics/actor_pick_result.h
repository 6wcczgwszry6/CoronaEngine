#pragma once

#include <cstdint>
#include <span>
#include <string_view>

namespace Corona::Systems::OpticsDetail {

struct ActorPickResolvedResult {
    std::string_view status;
    std::uintptr_t actor_handle{0};
};

[[nodiscard]] inline ActorPickResolvedResult resolve_actor_pick_result(
    bool read_ok,
    std::uint32_t instance_id,
    std::span<const std::uintptr_t> scene_actor_handles) noexcept {
    if (!read_ok) {
        return {"error", 0};
    }
    if (instance_id == 0) {
        return {"miss", 0};
    }

    const auto instance_index = static_cast<std::size_t>(instance_id - 1);
    if (instance_index >= scene_actor_handles.size()) {
        return {"miss", 0};
    }
    return {"success", scene_actor_handles[instance_index]};
}

}  // namespace Corona::Systems::OpticsDetail
