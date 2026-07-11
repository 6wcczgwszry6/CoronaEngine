#pragma once

#include <algorithm>
#include <cstdint>
#include <future>
#include <iterator>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <utility>
#include <vector>

#include "corona/systems/ui/ui_surface_lifecycle.h"

namespace Corona::Systems::Detail {

/** Thread-safe acknowledgement state for one Display-owned surface. */
class SurfaceLifecycleAcks {
   public:
    using Result = UI::DisplaySurfaceResult;
    using Ticket = UI::SurfaceCompletionTicket;
    using FirstPresentBoundary = std::uint64_t;

    void add_registration(const std::optional<Ticket>& ticket) {
        add_ticket(ticket, registration_outcome_, registration_tickets_);
    }

    [[nodiscard]] FirstPresentBoundary add_first_present(
        const std::optional<Ticket>& ticket) {
        std::optional<Outcome> outcome;
        FirstPresentBoundary boundary = 0;
        {
            std::lock_guard lock(mutex_);
            boundary = first_present_sequence_;
            if (first_present_terminal_outcome_) {
                outcome = first_present_terminal_outcome_;
            } else if (ticket) {
                boundary = ++first_present_sequence_;
                first_present_tickets_.push_back({boundary, *ticket});
            }
        }
        if (ticket && outcome) {
            complete(*ticket, *outcome);
        }
        return boundary;
    }

    void registration_succeeded() {
        complete_registration(Result::Status::Succeeded, {});
    }

    void registration_failed(std::string message) {
        std::vector<Ticket> registration_tickets;
        std::vector<Ticket> first_present_tickets;
        Outcome outcome{Result::Status::Failed, std::move(message)};
        {
            std::lock_guard lock(mutex_);
            if (!registration_outcome_) {
                registration_outcome_ = outcome;
                registration_tickets.swap(registration_tickets_);
            }
            if (!first_present_terminal_outcome_) {
                first_present_terminal_outcome_ = outcome;
                take_first_present_tickets(first_present_tickets);
            }
        }
        complete_all(registration_tickets, outcome);
        complete_all(first_present_tickets, outcome);
    }

    /** A false value is a skipped/no-op compose and is not a first present. */
    void present_completed(bool presented, FirstPresentBoundary boundary) {
        if (!presented || boundary == 0) {
            return;
        }

        std::vector<Ticket> tickets;
        {
            std::lock_guard lock(mutex_);
            if (first_present_terminal_outcome_) {
                return;
            }
            auto first_later_ticket = std::stable_partition(
                first_present_tickets_.begin(),
                first_present_tickets_.end(),
                [boundary](const SequencedTicket& pending) {
                    return pending.boundary <= boundary;
                });
            tickets.reserve(static_cast<std::size_t>(
                std::distance(first_present_tickets_.begin(),
                              first_later_ticket)));
            for (auto it = first_present_tickets_.begin();
                 it != first_later_ticket;
                 ++it) {
                tickets.push_back(it->ticket);
            }
            first_present_tickets_.erase(first_present_tickets_.begin(),
                                         first_later_ticket);
        }
        complete_all(tickets, {Result::Status::Succeeded, {}});
    }

    void present_failed(std::string message) {
        complete_first_present(Result::Status::Failed, std::move(message));
    }

    /**
     * Records a removal without certifying safety. Forward work becomes
     * impossible immediately, while removal remains pending until
     * removal_succeeded() is called after resource destruction.
     */
    void removal_requested(
        const std::optional<Ticket>& ticket,
        std::shared_ptr<std::promise<void>> done) {
        std::optional<Outcome> completed_removal;
        std::vector<Ticket> registration_tickets;
        std::vector<Ticket> first_present_tickets;
        const Outcome cancelled{Result::Status::Cancelled,
                                "surface removal requested"};
        {
            std::lock_guard lock(mutex_);
            if (removal_outcome_) {
                completed_removal = removal_outcome_;
            } else {
                if (ticket) {
                    removal_tickets_.push_back(*ticket);
                }
                if (done &&
                    std::find(removal_promises_.begin(),
                              removal_promises_.end(),
                              done) == removal_promises_.end()) {
                    removal_promises_.push_back(done);
                }
            }

            if (!registration_outcome_) {
                registration_outcome_ = cancelled;
                registration_tickets.swap(registration_tickets_);
            }
            if (!first_present_terminal_outcome_) {
                first_present_terminal_outcome_ = cancelled;
                take_first_present_tickets(first_present_tickets);
            }
        }

        complete_all(registration_tickets, cancelled);
        complete_all(first_present_tickets, cancelled);
        if (completed_removal) {
            if (ticket) {
                complete(*ticket, *completed_removal);
            }
            fulfill(done);
        }
    }

