#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <iphlpapi.h>
#pragma comment(lib, "iphlpapi.lib")
#endif

#include "browser_manager.h"
#include "cef_client.h"
#include "cef_native_rpc.h"

#include <corona/events/acoustics_system_events.h>
#include <corona/kernel/core/kernel_context.h>
#include <corona/systems/network/network_system.h>
#include <corona/systems/script/corona_engine_api.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <initializer_list>
#include <map>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace Corona::Systems::UI {

namespace {

std::shared_ptr<Corona::Systems::NetworkSystem> get_network_system() {
    auto sys_mgr = Corona::Kernel::KernelContext::instance().system_manager();
    if (!sys_mgr) {
        return nullptr;
    }
    return std::dynamic_pointer_cast<Corona::Systems::NetworkSystem>(
        sys_mgr->get_system("Network"));
}

Corona::Systems::NetworkSystem::SessionRole parse_network_session_role(
    const nlohmann::json& value) {
    if (!value.is_string()) {
        return Corona::Systems::NetworkSystem::SessionRole::Host;
    }
    const auto role = value.get<std::string>();
    if (role == "client") {
        return Corona::Systems::NetworkSystem::SessionRole::Client;
    }
    if (role == "none") {
        return Corona::Systems::NetworkSystem::SessionRole::None;
    }
    return Corona::Systems::NetworkSystem::SessionRole::Host;
}

std::string to_lower_ascii(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

bool looks_like_wlan_adapter(const std::string& adapter_name) {
    const std::string name = to_lower_ascii(adapter_name);
    return name.find("wlan") != std::string::npos ||
           name.find("wi-fi") != std::string::npos ||
           name.find("wifi") != std::string::npos ||
           name.find("wireless") != std::string::npos ||
           name.find("无线") != std::string::npos;
}

bool is_usable_ipv4(const std::string& ip) {
    return !ip.empty() && ip.rfind("127.", 0) != 0 && ip != "0.0.0.0";
}

std::string trim_ascii(std::string value) {
    const auto begin = std::find_if_not(value.begin(), value.end(), [](unsigned char c) {
        return std::isspace(c) != 0;
    });
    const auto end = std::find_if_not(value.rbegin(), value.rend(), [](unsigned char c) {
        return std::isspace(c) != 0;
    }).base();
    if (begin >= end) {
        return {};
    }
    return std::string(begin, end);
}

std::filesystem::path path_from_utf8(const std::string& value) {
    return std::filesystem::u8path(value);
}

std::string path_to_utf8(const std::filesystem::path& value) {
    return value.generic_string();
}

std::string stem_utf8(const std::string& route) {
    return path_from_utf8(route).stem().string();
}

std::string normalize_route(std::string route) {
    route = trim_ascii(std::move(route));
    std::replace(route.begin(), route.end(), '\\', '/');
    return route;
}

std::filesystem::path resolve_project_path(const std::filesystem::path& project_root,
                                           const std::string& route) {
    const auto route_path = path_from_utf8(route);
    if (route_path.is_absolute()) {
        return route_path;
    }
    return project_root / route_path;
}

using IniSection = std::unordered_map<std::string, std::string>;
using IniFile = std::unordered_map<std::string, IniSection>;

IniFile read_ini_file(const std::filesystem::path& file_path) {
    IniFile result;
    std::ifstream input(file_path);
    if (!input) {
        return result;
    }

    std::string section;
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        auto trimmed = trim_ascii(line);
        if (trimmed.empty() || trimmed[0] == '#' || trimmed[0] == ';') {
            continue;
        }
        if (trimmed.front() == '[' && trimmed.back() == ']') {
            section = to_lower_ascii(trim_ascii(trimmed.substr(1, trimmed.size() - 2)));
            continue;
        }
        const auto equals = trimmed.find('=');
        if (equals == std::string::npos || section.empty()) {
            continue;
        }
        auto key = to_lower_ascii(trim_ascii(trimmed.substr(0, equals)));
        auto value = trim_ascii(trimmed.substr(equals + 1));
        result[section][key] = value;
    }
    return result;
}

std::string ini_value(const IniFile& ini,
                      const std::string& section,
                      const std::string& key,
                      const std::string& fallback = {}) {
    const auto sec_it = ini.find(to_lower_ascii(section));
    if (sec_it == ini.end()) {
        return fallback;
    }
    const auto key_it = sec_it->second.find(to_lower_ascii(key));
    return key_it == sec_it->second.end() ? fallback : key_it->second;
}

std::vector<std::string> split_csv_routes(const std::string& value) {
    std::vector<std::string> routes;
    std::stringstream input(value);
    std::string item;
    while (std::getline(input, item, ',')) {
        item = normalize_route(item);
        if (!item.empty()) {
            routes.push_back(item);
        }
    }
    return routes;
}

std::array<float, 3> parse_float3(const std::string& value,
                                  std::array<float, 3> fallback) {
    std::stringstream input(value);
    std::string item;
    std::array<float, 3> result = fallback;
    for (size_t index = 0; index < 3; ++index) {
        if (!std::getline(input, item, ',')) {
            return fallback;
        }
        try {
            result[index] = std::stof(trim_ascii(item));
        } catch (...) {
            return fallback;
        }
    }
    return result;
}

bool parse_bool(std::string value, bool fallback = false) {
    value = to_lower_ascii(trim_ascii(std::move(value)));
    if (value == "1" || value == "true" || value == "yes" || value == "on") {
        return true;
    }
    if (value == "0" || value == "false" || value == "no" || value == "off") {
        return false;
    }
    return fallback;
}

int parse_int(const std::string& value, int fallback) {
    try {
        return std::stoi(trim_ascii(value));
    } catch (...) {
        return fallback;
    }
}

float parse_float(const std::string& value, float fallback) {
    try {
        return std::stof(trim_ascii(value));
    } catch (...) {
        return fallback;
    }
}

struct NativeEditorCamera {
    std::string camera_id;
    std::string name;
    bool deletable{true};
    int width{1920};
    int height{1080};
    bool view_open{false};
    int view_x{120};
    int view_y{120};
    int view_width{960};
    int view_height{540};
    float move_speed{1.0f};
    std::unique_ptr<Corona::API::Camera> engine_camera;
};

struct NativeEditorActor {
    std::string name;
    std::string actor_guid;
    std::string route;
    std::string actor_type{"actor"};
    bool follow_camera{false};
    std::uint64_t audio_resource_id{0};  // 音频物体绑定的音频资源 id（actor_type=="audio"）
    std::array<float, 3> position{0.0f, 0.0f, 0.0f};
    std::array<float, 3> rotation{0.0f, 0.0f, 0.0f};
    std::array<float, 3> scale{1.0f, 1.0f, 1.0f};
    std::unique_ptr<Corona::API::Geometry> geometry;
    std::unique_ptr<Corona::API::Optics> optics;
    std::unique_ptr<Corona::API::Mechanics> mechanics;
    std::unique_ptr<Corona::API::Acoustics> acoustics;
    std::unique_ptr<Corona::API::Actor> engine_actor;
};

struct NativeEditorScene {
    std::filesystem::path project_root;
    std::string route;
    std::string name;
    std::string script_path;
    std::string terrain_type;
    std::string terrain_path;
    std::string vision_source_path;
    std::string vision_import_mode;
    std::array<float, 3> sun_direction{1.0f, 1.0f, 1.0f};
    bool sun_enabled{true};
    bool floor_grid_enabled{true};
    std::vector<NativeEditorActor> actors;
    std::vector<NativeEditorCamera> cameras;
    size_t active_camera_index{0};
    std::unique_ptr<Corona::API::Environment> environment;
    std::unique_ptr<Corona::API::Scene> engine_scene;
};

struct NativeEditorState {
    std::string project_path;
    std::unique_ptr<NativeEditorScene> scene;
};

NativeEditorState& native_editor_state() {
    static NativeEditorState state;
    return state;
}

std::string read_last_project_from_editor_ini() {
    const auto cwd_ini = std::filesystem::current_path() / "CoronaEditor.ini";
    const auto ini = read_ini_file(cwd_ini);
    return normalize_route(ini_value(ini, "General", "last_project"));
}

std::string resolve_active_project_path(const nlohmann::json& args) {
    auto project_path = normalize_route(arg_string(args, 0));
    if (!project_path.empty()) {
        return project_path;
    }
    auto& state = native_editor_state();
    if (!state.project_path.empty()) {
        return state.project_path;
    }
    return read_last_project_from_editor_ini();
}

std::string choose_single_scene_route(const std::filesystem::path& project_root,
                                      const IniFile& project_ini) {
    auto route = normalize_route(ini_value(project_ini, "Project", "entrance_scene"));
    if (!route.empty()) {
        return route;
    }

    auto scenes = split_csv_routes(ini_value(project_ini, "Project", "scenes"));
    if (!scenes.empty()) {
        return scenes.front();
    }

    const auto scene_dir = project_root / "Scene";
    if (std::filesystem::is_directory(scene_dir)) {
        std::vector<std::filesystem::path> files;
        for (const auto& entry : std::filesystem::directory_iterator(scene_dir)) {
            if (entry.is_regular_file() && entry.path().extension() == ".scene") {
                files.push_back(entry.path());
            }
        }
        std::sort(files.begin(), files.end());
        if (!files.empty()) {
            return normalize_route(path_to_utf8(std::filesystem::relative(files.front(), project_root)));
        }
    }
    return {};
}

std::string actor_file_extension(const std::string& route) {
    auto ext = path_from_utf8(route).extension().string();
    if (!ext.empty() && ext.front() == '.') {
        ext.erase(ext.begin());
    }
    return ext;
}

bool path_is_inside_project(const std::filesystem::path& relative_path) {
    if (relative_path.empty()) {
        return false;
    }
    for (const auto& part : relative_path) {
        if (part == "..") {
            return false;
        }
    }
    return true;
}

std::string route_for_project_storage(const std::filesystem::path& project_root,
                                      const std::string& raw_path) {
    const auto normalized = normalize_route(raw_path);
    if (normalized.empty()) {
        return {};
    }
    const auto source_path = path_from_utf8(normalized);
    if (!source_path.is_absolute()) {
        return normalized;
    }

    std::error_code ec;
    const auto relative = std::filesystem::relative(source_path, project_root, ec);
    if (!ec && path_is_inside_project(relative)) {
        return normalize_route(path_to_utf8(relative));
    }
    return normalize_route(path_to_utf8(source_path));
}

std::string unique_actor_name(const NativeEditorScene& scene, const std::string& preferred_name) {
    const std::string base = trim_ascii(preferred_name).empty() ? "Actor" : trim_ascii(preferred_name);
    auto exists = [&](const std::string& candidate) {
        return std::any_of(scene.actors.begin(), scene.actors.end(), [&](const NativeEditorActor& actor) {
            return actor.name == candidate;
        });
    };
    if (!exists(base)) {
        return base;
    }
    for (int index = 1; index < 10000; ++index) {
        const auto candidate = base + "_" + std::to_string(index);
        if (!exists(candidate)) {
            return candidate;
        }
    }
    return base + "_" + std::to_string(scene.actors.size() + 1);
}

std::string make_actor_guid(const std::string& scene_route,
                            const std::string& actor_name,
                            size_t index) {
    std::ostringstream out;
    out << "native-" << std::hex << std::hash<std::string>{}(scene_route + ":" + actor_name)
        << "-" << index;
    return out.str();
}

std::string format_float3(const std::array<float, 3>& value) {
    std::ostringstream out;
    out << std::setprecision(9)
        << value[0] << ", " << value[1] << ", " << value[2];
    return out.str();
}

std::string unique_actor_key(const NativeEditorScene& scene,
                             const NativeEditorActor& actor,
                             std::unordered_map<std::string, int>& used_keys,
                             size_t index) {
    std::string base = actor.name.empty() ? "actor" + std::to_string(index + 1) : actor.name;
    auto used = used_keys.find(base);
    if (used == used_keys.end()) {
        used_keys.emplace(base, 0);
        return base;
    }
    used->second += 1;
    return base + "_" + std::to_string(used->second);
}

std::vector<std::string> build_actors_section_lines(const NativeEditorScene& scene) {
    std::vector<std::string> lines;
    lines.emplace_back("[actors]");
    std::unordered_map<std::string, int> used_keys;
    for (size_t index = 0; index < scene.actors.size(); ++index) {
        const auto& actor = scene.actors[index];
        const auto key = unique_actor_key(scene, actor, used_keys, index);
        lines.push_back(key + ".actor_type = " + actor.actor_type);
        lines.push_back(key + ".name = " + actor.name);
        lines.push_back(key + ".route = " + actor.route);
        if (!actor.actor_guid.empty()) {
            lines.push_back(key + ".actor_guid = " + actor.actor_guid);
        }
        lines.push_back(key + ".follow_camera = " + std::string(actor.follow_camera ? "true" : "false"));
        if (actor.mechanics) {
            lines.push_back(key + ".mechanics.physics_enabled = " +
                            std::string(actor.mechanics->get_physics_enabled() ? "true" : "false"));
        }
        lines.push_back(key + ".geometry.position = " + format_float3(actor.geometry ? actor.geometry->get_position() : actor.position));
        lines.push_back(key + ".geometry.rotation = " + format_float3(actor.geometry ? actor.geometry->get_rotation() : actor.rotation));
        lines.push_back(key + ".geometry.scale = " + format_float3(actor.geometry ? actor.geometry->get_scale() : actor.scale));
    }
    return lines;
}

std::vector<std::string> build_sun_section_lines(const NativeEditorScene& scene) {
    return {
        "[sun]",
        "enabled = " + std::string(scene.sun_enabled ? "true" : "false"),
        "sun_direction = " + format_float3(scene.sun_direction),
    };
}

std::vector<std::string> build_grid_section_lines(const NativeEditorScene& scene) {
    return {
        "[grid]",
        "enabled = " + std::string(scene.floor_grid_enabled ? "true" : "false"),
    };
}

void replace_ini_section(const std::filesystem::path& file_path,
                         const std::string& section_name,
                         const std::vector<std::string>& replacement_lines) {
    std::vector<std::string> lines;
    {
        std::ifstream input(file_path);
        std::string line;
        while (std::getline(input, line)) {
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            lines.push_back(line);
        }
    }

    const auto target = to_lower_ascii(section_name);
    auto is_target_section = [&](const std::string& line) {
        const auto trimmed = trim_ascii(line);
        if (trimmed.size() < 3 || trimmed.front() != '[' || trimmed.back() != ']') {
            return false;
        }
        return to_lower_ascii(trim_ascii(trimmed.substr(1, trimmed.size() - 2))) == target;
    };
    auto is_any_section = [](const std::string& line) {
        const auto trimmed = trim_ascii(line);
        return trimmed.size() >= 3 && trimmed.front() == '[' && trimmed.back() == ']';
    };

    auto begin = lines.end();
    for (auto it = lines.begin(); it != lines.end(); ++it) {
        if (is_target_section(*it)) {
            begin = it;
            break;
        }
    }

    if (begin == lines.end()) {
        if (!lines.empty() && !lines.back().empty()) {
            lines.emplace_back();
        }
        lines.insert(lines.end(), replacement_lines.begin(), replacement_lines.end());
    } else {
        auto end = std::next(begin);
        while (end != lines.end() && !is_any_section(*end)) {
            ++end;
        }
        auto insert_pos = lines.erase(begin, end);
        insert_pos = lines.insert(insert_pos, replacement_lines.begin(), replacement_lines.end());
        auto after_insert = std::next(insert_pos, static_cast<std::ptrdiff_t>(replacement_lines.size()));
        if (after_insert != lines.end() && (after_insert == lines.begin() || !std::prev(after_insert)->empty())) {
            lines.insert(after_insert, "");
        }
    }

    std::ofstream output(file_path, std::ios::trunc);
    for (const auto& line : lines) {
        output << line << '\n';
    }
}

void persist_native_scene_actors(const NativeEditorScene& scene) {
    const auto scene_file = resolve_project_path(scene.project_root, scene.route);
    replace_ini_section(scene_file, "actors", build_actors_section_lines(scene));
}

void persist_native_scene_environment(const NativeEditorScene& scene) {
    const auto scene_file = resolve_project_path(scene.project_root, scene.route);
    replace_ini_section(scene_file, "sun", build_sun_section_lines(scene));
    replace_ini_section(scene_file, "grid", build_grid_section_lines(scene));
}

void apply_native_scene_environment(NativeEditorScene& scene) {
    if (!scene.environment) {
        return;
    }

    scene.environment->set_sun_direction(scene.sun_direction);
    scene.environment->set_floor_grid(scene.floor_grid_enabled);
    scene.environment->set_sun_intensity(scene.sun_enabled ? 10.0f : 0.0f);
    scene.environment->set_sky_intensity(scene.sun_enabled ? 20.0f : 0.0f);
}

std::filesystem::path resolve_native_actor_asset_path(const NativeEditorScene& scene,
                                                      NativeEditorActor& item) {
    if (item.actor_type != "actor" || to_lower_ascii(actor_file_extension(item.route)) != "actor") {
        return resolve_project_path(scene.project_root, item.route);
    }

    const auto actor_file = resolve_project_path(scene.project_root, item.route);
    const auto actor_ini = read_ini_file(actor_file);
    const auto model_route = normalize_route(ini_value(actor_ini, "base", "path"));
    if (item.name.empty()) {
        item.name = ini_value(actor_ini, "base", "name", stem_utf8(item.route));
    }
    if (item.actor_guid.empty()) {
        item.actor_guid = ini_value(actor_ini, "base", "actor_guid");
    }
    if (!item.follow_camera) {
        item.follow_camera = parse_bool(ini_value(actor_ini, "base", "follow_camera", "false"));
    }
    if (model_route.empty()) {
        throw std::runtime_error("Actor file missing [base].path: " + item.route);
    }
    return resolve_project_path(scene.project_root, model_route);
}

NativeEditorActor& add_native_actor_to_scene(NativeEditorScene& scene,
                                             NativeEditorActor item,
                                             const std::filesystem::path& asset_path) {
    if (item.actor_type == "ui_image") {
        auto image_geometry = Corona::API::Geometry::from_image(path_to_utf8(asset_path));
        item.geometry = std::make_unique<Corona::API::Geometry>(std::move(image_geometry));
    } else if (item.actor_type == "audio") {
        // 音频物体：无网格，纯 transform 几何（空路径）。
        item.geometry = std::make_unique<Corona::API::Geometry>(std::string{});
    } else {
        item.geometry = std::make_unique<Corona::API::Geometry>(path_to_utf8(asset_path));
    }
    item.geometry->set_position(item.position);
    item.geometry->set_rotation(item.rotation);
    item.geometry->set_scale(item.scale);

    item.optics = std::make_unique<Corona::API::Optics>(*item.geometry);
    item.mechanics = std::make_unique<Corona::API::Mechanics>(*item.geometry);
    item.acoustics = std::make_unique<Corona::API::Acoustics>(*item.geometry);
    if (item.actor_type == "ui_image") {
        item.optics->set_lighting_enabled(false);
        item.mechanics->set_physics_enabled(false);
        item.follow_camera = true;
    } else if (item.actor_type == "audio") {
        // 音频物体不渲染、不参与物理；绑定音频资源。
        item.optics->set_visible(false);
        item.mechanics->set_physics_enabled(false);
        if (item.audio_resource_id != 0) {
            item.acoustics->set_audio_resource(item.audio_resource_id);
        }
    }

    item.engine_actor = std::make_unique<Corona::API::Actor>();
    Corona::API::Actor::Profile profile{};
    profile.geometry = item.geometry.get();
    profile.optics = item.optics.get();
    profile.mechanics = item.mechanics.get();
    profile.acoustics = item.acoustics.get();
    auto* profile_ref = item.engine_actor->add_profile(profile);
    item.engine_actor->set_active_profile(profile_ref);
    item.engine_actor->set_actor_guid(item.actor_guid);
    item.engine_actor->set_follow_camera(item.follow_camera);
    scene.engine_scene->add_actor(item.engine_actor.get());
    scene.actors.push_back(std::move(item));
    return scene.actors.back();
}

void load_native_actor(NativeEditorScene& scene,
                       const IniSection& actors_section,
                       const std::string& actor_key,
                       size_t index) {
    NativeEditorActor item;
    item.name = actors_section.contains(actor_key + ".name")
                    ? actors_section.at(actor_key + ".name")
                    : actor_key;
    item.actor_type = actors_section.contains(actor_key + ".actor_type")
                          ? actors_section.at(actor_key + ".actor_type")
                          : "actor";
    item.route = normalize_route(actors_section.contains(actor_key + ".route")
                                     ? actors_section.at(actor_key + ".route")
                                     : "");
    item.actor_guid = actors_section.contains(actor_key + ".actor_guid")
                          ? actors_section.at(actor_key + ".actor_guid")
                          : "";
    item.follow_camera = actors_section.contains(actor_key + ".follow_camera") &&
                         parse_bool(actors_section.at(actor_key + ".follow_camera"));
    item.position = parse_float3(
        actors_section.contains(actor_key + ".geometry.position")
            ? actors_section.at(actor_key + ".geometry.position")
            : "0.0, 0.0, 0.0",
        {0.0f, 0.0f, 0.0f});
    item.rotation = parse_float3(
        actors_section.contains(actor_key + ".geometry.rotation")
            ? actors_section.at(actor_key + ".geometry.rotation")
            : "0.0, 0.0, 0.0",
        {0.0f, 0.0f, 0.0f});
    item.scale = parse_float3(
        actors_section.contains(actor_key + ".geometry.scale")
            ? actors_section.at(actor_key + ".geometry.scale")
            : "1.0, 1.0, 1.0",
        {1.0f, 1.0f, 1.0f});

    if (item.route.empty()) {
        return;
    }

    const auto asset_path = resolve_native_actor_asset_path(scene, item);
    if (item.actor_guid.empty()) {
        item.actor_guid = make_actor_guid(scene.route, item.name, index);
    }
    auto& actor = add_native_actor_to_scene(scene, std::move(item), asset_path);
    if (actor.actor_type != "ui_image" && actors_section.contains(actor_key + ".mechanics.physics_enabled")) {
        actor.mechanics->set_physics_enabled(
            parse_bool(actors_section.at(actor_key + ".mechanics.physics_enabled"), true));
    }
}

NativeEditorCamera make_native_camera(NativeEditorScene& scene,
                                      const IniSection* camera_section,
                                      int index) {
    const std::string prefix = "camera" + std::to_string(index);
    const auto section_value = [&](const std::string& key, const std::string& fallback) {
        if (!camera_section) {
            return fallback;
        }
        const auto it = camera_section->find(prefix + "." + key);
        return it == camera_section->end() ? fallback : it->second;
    };

    NativeEditorCamera item;
    item.name = section_value("name", scene.name + (index == 0 ? "_MainCamera" : "_Camera" + std::to_string(index)));
    item.camera_id = section_value("id", scene.route + "#camera" + std::to_string(index));
    item.deletable = parse_bool(section_value("deletable", index == 0 ? "false" : "true"), index != 0);
    auto position = parse_float3(section_value("position", "0.0, 0.0, -5.0"), {0.0f, 0.0f, -5.0f});
    auto forward = parse_float3(section_value("forward", "0.0, 0.0, 1.0"), {0.0f, 0.0f, 1.0f});
    auto world_up = parse_float3(section_value("world_up", "0.0, 1.0, 0.0"), {0.0f, 1.0f, 0.0f});
    const float fov = parse_float(section_value("fov", "45.0"), 45.0f);
    item.width = parse_int(section_value("width", "1920"), 1920);
    item.height = parse_int(section_value("height", "1080"), 1080);
    item.view_open = parse_bool(section_value("view_open", "false"));
    item.view_x = parse_int(section_value("view_x", "120"), 120);
    item.view_y = parse_int(section_value("view_y", "120"), 120);
    item.view_width = parse_int(section_value("view_width", "960"), 960);
    item.view_height = parse_int(section_value("view_height", "540"), 540);
    item.move_speed = parse_float(section_value("move_speed", "1.0"), 1.0f);

    item.engine_camera = std::make_unique<Corona::API::Camera>(position, forward, world_up, fov);
    item.engine_camera->set_size(item.width, item.height);
    item.engine_camera->set_output_mode(section_value("output_mode", "final_color"));
    item.engine_camera->set_render_backend(section_value("render_backend", "native"));
    item.engine_camera->set_vision_render_mode(section_value("vision_render_mode", "path_tracing"));
    item.engine_camera->set_view_state(item.view_open, item.view_x, item.view_y,
                                       item.view_width, item.view_height, item.move_speed);
    if (index > 0) {
        item.engine_camera->set_offscreen_capture_mode(true);
    }
    return item;
}

std::unique_ptr<NativeEditorScene> load_native_scene(const std::filesystem::path& project_root,
                                                     const std::string& scene_route) {
    const auto scene_file = resolve_project_path(project_root, scene_route);
    const auto scene_ini = read_ini_file(scene_file);

    auto scene = std::make_unique<NativeEditorScene>();
    scene->project_root = project_root;
    scene->route = scene_route;
    scene->name = ini_value(scene_ini, "base", "name", stem_utf8(scene_route));
    scene->script_path = ini_value(scene_ini, "scripts", "path");
    scene->terrain_type = ini_value(scene_ini, "terrain", "type");
    scene->terrain_path = ini_value(scene_ini, "terrain", "path");
    scene->vision_source_path = ini_value(scene_ini, "vision", "source_path");
    scene->vision_import_mode = ini_value(scene_ini, "vision", "import_mode");
    scene->sun_direction = parse_float3(
        ini_value(scene_ini, "sun", "sun_direction", "1.0, 1.0, 1.0"),
        {1.0f, 1.0f, 1.0f});
    scene->sun_enabled = parse_bool(ini_value(scene_ini, "sun", "enabled", "true"), true);
    scene->floor_grid_enabled = parse_bool(ini_value(scene_ini, "grid", "enabled", "true"), true);

    scene->engine_scene = std::make_unique<Corona::API::Scene>();
    scene->environment = std::make_unique<Corona::API::Environment>();
    apply_native_scene_environment(*scene);
    scene->engine_scene->set_environment(scene->environment.get());

    const auto actors_it = scene_ini.find("actors");
    if (actors_it != scene_ini.end()) {
        std::vector<std::string> actor_keys;
        for (const auto& [key, value] : actors_it->second) {
            const auto dot = key.find('.');
            if (dot != std::string::npos) {
                actor_keys.push_back(key.substr(0, dot));
            }
        }
        std::sort(actor_keys.begin(), actor_keys.end());
        actor_keys.erase(std::unique(actor_keys.begin(), actor_keys.end()), actor_keys.end());
        size_t index = 0;
        for (const auto& actor_key : actor_keys) {
            try {
                load_native_actor(*scene, actors_it->second, actor_key, index++);
            } catch (const std::exception& e) {
                std::cerr << "Native scene actor load skipped: " << actor_key
                          << " (" << e.what() << ")" << std::endl;
            }
        }
    }

    const auto camera_it = scene_ini.find("camera");
    int camera_count = 0;
    if (camera_it != scene_ini.end()) {
        camera_count = parse_int(camera_it->second.contains("count") ? camera_it->second.at("count") : "0", 0);
        if (camera_count <= 0) {
            for (const auto& [key, value] : camera_it->second) {
                if (key.rfind("camera", 0) == 0) {
                    const auto dot = key.find('.');
                    if (dot > 6) {
                        camera_count = std::max(camera_count, parse_int(key.substr(6, dot - 6), -1) + 1);
                    }
                }
            }
        }
    }
    if (camera_count <= 0) {
        camera_count = 1;
    }
    for (int index = 0; index < camera_count; ++index) {
        scene->cameras.push_back(make_native_camera(*scene, camera_it == scene_ini.end() ? nullptr : &camera_it->second, index));
        scene->engine_scene->add_camera(scene->cameras.back().engine_camera.get());
    }
    scene->active_camera_index = 0;
    if (camera_it != scene_ini.end()) {
        const auto active_id = camera_it->second.contains("active_id") ? camera_it->second.at("active_id") : "";
        for (size_t index = 0; index < scene->cameras.size(); ++index) {
            if (scene->cameras[index].camera_id == active_id || scene->cameras[index].name == active_id) {
                scene->active_camera_index = index;
                break;
            }
        }
    }
    if (!scene->cameras.empty()) {
        scene->engine_scene->set_active_camera(scene->cameras[scene->active_camera_index].engine_camera.get());
    }
    scene->engine_scene->set_simulation_enabled(true);
    scene->engine_scene->set_enabled(true);
    return scene;
}

NativeEditorScene* ensure_native_editor_scene(const std::string& project_path_arg = {}) {
    auto& state = native_editor_state();
    const auto project_path = normalize_route(project_path_arg.empty()
                                                  ? resolve_active_project_path(nlohmann::json::array())
                                                  : project_path_arg);
    if (project_path.empty()) {
        throw std::runtime_error("No active project path for native editor initialization");
    }
    const auto project_root = path_from_utf8(project_path);
    const auto project_ini = read_ini_file(project_root / "project.ini");
    const auto scene_route = choose_single_scene_route(project_root, project_ini);
    if (scene_route.empty()) {
        throw std::runtime_error("No entrance scene found in project.ini");
    }

    if (!state.scene || state.project_path != project_path || state.scene->route != scene_route) {
        state.scene = load_native_scene(project_root, scene_route);
        state.project_path = project_path;
    }
    return state.scene.get();
}

NativeEditorScene* reload_native_editor_scene(const std::string& project_path_arg,
                                              const std::string& scene_route_arg) {
    auto& state = native_editor_state();
    const auto project_path = normalize_route(project_path_arg.empty()
                                                  ? resolve_active_project_path(nlohmann::json::array())
                                                  : project_path_arg);
    if (project_path.empty()) {
        throw std::runtime_error("No active project path for native editor reload");
    }

    const auto project_root = path_from_utf8(project_path);
    const auto project_ini = read_ini_file(project_root / "project.ini");
    auto scene_route = normalize_route(scene_route_arg);
    if (scene_route.empty()) {
        scene_route = state.scene ? state.scene->route : choose_single_scene_route(project_root, project_ini);
    }
    if (scene_route.empty()) {
        throw std::runtime_error("No scene route for native editor reload");
    }

    state.scene = load_native_scene(project_root, scene_route);
    state.project_path = project_path;
    return state.scene.get();
}

nlohmann::json make_on_init_payload(const NativeEditorScene& scene) {
    return {
        {"scenes", nlohmann::json::array({{
            {"path", scene.route},
            {"name", scene.name},
        }})},
        {"active_index", 0},
        {"path", scene.route},
        {"name", scene.name},
        {"single_scene", true},
    };
}

nlohmann::json camera_to_json(const NativeEditorCamera& camera) {
    nlohmann::json item;
    item["id"] = camera.camera_id;
    item["camera_id"] = camera.camera_id;
    item["name"] = camera.name;
    item["handle"] = camera.engine_camera ? camera.engine_camera->get_handle() : 0;
    item["position"] = camera.engine_camera ? camera.engine_camera->get_position() : std::array<float, 3>{0.0f, 0.0f, -5.0f};
    item["forward"] = camera.engine_camera ? camera.engine_camera->get_forward() : std::array<float, 3>{0.0f, 0.0f, 1.0f};
    item["world_up"] = camera.engine_camera ? camera.engine_camera->get_world_up() : std::array<float, 3>{0.0f, 1.0f, 0.0f};
    item["fov"] = camera.engine_camera ? camera.engine_camera->get_fov() : 45.0f;
    item["width"] = camera.width;
    item["height"] = camera.height;
    item["output_mode"] = camera.engine_camera ? camera.engine_camera->get_output_mode() : "final_color";
    item["render_backend"] = camera.engine_camera ? camera.engine_camera->get_render_backend() : "native";
    item["vision_render_mode"] = camera.engine_camera ? camera.engine_camera->get_vision_render_mode() : "path_tracing";
    item["shadow_cascade_debug"] = camera.engine_camera ? camera.engine_camera->get_shadow_cascade_debug() : false;
    item["move_speed"] = camera.move_speed;
    item["view_open"] = camera.view_open;
    item["view_x"] = camera.view_x;
    item["view_y"] = camera.view_y;
    item["view_width"] = camera.view_width;
    item["view_height"] = camera.view_height;
    item["deletable"] = camera.deletable;
    return item;
}

std::optional<std::array<float, 6>> native_actor_local_aabb(const NativeEditorActor& actor);
std::optional<std::array<float, 6>> native_actor_world_aabb(const NativeEditorActor& actor);
nlohmann::json aabb_to_json(const std::array<float, 6>& aabb);

nlohmann::json actor_to_json(const NativeEditorScene& scene, const NativeEditorActor& actor) {
    nlohmann::json item;
    item["name"] = actor.name;
    item["actor_guid"] = actor.actor_guid;
    item["handle"] = actor.engine_actor ? actor.engine_actor->get_handle() : 0;
    item["path"] = actor.route;
    item["route"] = actor.route;
    item["scene"] = scene.route;
    item["type"] = actor_file_extension(actor.route);
    item["model"] = actor.route;
    item["model_dependencies"] = nlohmann::json::array();
    item["actor_type"] = actor.actor_type;
    if (actor.actor_type == "audio") {
        item["audio_resource_id"] = std::to_string(actor.audio_resource_id);
    }
    item["collision"] = actor.mechanics ? actor.mechanics->get_collision_enabled() : true;
    item["visible"] = actor.optics ? actor.optics->get_visible() : true;
    item["script"] = "";
    item["follow_camera"] = actor.follow_camera;
    item["render_space"] = actor.follow_camera ? "ui" : "scene";
    item["geometry"] = {
        {"position", actor.geometry ? actor.geometry->get_position() : actor.position},
        {"rotation", actor.geometry ? actor.geometry->get_rotation() : actor.rotation},
        {"scale", actor.geometry ? actor.geometry->get_scale() : actor.scale},
    };
    const auto local_aabb = native_actor_local_aabb(actor);
    const auto world_aabb = native_actor_world_aabb(actor);
    item["local_aabb"] = local_aabb ? aabb_to_json(*local_aabb) : nlohmann::json(nullptr);
    item["world_aabb"] = world_aabb ? aabb_to_json(*world_aabb) : nlohmann::json(nullptr);
    item["aabb"] = item["world_aabb"];
    item["bounds_ready"] = static_cast<bool>(world_aabb);
    item["size"] = world_aabb
        ? nlohmann::json::array({
            (*world_aabb)[3] - (*world_aabb)[0],
            (*world_aabb)[4] - (*world_aabb)[1],
            (*world_aabb)[5] - (*world_aabb)[2],
        })
        : nlohmann::json::array({0.0f, 0.0f, 0.0f});
    if (actor.mechanics) {
        const auto [linear_x, linear_y, linear_z] = actor.mechanics->get_linear_lock();
        const auto [angular_x, angular_y, angular_z] = actor.mechanics->get_angular_lock();
        item["mechanics"] = {
            {"mass", actor.mechanics->get_mass()},
            {"restitution", actor.mechanics->get_restitution()},
            {"damping", actor.mechanics->get_damping()},
            {"physics_enabled", actor.mechanics->get_physics_enabled()},
            {"linear_lock", {linear_x, linear_y, linear_z}},
            {"angular_lock", {angular_x, angular_y, angular_z}},
        };
    }
    item["camera_lock"] = {
        {"lock_to_camera", false},
        {"position_offset", {0.0f, 0.0f, 2.0f}},
        {"rotation_offset", {0.0f, 0.0f, 0.0f}},
    };
    return item;
}

nlohmann::json scene_to_json(const NativeEditorScene& scene) {
    nlohmann::json cameras = nlohmann::json::array();
    for (const auto& camera : scene.cameras) {
        cameras.push_back(camera_to_json(camera));
    }
    nlohmann::json actors = nlohmann::json::array();
    for (const auto& actor : scene.actors) {
        actors.push_back(actor_to_json(scene, actor));
    }
    const auto active_index = scene.cameras.empty()
                                  ? 0
                                  : std::min(scene.active_camera_index, scene.cameras.size() - 1);
    const auto active_camera = scene.cameras.empty()
                                   ? nlohmann::json(nullptr)
                                   : camera_to_json(scene.cameras[active_index]);
    return {
        {"id", scene.route},
        {"scene_id", scene.route},
        {"name", scene.name},
        {"active_camera_id", active_camera.is_null() ? "" : active_camera.value("camera_id", "")},
        {"active_camera_name", active_camera.is_null() ? "" : active_camera.value("name", "")},
        {"camera", active_camera},
        {"cameras", cameras},
        {"sun", {{"enabled", scene.sun_enabled}, {"direction", scene.sun_direction}}},
        {"grid", {{"enabled", scene.floor_grid_enabled}}},
        {"terrain", {{"path", scene.terrain_path}, {"type", scene.terrain_type}}},
        {"vision", {
            {"source_path", scene.vision_source_path},
            {"import_mode", scene.vision_import_mode},
            {"bindings", nlohmann::json::array()},
            {"unsupported_shapes", nlohmann::json::array()},
        }},
        {"script", scene.script_path},
        {"actors", actors},
    };
}

NativeEditorActor* find_native_actor(NativeEditorScene& scene, const std::string& actor_name) {
    for (auto& actor : scene.actors) {
        if (actor.name == actor_name || actor.actor_guid == actor_name ||
            (actor.engine_actor && std::to_string(actor.engine_actor->get_handle()) == actor_name))
        {
            return &actor;
        }
    }
    return nullptr;
}

NativeEditorCamera* find_native_camera(NativeEditorScene& scene, const std::string& camera_name) {
    if (camera_name.empty() && !scene.cameras.empty()) {
        return &scene.cameras[std::min(scene.active_camera_index, scene.cameras.size() - 1)];
    }
    for (auto& camera : scene.cameras) {
        if (camera.name == camera_name || camera.camera_id == camera_name ||
            (camera.engine_camera && std::to_string(camera.engine_camera->get_handle()) == camera_name))
        {
            return &camera;
        }
    }
    return nullptr;
}

bool aabb_has_usable_extent(const std::array<float, 6>& aabb) {
    bool has_extent = false;
    for (size_t axis = 0; axis < 3; ++axis) {
        const float min_v = aabb[axis];
        const float max_v = aabb[axis + 3];
        if (!std::isfinite(min_v) || !std::isfinite(max_v) || max_v < min_v) {
            return false;
        }
        if (std::abs(max_v - min_v) > 1e-5f) {
            has_extent = true;
        }
    }
    return has_extent;
}

std::optional<std::array<float, 6>> native_actor_local_aabb(const NativeEditorActor& actor) {
    if (!actor.geometry) {
        return std::nullopt;
    }
    const auto local = actor.geometry->get_aabb();
    if (local.size() < 6) {
        return std::nullopt;
    }
    std::array<float, 6> result{};
    for (size_t index = 0; index < 6; ++index) {
        result[index] = local[index];
    }
    if (!aabb_has_usable_extent(result)) {
        return std::nullopt;
    }
    return result;
}

std::optional<std::array<float, 6>> native_actor_world_aabb(const NativeEditorActor& actor) {
    const auto local = native_actor_local_aabb(actor);
    if (!local || !actor.geometry) {
        return std::nullopt;
    }
    const auto position = actor.geometry->get_position();
    const auto scale = actor.geometry->get_scale();
    std::array<float, 6> result{};
    for (size_t axis = 0; axis < 3; ++axis) {
        const auto a = position[axis] + (*local)[axis] * scale[axis];
        const auto b = position[axis] + (*local)[axis + 3] * scale[axis];
        result[axis] = std::min(a, b);
        result[axis + 3] = std::max(a, b);
    }
    if (!aabb_has_usable_extent(result)) {
        return std::nullopt;
    }
    return result;
}

nlohmann::json aabb_to_json(const std::array<float, 6>& aabb) {
    return nlohmann::json::array({
        aabb[0], aabb[1], aabb[2], aabb[3], aabb[4], aabb[5],
    });
}

std::optional<std::array<float, 6>> native_scene_world_aabb(const NativeEditorScene& scene) {
    std::optional<std::array<float, 6>> aggregate;
    for (const auto& actor : scene.actors) {
        const auto actor_aabb = native_actor_world_aabb(actor);
        if (!actor_aabb) {
            continue;
        }
        if (!aggregate) {
            aggregate = *actor_aabb;
            continue;
        }
        for (size_t axis = 0; axis < 3; ++axis) {
            (*aggregate)[axis] = std::min((*aggregate)[axis], (*actor_aabb)[axis]);
            (*aggregate)[axis + 3] = std::max((*aggregate)[axis + 3], (*actor_aabb)[axis + 3]);
        }
    }
    return aggregate;
}

std::string json_string_value(const nlohmann::json& object,
                              std::initializer_list<const char*> keys) {
    if (!object.is_object()) {
        return {};
    }
    for (const char* key : keys) {
        const auto it = object.find(key);
        if (it != object.end() && it->is_string()) {
            const auto value = trim_ascii(it->get<std::string>());
            if (!value.empty()) {
                return value;
            }
        }
    }
    return {};
}

float json_float_at(const nlohmann::json& value, size_t index, float fallback = 0.0f) {
    if (!value.is_array() || index >= value.size() || !value[index].is_number()) {
        return fallback;
    }
    return value[index].get<float>();
}

std::optional<std::array<float, 3>> json_float3_value(const nlohmann::json& value) {
    if (!value.is_array() || value.size() < 3) {
        return std::nullopt;
    }
    return std::array<float, 3>{
        json_float_at(value, 0, 0.0f),
        json_float_at(value, 1, 0.0f),
        json_float_at(value, 2, 0.0f),
    };
}

std::optional<std::array<float, 3>> actor_data_float3(const nlohmann::json& actor_data,
                                                       const char* key) {
    if (!actor_data.is_object()) {
        return std::nullopt;
    }
    const auto top_it = actor_data.find(key);
    if (top_it != actor_data.end()) {
        if (auto value = json_float3_value(*top_it)) {
            return value;
        }
    }
    const auto geometry_it = actor_data.find("geometry");
    if (geometry_it != actor_data.end() && geometry_it->is_object()) {
        const auto nested_it = geometry_it->find(key);
        if (nested_it != geometry_it->end()) {
            return json_float3_value(*nested_it);
        }
    }
    return std::nullopt;
}

std::optional<float> actor_data_float(const nlohmann::json& actor_data,
                                      std::initializer_list<const char*> keys) {
    if (!actor_data.is_object()) {
        return std::nullopt;
    }
    for (const char* key : keys) {
        const auto it = actor_data.find(key);
        if (it != actor_data.end()) {
            if (it->is_number()) {
                return it->get<float>();
            }
            if (it->is_string()) {
                try {
                    return std::stof(it->get<std::string>());
                } catch (...) {
                    return std::nullopt;
                }
            }
        }
    }
    return std::nullopt;
}

int json_int_value(const nlohmann::json& object, const char* key, int fallback) {
    if (!object.is_object()) {
        return fallback;
    }
    const auto it = object.find(key);
    if (it == object.end()) {
        return fallback;
    }
    if (it->is_number_integer()) {
        return it->get<int>();
    }
    if (it->is_string()) {
        try {
            return std::stoi(it->get<std::string>());
        } catch (...) {
            return fallback;
        }
    }
    return fallback;
}

float json_float_value(const nlohmann::json& object, const char* key, float fallback) {
    if (!object.is_object()) {
        return fallback;
    }
    const auto it = object.find(key);
    if (it == object.end()) {
        return fallback;
    }
    if (it->is_number()) {
        return it->get<float>();
    }
    if (it->is_string()) {
        try {
            return std::stof(it->get<std::string>());
        } catch (...) {
            return fallback;
        }
    }
    return fallback;
}

NativeEditorCamera* ensure_native_editor_camera(NativeEditorScene& scene,
                                                const std::string& requested_name,
                                                const nlohmann::json& camera_data) {
    const auto camera_name = trim_ascii(requested_name.empty()
                                            ? json_string_value(camera_data, {"camera_name", "name"})
                                            : requested_name);
    auto* existing = find_native_camera(scene, camera_name);
    if (existing) {
        return existing;
    }

    const auto name = camera_name.empty() ? "vlm_review_camera" : camera_name;
    NativeEditorCamera item;
    item.name = name;
    item.camera_id = json_string_value(camera_data, {"camera_id", "id"});
    if (item.camera_id.empty()) {
        item.camera_id = scene.route + "#" + name;
    }
    item.deletable = parse_bool(json_string_value(camera_data, {"deletable"}), false);
    item.width = std::max(json_int_value(camera_data, "width", 512), 1);
    item.height = std::max(json_int_value(camera_data, "height", 512), 1);
    item.view_open = false;
    item.view_width = item.width;
    item.view_height = item.height;
    item.move_speed = json_float_value(camera_data, "move_speed", 1.0f);

    const auto position = camera_data.contains("position")
                              ? json_float3_value(camera_data["position"]).value_or(std::array<float, 3>{0.0f, 0.0f, -5.0f})
                              : std::array<float, 3>{0.0f, 0.0f, -5.0f};
    const auto forward = camera_data.contains("forward")
                             ? json_float3_value(camera_data["forward"]).value_or(std::array<float, 3>{0.0f, 0.0f, 1.0f})
                             : std::array<float, 3>{0.0f, 0.0f, 1.0f};
    const auto world_up = camera_data.contains("world_up")
                              ? json_float3_value(camera_data["world_up"]).value_or(std::array<float, 3>{0.0f, 1.0f, 0.0f})
                              : std::array<float, 3>{0.0f, 1.0f, 0.0f};
    const auto fov = json_float_value(camera_data, "fov", 45.0f);

    item.engine_camera = std::make_unique<Corona::API::Camera>(position, forward, world_up, fov);
    item.engine_camera->set_size(item.width, item.height);
    item.engine_camera->set_output_mode(json_string_value(camera_data, {"output_mode"}).empty()
                                            ? "base_color"
                                            : json_string_value(camera_data, {"output_mode"}));
    item.engine_camera->set_render_backend(json_string_value(camera_data, {"render_backend"}).empty()
                                               ? "native"
                                               : json_string_value(camera_data, {"render_backend"}));
    item.engine_camera->set_vision_render_mode(json_string_value(camera_data, {"vision_render_mode"}).empty()
                                                   ? "path_tracing"
                                                   : json_string_value(camera_data, {"vision_render_mode"}));
    item.engine_camera->set_view_state(false, item.view_x, item.view_y,
                                       item.view_width, item.view_height, item.move_speed);
    item.engine_camera->set_offscreen_capture_mode(true);
    item.engine_camera->set_surface(0);

    scene.cameras.push_back(std::move(item));
    auto& camera = scene.cameras.back();
    if (scene.engine_scene && camera.engine_camera) {
        scene.engine_scene->add_camera(camera.engine_camera.get());
    }
    return &camera;
}

bool json_bool_at(const nlohmann::json& value, size_t index, bool fallback = false) {
    if (!value.is_array() || index >= value.size()) {
        return fallback;
    }
    if (value[index].is_boolean()) {
        return value[index].get<bool>();
    }
    if (value[index].is_number_integer()) {
        return value[index].get<int>() != 0;
    }
    if (value[index].is_string()) {
        return parse_bool(value[index].get<std::string>(), fallback);
    }
    return fallback;
}

std::optional<bool> actor_data_bool(const nlohmann::json& actor_data,
                                    std::initializer_list<const char*> keys) {
    if (!actor_data.is_object()) {
        return std::nullopt;
    }
    for (const char* key : keys) {
        const auto it = actor_data.find(key);
        if (it != actor_data.end()) {
            if (it->is_boolean()) {
                return it->get<bool>();
            }
            if (it->is_number_integer()) {
                return it->get<int>() != 0;
            }
            if (it->is_string()) {
                return parse_bool(it->get<std::string>());
            }
        }
    }
    const auto mechanics_it = actor_data.find("mechanics");
    if (mechanics_it != actor_data.end() && mechanics_it->is_object()) {
        return actor_data_bool(*mechanics_it, keys);
    }
    return std::nullopt;
}

float arg_float_value(const nlohmann::json& args, size_t index, float fallback = 0.0f) {
    if (!args.is_array() || index >= args.size()) {
        return fallback;
    }
    const auto& value = args[index];
    try {
        if (value.is_number()) {
            return value.get<float>();
        }
        if (value.is_string()) {
            return std::stof(value.get<std::string>());
        }
    } catch (...) {
    }
    return fallback;
}

std::string json_string_at(const nlohmann::json& value,
                           size_t index,
                           std::string fallback = {}) {
    if (!value.is_array() || index >= value.size()) {
        return fallback;
    }
    if (value[index].is_string()) {
        return value[index].get<std::string>();
    }
    return value[index].dump();
}

NativeResult create_native_editor_actor(const std::string& scene_route_arg,
                                        const std::string& source_path,
                                        std::string actor_type,
                                        const nlohmann::json& actor_data) {
    const auto scene_route = normalize_route(scene_route_arg);
    actor_type = normalize_route(actor_type.empty() ? "model" : actor_type);
    if (actor_type.empty()) {
        actor_type = "model";
    }
    if (source_path.empty()) {
        return native_failure("create_actor source path is empty", 2);
    }

    auto* scene = ensure_native_editor_scene();
    if (!scene_route.empty() && scene_route != scene->route) {
        scene = reload_native_editor_scene("", scene_route);
    }

    auto apply_actor_data_to_existing = [&](NativeEditorActor& target) {
        if (auto position = actor_data_float3(actor_data, "position")) {
            target.position = *position;
            if (target.geometry) {
                target.geometry->set_position(*position);
            }
        }
        if (auto rotation = actor_data_float3(actor_data, "rotation")) {
            target.rotation = *rotation;
            if (target.geometry) {
                target.geometry->set_rotation(*rotation);
            }
        }
        if (auto scale = actor_data_float3(actor_data, "scale")) {
            target.scale = *scale;
            if (target.geometry) {
                target.geometry->set_scale(*scale);
            }
        }
        if (auto follow_camera = actor_data_bool(actor_data, {"follow_camera"})) {
            target.follow_camera = *follow_camera;
        }
        if (auto physics_enabled = actor_data_bool(actor_data, {"physics_enabled"})) {
            if (target.mechanics) {
                target.mechanics->set_physics_enabled(*physics_enabled);
            }
        }
    };

    NativeEditorActor item;
    item.actor_type = actor_type;
    item.route = route_for_project_storage(scene->project_root, source_path);
    const auto preferred_name = json_string_value(
        actor_data, {"actor_name", "name", "alias", "model_name", "object_id", "target"});
    const auto preferred_guid = json_string_value(actor_data, {"actor_guid", "guid"});
    if (auto skip_if_exists = actor_data_bool(actor_data, {"skip_if_exists"})) {
        if (*skip_if_exists) {
            NativeEditorActor* existing = nullptr;
            if (!preferred_guid.empty()) {
                existing = find_native_actor(*scene, preferred_guid);
            }
            if (existing == nullptr && !preferred_name.empty()) {
                existing = find_native_actor(*scene, preferred_name);
            }
            if (existing != nullptr) {
                if (actor_data_bool(actor_data, {"update_if_exists"}).value_or(false)) {
                    apply_actor_data_to_existing(*existing);
                    persist_native_scene_actors(*scene);
                }
                return native_success({
                    {"status", "success"},
                    {"scene", scene->route},
                    {"actor", actor_to_json(*scene, *existing)},
                    {"existed", true},
                });
            }
        }
    }
    item.name = unique_actor_name(*scene, preferred_name.empty() ? stem_utf8(item.route) : preferred_name);
    item.actor_guid = preferred_guid.empty()
        ? make_actor_guid(scene->route, item.name, scene->actors.size())
        : preferred_guid;
    item.follow_camera = item.actor_type == "ui_image";
    item.position = {0.0f, 0.0f, 0.0f};
    item.rotation = {0.0f, 0.0f, 0.0f};
    item.scale = {1.0f, 1.0f, 1.0f};

    if (item.actor_type == "actor" && to_lower_ascii(actor_file_extension(item.route)) == "actor") {
        const auto actor_file = resolve_project_path(scene->project_root, item.route);
        const auto actor_ini = read_ini_file(actor_file);
        const auto configured_name = ini_value(actor_ini, "base", "name");
        if (preferred_name.empty() && !configured_name.empty()) {
            item.name = unique_actor_name(*scene, configured_name);
            item.actor_guid = preferred_guid.empty()
                ? make_actor_guid(scene->route, item.name, scene->actors.size())
                : preferred_guid;
        }
        item.follow_camera = parse_bool(ini_value(actor_ini, "base", "follow_camera", "false"));
        item.position = parse_float3(
            ini_value(actor_ini, "geometry", "position", "0.0, 0.0, 0.0"),
            {0.0f, 0.0f, 0.0f});
        item.rotation = parse_float3(
            ini_value(actor_ini, "geometry", "rotation", "0.0, 0.0, 0.0"),
            {0.0f, 0.0f, 0.0f});
        item.scale = parse_float3(
            ini_value(actor_ini, "geometry", "scale", "1.0, 1.0, 1.0"),
            {1.0f, 1.0f, 1.0f});
    }

    if (auto position = actor_data_float3(actor_data, "position")) {
        item.position = *position;
    }
    if (auto rotation = actor_data_float3(actor_data, "rotation")) {
        item.rotation = *rotation;
    }
    if (auto scale = actor_data_float3(actor_data, "scale")) {
        item.scale = *scale;
    }
    if (auto follow_camera = actor_data_bool(actor_data, {"follow_camera"})) {
        item.follow_camera = *follow_camera;
    }

    // 音频物体：从 actor_data 解析绑定的音频资源 id（JS 以字符串传递，避免精度丢失）。
    {
        const auto rid_str = json_string_value(actor_data, {"audio_resource_id", "resource_id"});
        if (!rid_str.empty()) {
            try {
                item.audio_resource_id = std::stoull(rid_str);
            } catch (const std::exception&) {
                item.audio_resource_id = 0;
            }
        }
    }

    auto asset_path = resolve_native_actor_asset_path(*scene, item);
    if (item.actor_guid.empty()) {
        item.actor_guid = make_actor_guid(scene->route, item.name, scene->actors.size());
    }
    auto& actor = add_native_actor_to_scene(*scene, std::move(item), asset_path);
    if (auto ground_align = actor_data_bool(actor_data, {"ground_align"})) {
        if (*ground_align && actor.geometry) {
            const auto ground_y = actor_data_float(actor_data, {"ground_y"}).value_or(0.0f);
            const auto aabb = actor.geometry->get_aabb();
            auto position = actor.geometry->get_position();
            const auto scale = actor.geometry->get_scale();
            if (aabb.size() >= 6) {
                const auto min_y_world = position[1] + aabb[1] * scale[1];
                position[1] += ground_y - min_y_world;
                actor.position = position;
                actor.geometry->set_position(position);
            }
        }
    }
    if (auto physics_enabled = actor_data_bool(actor_data, {"physics_enabled"})) {
        if (actor.mechanics) {
            actor.mechanics->set_physics_enabled(*physics_enabled);
        }
    }
    persist_native_scene_actors(*scene);
    return native_success({
        {"status", "success"},
        {"scene", scene->route},
        {"actor", actor_to_json(*scene, actor)},
    });
}

std::optional<std::array<float, 3>> transform_float3_value(const nlohmann::json& data,
                                                           const std::string& key,
                                                           const std::string& alias = {}) {
    if (!data.is_object()) {
        return std::nullopt;
    }
    if (data.contains(key)) {
        if (auto value = json_float3_value(data[key])) {
            return value;
        }
    }
    if (!alias.empty() && data.contains(alias)) {
        if (auto value = json_float3_value(data[alias])) {
            return value;
        }
    }
    const auto geo = data.find("geometry");
    if (geo != data.end() && geo->is_object()) {
        if (geo->contains(key)) {
            if (auto value = json_float3_value((*geo)[key])) {
                return value;
            }
        }
        if (!alias.empty() && geo->contains(alias)) {
            if (auto value = json_float3_value((*geo)[alias])) {
                return value;
            }
        }
    }
    return std::nullopt;
}

NativeResult remove_native_editor_actor(const std::string& scene_route_arg,
                                        const std::string& actor_name) {
    if (trim_ascii(actor_name).empty()) {
        return native_failure("Actor name cannot be empty", 2);
    }

    auto* scene = ensure_native_editor_scene();
    const auto scene_route = normalize_route(scene_route_arg);
    if (!scene_route.empty() && scene_route != scene->route) {
        scene = reload_native_editor_scene("", scene_route);
    }

    auto it = std::find_if(scene->actors.begin(), scene->actors.end(), [&](const NativeEditorActor& actor) {
        if (actor.name == actor_name || actor.actor_guid == actor_name) {
            return true;
        }
        return actor.engine_actor && std::to_string(actor.engine_actor->get_handle()) == actor_name;
    });
    if (it == scene->actors.end()) {
        return native_failure("Actor not found: " + actor_name, 2);
    }

    const auto removed_name = it->name;
    const auto removed_guid = it->actor_guid;
    if (scene->engine_scene && it->engine_actor) {
        scene->engine_scene->remove_actor(it->engine_actor.get());
    }
    scene->actors.erase(it);
    persist_native_scene_actors(*scene);

    return native_success({
        {"status", "success"},
        {"scene", scene->route},
        {"actor", removed_name},
        {"actor_guid", removed_guid},
    });
}

NativeResult set_native_editor_actor_transform(const std::string& scene_route_arg,
                                               const std::string& actor_name,
                                               const nlohmann::json& transform_data) {
    if (trim_ascii(actor_name).empty()) {
        return native_failure("Actor name cannot be empty", 2);
    }
    auto* scene = ensure_native_editor_scene();
    const auto scene_route = normalize_route(scene_route_arg);
    if (!scene_route.empty() && scene_route != scene->route) {
        scene = reload_native_editor_scene("", scene_route);
    }

    auto* actor = find_native_actor(*scene, actor_name);
    if (!actor && actor_name.rfind("__shell_", 0) != 0) {
        actor = find_native_actor(*scene, "__shell_" + actor_name);
    }
    if (!actor) {
        return native_failure("Actor not found: " + actor_name, 2);
    }

    const auto position = transform_float3_value(transform_data, "position", "pos");
    const auto rotation = transform_float3_value(transform_data, "rotation", "rot");
    const auto scale = transform_float3_value(transform_data, "scale", "scl");
    if (!position && !rotation && !scale) {
        return native_failure("Transform must include position, rotation, or scale", 2);
    }

    if (position) {
        actor->position = *position;
        if (actor->geometry) {
            actor->geometry->set_position(*position);
        }
    }
    if (rotation) {
        actor->rotation = *rotation;
        if (actor->geometry) {
            actor->geometry->set_rotation(*rotation);
        }
    }
    if (scale) {
        actor->scale = *scale;
        if (actor->geometry) {
            actor->geometry->set_scale(*scale);
        }
    }
    persist_native_scene_actors(*scene);
    return native_success({
        {"status", "success"},
        {"scene", scene->route},
        {"actor", actor_to_json(*scene, *actor)},
    });
}

NativeResult apply_actor_operation(NativeEditorScene& scene,
                                   NativeEditorActor& actor,
                                   const std::string& operation,
                                   const nlohmann::json& vector) {
    if (operation == "SetMass") {
        if (actor.mechanics) actor.mechanics->set_mass(json_float_at(vector, 0, 1.0f));
    } else if (operation == "SetRestitution") {
        if (actor.mechanics) actor.mechanics->set_restitution(json_float_at(vector, 0, 0.8f));
    } else if (operation == "SetDamping") {
        if (actor.mechanics) actor.mechanics->set_damping(json_float_at(vector, 0, 0.99f));
    } else if (operation == "SetPhysicsEnabled") {
        if (actor.mechanics) actor.mechanics->set_physics_enabled(json_bool_at(vector, 0, true));
    } else if (operation == "SetCollision") {
        const auto value = json_string_at(vector, 0, "true");
        if (actor.mechanics) actor.mechanics->set_collision_enabled(
            value != "none" && value != "false" && value != "0");
    } else if (operation == "SetVisible") {
        if (actor.optics) actor.optics->set_visible(json_bool_at(vector, 0, true));
    } else if (operation == "SetFollowCamera") {
        actor.follow_camera = json_bool_at(vector, 0, false);
        if (actor.engine_actor) actor.engine_actor->set_follow_camera(actor.follow_camera);
    } else if (operation == "SetLinearLock") {
        if (actor.mechanics) {
            actor.mechanics->set_linear_lock(json_bool_at(vector, 0),
                                             json_bool_at(vector, 1),
                                             json_bool_at(vector, 2));
        }
    } else if (operation == "SetAngularLock") {
        if (actor.mechanics) {
            actor.mechanics->set_angular_lock(json_bool_at(vector, 0),
                                              json_bool_at(vector, 1),
                                              json_bool_at(vector, 2));
        }
    } else if (operation == "SetCameraLock" ||
               operation == "SetCameraLockOffset" ||
               operation == "SetCameraLockRotation") {
        // Camera-lock metadata is not yet stored natively; keep the RPC shape
        // alive so the details panel remains usable while native persistence catches up.
    } else {
        return native_failure("Unsupported actor operation: " + operation, 2);
    }

    return native_success({
        {"scene", scene.route},
        {"actor", actor.name},
        {"operation", operation},
        {"vector", vector},
    });
}

void emit_actor_change(const NativeContext& context,
                       const NativeEditorScene& scene,
                       const NativeEditorActor& actor) {
    if (!context.frame) {
        return;
    }
    const std::string script =
        "window.__coronaEmit&&window.__coronaEmit(" +
        nlohmann::json("actor-change").dump() + "," +
        nlohmann::json(actor.actor_type).dump() + "," +
        nlohmann::json(scene.route).dump() + "," +
        nlohmann::json(actor.name).dump() + ");";
    context.frame->ExecuteJavaScript(script, context.frame->GetURL(), 0);
}

nlohmann::json active_project_info_json() {
    auto& state = native_editor_state();
    const auto project_path = normalize_route(
        state.project_path.empty() ? resolve_active_project_path(nlohmann::json::array())
                                   : state.project_path);
    if (project_path.empty()) {
        throw std::runtime_error("No active project path");
    }

    const auto project_root = path_from_utf8(project_path);
    const auto project_ini = read_ini_file(project_root / "project.ini");
    const auto project = project_ini.contains("project") ? project_ini.at("project") : IniSection{};
    const auto value = [&](const std::string& key, const std::string& fallback = {}) {
        const auto it = project.find(to_lower_ascii(key));
        return it == project.end() ? fallback : it->second;
    };

    return {
        {"name", value("name", project_root.filename().string())},
        {"mode", value("mode", "3d")},
        {"entrance_scene", value("entrance_scene", choose_single_scene_route(project_root, project_ini))},
        {"core_version", value("core_version", value("version", ""))},
        {"create_time", value("create_time", value("created_at", ""))},
        {"last_opened", value("last_opened", value("last_open_time", ""))},
        {"project_path", path_to_utf8(project_root)},
    };
}

std::string detect_hostname_ipv4() {
    char host_name[256] = {};
    if (gethostname(host_name, sizeof(host_name)) != 0) {
        return "127.0.0.1";
    }

    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_DGRAM;
    addrinfo* result = nullptr;
    if (getaddrinfo(host_name, nullptr, &hints, &result) != 0) {
        return "127.0.0.1";
    }

    std::string fallback = "127.0.0.1";
    for (addrinfo* it = result; it; it = it->ai_next) {
        auto* addr = reinterpret_cast<sockaddr_in*>(it->ai_addr);
        char ip[INET_ADDRSTRLEN] = {};
        if (!inet_ntop(AF_INET, &addr->sin_addr, ip, sizeof(ip))) {
            continue;
        }
        std::string candidate(ip);
        if (is_usable_ipv4(candidate)) {
            fallback = candidate;
            break;
        }
    }
    freeaddrinfo(result);
    return fallback;
}

#ifdef _WIN32
std::string wide_to_utf8(const wchar_t* value) {
    if (!value || !*value) {
        return {};
    }
    const int size = WideCharToMultiByte(CP_UTF8, 0, value, -1, nullptr, 0, nullptr, nullptr);
    if (size <= 1) {
        return {};
    }
    std::string result(static_cast<size_t>(size - 1), '\0');
    WideCharToMultiByte(CP_UTF8, 0, value, -1, result.data(), size, nullptr, nullptr);
    return result;
}

std::string ipv4_from_sockaddr(const sockaddr* address) {
    if (!address || address->sa_family != AF_INET) {
        return {};
    }
    const auto* addr = reinterpret_cast<const sockaddr_in*>(address);
    char ip[INET_ADDRSTRLEN] = {};
    if (!inet_ntop(AF_INET, &addr->sin_addr, ip, sizeof(ip))) {
        return {};
    }
    return std::string(ip);
}

bool adapter_has_ipv4_gateway(const IP_ADAPTER_ADDRESSES* adapter) {
    for (auto* gateway = adapter ? adapter->FirstGatewayAddress : nullptr; gateway; gateway = gateway->Next) {
        if (gateway->Address.lpSockaddr &&
            gateway->Address.lpSockaddr->sa_family == AF_INET) {
            return true;
        }
    }
    return false;
}
#endif

std::string detect_wlan_ipv4() {
#ifdef _WIN32
    WSADATA wsa{};
    const bool started = WSAStartup(MAKEWORD(2, 2), &wsa) == 0;
    std::string wlan_with_gateway;
    std::string wlan_fallback;
    std::string gateway_fallback;
    std::string any_fallback;

    ULONG buffer_size = 15000;
    std::vector<unsigned char> buffer(buffer_size);
    ULONG flags = GAA_FLAG_SKIP_ANYCAST |
                  GAA_FLAG_SKIP_MULTICAST |
                  GAA_FLAG_SKIP_DNS_SERVER |
                  GAA_FLAG_INCLUDE_GATEWAYS;
    ULONG result = GetAdaptersAddresses(
        AF_INET, flags, nullptr,
        reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),
        &buffer_size);
    if (result == ERROR_BUFFER_OVERFLOW) {
        buffer.resize(buffer_size);
        result = GetAdaptersAddresses(
            AF_INET, flags, nullptr,
            reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data()),
            &buffer_size);
    }

    if (result == NO_ERROR) {
        auto* adapters = reinterpret_cast<IP_ADAPTER_ADDRESSES*>(buffer.data());
        for (auto* adapter = adapters; adapter; adapter = adapter->Next) {
            if (adapter->OperStatus != IfOperStatusUp ||
                adapter->IfType == IF_TYPE_SOFTWARE_LOOPBACK) {
                continue;
            }

            std::string adapter_name = wide_to_utf8(adapter->FriendlyName);
            if (adapter->AdapterName) {
                adapter_name += " ";
                adapter_name += adapter->AdapterName;
            }
            const bool is_wlan = looks_like_wlan_adapter(adapter_name);
            const bool has_gateway = adapter_has_ipv4_gateway(adapter);

            for (auto* unicast = adapter->FirstUnicastAddress; unicast; unicast = unicast->Next) {
                const std::string ip = ipv4_from_sockaddr(unicast->Address.lpSockaddr);
                if (!is_usable_ipv4(ip)) {
                    continue;
                }
                if (is_wlan && has_gateway && wlan_with_gateway.empty()) {
                    wlan_with_gateway = ip;
                }
                if (is_wlan && wlan_fallback.empty()) {
                    wlan_fallback = ip;
                }
                if (has_gateway && gateway_fallback.empty()) {
                    gateway_fallback = ip;
                }
                if (any_fallback.empty()) {
                    any_fallback = ip;
                }
            }
        }
    }

    std::string selected = !wlan_with_gateway.empty() ? wlan_with_gateway :
                           !wlan_fallback.empty() ? wlan_fallback :
                           !gateway_fallback.empty() ? gateway_fallback :
                           !any_fallback.empty() ? any_fallback :
                           detect_hostname_ipv4();
    if (started) {
        WSACleanup();
    }
    return selected;
