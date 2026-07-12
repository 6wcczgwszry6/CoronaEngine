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

};
