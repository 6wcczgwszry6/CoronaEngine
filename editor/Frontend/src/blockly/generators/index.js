// 统一注册各分类的 Python 代码生成器，并自定义 workspaceToCode
import * as Blockly from 'blockly/core';
import { pythonGenerator } from 'blockly/python';
import { resetPrelude, renderPreludeAt } from './prelude';
import { PYTHON_IMPORTS } from './constants';

import { defineAppearanceGenerators } from './appearance';
import { defineAudioGenerators } from './audio';
import { defineCameraGenerators } from './camera';
import { defineControlGenerators } from './control';
import { defineDetectGenerators } from './detect';
import { defineEngineGenerators } from './engine';
import { defineEventGenerators } from './event';
import { defineListGenerators } from './list';
import { defineObjectGenerators } from './object';
import { defineUiGenerators } from './ui';
import { defineMathGenerators } from './math';
import { defineVariableGenerators } from './variable';

// 注册所有分类的生成器（幂等）
try { defineAppearanceGenerators?.(); } catch {}
try { defineAudioGenerators?.(); } catch {}
try { defineCameraGenerators?.(); } catch {}
try { defineControlGenerators?.(); } catch {}
try { defineDetectGenerators?.(); } catch {}
try { defineEngineGenerators?.(); } catch {}
try { defineEventGenerators?.(); } catch {}
try { defineListGenerators?.(); } catch {}
try { defineObjectGenerators?.(); } catch {}
try { defineUiGenerators?.(); } catch {}
try { defineMathGenerators?.(); } catch {}
try { defineVariableGenerators?.(); } catch {}

// 辅助：规范化 blockToCode 的返回（string | [string, order] | null）
function normalizeCode(out) {
  if (!out) return '';
  if (Array.isArray(out)) return String(out[0] ?? '');
  return String(out);
}

// 缩进工具
function indentBlock(s) {
  if (!s) return '';
  // 去除首尾空行，避免产生多余的空白行
  s = s.replace(/^\s*\n+|\n+\s*$/g, '');
  return s
    .split('\n')
    .map((line) => (line ? '    ' + line : ''))
    .join('\n');
}

