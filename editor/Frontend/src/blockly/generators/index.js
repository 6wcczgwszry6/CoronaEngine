// 统一注册各分类的 Python 代码生成器，并自定义 workspaceToCode
import { pythonGenerator } from 'blockly/python';
import { resetPrelude, renderPreludeAt } from './prelude';
import { PYTHON_IMPORTS } from './constants';

import { defineAppearanceGenerators } from './appearance';
import { defineControlGenerators } from './control';
import { defineDetectGenerators } from './detect';
import { defineEngineGenerators } from './engine';
import { defineEventGenerators } from './event';
import { defineListGenerators } from './list';
import { defineMathGenerators } from './math';
import { defineVariableGenerators } from './variable';

// 注册所有分类的生成器（幂等）
try {
  defineAppearanceGenerators?.();
} catch {}
try {
  defineControlGenerators?.();
} catch {}
try {
  defineDetectGenerators?.();
} catch {}
try {
  defineEngineGenerators?.();
} catch {}
try {
  defineEventGenerators?.();
} catch {}
try {
  defineListGenerators?.();
} catch {}
try {
  defineMathGenerators?.();
} catch {}
try {
  defineVariableGenerators?.();
} catch {}

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

// 自定义：将工作区转换为 Python 代码
pythonGenerator.workspaceToCode = function customWorkspaceToCode(workspace) {
  // 在一次生成开始前，重置前置代码请求集合
  resetPrelude();
  // 初始化生成器
  pythonGenerator.init(workspace);

  // 拿到顶层积木并按坐标排序
  const topBlocks = workspace.getTopBlocks(true);
  topBlocks.sort((a, b) => {
    const aXY = a.getRelativeToSurfaceXY();
    const bXY = b.getRelativeToSurfaceXY();
    return aXY.y - bXY.y || aXY.x - bXY.x;
  });

  // 将按键相关的顶层积木输出到 handler，其余输出到 run
  const KEYBOARD_BLOCK_TYPES = new Set(['event_keyboard', 'event_keyboard_combo']);
  let mainCode = '';
  let handlerCode = '';

  for (const block of topBlocks) {
    if (block.disabled) continue;
    let blockCode = pythonGenerator.blockToCode(block);
    let chunk = normalizeCode(blockCode);
    if (chunk && !chunk.endsWith('\n')) chunk += '\n';
    if (KEYBOARD_BLOCK_TYPES.has(block.type)) {
      handlerCode += chunk;
    } else {
      mainCode += chunk;
    }
  }

  // 结束生成
  mainCode = pythonGenerator.finish(mainCode);
  if (mainCode && !mainCode.endsWith('\n')) mainCode += '\n';
  // handlerCode 不需要再次 finish，保持原样

  // 头注释（规范结尾仅 1 个换行）
  const timestamp = new Date().toISOString();
  const header = [
    '# -*- coding: utf-8 -*-',
    `# Generated from Blockly by CabbageEditor @ ${timestamp}`,
    PYTHON_IMPORTS.ENGINE_IMPORT,
  ].join('\n');

  // 各位置前置片段（已去除尾部多余换行；此处不再额外添加空行）
  const preludeGlobal = renderPreludeAt('global'); // 顶部（def run 之前）
  const preludeRunPrologue = renderPreludeAt('runPrologue'); // def run(): 后，函数体开头
  const preludeRunEpilogue = renderPreludeAt('runEpilogue'); // 函数体末尾

  // 组装输出（严格控制空行）
  const parts = [];
  parts.push(header);
  if (preludeGlobal) parts.push(preludeGlobal.trimEnd());

  // 如果有 handler 代码，则输出 def handle
  if (handlerCode.trim()) {
    parts.push(''); // 空行分隔
    parts.push('@Slot(str)\n' + 'def handle(key):' + '\n    print("key:", key)');
    const indentedHandlers = indentBlock(handlerCode);
    if (indentedHandlers) parts.push(indentedHandlers);
  }

  // 输出 def run
  parts.push('');
  parts.push('def run():');
  const runBody = [];
  const indentedPrologue = indentBlock(preludeRunPrologue);
  if (indentedPrologue) runBody.push(indentedPrologue);
  const indentedMain = indentBlock(mainCode);
  if (indentedMain) runBody.push(indentedMain);
  const indentedEpilogue = indentBlock(preludeRunEpilogue);
  if (indentedEpilogue) runBody.push(indentedEpilogue);
  if (runBody.length) {
    parts.push(runBody.join('\n'));
  } else {
    // 避免空函数导致语法错误
    parts.push('    pass');
  }

  // 末尾统一加一个换行
  return parts.join('\n') + '\n';
};

export { pythonGenerator };
