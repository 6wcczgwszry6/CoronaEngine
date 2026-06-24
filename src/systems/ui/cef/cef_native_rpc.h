#pragma once

#include <cef_browser.h>
#include <cef_frame.h>

#include <cstdint>
#include <functional>
#include <optional>
#include <string>
#include <unordered_map>

#include <nlohmann/json.hpp>

namespace Corona::Systems::UI {

struct NativeRequest {
    std::string module;
    std::string function;
    nlohmann::json args = nlohmann::json::array();
};

struct NativeContext {
    CefRefPtr<CefBrowser> browser;
    CefRefPtr<CefFrame> frame;
    int64_t query_id = 0;
};

struct NativeResult {
    bool handled = true;
    bool success = true;
    int error_code = 1;
    std::string error;
    nlohmann::json data = nlohmann::json::object();
    std::string route = "native-cpp";
};

using NativeHandlerFn = std::function<NativeResult(const NativeRequest&, const NativeContext&)>;
using NativeMethodTable = std::unordered_map<std::string, NativeHandlerFn>;

class NativeRpcRegistry {
public:
    static NativeRpcRegistry& instance();

    void register_module(std::string module, NativeHandlerFn handler);
    std::optional<NativeResult> dispatch(const NativeRequest& request,
                                         const NativeContext& context) const;

private:
    std::unordered_map<std::string, NativeHandlerFn> handlers_;
};

NativeResult native_success(nlohmann::json data = nlohmann::json::object(),
                            std::string route = "native-cpp");
NativeResult native_failure(std::string error,
                            int error_code = 1,
                            std::string route = "native-cpp");
NativeResult native_unhandled();

NativeRequest parse_native_request(const std::string& request_json);
std::string native_success_json(const NativeRequest& request, const NativeResult& result);
std::string unsupported_python_route_json(const NativeRequest& request);

bool is_python_fallback_allowed(const std::string& module, const std::string& function);
void register_builtin_native_rpc_handlers();

std::string arg_string(const nlohmann::json& args, size_t index, std::string fallback = "");
bool arg_bool(const nlohmann::json& args, size_t index, bool fallback = false);
uint16_t arg_uint16(const nlohmann::json& args, size_t index, uint16_t fallback = 0);
uint64_t arg_uint64(const nlohmann::json& args, size_t index, uint64_t fallback = 0);
std::uintptr_t arg_uintptr(const nlohmann::json& args, size_t index, std::uintptr_t fallback = 0);
nlohmann::json arg_object(const nlohmann::json& args, size_t index);

}  // namespace Corona::Systems::UI
