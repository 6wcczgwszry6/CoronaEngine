import { pythonGenerator } from 'blockly/python';

const py = (value) => JSON.stringify(String(value ?? ''));
const scope = (block) => py(block.getFieldValue('SCOPE') || 'OBJECT');
const name = (block, field = 'NAME') => py(block.getFieldValue(field) || '');
const value = (block, input = 'VALUE', legacy = 'x', fallback = '0') =>
  pythonGenerator.valueToCode(block, input, pythonGenerator.ORDER_NONE) || block.getFieldValue(legacy) || fallback;

export const defineVariableGenerators = () => {
  pythonGenerator.forBlock.variable_define = (block) => `CoronaEngine.data_define(${scope(block)}, ${name(block)}, ${value(block)})\n`;
  pythonGenerator.forBlock.variable_get = (block) => [`CoronaEngine.data_get(${scope(block)}, ${name(block)})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.variable_exists = (block) => [`CoronaEngine.data_exists(${scope(block)}, ${name(block)})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.variable_add = (block) => `CoronaEngine.data_add(${scope(block)}, ${name(block, 'v')}, ${value(block)})\n`;
  pythonGenerator.forBlock.variable_set = (block) => `CoronaEngine.data_set(${scope(block)}, ${name(block, 'v')}, ${value(block)})\n`;
  pythonGenerator.forBlock.variable_show = (block) => `CoronaEngine.var_show(${name(block, 'v')}, ${scope(block)})\n`;
  pythonGenerator.forBlock.variable_hide = (block) => `CoronaEngine.var_hide(${name(block, 'v')}, ${scope(block)})\n`;
};
