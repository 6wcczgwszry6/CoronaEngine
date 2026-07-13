from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .agent_runtime import AgentRuntime


@dataclass(frozen=True)
class SceneAnalysis:
    scene_version: int
    world_readiness: str
    environment_summary: list[dict[str, Any]]
    entity_summary: list[dict[str, Any]]
    interaction_candidates: list[dict[str, Any]]
    needs_review_entities: list[dict[str, Any]]
    recommendations: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class SceneInspectorAgent:
    """Read-only downstream Agent consuming only SceneWorldSnapshot."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    @staticmethod
    def _entity_summary(entity: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "entity_id": str(entity.get("entity_id") or ""),
            "actor_id": str(entity.get("actor_id") or ""),
            "name": str(entity.get("display_name") or entity.get("name") or ""),
            "entity_type": str(entity.get("entity_type") or ""),
            "semantic_role": str(entity.get("semantic_role") or ""),
            "materialization_status": str(entity.get("materialization_status") or ""),
            "grounding_status": str(entity.get("grounding_status") or ""),
            "sync_status": str(entity.get("sync_status") or ""),
            "game_ready": bool(entity.get("game_ready")),
        }

    def analyze(
        self,
        *,
        room_id: str,
        plan_id: str = "",
        min_version: int | None = None,
    ) -> dict[str, Any]:
        query = self._runtime.handle_message(
            room_id=str(room_id),
            plan_id=str(plan_id or ""),
            text="",
            action="runtime.scene_world_snapshot.get",
            sync_event={"min_version": min_version} if min_version is not None else {},
        )
        if not bool(query.get("found")):
            return {
                "available": False,
                "plan_id": str(query.get("plan_id") or plan_id or ""),
                "reason": str(query.get("reason") or "scene_world_snapshot_unavailable"),
                "analysis": SceneAnalysis(
                    scene_version=int(query.get("scene_version") or 0),
                    world_readiness="blocked",
                    environment_summary=[],
                    entity_summary=[],
                    interaction_candidates=[],
                    needs_review_entities=[],
                    recommendations=["等待 SceneWorldSnapshot 可用后重新分析。"],
                ).as_dict(),
            }

        snapshot = dict(query.get("snapshot") or {})
        environment_entities = [
            dict(item)
            for item in list(snapshot.get("environment_entities") or [])
            if isinstance(item, Mapping)
        ]
        actor_entities = [
            dict(item)
            for item in list(snapshot.get("actor_entities") or [])
            if isinstance(item, Mapping)
        ]
        all_entities = [*environment_entities, *actor_entities]
        needs_review = [
            {
                **self._entity_summary(entity),
                "readiness_missing_fields": list(entity.get("readiness_missing_fields") or []),
            }
            for entity in all_entities
            if not bool(entity.get("game_ready"))
        ]
        interaction_candidates = [
            {
                "entity_id": str(entity.get("entity_id") or ""),
                "name": str(entity.get("display_name") or entity.get("name") or ""),
                "interaction_capability": list(entity.get("interaction_capability") or []),
            }
            for entity in actor_entities
            if list(entity.get("interaction_capability") or [])
        ]
        world_readiness = str(snapshot.get("world_readiness") or "blocked")
        recommendations: list[str] = []
        if needs_review:
            recommendations.append("先补齐 needs_review 实体的真实 AABB、支撑或同步事实。")
        if not environment_entities:
            recommendations.append("当前快照没有可消费的环境实体，请核验 terrain 或 room geometry。")
        if world_readiness == "game_ready":
            recommendations.append("场景事实已可供只读下游 Agent 消费。")
        if not recommendations:
            recommendations.append("场景尚未达到 Game-ready，请等待 Runtime 收口。")

        analysis = SceneAnalysis(
            scene_version=int(snapshot.get("scene_version") or 0),
            world_readiness=world_readiness,
            environment_summary=[self._entity_summary(entity) for entity in environment_entities],
            entity_summary=[self._entity_summary(entity) for entity in actor_entities],
            interaction_candidates=interaction_candidates,
            needs_review_entities=needs_review,
            recommendations=recommendations,
        )
        return {
            "available": True,
            "plan_id": str(query.get("plan_id") or ""),
            "snapshot_stability": str(query.get("snapshot_stability") or ""),
            "analysis": analysis.as_dict(),
        }
