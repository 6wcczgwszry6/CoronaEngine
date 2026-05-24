//
// Created by Zero on 2023/6/14.
//

#include "global.h"
#include "pipeline.h"
#include "hotfix/hotfix.h"

namespace vision {

OC_MAKE_INSTANCE_FUNC_DEF_WITH_HOTFIX(Global, s_global)

Global::~Global() {
    RHIContext::destroy_instance();
    ImagePool::destroy_instance();
}

void Global::set_pipeline(SP<Pipeline> pipeline) {
    pipeline_ = pipeline;
}

Pipeline *Global::pipeline() {
    return pipeline_.lock().get();
}

BindlessArray &Global::bindless_array() {
    return pipeline()->bindless_array();
}

void Global::set_scene_path(const fs::path &sp) noexcept {
    scene_path_ = sp;
}

fs::path Global::scene_path() const noexcept {
    return scene_path_;
}

fs::path Global::scene_cache_path() const noexcept {
    return scene_path_ / ".cache";
}

Pipeline *Toolkit::pipeline() noexcept {
    return Global::instance().pipeline();
}

Device &Toolkit::device() noexcept {
    return pipeline()->device();
}

Scene &Toolkit::scene() noexcept {
    return pipeline()->scene();
}

Renderer &Toolkit::renderer() noexcept {
    return pipeline()->renderer();
}

FrameBuffer &Toolkit::frame_buffer() noexcept {
    return *pipeline()->frame_buffer();
}

TSpectrum &Toolkit::spectrum() noexcept {
    return renderer().spectrum();
}

Stream &Toolkit::stream() noexcept {
    return pipeline()->stream();
}

Geometry &Toolkit::geometry() noexcept {
    return scene().geometry();
}

GeometryData *Toolkit::geometry_data() noexcept {
    return geometry().data();
}

}// namespace vision