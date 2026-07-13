#pragma once

#include <include/cef_app.h>
#include <wrapper/cef_message_router.h>

namespace Corona::Systems::UI {

CefMessageRouterConfig make_cef_message_router_config();
CefRefPtr<CefApp> create_cef_app();
bool was_cef_process_dispatch_completed();

}  // namespace Corona::Systems::UI
