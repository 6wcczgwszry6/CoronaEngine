//
// Created by Zero on 06/09/2022.
//

#include "project_desc.h"
#include "json_util.h"
#include "core/util/logging.h"

namespace {

using namespace vision;

void warn_invalid_scene_schema(const string &message) {
    ocarina::core::logger().warn(message);
}

[[nodiscard]] string join_keys(const vector<string> &keys) {
    string result;
    for (size_t i = 0; i < keys.size(); ++i) {
        if (i != 0u) {
            result.append(", ");
        }
        result.push_back('\'');
        result.append(keys[i]);
        result.push_back('\'');
    }
    return result;
}

[[nodiscard]] bool is_known_top_level_key(string_view key) {
    return key == "scene" || key == "render" || key == "pipeline" || key == "output";
}

[[nodiscard]] bool is_legacy_top_level_key(string_view key) {
    return key == "camera" || key == "materials" || key == "mediums" || key == "shapes" ||
           key == "lights" || key == "sampler" || key == "spectrum" || key == "integrator" ||
           key == "light_sampler" || key == "warper" || key == "render_setting" || key == "denoiser";
}

[[nodiscard]] bool is_known_output_key(string_view key) {
    return key == "fn" || key == "spp" || key == "save_exit" || key == "denoise";
}

[[nodiscard]] DataWrap &ensure_object_member(DataWrap &parent,
                                             string_view key,
                                             string_view label) {
    if (!parent.contains(key)) {
        warn_invalid_scene_schema(format("invalid scene schema: missing block '{}'", label));
        parent[string(key)] = DataWrap::object();
    }
    DataWrap &child = parent[string(key)];
    if (!child.is_object()) {
        warn_invalid_scene_schema(format("invalid scene schema: '{}' must be an object", label));
        child = DataWrap::object();
    }
    return child;
}

void ensure_array_member(DataWrap &parent,
                         string_view key,
                         string_view label) {
    if (!parent.contains(key)) {
        warn_invalid_scene_schema(format("invalid scene schema: missing block '{}'", label));
        parent[string(key)] = DataWrap::array();
    }
    DataWrap &child = parent[string(key)];
    if (!child.is_array()) {
        warn_invalid_scene_schema(format("invalid scene schema: '{}' must be an array", label));
        child = DataWrap::array();
    }
}

[[nodiscard]] DataWrap &ensure_typed_object_member(DataWrap &parent,
                                                   string_view key,
                                                   string_view label) {
    DataWrap &child = ensure_object_member(parent, key, label);
    if (!child.contains("type") || !child.at("type").is_string()) {
        warn_invalid_scene_schema(format("invalid scene schema: '{}' requires string field 'type'", label));
    }
    return child;
}

void validate_scene_block(DataWrap &scene_data) {
    [[maybe_unused]] DataWrap &camera = ensure_typed_object_member(scene_data, "camera", "scene.camera");
    ensure_array_member(scene_data, "materials", "scene.materials");
    ensure_array_member(scene_data, "shapes", "scene.shapes");
    ensure_array_member(scene_data, "lights", "scene.lights");
    if (scene_data.contains("mediums")) {
        DataWrap &mediums = ensure_object_member(scene_data, "mediums", "scene.mediums");
        ensure_array_member(mediums, "list", "scene.mediums.list");
    }
}

void validate_render_block(DataWrap &render_data) {
    [[maybe_unused]] DataWrap &sampler = ensure_typed_object_member(render_data, "sampler", "render.sampler");
    [[maybe_unused]] DataWrap &integrator = ensure_typed_object_member(render_data, "integrator", "render.integrator");
    [[maybe_unused]] DataWrap &light_sampler = ensure_typed_object_member(render_data, "light_sampler", "render.light_sampler");
    if (render_data.contains("spectrum")) {
        [[maybe_unused]] DataWrap &spectrum = ensure_typed_object_member(render_data, "spectrum", "render.spectrum");
    }
    [[maybe_unused]] DataWrap &render_setting = ensure_object_member(render_data, "render_setting", "render.render_setting");
    if (render_data.contains("warper")) {
        [[maybe_unused]] DataWrap &warper = ensure_typed_object_member(render_data, "warper", "render.warper");
    }
    if (render_data.contains("denoiser")) {
        [[maybe_unused]] DataWrap &denoiser = ensure_typed_object_member(render_data, "denoiser", "render.denoiser");
    }
}

void validate_pipeline_block(DataWrap &pipeline_data) {
    DataWrap &pipeline = ensure_typed_object_member(pipeline_data, "pipeline", "pipeline");
    DataWrap &param = ensure_object_member(pipeline, "param", "pipeline.param");
    [[maybe_unused]] DataWrap &frame_buffer = ensure_typed_object_member(param, "frame_buffer", "pipeline.param.frame_buffer");
    [[maybe_unused]] DataWrap &rasterizer = ensure_typed_object_member(param, "rasterizer", "pipeline.param.rasterizer");
    if (param.contains("uv_unwrapper")) {
        [[maybe_unused]] DataWrap &uv_unwrapper = ensure_typed_object_member(param, "uv_unwrapper", "pipeline.param.uv_unwrapper");
    }
}

void validate_output_block(DataWrap &data) {
    if (data.contains("output") && !data.at("output").is_object()) {
        warn_invalid_scene_schema("invalid scene schema: 'output' must be an object");
        data["output"] = DataWrap::object();
    }
    if (!data.contains("output")) {
        return;
    }
    DataWrap &output = data["output"];
    for (const auto &item : output.items()) {
        const string &key = item.key();
        if (key == "resolution") {
            warn_invalid_scene_schema(
                "invalid scene schema: 'output.resolution' is not supported; use 'pipeline.param.frame_buffer.param.resolution'");
            continue;
        }
        if (!is_known_output_key(key)) {
            warn_invalid_scene_schema(format("invalid scene schema: unknown output field 'output.{}'", key));
        }
    }
}

void validate_project_schema(DataWrap &data) {
    if (!data.is_object()) {
        warn_invalid_scene_schema("invalid scene schema: root must be an object");
        data = DataWrap::object();
    }

    vector<string> missing_blocks;
    for (string_view key : {string_view{"scene"}, string_view{"render"}, string_view{"pipeline"}}) {
        if (!data.contains(key)) {
            missing_blocks.emplace_back(key);
            data[string(key)] = DataWrap::object();
        }
    }

    bool has_legacy_top_level_key = false;
    for (const auto &item : data.items()) {
        const string &key = item.key();
        if (is_legacy_top_level_key(key)) {
            has_legacy_top_level_key = true;
        }
        if (!is_known_top_level_key(key)) {
            ocarina::core::logger().warn(format("unknown top-level key '{}'", key));
        }
    }

    if (!missing_blocks.empty()) {
        if (has_legacy_top_level_key) {
            warn_invalid_scene_schema("invalid scene schema: old flat top-level format is not supported");
        }
        string message = "invalid scene schema: missing top-level block";
        if (missing_blocks.size() > 1u) {
            message.push_back('s');
        }
        message.append(" ");
        message.append(join_keys(missing_blocks));
        warn_invalid_scene_schema(message);
    }

    validate_scene_block(ensure_object_member(data, "scene", "scene"));
    validate_render_block(ensure_object_member(data, "render", "render"));
    validate_pipeline_block(data);
    validate_output_block(data);
}

}// namespace

