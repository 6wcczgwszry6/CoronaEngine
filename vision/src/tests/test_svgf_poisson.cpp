// Standalone CPU check: clang++ -std=c++17 test_svgf_poisson.cpp -o test_svgf_poisson.exe
#include <cmath>
#include <iostream>
#include <set>
#include <utility>

using uint = unsigned int;
#include "../render_core/denoiser/SVGF/svgf_config.h"

int main() {
    using Disk = vision::svgf::SVGFConfig::PoissonDisk;
    // A linear illumination ramp must not drift under a symmetric spatial filter.
    // Repeated taps (including the explicit centre) would also underestimate
    // propagated variance by treating the same input as independent samples.
    for (auto step : vision::svgf::SVGFConfig::Poisson::kStepSizes) {
        std::set<std::pair<int, int>> pixels{{0, 0}};
        double moment_x = 0.0, moment_y = 0.0;
        for (uint i = 0; i < Disk::kSampleCount; ++i) {
            const int x = static_cast<int>(std::round(Disk::kSamplesX[i] * (Disk::kRadius * step)));
            const int y = static_cast<int>(std::round(Disk::kSamplesY[i] * (Disk::kRadius * step)));
            if (!pixels.emplace(x, y).second) {
                std::cerr << "FAIL: duplicate pixel biases variance at step " << step << '\n';
                return 1;
            }
            moment_x += x * Disk::kWeights[i];
            moment_y += y * Disk::kWeights[i];
        }
        if (std::abs(moment_x) > 1e-5 || std::abs(moment_y) > 1e-5) {
            std::cerr << "FAIL: spatial filter shifts a linear illumination ramp\n";
            return 1;
        }
    }
    std::cout << "PASS: Poisson taps preserve ramps and sample independent pixels at every scale\n";
}
