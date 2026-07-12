import * as Blockly from 'blockly/core';

const setStatementBlock = (block, tooltip = '') => {
  block.setInputsInline(true);
  block.setPreviousStatement(true, null);
  block.setNextStatement(true, null);
  block.setStyle('object_blocks');
  block.setTooltip(tooltip);
};

export const defineObjectBlocks = () => {
  Blockly.Blocks['object_hide'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('隐藏对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      setStatementBlock(this, '隐藏指定名称的对象');
    },
  };

  Blockly.Blocks['object_show'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('显示对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      setStatementBlock(this, '显示指定名称的对象');
    },
  };

  Blockly.Blocks['object_delete'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('删除对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      setStatementBlock(this, '隐藏对象并在 Python 运行时标记为已删除');
    },
  };

  Blockly.Blocks['object_delete_last_touched'] = {
    init: function () {
      this.appendDummyInput().appendField('删除最近碰到的对象');
      setStatementBlock(this, '删除最近一次侦测到的碰撞对象');
    },
  };

  Blockly.Blocks['object_set_position'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('位置 X')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'Y')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      setStatementBlock(this, '设置指定对象的世界位置');
    },
  };

  Blockly.Blocks['object_get_x'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('的 X');
      this.setOutput(true, 'Number');
      this.setStyle('object_blocks');
      this.setTooltip('读取指定对象的 X 坐标');
    },
  };

  Blockly.Blocks['object_get_y'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('的 Y');
      this.setOutput(true, 'Number');
      this.setStyle('object_blocks');
      this.setTooltip('读取指定对象的 Y 坐标');
    },
  };

  Blockly.Blocks['object_get_z'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('的 Z');
      this.setOutput(true, 'Number');
      this.setStyle('object_blocks');
      this.setTooltip('读取指定对象的 Z 坐标');
    },
  };

  Blockly.Blocks['object_exists'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('存在？');
      this.setOutput(true, 'Boolean');
      this.setStyle('object_blocks');
      this.setTooltip('检查指定对象是否存在且未被删除');
    },
  };

  Blockly.Blocks['object_set_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG');
      setStatementBlock(this, '在 Python 运行时为对象设置标签');
    },
  };

  Blockly.Blocks['object_count_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG')
        .appendField('的对象数量');
      this.setOutput(true, 'Number');
      this.setStyle('object_blocks');
      this.setTooltip('统计指定标签的未删除对象数量');
    },
  };
  Blockly.Blocks['object_spawn'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('生成对象')
        .appendField(new Blockly.FieldTextInput('template'), 'TEMPLATE')
        .appendField('命名')
        .appendField(new Blockly.FieldTextInput('object_01'), 'NAME')
        .appendField('到 X')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'Y')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      setStatementBlock(this, '从模板生成或克隆一个对象；无原生接口时创建运行时虚拟对象');
    },
  };
  Blockly.Blocks['object_spawn_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('批量生成标签')
        .appendField(new Blockly.FieldTextInput('coin'), 'TAG')
        .appendField('数量')
        .appendField(new Blockly.FieldNumber(5, 0, Infinity, 1), 'COUNT');
      this.appendDummyInput()
        .appendField('模板')
        .appendField(new Blockly.FieldTextInput('template'), 'TEMPLATE')
        .appendField('起点 X')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'Y')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      this.appendDummyInput()
        .appendField('间距 X')
        .appendField(new Blockly.FieldNumber(1), 'DX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'DY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'DZ');
      setStatementBlock(this, '按标签批量生成对象，适合金币、砖块、靶子等重复元素');
    },
  };
  Blockly.Blocks['object_delete_raycast_hit'] = {
    init: function () {
      this.appendDummyInput().appendField('删除射线命中的对象');
      setStatementBlock(this, '删除最近一次射线检测命中的对象');
    },
  };
  Blockly.Blocks['object_move_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('移动标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG')
        .appendField('的对象 偏移 X')
        .appendField(new Blockly.FieldNumber(0), 'DX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'DY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'DZ');
      setStatementBlock(this, '批量移动指定标签的未删除对象');
    },
  };

};
