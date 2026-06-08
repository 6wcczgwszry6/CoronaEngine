"""Network plugin — LAN collaborative editing bridge.

Routes JS cefQuery -> C++ CoronaEngine network_start_session (Python bindings via nanobind).
Peer events (connect/disconnect) are pushed back to the frontend via js_call_func('network-event').
"""

import logging

logger = logging.getLogger(__name__)

# The plugin base lives in CoronaPlugin.core
from CoronaCore.core.corona_editor import CoronaEditor
from CoronaPlugin.core.corona_plugin_base import PluginBase


# ---------------------------------------------------------------------------
# Frontend push helper
# ---------------------------------------------------------------------------
FRONTEND_EVENT = "network-event"


def _push_to_frontend(event: dict) -> None:
    """Push a network event dict to the Vue frontend via coronaEventBus."""
    try:
        CoronaEditor.js_call_func(FRONTEND_EVENT, [event])
    except Exception:
        logger.exception("[Network] Failed to push event to frontend")


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------
@PluginBase.register_web("Network")
class NetworkPlugin(PluginBase):
    """Thin proxy that calls CoronaEngine network_* functions."""

    @classmethod
    def start_session(cls, instance_name: str, project_id: int, port: int = 27960) -> dict:
        """Start a LAN collaborative editing session."""
        try:
            engine = CoronaEditor.CoronaEngine
            ok = engine.network_start_session(instance_name, project_id, port)
            return {"ok": ok}
        except Exception as exc:
            logger.exception("[Network] start_session failed")
            return {"ok": False, "error": str(exc)}

    @classmethod
    def stop_session(cls) -> dict:
        """Stop the LAN collaborative editing session."""
        try:
            engine = CoronaEditor.CoronaEngine
            engine.network_stop_session()
            return {"ok": True}
        except Exception as exc:
            logger.exception("[Network] stop_session failed")
            return {"ok": False, "error": str(exc)}

    @classmethod
    def get_peer_count(cls) -> dict:
        """Get the number of currently connected peers."""
        try:
            engine = CoronaEditor.CoronaEngine
            count = engine.network_peer_count()
            return {"ok": True, "peer_count": count}
        except Exception as exc:
            logger.exception("[Network] get_peer_count failed")
            return {"ok": False, "peer_count": 0, "error": str(exc)}
