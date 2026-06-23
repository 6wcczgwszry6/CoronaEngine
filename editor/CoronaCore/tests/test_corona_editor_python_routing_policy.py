import json
import sys
import unittest
from pathlib import Path

EDITOR_ROOT = Path(__file__).resolve().parents[2]
if str(EDITOR_ROOT) not in sys.path:
    sys.path.insert(0, str(EDITOR_ROOT))

from CoronaCore.core.corona_editor import CoronaEditor


class _AllowedModule:
    @staticmethod
    def ai_rpc(payload):
        return {"echo": payload}


class _BlockedModule:
    @staticmethod
    def create_actor(scene_name, asset_path):
        return {"scene": scene_name, "asset": asset_path}


class CoronaEditorPythonRoutingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.previous_modules = dict(CoronaEditor.module_list)
        CoronaEditor.module_list = {
            "AITool": _AllowedModule,
            "SceneTools": _BlockedModule,
        }

    def tearDown(self):
        CoronaEditor.module_list = self.previous_modules

    def _call(self, module, function, args=None):
        response = CoronaEditor.deal_func_from_js(
            json.dumps({
                "module": module,
                "function": function,
                "args": args or [],
            })
        )
        return json.loads(response)

    def test_python_keeps_ai_modules_allowed(self):
        response = self._call("AITool", "ai_rpc", [{"message": "hello"}])

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], {"echo": {"message": "hello"}})

    def test_python_rejects_non_whitelisted_realtime_editor_modules(self):
        response = self._call("SceneTools", "create_actor", ["scene", "chair.obj"])

        self.assertFalse(response["success"])
        self.assertIn("not allowed on Python route", response["error"])

    def test_python_event_push_does_not_control_frontend_windows(self):
        calls = []
        previous_engine = CoronaEditor.CoronaEngine
        CoronaEditor.CoronaEngine = type(
            "FakeEngine",
            (),
            {
                "execute_javascript": staticmethod(
                    lambda tab_id, js_code: calls.append((tab_id, js_code))
                )
            },
        )()
        try:
            result = CoronaEditor.emit_editor_event("engine-started", [])
        finally:
            CoronaEditor.CoronaEngine = previous_engine

        self.assertIn("Editor event emitted: engine-started", result)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
