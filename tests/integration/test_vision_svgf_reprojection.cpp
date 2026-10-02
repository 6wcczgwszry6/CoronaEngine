// Keep the renderer DSL headers separate from Corona's host math headers.
#define VISION_PLUGIN_NAME "SVGF"
#define VISION_CATEGORY "denoiser"
#include "render_core/denoiser/SVGF/svgf.h"
#include "base/sensor/sensor.h"
#include "base/sampler.h"
#include <iostream>
#include <stdexcept>
#include <vector>
#include <cstdlib>

void check_svgf_shading_guide(vision::Pipeline& pipeline) {
    using namespace vision;
    pipeline.activate_global_context();
    // Reuse the normal-mapped substrate fixture prepared by the sampling test.
    Global::SceneGpuContextScope scope{pipeline.geometry().bindless_array(), pipeline.device()};
    const auto visibility = pipeline.frame_buffer()->cur_visibility_buffer_view(pipeline.frame_index() - 1u);
    std::vector<TriangleHit> hits(pipeline.pixel_num());
    pipeline.stream() << visibility.subview(0, hits.size()).download(hits.data()) << synchronize() << commit();
    if (hits[8u * 16u + 8u].inst_id == InvalidUI32) {
        throw std::runtime_error("normal guide fixture must have visible geometry at its center");
    }
    bool& individual = MaterialRegistry::instance().individual_ns();
    struct RestoreMode { bool& mode; bool value; ~RestoreMode() { mode = value; } } restore{individual, individual};
    for (bool enabled : {true, false}) {
        individual = enabled;
        // Exercise the same visibility-buffer compute path as SVGF.
        Kernel kernel = [&](BufferVar<TriangleHit> visible, BufferVar<float4> out) {
            Float3 eye = make_float3(0.f, 0.f, 3.f);
            auto hit = visible.read(8u * 16u + 8u);
            auto it = pipeline.geometry().compute_surface_interaction(hit, eye);
            Float3 normal = svgf::PixelStateUtils::query_shading_normal(&pipeline, hit, eye);
            out.write(0u, make_float4(normal, dot(normal, it.shading.normal())));
        };
        auto shader = pipeline.device().compile(kernel, enabled ? "svgf_mapped_normal_guide" : "svgf_shared_normal_guide");
        auto out = pipeline.device().create_buffer<float4>(1, "svgf_normal_guide_test");
        float4 normal{};
        pipeline.stream() << shader(visibility, out).dispatch(1u) << out.download(&normal) << synchronize() << commit();
        const float norm2 = normal.x * normal.x + normal.y * normal.y + normal.z * normal.z;
        if (!std::isfinite(norm2) || std::abs(norm2 - 1.f) > 1e-4f ||
            (enabled ? normal.w > 0.9f : std::abs(normal.w - 1.f) > 1e-4f)) {
            throw std::runtime_error("SVGF guide must be normalized and follow the active material normal mode");
        }
    }
    std::cout << "PASS: SVGF guides follow material normals and shared-frame mode\n";
}

