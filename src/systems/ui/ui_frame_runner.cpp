#include <corona/systems/ui/ui_frame_runner.h>

#include <corona/kernel/core/i_logger.h>
#include <corona/systems/ui/camera_viewport_manager.h>
#include <corona/systems/ui/quad_compositor.h>
#include <corona/systems/ui/vulkan_backend.h>

#include <algorithm>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include "cef/browser_manager.h"
#include "cef/cef_client.h"

#ifdef _WIN32
#include <windows.h>
#endif

namespace Corona::Systems::UI {

// ============================================================================
// SDL/UI lifecycle (replaces initialize_sdl_imgui / shutdown_sdl_imgui — no ImGui).
// ============================================================================

bool initialize_sdl_ui(SDL_Window*& window, std::unique_ptr<VulkanBackend>& vulkan_backend) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        CFW_LOG_ERROR("Failed to initialize SDL: {}", SDL_GetError());
        return false;
    }

    SDL_SetHint(SDL_HINT_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR, "0");

    int initial_width = 1920;
    int initial_height = 1080;
    int initial_x = SDL_WINDOWPOS_CENTERED;
    int initial_y = SDL_WINDOWPOS_CENTERED;
    SDL_DisplayID primary_display = SDL_GetPrimaryDisplay();
    const SDL_DisplayMode* desktop_mode = nullptr;
    if (primary_display != 0) {
        desktop_mode = SDL_GetDesktopDisplayMode(primary_display);
    }

    if (desktop_mode) {
        float display_scale = SDL_GetDisplayContentScale(primary_display);
        if (display_scale <= 0.0f) {
            display_scale = 1.0f;
        }

        float desktop_width = static_cast<float>(desktop_mode->w) / display_scale;
        float desktop_height = static_cast<float>(desktop_mode->h) / display_scale;

        SDL_Rect usable_bounds{};
        if (SDL_GetDisplayUsableBounds(primary_display, &usable_bounds) &&
            usable_bounds.w > 0 && usable_bounds.h > 0) {
            desktop_width = std::min(desktop_width, static_cast<float>(usable_bounds.w));
            desktop_height = std::min(desktop_height, static_cast<float>(usable_bounds.h));
        }

        initial_width = static_cast<int>(desktop_width * 0.8f);
        initial_height = static_cast<int>(desktop_height * 0.8f);
        initial_x = static_cast<int>((desktop_width - static_cast<float>(initial_width)) * 0.5f);
        initial_y = static_cast<int>((desktop_height - static_cast<float>(initial_height)) * 0.5f);
    }

    window = SDL_CreateWindow("Corona Engine (Horizon)", initial_width, initial_height,
                              SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIDDEN);
    if (window == nullptr) {
        CFW_LOG_ERROR("Failed to create window: {}", SDL_GetError());
        SDL_Quit();
        return false;
    }

    SDL_SetWindowPosition(window, initial_x, initial_y);
    SDL_StartTextInput(window);
    SDL_SetHint(SDL_HINT_IME_IMPLEMENTED_UI, "1");
    BrowserManager::instance().set_main_window(window);

    vulkan_backend = std::make_unique<VulkanBackend>(window);
    if (!vulkan_backend->initialize()) {
        CFW_LOG_ERROR("Failed to initialize Corona UI backend");
        SDL_DestroyWindow(window);
        window = nullptr;
        SDL_Quit();
        return false;
    }

    return true;
}

void shutdown_sdl_ui(SDL_Window*& window, std::unique_ptr<VulkanBackend>& vulkan_backend) {
    if (vulkan_backend) {
        vulkan_backend->shutdown();
        vulkan_backend.reset();
    }

    if (window) {
        SDL_StopTextInput(window);
        SDL_DestroyWindow(window);
        window = nullptr;
    }

    SDL_Quit();
}

// ============================================================================
// UiFrameRunner
// ============================================================================

