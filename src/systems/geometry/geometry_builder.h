/// @file geometry_builder.h
/// @brief 共享 GPU 几何构建器 — 从 Resource::Scene 构建 MeshDevice 数组
///
/// 抽取自 GeometrySystem::rebuild_actor_gpu_resources() 和
/// Python API Geometry::Geometry() 中的重复 Phase A（缓冲创建）+
/// Phase B（纹理批量上传）逻辑。
///
/// Phase C（写回 GeometryDevice + LOD 缓存清理）由调用方各自处理。
#pragma once

#include <corona/shared_data_hub.h>

#include <vector>

namespace Corona::Resource {
class Scene;
}  // namespace Corona::Resource

namespace Corona::Systems {

/// GPU 几何构建结果：包含所有 mesh 的顶点/索引缓冲和纹理
struct GeometryBuildResult {
    std::vector<MeshDevice> mesh_devices;
};

/// 从 Scene 资源构建所有 mesh 的 GPU 资源（顶点/索引缓冲 + 纹理）。
///
/// @param scene                     已导入的 Scene 资源（包含 mesh/材质/纹理数据）
/// @param shared_placeholder_texture 共享的 1x1 白色占位纹理（无纹理 mesh 使用）
/// @return GeometryBuildResult       所有 mesh 的 GPU 设备句柄数组
///
/// 内部流程：
///   阶段 A — 为每个 mesh 创建 HardwareBuffer（vertex/index/storage）×4 +
///           创建 HardwareImage（纹理或占位）
///   阶段 B — 批量上传纹理像素到 GPU（每 32 个一批）
///
/// 调用方负责：
///   阶段 C — 将 mesh_devices 写回 GeometryDevice + 清理 LOD 缓存
GeometryBuildResult build_geometry_gpu_resources(
    const Resource::Scene&      scene,
    Horizon::HardwareImage&     shared_placeholder_texture);

}  // namespace Corona::Systems