#pragma once

#include <SDL3/SDL.h>
#include <include/cef_browser.h>
#include <include/internal/cef_types.h>

#include <memory>
#include <string>
#include <vector>

namespace Corona::Systems::UI {

struct BrowserTab;

// ============================================================================
// 待处理的键盘事件
// ============================================================================

struct PendingKeyEvent {
    enum EventType { kKeyEvent,
                     kTextEvent,
                     kImeComposition };

    EventType type;
    int key_code = 0;
    int scan_code = 0;
    int modifiers = 0;
    bool pressed = false;
    std::string text;
    int ime_start = 0;
    int ime_length = 0;
    bool is_modifier_combo = false;

    explicit PendingKeyEvent(EventType t) : type(t) {}
};

// ============================================================================
// 浏览器输入处理器
// ============================================================================

class BrowserInputHandler {
   public:
    BrowserInputHandler() = default;

    void clear_pending_events();
    void process_sdl_key_event(const SDL_Event& event);
    void process_sdl_text_event(const SDL_Event& event);
    void process_sdl_ime_event(const SDL_Event& event);
    void send_key_events_to_browser(const CefRefPtr<CefBrowser>& browser);

   private:
    std::vector<PendingKeyEvent> pending_key_events_;
};

// Give keyboard/mouse focus to the tab with `focused_tab_id` and clear it on all others.
// Phase 6: promoted from a file-local helper to public API so the ImGui-free frame runner
// can call it on click (previously only used inside BrowserRenderer).
void focus_browser_tab_exclusively(int focused_tab_id);

}  // namespace Corona::Systems::UI
