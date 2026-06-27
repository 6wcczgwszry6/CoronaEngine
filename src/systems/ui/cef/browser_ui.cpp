#include "browser_ui.h"

#include <corona/systems/ui/camera_viewport_manager.h>

#include <SDL3/SDL.h>
#include <nlohmann/json.hpp>

#include <algorithm>
#include <cstdlib>
#include <cstdint>

#ifdef _WIN32
#include <windows.h>
#endif

#include "browser_manager.h"
#include "cef_client.h"
#include "sdl/sdl_utils.h"

namespace Corona::Systems::UI {

namespace {
float clamp_float(float value, float min_value, float max_value) {
    if (max_value < min_value) {
        return min_value;
    }
    return std::clamp(value, min_value, max_value);
}

#ifdef _WIN32
bool is_extended_windows_key(int windows_key_code) {
    switch (windows_key_code) {
        case VK_LEFT:
        case VK_UP:
        case VK_RIGHT:
        case VK_DOWN:
        case VK_PRIOR:
        case VK_NEXT:
        case VK_END:
        case VK_HOME:
        case VK_INSERT:
        case VK_DELETE:
        case VK_DIVIDE:
        case VK_RCONTROL:
        case VK_RMENU:
            return true;
        default:
            return false;
    }
}

int make_windows_native_key_code(int windows_key_code, bool pressed) {
    const UINT scan_code = MapVirtualKeyW(
        static_cast<UINT>(windows_key_code), MAPVK_VK_TO_VSC);
    int native_key_code = 1 | (static_cast<int>(scan_code) << 16);
    if (is_extended_windows_key(windows_key_code)) {
        native_key_code |= 1 << 24;
    }
    if (!pressed) {
        native_key_code |= static_cast<int>(0xC0000000u);
    }
    return native_key_code;
}
#endif
}  // namespace

// ============================================================================
// BrowserInputHandler 实现
// ============================================================================

void BrowserInputHandler::clear_pending_events() {
    pending_key_events_.clear();
}

void BrowserInputHandler::process_sdl_key_event(const SDL_Event& event) {
    bool pressed = (event.type == SDL_EVENT_KEY_DOWN);
    int key_code = static_cast<int>(event.key.key);
    int scan_code = static_cast<int>(event.key.scancode);
    int modifiers = 0;

    Uint32 sdl_mod = event.key.mod;
    if (sdl_mod & SDL_KMOD_CTRL) modifiers |= EVENTFLAG_CONTROL_DOWN;
    if (sdl_mod & SDL_KMOD_SHIFT) modifiers |= EVENTFLAG_SHIFT_DOWN;
    if (sdl_mod & SDL_KMOD_ALT) modifiers |= EVENTFLAG_ALT_DOWN;
    if (sdl_mod & SDL_KMOD_GUI) modifiers |= EVENTFLAG_COMMAND_DOWN;
    if (sdl_mod & SDL_KMOD_CAPS) modifiers |= EVENTFLAG_CAPS_LOCK_ON;
    if (sdl_mod & SDL_KMOD_NUM) modifiers |= EVENTFLAG_NUM_LOCK_ON;

    bool is_common_edit_shortcut = false;
    if (modifiers & EVENTFLAG_CONTROL_DOWN) {
        switch (key_code) {
            case SDLK_A:
            case SDLK_C:
            case SDLK_V:
            case SDLK_Z:
            case SDLK_Y:
                is_common_edit_shortcut = true;
                break;
            default:
                break;
        }
    }

    bool is_modifier_combo = (modifiers & (EVENTFLAG_CONTROL_DOWN | EVENTFLAG_ALT_DOWN)) &&
                             ((key_code >= 'a' && key_code <= 'z') ||
                              (key_code >= 'A' && key_code <= 'Z') ||
                              (key_code >= '0' && key_code <= '9'));

    PendingKeyEvent key_event(PendingKeyEvent::kKeyEvent);
    key_event.key_code = key_code;
    key_event.scan_code = scan_code;
    key_event.modifiers = modifiers;
    key_event.pressed = pressed;
    key_event.is_modifier_combo = is_modifier_combo || is_common_edit_shortcut;

    pending_key_events_.push_back(key_event);
}

void BrowserInputHandler::process_sdl_text_event(const SDL_Event& event) {
    if (event.text.text && event.text.text[0]) {
        PendingKeyEvent text_event(PendingKeyEvent::kTextEvent);
        text_event.text = event.text.text;
        pending_key_events_.push_back(text_event);
    }
}

void BrowserInputHandler::process_sdl_ime_event(const SDL_Event& event) {
    if (event.edit.text && event.edit.text[0]) {
        PendingKeyEvent ime_event(PendingKeyEvent::kImeComposition);
        ime_event.text = event.edit.text;
        ime_event.ime_start = event.edit.start;
        ime_event.ime_length = event.edit.length;
        pending_key_events_.push_back(ime_event);
    }
}

void BrowserInputHandler::send_key_events_to_browser(const CefRefPtr<CefBrowser>& browser) {
    if (!browser) return;

    for (const auto& pending_event : pending_key_events_) {
        if (pending_event.type == PendingKeyEvent::kKeyEvent) {
            CefKeyEvent cef_key_event;
            cef_key_event.type = pending_event.pressed ? KEYEVENT_RAWKEYDOWN : KEYEVENT_KEYUP;
            cef_key_event.windows_key_code = KeyUtils::convert_sdl_key_code_to_windows(pending_event.key_code);
#ifdef _WIN32
            cef_key_event.native_key_code = make_windows_native_key_code(
                cef_key_event.windows_key_code, pending_event.pressed);
#else
            cef_key_event.native_key_code = pending_event.scan_code;
            cef_key_event.character = pending_event.key_code;
            cef_key_event.unmodified_character = pending_event.key_code;
#endif
            cef_key_event.modifiers = pending_event.modifiers;
            cef_key_event.is_system_key =
                (pending_event.modifiers & EVENTFLAG_ALT_DOWN) != 0;

            bool is_common_edit_shortcut = false;
            if (pending_event.modifiers & EVENTFLAG_CONTROL_DOWN) {
                switch (pending_event.key_code) {
                    case SDLK_A:
                    case SDLK_C:
                    case SDLK_V:
                    case SDLK_Z:
                    case SDLK_Y:
                        is_common_edit_shortcut = true;
                        break;
                    default:
                        break;
                }
            }

            browser->GetHost()->SendKeyEvent(cef_key_event);

            if (pending_event.pressed &&
                (pending_event.key_code == SDLK_RETURN || pending_event.key_code == SDLK_KP_ENTER)) {
                CefKeyEvent char_event = cef_key_event;
                char_event.type = KEYEVENT_CHAR;
                char_event.character = 0x0D;
                char_event.unmodified_character = 0x0D;
                browser->GetHost()->SendKeyEvent(char_event);
            }

            if (pending_event.pressed && pending_event.is_modifier_combo) {
                if (is_common_edit_shortcut) {
                    cef_key_event.type = KEYEVENT_CHAR;
                    browser->GetHost()->SendKeyEvent(cef_key_event);
                } else {
                    switch (pending_event.key_code) {
                        case SDLK_RETURN:
                        case SDLK_KP_ENTER:
                        case SDLK_TAB:
                        case SDLK_BACKSPACE:
                        case SDLK_DELETE:
                        case SDLK_ESCAPE:
                            cef_key_event.type = KEYEVENT_CHAR;
                            browser->GetHost()->SendKeyEvent(cef_key_event);
                            break;
                        default:
                            break;
                    }
                }
            }
        } else if (pending_event.type == PendingKeyEvent::kTextEvent) {
            const std::string& text = pending_event.text;
            if (!text.empty()) {
                bool has_control_chars = false;
                for (char c : text) {
                    if (c == '\b' || c == '\t' || c == '\n' || c == '\r') {
                        has_control_chars = true;
                        break;
                    }
                }

                if (!has_control_chars) {
                    bool is_ascii = true;
                    for (char c : text) {
                        if (static_cast<unsigned char>(c) >= 128) {
                            is_ascii = false;
                            break;
                        }
                    }

                    if (is_ascii) {
                        for (char c : text) {
                            if (c >= 32 && c < 127) {
                                CefKeyEvent cef_text_event;
                                cef_text_event.type = KEYEVENT_CHAR;
                                cef_text_event.modifiers = 0;
                                cef_text_event.windows_key_code = static_cast<uint16_t>(c);
                                cef_text_event.native_key_code = static_cast<uint16_t>(c);
                                cef_text_event.character = static_cast<uint16_t>(c);
                                cef_text_event.unmodified_character = static_cast<uint16_t>(c);
                                browser->GetHost()->SendKeyEvent(cef_text_event);
                            }
                        }
                    } else {
                        if (char* utf16_text = SDL_iconv_string("UTF-16LE", "UTF-8", text.c_str(), text.length() + 1)) {
                            auto* utf16_chars = reinterpret_cast<uint16_t*>(utf16_text);
                            size_t utf16_len = 0;
                            while (utf16_chars[utf16_len] != 0) {
                                utf16_len++;
                            }
                            for (size_t i = 0; i < utf16_len; i++) {
                                CefKeyEvent cef_text_event;
                                cef_text_event.type = KEYEVENT_CHAR;
                                cef_text_event.modifiers = 0;
                                cef_text_event.windows_key_code = utf16_chars[i];
                                cef_text_event.native_key_code = utf16_chars[i];
                                cef_text_event.character = utf16_chars[i];
                                cef_text_event.unmodified_character = utf16_chars[i];
                                browser->GetHost()->SendKeyEvent(cef_text_event);
                            }
                            SDL_free(utf16_text);
                        }
                    }
                }
            }
        }
    }

    clear_pending_events();
}

// ============================================================================
// focus_browser_tab_exclusively: give CEF focus to one tab, clear it on the rest.
// (Phase 6: de-anonymized from the former BrowserRenderer translation unit so the
//  ImGui-free UiFrameRunner can call it. The ImGui-based BrowserRenderer is gone.)
// ============================================================================
void focus_browser_tab_exclusively(int focused_tab_id) {
    for (const auto& [tab_id, tab] : BrowserManager::instance().get_tabs()) {
        if (!tab || !tab->client) {
            continue;
        }
        auto browser = tab->client->GetBrowser();
        if (!browser) {
            continue;
        }
        browser->GetHost()->SetFocus(tab_id == focused_tab_id);
    }
}

}  // namespace Corona::Systems::UI
