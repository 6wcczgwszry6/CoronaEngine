"""Blockly 生成文件清理模块。"""
from pathlib import Path
from functools import wraps


def run_once(func):
    """装饰器：确保函数只执行一次。"""
    func._has_run = False

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not func._has_run:
            result = func(*args, **kwargs)
            func._has_run = True
            return result
        return None

    return wrapper


@run_once
def cleanup_blockly_files():
    """删除上次运行残留的 blockly 脚本与入口文件，避免热更新时导入冲突。"""
    current_dir = Path(__file__).parent.parent  # Backend/

    files_to_clean = [
        current_dir / 'runScript.py',
        *current_dir.glob('script/blockly_code*.py')
    ]

    for file_path in filter(Path.exists, files_to_clean):
        try:
            file_path.unlink()
            print(f"✓ 已删除: {file_path.name}")
        except OSError as e:
            print(f"✗ {file_path.name}: {e.strerror}")
