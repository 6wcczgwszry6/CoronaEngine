const CHANNEL_NAME = 'corona-cabbage-assistant-context-v1';
const STORAGE_KEY = 'corona.cabbageAssistantContext.v1';
const CONTEXT_MESSAGE_TYPE = 'cabbage-assistant-context';
const MAX_TASKS = 40;

let channel = null;

function getChannel() {
  if (typeof BroadcastChannel === 'undefined') return null;
  if (!channel) channel = new BroadcastChannel(CHANNEL_NAME);
  return channel;
}

function clone(value, fallback) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (_) {
    return fallback;
  }
}

function normalizeTask(task) {
  if (!task || typeof task !== 'object') return null;
  const issueKey = String(task.issueKey || task.code || '').trim();
  if (!issueKey) return null;
  return {
    issueKey,
    code: String(task.code || issueKey),
    severity: String(task.severity || 'warning'),
    confidence: Number(task.confidence ?? 1),
    nodeId: String(task.nodeId || ''),
    blockId: String(task.blockId || ''),
    title: String(task.title || '节点逻辑需要调整').trim().slice(0, 80),
    message: String(task.message || '').trim().slice(0, 600),
    suggestion: String(task.suggestion || '').trim().slice(0, 600),
    graphRevision: String(task.graphRevision || ''),
    createdAt: Number(task.createdAt) || Date.now(),
    updatedAt: Number(task.updatedAt) || Date.now(),
  };
}

function normalizeSnapshot(value) {
  if (!value || typeof value !== 'object') return null;
  const tasks = (Array.isArray(value.tasks) ? value.tasks : [])
    .slice(0, MAX_TASKS)
    .map(normalizeTask)
    .filter(Boolean);
  const selectedTaskKey = String(value.selectedTaskKey || '');
  return {
    schemaVersion: 1,
    projectScopeId: String(value.projectScopeId || ''),
    graphRevision: String(value.graphRevision || ''),
    graphExcerpt: clone(value.graphExcerpt || {}, {}),
    tasks,
    selectedTaskKey: tasks.some((task) => task.issueKey === selectedTaskKey)
      ? selectedTaskKey
      : '',
    updatedAt: Number(value.updatedAt) || Date.now(),
  };
}

export function createCabbageAssistantContext(source = {}) {
  return normalizeSnapshot({
    projectScopeId: source.projectScopeId,
    graphRevision: source.graphRevision,
    graphExcerpt: source.graphExcerpt,
    tasks: source.tasks,
    selectedTaskKey: source.selectedTaskKey,
    updatedAt: Date.now(),
  });
}

export function publishCabbageAssistantContext(source = {}) {
  const snapshot = source?.schemaVersion === 1
    ? normalizeSnapshot(source)
    : createCabbageAssistantContext(source);
  if (!snapshot) return null;
  try {
    window.localStorage?.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  } catch (_) {}
  try {
    getChannel()?.postMessage({ type: CONTEXT_MESSAGE_TYPE, payload: snapshot });
  } catch (_) {}
  return snapshot;
}

export function readCabbageAssistantContext(projectScopeId = '') {
  try {
    const raw = window.localStorage?.getItem(STORAGE_KEY);
    if (!raw) return null;
    const snapshot = normalizeSnapshot(JSON.parse(raw));
    if (!snapshot) return null;
    if (projectScopeId && snapshot.projectScopeId !== String(projectScopeId)) return null;
    return snapshot;
  } catch (_) {
    return null;
  }
}

export function subscribeCabbageAssistantContext(listener, {
  projectScopeId = '',
  emitCurrent = true,
} = {}) {
  let latestUpdatedAt = 0;
  const getExpectedScope = () => String(
    typeof projectScopeId === 'function' ? projectScopeId() : projectScopeId || ''
  );

  const accept = (value) => {
    const snapshot = normalizeSnapshot(value);
    if (!snapshot) return;
    const expectedScope = getExpectedScope();
    if (expectedScope && snapshot.projectScopeId !== expectedScope) return;
    if (snapshot.updatedAt < latestUpdatedAt) return;
    latestUpdatedAt = snapshot.updatedAt;
    listener(snapshot);
  };

  const onBroadcast = (event) => {
    if (event?.data?.type !== CONTEXT_MESSAGE_TYPE) return;
    accept(event.data.payload);
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
