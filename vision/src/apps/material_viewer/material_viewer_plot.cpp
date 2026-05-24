#include "material_viewer_plot.h"

#include "math/warp.h"

#include <algorithm>
#include <cmath>

using namespace vision;
using namespace ocarina;

namespace {

uchar4 make_uchar(float r, float g, float b) {
    return make_uchar4(static_cast<uint8_t>(std::clamp(r, 0.f, 1.f) * 255.f),
                       static_cast<uint8_t>(std::clamp(g, 0.f, 1.f) * 255.f),
                       static_cast<uint8_t>(std::clamp(b, 0.f, 1.f) * 255.f),
                       255u);
}

float tone_value(float value, float scale, bool log_scale) {
    float normalized = scale > 0.f ? value / scale : 0.f;
    normalized = std::max(0.f, normalized);
    if (!log_scale) {
        return std::clamp(normalized, 0.f, 1.f);
    }
    return std::log1p(normalized * 16.f) / std::log1p(16.f);
}

float lobe_height_value(float value, bool log_scale, float height_scale) {
    float positive = std::max(0.f, value) * std::max(0.01f, height_scale);
    if (!log_scale) {
        return std::min(positive, 4.f);
    }
    return std::min(std::log1p(positive * 12.f) / std::log1p(12.f), 4.f);
}

uchar4 heat_color(float value) {
    float t = std::clamp(value, 0.f, 1.f);
    float3 cold = make_float3(0.05f, 0.16f, 0.34f);
    float3 mid = make_float3(0.16f, 0.62f, 0.82f);
    float3 hot = make_float3(1.00f, 0.87f, 0.28f);
    float3 burn = make_float3(0.96f, 0.32f, 0.12f);
    float3 rgb = t < 0.55f ? lerp(cold, mid, t / 0.55f) : lerp(hot, burn, (t - 0.55f) / 0.45f);
    return make_uchar(rgb.x, rgb.y, rgb.z);
}

uint slice_row_from_height(uint resolution, float slice_plane_height) {
    float normalized = std::clamp(slice_plane_height * 0.5f + 0.5f, 0.f, 1.f);
    return std::min(resolution - 1u, static_cast<uint>(normalized * static_cast<float>(std::max(1u, resolution - 1u)) + 0.5f));
}

void clear_image(std::vector<uchar4> &pixels, uchar4 color) {
    std::fill(pixels.begin(), pixels.end(), color);
}

void fill_rect(std::vector<uchar4> &pixels, uint2 size, uint x0, uint y0, uint x1, uint y1, uchar4 color) {
    if (x0 >= x1 || y0 >= y1) {
        return;
    }
    x1 = std::min(x1, size.x);
    y1 = std::min(y1, size.y);
    for (uint y = y0; y < y1; ++y) {
        for (uint x = x0; x < x1; ++x) {
            pixels[static_cast<size_t>(y) * size.x + x] = color;
        }
    }
}

void draw_rect_outline(std::vector<uchar4> &pixels, uint2 size, uint x0, uint y0, uint x1, uint y1, uchar4 color) {
    if (x0 >= x1 || y0 >= y1) {
        return;
    }
    fill_rect(pixels, size, x0, y0, x1, std::min(y0 + 1u, y1), color);
    fill_rect(pixels, size, x0, y1 > 0 ? y1 - 1u : y1, x1, y1, color);
    fill_rect(pixels, size, x0, y0, std::min(x0 + 1u, x1), y1, color);
    fill_rect(pixels, size, x1 > 0 ? x1 - 1u : x1, y0, x1, y1, color);
}

void draw_line(std::vector<uchar4> &pixels, uint2 size, int x0, int y0, int x1, int y1, uchar4 color) {
    int dx = std::abs(x1 - x0);
    int sx = x0 < x1 ? 1 : -1;
    int dy = -std::abs(y1 - y0);
    int sy = y0 < y1 ? 1 : -1;
    int error = dx + dy;
    while (true) {
        if (x0 >= 0 && y0 >= 0 && x0 < static_cast<int>(size.x) && y0 < static_cast<int>(size.y)) {
            pixels[static_cast<size_t>(y0) * size.x + static_cast<size_t>(x0)] = color;
        }
        if (x0 == x1 && y0 == y1) {
            break;
        }
        int twice = 2 * error;
        if (twice >= dy) {
            error += dy;
            x0 += sx;
        }
        if (twice <= dx) {
            error += dx;
            y0 += sy;
        }
    }
}

void draw_circle(std::vector<uchar4> &pixels, uint2 size, int cx, int cy, int radius, uchar4 color) {
    int x = radius;
    int y = 0;
    int err = 1 - x;
    auto plot = [&](int px, int py) {
        if (px >= 0 && py >= 0 && px < static_cast<int>(size.x) && py < static_cast<int>(size.y)) {
            pixels[static_cast<size_t>(py) * size.x + static_cast<size_t>(px)] = color;
        }
    };
    while (x >= y) {
        plot(cx + x, cy + y);
        plot(cx + y, cy + x);
        plot(cx - y, cy + x);
        plot(cx - x, cy + y);
        plot(cx - x, cy - y);
        plot(cx - y, cy - x);
        plot(cx + y, cy - x);
        plot(cx + x, cy - y);
        ++y;
        if (err < 0) {
            err += 2 * y + 1;
        } else {
            --x;
            err += 2 * (y - x) + 1;
        }
    }
}

float edge_function(float2 a, float2 b, float2 c) {
    return (c.x - a.x) * (b.y - a.y) - (c.y - a.y) * (b.x - a.x);
}

float alpha_blend_channel(float dst, float src, float alpha) {
    return dst * (1.f - alpha) + src * alpha;
}

uchar4 alpha_blend(uchar4 dst, uchar4 src, float alpha) {
    alpha = std::clamp(alpha, 0.f, 1.f);
    float dst_r = static_cast<float>(dst.x) / 255.f;
    float dst_g = static_cast<float>(dst.y) / 255.f;
    float dst_b = static_cast<float>(dst.z) / 255.f;
    float src_r = static_cast<float>(src.x) / 255.f;
    float src_g = static_cast<float>(src.y) / 255.f;
    float src_b = static_cast<float>(src.z) / 255.f;
    return make_uchar(alpha_blend_channel(dst_r, src_r, alpha),
                      alpha_blend_channel(dst_g, src_g, alpha),
                      alpha_blend_channel(dst_b, src_b, alpha));
}

float3 safe_normalize(float3 value, float3 fallback = make_float3(0.f, 1.f, 0.f)) {
    float len2 = dot(value, value);
    if (len2 <= 1e-10f) {
        return fallback;
    }
    return value * rsqrt(len2);
}

float3 orthogonal_vector(float3 normal) {
    if (std::abs(normal.y) < 0.9f) {
        return safe_normalize(cross(normal, make_float3(0.f, 1.f, 0.f)), make_float3(1.f, 0.f, 0.f));
    }
    return safe_normalize(cross(normal, make_float3(1.f, 0.f, 0.f)), make_float3(0.f, 0.f, 1.f));
}

float sample_lobe_value(const std::vector<float> &grid, uint resolution, int gx, int gy) {
    gx = std::clamp(gx, 0, static_cast<int>(resolution) - 1);
    gy = std::clamp(gy, 0, static_cast<int>(resolution) - 1);
    return grid[static_cast<size_t>(gy) * resolution + static_cast<size_t>(gx)];
}

bool sample_direction_from_grid(uint resolution, int gx, int gy, float sign, float3 *direction) {
    float2 uv = make_float2((static_cast<float>(gx) + 0.5f) / static_cast<float>(resolution),
                            (static_cast<float>(gy) + 0.5f) / static_cast<float>(resolution));
    float2 disk = square_to_disk<EPort::H>(uv);
    *direction = material_viewer_direction_from_disk(disk, sign);
    return true;
}

struct SurfacePoint {
    float3 point{};
    float radial{};
    bool valid{false};
};

struct SliceSegment {
    float3 a{};
    float3 b{};
};

SurfacePoint sample_surface_point(const std::vector<float> &grid,
                                  uint resolution,
                                  uint gx,
                                  uint gy,
                                  float sign,
                                  float scale,
                                  bool log_scale,
                                  float height_scale) {
    SurfacePoint point;
    float3 direction{};
    if (!sample_direction_from_grid(resolution, static_cast<int>(gx), static_cast<int>(gy), sign, &direction)) {
        return point;
    }
    float value = grid[static_cast<size_t>(gy) * resolution + gx];
    point.radial = lobe_height_value(value, log_scale, height_scale);
    point.point = direction * point.radial;
    point.valid = true;
    return point;
}

void append_unique_slice_point(std::vector<float3> &points, float3 point, float epsilon = 1e-4f) {
    for (auto existing : points) {
        if (length_squared(existing - point) <= epsilon * epsilon) {
            return;
        }
    }
    points.emplace_back(point);
}

void intersect_edge_with_plane(const float3 &a,
                               const float3 &b,
                               float plane_y,
                               std::vector<float3> &points,
                               float epsilon = 1e-5f) {
    float da = a.y - plane_y;
    float db = b.y - plane_y;
    bool a_on = std::abs(da) <= epsilon;
    bool b_on = std::abs(db) <= epsilon;
    if (a_on && b_on) {
        append_unique_slice_point(points, a);
        append_unique_slice_point(points, b);
        return;
    }
    if (a_on) {
        append_unique_slice_point(points, a);
        return;
    }
    if (b_on) {
        append_unique_slice_point(points, b);
        return;
    }
    if ((da < 0.f && db < 0.f) || (da > 0.f && db > 0.f)) {
        return;
    }
    float t = std::clamp(da / (da - db), 0.f, 1.f);
    append_unique_slice_point(points, a * (1.f - t) + b * t);
}

std::optional<SliceSegment> intersect_triangle_with_plane(const float3 &a,
                                                          const float3 &b,
                                                          const float3 &c,
                                                          float plane_y) {
    std::vector<float3> points;
    points.reserve(4u);
    intersect_edge_with_plane(a, b, plane_y, points);
    intersect_edge_with_plane(b, c, plane_y, points);
    intersect_edge_with_plane(c, a, plane_y, points);
    if (points.size() < 2u) {
        return std::nullopt;
    }
    size_t first = 0u;
    size_t second = 1u;
    float best = length_squared(points[1] - points[0]);
    for (size_t i = 0; i < points.size(); ++i) {
        for (size_t j = i + 1u; j < points.size(); ++j) {
            float dist2 = length_squared(points[j] - points[i]);
            if (dist2 > best) {
                best = dist2;
                first = i;
                second = j;
            }
        }
    }
    if (best <= 1e-8f) {
        return std::nullopt;
    }
    return SliceSegment{points[first], points[second]};
}

std::vector<SliceSegment> compute_slice_segments(const std::vector<SurfacePoint> &surface_points,
                                                 uint resolution,
                                                 float plane_y) {
    std::vector<SliceSegment> segments;
    if (surface_points.empty() || resolution < 2u) {
        return segments;
    }
    for (uint gy = 0; gy + 1u < resolution; ++gy) {
        for (uint gx = 0; gx + 1u < resolution; ++gx) {
            const SurfacePoint &v00 = surface_points[static_cast<size_t>(gy) * resolution + gx];
            const SurfacePoint &v10 = surface_points[static_cast<size_t>(gy) * resolution + (gx + 1u)];
            const SurfacePoint &v01 = surface_points[static_cast<size_t>(gy + 1u) * resolution + gx];
            const SurfacePoint &v11 = surface_points[static_cast<size_t>(gy + 1u) * resolution + (gx + 1u)];
            if (v00.valid && v10.valid && v11.valid) {
                if (auto segment = intersect_triangle_with_plane(v00.point, v10.point, v11.point, plane_y)) {
                    segments.emplace_back(*segment);
                }
            }
            if (v00.valid && v11.valid && v01.valid) {
                if (auto segment = intersect_triangle_with_plane(v00.point, v11.point, v01.point, plane_y)) {
                    segments.emplace_back(*segment);
                }
            }
        }
    }
    return segments;
}

float3 estimate_lobe_normal(const std::vector<float> &grid,
                            uint resolution,
                            uint gx,
                            uint gy,
                            float sign,
                            float scale,
                            bool log_scale,
                            float height_scale,
                            float3 fallback) {
    float3 center_dir = fallback;
    if (!sample_direction_from_grid(resolution, static_cast<int>(gx), static_cast<int>(gy), sign, &center_dir)) {
        return fallback;
    }
    float center_radial = lobe_height_value(sample_lobe_value(grid, resolution, static_cast<int>(gx), static_cast<int>(gy)), log_scale, height_scale);
    float3 center = center_dir * center_radial;

    auto neighbor_point = [&](int nx, int ny, float3 default_value) {
        float3 dir{};
        if (!sample_direction_from_grid(resolution, nx, ny, sign, &dir)) {
            return default_value;
        }
        float radial = lobe_height_value(sample_lobe_value(grid, resolution, nx, ny), log_scale, height_scale);
        return dir * radial;
    };

    float3 left = neighbor_point(static_cast<int>(gx) - 1, static_cast<int>(gy), center);
    float3 right = neighbor_point(static_cast<int>(gx) + 1, static_cast<int>(gy), center);
    float3 down = neighbor_point(static_cast<int>(gx), static_cast<int>(gy) - 1, center);
    float3 up = neighbor_point(static_cast<int>(gx), static_cast<int>(gy) + 1, center);
    float3 tangent_x = right - left;
    float3 tangent_y = up - down;
    float3 normal = cross(tangent_x, tangent_y);
    normal = safe_normalize(normal, center_dir);
    if (dot(normal, center_dir) < 0.f) {
        normal = -normal;
    }
    return normal;
}

void draw_depth_line(std::vector<uchar4> &pixels,
                     uint2 image_size,
                     const std::vector<float> &zbuffer,
                     uint plot_x0,
                     uint plot_y0,
                     uint plot_width,
                     uint plot_height,
                     float2 a,
                     float depth_a,
                     float2 b,
                     float depth_b,
                     uchar4 color,
                     float epsilon = 0.01f) {
    int x0 = static_cast<int>(std::round(a.x));
    int y0 = static_cast<int>(std::round(a.y));
    int x1 = static_cast<int>(std::round(b.x));
    int y1 = static_cast<int>(std::round(b.y));
    int dx = std::abs(x1 - x0);
    int sx = x0 < x1 ? 1 : -1;
    int dy = -std::abs(y1 - y0);
    int sy = y0 < y1 ? 1 : -1;
    int error = dx + dy;
    int steps = std::max(dx, std::abs(y1 - y0));
    int step_index = 0;
    while (true) {
        if (x0 >= static_cast<int>(plot_x0) && y0 >= static_cast<int>(plot_y0) &&
            x0 < static_cast<int>(plot_x0 + plot_width) && y0 < static_cast<int>(plot_y0 + plot_height)) {
            size_t local_index = static_cast<size_t>(y0 - static_cast<int>(plot_y0)) * plot_width +
                                 static_cast<size_t>(x0 - static_cast<int>(plot_x0));
            float t = steps > 0 ? static_cast<float>(step_index) / static_cast<float>(steps) : 0.f;
            float depth = lerp(depth_a, depth_b, t);
            if (depth >= zbuffer[local_index] - epsilon) {
                pixels[static_cast<size_t>(y0) * image_size.x + static_cast<size_t>(x0)] = color;
            }
        }
        if (x0 == x1 && y0 == y1) {
            break;
        }
        int twice = 2 * error;
        if (twice >= dy) {
            error += dy;
            x0 += sx;
        }
        if (twice <= dx) {
            error += dx;
            y0 += sy;
        }
        ++step_index;
    }
}

void draw_overlay_line(std::vector<uchar4> &pixels,
                       uint2 image_size,
                       float2 a,
                       float2 b,
                       uchar4 color) {
    draw_line(pixels,
              image_size,
              static_cast<int>(std::round(a.x)),
              static_cast<int>(std::round(a.y)),
              static_cast<int>(std::round(b.x)),
              static_cast<int>(std::round(b.y)),
              color);
}

void rasterize_translucent_triangle(std::vector<uchar4> &pixels,
                                    uint2 image_size,
                                    const std::vector<float> &zbuffer,
                                    uint x0,
                                    uint y0,
                                    uint width,
                                    uint height,
                                    float2 a,
                                    float depth_a,
                                    float2 b,
                                    float depth_b,
                                    float2 c,
                                    float depth_c,
                                    uchar4 color,
                                    float alpha) {
    float area = edge_function(a, b, c);
    if (std::abs(area) < 1e-6f) {
        return;
    }
    int ix0 = std::max(static_cast<int>(x0), static_cast<int>(std::floor(std::min({a.x, b.x, c.x}))));
    int ix1 = std::min(static_cast<int>(x0 + width - 1u), static_cast<int>(std::ceil(std::max({a.x, b.x, c.x}))));
    int iy0 = std::max(static_cast<int>(y0), static_cast<int>(std::floor(std::min({a.y, b.y, c.y}))));
    int iy1 = std::min(static_cast<int>(y0 + height - 1u), static_cast<int>(std::ceil(std::max({a.y, b.y, c.y}))));
    for (int py = iy0; py <= iy1; ++py) {
        for (int px = ix0; px <= ix1; ++px) {
            float2 p = make_float2(static_cast<float>(px) + 0.5f, static_cast<float>(py) + 0.5f);
            float w0 = edge_function(b, c, p);
            float w1 = edge_function(c, a, p);
            float w2 = edge_function(a, b, p);
            bool inside = area > 0.f ? (w0 >= 0.f && w1 >= 0.f && w2 >= 0.f) : (w0 <= 0.f && w1 <= 0.f && w2 <= 0.f);
            if (!inside) {
                continue;
            }
            w0 /= area;
            w1 /= area;
            w2 /= area;
            float depth = w0 * depth_a + w1 * depth_b + w2 * depth_c;
            size_t local_index = static_cast<size_t>(py - static_cast<int>(y0)) * width + static_cast<size_t>(px - static_cast<int>(x0));
            if (depth < zbuffer[local_index] - 0.015f) {
                continue;
            }
            size_t pixel_index = static_cast<size_t>(py) * image_size.x + static_cast<size_t>(px);
            pixels[pixel_index] = alpha_blend(pixels[pixel_index], color, alpha);
        }
    }
}

void draw_slice_plane_overlay(std::vector<uchar4> &pixels,
                              uint2 image_size,
                              const std::vector<float> &zbuffer,
                              uint x0,
                              uint y0,
                              uint width,
                              uint height,
                              float yaw_deg,
                              float pitch_deg,
                              float zoom,
                              float slice_plane_height) {
    const float clamped_y = std::clamp(slice_plane_height, -0.98f, 0.98f);
    const float radius = std::sqrt(std::max(0.f, 1.f - clamped_y * clamped_y));
    if (radius <= 1e-4f) {
        return;
    }
    const ViewerProjector projector = make_material_viewer_projector(PlotRect{x0, y0, width, height}, zoom);
    const float3 plane_normal = material_viewer_rotate_point(make_float3(0.f, 1.f, 0.f), yaw_deg, pitch_deg);
    float3 tangent = material_viewer_rotate_point(orthogonal_vector(make_float3(0.f, 1.f, 0.f)), yaw_deg, pitch_deg);
    float3 bitangent = safe_normalize(cross(plane_normal, tangent), make_float3(0.f, 0.f, 1.f));
    tangent = safe_normalize(cross(bitangent, plane_normal), tangent);
    const uchar4 fill_color = make_uchar4(116u, 156u, 255u, 255u);
    const uchar4 ring_color = make_uchar4(196u, 220u, 255u, 255u);
    const uchar4 axis_u_color = make_uchar4(224u, 132u, 112u, 255u);
    const uchar4 axis_v_color = make_uchar4(92u, 176u, 255u, 255u);

    struct PlaneVertex {
        float2 pos{};
        float depth{};
    };
    auto project = [&](float3 point) {
        PlaneVertex vertex;
        float3 rotated = material_viewer_rotate_point(point, yaw_deg, pitch_deg);
        vertex.pos = material_viewer_project_screen(projector, rotated);
        vertex.depth = rotated.z;
        return vertex;
    };

    constexpr uint kSegments = 56u;
    PlaneVertex center_vertex = project(make_float3(0.f, clamped_y, 0.f));
    std::vector<PlaneVertex> ring_vertices;
    ring_vertices.reserve(kSegments + 1u);
    for (uint i = 0; i <= kSegments; ++i) {
        float theta = static_cast<float>(i) / static_cast<float>(kSegments) * kTwoPi;
        float3 point = make_float3(std::cos(theta) * radius, clamped_y, std::sin(theta) * radius);
        ring_vertices.emplace_back(project(point));
    }
    for (uint i = 0; i < kSegments; ++i) {
        rasterize_translucent_triangle(pixels,
                                       image_size,
                                       zbuffer,
                                       x0,
                                       y0,
                                       width,
                                       height,
                                       center_vertex.pos,
                                       center_vertex.depth,
                                       ring_vertices[i].pos,
                                       ring_vertices[i].depth,
                                       ring_vertices[i + 1u].pos,
                                       ring_vertices[i + 1u].depth,
                                       fill_color,
                                       0.16f);
    }
    for (uint i = 0; i < kSegments; ++i) {
        draw_depth_line(pixels,
                        image_size,
                        zbuffer,
                        x0,
                        y0,
                        width,
                        height,
                        ring_vertices[i].pos,
                        ring_vertices[i].depth,
                        ring_vertices[i + 1u].pos,
                        ring_vertices[i + 1u].depth,
                        ring_color,
                        0.02f);
    }

    PlaneVertex axis_u0 = project(make_float3(-radius, clamped_y, 0.f));
    PlaneVertex axis_u1 = project(make_float3(radius, clamped_y, 0.f));
    PlaneVertex axis_v0 = project(make_float3(0.f, clamped_y, -radius));
    PlaneVertex axis_v1 = project(make_float3(0.f, clamped_y, radius));
    draw_overlay_line(pixels, image_size, axis_u0.pos, axis_u1.pos, axis_u_color);
    draw_overlay_line(pixels, image_size, axis_v0.pos, axis_v1.pos, axis_v_color);
}

void draw_3d_lobe(std::vector<uchar4> &pixels, uint2 image_size, const std::vector<float> &grid,
                  uint resolution, uint x0, uint y0, uint width, uint height,
                  float scale, bool log_scale, float sign,
                  float height_scale,
                  float yaw_deg, float pitch_deg, float zoom,
                  float wo_yaw_deg, float wo_pitch_deg,
                  uchar4 surface_color, bool show_slice_plane, float slice_plane_height,
                  bool clear_background = true,
                  bool draw_slice_plane_shell = true) {
    if (clear_background) {
        fill_rect(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(14u, 18u, 24u, 255u));
        draw_rect_outline(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(90u, 100u, 110u, 255u));
    }
    if (grid.empty() || width < 8u || height < 8u) {
        return;
    }

    struct Vertex {
        float2 pos{};
        float depth{};
        float shade{};
        float radial{};
        float3 world{};
        float3 normal{};
        bool valid{false};
    };

    std::vector<Vertex> vertices(static_cast<size_t>(resolution) * resolution);
    std::vector<float> zbuffer(static_cast<size_t>(width) * height, -1e30f);

    const ViewerProjector projector = make_material_viewer_projector(PlotRect{x0, y0, width, height}, zoom);
    const float3 light_dir = normalize(make_float3(-0.45f, 0.82f, 0.35f));
    const float3 display_view_dir = material_viewer_direction_from_angles(wo_yaw_deg, wo_pitch_deg);

    auto project_vertex = [&](uint gx, uint gy, float hemisphere_sign) {
        Vertex vertex;
        float2 uv = make_float2((static_cast<float>(gx) + 0.5f) / static_cast<float>(resolution),
                                (static_cast<float>(gy) + 0.5f) / static_cast<float>(resolution));
        float2 disk = square_to_disk<EPort::H>(uv);

        float3 direction = material_viewer_direction_from_disk(disk, hemisphere_sign);
        float value = grid[static_cast<size_t>(gy) * resolution + gx];
        float radial = lobe_height_value(value, log_scale, height_scale);
        float3 point = direction * radial;
        float3 rotated = material_viewer_rotate_point(point, yaw_deg, pitch_deg);
        float3 normal_world = estimate_lobe_normal(grid, resolution, gx, gy, sign, scale, log_scale, height_scale, direction);
        float3 normal = material_viewer_rotate_point(normal_world, yaw_deg, pitch_deg);
        vertex.pos = material_viewer_project_screen(projector, rotated);
        vertex.depth = rotated.z;
        float ndotl = std::max(0.f, dot(safe_normalize(normal, direction), light_dir));
        float rim = std::pow(std::clamp(1.f - std::abs(dot(safe_normalize(normal, direction), make_float3(0.f, 0.f, 1.f))), 0.f, 1.f), 1.5f);
        vertex.shade = std::clamp(0.14f + 0.78f * ndotl + 0.12f * rim, 0.f, 1.f);
        vertex.radial = radial;
        vertex.world = rotated;
        vertex.normal = safe_normalize(normal, direction);
        vertex.valid = true;
        return vertex;
    };

    for (uint gy = 0; gy < resolution; ++gy) {
        for (uint gx = 0; gx < resolution; ++gx) {
            vertices[static_cast<size_t>(gy) * resolution + gx] = project_vertex(gx, gy, sign);
        }
    }

    std::vector<SurfacePoint> surface_points(static_cast<size_t>(resolution) * resolution);
    for (uint gy = 0; gy < resolution; ++gy) {
        for (uint gx = 0; gx < resolution; ++gx) {
            surface_points[static_cast<size_t>(gy) * resolution + gx] =
                sample_surface_point(grid, resolution, gx, gy, sign, scale, log_scale, height_scale);
        }
    }

    auto draw_triangle = [&](const Vertex &a, const Vertex &b, const Vertex &c) {
        if (!a.valid || !b.valid || !c.valid) {
            return;
        }
        float area = edge_function(a.pos, b.pos, c.pos);
        if (std::abs(area) < 1e-6f) {
            return;
        }

        float min_x = std::min({a.pos.x, b.pos.x, c.pos.x});
        float max_x = std::max({a.pos.x, b.pos.x, c.pos.x});
        float min_y = std::min({a.pos.y, b.pos.y, c.pos.y});
        float max_y = std::max({a.pos.y, b.pos.y, c.pos.y});

        int ix0 = std::max(static_cast<int>(x0), static_cast<int>(std::floor(min_x)));
        int ix1 = std::min(static_cast<int>(x0 + width - 1u), static_cast<int>(std::ceil(max_x)));
        int iy0 = std::max(static_cast<int>(y0), static_cast<int>(std::floor(min_y)));
        int iy1 = std::min(static_cast<int>(y0 + height - 1u), static_cast<int>(std::ceil(max_y)));

        for (int py = iy0; py <= iy1; ++py) {
            for (int px = ix0; px <= ix1; ++px) {
                float2 p = make_float2(static_cast<float>(px) + 0.5f, static_cast<float>(py) + 0.5f);
                float w0 = edge_function(b.pos, c.pos, p);
                float w1 = edge_function(c.pos, a.pos, p);
                float w2 = edge_function(a.pos, b.pos, p);
                bool inside = area > 0.f ? (w0 >= 0.f && w1 >= 0.f && w2 >= 0.f) : (w0 <= 0.f && w1 <= 0.f && w2 <= 0.f);
                if (!inside) {
                    continue;
                }
                w0 /= area;
                w1 /= area;
                w2 /= area;
                float depth = w0 * a.depth + w1 * b.depth + w2 * c.depth;
                size_t local_index = static_cast<size_t>(py - static_cast<int>(y0)) * width + static_cast<size_t>(px - static_cast<int>(x0));
                if (depth <= zbuffer[local_index]) {
                    continue;
                }
                zbuffer[local_index] = depth;
                float shade = std::clamp(w0 * a.shade + w1 * b.shade + w2 * c.shade, 0.f, 1.f);
                float3 normal = safe_normalize(w0 * a.normal + w1 * b.normal + w2 * c.normal, make_float3(0.f, 1.f, 0.f));
                float fresnel = std::pow(std::clamp(1.f - std::max(0.f, normal.z), 0.f, 1.f), 3.f);
                float3 rgb = make_float3(static_cast<float>(surface_color.x) / 255.f,
                                         static_cast<float>(surface_color.y) / 255.f,
                                         static_cast<float>(surface_color.z) / 255.f);
                rgb *= 0.22f + 0.78f * shade;
                rgb = lerp(rgb, make_float3(1.f), 0.08f * fresnel);
                pixels[static_cast<size_t>(py) * image_size.x + static_cast<size_t>(px)] = make_uchar(rgb.x, rgb.y, rgb.z);
            }
        }
    };

    auto project_world = [&](float3 point) {
        Vertex vertex;
        float3 rotated = material_viewer_rotate_point(point, yaw_deg, pitch_deg);
        vertex.pos = material_viewer_project_screen(projector, rotated);
        vertex.depth = rotated.z;
        vertex.shade = 1.f;
        vertex.radial = 0.f;
        vertex.world = rotated;
        vertex.normal = make_float3(0.f, 1.f, 0.f);
        vertex.valid = true;
        return vertex;
    };

    for (uint gy = 0; gy + 1u < resolution; ++gy) {
        for (uint gx = 0; gx + 1u < resolution; ++gx) {
            const Vertex &v00 = vertices[static_cast<size_t>(gy) * resolution + gx];
            const Vertex &v10 = vertices[static_cast<size_t>(gy) * resolution + (gx + 1u)];
            const Vertex &v01 = vertices[static_cast<size_t>(gy + 1u) * resolution + gx];
            const Vertex &v11 = vertices[static_cast<size_t>(gy + 1u) * resolution + (gx + 1u)];
            draw_triangle(v00, v10, v11);
            draw_triangle(v00, v11, v01);
        }
    }

    auto draw_surface_guides = [&](uchar4 color) {
        uint step = std::max(8u, resolution / 6u);
        for (uint gy = step; gy + step < resolution; gy += step) {
            bool has_prev = false;
            Vertex prev{};
            for (uint gx = 0; gx < resolution; ++gx) {
                const Vertex &current = vertices[static_cast<size_t>(gy) * resolution + gx];
                if (!current.valid) {
                    has_prev = false;
                    continue;
                }
                if (has_prev) {
                    draw_depth_line(pixels,
                                    image_size,
                                    zbuffer,
                                    x0,
                                    y0,
                                    width,
                                    height,
                                    prev.pos,
                                    prev.depth,
                                    current.pos,
                                    current.depth,
                                    color,
                                    0.01f);
                }
                prev = current;
                has_prev = true;
            }
        }
        for (uint gx = step; gx + step < resolution; gx += step) {
            bool has_prev = false;
            Vertex prev{};
            for (uint gy = 0; gy < resolution; ++gy) {
                const Vertex &current = vertices[static_cast<size_t>(gy) * resolution + gx];
                if (!current.valid) {
                    has_prev = false;
                    continue;
                }
                if (has_prev) {
                    draw_depth_line(pixels,
                                    image_size,
                                    zbuffer,
                                    x0,
                                    y0,
                                    width,
                                    height,
                                    prev.pos,
                                    prev.depth,
                                    current.pos,
                                    current.depth,
                                    color,
                                    0.01f);
                }
                prev = current;
                has_prev = true;
            }
        }
    };

    auto draw_contours = [&](uchar4 color) {
        constexpr std::array<float, 4> kContourLevels = {0.18f, 0.36f, 0.54f, 0.72f};
        auto edge_intersection = [](const Vertex &a, const Vertex &b, float level, float2 *pos, float *depth) {
            float da = a.radial - level;
            float db = b.radial - level;
            if ((da < 0.f && db < 0.f) || (da > 0.f && db > 0.f) || std::abs(a.radial - b.radial) < 1e-6f) {
                return false;
            }
            float t = std::clamp((level - a.radial) / (b.radial - a.radial), 0.f, 1.f);
            *pos = a.pos * (1.f - t) + b.pos * t;
            *depth = lerp(a.depth, b.depth, t);
            return true;
        };

        auto draw_triangle_contours = [&](const Vertex &a, const Vertex &b, const Vertex &c) {
            if (!a.valid || !b.valid || !c.valid) {
                return;
            }
            for (float level : kContourLevels) {
                std::array<float2, 3> positions{};
                std::array<float, 3> depths{};
                uint hit_count = 0u;
                if (edge_intersection(a, b, level, &positions[hit_count], &depths[hit_count])) {
                    ++hit_count;
                }
                if (edge_intersection(b, c, level, &positions[hit_count], &depths[hit_count])) {
                    ++hit_count;
                }
                if (hit_count < 2u && edge_intersection(c, a, level, &positions[hit_count], &depths[hit_count])) {
                    ++hit_count;
                }
                if (hit_count == 2u) {
                    draw_depth_line(pixels,
                                    image_size,
                                    zbuffer,
                                    x0,
                                    y0,
                                    width,
                                    height,
                                    positions[0],
                                    depths[0],
                                    positions[1],
                                    depths[1],
                                    color,
                                    0.012f);
                }
            }
        };

        for (uint gy = 0; gy + 1u < resolution; ++gy) {
            for (uint gx = 0; gx + 1u < resolution; ++gx) {
                const Vertex &v00 = vertices[static_cast<size_t>(gy) * resolution + gx];
                const Vertex &v10 = vertices[static_cast<size_t>(gy) * resolution + (gx + 1u)];
                const Vertex &v01 = vertices[static_cast<size_t>(gy + 1u) * resolution + gx];
                const Vertex &v11 = vertices[static_cast<size_t>(gy + 1u) * resolution + (gx + 1u)];
                draw_triangle_contours(v00, v10, v11);
                draw_triangle_contours(v00, v11, v01);
            }
        }
    };

    draw_surface_guides(make_uchar4(38u, 44u, 54u, 255u));
    draw_contours(make_uchar4(236u, 242u, 248u, 255u));

    if (show_slice_plane) {
        if (draw_slice_plane_shell) {
            draw_slice_plane_overlay(pixels, image_size, zbuffer, x0, y0, width, height, yaw_deg, pitch_deg, zoom, slice_plane_height);
        }

        float plane_y = std::clamp(slice_plane_height, -0.98f, 0.98f);
        auto segments = compute_slice_segments(surface_points, resolution, plane_y);
        for (const auto &segment : segments) {
            Vertex a = project_world(segment.a);
            Vertex b = project_world(segment.b);
            draw_depth_line(pixels,
                            image_size,
                            zbuffer,
                            x0,
                            y0,
                            width,
                            height,
                            a.pos,
                            a.depth,
                            b.pos,
                            b.depth,
                            make_uchar4(244u, 206u, 96u, 255u),
                            0.03f);
        }
    }

    auto draw_reference_ring = [&](float height_y, uchar4 color) {
        constexpr uint kSegments = 64u;
        float radius = std::sqrt(std::max(0.f, 1.f - height_y * height_y));
        if (radius <= 1e-4f) {
            return;
        }
        Vertex previous = project_world(make_float3(radius, height_y, 0.f));
        for (uint i = 1u; i <= kSegments; ++i) {
            float theta = static_cast<float>(i) / static_cast<float>(kSegments) * kTwoPi;
            Vertex current = project_world(make_float3(std::cos(theta) * radius, height_y, std::sin(theta) * radius));
            draw_depth_line(pixels, image_size, zbuffer, x0, y0, width, height, previous.pos, previous.depth, current.pos, current.depth, color, 0.018f);
            previous = current;
        }
    };
    draw_reference_ring(0.f, make_uchar4(54u, 62u, 72u, 255u));

    auto draw_vector_arrow = [&](float3 start, float3 direction, float length, uchar4 color, bool overlay) {
        float3 dir = safe_normalize(direction, make_float3(0.f, 1.f, 0.f));
        float3 end = start + dir * length;
        Vertex a = project_world(start);
        Vertex b = project_world(end);
        if (overlay) {
            draw_overlay_line(pixels, image_size, a.pos, b.pos, color);
        } else {
            draw_depth_line(pixels, image_size, zbuffer, x0, y0, width, height, a.pos, a.depth, b.pos, b.depth, color, 0.04f);
        }

        float3 side = safe_normalize(cross(dir, make_float3(0.f, 0.f, 1.f)), make_float3(1.f, 0.f, 0.f));
        if (length_squared(side) < 1e-6f) {
            side = make_float3(1.f, 0.f, 0.f);
        }
        float3 back = end - dir * (length * 0.18f);
        float3 wing = side * (length * 0.08f);
        Vertex left = project_world(back + wing);
        Vertex right = project_world(back - wing);
        if (overlay) {
            draw_overlay_line(pixels, image_size, left.pos, b.pos, color);
            draw_overlay_line(pixels, image_size, right.pos, b.pos, color);
        } else {
            draw_depth_line(pixels, image_size, zbuffer, x0, y0, width, height, left.pos, left.depth, b.pos, b.depth, color, 0.04f);
            draw_depth_line(pixels, image_size, zbuffer, x0, y0, width, height, right.pos, right.depth, b.pos, b.depth, color, 0.04f);
        }
    };

    draw_vector_arrow(make_float3(0.f), make_float3(0.f, sign, 0.f), 1.0f, make_uchar4(94u, 214u, 118u, 255u), true);
    draw_vector_arrow(make_float3(0.f), display_view_dir, 0.95f, make_uchar4(250u, 132u, 108u, 255u), false);

}

void draw_heatmap(std::vector<uchar4> &pixels, uint2 image_size, const std::vector<float> &grid,
                  uint resolution, uint x0, uint y0, uint width, uint height,
                  float scale, bool log_scale, float slice_plane_height) {
    if (grid.empty() || width == 0u || height == 0u) {
        return;
    }
    fill_rect(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(20u, 24u, 30u, 255u));
    for (uint py = 0; py < height; ++py) {
        uint gy = std::min(resolution - 1u, py * resolution / height);
        for (uint px = 0; px < width; ++px) {
            uint gx = std::min(resolution - 1u, px * resolution / width);
            float value = grid[static_cast<size_t>(gy) * resolution + gx];
            float2 uv = make_float2((static_cast<float>(gx) + 0.5f) / static_cast<float>(resolution),
                                    (static_cast<float>(gy) + 0.5f) / static_cast<float>(resolution));
            float2 disk = square_to_disk<EPort::H>(uv);
            pixels[static_cast<size_t>(y0 + py) * image_size.x + (x0 + px)] = heat_color(tone_value(value, scale, log_scale));
        }
    }
    float slice_y = std::clamp(slice_plane_height, -0.98f, 0.98f);
    float slice_radius = std::sqrt(std::max(0.f, 1.f - slice_y * slice_y));
    constexpr uint kSegments = 96u;
    auto map_disk_point = [&](float2 point) {
        float nx = point.x * 0.5f + 0.5f;
        float ny = point.y * 0.5f + 0.5f;
        int px = static_cast<int>(std::round(static_cast<float>(x0) + nx * static_cast<float>(width - 1u)));
        int py = static_cast<int>(std::round(static_cast<float>(y0 + height - 1u) - ny * static_cast<float>(height - 1u)));
        return make_int2(px, py);
    };
    float2 previous = make_float2(slice_radius, 0.f);
    for (uint i = 1u; i <= kSegments; ++i) {
        float theta = static_cast<float>(i) / static_cast<float>(kSegments) * kTwoPi;
        float2 current = make_float2(std::cos(theta) * slice_radius, std::sin(theta) * slice_radius);
        auto a = map_disk_point(previous);
        auto b = map_disk_point(current);
        draw_line(pixels, image_size, a.x, a.y, b.x, b.y, make_uchar4(144u, 182u, 255u, 255u));
        previous = current;
    }
    draw_rect_outline(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(90u, 100u, 110u, 255u));
}

void draw_slice_plot(std::vector<uchar4> &pixels, uint2 image_size, const std::vector<float> &grid,
                     uint resolution, uint x0, uint y0, uint width, uint height,
                     float scale, bool log_scale, float sign, float slice_plane_height, float height_scale) {
    fill_rect(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(16u, 20u, 25u, 255u));
    draw_rect_outline(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(90u, 100u, 110u, 255u));
    int center_y = static_cast<int>(y0 + height / 2u);
    draw_line(pixels, image_size, static_cast<int>(x0), center_y, static_cast<int>(x0 + width - 1u), center_y, make_uchar4(45u, 52u, 60u, 255u));
    if (grid.empty()) {
        return;
    }

    std::vector<SurfacePoint> surface_points(static_cast<size_t>(resolution) * resolution);
    for (uint gy = 0; gy < resolution; ++gy) {
        for (uint gx = 0; gx < resolution; ++gx) {
            surface_points[static_cast<size_t>(gy) * resolution + gx] =
                sample_surface_point(grid, resolution, gx, gy, sign, scale, log_scale, height_scale);
        }
    }

    float plane_y = std::clamp(slice_plane_height, -0.98f, 0.98f);
    auto segments = compute_slice_segments(surface_points, resolution, plane_y);
    auto map_point = [&](float3 point) {
        float nx = point.x * 0.5f + 0.5f;
        float nz = point.z * 0.5f + 0.5f;
        int px = static_cast<int>(std::round(static_cast<float>(x0) + nx * static_cast<float>(width - 1u)));
        int py = static_cast<int>(std::round(static_cast<float>(y0 + height - 1u) - nz * static_cast<float>(height - 1u)));
        return make_int2(px, py);
    };

    float radius = std::sqrt(std::max(0.f, 1.f - plane_y * plane_y));
    if (radius > 1e-4f) {
        constexpr uint kArcSegments = 64u;
        float3 previous = make_float3(-radius, plane_y, sign * 0.f);
        for (uint i = 1u; i <= kArcSegments; ++i) {
            float t = static_cast<float>(i) / static_cast<float>(kArcSegments);
            float x = lerp(-radius, radius, t);
            float z = sign * std::sqrt(std::max(0.f, radius * radius - x * x));
            float3 current = make_float3(x, plane_y, z);
            auto a = map_point(previous);
            auto b = map_point(current);
            draw_line(pixels, image_size, a.x, a.y, b.x, b.y, make_uchar4(60u, 70u, 82u, 255u));
            previous = current;
        }
    }

    for (const auto &segment : segments) {
        auto a = map_point(segment.a);
        auto b = map_point(segment.b);
        draw_line(pixels, image_size, a.x, a.y, b.x, b.y, make_uchar4(228u, 191u, 78u, 255u));
    }
}

void draw_polar_plot(std::vector<uchar4> &pixels, uint2 image_size, const std::vector<float> &grid,
                     uint resolution, uint x0, uint y0, uint width, uint height,
                     float scale, bool log_scale, float height_scale) {
    fill_rect(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(16u, 20u, 25u, 255u));
    draw_rect_outline(pixels, image_size, x0, y0, x0 + width, y0 + height, make_uchar4(90u, 100u, 110u, 255u));
    int cx = static_cast<int>(x0 + width / 2u);
    int cy = static_cast<int>(y0 + height - 6u);
    int radius = static_cast<int>(std::min(width, height) / 2u) - 8;
    draw_circle(pixels, image_size, cx, cy, radius, make_uchar4(45u, 52u, 60u, 255u));
    draw_line(pixels, image_size, cx - radius, cy, cx + radius, cy, make_uchar4(45u, 52u, 60u, 255u));
    draw_line(pixels, image_size, cx, cy, cx, cy - radius, make_uchar4(45u, 52u, 60u, 255u));
    if (grid.empty()) {
        return;
    }
    uint row = resolution / 2u;
    int prev_x = cx;
    int prev_y = cy;
    for (uint i = 0; i < resolution; ++i) {
        float normalized = static_cast<float>(i) / static_cast<float>(std::max(1u, resolution - 1u));
        float theta = normalized * (kPi * 0.5f);
        float value = grid[static_cast<size_t>(row) * resolution + i];
        float t = std::clamp(lobe_height_value(value, log_scale, height_scale) / 4.f, 0.f, 1.f);
        float radial = t * static_cast<float>(radius);
        int px = static_cast<int>(std::round(static_cast<float>(cx) + radial * std::sin(theta)));
        int py = static_cast<int>(std::round(static_cast<float>(cy) - radial * std::cos(theta)));
        if (i > 0u) {
            draw_line(pixels, image_size, prev_x, prev_y, px, py, make_uchar4(120u, 224u, 192u, 255u));
        }
        prev_x = px;
        prev_y = py;
    }
}

}// namespace