// ── 自定义工作区 → Python 代码 ──
pythonGenerator.workspaceToCode = function customWorkspaceToCode(workspace) {
  // 在一次生成开始前，重置前置代码请求集合
  resetPrelude();
  // 初始化生成器（包括 procedure / variable 数据库）
  pythonGenerator.init(workspace);

  // 拿到顶层积木并按坐标排序
  const topBlocks = workspace.getTopBlocks(true);
  topBlocks.sort((a, b) => {
    const aXY = a.getRelativeToSurfaceXY();
    const bXY = b.getRelativeToSurfaceXY();
    return aXY.y - bXY.y || aXY.x - bXY.x;
  });

  // 区分帽子积木（无 previousConnection）和孤立积木
  const hatBlocks = topBlocks.filter((b) => !b.previousConnection);
  const orphanCount = topBlocks.length - hatBlocks.length;

  // ── 积木类型分类 ──
  const KEYBOARD_BLOCK_TYPES = new Set(['event_keyboard', 'event_keyboard_combo']);
  const MOUSE_BLOCK_TYPES = new Set([
    'event_mouse_click', 'event_mouse_move',
    'event_mouse_wheel', 'event_mouse_contextmenu',
  ]);
  const BROADCAST_HAT_TYPE = 'event_RB';
  const CLONE_HAT_TYPE = 'control_cloneStart';
  // 标准函数定义块 —— 生成的 def 语句放在顶层，不嵌套在 run() 内
  const PROCEDURE_BLOCK_TYPES = new Set([
    'procedures_defnoreturn',
    'procedures_defreturn',
  ]);

  let mainCode = '';
  let handlerCode = '';
  let mouseHandlerCode = '';
  let procedureCode = '';
  let runtimeHandlerCode = '';
  const runtimeRegistrations = [];
  let broadcastHandlerIndex = 0;
  let cloneHandlerIndex = 0;

  const codeAfterHat = (block) => {
    const next = block.getNextBlock?.();
    if (!next) return '';
    let code = normalizeCode(pythonGenerator.blockToCode(next));
    if (code && !code.endsWith('\n')) code += '\n';
    return code;
  };

  for (const block of hatBlocks) {
    // Blockly v12+: block.disabled 仅反映自身禁用状态，不包含父级继承的禁用。
    // 使用 isEnabled() + getInheritedDisabled() 确保完整检查（上游 issue #9372）。
    if (!block.isEnabled() || block.getInheritedDisabled()) continue;
    if (block.type === BROADCAST_HAT_TYPE) {
      const message = block.getFieldValue('x') || '';
      const functionName = `_broadcast_handler_${broadcastHandlerIndex++}`;
      const body = indentBlock(codeAfterHat(block));
      runtimeHandlerCode += `def ${functionName}():\n${body || '    pass'}\n\n`;
      runtimeRegistrations.push(
        `CoronaEngine.register_broadcast_handler(${JSON.stringify(message)}, ${functionName})`,
      );
      continue;
    }
    if (block.type === CLONE_HAT_TYPE) {
      const functionName = `_clone_start_handler_${cloneHandlerIndex++}`;
      const body = indentBlock(codeAfterHat(block));
      runtimeHandlerCode += `def ${functionName}():\n${body || '    pass'}\n\n`;
      runtimeRegistrations.push(`CoronaEngine.register_clone_start_handler(${functionName})`);
      continue;
    }

    let blockCode = pythonGenerator.blockToCode(block);
    let chunk = normalizeCode(blockCode);
    if (chunk && !chunk.endsWith('\n')) chunk += '\n';

    if (KEYBOARD_BLOCK_TYPES.has(block.type)) {
      handlerCode += chunk;
    } else if (MOUSE_BLOCK_TYPES.has(block.type)) {
      mouseHandlerCode += chunk;
    } else if (PROCEDURE_BLOCK_TYPES.has(block.type)) {
      // 函数定义放在顶层
      procedureCode += chunk;
    } else {
      mainCode += chunk;
    }
  }

  // ── 孤立积木警告 ──
  let orphanWarning = '';
  if (orphanCount > 0) {
    orphanWarning =
      `# =========================================\n` +
      `# WARNING: ${orphanCount} 个孤立积木未连接任何事件积木，不会执行\n` +
      `# 请将它们连接到事件积木（如"当游戏开始时"）下方\n` +
      `# =========================================\n`;
  }

  // ── 结束生成 ──
  mainCode = pythonGenerator.finish(mainCode);
  if (mainCode && !mainCode.endsWith('\n')) mainCode += '\n';

  // ── 头注释 ──
  const timestamp = new Date().toISOString();
  const header = [
    '# -*- coding: utf-8 -*-',
    `# Generated from Blockly by CabbageEditor @ ${timestamp}`,
    PYTHON_IMPORTS.ENGINE_IMPORT,
  ].join('\n');

  // ── 前置片段 ──
  const preludeGlobal = renderPreludeAt('global');
  const preludeRunPrologue = renderPreludeAt('runPrologue');
  const preludeRunEpilogue = renderPreludeAt('runEpilogue');

  // ── 组装输出 ──
  const parts = [];
  parts.push(header);
  if (orphanWarning) parts.push(orphanWarning.trimEnd());
  if (preludeGlobal) parts.push(preludeGlobal.trimEnd());

  // 函数定义（顶层，不缩进 — 可被 run() 内代码调用）
  if (procedureCode.trim()) {
    parts.push('');
    parts.push(procedureCode.trimEnd());
  }

  // 键盘事件 handler
  // Runtime broadcast and clone handlers are defined globally and registered in run().
  if (runtimeHandlerCode.trim()) {
    parts.push('');
    parts.push(runtimeHandlerCode.trimEnd());
  }

  if (handlerCode.trim()) {
    parts.push('');
    parts.push('def handle(key, _mods=None):');
    const indentedHandlers = indentBlock(handlerCode);
    if (indentedHandlers) parts.push(indentedHandlers);
    else parts.push('    pass');
  }

  // 鼠标事件 handler
  if (mouseHandlerCode.trim()) {
    parts.push('');
    parts.push('def handle_mouse(_event_type, _button, _x, _y):');
    const indentedMouseHandlers = indentBlock(mouseHandlerCode);
    if (indentedMouseHandlers) parts.push(indentedMouseHandlers);
    else parts.push('    pass');
  }

  // 主函数 def run()
  parts.push('');
  parts.push('def run():');
  const runBody = [];
  if (runtimeRegistrations.length) {
    runBody.push(indentBlock(runtimeRegistrations.join('\n')));
  }
  const indentedPrologue = indentBlock(preludeRunPrologue);
  if (indentedPrologue) runBody.push(indentedPrologue);
  const indentedMain = indentBlock(mainCode);
  if (indentedMain) runBody.push(indentedMain);
  const indentedEpilogue = indentBlock(preludeRunEpilogue);
  if (indentedEpilogue) runBody.push(indentedEpilogue);
  if (runBody.length) {
    parts.push(runBody.join('\n'));
  } else {
    parts.push('    pass');
  }

  // 末尾统一加一个换行
  return parts.join('\n') + '\n';
};

