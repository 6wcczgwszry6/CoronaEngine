import warnings
import json
from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import logging

from CoronaCore.core.corona_editor import CoronaEditor

from CoronaPlugin.core.corona_plugin_base import PluginBase

_AITOOL_DIR = Path(__file__).resolve().parent
if str(_AITOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_AITOOL_DIR))

from .cai_extensions.register import install as _install_cai_extensions

from Quasar.ai_service.entrance import get_ai_entrance
from Quasar.ai_tools.common import build_error_response
from Quasar.cai import CAIApp

from .utils.image_utils import base64_to_image_file, upload_file_to_server
from .services.ai_plugin_controller import AIPluginController
from .services.cai_client import CAIClient
from .services.event_loop_runner import EventLoopRunner
from .services.local_file_service import LocalFileService
from .services.media_ingress import MediaIngress
from .services.request_service import AIRequestService
from .services.stream_dispatcher import StreamDispatcher
from .services.ai_hint_service import get_hint_service
from .services.agent_runtime.flags import install_f5_runtime_provider_env_defaults
from .services.node_graph_review_service import get_node_graph_review_service
from .services.node_graph_review_chat_service import get_node_graph_review_chat_service
from .services.node_graph_generation_service import get_node_graph_generation_service
from .services.cabbage_context_service import get_cabbage_context_service
from .services.lanchat_agent_worker import LANChatAgentWorker

try:
    import CoronaEngine as _CoronaEngine
except Exception:
    _CoronaEngine = None


def _create_lanchat_scene_composer():
    from .cai_extensions.agent.scene_composer import SceneComposer

    return SceneComposer(scene_name="Scene/default.scene")


install_f5_runtime_provider_env_defaults()


