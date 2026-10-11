#pragma once

#include <Codegen/ControlFlows.h>
#include <Codegen/CustomLibrary.h>
#include <Codegen/TypeAlias.h>

#include <array>
#include <cstdint>

namespace Corona::Systems::GpuCollisionMath {

using EmbeddedShader::abs;
using EmbeddedShader::Float;
using EmbeddedShader::GPU_ELSE_BRANCH;
using EmbeddedShader::GPU_IF;
using EmbeddedShader::GPU_IF_BRANCH;
using EmbeddedShader::max;
using EmbeddedShader::min;
using EmbeddedShader::sqrt;
using EmbeddedShader::Uint;

// Scalars deliberately avoid vector intrinsic return-type inference in Helicon.
// Define locals before assigning their expressions: proxy copies otherwise may
// retain expression references instead of the independent variables we need.
struct Vec3 {
    Float x, y, z;
};

inline Vec3 add(const Vec3& a, const Vec3& b) {
    Vec3 r;
    r.x = a.x + b.x;
    r.y = a.y + b.y;
    r.z = a.z + b.z;
    return r;
}
inline Vec3 sub(const Vec3& a, const Vec3& b) {
    Vec3 r;
    r.x = a.x - b.x;
    r.y = a.y - b.y;
    r.z = a.z - b.z;
    return r;
}
inline Vec3 mul(const Vec3& a, const Float& s) {
    Vec3 r;
    r.x = a.x * s;
    r.y = a.y * s;
    r.z = a.z * s;
    return r;
}
inline Float dot(const Vec3& a, const Vec3& b) {
    Float r;
    r = a.x * b.x + a.y * b.y + a.z * b.z;
    return r;
}
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    Vec3 r;
    r.x = a.y * b.z - a.z * b.y;
    r.y = a.z * b.x - a.x * b.z;
    r.z = a.x * b.y - a.y * b.x;
    return r;
}
inline Float length(const Vec3& a) {
    Float r;
    r = sqrt(dot(a, a));
    return r;
}
inline Vec3 normalize_safe(const Vec3& a) {
    Vec3 r;
    r.x = 0.0f;
    r.y = 1.0f;
    r.z = 0.0f;
    Float len;
    len = length(a);
    $IF(!(len < Float(1e-8f))) {
        r.x = a.x / len;
        r.y = a.y / len;
        r.z = a.z / len;
    }
    return r;
}
inline Float saturate(const Float& v) {
    Float r;
    r = max(Float(0.0f), min(Float(1.0f), v));
    return r;
}

// Sum/count, rather than one point per triangle pair, preserves the CPU
// narrowphase's average across every accepted point-face / edge-edge contact.
struct Contact {
    Float depth, nx, ny, nz, sx, sy, sz;
    Uint count;
};

inline void accumulate(Contact& out, const Float& depth, const Vec3& normal, const Vec3& point) {
    out.sx = out.sx + point.x;
    out.sy = out.sy + point.y;
    out.sz = out.sz + point.z;
    out.count = out.count + Uint(1u);
    $IF(out.depth < depth) {
        out.depth = depth;
        out.nx = normal.x;
        out.ny = normal.y;
        out.nz = normal.z;
    }
}

inline void segment_segment_closest(const Vec3& p, const Vec3& d,
                                    const Vec3& q, const Vec3& e,
                                    Float& t, Float& s) {
    Vec3 r;
    r = sub(p, q);
    Float a, f, ee;
    a = dot(d, d);
    f = dot(e, r);
    ee = dot(e, e);
    t = 0.0f;
    s = 0.0f;
    $IF(!((a < Float(1e-10f)) && (ee < Float(1e-10f)))) {
        $IF(a < Float(1e-10f)) {
            s = saturate(f / ee);
        }
        $ELSE {
            Float c;
            c = dot(d, r);
            $IF(ee < Float(1e-10f)) {
                t = saturate(-c / a);
            }
            $ELSE {
                Float b, denom;
                b = dot(d, e);
                denom = a * ee - b * b;
                $IF(denom > Float(1e-10f)) {
                    t = saturate((b * f - c * ee) / denom);
                }
                s = (b * t + f) / ee;
                $IF(s < Float(0.0f)) {
                    s = 0.0f;
                    t = saturate(-c / a);
                }
                $ELSE {
                    $IF(s > Float(1.0f)) {
                        s = 1.0f;
                        t = saturate((b - c) / a);
                    }
                }
            }
        }
    }
}

