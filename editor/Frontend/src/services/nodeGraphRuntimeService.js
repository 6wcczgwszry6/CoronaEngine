import { appService } from '@/utils/bridge.js';
import { coronaEventBus } from '@/utils/eventBus.js';

const SAVE_REQUEST_EVENT = 'node-graph-save-request';
const SAVE_RESULT_EVENT = 'node-graph-save-result';
const SAVE_ACCEPTED_EVENT = 'node-graph-save-accepted';
const GLOBAL_NODE_TARGET_ID = 'node_graph:project:global';

function requestId() {
  return `node_graph_save_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

async function runLocalFlusher() {
  if (typeof window.__coronaNodeGraphFlushSave !== 'function') return false;
  const result = await window.__coronaNodeGraphFlushSave();
  if (result === false) throw new Error('\u8282\u70b9\u56fe\u4fdd\u5b58\u5931\u8d25\uff0c\u5df2\u53d6\u6d88\u5168\u5c40\u8fd0\u884c');
  return true;
}

/**
 * Flush the project node graph before global preview starts. If the node editor
 * lives in another Dock/CEF context, request a save over the existing cross-tab
 * event channel. A short owner timeout means the editor is not mounted and the
 * latest persisted graph can be used. Once an editor accepts the request, wait
 * for the real save result so global run never races a slow disk write.
 */
export async function flushProjectNodeGraphBeforeRun({
  ownerTimeoutMs = 800,
  saveTimeoutMs = 6000,
} = {}) {
  if (await runLocalFlusher()) return { success: true, source: 'local' };

  const id = requestId();
  return new Promise((resolve, reject) => {
    let settled = false;
    let timer = null;
    const cleanup = () => {
      if (timer) window.clearTimeout(timer);
      timer = null;
      coronaEventBus.off(SAVE_ACCEPTED_EVENT, onAccepted);
      coronaEventBus.off(SAVE_RESULT_EVENT, onResult);
    };
    const finish = (result, error = null) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (error) reject(error);
      else resolve(result);
    };
    const armTimer = (delay, callback) => {
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(callback, Math.max(250, Number(delay) || 0));
    };
    const onAccepted = (payload = {}) => {
      if (String(payload.requestId || '') !== id) return;
      armTimer(saveTimeoutMs, () => {
        finish(null, new Error('\u8282\u70b9\u56fe\u4fdd\u5b58\u8d85\u65f6\uff0c\u5df2\u53d6\u6d88\u5168\u5c40\u8fd0\u884c'));
      });
    };
    const onResult = (payload = {}) => {
      if (String(payload.requestId || '') !== id) return;
      if (payload.success === false) {
        finish(null, new Error(payload.message || '\u8282\u70b9\u56fe\u4fdd\u5b58\u5931\u8d25\uff0c\u5df2\u53d6\u6d88\u5168\u5c40\u8fd0\u884c'));
        return;
      }
      finish({ success: true, source: 'dock' });
    };

    coronaEventBus.on(SAVE_ACCEPTED_EVENT, onAccepted);
    coronaEventBus.on(SAVE_RESULT_EVENT, onResult);
    armTimer(ownerTimeoutMs, () => {
      finish({ success: true, source: 'persisted', skipped: true });
    });

    const payload = { requestId: id, targetId: GLOBAL_NODE_TARGET_ID };
    // Same-window Dock.
    coronaEventBus.emit(SAVE_REQUEST_EVENT, payload);
    // Detached Dock/CEF windows.
    appService.crossTabBroadcast(SAVE_REQUEST_EVENT, payload).catch(() => {});
  });
}

/** Register the scene-side project node editor as the only global save owner. */
export function registerProjectNodeGraphSaveHandler(save) {
  const handled = new Set();
  const onRequest = async (payload = {}) => {
    const id = String(payload.requestId || '');
    if (!id || handled.has(id)) return;
    if (payload.targetId && payload.targetId !== GLOBAL_NODE_TARGET_ID) return;
    handled.add(id);
    window.setTimeout(() => handled.delete(id), 8000);

    const accepted = { requestId: id, targetId: GLOBAL_NODE_TARGET_ID };
    coronaEventBus.emit(SAVE_ACCEPTED_EVENT, accepted);
    appService.crossTabBroadcast(SAVE_ACCEPTED_EVENT, accepted).catch(() => {});

    let success = false;
    let message = '';
    try {
      success = (await save()) !== false;
      if (!success) message = '\u8282\u70b9\u56fe\u4fdd\u5b58\u5931\u8d25\uff0c\u5df2\u53d6\u6d88\u5168\u5c40\u8fd0\u884c';
    } catch (error) {
      message = String(error?.message || error || '\u8282\u70b9\u56fe\u4fdd\u5b58\u5931\u8d25');
    }

    const result = {
      requestId: id,
      targetId: GLOBAL_NODE_TARGET_ID,
      success,
      message,
    };
    coronaEventBus.emit(SAVE_RESULT_EVENT, result);
    appService.crossTabBroadcast(SAVE_RESULT_EVENT, result).catch(() => {});
  };

  coronaEventBus.on(SAVE_REQUEST_EVENT, onRequest);
  return () => coronaEventBus.off(SAVE_REQUEST_EVENT, onRequest);
}
