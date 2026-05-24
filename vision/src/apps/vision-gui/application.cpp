//
// Created by Zero on 26/10/2022.
//

#include "application.h"
#include "window/window.h"
#include "math/basic_types.h"
#include "base/mgr/global.h"
#include "base/mgr/interactive_runtime_switches.h"
#include "base/import/importer.h"
#include "rhi/stats.h"
#include "GLFW/glfw3.h"

//#define VS_KEY_RIGHT 262
//#define VS_KEY_LEFT 263
//#define VS_KEY_DOWN 264
//#define VS_KEY_UP 265

namespace vision {
using namespace ocarina;

namespace {

struct InteractiveRuntimeConfig {
    bool enable_full_ui{false};
    bool enable_printer{false};
    bool enable_hotfix{false};
};

[[nodiscard]] InteractiveRuntimeConfig interactive_runtime_config() noexcept {
    InteractiveRuntimeConfig config;
#if VISION_INTERACTIVE_AUX_WORK
    config.enable_full_ui = true;
    config.enable_printer = true;
    config.enable_hotfix = true;
#endif
    return config;
}

void report_interactive_benchmark_and_close(App &app) noexcept {
    if (app.window == nullptr || app.interactive_benchmark_reported || app.params.interactive_frames == 0) {
        return;
    }
    uint frame_index = app.pipeline().frame_index();
    if (frame_index < app.params.interactive_frames) {
        return;
    }
    double total_ms = app.pipeline().render_time();
    double avg_ms = frame_index == 0 ? 0.0 : total_ms / static_cast<double>(frame_index);
    printf("VISION_INTERACTIVE_AUX_WORK=%d\n", VISION_INTERACTIVE_AUX_WORK ? 1 : 0);
    printf("VISION_INTERACTIVE_FRAMES=%u\n", frame_index);
    printf("VISION_INTERACTIVE_RENDER_TIME_MS=%.2f\n", total_ms);
    printf("VISION_INTERACTIVE_AVG_FRAME_MS=%.4f\n", avg_ms);
    app.interactive_benchmark_reported = true;
    app.window->set_should_close();
}

void prepare_offline_mode(App &app) noexcept {
    app.pipeline().set_window(nullptr);
    app.pipeline().frame_buffer()->prepare_view_texture();
    app.pipeline().set_output_spp(app.params.spp);
    app.pipeline().set_output_save_exit(true);
    Env::printer().set_enabled(false);
}

void prepare_interactive_mode(App &app) noexcept {
    InteractiveRuntimeConfig config = interactive_runtime_config();
    uint2 res = app.pipeline().renderer().resolution();
    if (app.params.maximized_window) {
        res = make_uint2(0);
    }
    app.window = create_window("LajiRender", res, "imGui", true);
    app.window->set_ui_enabled(true);
    app.pipeline().set_window(app.window.get());
    res = app.window->size();
    app.pipeline().change_resolution(res);
    app.pipeline().frame_buffer()->prepare_view_texture(app.window->shared_texture_handle());
    Env::printer().set_enabled(config.enable_printer);
}

void update_interactive_aux_work(App &app) noexcept {
    InteractiveRuntimeConfig config = interactive_runtime_config();
    app.pipeline().upload_data();
    if (config.enable_hotfix) {
        HotfixSystem::instance().execute_callback();
    }
}

void render_interactive_ui(App &app) noexcept {
    if (app.window == nullptr) {
        return;
    }
    InteractiveRuntimeConfig config = interactive_runtime_config();
    if (config.enable_full_ui) {
        app.render_UI(app.window->widgets());
    } else {
        app.pipeline().ui().render_perf_panel(app.window->widgets());
    }
}

}// namespace

void App::init(int argc) {
    core::log_level_info();
    if (argc == 1 || cli_parser->has_help_cmd()) {
        cli_parser->print_help();
        exit(0);
    }
    params.init(cli_parser.get());
    device.init_rtx();
    if (params.clear_cache) {
        RHIContext::instance().clear_cache();
    }
    if (cli_parser) {
        cli_parser->try_print_help_and_exit();
    }
    prepare();
}

void App::init_pipeline() {
    Global::instance().set_device(&device);
    rp = Importer::import_scene(params.scene_file);
    pipeline().init();
}

void App::prepare() {
    init_pipeline();
    pipeline().prepare();
    if (params.spp > 0) {
        pipeline().set_output_spp(params.spp);
        pipeline().set_output_save_exit(true);
    }
    if (params.denoise) {
        pipeline().set_output_denoise(true);
    }
    if (params.headless) {
        prepare_offline_mode(*this);
    } else {
        prepare_interactive_mode(*this);
    }
    if (!params.output_fn.empty()) {
        pipeline().set_output_fn(params.output_fn);
    }
    if (!params.headless) {
        register_event();
    }
}

void App::on_key_event(int key, int action) noexcept {
    switch (key) {
        case 'F':
            key_f_press = bool(action);
            return;
        case 'R':
            key_r_press = bool(action);
            return;
        case 'G':
            key_g_press = bool(action);
            if (key_g_press) {
                Env::debugger().filp_enabled();
                cout << ocarina::format("\n Debugger state is {}", Env::debugger().is_enabled()) << endl;
            }
            return;
        case 'Z':
            if (action) {
                pipeline().ui().filp_show_fps();
            }
            return;
        case GLFW_KEY_F10:
            if (action) {
                window->swap_monitor();
            }
            return;
        case GLFW_KEY_F11:
            if (action) {
                window->full_screen();
            }
            return;
        default:
            break;
    }
    if (action == 0) {
        return;
    }
    double dt = window->dt();
    TSensor camera = pipeline().scene().sensor();
    float3 forward = camera->forward();
    float3 up = camera->up();
    float3 right = camera->right();
    float distance = camera->velocity() * dt;
    float sens = 1.f;
    switch (key) {
        case 'W':
            camera->move(forward * distance);
            break;
        case 'A':
            camera->move(-right * distance);
            break;
        case 'S':
            camera->move(-forward * distance);
            break;
        case 'D':
            camera->move(right * distance);
            break;
        case 'Q':
            camera->move(-up * distance);
            break;
        case 'E':
            camera->move(up * distance);
            break;
        case GLFW_KEY_UP:
            update_camera_view(0, sens);
            break;
        case GLFW_KEY_DOWN:
            update_camera_view(0, -sens);
            break;
        case GLFW_KEY_LEFT:
            update_camera_view(-sens, 0);
            break;
        case GLFW_KEY_RIGHT:
            update_camera_view(sens, 0);
            break;
        default:
            return;
    }
    invalidation = true;
}

void App::on_window_size_change(uint2 res) noexcept {
    if (res.x * res.y == 0) {
        return;
    }
    pipeline().change_resolution(res);
    pipeline().frame_buffer()->prepare_view_texture(window->shared_texture_handle());
    invalidation = true;
}

void App::on_scroll_event(float2 scroll) noexcept {
    invalidation = true;
    auto camera = pipeline().scene().sensor();
    camera->update_fov_y(scroll.y);
    invalidation = true;
}

void App::update_camera_view(float d_yaw, float d_pitch) const noexcept {
    auto camera = pipeline().scene().sensor();
    float sensitivity = camera->sensitivity();
    camera->update_yaw(d_yaw * sensitivity);
    camera->update_pitch(d_pitch * sensitivity);
}

void App::on_cursor_move(float2 pos) noexcept {
    if (is_zero(last_cursor_pos)) {
        last_cursor_pos = pos;
        return;
    }
    float2 delta = pos - last_cursor_pos;
    last_cursor_pos = pos;
    if (right_key_press) {
        update_camera_view(delta.x, -delta.y);
    } else {
        return;
    }
    invalidation = true;
}

void App::on_mouse_event(int button, int action, float2 pos) noexcept {
    switch (button) {
        case 0: {
            left_key_press = bool(action);
            switch (action) {
                case 1:
                    pipeline().on_touch(make_uint2(pos));
                    break;
                    //                case 0: Env::debugger().set_upper(make_uint2(pos)); break;
                default: break;
            }
            break;
        }
        case 1: right_key_press = bool(action); break;
        default: break;
    }
}

bool App::render_UI(Widgets *widgets) noexcept {
    pipeline().ui().render(widgets);
    return true;
}

void App::update(double dt) noexcept {
    update_interactive_aux_work(*this);
    if (invalidation || pipeline().has_changed()) {
        invalidation = false;
        pipeline().invalidate();
    }
    pipeline().display(dt);
    pipeline().reset_status();
    render_interactive_ui(*this);
    report_interactive_benchmark_and_close(*this);
//    window->set_background(pipeline().frame_buffer()->window_buffer().data());
    rp->check_and_save();
}

int App::run() noexcept {
    if (window == nullptr) {
        while (pipeline().frame_index() < pipeline().output_spp()) {
            update(0.0);
        }
        rp->check_and_save();
        return 0;
    }
    window->run([&](double dt) {
        update(dt);
    });
    return 0;
}

void App::register_event() noexcept {
    window->set_key_callback([&]<typename... Args>(Args &&...args) {
        on_key_event(OC_FORWARD(args)...);
    });
    window->set_mouse_callback([&]<typename... Args>(Args &&...args) {
        on_mouse_event(OC_FORWARD(args)...);
    });
    window->set_cursor_position_callback([&]<typename... Args>(Args &&...args) {
        on_cursor_move(OC_FORWARD(args)...);
    });
    window->set_scroll_callback([&]<typename... Args>(Args &&...args) {
        on_scroll_event(OC_FORWARD(args)...);
    });
    //todo check resize bug
    window->set_window_size_callback([&]<typename... Args>(Args &&...args) {
        on_window_size_change(OC_FORWARD(args)...);
    });
}

}// namespace vision