namespace vision {

void SceneDesc::init_material_descs(const DataWrap &materials) noexcept {
    for (uint i = 0; i < materials.size(); ++i) {
        MaterialDesc md;
        md.init(materials[i]);
        material_descs.push_back(md);
    }
}

void SceneDesc::init_shape_descs(const DataWrap &shapes) noexcept {
    for (const auto &shape : shapes) {
        ShapeDesc sd;
        sd.init(shape);
        shape_descs.push_back(sd);
    }
}

void SceneDesc::init_medium_descs(const DataWrap &mediums) noexcept {
    mediums_desc.global = mediums.value("global", "");
    mediums_desc.process = mediums.value("process", true);
    DataWrap lst = mediums.value("list", DataWrap::object());
    for (const auto &elm : lst) {
        MediumDesc desc;
        desc.init(elm);
        mediums_desc.mediums.push_back(desc);
    }
}

void SceneDesc::init_light_descs(const DataWrap &lights) noexcept {
    for (const auto &light : lights) {
        LightDesc desc;
        desc.init(light);
        light_descs.push_back(desc);
    }
}

void ProjectDesc::init(const DataWrap &data) noexcept {
    DataWrap scene_data = data.value("scene", DataWrap::object());
    DataWrap render_data = data.value("render", DataWrap::object());

    // scene_desc
    scene_desc.init_material_descs(scene_data.value("materials", DataWrap::object()));
    scene_desc.init_medium_descs(scene_data.value("mediums", DataWrap::object()));
    scene_desc.init_shape_descs(scene_data.value("shapes", DataWrap::object()));
    scene_desc.init_light_descs(scene_data.value("lights", DataWrap::array()));
    scene_desc.sensor_desc.init(scene_data.value("camera", DataWrap::object()));
    scene_desc.sensor_desc.medium.name = scene_desc.mediums_desc.global;

    // renderer_desc
    renderer_desc.integrator_desc.init(render_data.value("integrator", DataWrap::object()));
    renderer_desc.spectrum_desc.init(render_data.value("spectrum", DataWrap::object()));
    renderer_desc.light_sampler_desc.init(render_data.value("light_sampler", DataWrap::object()));
    renderer_desc.sampler_desc.init(render_data.value("sampler", DataWrap::object()));
    renderer_desc.warper_desc.init(render_data.value("warper", DataWrap::object()));
    renderer_desc.render_setting.init(render_data.value("render_setting", DataWrap::object()));
    renderer_desc.denoiser_desc.init(render_data.value("denoiser", DataWrap::object()));

    // project level
    output_desc.init(data.value("output", DataWrap::object()));
    pipeline_desc.init(data.value("pipeline", DataWrap::object()));
}

ProjectDesc ProjectDesc::from_json(const fs::path &path) {
    ProjectDesc project_desc;
    project_desc.scene_path = path.parent_path();
    DataWrap data = create_json_from_file(path);
    validate_project_schema(data);
    project_desc.init(data);
    return project_desc;
}

}// namespace vision