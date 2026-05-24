//
// Created by GitHub Copilot on 2026/4/9.
//

#pragma once

#include "core/stl.h"
#include "math/basic_types.h"

namespace vision {

enum WindowLibrary {
	GLFW,
	SDL3,
};

class Window;
using WindowPtr = ocarina::unique_ptr<Window>;

}// namespace vision