namespace vision {

void draw_preview_background(std::vector<uchar4> &pixels, uint2 image_size, const PreviewData &preview, const ViewerState &state) {
    clear_image(pixels, make_uchar4(10u, 12u, 16u, 255u));
    const PlotColumns columns = compute_plot_columns(image_size);
    const float shared_scale = std::max(preview.reflection_max, preview.transmission_max);
    const float left_scale = state.scale_mode == static_cast<int>(ScaleMode::Shared) ? shared_scale : preview.reflection_max;
    const float right_scale = state.scale_mode == static_cast<int>(ScaleMode::Shared) ? shared_scale : preview.transmission_max;

    if (state.display_mode == static_cast<int>(DisplayMode::TwoD)) {
        const uint row_height = (image_size.y - 2u * kOuterMargin - 2u * kPanelGap) / 3u;
        const uint row0 = kOuterMargin;
        const uint row1 = row0 + row_height + kPanelGap;
        const uint row2 = row1 + row_height + kPanelGap;
        draw_heatmap(pixels, image_size, preview.reflection, preview.resolution, columns.left_x, row0, columns.column_width, row_height, left_scale, state.log_scale, state.slice_plane_height);
        draw_heatmap(pixels, image_size, preview.transmission, preview.resolution, columns.right_x, row0, columns.column_width, row_height, right_scale, state.log_scale, state.slice_plane_height);
        draw_slice_plot(pixels, image_size, preview.reflection, preview.resolution, columns.left_x, row1, columns.column_width, row_height, left_scale, state.log_scale, 1.f, state.slice_plane_height, state.lobe_height_scale);
        draw_slice_plot(pixels, image_size, preview.transmission, preview.resolution, columns.right_x, row1, columns.column_width, row_height, right_scale, state.log_scale, -1.f, state.slice_plane_height, state.lobe_height_scale);
        draw_polar_plot(pixels, image_size, preview.reflection, preview.resolution, columns.left_x, row2, columns.column_width, row_height, left_scale, state.log_scale, state.lobe_height_scale);
        draw_polar_plot(pixels, image_size, preview.transmission, preview.resolution, columns.right_x, row2, columns.column_width, row_height, right_scale, state.log_scale, state.lobe_height_scale);
    } else {
        const uint row_height = image_size.y - 2u * kOuterMargin;
        draw_3d_lobe(pixels, image_size, preview.reflection, preview.resolution, columns.plot_x0, kOuterMargin, columns.plot_width, row_height,
                     left_scale, state.log_scale, 1.f, state.lobe_height_scale,
                     state.lobe_view_yaw_deg, state.lobe_view_pitch_deg, state.lobe_view_zoom,
                     state.yaw_deg, state.pitch_deg,
                     make_uchar4(228u, 191u, 78u, 255u), state.show_slice_plane, state.slice_plane_height,
                     true, true);
        draw_3d_lobe(pixels, image_size, preview.transmission, preview.resolution, columns.plot_x0, kOuterMargin, columns.plot_width, row_height,
                     right_scale, state.log_scale, -1.f, state.lobe_height_scale,
                     state.lobe_view_yaw_deg, state.lobe_view_pitch_deg, state.lobe_view_zoom,
                     state.yaw_deg, state.pitch_deg,
                     make_uchar4(92u, 204u, 188u, 255u), state.show_slice_plane, state.slice_plane_height,
                     false, false);
    }
}

}// namespace vision