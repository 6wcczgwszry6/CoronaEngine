#include "scene_folder.h"

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <Windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <system_error>

#include <nlohmann/json.hpp>

namespace Corona::Systems::UI::SceneFolders {
namespace {

namespace fs = std::filesystem;

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::string path_utf8(const fs::path& path) {
    const auto value = path.generic_u8string();
    return {reinterpret_cast<const char*>(value.data()), value.size()};
}

fs::path path_from_utf8(std::string_view value) {
    return fs::path(std::u8string(reinterpret_cast<const char8_t*>(value.data()), value.size()));
}

std::map<std::string, std::map<std::string, std::string>> read_ini(const fs::path& path) {
    std::ifstream stream(path);
    std::map<std::string, std::map<std::string, std::string>> result;
    std::string section;
    std::string line;
    while (std::getline(stream, line)) {
        line = trim(line);
        if (line.empty() || line[0] == ';' || line[0] == '#') continue;
        if (line.front() == '[' && line.back() == ']') {
            section = trim(line.substr(1, line.size() - 2));
            continue;
        }
        const auto equals = line.find('=');
        if (equals != std::string::npos) {
            result[section][trim(line.substr(0, equals))] = trim(line.substr(equals + 1));
        }
    }
    return result;
}

std::vector<std::string> split_words(std::string value) {
    std::istringstream stream(std::move(value));
    std::vector<std::string> words;
    for (std::string word; stream >> std::quoted(word);) words.push_back(std::move(word));
    return words;
}

bool is_relative_inside(const fs::path& path) {
    if (path.empty() || path.is_absolute() || path.has_root_name()) return false;
    for (const auto& part : path) {
        if (part == "..") return false;
    }
    return true;
}

struct SourceFile {
    fs::path source;
    fs::path relative;
};

void add_dependency(std::vector<SourceFile>& files,
                    std::vector<Diagnostic>& diagnostics,
                    const fs::path& source,
                    const fs::path& relative) {
    if (!is_relative_inside(relative)) {
        diagnostics.push_back({"unsafe_dependency", "Resource dependency escapes its bundle", source});
        return;
    }
    if (!fs::is_regular_file(source)) {
        diagnostics.push_back({"missing_dependency", "Resource dependency is missing", source});
        return;
    }
    const auto normalized = relative.lexically_normal();
    if (std::none_of(files.begin(), files.end(), [&](const SourceFile& item) {
            std::error_code ec;
            return fs::equivalent(item.source, source, ec) && !ec;
        })) {
        files.push_back({source, normalized});
    }
}

std::string unquote(std::string value) {
    value = trim(std::move(value));
    if (value.size() >= 2 && ((value.front() == '"' && value.back() == '"') ||
                              (value.front() == '\'' && value.back() == '\''))) {
        return value.substr(1, value.size() - 2);
    }
    return value;
}

void collect_mtl(const fs::path& mtl,
                 const fs::path& source_root,
                 std::vector<SourceFile>& files,
                 std::vector<Diagnostic>& diagnostics) {
    std::ifstream stream(mtl);
    for (std::string line; std::getline(stream, line);) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        const auto space = line.find_first_of(" \t");
        const auto key = lower(line.substr(0, space));
        static const std::set<std::string> texture_keys = {
            "map_ka", "map_kd", "map_ks", "map_ke", "map_ns", "map_d", "bump", "map_bump", "disp", "decal", "norm"};
        if (!texture_keys.contains(key) || space == std::string::npos) continue;
        auto words = split_words(line.substr(space + 1));
        if (words.empty()) continue;
        const auto texture_text = unquote(words.back());
        const auto texture = (mtl.parent_path() / path_from_utf8(texture_text)).lexically_normal();
        std::error_code ec;
        const auto relative = fs::relative(texture, source_root, ec);
        if (ec) {
            diagnostics.push_back({"unsafe_dependency", "Unable to relativize material texture", texture});
        } else {
            add_dependency(files, diagnostics, texture, relative);
        }
    }
}

std::vector<SourceFile> collect_bundle(const fs::path& source,
                                       std::vector<Diagnostic>& diagnostics) {
    std::vector<SourceFile> files;
    if (!fs::is_regular_file(source)) {
        diagnostics.push_back({"missing_model", "Model source does not exist", source});
        return files;
    }
    const auto source_root = source.parent_path();
    add_dependency(files, diagnostics, source, source.filename());
    const auto extension = lower(source.extension().string());

    if (extension == ".obj") {
        std::ifstream stream(source);
        for (std::string line; std::getline(stream, line);) {
            line = trim(line);
            if (line.rfind("mtllib", 0) != 0 || line.size() <= 6) continue;
            const auto mtl_text = unquote(line.substr(6));
            const auto mtl = (source_root / path_from_utf8(mtl_text)).lexically_normal();
            std::error_code ec;
            const auto relative = fs::relative(mtl, source_root, ec);
            if (ec) {
                diagnostics.push_back({"unsafe_dependency", "Unable to relativize OBJ material", mtl});
                continue;
            }
            const auto before = diagnostics.size();
            add_dependency(files, diagnostics, mtl, relative);
            if (before == diagnostics.size()) collect_mtl(mtl, source_root, files, diagnostics);
        }
    } else if (extension == ".gltf") {
        try {
            std::ifstream stream(source);
            const auto document = nlohmann::json::parse(stream);
            auto collect_uris = [&](const char* key) {
                if (!document.contains(key) || !document[key].is_array()) return;
                for (const auto& item : document[key]) {
                    if (!item.is_object() || !item.contains("uri") || !item["uri"].is_string()) continue;
                    const auto uri = item["uri"].get<std::string>();
                    if (uri.rfind("data:", 0) == 0) continue;
                    const auto dependency = (source_root / path_from_utf8(uri)).lexically_normal();
                    std::error_code ec;
                    const auto relative = fs::relative(dependency, source_root, ec);
                    if (ec) diagnostics.push_back({"unsafe_dependency", "Unable to relativize glTF dependency", dependency});
                    else add_dependency(files, diagnostics, dependency, relative);
                }
            };
            collect_uris("buffers");
            collect_uris("images");
        } catch (const std::exception& error) {
            diagnostics.push_back({"invalid_gltf", error.what(), source});
        }
    } else if (extension == ".dae" || extension == ".usd" || extension == ".usda") {
        std::ifstream stream(source, std::ios::binary);
        const std::string text((std::istreambuf_iterator<char>(stream)),
                               std::istreambuf_iterator<char>());
        std::vector<std::string> references;
        if (extension == ".dae") {
            constexpr std::string_view open_tag = "<init_from>";
            constexpr std::string_view close_tag = "</init_from>";
            size_t cursor = 0;
            while ((cursor = text.find(open_tag, cursor)) != std::string::npos) {
                const auto start = cursor + open_tag.size();
                const auto end = text.find(close_tag, start);
                if (end == std::string::npos) break;
                references.push_back(trim(text.substr(start, end - start)));
                cursor = end + close_tag.size();
            }
        } else {
            size_t cursor = 0;
            while ((cursor = text.find('@', cursor)) != std::string::npos) {
                const auto end = text.find('@', cursor + 1);
                if (end == std::string::npos) break;
                references.push_back(text.substr(cursor + 1, end - cursor - 1));
                cursor = end + 1;
            }
        }
        for (auto reference : references) {
            if (reference.empty() || reference.find("://") != std::string::npos) continue;
            const auto dependency = (source_root / path_from_utf8(reference)).lexically_normal();
            std::error_code ec;
            const auto relative = fs::relative(dependency, source_root, ec);
            if (ec) diagnostics.push_back({"unsafe_dependency", "Unable to relativize model dependency", dependency});
            else add_dependency(files, diagnostics, dependency, relative);
        }
    } else if (extension == ".fbx" || extension == ".usdc") {
        static const std::set<std::string> sidecar_extensions = {
            ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".webp", ".hdr", ".exr", ".mtl", ".bin"};
        std::error_code ec;
        for (fs::recursive_directory_iterator iterator(source_root, ec), end;
             !ec && iterator != end; iterator.increment(ec)) {
            if (!iterator->is_regular_file(ec) || iterator->path() == source) continue;
            if (!sidecar_extensions.contains(lower(iterator->path().extension().string()))) continue;
            const auto relative = fs::relative(iterator->path(), source_root, ec);
            if (!ec) add_dependency(files, diagnostics, iterator->path(), relative);
        }
    }
    return files;
}

std::string sha256_bytes(const std::vector<std::byte>& bytes) {
    BCRYPT_ALG_HANDLE algorithm{};
    BCRYPT_HASH_HANDLE hash{};
    DWORD object_size{};
    DWORD hash_size{};
    DWORD copied{};
    std::vector<UCHAR> object;
    std::vector<UCHAR> digest;
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) != 0 ||
        BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, reinterpret_cast<PUCHAR>(&object_size), sizeof(object_size), &copied, 0) != 0 ||
        BCryptGetProperty(algorithm, BCRYPT_HASH_LENGTH, reinterpret_cast<PUCHAR>(&hash_size), sizeof(hash_size), &copied, 0) != 0) {
        if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
        throw std::runtime_error("Unable to initialize SHA-256");
    }
    object.resize(object_size);
    digest.resize(hash_size);
    if (BCryptCreateHash(algorithm, &hash, object.data(), object_size, nullptr, 0, 0) != 0 ||
        BCryptHashData(hash, reinterpret_cast<PUCHAR>(const_cast<std::byte*>(bytes.data())), static_cast<ULONG>(bytes.size()), 0) != 0 ||
        BCryptFinishHash(hash, digest.data(), hash_size, 0) != 0) {
        if (hash) BCryptDestroyHash(hash);
        BCryptCloseAlgorithmProvider(algorithm, 0);
        throw std::runtime_error("Unable to compute SHA-256");
    }
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(algorithm, 0);
    std::ostringstream result;
    for (const auto byte : digest) result << std::hex << std::setw(2) << std::setfill('0') << static_cast<int>(byte);
    return result.str();
}