    void fail_forward(std::string message) {
        complete_forward(Result::Status::Failed, std::move(message));
    }

    void cancel_forward(std::string message) {
        complete_forward(Result::Status::Cancelled, std::move(message));
    }

    /** Called only after the displayer and composite resources are erased. */
    void removal_succeeded() {
        std::vector<Ticket> tickets;
        std::vector<std::shared_ptr<std::promise<void>>> promises;
        const Outcome outcome{Result::Status::Succeeded, {}};
        {
            std::lock_guard lock(mutex_);
            if (removal_outcome_) {
                return;
            }
            removal_outcome_ = outcome;
            tickets.swap(removal_tickets_);
            promises.swap(removal_promises_);
        }
        complete_all(tickets, outcome);
        for (const auto& promise : promises) {
            fulfill(promise);
        }
    }

   private:
    struct Outcome {
        Result::Status status;
        std::string message;
    };

    struct SequencedTicket {
        FirstPresentBoundary boundary;
        Ticket ticket;
    };

    void take_first_present_tickets(std::vector<Ticket>& destination) {
        destination.reserve(destination.size() + first_present_tickets_.size());
        for (const auto& pending : first_present_tickets_) {
            destination.push_back(pending.ticket);
        }
        first_present_tickets_.clear();
    }

    void add_ticket(const std::optional<Ticket>& ticket,
                    const std::optional<Outcome>& stored_outcome,
                    std::vector<Ticket>& pending) {
        if (!ticket) {
            return;
        }

        std::optional<Outcome> outcome;
        {
            std::lock_guard lock(mutex_);
            if (stored_outcome) {
                outcome = stored_outcome;
            } else {
                pending.push_back(*ticket);
            }
        }
        if (outcome) {
            complete(*ticket, *outcome);
        }
    }

    void complete_registration(Result::Status status, std::string message) {
        std::vector<Ticket> tickets;
        Outcome outcome{status, std::move(message)};
        {
            std::lock_guard lock(mutex_);
            if (registration_outcome_) {
                return;
            }
            registration_outcome_ = outcome;
            tickets.swap(registration_tickets_);
        }
        complete_all(tickets, outcome);
    }

    void complete_first_present(Result::Status status, std::string message) {
        std::vector<Ticket> tickets;
        Outcome outcome{status, std::move(message)};
        {
            std::lock_guard lock(mutex_);
            if (first_present_terminal_outcome_) {
                return;
            }
            first_present_terminal_outcome_ = outcome;
            take_first_present_tickets(tickets);
        }
        complete_all(tickets, outcome);
    }

    void complete_forward(Result::Status status, std::string message) {
        std::vector<Ticket> registration_tickets;
        std::vector<Ticket> first_present_tickets;
        Outcome outcome{status, std::move(message)};
        {
            std::lock_guard lock(mutex_);
            if (!registration_outcome_) {
                registration_outcome_ = outcome;
                registration_tickets.swap(registration_tickets_);
            }
            if (!first_present_terminal_outcome_) {
                first_present_terminal_outcome_ = outcome;
                take_first_present_tickets(first_present_tickets);
            }
        }
        complete_all(registration_tickets, outcome);
        complete_all(first_present_tickets, outcome);
    }

    static void complete(const Ticket& ticket, const Outcome& outcome) {
        ticket.try_complete(outcome.status, outcome.message);
    }

    static void complete_all(const std::vector<Ticket>& tickets,
                             const Outcome& outcome) {
        for (const auto& ticket : tickets) {
            complete(ticket, outcome);
        }
    }

    static void fulfill(const std::shared_ptr<std::promise<void>>& promise) {
        if (!promise) {
            return;
        }
        try {
            promise->set_value();
        } catch (const std::future_error&) {
            // Duplicate legacy events may share an already-satisfied promise.
        }
    }

    std::mutex mutex_;
    std::optional<Outcome> registration_outcome_;
    std::optional<Outcome> first_present_terminal_outcome_;
    std::optional<Outcome> removal_outcome_;
    std::vector<Ticket> registration_tickets_;
    FirstPresentBoundary first_present_sequence_ = 0;
    std::vector<SequencedTicket> first_present_tickets_;
    std::vector<Ticket> removal_tickets_;
    std::vector<std::shared_ptr<std::promise<void>>> removal_promises_;
};

}  // namespace Corona::Systems::Detail
