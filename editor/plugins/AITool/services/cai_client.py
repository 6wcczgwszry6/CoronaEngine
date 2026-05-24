import queue
import threading


class CAIStream:
    def __init__(self, maxsize: int):
        self._queue = queue.Queue(maxsize=maxsize)
        self._stop_event = threading.Event()

    def get(self, *args, **kwargs):
        return self._queue.get(*args, **kwargs)

    def stop(self):
        self._stop_event.set()

    def put(self, item) -> bool:
        while not self._stop_event.is_set():
            try:
                self._queue.put(item, timeout=0.1)
                return True
            except queue.Full:
                continue
        return False

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()


class CAIClient:
    def __init__(self, cai_app, executor, queue_maxsize: int):
        self._cai_app = cai_app
        self._executor = executor
        self._queue_maxsize = queue_maxsize

    def start_stream(self, payload: dict):
        stream = CAIStream(self._queue_maxsize)

        def stream_worker():
            try:
                for chunk in self._cai_app.chat_stream(payload):
                    if not stream.put(("chunk", chunk)):
                        break
            except Exception as exc:
                if not stream.stopped:
                    stream.put(("error", exc))
            finally:
                if not stream.stopped:
                    stream.put(("done", None))

        self._executor.submit(stream_worker)
        return stream
