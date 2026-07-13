#include "../shadow_lod_state.h"
#include <cassert>
using namespace Corona::Systems::GeometryDetail;
int main(){std::array<float,4> e{0.0f,0.05f,0.2f,0.8f};assert(choose_shadow_target(e,4,1.0f,0.2f,0)==2);assert(choose_shadow_target(e,4,1.0f,0.01f,0)==0);ShadowLodState s{2,1,true,100};auto live=decide_shadow_lod(s,220,0,3,4);assert(!live.expired&&live.target==2&&live.keep_level(1));auto expired=decide_shadow_lod(s,221,0,3,4);assert(expired.expired&&expired.target==-1);assert(expired.keep_level(0)&&expired.keep_level(3));}
