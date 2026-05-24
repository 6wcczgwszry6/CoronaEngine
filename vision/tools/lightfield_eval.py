import argparse
import json
import subprocess
import sys
from pathlib import Path

CANONICAL_GT_SPP = 4096
CANONICAL_OURS_SPP = 1


def build_exe(build_dir: Path, exe_name: str) -> Path:
    return build_dir / "bin" / exe_name


def parse_wrapper_output(stdout: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def relative_scene_name(scene: Path, repo_root: Path) -> str:
    try:
        return scene.relative_to(repo_root).as_posix()
    except ValueError:
        return scene.name


def append_results_row(
    results_log: Path,
    *,
    iteration: int,
    status: str,
    change: str,
    verify_scene: str,
    save_spp: int,
    golden_spp: int,
    rmse: float,
    average_frame_ms: float,
    average_fps: float,
    guard_frame_ms: float,
    notes: str,
) -> None:
    results_log.parent.mkdir(parents=True, exist_ok=True)
    if not results_log.exists():
        results_log.write_text(
            "iteration\tstatus\tchange\tverify_scene\tsave_spp\tgolden_spp\trmse\taverage_frame_ms\taverage_fps\tguard_frame_ms\tnotes\n",
            encoding="utf-8",
        )
    row = "\t".join(
        [
            str(iteration),
            status,
            change,
            verify_scene,
            str(save_spp),
            str(golden_spp),
            f"{rmse:.6f}",
            f"{average_frame_ms:.6f}",
            f"{average_fps:.6f}",
            f"{guard_frame_ms:.6f}",
            notes,
        ]
    )
    with results_log.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(row + "\n")


def run_eval(
    exe: Path,
    runtime_dir: Path,
    scene: Path,
    output: Path,
    metrics: Path,
    reference: Path | None,
    save_spp: int,
    warmup: int,
    profile: int,
    timeout_sec: int,
    disable_denoiser: bool,
    stage_profile: bool,
) -> dict:
    repo_root = Path(__file__).resolve().parent.parent
    wrapper = repo_root / "tools" / "run_with_timeout.ps1"
    app_args = [
        "-r",
        str(runtime_dir),
        "-m",
        "cli",
        "-s",
        str(scene),
        "--save-spp",
        str(save_spp),
        "--warmup-frames",
        str(warmup),
        "--profile-frames",
        str(profile),
        "--metrics-file",
        str(metrics),
        "-o",
        str(output),
    ]
    if disable_denoiser:
        app_args.extend(["--disable-denoiser", "true"])
    if stage_profile:
        app_args.extend(["--stage-profile", "true"])
    if reference is not None:
        app_args.extend(["--rmse-reference", str(reference)])
    app_args_expr = ",".join(ps_quote(arg) for arg in app_args)
    command = (
        f"& {ps_quote(str(wrapper))} "
        f"-FilePath {ps_quote(str(exe))} "
        f"-WorkingDirectory {ps_quote(str(runtime_dir))} "
        f"-TimeoutSec {timeout_sec} "
        f"-ArgumentList @({app_args_expr})"
    )
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
    ]
    completed = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    wrapper_info = parse_wrapper_output(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError(
            "evaluation failed\n"
            f"returncode={completed.returncode}\n"
            f"stdout={wrapper_info.get('stdout', '')}\n"
            f"stderr={wrapper_info.get('stderr', '')}\n"
            f"wrapper_stdout={completed.stdout}\n"
            f"wrapper_stderr={completed.stderr}"
        )
    return json.loads(metrics.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless light-field evaluation helper.")
    parser.add_argument("--build-dir", default="cmake-build-codex-msvc3")
    parser.add_argument("--runtime-dir")
    parser.add_argument("--scene", required=True)
    parser.add_argument("--artifact-dir", default="eval-out")
    parser.add_argument("--save-spp", type=int, default=64)
    parser.add_argument("--warmup", type=int, default=8)
    parser.add_argument("--profile", type=int, default=32)
    parser.add_argument("--timeout-sec", type=int, default=600)
    parser.add_argument("--disable-denoiser", action="store_true")
    parser.add_argument("--stage-profile", action="store_true")
    parser.add_argument("--golden", action="store_true")
    parser.add_argument("--reference")
    parser.add_argument(
        "--canonical-mode",
        choices=["gt", "ours"],
        help="Apply the retained paper-scale render contract: GT=4096 spp accumulation+denoiser off, Ours=1 spp + SSAT.",
    )
    parser.add_argument("--results-log")
    parser.add_argument("--result-iteration", type=int)
    parser.add_argument("--result-status")
    parser.add_argument("--result-change")
    parser.add_argument("--golden-spp", type=int)
    parser.add_argument("--guard-frame-ms", type=float)
    parser.add_argument("--result-notes", default="")
    parser.add_argument(
        "--metric-key",
        choices=["warmup_frames", "profile_frames", "average_frame_ms", "average_fps", "rmse", "output_file"],
        help="Print only the selected metric instead of the full JSON payload.",
    )
    args = parser.parse_args()

    build_dir = Path(args.build_dir).resolve()
    exe = build_exe(build_dir, "vision-eval.exe")
    if not exe.exists():
        raise FileNotFoundError(f"missing evaluation binary: {exe}")
    runtime_dir = Path(args.runtime_dir).resolve() if args.runtime_dir else exe.parent
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parent.parent
    scene_path = Path(args.scene).resolve()

    if args.canonical_mode == "gt":
        args.golden = True
        args.save_spp = CANONICAL_GT_SPP
        args.disable_denoiser = True
    elif args.canonical_mode == "ours":
        args.golden = False
        args.save_spp = CANONICAL_OURS_SPP

    scene_name = scene_path.stem
    image_ext = ".png"

    if args.golden:
        output = artifact_dir / f"{scene_name}_golden{image_ext}"
        metrics = artifact_dir / f"{scene_name}_golden_metrics.json"
        result = run_eval(
            exe,
            runtime_dir,
            scene_path,
            output,
            metrics,
            None,
            args.save_spp,
            args.warmup,
            args.profile,
            args.timeout_sec,
            args.disable_denoiser,
            args.stage_profile,
        )
    else:
        output = artifact_dir / f"{scene_name}_output{image_ext}"
        metrics = artifact_dir / f"{scene_name}_metrics.json"
        reference = Path(args.reference).resolve() if args.reference else artifact_dir / f"{scene_name}_golden{image_ext}"
        if args.canonical_mode == "ours" and not reference.exists():
            raise FileNotFoundError(f"canonical ours run requires a GT reference PNG: {reference}")
        result = run_eval(
            exe,
            runtime_dir,
            scene_path,
            output,
            metrics,
            reference,
            args.save_spp,
            args.warmup,
            args.profile,
            args.timeout_sec,
            args.disable_denoiser,
            args.stage_profile,
        )

    result["save_spp"] = args.save_spp
    result["canonical_mode"] = args.canonical_mode or ("gt" if args.golden else "custom")
    result["disable_denoiser"] = args.disable_denoiser
    result["verify_scene"] = relative_scene_name(scene_path, repo_root)

    if args.results_log:
        missing = [
            name
            for name, value in [
                ("--result-iteration", args.result_iteration),
                ("--result-status", args.result_status),
                ("--result-change", args.result_change),
                ("--golden-spp", args.golden_spp),
                ("--guard-frame-ms", args.guard_frame_ms),
            ]
            if value is None
        ]
        if missing:
            raise ValueError(f"results logging requires: {', '.join(missing)}")
        append_results_row(
            Path(args.results_log).resolve(),
            iteration=args.result_iteration,
            status=args.result_status,
            change=args.result_change,
            verify_scene=result["verify_scene"],
            save_spp=args.save_spp,
            golden_spp=args.golden_spp,
            rmse=float(result.get("rmse", 0.0)),
            average_frame_ms=float(result["average_frame_ms"]),
            average_fps=float(result["average_fps"]),
            guard_frame_ms=float(args.guard_frame_ms),
            notes=args.result_notes,
        )

    if args.metric_key:
        sys.stdout.write(f"{result[args.metric_key]}\n")
        return

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
