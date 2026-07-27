import { applyGeneratedNodeGraph, getGeneratedNodeGraphSnapshot, PROJECT_NODE_GRAPH_TARGET_ID } from '@/blockly/node-editor/aiNodeGraphService.js';
import { useDockStore } from '@/stores/dockStore.js';
import { aiService, appService } from '@/utils/bridge.js';
import { coronaEventBus } from '@/utils/eventBus.js';

const MUTATION_PATTERN = /(\u751f\u6210|\u5236\u4f5c|\u521b\u5efa|\u642d\u5efa|\u5b9e\u73b0|\u505a(?:\u4e00\u4e2a|\u4e2a)?|\u7f16\u8f91|\u4fee\u6539|\u8865\u5145|\u589e\u52a0|\u6dfb\u52a0|\u6269\u5c55|\u52a0(?:\u4e0a|\u5165|\u4e00\u4e2a|\u4e2a)?|\u5220\u9664|\u79fb\u9664|\u91cd\u505a|\u6539\u9020|generate|create|build|make|edit|modify|add|extend|delete|remove)/i;
const TARGET_PATTERN = /(\u6e38\u620f|demo|deno|\u73a9\u6cd5|\u529f\u80fd|\u8282\u70b9|\u79ef\u6728|\u903b\u8f91|\u573a\u666f|\u7269\u4f53|\u5bf9\u8c61|\u6a21\u578b|\u7403|\u6444\u50cf\u673a|\u79fb\u52a8|\u8df3\u8dc3|\u78b0\u649e|\u63a7\u5236|\u6309\u952e|\u7a7a\u683c|wasd|game|gameplay|block|node|logic|scene|object|actor|model|camera|move|jump|collision|control)/i;
const IMPERATIVE_PREFIX_PATTERN = /(?:^|[\s\u3002\uff0c,!.\uff01?\uff1f])(?:\u5e2e\u6211|\u5e2e\u5fd9|\u8bf7(?:\u4f60)?|\u7ed9\u6211|\u66ff\u6211|\u4e3a\u6211|\u9ebb\u70e6|\u6211\u8981|\u6211\u60f3(?:\u8ba9\u4f60)?|\u80fd\u5426|\u53ef\u4ee5(?:\u5e2e\u6211)?|please|could you|i want you to)/i;
const LEADING_MUTATION_PATTERN = /^(?:(?:\u8bf7(?:\u4f60)?|\u9ebb\u70e6|\u5e2e\u6211|\u5e2e\u5fd9|\u7ed9\u6211|\u66ff\u6211|\u4e3a\u6211)\s*)?(?:\u751f\u6210|\u5236\u4f5c|\u521b\u5efa|\u642d\u5efa|\u5b9e\u73b0|\u505a(?:\u4e00\u4e2a|\u4e2a)?|\u7f16\u8f91|\u4fee\u6539|\u8865\u5145|\u589e\u52a0|\u6dfb\u52a0|\u6269\u5c55|\u52a0(?:\u4e0a|\u5165|\u4e00\u4e2a|\u4e2a)?|\u5220\u9664|\u79fb\u9664|\u91cd\u505a|\u6539\u9020|generate|create|build|make|edit|modify|add|extend|delete|remove)/i;
const OBJECT_IMPERATIVE_PATTERN = /^(?:\u7ed9|\u4e3a|\u628a)(?:\u5f53\u524d|\u8fd9\u4e2a|\u8be5|\u6211\u7684)?(?:\u6e38\u620f|demo|deno|\u73a9\u6cd5|\u529f\u80fd|\u8282\u70b9|\u79ef\u6728|\u903b\u8f91).{0,24}?(?:\u751f\u6210|\u5236\u4f5c|\u521b\u5efa|\u642d\u5efa|\u5b9e\u73b0|\u7f16\u8f91|\u4fee\u6539|\u8865\u5145|\u589e\u52a0|\u6dfb\u52a0|\u6269\u5c55|\u5220\u9664|\u79fb\u9664|\u91cd\u505a|\u6539\u9020)/i;
const QUESTION_PATTERN = /(\u5982\u4f55|\u600e\u4e48|\u600e\u6837|\u4e3a\u4ec0\u4e48|\u662f\u4ec0\u4e48|\u6709\u4ec0\u4e48|\u80fd\u4e0d\u80fd|\u53ef\u4e0d\u53ef\u4ee5|\u5417\s*[?\uff1f]?$|how\s+(?:do|can|to)|what\b|why\b)/i;
const DELETE_PATTERN = /(\u5220\u9664|\u79fb\u9664|\u53bb\u6389|\u5220\u6389|delete|remove)/i;
const EDIT_PATTERN = /(\u4fee\u6539|\u7f16\u8f91|\u6539\u9020|\u91cd\u505a|\u8c03\u6574|edit|modify|rebuild|change)/i;
const EXTEND_PATTERN = /(\u8865\u5145|\u589e\u52a0|\u6dfb\u52a0|\u6269\u5c55|\u52a0(?:\u4e0a|\u5165|\u4e00\u4e2a|\u4e2a)?|extend|add)/i;
const FEATURE_TARGET_PATTERN = /(\u529f\u80fd|\u73a9\u6cd5|feature|function|gameplay)/i;
const POLL_INTERVAL_MS = 700;
const GENERATION_TIMEOUT_MS = 120000;

