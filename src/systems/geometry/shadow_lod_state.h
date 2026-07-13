#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

namespace Corona::Systems::GeometryDetail {
constexpr std::uint64_t kShadowLodRequestTtlFrames = 120;
struct ShadowLodState { int committed=-1; int previous=-1; bool swap_in_progress=false; std::uint64_t last_request_frame=0; };
struct ShadowLodDecision {
    int target=-1; bool expired=false; bool needs_build=false; int main_level=0; int main_previous=-1; int shadow_previous=-1;
    [[nodiscard]] bool keep_level(int level) const noexcept { return level==0 || level==main_level || level==main_previous || level==target || level==shadow_previous; }
};
[[nodiscard]] inline int choose_shadow_target(const std::array<float,8>& errors,int level_count,float max_abs_scale,float texel,int fallback) noexcept {
    if(level_count<=0 || !std::isfinite(texel) || texel<=0.0f || !std::isfinite(max_abs_scale)) return fallback;
    int target=std::clamp(fallback,0,level_count-1); const float scale=std::max(std::abs(max_abs_scale),1.0e-6f);
    for(int i=0;i<level_count;++i){const float e=errors[static_cast<size_t>(i)]*scale;if(std::isfinite(e)&&e<=texel)target=i;} return target;
}
[[nodiscard]] inline ShadowLodDecision decide_shadow_lod(const ShadowLodState& state,std::uint64_t frame,int main_level,int main_previous,int level_count) noexcept {
    ShadowLodDecision d; d.target=state.committed; d.main_level=main_level; d.main_previous=main_previous; d.shadow_previous=state.previous;
    if(state.committed>=0 && frame>state.last_request_frame && frame-state.last_request_frame>kShadowLodRequestTtlFrames){d.target=-1;d.expired=true;}
    if(d.target>=level_count)d.target=level_count-1; d.needs_build=d.target>=1; return d;
}
} // namespace Corona::Systems::GeometryDetail