std::vector<std::byte> read_bytes(const fs::path& path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) throw std::runtime_error("Unable to open file: " + path.string());
    const auto size = stream.tellg();
    stream.seekg(0);
    std::vector<std::byte> bytes(static_cast<size_t>(size));
    stream.read(reinterpret_cast<char*>(bytes.data()), size);
    return bytes;
}

std::string bundle_hash(std::vector<SourceFile> files) {
    std::sort(files.begin(), files.end(), [](const auto& left, const auto& right) {
        return left.relative.generic_u8string() < right.relative.generic_u8string();
    });
    std::vector<std::byte> aggregate;
    for (const auto& file : files) {
        const auto relative = path_utf8(file.relative);
        const auto bytes = read_bytes(file.source);
        aggregate.insert(aggregate.end(), reinterpret_cast<const std::byte*>(relative.data()),
                         reinterpret_cast<const std::byte*>(relative.data() + relative.size()));
        aggregate.push_back(std::byte{0});
        aggregate.insert(aggregate.end(), bytes.begin(), bytes.end());
    }
    return sha256_bytes(aggregate);
}

nlohmann::json manifest_json(const std::vector<ImportResult>& bundles) {
    nlohmann::json result = {{"format", "corona_scene_assets"}, {"version", 1}, {"bundles", nlohmann::json::array()}};
    for (const auto& bundle : bundles) {
        nlohmann::json files = nlohmann::json::array();
        for (const auto& file : bundle.files) {
            files.push_back({{"path", file.route}, {"sha256", file.sha256}, {"size", file.size}});
        }
        result["bundles"].push_back({{"type", bundle.type}, {"sha256", bundle.bundle_sha256},
                                     {"main", bundle.main_route}, {"files", std::move(files)},
                                     {"dependencies", bundle.dependencies}});
    }
    return result;
}

