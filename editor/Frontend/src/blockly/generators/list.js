import { pythonGenerator } from 'blockly/python';

const py = (value) => JSON.stringify(String(value ?? ''));
const scope = (block) => py(block.getFieldValue('SCOPE') || 'OBJECT');
const name = (block) => py(block.getFieldValue('NAME') || block.getFieldValue('v') || '');
const code = (block, input, fallback = 'None') => pythonGenerator.valueToCode(block, input, pythonGenerator.ORDER_NONE) || block.getFieldValue(`${input}_NUMBER`) || fallback;

export const defineListGenerators = () => {
  pythonGenerator.forBlock.list_define = (block) => `CoronaEngine.data_list_define(${scope(block)}, ${name(block)}, ${code(block, 'VALUE', '[]')})\n`;
  pythonGenerator.forBlock.list_show = (block) => `CoronaEngine.list_show(${name(block)}, None, ${scope(block)})\n`;
  pythonGenerator.forBlock.list_hide = (block) => `CoronaEngine.list_hide(${name(block)}, ${scope(block)})\n`;
  pythonGenerator.forBlock.list_add_named = (block) => `CoronaEngine.data_list_add(${scope(block)}, ${name(block)}, ${code(block, 'VALUE')})\n`;
  pythonGenerator.forBlock.list_insert_named = (block) => `CoronaEngine.data_list_insert(${scope(block)}, ${name(block)}, ${code(block, 'INDEX', '1')}, ${code(block, 'VALUE')})\n`;
  pythonGenerator.forBlock.list_remove_index_named = (block) => `CoronaEngine.data_list_remove_index(${scope(block)}, ${name(block)}, ${code(block, 'INDEX', '1')})\n`;
  pythonGenerator.forBlock.list_remove_value_named = (block) => `CoronaEngine.data_list_remove_value(${scope(block)}, ${name(block)}, ${code(block, 'VALUE')})\n`;
  pythonGenerator.forBlock.list_clear_named = (block) => `CoronaEngine.data_list_clear(${scope(block)}, ${name(block)})\n`;
  pythonGenerator.forBlock.list_item_named = (block) => [`CoronaEngine.data_list_item(${scope(block)}, ${name(block)}, ${code(block, 'INDEX', '1')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.list_length_named = (block) => [`CoronaEngine.data_list_length(${scope(block)}, ${name(block)})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.list_contains_named = (block) => [`CoronaEngine.data_list_contains(${scope(block)}, ${name(block)}, ${code(block, 'VALUE')})`, pythonGenerator.ORDER_FUNCTION_CALL];
};
