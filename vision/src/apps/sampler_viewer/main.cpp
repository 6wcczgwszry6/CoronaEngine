#include "sampler_viewer_app.h"

#include <filesystem>

int main(int argc, char *argv[]) {
    if (argc > 0) {
        std::filesystem::path exe_path(argv[0]);
        if (exe_path.has_parent_path()) {
            std::filesystem::current_path(exe_path.parent_path());
        }
    }
    vision::SamplerViewerApp app;
    return app.run();
}
