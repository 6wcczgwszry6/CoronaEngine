#include "../shadow_culling.h"

#include <cassert>
#include <cmath>

using namespace Corona::Systems::OpticsDetail;

int main() {
    const auto view = make_shadow_cascade_view(
        ktm::fmat4x4::from_eye(), 20.0f, 10.0f, 1024.0f);
    assert(std::abs(view.world_units_per_texel - (20.0f / 1024.0f)) < 1.0e-6f);

    Corona::Spatial::AABB inside;
    inside.min = {-0.5f, -0.5f, 0.1f};
    inside.max = {0.5f, 0.5f, 0.9f};
    assert(shadow_caster_visible(view.frustum, inside));

    Corona::Spatial::AABB outside;
    outside.min = {10.0f, 10.0f, 0.1f};
    outside.max = {11.0f, 11.0f, 0.9f};
    assert(!shadow_caster_visible(view.frustum, outside));

    Corona::Spatial::AABB invalid;
    invalid.min = {NAN, 0.0f, 0.0f};
    invalid.max = {1.0f, 1.0f, 1.0f};
    assert(shadow_caster_visible(view.frustum, invalid));

    std::array<float, 8> errors{0.0f, 0.05f, 0.15f, 0.4f, 0.8f, 1.0f, 1.0f, 1.0f};
    assert(select_shadow_lod_level(errors, 4, 1.0f, 0.2f, 0) == 2);
    assert(select_shadow_lod_level(errors, 4, 1.0f, 0.01f, 0) == 0);
    assert(select_shadow_lod_level(errors, 0, 1.0f, 1.0f, 3) == 3);
    return 0;
}
