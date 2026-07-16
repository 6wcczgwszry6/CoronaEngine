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

  Blockly.Blocks.object_tag_numbered_range = { init() {
    this.appendDummyInput()
      .appendField('\u6279\u91cf\u8bbe\u7f6e\u7f16\u53f7\u5bf9\u8c61 \u524d\u7f00').appendField(new Blockly.FieldTextInput('Coin'), 'PREFIX')
      .appendField('\u4ece').appendField(new Blockly.FieldNumber(1, 0, 9999, 1), 'FIRST')
      .appendField('\u5230').appendField(new Blockly.FieldNumber(12, 0, 9999, 1), 'LAST')
      .appendField('\u4f4d\u6570').appendField(new Blockly.FieldNumber(2, 0, 8, 1), 'DIGITS')
      .appendField('\u6807\u7b7e').appendField(new Blockly.FieldTextInput('coin'), 'TAG');
    objectStatement(this, '\u7ed9 Coin01..Coin12 \u7b49\u8fde\u7eed\u7f16\u53f7\u5bf9\u8c61\u8bbe\u7f6e\u7edf\u4e00\u6807\u7b7e\u3002');
  } };

  Blockly.Blocks.object_third_person_move = { init() {
    this.appendDummyInput()
      .appendField('\u8ba9\u5bf9\u8c61').appendField(new Blockly.FieldTextInput('CoinHero'), 'NAME')
      .appendField('\u6309 WASD \u76f8\u5bf9\u6444\u50cf\u673a\u79fb\u52a8 \u901f\u5ea6').appendField(new Blockly.FieldNumber(0.18, 0), 'SPEED');
    this.appendDummyInput()
      .appendField('\u969c\u788d\u6807\u7b7e').appendField(new Blockly.FieldTextInput('obstacle'), 'OBSTACLE_TAG')
      .appendField('\u8303\u56f4 X').appendField(new Blockly.FieldNumber(-12), 'MIN_X').appendField('\u5230').appendField(new Blockly.FieldNumber(12), 'MAX_X')
      .appendField('Z').appendField(new Blockly.FieldNumber(-12), 'MIN_Z').appendField('\u5230').appendField(new Blockly.FieldNumber(12), 'MAX_Z');
    objectStatement(this, 'WASD \u6309\u6444\u50cf\u673a\u65b9\u5411\u79fb\u52a8\uff0c\u8d8a\u754c\u4f1a\u9650\u5236\uff0c\u78b0\u5230\u969c\u788d\u4f1a\u9000\u56de\u3002');
  } };
  Blockly.Blocks.object_arcade_jump = { init() {
    this.appendDummyInput()
      .appendField('\u8ba9\u5bf9\u8c61').appendField(new Blockly.FieldTextInput('CoinHero'), 'NAME')
      .appendField('\u7a7a\u683c\u8df3\u8dc3 \u529b\u5ea6').appendField(new Blockly.FieldNumber(0.28, 0), 'POWER')
      .appendField('\u91cd\u529b').appendField(new Blockly.FieldNumber(0.025, 0), 'GRAVITY')
      .appendField('\u5730\u9762 Y').appendField(new Blockly.FieldNumber(0.8), 'GROUND_Y');
    objectStatement(this, '\u68c0\u6d4b\u7a7a\u683c\u7684\u4e00\u6b21\u6309\u4e0b\uff0c\u5e94\u7528\u4e0a\u5347\u901f\u5ea6\u3001\u91cd\u529b\u548c\u843d\u5730\u3002');
  } };
  Blockly.Blocks.object_collect_touching_tag = { init() {
    this.appendDummyInput()
      .appendField('\u6536\u96c6\u78b0\u5230\u7684\u6807\u7b7e').appendField(new Blockly.FieldTextInput('coin'), 'TAG')
      .appendField('\u6bcf\u4e2a\u52a0\u5206').appendField(new Blockly.FieldNumber(1), 'POINTS');
    objectStatement(this, '\u5220\u9664\u4e0e\u5f53\u524d\u811a\u672c\u89d2\u8272\u91cd\u53e0\u7684\u6307\u5b9a\u6807\u7b7e\u5bf9\u8c61\uff0c\u5e76\u7d2f\u52a0\u5f97\u5206\u3002');
  } };

  Blockly.Blocks.object_breakout_reset_round = { init() {
    this.appendDummyInput()
      .appendField('\u91cd\u7f6e\u6253\u7816\u5757 \u7403').appendField(new Blockly.FieldTextInput('Ball'), 'BALL')
      .appendField('\u6321\u677f').appendField(new Blockly.FieldTextInput('Paddle'), 'PADDLE')
      .appendField('\u7816\u5757\u6807\u7b7e').appendField(new Blockly.FieldTextInput('brick'), 'BRICK_TAG');
    this.appendDummyInput()
      .appendField('\u7403\u4f4d\u7f6e X').appendField(new Blockly.FieldNumber(0), 'BALL_X')
      .appendField('Y').appendField(new Blockly.FieldNumber(-3), 'BALL_Y')
      .appendField('Z').appendField(new Blockly.FieldNumber(2.5), 'BALL_Z');
    this.appendDummyInput()
      .appendField('\u6321\u677f\u4f4d\u7f6e X').appendField(new Blockly.FieldNumber(0), 'PADDLE_X')
      .appendField('Y').appendField(new Blockly.FieldNumber(-4.2), 'PADDLE_Y')
      .appendField('Z').appendField(new Blockly.FieldNumber(2.5), 'PADDLE_Z');
    this.appendDummyInput()
      .appendField('\u521d\u901f\u5ea6 X').appendField(new Blockly.FieldNumber(0.16), 'SPEED_X')
      .appendField('Y').appendField(new Blockly.FieldNumber(0.18), 'SPEED_Y')
      .appendField('\u91cd\u7f6e\u7816\u5757').appendField(new Blockly.FieldCheckbox('FALSE'), 'RESET_BRICKS');
    objectStatement(this, '\u91cd\u7f6e\u7403\u548c\u6321\u677f\u4f4d\u7f6e\uff0c\u53ef\u9009\u6062\u590d\u6240\u6709\u7816\u5757\u3002');
  } };
  Blockly.Blocks.object_breakout_paddle_control = { init() {
    this.appendDummyInput()
      .appendField('\u63a7\u5236\u6321\u677f').appendField(new Blockly.FieldTextInput('Paddle'), 'PADDLE')
      .appendField('A/D \u6216\u65b9\u5411\u952e \u901f\u5ea6').appendField(new Blockly.FieldNumber(0.28, 0), 'SPEED')
      .appendField('X \u8303\u56f4').appendField(new Blockly.FieldNumber(-5.2), 'MIN_X')
      .appendField('\u5230').appendField(new Blockly.FieldNumber(5.2), 'MAX_X');
    objectStatement(this, '\u6309\u952e\u63a7\u5236\u6321\u677f\u5de6\u53f3\u79fb\u52a8\u5e76\u9650\u5236\u8fb9\u754c\u3002');
  } };
  Blockly.Blocks.object_breakout_step = { init() {
    this.appendDummyInput()
      .appendField('\u66f4\u65b0\u6253\u7816\u5757 \u7403').appendField(new Blockly.FieldTextInput('Ball'), 'BALL')
      .appendField('\u6321\u677f').appendField(new Blockly.FieldTextInput('Paddle'), 'PADDLE')
      .appendField('\u7816\u5757\u6807\u7b7e').appendField(new Blockly.FieldTextInput('brick'), 'BRICK_TAG');
    this.appendDummyInput()
      .appendField('\u8fb9\u754c X').appendField(new Blockly.FieldNumber(-5.8), 'MIN_X')
      .appendField('\u5230').appendField(new Blockly.FieldNumber(5.8), 'MAX_X')
      .appendField('\u9876\u90e8 Y').appendField(new Blockly.FieldNumber(5.8), 'MAX_Y');
    objectStatement(this, '\u66f4\u65b0\u7403\u7684\u8fd0\u52a8\uff0c\u5904\u7406\u5899\u3001\u6321\u677f\u548c\u7816\u5757\u78b0\u649e\u3002');
  } };
  Blockly.Blocks.object_first_person_move = { init() {
    this.appendDummyInput()
      .appendField('\u7b2c\u4e00\u4eba\u79f0\u79fb\u52a8').appendField(new Blockly.FieldTextInput('FighterPlayer'), 'NAME')
      .appendField('\u901f\u5ea6').appendField(new Blockly.FieldNumber(0.2, 0), 'SPEED')
      .appendField('\u969c\u788d\u6807\u7b7e').appendField(new Blockly.FieldTextInput('obstacle'), 'OBSTACLE_TAG');
    this.appendDummyInput()
      .appendField('\u8303\u56f4 X').appendField(new Blockly.FieldNumber(-5), 'MIN_X').appendField('\u5230').appendField(new Blockly.FieldNumber(5), 'MAX_X')
      .appendField('Z').appendField(new Blockly.FieldNumber(-1), 'MIN_Z').appendField('\u5230').appendField(new Blockly.FieldNumber(48), 'MAX_Z');
    objectStatement(this, 'WASD \u6309\u5f53\u524d\u89c6\u89d2\u79fb\u52a8\uff0c\u5e76\u5904\u7406\u8fb9\u754c\u548c\u969c\u788d\u3002');
  } };
  Blockly.Blocks.combat_set_tag_health = { init() {
    this.appendDummyInput()
      .appendField('\u8bbe\u7f6e\u6807\u7b7e\u654c\u4eba').appendField(new Blockly.FieldTextInput('room1'), 'TAG')
      .appendField('\u751f\u547d\u503c').appendField(new Blockly.FieldNumber(2, 1), 'HEALTH');
    objectStatement(this, '\u4e3a\u6307\u5b9a\u6807\u7b7e\u7684\u6bcf\u4e2a\u654c\u4eba\u521d\u59cb\u5316\u751f\u547d\u503c\u3002');
  } };
  Blockly.Blocks.combat_melee_attack = { init() {
    this.appendDummyInput()
      .appendField('\u8fd1\u6218\u653b\u51fb \u73a9\u5bb6').appendField(new Blockly.FieldTextInput('FighterPlayer'), 'PLAYER')
      .appendField('\u654c\u4eba\u6807\u7b7e').appendField(new Blockly.FieldTextInput('room1'), 'TAG')
      .appendField('\u8bf7\u6c42\u53d8\u91cf').appendField(new Blockly.FieldTextInput('attack_requested'), 'REQUEST');
    this.appendDummyInput()
      .appendField('\u8303\u56f4').appendField(new Blockly.FieldNumber(2.2, 0), 'RANGE')
      .appendField('\u4f24\u5bb3').appendField(new Blockly.FieldNumber(1, 0), 'DAMAGE')
      .appendField('\u51b7\u5374').appendField(new Blockly.FieldNumber(0.25, 0), 'COOLDOWN');
    objectStatement(this, '\u6d88\u8017\u653b\u51fb\u8bf7\u6c42\uff0c\u4f24\u5bb3\u89c6\u7ebf\u524d\u65b9\u6700\u8fd1\u7684\u654c\u4eba\u3002');
  } };
  Blockly.Blocks.combat_enemy_chase_tag = { init() {
    this.appendDummyInput()
      .appendField('\u6807\u7b7e\u654c\u4eba').appendField(new Blockly.FieldTextInput('room1'), 'TAG')
      .appendField('\u8ffd\u9010\u73a9\u5bb6').appendField(new Blockly.FieldTextInput('FighterPlayer'), 'PLAYER')
      .appendField('\u901f\u5ea6').appendField(new Blockly.FieldNumber(0.06, 0), 'SPEED')
      .appendField('\u505c\u6b62\u8ddd\u79bb').appendField(new Blockly.FieldNumber(1.15, 0), 'STOP_DISTANCE');
    objectStatement(this, '\u8ba9\u5b58\u6d3b\u7684\u6807\u7b7e\u654c\u4eba\u671d\u73a9\u5bb6\u8ffd\u9010\u3002');
  } };
  Blockly.Blocks.combat_enemy_contact_damage = { init() {
    this.appendDummyInput()
      .appendField('\u6807\u7b7e\u654c\u4eba').appendField(new Blockly.FieldTextInput('room1'), 'TAG')
      .appendField('\u78b0\u5230\u73a9\u5bb6').appendField(new Blockly.FieldTextInput('FighterPlayer'), 'PLAYER')
      .appendField('\u4f24\u5bb3').appendField(new Blockly.FieldNumber(1, 0), 'DAMAGE')
      .appendField('\u51b7\u5374').appendField(new Blockly.FieldNumber(0.8, 0), 'COOLDOWN');
    objectStatement(this, '\u654c\u4eba\u8fdb\u5165\u63a5\u89e6\u8ddd\u79bb\u65f6\u6309\u51b7\u5374\u6263\u9664\u751f\u547d\u3002');
  } };
  Blockly.Blocks.combat_alive_count = { init() {
    this.appendDummyInput()
      .appendField('\u6807\u7b7e').appendField(new Blockly.FieldTextInput('room1'), 'TAG')
      .appendField('\u5b58\u6d3b\u6570\u91cf');
    this.setOutput(true, 'Number');
    this.setStyle('object_blocks');
    this.setTooltip('\u8fd4\u56de\u6307\u5b9a\u6807\u7b7e\u4e0b\u5c1a\u672a\u88ab\u51fb\u8d25\u7684\u654c\u4eba\u6570\u91cf\u3002');
  } };

};
