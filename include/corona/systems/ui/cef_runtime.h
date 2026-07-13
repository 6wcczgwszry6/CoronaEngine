#pragma once

#include <optional>

namespace Corona::Systems::UI {

/**
 * Dispatch the current process to CEF when launched with a CEF process type.
 * Call this once at the very beginning of main(), before any engine subsystem.
 */
[[nodiscard]] std::optional<int> execute_cef_subprocess_if_needed(
    int argc,
    char* argv[]);

}  // namespace Corona::Systems::UI
