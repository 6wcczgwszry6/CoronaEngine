"""Pluggable model selection for LANChat collaboration reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping, Protocol


COLLABORATION_STRUCTURED_PURPOSES = frozenset({
    "planning_artifact_reasoning",
    "program_artifact_reasoning",
    "art_artifact_reasoning",
})


@dataclass(frozen=True)
class CollaborationModelSelection:
    provider_name: str
    model_name: str
    temperature: float = 0.0
    request_timeout: float = 60.0
    output_mode: Literal["text", "json_object"] = "text"
    max_retries: int = 0

    def __post_init__(self) -> None:
        if not str(self.provider_name or "").strip():
            raise ValueError("provider_name is required")
        if not str(self.model_name or "").strip():
            raise ValueError("model_name is required")
        if float(self.request_timeout) <= 0:
            raise ValueError("request_timeout must be positive")
        if self.output_mode not in {"text", "json_object"}:
            raise ValueError("unsupported output_mode")
        if int(self.max_retries) < 0:
            raise ValueError("max_retries must be non-negative")


class CollaborationModelSelector(Protocol):
    def select(self, purpose: str) -> CollaborationModelSelection: ...


class StaticCollaborationModelSelector:
    """Resolve a default model with optional purpose-specific overrides."""

    def __init__(
        self,
        default: CollaborationModelSelection,
        *,
        overrides: Mapping[str, CollaborationModelSelection] | None = None,
    ) -> None:
        if not isinstance(default, CollaborationModelSelection):
            raise TypeError("default must be CollaborationModelSelection")
        normalized: dict[str, CollaborationModelSelection] = {}
        for purpose, selection in dict(overrides or {}).items():
            key = str(purpose or "").strip()
            if not key:
                raise ValueError("override purpose is required")
            if not isinstance(selection, CollaborationModelSelection):
                raise TypeError("override values must be CollaborationModelSelection")
            normalized[key] = selection
        self._default = default
        self._overrides = MappingProxyType(normalized)

    def select(self, purpose: str) -> CollaborationModelSelection:
        return self._overrides.get(str(purpose or "").strip(), self._default)


def default_collaboration_model_selector() -> CollaborationModelSelector:
    text_selection = CollaborationModelSelection(
        provider_name="deepseek",
        model_name="deepseek-v4-pro",
        temperature=0.0,
        request_timeout=60.0,
        output_mode="text",
    )
    structured_selection = CollaborationModelSelection(
        provider_name="deepseek",
        model_name="deepseek-v4-pro",
        temperature=0.0,
        request_timeout=90.0,
        output_mode="json_object",
    )
    return StaticCollaborationModelSelector(
        text_selection,
        overrides={purpose: structured_selection for purpose in COLLABORATION_STRUCTURED_PURPOSES},
    )


__all__ = [
    "CollaborationModelSelection",
    "CollaborationModelSelector",
    "COLLABORATION_STRUCTURED_PURPOSES",
    "StaticCollaborationModelSelector",
    "default_collaboration_model_selector",
]
