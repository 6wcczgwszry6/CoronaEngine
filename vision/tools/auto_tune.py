"""
auto_tune.py — Parameter sweep for SSAT denoiser.

Sets SSAT_* environment variables and runs auto_iterate.py for each config.
Results logged to tools/scene_params/sweep_<scene>.tsv

Usage:
    python tools/auto_tune.py --scene spaceship_desktop4k --config quality
    python tools/auto_tune.py --scene spaceship_desktop4k --config quality --quick
"""

import argparse
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_eval(scene: str, config: str, params: dict, iteration: int) -> dict | None:
    env = os.environ.copy()
    for key, val in params.items():
        env[f"SSAT_{key.upper()}"] = str(val)

    change_desc = " ".join(f"{k}={v}" for k, v in params.items())
    cmd = [
        sys.executable, str(REPO_ROOT / "tools" / "auto_iterate.py"),
        "--scene", scene,
        "--config", config,
        "--change", f"tune: {change_desc}",
        "--skip-build",
        "--iteration", str(iteration),
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, env=env,
        cwd=str(REPO_ROOT), timeout=600,
    )

    for line in result.stdout.splitlines():
        if "frame_ms=" in line and "rmse=" in line:
            parts = {}
            for segment in line.split():
                if "=" in segment:
                    k, v = segment.split("=", 1)
                    try:
                        parts[k] = float(v)
                    except ValueError:
                        parts[k] = v
            return parts

    for line in result.stdout.splitlines():
        if "rmse=" in line:
            for segment in line.replace(",", " ").split():
                if segment.startswith("rmse="):
                    rmse = float(segment.split("=")[1])
                    return {"rmse": rmse, "frame_ms": 0.0}

    return None


def main():
    parser = argparse.ArgumentParser(description="SSAT parameter sweep")
    parser.add_argument("--scene", required=True)
    parser.add_argument("--config", default="quality", choices=["quality", "performance"])
    parser.add_argument("--quick", action="store_true", help="Reduced grid for fast sweep")
    args = parser.parse_args()

    out_dir = REPO_ROOT / "tools" / "scene_params"
    out_dir.mkdir(exist_ok=True)
    sweep_log = out_dir / f"sweep_{args.scene}_{args.config}.tsv"

    if args.quick:
        grid = {
            "sigma_lum": [2.0, 4.0, 8.0],
            "sigma_x": [1.0, 2.0, 4.0],
            "angular_range": [0.0, 0.1, 0.2],
            "angular_samples": [1, 3],
        }
    else:
        grid = {
            "sigma_lum": [1.0, 2.0, 3.0, 5.0, 8.0],
            "sigma_x": [0.5, 1.0, 2.0, 3.0, 5.0],
            "sigma_u": [0.1, 0.3, 0.5, 1.0],
            "angular_range": [0.0, 0.05, 0.1, 0.15, 0.25],
            "angular_samples": [1, 3, 5],
            "sigma_z": [10.0, 50.0, 100.0],
        }

    keys = list(grid.keys())
    values = list(grid.values())
    combos = list(itertools.product(*values))

    print(f"Sweep: {len(combos)} configurations for {args.scene} {args.config}")

    with sweep_log.open("w", encoding="utf-8") as f:
        header = "\t".join(keys + ["rmse", "frame_ms", "status"])
        f.write(header + "\n")

    best_rmse = 999.0
    best_params = {}
    iteration = 1000

    for i, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        print(f"[{i+1}/{len(combos)}] {params}")

        result = run_eval(args.scene, args.config, params, iteration + i)

        if result is None:
            print("  → FAILED")
            rmse = 999.0
            frame_ms = 0.0
            status = "fail"
        else:
            rmse = result.get("rmse", 999.0)
            frame_ms = result.get("frame_ms", result.get("average_frame_ms", 0.0))
            status = "ok"
            print(f"  → rmse={rmse:.6f} frame_ms={frame_ms:.2f}")

        with sweep_log.open("a", encoding="utf-8") as f:
            row = "\t".join([str(v) for v in combo] + [f"{rmse:.6f}", f"{frame_ms:.2f}", status])
            f.write(row + "\n")

        if rmse < best_rmse:
            best_rmse = rmse
            best_params = params.copy()
            best_params["rmse"] = rmse
            best_params["frame_ms"] = frame_ms

    print(f"\n{'='*60}")
    print(f"Best RMSE: {best_rmse:.6f}")
    print(f"Best params: {best_params}")

    best_file = out_dir / f"{args.scene}_{args.config}.json"
    best_file.write_text(json.dumps(best_params, indent=2), encoding="utf-8")
    print(f"Saved to {best_file}")


if __name__ == "__main__":
    main()