#else
    return detect_hostname_ipv4();
#endif
}

nlohmann::json build_network_session_info(
    const std::shared_ptr<Corona::Systems::NetworkSystem>& sys) {
    nlohmann::json payload;
    payload["ok"] = true;
    payload["active"] =
        sys->session_state() == Corona::Systems::NetworkSystem::SessionState::Active;
    payload["role"] = std::string(sys->session_role_name());
    payload["peer_count"] = static_cast<int>(sys->peer_count());
    payload["host_address"] = sys->host_address();
    payload["host_port"] = sys->host_port();
    payload["listen_port"] = sys->session_port();
    payload["local_ip"] = detect_wlan_ipv4();
    return payload;
}

void emit_lanchat_event_json(const std::string& event_json) {
    if (event_json.empty()) {
        return;
    }
    std::string js = "if(window.__coronaEmit)window.__coronaEmit(" +
                     nlohmann::json("lanchat-event").dump() + "," +
                     event_json + ",{\"_fromCross\":1})";
    for (auto& [tab_id, tab] : BrowserManager::instance().get_tabs()) {
        if (tab && !tab->minimized && tab->client && tab->client->GetBrowser()) {
            tab->client->GetBrowser()->GetMainFrame()->ExecuteJavaScript(js, "", 0);
        }
    }
}