std::string safe_category(std::string_view category) {
    static const std::set<std::string> allowed = {"Models", "Actors", "Images", "Scripts", "Terrain", "Vision"};
    const std::string value(category);
    if (!allowed.contains(value)) throw std::invalid_argument("Unsupported asset category: " + value);
    return value;
}

ImportResult import_collected_files(const fs::path& root,
                                    std::vector<ImportResult>& bundles,
                                    std::vector<SourceFile> files,
                                    std::string type,
                                    std::string category,
                                    const fs::path& source) {
    ImportResult result;
    result.type = std::move(type);
    try {
        result.bundle_sha256 = bundle_hash(files);
        const auto bundle_rel = fs::path("Assets") / safe_category(category) /
                                result.bundle_sha256.substr(0, 12);
        const auto destination = root / bundle_rel;
        const auto staging = root / ".asset-stage" / result.bundle_sha256;
        std::error_code ec;
        fs::remove_all(staging, ec);
        for (const auto& file : files) {
            const auto target = staging / file.relative;
            fs::create_directories(target.parent_path());
            fs::copy_file(file.source, target, fs::copy_options::overwrite_existing);
            ImportedFile imported;
            imported.source = file.source;
            imported.route = path_utf8(bundle_rel / file.relative);
            imported.sha256 = sha256_file(file.source);
            imported.size = fs::file_size(file.source);
            result.files.push_back(std::move(imported));
        }
        if (!fs::exists(destination)) {
            fs::create_directories(destination.parent_path());
            fs::rename(staging, destination);
        } else {
            fs::remove_all(staging, ec);
        }
        fs::remove(root / ".asset-stage", ec);
        result.main_route = path_utf8(bundle_rel / files.front().relative);
        for (const auto& file : result.files) {
            if (file.route != result.main_route) result.dependencies.push_back(file.route);
        }
        const auto existing = std::find_if(bundles.begin(), bundles.end(), [&](const ImportResult& item) {
            return item.bundle_sha256 == result.bundle_sha256 && item.type == result.type;
        });
        if (existing == bundles.end()) bundles.push_back(result);
    } catch (const std::exception& error) {
        result.main_route.clear();
        result.diagnostics.push_back({"asset_import_failed", error.what(), source});
        std::error_code ec;
        fs::remove_all(root / ".asset-stage", ec);
    }
    return result;
}

