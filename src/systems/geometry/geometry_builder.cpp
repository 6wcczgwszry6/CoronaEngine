/// @file geometry_builder.cpp
/// @brief 共享 GPU 几何构建器实现

#include "geometry_builder.h"

#include <corona/kernel/core/i_logger.h>
#include <corona/resource/resource_manager.h>
#include <corona/resource/types/image.h>
#include <corona/resource/types/scene.h>

#include <cstdint>
#include <span>
#include <utility>
#include <vector>

namespace Corona::Systems {

namespace {

// ---- 缓冲/纹理创建包装器（与 geometry_system.cpp 和 corona_engine_api.cpp 功能等价）----

template <typename T>
Horizon::HardwareBuffer make_buffer(const std::vector<T>& data,
                                    Horizon::BufferUsageFlags usage,
                                    std::string name = {}) {
    Horizon::HardwareBufferDesc desc;
    desc.element_count = data.size();
    desc.element_size  = static_cast<uint32_t>(sizeof(T));
    desc.usage         = usage;
    desc.debug_name    = std::move(name);
    return Horizon::HardwareBuffer(
        desc, std::as_bytes(std::span<const T>(data.data(), data.size())));
}

Horizon::HardwareImage make_texture(uint32_t          width,
                                    uint32_t          height,
                                    Horizon::Format   format,
                                    std::string       name = {}) {
    return Horizon::HardwareImage(Horizon::HardwareImageDesc::texture_2d(
        width, height, format,
        Horizon::ImageUsageFlags::Sampled | Horizon::ImageUsageFlags::TransferDst,
        std::move(name)));
}

// ---- 待上传纹理条目 ----

struct PendingTextureUpload {
    std::uint32_t              mesh_idx;
    std::vector<unsigned char> rgba_data;
    unsigned char*             data_ptr = nullptr;
};

}  // namespace

// ============================================================================
// build_geometry_gpu_resources
// ============================================================================

GeometryBuildResult build_geometry_gpu_resources(
    const Resource::Scene&  scene,
    Horizon::HardwareImage& shared_placeholder_texture)
{
    auto& resource_manager = Resource::ResourceManager::get_instance();

    GeometryBuildResult result;
    result.mesh_devices.reserve(scene.data.meshes.size());

    std::vector<PendingTextureUpload> pending_uploads;
    pending_uploads.reserve(scene.data.meshes.size());

    // ================================================================
    // 阶段 A：遍历所有 mesh，创建 GPU 缓冲（顶点/索引/StorageBuffer + 纹理）
    // ================================================================
    for (std::uint32_t mesh_idx = 0; mesh_idx < scene.data.meshes.size(); ++mesh_idx) {
        const auto& mesh = scene.data.meshes[mesh_idx];
        MeshDevice dev{};

        // ---- 顶点/索引缓冲（4 个）----
        dev.vertexBuffer = make_buffer(
            scene.get_mesh_vertices(mesh_idx),
            Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Vertex,
            "geometry.vertex");
        dev.indexBuffer = make_buffer(
            scene.get_mesh_indices(mesh_idx),
            Horizon::BufferUsageFlags::TransferDst | Horizon::BufferUsageFlags::Index,
            "geometry.index");
        dev.vertexStorageBuffer = make_buffer(
            scene.get_mesh_vertices(mesh_idx),
            Horizon::BufferUsageFlags::TransferSrc | Horizon::BufferUsageFlags::TransferDst |
                Horizon::BufferUsageFlags::Storage,
            "geometry.vertex_storage");
        dev.indexStorageBuffer = make_buffer(
            scene.get_mesh_indices(mesh_idx),
            Horizon::BufferUsageFlags::TransferSrc | Horizon::BufferUsageFlags::TransferDst |
                Horizon::BufferUsageFlags::Storage,
            "geometry.index_storage");

        // ---- 材质索引 ----
        dev.materialIndex = (mesh.material_index != Resource::InvalidIndex)
                                ? mesh.material_index
                                : 0;

        // ---- 材质颜色 ----
        if (mesh.material_index != Resource::InvalidIndex &&
            mesh.material_index < scene.data.materials.size()) {
            dev.materialColor = scene.data.materials[mesh.material_index].base_color;
        }

        // ---- 纹理处理 ----
        bool           texture_created = false;
        uint32_t       texture_width   = 0;
        uint32_t       texture_height  = 0;
        Horizon::Format texture_format = Horizon::Format::SRGBA8_UNORM;

        if (mesh.material_index != Resource::InvalidIndex &&
            mesh.material_index < scene.data.materials.size()) {
            auto texture_id = scene.data.materials[mesh.material_index].albedo_texture;

            if (texture_id != Resource::InvalidTextureId) {
                auto texture_data = resource_manager.acquire_read<Resource::Image>(texture_id);
                if (texture_data && texture_data->get_data() != nullptr) {
                    const int tex_width    = texture_data->get_width();
                    const int tex_height   = texture_data->get_height();
                    const int tex_channels = texture_data->get_channels();

                    if (tex_width > 0 && tex_height > 0 && tex_channels > 0) {
                        // ---- 分支 A：压缩纹理（BC1/BC3/ASTC）----
                        if (texture_data->is_compressed()) {
                            const auto& compressed = texture_data->get_compressed_data();
                            texture_width  = static_cast<uint32_t>(tex_width);
                            texture_height = static_cast<uint32_t>(tex_height);
                            bool supported_format = true;

                            if (compressed.format == Resource::CompressedData::Format::BC1) {
                                texture_format = Horizon::Format::BC1_UNORM_SRGB;
                            } else if (compressed.format == Resource::CompressedData::Format::BC3) {
                                texture_format = Horizon::Format::BC3_UNORM_SRGB;
                            } else if (compressed.format == Resource::CompressedData::Format::ASTC_4x4) {
                                CFW_LOG_WARNING("[GeometryBuilder] ASTC_4x4 texture not supported; "
                                                "using placeholder");
                                supported_format = false;
                            }

                            if (supported_format) {
                                PendingTextureUpload upload{mesh_idx, {}, nullptr};
                                upload.rgba_data.assign(compressed.data.begin(),
                                                        compressed.data.end());
                                upload.data_ptr = upload.rgba_data.data();

                                dev.textureBuffer = make_texture(
                                    texture_width, texture_height, texture_format,
                                    "geometry.material_texture");
                                pending_uploads.push_back(std::move(upload));
                                texture_created = true;
                            }
                        }
                        // ---- 分支 B：未压缩纹理（RGBA 像素数据）----
                        else {
                            texture_width  = static_cast<uint32_t>(tex_width);
                            texture_height = static_cast<uint32_t>(tex_height);
                            texture_format = Horizon::Format::SRGBA8_UNORM;

                            unsigned char* src_data = texture_data->get_data();
                            PendingTextureUpload upload{mesh_idx, {}, nullptr};

                            if (tex_channels == 4) {
                                upload.rgba_data.assign(
                                    src_data,
                                    src_data + static_cast<size_t>(tex_width) * tex_height * 4);
                                upload.data_ptr = upload.rgba_data.data();
                            } else if (tex_channels == 3) {
                                upload.rgba_data.resize(
                                    static_cast<size_t>(tex_width) * tex_height * 4);
                                for (int i = 0; i < tex_width * tex_height; ++i) {
                                    upload.rgba_data[i * 4 + 0] = src_data[i * 3 + 0];
                                    upload.rgba_data[i * 4 + 1] = src_data[i * 3 + 1];
                                    upload.rgba_data[i * 4 + 2] = src_data[i * 3 + 2];
                                    upload.rgba_data[i * 4 + 3] = 255;
                                }
                                upload.data_ptr = upload.rgba_data.data();
                            } else if (tex_channels == 1) {
                                upload.rgba_data.resize(
                                    static_cast<size_t>(tex_width) * tex_height * 4);
                                for (int i = 0; i < tex_width * tex_height; ++i) {
                                    upload.rgba_data[i * 4 + 0] = src_data[i];
                                    upload.rgba_data[i * 4 + 1] = src_data[i];
                                    upload.rgba_data[i * 4 + 2] = src_data[i];
                                    upload.rgba_data[i * 4 + 3] = 255;
                                }
                                upload.data_ptr = upload.rgba_data.data();
                            }

                            if (upload.data_ptr != nullptr) {
                                dev.textureBuffer = make_texture(
                                    texture_width, texture_height, texture_format,
                                    "geometry.material_texture");
                                pending_uploads.push_back(std::move(upload));
                                texture_created = true;
                            }
                        }
                    }
                }
            }
        }

        // ---- 无纹理兜底：使用共享占位纹理 ----
        if (!texture_created) {
            dev.textureBuffer = shared_placeholder_texture;
        }

        result.mesh_devices.emplace_back(std::move(dev));
    }  // 阶段 A 结束

    // ================================================================
    // 阶段 B：批量上传纹理像素到 GPU（每 32 个一批）
    // ================================================================
    if (!pending_uploads.empty()) {
        constexpr size_t kBatchSize = 32;
        for (size_t batch_start = 0; batch_start < pending_uploads.size();
             batch_start += kBatchSize) {
            size_t batch_end = std::min(batch_start + kBatchSize, pending_uploads.size());

            for (size_t i = batch_start; i < batch_end; ++i) {
                auto& upload = pending_uploads[i];
                Horizon::HardwareImage& tex =
                    result.mesh_devices[upload.mesh_idx].textureBuffer;
                tex.write_bytes(std::as_bytes(
                    std::span<const unsigned char>(upload.data_ptr, upload.rgba_data.size())));
            }
        }
    }

    return result;
}

}  // namespace Corona::Systems