void check_svgf_spatial_bypass(vision::Pipeline& pipeline) {
    using namespace vision;
    pipeline.activate_global_context();
    auto* illumination = dynamic_cast<IlluminationIntegrator*>(pipeline.renderer().integrator().get());
    auto* denoiser = illumination ? dynamic_cast<svgf::SVGF*>(illumination->denoiser()) : nullptr;
    if (!denoiser) throw std::runtime_error("spatial bypass regression requires SVGF");
    struct EnvRestore {
        const char* name;
        std::string previous;
        bool present;
        static void set(const char* key, const char* value) {
#ifdef _WIN32
            _putenv_s(key, value ? value : "");
#else
            if (value) setenv(key, value, 1); else unsetenv(key);
#endif
        }
        EnvRestore(const char* key, const char* value) : name(key),
            previous(std::getenv(key) ? std::getenv(key) : ""), present(std::getenv(key) != nullptr) { set(key, value); }
        ~EnvRestore() { set(name, present ? previous.c_str() : nullptr); }
    } domain{"VISION_SVGF_RADIANCE_DOMAIN", "1"}, temporal{"VISION_SVGF_SKIP_VARIANCE", "1"},
      prefilter{"VISION_SVGF_SKIP_PREFILTER", "1"}, atrous{"VISION_SVGF_SKIP_ATROUS", "0"},
      resolve{"VISION_SVGF_SKIP_RESOLVE", "1"};
    const uint count = pipeline.pixel_num();
    std::vector<RadType4> samples(count);
    for (uint i = 0; i < count; ++i) {
        const float value = ((i % 16u + i / 16u) & 1u) ? 0.7f : 0.3f;
        samples[i] = RadType4{value, value, value, 1.f};
    }
    auto direct = pipeline.device().create_buffer<RadType4>(count, "svgf_bypass_direct");
    auto indirect = pipeline.device().create_buffer<RadType4>(count, "svgf_bypass_indirect");
    std::vector<svgf::SVGFDataDual> empty(count);
    RealTimeDenoiseInput input;
    input.resolution = pipeline.resolution();
    input.frame_index = pipeline.frame_index() - 1u;
    input.direct = direct.view(); input.indirect = indirect.view();
    input.visibility = pipeline.frame_buffer()->cur_visibility_buffer_view(input.frame_index);
    const auto eye = pipeline.scene().sensor()->position();
    input.camera_pos = {eye.x, eye.y, eye.z};
    pipeline.stream() << direct.upload(samples.data()) << indirect.upload(samples.data())
        << denoiser->svgf_data.view().upload(empty.data()) << denoiser->svgf_data2.view().upload(empty.data())
        << illumination->denoiser()->dispatch(input) << direct.download(samples.data()) << synchronize() << commit();
    const float center = static_cast<float>(samples[8u * 16u + 8u].x);
    if (!std::isfinite(center) || center < 0.35f || center > 0.65f) {
        throw std::runtime_error("bypassing temporal estimation must still spatially filter noisy geometry with empty guide caches");
    }
    std::cout << "PASS: spatial filtering survives the temporal debug bypass\n";
}

