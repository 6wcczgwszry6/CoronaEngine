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
      this.appendValueInput('NAME')
        .setCheck('String')
        .appendField('隐藏对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      setStatementBlock(this, '隐藏指定名称的对象');
    },
  };

  Blockly.Blocks['object_show'] = {
    init: function () {
      this.appendValueInput('NAME')
        .setCheck('String')
        .appendField('显示对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      setStatementBlock(this, '显示指定名称的对象');
    },
  };

  Blockly.Blocks['object_delete'] = {
    init: function () {
      this.appendValueInput('NAME')
        .setCheck('String')
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
      this.appendValueInput('NAME')
        .setCheck('String')
        .appendField('设置对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      this.appendValueInput('X')
        .setCheck('Number')
        .appendField('位置 X')
        .appendField(new Blockly.FieldNumber(0), 'X');
      this.appendValueInput('Y')
        .setCheck('Number')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'Y');
      this.appendValueInput('Z')
        .setCheck('Number')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      setStatementBlock(this, '设置指定对象的世界位置');
    },
  };

  Blockly.Blocks['object_get_x'] = {
    init: function () {
      this.appendValueInput('NAME')
        .setCheck('String')
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
      this.appendValueInput('NAME')
        .setCheck('String')
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
      this.appendValueInput('NAME')
        .setCheck('String')
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
      this.appendValueInput('NAME')
        .setCheck('String')
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
      this.appendValueInput('NAME')
        .setCheck('String')
        .appendField('设置对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME');
      this.appendValueInput('TAG')
        .setCheck('String')
        .appendField('标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG');
      setStatementBlock(this, '在 Python 运行时为对象设置标签');
    },
  };

  Blockly.Blocks['object_count_tag'] = {
    init: function () {
      this.appendValueInput('TAG')
        .setCheck('String')
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
      this.appendValueInput('TEMPLATE')
        .setCheck('String')
        .appendField('生成对象 模板')
        .appendField(new Blockly.FieldTextInput('template'), 'TEMPLATE');
      this.appendValueInput('NAME')
        .setCheck('String')
        .appendField('命名')
        .appendField(new Blockly.FieldTextInput('object_01'), 'NAME');
      for (const [key, label] of [['X', '到 X'], ['Y', 'Y'], ['Z', 'Z']]) {
        this.appendValueInput(key)
          .setCheck('Number')
          .appendField(label)
          .appendField(new Blockly.FieldNumber(0), key);
      }
      setStatementBlock(this, '从模板生成或克隆一个对象；无原生接口时创建运行时虚拟对象');
    },
  };
  Blockly.Blocks['object_spawn_tag'] = {
    init: function () {
      this.appendValueInput('TAG')
        .setCheck('String')
        .appendField('批量生成标签')
        .appendField(new Blockly.FieldTextInput('coin'), 'TAG');
      this.appendValueInput('COUNT')
        .setCheck('Number')
        .appendField('数量')
        .appendField(new Blockly.FieldNumber(5, 0, Infinity, 1), 'COUNT');
      this.appendValueInput('TEMPLATE')
        .setCheck('String')
        .appendField('模板')
        .appendField(new Blockly.FieldTextInput('template'), 'TEMPLATE');
      for (const [key, label, defaultValue] of [
        ['X', '起点 X', 0], ['Y', 'Y', 0], ['Z', 'Z', 0],
        ['DX', '间距 X', 1], ['DY', 'Y', 0], ['DZ', 'Z', 0],
      ]) {
        this.appendValueInput(key)
          .setCheck('Number')
          .appendField(label)
          .appendField(new Blockly.FieldNumber(defaultValue), key);
      }
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
      this.appendValueInput('TAG')
        .setCheck('String')
        .appendField('移动标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG_TEXT')
        .appendField('对象');
      this.appendValueInput('DX')
        .setCheck('Number')
        .appendField('偏移 X')
        .appendField(new Blockly.FieldNumber(0), 'DX_NUMBER');
      this.appendValueInput('DY')
        .setCheck('Number')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'DY_NUMBER');
      this.appendValueInput('DZ')
        .setCheck('Number')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'DZ_NUMBER');
      setStatementBlock(this, '将指定标签的全部对象按相同 XYZ 偏移量移动');
    },
  };


  const objectStatement = (block, tooltip = '') => { setStatementBlock(block, tooltip); };
  const addNumber = (block, key, label, defaultValue = 0) => block.appendValueInput(key).setCheck('Number').appendField(label).appendField(new Blockly.FieldNumber(defaultValue), `${key}_NUMBER`);
  const addText = (block, key, label, defaultValue = '') => block.appendValueInput(key).setCheck('String').appendField(label).appendField(new Blockly.FieldTextInput(defaultValue), `${key}_TEXT`);

  Blockly.Blocks.object_clamp_axis = { init() {
    addText(this, 'NAME', '\u9650\u5236\u5bf9\u8c61');
    this.appendDummyInput().appendField('\u8f74').appendField(new Blockly.FieldDropdown([['X','X'],['Y','Y'],['Z','Z']]), 'AXIS');
    addNumber(this, 'MIN', '\u6700\u5c0f'); addNumber(this, 'MAX', '\u6700\u5927'); objectStatement(this);
  } };
  Blockly.Blocks.object_save_checkpoint = { init() {
    addText(this, 'NAME', '\u4fdd\u5b58\u5bf9\u8c61'); addText(this, 'CHECKPOINT', '\u68c0\u67e5\u70b9');
    this.appendDummyInput().appendField('\u4fdd\u5b58\u901f\u5ea6').appendField(new Blockly.FieldCheckbox('TRUE'), 'SAVE_VELOCITY'); objectStatement(this);
  } };
  Blockly.Blocks.object_restore_checkpoint = { init() {
    addText(this, 'NAME', '\u6062\u590d\u5bf9\u8c61'); addText(this, 'CHECKPOINT', '\u68c0\u67e5\u70b9');
    this.appendDummyInput().appendField('\u6e05\u9664\u901f\u5ea6').appendField(new Blockly.FieldCheckbox('TRUE'), 'CLEAR_VELOCITY'); objectStatement(this);
  } };
  Blockly.Blocks.object_move_to_lane = { init() {
    addText(this, 'NAME', '\u5bf9\u8c61');
    this.appendDummyInput().appendField('\u79fb\u52a8\u5230').appendField(new Blockly.FieldDropdown([['X','X'],['Z','Z']]), 'AXIS').appendField('\u8dd1\u9053');
    addNumber(this, 'LANE', '\u7f16\u53f7'); addNumber(this, 'ORIGIN', '\u8d77\u70b9'); addNumber(this, 'SPACING', '\u95f4\u8ddd'); objectStatement(this);
  } };
  Blockly.Blocks.object_lane_index = { init() {
    addText(this, 'NAME', '\u5bf9\u8c61'); this.appendDummyInput().appendField('\u5f53\u524d').appendField(new Blockly.FieldDropdown([['X','X'],['Z','Z']]), 'AXIS').appendField('\u8dd1\u9053');
    addNumber(this, 'ORIGIN', '\u8d77\u70b9'); addNumber(this, 'SPACING', '\u95f4\u8ddd'); this.setOutput(true, 'Number'); this.setStyle('object_blocks');
  } };
  Blockly.Blocks.object_set_random_position = { init() {
    addText(this, 'NAME', '\u968f\u673a\u653e\u7f6e\u5bf9\u8c61');
    for (const [key,label] of [['CX','\u4e2d\u5fc3X'],['CY','Y'],['CZ','Z'],['SX','\u5c3a\u5bf8X'],['SY','Y'],['SZ','Z']]) addNumber(this,key,label);
    objectStatement(this);
  } };
  Blockly.Blocks.object_spawn_random_box = { init() {
    addText(this, 'TEMPLATE', '\u5728 3D \u533a\u57df\u968f\u673a\u751f\u6210\u6a21\u677f'); addText(this, 'TAG', '\u6807\u7b7e'); addNumber(this, 'COUNT', '\u6570\u91cf');
    for (const [key,label] of [['CX','\u4e2d\u5fc3X'],['CY','Y'],['CZ','Z'],['SX','\u5c3a\u5bf8X'],['SY','Y'],['SZ','Z']]) addNumber(this,key,label);
    objectStatement(this);
  } };
  Blockly.Blocks.object_scatter_tag = { init() {
    addText(this, 'TAG', '\u968f\u673a\u6563\u5e03\u6807\u7b7e');
    for (const [key,label] of [['CX','\u4e2d\u5fc3X'],['CY','Y'],['CZ','Z'],['SX','\u5c3a\u5bf8X'],['SY','Y'],['SZ','Z']]) addNumber(this,key,label);
    objectStatement(this);
  } };
  Blockly.Blocks.object_recycle_tag_axis = { init() {
    addText(this, 'TAG', '\u56de\u6536\u6807\u7b7e');
    this.appendDummyInput().appendField('\u524d\u8fdb\u8f74').appendField(new Blockly.FieldDropdown([['X','X'],['Y','Y'],['Z','Z']]), 'AXIS')
      .appendField('\u65b9\u5411').appendField(new Blockly.FieldDropdown([['\u5c0f\u4e8e','LESS'],['\u5927\u4e8e','GREATER']]), 'DIRECTION');
    addNumber(this, 'BOUNDARY', '\u8fb9\u754c'); addNumber(this, 'RESET', '\u91cd\u7f6e\u5750\u6807');
    this.appendDummyInput().appendField('\u968f\u673a\u8f74').appendField(new Blockly.FieldDropdown([['\u4e0d\u968f\u673a',''],['X','X'],['Y','Y'],['Z','Z']]), 'RANDOM_AXIS');
    addNumber(this, 'RANDOM_MIN', '\u968f\u673a\u6700\u5c0f'); addNumber(this, 'RANDOM_MAX', '\u968f\u673a\u6700\u5927'); objectStatement(this);
  } };
  Blockly.Blocks.object_reset_tag = { init() { addText(this, 'TAG', '\u6062\u590d\u6807\u7b7e\u5bf9\u8c61'); objectStatement(this); } };
  Blockly.Blocks.object_count_active_tag = { init() { addText(this, 'TAG', '\u6807\u7b7e'); this.appendDummyInput().appendField('\u5f53\u524d\u6709\u6548\u6570\u91cf'); this.setOutput(true, 'Number'); this.setStyle('object_blocks'); } };


  const actorDropdownOptions = () => {
    const raw = typeof window !== 'undefined' && Array.isArray(window.__coronaBlocklyActorOptions)
      ? window.__coronaBlocklyActorOptions : [];
    const options = raw.map((item) => Array.isArray(item) ? item : [String(item), String(item)]).filter((item) => item[1]);
    return [...options, ['手动输入', '__manual__']].length > 1 ? [...options, ['手动输入', '__manual__']] : [['当前物体', ''], ['手动输入', '__manual__']];
  };

  Blockly.Blocks.object_reference = { init() {
    this.appendDummyInput()
      .appendField('场景对象')
      .appendField(new Blockly.FieldDropdown(actorDropdownOptions), 'OBJECT')
      .appendField('或输入')
      .appendField(new Blockly.FieldTextInput(''), 'MANUAL');
    this.setOutput(true, 'String');
    this.setStyle('object_blocks');
    this.setTooltip('从当前场景选择对象；选择手动输入后可填写运行时生成对象名称');
  } };

  Blockly.Blocks.object_set_logical_collision = { init() {
    addText(this, 'NAME', '对象', '');
    this.appendDummyInput().appendField('的逻辑碰撞').appendField(new Blockly.FieldDropdown([['开启','TRUE'],['关闭','FALSE']]), 'ENABLED');
    objectStatement(this, '只控制 Scratch AABB 侦测，不会开启原生刚体');
  } };
  Blockly.Blocks.object_logical_collision_enabled = { init() {
    addText(this, 'NAME', '对象', '');
    this.appendDummyInput().appendField('的逻辑碰撞已开启？');
    this.setOutput(true, 'Boolean'); this.setStyle('object_blocks');
  } };
  Blockly.Blocks.object_set_native_physics = { init() {
    addText(this, 'NAME', '对象', '');
    this.appendDummyInput().appendField('的原生物理').appendField(new Blockly.FieldDropdown([['开启','TRUE'],['关闭','FALSE']]), 'ENABLED');
    objectStatement(this, '控制原生刚体；脚本速度模拟时通常应关闭');
  } };
  Blockly.Blocks.object_move_to_lane_smooth = { init() {
    addText(this, 'NAME', '对象', '');
    this.appendDummyInput().appendField('平滑移动到').appendField(new Blockly.FieldDropdown([['X','X'],['Z','Z']]), 'AXIS').appendField('轴跑道');
    addNumber(this, 'LANE', '编号'); addNumber(this, 'ORIGIN', '起点'); addNumber(this, 'SPACING', '间距', 2); addNumber(this, 'SPEED', '速度', 8);
    objectStatement(this);
  } };
  Blockly.Blocks.object_set_tag_velocity_axis = { init() {
    addText(this, 'TAG', '设置标签', 'tag');
    this.appendDummyInput().appendField('对象的').appendField(new Blockly.FieldDropdown([['X','X'],['Y','Y'],['Z','Z']]), 'AXIS').appendField('速度');
    addNumber(this, 'VALUE', '为', 0); objectStatement(this);
  } };
  Blockly.Blocks.object_randomize_mouse_pick = { init() {
    this.appendDummyInput().appendField('将最近鼠标命中的对象随机放到 3D 区域');
    for (const [key,label,def] of [['CX','中心X',0],['CY','Y',0],['CZ','Z',0],['SX','尺寸X',10],['SY','Y',10],['SZ','Z',10]]) addNumber(this,key,label,def);
    objectStatement(this);
  } };
  Blockly.Blocks.object_delete_mouse_pick = { init() { this.appendDummyInput().appendField('删除最近鼠标命中的对象'); objectStatement(this); } };
  Blockly.Blocks.object_reset_crossed_once = { init() {
    addText(this, 'NAME', '重置对象', ''); addText(this, 'TRIGGER', '通过一次标识 留空为全部', ''); objectStatement(this);
  } };

};
