import * as Blockly from 'blockly/core';

export const defineCameraBlocks = () => {
  Blockly.Blocks['camera_lock_mouse'] = {
    init: function () {
      this.appendDummyInput().appendField('锁定鼠标');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('锁定鼠标到窗口中心，隐藏光标，启用 FPS 相对模式');
    },
  };

  Blockly.Blocks['camera_unlock_mouse'] = {
    init: function () {
      this.appendDummyInput().appendField('解锁鼠标');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('解锁鼠标，恢复系统光标');
    },
  };

  Blockly.Blocks['camera_mouse_dx'] = {
    init: function () {
      this.appendDummyInput().appendField('鼠标移动 X');
      this.setOutput(true, 'Number');
      this.setStyle('camera_blocks');
      this.setTooltip('本帧鼠标在水平方向的位移量');
    },
  };

  Blockly.Blocks['camera_mouse_dy'] = {
    init: function () {
      this.appendDummyInput().appendField('鼠标移动 Y');
      this.setOutput(true, 'Number');
      this.setStyle('camera_blocks');
      this.setTooltip('本帧鼠标在垂直方向的位移量');
    },
  };

  Blockly.Blocks['camera_set_fov'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('视野设为')
        .appendField(new Blockly.FieldNumber(75, 10, 170), 'FOV')
        .appendField('度');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('设置摄像机视场角（10-170 度），用于瞄准镜缩放效果');
    },
  };

  Blockly.Blocks['camera_follow_object'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('摄像机跟随对象')
        .appendField(new Blockly.FieldTextInput(''), 'NAME')
        .appendField('偏移 X')
        .appendField(new Blockly.FieldNumber(0), 'OX')
        .appendField('Y')
        .appendField(new Blockly.FieldNumber(5), 'OY')
        .appendField('Z')
        .appendField(new Blockly.FieldNumber(-10), 'OZ');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('把摄像机移动到对象位置加偏移；放进循环里可持续跟随。');
    },
  };

  Blockly.Blocks['camera_raycast'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('从摄像机发射射线 距离')
        .appendField(new Blockly.FieldNumber(100, 0), 'MAX_DIST')
        .appendField('命中？');
      this.setOutput(true, 'Boolean');
      this.setStyle('camera_blocks');
      this.setTooltip('从当前摄像机向前发射射线并记录命中结果。');
    },
  };

  Blockly.Blocks['camera_raycast_object'] = {
    init: function () {
      this.appendDummyInput().appendField('摄像机射线命中的对象');
      this.setOutput(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('返回最近一次摄像机射线命中的对象名称。');
    },
  };

  Blockly.Blocks['camera_third_person_orbit'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('\u7b2c\u4e09\u4eba\u79f0\u6444\u50cf\u673a\u8ddf\u968f')
        .appendField(new Blockly.FieldTextInput('CoinHero'), 'NAME')
        .appendField('\u8ddd\u79bb')
        .appendField(new Blockly.FieldNumber(7, 1), 'DISTANCE')
        .appendField('\u9ad8\u5ea6')
        .appendField(new Blockly.FieldNumber(2.4), 'HEIGHT')
        .appendField('\u9f20\u6807\u7075\u654f\u5ea6')
        .appendField(new Blockly.FieldNumber(0.18, 0.01), 'SENSITIVITY');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('\u9501\u5b9a\u9f20\u6807\u540e\uff0c\u56f4\u7ed5\u89d2\u8272\u65cb\u8f6c\u4e3b\u6444\u50cf\u673a\u5e76\u6301\u7eed\u671d\u5411\u89d2\u8272\u3002');
    },
  };

  Blockly.Blocks['camera_first_person_follow'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('\u7b2c\u4e00\u4eba\u79f0\u6444\u50cf\u673a\u8ddf\u968f')
        .appendField(new Blockly.FieldTextInput('FighterPlayer'), 'NAME')
        .appendField('\u9ad8\u5ea6').appendField(new Blockly.FieldNumber(1.55), 'HEIGHT')
        .appendField('\u7075\u654f\u5ea6').appendField(new Blockly.FieldNumber(0.16, 0.01), 'SENSITIVITY')
        .appendField('\u6b66\u5668').appendField(new Blockly.FieldTextInput('Sword'), 'WEAPON');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setStyle('camera_blocks');
      this.setTooltip('\u9501\u5b9a\u9f20\u6807\u540e\uff0c\u6444\u50cf\u673a\u8d34\u8fd1\u89d2\u8272\u89c6\u89d2\uff0c\u9f20\u6807\u63a7\u5236\u671d\u5411\u5e76\u540c\u6b65\u6b66\u5668\u4f4d\u7f6e\u3002');
    },
  };

};
