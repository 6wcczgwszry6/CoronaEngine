#pragma once

// Phase 4 of the ImGui-removal plan: a thin raw-SDL window manager that takes over the
// job currently done by ImGui's imgui_impl_sdl3 platform layer. In Phase 4 it only wraps
// the single main window (created today in imgui_ui.cpp); create/destroy_secondary_window
// are stubs filled in Phase 7 (detach / re-dock).
//
// It is intentionally decoupled from ImGui: windows are identified by SDL_WindowID and the
// native surface handle (HWND on Windows / NSWindow* on macOS) used as the DisplaySystem
// surface key. Nothing references this manager yet in Phase 4 — it is wired into the frame
// loop in Phase 6.

#include <SDL3/SDL.h>

#include <cstdint>
#include <functional>
#include <unordered_map>
#include <vector>

namespace Corona::Systems::UI {

// A window owned/tracked by the manager. The main window is created elsewhere (Phase 4)
// and adopted; secondary windows are created by the manager itself (Phase 7).
struct ManagedWindow {
    SDL_Window* window = nullptr;
    SDL_WindowID window_id = 0;
    void* surface = nullptr;  // native handle (HWND/NSWindow*); DisplaySystem surface key
    bool is_main = false;
    // Phase 7: secondary windows are created HIDDEN and revealed only after their first
    // frame has been published to the DisplaySystem, to avoid a 1-frame white/black flash
    // on detach (mirrors the old ImGui deferred_platform_show_window trick).
    bool pending_show = false;
};

// Client-area pixel rectangle of a window (origin at client top-left = 0,0).
struct WindowClientRect {
    int width = 0;
    int height = 0;

    [[nodiscard]] explicit operator bool() const noexcept {
        return width > 0 && height > 0;
    }
};

// Extract the native window handle (HWND/NSWindow*) from an SDL window, mirroring the
// existing extraction in vulkan_backend.cpp. Returns nullptr on unsupported platforms or
// failure.
[[nodiscard]] void* native_surface_from_sdl_window(SDL_Window* window);

class SdlWindowManager {
   public:
    // Process-wide instance. The UI runs single-threaded on the main thread, so the window
    // set is shared (frame runner reads it; detach/redock commands mutate it) via this
    // singleton, mirroring BrowserManager / CameraViewportManager.
    static SdlWindowManager& instance();

    SdlWindowManager() = default;

    // Adopt the already-created main window (today: imgui_ui.cpp's SDL_CreateWindow). The
    // window's native surface is resolved and stored. Returns false if the handle is null
    // or the surface cannot be resolved.
    bool adopt_main_window(SDL_Window* window);

    // Lookups.
    [[nodiscard]] SDL_Window* main_window() const { return main_window_; }
    [[nodiscard]] void* main_surface() const;
    [[nodiscard]] SDL_Window* window_for_id(SDL_WindowID window_id) const;
    [[nodiscard]] const ManagedWindow* find_by_id(SDL_WindowID window_id) const;
    [[nodiscard]] const ManagedWindow* find_by_surface(void* surface) const;

    // Client-area pixel size of a window (SDL_GetWindowSizeInPixels with a logical-size
    // fallback), matching window_pixel_extent() in vulkan_backend.cpp.
    [[nodiscard]] WindowClientRect client_rect(SDL_Window* window) const;

    // Iterate all tracked windows (main + secondaries).
    void for_each_window(const std::function<void(const ManagedWindow&)>& fn) const;

    [[nodiscard]] std::size_t window_count() const { return windows_.size(); }

    // --- Secondary windows (detach). Stubs in Phase 4; implemented in Phase 7. ---
    // Returns the new window's surface handle, or nullptr if not yet implemented / failed.
    void* create_secondary_window(int x, int y, int width, int height);
    void destroy_secondary_window(void* surface);
    void destroy_all_secondary();

    // Deferred show: if `surface`'s window is still hidden awaiting its first frame, show it
    // now (called after that surface's first UIFrameReadyEvent is published, eliminating the
    // 1-frame white flash on detach). No-op if already shown or unknown surface.
    void reveal_pending_window(void* surface);

    // Phase 8: install the OS hit-test on a (borderless) secondary window so its Vue title-bar
    // drag regions move the window (SDL_HITTEST_DRAGGABLE) and its edges resize it (8-way
    // RESIZE_*), while the panel body stays interactive (SDL_HITTEST_NORMAL). tab_id lets the
    // callback look up that window's drag_regions. No-op for an unknown surface.
    void enable_drag_hit_test(void* surface, int tab_id);

   private:
    SDL_Window* main_window_ = nullptr;
    SDL_WindowID main_window_id_ = 0;
    std::unordered_map<SDL_WindowID, ManagedWindow> windows_;
};

}  // namespace Corona::Systems::UI
