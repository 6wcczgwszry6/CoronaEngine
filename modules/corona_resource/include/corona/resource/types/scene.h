#pragma once
#include <array>
#include <cstdint>
#include <deque>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

#include "corona/resource/resource.h"
#include "corona/resource/types/image.h"

namespace Corona::Resource {

constexpr std::uint32_t InvalidIndex = UINT32_MAX;
constexpr std::uint64_t InvalidTextureId = UINT64_MAX;

struct Transform {
    std::array<float, 3> position{0.0f, 0.0f, 0.0f};
    std::array<float, 3> rotation{0.0f, 0.0f, 0.0f};
    std::array<float, 3> scale{1.0f, 1.0f, 1.0f};
};

struct AABB {
    std::array<float, 3> min{};
    std::array<float, 3> max{};
};

#pragma pack(push, 1)
struct Vertex {
    std::array<float, 3> position{};
    std::array<float, 3> normal{};
    std::array<float, 2> tex_coords{};
};
#pragma pack(pop)

/// 每顶点骨骼影响上限（与着色/教程一致）
constexpr int MAX_BONE_INFLUENCE = 4;

/// 单顶点的骨骼权重（仅 CPU 端，不上传 GPU）。
/// 与 MeshData::vertices 等长并行存储；CPU 蒙皮时读取，
/// 蒙皮输出仍是标准 32 字节 Vertex，故 GPU 布局不变。
struct BoneWeights {
    std::array<std::int32_t, MAX_BONE_INFLUENCE> ids{-1, -1, -1, -1};
    std::array<float, MAX_BONE_INFLUENCE> weights{0.0f, 0.0f, 0.0f, 0.0f};

    /// 填入首个空槽（ids[i] < 0）。返回 false 表示 4 个槽已满（权重被丢弃）。
    bool add_influence(std::int32_t bone_id, float weight) {
        if (weight <= 0.0f) return true;  // 0 权重无意义，视为成功忽略
        for (int i = 0; i < MAX_BONE_INFLUENCE; ++i) {
            if (ids[i] < 0) {
                ids[i] = bone_id;
                weights[i] = weight;
                return true;
            }
        }
        return false;
    }
};

/// LOD 级别数据（独立顶点+索引，可直接用于渲染或物理碰撞）
struct LODLevel {
    std::vector<Vertex> vertices;
    std::vector<std::uint16_t> indices;
    float error = 0.0f;             // meshopt 计算的几何误差
    float screen_threshold = 0.0f;  // 建议屏幕占比切换阈值

    // 骨骼权重（仅蒙皮网格非空，与本级 vertices 等长并行）。
    // 蒙皮网格的 LOD 也需蒙皮（渲染选级 / 最简 LOD 碰撞），故随顶点同步 remap。
    std::vector<BoneWeights> bone_weights;
};

struct MeshData {
    std::vector<Vertex> vertices;
    std::vector<std::uint16_t> indices;
    std::uint32_t material_index = InvalidIndex;
    std::array<float, 3> aabb_min{};
    std::array<float, 3> aabb_max{};

    // LOD 级别（LOD 1..N，LOD 0 即为 vertices/indices）
    std::vector<LODLevel> lod_levels;

    // 骨骼权重（仅蒙皮网格非空，与 vertices 等长并行）。
    // 经 meshopt remap / 拆分 / LOD 时必须与 vertices 用同一 remap 表同步重排。
    std::vector<BoneWeights> bone_weights;

    // 原始变换信息（用于恢复原始尺寸）
    std::array<float, 3> original_center{0.0f, 0.0f, 0.0f};
    float original_scale_factor{1.0f};  // 归一化时使用的缩放因子
    bool is_normalized{false};