let activeGeneration = null;

function wait(delay) {
  return new Promise((resolve) => window.setTimeout(resolve, delay));
}

function messageOf(response, fallback) {
  return String(response?.message || response?.error || fallback);
}

function responseLanguageForInstruction(instruction) {
  if (/[\u3400-\u9fff]/.test(instruction)) return 'zh-CN';
  const locale = String(globalThis.document?.documentElement?.lang || '').trim();
  return locale.toLowerCase().startsWith('en') ? 'en-US' : 'zh-CN';
}

export function nodeGraphGenerationIntent(text) {
  const instruction = String(text || '').trim();
  const hasImperativePrefix = IMPERATIVE_PREFIX_PATTERN.test(instruction);
  const startsWithMutation = LEADING_MUTATION_PATTERN.test(instruction);
  const hasObjectImperative = OBJECT_IMPERATIVE_PATTERN.test(instruction);
  const isUncommandedQuestion = QUESTION_PATTERN.test(instruction) && !hasImperativePrefix;
  if (!instruction
    || !MUTATION_PATTERN.test(instruction)
    || !TARGET_PATTERN.test(instruction)
    || (!hasImperativePrefix && !startsWithMutation && !hasObjectImperative)
    || isUncommandedQuestion) {
    return { matched: false, operation: '', instruction };
  }
  let operation = 'create';
  if (DELETE_PATTERN.test(instruction)) operation = 'delete';
  else if (EDIT_PATTERN.test(instruction)) operation = 'edit';
  else if (EXTEND_PATTERN.test(instruction) || FEATURE_TARGET_PATTERN.test(instruction)) operation = 'extend';
  return { matched: true, operation, instruction };
}

async function requestNodePanelOpen() {
  try { useDockStore().openPanel('NodeGraphPanel'); } catch (_) {}
  coronaEventBus.emit('node-graph-panel-open-request');
  try {
    await appService.crossTabBroadcast('node-graph-panel-open-request', {});
  } catch (_) {}
}

async function acquireSnapshot() {
  let snapshot = await getGeneratedNodeGraphSnapshot({ timeoutMs: 900 });
  if (snapshot?.workspace) return snapshot;
  await requestNodePanelOpen();
  const deadline = Date.now() + 6000;
  while (Date.now() < deadline) {
    await wait(300);
    snapshot = await getGeneratedNodeGraphSnapshot({ timeoutMs: 700 });
    if (snapshot?.workspace) return snapshot;
  }
  throw new Error('请先打开“节点”窗口，包菜才能读取并修改当前节点逻辑。');
}

function assertCurrentRequest(state) {
  if (activeGeneration !== state || state.cancelled) {
    throw new Error('已停止本次节点生成。');
  }
}

