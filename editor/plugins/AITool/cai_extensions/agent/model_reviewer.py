"""模型质量审查器 — 生成后逐个导入引擎 → 截图 → VLM 审查 → 修正 → 卸载。

与生成阶段解耦: 生成是纯 API 调用(不碰引擎), 审查是串行队列(全局锁保护),
避免并行截图导致引擎 GPU 管线死锁。

每条审查结果注入后续的 LLM 布局 prompt, 让布局知道旋转角/比例建议。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 全局互斥锁: 同一时刻只允许一个审查会话, 防止截图竞态死锁
_review_lock = threading.Lock()

VLM_REVIEW_CAMERA_NAME = "vlm_review_camera"

# 审查 VLM prompt
_REVIEW_SYSTEM_PROMPT = """你是 3D 模型质量检查员。检查单个模型的:
1. 朝向/旋转角是否合理 (椅子朝前, 灯朝上, 沙发靠背面朝外)
2. 比例是否正常 (不会过大或过小)
3. 是否有明显的生成缺陷 (残缺/变形/纹理错误)

输出 JSON:
{
  "overall": "PASS" | "FAIL",
  "rotation_correction": [rx, ry, rz],   // 需要的旋转修正(弧度), 不需要则为 [0,0,0]；例如 90度=1.5708
  "scale_correction": [sx, sy, sz],       // 需要的比例修正, 不需要则为 [1,1,1]
  "issues": ["问题描述"],
  "fix_suggestion": "修正建议 (给后续 LLM 布局用, 如: 旋转 90° 使其朝前)"
}"""


def _get_current_scene() -> Optional[Any]:
    try:
        from CoronaCore.core.managers import scene_manager
        routes = scene_manager.list_all()
        return scene_manager.get(routes[0]) if routes else None
    except Exception as exc:
        logger.warning("[ModelReviewer] 无法获取当前场景: %s", exc)
        return None


def get_or_create_vlm_review_camera(scene: Any, camera_factory: Optional[Any] = None) -> Optional[Any]:
    """Return a hidden VLM review camera without switching the active viewport camera."""
    if scene is None:
        return None
    try:
        existing = scene.find_camera(VLM_REVIEW_CAMERA_NAME)
        if existing is not None:
            return existing
    except Exception:
        pass

    try:
        if camera_factory is None:
            from CoronaCore.core.entities.camera import Camera
            camera_factory = Camera
        camera = camera_factory(
            name=VLM_REVIEW_CAMERA_NAME,
            width=512,
            height=512,
            view_open=False,
            deletable=False,
            render_backend="native",
            output_mode="base_color",
        )
        scene.add_camera_to_scene(camera)
        logger.info("[ModelReviewer] 已创建 VLM 独立截图摄像头: %s", VLM_REVIEW_CAMERA_NAME)
        return camera
    except Exception as exc:
        logger.warning("[ModelReviewer] 创建 VLM 独立截图摄像头失败: %s", exc)
        return None


def _wait_for_file_ready(filepath: str, timeout: float = 1.5, interval: float = 0.05) -> bool:
    """Wait until the screenshot file exists and its size has settled briefly."""
    deadline = time.time() + timeout
    last_size = -1
    stable_count = 0
    while time.time() < deadline:
        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0
        if size > 0 and size == last_size:
            stable_count += 1
            if stable_count >= 2:
                return True
        else:
            stable_count = 0
            last_size = size
        time.sleep(interval)
    return False


def _save_camera_screenshot_with_timeout(camera: Any, filepath: str, timeout: float = 5.0) -> bool:
    def _save() -> Any:
        save_sync = getattr(camera, "save_screenshot_sync", None)
        if callable(save_sync):
            return save_sync(filepath)
        return camera.save_screenshot(filepath)

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_save)
    try:
        result = future.result(timeout=timeout)
        if result is False:
            return False
        return _wait_for_file_ready(filepath)
    except FuturesTimeoutError:
        logger.warning("[ModelReviewer] VLM 独立摄像头截图超时: %s", filepath)
        executor.shutdown(wait=False, cancel_futures=True)
        return False
    except Exception as exc:
        logger.warning("[ModelReviewer] VLM 独立摄像头截图异常: %s", exc)
        return False
    finally:
        if future.done():
            executor.shutdown(wait=False)


def _capture_with_review_camera(
    scene: Any,
    review_camera: Any,
    output_dir: str,
    model_name: str,
    calc_camera_pose: Any,
) -> Optional[str]:
    os.makedirs(output_dir, exist_ok=True)
    distance = 3.0
    center = [0.0, 0.5, 0.0]
    angles = [0, 90, 180, 270]
    saved: List[str] = []
    old_mode = None
    try:
        old_mode_fn = getattr(review_camera, "get_output_mode", None)
        old_mode = old_mode_fn() if callable(old_mode_fn) else getattr(review_camera, "output_mode", None)
    except Exception:
        old_mode = None

    try:
        set_mode = getattr(review_camera, "set_output_mode", None)
        if callable(set_mode):
            set_mode("base_color")
        for az in angles:
            pose = calc_camera_pose(center, distance, az, 25.0)
            filepath = os.path.join(output_dir, f"{model_name}_az{az:03d}.png")
            try:
                review_camera.set(pose["position"], pose["forward"], pose["up"], 45.0)
                time.sleep(0.1)
                if _save_camera_screenshot_with_timeout(review_camera, filepath):
                    saved.append(filepath)
                else:
                    logger.warning("[ModelReviewer] %s az=%d VLM 截图失败/为空", model_name, az)
            except Exception as exc:
                logger.warning("[ModelReviewer] %s az=%d VLM 独立截图异常: %s", model_name, az, exc)
    finally:
        if old_mode:
            try:
                review_camera.set_output_mode(old_mode)
            except Exception:
                pass

    logger.info("[ModelReviewer] %s 独立摄像头截图 %d/%d", model_name, len(saved), len(angles))
    return output_dir if saved else None


def _capture_single_model_main_camera_fallback(output_dir: str, model_name: str) -> Optional[str]:
    """Legacy debug path. This moves the main camera; keep it opt-in only."""
    import os

    try:
        from ..flows.scene_composition_workflow_v2.nodes_tier_review import (
            _calc_camera_pose,
        )
    except ImportError:
        logger.warning("[ModelReviewer] 无法导入截图工具")
        return None

    from ..flows.scene_composition_workflow.helpers import get_tool

    move_tool = get_tool("camera_move")
    shot_tool = get_tool("camera_screenshot")
    if move_tool is None or shot_tool is None:
        logger.warning("[ModelReviewer] 拍摄工具缺失")
        return None

    os.makedirs(output_dir, exist_ok=True)
    distance = 3.0  # 单模型审查用更近的距离
    center = [0.0, 0.5, 0.0]
    angles = [0, 90, 180, 270]

    saved = []
    for az in angles:
        pose = _calc_camera_pose(center, distance, az, 25.0)
        try:
            move_tool.invoke({
                "position": pose["position"],
                "forward": pose["forward"],
                "up": pose["up"],
            })
            time.sleep(0.3)
            filepath = os.path.join(output_dir, f"{model_name}_az{az:03d}.png")

            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                shot_tool.invoke,
                {"output_path": filepath, "output_mode": "base_color"},
            )
            try:
                ok = future.result(timeout=5.0)
                if ok is False:
                    logger.warning("[ModelReviewer] %s az=%d 截图工具返回失败", model_name, az)
                elif os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    saved.append(filepath)
                else:
                    logger.warning("[ModelReviewer] %s az=%d 截图文件缺失或为空", model_name, az)
            except FuturesTimeoutError:
                logger.warning("[ModelReviewer] %s az=%d 截图超时, 跳过", model_name, az)
                executor.shutdown(wait=False, cancel_futures=True)
            else:
                executor.shutdown(wait=False)
            time.sleep(0.3)
        except Exception as e:
            logger.warning("[ModelReviewer] %s az=%d 截图异常: %s", model_name, az, e)

    logger.info("[ModelReviewer] %s 截图 %d/%d", model_name, len(saved), len(angles))
    return output_dir if saved else None


def _capture_single_model(output_dir: str, model_name: str, tier: int = 99) -> Optional[str]:
    """对场景中单个模型拍摄 4 角度截图。默认使用独立 VLM 摄像头, 不扰动主视口。"""
    try:
        from ..flows.scene_composition_workflow_v2.nodes_tier_review import (
            _calc_camera_pose,
        )
    except ImportError:
        logger.warning("[ModelReviewer] 无法导入截图姿态工具")
        return None

    scene = _get_current_scene()
    review_camera = get_or_create_vlm_review_camera(scene)
    if review_camera is not None:
        return _capture_with_review_camera(scene, review_camera, output_dir, model_name, _calc_camera_pose)

    allow_main = os.environ.get("CORONA_VLM_ALLOW_MAIN_CAMERA_CAPTURE", "0").strip() == "1"
    if not allow_main:
        logger.warning(
            "[ModelReviewer] VLM 独立截图摄像头不可用, 跳过截图; "
            "如需旧主相机调试, 设置 CORONA_VLM_ALLOW_MAIN_CAMERA_CAPTURE=1"
        )
        return None
    logger.warning("[ModelReviewer] 使用旧主相机截图 fallback, 可能扰动主视口")
    return _capture_single_model_main_camera_fallback(output_dir, model_name)


def _vlm_review_model(screenshot_dir: str, model_name: str, model_type: str) -> Dict[str, Any]:
    """对模型截图进行 VLM 审查, 返回结构化评审结果。"""
    from ..flows.scene_composition_workflow.helpers import get_tool, parse_review_result

    review_tool = get_tool("scene_rationality_review")
    if review_tool is None:
        logger.warning("[ModelReviewer] VLM 审查工具不可用, 跳过 %s", model_name)
        return {"overall": "SKIPPED", "rotation_correction": [0, 0, 0],
                "scale_correction": [1, 1, 1], "issues": [], "fix_suggestion": ""}

    scene_desc = (
        f"单模型质量审查: {model_name} (类型: {model_type})\n"
        f"检查旋转角、比例、缺陷。只输出 JSON。"
    )

    try:
        raw = review_tool.invoke({
            "output_dir": screenshot_dir,
            "scene_description": scene_desc,
            "max_images": 4,
        })
        parsed = parse_review_result(raw)
        # 提取 corrections 或 problem_actors 中的旋转/比例建议
        result = {
            "overall": parsed.get("overall", "PASS"),
            "rotation_correction": [0, 0, 0],
            "scale_correction": [1, 1, 1],
            "issues": parsed.get("issues", []),
            "fix_suggestion": "",
        }
        # 从 corrections 中提取旋转/比例
        corrections = parsed.get("corrections", []) or []
        for c in corrections:
            if c.get("rotation"):
                result["rotation_correction"] = c["rotation"]
            if c.get("scale"):
                result["scale_correction"] = c["scale"]
        # 从 suggestions 中提取修正建议
        suggestions = parsed.get("suggestions", []) or []
        if suggestions:
            result["fix_suggestion"] = "; ".join(suggestions[:2])
        return result
    except Exception as e:
        logger.warning("[ModelReviewer] VLM 审查异常 %s: %s", model_name, e)
        return {"overall": "ERROR", "rotation_correction": [0, 0, 0],
                "scale_correction": [1, 1, 1], "issues": [str(e)], "fix_suggestion": ""}


def review_single_model(
    model_path: str,
    model_name: str,
    model_type: str = "",
    output_base: str = "",
) -> Dict[str, Any]:
    """审查单个模型: 导入引擎 → 截图 → VLM → 记录修正 → 卸载。

    全局锁保护, 同一时刻只允许一个审查会话。
    返回审查结果, 注入后续布局 prompt。
    """
    import os as _os
    import tempfile as _tf

    with _review_lock:
        logger.info("[ModelReviewer] ====== 开始审查: %s ======", model_name)

        # 1. 导入引擎
        actor_name = None
        try:
            from CoronaCore.core.managers import scene_manager
            routes = scene_manager.list_all()
            scene = scene_manager.get(routes[0]) if routes else None
            if scene is None:
                logger.warning("[ModelReviewer] 无可用场景, 跳过 %s", model_name)
                return _empty_review()

            # 先清理场景中可能残留的物体
            existing = scene.find_actor(model_name)
            if existing:
                scene.remove_actor(model_name)

            actor = scene.import_model(model_path, model_name)
            if actor is None:
                logger.warning("[ModelReviewer] 导入失败: %s", model_name)
                return _empty_review()
            actor_name = model_name
            logger.info("[ModelReviewer] %s 导入成功", model_name)
        except Exception as e:
            logger.warning("[ModelReviewer] 导入异常 %s: %s", model_name, e)
            return _empty_review()

        # 2. 截图
        tmp_dir = _os.path.join(_tf.gettempdir(), f"corona_review_{model_name}")
        screenshot_dir = _capture_single_model(tmp_dir, model_name)
        if not screenshot_dir:
            _remove_actor_safe(scene, model_name)
            return _empty_review()

        # 3. VLM 审查
        review = _vlm_review_model(screenshot_dir, model_name, model_type or model_name)

        # 4. 清理
        _remove_actor_safe(scene, model_name)
        # 清理截图临时文件
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

        review["model_name"] = model_name
        logger.info("[ModelReviewer] %s 审查完成: overall=%s rotation=%s scale=%s",
                    model_name, review["overall"],
                    review["rotation_correction"], review["scale_correction"])
        return review


def _empty_review() -> Dict[str, Any]:
    return {"overall": "SKIPPED", "rotation_correction": [0, 0, 0],
            "scale_correction": [1, 1, 1], "issues": [], "fix_suggestion": "",
            "model_name": ""}


def _remove_actor_safe(scene: Any, name: str) -> None:
    try:
        scene.remove_actor(name)
    except Exception:
        pass


def build_review_context(reviews: List[Dict[str, Any]]) -> str:
    """将审查结果构建为 LLM 布局 prompt 的上下文片段。

    注入到 compose_scene 的 prompt 中, 让 LLM 布局时考虑旋转角/比例建议。
    """
    if not reviews:
        return ""

    lines = ["\n## 模型审查结果 (布局时参考)"]
    for r in reviews:
        name = r.get("model_name", "?")
        rot = r.get("rotation_correction", [0, 0, 0])
        scl = r.get("scale_correction", [1, 1, 1])
        fix = r.get("fix_suggestion", "")
        issues = r.get("issues", [])

        parts = [f"- {name}:"]
        if any(v != 0 for v in rot):
            parts.append(f"旋转修正=[{rot[0]:.0f}, {rot[1]:.0f}, {rot[2]:.0f}]°")
        if any(v != 1 for v in scl):
            parts.append(f"比例修正=[{scl[0]:.2f}, {scl[1]:.2f}, {scl[2]:.2f}]")
        if fix:
            parts.append(fix)
        if issues:
            parts.append(f"问题: {'; '.join(issues[:2])}")
        lines.append("  ".join(parts))

    return "\n".join(lines)