void write_ini_file(const fs::path& path,
                    const std::map<std::string, std::map<std::string, std::string>>& ini) {
    fs::create_directories(path.parent_path());
    std::ofstream stream(path, std::ios::binary | std::ios::trunc);
    if (!stream) throw std::runtime_error("Unable to write scene.ini");
    for (const auto& [section, values] : ini) {
        stream << '[' << section << "]\n";
        for (const auto& [key, value] : values) stream << key << " = " << value << '\n';
        stream << '\n';
    }
}

struct LegacyPaths {
    fs::path project_root;
    fs::path scene_file;
};

std::optional<LegacyPaths> locate_legacy_scene(const fs::path& input,
                                               std::vector<Diagnostic>& diagnostics) {
    auto source = fs::absolute(input).lexically_normal();
    if (fs::is_directory(source)) source /= "project.ini";
    if (source.filename() == "project.ini") {
        if (!fs::is_regular_file(source)) {
            diagnostics.push_back({"missing_project", "Legacy project.ini is missing", source});
            return std::nullopt;
        }
        const auto project = read_ini(source);
        auto route = fs::path("Scene") / "default.scene";
        if (const auto section = project.find("Project"); section != project.end() &&
            section->second.contains("entrance_scene")) {
            route = path_from_utf8(section->second.at("entrance_scene"));
        }
        const auto scene = source.parent_path() / route;
        if (!fs::is_regular_file(scene)) {
            diagnostics.push_back({"missing_scene", "Legacy scene file is missing", scene});
            return std::nullopt;
        }
        return LegacyPaths{source.parent_path(), scene};
    }
    if (lower(source.extension().string()) == ".scene" && fs::is_regular_file(source)) {
        auto root = source.parent_path();
        if (lower(root.filename().string()) == "scene") root = root.parent_path();
        return LegacyPaths{root, source};
    }
    diagnostics.push_back({"unsupported_legacy_source", "Expected project.ini or a legacy .scene", source});
    return std::nullopt;
}

fs::path resolve_legacy_route(const fs::path& project_root, std::string_view route) {
    const auto path = path_from_utf8(route);
    return path.is_absolute() ? path : project_root / path;
}

}  // namespace

bool is_valid_asset_route(std::string_view route) {
    if (route.empty() || route.find('\\') != std::string_view::npos) return false;
    const auto path = path_from_utf8(route);
    if (!is_relative_inside(path)) return false;
    const auto iterator = path.begin();
    return iterator != path.end() && *iterator == "Assets";
}