namespace {

// Build the layout inputs from the current browser tabs (main + docked panels).
std::vector<PanelLayoutInput> collect_layout_inputs() {
    std::vector<PanelLayoutInput> inputs;
    for (const auto& [tab_id, tab] : BrowserManager::instance().get_tabs()) {
        if (!tab || !tab->open || tab->minimized) {
            continue;
        }
        PanelLayoutInput in;
        in.tab_id = tab_id;
        in.docking_pos = tab->docking_pos;
        in.dock_width = tab->dock_width;
        in.dock_height = tab->dock_height;
        in.camera_view = tab->camera_view;
        in.initial_x = tab->initial_x;
        in.initial_y = tab->initial_y;
        inputs.push_back(std::move(in));
    }
    return inputs;
}

}  // namespace

void UiFrameRunner::dispatch_keyboard_to_active_tab(int active_tab_id) {
    if (active_tab_id != -1 && url_input_active_tab_ == -1) {
        auto* tab = BrowserManager::instance().get_tab(active_tab_id);
        if (tab && tab->client && tab->client->GetBrowser()) {
            tab->client->GetBrowser()->GetHost()->SetFocus(true);
            input_handler_.send_key_events_to_browser(tab->client->GetBrowser());
            return;
        }
    }
    input_handler_.clear_pending_events();
}

void UiFrameRunner::route_mouse_to_panels(const std::vector<PanelPlacement>& placements,
                                          int& active_tab_id) {
    // Build hit targets with an explicit z-order: the main panel is always bottom-most and
    // docked panels sit on top. hit_test() scans last-first (topmost wins), so we must push
    // the main panel FIRST regardless of the unordered_map iteration order of get_tabs() —
    // otherwise a click on a docked panel can fall through to the full-screen main panel.
    std::vector<HitTarget> targets;
    targets.reserve(placements.size());
    auto append_target = [&](const PanelPlacement& placement) {
        HitTarget target;
        target.tab_id = placement.tab_id;
        target.rect = placement.rect;
        target.is_main = placement.is_main;
        targets.push_back(target);
    };
    for (const PanelPlacement& placement : placements) {
        if (placement.is_main) {
            append_target(placement);
        }
    }
    for (const PanelPlacement& placement : placements) {
        if (!placement.is_main) {
            append_target(placement);
        }
    }

    const HitResult hit = input_router_.hit_test(targets);
    const InputState& st = input_router_.state();

    // Drain button transitions regardless of hit, so a release outside the panel still
    // closes a click that began inside it (mirrors the old was_down/is_active handling).
    std::vector<ButtonEvent> button_events = input_router_.drain_button_events();
    const float wheel = input_router_.consume_wheel();

    // Determine which tab (if any) receives mouse events.
    auto* tab = (hit.hit && hit.tab_id != -1) ? BrowserManager::instance().get_tab(hit.tab_id) : nullptr;
    auto browser = (tab && tab->client) ? tab->client->GetBrowser() : nullptr;
    if (!browser) {
        return;
    }

    // Panel origin = global mouse - panel-local mouse (from hit_test).
    const float item_x = st.mouse_x - hit.local_x;
    const float item_y = st.mouse_y - hit.local_y;

    // On any click into this panel, make it the active tab and focus it exclusively.
    auto to_cef_button = [](MouseButton b) {
        switch (b) {
            case MouseButton::Right: return MBT_RIGHT;
            case MouseButton::Middle: return MBT_MIDDLE;
            case MouseButton::Left:
            default: return MBT_LEFT;
        }
    };

    for (const ButtonEvent& be : button_events) {
        if (be.pressed) {
            active_tab_id = hit.tab_id;
            url_input_active_tab_ = -1;
            focus_browser_tab_exclusively(hit.tab_id);
        }
        MouseUtils::send_mouse_click_ex(browser, be.mouse_x, be.mouse_y, item_x, item_y,
                                        to_cef_button(be.button), /*mouse_up=*/!be.pressed,
                                        be.click_count, st.shift, st.ctrl, st.alt);
    }

    // Mouse move (always treated as hovering the hit panel here).
    MouseUtils::send_mouse_move_ex(browser, st.mouse_x, st.mouse_y, item_x, item_y,
                                   st.left_down, st.right_down, st.shift, st.ctrl, st.alt,
                                   /*mouse_leave=*/false);

    // Wheel.
    if (wheel != 0.0f) {
        MouseUtils::send_mouse_wheel_ex(browser, st.mouse_x, st.mouse_y, item_x, item_y, wheel,
                                        st.left_down, st.right_down, st.shift, st.ctrl, st.alt);
    }
}

