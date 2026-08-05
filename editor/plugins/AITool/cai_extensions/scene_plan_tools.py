"""CoronaEngine-owned indoor scene planning tool."""

from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Quasar.ai_config.ai_config import AIConfig
from Quasar.ai_models.base_pool import get_chat_model
from Quasar.ai_tools.response_adapter import (
    build_error_result,
    build_part,
    build_success_result,
)


class ScenePlanInput(BaseModel):
    scene_type: str = Field(..., description="场景类型，例如：卧室、电竞房、客厅等")
    style: str = Field(default="现代", description="首选的设计风格")
    detail_level: str = Field(default="中等", description="细节丰富程度")
    constraints: Optional[str] = Field(default=None, description="尺寸、颜色等约束")
    style_count: int = Field(default=1, description="设计方案数量")
    views: List[str] = Field(default_factory=lambda: ["overall"])
    image_size: str = Field(default="2K")
    resolution: str = Field(default="1:1")


def load_scene_plan_tools(config: AIConfig) -> List[StructuredTool]:
    llm = get_chat_model(category="text", temperature=0.8, request_timeout=60.0)

    def _extract_json_block(text: str) -> Tuple[str, Optional[dict]]:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text or "", flags=re.S | re.I)
        if match:
            try:
                return (
                    (text[: match.start()] + text[match.end() :]).strip(),
                    json.loads(match.group(1)),
                )
            except Exception:
                return text.strip(), None
        return text.strip(), None

    def _generate_scene_plan(
        scene_type: str,
        style: str = "现代",
        detail_level: str = "中等",
        constraints: Optional[str] = None,
        views: Optional[List[str]] = None,
        image_size: str = "2K",
        resolution: str = "1:1",
        style_count: int = 1,
    ) -> str:
        prompt = f"""你是一个顶级的室内设计师和场景规划师。
请根据场景类型【{scene_type}】提供 {style_count} 种设计方案，同时输出可读文本和合法 JSON。
每种方案必须包含物品清单、布局描述和 [IMAGE_PROMPT] 中文提示词。
JSON 结构：{{"scene_type":"{scene_type}","detail_level":"{detail_level}","plans":[]}}
约束条件：{constraints or '无'}"""
        try:
            response = llm.invoke(
                [
                    SystemMessage(content="你是专业的室内场景规划与拆解助手。"),
                    HumanMessage(content=prompt),
                ]
            )
            readable, structured = _extract_json_block(response.content or "")
            part = build_part(
                content_type="text",
                content_text=readable,
                parameter={
                    "additional_type": ["scene_plan"],
                    "scene_plan_data": structured,
                    "scene_type": scene_type,
                    "style": style,
                    "final_tool_output": True,
                    "suppress_postprocess": True,
                },
            )
            return build_success_result(parts=[part]).to_envelope(interface_type="text")
        except Exception as exc:
            return build_error_result(error_message=str(exc)).to_envelope(interface_type="text")

    return [
        StructuredTool(
            name="generate_scene_plan",
            description="生成室内场景设计方案、物品清单、布局和绘图提示词。",
            func=_generate_scene_plan,
            args_schema=ScenePlanInput,
        )
    ]


__all__ = ["ScenePlanInput", "load_scene_plan_tools"]
