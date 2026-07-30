import { aiService } from '@/utils/bridge.js';
import { createServiceResponseError } from '@/utils/serviceInitialization.js';

const CHANNEL_NAME = 'corona-cabbage-assistant-context-v2';
const STORAGE_KEY = 'corona.cabbageAssistantContext.v2';
const CONTEXT_MESSAGE_TYPE = 'cabbage-assistant-context';
const TRANSFORM_DEBOUNCE_MS = 650;
const PROFILE_POLL_MS = 1200;

let channel = null;
let latestSnapshot = null;
let writeChain = Promise.resolve();
let activeScoreUpdateTaskId = '';
const pendingTransforms = new Map();

function getChannel() {
  if (typeof BroadcastChannel === 'undefined') return null;
  if (!channel) channel = new BroadcastChannel(CHANNEL_NAME);
  return channel;
}

function clone(value, fallback) {
  try { return JSON.parse(JSON.stringify(value)); } catch (_) { return fallback; }
}

function currentScopeId() {
  const path = String(window.localStorage?.getItem('corona.activeProjectPath') || '')
    .trim().replace(/\\/g, '/').replace(/\/+$/, '').toLocaleLowerCase('en-US');
  let hash = 2166136261;
  for (let index = 0; index < path.length; index += 1) {
    hash ^= path.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function normalizeTask(task) {
  if (!task || typeof task !== 'object') return null;
  const taskKey = String(task.taskKey || task.issueKey || task.code || '').trim();
  if (!taskKey) return null;
  return { ...clone(task, {}), taskKey, issueKey: taskKey };
}

function normalizeSnapshot(value) {
  if (!value || typeof value !== 'object') return null;
  const context = value.context && typeof value.context === 'object' ? value.context : value;
  const activeTasks = (Array.isArray(context.activeTasks) ? context.activeTasks : []).map(normalizeTask).filter(Boolean);
  const taskHistory = (Array.isArray(context.taskHistory) ? context.taskHistory : []).map(normalizeTask).filter(Boolean);
  const selectedTaskKey = String(value.selectedTaskKey || context.selectedTaskKey || '');
  return {
    schemaVersion: 1,
    worldId: String(context.worldId || ''),
    projectScopeId: String(value.projectScopeId || context.projectScopeId || currentScopeId()),
    graphRevision: String(value.graphRevision || context.graphRevision || ''),
    graphExcerpt: clone(value.graphExcerpt || context.graphExcerpt || {}, {}),
    profile: clone(context.profile || {}, {}),
    profileHistory: clone(context.profileHistory || [], []),
    issueMemory: clone(context.issueMemory || {}, {}),
    metrics: clone(context.metrics || {}, {}),
    activeTasks,
    taskHistory,
    chatMessages: clone(context.chatMessages || [], []),
    recentOperationEvents: clone(context.recentOperationEvents || [], []),
    selectedTaskKey: activeTasks.some((task) => task.taskKey === selectedTaskKey) ? selectedTaskKey : '',
    updatedAt: Number(context.updatedAt || value.updatedAt) || Date.now(),
  };
}

function publishSnapshot(snapshot) {
  const normalized = normalizeSnapshot(snapshot);
  if (!normalized) return null;
  latestSnapshot = normalized;
  try { window.localStorage?.setItem(STORAGE_KEY, JSON.stringify(normalized)); } catch (_) {}
  try { getChannel()?.postMessage({ type: CONTEXT_MESSAGE_TYPE, payload: normalized }); } catch (_) {}
  return normalized;
}

function enqueue(operation) {
  const run = () => Promise.resolve().then(operation);
  const pending = writeChain.then(run, run);
  writeChain = pending.catch((error) => {
    console.warn('[CabbageContext]', error?.message || error);
  });
  return pending;
}

function responseContext(response) {
  if (response?.success === true && response?.context) return response.context;
  return null;
}

function publishBackendContext(context) {
  const scope = currentScopeId();
  const current = latestSnapshot?.projectScopeId === scope ? latestSnapshot : null;
  return publishSnapshot({
    context,
    projectScopeId: scope,
    graphRevision: current?.graphRevision || '',
    graphExcerpt: current?.graphExcerpt || {},
    selectedTaskKey: current?.selectedTaskKey || '',
  });
}

function transformKey(event) {
  const details = event?.details || {};
  return [event.type, details.sceneName || '', details.actorName || details.actor || ''].join(':');
}

async function sendEvent(event) {
  const response = await aiService.recordCabbageEvent({
    ...event,
    worldId: String(event?.worldId || latestSnapshot?.worldId || ''),
    timestamp: Number(event?.timestamp) || Date.now(),
  });
  const context = responseContext(response);
  if (context) publishBackendContext(context);
  if (response?.success === true && (
    Array.isArray(response.completedTaskKeys) && response.completedTaskKeys.length
    || ['run_started', 'run_succeeded', 'run_failed', 'node_issue_found', 'node_issue_fixed'].includes(event?.type)
  )) {
    void requestProfileScoreUpdate().catch(() => {});
  }
  return response;
}

export function createCabbageAssistantContext(source = {}) {
  return normalizeSnapshot({
    ...source,
    activeTasks: source.activeTasks || source.tasks,
    chatMessages: source.chatMessages || source.messages,
    updatedAt: Date.now(),
  });
}

export function publishCabbageAssistantContext(source = {}) {
  return publishSnapshot(createCabbageAssistantContext(source));
}

export function readCabbageAssistantContext(projectScopeId = '') {
  let snapshot = latestSnapshot;
  if (!snapshot) {
    try { snapshot = normalizeSnapshot(JSON.parse(window.localStorage?.getItem(STORAGE_KEY) || 'null')); } catch (_) { snapshot = null; }
  }
  if (!snapshot) return null;
  if (projectScopeId && snapshot.projectScopeId !== String(projectScopeId)) return null;
  return clone(snapshot, null);
}

export async function loadCurrentWorld() {
  cancelPendingTransformEvents();
  const response = await aiService.loadCabbageContext();
  if (response?.success !== true || !response?.context) {
    throw createServiceResponseError(response, '加载当前世界的包菜上下文失败');
  }
  return publishSnapshot({ context: response.context, projectScopeId: currentScopeId() });
}

export function recordEvent(event = {}) {
  const normalized = { ...clone(event, {}), timestamp: Number(event.timestamp) || Date.now() };
  if (['transform_position', 'transform_rotation', 'transform_scale'].includes(normalized.type)) {
    const key = transformKey(normalized);
    const previous = pendingTransforms.get(key);
    if (previous?.timer) window.clearTimeout(previous.timer);
    const entry = {
      event: normalized,
      timer: window.setTimeout(() => {
        pendingTransforms.delete(key);
        enqueue(() => sendEvent(entry.event));
      }, TRANSFORM_DEBOUNCE_MS),
    };
    pendingTransforms.set(key, entry);
    return Promise.resolve({ success: true, status: 'queued' });
  }
  return enqueue(() => sendEvent(normalized));
}

export function updateTask(payload = {}) {
  return enqueue(async () => {
    const response = await aiService.updateCabbageTask({
      ...payload,
      worldId: String(payload?.worldId || latestSnapshot?.worldId || ''),
    });
    const context = responseContext(response);
    if (context) publishBackendContext(context);
    return response;
  });
}

export function appendMessage(message = {}) {
  return enqueue(async () => {
    const response = await aiService.appendCabbageMessage({
      ...message,
      worldId: String(message?.worldId || latestSnapshot?.worldId || ''),
    });
    const context = responseContext(response);
    if (context) publishBackendContext(context);
    return response;
  });
}

async function pollScoreUpdate(taskId) {
  while (activeScoreUpdateTaskId === taskId) {
    const response = await aiService.getCabbageProfileScoreStatus(taskId);
    if (response?.success !== true) break;
    if (response.status === 'completed') {
      activeScoreUpdateTaskId = '';
      const result = response.result || {};
      if (result?.success === true && result?.profile) {
        const snapshot = readCabbageAssistantContext() || {};
        publishSnapshot({ ...snapshot, profile: result.profile, updatedAt: Date.now() });
      }
      return result;
    }
    await new Promise((resolve) => window.setTimeout(resolve, PROFILE_POLL_MS));
  }
  return null;
}

export async function requestProfileScoreUpdate(options = {}) {
  if (activeScoreUpdateTaskId) return { success: true, status: 'pending', taskId: activeScoreUpdateTaskId };
  const response = await aiService.startCabbageProfileScoreUpdate(options);
  if (response?.status === 'skipped' && response.profile) {
    const snapshot = readCabbageAssistantContext() || {};
    publishSnapshot({ ...snapshot, profile: response.profile, updatedAt: Date.now() });
    return response;
  }
  if (response?.success === true && response?.taskId) {
    activeScoreUpdateTaskId = String(response.taskId);
    void pollScoreUpdate(activeScoreUpdateTaskId).catch((error) => {
      activeScoreUpdateTaskId = '';
      console.warn('[CabbageContext] profile score update failed', error?.message || error);
    });
  }
  return response;
}

export function subscribeCabbageAssistantContext(listener, { projectScopeId = '', emitCurrent = true } = {}) {
  let latestUpdatedAt = 0;
  const getExpectedScope = () => String(typeof projectScopeId === 'function' ? projectScopeId() : projectScopeId || '');
  const accept = (value) => {
    const snapshot = normalizeSnapshot(value);
    if (!snapshot) return;
    const expected = getExpectedScope();
    if (expected && snapshot.projectScopeId !== expected) return;
    if (snapshot.updatedAt < latestUpdatedAt) return;
    latestUpdatedAt = snapshot.updatedAt;
    latestSnapshot = snapshot;
    listener(clone(snapshot, snapshot));
  };
  const onBroadcast = (event) => {
    if (event?.data?.type === CONTEXT_MESSAGE_TYPE) accept(event.data.payload);
  };
  const onStorage = (event) => {
    if (event?.key !== STORAGE_KEY || !event.newValue) return;
    try { accept(JSON.parse(event.newValue)); } catch (_) {}
  };
  const currentChannel = getChannel();
  currentChannel?.addEventListener('message', onBroadcast);
  window.addEventListener('storage', onStorage);
  if (emitCurrent) {
    const current = readCabbageAssistantContext(getExpectedScope());
    if (current) accept(current);
  }
  return () => {
    currentChannel?.removeEventListener('message', onBroadcast);
    window.removeEventListener('storage', onStorage);
  };
}

export function cancelPendingTransformEvents() {
  for (const entry of pendingTransforms.values()) {
    if (entry.timer) window.clearTimeout(entry.timer);
  }
  pendingTransforms.clear();
}

export async function flush() {
  const entries = Array.from(pendingTransforms.values());
  pendingTransforms.clear();
  for (const entry of entries) {
    if (entry.timer) window.clearTimeout(entry.timer);
    enqueue(() => sendEvent(entry.event));
  }
  await writeChain;
}

export const cabbageContextService = {
  loadCurrentWorld,
  recordEvent,
  updateTask,
  appendMessage,
  requestProfileScoreUpdate,
  flush,
};
