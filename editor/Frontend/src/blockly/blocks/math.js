import * as Blockly from 'blockly/core';

export const defineMathBlocks = () => {
  // Keep legacy math_change compatible but display it with operator colours.
  if (Blockly.Blocks.math_change && !Blockly.Blocks.math_change.__coronaMathStylePatched) {
    const originalInit = Blockly.Blocks.math_change.init;
    Blockly.Blocks.math_change.init = function () {
      originalInit.call(this);
      this.setStyle('math_blocks');
    };
    Blockly.Blocks.math_change.__coronaMathStylePatched = true;
  }

  Blockly.Blocks.math_AND = {
    init() {
      this.setStyle('condition_blocks');
      this.appendValueInput('A').setCheck('Boolean').appendField('');
      this.appendValueInput('B').setCheck('Boolean').appendField('\u4e0e');
      this.setInputsInline(true);
      this.setOutput(true, 'Boolean');
      this.setTooltip('\u903b\u8f91\u4e0e\u8fd0\u7b97\uff0c\u4e24\u4e2a\u6761\u4ef6\u90fd\u6ee1\u8db3\u65f6\u8fd4\u56de true\uff0c\u5426\u5219\u8fd4\u56de false');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks.math_OR = {
    init() {
      this.setStyle('condition_blocks');
      this.appendValueInput('A').setCheck('Boolean').appendField('');
      this.appendValueInput('B').setCheck('Boolean').appendField('\u6216');
      this.setInputsInline(true);
      this.setOutput(true, 'Boolean');
      this.setTooltip('\u903b\u8f91\u6216\u8fd0\u7b97\uff0c\u4e24\u4e2a\u6761\u4ef6\u4e2d\u81f3\u5c11\u4e00\u4e2a\u6ee1\u8db3\u65f6\u8fd4\u56de true\uff0c\u5426\u5219\u8fd4\u56de false');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks.math_NOT = {
    init() {
      this.setStyle('condition_blocks');
      this.appendValueInput('A').setCheck('Boolean').appendField('\u975e');
      this.setInputsInline(true);
      this.setOutput(true, 'Boolean');
      this.setTooltip('\u903b\u8f91\u975e\u8fd0\u7b97\uff0c\u6761\u4ef6\u4e0d\u6ee1\u8db3\u65f6\u8fd4\u56de true\uff0c\u6ee1\u8db3\u65f6\u8fd4\u56de false');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks.math_connect = {
    init() {
      this.setStyle('text_blocks');
      this.appendValueInput('LEFT').appendField('\u8fde\u63a5');
      this.appendValueInput('RIGHT').appendField('\u548c');
      this.setInputsInline(true);
      this.setOutput(true, 'String');
      this.setTooltip('\u5c06\u5de6\u53f3\u4e24\u8fb9\u7684\u5185\u5bb9\u8fde\u63a5\u6210\u4e00\u4e2a\u5b57\u7b26\u4e32');
      this.setHelpUrl('');
    },
  };

  // Keep old custom operator block types for workspace compatibility, but hide them from toolbox.
  const binaryValueBlock = (type, label, output = 'Number') => {
    Blockly.Blocks[type] = {
      init() {
        this.appendValueInput('A')
          .setCheck(null)
          .appendField(new Blockly.FieldNumber(0), 'x1');
        this.appendValueInput('B')
          .setCheck(null)
          .appendField(label)
          .appendField(new Blockly.FieldNumber(0), 'x2');
        this.setInputsInline(true);
        this.setOutput(true, output);
        this.setStyle(output === 'Boolean' ? 'condition_blocks' : 'math_blocks');
      },
    };
  };

  binaryValueBlock('math_add', '+');
  binaryValueBlock('math_sub', '-');
  binaryValueBlock('math_mul', '\u00d7');
  binaryValueBlock('math_div', '\u00f7');
  binaryValueBlock('math_G', '>', 'Boolean');
  binaryValueBlock('math_L', '<', 'Boolean');
  binaryValueBlock('math_E', '=', 'Boolean');

  Blockly.Blocks.math_random = {
    init() {
      this.appendValueInput('A')
        .setCheck('Number')
        .appendField('\u968f\u673a\u6570\u4ece')
        .appendField(new Blockly.FieldNumber(0), 'x1');
      this.appendValueInput('B')
        .setCheck('Number')
        .appendField('\u5230')
        .appendField(new Blockly.FieldNumber(10), 'x2');
      this.setInputsInline(true);
      this.setOutput(true, 'Number');
      this.setStyle('math_blocks');
    },
  };
};
