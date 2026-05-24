"""
P0 前置验证: 引擎多场景并发能力测试

用法: 在引擎运行时，从 CabbageEditor 目录执行:
  python test_engine_concurrency.py

验证:
  1. 3 线程同时 get_or_create 不同 scene_id → 是否崩溃/报错
  2. 每个 scene 能否正常 add_model (轻量测试)
  3. GPU 显存是否爆 (需手动观察任务管理器)
"""
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from CoronaCore.core.managers import scene_manager
from CoronaCore.core.corona_editor import CoronaEditor
_CoronaEngine = CoronaEditor.CoronaEngine


class ConcurrencyTestResult:
    def __init__(self):
        self.success = 0
        self.failed = 0
        self.errors = []
        self._lock = threading.Lock()

    def record_success(self, thread_name):
        with self._lock:
            self.success += 1
            print(f"  [OK] {thread_name}")

    def record_error(self, thread_name, error):
        with self._lock:
            self.failed += 1
            self.errors.append((thread_name, str(error)))
            print(f"  [FAIL] {thread_name}: {error}")


results = ConcurrencyTestResult()
barrier = threading.Barrier(3, timeout=10)  # 3个线程同时释放


def test_get_or_create(scene_name: str):
    """测试: get_or_create 不同 scene_name 并发调用"""
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] waiting at barrier...")
    try:
        barrier.wait()  # 所有线程同时开始
    except threading.BrokenBarrierError:
        pass

    try:
        t0 = time.time()
        scene = scene_manager.get_or_create(scene_name)
        elapsed = time.time() - t0

        # 基本验证
        assert scene is not None, "scene is None"
        assert scene.route == scene_name, f"route mismatch: {scene.route} vs {scene_name}"
        assert scene.engine_scene is not None, "engine_scene is None"

        # 验证 scene 可用: 检查 camera
        cameras = scene.get_cameras()
        print(f"  [{thread_name}] scene={scene_name} cameras={len(cameras)} elapsed={elapsed:.3f}s")
        results.record_success(thread_name)

    except Exception as e:
        results.record_error(thread_name, e)


def test_actor_count(scene_names):
    """验证: 每个 scene 独立, 添加 actor 不互相干扰"""
    print("\n--- Actor isolation test ---")
    scenes = {}
    for name in scene_names:
        s = scene_manager.get(name)
        if s is None:
            print(f"  [SKIP] scene {name} not found")
            continue
        # 注意: add_model 需要实际的模型文件, 这里只检查 scene 独立性
        actor_count = len(s.get_actors())
        print(f"  scene {os.path.basename(name)}: {actor_count} actors")
        scenes[name] = s

    # 验证 scene 对象不共享内部状态
    if len(scenes) >= 2:
        names = list(scenes.keys())
        s1, s2 = scenes[names[0]], scenes[names[1]]
        assert s1 is not s2, "scenes are same object!"
        assert s1.engine_scene is not s2.engine_scene, "engine_scene objects are same!"
        print(f"  [OK] scenes {names[0]} and {names[1]} are independent objects")


def main():
    print("=" * 60)
    print("P0: Engine Multi-Scene Concurrency Test")
    print("=" * 60)

    import tempfile
    _tmpdir = tempfile.mkdtemp(prefix="p0_test_")
    # 使用绝对路径，避免 read_data() 访问 active_project_path
    _base = os.path.join(_tmpdir, "Scene")
    os.makedirs(_base, exist_ok=True)

    scene_names = [
        os.path.join(_base, "test_concurrent_scene_a.json"),
        os.path.join(_base, "test_concurrent_scene_b.json"),
        os.path.join(_base, "test_concurrent_scene_c.json"),
    ]

    # 清理旧测试数据
    for name in scene_names:
        if scene_manager.has(name):
            scene_manager.remove(name)

    # Test 1: 并发 get_or_create
    print("\n--- Test 1: Concurrent get_or_create (3 threads) ---")
    threads = []
    for i, name in enumerate(scene_names):
        t = threading.Thread(
            target=test_get_or_create,
            args=(name,),
            name=f"Worker-{i}",
        )
        threads.append(t)

    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    total_elapsed = time.time() - t0

    print(f"\n  Total: {results.success}/{len(scene_names)} succeeded, "
          f"{results.failed} failed, elapsed={total_elapsed:.3f}s")

    # Test 2: Actor 隔离
    print("\n--- Test 2: Actor isolation ---")
    test_actor_count(scene_names)

    # Test 3: scene_manager 状态一致性
    print("\n--- Test 3: State consistency ---")
    all_scenes = scene_manager.list_all()
    test_names_found = [n for n in scene_names if n in all_scenes]
    print(f"  Expected 3 scenes, found {len(test_names_found)}: {test_names_found}")
    if len(test_names_found) == 3:
        print("  [OK] all 3 scenes registered")
    else:
        print(f"  [WARN] missing: {set(scene_names) - set(test_names_found)}")

    # 清理
    for name in scene_names:
        if scene_manager.has(name):
            scene_manager.remove(name)

    # 总结
    print("\n" + "=" * 60)
    if results.failed == 0:
        print("RESULT: PASS — Engine supports concurrent multi-scene creation")
        print(f"MAX_PARALLEL_SCENES can be >= 3")
    else:
        print(f"RESULT: FAIL — {results.failed} errors found")
        for thread_name, error in results.errors:
            print(f"  - {thread_name}: {error}")
        print("Check if engine supports holding multiple scenes simultaneously")
    print("=" * 60)

    return results.failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
