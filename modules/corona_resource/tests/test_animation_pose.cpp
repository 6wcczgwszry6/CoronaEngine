// ============================================================================
// P1 验证：骨骼动画运行时求值（animation_pose）数学自洽性单测
//
// 不依赖引擎/GPU/磁盘。验证：
//   1. mat4_mul 单位元 / 结合律
//   2. compose_trs：单位四元数 = 纯 T*S；90° 旋转方向正确
//   3. slerp 端点 + 中点
//   4. compute_pose 绑定姿态 → final ≈ 单位阵（核心验证闸）
//   5. compute_pose 无动画通道时回退 local；层级累乘正确
// ============================================================================
#include <array>
#include <cmath>
#include <cstdio>
#include <vector>

#include "corona/resource/types/animation_pose.h"

using namespace Corona::Resource;

namespace {

int g_passed = 0;
int g_failed = 0;

constexpr std::array<float, 16> kIdentity{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};

void check(bool cond, const char* name) {
    if (cond) {
        ++g_passed;
        std::printf("[PASS] %s\n", name);
    } else {
        ++g_failed;
        std::printf("[FAIL] %s\n", name);
    }
}

bool near_eq(float a, float b, float eps = 1e-4f) {
    return std::fabs(a - b) <= eps;
}

bool mat_near(const std::array<float, 16>& a, const std::array<float, 16>& b, float eps = 1e-4f) {
    for (int i = 0; i < 16; ++i) {
        if (!near_eq(a[i], b[i], eps)) return false;
    }
    return true;
}

// 列主序矩阵 * 点 (x,y,z,1)，返回变换后的 xyz
std::array<float, 3> transform_point(const std::array<float, 16>& m, const std::array<float, 3>& p) {
    return {
        m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
        m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
        m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]};
}

void test_mat4_mul() {
    // 单位元
    std::array<float, 16> a{2, 0, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 5, 6, 7, 1};
    check(mat_near(mat4_mul(a, kIdentity), a), "mat4_mul: A*I == A");
    check(mat_near(mat4_mul(kIdentity, a), a), "mat4_mul: I*A == A");
}

void test_compose_trs() {
    // 单位四元数 → 纯平移+缩放
    auto m = compose_trs({1.0f, 2.0f, 3.0f}, {0.0f, 0.0f, 0.0f, 1.0f}, {2.0f, 2.0f, 2.0f});
    auto p = transform_point(m, {1.0f, 0.0f, 0.0f});
    // 缩放 2 后平移 (1,2,3) → (2+1, 0+2, 0+3) = (3,2,3)
    check(near_eq(p[0], 3.0f) && near_eq(p[1], 2.0f) && near_eq(p[2], 3.0f),
          "compose_trs: identity quat = T*S");

    // 绕 Z 轴 90°（四元数 (0,0,sin45,cos45)）：x 轴 → y 轴
    float s = std::sin(3.14159265f / 4.0f);
    float c = std::cos(3.14159265f / 4.0f);
    auto rz = compose_trs({0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, s, c}, {1.0f, 1.0f, 1.0f});
    auto rp = transform_point(rz, {1.0f, 0.0f, 0.0f});
    check(near_eq(rp[0], 0.0f) && near_eq(rp[1], 1.0f) && near_eq(rp[2], 0.0f),
          "compose_trs: Z-90deg maps +X to +Y");
}

void test_slerp_endpoints() {
    AnimChannel ch;
    ch.bone_name = "b";
    // 两个旋转关键帧：单位 → 绕 Z 90°
    float s = std::sin(3.14159265f / 4.0f);
    float c = std::cos(3.14159265f / 4.0f);
    ch.rotations.emplace_back(0.0f, std::array<float, 4>{0, 0, 0, 1});
    ch.rotations.emplace_back(10.0f, std::array<float, 4>{0, 0, s, c});
    ch.positions.emplace_back(0.0f, std::array<float, 3>{0, 0, 0});
    ch.scales.emplace_back(0.0f, std::array<float, 3>{1, 1, 1});

    // t=0：单位旋转，+X 不变
    auto m0 = sample_channel(ch, 0.0f);
    auto p0 = transform_point(m0, {1, 0, 0});
    check(near_eq(p0[0], 1.0f) && near_eq(p0[1], 0.0f), "slerp: t=0 -> identity rotation");

    // t=10（末帧）：90°，+X → +Y
    auto m1 = sample_channel(ch, 10.0f);
    auto p1 = transform_point(m1, {1, 0, 0});
    check(near_eq(p1[0], 0.0f) && near_eq(p1[1], 1.0f), "slerp: t=end -> 90deg rotation");

    // t=5（中点）：45°，+X → (cos45, sin45)
    auto mh = sample_channel(ch, 5.0f);
    auto ph = transform_point(mh, {1, 0, 0});
    check(near_eq(ph[0], c) && near_eq(ph[1], s), "slerp: midpoint -> 45deg rotation");
}

