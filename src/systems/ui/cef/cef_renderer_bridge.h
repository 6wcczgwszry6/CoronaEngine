#pragma once

#include <include/cef_app.h>

namespace Corona::Systems::UI {

CefRefPtr<CefRenderProcessHandler> create_cef_render_process_handler();

}  // namespace Corona::Systems::UI
