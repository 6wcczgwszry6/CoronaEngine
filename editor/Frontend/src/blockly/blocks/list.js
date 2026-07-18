import * as Blockly from 'blockly/core';
import { dataNameOptions, registerDataName } from './variable.js';

const scopes = [['\u5f53\u524d\u7269\u4f53', 'OBJECT'], ['\u5f53\u524d\u573a\u666f', 'SCENE']];
const scopeField = () => new Blockly.FieldDropdown(scopes);
const listField = () => new Blockly.FieldDropdown(() => dataNameOptions('list'));
const setStatement = (block) => { block.setInputsInline(true); block.setPreviousStatement(true, null); block.setNextStatement(true, null); block.setStyle('list_blocks'); };
const namedHeader = (block, text) => block.appendDummyInput().appendField(text).appendField(scopeField(), 'SCOPE').appendField('\u5217\u8868').appendField(listField(), 'NAME');

export const defineListBlocks = () => {
  Blockly.Blocks.list_define = { init() {
    this.appendDummyInput().appendField('\u521d\u59cb\u5316').appendField(scopeField(), 'SCOPE').appendField('\u5217\u8868')
      .appendField(new Blockly.FieldTextInput('items', (v) => registerDataName('list', v)), 'NAME').appendField(new Blockly.FieldTextInput(''), 'v');
    this.getField('v')?.setVisible(false); this.appendValueInput('VALUE').setCheck('Array').appendField('\u4e3a'); setStatement(this);
  } };
  for (const [type, label] of [['list_show', '\u663e\u793a'], ['list_hide', '\u9690\u85cf']]) Blockly.Blocks[type] = { init() { namedHeader(this, label); this.appendDummyInput('LEGACY').appendField(new Blockly.FieldTextInput(''), 'v'); this.getInput('LEGACY')?.setVisible(false); setStatement(this); } };
  Blockly.Blocks.list_add_named = { init() { namedHeader(this, '\u5411'); this.appendValueInput('VALUE').setCheck(null).appendField('\u52a0\u5165').appendField(new Blockly.FieldNumber(0), 'VALUE_NUMBER').appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c'); setStatement(this); } };
  Blockly.Blocks.list_insert_named = { init() { namedHeader(this, '\u5411'); this.appendValueInput('INDEX').setCheck('Number').appendField('\u7b2c').appendField(new Blockly.FieldNumber(1, 1), 'INDEX_NUMBER'); this.appendValueInput('VALUE').setCheck(null).appendField('\u9879\u63d2\u5165').appendField(new Blockly.FieldNumber(0), 'VALUE_NUMBER').appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c'); setStatement(this); } };
  Blockly.Blocks.list_remove_index_named = { init() { namedHeader(this, '\u5220\u9664'); this.appendValueInput('INDEX').setCheck('Number').appendField('\u7b2c').appendField(new Blockly.FieldNumber(1, 1), 'INDEX_NUMBER'); this.appendDummyInput().appendField('\u9879'); setStatement(this); } };
  Blockly.Blocks.list_remove_value_named = { init() { namedHeader(this, '\u4ece'); this.appendValueInput('VALUE').setCheck(null).appendField('\u5220\u9664\u5185\u5bb9').appendField(new Blockly.FieldNumber(0), 'VALUE_NUMBER').appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c'); setStatement(this); } };
  Blockly.Blocks.list_clear_named = { init() { namedHeader(this, '\u6e05\u7a7a'); setStatement(this); } };
  Blockly.Blocks.list_item_named = { init() { namedHeader(this, '\u8bfb\u53d6'); this.appendValueInput('INDEX').setCheck('Number').appendField('\u7b2c').appendField(new Blockly.FieldNumber(1, 1), 'INDEX_NUMBER'); this.appendDummyInput().appendField('\u9879'); this.setOutput(true, null); this.setStyle('list_blocks'); } };
  Blockly.Blocks.list_length_named = { init() { namedHeader(this, '\u8bfb\u53d6'); this.appendDummyInput().appendField('\u957f\u5ea6'); this.setOutput(true, 'Number'); this.setStyle('list_blocks'); } };
  Blockly.Blocks.list_contains_named = { init() { namedHeader(this, '\u5224\u65ad'); this.appendValueInput('VALUE').setCheck(null).appendField('\u5305\u542b').appendField(new Blockly.FieldNumber(0), 'VALUE_NUMBER').appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c'); this.appendDummyInput().appendField('\uff1f'); this.setOutput(true, 'Boolean'); this.setStyle('list_blocks'); } };
};