std::optional<SceneFolderLayout> detect_scene_folder(const fs::path& input) {
    auto root = fs::is_directory(input) ? input : input.parent_path();
    const auto scene_file = fs::is_directory(input) ? input / "scene.ini" : input;
    if (scene_file.filename() != "scene.ini" || !fs::is_regular_file(scene_file)) return std::nullopt;
    const auto ini = read_ini(scene_file);
    const auto format = ini.find("format");
    if (format == ini.end() || !format->second.contains("type") ||
        format->second.at("type") != "corona_scene_folder" ||
        !format->second.contains("version") || format->second.at("version") != "1") return std::nullopt;
    SceneFolderLayout layout{root, scene_file};
    if (const auto scene = ini.find("scene"); scene != ini.end() && scene->second.contains("name")) {
        layout.scene_name = scene->second.at("name");
    }
    if (layout.scene_name.empty()) layout.scene_name = path_utf8(root.filename());
    return layout;
}

std::optional<SceneFolderLayout> create_scene_folder(const fs::path& root,
                                                     std::string_view scene_name) {
    if (root.empty() || fs::exists(root)) return std::nullopt;
    const auto staging = root.parent_path() / ("." + root.filename().string() + ".creating");
    std::error_code ec;
    fs::remove_all(staging, ec);
    try {
        fs::create_directories(staging / "Assets");
        std::map<std::string, std::map<std::string, std::string>> ini;
        ini["format"] = {{"type", "corona_scene_folder"}, {"version", "1"}};
        ini["scene"] = {{"name", scene_name.empty() ? root.filename().string() : std::string(scene_name)}};
        ini["sun"] = {{"sun_direction", "1.0, 1.0, 1.0"}, {"enabled", "true"}};
        ini["grid"] = {{"enabled", "true"}};
        ini["actors"] = {};
        ini["scripts"] = {{"path", ""}};
        ini["terrain"] = {{"type", ""}, {"path", ""}};
        write_ini_file(staging / "scene.ini", ini);
        SceneAssetStore store(staging);
        if (!store.write_manifest()) throw std::runtime_error("Unable to create asset manifest");
        fs::rename(staging, root);
        return detect_scene_folder(root);
    } catch (...) {
        fs::remove_all(staging, ec);
        return std::nullopt;
    }
}

std::string sha256_file(const fs::path& path) {
    return sha256_bytes(read_bytes(path));
}

SceneAssetStore::SceneAssetStore(fs::path scene_root) : root_(std::move(scene_root)) {
    const auto manifest = root_ / "assets.manifest.json";
    if (!fs::is_regular_file(manifest)) return;
    try {
        std::ifstream stream(manifest);
        const auto document = nlohmann::json::parse(stream);
        if (document.value("format", "") != "corona_scene_assets" ||
            document.value("version", 0) != 1 || !document.contains("bundles") ||
            !document["bundles"].is_array()) return;
        for (const auto& item : document["bundles"]) {
            ImportResult bundle;
            bundle.type = item.value("type", "model");
            bundle.bundle_sha256 = item.value("sha256", "");
            bundle.main_route = item.value("main", "");
            if (item.contains("files") && item["files"].is_array()) {
                for (const auto& file_item : item["files"]) {
                    ImportedFile file;
                    file.route = file_item.value("path", "");
                    file.sha256 = file_item.value("sha256", "");
                    file.size = file_item.value("size", std::uint64_t{});
                    bundle.files.push_back(std::move(file));
                }
            }
            if (item.contains("dependencies") && item["dependencies"].is_array()) {
                for (const auto& dependency : item["dependencies"]) {
                    if (dependency.is_string()) bundle.dependencies.push_back(dependency.get<std::string>());
                }
            }
            if (!bundle.bundle_sha256.empty() && !bundle.main_route.empty()) {
                bundles_.push_back(std::move(bundle));
            }
        }
    } catch (...) {
        bundles_.clear();
    }
}

ImportResult SceneAssetStore::import_model(const fs::path& source) {
    ImportResult result;
    auto files = collect_bundle(fs::absolute(source).lexically_normal(), result.diagnostics);
    if (!result.diagnostics.empty()) return result;
    return import_collected_files(root_, bundles_, std::move(files), "model", "Models", source);
}