void check_substrate_sample_classification(vision::Pipeline& pipeline) {
    using namespace vision;
    pipeline.activate_global_context();
    MaterialDesc desc;
    desc.init(ParameterSet{DataWrap::parse(R"({
        "type":"substrate","name":"substrate-routing-test",
        "param":{"color":[0.8,0.5,0.2],"spec":[0.05,0.05,0.05],"roughness":0.3,
                 "normal":{"channels":"xyz","node":"guide-normal"}},
        "node_tab":{"guide-normal":{"type":"number","param":{"value":[0.6,0.0,0.8]}}}
    })")});
    auto material = Material::create_root(desc);
    pipeline.scene().add_material(material);
    pipeline.scene().instances()[0]->set_material(material);
    pipeline.scene().prepare();
    pipeline.upload_data();
    // This fixture replaces material storage outside the scene-import path.
    // Publish the new bindless slot before any shader reads normal-map data.
    pipeline.upload_scene_bindless_array();
    Global::SceneGpuContextScope scope{pipeline.geometry().bindless_array(), pipeline.device()};
    auto& sampler = pipeline.renderer().sampler();
    Kernel kernel = [&](BufferVar<uint> out) {
        sampler->load_data();
        sampler->set_seed(make_uint2(0u), dispatch_id(), Dimension::PathTracing);
        auto ray = make_ray(Float3{make_float3(0.f, 0.f, 3.f)}, Float3{make_float3(0.f, 0.f, -1.f)});
        auto hit = pipeline.geometry().trace_closest(ray);
        auto it = pipeline.geometry().compute_surface_interaction(hit, ray);
        auto swl = pipeline.renderer().integrator()->spectrum()->sample_wavelength(sampler);
        MaterialEvaluator evaluator(it, swl);
        pipeline.scene().materials().dispatch(it.material_id(), [&](const Material* current) {
            current->build_evaluator(evaluator, it, swl);
        });
        auto sampled = evaluator.sample(it.wo, sampler);
        out.write(dispatch_id(), sampled.eval.flags);
    };
    auto shader = pipeline.device().compile(kernel, "substrate_sample_classification");
    std::vector<uint> flags(32);
    auto out = pipeline.device().create_buffer<uint>(flags.size(), "substrate_flags");
    pipeline.stream() << shader(out).dispatch(static_cast<uint>(flags.size()))
                      << out.download(flags.data()) << synchronize() << commit();
    for (auto value : flags) {
        if ((value & BxDFFlag::GlossyRefl) != BxDFFlag::GlossyRefl) {
            throw std::runtime_error("substrate sampled reflection must retain the glossy flag used by its direct-light and albedo split");
        }
    }
    std::cout << "PASS: substrate samples retain glossy reflection classification\n";
}

void check_motion_visibility_history(vision::Pipeline& pipeline) {
    auto* sensor = pipeline.scene().sensor().get();
    sensor->set_position(vision::make_float3(0.f, 0.f, 3.f));
    sensor->set_yaw(0.f); sensor->set_pitch(0.f); sensor->set_fov_y(45.f);
    sensor->update_device_data();
    pipeline.invalidate();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    sensor->set_position(vision::make_float3(100.f, 0.f, 3.f));
    sensor->update_device_data();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    std::vector<vision::TriangleHit> current(pipeline.pixel_num()), previous(current.size());
    const auto rendered_frame = pipeline.frame_index() - 1u;
    // Bound downloads even on the old, incorrectly oversized half-zero view.
    const auto cur = pipeline.frame_buffer()->cur_visibility_buffer_view(rendered_frame).subview(0, current.size());
    const auto prev = pipeline.frame_buffer()->prev_visibility_buffer_view(rendered_frame).subview(0, previous.size());
    pipeline.stream() << cur.download(current.data()) << prev.download(previous.data())
                      << vision::synchronize() << vision::commit();
    const auto center = 8u * 16u + 8u;
    std::cout << "Visibility after camera cut: current=" << current[center].inst_id
              << " previous=" << previous[center].inst_id << '\n';
    if (current[center].inst_id != vision::InvalidUI32 || previous[center].inst_id == vision::InvalidUI32) {
        throw std::runtime_error("current GBuffer writes must preserve the actual previous frame geometry for disocclusion");
    }
}

void check_camera_dolly_reprojection(vision::Pipeline& pipeline) {
    auto expect = [](bool value, const char* message) { if (!value) throw std::runtime_error(message); };
    auto* illumination = dynamic_cast<vision::IlluminationIntegrator*>(pipeline.renderer().integrator().get());
    auto* svgf = illumination ? dynamic_cast<vision::svgf::SVGF*>(illumination->denoiser()) : nullptr;
    expect(svgf != nullptr, "dolly regression must inspect the actual SVGF history");
    auto* sensor = pipeline.scene().sensor().get();
    sensor->set_position(vision::make_float3(0.f, 0.f, 3.f));
    sensor->set_yaw(0.f); sensor->set_pitch(0.f); sensor->set_fov_y(45.f);
    sensor->update_device_data();
    pipeline.invalidate();
    pipeline.upload_data();
    for (int i = 0; i < 16; ++i) {
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
    }
    float center_specular_history = 0.f;
    auto center_history = [&]() {
        std::vector<vision::svgf::SVGFDataDual> history(pipeline.pixel_num());
        std::vector<vision::TriangleHit> visibility(pipeline.pixel_num());
        const auto resolution = pipeline.resolution();
        const auto center_index = (resolution.y / 2u) * resolution.x + resolution.x / 2u;
        const auto rendered_frame = pipeline.frame_index() - 1;
        auto& buffer = (rendered_frame & 1u) == 0u ? svgf->svgf_data : svgf->svgf_data2;
        pipeline.stream() << buffer.view().download(history.data())
            << pipeline.frame_buffer()->cur_visibility_buffer_view(rendered_frame).subview(0, visibility.size()).download(visibility.data())
            << vision::synchronize() << vision::commit();
        expect(visibility[center_index].inst_id != vision::InvalidUI32,
               "dolly regression center must hit the triangle, not stale sky history");
        center_specular_history = static_cast<float>(history[center_index].moments_direct.w);
        return static_cast<float>(history[center_index].moments_direct.z);
    };
    expect(center_history() > 1.5f, "dolly regression needs valid initial history");
    // A jittered boundary can miss this surface at exactly the reprojected
    // pixel while adjacent previous pixels still contain valid same-surface
    // illumination. Exercise that hole without accepting unrelated geometry.
    const auto center = 8u * 16u + 8u;
    auto previous_visibility = pipeline.frame_buffer()->cur_visibility_buffer_view(pipeline.frame_index() - 1u);
    vision::TriangleHit missing{};
    missing.inst_id = vision::InvalidUI32;
    pipeline.stream() << previous_visibility.subview(center, 1).upload(&missing)
                      << vision::synchronize() << vision::commit();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    expect(center_history() > 1.5f,
           "a rejected bilinear tap must recover valid same-surface history from adjacent previous pixels");
    previous_visibility = pipeline.frame_buffer()->cur_visibility_buffer_view(pipeline.frame_index() - 1u);
    for (unsigned y = 7; y <= 9; ++y) {
        for (unsigned x = 7; x <= 9; ++x) {
            pipeline.stream() << previous_visibility.subview(y * 16u + x, 1).upload(&missing);
        }
    }
    pipeline.stream() << vision::synchronize() << vision::commit();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    expect(center_history() == 1.f,
           "a disoccluded surface with no matching previous neighbours must still reject history");
    expect(center_specular_history == 1.f,
           "disocclusion must also reset independent specular history");
    pipeline.invalidate();
    for (int i = 0; i < 16; ++i) {
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
    }
    // The same stationary triangle remains visible. Moving the eye by 0.2
    // changes current-eye distance by > 3%, but not previous-eye depth.
    sensor->set_position(vision::make_float3(0.f, 0.f, 2.8f));
    sensor->update_device_data();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    const float reprojected_history = center_history();
    std::cout << "Dolly center history=" << reprojected_history << '\n';
    expect(reprojected_history > 1.5f,
           "dolly movement must compare both surface depths from the previous camera, retaining valid history");

    // This diffuse surface has view-independent lighting: a valid lateral
    // reprojection must not discard its accumulated samples just to track gloss.
    sensor->set_position(vision::make_float3(0.4f, 0.f, 2.8f));
    sensor->update_device_data();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    const float moving_history = center_history();
    expect(moving_history > 12.f,
           "valid moving diffuse surfaces must retain accumulated illumination independently of specular responsiveness");
    expect(center_specular_history > 1.5f && center_specular_history < 12.f,
           "moving specular history must still match its responsive effective alpha");
    const float moving_specular_history = center_specular_history;
    for (int i = 0; i < 16; ++i) {
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
    }
    const float stopped_history = center_history();
    std::cout << "Motion effective history=" << moving_history << " stopped=" << stopped_history << '\n';
    expect(stopped_history > moving_history + 8.f,
           "stationary history must recover after camera movement");
    expect(center_specular_history > moving_specular_history + 8.f,
           "specular history must independently recover after camera movement");

    // Turning at a fixed eye moves pixels without changing the outgoing
    // direction at a reprojected world-space surface point.
    sensor->set_position(vision::make_float3(0.f, 0.f, 3.f));
    sensor->set_yaw(0.f);
    sensor->update_device_data();
    pipeline.invalidate();
    for (int i = 0; i < 16; ++i) {
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
    }
    sensor->set_yaw(6.f);
    sensor->update_device_data();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    center_history();
    std::cout << "Rotation specular history=" << center_specular_history << '\n';
    expect(center_specular_history > 14.f,
           "pure camera rotation must retain valid specular history when the world-space view direction is unchanged");

    // The sensor's FOV spans the shorter dimension. Swapping width/height
    // must not change the angular response at the same surface point.
    float landscape_history = 0.f;
    for (bool portrait : {false, true}) {
        pipeline.change_resolution(portrait ? vision::make_uint2(16u, 24u)
                                            : vision::make_uint2(24u, 16u));
        sensor->set_position(vision::make_float3(0.f, 0.f, 3.f));
        sensor->set_yaw(0.f);
        sensor->update_device_data();
        pipeline.invalidate();
        for (int i = 0; i < 16; ++i) {
            pipeline.upload_data();
            pipeline.display(1.0 / 60.0);
        }
        sensor->set_position(vision::make_float3(0.4f, 0.f, 3.f));
        sensor->update_device_data();
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
        center_history();
        expect(center_specular_history > 1.5f && center_specular_history < 12.f,
               "both image orientations must remain responsive to view parallax");
        std::cout << "Aspect specular history portrait=" << portrait << " history="
                  << center_specular_history << '\n';
        if (!portrait) landscape_history = center_specular_history;
        else expect(std::abs(center_specular_history - landscape_history) < landscape_history * 0.1f,
                    "portrait and landscape views with the same short side must use the same angular history response");
    }
    // The following spatial fixture uses a 16x16 visibility buffer.
    pipeline.change_resolution(vision::make_uint2(16u, 16u));
    sensor->set_position(vision::make_float3(0.f, 0.f, 3.f));
    sensor->update_device_data();
    pipeline.invalidate();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);

}
