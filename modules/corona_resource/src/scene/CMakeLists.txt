set(CORONA_RESOURCE_SCENE_IMPORT_SOURCE_FILES
    desc/common.cpp
    desc/node_desc.cpp
    desc/transform_desc.cpp
    desc/attr_desc.cpp
    desc/slot_desc.cpp
    desc/shader_node_desc.cpp
    desc/graph_desc.cpp
    desc/integrator_desc.cpp
    desc/material_desc.cpp
    desc/output_desc.cpp
    desc/pipeline_desc.cpp
    desc/sampler_desc.cpp
    desc/scene_desc.cpp
    desc/scene_element_desc.cpp
)

set(CORONA_RESOURCE_SCENE_IMPORT_HEADER_FILES
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/importer/i_importer.hpp
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/importer/json_importer.hpp
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/json_helper.hpp
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/common.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/node_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/transform_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/graph_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/shader_desc_s.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/integrator_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/material_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/output_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/pipeline_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/sampler_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/scene_desc.h
    ${CORONA_RESOURCE_ROOT}/include/corona/scene/desc/scene_element_desc.h
)

# Create static library
add_library(CoronaResourceScene STATIC
    ${CORONA_RESOURCE_SCENE_IMPORT_SOURCE_FILES}
    ${CORONA_RESOURCE_SCENE_IMPORT_HEADER_FILES}
)
add_library(corona::resource::scene ALIAS CoronaResourceScene)

# Set C++20 standard
target_compile_features(CoronaResourceScene PUBLIC cxx_std_20)

# Configure include directories
target_include_directories(CoronaResourceScene
    PUBLIC
    $<BUILD_INTERFACE:${CORONA_RESOURCE_ROOT}/include>
    $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include/corona_resource/scene>

)

# Link dependencies
target_link_libraries(CoronaResourceScene
    PUBLIC
    stb_headers
    assimp::assimp
    corona::kernel
    nlohmann_json::nlohmann_json
    ktm::ktm
)
