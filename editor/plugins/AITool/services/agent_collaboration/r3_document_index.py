from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class R3AuthoritativeDocument:
    document_id: str
    title: str
    repository_path: str
    purpose: str
    major_sections: tuple[str, ...]


R3_STABILITY_GATE_PLAN = R3AuthoritativeDocument(
    document_id="r3_stability_gate_plan",
    title="R3 稳定门禁与三职能 Agent 双轨推进计划",
    repository_path="docs/R3稳定门禁与三职能Agent双轨推进计划.md",
    purpose=(
        "Defines the authoritative Red/Yellow/Green gate, Track A Game-ready "
        "Runtime work, Track B non-executing collaboration work, and W0-W6 order."
    ),
    major_sections=(
        "架构不变量",
        "双轨推进与隔离边界",
        "两层门禁",
        "红黄绿判定",
        "W0：基线冻结与 R3 门禁底座",
        "W1：轨道 A，Game-ready Runtime 事实收口",
        "W2：轨道 A，F5 Vertical Slice 与 Gate 决策",
        "W3：轨道 B，三职能强类型契约底座",
        "W4：轨道 B，三职能非执行型协作闭环",
        "W5：Green 后真实协作与写入闭环",
        "W6：R3 验收与下游 Agent 承接",
        "AI 续跑协议",
    ),
)

R3_AGENT_CONSTRAINT_LOOP = R3AuthoritativeDocument(
    document_id="r3_agent_constraint_loop",
    title="Agent 任务约束循环：R3 与三职能协同版",
    repository_path="docs/Agent任务约束循环_R3三职能协同版.md",
    purpose=(
        "Constrains every implementation turn by the current gate, one acceptance "
        "breakpoint, architecture invariants, risk level, and bounded verification."
    ),
    major_sections=(
        "每轮闭环",
        "任务选择算法",
        "事实核实规则",
        "Gate 驱动的执行边界",
        "架构硬约束",
        "风险判定",
        "最小实现原则",
        "测试预算",
        "停手与重新诊断条件",
        "完成、状态与回写",
        "AI 交接与上下文压缩",
    ),
)

R3_AUTHORITATIVE_DOCUMENTS: Mapping[str, R3AuthoritativeDocument] = MappingProxyType(
    {
        R3_STABILITY_GATE_PLAN.document_id: R3_STABILITY_GATE_PLAN,
        R3_AGENT_CONSTRAINT_LOOP.document_id: R3_AGENT_CONSTRAINT_LOOP,
    }
)


def get_r3_authoritative_document(document_id: str) -> R3AuthoritativeDocument:
    """Return a CodeGraph-indexable pointer to an authoritative R3 document."""

    normalized = str(document_id or "").strip()
    if not normalized:
        raise ValueError("document_id is required")
    try:
        return R3_AUTHORITATIVE_DOCUMENTS[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown R3 authoritative document: {normalized}") from exc
