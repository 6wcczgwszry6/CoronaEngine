//
// Created by GitHub Copilot on 2026/4/9.
//

#pragma once

#include "window/GUI/decl.h"
#include "window/GUI/window.h"

namespace vision {

[[nodiscard]] WindowPtr create_window(const char *name,
                                      ocarina::uint2 initial_size,
                                      WindowLibrary library,
                                      const char *type = "imGui",
                                      bool resizable = false) noexcept;

[[nodiscard]] WindowPtr create_window(const char *name,
                                      ocarina::uint2 initial_size,
                                      const char *type = "imGui",
                                      bool resizable = false) noexcept;

}// namespace vision