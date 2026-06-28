#pragma once
// ============================================================================
// 骨骼动画运行时求值（P1）
//
// 纯函数：给定 SkeletonData + AnimationClip + 时间，算出每根骨骼的最终矩阵
//   final[id] = global_inverse * global(node) * offset
// 供 P2 的 CPU 蒙皮使用：skinned[v] = Σ wᵢ · (final[idᵢ] · bind[v])。
//
// 矩阵全程列主序 std::array<float,16>（下标 = col*4 + row），与 scene.h 的
// BoneInfo::offset / BoneNode::local / SkeletonData::global_inverse 约定一致，
// 也与 ktm/glsl 一致。本模块不依赖 ktm，便于独立单测。
// ============================================================================
#include <array>
#include <vector>

#include "corona/resource/types/scene.h"

namespace Corona::Resource {

/// 列主序 4x4 矩阵乘法 C = A * B（下标 col*4+row）。
[[nodiscard]] std::array<float, 16> mat4_mul(const std::array<float, 16>& a,
                                             const std::array<float, 16>& b);

/// 由 平移/四元数(x,y,z,w)/缩放 合成局部变换矩阵 M = T * R * S（列主序）。
[[nodiscard]] std::array<float, 16> compose_trs(const std::array<float, 3>& translation,
                                                const std::array<float, 4>& rotation_xyzw,
                                                const std::array<float, 3>& scale);

/// 在给定时间（tick）采样一个动画通道，返回该骨骼的局部变换矩阵（列主序）。
/// 位置/缩放用线性插值，旋转用四元数 Slerp。单关键帧直接返回该值。
[[nodiscard]] std::array<float, 16> sample_channel(const AnimChannel& channel, float time_ticks);

/// 推进动画时间并自动循环：返回 fmod(current + tps*dt, duration)。
/// duration<=0 时返回 0。
[[nodiscard]] float advance_anim_time(float current_ticks, float dt_seconds,
                                      const AnimationClip& clip);

/// 计算给定 clip 在给定时间（tick）下的最终骨骼矩阵。
/// out_finals 会被 resize 到 skeleton.bone_count，每个元素列主序 mat4。
/// 未被动画驱动的节点使用其绑定姿态 local；未出现在 bone_map 的节点不写 final。
void compute_pose(const SkeletonData& skeleton,
                  const AnimationClip& clip,
                  float time_ticks,
                  std::vector<std::array<float, 16>>& out_finals);

}  // namespace Corona::Resource
