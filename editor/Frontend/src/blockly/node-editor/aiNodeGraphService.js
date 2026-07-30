const INTERNAL_AI_SCHEMA_VERSION = 1;
export const PROJECT_NODE_GRAPH_TARGET_ID = 'node_graph:project:global';
const VALID_NODE_TYPES = new Set(['start', 'custom', 'end']);
const VALID_PORT_SIDES = new Set(['left', 'right', 'bottom']);

const consumers = new Map();
const CHANNEL_NAME = 'corona-node-graph-ai-v2';
const INSTANCE_ID = `node_graph_ai_${Date.now()}_${Math.random().toString(36).slice(2)}`;
let channel = null;
let requestSequence = 0;
const pendingRequests = new Map();

function cloneJson(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (error) {
    throw new Error(`内部 AI 结果不是可序列化的 JSON：${error?.message || error}`);
  }
}

function hashText(text) {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

/** Full revision for generation. Unlike review fingerprints, this includes node layout. */
export function generatedNodeGraphRevision(workspace, scope = '') {
  const normalizedScope = String(scope || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/\/+$/, '')
    .toLocaleLowerCase('en-US');
  return hashText(`${normalizedScope}\n${JSON.stringify(workspace || {})}`);
}

function finiteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function workspaceRoots(state, label) {
  if (!state || typeof state !== 'object' || Array.isArray(state)) {
    throw new Error(`${label} 必须是 Blockly workspace 对象`);
  }
  if (state.blocks == null) return [];
  if (!state.blocks || typeof state.blocks !== 'object' || Array.isArray(state.blocks)) {
    throw new Error(`${label}.blocks 必须是对象`);
  }
  if (state.blocks.blocks == null) return [];
  if (!Array.isArray(state.blocks.blocks)) {
    throw new Error(`${label}.blocks.blocks 必须是数组`);
  }
  return state.blocks.blocks;
}

function validateSerializedBlock(block, ids, label) {
  if (!block || typeof block !== 'object' || Array.isArray(block)) {
    throw new Error(`${label} 必须是 Blockly serialization block 对象`);
  }
  const id = String(block.id || '').trim();
  const type = String(block.type || '').trim();
  if (!id) throw new Error(`${label} 缺少积木 ID`);
  if (ids.has(id)) throw new Error(`${label} 的积木 ID 重复：${id}`);
  ids.add(id);
  if (!type) throw new Error(`${label} 缺少积木 type`);

  const walkConnection = (connection, connectionLabel, allowShadow = true) => {
    if (!connection || typeof connection !== 'object' || Array.isArray(connection)) {
      throw new Error(`${connectionLabel} 必须是连接对象`);
    }
    const children = [];
    if (connection.block && typeof connection.block === 'object') children.push(connection.block);
    if (allowShadow && connection.shadow && typeof connection.shadow === 'object') children.push(connection.shadow);
    if (!children.length) throw new Error(`${connectionLabel} 必须包含 block${allowShadow ? ' 或 shadow' : ''}`);
    children.forEach((child, index) => validateSerializedBlock(child, ids, `${connectionLabel}[${index}]`));
  };

  if (block.inputs != null) {
    if (!block.inputs || typeof block.inputs !== 'object' || Array.isArray(block.inputs)) {
      throw new Error(`${label}.inputs 必须是对象`);
    }
    Object.entries(block.inputs).forEach(([name, connection]) => {
      walkConnection(connection, `${label}.inputs.${name}`);
    });
  }
  if (block.next != null) walkConnection(block.next, `${label}.next`, false);
}

function validateWorkspace(state, label, { condition = false } = {}) {
  const roots = workspaceRoots(state, label);
  const ids = new Set();
  roots.forEach((block, index) => validateSerializedBlock(block, ids, `${label}.blocks[${index}]`));
  if (condition && roots.length !== 1) {
    throw new Error(`${label} 必须包含且只包含一个可见的 Boolean 顶层条件积木；无条件跳转请使用 logic_boolean TRUE`);
  }
}

/**
 * Validate and clone the JSON envelope used by the future in-editor AI.
 * This function never accepts XML text, paths, or generated Python.
 */
export function validateGeneratedNodeGraphResult(result) {
  if (!result || typeof result !== 'object' || Array.isArray(result)) {
    throw new Error('内部 AI 结果必须是 JSON 对象，不能是 XML、文件路径或文本');
  }
  if (result.schemaVersion !== INTERNAL_AI_SCHEMA_VERSION) {
    throw new Error(`schemaVersion 必须为 ${INTERNAL_AI_SCHEMA_VERSION}`);
  }
  if (result.targetId !== PROJECT_NODE_GRAPH_TARGET_ID) {
    throw new Error(`targetId 必须为 ${PROJECT_NODE_GRAPH_TARGET_ID}`);
  }
  if (Object.prototype.hasOwnProperty.call(result, 'generatedCode') || Object.prototype.hasOwnProperty.call(result, 'GeneratedCode')) {
    throw new Error('内部 AI 不得提供 Python；代码必须由 nodeGraphToCode 从可见积木生成');
  }

  const cloned = cloneJson(result);
  const workspace = cloned.workspace;
  if (!workspace || typeof workspace !== 'object' || Array.isArray(workspace)) {
    throw new Error('workspace 必须是对象');
  }
  if (workspace.version !== 1) throw new Error('workspace.version 必须为 1');
  if (!Array.isArray(workspace.nodes)) throw new Error('workspace.nodes 必须是数组');
  if (!Array.isArray(workspace.edges)) throw new Error('workspace.edges 必须是数组');
  if (!workspace.globalVariablesWorkspace || typeof workspace.globalVariablesWorkspace !== 'object' || Array.isArray(workspace.globalVariablesWorkspace)) {
    throw new Error('workspace.globalVariablesWorkspace 必须是对象');
  }

  const nodeIds = new Set();
  let startCount = 0;
  workspace.nodes.forEach((node, index) => {
    const label = `nodes[${index}]`;
    if (!node || typeof node !== 'object' || Array.isArray(node)) throw new Error(`${label} 必须是对象`);
    const id = String(node.id || '').trim();
    if (!id) throw new Error(`${label} 缺少 ID`);
    if (nodeIds.has(id)) throw new Error(`节点 ID 重复：${id}`);
    nodeIds.add(id);
    if (!VALID_NODE_TYPES.has(node.nodeType)) throw new Error(`${label}.nodeType 无效：${node.nodeType || ''}`);
    if (node.nodeType === 'start') startCount += 1;
    if (!finiteNumber(node.x) || !finiteNumber(node.y)) throw new Error(`${label} 的 x/y 必须是有限数值`);
    validateWorkspace(node.workspace || {}, `节点 ${id} workspace`);
  });
  if (startCount !== 1) throw new Error('节点图必须恰好包含一个 start 节点');

  const edgeIds = new Set();
  workspace.edges.forEach((edge, index) => {
    const label = `edges[${index}]`;
    if (!edge || typeof edge !== 'object' || Array.isArray(edge)) throw new Error(`${label} 必须是对象`);
    const id = String(edge.id || '').trim();
    if (!id) throw new Error(`${label} 缺少 ID`);
    if (edgeIds.has(id)) throw new Error(`连线 ID 重复：${id}`);
    edgeIds.add(id);
    ['source', 'target'].forEach((role) => {
      const endpoint = edge[role];
      if (!endpoint || typeof endpoint !== 'object' || Array.isArray(endpoint)) {
        throw new Error(`${label}.${role} 必须是端点对象`);
      }
      if (!nodeIds.has(String(endpoint.nodeId || ''))) {
        throw new Error(`${label}.${role} 指向不存在的节点：${endpoint.nodeId || ''}`);
      }
      if (!VALID_PORT_SIDES.has(endpoint.side)) throw new Error(`${label}.${role}.side 无效`);
      if (!Number.isInteger(endpoint.index) || endpoint.index < 0) throw new Error(`${label}.${role}.index 必须是非负整数`);
    });
    validateWorkspace(edge.conditionWorkspace || {}, `连线 ${id} conditionWorkspace`, { condition: true });
  });
  validateWorkspace(workspace.globalVariablesWorkspace, 'globalVariablesWorkspace');
  return cloned;
}

/** Register the currently mounted project-level node editor as the internal AI target. */
export function registerGeneratedNodeGraphConsumer(consumer, options = {}) {
  const config = typeof consumer === 'function'
    ? { handler: consumer, ...options }
    : (consumer && typeof consumer === 'object' ? consumer : {});
  if (typeof config.handler !== 'function') {
    throw new TypeError('Generated node graph consumer must provide a handler function');
  }
  const id = String(config.instanceId || `${INSTANCE_ID}_${++requestSequence}`);
  consumers.set(id, {
    id,
    handler: config.handler,
    getSnapshot: typeof config.getSnapshot === 'function' ? config.getSnapshot : null,
  });
  ensureChannel();
  return () => consumers.delete(id);
}

function ensureChannel() {
  if (channel || typeof BroadcastChannel === 'undefined') return channel;
  channel = new BroadcastChannel(CHANNEL_NAME);
  channel.addEventListener('message', handleChannelMessage);
  return channel;
}

function cloneSnapshot(value) {
  return cloneJson(value || {});
}

async function localSnapshot() {
  const active = Array.from(consumers.values()).filter((item) => item.getSnapshot);
  if (active.length !== 1) return null;
  const snapshot = await active[0].getSnapshot();
  if (!snapshot || typeof snapshot !== 'object') return null;
  return cloneSnapshot(snapshot);
}

function settlePending(requestId, payload) {
  const pending = pendingRequests.get(requestId);
  if (!pending) return;
  if (pending.accept && !pending.accept(payload)) return;
  pendingRequests.delete(requestId);
  window.clearTimeout(pending.timer);
  pending.resolve(payload);
}

async function handleChannelMessage(event) {
  const message = event?.data;
  if (!message || typeof message !== 'object' || message.senderId === INSTANCE_ID) return;
  if (message.kind === 'snapshot-response' || message.kind === 'apply-response') {
    settlePending(String(message.requestId || ''), message);
    return;
  }

  if (message.kind === 'snapshot-request') {
    const snapshot = await localSnapshot();
    if (!snapshot) return;
    ensureChannel()?.postMessage({
      kind: 'snapshot-response',
      requestId: message.requestId,
      senderId: INSTANCE_ID,
      snapshot,
    });
    return;
  }

  if (message.kind === 'apply-request') {
    const active = Array.from(consumers.values());
    if (active.length !== 1) return;
    let result;
    try {
      result = await active[0].handler(message.result);
    } catch (error) {
      result = { success: false, errors: [String(error?.message || error)], warnings: [] };
    }
    ensureChannel()?.postMessage({
      kind: 'apply-response',
      requestId: message.requestId,
      senderId: INSTANCE_ID,
      result,
    });
  }
}

function requestAcrossWindows(kind, payload, { timeoutMs = 2500, accept = null } = {}) {
  const currentChannel = ensureChannel();
  if (!currentChannel) return Promise.resolve(null);
  const requestId = `${kind}_${Date.now()}_${++requestSequence}`;
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => {
      pendingRequests.delete(requestId);
      resolve(null);
    }, Math.max(250, Number(timeoutMs) || 2500));
    pendingRequests.set(requestId, { resolve, timer, accept });
    currentChannel.postMessage({ kind, requestId, senderId: INSTANCE_ID, ...payload });
  });
}

