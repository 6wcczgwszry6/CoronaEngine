const CHANNEL_NAME = 'corona-cabbage-tutorial-session-v2';
const REQUEST_TYPE = 'tutorial-restore-request';
const RESPONSE_TYPE = 'tutorial-restore-response';

const restorers = new Map();
const pending = new Map();
const incomingRequests = new Map();
let channel = null;
let listening = false;

function getChannel() {
  if (typeof BroadcastChannel === 'undefined') return null;
  if (!channel) channel = new BroadcastChannel(CHANNEL_NAME);
  if (!listening) {
    listening = true;
    channel.addEventListener('message', handleMessage);
  }
  return channel;
}

function clone(value, fallback = {}) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (_) {
    return fallback;
  }
}

async function executeRestorer(name, payload) {
  const handler = restorers.get(String(name || ''));
  if (!handler) return { handled: false, success: false, error: '' };
  try {
    const result = await handler(clone(payload, {}));
    if (result === false || result?.success === false) {
      return {
        handled: true,
        success: false,
        error: String(result?.error || `Tutorial restorer ${name} failed`),
      };
    }
    return { handled: true, success: true, result: clone(result ?? {}, {}) };
  } catch (error) {
    return { handled: true, success: false, error: String(error?.message || error) };
  }
}

async function handleMessage(event) {
  const message = event?.data;
  if (!message || typeof message !== 'object') return;
  if (message.type === REQUEST_TYPE) {
    const requestId = String(message.requestId || '');
    if (!requestId) return;
    let execution = incomingRequests.get(requestId);
    if (!execution) {
      execution = executeRestorer(message.name, message.payload);
      incomingRequests.set(requestId, execution);
    }
    const response = await execution;
    if (!response.handled) {
      if (incomingRequests.get(requestId) === execution) incomingRequests.delete(requestId);
      return;
    }
    window.setTimeout(() => {
      if (incomingRequests.get(requestId) === execution) incomingRequests.delete(requestId);
    }, 10000);
    getChannel()?.postMessage({
      type: RESPONSE_TYPE,
      requestId,
      name: message.name,
      ...response,
    });
    return;
  }
  if (message.type !== RESPONSE_TYPE) return;
  const entry = pending.get(String(message.requestId || ''));
  if (!entry || entry.name !== String(message.name || '')) return;
  pending.delete(entry.requestId);
  window.clearTimeout(entry.timer);
  window.clearInterval(entry.retryTimer);
  if (message.success) entry.resolve(message.result || { success: true });
  else entry.reject(new Error(String(message.error || `Tutorial restorer ${entry.name} failed`)));
}

export function registerTutorialRestorer(name, handler) {
  const key = String(name || '').trim();
  if (!key || typeof handler !== 'function') return () => {};
  restorers.set(key, handler);
  getChannel();
  return () => {
    if (restorers.get(key) === handler) restorers.delete(key);
  };
}

export async function requestTutorialRestore(name, payload = {}, { timeoutMs = 5000 } = {}) {
  const key = String(name || '').trim();
  if (!key) throw new Error('Tutorial restorer name is required');
  const local = await executeRestorer(key, payload);
  if (local.handled) {
    if (local.success) return local.result || { success: true };
    throw new Error(local.error || `Tutorial restorer ${key} failed`);
  }
  const currentChannel = getChannel();
  if (!currentChannel) throw new Error(`Tutorial restorer ${key} is unavailable`);
  const requestId = `tutorial_restore_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return new Promise((resolve, reject) => {
    const request = {
      type: REQUEST_TYPE,
      requestId,
      name: key,
      payload: clone(payload, {}),
    };
    const timer = window.setTimeout(() => {
      const entry = pending.get(requestId);
      if (entry) window.clearInterval(entry.retryTimer);
      pending.delete(requestId);
      reject(new Error(`Tutorial restorer ${key} timed out`));
    }, Math.max(500, Number(timeoutMs) || 5000));
    const entry = { requestId, name: key, resolve, reject, timer, retryTimer: null };
    pending.set(requestId, entry);
    entry.retryTimer = window.setInterval(() => currentChannel.postMessage(request), 250);
    currentChannel.postMessage(request);
  });
}

export function closeTutorialSessionChannel() {
  for (const entry of pending.values()) {
    window.clearTimeout(entry.timer);
    window.clearInterval(entry.retryTimer);
    entry.reject(new Error('Tutorial session channel closed'));
  }
  pending.clear();
  incomingRequests.clear();
  channel?.close?.();
  channel = null;
  listening = false;
}
