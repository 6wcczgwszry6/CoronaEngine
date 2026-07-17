import * as Blockly from 'blockly/core';

const setStatementBlock = (block, tooltip = '') => {
  block.setInputsInline(true);
  block.setPreviousStatement(true, null);
  block.setNextStatement(true, null);
  block.setStyle('ui_blocks');
  block.setTooltip(tooltip);
};

export const defineUiBlocks = () => {
  Blockly.Blocks['ui_set_score'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置分数为')
        .appendField(new Blockly.FieldNumber(0), 'VALUE');
      setStatementBlock(this, '把当前运行时分数设置为指定数值');
    },
  };

  Blockly.Blocks['ui_add_score'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('分数增加')
        .appendField(new Blockly.FieldNumber(1), 'DELTA');
      setStatementBlock(this, '在当前运行时分数上增加指定数值');
    },
  };

  Blockly.Blocks['ui_game_win'] = {
    init: function () {
      this.appendDummyInput().appendField('游戏胜利');
      setStatementBlock(this, '标记游戏胜利并停止当前脚本');
    },
  };

  Blockly.Blocks['ui_game_over'] = {
    init: function () {
      this.appendDummyInput().appendField('游戏失败');
      setStatementBlock(this, '标记游戏失败并停止当前脚本');
    },
  };
  Blockly.Blocks['ui_set_lives'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置生命为')
        .appendField(new Blockly.FieldNumber(3), 'VALUE');
      setStatementBlock(this, '把当前运行时生命值设置为指定数值');
    },
  };
  Blockly.Blocks['ui_add_lives'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('生命增加')
        .appendField(new Blockly.FieldNumber(1), 'DELTA');
      setStatementBlock(this, '在当前生命值基础上增加或减少');
    },
  };
  Blockly.Blocks['ui_lives'] = {
    init: function () {
      this.appendDummyInput().appendField('生命');
      this.setOutput(true, 'Number');
      this.setStyle('ui_blocks');
      this.setTooltip('读取当前运行时生命值');
    },
  };
  Blockly.Blocks['ui_set_countdown'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置倒计时')
        .appendField(new Blockly.FieldNumber(30, 0), 'SECONDS')
        .appendField('秒');
      setStatementBlock(this, '启动一个基于运行时 monotonic time 的倒计时');
    },
  };
  Blockly.Blocks['ui_countdown_left'] = {
    init: function () {
      this.appendDummyInput().appendField('倒计时剩余');
      this.setOutput(true, 'Number');
      this.setStyle('ui_blocks');
      this.setTooltip('读取倒计时剩余秒数');
    },
  };
  Blockly.Blocks['ui_countdown_finished'] = {
    init: function () {
      this.appendDummyInput().appendField('倒计时结束？');
      this.setOutput(true, 'Boolean');
      this.setStyle('ui_blocks');
      this.setTooltip('倒计时是否已经结束');
    },
  };


  const valueStatement = (type, label, input, legacy, defaultValue) => {
    Blockly.Blocks[type] = { init() {
      this.appendValueInput(input)
        .setCheck('Number')
        .appendField(label)
        .appendField(new Blockly.FieldNumber(defaultValue), legacy)
        .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
      setStatementBlock(this);
    } };
  };
  valueStatement('ui_set_score', '\u8bbe\u7f6e\u5206\u6570\u4e3a', 'VALUE_INPUT', 'VALUE', 0);
  valueStatement('ui_add_score', '\u5206\u6570\u589e\u52a0', 'VALUE_INPUT', 'DELTA', 1);
  valueStatement('ui_set_lives', '\u8bbe\u7f6e\u751f\u547d\u4e3a', 'VALUE_INPUT', 'VALUE', 3);
  valueStatement('ui_add_lives', '\u751f\u547d\u589e\u52a0', 'VALUE_INPUT', 'DELTA', 1);
  valueStatement('ui_set_countdown', '\u8bbe\u7f6e\u5012\u8ba1\u65f6\u79d2\u6570', 'VALUE_INPUT', 'SECONDS', 30);
  Blockly.Blocks.ui_score = { init() { this.appendDummyInput().appendField('\u5f53\u524d\u5206\u6570'); this.setOutput(true, 'Number'); this.setStyle('ui_blocks'); } };
  Blockly.Blocks.ui_game_state = { init() { this.appendDummyInput().appendField('\u5f53\u524d\u6e38\u620f\u72b6\u6001'); this.setOutput(true, 'String'); this.setStyle('ui_blocks'); } };
  Blockly.Blocks.ui_countdown_elapsed = { init() { this.appendDummyInput().appendField('\u5012\u8ba1\u65f6\u5df2\u7ecf\u8fc7\u79d2\u6570'); this.setOutput(true, 'Number'); this.setStyle('ui_blocks'); } };

};