inline void point_triangle_signed_dist(const Vec3& point, const std::array<Vec3, 3>& tri,
                                       const Vec3& normal, Float& distance, Uint& inside) {
    distance = dot(normal, sub(point, tri[0]));
    Vec3 projected, v0, v1, v2;
    projected = sub(point, mul(normal, distance));
    v0 = sub(tri[2], tri[0]);
    v1 = sub(tri[1], tri[0]);
    v2 = sub(projected, tri[0]);
    Float d00, d01, d02, d11, d12, denom;
    d00 = dot(v0, v0);
    d01 = dot(v0, v1);
    d02 = dot(v0, v2);
    d11 = dot(v1, v1);
    d12 = dot(v1, v2);
    denom = d00 * d11 - d01 * d01;
    inside = 0u;
    $IF(!(abs(denom) < Float(1e-12f))) {
        Float inverse, u, v;
        inverse = Float(1.0f) / denom;
        u = (d11 * d02 - d01 * d12) * inverse;
        v = (d00 * d12 - d01 * d02) * inverse;
        $IF((u >= Float(-1e-5f)) && (v >= Float(-1e-5f)) &&
            (u + v <= Float(1.0f + 1e-5f))) { inside = 1u; }
    }
}

inline void coplanar_triangles_overlap(const std::array<Vec3, 3>& a,
                                       const std::array<Vec3, 3>& b,
                                       const Vec3& normal, Uint& overlap) {
    Vec3 tangent, u, v;
    tangent.x = 1.0f;
    tangent.y = 0.0f;
    tangent.z = 0.0f;
    $IF(abs(dot(normal, tangent)) > Float(0.9f)) {
        tangent.x = 0.0f;
        tangent.y = 1.0f;
    }
    u = normalize_safe(cross(normal, tangent));
    v = cross(normal, u);
    std::array<Float, 3> ax, ay, bx, by;
    for (std::size_t i = 0; i < 3; ++i) {
        ax[i] = dot(u, a[i]);
        ay[i] = dot(v, a[i]);
        bx[i] = dot(u, b[i]);
        by[i] = dot(v, b[i]);
    }
    overlap = 1u;
    auto test_axis = [&](const Float& x, const Float& y) {
        Float amin, amax, bmin, bmax, ap, bp;
        amin = ax[0] * x + ay[0] * y;
        amax = amin;
        bmin = bx[0] * x + by[0] * y;
        bmax = bmin;
        for (std::size_t i = 1; i < 3; ++i) {
            ap = ax[i] * x + ay[i] * y;
            bp = bx[i] * x + by[i] * y;
            amin = min(amin, ap);
            amax = max(amax, ap);
            bmin = min(bmin, bp);
            bmax = max(bmax, bp);
        }
        $IF((amax < bmin - Float(1e-5f)) || (bmax < amin - Float(1e-5f))) { overlap = 0u; }
    };
    for (std::size_t i = 0; i < 3; ++i) {
        const auto j = (i + 1) % 3;
        Float x, y;
        x = -(ay[j] - ay[i]);
        y = ax[j] - ax[i];
        test_axis(x, y);
    }
    for (std::size_t i = 0; i < 3; ++i) {
        const auto j = (i + 1) % 3;
        Float x, y;
        x = -(by[j] - by[i]);
        y = bx[j] - bx[i];
        test_axis(x, y);
    }
}

