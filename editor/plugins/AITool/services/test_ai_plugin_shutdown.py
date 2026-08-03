import unittest
from types import SimpleNamespace

from editor.plugins.AITool.services.ai_plugin_controller import AIPluginController


class AIPluginShutdownTests(unittest.TestCase):
    def test_cleanup_cancels_streams_and_does_not_wait_forever_for_executor(self):
        calls = []
        controller = AIPluginController(
            request_service=SimpleNamespace(),
            media_ingress=SimpleNamespace(),
            stream_dispatcher=SimpleNamespace(),
            cai_client=SimpleNamespace(shutdown=lambda: calls.append("client")),
            event_loop_runner=SimpleNamespace(shutdown=lambda: calls.append("loop")),
            build_error_response=lambda *_: None,
        )
        executor = SimpleNamespace(
            shutdown=lambda **kwargs: calls.append(("executor", kwargs))
        )

        controller.cleanup(executor)

        self.assertEqual(
            calls,
            ["client", "loop", ("executor", {"wait": False, "cancel_futures": True})],
        )


if __name__ == "__main__":
    unittest.main()
