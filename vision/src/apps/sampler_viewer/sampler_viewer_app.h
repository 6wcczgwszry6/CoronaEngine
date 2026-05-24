#pragma once

#include <memory>

namespace vision {

class SamplerViewerApp {
public:
    SamplerViewerApp();
    ~SamplerViewerApp();

    int run();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}// namespace vision
