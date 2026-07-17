import * as Blockly from 'blockly/core';

export const defineEngineBlocks = () => {
  Blockly.Blocks['engine_move'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('移动')
        .appendField(new Blockly.FieldNumber(10, 0), 'STEPS')
        .appendField('步');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('让角色向前移动指定的步数');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_rotateX'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('水平旋转')
        .appendField(new Blockly.FieldNumber(15, -Infinity), 'ANGLE')
        .appendField('度');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('让角色绕 X 轴旋转指定角度');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_rotateY'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('竖直旋转')
        .appendField(new Blockly.FieldNumber(15, -Infinity), 'ANGLE')
        .appendField('度');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('让角色绕 Y 轴旋转指定角度');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_rotateZ'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('旋转')
        .appendField(new Blockly.FieldNumber(15, -Infinity), 'ANGLE')
        .appendField('度');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('让角色绕 Z 轴旋转指定角度（2D平面旋转）');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_face'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('面向')
        .appendField(new Blockly.FieldNumber(0, 0, 360), 'DIRECTION')
        .appendField('度方向');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('让角色面向指定角度（0=右, 90=上, 180=左, 270=下）');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_moveto'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('移动到')
        .appendField(
          new Blockly.FieldDropdown([
            ['随机位置', 'random_position'],
            ['准星位置', 'sight_position'],
          ]),
          'POSITION'
        );
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('将角色移动到预设位置');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_movetoXYZ'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('移到 X:')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField('Y:')
        .appendField(new Blockly.FieldNumber(0), 'Y')
        .appendField('Z:')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('将角色移动到指定的 XYZ 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_movetoXYZtime'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('在')
        .appendField(new Blockly.FieldNumber(1, 0), 'TIME')
        .appendField('秒内移到')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField(new Blockly.FieldNumber(0), 'Y')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('在指定时间内平滑移动到目标 XYZ 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Xset'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 X 坐标设为')
        .appendField(new Blockly.FieldNumber(0), 'X');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('直接设置角色的 X 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Yset'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 Y 坐标设为')
        .appendField(new Blockly.FieldNumber(0), 'Y');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('直接设置角色的 Y 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Zset'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 Z 坐标设为')
        .appendField(new Blockly.FieldNumber(0), 'Z');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('直接设置角色的 Z 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Xadd'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 X 坐标增加')
        .appendField(new Blockly.FieldNumber(10), 'DX');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('在当前位置基础上增加 X 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Yadd'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 Y 坐标增加')
        .appendField(new Blockly.FieldNumber(10), 'DY');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('在当前位置基础上增加 Y 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_Zadd'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('将 Z 坐标增加')
        .appendField(new Blockly.FieldNumber(10), 'DZ');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('在当前位置基础上增加 Z 坐标');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['engine_X'] = {
    init: function () {
      this.appendDummyInput().appendField('X');
      this.setOutput(true, 'Number');
      this.setStyle('engine_blocks');
      this.setTooltip('该角色的 X 坐标');
    },
  };

  Blockly.Blocks['engine_Y'] = {
    init: function () {
      this.appendDummyInput().appendField('Y');
      this.setOutput(true, 'Number');
      this.setStyle('engine_blocks');
      this.setTooltip('该角色的 Y 坐标');
    },
  };

  Blockly.Blocks['engine_Z'] = {
    init: function () {
      this.appendDummyInput().appendField('Z');
      this.setOutput(true, 'Number');
      this.setStyle('engine_blocks');
      this.setTooltip('该角色的 Z 坐标');
    },
  };

  // ── 物理扩展：速度与冲量 ──

  Blockly.Blocks['engine_set_velocity'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置速度 X')
        .appendField(new Blockly.FieldNumber(0), 'VX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'VY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'VZ');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('设置物体当前线速度（单位/秒），用于移动靶运动控制');
    },
  };

  Blockly.Blocks['engine_apply_impulse'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('施加冲量 X')
        .appendField(new Blockly.FieldNumber(0), 'IX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'IY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'IZ');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('施加瞬时冲量（N·s），用于子弹命中反馈/爆炸推开效果');
    },
  };

  Blockly.Blocks['engine_get_velocity'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('当前速度')
        .appendField(
          new Blockly.FieldDropdown([['X', 'X'], ['Y', 'Y'], ['Z', 'Z']]),
          'AXIS'
        );
      this.setOutput(true, 'Number');
      this.setStyle('engine_blocks');
      this.setTooltip('获取物体当前速度分量');
    },
  };
  Blockly.Blocks['engine_set_gravity'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置重力')
        .appendField(new Blockly.FieldDropdown([['启用', 'TRUE'], ['关闭', 'FALSE']]), 'ENABLED')
        .appendField('强度')
        .appendField(new Blockly.FieldNumber(9.8), 'STRENGTH');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('设置当前脚本运行时重力；无原生物理接口时用 Python 速度缓存降级模拟');
    },
  };
  Blockly.Blocks['engine_jump'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('向上跳 力度')
        .appendField(new Blockly.FieldNumber(8), 'POWER');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('给当前对象施加向上的跳跃冲量；无原生接口时更新速度缓存');
    },
  };
  Blockly.Blocks['engine_bounce_axis'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('反弹')
        .appendField(new Blockly.FieldDropdown([['X', 'X'], ['Y', 'Y'], ['Z', 'Z']]), 'AXIS')
        .appendField('方向 系数')
        .appendField(new Blockly.FieldNumber(1), 'FACTOR');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('按指定轴反转当前速度并乘以系数，用于打砖块/弹跳/滚动天空');
    },
  };
  Blockly.Blocks['engine_set_game_speed'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('设置游戏速度')
        .appendField(new Blockly.FieldNumber(1), 'VALUE');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('engine_blocks');
      this.setTooltip('把 demo 逻辑用游戏速度保存到当前运行时变量');
    },
  };
  Blockly.Blocks['engine_get_game_speed'] = {
    init: function () {
      this.appendDummyInput().appendField('游戏速度');
      this.setOutput(true, 'Number');
      this.setStyle('engine_blocks');
      this.setTooltip('读取当前运行时游戏速度，默认 1');
    },
  };


  const numberValueStatement = (type, label, input, legacy, defaultValue = 0) => {
    Blockly.Blocks[type] = { init() {
      this.appendValueInput(input)
        .setCheck('Number')
        .appendField(label)
        .appendField(new Blockly.FieldNumber(defaultValue), legacy)
        .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
      this.setInputsInline(true); this.setPreviousStatement(true); this.setNextStatement(true); this.setStyle('engine_blocks');
    } };
  };
  numberValueStatement('engine_Xset', '\u8bbe\u7f6e X \u4e3a', 'VALUE', 'X');
  numberValueStatement('engine_Yset', '\u8bbe\u7f6e Y \u4e3a', 'VALUE', 'Y');
  numberValueStatement('engine_Zset', '\u8bbe\u7f6e Z \u4e3a', 'VALUE', 'Z');
  numberValueStatement('engine_Xadd', 'X \u589e\u52a0', 'VALUE', 'DX');
  numberValueStatement('engine_Yadd', 'Y \u589e\u52a0', 'VALUE', 'DY');
  numberValueStatement('engine_Zadd', 'Z \u589e\u52a0', 'VALUE', 'DZ');
  numberValueStatement('engine_jump', '\u8df3\u8dc3\u529b\u5ea6', 'VALUE', 'POWER', 8);
  numberValueStatement('engine_set_game_speed', '\u8bbe\u7f6e\u6e38\u620f\u901f\u5ea6', 'VALUE', 'VALUE', 1);

  const vectorStatement = (type, label, names, legacyNames) => {
    Blockly.Blocks[type] = { init() {
      this.appendDummyInput('LABEL').appendField(label);
      names.forEach((name, index) => {
        this.appendValueInput(name)
          .setCheck('Number')
          .appendField(name.replace(/^V|^I/, ''))
          .appendField(new Blockly.FieldNumber(0), legacyNames[index])
          .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
      });
      this.setInputsInline(true); this.setPreviousStatement(true); this.setNextStatement(true); this.setStyle('engine_blocks');
    } };
  };
  vectorStatement('engine_set_velocity', '\u8bbe\u7f6e\u901f\u5ea6', ['VX','VY','VZ'], ['VX','VY','VZ']);
  vectorStatement('engine_apply_impulse', '\u65bd\u52a0\u51b2\u91cf', ['IX','IY','IZ'], ['IX','IY','IZ']);

  Blockly.Blocks.engine_set_velocity_axis = { init() {
    this.appendValueInput('VALUE')
      .setCheck('Number')
      .appendField('\u8bbe\u7f6e')
      .appendField(new Blockly.FieldDropdown([['X','X'],['Y','Y'],['Z','Z']]), 'AXIS')
      .appendField('\u901f\u5ea6\u4e3a')
      .appendField(new Blockly.FieldNumber(0), 'VALUE_DEFAULT')
      .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
    this.setInputsInline(true); this.setPreviousStatement(true); this.setNextStatement(true); this.setStyle('engine_blocks');
  } };
  Blockly.Blocks.engine_bounce_last_collision = { init() {
    this.appendValueInput('FACTOR')
      .setCheck('Number')
      .appendField('\u6839\u636e\u6700\u8fd1\u78b0\u649e\u65b9\u5411\u53cd\u5f39 \u7cfb\u6570')
      .appendField(new Blockly.FieldNumber(1), 'FACTOR_DEFAULT')
      .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
    this.setInputsInline(true); this.setPreviousStatement(true); this.setNextStatement(true); this.setStyle('engine_blocks');
  } };
  Blockly.Blocks.engine_stop_motion = { init() {
    this.appendDummyInput().appendField('\u505c\u6b62\u5f53\u524d\u7269\u4f53\u8fd0\u52a8');
    this.setPreviousStatement(true); this.setNextStatement(true); this.setStyle('engine_blocks');
  } };

};