export { pythonGenerator };

const NODE_KEYBOARD_HATS = new Set(['event_keyboard', 'event_keyboard_combo']);
const NODE_MOUSE_HATS = new Set([
  'event_mouse_click',
  'event_mouse_move',
  'event_mouse_wheel',
  'event_mouse_contextmenu',
]);
const NODE_PROCEDURE_BLOCKS = new Set(['procedures_defnoreturn', 'procedures_defreturn']);
const GLOBAL_WORKSPACE_ROOT_TYPES = new Set(['variable_define', 'list_define', 'variable_show', 'variable_hide', 'list_show', 'list_hide']);
const BLOCKING_ACTIVE_LOOP_TYPES = new Set(['control_for', 'control_until', 'controls_whileUntil']);

function hasWorkspaceBlocks(state) {
  return Boolean(Array.isArray(state?.blocks?.blocks) && state.blocks.blocks.length);
}

function loadSerializedWorkspace(state) {
  const workspace = new Blockly.Workspace();
  if (state && typeof state === 'object' && Object.keys(state).length) {
    Blockly.serialization.workspaces.load(JSON.parse(JSON.stringify(state)), workspace);
  }
  return workspace;
}

function sortedEnabledTopBlocks(workspace) {
  return workspace
    .getTopBlocks(true)
    .filter((block) => block.isEnabled?.() !== false && !block.getInheritedDisabled?.())
    .sort((a, b) => {
      const aXY = a.getRelativeToSurfaceXY?.() || { x: 0, y: 0 };
      const bXY = b.getRelativeToSurfaceXY?.() || { x: 0, y: 0 };
      return aXY.y - bXY.y || aXY.x - bXY.x;
    });
}

function pythonString(value) {
  return JSON.stringify(String(value ?? ''));
}

function safePythonId(value, prefix = 'node') {
  const normalized = String(value ?? '')
    .replace(/[^a-zA-Z0-9_]/g, '_')
    .replace(/^([0-9])/, '_$1');
  return `${prefix}_${normalized || 'unnamed'}`;
}

