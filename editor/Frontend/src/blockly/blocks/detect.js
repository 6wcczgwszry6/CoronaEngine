import * as Blockly from 'blockly/core';

export const defineDetectBlocks = () => {
  Blockly.Blocks['detect_touch'] = {
    init: function () {
      this.setStyle('detect_blocks');
      this.appendDummyInput()
        .appendField('碰到')
        .appendField(new Blockly.FieldTextInput(''), 'x');
      this.setOutput(true, 'Boolean'); // 设置输出为布尔值
      this.setInputsInline(true);
      this.setHelpUrl('');
      this.setTooltip('检测该按钮是否被按下，返回true或false');
    },
  };

  Blockly.Blocks['detect_distance'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('到')
        .appendField(new Blockly.FieldTextInput(''), 'x')
        .appendField('的距离');
      this.setOutput(true, 'Number');
      this.setStyle('detect_blocks');
    },
  };

  Blockly.Blocks['detect_ask'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('询问')
        .appendField(new Blockly.FieldTextInput(''), 'x')
        .appendField('并等待');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['detect_keyboard1'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('按下')
        .appendField(new Blockly.FieldTextInput(''), 'x')
        .appendField('？');
      this.setOutput(true, 'Boolean'); // 设置输出为布尔值
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
      this.setTooltip('检测该按键是否被按下，返回true或false');
    },
  };

  Blockly.Blocks['detect_keyboard0'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('松开')
        .appendField(new Blockly.FieldTextInput(''), 'x')
        .appendField('？');
      this.setOutput(true, 'Boolean'); // 设置输出为布尔值
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
      this.setTooltip('检测该按键是否被松开，返回true或false');
    },
  };

  Blockly.Blocks['detect_mouse1'] = {
    init: function () {
      this.appendDummyInput().appendField('按下鼠标？');
      this.setOutput(true, 'Boolean'); // 设置输出为布尔值
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
      this.setTooltip('检测鼠标是否被按下，返回true或false');
    },
  };

  Blockly.Blocks['detect_mouse0'] = {
    init: function () {
      this.appendDummyInput().appendField('松开鼠标？');
      this.setOutput(true, 'Boolean'); // 设置输出为布尔值
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
      this.setTooltip('检测鼠标是否被松开，返回true或false');
    },
  };

  const detectAttribute = [
    ['动画名称', 'NAME'],
    ['动画编号', 'ID'],
    ['X坐标', 'X'],
    ['Y坐标', 'Y'],
    ['Z坐标', 'Z'],
    ['方向', 'DIRECTION'],
    ['大小', 'SIZE'],
  ];
  Blockly.Blocks['detect_attribute'] = {
    init: function () {
      this.appendDummyInput().appendField(new Blockly.FieldDropdown(detectAttribute), 'x');
      this.setInputsInline(true);
      this.setOutput(true, 'Number');
      this.setStyle('detect_blocks');
      this.setTooltip('检测指定的属性');
    },
  };

  // ── 射线检测（射击命中判定）──

  Blockly.Blocks['detect_raycast'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('射线命中? 起点X')
        .appendField(new Blockly.FieldNumber(0), 'OX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'OY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(0), 'OZ');
      this.appendDummyInput()
        .appendField('方向X')
        .appendField(new Blockly.FieldNumber(0), 'DX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(0), 'DY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(1), 'DZ');
      this.appendDummyInput()
        .appendField('距离')
        .appendField(new Blockly.FieldNumber(100, 0), 'MAX_DIST');
      this.setOutput(true, 'Boolean');
      this.setStyle('detect_blocks');
      this.setTooltip('从起点沿方向发射射线，检测是否在指定距离内命中物体');
    },
  };

  Blockly.Blocks['detect_raycast_distance'] = {
    init: function () {
      this.appendDummyInput().appendField('射线命中距离');
      this.setOutput(true, 'Number');
      this.setStyle('detect_blocks');
      this.setTooltip('获取最近一次射线检测的命中距离');
    },
  };

  Blockly.Blocks['detect_raycast_object'] = {
    init: function () {
      this.appendDummyInput().appendField('射线命中物体');
      this.setOutput(true, null);  // String 类型
      this.setStyle('detect_blocks');
      this.setTooltip('获取最近一次射线检测命中的物体名称');
    },
  };

  Blockly.Blocks['detect_raycast_point'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('射线命中点')
        .appendField(
          new Blockly.FieldDropdown([['X', 'X'], ['Y', 'Y'], ['Z', 'Z']]),
          'AXIS'
        );
      this.setOutput(true, 'Number');
      this.setStyle('detect_blocks');
      this.setTooltip('获取最近一次射线检测命中点的坐标分量');
    },
  };

  Blockly.Blocks['detect_touch_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('碰到标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG')
        .appendField('？');
      this.setOutput(true, 'Boolean');
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setHelpUrl('');
      this.setTooltip('检测当前对象是否碰到指定标签的对象。');
    },
  };

  Blockly.Blocks['detect_last_touch_object'] = {
    init: function () {
      this.appendDummyInput().appendField('最近碰到的对象');
      this.setOutput(true, null);
      this.setStyle('detect_blocks');
      this.setTooltip('返回最近一次碰撞检测命中的对象名称。');
    },
  };
  Blockly.Blocks['detect_ground_below'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('脚下有地面？距离')
        .appendField(new Blockly.FieldNumber(1, 0), 'DISTANCE');
      this.setOutput(true, 'Boolean');
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setTooltip('检测当前对象下方指定距离内是否有地面；无射线接口时用 Y 坐标降级');
    },
  };
  Blockly.Blocks['detect_raycast_hit_tag'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('射线命中标签')
        .appendField(new Blockly.FieldTextInput('tag'), 'TAG')
        .appendField('？');
      this.setOutput(true, 'Boolean');
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setTooltip('判断最近一次射线命中的对象是否匹配指定标签');
    },
  };
  Blockly.Blocks['detect_passed_x'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('通过 X')
        .appendField(new Blockly.FieldNumber(0), 'X')
        .appendField('？');
      this.setOutput(true, 'Boolean');
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setTooltip('判断对象 X 坐标是否已经达到或超过指定值');
    },
  };
  Blockly.Blocks['detect_passed_z'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('通过 Z')
        .appendField(new Blockly.FieldNumber(0), 'Z')
        .appendField('？');
      this.setOutput(true, 'Boolean');
      this.setInputsInline(true);
      this.setStyle('detect_blocks');
      this.setTooltip('判断对象 Z 坐标是否已经达到或超过指定值');
    },
  };


  Blockly.Blocks.detect_touch_started = {
    init() {
      this.appendValueInput('NAME').setCheck('String').appendField('\u521a\u521a\u78b0\u5230\u5bf9\u8c61');
      this.setOutput(true, 'Boolean');
      this.setStyle('detect_blocks');
      this.setTooltip('\u63a5\u89e6\u4ece\u65e0\u5230\u6709\u65f6\u53ea\u8fd4\u56de\u4e00\u6b21 true');
    },
  };
  Blockly.Blocks.detect_touch_tag_started = {
    init() {
      this.appendValueInput('TAG').setCheck('String').appendField('\u521a\u521a\u78b0\u5230\u6807\u7b7e');
      this.setOutput(true, 'Boolean');
      this.setStyle('detect_blocks');
    },
  };
  const addNumberInput = (block, key, label, defaultValue = 0) =>
    block.appendValueInput(key).setCheck('Number').appendField(label).appendField(new Blockly.FieldNumber(defaultValue), `${key}_NUMBER`);
  const defineCrossedOnce = (type, axis) => {
    Blockly.Blocks[type] = { init() {
      this.appendValueInput('NAME').setCheck('String').appendField('\u5bf9\u8c61');
      this.appendDummyInput().appendField('\u901a\u8fc7 ' + axis).appendField(new Blockly.FieldDropdown([['\u589e\u5927\u65b9\u5411', 'POSITIVE'], ['\u51cf\u5c0f\u65b9\u5411', 'NEGATIVE'], ['\u4efb\u610f\u65b9\u5411', 'ANY']]), 'DIRECTION');
      addNumberInput(this, 'THRESHOLD', '\u5750\u6807');
      this.appendDummyInput().appendField('\u4e00\u6b21\uff1f');
      this.setOutput(true, 'Boolean'); this.setStyle('detect_blocks');
    } };
  };
  defineCrossedOnce('detect_crossed_x_once', 'X');
  defineCrossedOnce('detect_crossed_z_once', 'Z');
  Blockly.Blocks.detect_outside_axis = {
    init() {
      this.appendValueInput('NAME').setCheck('String').appendField('\u5bf9\u8c61');
      this.appendDummyInput().appendField('\u5728').appendField(new Blockly.FieldDropdown([['X','X'],['Y','Y'],['Z','Z']]), 'AXIS').appendField('\u8303\u56f4\u5916');
      addNumberInput(this, 'MIN', '\u6700\u5c0f');
      addNumberInput(this, 'MAX', '\u6700\u5927');
      this.setOutput(true, 'Boolean'); this.setStyle('detect_blocks');
    },
  };
  Blockly.Blocks.detect_inside_box = {
    init() {
      this.appendValueInput('NAME').setCheck('String').appendField('\u5bf9\u8c61\u5728 3D \u533a\u57df\u5185');
      for (const [key, label] of [['CX','\u4e2d\u5fc3X'],['CY','Y'],['CZ','Z'],['SX','\u5c3a\u5bf8X'],['SY','Y'],['SZ','Z']]) addNumberInput(this, key, label);
      this.setOutput(true, 'Boolean'); this.setStyle('detect_blocks');
    },
  };
  Blockly.Blocks.detect_last_collision_axis = { init() { this.appendDummyInput().appendField('\u6700\u8fd1\u78b0\u649e\u8f74'); this.setOutput(true, 'String'); this.setStyle('detect_blocks'); } };
  for (const axis of ['X', 'Y', 'Z']) {
    Blockly.Blocks[`detect_last_collision_normal_${axis.toLowerCase()}`] = { init() { this.appendDummyInput().appendField(`\u6700\u8fd1\u78b0\u649e\u6cd5\u7ebf ${axis}`); this.setOutput(true, 'Number'); this.setStyle('detect_blocks'); } };
  }

};
