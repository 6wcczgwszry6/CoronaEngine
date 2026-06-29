#pragma once

/// @file gpu_mem_ledger.h
/// @brief 进程级 GPU 显存账本（mesh / texture 两类）+ RAII 字节令牌。
///
/// 仅做"记账"——构造时计入、析构时扣减，不做任何淘汰。由 geometry system 在
/// 创建 GPU 缓冲/纹理处用 GpuMemToken 喂养，令牌挂在 MeshDevice / LODMeshBuffers
/// 上，随其生命周期自动增减（含槽位复用、buffer 收缩、显式 clear、Python 槽位回收）。
///
/// 头文件 only（inline 单例 + 内联令牌），无 .cpp、无链接依赖，可被任意 TU 包含。
/// 设计依据：Storage<T> 以 `*ptr = T{}`（移动赋值）复用槽位、deallocate 不析构槽位，
/// 故真实 HardwareBuffer 的释放时机与 MeshDevice 析构时机一致 —— 令牌与之同寿。

#include <atomic>
#include <cstddef>
#include <cstdint>

namespace Corona::Memory {

/// 资源类别：mesh（顶点/索引缓冲）或 texture（纹理）。
enum class ResKind : std::uint8_t { Mesh = 0, Texture = 1 };

/// GPU 显存账本：mesh / texture 两类原子计数 + 峰值。仅统计，线程安全。
class GpuLedger {
   public:
    void add(ResKind kind, std::size_t bytes) noexcept {
        if (bytes == 0) return;
        if (kind == ResKind::Mesh) {
            const std::size_t now = mesh_bytes_.fetch_add(bytes, std::memory_order_relaxed) + bytes;
            bump_peak(mesh_peak_, now);
        } else {
            const std::size_t now = tex_bytes_.fetch_add(bytes, std::memory_order_relaxed) + bytes;
            bump_peak(tex_peak_, now);
        }
    }

    void sub(ResKind kind, std::size_t bytes) noexcept {
        if (bytes == 0) return;
        if (kind == ResKind::Mesh)
            mesh_bytes_.fetch_sub(bytes, std::memory_order_relaxed);
        else
            tex_bytes_.fetch_sub(bytes, std::memory_order_relaxed);
    }

    [[nodiscard]] std::size_t mesh_bytes() const noexcept {
        return mesh_bytes_.load(std::memory_order_relaxed);
    }
    [[nodiscard]] std::size_t texture_bytes() const noexcept {
        return tex_bytes_.load(std::memory_order_relaxed);
    }
    [[nodiscard]] std::size_t total_bytes() const noexcept {
        return mesh_bytes() + texture_bytes();
    }
    [[nodiscard]] std::size_t mesh_peak() const noexcept {
        return mesh_peak_.load(std::memory_order_relaxed);
    }
    [[nodiscard]] std::size_t texture_peak() const noexcept {
        return tex_peak_.load(std::memory_order_relaxed);
    }

   private:
    static void bump_peak(std::atomic<std::size_t>& peak, std::size_t now) noexcept {
        std::size_t cur = peak.load(std::memory_order_relaxed);
        while (now > cur && !peak.compare_exchange_weak(cur, now, std::memory_order_relaxed)) {
        }
    }

    std::atomic<std::size_t> mesh_bytes_{0};
    std::atomic<std::size_t> tex_bytes_{0};
    std::atomic<std::size_t> mesh_peak_{0};
    std::atomic<std::size_t> tex_peak_{0};
};

/// 进程级单例。故意泄漏（never destroyed），避免静态析构顺序问题：
/// 退出时仍可能有 MeshDevice 令牌析构调用 sub()，泄漏单例保证其始终有效。
inline GpuLedger& gpu_ledger() noexcept {
    static GpuLedger* instance = new GpuLedger();
    return *instance;
}

/// move-only RAII 字节令牌：构造即计入、析构即扣减、移动转移所有权、拷贝禁止。
/// 拷贝禁止使编译器替我们标出任何对宿主结构体（MeshDevice 等）的意外拷贝。
class GpuMemToken {
   public:
    GpuMemToken() noexcept = default;

    GpuMemToken(ResKind kind, std::size_t bytes) noexcept : kind_(kind), bytes_(bytes) {
        gpu_ledger().add(kind_, bytes_);
    }

    ~GpuMemToken() {
        if (bytes_) gpu_ledger().sub(kind_, bytes_);
    }

    GpuMemToken(GpuMemToken&& other) noexcept : kind_(other.kind_), bytes_(other.bytes_) {
        other.bytes_ = 0;
    }

    GpuMemToken& operator=(GpuMemToken&& other) noexcept {
        if (this != &other) {
            if (bytes_) gpu_ledger().sub(kind_, bytes_);
            kind_ = other.kind_;
            bytes_ = other.bytes_;
            other.bytes_ = 0;
        }
        return *this;
    }

    GpuMemToken(const GpuMemToken&) = delete;
    GpuMemToken& operator=(const GpuMemToken&) = delete;

    [[nodiscard]] std::size_t bytes() const noexcept { return bytes_; }

   private:
    ResKind     kind_  = ResKind::Mesh;
    std::size_t bytes_ = 0;
};

}  // namespace Corona::Memory