nlohmann::json build_lanchat_members(
    const std::vector<Corona::Network::LanChatMember>& members) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& member : members) {
        result.push_back(member.nickname);
    }
    return result;
}

nlohmann::json build_lanchat_member_details(
    const std::vector<Corona::Network::LanChatMember>& members) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& member : members) {
        result.push_back({
            {"member_id", member.member_id},
            {"nickname", member.nickname},
            {"status", member.status},
        });
    }
    return result;
}

nlohmann::json build_lanchat_history(
    const std::vector<Corona::Network::LanChatMessage>& history) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& message : history) {
        result.push_back({
            {"message_id", message.message_id},
            {"sender_id", message.sender_id},
            {"room_id", message.room_id},
            {"seq", message.seq},
            {"from", message.sender_name},
            {"text", message.text},
            {"ts", message.timestamp_ms / 1000},
            {"sender_type", message.sender_type},
            {"message_kind", message.message_kind},
            {"target_agent_id", message.target_agent_id},
            {"source_user_id", message.source_user_id},
            {"correlation_id", message.correlation_id},
            {"metadata_json", message.metadata_json},
        });
    }
    return result;
}

nlohmann::json build_lanchat_history_rooms(
    const std::vector<Corona::Network::LanChatHistoryRoomSummary>& rooms) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& room : rooms) {
        const std::string load_id = room.session_id.empty() ? room.room_id : room.session_id;
        result.push_back({
            {"room_id", load_id},
            {"session_id", load_id},
            {"display_room_id", room.room_id},
            {"message_count", room.message_count},
            {"last_timestamp_ms", room.last_timestamp_ms},
            {"last_ts", room.last_timestamp_ms / 1000},
            {"last_sender_name", room.last_sender_name},
            {"last_text", room.last_text},
        });
    }
    return result;
}

