// Keep the renderer DSL headers separate from Corona's host math headers.
#define VISION_PLUGIN_NAME "SVGF"
#define VISION_CATEGORY "denoiser"
#include "render_core/denoiser/SVGF/svgf.h"
#include "base/sensor/sensor.h"
#include <iostream>
#include <stdexcept>
#include <vector>

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
    auto center_history = [&]() {
        std::vector<vision::svgf::SVGFDataDual> history(pipeline.pixel_num());
        std::vector<vision::TriangleHit> visibility(pipeline.pixel_num());
        const auto rendered_frame = pipeline.frame_index() - 1;
        auto& buffer = (rendered_frame & 1u) == 0u ? svgf->svgf_data : svgf->svgf_data2;
        pipeline.stream() << buffer.view().download(history.data())
            << pipeline.frame_buffer()->cur_visibility_buffer_view(rendered_frame).subview(0, visibility.size()).download(visibility.data())
            << vision::synchronize() << vision::commit();
        expect(visibility[8 * 16 + 8].inst_id != vision::InvalidUI32,
               "dolly regression center must hit the triangle, not stale sky history");
        return static_cast<float>(history[8 * 16 + 8].moments_direct.z);
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

    // A lateral move leaves this triangle visible but raises the temporal alpha.
    // Its age must reflect that shorter window, then recover while stationary.
    sensor->set_position(vision::make_float3(0.4f, 0.f, 2.8f));
    sensor->update_device_data();
    pipeline.upload_data();
    pipeline.display(1.0 / 60.0);
    const float moving_history = center_history();
    expect(moving_history > 1.5f && moving_history < 12.f,
           "moving SVGF history must match its effective alpha, not total frame age");
    for (int i = 0; i < 16; ++i) {
        pipeline.upload_data();
        pipeline.display(1.0 / 60.0);
    }
    const float stopped_history = center_history();
    std::cout << "Motion effective history=" << moving_history << " stopped=" << stopped_history << '\n';
    expect(stopped_history > moving_history + 8.f,
           "stationary history must recover after camera movement");

}
