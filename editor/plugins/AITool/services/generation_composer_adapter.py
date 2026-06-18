from __future__ import annotations

from typing import Any, Callable

from .generation_scheduler import GenerationJob


class SceneComposerJobRunner:
    """GenerationScheduler stage handler for SceneComposer.compose().

    This adapter is intentionally thin: the scheduler owns queueing/cancel/pause,
    SceneComposer owns progressive scene generation, and Coordinator context is
    passed as runtime-only kwargs so batch boundaries can flow back as events.
    """

    def __init__(self, composer_factory: Callable[[], Any]) -> None:
        self._composer_factory = composer_factory

    def compose(self, job: GenerationJob) -> dict[str, Any]:
        composer = self._composer_factory()
        seed_plan = job.payload.get("seed_plan") if isinstance(job.payload.get("seed_plan"), dict) else {}
        prompt = str(
            job.payload.get("prompt")
            or job.payload.get("intent_text")
            or seed_plan.get("intent_summary")
            or ""
        )
        if not prompt:
            raise ValueError("generation job has no prompt or SeedPlan intent_summary")
        actor_id = self._target_actor_id(job.payload)
        result = composer.compose(
            prompt,
            do_import=bool(job.payload.get("do_import", True)),
            do_review=bool(job.payload.get("do_review", False)),
            progress_sink=job.runtime_context.get("progress_sink"),
            actor_id=actor_id,
            **job.compose_kwargs(),
        )
        if not isinstance(result, dict):
            result = {"compose_result": result}
        return {"compose_result": result}

    def stage_handlers(self) -> dict[str, Callable[[GenerationJob], Any]]:
        return {"compose": self.compose}

    @staticmethod
    def _target_actor_id(payload: dict[str, Any]) -> str:
        for key in ("actor_id", "target_actor_id"):
            value = str(payload.get(key) or "").strip()
            if value:
                return value
        latest = payload.get("latest_intervention")
        if isinstance(latest, dict):
            for key in ("actor_id", "target_actor_id"):
                value = str(latest.get(key) or "").strip()
                if value:
                    return value
        interventions = payload.get("pending_interventions")
        if isinstance(interventions, list):
            for item in reversed(interventions):
                if not isinstance(item, dict):
                    continue
                for key in ("actor_id", "target_actor_id"):
                    value = str(item.get(key) or "").strip()
                    if value:
                        return value
        return ""


__all__ = ["SceneComposerJobRunner"]
