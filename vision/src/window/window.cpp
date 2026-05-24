//
// Created by GitHub Copilot on 2026/4/9.
//

#include "window.h"

#include <cstring>

#include "window/GUI_impl/imGui/glfw_window.h"

namespace vision {

WindowPtr create_window(const char *name,
                        ocarina::uint2 initial_size,
                        WindowLibrary library,
                        const char *type,
                        bool resizable) noexcept {
    if (library == WindowLibrary::GLFW) {
        return create_window(name, initial_size, type, resizable);
    }
    OC_WARNING("SDL window backend is not implemented in Vision window module yet. Falling back to GLFW.");
    return create_window(name, initial_size, type, resizable);
}

WindowPtr create_window(const char *name,
                        ocarina::uint2 initial_size,
                        const char *type,
                        bool resizable) noexcept {
    bool enable_ui = true;
    if (type != nullptr && std::strcmp(type, "imGui") != 0 && std::strcmp(type, "gl") != 0) {
        OC_WARNING_FORMAT("Unknown window type '{}', falling back to imGui/GLFW backend.", type);
    } else if (type != nullptr && std::strcmp(type, "gl") == 0) {
        enable_ui = false;
    }
    return ocarina::make_unique<GLWindow>(name, initial_size, resizable, enable_ui);
}

}// namespace vision