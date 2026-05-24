"""Compare rendered test images against golden images.

Metrics:
  - RMSE              pixel-level root-mean-square error
  - Downsampled RMSE  RMSE after 8x8 box averaging (noise-robust, SPP-tolerant)
  - Image Mean        global mean (bias detector)
  - Per-channel Mean  R/G/B means (per-channel bias detector)

Requires: OpenCV with OPENCV_IO_ENABLE_OPENEXR=1, numpy.

Usage:
    python regression_compare.py                            # compare all scenes
    python regression_compare.py --scenes cbox kitchen      # specific scenes
    python regression_compare.py --threshold 0.02           # custom threshold
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# Enable OpenCV EXR support
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

DEFAULT_GOLDEN = "golden_image.exr"
DEFAULT_TEST = "test_image.exr"
DEFAULT_THRESHOLD = 0.04


def find_project_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "CMakeLists.txt").exists() and (parent / "src").is_dir():
            return parent
    sys.exit("ERROR: cannot locate Vision project root")


def default_scene_root(project_root: Path) -> Path:
    return project_root.parent / "CoronaTestScenes" / "test_vision" / "render_scene"


def read_exr(path: Path) -> np.ndarray | None:
    """Read EXR file as float32 numpy array. Returns None on failure."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    return img.astype(np.float32)


def compute_rmse(a: np.ndarray, b: np.ndarray) -> float:
    """Compute Root Mean Square Error between two images."""
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
    diff = (a - b).astype(np.float64)
    return float(np.sqrt(np.mean(diff * diff)))


