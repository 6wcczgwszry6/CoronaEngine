/**
 * @file media_example.cpp
 * @brief Demonstrates FFmpeg-backed video/audio import & export via corona_resource.
 *
 * Video is imported as metadata + an on-demand decoder (frames are pulled one
 * at a time as RGBA). Audio is imported fully decoded to interleaved float32
 * PCM. Both can be exported (video = transcode, audio = re-encode) by extension.
 *
 * Usage:
 *   MediaExample <input.(mp4|mkv|...)> [output.mp4]      # video
 *   MediaExample <input.(wav|mp3|flac|...)> [output.wav] # audio
 *
 * With no arguments the example only prints a short usage note, because it has
 * no bundled media assets to operate on.
 */

#include <cstdint>
#include <filesystem>
#include <iostream>
#include <string>

#include "corona/resource/resource_manager.h"
#include "corona/resource/types/audio.h"
#include "corona/resource/types/video.h"

using namespace Corona::Resource;

namespace {

bool is_audio_ext(const std::filesystem::path& p) {
    auto e = p.extension().string();
    for (auto& c : e) c = static_cast<char>(::tolower(c));
    return e == ".wav" || e == ".mp3" || e == ".ogg" || e == ".flac" || e == ".aac" || e == ".m4a";
}

void demo_video(ResourceManager& mgr, const std::filesystem::path& in,
                const std::filesystem::path& out) {
    std::cout << "\n=== Video ===\n";
    TResourceID rid = mgr.import_sync(in);
    if (rid == IResource::INVALID_UID) {
        std::cout << "Failed to import video: " << in << "\n";
        return;
    }

    {
        // Decoding advances internal decoder state, so it needs a write handle.
        auto handle = mgr.acquire_write<Video>(rid);
        if (!handle) {
            std::cout << "Could not acquire video resource\n";
            return;
        }
        const auto& m = handle->metadata();
        std::cout << "  resolution : " << m.width << "x" << m.height << "\n"
                  << "  duration   : " << m.duration_seconds << " s\n"
                  << "  fps        : " << m.fps << "\n"
                  << "  frames     : " << m.frame_count << "\n"
                  << "  codec      : " << m.codec_name << "\n"
                  << "  bit_rate   : " << m.bit_rate << " bps\n";

        // Decode the first frame and a frame near the middle.
        if (auto f = handle->decode_next_frame()) {
            std::cout << "  first frame: " << f->width << "x" << f->height
                      << " @ " << f->pts_seconds << "s (" << f->rgba.size() << " bytes RGBA)\n";
        }
        if (m.duration_seconds > 0.0) {
            if (auto f = handle->decode_frame_at(m.duration_seconds / 2.0)) {
                std::cout << "  mid frame  : @ " << f->pts_seconds << "s\n";
            }
        }
    }

    if (!out.empty()) {
        std::cout << "  transcoding -> " << out << " ...\n";
        bool ok = mgr.export_sync(rid, out);
        std::cout << "  export " << (ok ? "succeeded" : "FAILED") << "\n";
    }
}

void demo_audio(ResourceManager& mgr, const std::filesystem::path& in,
                const std::filesystem::path& out) {
    std::cout << "\n=== Audio ===\n";
    TResourceID rid = mgr.import_sync(in);
    if (rid == IResource::INVALID_UID) {
        std::cout << "Failed to import audio: " << in << "\n";
        return;
    }

    {
        auto handle = mgr.acquire_read<Audio>(rid);
        if (!handle) {
            std::cout << "Could not acquire audio resource\n";
            return;
        }
        const auto& m = handle->metadata();
        std::cout << "  sample_rate: " << m.sample_rate << " Hz\n"
                  << "  channels   : " << m.channels << "\n"
                  << "  frames     : " << m.frame_count << " (per channel)\n"
                  << "  duration   : " << m.duration_seconds << " s\n"
                  << "  codec      : " << m.codec_name << "\n"
                  << "  samples    : " << handle->samples().size() << " floats (interleaved)\n";
    }

    if (!out.empty()) {
        std::cout << "  encoding -> " << out << " ...\n";
        bool ok = mgr.export_sync(rid, out);
        std::cout << "  export " << (ok ? "succeeded" : "FAILED") << "\n";
    }
}

}  // namespace

int main(int argc, char** argv) {
    auto& mgr = ResourceManager::get_instance();
    mgr.register_parser<VideoParser>();
    mgr.register_parser<AudioParser>();

    if (argc < 2) {
        std::cout << "Usage:\n"
                  << "  " << argv[0] << " <input.(mp4|mkv|mov|...)> [output.mp4]   # video\n"
                  << "  " << argv[0] << " <input.(wav|mp3|flac|...)> [output.wav]  # audio\n"
                  << "\nNo input provided; nothing to do.\n";
        return 0;
    }

    std::filesystem::path in = argv[1];
    std::filesystem::path out = (argc >= 3) ? std::filesystem::path(argv[2]) : std::filesystem::path{};

    if (!std::filesystem::exists(in)) {
        std::cout << "Input file not found: " << in << "\n";
        return 1;
    }

    if (is_audio_ext(in)) {
        demo_audio(mgr, in, out);
    } else {
        demo_video(mgr, in, out);
    }

    return 0;
}
