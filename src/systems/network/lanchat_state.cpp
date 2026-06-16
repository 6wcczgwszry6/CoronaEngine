#include <corona/systems/network/lanchat_state.h>

#include <algorithm>
#include <cctype>
#include <cmath>

namespace Corona::Network {
namespace {

constexpr size_t kAgentTriggerHistoryLimit = 20;

bool is_mention_boundary(char ch) {
    const auto uch = static_cast<unsigned char>(ch);
    if (uch >= 0x80) {
        return true;
    }
    if (std::isspace(uch) != 0) {
        return true;
    }
    switch (ch) {
    case '.':
    case ',':
    case ';':
    case ':':
    case '!':
    case '?':
    case ')':
    case ']':
    case '}':
    case '"':
    case '\'':
        return true;
    default:
        return false;
    }
}

bool mentions_agent(const std::string& text, const std::string& agent_name) {
    if (agent_name.empty()) {
        return false;
    }

    const std::string needle = "@" + agent_name;
    size_t pos = text.find(needle);
    while (pos != std::string::npos) {
        const size_t end = pos + needle.size();
        if (end >= text.size() || is_mention_boundary(text[end])) {
            return true;
        }
        pos = text.find(needle, pos + 1);
    }
    return false;
}

}  // namespace

bool LanChatState::open_room(const std::string& room_id,
                             const std::string& local_peer_id,
                             const std::string& host_name) {
    close_room();
    room_id_ = room_id;
    next_seq_ = 1;
    return join_member(local_peer_id, host_name).ok;
}

void LanChatState::close_room() {
    room_id_.clear();
    next_seq_ = 1;
    members_.clear();
    history_.clear();
    agents_.clear();
    {
        std::lock_guard<std::mutex> lock(agent_trigger_mutex_);
        pending_agent_triggers_.clear();
        triggered_agent_keys_.clear();
    }
    locks_.clear();
    intents_.clear();
}

LanChatResult LanChatState::join_member(const std::string& member_id,
                                        const std::string& nickname,
                                        uint64_t now_ms) {
    if (member_id.empty()) {
        return {false, "member_id is required"};
    }

    auto it = find_member(member_id);
    if (it == members_.end()) {
        members_.push_back({member_id, nickname, "online", now_ms});
    } else {
        it->nickname = nickname;
        it->status = "online";
        it->last_seen_ms = now_ms;
    }
    return {true, {}};
}

LanChatResult LanChatState::leave_member(const std::string& member_id) {
    auto it = find_member(member_id);
    if (it == members_.end()) {
        return {false, "member not found"};
    }
    members_.erase(it);
    return {true, {}};
}

LanChatMessageResult LanChatState::record_message(const std::string& message_id,
                                                  const std::string& sender_id,
                                                  const std::string& sender_name,
                                                  const std::string& text,
                                                  uint64_t timestamp_ms) {
    if (message_id.empty()) {
        return {false, {}, "message_id is required"};
    }
    if (has_message_id(message_id)) {
        return {false, {}, "duplicate message_id"};
    }

    LanChatMessage message;
    message.message_id = message_id;
    message.sender_id = sender_id;
    message.sender_name = sender_name;
    message.room_id = room_id_;
    message.text = text;
    message.seq = next_seq_++;
    message.timestamp_ms = timestamp_ms;

    history_.push_back(message);
    return {true, message, {}};
}

LanChatMessageResult LanChatState::apply_remote_message(const LanChatMessage& message) {
    if (message.message_id.empty()) {
        return {false, {}, "message_id is required"};
    }
    if (has_message_id(message.message_id)) {
        return {false, {}, "duplicate message_id"};
    }

    history_.push_back(message);
    std::sort(history_.begin(), history_.end(), [](const auto& lhs, const auto& rhs) {
        if (lhs.seq != rhs.seq) {
            return lhs.seq < rhs.seq;
        }
        return lhs.message_id < rhs.message_id;
    });
    next_seq_ = std::max(next_seq_, message.seq + 1);
    return {true, message, {}};
}

LanChatResult LanChatState::register_agent(const std::string& agent_id,
                                           const std::string& name,
                                           const std::string& persona,
                                           const std::string& owner_id) {
    if (agent_id.empty()) {
        return {false, "agent_id is required"};
    }

    auto it = find_agent(agent_id);
    auto duplicate_name = std::find_if(agents_.begin(), agents_.end(), [&](const auto& agent) {
        return agent.agent_id != agent_id && agent.name == name;
    });
    if (duplicate_name != agents_.end()) {
        return {false, "agent name already exists"};
    }

    if (it == agents_.end()) {
        agents_.push_back({agent_id, name, persona, owner_id});
    } else {
        it->name = name;
        it->persona = persona;
        it->owner_id = owner_id;
    }
    return {true, {}};
}

void LanChatState::enqueue_agent_triggers_for_message(const LanChatMessage& message,
                                                      const std::string& local_peer_id,
                                                      bool is_agent_reply) {
    if (is_agent_reply || message.message_id.empty() || local_peer_id.empty()) {
        return;
    }

    for (const auto& agent : agents_) {
        if (agent.owner_id != local_peer_id || agent.agent_id == message.sender_id) {
            continue;
        }
        if (!mentions_agent(message.text, agent.name)) {
            continue;
        }

        LanChatAgentTrigger trigger;
        trigger.trigger_id = message.message_id + ":" + agent.agent_id;
        trigger.message_id = message.message_id;
        trigger.room_id = message.room_id;
        trigger.sender_id = message.sender_id;
        trigger.sender_name = message.sender_name;
        trigger.agent_id = agent.agent_id;
        trigger.agent_name = agent.name;
        trigger.persona = agent.persona;
        trigger.text = message.text;

        const size_t start = history_.size() > kAgentTriggerHistoryLimit
            ? history_.size() - kAgentTriggerHistoryLimit
            : 0;
        trigger.history.assign(history_.begin() + static_cast<std::ptrdiff_t>(start),
                               history_.end());

        std::lock_guard<std::mutex> lock(agent_trigger_mutex_);
        if (!triggered_agent_keys_.insert(trigger.trigger_id).second) {
            continue;
        }
        pending_agent_triggers_.push_back(std::move(trigger));
    }
}

std::optional<LanChatAgentTrigger> LanChatState::pop_agent_trigger() {
    std::lock_guard<std::mutex> lock(agent_trigger_mutex_);
    if (pending_agent_triggers_.empty()) {
        return std::nullopt;
    }
    auto trigger = std::move(pending_agent_triggers_.front());
    pending_agent_triggers_.pop_front();
    return trigger;
}

LanChatResult LanChatState::remove_agent(const std::string& agent_id) {
    auto it = find_agent(agent_id);
    if (it == agents_.end()) {
        return {false, "agent not found"};
    }
    agents_.erase(it);
    return {true, {}};
}

LanChatResult LanChatState::lock_object(const std::string& object_id,
                                        const std::string& user_id,
                                        const std::string& operation,
                                        uint64_t now_ms) {
    if (object_id.empty() || user_id.empty()) {
        return {false, "object_id and user_id are required"};
    }

    auto it = find_lock(object_id);
    if (it != locks_.end() && it->expires_at_ms > now_ms && it->user_id != user_id) {
        return {false, "object already locked"};
    }
    if (it == locks_.end()) {
        locks_.push_back({object_id, user_id, operation, now_ms + kLockTtlMs});
    } else {
        it->user_id = user_id;
        it->operation = operation;
        it->expires_at_ms = now_ms + kLockTtlMs;
    }
    return {true, {}};
}

LanChatResult LanChatState::unlock_object(const std::string& object_id,
                                          const std::string& user_id) {
    auto it = find_lock(object_id);
    if (it == locks_.end()) {
        return {false, "object is not locked"};
    }
    if (it->user_id != user_id) {
        return {false, "lock owned by another user"};
    }
    locks_.erase(it);
    return {true, {}};
}

std::string LanChatState::locked_by(const std::string& object_id, uint64_t now_ms) {
    auto it = find_lock(object_id);
    if (it == locks_.end()) {
        return {};
    }
    if (it->expires_at_ms <= now_ms) {
        locks_.erase(it);
        return {};
    }
    return it->user_id;
}

void LanChatState::broadcast_intent(const std::string& user_id,
                                    const std::string& tooltip,
                                    const std::array<float, 3>& position,
                                    const std::string& status,
                                    uint64_t now_ms) {
    auto it = find_intent(user_id);
    if (it == intents_.end()) {
        intents_.push_back({user_id, tooltip, position, status, now_ms});
    } else {
        it->tooltip = tooltip;
        it->position = position;
        it->status = status;
        it->timestamp_ms = now_ms;
    }
}

std::string LanChatState::check_preview_collision(const std::string& user_id,
                                                  const std::array<float, 3>& position,
                                                  float delta,
                                                  uint64_t now_ms) {
    intents_.erase(std::remove_if(intents_.begin(), intents_.end(), [now_ms](const auto& intent) {
                       return intent.timestamp_ms + kIntentTtlMs <= now_ms;
                   }),
                   intents_.end());

    const float max_distance_sq = delta * delta;
    for (const auto& intent : intents_) {
        if (intent.user_id == user_id) {
            continue;
        }
        const float dx = intent.position[0] - position[0];
        const float dz = intent.position[2] - position[2];
        if (dx * dx + dz * dz <= max_distance_sq) {
            return intent.user_id;
        }
    }
    return {};
}

bool LanChatState::has_message_id(const std::string& message_id) const {
    return std::any_of(history_.begin(), history_.end(), [&](const auto& message) {
        return message.message_id == message_id;
    });
}

std::vector<LanChatMember>::iterator LanChatState::find_member(const std::string& member_id) {
    return std::find_if(members_.begin(), members_.end(), [&](const auto& member) {
        return member.member_id == member_id;
    });
}

std::vector<LanChatAgent>::iterator LanChatState::find_agent(const std::string& agent_id) {
    return std::find_if(agents_.begin(), agents_.end(), [&](const auto& agent) {
        return agent.agent_id == agent_id;
    });
}

std::vector<LanChatState::ObjectLock>::iterator LanChatState::find_lock(const std::string& object_id) {
    return std::find_if(locks_.begin(), locks_.end(), [&](const auto& lock) {
        return lock.object_id == object_id;
    });
}

std::vector<LanChatIntent>::iterator LanChatState::find_intent(const std::string& user_id) {
    return std::find_if(intents_.begin(), intents_.end(), [&](const auto& intent) {
        return intent.user_id == user_id;
    });
}

}  // namespace Corona::Network
