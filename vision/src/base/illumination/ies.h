//
// Created by Zero on 2023/8/20.
//

#pragma once

#include "core/stl.h"
#include "base/using.h"

namespace vision {


// from blender cycles
class IESFile {
protected:
    /**
     * The brightness distribution is stored in spherical coordinates.
     * The horizontal angles correspond to theta in the regular notation
     * and always span the full range from 0 to 360.
     * The vertical angles correspond to phi and always start at 0.
     */
    ocarina::vector<float> _v_angles, _h_angles;

    /**
     * The actual values are stored here, with every entry storing the values
     * of one horizontal segment.
     */
    ocarina::vector<ocarina::vector<float>> _intensity;

    /**
     * Types of angle representation in IES files. Currently, only B and C are supported.
     */
    enum IESType { TYPE_A = 3,
                   TYPE_B = 2,
                   TYPE_C = 1 } type;

public:
    IESFile() = default;
    ~IESFile();
    int packed_size();
    void pack(float *data);
    bool load(const ocarina::string &ies);
    void clear();

protected:
    bool parse(const ocarina::string &ies);
    bool process();
    bool process_type_b();
    bool process_type_c();
};

}// namespace vision
