// 生成器前置代码（Prelude）注册表（支持多插入点）
// 用法：
// - 在某个积木的生成器中：import { need } from './prelude'; need('keyboard')
// - 生成流程中：resetPrelude()；然后在不同位置 renderPreludeAt('global'|'runPrologue'|'runEpilogue')

import { PYTHON_IMPORTS } from './constants';

// 已请求的前置段集合
const _required = new Set();

// 预设的前置片段清单（可按需扩展/修改）
// 每个键支持：
// - 字符串：仅用于 global 位置；
// - 或对象：{ global?: string, runPrologue?: string, runEpilogue?: string }
const PRELUDE_SNIPPETS = {
  // 键盘事件支持：当使用键盘事件积木时加入
  keyboard: {
    global: [
      '# 键盘/事件桥接初始化',
      'import logging as _logging',
      '_kl = _logging.getLogger("BlocklyKeyboard")',
      PYTHON_IMPORTS.PYTHON_SLOT_IMPORT,
      `try:
    ${PYTHON_IMPORTS.MAIN_WINDOW_IMPORT}
except ImportError:
    _kl.warning("get_window 导入失败，键盘事件不可用")
    get_window = None`,
    ].join('\n'),
    runPrologue: [
      'if callable(get_window):',
      '    try:',
      '        wb = get_window()',
      '        bw = wb.browser_widget',
      '        if bw is None:',
      '            _kl.warning("browser_widget 为空，键盘事件不可用")',
      '        else:',
      '            prev = getattr(bw, "_blockly_handle_slot", None)',
      '            if prev is not None:',
      '                try: bw.code_input_changed.disconnect(prev)',
      '                except Exception: pass',
      '            bw.code_input_changed.connect(handle)',
      '            bw._blockly_handle_slot = handle',
      '            _kl.info("键盘事件桥接成功")',
      '    except Exception as _e:',
      '        _kl.warning(f"键盘事件桥接失败: {_e}")',
      'else:',
      '    _kl.warning("get_window 不可调用，键盘事件不可用")',
    ].join('\n'),
    runEpilogue: ['# 键盘事件已就绪'].join('\n'),
  },

  // 鼠标事件支持：当使用鼠标事件积木时加入
  mouse: {
    global: [
      '# 鼠标状态追踪变量',
      PYTHON_IMPORTS.PYTHON_SLOT_IMPORT,
      'from CoronaCore.utils import corona_engine_scratch as _CE',
      'import threading as _threading',
    ].join('\n'),
    runPrologue: [
      '# 鼠标事件桥接',
      '_ce_lock = _threading.Lock()',
      'if callable(get_window):',
      '    try:',
      '        wb = get_window()',
      '        bw = wb.browser_widget',
      '        if bw is None:',
      '            _kl.warning("browser_widget 为空，鼠标事件不可用")',
      '        else:',
      '            prev_mouse = getattr(bw, "_blockly_mouse_slot", None)',
      '            if prev_mouse is not None:',
      '                try: bw.mouse_event_changed.disconnect(prev_mouse)',
      '                except Exception: pass',
      '            bw.mouse_event_changed.connect(handle_mouse)',
      '            bw._blockly_mouse_slot = handle_mouse',
      '            _kl.info("鼠标事件桥接成功")',
      '    except Exception as _e:',
      '        _kl.warning(f"鼠标事件桥接失败: {_e}")',
      'else:',
      '    _kl.warning("get_window 不可调用，鼠标事件不可用")',
    ].join('\n'),
    runEpilogue: '# 鼠标事件收尾',
  },
};

// 标记需要某个前置片段
export function need(name) {
  _required.add(name);
}

// 重置（在一次 workspaceToCode 开始前调用）
export function resetPrelude() {
  _required.clear();
}

// 渲染所有已请求的前置片段（旧接口：仅 global）
export function renderPrelude() {
  return renderPreludeAt('global');
}

// 渲染指定插入点的片段并返回文本（以单个换行结尾，或空串）
export function renderPreludeAt(where /* 'global' | 'runPrologue' | 'runEpilogue' */) {
  const parts = [];
  for (const name of _required) {
    const entry = PRELUDE_SNIPPETS[name];
    if (!entry) continue;
    let text = '';
    if (typeof entry === 'string') {
      if (where === 'global') text = entry;
    } else if (typeof entry === 'object') {
      text = entry[where] || '';
    }
    if (text) parts.push(String(text).replace(/[\r\n]+$/, '')); // 去除尾部多余换行
  }
  if (parts.length === 0) return '';
  return parts.join('\n') + '\n';
}
