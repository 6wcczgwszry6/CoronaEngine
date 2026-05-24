//
// Created by Z on 2026/4/2.
//

#pragma once

#include "node_desc.h"
#include "core/stl.h"
#include "core/util/hash.h"
#include "base/using.h"

namespace vision {

enum class ParamType {
    Slot,
    Bool,
    Int,
    Float,
    String,
};

struct ParamDesc {
    string key{};
    ParamType type{ParamType::Slot};
    uint dim{0};
    AttrTag attr_tag{};
    bool required{false};
};

class ParamSchema {
private:
    vector<ParamDesc> specs_{};
    set<string> known_keys_{};

private:
    void check_required_keys(const DataWrap &params, const string &context) const noexcept;
    void check_unknown_keys(const DataWrap &params, const string &context) const noexcept;
    void check_slot_value(const GraphDesc &desc, const ParamDesc &spec,
                          const DataWrap &value, const string &context) const noexcept;
    void check_plain_value(const ParamDesc &spec, const DataWrap &value,
                           const string &context) const noexcept;
    [[nodiscard]] string suggest(const string &key) const noexcept;

public:
    void add(ParamDesc desc) noexcept;

    void add_slot(const string &key, AttrTag tag, uint dim,
                  bool required = false) noexcept {
        add({key, ParamType::Slot, dim, tag, required});
    }

    template<typename T>
    void add_slot(const string &key, T default_value, AttrTag tag,
                  bool required = false) noexcept {
        add({key, ParamType::Slot, type_dimension_v<T>, tag, required});
    }

    void add_plain(const string &key, ParamType type,
                   bool required = false) noexcept {
        add({key, type, 0u, {}, required});
    }

    void validate(const GraphDesc &desc, const string &context) const noexcept;
    void validate(const AttrDesc &desc, const string &context) const noexcept;
};

}
