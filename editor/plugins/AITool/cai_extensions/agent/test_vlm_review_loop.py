"""离线自验：VLM 审查外回路（突击方案 §2.3vlm / ⟦COMMIT:5⟧）。

注入假 capture_fn / review_fn / engine_gate，不依赖引擎/VLM API。验收：
- 截图超时 → 记 timed_out、不中断整批（卡死源兜底）
- 截图/审查异常 → 记 skipped、不抛
- 产出 advisory（rotation/scale/issues），actionable 只挑有修正的
- 所有截图经 engine_gate.screenshot 串行收口
- 绝不改场景（本模块无 layout 写入口）

直接 `python test_vlm_review_loop.py` 运行。
"""
import sys
import os
import threading
import time
import shutil

sys.path.insert(0, os.path.dirname(__file__))
from vlm_review_loop import review_models_async, VlmReviewReport  # noqa: E402
import model_reviewer  # noqa: E402


class FakeGate:
    """记录截图是否经 gate。"""
    def __init__(self):
        self.screenshot_calls = 0

    def screenshot(self, fn, *args, **kwargs):
        self.screenshot_calls += 1
        return fn(*args, **kwargs)


def test_advisory_with_corrections():
    def capture(out_dir, name):
        return f"/shots/{name}"

    def review(shot_dir, name, mtype):
        # 兽头朝外 → 给旋转修正
        if name == "兽头":
            return {"overall": "WARN", "rotation_correction": [0, 180, 0],
                    "issues": ["朝向错误：背对房间"], "fix_suggestion": "旋转180度朝内"}
        return {"overall": "PASS"}

    gate = FakeGate()
    report = review_models_async(
        [{"actor_id": "兽头"}, {"actor_id": "桌子"}],
        capture_fn=capture, review_fn=review, engine_gate=gate,
    )
    assert len(report.advices) == 2
    actionable = report.actionable()
    ids = {a.actor_id for a in actionable}
    assert "兽头" in ids, "有旋转修正的应进 actionable"
    assert "桌子" not in ids, "PASS 无修正的不进 actionable"
    assert gate.screenshot_calls == 2, "每次截图都必须经 EngineWriteGate.screenshot"
    print("[OK] 产出 advisory + actionable 只挑有修正 + 截图经 gate 收口")


def test_screenshot_timeout_tolerated():
    def capture(out_dir, name):
        if name == "卡死模型":
            raise TimeoutError("截图超时模拟")
        return f"/shots/{name}"

    def review(shot_dir, name, mtype):
        return {"overall": "PASS"}

    report = review_models_async(
        [{"actor_id": "卡死模型"}, {"actor_id": "正常模型"}],
        capture_fn=capture, review_fn=review,
    )
    assert "卡死模型" in report.timed_out, "截图超时应记 timed_out"
    assert len(report.advices) == 1 and report.advices[0].actor_id == "正常模型", \
        "超时不应中断整批，正常模型仍审查"
    print("[OK] 截图超时被容忍（卡死源兜底），不中断整批")


def test_review_exception_skipped():
    def capture(out_dir, name):
        return f"/shots/{name}"

    def review(shot_dir, name, mtype):
        if name == "坏模型":
            raise RuntimeError("VLM API 失败")
        return {"overall": "PASS"}

    report = review_models_async(
        [{"actor_id": "坏模型"}, {"actor_id": "好模型"}],
        capture_fn=capture, review_fn=review,
    )
    assert "坏模型" in report.skipped, "审查异常应记 skipped"
    assert any(a.actor_id == "好模型" for a in report.advices)
    print("[OK] VLM 审查异常被跳过，不抛、不中断整批")


def test_no_screenshot_skipped():
    def capture(out_dir, name):
        return None  # 截图失败返回 None

    def review(shot_dir, name, mtype):
        raise AssertionError("无截图不应调 review")

    report = review_models_async(
        [{"actor_id": "无图"}],
        capture_fn=capture, review_fn=review,
    )
    assert "无图" in report.skipped
    assert not report.advices
    assert "未完成" in report.to_user_text()
    assert "未发现明显语义问题" not in report.to_user_text()
    print("[OK] 无截图跳过审查")


def test_empty_targets():
    report = review_models_async([], capture_fn=lambda d, n: None,
                                 review_fn=lambda s, n, t: {})
    assert isinstance(report, VlmReviewReport) and not report.advices
    print("[OK] 空目标安全返回")


