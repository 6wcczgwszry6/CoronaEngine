#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace Corona::Systems::UI::SceneFolders {

struct SceneFolderLayout {
    std::filesystem::path root;
    std::filesystem::path scene_file;
    std::string scene_name;
    std::uint32_t version{1};
};

struct Diagnostic {
    std::string code;
    std::string message;
    std::filesystem::path path;
    std::string actor;
};

struct ImportedFile {
    std::filesystem::path source;
    std::string route;
    std::string sha256;
    std::uint64_t size{};
};

struct ImportResult {
    std::string type{"model"};
    std::string main_route;
    std::string bundle_sha256;
    std::vector<ImportedFile> files;
    std::vector<std::string> dependencies;
    std::vector<Diagnostic> diagnostics;

    [[nodiscard]] bool ok() const noexcept {
        return diagnostics.empty() && !main_route.empty();
    }
};

[[nodiscard]] bool is_valid_asset_route(std::string_view route);
[[nodiscard]] std::optional<SceneFolderLayout> detect_scene_folder(
    const std::filesystem::path& input);
[[nodiscard]] std::optional<SceneFolderLayout> create_scene_folder(
    const std::filesystem::path& root,
    std::string_view scene_name);
[[nodiscard]] std::string sha256_file(const std::filesystem::path& path);

class SceneAssetStore {
   public:
    explicit SceneAssetStore(std::filesystem::path scene_root);

    [[nodiscard]] ImportResult import_model(const std::filesystem::path& source);
    [[nodiscard]] ImportResult import_actor(const std::filesystem::path& actor_source,
                                            const std::filesystem::path& model_source);
    [[nodiscard]] ImportResult import_file(const std::filesystem::path& source,
                                           std::string_view category);
    [[nodiscard]] bool write_manifest() const;
    [[nodiscard]] std::vector<Diagnostic> validate_manifest() const;
    [[nodiscard]] bool contains_route(std::string_view route) const;

    [[nodiscard]] const std::filesystem::path& root() const noexcept { return root_; }

   private:
    std::filesystem::path root_;
    std::vector<ImportResult> bundles_;
};

struct LegacyMigrationRequest {
    std::filesystem::path source_path;
    std::filesystem::path target_root;
    std::string scene_name;
};

struct LegacyMigrationResult {
    std::filesystem::path root;
    std::vector<Diagnostic> diagnostics;

    [[nodiscard]] bool ok() const noexcept {
        return diagnostics.empty() && !root.empty();
    }
};

[[nodiscard]] LegacyMigrationResult migrate_legacy_scene(
    const LegacyMigrationRequest& request);

}  // namespace Corona::Systems::UI::SceneFolders
