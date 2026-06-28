#include <corona/events/acoustics_system_events.h>
#include <corona/kernel/core/i_logger.h>
#include <corona/kernel/event/i_event_bus.h>
#include <corona/kernel/event/i_event_stream.h>
#include <corona/resource/resource_manager.h>
#include <corona/resource/types/audio.h>
#include <corona/systems/acoustics/acoustics_system.h>

namespace Corona::Systems {

bool AcousticsSystem::initialize(Kernel::ISystemContext* ctx) {
    CFW_LOG_NOTICE("AcousticsSystem: Initializing...");

    // --- miniaudio engine 初始化（自带默认设备 + 混音） ---
    ma_result res = ma_engine_init(nullptr, &engine_);
    if (res != MA_SUCCESS) {
        CFW_LOG_ERROR("AcousticsSystem: ma_engine_init failed: {}", static_cast<int>(res));
        return false;
    }
    engine_ready_ = true;

    CFW_LOG_NOTICE("AcousticsSystem: miniaudio engine initialized successfully");

    // --- 订阅播放事件 ---
    if (auto* event_bus = ctx->event_bus()) {
        event_bus->subscribe<Events::PlayAudioEvent>(
            [this](const Events::PlayAudioEvent& ev) {
                std::lock_guard lock(cmd_mutex_);
                pending_plays_.push_back(ev);
            });
        event_bus->subscribe<Events::StopAudioEvent>(
            [this](const Events::StopAudioEvent& ev) {
                std::lock_guard lock(cmd_mutex_);
                pending_stops_.push_back(ev);
            });
        CFW_LOG_NOTICE("AcousticsSystem: subscribed to PlayAudioEvent / StopAudioEvent");
    } else {
        CFW_LOG_WARNING("AcousticsSystem: event_bus not available, audio playback commands disabled");
    }

    return true;
}

void AcousticsSystem::destroy_playback(ActivePlayback& ap) {
    // 顺序关键：先停 sound（解除对 buffer 的引用），再放 buffer，最后 handle 析构。
    if (ap.sound_ready) {
        ma_sound_uninit(&ap.sound);
        ap.sound_ready = false;
    }
    if (ap.buffer_ready) {
        ma_audio_buffer_uninit(&ap.buffer);
        ap.buffer_ready = false;
    }
    // ap.handle 在 ActivePlayback 析构时自动释放（unref + 解锁）。
}

void AcousticsSystem::process_play_request(std::uint64_t resource_id, bool loop) {
    if (!engine_ready_) {
        return;
    }

    // 如果已在播放，先停掉旧实例
    process_stop_request(resource_id);

    // 从资源管理器取 Audio（持有 handle 保活 + 防淘汰，整段播放期间有效）
    auto handle = Resource::ResourceManager::get_instance().acquire_read<Resource::Audio>(resource_id);
    if (!handle) {
        CFW_LOG_ERROR("[AcousticsSystem] play: resource {} not found or not Audio/ready", resource_id);
        return;
    }

    const auto& meta = handle->metadata();
    const auto& pcm = handle->samples();
    if (pcm.empty() || meta.channels <= 0) {
        CFW_LOG_WARNING("[AcousticsSystem] play: resource {} has no/invalid PCM data", resource_id);
        return;
    }

    auto ap = std::make_unique<ActivePlayback>();
    ap->resource_id = resource_id;
    ap->loop = loop;
    ap->handle = std::move(handle);

    const auto& ap_pcm = ap->handle->samples();
    const ma_uint64 frame_count = static_cast<ma_uint64>(ap_pcm.size() / meta.channels);

    // ma_audio_buffer 直接引用资源 PCM（零拷贝）。
    ma_audio_buffer_config cfg = ma_audio_buffer_config_init(
        ma_format_f32,
        static_cast<ma_uint32>(meta.channels),
        frame_count,
        ap_pcm.data(),
        nullptr);

    ma_result res = ma_audio_buffer_init(&cfg, &ap->buffer);
    if (res != MA_SUCCESS) {
        CFW_LOG_ERROR("[AcousticsSystem] play: ma_audio_buffer_init failed: {}", static_cast<int>(res));
        return;
    }
    ap->buffer_ready = true;

    res = ma_sound_init_from_data_source(&engine_, &ap->buffer, 0, nullptr, &ap->sound);
    if (res != MA_SUCCESS) {
        CFW_LOG_ERROR("[AcousticsSystem] play: ma_sound_init_from_data_source failed: {}", static_cast<int>(res));
        destroy_playback(*ap);
        return;
    }
    ap->sound_ready = true;

    ma_sound_set_looping(&ap->sound, loop ? MA_TRUE : MA_FALSE);

    res = ma_sound_start(&ap->sound);
    if (res != MA_SUCCESS) {
        CFW_LOG_ERROR("[AcousticsSystem] play: ma_sound_start failed: {}", static_cast<int>(res));
        destroy_playback(*ap);
        return;
    }

    std::lock_guard lock(playback_mutex_);
    active_playbacks_.push_back(std::move(ap));

    CFW_LOG_INFO("[AcousticsSystem] play started: rid={} {}Hz {}ch loop={}", resource_id, meta.sample_rate, meta.channels, loop);
}

void AcousticsSystem::process_stop_request(std::uint64_t resource_id) {
    std::lock_guard lock(playback_mutex_);
    for (auto it = active_playbacks_.begin(); it != active_playbacks_.end();) {
        if (*it && (*it)->resource_id == resource_id) {
            destroy_playback(**it);
            it = active_playbacks_.erase(it);
        } else {
            ++it;
        }
    }
}

void AcousticsSystem::update() {
    // --- 消费命令队列 ---
    {
        std::lock_guard lock(cmd_mutex_);
        for (const auto& cmd : pending_plays_) {
            process_play_request(cmd.resource_id, cmd.loop);
        }
        pending_plays_.clear();
        for (const auto& cmd : pending_stops_) {
            process_stop_request(cmd.resource_id);
        }
        pending_stops_.clear();
    }

    // --- 监控各播放：loop 由 miniaudio 自动循环；非 loop 播完则清理 ---
    {
        std::lock_guard lock(playback_mutex_);

        auto it = active_playbacks_.begin();
        while (it != active_playbacks_.end()) {
            auto& ap = **it;
            if (!ap.sound_ready) {
                ++it;
                continue;
            }

            // 循环播放永不"结束"，交给 miniaudio。
            if (!ap.loop && ma_sound_at_end(&ap.sound) == MA_TRUE) {
                CFW_LOG_INFO("[AcousticsSystem] playback finished: rid={}", ap.resource_id);
                destroy_playback(ap);
                it = active_playbacks_.erase(it);
            } else {
                ++it;
            }
        }
    }
}

void AcousticsSystem::shutdown() {
    CFW_LOG_NOTICE("AcousticsSystem: Shutting down...");

    {
        std::lock_guard lock(playback_mutex_);
        for (auto& ap : active_playbacks_) {
            if (ap) {
                destroy_playback(*ap);
            }
        }
        active_playbacks_.clear();
    }

    if (engine_ready_) {
        ma_engine_uninit(&engine_);
        engine_ready_ = false;
    }

    CFW_LOG_NOTICE("AcousticsSystem: Shutdown complete");
}

}  // namespace Corona::Systems
