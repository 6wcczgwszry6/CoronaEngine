import logging
import os
import sys
import atexit
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

editor = CoronaEditor
editor.module_list["CoronaEditor"] = CoronaEditor
from backend.registry import register_core_python_script_services
register_core_python_script_services()
editor.register_script_dispatcher()
atexit.register(editor.unregister_script_dispatcher)

try:
    from CoronaPlugin.utils.load_utils import reimport
    reimport()
except:
    pass


def run():
    logging.info("Python script runtime initialized; C++ UI owns the Vue/CEF frontend tab.")