def downsample_block(img: np.ndarray, block: int = 8) -> np.ndarray:
    """Downsample image by block-averaging (box filter).

    Crops to the nearest multiple of *block* then reshapes+averages.
    Equivalent to increasing SPP by block² for noise reduction.
    """
    h, w = img.shape[:2]
    h2, w2 = (h // block) * block, (w // block) * block
    cropped = img[:h2, :w2].astype(np.float64)
    if cropped.ndim == 3:
        c = cropped.shape[2]
        return cropped.reshape(h2 // block, block, w2 // block, block, c).mean(axis=(1, 3)).astype(np.float32)
    return cropped.reshape(h2 // block, block, w2 // block, block).mean(axis=(1, 3)).astype(np.float32)


def per_channel_mean(img: np.ndarray) -> list[float]:
    """Return per-channel mean as [R, G, B] (converted from OpenCV BGR/BGRA)."""
    f = img.astype(np.float64)
    if f.ndim == 3:
        # OpenCV loads as BGR or BGRA; extract B,G,R and return as R,G,B
        b = float(f[:, :, 0].mean())
        g = float(f[:, :, 1].mean())
        r = float(f[:, :, 2].mean())
        return [r, g, b]
    return [float(f.mean())]


def load_timing(scene_dir: Path, name: str) -> dict | None:
    p = scene_dir / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def compare_scene(scene_dir: Path, golden_name: str, test_name: str,
                  threshold: float) -> dict:
    """Compare golden vs test for one scene. Returns result dict."""
    golden_path = scene_dir / golden_name
    test_path = scene_dir / test_name
    result = {"scene": scene_dir.name, "status": "SKIP", "rmse": None, "detail": ""}

    if not golden_path.exists():
        result["detail"] = f"golden not found: {golden_name}"
        return result

    if not test_path.exists():
        result["detail"] = f"test not found: {test_name}"
        return result

    golden = read_exr(golden_path)
    test = read_exr(test_path)

    if golden is None:
        result["status"] = "ERROR"
        result["detail"] = "failed to read golden EXR"
        return result
    if test is None:
        result["status"] = "ERROR"
        result["detail"] = "failed to read test EXR"
        return result

    try:
        rmse = compute_rmse(golden, test)
    except ValueError as e:
        result["status"] = "ERROR"
        result["detail"] = str(e)
        return result

    result["rmse"] = rmse
    result["golden_mean"] = float(np.mean(golden.astype(np.float64)))
    result["test_mean"] = float(np.mean(test.astype(np.float64)))

    # Per-channel mean (already returned as RGB)
    result["golden_rgb"] = per_channel_mean(golden)
    result["test_rgb"] = per_channel_mean(test)

    # Downsampled RMSE (8x8 block average — robust to noise)
    ds_golden = downsample_block(golden, 8)
    ds_test = downsample_block(test, 8)
    result["ds_rmse"] = compute_rmse(ds_golden, ds_test)

    # Pass/fail based on DS8 RMSE (noise-robust, tolerant to SPP differences)
    ds = result["ds_rmse"]
    if ds <= threshold:
        result["status"] = "PASS"
        result["detail"] = f"DS8 {ds:.6f} <= {threshold}"
    else:
        result["status"] = "FAIL"
        result["detail"] = f"DS8 {ds:.6f} > {threshold}"

    # Load timing data
    golden_t = load_timing(scene_dir, "golden_timing.json")
    test_timing_name = test_name.replace(".exr", "_timing.json")
    test_t = load_timing(scene_dir, test_timing_name)

    result["golden_render_time"] = golden_t["render_time_sec"] if golden_t and golden_t.get("render_time_sec") else None
    result["test_render_time"] = test_t["render_time_sec"] if test_t and test_t.get("render_time_sec") else None
    result["golden_spp"] = golden_t["spp"] if golden_t else None
    result["test_spp"] = test_t["spp"] if test_t else None

    # Per-SPP time in milliseconds
    result["golden_ms_per_spp"] = None
    result["test_ms_per_spp"] = None
    if result["golden_render_time"] and result["golden_spp"]:
        result["golden_ms_per_spp"] = result["golden_render_time"] * 1000.0 / result["golden_spp"]
    if result["test_render_time"] and result["test_spp"]:
        result["test_ms_per_spp"] = result["test_render_time"] * 1000.0 / result["test_spp"]

    # Normalized ratio: (test_ms_per_spp) / (golden_ms_per_spp)
    result["time_ratio"] = None
    if result["golden_ms_per_spp"] and result["test_ms_per_spp"]:
        result["time_ratio"] = result["test_ms_per_spp"] / result["golden_ms_per_spp"]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare regression images")
    parser.add_argument("--golden", type=str, default=DEFAULT_GOLDEN,
                        help=f"Golden image filename (default: {DEFAULT_GOLDEN})")
    parser.add_argument("--test", type=str, default=DEFAULT_TEST,
                        help=f"Test image filename (default: {DEFAULT_TEST})")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"DS8 RMSE threshold (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--scene-root", type=str, default=None,
                        help="Root directory containing scene folders")
    parser.add_argument("--scenes", nargs="*", default=None,
                        help="Specific scene names (default: all)")
    args = parser.parse_args()

    project_root = find_project_root()
    scene_root = Path(args.scene_root) if args.scene_root else default_scene_root(project_root)

    if not scene_root.is_dir():
        sys.exit(f"ERROR: scene root not found: {scene_root}")

    # Discover scenes (only dirs that contain vision_scene.json)
    scenes = []
    for d in sorted(scene_root.iterdir()):
        if not d.is_dir():
            continue
        if not (d / "vision_scene.json").exists():
            continue
        if args.scenes and d.name not in args.scenes:
            continue
        scenes.append(d)

    if not scenes:
        sys.exit("ERROR: no matching scenes found")

    print(f"Comparing {len(scenes)} scene(s)  golden={args.golden}  test={args.test}  threshold={args.threshold}")
    print()

    results = []
    for scene_dir in scenes:
        r = compare_scene(scene_dir, args.golden, args.test, args.threshold)
        results.append(r)
        tag = r["status"].ljust(5)
        rmse_str = f"RMSE={r['rmse']:.6f}" if r["rmse"] is not None else ""
        ds_str = f"  ds8={r['ds_rmse']:.6f}" if r.get("ds_rmse") is not None else ""
        rgb_str = ""
        g_rgb = r.get("golden_rgb", [])
        t_rgb = r.get("test_rgb", [])
        if len(g_rgb) == 3 and len(t_rgb) == 3:
            rgb_str = (f"  gRGB=({g_rgb[0]:.4f},{g_rgb[1]:.4f},{g_rgb[2]:.4f})"
                       f"  tRGB=({t_rgb[0]:.4f},{t_rgb[1]:.4f},{t_rgb[2]:.4f})")
        perf_parts = []
        if r.get("golden_ms_per_spp") is not None:
            perf_parts.append(f"golden={r['golden_ms_per_spp']:.1f}ms/spp")
        if r.get("test_ms_per_spp") is not None:
            perf_parts.append(f"test={r['test_ms_per_spp']:.1f}ms/spp")
        if r.get("time_ratio") is not None:
            perf_parts.append(f"ratio={r['time_ratio']:.2f}x")
        perf_str = f"  [{', '.join(perf_parts)}]" if perf_parts else ""
        print(f"  {tag}  {r['scene']:<20s}  {rmse_str}{ds_str}{rgb_str}{perf_str}")

    # Summary
    print()
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    print(f"Results: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped")

    # Write report
    report_path = Path(__file__).resolve().parent / "report_regression.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Regression Comparison Report\n\n")
        f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **DS8 RMSE Threshold**: {args.threshold}\n")
        f.write(f"- **Golden**: {args.golden}\n")
        f.write(f"- **Test**: {args.test}\n\n")
        f.write(f"| Scene | Status | RMSE | DS8 RMSE | Golden RGB | Test RGB | Golden (ms/spp) | Test (ms/spp) | Ratio | Detail |\n")
        f.write(f"|-------|--------|------|----------|------------|----------|-----------------|---------------|-------|--------|\n")
        for r in results:
            rmse_str = f"{r['rmse']:.6f}" if r['rmse'] is not None else "-"
            ds_str = f"{r['ds_rmse']:.6f}" if r.get('ds_rmse') is not None else "-"
            g_rgb = r.get('golden_rgb', [])
            t_rgb = r.get('test_rgb', [])
            g_rgb_str = f"({g_rgb[0]:.4f}, {g_rgb[1]:.4f}, {g_rgb[2]:.4f})" if len(g_rgb) == 3 else "-"
            t_rgb_str = f"({t_rgb[0]:.4f}, {t_rgb[1]:.4f}, {t_rgb[2]:.4f})" if len(t_rgb) == 3 else "-"
            g_ms = f"{r['golden_ms_per_spp']:.1f}" if r.get('golden_ms_per_spp') else "-"
            t_ms = f"{r['test_ms_per_spp']:.1f}" if r.get('test_ms_per_spp') else "-"
            ratio_str = f"{r['time_ratio']:.2f}x" if r.get('time_ratio') else "-"
            f.write(f"| {r['scene']} | {r['status']} | {rmse_str} | {ds_str} | {g_rgb_str} | {t_rgb_str} | {g_ms} | {t_ms} | {ratio_str} | {r['detail']} |\n")
        f.write(f"\n**Summary**: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped\n")
    print(f"Report: {report_path}")

    if failed > 0 or errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
