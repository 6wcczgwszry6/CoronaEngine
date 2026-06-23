import logging
import os
import sys
from pathlib import Path

from CoronaCore.core.corona_editor import CoronaEditor

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from config.app_config import get_app_config

app_config = get_app_config()
sys.path.append(str(app_config.paths.repo_root))

try:
    from utils.logging import configure_logging
    configure_logging()
except Exception:
    import traceback as _tb
    _tb.print_exc()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] %(message)s",
        force=True,
    )

try:
    from CoronaPlugin.utils.load_utils import reimport
    reimport()
except:
    pass

editor = CoronaEditor
editor.module_list["CoronaEditor"] = CoronaEditor


def run():
    try:
        from plugins.AITool.Quasar.ai_tools.warmup import warmup_all
        from plugins.AITool.utils.load_local_ai_setting import load_ai_setting
        load_ai_setting()
        warmup_all()
    except:
        pass

    logging.info("Python editor backend initialized; C++ UI owns the Vue/CEF frontend tab.")
