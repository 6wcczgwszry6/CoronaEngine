from __future__ import annotations

import argparse
import sys
from pathlib import Path

from horizon_workspace import ensure_workspace, update_workspace
from workflow import (
    CONFIGURATIONS,
    DEFAULT_CONFIGURATION,
    CommandError,
    build_dir,
    clean_repo,
    cmake_build,
    cmake_configure,
    conan_install,
    run_command,
    safe_remove,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = "corona_engine"
LOCAL_RECIPES = (
    "conan/recipes/ktm",
    "conan/recipes/pfr",
    "conan/recipes/slang",
    "conan/recipes/vulkan-memory-allocator",
    "conan/recipes/astc-encoder",
    "conan/recipes/cef-binary",
    "conan/recipes/ffmpeg",
)
RECIPE_TOGGLE_ENV = "CORONA_CONAN_EXPORT_LOCAL_RECIPES"


def conan_options(targets: list[str]) -> list[str]:
    options: list[str] = []
    lowered = [target.lower() for target in targets]
    if any("test" in target for target in lowered):
        options.append("&:with_tests=True")
    if any("vision" in target or "oidn" in target for target in lowered):
        options.append("&:with_vision=True")
    if any("oidn" in target for target in lowered):
        options.append("&:with_oidn=True")
    return options


def install(configuration: str, targets: list[str], *, update: bool = False) -> None:
    ensure_workspace(REPO_ROOT)
    conan_install(
        REPO_ROOT,
        configuration,
        options=conan_options(targets),
        recipes=LOCAL_RECIPES,
        recipe_toggle_env=RECIPE_TOGGLE_ENV,
        update=update,
    )


def execute(args: argparse.Namespace) -> None:
    targets = args.targets or [DEFAULT_TARGET]
    target = targets[0]
    configuration = args.configuration
    if args.command == "status":
        run_command(("git", "status", "--short", "--branch"), cwd=REPO_ROOT)
        lock = ensure_workspace(REPO_ROOT)
        print(f"Horizon: {lock.commit} ({lock.ref})")
        run_command(("conan", "--version"), cwd=REPO_ROOT)
        run_command(("cmake", "--list-presets"), cwd=REPO_ROOT)
    elif args.command in {"install", "_bootstrap"}:
        install(configuration, targets)
    elif args.command == "configure":
        install(configuration, targets)
        cmake_configure(REPO_ROOT, configuration)
    elif args.command == "build":
        install(configuration, targets)
        cmake_configure(REPO_ROOT, configuration)
        cmake_build(REPO_ROOT, configuration, target)
    elif args.command == "build-fast":
        ensure_workspace(REPO_ROOT)
        cmake_build(REPO_ROOT, configuration, target)
    elif args.command == "rebuild":
        safe_remove(REPO_ROOT, build_dir(REPO_ROOT, configuration))
        install(configuration, targets)
        cmake_configure(REPO_ROOT, configuration)
        cmake_build(REPO_ROOT, configuration, target)
    elif args.command == "update":
        update_workspace(REPO_ROOT)
        install(configuration, targets, update=True)
        cmake_configure(REPO_ROOT, configuration)
    elif args.command == "clean":
        clean_repo(REPO_ROOT)
    else:
        raise RuntimeError(f"Unsupported command: {args.command}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CoronaEngine developer workflow")
    parser.add_argument(
        "command", nargs="?", default="status",
        choices=("status", "install", "configure", "build", "build-fast", "rebuild", "update", "clean", "_bootstrap"),
    )
    parser.add_argument("targets", nargs="*")
    parser.add_argument("--configuration", choices=CONFIGURATIONS, default=DEFAULT_CONFIGURATION)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        execute(create_parser().parse_args(argv))
        return 0
    except CommandError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return error.returncode
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
