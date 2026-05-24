#pragma once

#include "material_viewer_shared.h"

#include <memory>

namespace vision {

class MaterialViewerGLRenderer {
public:
    MaterialViewerGLRenderer();
    ~MaterialViewerGLRenderer();

    void initialize() noexcept;
    [[nodiscard]] bool is_available() const noexcept;
    void shutdown() noexcept;
    void update_meshes(const PreviewData &preview,
                       const ViewerState &state,
                       ocarina::uint2 window_size) noexcept;
    void render() noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}// namespace vision