nlohmann::json build_lanchat_agents(
    const std::vector<Corona::Network::LanChatAgent>& agents) {
    nlohmann::json result = nlohmann::json::array();
    for (const auto& agent : agents) {
        result.push_back({
            {"agent_id", agent.agent_id},
            {"name", agent.name},
            {"persona", agent.persona},
            {"owner", agent.owner_id},
        });
    }
    return result;
}

std::string make_agent_id(const std::string& owner, const std::string& name) {
    static uint64_t counter = 0;
    std::ostringstream out;
    out << "agent-" << std::hash<std::string>{}(owner + ":" + name) << "-" << ++counter;
    return out.str();
}

void read_transform_from_actor_json(const nlohmann::json& actor, float transform[9]) {
    if (!actor.contains("geometry")) {
        return;
    }
    const auto& geo = actor["geometry"];
    if (geo.contains("position") && geo["position"].is_array() && geo["position"].size() >= 3) {
        transform[0] = geo["position"][0].get<float>();
        transform[1] = geo["position"][1].get<float>();
        transform[2] = geo["position"][2].get<float>();
    }
    if (geo.contains("rotation") && geo["rotation"].is_array() && geo["rotation"].size() >= 3) {
        transform[3] = geo["rotation"][0].get<float>();
        transform[4] = geo["rotation"][1].get<float>();
        transform[5] = geo["rotation"][2].get<float>();
    }
    if (geo.contains("scale") && geo["scale"].is_array() && geo["scale"].size() >= 3) {
        transform[6] = geo["scale"][0].get<float>();
        transform[7] = geo["scale"][1].get<float>();
        transform[8] = geo["scale"][2].get<float>();
    }
}

