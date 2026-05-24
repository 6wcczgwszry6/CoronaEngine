import * as Blockly from 'blockly/core';

export const defineListBlocks = (actorname) => {
  Blockly.Blocks['list_show'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('显示列表')
        .appendField(new Blockly.FieldTextInput(), 'v');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour('#E4080A');
      this.setHelpUrl('');
    },
  };

  Blockly.Blocks['list_hide'] = {
    init: function () {
      this.appendDummyInput()
        .appendField('隐藏列表')
        .appendField(new Blockly.FieldTextInput(), 'v');
      this.setInputsInline(true);
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour('#E4080A');
      this.setHelpUrl('');
    },
  };
};