export async function generateNodeGraphFromInstruction(instruction, operation = 'create') {
  if (activeGeneration) throw new Error('包菜正在生成上一份节点逻辑，请先等待或停止。');
  const state = { taskId: '', cancelled: false };
  activeGeneration = state;
  try {
    const snapshot = await acquireSnapshot();
    assertCurrentRequest(state);
    const requestId = `node_generate_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    const payload = {
      schemaVersion: 1,
      requestId,
      targetId: PROJECT_NODE_GRAPH_TARGET_ID,
      projectScopeId: String(snapshot.projectScopeId || ''),
      baseGraphRevision: String(snapshot.graphRevision || ''),
      operation,
      instruction: String(instruction || '').trim(),
      responseLanguage: responseLanguageForInstruction(instruction),
      workspace: snapshot.workspace,
      projectContext: snapshot.projectContext || {},
    };
    if (!payload.projectScopeId || !payload.baseGraphRevision) {
      throw new Error('当前世界的节点上下文尚未准备好，请稍后再试。');
    }

    const started = await aiService.startNodeGraphGeneration(payload);
    state.taskId = String(started?.taskId || '');
    if (state.cancelled && state.taskId) {
      try { await aiService.cancelNodeGraphGeneration(state.taskId); } catch (_) {}
      throw new Error('已停止本次节点生成。');
    }
    if (started?.success !== true || !state.taskId) {
      throw new Error(messageOf(started, 'DeepSeek 节点生成服务暂时不可用。'));
    }

    const deadline = Date.now() + GENERATION_TIMEOUT_MS;
    let generated = null;
    while (Date.now() < deadline) {
      assertCurrentRequest(state);
      const status = await aiService.getNodeGraphGenerationStatus(state.taskId);
      assertCurrentRequest(state);
      if (status?.success !== true) {
        throw new Error(messageOf(status, '无法读取节点生成状态。'));
      }
      if (status.status === 'cancelled') throw new Error('已停止本次节点生成。');
      if (status.status === 'completed') {
        generated = status.result;
        break;
      }
      await wait(POLL_INTERVAL_MS);
    }
    if (!generated) throw new Error('DeepSeek 生成节点逻辑超时，当前节点图没有被修改。');
    if (generated.success !== true || generated.status !== 'ok') {
      throw new Error(messageOf(generated, 'DeepSeek 没有返回可应用的节点图。'));
    }
    for (const key of ['requestId', 'targetId', 'projectScopeId', 'baseGraphRevision', 'operation']) {
      if (String(generated[key] || '') !== String(payload[key] || '')) {
        throw new Error(`DeepSeek 返回的 ${key} 已过期，当前节点图没有被修改。`);
      }
    }

    const latest = await getGeneratedNodeGraphSnapshot({ timeoutMs: 1800 });
    if (!latest?.workspace
      || String(latest.projectScopeId || '') !== payload.projectScopeId
      || String(latest.graphRevision || '') !== payload.baseGraphRevision) {
      throw new Error('生成期间当前世界或节点逻辑已经改变，旧结果没有覆盖你的编辑。');
    }

    const applied = await applyGeneratedNodeGraph(generated);
    if (applied?.success !== true) {
      const details = Array.isArray(applied?.errors) ? applied.errors.join('；') : '';
      throw new Error(details || '生成结果未通过节点编辑器校验，当前节点图没有被修改。');
    }
    return {
      success: true,
      summary: String(generated.summary || '节点逻辑已经生成并保存。'),
      warnings: Array.isArray(applied.warnings) ? applied.warnings : [],
    };
  } finally {
    if (activeGeneration === state) activeGeneration = null;
  }
}

export async function cancelActiveNodeGraphGeneration() {
  const state = activeGeneration;
  if (!state) return false;
  state.cancelled = true;
  if (state.taskId) {
    try { await aiService.cancelNodeGraphGeneration(state.taskId); } catch (_) {}
  }
  return true;
}
