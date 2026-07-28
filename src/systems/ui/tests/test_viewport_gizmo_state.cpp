#include <corona/shared_data_hub.h>

#include <iostream>

namespace {

bool expect(bool condition, const char* message) {
    if (!condition) {
        std::cerr << message << '\n';
        return false;
    }
    return true;
}

}  // namespace

int main() {
    auto& hub = Corona::SharedDataHub::instance();
    hub.set_viewport_gizmo_target({
        .camera_handle = 101,
        .scene_id = "Scene/default.scene",
        .actor_name = "Cube",
        .actor_handle = 202,
    });

    const auto first = hub.viewport_gizmo_state(101);
    bool ok = true;
    ok &= expect(first.target.actor_handle == 202, "target must round-trip per camera");
    ok &= expect(first.target.actor_name == "Cube", "actor name must round-trip");
    ok &= expect(hub.viewport_gizmo_state(102).target.actor_handle == 0,
                 "gizmo targets must be isolated by camera");

    hub.update_viewport_gizmo_interaction(101, Corona::ViewportGizmoAxis::Y, true);
    const auto dragging = hub.viewport_gizmo_state(101);
    ok &= expect(dragging.active_axis == Corona::ViewportGizmoAxis::Y && dragging.dragging,
                 "active axis and dragging state must update atomically");

    hub.clear_viewport_gizmo_target(101);
    const auto cleared = hub.viewport_gizmo_state(101);
    ok &= expect(cleared.target.actor_handle == 0 && !cleared.dragging,
                 "clearing a target must clear transient interaction state");
    return ok ? 0 : 1;
}
