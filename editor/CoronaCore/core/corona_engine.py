"""Robust loader for the CoronaEngine module.
Tries multiple import paths so modules can be imported both as package (Backend.*) and as top-level scripts.
Returns the module object or the CoronaEngine class from the fallback module, or None.
"""
from importlib import import_module
from typing import Optional


def load_corona_engine() -> Optional[object]:
    candidates = [
        'CoronaEngine',
        'CoronaCore.utils.corona_engine_fallback',
    ]
    for name in candidates:
        try:
            mod = import_module(name)

            # 如果模块有 CoronaEngine 类属性，返回该类
            if hasattr(mod, 'CoronaEngine'):
                return getattr(mod, 'CoronaEngine')

            # 否则，检查模块是否本身就是 CoronaEngine（原生C++模块的情况）
            # 如果模块有 Scene 属性，说明它是可用的引擎模块
            if hasattr(mod, 'Scene'):
                return mod
        except Exception:
            continue

    # 如果所有动态导入都失败，则作为最后的手段直接导入 fallback
    try:
        from CoronaCore.utils.corona_engine_fallback import CoronaEngine
        return CoronaEngine
    except ImportError:
        pass

    # 最后尝试
    return None

corona_engine = None
def get_corona_engine() -> Optional[object]:
    global corona_engine
    if corona_engine is None:
        corona_engine = load_corona_engine()
    return corona_engine
