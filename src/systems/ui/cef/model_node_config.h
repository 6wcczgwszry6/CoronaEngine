#pragma once

#include <corona/systems/geometry/model_node_state.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace Corona::Systems::UI::ModelNodeConfig {
using json=nlohmann::json;
inline bool finite3(const json& value) { if(!value.is_array()||value.size()!=3)return false; for(const auto& v:value) if(!v.is_number()||!std::isfinite(v.get<float>()))return false; return true; }
inline json fields(const json& input) {
    if(!input.is_object()) throw std::invalid_argument("Model node fields must be an object"); json out=json::object();
    for(const char* key:{"position","rotation","scale"}) if(input.contains(key)) { if(!finite3(input.at(key))) throw std::invalid_argument(std::string("Invalid model node ")+key); out[key]=input.at(key); }
    if(input.contains("visible")) { if(!input.at("visible").is_boolean()) throw std::invalid_argument("Invalid model node visible"); out["visible"]=input.at("visible"); }
    return out;
}
inline json normalize(const json& values) {
    if(!values.is_array()) throw std::invalid_argument("Model node overrides must be an array"); std::map<std::uint32_t,json> sorted;
    for(const auto& value:values) { if(!value.is_object()||!value.contains("node_index")||!value.at("node_index").is_number_unsigned()||!value.contains("node_path")||!value.at("node_path").is_string()||value.at("node_path").get<std::string>().empty()) throw std::invalid_argument("Invalid model node override identity"); auto f=fields(value); f["node_index"]=value.at("node_index"); f["node_path"]=value.at("node_path"); const auto i=f.at("node_index").get<std::uint32_t>(); if(auto it=sorted.find(i);it!=sorted.end() && it->second.at("node_path")!=f.at("node_path"))throw std::invalid_argument("Duplicate model node index uses another path"); sorted[i]=std::move(f); }
    json out=json::array();for(auto& [_,v]:sorted)out.push_back(std::move(v));return out;
}
inline json merge(json values,std::uint32_t index,const std::string& path,const json& patch) { values=normalize(values); bool found=false;for(auto& v:values)if(v.at("node_index").get<std::uint32_t>()==index){v["node_path"]=path;for(auto it=patch.begin();it!=patch.end();++it)v[it.key()]=it.value();found=true;}if(!found){auto v=fields(patch);v["node_index"]=index;v["node_path"]=path;values.push_back(std::move(v));}return normalize(values); }
inline std::pair<json,json> partition(const json& values,const std::string& saved,const std::string& current,const json& nodes) { json active=json::array(), unmatched=json::array(); if(saved!=current){if(!values.empty()) unmatched.push_back({{"resource",saved},{"overrides",values}});return {active,unmatched};}for(const auto& v:normalize(values)){bool found=false;for(const auto& n:nodes)if(n.at("node_index")==v.at("node_index")&&n.at("node_path")==v.at("node_path")){found=true;break;}if(found)active.push_back(v);else unmatched.push_back({{"resource",saved},{"overrides",json::array({v})}});}return {active,unmatched}; }
}
