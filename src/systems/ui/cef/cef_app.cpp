#include "cef_app.h"

#include "cef_renderer_bridge.h"

namespace Corona::Systems::UI {

namespace {

class CoronaCefApp final : public CefApp {
   public:
    CoronaCefApp() : render_handler_(create_cef_render_process_handler()) {}

    void OnBeforeCommandLineProcessing(
        const CefString& process_type,
        CefRefPtr<CefCommandLine> command_line) override {
        command_line->AppendSwitch("disable-web-security");
        command_line->AppendSwitch("allow-file-access-from-files");
        command_line->AppendSwitch("allow-file-access");
        command_line->AppendSwitch("no-sandbox");
        command_line->AppendSwitch("disable-gpu");
        command_line->AppendSwitch("disable-gpu-compositing");
        command_line->AppendSwitch("disable-extensions");
        command_line->AppendSwitch("disable-component-extensions-with-background-pages");
        command_line->AppendSwitch("enable-net-benchmarking");
        command_line->AppendSwitch("disable-pdf-extension");
        command_line->AppendSwitch("disable-pdf-viewer");
        command_line->AppendSwitch("disable-component-update");
        command_line->AppendSwitch("disable-background-networking");
        command_line->AppendSwitch("disable-d3d11");
        command_line->AppendSwitch("disable-accelerated-video-decode");
    }

    CefRefPtr<CefRenderProcessHandler> GetRenderProcessHandler() override {
        return render_handler_;
    }

   private:
    CefRefPtr<CefRenderProcessHandler> render_handler_;

    IMPLEMENT_REFCOUNTING(CoronaCefApp);
};

}  // namespace

CefMessageRouterConfig make_cef_message_router_config() {
    CefMessageRouterConfig config;
    config.js_query_function = "cefQuery";
    config.js_cancel_function = "cefQueryCancel";
    return config;
}

CefRefPtr<CefApp> create_cef_app() {
    return new CoronaCefApp();
}

}  // namespace Corona::Systems::UI
