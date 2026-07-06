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

    if (request_payload.value("api", std::string{}) == "EditorApi.register_callback") {
        const auto args = request_payload.value("args", nlohmann::json::array());
        if (!args.is_array() || args.empty() || !args[0].is_string()) {
            callback->Failure(400, "EditorApi.register_callback requires an event name");
            return true;
        }
        const auto callback_spec = args.size() > 1 && args[1].is_object()
                                       ? args[1]
                                       : nlohmann::json::object();
        const auto token = editor_api.register_callback(args[0].get<std::string>(),
                                                        callback_spec,
                                                        native_context);
        if (token == 0) {
            callback->Failure(404, args[0].get<std::string>() + " is not a defined Editor API event");
            return true;
        }
        NativeRequest response_request;
        response_request.module = "EditorApi";
        response_request.function = "register_callback";
        response_request.args = args;
        callback->Success(native_success_json(response_request,
                                              native_success({{"callback_token", token}},
                                                             "editor-api-callback")));
        return true;
    }

    if (request_payload.value("api", std::string{}) == "EditorApi.unregister_callback") {
        const auto args = request_payload.value("args", nlohmann::json::array());
        if (!args.is_array() || args.empty() || !args[0].is_number_integer()) {
            callback->Failure(400, "EditorApi.unregister_callback requires a callback token");
            return true;
        }
        const auto raw_token = args[0].get<std::int64_t>();
        if (raw_token < 0) {
            callback->Failure(400, "EditorApi.unregister_callback requires a non-negative callback token");
            return true;
        }
        const auto removed = editor_api.unregister_callback(static_cast<std::uint64_t>(raw_token));
        NativeRequest response_request;
        response_request.module = "EditorApi";
        response_request.function = "unregister_callback";
        response_request.args = args;
        callback->Success(native_success_json(response_request,
                                              native_success({{"removed", removed}},
                                                             "editor-api-callback")));
        return true;
    }

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
