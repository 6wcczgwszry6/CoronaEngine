#include "cef_client.h"
#include "cef_editor_api.h"
#include "cef_editor_native_api_registry.h"

#include <string>

namespace Corona::Systems::UI {

bool BrowserSideJSHandler::OnQuery(CefRefPtr<CefBrowser> browser,
                                   CefRefPtr<CefFrame> frame,
                                   int64_t query_id,
                                   const CefString& request,
                                   bool persistent,
                                   CefRefPtr<Callback> callback) {
    CEF_REQUIRE_UI_THREAD();
    std::string req = request.ToString();

    const auto request_payload = nlohmann::json::parse(req, nullptr, false);
    if (request_payload.is_discarded()) {
        NativeRequest invalid_request;
        callback->Success(unsupported_editor_api_route_json(invalid_request));
        return true;
    }

    register_builtin_native_api_handlers();
    NativeContext native_context{browser, frame, query_id};
    CefEditorApiEndpoint editor_api;

    const auto editor_api_request = parse_editor_api_request(request_payload, EditorApiCaller::Cef);
    if (!editor_api_request) {
        NativeRequest invalid_request;
        invalid_request.module = "EditorApi";
        invalid_request.function = "invalid_request";
        callback->Success(unsupported_editor_api_route_json(invalid_request));
        return true;
    }
    if (!EditorApiRegistry::instance().find(editor_api_request->api_name)) {
        callback->Failure(404,
                          editor_api_request->api_name + " is not defined by C++ Editor API");
        return true;
    }

    auto native_result = editor_api.invoke(editor_api_request->api_name,
                                           editor_api_request->args,
                                           native_context);
    NativeRequest response_request;
    response_request.module = "EditorApi";
    response_request.function = editor_api_request->api_name;
    response_request.args = editor_api_request->args;
    if (native_result.success) {
        callback->Success(native_success_json(response_request, native_result));
    } else {
        callback->Failure(native_result.error_code, native_result.error);
    }
    return true;
}

}  // namespace Corona::Systems::UI