ImportResult SceneAssetStore::import_file(const fs::path& source, std::string_view category) {
    ImportResult result;
    const auto absolute = fs::absolute(source).lexically_normal();
    std::vector<SourceFile> files;
    add_dependency(files, result.diagnostics, absolute, absolute.filename());
    if (!result.diagnostics.empty()) return result;
    return import_collected_files(root_, bundles_, std::move(files), lower(std::string(category)),
                                  std::string(category), source);
}

ImportResult SceneAssetStore::import_actor(const fs::path& actor_source,
                                           const fs::path& model_source) {
    auto model = import_model(model_source);
    if (!model.ok()) return model;

    ImportResult result;
    const auto preparation = root_ / ".actor-prep";
    const auto prepared_actor = preparation / actor_source.filename();
    std::error_code ec;
    try {
        auto ini = read_ini(actor_source);
        if (!ini.contains("base")) {
            result.diagnostics.push_back({"invalid_actor", "Actor file has no [base] section", actor_source});
            return result;
        }
        ini["base"]["path"] = model.main_route;
        fs::remove_all(preparation, ec);
        write_ini_file(prepared_actor, ini);
        result = import_file(prepared_actor, "Actors");
        if (result.ok()) {
            result.dependencies.push_back(model.main_route);
            const auto stored = std::find_if(bundles_.begin(), bundles_.end(), [&](const ImportResult& bundle) {
                return bundle.bundle_sha256 == result.bundle_sha256 && bundle.type == result.type;
            });
            if (stored != bundles_.end() &&
                std::find(stored->dependencies.begin(), stored->dependencies.end(), model.main_route) ==
                    stored->dependencies.end()) {
                stored->dependencies.push_back(model.main_route);
            }
        }
        fs::remove_all(preparation, ec);
        return result;
    } catch (const std::exception& error) {
        fs::remove_all(preparation, ec);
        result.diagnostics.push_back({"actor_import_failed", error.what(), actor_source});
        return result;
    }
}

bool SceneAssetStore::write_manifest() const {
    try {
        fs::create_directories(root_);
        const auto target = root_ / "assets.manifest.json";
        const auto temporary = root_ / "assets.manifest.json.tmp";
        {
            std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
            stream << manifest_json(bundles_).dump(2) << '\n';
            if (!stream) return false;
        }
        std::error_code ec;
        fs::remove(target, ec);
        fs::rename(temporary, target);
        return true;
    } catch (...) {
        return false;
    }
}

