#include <corona/systems/ui/sdl_window_manager.h>

#include <corona/kernel/core/i_logger.h>

#include <algorithm>

namespace Corona::Systems::UI {

void* native_surface_from_sdl_window(SDL_Window* window) {
    if (window == nullptr) {
        return nullptr;
    }
    void* native_handle = nullptr;
#if defined(_WIN32)
    native_handle = SDL_GetPointerProperty(
        SDL_GetWindowProperties(window),
        SDL_PROP_WINDOW_WIN32_HWND_POINTER,
        nullptr);
#elif defined(__APPLE__)
    native_handle = SDL_GetPointerProperty(
        SDL_GetWindowProperties(window),
        SDL_PROP_WINDOW_COCOA_WINDOW_POINTER,
        nullptr);
#endif
    return native_handle;
}

bool SdlWindowManager::adopt_main_window(SDL_Window* window) {
    if (window == nullptr) {
        CFW_LOG_ERROR("SdlWindowManager: adopt_main_window called with null window");
        return false;
    }

    void* surface = native_surface_from_sdl_window(window);
    if (surface == nullptr) {
        CFW_LOG_ERROR("SdlWindowManager: failed to resolve native surface for main window");
        return false;
    }

    main_window_ = window;
    main_window_id_ = SDL_GetWindowID(window);

    ManagedWindow managed;
    managed.window = window;
    managed.window_id = main_window_id_;
    managed.surface = surface;
    managed.is_main = true;
    windows_[main_window_id_] = managed;

    CFW_LOG_INFO("SdlWindowManager: adopted main window (id={})", main_window_id_);
    return true;
}

void* SdlWindowManager::main_surface() const {
    const auto it = windows_.find(main_window_id_);
    return it != windows_.end() ? it->second.surface : nullptr;
}

SDL_Window* SdlWindowManager::window_for_id(SDL_WindowID window_id) const {
    const auto it = windows_.find(window_id);
    return it != windows_.end() ? it->second.window : nullptr;
}

const ManagedWindow* SdlWindowManager::find_by_id(SDL_WindowID window_id) const {
    const auto it = windows_.find(window_id);
    return it != windows_.end() ? &it->second : nullptr;
}

WindowClientRect SdlWindowManager::client_rect(SDL_Window* window) const {
    if (window == nullptr) {
        return {};
    }

    int width = 0;
    int height = 0;
    if (SDL_GetWindowSizeInPixels(window, &width, &height) && width > 0 && height > 0) {
        return {width, height};
    }

    width = 0;
    height = 0;
    if (SDL_GetWindowSize(window, &width, &height) && width > 0 && height > 0) {
        return {width, height};
    }

    return {};
}

void SdlWindowManager::for_each_window(const std::function<void(const ManagedWindow&)>& fn) const {
    if (!fn) {
        return;
    }
    for (const auto& [id, managed] : windows_) {
        fn(managed);
    }
}

// --- Secondary windows: stubs in Phase 4, implemented in Phase 7 (detach / re-dock). ---

void* SdlWindowManager::create_secondary_window(int /*x*/, int /*y*/, int /*width*/, int /*height*/) {
    CFW_LOG_WARNING("SdlWindowManager: create_secondary_window not implemented until Phase 7");
    return nullptr;
}

void SdlWindowManager::destroy_secondary_window(void* /*surface*/) {
    // No-op until Phase 7.
}

void SdlWindowManager::destroy_all_secondary() {
    // No-op until Phase 7: only the main window is tracked, and it is owned elsewhere.
}

}  // namespace Corona::Systems::UI
