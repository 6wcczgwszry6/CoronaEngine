#pragma once

#include "cef_editor_api.h"

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include <string>

namespace EngineScripts {

void BindCef(nanobind::module_& m) {
    namespace nb = nanobind;
    m.def("register_python_script_dispatcher", [](nb::object dispatcher) {
        Corona::Systems::UI::register_python_script_dispatcher(dispatcher.ptr());
    }, nb::arg("dispatcher"));

    m.def("unregister_python_script_dispatcher", []() {
        Corona::Systems::UI::unregister_python_script_dispatcher();
    });

    m.def("invoke_cpp_api", [](const std::string& api_name, const std::string& args_json) {
        auto args = nlohmann::json::parse(args_json.empty() ? "[]" : args_json, nullptr, false);
        if (args.is_discarded()) {
            nlohmann::json response = {
                {"success", false},
                {"error", "Invalid Editor API args JSON"},
            };
            return response.dump();
        }

        Corona::Systems::UI::register_builtin_native_api_handlers();
        Corona::Systems::UI::PythonEditorApiEndpoint endpoint;
        Corona::Systems::UI::NativeContext context;
        auto result = endpoint.invoke(api_name, args, context);
        nlohmann::json response = {
            {"success", result.success},
            {"route", result.route},
        };
        if (result.success) {
            response["data"] = result.data;
        } else {
            response["error"] = result.error;
            response["error_code"] = result.error_code;
        }
        return response.dump();
    }, nb::arg("api_name"), nb::arg("args_json"));
}

}  // namespace EngineScripts
