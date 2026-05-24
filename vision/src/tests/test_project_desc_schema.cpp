#include "base/import/project_desc.h"
#include "core/util/logging.h"

#include <algorithm>
#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string_view>
#include <vector>

#include <spdlog/details/null_mutex.h>
#include <spdlog/details/os.h>
#include <spdlog/sinks/base_sink.h>

using namespace vision;

namespace {

template<typename Mutex>
class VectorSink final : public spdlog::sinks::base_sink<Mutex> {
private:
    std::vector<std::string> lines_{};

protected:
    void sink_it_(const spdlog::details::log_msg &msg) override {
        spdlog::memory_buf_t formatted;
        this->formatter_->format(msg, formatted);
        auto eol_len = strlen(spdlog::details::os::default_eol);
        using diff_t = typename std::iterator_traits<decltype(formatted.end())>::difference_type;
        lines_.emplace_back(formatted.begin(), formatted.end() - static_cast<diff_t>(eol_len));
    }

    void flush_() override {}

public:
    [[nodiscard]] const std::vector<std::string> &lines() const noexcept { return lines_; }
};

using TestSink = VectorSink<spdlog::details::null_mutex>;

class LoggerCapture {
private:
    spdlog::logger &logger_;
    std::vector<spdlog::sink_ptr> old_sinks_{};
    spdlog::level::level_enum old_level_{};
    spdlog::level::level_enum old_flush_level_{};
    std::shared_ptr<TestSink> sink_{};

public:
    LoggerCapture()
        : logger_(ocarina::core::logger()),
          old_sinks_(logger_.sinks()),
          old_level_(logger_.level()),
          old_flush_level_(logger_.flush_level()),
          sink_(std::make_shared<TestSink>()) {
        logger_.sinks().clear();
        logger_.sinks().push_back(sink_);
        logger_.set_pattern("%v");
        logger_.set_level(spdlog::level::warn);
        logger_.flush_on(spdlog::level::warn);
    }

    ~LoggerCapture() {
        logger_.sinks() = old_sinks_;
        logger_.set_level(old_level_);
        logger_.flush_on(old_flush_level_);
    }

    [[nodiscard]] const std::vector<std::string> &lines() const noexcept {
        return sink_->lines();
    }
};

[[nodiscard]] bool contains_substring(const std::vector<std::string> &lines,
                                      std::string_view expected) noexcept {
    return std::any_of(lines.begin(), lines.end(), [&](const std::string &line) {
        return line.find(expected) != std::string::npos;
    });
}

void dump_lines_if_failed(std::string_view test_name,
                          bool ok,
                          const std::vector<std::string> &lines) {
    if (ok) {
        return;
    }
    std::cerr << "[LOGS] " << test_name << std::endl;
    if (lines.empty()) {
        std::cerr << "  <empty>" << std::endl;
        return;
    }
    for (const auto &line : lines) {
        std::cerr << "  " << line << std::endl;
    }
}

bool expect(bool condition, std::string_view message) {
    if (!condition) {
        std::cerr << "[FAIL] " << message << std::endl;
        return false;
    }
    return true;
}

fs::path write_scene_file(std::string_view name, std::string_view content) {
    auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    const fs::path dir = fs::temp_directory_path() / format("vision-test-project-desc-schema-{}", stamp);
    fs::create_directories(dir);
    const fs::path scene = dir / std::string{name};
    std::ofstream out(scene, std::ios::binary);
    out << content;
    out.close();
    return scene;
}

bool test_accepts_nested_schema_without_output() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "transform": {
          "type": "matrix4x4",
          "param": {
            "matrix4x4": [
              [1.0, 0.0, 0.0, 0.0],
              [0.0, 1.0, 0.0, 0.0],
              [0.0, 0.0, 1.0, 0.0],
              [0.0, 0.0, 0.0, 1.0]
            ]
          }
        },
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32],
          "tone_mapper": {
            "type": "linear"
          },
          "upsampler": {
            "type": "bilateral"
          }
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("nested_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(desc.scene_path == scene_path.parent_path(), "scene path should be initialized from parent directory");
    ok &= expect(lines.empty(), "valid nested schema should not emit warnings or errors");
    dump_lines_if_failed("test_accepts_nested_schema_without_output", ok, lines);
    return ok;
}

bool test_accepts_missing_render_spectrum_block() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("missing_spectrum_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(lines.empty(), "missing render.spectrum should not emit warnings or errors");
    ok &= expect(desc.renderer_desc.spectrum_desc.sub_type == "srgb",
                 "missing render.spectrum should default spectrum type to srgb");
    dump_lines_if_failed("test_accepts_missing_render_spectrum_block", ok, lines);
    return ok;
}

