import asyncio
import logging
import threading


logger = logging.getLogger(__name__)


class EventLoopRunner:
    def __init__(self, thread_name: str = "AI_EventLoop_Thread"):
        self._loop: asyncio.AbstractEventLoop | None = None
        self.active_tasks: set[asyncio.Task] = set()
        self._thread_name = thread_name
        self._loop_thread: threading.Thread | None = None

    @property
    def loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    @loop.setter
    def loop(self, value):
        self._loop = value

    def ensure_running(self):
        if self._loop_thread is None or not self._loop_thread.is_alive():
            loop = self.loop
            self._loop_thread = threading.Thread(
                target=self._run_event_loop,
                args=(loop,),
                name=self._thread_name,
                daemon=True,
            )
            self._loop_thread.start()
            logger.info("AI 事件循环线程已启动")

    def submit(self, coro, request_id: str | None, request_service):
        self.ensure_running()
        self.loop.call_soon_threadsafe(
            self._start_task,
            coro,
            request_id,
            request_service,
        )

    def shutdown(self):
        for task in list(self.active_tasks):
            self.loop.call_soon_threadsafe(task.cancel)

        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)

        self.active_tasks.clear()

    def _run_event_loop(self, loop):
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except Exception as exc:
            logger.exception("事件循环运行异常: %s", exc)
        finally:
            loop.close()

    def _start_task(self, coro, request_id: str | None, request_service):
        task = self.loop.create_task(coro)
        self.active_tasks.add(task)
        task.add_done_callback(self.active_tasks.discard)
        request_service.attach_task(request_id, task)