NativeResult dispatch_method(const std::string& module,
                             const NativeMethodTable& methods,
                             const NativeRequest& request,
                             const NativeContext& context) {
    const auto it = methods.find(request.function);
    if (it == methods.end()) {
        return native_failure("Unknown " + module + " function: " + request.function);
    }
    try {
        return it->second(request, context);
    } catch (const std::exception& e) {
        return native_failure(e.what(), 2);
    } catch (...) {
        return native_failure(module + " native handler error", 2);
    }
}

std::shared_ptr<Corona::Systems::NetworkSystem> require_network_system() {
    return get_network_system();
}

}  // namespace

std::string create_editor_actor_from_python(const std::string& scene_name,
                                            const std::string& asset_path,
                                            const std::string& actor_type,
                                            const std::string& actor_data_json) {
    try {
        nlohmann::json actor_data = nlohmann::json::object();
        if (!actor_data_json.empty()) {
            actor_data = nlohmann::json::parse(actor_data_json);
            if (!actor_data.is_object()) {
                actor_data = nlohmann::json::object();
            }
        }

        const auto result = create_native_editor_actor(scene_name, asset_path, actor_type, actor_data);
        if (!result.success) {
            return nlohmann::json{
                {"status", "error"},
                {"message", result.error},
                {"error", result.error},
            }.dump();
        }
        return result.data.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
            {"error", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "create_editor_actor native handler error"},
            {"error", "create_editor_actor native handler error"},
        }.dump();
    }
}