@PluginBase.register_web("AITool")
class AITool(PluginBase):
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AI_")
    _STREAM_QUEUE_MAXSIZE = 128
    _request_service = AIRequestService()
    _media_ingress = MediaIngress(base64_to_image_file, upload_file_to_server)
    _stream_dispatcher = StreamDispatcher(CoronaEditor.emit_editor_event)
    _cai_app = CAIApp.from_legacy_entrance(lambda: get_ai_entrance())
    _install_cai_extensions(_cai_app)
    _cai_client = CAIClient(_cai_app, _executor, _STREAM_QUEUE_MAXSIZE)
    _event_loop_runner = EventLoopRunner()
    _controller = AIPluginController(
        _request_service,
        _media_ingress,
        _stream_dispatcher,
        _cai_client,
        _event_loop_runner,
        build_error_response,
    )
    _lanchat_agent_worker = LANChatAgentWorker(
        corona_engine=_CoronaEngine,
        composer_factory=_create_lanchat_scene_composer,
        async_agent_execution=True,
    )
    _request_states = _request_service.states
    _hint_service = get_hint_service()
    _node_graph_review_service = get_node_graph_review_service()
    _node_graph_review_chat_service = get_node_graph_review_chat_service()
    _node_graph_generation_service = get_node_graph_generation_service()
    _cabbage_context_service = get_cabbage_context_service()

    @classmethod
    def _init_hint_service(cls) -> None:
        """将内置 AI 调用注入提示服务。"""

        def ai_caller(prompt: str) -> str | None:
            try:
                from Quasar.cai.protocol.request import ChatRequest

                # The hint service already embeds system instructions in the prompt,
                # so we just send it as a simple user message.
                req = ChatRequest.from_text(
                    text=prompt,
                    metadata={"hint_generation": True, "skip_conversation_store": True},
                )
                chunks = cls._cai_app.chat(req)
                text = "".join(chunks).strip()
                text = text.strip('"''""').strip()
                return text if text else None
            except Exception as exc:
                logging.getLogger(__name__).debug("AI hint generation failed: %s", exc)
                return None

        cls._hint_service.set_ai_caller(ai_caller)

    @classmethod
    def send_message_to_ai_stream(cls, ai_message: str) -> None:
        """发送消息到 AI（流式输出）"""
        cls._controller.send_message_to_ai_stream(ai_message)

    @classmethod
    def generate_hint(cls, element_type: str, context: dict = None) -> str:
        """生成AI提示气泡（内置 AI 生成 + 预定义回退）"""
        try:
            return cls._hint_service.generate_hint(element_type, context or {})
        except Exception as e:
            logging.getLogger(__name__).error("Error generating hint: %s", e)
            return "继续探索编辑器吧！"

    @classmethod
    def submit_request(cls, request) -> dict:
        """AI script-service request entry for the C++ Editor API facade."""
        try:
            parsed = json.loads(request) if isinstance(request, str) else request
        except Exception:
            parsed = request
        if isinstance(parsed, dict):
            operation = parsed.get("operation")
            if operation == "node_graph.review.start":
                return cls._node_graph_review_service.start(parsed.get("payload") or {})
            if operation == "node_graph.review.status":
                return cls._node_graph_review_service.status(parsed.get("taskId") or parsed.get("task_id") or "")
            if operation == "node_graph.review.chat":
                return cls._node_graph_review_chat_service.chat(parsed.get("payload") or {})
            if operation == "node_graph.review.chat.start":
                return cls._node_graph_review_chat_service.start(parsed.get("payload") or {})
            if operation == "node_graph.review.chat.status":
                return cls._node_graph_review_chat_service.status(parsed.get("taskId") or parsed.get("task_id") or "")
            if operation == "node_graph.review.chat.cancel":
                return cls._node_graph_review_chat_service.cancel(parsed.get("taskId") or parsed.get("task_id") or "")
            if operation == "node_graph.generate.start":
                return cls._node_graph_generation_service.start(parsed.get("payload") or {})
            if operation == "node_graph.generate.status":
                return cls._node_graph_generation_service.status(parsed.get("taskId") or parsed.get("task_id") or "")
            if operation == "node_graph.generate.cancel":
                return cls._node_graph_generation_service.cancel(parsed.get("taskId") or parsed.get("task_id") or "")
            if operation == "cabbage.context.load":
                return cls._cabbage_context_service.load()
            if operation == "cabbage.context.record_event":
                return cls._cabbage_context_service.record_event(parsed.get("payload") or {})
            if operation == "cabbage.context.update_task":
                return cls._cabbage_context_service.update_task(parsed.get("payload") or {})
            if operation == "cabbage.context.append_message":
                return cls._cabbage_context_service.append_message(parsed.get("payload") or {})
            if operation == "cabbage.goal_plan.start":
                return cls._cabbage_context_service.start_goal_plan(parsed.get("payload") or {})
            if operation == "cabbage.goal_plan.status":
                return cls._cabbage_context_service.goal_plan_status(
                    parsed.get("taskId") or parsed.get("task_id") or ""
                )
            if operation == "cabbage.profile.score.start":
                return cls._cabbage_context_service.start_score_update(parsed.get("payload") or {})
            if operation == "cabbage.profile.score.status":
                return cls._cabbage_context_service.score_update_status(parsed.get("taskId") or parsed.get("task_id") or "")
        return cls._controller.submit_request(request)

    @classmethod
    def cleanup(cls):
        """清理资源"""
        cls._lanchat_agent_worker.stop()
        cls._node_graph_review_service.shutdown()
        cls._node_graph_review_chat_service.shutdown()
        cls._node_graph_generation_service.shutdown()
        cls._cabbage_context_service.shutdown()
        cls._controller.cleanup(cls._executor)

    @staticmethod
    def read_local_file_as_base64(file_url: str) -> str:
        return LocalFileService.read_as_base64(file_url)


AITool._init_hint_service()
AITool._lanchat_agent_worker.start()

# ---------------------------------------------------------------------------
# P0: 引擎多场景并发测试（设置环境变量 CORONA_P0_CONCURRENCY_TEST=1 启用）
# ---------------------------------------------------------------------------
import os as _os
if _os.environ.get("CORONA_P0_CONCURRENCY_TEST") == "1":
    _cabbage_root = _AITOOL_DIR.parent
    if str(_cabbage_root) not in sys.path:
        sys.path.insert(0, str(_cabbage_root))
    from test_engine_concurrency import main as _p0_main
    import threading as _threading

    def _run_p0_test():
        import time as _time
        _time.sleep(3)
        _p0_main()

    _threading.Thread(target=_run_p0_test, name="P0-ConcurrencyTest", daemon=True).start()
