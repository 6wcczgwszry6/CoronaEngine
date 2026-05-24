#pragma once

#include "material_viewer_shared.h"

namespace vision {

void draw_preview_background(std::vector<ocarina::uchar4> &pixels,
                             ocarina::uint2 image_size,
                             const PreviewData &preview,
                             const ViewerState &state);

}// namespace vision