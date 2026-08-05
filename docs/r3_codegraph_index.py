"""CodeGraph bridge for the authoritative R3 planning documents.

CodeGraph 1.0.1 indexes source files but not Markdown. This module intentionally
contains only stable document locations and work-block names; the Markdown files
remain the sole source of truth for task dependencies, status, and acceptance.
"""

from typing import Final


R3_STABILITY_GATE_PLAN_DOCUMENT: Final = (
    "docs/plan/R3稳定门禁与三职能Agent双轨推进计划.md"
)
R3_AGENT_CONSTRAINT_LOOP_DOCUMENT: Final = (
    "docs/Agent任务约束循环_R3三职能协同版.md"
)
R3_PROGRESS_RECORD_DOCUMENT: Final = "docs/R3-min推进记录.md"

R3_WORK_BLOCK_INDEX: Final[dict[str, str]] = {
    "W0": "基线冻结与 R3 门禁底座",
    "W1": "轨道 A：Game-ready Runtime 事实收口",
    "W2": "轨道 A：F5 Vertical Slice 与 Gate 决策",
    "W3": "轨道 B：三职能强类型契约底座",
    "W4": "轨道 B：三职能非执行型协作闭环",
    "W5": "Green 后真实协作与写入闭环",
    "W6": "R3 验收与下游 Agent 承接",
}


def get_r3_authoritative_documents() -> tuple[str, str, str]:
    """Return the plan, execution constraint, and progress document paths."""

    return (
        R3_STABILITY_GATE_PLAN_DOCUMENT,
        R3_AGENT_CONSTRAINT_LOOP_DOCUMENT,
        R3_PROGRESS_RECORD_DOCUMENT,
    )


def get_r3_work_block_documentation() -> dict[str, str]:
    """Return discoverable work-block labels; read the plan for all details."""

    return dict(R3_WORK_BLOCK_INDEX)
