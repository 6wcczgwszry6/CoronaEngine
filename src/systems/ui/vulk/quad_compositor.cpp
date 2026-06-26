#include <corona/systems/ui/quad_compositor.h>

#include <corona/systems/ui/vulkan_backend.h>  // VulkanBackend::ensure_render_target
#include <corona/kernel/core/i_logger.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <span>
#include <vector>

namespace Corona::Systems {

namespace {

// Vertex layout consumed by imgui.vert.glsl: location 0 vec2 pos, 1 vec2 uv, 2 vec4 color.
struct QuadVertex {
    float pos[2]{};
    float uv[2]{};
    float color[4]{};
};

// Push-constant upload helpers (PushConsts is shared by imgui.vert/frag.glsl).
struct FVec2Upload {
    float x;
    float y;
};
struct FVec4Upload {
    float x;
    float y;
    float z;
    float w;
};

[[nodiscard]] FVec2Upload up2(const ktm::fvec2& v) {
    return {v.x, v.y};
}
[[nodiscard]] FVec4Upload up4(float x, float y, float z, float w) {
    return {x, y, z, w};
}

}  // namespace

bool QuadCompositor::ensure_white_texture() {
    if (white_ready_) {
        return true;
    }

    white_image_ = Horizon::HardwareImage(Horizon::HardwareImageDesc::texture_2d(
        1, 1,
        Horizon::Format::SRGBA8_UNORM,
        Horizon::ImageUsageFlags::Sampled | Horizon::ImageUsageFlags::TransferDst,
        "ui.white"));
    if (!white_image_) {
        CFW_LOG_ERROR("QuadCompositor: failed to create 1x1 white texture");
        return false;
    }

    const unsigned char pixel[4] = {255, 255, 255, 255};
    const auto bytes = std::span<const std::byte>(
        reinterpret_cast<const std::byte*>(pixel), sizeof(pixel));
    white_upload_receipt_ =
        white_upload_executor_.stream()
        << white_image_.upload(bytes)
        << Horizon::commit();

    white_ready_ = true;
    return true;
}

bool QuadCompositor::composite(
    std::span<const QuadDraw> quads,
    ViewportRenderResources& res,
    Horizon::RasterizerPipeline<imgui_vert_glsl_t, imgui_frag_glsl_t>& pipeline,
    uint32_t target_width,
    uint32_t target_height,
    Horizon::ImageUsageFlags render_target_usage) {
    if (target_width == 0 || target_height == 0 || quads.empty()) {
        return false;
    }

    if (!ensure_white_texture()) {
        return false;
    }
    res.executor.wait(white_upload_receipt_);

    if (!VulkanBackend::ensure_render_target(res, target_width, target_height, render_target_usage)) {
        return false;
    }

    // --- Build merged vertex/index arrays (4 verts + 6 indices per quad) ---
    std::vector<QuadVertex> vertices;
    vertices.reserve(quads.size() * 4);
    std::vector<uint32_t> indices;
    indices.reserve(quads.size() * 6);

    for (const QuadDraw& q : quads) {
        const float x0 = q.dest_min.x;
        const float y0 = q.dest_min.y;
        const float x1 = q.dest_max.x;
        const float y1 = q.dest_max.y;
        const float u0 = q.uv_min.x;
        const float v0 = q.uv_min.y;
        const float u1 = q.uv_max.x;
        const float v1 = q.uv_max.y;
        const float cr = q.color.x;
        const float cg = q.color.y;
        const float cb = q.color.z;
        const float ca = q.color.w;

        auto push_vertex = [&](float px, float py, float pu, float pv) {
            QuadVertex gv{};
            gv.pos[0] = px;
            gv.pos[1] = py;
            gv.uv[0] = pu;
            gv.uv[1] = pv;
            gv.color[0] = cr;
            gv.color[1] = cg;
            gv.color[2] = cb;
            gv.color[3] = ca;
            vertices.push_back(gv);
        };

        push_vertex(x0, y0, u0, v0);  // top-left
        push_vertex(x1, y0, u1, v0);  // top-right
        push_vertex(x1, y1, u1, v1);  // bottom-right
        push_vertex(x0, y1, u0, v1);  // bottom-left

        // Local indices (vertex_offset is applied per-draw below).
        indices.insert(indices.end(), {0u, 1u, 2u, 0u, 2u, 3u});
    }

    // --- Ensure buffer capacity, reallocate only when needed ---
    const size_t vtx_bytes = vertices.size() * sizeof(QuadVertex);
    const size_t idx_bytes = indices.size() * sizeof(uint32_t);

    if (!res.vertex_buffer || res.vertex_buffer_capacity < vtx_bytes) {
        Horizon::HardwareBufferDesc desc;
        desc.element_count = vertices.size() + 256;
        desc.element_size = static_cast<uint32_t>(sizeof(QuadVertex));
        desc.usage = Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Vertex;
        desc.debug_name = "ui_quad.vertex";
        res.vertex_buffer = Horizon::HardwareBuffer(desc);
        res.vertex_buffer_capacity = desc.byte_size();
        if (!res.vertex_buffer) {
            CFW_LOG_ERROR("QuadCompositor: failed to allocate vertex buffer ({} bytes)", res.vertex_buffer_capacity);
            return false;
        }
    }

    if (!res.index_buffer || res.index_buffer_capacity < idx_bytes) {
        Horizon::HardwareBufferDesc desc;
        desc.element_count = indices.size() + 512;
        desc.element_size = static_cast<uint32_t>(sizeof(uint32_t));
        desc.usage = Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Index;
        desc.debug_name = "ui_quad.index";
        res.index_buffer = Horizon::HardwareBuffer(desc);
        res.index_buffer_capacity = desc.byte_size();
        if (!res.index_buffer) {
            CFW_LOG_ERROR("QuadCompositor: failed to allocate index buffer ({} bytes)", res.index_buffer_capacity);
            return false;
        }
    }

    const bool vertex_write_ok = res.vertex_buffer.write_bytes(
        std::as_bytes(std::span<const QuadVertex>(vertices.data(), vertices.size())));
    const bool index_write_ok = res.index_buffer.write_bytes(
        std::as_bytes(std::span<const uint32_t>(indices.data(), indices.size())));
    if (!vertex_write_ok || !index_write_ok) {
        CFW_LOG_ERROR("QuadCompositor: geometry upload failed vertex_ok={} index_ok={}",
                      vertex_write_ok, index_write_ok);
        return false;
    }

    // --- Set pipeline output ---
    pipeline.out_color = res.render_target;
    pipeline.bind_render_target(0, res.render_target);
    pipeline.clear_records();

    const float fb_w = static_cast<float>(target_width);
    const float fb_h = static_cast<float>(target_height);
    const ktm::fvec2 scale(2.0f / fb_w, 2.0f / fb_h);
    const ktm::fvec2 translate(-1.0f, -1.0f);

    int recorded = 0;
    for (size_t i = 0; i < quads.size(); ++i) {
        const QuadDraw& q = quads[i];

        // Clip rect in target pixels (full target when unset).
        float cx0 = 0.0f, cy0 = 0.0f, cx1 = fb_w, cy1 = fb_h;
        if (q.has_clip) {
            cx0 = std::clamp(q.clip_rect.x, 0.0f, fb_w);
            cy0 = std::clamp(q.clip_rect.y, 0.0f, fb_h);
            cx1 = std::clamp(q.clip_rect.z, 0.0f, fb_w);
            cy1 = std::clamp(q.clip_rect.w, 0.0f, fb_h);
        }

        const int32_t scissor_x = static_cast<int32_t>(std::floor(cx0));
        const int32_t scissor_y = static_cast<int32_t>(std::floor(cy0));
        const int32_t scissor_w = static_cast<int32_t>(std::ceil(cx1)) - scissor_x;
        const int32_t scissor_h = static_cast<int32_t>(std::ceil(cy1)) - scissor_y;
        if (scissor_w <= 0 || scissor_h <= 0) {
            continue;
        }

        const uint32_t texture_index =
            q.texture ? q.texture->storeSampledDescriptor() : white_image_.storeSampledDescriptor();

        pipeline[imgui_vert_glsl_t::pushConsts::scale] = up2(scale);
        pipeline[imgui_vert_glsl_t::pushConsts::translate] = up2(translate);
        pipeline[imgui_frag_glsl_t::pushConsts::clip_rect] = up4(cx0, cy0, cx1, cy1);
        pipeline[imgui_frag_glsl_t::pushConsts::texture_index] = texture_index;

        Horizon::DrawIndexedParams draw_params;
        draw_params.index_count = 6;
        draw_params.first_index = static_cast<uint32_t>(i * 6);
        draw_params.vertex_offset = static_cast<int32_t>(i * 4);
        draw_params.index_type = Horizon::IndexType::UInt32;
        draw_params.enable_scissor = true;
        draw_params.scissor = Horizon::ScissorRect{
            scissor_x,
            scissor_y,
            static_cast<uint32_t>(scissor_w),
            static_cast<uint32_t>(scissor_h)};

        pipeline.record(res.index_buffer, res.vertex_buffer, draw_params);
        ++recorded;
    }

    if (recorded == 0) {
        return false;
    }

    (void)(res.executor.stream()
           << pipeline(static_cast<uint16_t>(target_width), static_cast<uint16_t>(target_height))
           << Horizon::commit());

    return true;
}

}  // namespace Corona::Systems
