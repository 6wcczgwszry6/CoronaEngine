#pragma once

#include <horizon.h>

#include <corona/shared_data_hub.h>  // MeshDevice

#include <vector>

namespace Corona {
namespace Resource {
class Scene;
}  // namespace Resource
}  // namespace Corona

namespace Corona::Systems {

// ============================================================================
// 几何 GPU 资源构建器（单一来源）
// ============================================================================
//
// 把"已导入的 Resource::Scene → GPU MeshDevice 数组"这件事收成唯一一份实现。
// 此前该逻辑在两处重复：
//   - Python API 层 Geometry 构造函数（初始加载）
//   - GeometrySystem::rebuild_actor_gpu_resources（距离重载 / LRU 恢复）
// 两份代码已在维护中分叉（占位纹理生命周期、压缩纹理路径），由此函数统一。
//
// 行为：为 scene 中每个 mesh 创建顶点/索引缓冲 + 对应 StorageBuffer + 纹理
// （压缩 BC1/BC3，未压缩 1/3/4 通道→RGBA8），无纹理的 mesh 使用传入的占位纹理。
// 纹理像素分批同步上传（每 32 个一批）。
//
// 无状态、不加任何锁、不触碰 SharedDataHub 槽位——调用方负责把返回的数组写回
// GeometryDevice::mesh_handles 并处理 LOD 缓存失效。GPU 资源创建在调用线程完成。

/// 从已导入的 Scene 构建 GPU MeshDevice 数组。
///
/// @param scene               已导入的场景资源（含 meshes / materials）
/// @param placeholder_texture 无纹理 mesh 的兜底纹理（1x1 白），调用方持有其生命周期
/// @return 与 scene.data.meshes 一一对应的 MeshDevice 数组
[[nodiscard]] std::vector<MeshDevice> build_mesh_devices_from_scene(
    const Resource::Scene&   scene,
    Horizon::HardwareImage&  placeholder_texture);

}  // namespace Corona::Systems