/** Obtain the mounted project graph, including detached node-Dock windows. */
export async function getGeneratedNodeGraphSnapshot({ timeoutMs = 2500 } = {}) {
  const local = await localSnapshot();
  if (local) return local;
  const response = await requestAcrossWindows('snapshot-request', {}, {
    timeoutMs,
    accept: (message) => Boolean(message?.snapshot?.workspace),
  });
  return response?.snapshot ? cloneSnapshot(response.snapshot) : null;
}

/**
 * Apply an internal AI result to the mounted project graph. The mounted editor performs
 * compilation, persistence, and rollback. Detached Dock windows are reached through the
 * same-origin BroadcastChannel; no C++ interface or file import route is involved.
 */
export async function applyGeneratedNodeGraph(result, { timeoutMs = 12000 } = {}) {
  let validated;
  try {
    validated = validateGeneratedNodeGraphResult(result);
  } catch (error) {
    return { success: false, errors: [String(error?.message || error)], warnings: [] };
  }
  const active = Array.from(consumers.values());
  if (active.length > 1) {
    return { success: false, errors: ['\u68c0\u6d4b\u5230\u591a\u4e2a\u9879\u76ee\u8282\u70b9\u56fe\u7f16\u8f91\u5668\uff0c\u65e0\u6cd5\u786e\u5b9a\u5e94\u7528\u76ee\u6807'], warnings: [] };
  }
  if (active.length === 1) {
    try {
      return await active[0].handler(validated);
    } catch (error) {
      return { success: false, errors: [String(error?.message || error)], warnings: [] };
    }
  }

  const response = await requestAcrossWindows('apply-request', { result: validated }, {
    timeoutMs,
    accept: (message) => Boolean(message?.result),
  });
  return response?.result || {
    success: false,
    errors: ['\u9879\u76ee\u5e38\u9a7b\u8282\u70b9\u56fe\u5c1a\u672a\u6253\u5f00\uff0c\u65e0\u6cd5\u5e94\u7528\u5185\u90e8 AI \u7ed3\u679c'],
    warnings: [],
  };
}