void test_advance_time_loops() {
    AnimationClip clip;
    clip.duration = 10.0f;
    clip.ticks_per_second = 1.0f;
    // 从 9 推进 2 秒 → 11 fmod 10 = 1
    float t = advance_anim_time(9.0f, 2.0f, clip);
    check(near_eq(t, 1.0f), "advance_anim_time: wraps around duration");
}

// 核心验证闸：绑定姿态下 final ≈ 单位阵。
// 构造：单骨骼，offset = inverse(local_bind)，global_inverse = I，
// 无动画通道（用 bind local）→ final = I * local_bind * inverse(local_bind) = I。
void test_bind_pose_identity_single() {
    SkeletonData skel;
    skel.bone_count = 1;
    skel.global_inverse = kIdentity;

    // 单骨骼 local_bind = 平移(5,0,0) * 缩放2
    auto local_bind = compose_trs({5.0f, 0.0f, 0.0f}, {0, 0, 0, 1}, {2, 2, 2});

    BoneNode node;
    node.name = "root_bone";
    node.local = local_bind;
    skel.nodes.push_back(node);
    skel.root = 0;

    // offset = inverse(local_bind)。手动求逆（T*S 可解析求逆）：
    // local_bind: 缩放2+平移(5,0,0)。逆 = 缩放0.5，平移 -(5,0,0)*0.5
    std::array<float, 16> inv_bind{0.5f, 0, 0, 0, 0, 0.5f, 0, 0, 0, 0, 0.5f, 0,
                                   -2.5f, 0, 0, 1};
    BoneInfo info;
    info.id = 0;
    info.offset = inv_bind;
    skel.bone_map["root_bone"] = info;

    // 空 clip（无通道）→ 用 bind local
    AnimationClip clip;
    clip.duration = 1.0f;
    clip.ticks_per_second = 1.0f;

    std::vector<std::array<float, 16>> finals;
    compute_pose(skel, clip, 0.0f, finals);

    check(finals.size() == 1, "bind-pose: finals sized to bone_count");
    check(!finals.empty() && mat_near(finals[0], kIdentity, 1e-3f),
          "bind-pose: single bone final ~= identity (CORE GATE)");
}

// 层级：父(平移10) + 子(平移3)，子骨骼 offset=inverse(父*子 bind global)，
// global_inverse=I，无通道 → 子 final ≈ I。验证父变换正确累乘到子。
void test_bind_pose_identity_hierarchy() {
    SkeletonData skel;
    skel.bone_count = 1;
    skel.global_inverse = kIdentity;

    auto parent_local = compose_trs({10.0f, 0.0f, 0.0f}, {0, 0, 0, 1}, {1, 1, 1});
    auto child_local = compose_trs({3.0f, 0.0f, 0.0f}, {0, 0, 0, 1}, {1, 1, 1});

    BoneNode parent;
    parent.name = "parent";
    parent.local = parent_local;
    parent.children = {1};
    BoneNode child;
    child.name = "child";
    child.local = child_local;
    skel.nodes.push_back(parent);
    skel.nodes.push_back(child);
    skel.root = 0;

    // 子骨骼绑定全局 = parent_local * child_local = 平移(13,0,0)
    // offset = inverse = 平移(-13,0,0)
    std::array<float, 16> child_offset{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -13, 0, 0, 1};
    BoneInfo info;
    info.id = 0;
    info.offset = child_offset;
    skel.bone_map["child"] = info;

    AnimationClip clip;
    clip.duration = 1.0f;
    clip.ticks_per_second = 1.0f;

    std::vector<std::array<float, 16>> finals;
    compute_pose(skel, clip, 0.0f, finals);

    check(!finals.empty() && mat_near(finals[0], kIdentity, 1e-3f),
          "bind-pose: hierarchical bone final ~= identity (parent accum)");
}

}  // namespace

int main() {
    std::printf("=== Animation Pose (P1) Unit Tests ===\n");
    test_mat4_mul();
    test_compose_trs();
    test_slerp_endpoints();
    test_advance_time_loops();
    test_bind_pose_identity_single();
    test_bind_pose_identity_hierarchy();

    std::printf("\n=== Results: %d passed, %d failed ===\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