std::vector<Diagnostic> SceneAssetStore::validate_manifest() const {
    std::vector<Diagnostic> diagnostics;
    const auto manifest_path = root_ / "assets.manifest.json";
    try {
        std::ifstream stream(manifest_path);
        const auto document = nlohmann::json::parse(stream);
        if (document.value("format", "") != "corona_scene_assets" || document.value("version", 0) != 1 ||
            !document.contains("bundles") || !document["bundles"].is_array()) {
            diagnostics.push_back({"invalid_manifest", "Unsupported asset manifest", manifest_path});
            return diagnostics;
        }
        std::set<std::string> manifest_routes;
        for (const auto& bundle : document["bundles"]) {
            if (!bundle.contains("files") || !bundle["files"].is_array()) continue;
            for (const auto& item : bundle["files"]) {
                const auto route = item.value("path", "");
                if (is_valid_asset_route(route)) manifest_routes.insert(route);
            }
        }
        for (const auto& bundle : document["bundles"]) {
            if (!bundle.contains("files") || !bundle["files"].is_array() ||
                !bundle.contains("dependencies") || !bundle["dependencies"].is_array()) {
                diagnostics.push_back({"invalid_manifest", "Bundle has no files", manifest_path});
                continue;
            }
            const auto main_route = bundle.value("main", "");
            if (!is_valid_asset_route(main_route)) {
                diagnostics.push_back({"unsafe_route", "Bundle main resource has an unsafe route",
                                       path_from_utf8(main_route)});
                continue;
            }
            std::set<std::string> listed_routes;
            std::vector<SourceFile> hash_files;
            const auto main_path = path_from_utf8(main_route);
            fs::path bundle_root;
            int component_count = 0;
            for (const auto& component : main_path) {
                if (component_count++ == 3) break;
                bundle_root /= component;
            }
            for (const auto& item : bundle["files"]) {
                const auto route = item.value("path", "");
                if (!is_valid_asset_route(route)) {
                    diagnostics.push_back({"unsafe_route", "Manifest contains an unsafe route", path_from_utf8(route)});
                    continue;
                }
                listed_routes.insert(route);
                const auto path = root_ / path_from_utf8(route);
                if (!fs::is_regular_file(path)) {
                    diagnostics.push_back({"missing_asset", "Manifest asset is missing", path});
                } else if (sha256_file(path) != item.value("sha256", "")) {
                    diagnostics.push_back({"hash_mismatch", "Manifest asset hash mismatch", path});
                } else if (fs::file_size(path) != item.value("size", std::uint64_t{})) {
                    diagnostics.push_back({"size_mismatch", "Manifest asset size mismatch", path});
                } else {
                    std::error_code relative_ec;
                    const auto relative = fs::relative(path_from_utf8(route), bundle_root, relative_ec);
                    if (relative_ec || !is_relative_inside(relative)) {
                        diagnostics.push_back({"unsafe_route", "Manifest file escapes its bundle", path});
                    } else {
                        hash_files.push_back({path, relative});
                    }
                }
            }
            if (!listed_routes.contains(main_route)) {
                diagnostics.push_back({"invalid_manifest", "Bundle main resource is not listed", manifest_path});
            }
            std::set<std::string> expected_dependencies = listed_routes;
            expected_dependencies.erase(main_route);
            std::set<std::string> actual_dependencies;
            for (const auto& dependency : bundle["dependencies"]) {
                if (!dependency.is_string() || !is_valid_asset_route(dependency.get<std::string>())) {
                    diagnostics.push_back({"unsafe_route", "Bundle dependency has an unsafe route", manifest_path});
                    continue;
                }
                const auto route = dependency.get<std::string>();
                actual_dependencies.insert(route);
                if (!manifest_routes.contains(route)) {
                    diagnostics.push_back({"missing_dependency", "Bundle dependency is not listed in the manifest",
                                           path_from_utf8(route)});
                }
            }
            for (const auto& dependency : expected_dependencies) {
                if (!actual_dependencies.contains(dependency)) {
                    diagnostics.push_back({"invalid_dependencies", "Bundle file dependency is not recorded",
                                           path_from_utf8(dependency)});
                }
            }
            if (hash_files.size() == listed_routes.size() && !hash_files.empty() &&
                bundle_hash(hash_files) != bundle.value("sha256", "")) {
                diagnostics.push_back({"bundle_hash_mismatch", "Manifest bundle hash mismatch", manifest_path});
            }
        }
    } catch (const std::exception& error) {
        diagnostics.push_back({"invalid_manifest", error.what(), manifest_path});
    }
    return diagnostics;
}

bool SceneAssetStore::contains_route(std::string_view route) const {
    if (!is_valid_asset_route(route)) return false;
    return std::any_of(bundles_.begin(), bundles_.end(), [&](const ImportResult& bundle) {
        return std::any_of(bundle.files.begin(), bundle.files.end(), [&](const ImportedFile& file) {
            return file.route == route;
        });
    });
}

