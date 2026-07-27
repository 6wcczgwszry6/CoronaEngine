from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class ModelCallEvidence:
    room_id: str
    message_id: str
    correlation_id: str
    purpose: str
    provider: str
    model: str
    plan_version: int
    dedupe_result: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "purpose": self.purpose,
            "provider": self.provider,
            "model": self.model,
            "plan_version": self.plan_version,
            "dedupe_result": self.dedupe_result,
        }


@dataclass(frozen=True)
class ModelCallClaim:
    allowed: bool
    evidence: ModelCallEvidence


class ModelCallLedger:
    """Per-message model-call budget and audit evidence."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[tuple[str, str], list[ModelCallEvidence]] = {}
        self._summary_emitted: set[tuple[str, str]] = set()

    @staticmethod
    def _key(room_id: str, message_id: str) -> tuple[str, str]:
        return (str(room_id or "default"), str(message_id or ""))

    def claim(
        self,
        *,
        room_id: str,
        message_id: str,
        correlation_id: str,
        purpose: str,
        provider: str,
        model: str,
        plan_version: int = 0,
        max_calls: int = 1,
    ) -> ModelCallClaim:
        key = self._key(room_id, message_id)
        evidence = ModelCallEvidence(
            room_id=key[0],
            message_id=key[1],
            correlation_id=str(correlation_id or ""),
            purpose=str(purpose or "unspecified"),
            provider=str(provider or "unknown"),
            model=str(model or "unknown"),
            plan_version=max(0, int(plan_version or 0)),
            dedupe_result="executed",
        )
        with self._lock:
            records = self._records.setdefault(key, [])
            if len(records) >= max(0, int(max_calls)):
                blocked = replace(evidence, dedupe_result="budget_exhausted")
                return ModelCallClaim(allowed=False, evidence=blocked)
            records.append(evidence)
            return ModelCallClaim(allowed=True, evidence=evidence)

    def summary(self, *, room_id: str, message_id: str, correlation_id: str = "") -> dict[str, Any]:
        key = self._key(room_id, message_id)
        with self._lock:
            records = list(self._records.get(key, ()))
        return {
            "room_id": key[0],
            "message_id": key[1],
            "correlation_id": str(correlation_id or (records[0].correlation_id if records else "")),
            "call_count": len(records),
            "purposes": [record.purpose for record in records],
            "calls": [record.as_dict() for record in records],
        }

    def claim_summary(self, *, room_id: str, message_id: str) -> bool:
        key = self._key(room_id, message_id)
        with self._lock:
            if key in self._summary_emitted:
                return False
            self._summary_emitted.add(key)
            return True


__all__ = ["ModelCallClaim", "ModelCallEvidence", "ModelCallLedger"]
