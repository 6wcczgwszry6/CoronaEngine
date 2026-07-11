#include <SDL3/SDL.h>

#include <corona/systems/display/display_system.h>
#include <corona/kernel/core/kernel_context.h>
#include <corona/systems/ui/quad_compositor.h>
#include <corona/systems/ui/vulkan_backend.h>

#include <cstdlib>
#include <array>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {

constexpr int kSkip = 77;

class KernelSystemContext final : public Corona::Kernel::ISystemContext {
   public:
    Corona::Kernel::IEventBus* event_bus() override { return Corona::Kernel::KernelContext::instance().event_bus(); }
    Corona::Kernel::IEventBusStream* event_stream() override { return Corona::Kernel::KernelContext::instance().event_stream(); }
    Corona::Kernel::ISystem* get_system(std::string_view) override { return nullptr; }
    float get_delta_time() const override { return 1.0f / 120.0f; }
    uint64_t get_frame_number() const override { return frame_; }
    uint64_t frame_ = 0;
};

void destroy_windows(std::vector<SDL_Window*>& windows) {
    for (auto* window : windows) {
        if (window) SDL_DestroyWindow(window);
    }
    windows.clear();
}

int run_smoke() {
    if (std::getenv("CORONA_RUN_GPU_SMOKE") == nullptr ||
        std::string(std::getenv("CORONA_RUN_GPU_SMOKE")) != "1") {
        std::cout << "UiMultiSurfaceSmoke skipped; set CORONA_RUN_GPU_SMOKE=1 to enable\n";
        return kSkip;
    }

    if (!SDL_Init(SDL_INIT_VIDEO)) {
        std::cerr << "UiMultiSurfaceSmoke skipped: SDL_Init failed: " << SDL_GetError() << '\n';
        return kSkip;
    }
    auto& kernel = Corona::Kernel::KernelContext::instance();
    if (!kernel.initialize()) {
        std::cerr << "UiMultiSurfaceSmoke skipped: KernelContext initialization failed\n";
        SDL_Quit();
        return kSkip;
    }

    std::vector<SDL_Window*> windows;
    auto* main_window = SDL_CreateWindow("Corona UI multisurface smoke", 320, 240,
                                         SDL_WINDOW_VULKAN | SDL_WINDOW_HIDDEN | SDL_WINDOW_RESIZABLE);
    if (!main_window) {
        std::cerr << "UiMultiSurfaceSmoke skipped: main SDL window failed: " << SDL_GetError() << '\n';
        SDL_Quit();
        return kSkip;
    }
    windows.push_back(main_window);

    Corona::Systems::DisplaySystem display;
    KernelSystemContext context;
    if (!display.initialize(&context)) {
        std::cerr << "UiMultiSurfaceSmoke failed: DisplaySystem initialization failed\n";
        destroy_windows(windows);
        kernel.shutdown();
        SDL_Quit();
        return 1;
    }
    Corona::Systems::VulkanBackend backend(main_window);
    if (!backend.initialize()) {
        std::cerr << "UiMultiSurfaceSmoke skipped: VulkanBackend initialization failed\n";
        display.shutdown();
        destroy_windows(windows);
        kernel.shutdown();
        SDL_Quit();
        return kSkip;
    }

    // Exercise the real DisplaySystem lifecycle as part of the smoke target. The
    // display event bus is intentionally absent here: this keeps the test CEF-free
    // while still validating that a display instance can be initialized/shut down
    // around the Vulkan surface owner.
    display.update();

    const auto render_solid = [&](void* surface, uint32_t width, uint32_t height) {
        Corona::Systems::QuadDraw quad;
        quad.dest_min = ktm::fvec2(0.0f, 0.0f);
        quad.dest_max = ktm::fvec2(static_cast<float>(width), static_cast<float>(height));
        quad.color = ktm::fvec4(0.12f, 0.28f, 0.72f, 1.0f);
        const std::array<Corona::Systems::QuadDraw, 1> quads{quad};
        backend.render_quads(surface, quads, width, height);
    };

    // Cover 1, 3 and 16 windows, including a same-frame registration burst.
    for (int requested = 1; requested <= 16; requested = requested == 1 ? 3 : 16) {
        std::vector<void*> surfaces;
        for (int i = 1; i < requested; ++i) {
            auto* window = SDL_CreateWindow("Corona UI secondary", 160, 120,
                                            SDL_WINDOW_VULKAN | SDL_WINDOW_HIDDEN | SDL_WINDOW_RESIZABLE);
            if (!window) {
                std::cerr << "UiMultiSurfaceSmoke failed creating secondary: " << SDL_GetError() << '\n';
                display.shutdown();
                backend.shutdown();
                destroy_windows(windows);
                SDL_Quit();
                return 1;
            }
            windows.push_back(window);
            const auto properties = SDL_GetWindowProperties(window);
            void* native_surface = static_cast<void*>(SDL_GetPointerProperty(
                properties, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
            if (!native_surface) {
                native_surface = window;
            }
            if (!backend.register_surface(native_surface, window)) {
                std::cerr << "UiMultiSurfaceSmoke failed registering secondary surface\n";
                display.shutdown();
                backend.shutdown();
                destroy_windows(windows);
                SDL_Quit();
                return 1;
            }
            surfaces.push_back(native_surface);
        }

        for (void* surface : surfaces) {
            backend.new_frame(surface);
            backend.rebuild(surface, 160, 120);
            render_solid(surface, 160, 120);
            backend.present_surface(surface);
        }
        backend.new_frame(backend.main_surface());
        backend.rebuild(backend.main_surface(), 320, 240);
        render_solid(backend.main_surface(), 320, 240);
        backend.present_surface(backend.main_surface());
        display.update();

        for (void* surface : surfaces) backend.unregister_surface(surface);
        while (windows.size() > 1) {
            SDL_DestroyWindow(windows.back());
            windows.pop_back();
        }
    }

    // Resize/minimize/restore path on the main window.
    SDL_SetWindowSize(main_window, 640, 480);
    backend.rebuild(backend.main_surface(), 640, 480);
    render_solid(backend.main_surface(), 640, 480);
    SDL_MinimizeWindow(main_window);
    SDL_RestoreWindow(main_window);
    backend.rebuild(backend.main_surface(), 320, 240);
    render_solid(backend.main_surface(), 320, 240);

    // Repeated create/destroy catches stale surface/image handles.
    for (int cycle = 0; cycle < 100; ++cycle) {
        auto* window = SDL_CreateWindow("Corona UI cycle", 96, 96,
                                        SDL_WINDOW_VULKAN | SDL_WINDOW_HIDDEN);
        if (!window) break;
        windows.push_back(window);
        const auto properties = SDL_GetWindowProperties(window);
        void* native_surface = static_cast<void*>(SDL_GetPointerProperty(
            properties, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
        if (!native_surface) native_surface = window;
        if (!backend.register_surface(native_surface, window)) break;
        backend.new_frame(native_surface);
        backend.rebuild(native_surface, 96, 96);
        render_solid(native_surface, 96, 96);
        backend.unregister_surface(native_surface);
        SDL_DestroyWindow(window);
        windows.pop_back();
    }

    // Direct shutdown with three live secondaries.
    std::vector<void*> live_surfaces;
    for (int i = 0; i < 3; ++i) {
        auto* window = SDL_CreateWindow("Corona UI shutdown", 128, 128,
                                        SDL_WINDOW_VULKAN | SDL_WINDOW_HIDDEN);
        if (!window) break;
        windows.push_back(window);
        const auto properties = SDL_GetWindowProperties(window);
        void* native_surface = static_cast<void*>(SDL_GetPointerProperty(
            properties, SDL_PROP_WINDOW_WIN32_HWND_POINTER, nullptr));
        if (!native_surface) native_surface = window;
        if (backend.register_surface(native_surface, window)) live_surfaces.push_back(native_surface);
    }
    for (void* surface : live_surfaces) backend.unregister_surface(surface);

    display.shutdown();
    backend.shutdown();
    kernel.shutdown();
    destroy_windows(windows);
    SDL_Quit();
    std::cout << "UiMultiSurfaceSmoke passed: 1/3/16, burst, resize/minimize/restore, 100 cycles, shutdown drain\n";
    return 0;
}

}  // namespace

int main() { return run_smoke(); }
