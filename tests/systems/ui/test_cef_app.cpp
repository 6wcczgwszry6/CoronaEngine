#include <corona/systems/ui/cef_runtime.h>

#include <array>
#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>

#include "cef/cef_app.h"

namespace {

void require(bool condition, std::string_view message) {
    if (condition) {
        return;
    }
    std::cerr << "CefAppTests failed: " << message << '\n';
    std::exit(1);
}

void test_message_router_config() {
    const auto config = Corona::Systems::UI::make_cef_message_router_config();
    require(config.js_query_function == "cefQuery", "unexpected query function");
    require(config.js_cancel_function == "cefQueryCancel", "unexpected cancel function");
}

void test_app_contract() {
    auto app = Corona::Systems::UI::create_cef_app();
    require(app != nullptr, "CEF app factory returned null");
    require(app->GetRenderProcessHandler() != nullptr, "renderer handler is missing");

    auto command_line = CefCommandLine::CreateCommandLine();
    command_line->InitFromString("corona_cef_app_tests.exe");
    app->OnBeforeCommandLineProcessing({}, command_line);

    constexpr std::array<std::string_view, 15> expected_switches{
        "disable-web-security",
        "allow-file-access-from-files",
        "allow-file-access",
        "no-sandbox",
        "disable-gpu",
        "disable-gpu-compositing",
        "disable-extensions",
        "disable-component-extensions-with-background-pages",
        "enable-net-benchmarking",
        "disable-pdf-extension",
        "disable-pdf-viewer",
        "disable-component-update",
        "disable-background-networking",
        "disable-d3d11",
        "disable-accelerated-video-decode",
    };

    for (const auto switch_name : expected_switches) {
        require(command_line->HasSwitch(std::string(switch_name)), switch_name);
    }
}

void test_browser_process_dispatch(int argc, char* argv[]) {
    const auto exit_code =
        Corona::Systems::UI::execute_cef_subprocess_if_needed(argc, argv);
    require(!exit_code.has_value(), "browser process was treated as a subprocess");
    require(Corona::Systems::UI::was_cef_process_dispatch_completed(),
            "browser process dispatch state was not recorded");
}

}  // namespace

int main(int argc, char* argv[]) {
    test_browser_process_dispatch(argc, argv);
    test_message_router_config();
    test_app_contract();
    return 0;
}
