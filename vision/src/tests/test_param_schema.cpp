//
// Created by GitHub Copilot on 2026/4/2.
//

#include "base/import/param_schema.h"
#include "core/util/logging.h"

#include <algorithm>
#include <cstring>
#include <iostream>
#include <memory>
#include <mutex>
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

GraphDesc make_desc(const DataWrap &param) {
    GraphDesc desc{"Material"};
    desc.sub_type = "test";
    desc.name = "ParamSchemaTest";
    desc.set_parameter(ParameterSet{param});
    desc.node_map.emplace("known_node", ShaderNodeDesc{AttrTag::Number, "number"});
    return desc;
}

bool test_invalid_params_emit_warnings() {
    ParamSchema schema;
    schema.add_slot("color", make_float3(1.f), AttrTag::Albedo);
    schema.add_slot("roughness", 0.5f, AttrTag::Number);
    schema.add_slot("ior", 1.5f, AttrTag::Number, true);
    schema.add_plain("remapping_roughness", ParamType::Bool);

    DataWrap param = DataWrap::object();
    param["color"] = DataWrap::array({1.f, 0.5f});
    param["ior"] = DataWrap::object({{"node", "missing_node"}});
    param["remapping_roughness"] = "yes";
    param["rougness"] = 0.5f;

    GraphDesc desc = make_desc(param);
    LoggerCapture capture;
    schema.validate(desc, "Material 'ParamSchemaTest' (type=test)");
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(contains_substring(lines, "unknown param 'rougness'"),
                 "should report unknown param warning");
    ok &= expect(contains_substring(lines, "did you mean 'roughness'"),
                 "unknown param warning should include a suggestion when close enough");
    ok &= expect(contains_substring(lines, "slot 'color' expects dim 3, got 2"),
                 "should report slot dimension mismatch");
    ok &= expect(contains_substring(lines, "slot 'ior' references node 'missing_node' which is not in node_tab"),
                 "should report missing node reference");
    ok &= expect(contains_substring(lines, "param 'remapping_roughness' expected bool, got string"),
                 "should report plain param type mismatch");
    dump_lines_if_failed("test_invalid_params_emit_warnings", ok, lines);

    return ok;
}

bool test_valid_params_emit_no_warnings() {
    ParamSchema schema;
    schema.add_slot("color", make_float3(1.f), AttrTag::Albedo);
    schema.add_slot("ior", 1.5f, AttrTag::Number);
    schema.add_plain("remapping_roughness", ParamType::Bool);

    DataWrap param = DataWrap::object();
    param["color"] = DataWrap::array({1.f, 0.5f, 0.25f});
    param["ior"] = DataWrap::object({{"node", "known_node"}, {"channels", "x"}});
    param["remapping_roughness"] = true;

    GraphDesc desc = make_desc(param);
    LoggerCapture capture;
    schema.validate(desc, "Material 'ParamSchemaTest' (type=test)");
    bool ok = expect(capture.lines().empty(), "valid params should not emit warnings");
    dump_lines_if_failed("test_valid_params_emit_no_warnings", ok, capture.lines());
    return ok;
}

bool test_node_string_and_inline_object_are_valid() {
    ParamSchema schema;
    schema.add_slot("roughness", 0.5f, AttrTag::Number);
    schema.add_slot("ior", 1.5f, AttrTag::Number);
    schema.add_slot("color", make_float3(1.f), AttrTag::Albedo);

    DataWrap param = DataWrap::object();
    param["roughness"] = DataWrap::object({{"node", "known_node"}, {"channels", "x"}});
    param["ior"] = DataWrap::object({{"node", DataWrap::object({{"type", "number"}, {"param", DataWrap::object({{"value", 1.5f}})}})},
                                      {"channels", "x"}});
    param["color"] = DataWrap::object({{"node", DataWrap::object({{"type", "image"}, {"param", DataWrap::object({{"fn", "textures/test.png"}, {"color_space", "srgb"}})}})},
                                        {"channels", "xyz"}});

    GraphDesc desc = make_desc(param);
    LoggerCapture capture;
    schema.validate(desc, "Material 'ParamSchemaTest' (type=test)");
    bool ok = expect(capture.lines().empty(), "node string and inline node object should not emit warnings");
    dump_lines_if_failed("test_node_string_and_inline_object_are_valid", ok, capture.lines());
    return ok;
}

bool test_channel_count_controls_slot_dimension() {
    ParamSchema schema;
    schema.add_slot("color", make_float3(1.f), AttrTag::Albedo);
    schema.add_slot("roughness", 0.5f, AttrTag::Number);

    DataWrap param = DataWrap::object();
    param["color"] = DataWrap::object({{"node", "known_node"}, {"channels", "x"}});
    param["roughness"] = DataWrap::object({{"node", DataWrap::object({{"type", "number"},
                                                                            {"param", DataWrap::object({{"value", DataWrap::array({0.1f, 0.2f, 0.3f})}})}})},
                                          {"channels", "x"}});

    GraphDesc desc = make_desc(param);
    LoggerCapture capture;
    schema.validate(desc, "Material 'ParamSchemaTest' (type=test)");
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(contains_substring(lines, "slot 'color' expects dim 3, got channels dim 1 ('x')"),
                 "node reference slot dimension should be derived from channel count");
    ok &= expect(!contains_substring(lines, "slot 'roughness' expects dim 1, got 3"),
                 "inline node payload dimension should not be checked against slot dim when channels are present");
    dump_lines_if_failed("test_channel_count_controls_slot_dimension", ok, lines);
    return ok;
}

bool test_inline_node_requires_param_object() {
    ParamSchema schema;
    schema.add_slot("ior", 1.5f, AttrTag::Number);
    schema.add_slot("color", make_float3(1.f), AttrTag::Albedo);

    DataWrap param = DataWrap::object();
    param["ior"] = DataWrap::object({{"node", DataWrap::object({{"type", "number"}, {"value", 1.5f}})}});
    param["color"] = DataWrap::object({{"node", DataWrap::object({{"type", "image"}, {"fn", "textures/test.png"}})}});

    GraphDesc desc = make_desc(param);
    LoggerCapture capture;
    schema.validate(desc, "Material 'ParamSchemaTest' (type=test)");
    const auto &lines = capture.lines();

    bool ok = true;
    ok &= expect(contains_substring(lines, "slot 'ior' node object must contain 'param'"),
                 "number node without param should warn");
    ok &= expect(contains_substring(lines, "slot 'color' node object must contain 'param'"),
                 "image node without param should warn");
    dump_lines_if_failed("test_inline_node_requires_param_object", ok, lines);
    return ok;
}

}// namespace

int main() {
    bool ok = true;
    ok &= test_invalid_params_emit_warnings();
    ok &= test_valid_params_emit_no_warnings();
    ok &= test_node_string_and_inline_object_are_valid();
    ok &= test_channel_count_controls_slot_dimension();
    ok &= test_inline_node_requires_param_object();
    if (!ok) {
        return 1;
    }
    std::cout << "ParamSchema test passed." << std::endl;
    return 0;
}