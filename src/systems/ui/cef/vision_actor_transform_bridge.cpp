#include "vision_actor_transform_bridge.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <numbers>
#include <string>

#include <nlohmann/json.hpp>

namespace Corona::Systems::UI {
namespace {

constexpr double kAffineTolerance = 1.0e-6;
constexpr double kShearTolerance = 1.0e-4;
constexpr double kVectorTolerance = 1.0e-8;

using Vec3 = std::array<double, 3>;

struct Matrix4 {
    double value[4][4]{};  // Vision/Ocarina convention: [column][row].
};

Matrix4 identity_matrix() {
    Matrix4 matrix;
    for (int index = 0; index < 4; ++index) {
        matrix.value[index][index] = 1.0;
    }
    return matrix;
}

bool finite(double value) {
    return std::isfinite(value);
}

double dot(const Vec3& lhs, const Vec3& rhs) {
    return lhs[0] * rhs[0] + lhs[1] * rhs[1] + lhs[2] * rhs[2];
}

Vec3 subtract(const Vec3& lhs, const Vec3& rhs) {
    return {lhs[0] - rhs[0], lhs[1] - rhs[1], lhs[2] - rhs[2]};
}

Vec3 multiply(const Vec3& value, double scalar) {
    return {value[0] * scalar, value[1] * scalar, value[2] * scalar};
}

Vec3 cross(const Vec3& lhs, const Vec3& rhs) {
    return {
        lhs[1] * rhs[2] - lhs[2] * rhs[1],
        lhs[2] * rhs[0] - lhs[0] * rhs[2],
        lhs[0] * rhs[1] - lhs[1] * rhs[0],
    };
}

double length(const Vec3& value) {
    return std::sqrt(dot(value, value));
}

bool normalize(Vec3& value) {
    const double magnitude = length(value);
    if (!finite(magnitude) || magnitude <= kVectorTolerance) {
        return false;
    }
    value = multiply(value, 1.0 / magnitude);
    return true;
}

Matrix4 multiply(const Matrix4& lhs, const Matrix4& rhs) {
    Matrix4 result;
    for (int column = 0; column < 4; ++column) {
        for (int row = 0; row < 4; ++row) {
            for (int inner = 0; inner < 4; ++inner) {
                result.value[column][row] +=
                    lhs.value[inner][row] * rhs.value[column][inner];
            }
        }
    }
    return result;
}

Matrix4 translation_matrix(const Vec3& position) {
    auto matrix = identity_matrix();
    matrix.value[3][0] = position[0];
    matrix.value[3][1] = position[1];
    matrix.value[3][2] = position[2];
    return matrix;
}

Matrix4 rotation_x(double angle) {
    auto matrix = identity_matrix();
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    matrix.value[1][1] = cosine;
    matrix.value[1][2] = sine;
    matrix.value[2][1] = -sine;
    matrix.value[2][2] = cosine;
    return matrix;
}

Matrix4 rotation_y(double angle) {
    auto matrix = identity_matrix();
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    matrix.value[0][0] = cosine;
    matrix.value[0][2] = -sine;
    matrix.value[2][0] = sine;
    matrix.value[2][2] = cosine;
    return matrix;
}

Matrix4 rotation_z(double angle) {
    auto matrix = identity_matrix();
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    matrix.value[0][0] = cosine;
    matrix.value[0][1] = sine;
    matrix.value[1][0] = -sine;
    matrix.value[1][1] = cosine;
    return matrix;
}

bool json_vec3(const nlohmann::json& value, Vec3& result) {
    if (!value.is_array() || value.size() != 3) {
        return false;
    }
    for (std::size_t index = 0; index < 3; ++index) {
        if (!value[index].is_number()) {
            return false;
        }
        result[index] = value[index].get<double>();
        if (!finite(result[index])) {
            return false;
        }
    }
    return true;
}

bool json_number(const nlohmann::json& object,
                 std::string_view key,
                 double fallback,
                 double& result) {
    const auto iterator = object.find(std::string(key));
    if (iterator == object.end()) {
        result = fallback;
        return true;
    }
    if (!iterator->is_number()) {
        return false;
    }
    result = iterator->get<double>();
    return finite(result);
}

bool matrix_from_json(const nlohmann::json& value, Matrix4& matrix) {
    if (!value.is_array() || value.size() != 4) {
        return false;
    }
    for (std::size_t column = 0; column < 4; ++column) {
        if (!value[column].is_array() || value[column].size() != 4) {
            return false;
        }
        for (std::size_t row = 0; row < 4; ++row) {
            if (!value[column][row].is_number()) {
                return false;
            }
            matrix.value[column][row] = value[column][row].get<double>();
            if (!finite(matrix.value[column][row])) {
                return false;
            }
        }
    }
    return true;
}

bool matrix_from_axis_angle(const nlohmann::json& value, Matrix4& matrix) {
    if (!value.is_array() || value.size() != 4) {
        return false;
    }
    Vec3 axis{};
    for (std::size_t index = 0; index < 4; ++index) {
        if (!value[index].is_number()) {
            return false;
        }
        const double component = value[index].get<double>();
        if (!finite(component)) {
            return false;
        }
        if (index < 3) {
            axis[index] = component;
        }
    }
    const double angle_degrees = value[3].get<double>();
    if (std::abs(angle_degrees) <= kVectorTolerance) {
        matrix = identity_matrix();
        return true;
    }
    if (!normalize(axis)) {
        return false;
    }
    const double angle = angle_degrees * std::numbers::pi / 180.0;
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    const Vec3 t = multiply(axis, 1.0 - cosine);

    matrix = identity_matrix();
    matrix.value[0][0] = cosine + t[0] * axis[0];
    matrix.value[0][1] = t[0] * axis[1] + sine * axis[2];
    matrix.value[0][2] = t[0] * axis[2] - sine * axis[1];
    matrix.value[1][0] = t[1] * axis[0] - sine * axis[2];
    matrix.value[1][1] = cosine + t[1] * axis[1];
    matrix.value[1][2] = t[1] * axis[2] + sine * axis[0];
    matrix.value[2][0] = t[2] * axis[0] + sine * axis[1];
    matrix.value[2][1] = t[2] * axis[1] - sine * axis[0];
    matrix.value[2][2] = cosine + t[2] * axis[2];
    return true;
}

bool vision_matrix_from_transform(const nlohmann::json& transform, Matrix4& matrix) {
    if (!transform.is_object()) {
        return false;
    }
    const std::string type = transform.value("type", "matrix4x4");
    const auto params_iterator = transform.find("param");
    const nlohmann::json& params =
        params_iterator != transform.end() && params_iterator->is_object()
            ? *params_iterator
            : transform;

    if (type == "matrix4x4") {
        const auto iterator = params.find("matrix4x4");
        return iterator != params.end() && matrix_from_json(*iterator, matrix);
    }

    if (type == "trs") {
        Vec3 translation{0.0, 0.0, 0.0};
        Vec3 scale{1.0, 1.0, 1.0};
        const auto translation_iterator = params.find("t");
        if (translation_iterator != params.end() && !json_vec3(*translation_iterator, translation)) {
            return false;
        }
        const auto scale_iterator = params.find("s");
        if (scale_iterator != params.end() && !json_vec3(*scale_iterator, scale)) {
            return false;
        }
        Matrix4 rotation = identity_matrix();
        const auto rotation_iterator = params.find("r");
        if (rotation_iterator != params.end() &&
            !matrix_from_axis_angle(*rotation_iterator, rotation)) {
            return false;
        }
        matrix = rotation;
        for (int row = 0; row < 3; ++row) {
            matrix.value[0][row] *= scale[0];
            matrix.value[1][row] *= scale[1];
            matrix.value[2][row] *= scale[2];
        }
        matrix.value[3][0] = translation[0];
        matrix.value[3][1] = translation[1];
        matrix.value[3][2] = translation[2];
        return true;
    }

    if (type == "Euler") {
        Vec3 position{0.0, 0.0, 0.0};
        const auto position_iterator = params.find("position");
        if (position_iterator != params.end() && !json_vec3(*position_iterator, position)) {
            return false;
        }
        double yaw = 0.0;
        double roll = 0.0;
        double pitch = 0.0;
        if (!json_number(params, "yaw", 0.0, yaw) ||
            !json_number(params, "roll", 0.0, roll) ||
            !json_number(params, "pitch", 0.0, pitch)) {
            return false;
        }
        constexpr double degrees_to_radians = std::numbers::pi / 180.0;
        matrix = multiply(translation_matrix(position),
                          multiply(rotation_x(pitch * degrees_to_radians),
                                   multiply(rotation_z(roll * degrees_to_radians),
                                            rotation_y(yaw * degrees_to_radians))));
        return true;
    }

    if (type == "look_at") {
        Vec3 position{0.0, 0.0, 0.0};
        Vec3 target{0.0, 0.0, 1.0};
        Vec3 up{0.0, 1.0, 0.0};
        const auto position_iterator = params.find("position");
        const auto target_iterator = params.find("target_pos");
        const auto up_iterator = params.find("up");
        if ((position_iterator != params.end() && !json_vec3(*position_iterator, position)) ||
            (target_iterator != params.end() && !json_vec3(*target_iterator, target)) ||
            (up_iterator != params.end() && !json_vec3(*up_iterator, up))) {
            return false;
        }
        Vec3 forward = subtract(target, position);
        if (!normalize(forward)) {
            return false;
        }
        Vec3 right = cross(forward, up);
        if (!normalize(right)) {
            return false;
        }
        Vec3 corrected_up = cross(right, forward);
        if (!normalize(corrected_up)) {
            return false;
        }
        matrix = identity_matrix();
        for (int row = 0; row < 3; ++row) {
            matrix.value[0][row] = right[row];
            matrix.value[1][row] = corrected_up[row];
            matrix.value[2][row] = forward[row];
            matrix.value[3][row] = position[row];
        }
        return true;
    }

    return false;
}

Matrix4 vision_to_corona_matrix(Matrix4 matrix) {
    for (int column = 0; column < 4; ++column) {
        for (int row = 0; row < 4; ++row) {
            if (column == 2) {
                matrix.value[column][row] = -matrix.value[column][row];
            }
            if (row == 2) {
                matrix.value[column][row] = -matrix.value[column][row];
            }
        }
    }
    return matrix;
}

bool is_affine(const Matrix4& matrix) {
    for (int column = 0; column < 4; ++column) {
        for (int row = 0; row < 4; ++row) {
            if (!finite(matrix.value[column][row])) {
                return false;
            }
        }
    }
    return std::abs(matrix.value[0][3]) <= kAffineTolerance &&
           std::abs(matrix.value[1][3]) <= kAffineTolerance &&
           std::abs(matrix.value[2][3]) <= kAffineTolerance &&
           std::abs(matrix.value[3][3] - 1.0) <= kAffineTolerance;
}

VisionActorTransformState decompose_corona_matrix(const Matrix4& matrix) {
    VisionActorTransformState result;
    if (!is_affine(matrix)) {
        return result;
    }

    Vec3 column_x{matrix.value[0][0], matrix.value[0][1], matrix.value[0][2]};
    Vec3 column_y{matrix.value[1][0], matrix.value[1][1], matrix.value[1][2]};
    const Vec3 column_z{matrix.value[2][0], matrix.value[2][1], matrix.value[2][2]};
    const double scale_x = length(column_x);
    const double scale_y = length(column_y);
    const double scale_z_magnitude = length(column_z);
    if (scale_x <= kVectorTolerance || scale_y <= kVectorTolerance ||
        scale_z_magnitude <= kVectorTolerance || !normalize(column_x)) {
        return result;
    }

    const Vec3 normalized_y = multiply(column_y, 1.0 / scale_y);
    const Vec3 normalized_z = multiply(column_z, 1.0 / scale_z_magnitude);
    const double shear_xy = dot(column_x, normalized_y);
    const double shear_xz = dot(column_x, normalized_z);
    const double shear_yz = dot(normalized_y, normalized_z);
    result.lossy = std::max({std::abs(shear_xy), std::abs(shear_xz),
                             std::abs(shear_yz)}) > kShearTolerance;

    column_y = subtract(column_y, multiply(column_x, dot(column_x, column_y)));
    if (!normalize(column_y)) {
        return VisionActorTransformState{};
    }
    Vec3 rotation_z_axis = cross(column_x, column_y);
    if (!normalize(rotation_z_axis)) {
        return VisionActorTransformState{};
    }
    const double scale_z = dot(column_z, rotation_z_axis) < 0.0
                               ? -scale_z_magnitude
                               : scale_z_magnitude;

    const double r00 = column_x[0];
    const double r10 = column_x[1];
    const double r20 = column_x[2];
    const double r11 = column_y[1];
    const double r12 = rotation_z_axis[1];
    const double r21 = column_y[2];
    const double r22 = rotation_z_axis[2];
    const double rotation_y_value = std::asin(std::clamp(-r20, -1.0, 1.0));
    const double cosine_y = std::cos(rotation_y_value);
    double rotation_x_value = 0.0;
    double rotation_z_value = 0.0;
    if (std::abs(cosine_y) > kVectorTolerance) {
        rotation_x_value = std::atan2(r21, r22);
        rotation_z_value = std::atan2(r10, r00);
    } else {
        rotation_x_value = std::atan2(-r12, r11);
    }

    result.position = {
        static_cast<float>(matrix.value[3][0]),
        static_cast<float>(matrix.value[3][1]),
        static_cast<float>(matrix.value[3][2]),
    };
    result.rotation = {
        static_cast<float>(rotation_x_value),
        static_cast<float>(rotation_y_value),
        static_cast<float>(rotation_z_value),
    };
    result.scale = {
        static_cast<float>(scale_x),
        static_cast<float>(scale_y),
        static_cast<float>(scale_z),
    };
    result.valid = true;
    return result;
}

std::array<double, 4> multiply_quaternion(const std::array<double, 4>& lhs,
                                         const std::array<double, 4>& rhs) {
    return {
        lhs[0] * rhs[0] - lhs[1] * rhs[1] - lhs[2] * rhs[2] - lhs[3] * rhs[3],
        lhs[0] * rhs[1] + lhs[1] * rhs[0] + lhs[2] * rhs[3] - lhs[3] * rhs[2],
        lhs[0] * rhs[2] - lhs[1] * rhs[3] + lhs[2] * rhs[0] + lhs[3] * rhs[1],
        lhs[0] * rhs[3] + lhs[1] * rhs[2] - lhs[2] * rhs[1] + lhs[3] * rhs[0],
    };
}

std::array<double, 4> quaternion_from_corona_euler(const std::array<float, 3>& rotation) {
    const double half_x = static_cast<double>(rotation[0]) * 0.5;
    const double half_y = static_cast<double>(rotation[1]) * 0.5;
    const double half_z = static_cast<double>(rotation[2]) * 0.5;
    const std::array<double, 4> qx{std::cos(half_x), std::sin(half_x), 0.0, 0.0};
    const std::array<double, 4> qy{std::cos(half_y), 0.0, std::sin(half_y), 0.0};
    const std::array<double, 4> qz{std::cos(half_z), 0.0, 0.0, std::sin(half_z)};
    return multiply_quaternion(qz, multiply_quaternion(qy, qx));
}

}  // namespace

VisionActorTransformState decode_vision_actor_transform(const nlohmann::json& transform) {
    Matrix4 vision_matrix;
    if (!vision_matrix_from_transform(transform, vision_matrix)) {
        return {};
    }
    return decompose_corona_matrix(vision_to_corona_matrix(vision_matrix));
}

nlohmann::json encode_vision_actor_transform(const VisionActorTransformState& state) {
    if (!state.valid) {
        return nlohmann::json::object();
    }
    auto vision_quaternion = quaternion_from_corona_euler(state.rotation);
    vision_quaternion[1] = -vision_quaternion[1];
    vision_quaternion[2] = -vision_quaternion[2];
    if (vision_quaternion[0] < 0.0) {
        for (auto& component : vision_quaternion) {
            component = -component;
        }
    }
    const double sine_half_angle = std::sqrt(
        vision_quaternion[1] * vision_quaternion[1] +
        vision_quaternion[2] * vision_quaternion[2] +
        vision_quaternion[3] * vision_quaternion[3]);
    Vec3 axis{1.0, 0.0, 0.0};
    double angle_degrees = 0.0;
    if (sine_half_angle > kVectorTolerance) {
        axis = {
            vision_quaternion[1] / sine_half_angle,
            vision_quaternion[2] / sine_half_angle,
            vision_quaternion[3] / sine_half_angle,
        };
        angle_degrees = 2.0 * std::atan2(sine_half_angle, vision_quaternion[0]) *
                        180.0 / std::numbers::pi;
    }
    const nlohmann::json vision_axis_angle = nlohmann::json::array({
        axis[0], axis[1], axis[2], angle_degrees,
    });
    return {
        {"type", "trs"},
        {"param",
         {
             {"t", {state.position[0], state.position[1], -state.position[2]}},
             {"r", std::move(vision_axis_angle)},
             {"s", state.scale},
         }},
    };
}

}  // namespace Corona::Systems::UI
