"""Render golden or test images for regression testing.

Usage:
    python regression_render.py                          # render golden_image.exr for all scenes
    python regression_render.py --output-name test_image.exr  # render test images
    python regression_render.py --scenes cbox kitchen    # specific scenes only
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

DEFAULT_SPP = 200
DEFAULT_OUTPUT = "golden_image.exr"


def find_project_root() -> Path:
    """Walk up from this script to find the Vision project root (contains CMakeLists.txt)."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CMakeLists.txt").exists() and (parent / "src").is_dir():
            return parent
    sys.exit("ERROR: cannot locate Vision project root")


def default_scene_root(project_root: Path) -> Path:
    return project_root.parent / "CoronaTestScenes" / "test_vision" / "render_scene"


def discover_scenes(scene_root: Path, scene_filter: list[str] | None) -> list[Path]:
    """Return sorted list of scene dirs that contain vision_scene.json."""
    scenes = []
    for d in sorted(scene_root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "vision_scene.json").exists():
            continue
        if scene_filter and d.name not in scene_filter:
            continue
        scenes.append(d)
    return scenes


def render_scene(exe: Path, scene_dir: Path, spp: int, output_name: str,
                 *, skip_existing: bool = False) -> dict:
    """Render a single scene. Returns result dict."""
    scene_file = scene_dir / "vision_scene.json"
    output_file = scene_dir / output_name
    result = {"scene": scene_dir.name, "status": "SKIP", "time": 0.0, "detail": ""}

    if skip_existing and output_file.exists():
        print(f"  SKIP  {scene_dir.name} (already exists)")
        result["detail"] = "already exists"
        return result

    print(f"  RENDER  {scene_dir.name}  \u2192  {output_name}  (spp={spp})", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            [str(exe), "-s", str(scene_file), "-n", str(spp), "-o", output_name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        output_lines = []

        def _reader():
            for line in proc.stdout:
                output_lines.append(line)

        reader = threading.Thread(target=_reader, daemon=True)
        reader.start()

        while proc.poll() is None:
            elapsed_so_far = time.time() - t0
            print(f"    rendering {scene_dir.name}... {elapsed_so_far:.0f}s", end="\r", flush=True)
            time.sleep(2)

        reader.join(timeout=5)
        print(" " * 60, end="\r")  # clear progress line

        elapsed = time.time() - t0
        result["time"] = elapsed
        stdout_text = "".join(output_lines)

        # Parse pure render time from C++ output
        render_time_ms = None
        m = re.search(r"VISION_RENDER_TIME_MS=([\d.]+)", stdout_text)
        if m:
            render_time_ms = float(m.group(1))
        result["render_time"] = render_time_ms / 1000.0 if render_time_ms else None

        if proc.returncode != 0:
            print(f"  FAIL  {scene_dir.name}  exit code {proc.returncode}")
            result["status"] = "FAIL"
            result["detail"] = f"exit code {proc.returncode}"
        else:
            render_str = f", render {render_time_ms / 1000.0:.1f}s" if render_time_ms else ""
            print(f"  OK    {scene_dir.name}  wall {elapsed:.1f}s{render_str}")
            result["status"] = "OK"
            result["detail"] = f"{elapsed:.1f}s"
            # Write timing JSON
            timing_name = output_name.replace(".exr", "_timing.json")
            timing = {
                "spp": spp,
                "wall_time_sec": round(elapsed, 2),
                "render_time_sec": round(render_time_ms / 1000.0, 2) if render_time_ms else None,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            (scene_dir / timing_name).write_text(
                json.dumps(timing, indent=2), encoding="utf-8"
            )
    except subprocess.TimeoutExpired:
        proc.kill()
        result["status"] = "FAIL"
        result["time"] = time.time() - t0
        result["detail"] = "TIMEOUT (600s)"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Render regression images")
    parser.add_argument("--build-dir", type=str, default=None,
                        help="Build directory (default: cmake-build-release)")
    parser.add_argument("--spp", type=int, default=DEFAULT_SPP,
                        help=f"Samples per pixel (default: {DEFAULT_SPP})")
    parser.add_argument("--output-name", type=str, default=DEFAULT_OUTPUT,
                        help=f"Output filename (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--scene-root", type=str, default=None,
                        help="Root directory containing scene folders")
    parser.add_argument("--scenes", nargs="*", default=None,
                        help="Specific scene names to render (default: all)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip scenes that already have the output file")
    args = parser.parse_args()

    project_root = find_project_root()
    build_dir = Path(args.build_dir) if args.build_dir else project_root / "cmake-build-release"
    exe = build_dir / "bin" / "vision-gui.exe"

    if not exe.exists():
        sys.exit(f"ERROR: {exe} not found. Build the project first.")

    scene_root = Path(args.scene_root) if args.scene_root else default_scene_root(project_root)
    if not scene_root.is_dir():
        sys.exit(f"ERROR: scene root not found: {scene_root}")

    scenes = discover_scenes(scene_root, args.scenes)
    if not scenes:
        sys.exit("ERROR: no matching scenes found")

    print(f"Rendering {len(scenes)} scene(s) with {args.spp} spp → {args.output_name}")
    print(f"  exe: {exe}")
    print()

    results = []
    t_total = time.time()
    for i, scene_dir in enumerate(scenes, 1):
        print(f"[{i}/{len(scenes)}] ", end="", flush=True)
        r = render_scene(exe, scene_dir, args.spp, args.output_name,
                         skip_existing=args.skip_existing)
        results.append(r)

    elapsed_total = time.time() - t_total
    ok_count = sum(1 for r in results if r["status"] == "OK")
    skip_count = sum(1 for r in results if r["status"] == "SKIP")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    print()
    print(f"Results: {ok_count} rendered, {skip_count} skipped, {fail_count} failed  ({elapsed_total:.1f}s)")

    # Write report
    report_path = Path(__file__).resolve().parent / f"report_render_{args.output_name.replace('.exr','')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Render Report ({args.output_name})\n\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Executable**: {exe}\n")
        f.write(f"- **SPP**: {args.spp}\n")
        f.write(f"- **Output**: {args.output_name}\n")
        f.write(f"- **Total Time**: {elapsed_total:.1f}s\n\n")
        f.write(f"| Scene | Status | Time | Detail |\n")
        f.write(f"|-------|--------|------|--------|\n")
        for r in results:
            f.write(f"| {r['scene']} | {r['status']} | {r['time']:.1f}s | {r['detail']} |\n")
        f.write(f"\n**Summary**: {ok_count} rendered, {skip_count} skipped, {fail_count} failed\n")
    print(f"Report: {report_path}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
