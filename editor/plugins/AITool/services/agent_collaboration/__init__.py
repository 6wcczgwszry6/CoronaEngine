"""Strongly typed, non-runtime contracts for three-role collaboration."""

from .contracts import (
    ARTIFACT_TYPES,
    PRODUCER_ROLES,
    AgentTask,
    ArtifactEnvelope,
    ArtDirection,
    EntityBindingPlan,
    GameDesignBrief,
    GameProjectState,
    GameplayLogicPlan,
    LevelPlan,
    NonExecutableArtifactError,
    SceneCompositionPlan,
    ValidationResult,
    assert_executable,
    validate_artifact_payload,
)

__all__ = [
    "ARTIFACT_TYPES",
    "PRODUCER_ROLES",
    "AgentTask",
    "ArtifactEnvelope",
    "ArtDirection",
    "EntityBindingPlan",
    "GameDesignBrief",
    "GameProjectState",
    "GameplayLogicPlan",
    "LevelPlan",
    "NonExecutableArtifactError",
    "SceneCompositionPlan",
    "ValidationResult",
    "assert_executable",
    "validate_artifact_payload",
]
