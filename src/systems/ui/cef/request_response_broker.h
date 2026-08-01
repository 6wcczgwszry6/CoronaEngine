#pragma once

#include <nlohmann/json.hpp>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace Corona::Systems::UI {

struct CefRequestContext {
    std::string request_id;
    int browser_id{0};
    std::string frame_id;
    std::uintptr_t camera_handle{0};
    std::string scene_id;
};

struct CefResponse {
    std::string status;
    nlohmann::json payload = nlohmann::json::object();
};

class CefRequestResponseBroker {
public:
    using Clock = std::chrono::steady_clock;
    using Dispatcher = std::function<void(const CefRequestContext&, const CefResponse&)>;

    static constexpr std::chrono::milliseconds kDefaultTimeout{500};

    bool register_request(CefRequestContext context,
                          Dispatcher dispatcher = {},
                          Clock::time_point now = Clock::now());
    bool complete(std::string_view request_id, CefResponse response);
    bool complete(std::string_view request_id,
                  std::uintptr_t camera_handle,
                  std::string_view scene_id,
                  CefResponse response);
    bool cancel(std::string_view request_id);
    std::size_t cancel_browser(int browser_id);
    std::size_t expire(Clock::time_point now = Clock::now());
    std::size_t dispatch();
    void set_dispatcher(Dispatcher dispatcher);
    [[nodiscard]] std::size_t pending_count() const;

private:
    struct Pending {
        CefRequestContext context;
        Dispatcher dispatcher;
        Clock::time_point deadline;
    };

    struct Completed {
        CefRequestContext context;
        Dispatcher dispatcher;
        CefResponse response;
    };

    mutable std::mutex mutex_;
    std::unordered_map<std::string, Pending> pending_;
    std::vector<Completed> completed_;
    Dispatcher default_dispatcher_;

    static std::string make_key(const CefRequestContext& context);
};

CefRequestResponseBroker& cef_request_response_broker();

}  // namespace Corona::Systems::UI
