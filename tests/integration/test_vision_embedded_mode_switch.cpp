#include <corona/systems/optics/optics_system.h>
#include "base/mgr/global.h"
#include "base/mgr/pipeline.h"
#include "base/sensor/sensor.h"
#include "vision/vision_camera_adapter.h"
#include "vision/vision_external_live_aabb.h"
#include <filesystem>
#include <fstream>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <iomanip>
#include <sstream>

void check_camera_dolly_reprojection(vision::Pipeline& pipeline);
void check_motion_visibility_history(vision::Pipeline& pipeline);
void check_substrate_sample_classification(vision::Pipeline& pipeline);
void check_svgf_shading_guide(vision::Pipeline& pipeline);
void check_svgf_spatial_bypass(vision::Pipeline& pipeline);

namespace Corona::Systems {
struct VisionEmbeddedModeSwitchTest {
    static void expect(bool value, const char* message) {
        if (!value) throw std::runtime_error(message);
    }
    static void render(vision::Pipeline& pipeline, const char* label, bool lit = true) {
        const auto before = pipeline.frame_index();
        for (int i = 0; i < 3; ++i) pipeline.display(1.0 / 60.0);
        expect(pipeline.frame_index() > before, "real integrator must advance frames");
        std::vector<vision::float4> pixels(pipeline.pixel_num());
        pipeline.final_picture(pipeline.output_desc(), pixels.data());
        float sum = 0;
        for (const auto& pixel : pixels) {
            expect(std::isfinite(pixel.x) && std::isfinite(pixel.y) && std::isfinite(pixel.z),
                   "GPU output must be finite");
            sum += pixel.x + pixel.y + pixel.z;
        }
        expect(lit ? sum > 0.f : sum == 0.f, "GPU output must match geometry visibility");
        std::cout << "GPU frames: " << label << " frame=" << pipeline.frame_index()
                  << " rgb_sum=" << sum << '\n';
    }
    static void check_stationary_history_reset(vision::Pipeline& pipeline) {
        pipeline.activate_global_context();
        pipeline.invalidate();
        pipeline.display(1.0 / 60.0);
        std::vector<vision::float4> first(pipeline.pixel_num()), restarted(first.size());
        pipeline.final_picture(pipeline.output_desc(), first.data());
        // Build stationary boundary history well beyond the interior EMA window.
        for (int i = 0; i < 320; ++i) pipeline.display(1.0 / 60.0);
        expect(pipeline.frame_index() == 321u, "stationary SVGF must advance its sample sequence");
        pipeline.invalidate();
        pipeline.display(1.0 / 60.0);
        pipeline.final_picture(pipeline.output_desc(), restarted.data());
        for (size_t i = 0; i < first.size(); ++i) {
            expect(std::isfinite(restarted[i].x) &&
                   std::abs(first[i].x - restarted[i].x) < 1e-6f &&
                   std::abs(first[i].y - restarted[i].y) < 1e-6f &&
                   std::abs(first[i].z - restarted[i].z) < 1e-6f,
                   "explicit invalidation must discard long SVGF history on its first frame");
        }
        std::cout << "PASS: stationary SVGF history resets after 321 frames\n";
    }
    static void check_realtime_camera_history(vision::Pipeline& pipeline) {
        Corona::CameraDevice camera;
        camera.width = 16; camera.height = 16;
        camera.position = {0.f, 0.f, -3.f}; camera.forward = {0.f, 0.f, 1.f};
        camera.world_up = {0.f, 1.f, 0.f}; camera.fov = 45.f;
        Vision::sync_vision_camera(pipeline, camera);
        pipeline.upload_data();
        render(pipeline, "SVGF-before-camera-motion");
        const auto initial_frame = pipeline.frame_index();
        std::vector<vision::float4> before(pipeline.pixel_num()), after(before.size());
        pipeline.final_picture(pipeline.output_desc(), before.data());
        for (unsigned i = 0; i < 16; ++i) {
            camera.position.x += 0.01f;
            camera.forward.x += 0.005f;
            Vision::sync_vision_camera(pipeline, camera);
            expect(pipeline.frame_index() == initial_frame + i,
                   "realtime camera movement must retain SVGF reprojection history and sample sequence");
            pipeline.upload_data();
            pipeline.display(1.0 / 60.0);
        }
        pipeline.final_picture(pipeline.output_desc(), after.data());
        float difference = 0.f;
        for (size_t i = 0; i < after.size(); ++i) {
            expect(std::isfinite(after[i].x) && std::isfinite(after[i].y) && std::isfinite(after[i].z),
                   "moving realtime output must remain finite");
            difference += std::abs(after[i].x - before[i].x);
        }
        expect(difference > 0.01f, "retaining history must still render the new camera pose");
        camera.fov += 5.f;
        Vision::sync_vision_camera(pipeline, camera);
        expect(pipeline.frame_index() == 0, "projection changes must discard incompatible history");
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
        camera.width = 24;
        Vision::sync_vision_camera(pipeline, camera);
        expect(pipeline.frame_index() == 0 && pipeline.resolution().x == 24,
               "resizing must discard old history and allocate the new output");
        pipeline.upload_data();
        render(pipeline, "SVGF-after-camera-resize");
        camera.width = 16;
        Vision::sync_vision_camera(pipeline, camera);
        pipeline.upload_data();
        std::cout << "PASS: realtime camera translation/rotation preserves history; projection/resize resets\n";
    }
    // Optional visual regression capture uses the same camera adapter and active
    // view context as OpticsSystem's editor render loop. It is not a CTest job.
    static void capture_camera_motion(const char* scene, const char* destination, bool fast = false) {
        namespace fs = std::filesystem;
        ocarina::RHIContext::instance().init(fs::current_path());
        static auto device = ocarina::RHIContext::instance().create_device("cuda");
        device.init_rtx();
        vision::Global::instance().set_device(&device);
        OpticsSystem system;
        expect(system.load_external_vision_scene(scene, CameraVisionRenderMode::SVGF,
                   Vision::VisionPipelineSource::ExternalFile), "motion capture scene must load");
        auto pipeline = vision::Global::instance().pipeline_shared();
        const auto resolution = pipeline->resolution();
        // The editor owns a separate renderer/sensor for each camera.
        expect(pipeline->create_view_context(42, resolution), "capture view must be created");
        expect(pipeline->activate_view_context(42), "capture view must be active");
        auto* sensor = pipeline->scene().sensor().get();
        const auto position = sensor->position();
        const float yaw = sensor->yaw(), pitch = sensor->pitch();
        Corona::CameraDevice camera;
        camera.width = resolution.x; camera.height = resolution.y;
        camera.fov = sensor->fov_y(); camera.world_up = {0.f, 1.f, 0.f};
        const fs::path out = fs::absolute(destination);
        fs::create_directories(out);
        std::ofstream metrics(out / "frames.csv");
        metrics << "frame,history_before,history_after,yaw,pitch,x,y,z,gpu_ms\n" << std::setprecision(9);
        std::vector<vision::float4> pixels(pipeline->pixel_num());
        constexpr float radians = 0.017453292519943295f;
        for (unsigned frame = 0; frame < 224; ++frame) {
            const auto excursion = [fast](unsigned step, float distance) {
                // The fast path reaches its endpoint in eight frames and holds
                // there to expose trails and the first frames after stopping.
                return fast ? std::min(float(step) / 8.f, 1.f) * distance
                            : float(step) / 32.f * distance;
            };
            const float rotation = frame <= 64 ? 0.f : frame <= 96 ? excursion(frame - 64, fast ? 15.f : 3.f)
                : frame <= 128 ? (fast ? 15.f - excursion(frame - 96, 15.f) : excursion(128 - frame, 3.f)) : 0.f;
            const float translation = frame <= 128 ? 0.f : frame <= 160 ? excursion(frame - 128, fast ? 0.48f : 0.12f)
                : frame <= 192 ? (fast ? 0.48f - excursion(frame - 160, 0.48f) : excursion(192 - frame, 0.12f)) : 0.f;
            const float yr = (yaw + rotation) * radians, pr = pitch * radians;
            camera.position = {position.x + translation, position.y, -position.z};
            camera.forward = {std::sin(yr)*std::cos(pr), std::sin(pr), std::cos(yr)*std::cos(pr)};
            Vision::sync_vision_camera(*pipeline, camera);
            const auto history = pipeline->frame_index();
            pipeline->upload_data();
            pipeline->display(1.0 / 60.0);
            metrics << frame << ',' << history << ',' << pipeline->frame_index() << ','
                    << sensor->yaw() << ',' << sensor->pitch() << ',' << sensor->position().x << ','
                    << sensor->position().y << ',' << sensor->position().z << ','
                    << pipeline->cur_render_time() << '\n';
            if (frame >= 64) {
                std::ostringstream name;
                name << "frame_" << std::setfill('0') << std::setw(4) << frame << ".png";
                auto desc = pipeline->output_desc();
                desc.fn = name.str();
                pipeline->final_picture(desc, pixels.data());
                vision::Image::save_image(out / name.str(), vision::PixelStorage::FLOAT4, resolution, pixels.data());
            }
        }
        pipeline.reset();
        system.clear_vision_runtimes();
        std::cout << "PASS: captured 160 frames through the production camera adapter\n";
    }
    static void run() {
        namespace fs = std::filesystem;
        const auto original_cwd = fs::current_path();
        const auto base = original_cwd / "embedded-mode-switch-test-assets";
        fs::create_directories(base);
        std::ofstream(base / "triangle.obj") << "v -1 -1 0\nv 1 -1 0\nv 0 1 0\nf 1 2 3\n";
        const unsigned char white_tga[] = {0,0,2,0,0,0,0,0,0,0,0,0,1,0,1,0,24,0,255,255,255};
        std::ofstream(base / "albedo.tga", std::ios::binary).write(
            reinterpret_cast<const char*>(white_tga), sizeof(white_tga));
        ocarina::RHIContext::instance().init(original_cwd);
        // Keep the device alive until process exit: Vision's global kernel tools own GPU state.
        static auto device = ocarina::RHIContext::instance().create_device("cuda");
        device.init_rtx();
        vision::Global::instance().set_device(&device);
        OpticsSystem system;
        OpticsSystem::VisionSceneLoadRequest request;
        request.scene_key = (base / "memory-only.embedded").string();
        request.base_dir = base.filename().string();
        request.external_live = true;
        request.scene_json = R"({
          "scene": {
            "camera":{"type":"thin_lens","param":{"transform":{"type":"look_at","param":{"position":[0,0,3],"target_pos":[0,0,0],"up":[0,1,0]}}}},
            "materials":[{"type":"diffuse","name":"mat","param":{"color":{"channels":"xyz","node":{"type":"image","param":{"fn":"albedo.tga"}}}}}],"shapes":[{"type":"model","param":{"fn":"triangle.obj","material":"mat"}}],"lights":[{"type":"point","param":{"position":[0,0,2]}}]
          },
          "render":{"sampler":{"type":"independent","param":{"spp":1}},"integrator":{"type":"pt","param":{"max_depth":2}},"light_sampler":{"type":"uniform"}},
          "pipeline":{"type":"fixed","param":{"frame_buffer":{"type":"normal","param":{"resolution":[16,16]}}}},
          "output":{"spp":1,"denoise":false}
        })";
        expect(!fs::exists(request.scene_key), "fixture must never create an embedded file");
        expect(system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::PathTracing),
               "in-memory PT must initialize");
        auto pt = vision::Global::instance().pipeline_shared();
        render(*pt, "PT");
        expect(!pt->frame_buffer()->enable_accumulation(), "realtime PT must not accumulate SVGF output");
        expect(system.load_external_vision_scene(request.scene_key,
            CameraVisionRenderMode::ProgressivePathTracing, Vision::VisionPipelineSource::ExternalLive),
            "progressive PT must load from the same embedded source");
        auto progressive = vision::Global::instance().pipeline_shared();
        expect(progressive != pt, "PT modes must keep independent histories");
        expect(!progressive->output_desc().denoise && progressive->frame_buffer()->enable_accumulation(),
            "progressive PT must accumulate without realtime denoise");
        auto* illumination = dynamic_cast<vision::IlluminationIntegrator*>(progressive->renderer().integrator().get());
        expect(illumination && illumination->denoiser() && !illumination->denoiser()->enabled(),
            "the actual denoiser must remain disabled, not just the output flag");
        progressive->invalidate();
        auto* fb = progressive->frame_buffer();
        std::vector<vision::float4> first(progressive->pixel_num()), second(first.size()), average(first.size());
        progressive->display(1.0 / 60.0);
        progressive->stream() << fb->rt_buffer().device_buffer().download(first.data())
                              << vision::synchronize() << vision::commit();
        progressive->display(1.0 / 60.0);
        progressive->stream() << fb->rt_buffer().device_buffer().download(second.data())
                              << fb->accumulation_buffer().device_buffer().download(average.data())
                              << vision::synchronize() << vision::commit();
        for (size_t i = 0; i < first.size(); ++i) {
            expect(std::isfinite(average[i].x) &&
                   std::abs(average[i].x - (first[i].x + second[i].x) * 0.5f) < 0.0001f &&
                   std::abs(average[i].y - (first[i].y + second[i].y) * 0.5f) < 0.0001f &&
                   std::abs(average[i].z - (first[i].z + second[i].z) * 0.5f) < 0.0001f,
                   "progressive output must average actual consecutive PT samples");
        }
        Corona::CameraDevice camera;
        camera.width = 16; camera.height = 16;
        camera.position = {0.f, 0.f, -3.f}; camera.forward = {0.f, 0.f, 1.f};
        camera.world_up = {0.f, 1.f, 0.f}; camera.fov = 45.f;
        Vision::sync_vision_camera(*progressive, camera);
        render(*progressive, "Progressive");
        const auto accumulated_frames = progressive->frame_index();
        Vision::sync_vision_camera(*progressive, camera);
        expect(progressive->frame_index() == accumulated_frames, "a stationary camera must keep accumulating");
        camera.position.x += 0.1f;
        Vision::sync_vision_camera(*progressive, camera);
        expect(progressive->frame_index() == 0, "moving the camera must restart convergence");
        progressive->stream() << fb->accumulation_buffer().device_buffer().download(average.data())
                              << vision::synchronize() << vision::commit();
        for (const auto& pixel : average) {
            expect(pixel.x == 0.f && pixel.y == 0.f && pixel.z == 0.f,
                   "camera changes must clear old accumulated pixels");
        }
        expect(system.load_external_vision_scene(request.scene_key, CameraVisionRenderMode::PathTracing,
            Vision::VisionPipelineSource::ExternalLive), "switch back to realtime PT");
        render(*pt, "PT-after-progressive");
        progressive.reset();
        const auto resource_key = system.make_vision_scene_resource_key(request.scene_key,
            Vision::VisionPipelineSource::ExternalLive);
        auto resource = system.vision_scene_resources_.at(resource_key);
        expect(resource->is_embedded() && resource->source_revision == 1,
               "only successful import publishes first source revision");
        expect(fs::path(resource->source_desc->base_dir).is_absolute(), "source base must be absolute");
        request.base_dir = resource->source_desc->base_dir;
        Vision::ExternalLiveAabbCache pt_cache;
        auto original_matrix = pt->scene().instances()[0]->o2w();
        const auto hidden_matrix = vision::make_float4x4(0.f);
        auto hidden = Vision::sync_external_live_group(*resource, pt_cache, 42, 0,
            pt->scene().groups()[0], 10, 11, hidden_matrix, true, true);
        expect(hidden.changed, "hiding must update production instance state");
        resource->mark_transforms_changed();
        pt->update_geometry();
        // Changing CWD must not change the meaning of relative source resources.
        // The alternate working directory also contains Vision CUDA compiler headers.
        fs::current_path(original_cwd.parent_path() / "examples" / "engine");
        const auto key = system.make_vision_pipeline_key(request.scene_key, CameraVisionRenderMode::SVGF,
                                                         Vision::VisionPipelineSource::ExternalLive);
        expect(system.ensure_external_vision_runtime(key) != nullptr,
               "second mode must import the in-memory source, not the identity as a file");
        auto svgf = vision::Global::instance().pipeline_shared();
        expect(svgf && svgf != pt, "new mode must own a distinct pipeline");
        expect(svgf->frame_buffer() != pt->frame_buffer(), "framebuffer histories must be per runtime");
        expect(svgf->scene().instances().size() == 1, "relative model must load in new mode");
        render(*svgf, "SVGF-hidden", false);
        Vision::ExternalLiveAabbCache svgf_cache;
        auto restored = Vision::sync_external_live_group(*resource, svgf_cache, 42, 0,
            svgf->scene().groups()[0], 10, 10, original_matrix, false, true);
        expect(restored.changed, "restoring after mode switch must update geometry");
        expect(Vision::aabb_matrix_values(svgf->scene().instances()[0]->o2w()) ==
                   Vision::aabb_matrix_values(original_matrix), "hidden mode must preserve original transform");
        resource->mark_transforms_changed();
        svgf->update_geometry();
        render(*svgf, "SVGF-restored");
        check_stationary_history_reset(*svgf);
        check_motion_visibility_history(*svgf);
        check_realtime_camera_history(*svgf);
        check_camera_dolly_reprojection(*svgf);
        check_svgf_spatial_bypass(*svgf);
        // Restore the PT view through the same production group helper. The
        // editor test additionally exercises automatic runtime transform upload.
        Vision::sync_external_live_group(*resource, pt_cache, 42, 0,
            pt->scene().groups()[0], 10, 10, original_matrix, false, true);
        pt->update_geometry();
        pt->invalidate_all_view_contexts();
        expect(system.load_external_vision_scene(request.scene_key, CameraVisionRenderMode::PathTracing,
            Vision::VisionPipelineSource::ExternalLive), "switch back to PT");
        render(*pt, "PT-return");
        expect(resource->source_revision == 1, "mode changes do not republish source");
        const auto original_json = request.scene_json;
        for (const auto& invalid : {std::string{}, std::string{"{"}, std::string{"[]"}, std::string{"{}"},
                std::string{R"({"scene":{"shapes":1}})"}, std::string{R"({"scene":{"mediums":1}})"},
                std::string{R"({"scene":{"mediums":{"global":2}}})"},
                std::string{R"({"scene":{"mediums":{"process":1}}})"},
                std::string{R"({"scene":{"mediums":{"list":1}}})"}}) {
            request.scene_json = invalid;
            expect(!system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::SVGF, true),
                   "invalid reload must fail");
            expect(resource->source_revision == 1 && resource->source_desc->scene_json == original_json,
                   "failed reload must preserve last successful source");
        }
        request.scene_json = original_json;
        const auto filename = request.scene_json.find("triangle.obj");
        request.scene_json.replace(filename, 12, "missing.obj");
        expect(!system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::SVGF, true),
               "missing model must fail before GPU import");
        expect(resource->source_revision == 1, "missing resource cannot publish a revision");
        request.scene_json = original_json;
        request.scene_json.replace(request.scene_json.find("albedo.tga"), 10, "missing.tga");
        expect(!system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::SVGF, true),
               "missing relative texture must fail before GPU import");
        expect(resource->source_revision == 1, "missing texture cannot publish a revision");
        render(*pt, "PT-after-failed-reload");
        // Same identity, different JSON must replace both previous modes even without force.
        request.scene_json = original_json;
        const auto resolution = request.scene_json.find("[16,16]");
        request.scene_json.replace(resolution, 7, "[24,16]");
        expect(system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::SVGF),
               "same-key new JSON must load");
        expect(resource->source_revision == 2, "new JSON must publish a new revision");
        expect(system.vision_runtimes_.size() == 1, "reload must retire all previous modes");
        pt.reset(); svgf.reset();
        auto reloaded = vision::Global::instance().pipeline_shared();
        expect(reloaded->resolution().x == 24, "new JSON must actually change pipeline resolution");
        render(*reloaded, "SVGF-new-JSON");
        // A force reload with identical JSON also reloads changed on-disk resources.
        std::ofstream(base / "triangle.obj") << "v -2 -1 0\nv 2 -1 0\nv 0 1 0\nf 1 2 3\n";
        expect(system.load_external_vision_scene_from_json(request, CameraVisionRenderMode::PathTracing, true),
               "resource reload must import again");
        reloaded.reset();
        reloaded = vision::Global::instance().pipeline_shared();
        expect(resource->source_revision == 3, "forced resource reload must publish a new revision");
        expect(reloaded->scene().groups()[0]->aabb.upper.x == 2.f, "reloaded model must use new vertices");
        render(*reloaded, "PT-resource-reload");
        std::weak_ptr<vision::GeometryGpuResource> retired_gpu = reloaded->scene().geometry().gpu_resource();
        reloaded.reset();
        // Use production teardown to remove every external runtime, leaving only
        // an engine-built placeholder. The shared source must survive this boundary.
        system.activate_single_vision_runtime_key(system.make_vision_pipeline_key("",
            CameraVisionRenderMode::PathTracing, Vision::VisionPipelineSource::EngineBuilt));
        expect(retired_gpu.expired(), "retiring the last runtime must release scene GPU resources");
        expect(system.ensure_external_vision_runtime(key) != nullptr, "rebuild after runtime retirement");
        reloaded = vision::Global::instance().pipeline_shared();
        expect(reloaded->resolution().x == 24 && resource->source_revision == 3,
               "recreated runtime must consume latest source without republishing");
        render(*reloaded, "SVGF-recreated");
        reloaded.reset();
        expect(!fs::exists(request.scene_key), "embedded scene must remain memory-only");
        std::ofstream(base / "file-scene.json") << original_json;
        expect(system.load_external_vision_scene((base / "file-scene.json").string(),
            CameraVisionRenderMode::SVGF, Vision::VisionPipelineSource::ExternalFile),
            "explicit file source must continue to import");
        const auto file_resource = system.vision_scene_resources_.at(system.make_vision_scene_resource_key(
            (base / "file-scene.json").string(), Vision::VisionPipelineSource::ExternalFile));
        expect(file_resource->source_desc->kind == Vision::VisionSceneSourceKind::File &&
                   fs::path(file_resource->source_desc->base_dir).is_absolute(),
               "file source must retain explicit kind and absolute base");
        expect(system.load_external_vision_scene((base / "file-scene.json").string(),
            CameraVisionRenderMode::PathTracing, Vision::VisionPipelineSource::ExternalFile),
            "file source must also support a second mode");
        expect(file_resource->source_revision == 1, "file mode switch must not republish source");
        render(*vision::Global::instance().pipeline(), "File-PT");
        check_substrate_sample_classification(*vision::Global::instance().pipeline());
        check_svgf_shading_guide(*vision::Global::instance().pipeline());
        system.clear_vision_runtimes();
        resource.reset();
        fs::current_path(original_cwd);
        fs::remove(base / "file-scene.json");
        fs::remove(base / "albedo.tga");
        fs::remove(base / "triangle.obj");
        fs::remove(base);
        std::cout << "PASS: embedded PT/SVGF runtime initialization\n";
    }
};
}
int main(int argc, char** argv) {
    try {
        if (argc == 4 && (std::string(argv[1]) == "--capture-camera-motion" ||
                          std::string(argv[1]) == "--capture-fast-camera-motion")) {
            Corona::Systems::VisionEmbeddedModeSwitchTest::capture_camera_motion(
                argv[2], argv[3], std::string(argv[1]) == "--capture-fast-camera-motion");
        } else {
            Corona::Systems::VisionEmbeddedModeSwitchTest::run();
        }
    }
    catch (const std::exception& e) { std::cerr << "FAIL: " << e.what() << '\n'; return 1; }
}
