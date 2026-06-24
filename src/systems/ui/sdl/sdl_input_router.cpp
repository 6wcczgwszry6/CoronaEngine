#include <corona/systems/ui/sdl_input_router.h>

#include <cmath>

namespace Corona::Systems::UI {

namespace {

[[nodiscard]] bool rect_contains(const LayoutRect& r, float px, float py) {
    return px >= r.x && py >= r.y && px < r.x + r.w && py < r.y + r.h;
}

}  // namespace

bool SdlInputRouter::process_event(const SDL_Event& event) {
    switch (event.type) {
        case SDL_EVENT_MOUSE_MOTION: {
            state_.mouse_x = event.motion.x;
            state_.mouse_y = event.motion.y;
            return true;
        }
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
        case SDL_EVENT_MOUSE_BUTTON_UP: {
            const bool down = (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN);
            state_.mouse_x = event.button.x;
            state_.mouse_y = event.button.y;
            switch (event.button.button) {
                case SDL_BUTTON_LEFT:
                    state_.left_down = down;
                    if (down) {
                        // Double/triple-click detection, mirroring
                        // MouseUtils::MouseStateManager::handle_mouse_click.
                        const Uint32 now = SDL_GetTicks();
                        const float dx = state_.mouse_x - last_click_x_;
                        const float dy = state_.mouse_y - last_click_y_;
                        const float dist = std::sqrt(dx * dx + dy * dy);
                        if ((now - last_click_time_) < kDoubleClickTime &&
                            dist < kDoubleClickDist) {
                            ++click_count_;
                        } else {
                            click_count_ = 1;
                        }
                        if (click_count_ > 3) {
                            click_count_ = 1;
                        }
                        last_click_time_ = now;
                        last_click_x_ = state_.mouse_x;
                        last_click_y_ = state_.mouse_y;
                    }
                    break;
                case SDL_BUTTON_RIGHT:
                    state_.right_down = down;
                    break;
                case SDL_BUTTON_MIDDLE:
                    state_.middle_down = down;
                    break;
                default:
                    break;
            }
            return true;
        }
        case SDL_EVENT_MOUSE_WHEEL: {
            state_.wheel += event.wheel.y;
            return true;
        }
        default:
            return false;
    }
}

void SdlInputRouter::refresh_modifiers() {
    const SDL_Keymod mod = SDL_GetModState();
    state_.shift = (mod & SDL_KMOD_SHIFT) != 0;
    state_.ctrl = (mod & SDL_KMOD_CTRL) != 0;
    state_.alt = (mod & SDL_KMOD_ALT) != 0;
    state_.gui = (mod & SDL_KMOD_GUI) != 0;
}

float SdlInputRouter::consume_wheel() {
    const float w = state_.wheel;
    state_.wheel = 0.0f;
    return w;
}

HitResult SdlInputRouter::hit_test(const std::vector<HitTarget>& targets) const {
    HitResult result;

    // Topmost-first: the last target containing the point wins.
    for (auto it = targets.rbegin(); it != targets.rend(); ++it) {
        const HitTarget& target = *it;
        if (!rect_contains(target.rect, state_.mouse_x, state_.mouse_y)) {
            continue;
        }

        result.hit = true;
        result.tab_id = target.tab_id;
        result.is_main = target.is_main;
        result.local_x = state_.mouse_x - target.rect.x;
        result.local_y = state_.mouse_y - target.rect.y;

        // Drag-bar test in panel-local coords. Empty list ⇒ default top-30px handle,
        // matching browser_ui.cpp's behavior for panels that set no drag regions.
        if (target.drag_regions.empty()) {
            result.in_drag_region = (result.local_y >= 0.0f && result.local_y < 30.0f &&
                                     result.local_x >= 0.0f && result.local_x < target.rect.w);
        } else {
            for (const LayoutRect& region : target.drag_regions) {
                if (rect_contains(region, result.local_x, result.local_y)) {
                    result.in_drag_region = true;
                    break;
                }
            }
        }
        break;
    }

    return result;
}

}  // namespace Corona::Systems::UI