export function validateNodeGraph(rawGraph) {
  const graph = rawGraph && typeof rawGraph === 'object' ? rawGraph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  const startNodes = nodes.filter((node) => node?.nodeType === 'start');
  if (startNodes.length !== 1) {
    throw new Error(startNodes.length === 0 ? '\u8282\u70b9\u56fe\u5fc5\u987b\u5305\u542b\u4e00\u4e2a\u5f00\u59cb\u8282\u70b9' : '\u8282\u70b9\u56fe\u53ea\u80fd\u5305\u542b\u4e00\u4e2a\u5f00\u59cb\u8282\u70b9');
  }
  const ids = nodes.map((node) => String(node?.id ?? ''));
  if (ids.some((id) => !id)) throw new Error('\u8282\u70b9\u56fe\u4e2d\u5b58\u5728\u7f3a\u5c11 ID \u7684\u8282\u70b9');
  if (new Set(ids).size !== ids.length) throw new Error('\u8282\u70b9\u56fe\u4e2d\u5b58\u5728\u91cd\u590d\u7684\u8282\u70b9 ID');
  const nodeIds = new Set(ids);
  const validSides = new Set(['left', 'right', 'bottom']);
  const edgeIds = new Set();
  for (const edge of edges) {
    const edgeId = String(edge?.id ?? '');
    if (!edgeId) throw new Error('\u8282\u70b9\u56fe\u4e2d\u5b58\u5728\u7f3a\u5c11 ID \u7684\u8fde\u7ebf');
    if (edgeIds.has(edgeId)) throw new Error(`\u8fde\u7ebf ID \u91cd\u590d: ${edgeId}`);
    edgeIds.add(edgeId);
    for (const [label, endpoint] of [['\u8d77\u70b9', edge?.source], ['\u7ec8\u70b9', edge?.target]]) {
      if (!nodeIds.has(String(endpoint?.nodeId ?? ''))) throw new Error(`\u8fde\u7ebf\u201c${edge?.name || edgeId}\u201d${label}\u6307\u5411\u4e0d\u5b58\u5728\u7684\u8282\u70b9`);
      if (!validSides.has(endpoint?.side) || !Number.isInteger(Number(endpoint?.index)) || Number(endpoint.index) < 0) throw new Error(`\u8fde\u7ebf\u201c${edge?.name || edgeId}\u201d${label}\u7aef\u53e3\u65e0\u6548`);
    }
  }
  const outgoing = new Map(ids.map((id) => [id, []]));
  for (const edge of edges) outgoing.get(String(edge.source.nodeId))?.push(edge);
  const reachable = new Set();
  const queue = [String(startNodes[0].id)];
  while (queue.length) {
    const id = queue.shift();
    if (reachable.has(id)) continue;
    reachable.add(id);
    for (const edge of outgoing.get(id) || []) queue.push(String(edge.target.nodeId));
  }
  const warnings = [];
  const unreachable = nodes.filter((node) => !reachable.has(String(node.id)));
  if (unreachable.length) warnings.push(`${unreachable.length} \u4e2a\u8282\u70b9\u4ece\u5f00\u59cb\u8282\u70b9\u4e0d\u53ef\u8fbe`);
  for (const node of nodes) {
    const name = node?.nodeType === 'custom' ? node?.customName || node?.name || '\u81ea\u5b9a\u4e49\u8282\u70b9' : node?.nodeType === 'start' ? '\u5f00\u59cb\u8282\u70b9' : '\u7ed3\u675f\u8282\u70b9';
    if (node?.nodeType !== 'end' && !(outgoing.get(String(node.id)) || []).length) warnings.push(`\u8282\u70b9\u201c${name}\u201d\u6ca1\u6709\u51fa\u7ebf\uff0c\u8fd0\u884c\u65f6\u4f1a\u505c\u7559`);
    if (!hasWorkspaceBlocks(node?.workspace || {})) warnings.push(`\u8282\u70b9\u201c${name}\u201d\u5185\u90e8\u6ca1\u6709\u79ef\u6728`);
  }
  if (hasWorkspaceBlocks(graph.globalVariablesWorkspace || {})) {
    const workspace = loadSerializedWorkspace(graph.globalVariablesWorkspace || {});
    try {
      for (const block of sortedEnabledTopBlocks(workspace)) {
        if (!GLOBAL_WORKSPACE_ROOT_TYPES.has(block.type)) {
          throw new Error(block.outputConnection
            ? '\u5168\u5c40\u53d8\u91cf\u6c60\u4e2d\u7684\u8fd4\u56de\u503c\u79ef\u6728\u5fc5\u987b\u8fde\u63a5\u5230\u521d\u59cb\u5316\u79ef\u6728'
            : '\u6b64\u79ef\u6728\u5e94\u653e\u5165\u8282\u70b9\u5185\u90e8\u7f16\u8f91\u533a');
        }
      }
    } finally {
      workspace.dispose();
    }
  }
  for (const node of nodes) {
    if (!hasWorkspaceBlocks(node?.workspace || {})) continue;
    const workspace = loadSerializedWorkspace(node.workspace || {});
    try {
      for (const block of workspace.getAllBlocks?.(false) || []) {
        if (block.type !== 'node_while_active') continue;
        const descendants = block.getDescendants?.(false) || [];
        if (descendants.some((child) => child !== block && BLOCKING_ACTIVE_LOOP_TYPES.has(child.type))) {
          const name = node?.customName || node?.name || node?.id || '';
          throw new Error(`\u8282\u70b9\u201c${name}\u201d\u7684\u201c\u5f53\u524d\u8282\u70b9\u6301\u7eed\u65f6\u201d\u4e2d\u4e0d\u80fd\u4f7f\u7528\u6c38\u4e45\u6216\u963b\u585e\u5faa\u73af`);
        }
      }
    } finally {
      workspace.dispose();
    }
  }
  return { warnings };
}

