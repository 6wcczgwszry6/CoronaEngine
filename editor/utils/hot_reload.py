"""模块热重载管理。"""
import sys


def clear_script_modules():
    """清理 runScript 和 script 相关模块缓存。"""
    modules_to_clear = [
        name for name in sys.modules.keys()
        if 'runScript' in name or 'script' in name
    ]

    for module_name in modules_to_clear:
        del sys.modules[module_name]

    if modules_to_clear:
        print(f"✓ 已清理 {len(modules_to_clear)} 个模块缓存")
