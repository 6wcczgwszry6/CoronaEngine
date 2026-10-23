/*
Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.

NVIDIA CORPORATION and its licensors retain all intellectual property
and proprietary rights in and to this software, related documentation
and any modifications thereto. Any use, reproduction, disclosure or
distribution of this software and related documentation without an express
license agreement from NVIDIA CORPORATION is strictly prohibited.
*/

// This software contains source code provided by NVIDIA Corporation.
// NRD 4.14.3 front/back-end packing. See LICENSE-NRD.txt.
#include "utils.h"

namespace vision::reblur {
void Filter::compile_modulation(Device &device) {
    Kernel pack = [](Var<FilterParam> p) {
        auto guides = guide_view(p.guide);
        // One warp packs a 16x16 tile and shares the validity reads with classification.
        ocarina::configure_block(32u);
        Uint lane = dispatch_id() % 32u, tile = dispatch_id() / 32u;
        Uint width = (p.size.x + 15u) / 16u;
        Uint2 origin = make_uint2(tile % width, tile / width) * 16u;
        Uint active = 0u;
        $for(k, 8u) {
            Uint t = k * 32u + lane;
            Uint2 q = origin + make_uint2(t % 16u, t / 16u);
            $if(all(q < p.size)) {
                Uint i = q.y * p.size.x + q.x;
                auto g = guides.read(i);
                $if(valid_guide(g)) {
                    active = 1u;
                    Float4 d = pack_signal(p.raw_diffuse.read(i), g.diffuse_factor.xyz(), g.position.w, 1.f);
                    Float4 s = pack_signal(p.raw_specular.read(i), g.specular_factor.xyz(), g.position.w, g.normal_roughness.w);
                    p.dst_diffuse.write(i, store_half(d)); p.dst_specular.write(i, store_half(s));
                };
            };
        };
        Uint count = ocarina::warp_active_count_bits(active != 0u);
        $if(lane == 0u) { p.tiles.write(tile, count); };
    };
    pack_ = device.compile(pack, "REBLUR-ClassifyAndPack");
}
}
