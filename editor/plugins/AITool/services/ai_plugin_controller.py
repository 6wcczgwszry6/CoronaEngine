import asyncio
import json
import logging
import queue


logger = logging.getLogger(__name__)


class AIPluginController:
    def __init__(
        self,
        request_service,
        media_ingress,
        stream_dispatcher,
        cai_client,
        event_loop_runner,
        build_error_response,
    ):
        self.request_service = request_service
        self._media_ingress = media_ingress
        self._stream_dispatcher = stream_dispatcher
        self._cai_client = cai_client
        self._event_loop_runner = event_loop_runner
        self._build_error_response = build_error_response

    def send_message_to_ai_stream(self, ai_message: str) -> None:
        ai_message, request_id, session_id = self.request_service.prepare_legacy_message(ai_message)
        if isinstance(request_id, str):
            self.request_service.mark_accepted(request_id, session_id)
        logger.info(
            "[AI RPC] 接收旧入口请求 [request=%s, session=%s, operation=legacy.stream]",
            request_id or "N/A",
            session_id or "N/A",
        )
        self._event_loop_runner.submit(
            self._process_ai_message_stream(ai_message, request_id),
            request_id,
            self.request_service,
        )

    def ai_rpc(self, request) -> dict:
        try:
            if isinstance(request, str):
                request = json.loads(request)
            if not isinstance(request, dict):
                return {"success": False, "error": "INVALID_REQUEST"}

            operation = request.get("operation", "chat.stream")
            request_id = request.get("request_id")

            if operation == "request.status":
                return self.request_service.get_status(request_id)

            if operation == "request.cancel":
                return self.request_service.cancel(request_id, self._event_loop_runner.loop)

            if operation != "chat.stream":
                return {"success": False, "request_id": request_id, "error": "UNKNOWN_OPERATION"}

            payload, request_id, session_id, error_response = self.request_service.normalize_chat_request(request)
            if error_response is not None:
                return error_response

            ai_message = json.dumps(payload, ensure_ascii=False)
            logger.info(
                "[AI RPC] 接收请求 [request=%s, session=%s, operation=%s]",
                request_id or "N/A",
                session_id or "N/A",
                operation,
            )
            self._event_loop_runner.submit(
                self._process_ai_message_stream(ai_message, request_id),
                request_id,
                self.request_service,
            )
            return {"success": True, "request_id": request_id, "status": "accepted"}
        except Exception as exc:
            logger.exception("[AI RPC] 处理请求失败: %s", exc)
            return {"success": False, "error": str(exc)}

    def cleanup(self, executor):
        self._event_loop_runner.shutdown()
        executor.shutdown(wait=True, cancel_futures=True)
        logger.info("AI 插件资源已清理")

    async def _process_ai_message_stream(self, ai_message: str, request_id: str | None = None) -> None:
        msg_data: dict | None = None
        token = None
        chunk_stream = None
        try:
            msg_data = json.loads(ai_message)
            payload = msg_data if isinstance(msg_data, dict) else {"message": msg_data}

            payload, token = self._media_ingress.prepare_payload(payload)
            chunk_stream = self._cai_client.start_stream(payload)

            while True:
                try:
                    msg_type, data = await self._event_loop_runner.loop.run_in_executor(
                        None, chunk_stream.get, True, 0.1
                    )
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                except Exception as exc:
                    logger.error("[AI Bridge Stream] 队列获取错误: %s", exc)
                    await asyncio.sleep(0.01)
                    continue

                if msg_type == "done":
                    break
                if msg_type == "error":
                    raise data
                if msg_type == "chunk":
                    try:
                        event_type = self._stream_dispatcher.dispatch_chunk(data, request_id, token)
                        if event_type == "done":
                            break
                    except Exception as exc:
                        logger.exception("[AI Bridge Stream] 处理流式块错误：%s", exc)
                        continue

        except Exception as exc:
            metadata = {}
            if isinstance(msg_data, dict):
                meta_in = msg_data.get("metadata", {})
                metadata = meta_in if isinstance(meta_in, dict) else {}

            if token:
                metadata["token"] = token
            if request_id:
                metadata.setdefault("request_id", request_id)

            error_payload = self._build_error_response(
                interface_type="integrated",
                session_id=(
                    msg_data.get("session_id") if isinstance(msg_data, dict) else None
                ),
                exc=exc,
                metadata=metadata,
            )
            self._stream_dispatcher.dispatch_error(error_payload)
        finally:
            if chunk_stream is not None:
                chunk_stream.stop()