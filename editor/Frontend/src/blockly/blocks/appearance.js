import * as Blockly from 'blockly/core';

// 辅助函数，用于设置通用属性
const setCommonProperties = (block, colour, tooltip = '') => {
  block.setInputsInline(true);
  block.setPreviousStatement(true, null);
  block.setNextStatement(true, null);
  block.setColour(colour);
  block.setTooltip(tooltip);
};

export const defineAppearanceBlocks = (actorname) => {
  Blockly.Blocks['appearance_cartoonSet'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('换成')
        .appendField(new Blockly.FieldNumber(0, 0), 'INDEX')
        .appendField('动画');
      setCommonProperties(this, '#C501F6', '输入有效的动画序号（整数且大于等于 0）');
    },
  };

  Blockly.Blocks['appearance_nextCartoon'] = {
    init: function () {
      this.appendDummyInput().appendField('下一个动画');
      setCommonProperties(this, '#C501F6', '切换到下一个动画');
    },
  };

  Blockly.Blocks['appearance_playCartoon'] = {
    init: function () {
      this.appendDummyInput().appendField('播放动画');
      setCommonProperties(this, '#C501F6', '播放当前动画');
    },
  };

  Blockly.Blocks['appearance_stopCartoon'] = {
    init: function () {
      this.appendDummyInput().appendField('停止动画');
      setCommonProperties(this, '#C501F6', '停止当前动画');
    },
  };

  Blockly.Blocks['appearance_resetCartoon'] = {
    init: function () {
      this.appendDummyInput().appendField('重置动画');
      setCommonProperties(this, '#C501F6', '将当前动画重置到第一帧');
    },
  };

  Blockly.Blocks['appearance_sizeAdd'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('大小增加')
        .appendField(new Blockly.FieldNumber(10), 'DS');
      setCommonProperties(this, '#C501F6', '增加或减少角色的大小，正数增加，负数减少');
    },
  };

  Blockly.Blocks['appearance_sizeSet'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('大小设为')
        .appendField(new Blockly.FieldNumber(100), 'SIZE');
      setCommonProperties(this, '#C501F6', '设置角色的大小，输入有效的大小数值');
    },
  };

  Blockly.Blocks['appearance_show'] = {
    init: function () {
      this.appendDummyInput().appendField('显示');
      setCommonProperties(this, '#C501F6', '显示角色');
    },
  };

  Blockly.Blocks['appearance_hide'] = {
    init: function () {
      this.appendDummyInput().appendField('隐藏');
      setCommonProperties(this, '#C501F6', '隐藏角色');
    },
  };

  Blockly.Blocks['appearance_cartoon'] = {
    init: function () {
      this.setStyle('math_blocks'); // 使用数学类样式（通常自带圆形）
      this.appendDummyInput().appendField('动画');
      this.setOutput(true, 'Number'); // 关键：输出数值类型
      this.setColour('#C501F6');
      this.setTooltip('该角色的动画序号');
    },
  };

  Blockly.Blocks['appearance_size'] = {
    init: function () {
      this.setStyle('math_blocks'); // 使用数学类样式（通常自带圆形）
      this.appendDummyInput().appendField('大小');
      this.setOutput(true, 'Number'); // 关键：输出数值类型
      this.setColour('#C501F6');
      this.setTooltip('该角色的大小');
    },
  };
};
