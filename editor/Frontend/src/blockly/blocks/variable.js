import * as Blockly from 'blockly/core';

const variableNames = new Set(['score', 'lives', 'game_state']);
const listNames = new Set(['items']);

export function registerDataName(kind, name) {
  const value = String(name ?? '').trim();
  if (!value) return value;
  (kind === 'list' ? listNames : variableNames).add(value);
  return value;
}

export function dataNameOptions(kind = 'variable') {
  const values = [...(kind === 'list' ? listNames : variableNames)].sort((a, b) => a.localeCompare(b));
  return values.length ? values.map((name) => [name, name]) : [['\u672a\u5b9a\u4e49', '__undefined__']];
}

export function registerDataNamesFromState(state) {
  const visit = (block) => {
    if (!block || typeof block !== 'object') return;
    const fields = block.fields || {};
    const type = String(block.type || '');
    const kind = type.startsWith('list_') ? 'list' : 'variable';
    const name = fields.NAME ?? fields.v;
    if ((type.startsWith('variable_') || type.startsWith('list_')) && name) registerDataName(kind, name);
    for (const input of Object.values(block.inputs || {})) visit(input?.block || input?.shadow);
    visit(block.next?.block);
  };
  for (const block of state?.blocks?.blocks || []) visit(block);
}

const scopes = [['\u5f53\u524d\u7269\u4f53', 'OBJECT'], ['\u5f53\u524d\u573a\u666f', 'SCENE']];
const scopeField = () => new Blockly.FieldDropdown(scopes);
const nameField = (kind) => new Blockly.FieldDropdown(() => dataNameOptions(kind));
const setStatement = (block) => {
  block.setInputsInline(true);
  block.setPreviousStatement(true, null);
  block.setNextStatement(true, null);
  block.setStyle('variable_blocks');
};

export const defineVariableBlocks = () => {
  Blockly.Blocks.variable_define = { init() {
    this.appendDummyInput().appendField('\u521d\u59cb\u5316').appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf')
      .appendField(new Blockly.FieldTextInput('score', (v) => registerDataName('variable', v)), 'NAME');
    this.appendValueInput('VALUE')
      .setCheck(null)
      .appendField('\u4e3a')
      .appendField(new Blockly.FieldNumber(0), 'x')
      .appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c');
    setStatement(this); this.setTooltip('\u5728\u8282\u70b9\u56fe\u542f\u52a8\u65f6\u521d\u59cb\u5316\u6570\u636e');
  } };
  Blockly.Blocks.variable_get = { init() { this.appendDummyInput().appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf').appendField(nameField('variable'), 'NAME'); this.setOutput(true, null); this.setStyle('variable_blocks'); } };
  Blockly.Blocks.variable_exists = { init() { this.appendDummyInput().appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf').appendField(nameField('variable'), 'NAME').appendField('\u5b58\u5728\uff1f'); this.setOutput(true, 'Boolean'); this.setStyle('variable_blocks'); } };
  Blockly.Blocks.variable_add = { init() {
    this.appendDummyInput().appendField('\u5c06').appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf').appendField(nameField('variable'), 'v');
    this.appendValueInput('VALUE')
      .setCheck('Number')
      .appendField('\u589e\u52a0')
      .appendField(new Blockly.FieldNumber(0), 'x')
      .appendField('\u6216\u63a5\u5165\u53d8\u91cf/\u8fd0\u7b97');
    setStatement(this);
  } };
  Blockly.Blocks.variable_set = { init() {
    this.appendDummyInput().appendField('\u5c06').appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf').appendField(nameField('variable'), 'v');
    this.appendValueInput('VALUE')
      .setCheck(null)
      .appendField('\u8bbe\u4e3a')
      .appendField(new Blockly.FieldNumber(0), 'x')
      .appendField('\u6216\u63a5\u5165\u5176\u4ed6\u503c');
    setStatement(this);
  } };
  for (const [type, label] of [['variable_show', '\u663e\u793a'], ['variable_hide', '\u9690\u85cf']]) Blockly.Blocks[type] = { init() { this.appendDummyInput().appendField(label).appendField(scopeField(), 'SCOPE').appendField('\u53d8\u91cf').appendField(nameField('variable'), 'v'); setStatement(this); } };
};
