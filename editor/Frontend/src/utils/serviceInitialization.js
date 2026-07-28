export function createServiceResponseError(response, fallbackMessage) {
  const error = new Error(response?.message || fallbackMessage);
  error.status = String(response?.status || 'unavailable');
  error.retryable = error.status === 'initializing';
  return error;
}

export function createServiceInitializationRetry({
  delayMs = 750,
  schedule = (callback, delay) => globalThis.setTimeout(callback, delay),
  cancel = (handle) => globalThis.clearTimeout(handle),
} = {}) {
  let handle = null;

  return {
    schedule(callback) {
      if (handle !== null) cancel(handle);
      handle = schedule(() => {
        handle = null;
        callback();
      }, delayMs);
    },
    cancel() {
      if (handle === null) return;
      cancel(handle);
      handle = null;
    },
  };
}