std::string remove_editor_actor_from_python(const std::string& scene_name,
                                            const std::string& actor_name) {
    try {
        const auto result = remove_native_editor_actor(scene_name, actor_name);
        if (!result.success) {
            return nlohmann::json{
                {"status", "error"},
                {"message", result.error},
                {"error", result.error},
            }.dump();
        }
        return result.data.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
            {"error", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "remove_editor_actor native handler error"},
            {"error", "remove_editor_actor native handler error"},
        }.dump();
    }
}

std::string get_editor_actor_bounds_from_python(const std::string& scene_name,
                                                const std::string& actor_name) {
    try {
        auto* scene = ensure_native_editor_scene();
        const auto scene_route = normalize_route(scene_name);
        if (!scene_route.empty() && scene_route != scene->route) {
            scene = reload_native_editor_scene("", scene_route);
        }
        auto* actor = find_native_actor(*scene, actor_name);
        if (!actor) {
            return nlohmann::json{
                {"status", "error"},
                {"message", "Actor not found: " + actor_name},
            }.dump();
        }
        const auto aabb = native_actor_world_aabb(*actor);
        if (!aabb) {
            return nlohmann::json{
                {"status", "error"},
                {"message", "Actor has no native bounds: " + actor_name},
            }.dump();
        }
        return nlohmann::json{
            {"status", "success"},
            {"scene", scene->route},
            {"actor", actor_to_json(*scene, *actor)},
            {"aabb", aabb_to_json(*aabb)},
        }.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "get_editor_actor_bounds native handler error"},
        }.dump();
    }
}

std::string get_editor_scene_snapshot_from_python(const std::string& scene_name) {
    try {
        auto* scene = ensure_native_editor_scene();
        const auto scene_route = normalize_route(scene_name);
        if (!scene_route.empty() && scene_route != scene->route) {
            scene = reload_native_editor_scene("", scene_route);
        }
        nlohmann::json actors = nlohmann::json::array();
        for (const auto& actor : scene->actors) {
            actors.push_back(actor_to_json(*scene, actor));
        }
        const auto scene_aabb = native_scene_world_aabb(*scene);
        return nlohmann::json{
            {"status", "success"},
            {"scene", scene->route},
            {"scene_name", scene->name},
            {"actor_count", scene->actors.size()},
            {"actors", actors},
            {"scene_aabb", scene_aabb ? aabb_to_json(*scene_aabb) : nlohmann::json(nullptr)},
            {"bounds_ready", static_cast<bool>(scene_aabb)},
        }.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "get_editor_scene_snapshot native handler error"},
        }.dump();
    }
}

std::string set_editor_actor_transform_from_python(const std::string& scene_name,
                                                   const std::string& actor_name,
                                                   const std::string& transform_json) {
    try {
        nlohmann::json transform_data = nlohmann::json::object();
        if (!transform_json.empty()) {
            transform_data = nlohmann::json::parse(transform_json);
            if (!transform_data.is_object()) {
                transform_data = nlohmann::json::object();
            }
        }
        const auto result = set_native_editor_actor_transform(scene_name, actor_name, transform_data);
        if (!result.success) {
            return nlohmann::json{
                {"status", "error"},
                {"message", result.error},
                {"error", result.error},
            }.dump();
        }
        return result.data.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
            {"error", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "set_editor_actor_transform native handler error"},
            {"error", "set_editor_actor_transform native handler error"},
        }.dump();
    }
}

std::string get_editor_scene_bounds_from_python(const std::string& scene_name) {
    try {
        auto* scene = ensure_native_editor_scene();
        const auto scene_route = normalize_route(scene_name);
        if (!scene_route.empty() && scene_route != scene->route) {
            scene = reload_native_editor_scene("", scene_route);
        }
        const auto aabb = native_scene_world_aabb(*scene);
        if (!aabb) {
            return nlohmann::json{
                {"status", "error"},
                {"message", "Scene has no native actor bounds"},
            }.dump();
        }
        return nlohmann::json{
            {"status", "success"},
            {"scene", scene->route},
            {"aabb", aabb_to_json(*aabb)},
        }.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "get_editor_scene_bounds native handler error"},
        }.dump();
    }
}

std::string capture_editor_camera_view_from_python(const std::string& scene_name,
                                                   const std::string& camera_name,
                                                   const std::string& camera_data_json,
                                                   const std::string& output_path) {
    try {
        nlohmann::json camera_data = nlohmann::json::object();
        if (!camera_data_json.empty()) {
            camera_data = nlohmann::json::parse(camera_data_json);
            if (!camera_data.is_object()) {
                camera_data = nlohmann::json::object();
            }
        }

        auto* scene = ensure_native_editor_scene();
        const auto scene_route = normalize_route(scene_name);
        if (!scene_route.empty() && scene_route != scene->route) {
            scene = reload_native_editor_scene("", scene_route);
        }

        auto* camera = ensure_native_editor_camera(*scene, camera_name, camera_data);
        if (!camera || !camera->engine_camera) {
            return nlohmann::json{
                {"status", "error"},
                {"message", "Native editor camera unavailable"},
            }.dump();
        }

        const auto position = camera_data.contains("position")
                                  ? json_float3_value(camera_data["position"]).value_or(camera->engine_camera->get_position())
                                  : camera->engine_camera->get_position();
        const auto forward = camera_data.contains("forward")
                                 ? json_float3_value(camera_data["forward"]).value_or(camera->engine_camera->get_forward())
                                 : camera->engine_camera->get_forward();
        const auto world_up = camera_data.contains("world_up")
                                  ? json_float3_value(camera_data["world_up"]).value_or(camera->engine_camera->get_world_up())
                                  : camera->engine_camera->get_world_up();
        const auto fov = json_float_value(camera_data, "fov", camera->engine_camera->get_fov());
        camera->engine_camera->set(position, forward, world_up, fov);
        camera->width = std::max(json_int_value(camera_data, "width", camera->width), 1);
        camera->height = std::max(json_int_value(camera_data, "height", camera->height), 1);
        camera->engine_camera->set_size(camera->width, camera->height);
        const auto output_mode = json_string_value(camera_data, {"output_mode"});
        camera->engine_camera->set_output_mode(output_mode.empty() ? "base_color" : output_mode);
        camera->engine_camera->set_offscreen_capture_mode(true);
        camera->engine_camera->set_surface(0);

        const bool saved = camera->engine_camera->save_screenshot_sync(output_path);
        return nlohmann::json{
            {"status", saved ? "success" : "error"},
            {"ok", saved},
            {"scene", scene->route},
            {"path", output_path},
            {"camera", camera_to_json(*camera)},
            {"message", saved ? "" : "Screenshot save failed"},
        }.dump();
    } catch (const std::exception& e) {
        return nlohmann::json{
            {"status", "error"},
            {"message", e.what()},
        }.dump();
    } catch (...) {
        return nlohmann::json{
            {"status", "error"},
            {"message", "capture_editor_camera_view native handler error"},
        }.dump();
    }
}

void register_main_view_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"on_init", [](const NativeRequest& request, const NativeContext&) {
            const auto project_path = resolve_active_project_path(request.args);
            auto* scene = ensure_native_editor_scene(project_path);
            return native_success(make_on_init_payload(*scene));
        }},
        {"scene_save", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto scene_route = normalize_route(arg_string(request.args, 0));
            if (!scene_route.empty() && scene_route != scene->route) {
                scene = reload_native_editor_scene("", scene_route);
            }
            persist_native_scene_actors(*scene);
            return native_success({
                {"status", "success"},
                {"filepath", path_to_utf8(resolve_project_path(scene->project_root, scene->route))},
                {"format", "corona_scene"},
            });
        }},
    };

    registry.register_module("MainView", [](const NativeRequest& request,
                                            const NativeContext& context) {
        const auto it = methods.find(request.function);
        if (it == methods.end()) {
            return native_unhandled();
        }
        try {
            return it->second(request, context);
        } catch (const std::exception& e) {
            return native_failure(e.what(), 2);
        } catch (...) {
            return native_failure("MainView native handler error", 2);
        }
    });
}

void register_project_settings_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"get_active_project_info", [](const NativeRequest&, const NativeContext&) {
            return native_success(active_project_info_json());
        }},
    };

    registry.register_module("ProjectSettings", [](const NativeRequest& request,
                                                   const NativeContext& context) {
        const auto it = methods.find(request.function);
        if (it == methods.end()) {
            return native_unhandled();
        }
        try {
            return it->second(request, context);
        } catch (const std::exception& e) {
            return native_failure(e.what(), 2);
        } catch (...) {
            return native_failure("ProjectSettings native handler error", 2);
        }
    });
}

void register_scene_datas_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"get_scene", [](const NativeRequest&, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            return native_success(scene_to_json(*scene));
        }},
        {"get_actor", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 1);
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor) {
                return native_failure("Actor not found: " + actor_name, 2);
            }
            return native_success(actor_to_json(*scene, *actor));
        }},
        {"actor_operation", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 1);
            const auto operation = arg_string(request.args, 2);
            const auto vector = request.args.is_array() && request.args.size() > 3
                                    ? request.args[3]
                                    : nlohmann::json::array();
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor) {
                return native_failure("Actor not found: " + actor_name, 2);
            }
            auto result = apply_actor_operation(*scene, *actor, operation, vector);
            if (result.handled && result.success) {
                persist_native_scene_actors(*scene);
            }
            return result;
        }},
        {"save_actor", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto scene_route = normalize_route(arg_string(request.args, 0));
            if (!scene_route.empty() && scene_route != scene->route) {
                scene = reload_native_editor_scene("", scene_route);
            }
            const auto actor_name = arg_string(request.args, 1);
            if (!actor_name.empty() && !find_native_actor(*scene, actor_name)) {
                return native_failure("Actor not found: " + actor_name, 2);
            }
            persist_native_scene_actors(*scene);
            return native_success({
                {"status", "success"},
                {"scene", scene->route},
                {"actor", actor_name},
            });
        }},
    };

    registry.register_module("SceneDatas", [](const NativeRequest& request,
                                              const NativeContext& context) {
        const auto it = methods.find(request.function);
        if (it == methods.end()) {
            return native_unhandled();
        }
        try {
            return it->second(request, context);
        } catch (const std::exception& e) {
            return native_failure(e.what(), 2);
        } catch (...) {
            return native_failure("SceneDatas native handler error", 2);
        }
    });
}