class FakeCamera:
    def __init__(self, name="main", **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.position = [0, 0, 0]
        self.forward = [0, 0, 1]
        self.up = [0, 1, 0]
        self.fov = 45.0
        self.output_mode = kwargs.get("output_mode", "beauty")
        self.set_calls = 0

    def set(self, position, forward, world_up, fov):
        self.position = list(position)
        self.forward = list(forward)
        self.up = list(world_up)
        self.fov = fov
        self.set_calls += 1

    def get_output_mode(self):
        return self.output_mode

    def set_output_mode(self, mode):
        self.output_mode = mode

    def save_screenshot_sync(self, path):
        with open(path, "wb") as f:
            f.write(b"fake-png")
        return True


class FakeScene:
    def __init__(self, cameras=None):
        self.cameras = list(cameras or [])
        self.active = FakeCamera("main_camera")
        self.added = []

    def find_camera(self, name):
        if name is None:
            return self.active
        for camera in self.cameras:
            if getattr(camera, "name", None) == name:
                return camera
        return None

    def add_camera_to_scene(self, camera):
        self.cameras.append(camera)
        self.added.append(camera)

    def get_active_camera(self):
        return self.active


def _test_tmp_dir(name):
    root = os.path.abspath(os.path.join(os.getcwd(), "temp", "vlm_review_test"))
    path = os.path.join(root, name)
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    return path


def test_vlm_review_camera_reuses_existing():
    existing = FakeCamera(model_reviewer.VLM_REVIEW_CAMERA_NAME)
    scene = FakeScene([existing])
    camera = model_reviewer.get_or_create_vlm_review_camera(scene, camera_factory=FakeCamera)
    assert camera is existing
    assert not scene.added
    print("[OK] VLM review camera reuses existing camera")


def test_vlm_review_camera_created_without_switching_active():
    scene = FakeScene()
    active_before = scene.get_active_camera()
    camera = model_reviewer.get_or_create_vlm_review_camera(scene, camera_factory=FakeCamera)
    assert camera is scene.added[0]
    assert camera.name == model_reviewer.VLM_REVIEW_CAMERA_NAME
    assert scene.get_active_camera() is active_before
    assert camera.kwargs.get("view_open") is False
    assert camera.kwargs.get("deletable") is False
    print("[OK] VLM review camera created without switching active camera")


def test_vlm_capture_uses_review_camera_not_main():
    scene = FakeScene()
    review_camera = FakeCamera(model_reviewer.VLM_REVIEW_CAMERA_NAME)
    main_before = list(scene.active.position)

    def pose(center, distance, az, elevation):
        return {"position": [az / 90.0, 2.0, 3.0], "forward": [0, 0, -1], "up": [0, 1, 0]}

    tmp = _test_tmp_dir("capture")
    try:
        result = model_reviewer._capture_with_review_camera(scene, review_camera, tmp, "sample", pose)
        assert result == tmp
        assert review_camera.set_calls == 4
        assert scene.active.position == main_before
        assert os.path.exists(os.path.join(tmp, "sample_az000.png"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[OK] VLM capture uses review camera and leaves main camera untouched")


def test_screenshot_waits_for_late_png_write():
    camera = FakeCamera(model_reviewer.VLM_REVIEW_CAMERA_NAME)

    def delayed_save(path):
        def writer():
            time.sleep(0.25)
            with open(path, "wb") as f:
                f.write(b"late-png")
        threading.Thread(target=writer, daemon=True).start()
        return True

    camera.save_screenshot_sync = delayed_save
    tmp = _test_tmp_dir("late")
    try:
        path = os.path.join(tmp, "late.png")
        assert model_reviewer._save_camera_screenshot_with_timeout(camera, path, timeout=1.0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[OK] VLM screenshot waits until late PNG is actually on disk")


if __name__ == "__main__":
    test_advisory_with_corrections()
    test_screenshot_timeout_tolerated()
    test_review_exception_skipped()
    test_no_screenshot_skipped()
    test_empty_targets()
    test_vlm_review_camera_reuses_existing()
    test_vlm_review_camera_created_without_switching_active()
    test_vlm_capture_uses_review_camera_not_main()
    test_screenshot_waits_for_late_png_write()
    print("\n=== COMMIT 5 VLM 外回路 ALL PASS ===")
