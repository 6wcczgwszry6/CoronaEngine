import * as Blockly from 'blockly/core';
import { translateUiText } from '@/i18n/domTranslator.js';

const tr = (text) => translateUiText(text);

// 定义事件相关的积木块，适配 Vue 鼠标键盘事件
export const defineEventBlocks = (broadcastList, createNewBroadcast) => {
  // 中文注释：安全获取广播下拉选项，避免 broadcastList 为 null/undefined 时出错
  const getBroadcastOptions = () => {
    const list = Array.isArray(broadcastList?.value) ? broadcastList.value : [];
    const options = list.length
      ? list.map((item) => [item, item])
      : [[`<${tr('\u65e0\u5e7f\u64ad')}>`, 'NO_BROADCAST']];
    options.push([tr('\u65b0\u5efa\u5e7f\u64ad...'), 'CREATE_NEW']);
    return options;
  };

  Blockly.Blocks['event_gameStart'] = {
    init: function () {
      this.appendDummyInput().appendField(tr('\u5f53\u6e38\u620f\u5f00\u59cb\u65f6'));
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 常用键选项（字母、数字、方向键与若干特殊键）
  const KEY_OPTIONS = (function () {
    const letters = Array.from({ length: 26 }, (v, i) => String.fromCharCode(65 + i));
    const nums = Array.from({ length: 10 }, (v, i) => String(i));
    const keys = [];
    letters.forEach((k) => keys.push([k, `Key${k}`]));
    nums.forEach((n) => keys.push([n, `Digit${n}`]));
    // 方向键与特殊键
    const special = [
      ['ArrowUp', 'ArrowUp'],
      ['ArrowDown', 'ArrowDown'],
      ['ArrowLeft', 'ArrowLeft'],
      ['ArrowRight', 'ArrowRight'],
      ['Space', 'Space'],
      ['Enter', 'Enter'],
      ['Escape', 'Escape'],
      ['Tab', 'Tab'],
      ['Backspace', 'Backspace'],
    ];
    special.forEach((s) => keys.push(s));
    return keys;
  })();

  Blockly.Blocks['event_keyboard'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u5f53\u6309\u4e0b'))
        .appendField(new Blockly.FieldDropdown(KEY_OPTIONS), 'x')
        .appendField(tr('\u65f6'));
      this.appendStatementInput('DO') // 新增：允许后续语句块串联
        .setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['event_RB'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u5f53\u63a5\u6536\u5230\u5e7f\u64ad'))
        .appendField(
          new Blockly.FieldDropdown(
            // 生成菜单
            () => getBroadcastOptions(),
            // 校验器：处理“新建广播...”的特殊选项
            function (value) {
              if (value === 'CREATE_NEW') {
                try {
                  createNewBroadcast && createNewBroadcast();
                } catch (e) {}
                // 返回上一次有效值，阻止将字段设置为 CREATE_NEW
                return this.getValue();
              }
              if (value === 'NO_BROADCAST') {
                // 占位不可选，恢复原值
                return this.getValue();
              }
              return value;
            }
          ),
          'x'
        );
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['event_broadcast'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u53d1\u9001\u5e7f\u64ad'))
        .appendField(
          new Blockly.FieldDropdown(
            () => getBroadcastOptions(),
            function (value) {
              if (value === 'CREATE_NEW') {
                try {
                  createNewBroadcast && createNewBroadcast();
                } catch (e) {}
                return this.getValue();
              }
              if (value === 'NO_BROADCAST') {
                return this.getValue();
              }
              return value;
            }
          ),
          'x'
        );
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['event_broadcastWait'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u53d1\u9001\u5e7f\u64ad'))
        .appendField(
          new Blockly.FieldDropdown(
            () => getBroadcastOptions(),
            function (value) {
              if (value === 'CREATE_NEW') {
                try {
                  createNewBroadcast && createNewBroadcast();
                } catch (e) {}
                return this.getValue();
              }
              if (value === 'NO_BROADCAST') {
                return this.getValue();
              }
              return value;
            }
          ),
          'x'
        )
        .appendField(tr('\u5e76\u7b49\u5f85'));
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 键盘组合键事件积木块
  Blockly.Blocks['event_keyboard_combo'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u5f53\u6309\u4e0b\u7ec4\u5408\u952e'))
        .appendField(new Blockly.FieldTextInput('Ctrl+Alt+K'), 'combo')
        .appendField(tr('\u65f6'));
      this.appendStatementInput('DO').setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 鼠标点击事件积木块
  Blockly.Blocks['event_mouse_click'] = {
    init: function () {
      this.appendDummyInput()
        .appendField(tr('\u5f53\u9f20\u6807\u70b9\u51fb'))
        .appendField(
          new Blockly.FieldDropdown([
            [tr('\u5de6\u952e'), 'left'],
            [tr('\u53f3\u952e'), 'right'],
            [tr('\u4e2d\u952e'), 'middle'],
          ]),
          'button'
        )
        .appendField(tr('\u65f6'));
      this.appendStatementInput('DO').setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 鼠标移动事件积木块
  Blockly.Blocks['event_mouse_move'] = {
    init: function () {
      this.appendDummyInput().appendField(tr('\u5f53\u9f20\u6807\u79fb\u52a8\u65f6'));
      this.appendStatementInput('DO').setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 鼠标滚轮事件积木块
  Blockly.Blocks['event_mouse_wheel'] = {
    init: function () {
      this.appendDummyInput().appendField(tr('\u5f53\u9f20\u6807\u6eda\u8f6e\u6eda\u52a8\u65f6'));
      this.appendStatementInput('DO').setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  // 鼠标右键菜单事件积木块
  Blockly.Blocks['event_mouse_contextmenu'] = {
    init: function () {
      this.appendDummyInput().appendField(tr('\u5f53\u9f20\u6807\u53f3\u952e\u83dc\u5355\u65f6'));
      this.appendStatementInput('DO').setCheck(null);
      this.setInputsInline(true);
      this.setPreviousStatement(false, null);
      this.setNextStatement(true, null);
      this.setStyle('event_blocks');
      this.setHelpUrl('');
    },
  };

  const defineNodeLifecycleHat = (type, label, tooltip) => {
    Blockly.Blocks[type] = {
      init: function () {
        this.appendDummyInput().appendField(tr(label));
        this.appendStatementInput('DO').setCheck(null).appendField(tr('\u6267\u884c'));
        this.setPreviousStatement(false, null);
        this.setNextStatement(false, null);
        this.setStyle('event_blocks');
        this.setTooltip(tr(tooltip));
      },
    };
  };
  defineNodeLifecycleHat(
    'node_when_enter',
    '\u5f53\u8fdb\u5165\u5f53\u524d\u8282\u70b9\u65f6',
    '\u8fdb\u5165\u8282\u70b9\u65f6\u6267\u884c\u4e00\u6b21'
  );
  defineNodeLifecycleHat(
    'node_while_active',
    '\u5f53\u524d\u8282\u70b9\u6301\u7eed\u65f6',
    '\u8282\u70b9\u6fc0\u6d3b\u671f\u95f4\u6bcf 0.05 \u79d2\u6267\u884c\u4e00\u6b21'
  );
  defineNodeLifecycleHat(
    'node_when_exit',
    '\u5f53\u79bb\u5f00\u5f53\u524d\u8282\u70b9\u65f6',
    '\u5207\u6362\u5230\u4e0b\u4e00\u8282\u70b9\u524d\u6267\u884c\u4e00\u6b21'
  );
};
