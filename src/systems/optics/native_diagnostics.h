#pragma once

#include <array>
#include <algorithm>
#include <cstdint>
#include <optional>

namespace Corona::Systems::OpticsDetail {

inline constexpr std::uint32_t kDiagnosticShadowCascadeCount = 4;

[[nodiscard]] constexpr std::uint32_t parse_shadow_cascade_mask(
    std::optional<std::uint64_t> raw,
    std::uint32_t cascade_count = kDiagnosticShadowCascadeCount) noexcept {
    const std::uint32_t supported = cascade_count >= 32u
                                        ? 0xffffffffu
                                        : ((1u << cascade_count) - 1u);
    return raw ? static_cast<std::uint32_t>(*raw) & supported : supported;
}

struct NativePerfSample {
    double total_ms{0.0};
    double throttle_wait_ms{0.0};
    double collect_ms{0.0};
    double submit_ms{0.0};
    double shadow_record_ms{0.0};
    double commit_ms{0.0};
    std::uint32_t instance_count{0};
    std::uint32_t visibility_draws{0};
    std::uint64_t visibility_indices{0};
    std::array<std::uint32_t, kDiagnosticShadowCascadeCount> cascade_draws{};
    std::array<std::uint64_t, kDiagnosticShadowCascadeCount> cascade_indices{};
    std::uint32_t output_width{0};
    std::uint32_t output_height{0};
    bool shadows_enabled{false};
    bool debug_mode{false};
    bool sky_ambient_enabled{false};
    bool sky_sh_updated{false};
};

struct NativePerfStats {
    std::uint32_t samples{0};
    double avg_total_ms{0.0};
    double max_total_ms{0.0};
    double avg_throttle_wait_ms{0.0};
    double max_throttle_wait_ms{0.0};
    double avg_collect_ms{0.0};
    double avg_submit_ms{0.0};
    double max_submit_ms{0.0};
    double avg_shadow_record_ms{0.0};
    double max_shadow_record_ms{0.0};
    double avg_commit_ms{0.0};
    double max_commit_ms{0.0};
    std::uint32_t max_instances{0};
    double avg_visibility_draws{0.0};
    double avg_visibility_indices{0.0};
    std::array<double, kDiagnosticShadowCascadeCount> avg_cascade_draws{};
    std::array<double, kDiagnosticShadowCascadeCount> avg_cascade_indices{};
    std::uint32_t max_output_width{0};
    std::uint32_t max_output_height{0};
    std::uint32_t shadow_samples{0};
    std::uint32_t debug_samples{0};
    std::uint32_t sky_ambient_samples{0};
    std::uint32_t sky_sh_update_samples{0};
};

class NativePerfWindow {
public:
    void add(const NativePerfSample& sample) noexcept {
        ++samples_;
        total_ms_ += sample.total_ms;
        throttle_wait_ms_ += sample.throttle_wait_ms;
        collect_ms_ += sample.collect_ms;
        submit_ms_ += sample.submit_ms;
        shadow_record_ms_ += sample.shadow_record_ms;
        commit_ms_ += sample.commit_ms;
        visibility_draws_ += sample.visibility_draws;
        visibility_indices_ += sample.visibility_indices;
        max_total_ms_ = std::max(max_total_ms_, sample.total_ms);
        max_throttle_wait_ms_ = std::max(max_throttle_wait_ms_, sample.throttle_wait_ms);
        max_submit_ms_ = std::max(max_submit_ms_, sample.submit_ms);
        max_shadow_record_ms_ = std::max(max_shadow_record_ms_, sample.shadow_record_ms);
        max_commit_ms_ = std::max(max_commit_ms_, sample.commit_ms);
        max_instances_ = std::max(max_instances_, sample.instance_count);
        if (static_cast<std::uint64_t>(sample.output_width) * sample.output_height >
            static_cast<std::uint64_t>(max_output_width_) * max_output_height_) {
            max_output_width_ = sample.output_width;
            max_output_height_ = sample.output_height;
        }
        shadow_samples_ += sample.shadows_enabled ? 1u : 0u;
        debug_samples_ += sample.debug_mode ? 1u : 0u;
        sky_ambient_samples_ += sample.sky_ambient_enabled ? 1u : 0u;
        sky_sh_update_samples_ += sample.sky_sh_updated ? 1u : 0u;
        for (std::size_t index = 0; index < kDiagnosticShadowCascadeCount; ++index) {
            cascade_draws_[index] += sample.cascade_draws[index];
            cascade_indices_[index] += sample.cascade_indices[index];
        }
    }

    [[nodiscard]] NativePerfStats snapshot() const noexcept {
        NativePerfStats stats;
        stats.samples = samples_;
        if (samples_ == 0) {
            return stats;
        }
        const double inverse = 1.0 / static_cast<double>(samples_);
        stats.avg_total_ms = total_ms_ * inverse;
        stats.max_total_ms = max_total_ms_;
        stats.avg_throttle_wait_ms = throttle_wait_ms_ * inverse;
        stats.max_throttle_wait_ms = max_throttle_wait_ms_;
        stats.avg_collect_ms = collect_ms_ * inverse;
        stats.avg_submit_ms = submit_ms_ * inverse;
        stats.max_submit_ms = max_submit_ms_;
        stats.avg_shadow_record_ms = shadow_record_ms_ * inverse;
        stats.max_shadow_record_ms = max_shadow_record_ms_;
        stats.avg_commit_ms = commit_ms_ * inverse;
        stats.max_commit_ms = max_commit_ms_;
        stats.max_instances = max_instances_;
        stats.max_output_width = max_output_width_;
        stats.max_output_height = max_output_height_;
        stats.shadow_samples = shadow_samples_;
        stats.debug_samples = debug_samples_;
        stats.sky_ambient_samples = sky_ambient_samples_;
        stats.sky_sh_update_samples = sky_sh_update_samples_;
        stats.avg_visibility_draws = static_cast<double>(visibility_draws_) * inverse;
        stats.avg_visibility_indices = static_cast<double>(visibility_indices_) * inverse;
        for (std::size_t index = 0; index < kDiagnosticShadowCascadeCount; ++index) {
            stats.avg_cascade_draws[index] =
                static_cast<double>(cascade_draws_[index]) * inverse;
            stats.avg_cascade_indices[index] =
                static_cast<double>(cascade_indices_[index]) * inverse;
        }
        return stats;
    }

    void reset() noexcept { *this = NativePerfWindow{}; }

private:
    std::uint32_t samples_{0};
    double total_ms_{0.0};
    double throttle_wait_ms_{0.0};
    double collect_ms_{0.0};
    double submit_ms_{0.0};
    double shadow_record_ms_{0.0};
    double commit_ms_{0.0};
    double max_total_ms_{0.0};
    double max_throttle_wait_ms_{0.0};
    double max_submit_ms_{0.0};
    double max_shadow_record_ms_{0.0};
    double max_commit_ms_{0.0};
    std::uint32_t max_instances_{0};
    std::uint64_t visibility_draws_{0};
    std::uint64_t visibility_indices_{0};
    std::array<std::uint64_t, kDiagnosticShadowCascadeCount> cascade_draws_{};
    std::array<std::uint64_t, kDiagnosticShadowCascadeCount> cascade_indices_{};
    std::uint32_t max_output_width_{0};
    std::uint32_t max_output_height_{0};
    std::uint32_t shadow_samples_{0};
    std::uint32_t debug_samples_{0};
    std::uint32_t sky_ambient_samples_{0};
    std::uint32_t sky_sh_update_samples_{0};
};

}  // namespace Corona::Systems::OpticsDetail