    /// 是否为蒙皮网格（携带骨骼权重）
    [[nodiscard]] bool is_skinned() const { return !bone_weights.empty(); }
};

/// LOD 生成配置
struct LODGenerationOptions {
    bool enabled = false;                                    // 是否生成 LOD
    std::uint32_t level_count = 3;                            // LOD 级数（不含 LOD 0）
    std::vector<float> target_ratios = {0.5f, 0.25f, 0.05f};  // 各级三角形保留比例
    std::vector<float> max_errors = {0.05f, 0.2f, 1.0f};      // 各级最大允许误差（越大简化越激进）
    std::vector<std::uint32_t> max_triangles = {0, 0, 200};   // 各级三角形数上限（0=不限制，仅用 ratio）
};

// Assimp 导入选项
struct AssimpImportOptions {
    bool simplify_mesh = true;           // 是否启用网格简化
    float simplification_error = 0.01f;  // 简化误差阈值
    LODGenerationOptions lod_options;    // LOD 生成配置
    ImageImportOptions image_options;    // 纹理导入选项
};

// 透明度混合模式
enum class AlphaMode : std::uint32_t {
    Opaque = 0,  // 完全不透明，忽略 alpha
    Mask = 1,    // Alpha 测试（cutoff）
    Blend = 2    // Alpha 混合
};

struct MaterialData {
    std::array<float, 4> base_color{1.0f, 1.0f, 1.0f, 1.0f};
    float metallic = 0.0f;
    float roughness = 0.5f;
    float ior = 1.5f;

    // 透明度相关属性
    AlphaMode alpha_mode = AlphaMode::Opaque;
    float alpha_cutoff = 0.5f;  // 仅在 AlphaMode::Mask 时使用

    std::uint64_t albedo_texture = InvalidTextureId;
    std::uint64_t normal_texture = InvalidTextureId;
    std::uint64_t metallic_texture = InvalidTextureId;
    std::uint64_t roughness_texture = InvalidTextureId;
    std::uint64_t opacity_texture = InvalidTextureId;  // 独立的透明度纹理
    std::string name;
};

struct LightData {
    enum class LightType : std::uint32_t {
        Point = 0,
        Directional = 1,
        Spot = 2,
        Area = 3
    };

    LightType type = LightType::Point;
    float intensity = 1.0f;
    float radius = 1.0f;
    float inner_angle = 30.0f;
    float outer_angle = 45.0f;
    std::array<float, 3> color{1.0f, 1.0f, 1.0f};
    std::array<float, 2> size{1.0f, 1.0f};
    float _padding[2]{};
};

struct CameraData {
    float fov = 60.0f;
    float near_clip = 0.1f;
    float far_clip = 1000.0f;
    float aspect_ratio = 1.77778f;
};

struct NodeData {
    Transform transform;

    NodeData* parent = nullptr;
    std::vector<NodeData*> children;

    std::uint32_t mesh_index = InvalidIndex;
    std::uint32_t light_index = InvalidIndex;
    std::uint32_t camera_index = InvalidIndex;

    std::string name;
};

// ============================================================================
// 骨骼动画数据（绑定期导入，运行时只读）
// ============================================================================

/// 单根骨骼的元信息：在 final_bone_matrices 数组中的索引 + offset 矩阵。
/// offset（assimp mOffsetMatrix）把顶点从「网格绑定空间」变到「该骨骼空间」。
/// 矩阵以列主序（column-major，4 列各 4 个 float）存储，与 ktm/glsl 一致；
/// 导入期由 ai_to_mat4_colmajor 完成行主→列主转置。
struct BoneInfo {
    std::int32_t id = -1;
    std::array<float, 16> offset{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
};

/// 骨架层级节点（扁平存储，children 用索引引用，避免裸指针 / 复制悬挂）。
/// local 为该节点相对父节点的绑定姿态局部变换（列主序）。
struct BoneNode {
    std::string name;
    std::array<float, 16> local{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
    std::vector<int> children;  // SkeletonData::nodes 中的下标
};

/// 一根骨骼的动画通道：位置/旋转/缩放关键帧（各自带时间戳，单位 tick）。
/// 旋转用四元数 (x, y, z, w)，运行时用 Slerp 插值。
struct AnimChannel {
    std::string bone_name;
    std::vector<std::pair<float, std::array<float, 3>>> positions;  // (time, xyz)
    std::vector<std::pair<float, std::array<float, 4>>> rotations;  // (time, quat xyzw)
    std::vector<std::pair<float, std::array<float, 3>>> scales;     // (time, xyz)
};

/// 一个动画片段（对应 assimp aiAnimation）。
struct AnimationClip {
    std::string name;
    float duration = 0.0f;          // 总时长（tick）
    float ticks_per_second = 25.0f;  // 每秒 tick 数（0 时回退默认）
    std::vector<AnimChannel> channels;
};

/// 骨架：层级 + 骨骼映射 + 全局逆变换（global inverse）。
struct SkeletonData {
    std::vector<BoneNode> nodes;                          // 扁平层级树
    int root = 0;                                         // 根节点下标
    std::unordered_map<std::string, BoneInfo> bone_map;   // 骨骼名 → {id, offset}
    int bone_count = 0;                                   // 唯一骨骼数（= final 矩阵数组长度）
    std::array<float, 16> global_inverse{1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
};

struct SceneData {
    std::vector<MeshData> meshes;
    std::vector<MaterialData> materials;
    std::vector<LightData> lights;
    std::vector<CameraData> cameras;