LegacyMigrationResult migrate_legacy_scene(const LegacyMigrationRequest& request) {
    LegacyMigrationResult result;
    if (request.target_root.empty()) {
        result.diagnostics.push_back({"empty_target", "Target scene folder is empty", request.target_root});
        return result;
    }
    const auto target = fs::absolute(request.target_root).lexically_normal();
    if (fs::exists(target)) {
        result.diagnostics.push_back({"target_exists", "Target scene folder already exists", target});
        return result;
    }
    const auto legacy = locate_legacy_scene(request.source_path, result.diagnostics);
    if (!legacy) return result;

    const auto staging = target.parent_path() / ("." + target.filename().string() + ".migrating");
    std::error_code ec;
    fs::remove_all(staging, ec);
    try {
        fs::create_directories(staging);
        auto ini = read_ini(legacy->scene_file);
        auto name = request.scene_name;
        if (name.empty()) {
            if (const auto base = ini.find("base"); base != ini.end() && base->second.contains("name")) {
                name = base->second.at("name");
            }
        }
        if (name.empty()) name = target.filename().string();
        ini.erase("base");
        ini.erase("Project");
        ini["format"] = {{"type", "corona_scene_folder"}, {"version", "1"}};
        ini["scene"] = {{"name", name}};

        SceneAssetStore store(staging);
        if (auto actors = ini.find("actors"); actors != ini.end()) {
            std::vector<std::string> route_keys;
            for (const auto& [key, value] : actors->second) {
                if (key.size() > 6 && key.ends_with(".route")) route_keys.push_back(key);
            }
            for (const auto& route_key : route_keys) {
                const auto actor_key = route_key.substr(0, route_key.size() - 6);
                const auto type_key = actor_key + ".actor_type";
                const auto actor_type = actors->second.contains(type_key) ? actors->second.at(type_key) : "model";
                const auto source = resolve_legacy_route(legacy->project_root, actors->second.at(route_key));
                ImportResult imported;
                if (actor_type == "ui_image") {
                    imported = store.import_file(source, "Images");
                } else if (actor_type == "actor" && lower(source.extension().string()) == ".actor") {
                    const auto actor_ini = read_ini(source);
                    const auto model_route = actor_ini.contains("base") && actor_ini.at("base").contains("path")
                                                 ? actor_ini.at("base").at("path")
                                                 : std::string{};
                    if (model_route.empty()) {
                        imported.diagnostics.push_back({"invalid_actor", "Actor file is missing [base].path", source});
                    } else {
                        imported = store.import_actor(source, resolve_legacy_route(legacy->project_root, model_route));
                    }
                } else {
                    imported = store.import_model(source);
                }
                if (!imported.ok()) {
                    for (auto diagnostic : imported.diagnostics) {
                        diagnostic.actor = actor_key;
                        result.diagnostics.push_back(std::move(diagnostic));
                    }
                } else {
                    actors->second[route_key] = imported.main_route;
                }
            }
            std::vector<std::string> texture_keys;
            for (const auto& [key, value] : actors->second) {
                if (key.ends_with(".material.texture") && !trim(value).empty()) texture_keys.push_back(key);
            }
            for (const auto& texture_key : texture_keys) {
                const auto source = resolve_legacy_route(legacy->project_root, actors->second.at(texture_key));
                const auto imported = store.import_file(source, "Images");
                if (!imported.ok()) {
                    const auto suffix_size = std::string(".material.texture").size();
                    const auto actor_key = texture_key.substr(0, texture_key.size() - suffix_size);
                    for (auto diagnostic : imported.diagnostics) {
                        diagnostic.actor = actor_key;
                        result.diagnostics.push_back(std::move(diagnostic));
                    }
                } else {
                    actors->second[texture_key] = imported.main_route;
                }
            }
        }

        const auto migrate_section_path = [&](const char* section_name, const char* key,
                                              std::string_view category) {
            auto section = ini.find(section_name);
            if (section == ini.end() || !section->second.contains(key) ||
                trim(section->second.at(key)).empty()) return;
            const auto source = resolve_legacy_route(legacy->project_root, section->second.at(key));
            const auto imported = store.import_file(source, category);
            if (!imported.ok()) {
                result.diagnostics.insert(result.diagnostics.end(), imported.diagnostics.begin(),
                                          imported.diagnostics.end());
            } else {
                section->second[key] = imported.main_route;
            }
        };
        migrate_section_path("scripts", "path", "Scripts");
        migrate_section_path("terrain", "path", "Terrain");
        migrate_section_path("vision", "source_path", "Vision");

        if (!result.diagnostics.empty()) throw std::runtime_error("Legacy assets are incomplete");
        write_ini_file(staging / "scene.ini", ini);
        if (!store.write_manifest()) throw std::runtime_error("Unable to write asset manifest");
        const auto validation = store.validate_manifest();
        if (!validation.empty()) {
            result.diagnostics.insert(result.diagnostics.end(), validation.begin(), validation.end());
            throw std::runtime_error("Migrated assets failed validation");
        }
        if (!detect_scene_folder(staging)) throw std::runtime_error("Migrated scene.ini failed validation");
        fs::rename(staging, target);
        result.root = target;
    } catch (const std::exception& error) {
        if (result.diagnostics.empty()) {
            result.diagnostics.push_back({"migration_failed", error.what(), request.source_path});
        }
        fs::remove_all(staging, ec);
        result.root.clear();
    }
    return result;
}

}  // namespace Corona::Systems::UI::SceneFolders
