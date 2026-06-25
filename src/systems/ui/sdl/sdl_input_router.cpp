#include <corona/systems/ui/sdl_input_router.h>

#include <cmath>

namespace Corona::Systems::UI {

namespace {

[[nodiscard]] bool rect_contains(const LayoutRect& r, float px, float py) {
    return px >= r.x && py >= r.y && px < r.x + r.w && py < r.y + r.h;
}

[[nodiscard]] SDL_WindowID window_id_of(const SDL_Event& event) {
    switch (event.type) {
        case SDL_EVENT_MOUSE_MOTION:
            return event.motion.windowID;
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
        case SDL_EVENT_MOUSE_BUTTON_UP:
            return event.button.windowID;
        case SDL_EVENT_MOUSE_WHEEL:
            return event.wheel.windowID;
        default:
            return 0;
    }
}

}  // namespace

SdlInputRouter::PerWindowInput& SdlInputRouter::bucket(SDL_WindowID window_id) {
    return windows_[window_id];
}

bool SdlInputRouter::process_event(const SDL_Event& event) {
    const SDL_WindowID window_id = window_id_of(event);
    switch (event.type) {
        case SDL_EVENT_MOUSE_MOTION: {
            PerWindowInput& w = bucket(window_id);
            w.mouse_x = event.motion.x;
            w.mouse_y = event.motion.y;
            return true;
        }
        case SDL_EVENT_MOUSE_BUTTON_DOWN:
        case SDL_EVENT_MOUSE_BUTTON_UP: {
            const bool down = (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN);
            PerWindowInput& w = bucket(window_id);
            w.mouse_x = event.button.x;
            w.mouse_y = event.button.y;

            MouseButton button = MouseButton::Left;
            bool known_button = true;
            switch (event.button.button) {
                case SDL_BUTTON_LEFT:
                    button = MouseButton::Left;
                    w.left_down = down;
                    if (down) {
                        // Double/triple-click detection, mirroring the old MouseStateManager.
                        const Uint32 now = SDL_GetTicks();
                        const float dx = w.mouse_x - w.last_click_x;
                        const float dy = w.mouse_y - w.last_click_y;
                        const float dist = std::sqrt(dx * dx + dy * dy);
                        if ((now - w.last_click_time) < kDoubleClickTime &&
                            dist < kDoubleClickDist) {
                            ++w.click_count;
                        } else {
                            w.click_count = 1;
                        }
                        if (w.click_count > 3) {
                            w.click_count = 1;
                        }
                        w.last_click_time = now;
                        w.last_click_x = w.mouse_x;
                        w.last_click_y = w.mouse_y;
                    }
                    break;
                case SDL_BUTTON_RIGHT:
                    button = MouseButton::Right;
                    w.right_down = down;
                    break;
                case SDL_BUTTON_MIDDLE:
                    button = MouseButton::Middle;
                    w.middle_down = down;
                    break;
                default:
                    known_button = false;
                    break;
            }

            if (known_button) {
                ButtonEvent be;
                be.button = button;
                be.pressed = down;
                be.mouse_x = w.mouse_x;
                be.mouse_y = w.mouse_y;
                // click_count is meaningful for left-button presses; 1 otherwise.
                be.click_count = (down && button == MouseButton::Left) ? w.click_count : 1;
                w.button_events.push_back(be);
            }
            return true;
        }
        case SDL_EVENT_MOUSE_WHEEL: {
            bucket(window_id).wheel += event.wheel.y;
            return true;
        }
        default:
            return false;
    }
}

void SdlInputRouter::refresh_modifiers() {
    const SDL_Keymod mod = SDL_GetModState();
    shift_ = (mod & SDL_KMOD_SHIFT) != 0;
    ctrl_ = (mod & SDL_KMOD_CTRL) != 0;
    alt_ = (mod & SDL_KMOD_ALT) != 0;
    gui_ = (mod & SDL_KMOD_GUI) != 0;
}

InputState SdlInputRouter::state(SDL_WindowID window_id) const {
    InputState s;
    s.shift = shift_;
    s.ctrl = ctrl_;
    s.alt = alt_;
    s.gui = gui_;
    const auto it = windows_.find(window_id);
    if (it != windows_.end()) {
        const PerWindowInput& w = it->second;
        s.mouse_x = w.mouse_x;
        s.mouse_y = w.mouse_y;
        s.left_down = w.left_down;
        s.right_down = w.right_down;
        s.middle_down = w.middle_down;
        s.wheel = w.wheel;
    }
    return s;
}

float SdlInputRouter::consume_wheel(SDL_WindowID window_id) {
    const auto it = windows_.find(window_id);
    if (it == windows_.end()) {
        return 0.0f;
    }
    const float wheel = it->second.wheel;
    it->second.wheel = 0.0f;
    return wheel;
}

std::vector<ButtonEvent> SdlInputRouter::drain_button_events(SDL_WindowID window_id) {
    const auto it = windows_.find(window_id);
    if (it == windows_.end()) {
        return {};
    }
    std::vector<ButtonEvent> events;
    events.swap(it->second.button_events);
    return events;
}

HitResult SdlInputRouter::hit_test(SDL_WindowID window_id,
                                   const std::vector<HitTarget>& targets) const {
    HitResult result;

    const auto it = windows_.find(window_id);
    if (it == windows_.end()) {
        return result;
    }
    const float mouse_x = it->second.mouse_x;
    const float mouse_y = it->second.mouse_y;

    // Topmost-first: the last target containing the point wins.
    for (auto t = targets.rbegin(); t != targets.rend(); ++t) {
        const HitTarget& target = *t;
        if (!rect_contains(target.rect, mouse_x, mouse_y)) {
            continue;
        }

        result.hit = true;
        result.tab_id = target.tab_id;
        result.is_main = target.is_main;
        result.local_x = mouse_x - target.rect.x;
        result.local_y = mouse_y - target.rect.y;

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