    std::deque<NodeData> nodes;

    // 骨骼动画（仅蒙皮模型非空）。skeleton 有值即视为蒙皮场景。
    std::optional<SkeletonData> skeleton;
    std::vector<AnimationClip> animations;
};

class Scene : public IResource {
   public:
    explicit Scene(const std::filesystem::path& path);
    ~Scene() override = default;

    SceneData data;

    [[nodiscard]] std::string_view get_node_name(std::uint32_t node_idx) const;
    [[nodiscard]] std::string_view get_material_name(std::uint32_t mat_idx) const;

    std::uint32_t add_node(std::string_view name, std::uint32_t parent = InvalidIndex);

    template <typename F>
    void for_each_child(std::uint32_t node_idx, F&& func) const {
        const auto& nd = data.nodes[node_idx];
        for (auto* child_ptr : nd.children) {
            std::uint32_t idx = 0;
            for (const auto& candidate : data.nodes) {
                if (&candidate == child_ptr) break;
                ++idx;
            }
            if (idx < data.nodes.size()) {
                func(idx);
            }
        }
    }
    std::uint32_t add_mesh(MeshData&& mesh);

    // 修改：返回底层容器的常量引用（零拷贝）
    [[nodiscard]] const std::vector<Vertex>& get_mesh_vertices(std::uint32_t mesh_idx) const;
    [[nodiscard]] const std::vector<std::uint16_t>& get_mesh_indices(std::uint32_t mesh_idx) const;

    [[nodiscard]] const Vertex& get_vertex_global(std::uint32_t mesh_idx, std::uint16_t local_index) const;

    /// 获取指定 mesh 的 LOD 级数（不含 LOD 0）
    [[nodiscard]] std::uint32_t get_mesh_lod_count(std::uint32_t mesh_idx) const;
    /// 获取指定 mesh 的指定 LOD 级别数据（0=最高精度即 mesh 本身的 vertices/indices，1..N 为低精度）
    [[nodiscard]] const LODLevel& get_mesh_lod(std::uint32_t mesh_idx, std::uint32_t lod_level) const;

    /// 计算整个场景所有 mesh 合并后的 AABB 包围盒
    [[nodiscard]] AABB get_scene_aabb() const;

    /// 是否为蒙皮场景（已导入骨架数据）。运行时据此决定是否走 CPU 蒙皮路径。
    [[nodiscard]] bool is_skinned() const { return data.skeleton.has_value(); }
};

class SceneParser : public IParser {
   public:
    SceneParser();
    ~SceneParser() override = default;

    /// 设置 Assimp 导入选项（在 import 之前调用）
    AssimpImportOptions assimp_options;

   protected:
    std::shared_ptr<IResource> parse_assimp(const std::filesystem::path& path);
};

}  // namespace Corona::Resource