/**
 * Compile serialized node graph data into Python executable by the Scratch runtime.
 * Keep the existing node graph JSON schema unchanged.
 */
export function nodeGraphToCode(rawGraph) {
  const graph = rawGraph && typeof rawGraph === 'object' ? rawGraph : {};
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  validateNodeGraph(graph);
  const startNode = nodes.find((node) => node?.nodeType === 'start');

  resetPrelude();
  const procedureChunks = [];
  const keyboardChunks = [];
  const mouseChunks = [];
  const runtimeDefinitions = [];
  const runtimeRegistrations = [];
  const nodeLifecycle = new Map();
  const conditionFunctions = new Map();
  let runtimeIndex = 0;

  const codeAfterHat = (block) => {
    let code = block.getInput?.('DO') ? pythonGenerator.statementToCode(block, 'DO') : '';
    if (!code) {
      const next = block.getNextBlock?.();
      if (next) code = normalizeCode(pythonGenerator.blockToCode(next));
    }
    if (code && !code.endsWith('\n')) code += '\n';
    return code;
  };

  const compileWorkspace = (state, nodeId, isGlobal = false) => {
    const lifecycle = { enter: [], active: [], exit: [] };
    if (!hasWorkspaceBlocks(state)) return lifecycle;
    const workspace = loadSerializedWorkspace(state);
    try {
      pythonGenerator.init(workspace);
      for (const block of sortedEnabledTopBlocks(workspace)) {
        if (NODE_PROCEDURE_BLOCKS.has(block.type)) {
          const code = normalizeCode(pythonGenerator.blockToCode(block));
          if (code.trim()) procedureChunks.push(code.trimEnd());
          continue;
        }
        if (['node_when_enter', 'node_while_active', 'node_when_exit'].includes(block.type)) {
          if (isGlobal) continue;
          const bucket = block.type === 'node_when_enter' ? 'enter' : block.type === 'node_while_active' ? 'active' : 'exit';
          const code = codeAfterHat(block);
          if (code.trim()) lifecycle[bucket].push(code);
          continue;
        }
        if (block.type === 'event_gameStart') {
          if (!isGlobal) lifecycle.enter.push(codeAfterHat(block));
          continue;
        }
        if (NODE_KEYBOARD_HATS.has(block.type)) {
          if (!isGlobal) {
            const code = normalizeCode(pythonGenerator.blockToCode(block));
            if (code.trim()) keyboardChunks.push(`if _node_graph_state == ${pythonString(nodeId)}:\n${indentBlock(code)}`);
          }
          continue;
        }
        if (NODE_MOUSE_HATS.has(block.type)) {
          if (!isGlobal) {
            const code = normalizeCode(pythonGenerator.blockToCode(block));
            if (code.trim()) mouseChunks.push(`if _node_graph_state == ${pythonString(nodeId)}:\n${indentBlock(code)}`);
          }
          continue;
        }
        if (block.type === 'event_RB' || block.type === 'control_cloneStart') {
          if (isGlobal) continue;
          const functionName = `_node_runtime_handler_${runtimeIndex++}`;
          const body = indentBlock(codeAfterHat(block));
          runtimeDefinitions.push(`def ${functionName}():\n    if _node_graph_state != ${pythonString(nodeId)}:\n        return\n${body || '    pass'}`);
          if (block.type === 'event_RB') runtimeRegistrations.push(`CoronaEngine.register_broadcast_handler(${pythonString(block.getFieldValue('x') || '')}, ${functionName})`);
          else runtimeRegistrations.push(`CoronaEngine.register_clone_start_handler(${functionName})`);
          continue;
        }
        let code = normalizeCode(pythonGenerator.blockToCode(block));
        if (code && !code.endsWith('\n')) code += '\n';
        if (code.trim()) lifecycle.enter.push(code);
      }
    } finally {
      workspace.dispose();
    }
    return lifecycle;
  };

  const globalCode = compileWorkspace(graph.globalVariablesWorkspace || {}, '', true).enter.join('');
  for (const node of nodes) nodeLifecycle.set(String(node.id), compileWorkspace(node.workspace || {}, String(node.id), false));

  edges.forEach((edge, index) => {
    const state = edge?.conditionWorkspace || {};
    if (!hasWorkspaceBlocks(state)) return;
    const workspace = loadSerializedWorkspace(state);
    try {
      pythonGenerator.init(workspace);
      const topBlocks = sortedEnabledTopBlocks(workspace);
      if (topBlocks.length !== 1 || !topBlocks[0].outputConnection) throw new Error(`\u8fde\u7ebf\u201c${edge?.name || index + 1}\u201d\u7684\u6761\u4ef6\u5fc5\u987b\u662f\u4e00\u4e2a\u8fd4\u56de\u503c\u79ef\u6728`);
      const expression = normalizeCode(pythonGenerator.blockToCode(topBlocks[0])).trim();
      if (!expression) throw new Error(`\u8fde\u7ebf\u201c${edge?.name || index + 1}\u201d\u6ca1\u6709\u751f\u6210\u6709\u6548\u6761\u4ef6`);
      conditionFunctions.set(index, { functionName: safePythonId(edge?.id || index, '_node_condition'), expression });
    } finally {
      workspace.dispose();
    }
  });

  const preludeGlobal = renderPreludeAt('global');
  const preludeRunPrologue = renderPreludeAt('runPrologue');
  const preludeRunEpilogue = renderPreludeAt('runEpilogue');
  const parts = ['# -*- coding: utf-8 -*-', '# Generated from node graph by CabbageEditor', PYTHON_IMPORTS.ENGINE_IMPORT];
  if (preludeGlobal.trim()) parts.push('', preludeGlobal.trimEnd());
  parts.push('', '_node_graph_state = None');
  if (procedureChunks.length) parts.push('', procedureChunks.join('\n\n'));
  if (runtimeDefinitions.length) parts.push('', runtimeDefinitions.join('\n\n'));
  for (const [, condition] of conditionFunctions) parts.push('', `def ${condition.functionName}():`, `    return bool(${condition.expression})`);
  if (keyboardChunks.length) parts.push('', 'def handle(key, _mods=None):', indentBlock(keyboardChunks.join('\n')) || '    pass');
  if (mouseChunks.length) parts.push('', 'def handle_mouse(_event_type, _button, _x, _y):', indentBlock(mouseChunks.join('\n')) || '    pass');

  parts.push('', 'def run():', '    global _node_graph_state');
  if (runtimeRegistrations.length) parts.push(indentBlock(runtimeRegistrations.join('\n')));
  if (preludeRunPrologue.trim()) parts.push(indentBlock(preludeRunPrologue));
  if (globalCode.trim()) parts.push(indentBlock(globalCode));
  parts.push(`    _node_graph_state = ${pythonString(startNode.id)}`);
  parts.push('    while _node_graph_state is not None:');
  parts.push('        CoronaEngine.check_stop()');

  nodes.forEach((node, nodeIndex) => {
    const nodeId = String(node.id);
    const lifecycle = nodeLifecycle.get(nodeId) || { enter: [], active: [], exit: [] };
    const enterCode = lifecycle.enter.join('');
    const activeCode = lifecycle.active.join('');
    const exitCode = lifecycle.exit.join('');
    const traceName = node?.nodeType === 'custom' ? node?.customName || node?.name || '\u81ea\u5b9a\u4e49\u8282\u70b9' : node?.nodeType === 'start' ? '\u5f00\u59cb\u8282\u70b9' : '\u7ed3\u675f\u8282\u70b9';
    parts.push(`        ${nodeIndex === 0 ? 'if' : 'elif'} _node_graph_state == ${pythonString(nodeId)}:`);
    parts.push(`            CoronaEngine.node_graph_enter(${pythonString(nodeId)}, ${pythonString(traceName)})`);
    if (enterCode.trim()) parts.push(indentBlock(indentBlock(indentBlock(enterCode))));
    if (node.nodeType === 'end') {
      parts.push('            _node_graph_state = None');
      parts.push('            continue');
      return;
    }
    const outgoing = edges.map((edge, index) => ({ edge, index })).filter(({ edge }) => String(edge?.source?.nodeId ?? '') === nodeId);
    parts.push(`            while _node_graph_state == ${pythonString(nodeId)}:`);
    parts.push('                CoronaEngine.check_stop()');
    if (activeCode.trim()) parts.push(indentBlock(indentBlock(indentBlock(indentBlock(activeCode)))));
    if (outgoing.length) {
      outgoing.forEach(({ edge, index }, branchIndex) => {
        const condition = conditionFunctions.get(index);
        parts.push(`                ${branchIndex === 0 ? 'if' : 'elif'} ${condition ? `${condition.functionName}()` : 'True'}:`);
        if (exitCode.trim()) parts.push(indentBlock(indentBlock(indentBlock(indentBlock(indentBlock(exitCode))))));
        parts.push(`                    _node_graph_state = ${pythonString(edge.target.nodeId)}`);
        parts.push('                    break');
      });
      parts.push(`                if _node_graph_state == ${pythonString(nodeId)}:`);
      const waitingEdge = outgoing.find(({ index }) => conditionFunctions.has(index))?.edge;
      parts.push(`                    CoronaEngine.node_graph_waiting(${pythonString(waitingEdge?.id || '')}, ${pythonString(waitingEdge?.name || '\u7b49\u5f85\u8fde\u7ebf\u6761\u4ef6')})`);
    } else {
      parts.push(`                CoronaEngine.node_graph_waiting('', ${pythonString('\u7b49\u5f85\u8282\u70b9\u51fa\u7ebf')})`);
    }
    parts.push('                CoronaEngine.wait(0.05)');
    parts.push('            CoronaEngine.wait(0.01)');
  });
  parts.push('        else:');
  parts.push('            raise RuntimeError("\u8282\u70b9\u56fe\u8fdb\u5165\u4e86\u672a\u77e5\u8282\u70b9: " + str(_node_graph_state))');
  if (preludeRunEpilogue.trim()) parts.push(indentBlock(preludeRunEpilogue));
  return parts.join('\n') + '\n';
}