bool test_rejects_legacy_flat_schema() {
    constexpr std::string_view json = R"JSON(
{
  "camera": {
    "type": "thin_lens",
    "param": {
      "fov_y": 45.0,
      "focal_distance": 5.0,
      "lens_radius": 0.25,
      "filter": {
        "type": "box"
      }
    }
  },
  "materials": [],
  "mediums": {
    "process": false,
    "list": []
  },
  "shapes": [],
  "lights": [],
  "sampler": {
    "type": "independent"
  },
  "integrator": {
    "type": "pt",
    "param": {
      "max_depth": 2,
      "min_depth": 0
    }
  },
  "light_sampler": {
    "type": "uniform",
    "param": {}
  },
  "spectrum": {
    "type": "srgb"
  },
  "render_setting": {
    "polymorphic_mode": 1,
    "min_world_radius": 1.0,
    "ray_offset_factor": 1.0
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("legacy_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(contains_substring(lines, "invalid scene schema: old flat top-level format is not supported"),
           "legacy flat schema should emit a warning");
    ok &= expect(desc.pipeline_desc.sub_type == "fixed",
           "legacy flat schema should continue with default pipeline fallback");
    dump_lines_if_failed("test_rejects_legacy_flat_schema", ok, lines);
    return ok;
}

bool test_unknown_top_level_key_warns_and_continues() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  },
  "debug": {
    "enabled": true
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("unknown_key_scene.json", json);
    LoggerCapture capture;
    [[maybe_unused]] ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(contains_substring(lines, "unknown top-level key 'debug'"),
                 "unknown top-level key should emit a warning");
    ok &= expect(!contains_substring(lines, "invalid scene schema"),
                 "unknown top-level key should not fail schema validation");
    dump_lines_if_failed("test_unknown_top_level_key_warns_and_continues", ok, lines);
    return ok;
}

bool test_rejects_missing_scene_camera_block() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("missing_camera_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(desc.scene_desc.sensor_desc.sub_type == "thin_lens",
           "missing scene.camera should fall back to default sensor type");
    ok &= expect(contains_substring(lines, "invalid scene schema: missing block 'scene.camera'"),
           "missing scene.camera should emit a warning");
    dump_lines_if_failed("test_rejects_missing_scene_camera_block", ok, lines);
    return ok;
}

bool test_rejects_malformed_integrator_block() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": "pt",
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("malformed_integrator_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(desc.renderer_desc.integrator_desc.sub_type == "pt",
           "malformed render.integrator should fall back to default integrator type");
    ok &= expect(contains_substring(lines, "invalid scene schema: 'render.integrator' must be an object"),
           "malformed render.integrator should emit a warning");
    dump_lines_if_failed("test_rejects_malformed_integrator_block", ok, lines);
    return ok;
}

bool test_rejects_missing_pipeline_frame_buffer_block() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "rasterizer": {
        "type": "cpu"
      }
    }
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("missing_frame_buffer_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(desc.pipeline_desc.frame_buffer_desc.sub_type == "normal",
           "missing pipeline.param.frame_buffer should fall back to default frame buffer type");
    ok &= expect(contains_substring(lines, "invalid scene schema: missing block 'pipeline.param.frame_buffer'"),
           "missing pipeline.param.frame_buffer should emit a warning");
    dump_lines_if_failed("test_rejects_missing_pipeline_frame_buffer_block", ok, lines);
    return ok;
}

bool test_rejects_output_resolution_field() {
    constexpr std::string_view json = R"JSON(
{
  "scene": {
    "camera": {
      "type": "thin_lens",
      "param": {
        "fov_y": 45.0,
        "focal_distance": 5.0,
        "lens_radius": 0.25,
        "filter": {
          "type": "box"
        }
      }
    },
    "materials": [],
    "mediums": {
      "process": false,
      "list": []
    },
    "shapes": [],
    "lights": []
  },
  "render": {
    "sampler": {
      "type": "independent"
    },
    "integrator": {
      "type": "pt",
      "param": {
        "max_depth": 2,
        "min_depth": 0
      }
    },
    "light_sampler": {
      "type": "uniform",
      "param": {}
    },
    "spectrum": {
      "type": "srgb"
    },
    "render_setting": {
      "polymorphic_mode": 1,
      "min_world_radius": 1.0,
      "ray_offset_factor": 1.0
    }
  },
  "pipeline": {
    "type": "fixed",
    "param": {
      "frame_buffer": {
        "type": "normal",
        "param": {
          "resolution": [32, 32]
        }
      },
      "rasterizer": {
        "type": "cpu"
      }
    }
  },
  "output": {
    "spp": 16,
    "fn": "output.exr",
    "denoise": true,
    "resolution": [64, 64]
  }
}
)JSON";

    const fs::path scene_path = write_scene_file("output_resolution_scene.json", json);
    LoggerCapture capture;
    ProjectDesc desc = ProjectDesc::from_json(scene_path);
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(desc.output_desc.denoise,
           "output.denoise should still be accepted");
    ok &= expect(contains_substring(lines,
           "invalid scene schema: 'output.resolution' is not supported; use 'pipeline.param.frame_buffer.param.resolution'"),
           "output.resolution should emit a migration warning");
    dump_lines_if_failed("test_rejects_output_resolution_field", ok, lines);
    return ok;
}

}// namespace

int main() {
    bool ok = true;
    ok &= test_accepts_nested_schema_without_output();
    ok &= test_accepts_missing_render_spectrum_block();
    ok &= test_rejects_legacy_flat_schema();
    ok &= test_unknown_top_level_key_warns_and_continues();
    ok &= test_rejects_missing_scene_camera_block();
    ok &= test_rejects_malformed_integrator_block();
    ok &= test_rejects_missing_pipeline_frame_buffer_block();
    ok &= test_rejects_output_resolution_field();
    if (!ok) {
        return 1;
    }
    std::cout << "ProjectDesc schema test passed." << std::endl;
    return 0;
}