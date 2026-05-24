//
// Created by Zero on 02/09/2022.
//

#include "application.h"

#include <exception>
#include <iostream>

using namespace ocarina;
using namespace vision;

int main(int argc, char *argv[]) {
    fs::path runtime_dir = fs::path(argv[0]).parent_path();
    fs::current_path(runtime_dir);
    try {
        return App(argc, argv).run();
    } catch (const std::exception &e) {
        std::cerr << "startup failed: " << e.what() << std::endl;
        return -1;
    } catch (...) {
        std::cerr << "startup failed: unknown error" << std::endl;
        return -1;
    }
}