void UiFrameRunner::run_frame(UiFrameContext& context) {
    if (!context.running || !context.active_tab_id || !context.vulkan_backend) {
        return;
    }

    // 1) Pump SDL events.
    input_router_.refresh_modifiers();
    auto result = event_handler_.process_events(
        context.window, url_input_active_tab_,
        [&](const SDL_Event& event) { input_handler_.process_sdl_key_event(event); },
        [&](const SDL_Event& event) { input_handler_.process_sdl_text_event(event); },
        [&](const SDL_Event& event) { input_handler_.process_sdl_ime_event(event); },
        [&](const SDL_Event& event) { input_router_.process_event(event); });

    if (result.should_quit) {
        *context.running = false;
    }

    if (result.window_resized && context.window && context.window_size_changed) {
        *context.window_size_changed = true;
        context.vulkan_backend->request_rebuild();
    }

    // 2) Forward queued keyboard/text/IME to the active tab.
    dispatch_keyboard_to_active_tab(*context.active_tab_id);

    // 3) Rebuild render target on resize.
    if (context.vulkan_backend->is_rebuild_needed()) {
        int width = 0;
        int height = 0;
        SDL_GetWindowSize(context.window, &width, &height);
        context.vulkan_backend->rebuild(width, height);
    }

    context.vulkan_backend->new_frame();

    // 4) Drive browser texture updates + close handling.
    BrowserManager::instance().update();
    std::vector<int> tabs_to_close;
    for (auto& [tab_id, tab] : BrowserManager::instance().get_tabs()) {
        if (!tab || !tab->open) {
            tabs_to_close.push_back(tab_id);
            continue;
        }
        if (tab->minimized) {
            continue;
        }
        BrowserManager::instance().update_texture(tab_id);
    }

    // 5) Compute fixed-rect layout in LOGICAL coordinates.
    //
    // Coordinate contract (matches the former ImGui path):
    //   - Layout, hit-testing, CEF buffer sizes, and CEF-local mouse coords are all LOGICAL
    //     (SDL window coordinates). CEF/Vue work in CSS/logical pixels, so feeding logical
    //     sizes keeps the page laid out correctly on high-DPI displays.
    //   - Only the GPU render target and the compositor surface are in PHYSICAL pixels. The
    //     UI quad dest rects and the camera surface bounds are converted logical -> pixels
    //     via the per-axis DPI scale below.
    int logical_w = 0;
    int logical_h = 0;
    SDL_GetWindowSize(context.window, &logical_w, &logical_h);
    if (logical_w <= 0 || logical_h <= 0) {
        return;  // window not ready this frame
    }

    // Pixel size of the render target. On the very first frame(s) it may not exist yet
    // (width()/height() == 0); fall back to a 1:1 scale so we never collapse quads or
    // camera bounds to zero.
    const uint32_t pixel_w = context.vulkan_backend->width();
    const uint32_t pixel_h = context.vulkan_backend->height();
    const float scale_x = (pixel_w > 0) ? static_cast<float>(pixel_w) / static_cast<float>(logical_w) : 1.0f;
    const float scale_y = (pixel_h > 0) ? static_cast<float>(pixel_h) / static_cast<float>(logical_h) : 1.0f;

    const WorkArea work = make_client_work_area(logical_w, logical_h);
    const std::vector<PanelLayoutInput> inputs = collect_layout_inputs();
    const std::vector<PanelPlacement> placements = compute_panel_layout(work, inputs);

    // 6) Resize every visible tab's CEF buffer to its LOGICAL panel size (matches the old
    //    per-tab resize_tab(avail_size)), and bind camera viewports onto the main surface
    //    using PIXEL bounds (the DisplaySystem composites optics against the pixel surface).
    void* main_surface = nullptr;
#if defined(_WIN32)
    if (context.window) {
        main_surface = SDL_GetPointerProperty(SDL_GetWindowProperties(context.window),
                                              SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr);
    }
#elif defined(__APPLE__)
    if (context.window) {
        main_surface = SDL_GetPointerProperty(SDL_GetWindowProperties(context.window),
                                              SDL_PROP_WINDOW_COCOA_WINDOW_POINTER, nullptr);
    }
#endif

    for (const PanelPlacement& placement : placements) {
        auto* tab = BrowserManager::instance().get_tab(placement.tab_id);
        if (!tab) {
            continue;
        }

        // Logical panel size -> CEF buffer.
        const int lw = std::max(1, static_cast<int>(std::lround(placement.rect.w)));
        const int lh = std::max(1, static_cast<int>(std::lround(placement.rect.h)));
        if (lw != tab->width || lh != tab->height) {
            BrowserManager::instance().resize_tab(placement.tab_id, lw, lh);
        }

        if (!tab->camera_view) {
            continue;
        }

        // Pixel bounds for the camera viewport composited onto the main surface.
        const int px = static_cast<int>(std::lround(placement.rect.x * scale_x));
        const int py = static_cast<int>(std::lround(placement.rect.y * scale_y));
        const int pw = std::max(1, static_cast<int>(std::lround(placement.rect.w * scale_x)));
        const int ph = std::max(1, static_cast<int>(std::lround(placement.rect.h * scale_y)));
        tab->platform_handle_raw = main_surface;
        tab->platform_window_id = context.window ? SDL_GetWindowID(context.window) : 0;
        if (main_surface) {
            CameraViewportManager::instance().bind_surface(placement.tab_id, main_surface,
                                                           px, py, pw, ph);
        }
        CameraViewportManager::instance().update_layout(placement.tab_id, px, py, pw, ph);
    }

    // 7) Route mouse input to the hit panel's browser (LOGICAL coordinates throughout).
    route_mouse_to_panels(placements, *context.active_tab_id);

    // 8) Build quad list (one quad per visible panel texture) and render. Quad dest rects are
    //    in PIXELS (the render target is pixel-sized); the CEF texture (logical-sized) is
    //    upscaled by the sampler.
    std::vector<QuadDraw> quads;
    quads.reserve(placements.size());
    for (const PanelPlacement& placement : placements) {
        auto* tab = BrowserManager::instance().get_tab(placement.tab_id);
        if (!tab || !is_valid_texture_id(tab->texture_id)) {
            continue;
        }
        const Horizon::HardwareImage* image =
            BrowserManager::instance().get_texture_image(tab->texture_id);
        if (image == nullptr) {
            continue;
        }
        QuadDraw quad;
        quad.texture = image;
        quad.dest_min = ktm::fvec2(placement.rect.x * scale_x, placement.rect.y * scale_y);
        quad.dest_max = ktm::fvec2((placement.rect.x + placement.rect.w) * scale_x,
                                   (placement.rect.y + placement.rect.h) * scale_y);
        quads.push_back(quad);
    }

    context.vulkan_backend->render_quads(quads);
    context.vulkan_backend->present_frame();

    // 9) Close tabs flagged closed.
    for (int tab_id : tabs_to_close) {
        BrowserManager::instance().remove_tab(tab_id);
        if (tab_id == *context.active_tab_id) {
            *context.active_tab_id = -1;
        }
        if (tab_id == url_input_active_tab_) {
            url_input_active_tab_ = -1;
        }
    }
}

}  // namespace Corona::Systems::UI
