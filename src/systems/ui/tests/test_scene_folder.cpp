#include "cef/scene_folder.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string_view>

#include <nlohmann/json.hpp>

namespace fs = std::filesystem;
using namespace Corona::Systems::UI::SceneFolders;

namespace {

[[noreturn]] void fail(std::string_view message) {
    std::cerr << "FAIL: " << message << '\n';
    std::exit(1);
}

void expect(bool condition, std::string_view message) {
    if (!condition) fail(message);
}

void write_text(const fs::path& path, std::string_view value) {
    fs::create_directories(path.parent_path());
    std::ofstream stream(path, std::ios::binary | std::ios::trunc);
    stream << value;
}

struct TempDir {
    fs::path path = fs::temp_directory_path() / "corona_scene_folder_tests";
    TempDir() {
        std::error_code ec;
        fs::remove_all(path, ec);
        fs::create_directories(path);
    }
    ~TempDir() {
        std::error_code ec;
        fs::remove_all(path, ec);
    }
};

void portable_route_validation_rejects_escape_and_absolute_paths() {
    expect(is_valid_asset_route("Assets/Models/a/model.glb"), "portable asset route should be valid");
    expect(!is_valid_asset_route("../model.glb"), "parent traversal should be rejected");
    expect(!is_valid_asset_route("D:/model.glb"), "absolute Windows path should be rejected");
    expect(!is_valid_asset_route("Resource/model.glb"), "route outside Assets should be rejected");
    expect(!is_valid_asset_route(""), "empty route should be rejected");
}

void scene_folder_detection_requires_versioned_scene_ini() {
    TempDir temp;
    write_text(temp.path / "scene.ini",
               "[format]\n"
               "type = corona_scene_folder\n"
               "version = 1\n"
               "[scene]\n"
               "name = Portable\n");
    const auto layout = detect_scene_folder(temp.path);
    expect(layout.has_value(), "portable folder should be detected");
    expect(layout->root == temp.path, "folder root should be retained");
    expect(layout->scene_file == temp.path / "scene.ini", "scene file should resolve under root");
    expect(layout->scene_name == "Portable", "scene name should be parsed");
}

void glb_import_is_content_addressed_and_manifest_validates() {
    TempDir temp;
    const auto source = temp.path / "source" / "chair.glb";
    const auto scene_root = temp.path / "scene";
    write_text(source, "glb payload");

    SceneAssetStore store(scene_root);
    const auto first = store.import_model(source);
    const auto second = store.import_model(source);
    expect(first.ok(), "GLB import should succeed");
    expect(second.ok(), "repeated GLB import should succeed");
    expect(first.main_route == second.main_route, "same content should reuse the same route");
    expect(is_valid_asset_route(first.main_route), "imported route should be portable");
    expect(fs::is_regular_file(scene_root / fs::path(first.main_route)), "imported model should exist");
    expect(store.write_manifest(), "manifest should be written");
    expect(store.validate_manifest().empty(), "fresh manifest should validate");

    {
        const auto manifest_path = scene_root / "assets.manifest.json";
        std::ifstream input(manifest_path);
        auto manifest = nlohmann::json::parse(input);
        manifest["bundles"][0]["sha256"] = std::string(64, '0');
        std::ofstream output(manifest_path, std::ios::trunc);
        output << manifest.dump(2);
    }
    expect(!store.validate_manifest().empty(), "corrupted bundle hash should fail validation");
    expect(store.write_manifest(), "manifest should be restorable after bundle hash test");

    write_text(scene_root / fs::path(first.main_route), "tampered");
    expect(!store.validate_manifest().empty(), "tampered resource should fail validation");
}

void obj_import_copies_material_and_texture_dependencies() {
    TempDir temp;
    const auto source_dir = temp.path / "source";
    write_text(source_dir / "chair.obj", "mtllib materials/chair.mtl\nv 0 0 0\n");
    write_text(source_dir / "materials" / "chair.mtl", "map_Kd ../textures/wood.png\n");
    write_text(source_dir / "textures" / "wood.png", "texture");

    SceneAssetStore store(temp.path / "scene");
    const auto result = store.import_model(source_dir / "chair.obj");
    expect(result.ok(), "OBJ bundle import should succeed");
    expect(result.files.size() == 3, "OBJ, MTL and texture should be copied");
    for (const auto& file : result.files) {
        expect(fs::is_regular_file(temp.path / "scene" / fs::path(file.route)),
               "every bundle file should exist");
    }
    expect(store.write_manifest(), "OBJ manifest should be written");
    std::ifstream manifest_stream(temp.path / "scene" / "assets.manifest.json");
    const auto manifest = nlohmann::json::parse(manifest_stream);
    const auto& bundle = manifest.at("bundles").at(0);
    expect(bundle.at("dependencies").size() == 2,
           "manifest should record the main resource dependency routes");
    expect(store.validate_manifest().empty(), "OBJ manifest relationships should validate");
}

void missing_obj_dependency_fails_without_creating_bundle() {
    TempDir temp;
    const auto source = temp.path / "source" / "broken.obj";
    write_text(source, "mtllib missing.mtl\nv 0 0 0\n");

    SceneAssetStore store(temp.path / "scene");
    const auto result = store.import_model(source);
    expect(!result.ok(), "missing dependency should fail import");
    expect(!result.diagnostics.empty(), "failure should report diagnostics");
    expect(!fs::exists(temp.path / "scene" / "Assets" / "Models"),
           "failed import should not leave a bundle");
}

void legacy_project_migrates_to_transactional_scene_folder() {
    TempDir temp;
    const auto legacy = temp.path / "legacy";
    const auto target = temp.path / "Portable";
    write_text(legacy / "project.ini",
               "[Project]\nname = Legacy\nmode = 3d\nentrance_scene = Scene/default.scene\n");
    write_text(legacy / "Scene" / "default.scene",
               "[base]\nname = Migrated\n"
               "[sun]\nsun_direction = 1, 2, 3\nenabled = true\n"
               "[actors]\n"
               "chair.actor_type = model\n"
               "chair.name = Chair\n"
               "chair.route = Resource/chair.glb\n"
               "chair.material.texture = Resource/chair.png\n"
               "chair.geometry.position = 1, 2, 3\n"
               "[scripts]\npath = Scripts/scene_script.py\n");
    write_text(legacy / "Resource" / "chair.glb", "model");
    write_text(legacy / "Resource" / "chair.png", "texture");
    write_text(legacy / "Scripts" / "scene_script.py", "print('portable')\n");
    const auto original_scene = sha256_file(legacy / "Scene" / "default.scene");

    LegacyMigrationRequest request{legacy / "project.ini", target, "Portable"};
    const auto result = migrate_legacy_scene(request);
    expect(result.ok(), "legacy project migration should succeed");
    expect(result.root == target, "migration should return the target root");
    expect(fs::is_regular_file(target / "scene.ini"), "migration should write scene.ini");
    expect(fs::is_regular_file(target / "assets.manifest.json"), "migration should write manifest");
    expect(detect_scene_folder(target).has_value(), "migrated target should be a portable scene");
    expect(sha256_file(legacy / "Scene" / "default.scene") == original_scene,
           "migration should not modify the legacy scene");

    auto ini = std::ifstream(target / "scene.ini");
    const std::string text((std::istreambuf_iterator<char>(ini)), std::istreambuf_iterator<char>());
    expect(text.find("\nmode =") == std::string::npos, "portable scene must not persist mode");
    expect(text.find("entrance_scene") == std::string::npos,
           "portable scene must not persist entrance_scene");
    expect(text.find("chair.route = Assets/Models/") != std::string::npos,
           "actor route should be rewritten into Assets");
    expect(text.find("chair.material.texture = Assets/Images/") != std::string::npos,
           "actor material texture should be rewritten into Assets");
    expect(text.find("path = Assets/Scripts/") != std::string::npos,
           "script route should be rewritten into Assets");
}

void missing_legacy_asset_aborts_without_target_directory() {
    TempDir temp;
    const auto legacy = temp.path / "legacy";
    const auto target = temp.path / "Portable";
    write_text(legacy / "project.ini",
               "[Project]\nname = Legacy\nentrance_scene = Scene/default.scene\n");
    write_text(legacy / "Scene" / "default.scene",
               "[base]\nname = Broken\n"
               "[actors]\nchair.actor_type = model\nchair.route = Resource/missing.glb\n");

    const auto result = migrate_legacy_scene({legacy / "project.ini", target, "Portable"});
    expect(!result.ok(), "migration with a missing model should fail");
    expect(!result.diagnostics.empty(), "migration failure should list diagnostics");
    expect(!fs::exists(target), "failed migration should not leave a target directory");
    expect(fs::is_regular_file(legacy / "project.ini"), "legacy source should remain intact");
}

void new_scene_folder_has_no_mode_and_an_empty_valid_manifest() {
    TempDir temp;
    const auto target = temp.path / "NewScene";
    const auto created = create_scene_folder(target, "New Scene");
    expect(created.has_value(), "new portable scene should be created");
    expect(detect_scene_folder(target).has_value(), "new portable scene should be detectable");
    SceneAssetStore store(target);
    expect(store.validate_manifest().empty(), "new scene manifest should validate");
    auto stream = std::ifstream(target / "scene.ini");
    const std::string text((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    expect(text.find("\nmode =") == std::string::npos, "new scene must not contain mode");
    expect(text.find("[actors]") != std::string::npos, "new scene should contain actors section");
}

void reopening_asset_store_preserves_existing_manifest_bundles() {
    TempDir temp;
    const auto scene = temp.path / "scene";
    write_text(temp.path / "one.glb", "one");
    write_text(temp.path / "two.glb", "two");
    {
        SceneAssetStore store(scene);
        expect(store.import_model(temp.path / "one.glb").ok(), "first model import should succeed");
        expect(store.write_manifest(), "first manifest should be written");
    }
    {
        SceneAssetStore store(scene);
        expect(store.import_model(temp.path / "two.glb").ok(), "second model import should succeed");
        expect(store.write_manifest(), "updated manifest should be written");
    }
    const auto manifest = nlohmann::json::parse(std::ifstream(scene / "assets.manifest.json"));
    expect(manifest["bundles"].size() == 2, "reopened store should retain the first bundle");
}

void gltf_import_copies_external_buffers_and_images() {
    TempDir temp;
    const auto source = temp.path / "source";
    write_text(source / "scene.gltf",
               R"({"asset":{"version":"2.0"},"buffers":[{"uri":"mesh.bin"}],"images":[{"uri":"textures/albedo.png"}]})");
    write_text(source / "mesh.bin", "buffer");
    write_text(source / "textures" / "albedo.png", "image");
    SceneAssetStore store(temp.path / "portable");
    const auto result = store.import_model(source / "scene.gltf");
    expect(result.ok(), "glTF import should succeed");
    expect(result.files.size() == 3, "glTF should include buffer and image dependencies");
}

void actor_import_rewrites_model_path_into_portable_assets() {
    TempDir temp;
    const auto source = temp.path / "source";
    write_text(source / "chair.glb", "model");
    write_text(source / "chair.actor", "[base]\nname = Chair\npath = chair.glb\n");
    SceneAssetStore store(temp.path / "portable");
    const auto result = store.import_actor(source / "chair.actor", source / "chair.glb");
    expect(result.ok(), "actor import should succeed");
    expect(result.main_route.find("Assets/Actors/") == 0,
           "actor descriptor should be stored in Assets/Actors");
    auto stream = std::ifstream(temp.path / "portable" / fs::path(result.main_route));
    const std::string text((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
    expect(text.find("path = Assets/Models/") != std::string::npos,
           "portable actor should reference its imported model");
    expect(result.dependencies.size() == 1 && result.dependencies.front().find("Assets/Models/") == 0,
           "actor bundle should record its model bundle dependency");
    expect(store.write_manifest(), "actor manifest should be written");
    expect(store.validate_manifest().empty(), "actor manifest should validate");
}

void manifest_rejects_unlisted_but_existing_asset_route() {
    TempDir temp;
    const auto scene = temp.path / "scene";
    write_text(scene / "Assets" / "Models" / "manual.glb", "unlisted");
    SceneAssetStore store(scene);
    expect(store.write_manifest(), "empty manifest should be written");
    expect(!store.contains_route("Assets/Models/manual.glb"),
           "an existing file outside the manifest must not be trusted");
}

void dae_import_collects_declared_external_texture_and_rejects_missing_one() {
    TempDir temp;
    const auto source = temp.path / "source";
    write_text(source / "scene.dae", "<COLLADA><init_from>textures/albedo.png</init_from></COLLADA>");
    write_text(source / "textures" / "albedo.png", "image");
    SceneAssetStore store(temp.path / "portable");
    const auto imported = store.import_model(source / "scene.dae");
    expect(imported.ok(), "DAE external texture should be collected");
    expect(imported.files.size() == 2, "DAE bundle should contain its declared texture");

    write_text(source / "broken.dae", "<COLLADA><init_from>textures/missing.png</init_from></COLLADA>");
    const auto broken = store.import_model(source / "broken.dae");
    expect(!broken.ok(), "DAE with missing declared texture should fail");
}

void portable_scene_reopens_after_copy_to_another_root() {
    TempDir temp;
    const auto original = temp.path / "portable";
    expect(create_scene_folder(original, "Movable").has_value(), "portable scene should be created");
    write_text(temp.path / "source" / "model.glb", "portable model");
    SceneAssetStore original_store(original);
    expect(original_store.import_model(temp.path / "source" / "model.glb").ok(),
           "portable model should import before moving");
    expect(original_store.write_manifest(), "portable manifest should be written before moving");

    const auto moved = fs::current_path() / "corona_scene_folder_moved_test";
    std::error_code ec;
    fs::remove_all(moved, ec);
    fs::copy(original, moved, fs::copy_options::recursive);
    expect(detect_scene_folder(moved).has_value(), "copied scene should be detected at its new root");
    SceneAssetStore moved_store(moved);
    expect(moved_store.validate_manifest().empty(), "copied scene assets should validate at the new root");
    fs::remove_all(moved, ec);
}

}  // namespace

int main() {
    portable_route_validation_rejects_escape_and_absolute_paths();
    scene_folder_detection_requires_versioned_scene_ini();
    glb_import_is_content_addressed_and_manifest_validates();
    obj_import_copies_material_and_texture_dependencies();
    missing_obj_dependency_fails_without_creating_bundle();
    legacy_project_migrates_to_transactional_scene_folder();
    missing_legacy_asset_aborts_without_target_directory();
    new_scene_folder_has_no_mode_and_an_empty_valid_manifest();
    reopening_asset_store_preserves_existing_manifest_bundles();
    gltf_import_copies_external_buffers_and_images();
    actor_import_rewrites_model_path_into_portable_assets();
    manifest_rejects_unlisted_but_existing_asset_route();
    dae_import_collects_declared_external_texture_and_rejects_missing_one();
    portable_scene_reopens_after_copy_to_another_root();
    std::cout << "All scene folder tests passed\n";
    return 0;
}
