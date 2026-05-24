"""
路径配置
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathsConfig:
    """路径配置"""

    repo_root: Path
    frontend_dist: Path
    plugins_dir: Path
    config_dir: Path


def get_default_paths() -> PathsConfig:
    """获取默认路径配置"""
    # 从当前文件位置计算项目根目录
    repo_root = Path(__file__).resolve().parents[1].parents[0]
    frontend_dist = repo_root / "Frontend" / "dist" / "index.html"
    config_dir = repo_root / "config"
    plugins_dir = repo_root / "plugins"

    return PathsConfig(
        repo_root=repo_root,
        frontend_dist=frontend_dist,
        plugins_dir=plugins_dir,
        config_dir=config_dir,
    )


core_path = get_default_paths()
