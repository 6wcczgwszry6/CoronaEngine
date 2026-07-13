from __future__ import annotations

import unittest

from editor.plugins.AITool.services.agent_collaboration import (
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
    assert_executable,
)


def _brief(*, goal: str = "Build a cooperative treasure room") -> GameDesignBrief:
    return GameDesignBrief(
        project_goal=goal,
        player_experience=("explore", "cooperate"),
        core_rules=("host confirms world writes",),
        acceptance_criteria=("two players can inspect the same world version",),
    )


def _envelope(**overrides) -> ArtifactEnvelope:
    values = {
        "artifact_id": "artifact-brief-v1",
        "artifact_type": "GameDesignBrief",
        "version": 1,
        "producer_role": "planning",
        "source_task_id": "task-plan-1",
        "base_project_version": 1,
        "base_world_version": 0,
        "dependencies": (),
        "snapshot_source": "none",
        "non_executable": True,
        "status": "validated",
        "payload": _brief(),
    }
    values.update(overrides)
    return ArtifactEnvelope(**values)


class AgentCollaborationContractTests(unittest.TestCase):
    def test_artifact_hash_is_deterministic_and_payload_is_deeply_immutable(self) -> None:
        first = _envelope(payload={
            "acceptance_criteria": ["same world"],
            "core_rules": ["host confirms"],
            "player_experience": ["explore"],
            "project_goal": "treasure room",
        })
        second = _envelope(payload={
            "project_goal": "treasure room",
            "player_experience": ["explore"],
            "core_rules": ["host confirms"],
            "acceptance_criteria": ["same world"],
        })

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertTrue(first.validation_result.valid)
        with self.assertRaises(TypeError):
            first.payload["project_goal"] = "mutated"  # type: ignore[index]
        exported = first.as_dict()
        exported["payload"]["project_goal"] = "local mutation"
        self.assertEqual(first.as_dict()["payload"]["project_goal"], "treasure room")

    def test_payload_change_changes_content_hash(self) -> None:
        first = _envelope(payload=_brief(goal="first goal"))
        second = _envelope(payload=_brief(goal="second goal"))

        self.assertNotEqual(first.content_hash, second.content_hash)

    def test_validation_result_is_computed_and_invalid_payload_cannot_claim_validated(self) -> None:
        artifact = _envelope(payload={"project_goal": "missing lists"})

        self.assertFalse(artifact.validation_result.valid)
        self.assertEqual(artifact.status, "invalid")
        self.assertIn("core_rules:required_nonempty_text_list", artifact.validation_result.errors)
        with self.assertRaises(TypeError):
            ArtifactEnvelope(  # type: ignore[call-arg]
                artifact_id="forged",
                artifact_type="GameDesignBrief",
                version=1,
                producer_role="planning",
                source_task_id="task-forged",
                base_project_version=1,
                base_world_version=0,
                payload=_brief(),
                validation_result={"valid": True},
            )

    def test_mock_artifact_is_constructible_for_audit_but_never_executable(self) -> None:
        artifact = _envelope(snapshot_source="mock", non_executable=True)

        self.assertEqual(artifact.snapshot_source, "mock")
        with self.assertRaises(NonExecutableArtifactError):
            assert_executable(artifact)
        with self.assertRaises(NonExecutableArtifactError):
            _envelope(snapshot_source="mock", non_executable=False)

    def test_validated_production_artifact_can_pass_future_execution_boundary(self) -> None:
        artifact = _envelope(
            snapshot_source="runtime",
            non_executable=False,
            status="validated",
        )

        assert_executable(artifact)

    def test_non_executable_or_invalid_artifact_is_rejected(self) -> None:
        with self.assertRaises(NonExecutableArtifactError):
            assert_executable(_envelope())
        with self.assertRaises(NonExecutableArtifactError):
            assert_executable(
                _envelope(
                    snapshot_source="runtime",
                    non_executable=False,
                    payload={"project_goal": "invalid"},
                )
            )

    def test_all_six_first_stage_payload_dtos_validate_through_envelope(self) -> None:
        payloads = (
            ("GameDesignBrief", "planning", _brief()),
            (
                "LevelPlan",
                "planning",
                LevelPlan(
                    level_goal="Find the shared treasure",
                    zones=("entry", "vault"),
                    progression=("enter", "solve", "claim"),
                    acceptance_criteria=("both players reach the vault",),
                ),
            ),
            (
                "ArtDirection",
                "art",
                ArtDirection(
                    style_keywords=("warm", "mysterious"),
                    palette=("amber", "deep blue"),
                    lighting=("warm lanterns",),
                    avoid_keywords=("horror",),
                ),
            ),
            (
                "SceneCompositionPlan",
                "art",
                SceneCompositionPlan(
                    scene_type="indoor_room",
                    environment_requirements=("room_box", "room_floor"),
                    entity_requirements=("treasure_chest", "table"),
                    layout_rules=("keep the main path clear",),
                ),
            ),
            (
                "GameplayLogicPlan",
                "program",
                GameplayLogicPlan(
                    states=("searching", "complete"),
                    triggers=("treasure_found",),
                    rules=("host owns authoritative state",),
                    win_conditions=("treasure found",),
                    lose_conditions=("time expired",),
                ),
            ),
            (
                "EntityBindingPlan",
                "program",
                EntityBindingPlan(
                    snapshot_plan_id="plan-fixture",
                    snapshot_version=3,
                    bindings=({"entity_id": "entity-1", "semantic_role": "treasure_chest"},),
                ),
            ),
        )
        artifacts: dict[str, ArtifactEnvelope] = {}
        for artifact_type, role, payload in payloads:
            with self.subTest(artifact_type=artifact_type):
                artifact = ArtifactEnvelope(
                    artifact_id=f"artifact-{artifact_type}-v1",
                    artifact_type=artifact_type,
                    version=1,
                    producer_role=role,
                    source_task_id=f"task-{artifact_type}-1",
                    base_project_version=1,
                    base_world_version=3 if artifact_type == "EntityBindingPlan" else 0,
                    snapshot_source="mock" if artifact_type == "EntityBindingPlan" else "none",
                    non_executable=True,
                    payload=payload,
                )
                self.assertTrue(artifact.validation_result.valid)
                artifacts[artifact_type] = artifact

        binding = artifacts["EntityBindingPlan"]
        with self.assertRaises(NonExecutableArtifactError):
            assert_executable(binding)

    def test_project_and_task_contracts_validate_without_runtime_dependencies(self) -> None:
        project = GameProjectState(
            project_id="project-1",
            project_version=1,
            room_id="room-1",
            artifact_refs=("artifact-b", "artifact-a", "artifact-a"),
        )
        task = AgentTask(
            task_id="task-plan-1",
            assigned_role="planning",
            objective="Create a validated design brief",
            input_artifact_refs=(),
            output_types=("LevelPlan", "GameDesignBrief"),
            depends_on=(),
            acceptance_criteria=("schema valid",),
            capability_set=("artifact.write",),
        )

        self.assertEqual(project.artifact_refs, ("artifact-a", "artifact-b"))
        self.assertEqual(task.output_types, ("GameDesignBrief", "LevelPlan"))
        self.assertEqual(task.status, "pending")
        with self.assertRaises(ValueError):
            GameProjectState(
                project_id="project-invalid",
                project_version=1,
                room_id="room-1",
                validation_status="pretend-valid",
            )
        with self.assertRaises(TypeError):
            _envelope(dependencies="artifact-not-a-sequence")
        with self.assertRaises(ValueError):
            AgentTask(
                task_id="task-invalid",
                assigned_role="planning",
                objective="Missing acceptance criteria",
                input_artifact_refs=(),
                output_types=("GameDesignBrief",),
                depends_on=(),
                acceptance_criteria=(),
                capability_set=(),
            )


if __name__ == "__main__":
    unittest.main()
