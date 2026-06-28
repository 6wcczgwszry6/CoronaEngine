from typing import Any, Dict

from Quasar.ai_workflow.streaming import stream_output_node
from .formatters import NO_OUTPUT


@stream_output_node("integrated", NO_OUTPUT)
def six_view_capture_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Collect model preview images already produced by upstream generators."""
    model_results = state.get("model_results", [])
    existing_views = dict(state.get("six_view_images", {}) or {})

    if not isinstance(model_results, list):
        return {"six_view_images": existing_views}

    for result in model_results:
        if not isinstance(result, dict) or result.get("error"):
            continue
        actor_name = result.get("object_id") or result.get("item_name") or ""
        if actor_name and result.get("six_views_dict"):
            existing_views[actor_name] = result["six_views_dict"]

    return {
        "model_results": model_results,
        "six_view_images": existing_views,
    }
