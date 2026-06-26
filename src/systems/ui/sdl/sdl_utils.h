#pragma once

#include <SDL3/SDL.h>
#include <cef_browser.h>
#include <include/internal/cef_types.h>

#include <functional>
#include <string>
#include <vector>

namespace Corona::Systems::UI {

// ============================================================================
// 键盘工具函数
// ============================================================================

namespace KeyUtils {

int convert_sdl_key_code_to_windows(int sdl_key);
bool is_modifier_key(int key);
bool should_send_char_event(int key, int modifiers);

}  // namespace KeyUtils

// ============================================================================
// 鼠标状态管理器
// ============================================================================

namespace MouseUtils {

CefBrowserHost::MouseButtonType convert_mouse_button(Uint8 sdl_button);

// ----------------------------------------------------------------------------
// ImGui-free CEF mouse forwarding (Phase 6 of the ImGui-removal plan).
//
// The SDL input router tracks pointer/modifier state directly from SDL events and
// forwards to CEF through these explicit-state functions. Coordinates are plain
// floats (mouse_* is global, item_* is the panel's top-left); modifier/button state
// is passed in rather than read from an ImGui context.
// ----------------------------------------------------------------------------
[[nodiscard]] uint32_t make_modifiers(bool left_down, bool right_down,
                                      bool shift, bool ctrl, bool alt);
[[nodiscard]] CefMouseEvent create_mouse_event_ex(float mouse_x, float mouse_y,
                                                  float item_x, float item_y,
                                                  uint32_t modifiers);
void send_mouse_click_ex(CefRefPtr<CefBrowser> browser, float mouse_x, float mouse_y,
                         float item_x, float item_y,
                         CefBrowserHost::MouseButtonType button, bool mouse_up,
                         int click_count, bool shift, bool ctrl, bool alt);
void send_mouse_move_ex(CefRefPtr<CefBrowser> browser, float mouse_x, float mouse_y,
                        float item_x, float item_y, bool left_down, bool right_down,
                        bool shift, bool ctrl, bool alt, bool mouse_leave = false);
void send_mouse_wheel_ex(CefRefPtr<CefBrowser> browser, float mouse_x, float mouse_y,
                         float item_x, float item_y, float wheel_delta,
                         bool left_down, bool right_down, bool shift, bool ctrl, bool alt);

}  // namespace MouseUtils

// ============================================================================
// SDL 事件处理器
// ============================================================================

struct EventProcessResult {
    bool should_quit = false;
    bool window_resized = false;
    int url_input_active_tab = -1;
    // Phase 7d: SDL_WindowIDs of SECONDARY windows the user closed (clicked the OS X button)
    // this pump. The main window's close request still sets should_quit; secondary closes are
    // reported here so the frame runner can redock the hosted tab (promise-synced teardown).
    std::vector<SDL_WindowID> closed_window_ids;
};

class SDLEventHandler {
   public:
    SDLEventHandler() = default;

    using KeyEventCallback = std::function<void(const SDL_Event&)>;

    // Phase 6: on_mouse_event receives every mouse/wheel SDL_Event so the SDL input router
    // can track pointer state (replacing ImGui_ImplSDL3_ProcessEvent). Keyboard/text/IME
    // events still go to their respective callbacks.
    EventProcessResult process_events(SDL_Window* window,
                                      int current_url_input_active_tab,
                                      KeyEventCallback on_key_event = nullptr,
                                      KeyEventCallback on_text_event = nullptr,
                                      KeyEventCallback on_ime_event = nullptr,
                                      KeyEventCallback on_mouse_event = nullptr);

   private:
    bool is_input_method_switch(const SDL_Event& event);
};

}  // namespace Corona::Systems::UI
