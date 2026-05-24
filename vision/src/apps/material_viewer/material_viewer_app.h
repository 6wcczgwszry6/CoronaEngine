#pragma once

#include <memory>

namespace vision {

class MaterialViewerApp {
public:
    MaterialViewerApp();
    ~MaterialViewerApp();

    int run();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}// namespace vision