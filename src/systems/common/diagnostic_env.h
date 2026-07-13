#pragma once

#include <algorithm>
#include <cctype>
#include <string>
#include <string_view>

namespace Corona::Systems::Diagnostics {

[[nodiscard]] inline bool parse_env_flag(const char* raw) {
    if (raw == nullptr || raw[0] == '\0') {
        return false;
    }
    std::string value(raw);
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return value != "0" && value != "false" && value != "off" && value != "no";
}

}  // namespace Corona::Systems::Diagnostics
