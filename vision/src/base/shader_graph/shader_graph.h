//
// Created by Zero on 2025/3/28.
//

#pragma once

#include "shader_node.h"
#include "base/using.h"

namespace vision {

class GraphBlueprint final {
private:
    map<string, ShaderNodeDesc> node_map_{};

public:
    GraphBlueprint() = default;
    explicit GraphBlueprint(map<string, ShaderNodeDesc> node_map) noexcept;
    void clear() noexcept;
    [[nodiscard]] bool empty() const noexcept;
    [[nodiscard]] const map<string, ShaderNodeDesc> &node_map() const noexcept { return node_map_; }
};

class GraphBuilder final {
public:
    [[nodiscard]] static GraphBlueprint build(const map<string, ShaderNodeDesc> &tab) noexcept;
};

class GraphResolver final {
public:
    static void resolve(class ShaderGraph &graph, const GraphBlueprint &blueprint) noexcept;
};

class ShaderGraph : public enable_shared_from_this<ShaderGraph>, public ShaderNodeSlotSet {
protected:
    bool is_root_{false};
    weak_ptr<ShaderGraph> graph_;
    GraphBlueprint blueprint_{};
    map<string, SP<ShaderNode>> node_map_;
    bool graph_resolved_{false};

public:
    void add_node(SP<ShaderNode> node) noexcept;
    void add_node(const string &name, SP<ShaderNode> node);
    void clear() noexcept;
    void set_graph_blueprint(const map<string, ShaderNodeDesc> &tab) noexcept;
    void build_graph_blueprint(const map<string, ShaderNodeDesc> &tab) noexcept;
    void ensure_graph_ready() noexcept;
    void resolve_graph() noexcept;
    void initialize_root_graph() noexcept;
    void initialize_attached_graph(const SP<ShaderGraph> &graph) noexcept;
    [[nodiscard]] ShaderNodeSlot construct_slot(const ParameterSet &ps, AttrTag tag) const noexcept;
    [[nodiscard]] ShaderNodeSlot construct_slot(const AttrDesc &desc, const string &attr_name,
                                                AttrTag tag) const noexcept;
    template<typename T>
    [[nodiscard]] ShaderNodeSlot construct_slot(const AttrDesc &desc, const string &attr_name,
                                                T val, AttrTag tag) noexcept;
    [[nodiscard]] ShaderGraph *try_graph() noexcept;
    [[nodiscard]] const ShaderGraph *try_graph() const noexcept;
    [[nodiscard]] ShaderGraph &graph() noexcept;
    [[nodiscard]] const ShaderGraph &graph() const noexcept;
    [[nodiscard]] SP<const ShaderGraph> try_shared_graph() const noexcept;
    [[nodiscard]] SP<const ShaderGraph> shared_graph() const noexcept;
    [[nodiscard]] SP<ShaderGraph> try_shared_graph() noexcept;
    [[nodiscard]] SP<ShaderGraph> shared_graph() noexcept;
    [[nodiscard]] bool has_graph() const noexcept;
    OC_MAKE_MEMBER_GETTER_SETTER(is_root, )
    void attach_graph(SP<ShaderGraph> graph) noexcept;
    void set_graph(SP<ShaderGraph> graph) noexcept;
    void attach_graph_and_resolve(const SP<ShaderGraph> &graph) noexcept;
    void set_graph_and_resolve(const SP<ShaderGraph> &graph) noexcept;
    [[nodiscard]] SP<ShaderNode> get_node(const string &name) const noexcept {
        return node_map_.at(name);
    }
    [[nodiscard]] bool has_blueprint() const noexcept;
    [[nodiscard]] bool graph_resolved() const noexcept;
};

}// namespace vision
