import { pythonGenerator } from 'blockly/python';
import * as Blockly from 'blockly/core';
import { need } from './prelude';

// 简单缩进工具（仅用于本文件内需要时）
function indent(s) {
  if (!s) return '';
  s = String(s).replace(/^\s*\n+|\n+\s*$/g, '');
  return (
    s
      .split('\n')
      .map((l) => (l ? '  ' + l : ''))
      .join('\n') + (s ? '\n' : '')
  );
}

export const defineEventGenerators = () => {
  pythonGenerator.forBlock['event_gameStart'] = function (block) {
    return `CoronaEngine.gameStart()\n`;
  };

  pythonGenerator.forBlock['event_keyboard'] = function (block) {
    // 当使用键盘事件积木时，需要键盘前置片段
    need('keyboard');
    const key = block.getFieldValue('x') || '';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if key == '${key}':\n` + indent(branch);
  };

  pythonGenerator.forBlock['event_RB'] = function (block) {
    const x = block.getFieldValue('x');
    return `CoronaEngine.RB("${x}")\n`;
  };

  pythonGenerator.forBlock['event_broadcast'] = function (block) {
    const x = block.getFieldValue('x');
    return `CoronaEngine.broadcast("${x}")\n`;
  };

  pythonGenerator.forBlock['event_broadcastWait'] = function (block) {
    const x = block.getFieldValue('x');
    return `CoronaEngine.broadcastWait("${x}")\n`;
  };

  pythonGenerator.forBlock['event_keyboard_combo'] = function (block) {
    // 组合键事件：同样路由到 handler
    need('keyboard');
    var combo = block.getFieldValue('combo') || '';
    return `# 组合键事件: ${combo}\n`;
  };

  // 鼠标点击事件
  pythonGenerator.forBlock['event_mouse_click'] = function (block) {
    const button = block.getFieldValue('button');
    const buttonMap = { left: '左键', right: '右键', middle: '中键' };
    return `# 鼠标${buttonMap[button] || button}点击事件\n`;
  };

  pythonGenerator.forBlock['event_mouse_move'] = function () {
    return '# 鼠标移动事件\n';
  };

  pythonGenerator.forBlock['event_mouse_wheel'] = function () {
    return '# 鼠标滚轮事件\n';
  };

  pythonGenerator.forBlock['event_mouse_contextmenu'] = function () {
    return '# 鼠标右键菜单事件\n';
  };
};
