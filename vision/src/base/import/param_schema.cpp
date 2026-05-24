//
// Created by Zero on 2026/4/2.
//

#include "param_schema.h"

#include <algorithm>
#include <limits>

namespace vision {

namespace {

[[nodiscard]] string json_type_name(const DataWrap &value) noexcept {
	if (value.is_null()) {
		return "null";
	}
	if (value.is_boolean()) {
		return "bool";
	}
	if (value.is_number_integer() || value.is_number_unsigned()) {
		return "int";
	}
	if (value.is_number_float()) {
		return "float";
	}
	if (value.is_number()) {
		return "number";
	}
	if (value.is_string()) {
		return "string";
	}
	if (value.is_array()) {
		return "array";
	}
	if (value.is_object()) {
		return "object";
	}
	return "unknown";
}

[[nodiscard]] string expected_type_name(ParamType type) noexcept {
	switch (type) {
		case ParamType::Slot: return "slot";
		case ParamType::Bool: return "bool";
		case ParamType::Int: return "int";
		case ParamType::Float: return "float";
		case ParamType::String: return "string";
		default: break;
	}
	return "unknown";
}

[[nodiscard]] size_t edit_distance(const string &lhs, const string &rhs) noexcept {
	const size_t lhs_size = lhs.size();
	const size_t rhs_size = rhs.size();
	vector<size_t> prev(rhs_size + 1u);
	vector<size_t> curr(rhs_size + 1u);
	for (size_t j = 0; j <= rhs_size; ++j) {
		prev[j] = j;
	}
	for (size_t i = 1; i <= lhs_size; ++i) {
		curr[0] = i;
		for (size_t j = 1; j <= rhs_size; ++j) {
			const size_t cost = lhs[i - 1] == rhs[j - 1] ? 0u : 1u;
			curr[j] = std::min({prev[j] + 1u, curr[j - 1] + 1u, prev[j - 1] + cost});
		}
		prev.swap(curr);
	}
	return prev[rhs_size];
}

[[nodiscard]] bool is_valid_slot_array(const DataWrap &value) noexcept {
	for (const auto &element : value) {
		if (!element.is_number()) {
			return false;
		}
	}
	return true;
}

void check_slot_dimension(const string &key, uint expected_dim, const DataWrap &value,
					  const string &context) noexcept {
	if (value.is_array()) {
		if (!is_valid_slot_array(value)) {
			OC_WARNING_FORMAT("{}: slot '{}' array elements must be numbers", context, key);
			return;
		}
		if (expected_dim > 0u && value.size() != expected_dim) {
			OC_WARNING_FORMAT("{}: slot '{}' expects dim {}, got {}", context, key, expected_dim, value.size());
		}
		return;
	}
	if (value.is_number()) {
		if (expected_dim > 1u) {
			OC_WARNING_FORMAT("{}: slot '{}' expects dim {}, got scalar", context, key, expected_dim);
		}
		return;
	}
	OC_WARNING_FORMAT("{}: slot '{}' number node value must be number or array, got {}", context,
					  key, json_type_name(value));
}

void check_channels_dimension(const ParamDesc &spec, const string &channels,
					  const string &context) noexcept {
	if (spec.dim > 0u && channels.size() != spec.dim) {
		OC_WARNING_FORMAT("{}: slot '{}' expects dim {}, got channels dim {} ('{}')",
					  context, spec.key, spec.dim, channels.size(), channels);
	}
}

[[nodiscard]] const DataWrap *node_param_payload(const DataWrap &value) noexcept {
	if (!value.contains("param")) {
		return nullptr;
	}
	if (!value["param"].is_object()) {
		return nullptr;
	}
	return &value["param"];
}

void check_inline_node_value(const ParamDesc &spec, const DataWrap &value,
					 const string &context, uint expected_dim) noexcept {
	if (!value.is_object()) {
		OC_WARNING_FORMAT("{}: slot '{}' node data must be object, got {}", context, spec.key,
					  json_type_name(value));
		return;
	}
    const DataWrap type_value = value.value("type", DataWrap("image"));
	if (!type_value.is_string()) {
		OC_WARNING_FORMAT("{}: slot '{}' type must be string, got {}", context, spec.key,
					  json_type_name(type_value));
		return;
	}
	const DataWrap *payload = node_param_payload(value);
	if (!value.contains("param")) {
		OC_WARNING_FORMAT("{}: slot '{}' node object must contain 'param'", context, spec.key);
		return;
	}
	if (payload == nullptr) {
		OC_WARNING_FORMAT("{}: slot '{}' node param must be object, got {}", context, spec.key,
					  json_type_name(value["param"]));
		return;
	}
    const string type = type_value.get<string>();
	if (type == "image") {
		if (!payload->contains("fn") || !(*payload)["fn"].is_string()) {
			OC_WARNING_FORMAT("{}: slot '{}' image node missing string 'fn'", context, spec.key);
		}
		return;
	}
	if (type == "number") {
		if (!payload->contains("value")) {
			OC_WARNING_FORMAT("{}: slot '{}' number node missing 'value'", context, spec.key);
			return;
		}
		check_slot_dimension(spec.key, expected_dim, (*payload)["value"], context);
		return;
	}
	OC_WARNING_FORMAT("{}: slot '{}' unsupported node type '{}', expected node data in 'param'", context,
				  spec.key, type);
}

}// namespace

void ParamSchema::add(ParamDesc desc) noexcept {
	auto iter = std::find_if(specs_.begin(), specs_.end(), [&](const ParamDesc &spec) {
		return spec.key == desc.key;
	});
	if (iter != specs_.end()) {
		*iter = std::move(desc);
		known_keys_.insert(iter->key);
		return;
	}
	known_keys_.insert(desc.key);
	specs_.emplace_back(std::move(desc));
}

void ParamSchema::check_required_keys(const DataWrap &params, const string &context) const noexcept {
	for (const ParamDesc &spec : specs_) {
		if (!spec.required) {
			continue;
		}
		if (!params.is_object() || !params.contains(spec.key)) {
			OC_WARNING_FORMAT("{}: missing required param '{}'", context, spec.key);
		}
	}
}

void ParamSchema::check_unknown_keys(const DataWrap &params, const string &context) const noexcept {
	if (!params.is_object()) {
		return;
	}
	for (const auto &[key, _] : params.items()) {
		if (known_keys_.contains(key)) {
			continue;
		}
		string suggestion = suggest(key);
		if (suggestion.empty()) {
			OC_WARNING_FORMAT("{}: unknown param '{}'", context, key);
		} else {
			OC_WARNING_FORMAT("{}: unknown param '{}', did you mean '{}' ?", context, key, suggestion);
		}
	}
}

void ParamSchema::check_slot_value(const GraphDesc &desc, const ParamDesc &spec,
								   const DataWrap &value, const string &context) const noexcept {
	if (value.is_null()) {
		return;
	}
	if (value.is_number()) {
		if (spec.dim > 1u) {
			OC_WARNING_FORMAT("{}: slot '{}' expects dim {}, got scalar", context, spec.key, spec.dim);
		}
		return;
	}
	if (value.is_array()) {
		if (!is_valid_slot_array(value)) {
			OC_WARNING_FORMAT("{}: slot '{}' array elements must be numbers", context, spec.key);
			return;
		}
		if (spec.dim > 0u && value.size() != spec.dim) {
			OC_WARNING_FORMAT("{}: slot '{}' expects dim {}, got {}", context, spec.key, spec.dim, value.size());
		}
		return;
	}
	if (value.is_string()) {
		string node_name = value.get<string>();
		if (!desc.node_map.contains(node_name)) {
			OC_WARNING_FORMAT("{}: slot '{}' references node '{}' which is not in node_tab", context,
						  spec.key, node_name);
		}
		return;
	}
	if (!value.is_object()) {
		OC_WARNING_FORMAT("{}: slot '{}' expected slot-like value, got {}", context, spec.key, json_type_name(value));
		return;
	}
	if (value.contains("node")) {
		if (!value.contains("channels")) {
			OC_WARNING_FORMAT("{}: slot '{}' node reference should contain 'channels'", context, spec.key);
		} else if (!value["channels"].is_string()) {
			OC_WARNING_FORMAT("{}: slot '{}' channels must be string, got {}", context, spec.key,
						  json_type_name(value["channels"]));
		} else {
			check_channels_dimension(spec, value["channels"].get<string>(), context);
		}
		if (value.contains("output_key") && !value["output_key"].is_string()) {
			OC_WARNING_FORMAT("{}: slot '{}' output_key must be string, got {}", context, spec.key,
						  json_type_name(value["output_key"]));
		}
		const DataWrap &node_value = value["node"];
		if (node_value.is_string()) {
			string node_name = node_value.get<string>();
			if (!desc.node_map.contains(node_name)) {
				OC_WARNING_FORMAT("{}: slot '{}' references node '{}' which is not in node_tab", context,
							  spec.key, node_name);
			}
			return;
		}
		if (node_value.is_object()) {
			check_inline_node_value(spec, node_value, context, 0u);
			return;
		}
		OC_WARNING_FORMAT("{}: slot '{}' node reference must be string or object, got {}", context,
					  spec.key, json_type_name(node_value));
		return;
	}
	check_inline_node_value(spec, value, context, spec.dim);
}

void ParamSchema::check_plain_value(const ParamDesc &spec, const DataWrap &value,
									const string &context) const noexcept {
	if (value.is_null()) {
		return;
	}
	bool valid = false;
	switch (spec.type) {
		case ParamType::Bool:
			valid = value.is_boolean();
			break;
		case ParamType::Int:
			valid = value.is_number_integer() || value.is_number_unsigned();
			break;
		case ParamType::Float:
			valid = value.is_number();
			break;
		case ParamType::String:
			valid = value.is_string();
			break;
		case ParamType::Slot:
			valid = true;
			break;
		default:
			break;
	}
	if (!valid) {
		OC_WARNING_FORMAT("{}: param '{}' expected {}, got {}", context, spec.key,
						  expected_type_name(spec.type), json_type_name(value));
	}
}

string ParamSchema::suggest(const string &key) const noexcept {
	if (known_keys_.empty()) {
		return {};
	}
	size_t best_distance = std::numeric_limits<size_t>::max();
	string best_key;
	for (const string &known_key : known_keys_) {
		size_t dist = edit_distance(key, known_key);
		if (dist < best_distance) {
			best_distance = dist;
			best_key = known_key;
		}
	}
	const size_t limit = key.size() <= 4u ? 1u : 2u;
	if (best_distance > limit) {
		return {};
	}
	return best_key;
}

void ParamSchema::validate(const GraphDesc &desc, const string &context) const noexcept {
	const DataWrap params = desc.parameter_set().data();
	if (!params.is_null() && !params.is_object()) {
		OC_WARNING_FORMAT("{}: param block must be object, got {}", context, json_type_name(params));
		return;
	}

	check_required_keys(params, context);
	check_unknown_keys(params, context);

	if (!params.is_object()) {
		return;
	}

	for (const ParamDesc &spec : specs_) {
		if (!params.contains(spec.key)) {
			continue;
		}
		const DataWrap &value = params[spec.key];
		if (spec.type == ParamType::Slot) {
			check_slot_value(desc, spec, value, context);
		} else {
			check_plain_value(spec, value, context);
		}
	}
}

void ParamSchema::validate(const AttrDesc &desc, const string &context) const noexcept {
	const DataWrap params = desc.parameter_set().data();
	if (!params.is_null() && !params.is_object()) {
		OC_WARNING_FORMAT("{}: param block must be object, got {}", context, json_type_name(params));
		return;
	}

	check_required_keys(params, context);
	check_unknown_keys(params, context);

	if (!params.is_object()) {
		return;
	}

	for (const ParamDesc &spec : specs_) {
		if (!params.contains(spec.key)) {
			continue;
		}
		const DataWrap &value = params[spec.key];
		if (spec.type != ParamType::Slot) {
			check_plain_value(spec, value, context);
		}
	}
}

}