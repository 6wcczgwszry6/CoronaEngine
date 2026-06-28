#include "corona/resource/types/animation_pose.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <unordered_map>

namespace Corona::Resource {

namespace {

constexpr std::array<float, 16> kIdentity{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};

/// 在排序关键帧序列中找到包围 time 的左侧下标 i（keys[i].time <= time < keys[i+1].time）。
/// time 早于首帧返回 0；晚于末帧返回 size-2（与末帧插值因子=1）。
template <typename KeyVec>
std::size_t find_key_index(const KeyVec& keys, float time) {
    // keys 非空且 size>=2 由调用方保证
    for (std::size_t i = 0; i + 1 < keys.size(); ++i) {
        if (time < keys[i + 1].first) {
            return i;
        }
    }
    return keys.size() - 2;
}

/// 归一化插值因子 [0,1]：(time - t0) / (t1 - t0)，分母为 0 时返回 0。
float blend_factor(float time, float t0, float t1) {
    float denom = t1 - t0;
    if (denom <= 0.0f) return 0.0f;
    float f = (time - t0) / denom;
    return std::clamp(f, 0.0f, 1.0f);
}

std::array<float, 3> lerp_vec3(const std::array<float, 3>& a, const std::array<float, 3>& b, float t) {
    return {a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t};
}

/// 四元数 (x,y,z,w) 球面插值，自动选短弧。接近共线时退化为归一化线性插值。
std::array<float, 4> slerp_quat(std::array<float, 4> a, std::array<float, 4> b, float t) {
    float cos_theta = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
    // 选短弧
    if (cos_theta < 0.0f) {
        b = {-b[0], -b[1], -b[2], -b[3]};
        cos_theta = -cos_theta;
    }

    std::array<float, 4> result;
    if (cos_theta > 0.9995f) {
        // 近共线：线性插值后归一化，避免 sin(theta)→0 数值问题
        result = {a[0] + (b[0] - a[0]) * t,
                  a[1] + (b[1] - a[1]) * t,
                  a[2] + (b[2] - a[2]) * t,
                  a[3] + (b[3] - a[3]) * t};
    } else {
        float theta = std::acos(cos_theta);
        float sin_theta = std::sin(theta);
        float wa = std::sin((1.0f - t) * theta) / sin_theta;
        float wb = std::sin(t * theta) / sin_theta;
        result = {a[0] * wa + b[0] * wb,
                  a[1] * wa + b[1] * wb,
                  a[2] * wa + b[2] * wb,
                  a[3] * wa + b[3] * wb};
    }

    float len = std::sqrt(result[0] * result[0] + result[1] * result[1] +
                          result[2] * result[2] + result[3] * result[3]);
    if (len <= 0.0f) return {0.0f, 0.0f, 0.0f, 1.0f};
    float inv = 1.0f / len;
    return {result[0] * inv, result[1] * inv, result[2] * inv, result[3] * inv};
}

}  // namespace

std::array<float, 16> mat4_mul(const std::array<float, 16>& a, const std::array<float, 16>& b) {
    // 列主序：C[col*4+row] = Σ_k A[k*4+row] * B[col*4+k]
    std::array<float, 16> c{};
    for (int col = 0; col < 4; ++col) {
        for (int row = 0; row < 4; ++row) {
            float sum = 0.0f;
            for (int k = 0; k < 4; ++k) {
                sum += a[k * 4 + row] * b[col * 4 + k];
            }
            c[col * 4 + row] = sum;
        }
    }
    return c;
}

std::array<float, 16> compose_trs(const std::array<float, 3>& t,
                                  const std::array<float, 4>& q,
                                  const std::array<float, 3>& s) {
    const float x = q[0], y = q[1], z = q[2], w = q[3];
    const float xx = x * x, yy = y * y, zz = z * z;
    const float xy = x * y, xz = x * z, yz = y * z;
    const float wx = w * x, wy = w * y, wz = w * z;

    // 旋转矩阵元素 R[row][col]
    const float r00 = 1.0f - 2.0f * (yy + zz);
    const float r01 = 2.0f * (xy - wz);
    const float r02 = 2.0f * (xz + wy);
    const float r10 = 2.0f * (xy + wz);
    const float r11 = 1.0f - 2.0f * (xx + zz);
    const float r12 = 2.0f * (yz - wx);
    const float r20 = 2.0f * (xz - wy);
    const float r21 = 2.0f * (yz + wx);
    const float r22 = 1.0f - 2.0f * (xx + yy);

    // M = T * R * S，列主序：列 c (c<3) = R 第 c 列 * scale[c]，列 3 = 平移
    std::array<float, 16> m{};
    m[0] = r00 * s[0];  m[1] = r10 * s[0];  m[2] = r20 * s[0];  m[3] = 0.0f;   // 列 0
    m[4] = r01 * s[1];  m[5] = r11 * s[1];  m[6] = r21 * s[1];  m[7] = 0.0f;   // 列 1
    m[8] = r02 * s[2];  m[9] = r12 * s[2];  m[10] = r22 * s[2]; m[11] = 0.0f;  // 列 2
    m[12] = t[0];       m[13] = t[1];       m[14] = t[2];       m[15] = 1.0f;  // 列 3
    return m;
}

std::array<float, 16> sample_channel(const AnimChannel& channel, float time_ticks) {
    // 位置
    std::array<float, 3> pos{0.0f, 0.0f, 0.0f};
    if (channel.positions.size() == 1) {
        pos = channel.positions[0].second;
    } else if (channel.positions.size() >= 2) {
        std::size_t i = find_key_index(channel.positions, time_ticks);
        float f = blend_factor(time_ticks, channel.positions[i].first, channel.positions[i + 1].first);
        pos = lerp_vec3(channel.positions[i].second, channel.positions[i + 1].second, f);
    }

    // 旋转（四元数 Slerp）
    std::array<float, 4> rot{0.0f, 0.0f, 0.0f, 1.0f};
    if (channel.rotations.size() == 1) {
        rot = channel.rotations[0].second;
    } else if (channel.rotations.size() >= 2) {
        std::size_t i = find_key_index(channel.rotations, time_ticks);
        float f = blend_factor(time_ticks, channel.rotations[i].first, channel.rotations[i + 1].first);
        rot = slerp_quat(channel.rotations[i].second, channel.rotations[i + 1].second, f);
    }

    // 缩放
    std::array<float, 3> scale{1.0f, 1.0f, 1.0f};
    if (channel.scales.size() == 1) {
        scale = channel.scales[0].second;
    } else if (channel.scales.size() >= 2) {
        std::size_t i = find_key_index(channel.scales, time_ticks);
        float f = blend_factor(time_ticks, channel.scales[i].first, channel.scales[i + 1].first);
        scale = lerp_vec3(channel.scales[i].second, channel.scales[i + 1].second, f);
    }

    return compose_trs(pos, rot, scale);
}

float advance_anim_time(float current_ticks, float dt_seconds, const AnimationClip& clip) {
    if (clip.duration <= 0.0f) return 0.0f;
    float t = current_ticks + clip.ticks_per_second * dt_seconds;
    t = std::fmod(t, clip.duration);
    if (t < 0.0f) t += clip.duration;  // 负 dt 容错
    return t;
}

void compute_pose(const SkeletonData& skeleton,
                  const AnimationClip& clip,
                  float time_ticks,
                  std::vector<std::array<float, 16>>& out_finals) {
    out_finals.assign(static_cast<std::size_t>(std::max(0, skeleton.bone_count)), kIdentity);

    if (skeleton.nodes.empty()) return;

    // 构建 骨骼名 → 通道 映射（仅本 clip）
    std::unordered_map<std::string, const AnimChannel*> channel_map;
    channel_map.reserve(clip.channels.size());
    for (const auto& ch : clip.channels) {
        channel_map[ch.bone_name] = &ch;
    }

    // 递归层级累乘。用显式栈避免深骨架递归过深。
    struct StackItem {
        int node_idx;
        std::array<float, 16> parent_global;
    };
    std::vector<StackItem> stack;
    stack.push_back({skeleton.root, kIdentity});

    while (!stack.empty()) {
        StackItem item = stack.back();
        stack.pop_back();

        if (item.node_idx < 0 || item.node_idx >= static_cast<int>(skeleton.nodes.size())) {
            continue;
        }
        const BoneNode& node = skeleton.nodes[static_cast<std::size_t>(item.node_idx)];

        // 局部变换：有动画通道则采样，否则用绑定姿态 local
        std::array<float, 16> local;
        auto ch_it = channel_map.find(node.name);
        if (ch_it != channel_map.end()) {
            local = sample_channel(*ch_it->second, time_ticks);
        } else {
            local = node.local;
        }

        std::array<float, 16> global = mat4_mul(item.parent_global, local);

        // 若该节点是受蒙皮影响的骨骼，写最终矩阵
        auto bone_it = skeleton.bone_map.find(node.name);
        if (bone_it != skeleton.bone_map.end()) {
            std::int32_t id = bone_it->second.id;
            if (id >= 0 && id < static_cast<std::int32_t>(out_finals.size())) {
                // final = global_inverse * global * offset
                std::array<float, 16> tmp = mat4_mul(skeleton.global_inverse, global);
                out_finals[static_cast<std::size_t>(id)] = mat4_mul(tmp, bone_it->second.offset);
            }
        }

        for (int child : node.children) {
            stack.push_back({child, global});
        }
    }
}

}  // namespace Corona::Resource
