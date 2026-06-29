"""VLM 审查外回路（突击方案 §2.3vlm / ⟦COMMIT:5⟧ ⟦DECIDE:vlm-tonight⟧=今晚接）。

定位：**外回路**——语义层、贵、异步、跑在审查队列上，**产出修正建议、绝不阻塞放置**。
与 consistency_check（AABB 内回路，确定性、每次摆放都跑、放置前 gate）互补：
  - AABB 内回路抓几何硬伤（穿模/挡门/超 Zone/悬空）。
  - VLM 外回路抓 AABB 抓不到的语义问题：朝向（兽头朝外）、语义摆放（电视朝沙发）、
    整体"看起来对不对"。

⟦RISK:vlm-screenshot-deadlock⟧（独立于物理的第二个卡死源）：
  物理求解器死循环已修（关物理），但 VLM 要截图、截图走引擎渲染同步，是第二个独立
  卡死源。**前置验证已通过**：现有 model_reviewer._capture_single_model 已用
  ThreadPoolExecutor + future.result(timeout=5.0) + cancel_futures 把截图隔离到
  worker 线程，超时即 skip。本模块复用该机制，并额外经 EngineWriteGate.screenshot
  串行收口（防截图与 import/remove 写入交错）。

铁律（突击方案 §10.5）：VLM 是外回路，**产建议不阻塞放置**。它输出 advisory
corrections（rotation/scale/issues），调用方/FinalReview 决定是否采纳——VLM 自己
绝不直接改场景、绝不卡主链路。

设计：纯编排，capture_fn / review_fn / engine_gate 依赖注入，便于离线测。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_user_text(value: Any, *, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    lower = text.lower()
    markers = (
        "prompt",
        "raw_prompt",
        "provider",
        "model_provider",
        "runtime_context",
        "scheduler_updates",
        "hidden_debug_ref",
        "debug",
        "job_id",
        "session_id",
        "token",
        "api_key",
        "vlm_raw",
        "screenshot_dir",
        "output_dir",
    )
    cut_points = [lower.find(marker) for marker in markers if lower.find(marker) >= 0]
    if cut_points:
        keep = text[:min(cut_points)].strip(" \t\r\n,;；。")
        return keep or fallback or "内部细节已隐藏"
    return text


def _coerce_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.0
    return max(0.0, min(1.0, confidence))


@dataclass
class VlmAdvice:
    """VLM 对单个模型的审查建议（advisory，不强制）。"""
    actor_id: str
    overall: str = "PASS"                       # "PASS" | "WARN" | "FAIL" | "SKIPPED"
    position_correction: List[float] = field(default_factory=list)
    rotation_correction: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale_correction: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    issues: List[str] = field(default_factory=list)
    fix_suggestion: str = ""
    confidence: float = 0.0

    def has_correction(self) -> bool:
        """是否给出了非平凡的修正建议（位置、旋转或缩放）。"""
        pos_nontrivial = len(self.position_correction) >= 3
        rot_nontrivial = any(abs(r) > 1e-3 for r in self.rotation_correction)
        scale_nontrivial = any(abs(s - 1.0) > 1e-3 for s in self.scale_correction)
        return pos_nontrivial or rot_nontrivial or scale_nontrivial

    def is_confident(self, threshold: float = 0.55) -> bool:
        return _coerce_confidence(self.confidence) >= threshold


@dataclass
class VlmReviewReport:
    """一轮 VLM 外回路审查的汇总。"""
    advices: List[VlmAdvice] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)       # 截图/审查失败被跳过的
    timed_out: List[str] = field(default_factory=list)      # 截图超时（卡死源兜底命中）
    confidence_threshold: float = 0.55
    status: str = "completed"                              # completed | disabled | skipped | unavailable
    reason: str = ""
    checkpoint_type: str = "final_consistency_review"       # structure_review | high_risk_object_review | final_consistency_review
    reviewed_targets: List[Dict[str, Any]] = field(default_factory=list)
    advisory_items: List[Dict[str, Any]] = field(default_factory=list)
    proposal_items: List[Dict[str, Any]] = field(default_factory=list)

    def actionable(self) -> List[VlmAdvice]:
        """返回有可执行修正建议的条目（供 FinalReview 选择性采纳）。"""
        return [
            a for a in self.advices
            if a.is_confident(self.confidence_threshold) and (a.has_correction() or a.overall == "FAIL")
        ]

    def to_user_text(self) -> str:
        if self.status == "disabled":
            reason = _safe_user_text(self.reason, fallback="当前配置关闭。")
            return f"VLM 外审未执行：{reason}；本轮以 AABB 几何检查和最终调整建议为准。"
        if self.status in {"skipped", "unavailable"} and self.reason:
            reason = _safe_user_text(self.reason, fallback="审查条件不满足。")
            return f"VLM 外审未完成：{reason}；本轮以 AABB 几何检查为准。"
        act = self.actionable()
        if not act:
            if self.timed_out or self.skipped:
                skipped = len(self.skipped)
                timed_out = len(self.timed_out)
                return f"VLM 外审未完成：截图失败/跳过 {skipped} 个，超时 {timed_out} 个；本轮以 AABB 几何检查为准。"
            low_confidence_count = sum(
                1
                for advice in self.advices
                if not advice.is_confident(self.confidence_threshold)
                and (advice.has_correction() or advice.overall == "FAIL")
            )
            if low_confidence_count:
                details = []
                for item in self.advisory_items[:5]:
                    actor = _safe_user_text(item.get("actor_id"), fallback="某个物体")
                    issues = item.get("issues") if isinstance(item.get("issues"), list) else []
                    tip = _safe_user_text(item.get("fix_suggestion"))
                    if not tip:
                        issue_texts = [_safe_user_text(value) for value in issues if _safe_user_text(value)]
                        tip = "、".join(issue_texts[:2])
                    tip = tip or _safe_user_text(item.get("overall"), fallback="存在低置信提示")
                    details.append(f"{actor}：{tip}")
                detail_text = "；".join(details)
                suffix = f"包括：{detail_text}；" if detail_text else ""
                return (
                    f"VLM 审查发现 {low_confidence_count} 条低置信建议；"
                    f"{suffix}本轮不自动执行，等待后续批次或人工确认。"
                )
            return "VLM 审查未发现明显语义问题。"
        lines = ["VLM 审查发现可优化项（建议，非强制）："]
        for a in act[:5]:
            actor = _safe_user_text(a.actor_id, fallback="某个物体")
            tip = _safe_user_text(a.fix_suggestion or "、".join(a.issues[:2]) or a.overall)
            lines.append(f"- {actor}：{tip}")
        return "\n".join(lines)


def _advice_item(advice: VlmAdvice, *, checkpoint_type: str, proposal: bool) -> Dict[str, Any]:
    return {
        "actor_id": _safe_user_text(advice.actor_id, fallback=""),
        "checkpoint_type": checkpoint_type,
        "overall": _safe_user_text(advice.overall, fallback="WARN"),
        "issues": [_safe_user_text(item) for item in list(advice.issues or []) if _safe_user_text(item)],
        "fix_suggestion": _safe_user_text(advice.fix_suggestion),
        "confidence": _coerce_confidence(advice.confidence),
        "proposal": bool(proposal),
    }


def review_models_async(
    targets: List[Dict[str, Any]],
    *,
    capture_fn: Callable[[str, str], Optional[str]],
    review_fn: Callable[[str, str, str], Dict[str, Any]],
    engine_gate: Any = None,
    screenshot_timeout: float = 5.0,
    checkpoint_type: str = "final_consistency_review",
) -> VlmReviewReport:
    """对一批模型跑 VLM 外回路审查，产出 advisory 报告（绝不改场景、绝不阻塞）。

    targets: [{actor_id, model_name?, model_type?}]
    capture_fn(output_dir, model_name) -> screenshot_dir | None（截图路径，已自带
        timeout+skip；本函数额外经 engine_gate.screenshot 串行收口）。
    review_fn(screenshot_dir, model_name, model_type) -> dict（VLM 审查结果）。
    engine_gate: EngineWriteGate（截图经 .screenshot 收口；None 则直接调 capture_fn）。

    任一目标的截图/审查失败 → 记 skipped/timed_out，**不中断整批、不抛**。
    """
    report = VlmReviewReport(checkpoint_type=str(checkpoint_type or "final_consistency_review"))
    if not targets:
        return report

    for tgt in targets:
        actor_id = (tgt.get("actor_id") or tgt.get("name") or "").strip()
        if not actor_id:
            continue
        model_name = tgt.get("model_name") or actor_id
        model_type = tgt.get("model_type") or model_name
        raw_out_dir = tgt.get("output_dir") or os.path.join("_vlm_review", actor_id)
        try:
            from .vlm_capture import resolve_vlm_output_dir
        except ImportError:
            from vlm_capture import resolve_vlm_output_dir
        out_dir = resolve_vlm_output_dir(raw_out_dir)
        report.reviewed_targets.append({
            "actor_id": _safe_user_text(actor_id),
            "model_name": _safe_user_text(model_name),
            "model_type": _safe_user_text(model_type),
            "checkpoint_type": report.checkpoint_type,
        })

        # 1. 截图（经 EngineWriteGate 收口；capture_fn 自带 timeout+skip 兜底卡死源）
        try:
            if engine_gate is not None:
                shot_dir = engine_gate.screenshot(capture_fn, out_dir, model_name)
            else:
                shot_dir = capture_fn(out_dir, model_name)
        except TimeoutError:
            logger.warning("[VlmReviewLoop] %s 截图超时（卡死源兜底命中），跳过", actor_id)
            report.timed_out.append(actor_id)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VlmReviewLoop] %s 截图异常，跳过: %s", actor_id, exc)
            report.skipped.append(actor_id)
            continue

        if not shot_dir:
            logger.info("[VlmReviewLoop] %s 无截图（超时或失败），跳过审查", actor_id)
            report.skipped.append(actor_id)
            continue

        # 2. VLM 审查（产建议，不阻塞）
        try:
            raw = review_fn(shot_dir, model_name, model_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[VlmReviewLoop] %s VLM 审查异常，跳过: %s", actor_id, exc)
            report.skipped.append(actor_id)
            continue

        advice = VlmAdvice(
            actor_id=actor_id,
            overall=str(raw.get("overall", "PASS")),
            position_correction=list(raw.get("position_correction", []) or []),
            rotation_correction=list(raw.get("rotation_correction", [0.0, 0.0, 0.0])),
            scale_correction=list(raw.get("scale_correction", [1.0, 1.0, 1.0])),
            issues=list(raw.get("issues", []) or []),
            fix_suggestion=str(raw.get("fix_suggestion", "") or ""),
            confidence=_coerce_confidence(raw.get("confidence")),
        )
        report.advices.append(advice)
        item = _advice_item(
            advice,
            checkpoint_type=report.checkpoint_type,
            proposal=advice in report.actionable(),
        )
        if item["proposal"]:
            report.proposal_items.append(item)
        elif advice.overall != "PASS" or advice.issues or advice.fix_suggestion:
            report.advisory_items.append(item)

    logger.info(
        "[VlmReviewLoop] 完成 — 审查 %d, 跳过 %d, 超时 %d, 可执行建议 %d",
        len(report.advices), len(report.skipped), len(report.timed_out),
        len(report.actionable()),
    )
    return report



def _default_scene_snapshot(scene_name: str) -> Dict[str, Any]:
    from ..mcp.tools.native_scene_state import get_native_scene_snapshot

    return get_native_scene_snapshot(
        scene_name,
        wait_for_bounds=True,
        timeout_s=2.0,
        interval_s=0.05,
    )


def _default_scene_capture(scene_name: str, output_dir: str, *, actor_name: Optional[str] = None, scope: str = "scene") -> Any:
    from .vlm_capture import capture_vlm_views

    return capture_vlm_views(
        scene_name,
        output_dir,
        actor_name=actor_name,
        scope=scope,
    )


def _default_scene_scale_review(*, output_dir: str, scene_description: str, max_images: int) -> Dict[str, Any]:
    from ..flows.scene_composition_workflow.helpers import get_tool, parse_review_result

    review_tool = get_tool("scene_rationality_review")
    if review_tool is None:
        return {"error": "scene_rationality_review tool is unavailable"}
    raw = review_tool.invoke({
        "output_dir": output_dir,
        "scene_description": scene_description,
        "max_images": max_images,
    })
    return parse_review_result(raw)


def _format_vec(value: Any, *, ndigits: int = 3) -> List[float]:
    if not isinstance(value, (list, tuple)):
        return []
    out: List[float] = []
    for item in value[:3]:
        try:
            out.append(round(float(item), ndigits))
        except Exception:
            return []
    return out


def _build_scene_scale_description(snapshot: Dict[str, Any]) -> str:
    scene = str(snapshot.get("scene") or snapshot.get("scene_name") or "")
    scene_aabb = snapshot.get("scene_aabb") if isinstance(snapshot.get("scene_aabb"), list) else []
    actors = snapshot.get("actors") if isinstance(snapshot.get("actors"), list) else []
    lines = [
        "全场景相对尺度审查：请重点比较场景中所有可见物体之间的相对大小是否符合常识。",
        "不要只评价单个模型外观；需要比较床、桌椅、柜子、灯具、人物、装饰物等之间的比例。",
        "如果某个物体相对其他物体明显过大或过小，请在 corrections 中给出该物体修正后的 scale。",
        f"scene={scene}",
    ]
    if scene_aabb:
        lines.append(f"scene_aabb={scene_aabb}")
    lines.append("actors with native world bounds:")
    for actor in actors[:80]:
        if not isinstance(actor, dict):
            continue
        name = str(actor.get("name") or actor.get("actor_guid") or "").strip()
        if not name:
            continue
        geometry = actor.get("geometry") if isinstance(actor.get("geometry"), dict) else {}
        position = _format_vec(geometry.get("position"), ndigits=3)
        rotation = _format_vec(geometry.get("rotation"), ndigits=3)
        scale = _format_vec(geometry.get("scale"), ndigits=3)
        size = _format_vec(actor.get("size"), ndigits=3)
        world_aabb = actor.get("world_aabb") if isinstance(actor.get("world_aabb"), list) else []
        bounds_ready = bool(actor.get("bounds_ready"))
        lines.append(
            f"- {name}: type={actor.get('actor_type') or actor.get('type') or 'unknown'} "
            f"pos={position} rot={rotation} scale={scale} size={size} "
            f"world_aabb={world_aabb} bounds_ready={bounds_ready}"
        )
    return "\n".join(lines)


def _coerce_scene_review(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        review = raw.get("review") if isinstance(raw.get("review"), dict) else None
        return review if review is not None else raw
    return {"error": f"unsupported scene scale review result: {type(raw).__name__}"}


def _correction_actor_name(correction: Dict[str, Any]) -> str:
    return str(
        correction.get("object_id")
        or correction.get("actor")
        or correction.get("actor_id")
        or correction.get("name")
        or ""
    ).strip()


def _issue_actor_name(issue: Dict[str, Any]) -> str:
    return str(
        issue.get("actor")
        or issue.get("object_id")
        or issue.get("actor_id")
        or issue.get("name")
        or ""
    ).strip()


def _scene_scale_review_report(review: Dict[str, Any], *, snapshot: Dict[str, Any], checkpoint_type: str) -> VlmReviewReport:
    report = VlmReviewReport(checkpoint_type=checkpoint_type)
    actors = snapshot.get("actors") if isinstance(snapshot.get("actors"), list) else []
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        name = str(actor.get("name") or actor.get("actor_guid") or "").strip()
        if name:
            report.reviewed_targets.append({
                "actor_id": name,
                "model_name": name,
                "model_type": str(actor.get("actor_type") or actor.get("type") or "model"),
                "checkpoint_type": checkpoint_type,
            })

    if review.get("error"):
        report.status = "unavailable"
        report.reason = str(review.get("error") or "scene scale review failed")
        return report

    issues_by_actor: Dict[str, List[str]] = {}
    for item in review.get("problem_actors") or []:
        if not isinstance(item, dict):
            continue
        actor = _issue_actor_name(item)
        if not actor:
            continue
        issue = str(item.get("issue") or item.get("reason") or "wrong_scale")
        reason = str(item.get("reason") or issue)
        issues_by_actor.setdefault(actor, []).append(reason)

    confidence_default = 0.75 if review.get("corrections") else 0.0
    for correction in review.get("corrections") or []:
        if not isinstance(correction, dict):
            continue
        actor = _correction_actor_name(correction)
        if not actor:
            continue
        scale = correction.get("scale")
        try:
            scale_values = [float(v) for v in list(scale or [])[:3]]
        except Exception:
            scale_values = []
        if len(scale_values) < 3:
            scale_values = [1.0, 1.0, 1.0]
        rotation = correction.get("rotation")
        try:
            rotation_values = [float(v) for v in list(rotation or [])[:3]]
        except Exception:
            rotation_values = [0.0, 0.0, 0.0]
        while len(rotation_values) < 3:
            rotation_values.append(0.0)
        position = correction.get("position")
        try:
            position_values = [float(v) for v in list(position or [])[:3]]
        except Exception:
            position_values = []
        reason = str(correction.get("reason") or "").strip()
        issues = list(issues_by_actor.get(actor, []))
        if reason and reason not in issues:
            issues.append(reason)
        advice = VlmAdvice(
            actor_id=actor,
            overall=str(review.get("overall") or "WARN"),
            position_correction=position_values,
            rotation_correction=rotation_values[:3],
            scale_correction=scale_values[:3],
            issues=issues,
            fix_suggestion=reason or "; ".join(issues[:2]),
            confidence=_coerce_confidence(correction.get("confidence", review.get("confidence", confidence_default))),
        )
        report.advices.append(advice)

    actionable = set(id(item) for item in report.actionable())
    for advice in report.advices:
        item = _advice_item(
            advice,
            checkpoint_type=checkpoint_type,
            proposal=id(advice) in actionable,
        )
        if item["proposal"]:
            report.proposal_items.append(item)
        elif advice.overall != "PASS" or advice.issues or advice.fix_suggestion:
            report.advisory_items.append(item)

    if not report.advices:
        for actor, issues in issues_by_actor.items():
            advice = VlmAdvice(
                actor_id=actor,
                overall=str(review.get("overall") or "WARN"),
                issues=list(issues),
                fix_suggestion="; ".join(issues[:2]),
                confidence=_coerce_confidence(review.get("confidence")),
            )
            report.advices.append(advice)
            report.advisory_items.append(_advice_item(advice, checkpoint_type=checkpoint_type, proposal=False))
    return report


def review_scene_scale_async(
    *,
    scene_name: str = "",
    capture_fn: Optional[Callable[..., Any]] = None,
    review_fn: Optional[Callable[..., Any]] = None,
    snapshot_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    engine_gate: Any = None,
    output_dir: str = "_vlm_review/final_scene_scale",
    max_images: int = 8,
    checkpoint_type: str = "final_consistency_review",
) -> VlmReviewReport:
    """Run final whole-scene VLM review focused on relative object scale."""
    capture_fn = capture_fn or _default_scene_capture
    review_fn = review_fn or _default_scene_scale_review
    snapshot_fn = snapshot_fn or _default_scene_snapshot

    try:
        try:
            snapshot = snapshot_fn(scene_name)
        except TypeError:
            snapshot = snapshot_fn()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VlmReviewLoop] scene scale snapshot failed: %s", exc)
        return VlmReviewReport(
            status="skipped",
            reason=f"native scene snapshot unavailable: {exc}",
            checkpoint_type=checkpoint_type,
        )

    try:
        if engine_gate is not None:
            capture = engine_gate.screenshot(
                capture_fn,
                scene_name,
                output_dir,
                actor_name=None,
                scope="scene",
            )
        else:
            capture = capture_fn(scene_name, output_dir, actor_name=None, scope="scene")
    except TimeoutError:
        report = VlmReviewReport(status="skipped", reason="scene VLM capture timed out", checkpoint_type=checkpoint_type)
        report.timed_out.append("__scene__")
        return report
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VlmReviewLoop] scene scale capture failed: %s", exc)
        report = VlmReviewReport(status="skipped", reason=f"scene VLM capture failed: {exc}", checkpoint_type=checkpoint_type)
        report.skipped.append("__scene__")
        return report

    if not capture or str(getattr(capture, "status", "") or "") != "success":
        reason = str(getattr(capture, "skipped_reason", "") or "scene VLM capture produced no screenshots")
        report = VlmReviewReport(status="skipped", reason=reason, checkpoint_type=checkpoint_type)
        report.skipped.append("__scene__")
        return report

    description = _build_scene_scale_description(snapshot)
    try:
        raw_review = review_fn(
            output_dir=str(getattr(capture, "output_dir", output_dir) or output_dir),
            scene_description=description,
            max_images=max_images,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[VlmReviewLoop] scene scale VLM review failed: %s", exc)
        return VlmReviewReport(
            status="unavailable",
            reason=f"scene scale VLM review failed: {exc}",
            checkpoint_type=checkpoint_type,
        )

    report = _scene_scale_review_report(
        _coerce_scene_review(raw_review),
        snapshot=snapshot,
        checkpoint_type=checkpoint_type,
    )
    logger.info(
        "[VlmReviewLoop] scene scale review completed actors=%d advices=%d proposals=%d",
        len(report.reviewed_targets),
        len(report.advices),
        len(report.proposal_items),
    )
    return report


__all__ = ["VlmAdvice", "VlmReviewReport", "review_models_async", "review_scene_scale_async"]
