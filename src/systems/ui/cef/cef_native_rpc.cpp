#include "cef_native_rpc.h"

#include <mutex>
#include <stdexcept>
#include <unordered_set>

namespace Corona::Systems::UI {

void register_scene_tools_rpc_handlers(NativeRpcRegistry& registry);
void register_scene_datas_rpc_handlers(NativeRpcRegistry& registry);
void register_main_view_rpc_handlers(NativeRpcRegistry& registry);
void register_project_settings_rpc_handlers(NativeRpcRegistry& registry);
void register_network_rpc_handlers(NativeRpcRegistry& registry);
void register_lanchat_rpc_handlers(NativeRpcRegistry& registry);

NativeRpcRegistry& NativeRpcRegistry::instance() {
    static NativeRpcRegistry registry;
    return registry;
}

void NativeRpcRegistry::register_module(std::string module, NativeHandlerFn handler) {
    handlers_[std::move(module)] = std::move(handler);
}

std::optional<NativeResult> NativeRpcRegistry::dispatch(
    const NativeRequest& request,
    const NativeContext& context) const {
    const auto it = handlers_.find(request.module);
    if (it == handlers_.end()) {
        return std::nullopt;
    }
    auto result = it->second(request, context);
    if (!result.handled) {
        return std::nullopt;
    }
    return result;
}

NativeResult native_success(nlohmann::json data, std::string route) {
    NativeResult result;
    result.success = true;
    result.data = std::move(data);
    result.route = std::move(route);
    return result;
}

NativeResult native_failure(std::string error, int error_code, std::string route) {
    NativeResult result;
    result.handled = true;
    result.success = false;
    result.error_code = error_code;
    result.error = std::move(error);
    result.route = std::move(route);
    return result;
}

NativeResult native_unhandled() {
    NativeResult result;
    result.handled = false;
    result.success = false;
    result.route = "unhandled";
    return result;
}

NativeRequest parse_native_request(const std::string& request_json) {
    const auto root = nlohmann::json::parse(request_json, nullptr, false);
    if (root.is_discarded() || !root.is_object()) {
        throw std::runtime_error("Invalid native request JSON");
    }

    NativeRequest request;

    if (auto it = root.find("module"); it != root.end() && it->is_string()) {
        request.module = it->get<std::string>();
    }
    if (auto it = root.find("function"); it != root.end() && it->is_string()) {
        request.function = it->get<std::string>();
    }
    if (auto it = root.find("args"); it != root.end()) {
        request.args = *it;
    } else {
        request.args = nlohmann::json::array();
    }
    if (!request.args.is_array()) {
        request.args = nlohmann::json::array({request.args});
    }
    return request;
}

std::string native_success_json(const NativeRequest& request, const NativeResult& result) {
    nlohmann::json payload;
    payload["success"] = true;
    payload["data"] = result.data;
    payload["function"] = request.function;
    payload["module"] = request.module;
    payload["route"] = result.route;
    return payload.dump();
}

std::string unsupported_python_route_json(const NativeRequest& request) {
    nlohmann::json payload;
    payload["success"] = false;
    payload["error"] = request.module + "." + request.function + " is not allowed on Python route";
    payload["module"] = request.module;
    payload["function"] = request.function;
    payload["route"] = "unsupported";
    return payload.dump();
}

bool is_python_fallback_allowed(const std::string& module, const std::string& function) {
    static const std::unordered_set<std::string> module_allowlist = {
        "AITool",
        "ScratchTool",
    };
    if (module_allowlist.contains(module)) {
        return true;
    }

    static const std::unordered_map<std::string, std::unordered_set<std::string>> method_allowlist = {
        {"MainView", {
            "scene_save",
            "import_resource_file",
            "import_model",
            "import_media",
            "import_scene_file",
            "run_project",
        }},
        {"ProjectLauncher", {
            "get_default_project_path",
            "get_app_version",
            "get_recent_projects",
            "create_project",
            "create_world_project",
            "create_multiplayer_project",
            "open_project",
            "open_project_file",
            "browse_folder",
            "set_project_mode",
        }},
        {"FileManager", {
            "open_file",
        }},
        {"ProjectSettings", {
            "save_active_project_info",
            "browse_scene_file",
        }},
        {"SceneDatas", {
            "save_actor",
            "select_model_file",
        }},
        {"SceneTools", {
            "save_screenshot",
            "select_screenshot_path",
            "select_vision_scene_path",
            "import_vision_scene_into_current_scene",
            "sun_direction",
            "floor_grid",
        }},
    };

    const auto it = method_allowlist.find(module);
    return it != method_allowlist.end() && it->second.contains(function);
}

void register_builtin_native_rpc_handlers() {
    static std::once_flag once;
    std::call_once(once, [] {
        auto& registry = NativeRpcRegistry::instance();
        register_main_view_rpc_handlers(registry);
        register_project_settings_rpc_handlers(registry);
        register_scene_datas_rpc_handlers(registry);
        register_scene_tools_rpc_handlers(registry);
        register_network_rpc_handlers(registry);
        register_lanchat_rpc_handlers(registry);
    });
}

std::string arg_string(const nlohmann::json& args, size_t index, std::string fallback) {
    if (!args.is_array() || index >= args.size()) {
        return fallback;
    }
    const auto& value = args[index];
    if (value.is_string()) {
        return value.get<std::string>();
    }
    if (value.is_number_integer() || value.is_number_unsigned() || value.is_number_float()) {
        return value.dump();
    }
    return fallback;
}

bool arg_bool(const nlohmann::json& args, size_t index, bool fallback) {
    if (!args.is_array() || index >= args.size()) {
        return fallback;
    }
    const auto& value = args[index];
    if (value.is_boolean()) {
        return value.get<bool>();
    }
    return fallback;
}

uint16_t arg_uint16(const nlohmann::json& args, size_t index, uint16_t fallback) {
    if (!args.is_array() || index >= args.size()) {
        return fallback;
    }
    try {
        const auto& value = args[index];
        if (value.is_number_unsigned()) {
            return value.get<uint16_t>();
        }
        if (value.is_number_integer()) {
            const auto raw = value.get<int64_t>();
            return raw >= 0 ? static_cast<uint16_t>(raw) : fallback;
        }
        if (value.is_string()) {
            return static_cast<uint16_t>(std::stoul(value.get<std::string>()));
        }
    } catch (...) {
    }
    return fallback;
}

uint64_t arg_uint64(const nlohmann::json& args, size_t index, uint64_t fallback) {
    if (!args.is_array() || index >= args.size()) {
        return fallback;
    }
    try {
        const auto& value = args[index];
        if (value.is_number_unsigned()) {
            return value.get<uint64_t>();
        }
        if (value.is_number_integer()) {
            const auto raw = value.get<int64_t>();
            return raw >= 0 ? static_cast<uint64_t>(raw) : fallback;
        }
        if (value.is_string()) {
            return std::stoull(value.get<std::string>());
        }
    } catch (...) {
    }
    return fallback;
}

std::uintptr_t arg_uintptr(const nlohmann::json& args, size_t index, std::uintptr_t fallback) {
    return static_cast<std::uintptr_t>(arg_uint64(args, index, static_cast<uint64_t>(fallback)));
}

nlohmann::json arg_object(const nlohmann::json& args, size_t index) {
    if (!args.is_array() || index >= args.size() || !args[index].is_object()) {
        return nlohmann::json::object();
    }
    return args[index];
}

}  // namespace Corona::Systems::UI