inline void project_interval(const std::array<Float, 3>& source_distance,
                             const std::array<Vec3, 3>& tri, const Vec3& axis,
                             Float& out_min, Float& out_max) {
    std::array<Float, 3> distance, projection;
    for (std::size_t i = 0; i < 3; ++i) {
        distance[i] = source_distance[i];
        projection[i] = dot(axis, tri[i]);
    }
    Float dl, pl, da, db, pa, pb;
    // The CPU implementation defaults to vertex 2 as the lone endpoint.
    dl = distance[2];
    pl = projection[2];
    da = distance[0];
    db = distance[1];
    pa = projection[0];
    pb = projection[1];
    $IF(((distance[0] > Float(0.0f)) != (distance[1] > Float(0.0f))) &&
        ((distance[0] > Float(0.0f)) != (distance[2] > Float(0.0f)))) {
        dl = distance[0];
        pl = projection[0];
        da = distance[1];
        db = distance[2];
        pa = projection[1];
        pb = projection[2];
    }
    $ELSE {
        $IF(((distance[1] > Float(0.0f)) != (distance[0] > Float(0.0f))) &&
            ((distance[1] > Float(0.0f)) != (distance[2] > Float(0.0f)))) {
            dl = distance[1];
            pl = projection[1];
            da = distance[0];
            db = distance[2];
            pa = projection[0];
            pb = projection[2];
        }
    }
    Float ta, tb, denom_a, denom_b;
    ta = pl;
    tb = pl;
    denom_a = dl - da;
    denom_b = dl - db;
    $IF(abs(denom_a) > Float(1e-10f)) { ta = pl + (pa - pl) * (dl / denom_a); }
    $IF(abs(denom_b) > Float(1e-10f)) { tb = pl + (pb - pl) * (dl / denom_b); }
    out_min = min(ta, tb);
    out_max = max(ta, tb);
}

inline void moller_triangle_triangle_intersect(const std::array<Vec3, 3>& a,
                                               const std::array<Vec3, 3>& b,
                                               const Float& threshold,
                                               Uint& hit, Vec3& normal, Float& depth) {
    hit = 0u;
    depth = 0.0f;
    normal.x = 0.0f;
    normal.y = 1.0f;
    normal.z = 0.0f;
    Vec3 na_raw, nb_raw;
    na_raw = cross(sub(a[1], a[0]), sub(a[2], a[0]));
    nb_raw = cross(sub(b[1], b[0]), sub(b[2], b[0]));
    Float la, lb;
    la = length(na_raw);
    lb = length(nb_raw);
    $IF((la >= Float(1e-7f)) && (lb >= Float(1e-7f))) {
        Vec3 na, nb;
        na = mul(na_raw, Float(1.0f) / la);
        nb = mul(nb_raw, Float(1.0f) / lb);
        Float plane_a, plane_b;
        plane_a = dot(na, a[0]);
        plane_b = dot(nb, b[0]);
        std::array<Float, 3> da, db;
        for (std::size_t i = 0; i < 3; ++i) {
            db[i] = dot(na, b[i]) - plane_a;
            da[i] = dot(nb, a[i]) - plane_b;
        }
        Uint separated;
        separated = 0u;
        $IF((db[0] * db[1] > Float(0.0f)) && (db[0] * db[2] > Float(0.0f)) &&
            (abs(db[0]) > Float(1e-7f)) && (abs(db[1]) > Float(1e-7f)) && (abs(db[2]) > Float(1e-7f))) {
            separated = 1u;
        }
        $IF((da[0] * da[1] > Float(0.0f)) && (da[0] * da[2] > Float(0.0f)) &&
            (abs(da[0]) > Float(1e-7f)) && (abs(da[1]) > Float(1e-7f)) && (abs(da[2]) > Float(1e-7f))) {
            separated = 1u;
        }
        $IF(separated == Uint(0u)) {
            Vec3 line;
            line = cross(na, nb);
            Float line_length;
            line_length = length(line);
            $IF(line_length < Float(1e-6f)) {
                Uint overlap;
                coplanar_triangles_overlap(a, b, na, overlap);
                $IF(overlap != Uint(0u)) {
                    hit = 1u;
                    normal = na;
                    depth = threshold;
                }
            }
            $ELSE {
                Vec3 axis;
                axis = mul(line, Float(1.0f) / line_length);
                Float amin, amax, bmin, bmax, start, end;
                project_interval(da, a, axis, amin, amax);
                project_interval(db, b, axis, bmin, bmax);
                start = max(amin, bmin);
                end = min(amax, bmax);
                $IF(!(end <= start - Float(1e-7f))) {
                    hit = 1u;
                    depth = end - start;
                    normal = mul(nb, Float(-1.0f));
                }
            }
        }
    }
}

