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
    need('keyboard');
    const key = block.getFieldValue('x') || '';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if key == '${key}':\n` + indent(branch);
  };

  pythonGenerator.forBlock['event_keyboard_combo'] = function (block) {
    need('keyboard');
    var combo = block.getFieldValue('combo') || 'Ctrl+Alt+K';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    const parts = combo.split('+').map(s => s.trim());
    const checks = parts.map(p => `'${p}' in _mods`).join(' and ');
    return `if key == '${parts[parts.length - 1]}' and ${checks}:\n` + indent(branch);
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

  // ============================================================
  // 鼠标事件生成器（输出到 handle_mouse 函数）
  // ============================================================

  pythonGenerator.forBlock['event_mouse_click'] = function (block) {
    need('mouse');
    const button = block.getFieldValue('button');
    const buttonMap = { left: 'LeftButton', right: 'RightButton', middle: 'MiddleButton' };
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return (
      `if _event_type == 'click' and _button == '${buttonMap[button] || button}':\n` +
      indent(branch)
    );
  };

  pythonGenerator.forBlock['event_mouse_move'] = function (block) {
    need('mouse');
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if _event_type == 'move':\n` + indent(branch);
  };

  pythonGenerator.forBlock['event_mouse_wheel'] = function (block) {
    need('mouse');
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if _event_type == 'wheel':\n` + indent(branch);
  };

  pythonGenerator.forBlock['event_mouse_contextmenu'] = function (block) {
    need('mouse');
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if _event_type == 'contextmenu':\n` + indent(branch);
  };
};