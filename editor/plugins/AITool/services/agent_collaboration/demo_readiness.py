"""Collaboration-side derivation of Runtime-neutral demo readiness inputs."""

from __future__ import annotations

from typing import Sequence

from ..integration_contracts import DemoReadinessRequirement
from .contracts import GameplayEntitySlot


def derive_demo_readiness_requirements(
    slots: Sequence[GameplayEntitySlot],
) -> tuple[DemoReadinessRequirement, ...]:
    """Convert validated gameplay slots without embedding scenario role names."""

    requirements: list[DemoReadinessRequirement] = []
    seen_slot_ids: set[str] = set()
    for slot in slots:
        if not isinstance(slot, GameplayEntitySlot):
            raise TypeError("slots must contain GameplayEntitySlot values")
        slot_id = str(slot.slot_id or "").strip()
        if slot_id in seen_slot_ids:
            raise ValueError(f"duplicate gameplay slot_id: {slot_id}")
        seen_slot_ids.add(slot_id)
        requirements.append(
            DemoReadinessRequirement(
                requirement_id=f"demo.slot.{slot_id}",
                semantic_role=str(slot.semantic_role or ""),
                required_capabilities=tuple(slot.required_capabilities),
                min_count=1,
            )
        )
    if not requirements:
        raise ValueError("at least one gameplay slot is required")
    return tuple(sorted(requirements, key=lambda item: item.requirement_id))


__all__ = ["derive_demo_readiness_requirements"]