// Emits one exact triangle-pair test. All C++ loops below generate a fixed
// number of shader statements; no runtime loops, atomics, or shared memory.
inline void triangle_contact(const std::array<Vec3, 3>& a,
                             const std::array<Vec3, 3>& b,
                             const Float& threshold, Contact& out) {
    out.depth = Float(0.0f) - threshold;
    out.nx = 0.0f;
    out.ny = 1.0f;
    out.nz = 0.0f;
    out.sx = 0.0f;
    out.sy = 0.0f;
    out.sz = 0.0f;
    out.count = 0u;
    Vec3 amin, amax, bmin, bmax;
    amin = a[0];
    amax = a[0];
    bmin = b[0];
    bmax = b[0];
    for (std::size_t i = 1; i < 3; ++i) {
        amin.x = min(amin.x, a[i].x);
        amin.y = min(amin.y, a[i].y);
        amin.z = min(amin.z, a[i].z);
        amax.x = max(amax.x, a[i].x);
        amax.y = max(amax.y, a[i].y);
        amax.z = max(amax.z, a[i].z);
        bmin.x = min(bmin.x, b[i].x);
        bmin.y = min(bmin.y, b[i].y);
        bmin.z = min(bmin.z, b[i].z);
        bmax.x = max(bmax.x, b[i].x);
        bmax.y = max(bmax.y, b[i].y);
        bmax.z = max(bmax.z, b[i].z);
    }
    $IF(!((amin.x - threshold > bmax.x) || (bmin.x - threshold > amax.x) ||
          (amin.y - threshold > bmax.y) || (bmin.y - threshold > amax.y) ||
          (amin.z - threshold > bmax.z) || (bmin.z - threshold > amax.z))) {
        Vec3 na, nb, intersection_normal;
        na = normalize_safe(cross(sub(a[1], a[0]), sub(a[2], a[0])));
        nb = normalize_safe(cross(sub(b[1], b[0]), sub(b[2], b[0])));
        Float intersection_depth;
        Uint intersects;
        moller_triangle_triangle_intersect(a, b, threshold, intersects, intersection_normal, intersection_depth);
        $IF(intersects != Uint(0u)) {
            Vec3 point;
            point.x = (a[0].x + a[1].x + a[2].x + b[0].x + b[1].x + b[2].x) / Float(6.0f);
            point.y = (a[0].y + a[1].y + a[2].y + b[0].y + b[1].y + b[2].y) / Float(6.0f);
            point.z = (a[0].z + a[1].z + a[2].z + b[0].z + b[1].z + b[2].z) / Float(6.0f);
            accumulate(out, intersection_depth, intersection_normal, point);
        }
        $ELSE {
            for (std::size_t i = 0; i < 3; ++i) {
                Float distance;
                Uint inside;
                point_triangle_signed_dist(b[i], a, na, distance, inside);
                $IF((inside != Uint(0u)) && (distance >= Float(0.0f)) && (distance <= threshold)) {
                    Vec3 point;
                    point = sub(b[i], mul(na, distance));
                    accumulate(out, threshold - distance, na, point);
                }
            }
            for (std::size_t i = 0; i < 3; ++i) {
                Float distance;
                Uint inside;
                point_triangle_signed_dist(a[i], b, nb, distance, inside);
                $IF((inside != Uint(0u)) && (distance >= Float(0.0f)) && (distance <= threshold)) {
                    Vec3 point, normal;
                    point = sub(a[i], mul(nb, distance));
                    normal = mul(nb, Float(-1.0f));
                    accumulate(out, threshold - distance, normal, point);
                }
            }
            for (std::size_t i = 0; i < 3; ++i) {
                for (std::size_t j = 0; j < 3; ++j) {
                    Vec3 da, db, pa, pb, difference;
                    da = sub(a[(i + 1) % 3], a[i]);
                    db = sub(b[(j + 1) % 3], b[j]);
                    Float t, s, distance_sq;
                    segment_segment_closest(a[i], da, b[j], db, t, s);
                    pa = add(a[i], mul(da, t));
                    pb = add(b[j], mul(db, s));
                    difference = sub(pb, pa);
                    distance_sq = dot(difference, difference);
                    $IF((distance_sq < threshold * threshold) && (distance_sq >= Float(1e-12f))) {
                        Float distance;
                        distance = sqrt(distance_sq);
                        Vec3 normal, point;
                        normal = mul(difference, Float(1.0f) / distance);
                        point = mul(add(pa, pb), Float(0.5f));
                        accumulate(out, threshold - distance, normal, point);
                    }
                }
            }
        }
    }
}

}  // namespace Corona::Systems::GpuCollisionMath
