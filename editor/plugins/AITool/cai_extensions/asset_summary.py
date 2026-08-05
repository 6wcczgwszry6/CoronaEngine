"""CoronaEngine-specific workflow asset presentation."""

from __future__ import annotations

from typing import Any, Dict


def summarize_global_assets(assets: Dict[str, Any]) -> str:
    lines = ["[工作流上下文] 以下是之前工作流产生的资产信息，你可以引用："]
    model_results = assets.get("model_retrieval", {}).get("model_results", [])
    if model_results:
        lines.append(f"\n## 可用 3D 模型 ({len(model_results)} 个):")
        for row in model_results:
            name = row.get("item_name", "未知")
            error = row.get("error", "")
            lines.append(f"  - {name}: {error or row.get('model_path', '')}")
    composition = assets.get("scene_composition", {})
    if composition:
        lines.extend(
            [
                "\n## 场景组合结果:",
                f"  - 场景文件: {composition.get('scene_path', '')}",
                f"  - 已导入模型: {composition.get('imported_count', 0)}",
            ]
        )
        review = composition.get("review_result", {})
        if review:
            lines.append(
                f"  - 审查: {review.get('overall', 'N/A')} (评分: {review.get('score', 'N/A')})"
            )
    return "\n".join(lines)
