"""Generate golden reference images for regression testing.

Renders each test scene with high SPP and saves as golden_image.exr.
Skips scenes that already have a golden image unless --force is specified.

Usage:
    python generate_golden.py                    # generate all missing golden images
    python generate_golden.py --scenes cbox      # specific scene only
    python generate_golden.py --force            # regenerate even if exists
    python generate_golden.py --spp 500          # custom SPP
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
OUTPUT_NAME = "golden_image.exr"


def find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CMakeLists.txt").exists() and (parent / "src").is_dir():
            return parent
    sys.exit("ERROR: cannot locate Vision project root")


def default_scene_root(project_root: Path) -> Path:
    return project_root.parent / "CoronaTestScenes" / "test_vision" / "render_scene"


def discover_scenes(scene_root: Path, scene_filter: list[str] | None) -> list[Path]:
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


def render_scene(exe: Path, scene_dir: Path, spp: int, *, force: bool) -> dict:
    """Render a single scene. Returns result dict."""
    scene_file = scene_dir / "vision_scene.json"
    output_file = scene_dir / OUTPUT_NAME
    result = {"scene": scene_dir.name, "status": "SKIP", "time": 0.0, "detail": ""}

    if not force and output_file.exists():
        result["detail"] = "already exists"
        return result

    print(f"  RENDER  {scene_dir.name}  (spp={spp})", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.Popen(
            [str(exe), "-s", str(scene_file), "-n", str(spp), "-o", OUTPUT_NAME],
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

        if proc.returncode == 0:
            render_str = f", render {render_time_ms / 1000.0:.1f}s" if render_time_ms else ""
            result["status"] = "OK"
            result["detail"] = f"wall {elapsed:.1f}s{render_str}"
            # Write golden_timing.json
            timing = {
                "spp": spp,
                "wall_time_sec": round(elapsed, 2),
                "render_time_sec": round(render_time_ms / 1000.0, 2) if render_time_ms else None,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            (scene_dir / "golden_timing.json").write_text(
                json.dumps(timing, indent=2), encoding="utf-8"
            )
        else:
            result["status"] = "FAIL"
            result["detail"] = f"exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        proc.kill()
        result["status"] = "FAIL"
        result["time"] = time.time() - t0
        result["detail"] = "TIMEOUT (600s)"

    return result


def write_report(report_path: Path, results: list[dict], spp: int,
                 exe: Path, elapsed_total: float) -> None:
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Golden Image Generation Report\n\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Executable**: {exe}\n")
        f.write(f"- **SPP**: {spp}\n")
        f.write(f"- **Total Time**: {elapsed_total:.1f}s\n\n")
        f.write(f"| Scene | Status | Time | Detail |\n")
        f.write(f"|-------|--------|------|--------|\n")
        for r in results:
            f.write(f"| {r['scene']} | {r['status']} | {r['time']:.1f}s | {r['detail']} |\n")
        ok = sum(1 for r in results if r["status"] == "OK")
        skip = sum(1 for r in results if r["status"] == "SKIP")
        fail = sum(1 for r in results if r["status"] == "FAIL")
        f.write(f"\n**Summary**: {ok} generated, {skip} skipped, {fail} failed\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate golden reference images")
    parser.add_argument("--build-dir", type=str, default=None,
                        help="Build directory (default: cmake-build-release)")
    parser.add_argument("--spp", type=int, default=DEFAULT_SPP,
                        help=f"Samples per pixel (default: {DEFAULT_SPP})")
    parser.add_argument("--scene-root", type=str, default=None,
                        help="Root directory containing scene folders")
    parser.add_argument("--scenes", nargs="*", default=None,
                        help="Specific scene names (default: all)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if golden_image.exr already exists")
    parser.add_argument("--report", type=str, default=None,
                        help="Report output path (default: tools/dev_verify/report_golden.md)")
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

    print(f"Generating golden images for {len(scenes)} scene(s) with {args.spp} spp")
    print(f"  exe: {exe}")
    print(f"  force: {args.force}")
    print()

    results = []
    t_total = time.time()
    for i, scene_dir in enumerate(scenes, 1):
        print(f"[{i}/{len(scenes)}] ", end="", flush=True)
        r = render_scene(exe, scene_dir, args.spp, force=args.force)
        results.append(r)
        print(f"  {r['status']:<6s} {r['scene']:<20s} {r['detail']}")
        sys.stdout.flush()

    elapsed_total = time.time() - t_total

    # Summary
    ok = sum(1 for r in results if r["status"] == "OK")
    skip = sum(1 for r in results if r["status"] == "SKIP")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    print(f"\nResults: {ok} generated, {skip} skipped, {fail} failed  ({elapsed_total:.1f}s)")

    # Write report
    report_path = Path(args.report) if args.report else (Path(__file__).resolve().parent / "report_golden.md")
    write_report(report_path, results, args.spp, exe, elapsed_total)
    print(f"Report: {report_path}")

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