void register_scene_tools_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"list_scene_tree", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto scene_route = normalize_route(arg_string(request.args, 0));
            if (!scene_route.empty() && scene_route != scene->route) {
                scene = reload_native_editor_scene("", scene_route);
            }
            nlohmann::json actors = nlohmann::json::array();
            for (const auto& actor : scene->actors) {
                actors.push_back({
                    {"name", actor.name},
                    {"path", actor.route},
                    {"type", actor.actor_type},
                    {"visible", actor.optics ? actor.optics->get_visible() : true},
                    {"handle", actor.engine_actor ? actor.engine_actor->get_handle() : 0},
                    {"actor_guid", actor.actor_guid},
                    {"vision_proxy", false},
                    {"audio_resource_id", actor.actor_type == "audio"
                                              ? std::to_string(actor.audio_resource_id)
                                              : std::string{}},
                });
            }
            nlohmann::json cameras = nlohmann::json::array();
            for (const auto& camera : scene->cameras) {
                cameras.push_back(camera_to_json(camera));
            }
            return native_success({
                {"actors", actors},
                {"cameras", cameras},
                {"vision", {
                    {"enabled", !scene->vision_source_path.empty()},
                    {"source_path", scene->vision_source_path},
                    {"import_mode", scene->vision_import_mode},
                    {"binding_count", 0},
                    {"unsupported_count", 0},
                }},
            });
        }},
        {"list_actor_tree", [](const NativeRequest&, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            nlohmann::json actors = nlohmann::json::array();
            for (const auto& actor : scene->actors) {
                actors.push_back(actor_to_json(*scene, actor));
            }
            return native_success(actors);
        }},
        {"reload_scene", [](const NativeRequest& request, const NativeContext&) {
            const auto scene_route = arg_string(request.args, 0);
            const auto project_path = arg_string(request.args, 1);
            auto* scene = reload_native_editor_scene(project_path, scene_route);
            return native_success({
                {"status", "success"},
                {"scene", scene->route},
                {"actor_count", scene->actors.size()},
                {"camera_count", scene->cameras.size()},
            });
        }},
        {"sun_direction", [](const NativeRequest& request, const NativeContext&) {
            const auto scene_route = normalize_route(arg_string(request.args, 0));
            auto* scene = ensure_native_editor_scene();
            if (!scene_route.empty() && scene_route != scene->route) {
                scene = reload_native_editor_scene("", scene_route);
            }

            scene->sun_enabled = arg_bool(request.args, 1, true);
            const auto direction_arg = request.args.is_array() && request.args.size() > 2
                                           ? request.args[2]
                                           : nlohmann::json::array();
            std::array<float, 3> direction{
                json_float_at(direction_arg, 0, scene->sun_direction[0]),
                json_float_at(direction_arg, 1, scene->sun_direction[1]),
                json_float_at(direction_arg, 2, scene->sun_direction[2]),
            };
            const float length_sq =
                direction[0] * direction[0] +
                direction[1] * direction[1] +
                direction[2] * direction[2];
            if (scene->sun_enabled && length_sq < 1.0e-8f) {
                direction = {1.0f, 1.0f, 1.0f};
            }
            scene->sun_direction = direction;

            apply_native_scene_environment(*scene);
            persist_native_scene_environment(*scene);
            return native_success({
                {"status", "success"},
                {"scene", scene->route},
                {"sun", {{"enabled", scene->sun_enabled}, {"direction", scene->sun_direction}}},
            });
        }},
        {"floor_grid", [](const NativeRequest& request, const NativeContext&) {
            const auto scene_route = normalize_route(arg_string(request.args, 0));
            auto* scene = ensure_native_editor_scene();
            if (!scene_route.empty() && scene_route != scene->route) {
                scene = reload_native_editor_scene("", scene_route);
            }

            scene->floor_grid_enabled = arg_bool(request.args, 1, true);
            apply_native_scene_environment(*scene);
            persist_native_scene_environment(*scene);
            return native_success({
                {"status", "success"},
                {"scene", scene->route},
                {"grid", {{"enabled", scene->floor_grid_enabled}}},
            });
        }},
        {"create_actor", [](const NativeRequest& request, const NativeContext&) {
            const auto scene_route = arg_string(request.args, 0);
            const auto source_path = arg_string(request.args, 1);
            auto actor_type = normalize_route(arg_string(request.args, 2, "model"));
            const auto actor_data = arg_object(request.args, 3);
            return create_native_editor_actor(scene_route, source_path, actor_type, actor_data);
        }},
        {"rename_actor", [](const NativeRequest& request, const NativeContext& context) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 1);
            const auto new_name = trim_ascii(arg_string(request.args, 2));
            if (new_name.empty()) {
                return native_failure("Actor name cannot be empty", 2);
            }
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor) {
                return native_failure("Actor not found: " + actor_name, 2);
            }
            const auto duplicate = std::any_of(scene->actors.begin(), scene->actors.end(), [&](const NativeEditorActor& other) {
                return &other != actor && other.name == new_name;
            });
            if (duplicate) {
                return native_failure("Actor name already exists: " + new_name, 2);
            }
            const auto old_name = actor->name;
            actor->name = new_name;
            persist_native_scene_actors(*scene);
            emit_actor_change(context, *scene, *actor);
            return native_success({
                {"status", "success"},
                {"scene", scene->route},
                {"old_name", old_name},
                {"new_name", actor->name},
                {"actor", actor_to_json(*scene, *actor)},
            });
        }},
        {"list_camera_views", [](const NativeRequest&, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            nlohmann::json cameras = nlohmann::json::array();
            for (const auto& camera : scene->cameras) {
                cameras.push_back(camera_to_json(camera));
            }
            return native_success({{"cameras", cameras}});
        }},
        {"is_vision_available", [](const NativeRequest&, const NativeContext&) {
            return native_success({{"available", Corona::API::is_vision_available()}});
        }},
        {"load_vision_scene", [](const NativeRequest& request, const NativeContext&) {
            Corona::API::load_vision_scene(arg_string(request.args, 0));
            return native_success({{"status", "success"}});
        }},
        {"set_output_mode", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto camera_name = arg_string(request.args, 1);
            const auto mode = arg_string(request.args, 2, "final_color");
            auto* camera = find_native_camera(*scene, camera_name);
            if (!camera || !camera->engine_camera) {
                return native_failure("Camera not found: " + camera_name, 2);
            }
            camera->engine_camera->set_output_mode(mode);
            return native_success({{"status", "success"}, {"mode", camera->engine_camera->get_output_mode()}});
        }},
        {"get_output_mode", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto camera_name = arg_string(request.args, 1);
            auto* camera = find_native_camera(*scene, camera_name);
            if (!camera || !camera->engine_camera) {
                return native_failure("Camera not found: " + camera_name, 2);
            }
            return native_success({{"status", "success"}, {"mode", camera->engine_camera->get_output_mode()}});
        }},
        {"set_shadow_cascade_debug", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto camera_name = arg_string(request.args, 1);
            const bool enabled = arg_bool(request.args, 2, false);
            auto* camera = find_native_camera(*scene, camera_name);
            if (!camera || !camera->engine_camera) {
                return native_failure("Camera not found: " + camera_name, 2);
            }
            camera->engine_camera->set_shadow_cascade_debug(enabled);
            return native_success({
                {"status", "success"},
                {"enabled", camera->engine_camera->get_shadow_cascade_debug()},
            });
        }},
        {"get_shadow_cascade_debug", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto camera_name = arg_string(request.args, 1);
            auto* camera = find_native_camera(*scene, camera_name);
            if (!camera || !camera->engine_camera) {
                return native_failure("Camera not found: " + camera_name, 2);
            }
            return native_success({
                {"status", "success"},
                {"enabled", camera->engine_camera->get_shadow_cascade_debug()},
            });
        }},
        {"open_actor", [](const NativeRequest& request, const NativeContext& context) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 1);
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor) {
                return native_failure("Actor not found: " + actor_name, 2);
            }
            emit_actor_change(context, *scene, *actor);
            return native_success({{"status", "success"}, {"actor", actor_to_json(*scene, *actor)}});
        }},
        {"focus_actor", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 1);
            const auto camera_name = arg_string(request.args, 2);
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor || !actor->geometry) {
                return native_failure("Actor not found or has no geometry: " + actor_name, 2);
            }
            auto* camera = find_native_camera(*scene, camera_name);
            if (!camera || !camera->engine_camera) {
                return native_failure("Camera not found: " + camera_name, 2);
            }

            const auto aabb = actor->geometry->get_aabb();
            const auto pos = actor->geometry->get_position();
            const auto scale = actor->geometry->get_scale();
            const std::array<float, 3> center{
                pos[0] + ((aabb[0] + aabb[3]) * 0.5f) * scale[0],
                pos[1] + ((aabb[1] + aabb[4]) * 0.5f) * scale[1],
                pos[2] + ((aabb[2] + aabb[5]) * 0.5f) * scale[2],
            };
            const float dx = std::abs((aabb[3] - aabb[0]) * scale[0]);
            const float dy = std::abs((aabb[4] - aabb[1]) * scale[1]);
            const float dz = std::abs((aabb[5] - aabb[2]) * scale[2]);
            const float diagonal = std::sqrt(dx * dx + dy * dy + dz * dz);
            const float distance = std::max(diagonal * 2.0f, 1.0f);
            const std::array<float, 3> camera_position{center[0], center[1], center[2] - distance};
            const std::array<float, 3> forward{0.0f, 0.0f, 1.0f};
            const std::array<float, 3> up{0.0f, 1.0f, 0.0f};
            camera->engine_camera->set(camera_position, forward, up, camera->engine_camera->get_fov());
            return native_success({
                {"status", "success"},
                {"center", center},
                {"distance", distance},
                {"camera", camera_to_json(*camera)},
            });
        }},
        {"remove_actor", [](const NativeRequest& request, const NativeContext&) {
            const auto scene_route = arg_string(request.args, 0);
            const auto actor_name = arg_string(request.args, 1);
            return remove_native_editor_actor(scene_route, actor_name);
        }},
        {"pick_actor_at_pixel", [](const NativeRequest& request, const NativeContext& context) {
            auto* scene = ensure_native_editor_scene();
            auto* camera = find_native_camera(*scene, {});
            if (!camera || !camera->engine_camera) {
                return native_failure("No active camera available", 2);
            }
            const float x = arg_float_value(request.args, 1);
            const float y = arg_float_value(request.args, 2);
            const float viewport_width = arg_float_value(request.args, 3, static_cast<float>(camera->width));
            const float viewport_height = arg_float_value(request.args, 4, static_cast<float>(camera->height));
            if (viewport_width <= 0.0f || viewport_height <= 0.0f) {
                return native_failure("Invalid viewport size", 2);
            }
            const int pick_x = static_cast<int>(x * static_cast<float>(camera->width) / viewport_width);
            const int pick_y = static_cast<int>(y * static_cast<float>(camera->height) / viewport_height);
            if (pick_x < 0 || pick_x >= camera->width || pick_y < 0 || pick_y >= camera->height) {
                return native_success({{"status", "miss"}});
            }
            const auto handle = camera->engine_camera->pick_actor_at_pixel(pick_x, pick_y);
            if (handle == 0) {
                return native_success({{"status", "pending"}});
            }
            auto* actor = find_native_actor(*scene, std::to_string(handle));
            if (!actor) {
                return native_success({{"status", "miss"}, {"handle", handle}});
            }
            emit_actor_change(context, *scene, *actor);
            return native_success({
                {"status", "success"},
                {"actor", actor_to_json(*scene, *actor)},
            });
        }},
        {"play_audio", [](const NativeRequest& request, const NativeContext&) {
            auto* event_bus = Corona::Kernel::KernelContext::instance().event_bus();
            if (!event_bus) {
                return native_failure("event_bus unavailable", 2);
            }
            const uint64_t rid = arg_uint64(request.args, 0);
            if (rid == 0) {
                return native_failure("invalid resource_id", 2);
            }
            const bool loop = arg_bool(request.args, 1, false);
            event_bus->publish<::Corona::Events::PlayAudioEvent>({rid, loop});

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"stop_audio", [](const NativeRequest& request, const NativeContext&) {
            auto* event_bus = Corona::Kernel::KernelContext::instance().event_bus();
            if (!event_bus) {
                return native_failure("event_bus unavailable", 2);
            }
            const uint64_t rid = arg_uint64(request.args, 0);
            if (rid == 0) {
                return native_failure("invalid resource_id", 2);
            }
            event_bus->publish<::Corona::Events::StopAudioEvent>({rid});

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"actor_play_audio", [](const NativeRequest& request, const NativeContext&) {
            // 在指定 actor 的世界位置播放其绑定的音频（空间音频）。
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 0);
            const bool loop = arg_bool(request.args, 1, false);
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor || !actor->acoustics) {
                return native_failure("actor not found or has no acoustics component", 2);
            }
            actor->acoustics->play(loop);

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"actor_stop_audio", [](const NativeRequest& request, const NativeContext&) {
            auto* scene = ensure_native_editor_scene();
            const auto actor_name = arg_string(request.args, 0);
            auto* actor = find_native_actor(*scene, actor_name);
            if (!actor || !actor->acoustics) {
                return native_failure("actor not found or has no acoustics component", 2);
            }
            actor->acoustics->stop();

            nlohmann::json payload;
            payload["ok"] = true;
            return native_success(payload);
        }},
    };

    registry.register_module("SceneTools", [](const NativeRequest& request,
                                              const NativeContext& context) {
        const auto it = methods.find(request.function);
        if (it == methods.end()) {
            return native_unhandled();
        }
        try {
            return it->second(request, context);
        } catch (const std::exception& e) {
            return native_failure(e.what(), 2);
        } catch (...) {
            return native_failure("SceneTools native handler error", 2);
        }
    });
}

void register_network_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"start_session", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string name = arg_string(request.args, 0);
            const uint64_t project_id = arg_uint64(request.args, 1);
            const uint16_t port = arg_uint16(request.args, 2, 27960);
            const auto role = request.args.size() > 3
                ? parse_network_session_role(request.args[3])
                : Corona::Systems::NetworkSystem::SessionRole::Host;

            const bool ok = sys->start_session(name, project_id, port, role);
            auto payload = build_network_session_info(sys);
            payload["ok"] = ok;
            return native_success(payload);
        }},
        {"stop_session", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->stop_session();
            return native_success({{"ok", true}});
        }},
        {"get_peer_count", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success(build_network_session_info(sys));
        }},
        {"get_session_info", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success(build_network_session_info(sys));
        }},
        {"connect_to_peer", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string ip = arg_string(request.args, 0);
            const uint16_t port = arg_uint16(request.args, 1, 27960);
            const std::string peer_name = arg_string(request.args, 2);
            const bool ok = sys->connect_to_peer(ip, port, peer_name);
            auto payload = build_network_session_info(sys);
            payload["ok"] = ok;
            return native_success(payload);
        }},
        {"set_project_root", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string root = arg_string(request.args, 0);
            if (!root.empty()) {
                sys->set_project_root(root);
            }
            return native_success({{"ok", true}});
        }},
        {"poll_pending_actor_create", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, model_path, actor_json;
            Corona::Network::ActorCreatePacked packed;
            if (sys->pop_pending_actor_create(actor_guid, scene_name, model_path,
                                               &packed, sizeof(packed), &actor_json)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["model_path"] = model_path;
                nlohmann::json actor_data = nlohmann::json::object();
                if (!actor_json.empty()) {
                    try {
                        actor_data = nlohmann::json::parse(actor_json);
                        if (!actor_data.is_object()) {
                            actor_data = nlohmann::json::object();
                        }
                    } catch (const nlohmann::json::parse_error&) {
                        actor_data = nlohmann::json::object();
                    }
                }
                actor_data["geometry"]["position"] = {
                    packed.transform[0], packed.transform[1], packed.transform[2]
                };
                actor_data["geometry"]["rotation"] = {
                    packed.transform[3], packed.transform[4], packed.transform[5]
                };
                actor_data["geometry"]["scale"] = {
                    packed.transform[6], packed.transform[7], packed.transform[8]
                };
                payload["actor_data"] = actor_data;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_transform", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, source_user_id, correlation_id;
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            if (sys->pop_pending_actor_transform_update(
                    actor_guid, scene_name, transform, 9,
                    source_user_id, correlation_id)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["source_user_id"] = source_user_id;
                payload["correlation_id"] = correlation_id;
                payload["geometry"]["position"] = {transform[0], transform[1], transform[2]};
                payload["geometry"]["rotation"] = {transform[3], transform[4], transform[5]};
                payload["geometry"]["scale"] = {transform[6], transform[7], transform[8]};
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_delete", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, actor_name;
            if (sys->pop_pending_actor_delete(actor_guid, scene_name, actor_name)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["actor_name"] = actor_name;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_scene_snapshot_request", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string scene_name;
            if (sys->pop_pending_actor_scene_snapshot_request(scene_name)) {
                payload["has_pending"] = true;
                payload["scene_name"] = scene_name;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_scene_snapshot", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string scene_name, snapshot_json;
            if (sys->pop_pending_actor_scene_snapshot(scene_name, snapshot_json)) {
                payload["has_pending"] = true;
                payload["scene_name"] = scene_name;
                payload["snapshot_json"] = snapshot_json;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"poll_pending_actor_state_update", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            nlohmann::json payload;
            std::string actor_guid, scene_name, actor_json;
            if (sys->pop_pending_actor_state_update(actor_guid, scene_name, actor_json)) {
                payload["has_pending"] = true;
                payload["actor_guid"] = actor_guid;
                payload["scene_name"] = scene_name;
                payload["actor_json"] = actor_json;
            } else {
                payload["has_pending"] = false;
            }
            payload["ok"] = true;
            return native_success(payload);
        }},
        {"set_sync_paused", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_sync_paused(arg_bool(request.args, 0, false));
            return native_success({{"ok", true}});
        }},
        {"register_actor_identity", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string actor_guid = arg_string(request.args, 0);
            const std::uintptr_t actor_handle = arg_uintptr(request.args, 1);
            const bool locally_owned = arg_bool(request.args, 2, true);
            const bool ok = sys->register_actor_identity(actor_guid, actor_handle, locally_owned);
            return native_success({{"ok", ok}});
        }},
        {"claim_actor_ownership", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const bool ok = sys->claim_actor_ownership(arg_string(request.args, 0));
            return native_success({{"ok", ok}});
        }},
        {"broadcast_actor_transform", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const std::string actor_guid = arg_string(request.args, 0);
            const std::string scene_name = arg_string(request.args, 1);
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            std::string source_user_id;
            std::string correlation_id;
            const auto actor_data = arg_object(request.args, 2);
            if (!actor_data.empty()) {
                read_transform_from_actor_json(actor_data, transform);
                source_user_id = actor_data.value("source_user_id", "");
                correlation_id = actor_data.value("correlation_id", "");
            }
            sys->broadcast_actor_transform_update(
                actor_guid, scene_name, transform, source_user_id, correlation_id);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_delete", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->broadcast_actor_delete(
                arg_string(request.args, 0),
                arg_string(request.args, 1),
                arg_string(request.args, 2));
            return native_success({{"ok", true}});
        }},
        {"request_actor_scene_snapshot", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->request_actor_scene_snapshot(arg_string(request.args, 0));
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_scene_snapshot", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string snapshot_json;
            if (request.args.size() > 1) {
                snapshot_json = request.args[1].is_string()
                    ? request.args[1].get<std::string>()
                    : request.args[1].dump();
            }
            sys->broadcast_actor_scene_snapshot(arg_string(request.args, 0), snapshot_json);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_state_update", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string actor_json;
            if (request.args.size() > 2) {
                actor_json = request.args[2].is_string()
                    ? request.args[2].get<std::string>()
                    : request.args[2].dump();
            }
            sys->broadcast_actor_state_update(
                arg_string(request.args, 0),
                arg_string(request.args, 1),
                actor_json);
            return native_success({{"ok", true}});
        }},
        {"broadcast_actor_create", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            std::string actor_guid = arg_string(request.args, 0);
            const std::string scene_name = arg_string(request.args, 1);
            const std::string model_path = arg_string(request.args, 2);
            float transform[9] = {0,0,0, 0,0,0, 1,1,1};
            std::vector<std::string> dependency_paths;
            std::string actor_json;
            const auto actor_data = arg_object(request.args, 3);
            if (!actor_data.empty()) {
                actor_json = actor_data.dump();
                if (actor_guid.empty() &&
                    actor_data.contains("actor_guid") &&
                    actor_data["actor_guid"].is_string()) {
                    actor_guid = actor_data["actor_guid"].get<std::string>();
                }
                if (actor_data.contains("model_dependencies") &&
                    actor_data["model_dependencies"].is_array()) {
                    for (const auto& dep : actor_data["model_dependencies"]) {
                        if (dep.is_string()) {
                            dependency_paths.push_back(dep.get<std::string>());
                        }
                    }
                }
                read_transform_from_actor_json(actor_data, transform);
            }
            if (actor_guid.empty()) {
                actor_guid = scene_name + ":" + model_path;
            }

            Corona::Network::ActorCreatePacked opt;
            std::memset(&opt, 0, sizeof(opt));
            opt.visible = true;
            opt.bEnableLighting = true;
            opt.metallic = 0.0f;
            opt.roughness = 0.5f;
            opt.specular = 0.5f;
            opt.specularTint = 0.0f;
            opt.sheen = 0.0f;
            opt.sheenTint = 0.5f;
            opt.clearcoat = 0.0f;
            opt.clearcoatGloss = 1.0f;
            opt.ambient[0] = 0.2f; opt.ambient[1] = 0.2f; opt.ambient[2] = 0.2f;
            opt.diffuse[0] = 0.8f; opt.diffuse[1] = 0.8f; opt.diffuse[2] = 0.8f;
            opt.specular_color[0] = 1.0f; opt.specular_color[1] = 1.0f; opt.specular_color[2] = 1.0f;
            opt.shininess = 32.0f;

            sys->broadcast_actor_create(actor_guid, scene_name, model_path,
                                        dependency_paths, transform,
                                        &opt, sizeof(opt), actor_json);
            return native_success({{"ok", true}});
        }},
    };

    registry.register_module("Network", [](const NativeRequest& request,
                                           const NativeContext& context) {
        return dispatch_method("Network", methods, request, context);
    });
}

void register_lanchat_rpc_handlers(NativeRpcRegistry& registry) {
    static const NativeMethodTable methods = {
        {"start_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            const uint16_t port = payload_arg.value("port", 27960);
            const std::string nickname = payload_arg.value("nickname", "房主");
            const bool restore_history = payload_arg.value("restore_history", false);
            const std::string history_room = payload_arg.value("history_room", room);
            const std::string host_nickname = nickname.empty() ? "房主" : nickname;
            const bool ok = sys->lanchat_start_room(room, host_nickname, port);
            bool restored_history = false;
            if (ok && restore_history) {
                restored_history = sys->lanchat_restore_history_room(history_room);
            }
            const uint16_t actual_port = sys->session_port() != 0 ? sys->session_port() : port;
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = host_nickname;
            data["ip"] = detect_wlan_ipv4();
            data["port"] = actual_port;
            data["room"] = room;
            data["peer_id"] = sys->local_peer_id();
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            data["restored_history"] = restored_history;
            return native_success(data);
        }},
        {"start_local_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            const std::string nickname = payload_arg.value("nickname", "房主");
            const bool restore_history = payload_arg.value("restore_history", false);
            const std::string history_room = payload_arg.value("history_room", room);
            const std::string host_nickname = nickname.empty() ? "房主" : nickname;
            const bool ok = sys->lanchat_start_local_room(room, host_nickname);
            bool restored_history = false;
            if (ok && restore_history) {
                restored_history = sys->lanchat_restore_history_room(history_room);
            }
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = host_nickname;
            data["ip"] = "";
            data["port"] = 0;
            data["room"] = room;
            data["mode"] = "single";
            data["peer_id"] = "local-single-player";
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            data["restored_history"] = restored_history;
            return native_success(data);
        }},
        {"stop_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_leave_room();
            sys->stop_session();
            return native_success({{"ok", true}});
        }},
        {"stop_local_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_stop_local_room();
            return native_success({{"ok", true}});
        }},
        {"get_history", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"history", build_lanchat_history(sys->lanchat_history())},
            });
        }},
        {"list_history_rooms", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"rooms", build_lanchat_history_rooms(sys->lanchat_history_rooms())},
            });
        }},
        {"load_history_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string room = payload_arg.value("room", "");
            nlohmann::json data;
            data["ok"] = !room.empty();
            data["room"] = room;
            data["history"] = room.empty()
                ? nlohmann::json::array()
                : build_lanchat_history(sys->lanchat_load_history_room(room));
            data["agents"] = room.empty()
                ? nlohmann::json::array()
                : build_lanchat_agents(sys->lanchat_load_history_agents(room));
            if (room.empty()) {
                data["error"] = "ROOM_REQUIRED";
            }
            return native_success(data);
        }},
        {"join_room", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->set_lanchat_event_callback(emit_lanchat_event_json);
            const auto payload_arg = arg_object(request.args, 0);
            const std::string ip = payload_arg.value("ip", "");
            const uint16_t port = payload_arg.value("port", 27960);
            const std::string room = payload_arg.value("room", "");
            const std::string nickname = payload_arg.value("nickname", "Guest");
            const bool ok = sys->lanchat_join_room(ip, port, room, nickname);
            nlohmann::json data;
            data["ok"] = ok;
            data["you"] = nickname;
            data["peer_id"] = sys->local_peer_id();
            data["port"] = sys->host_port() != 0 ? sys->host_port() : port;
            data["members"] = build_lanchat_members(sys->lanchat_members());
            data["member_details"] = build_lanchat_member_details(sys->lanchat_members());
            data["history"] = build_lanchat_history(sys->lanchat_history());
            data["agents"] = build_lanchat_agents(sys->lanchat_agents());
            if (!ok) {
                data["error"] = "JOIN_FAILED";
            }
            return native_success(data);
        }},
        {"leave_room", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            sys->lanchat_leave_room();
            return native_success({{"ok", true}});
        }},
        {"send_message", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string text = payload_arg.value("text", "");
            const std::string message_kind = payload_arg.value("message_kind", "chat");
            const std::string target_agent_id = payload_arg.value("target_agent_id", "");
            const std::string source_user_id = payload_arg.value("source_user_id", "");
            const std::string correlation_id = payload_arg.value("correlation_id", "");
            std::string metadata_json;
            if (payload_arg.contains("metadata_json")) {
                metadata_json = payload_arg.value("metadata_json", "");
            } else if (payload_arg.contains("metadata")) {
                metadata_json = payload_arg["metadata"].dump();
            }
            const auto result = sys->lanchat_send_message_ex(
                text, message_kind, target_agent_id, source_user_id,
                correlation_id, metadata_json);
            nlohmann::json data;
            data["ok"] = result.accepted;
            if (result.accepted) {
                data["message_id"] = result.message.message_id;
                data["seq"] = result.message.seq;
            } else {
                data["error"] = result.error.empty() ? "SEND_FAILED" : result.error;
            }
            return native_success(data);
        }},
        {"add_agent", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const std::string name = payload_arg.value("name", "Agent");
            const std::string persona = payload_arg.value("persona", "");
            const std::string peer_id = sys->local_peer_id().empty()
                ? "local-single-player"
                : sys->local_peer_id();
            const std::string agent_id = make_agent_id(peer_id, name);
            const auto result = sys->lanchat_register_agent(agent_id, name, persona);
            nlohmann::json data;
            data["ok"] = result.ok;
            data["agent_id"] = agent_id;
            data["name"] = name;
            if (!result.ok) {
                data["error"] = result.error;
            }
            return native_success(data);
        }},
        {"remove_agent", [](const NativeRequest& request, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            const auto payload_arg = arg_object(request.args, 0);
            const auto result = sys->lanchat_remove_agent(payload_arg.value("agent_id", ""));
            nlohmann::json data;
            data["ok"] = result.ok;
            if (!result.ok) {
                data["error"] = result.error;
            }
            return native_success(data);
        }},
        {"list_agents", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"agents", build_lanchat_agents(sys->lanchat_agents())},
            });
        }},
        {"get_local_ip", [](const NativeRequest&, const NativeContext&) {
            auto sys = require_network_system();
            if (!sys) {
                return native_failure("NetworkSystem unavailable", 2);
            }
            return native_success({
                {"ok", true},
                {"ip", detect_wlan_ipv4()},
                {"port", sys->session_port() != 0 ? sys->session_port() : 27960},
            });
        }},
    };

    registry.register_module("LANChat", [](const NativeRequest& request,
                                           const NativeContext& context) {
        return dispatch_method("LANChat", methods, request, context);
    });
}

}  // namespace Corona::Systems::UI
