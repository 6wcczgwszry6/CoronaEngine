import { pythonGenerator } from 'blockly/python';

const pyString = (value) => JSON.stringify(String(value ?? ''));
const connectedValue = (block, name) => block.getInput(name)
  ? pythonGenerator.valueToCode(block, name, pythonGenerator.ORDER_NONE)
  : '';

const valueOrLegacyText = (block, name, fallback = '') =>
  connectedValue(block, name)
  || pyString(block.getFieldValue(name) ?? block.getFieldValue(`${name}_TEXT`) ?? fallback);

const valueOrLegacyNumber = (block, name, fallback = '0') =>
  connectedValue(block, name)
  || block.getFieldValue(name)
  || block.getFieldValue(`${name}_NUMBER`)
  || fallback;

export const defineObjectGenerators = () => {
  pythonGenerator.forBlock['object_hide'] = function (block) {
    return `CoronaEngine.object_hide(${valueOrLegacyText(block, 'NAME')})\n`;
  };

  pythonGenerator.forBlock['object_show'] = function (block) {
    return `CoronaEngine.object_show(${valueOrLegacyText(block, 'NAME')})\n`;
  };

  pythonGenerator.forBlock['object_delete'] = function (block) {
    return `CoronaEngine.object_delete(${valueOrLegacyText(block, 'NAME')})\n`;
  };

  pythonGenerator.forBlock['object_delete_last_touched'] = function () {
    return 'CoronaEngine.object_delete_last_touched()\n';
  };

  pythonGenerator.forBlock['object_set_position'] = function (block) {
    const name = valueOrLegacyText(block, 'NAME');
    const x = valueOrLegacyNumber(block, 'X');
    const y = valueOrLegacyNumber(block, 'Y');
    const z = valueOrLegacyNumber(block, 'Z');
    return `CoronaEngine.object_set_position(${name}, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['object_get_x'] = function (block) {
    return [`CoronaEngine.object_x(${valueOrLegacyText(block, 'NAME')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_get_y'] = function (block) {
    return [`CoronaEngine.object_y(${valueOrLegacyText(block, 'NAME')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_get_z'] = function (block) {
    return [`CoronaEngine.object_z(${valueOrLegacyText(block, 'NAME')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_exists'] = function (block) {
    return [`CoronaEngine.object_exists(${valueOrLegacyText(block, 'NAME')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_set_tag'] = function (block) {
    const name = valueOrLegacyText(block, 'NAME');
    const tag = valueOrLegacyText(block, 'TAG', 'tag');
    return `CoronaEngine.object_set_tag(${name}, ${tag})\n`;
  };

  pythonGenerator.forBlock['object_count_tag'] = function (block) {
    return [`CoronaEngine.object_count_tag(${valueOrLegacyText(block, 'TAG', 'tag')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_spawn'] = function (block) {
    const template = valueOrLegacyText(block, 'TEMPLATE', 'template');
    const name = valueOrLegacyText(block, 'NAME', 'object_01');
    const x = valueOrLegacyNumber(block, 'X');
    const y = valueOrLegacyNumber(block, 'Y');
    const z = valueOrLegacyNumber(block, 'Z');
    return `CoronaEngine.object_spawn(${template}, ${name}, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['object_spawn_tag'] = function (block) {
    const template = valueOrLegacyText(block, 'TEMPLATE', 'template');
    const tag = valueOrLegacyText(block, 'TAG', 'coin');
    const count = valueOrLegacyNumber(block, 'COUNT', '5');
    const x = valueOrLegacyNumber(block, 'X');
    const y = valueOrLegacyNumber(block, 'Y');
    const z = valueOrLegacyNumber(block, 'Z');
    const dx = valueOrLegacyNumber(block, 'DX', '1');
    const dy = valueOrLegacyNumber(block, 'DY');
    const dz = valueOrLegacyNumber(block, 'DZ');
    return `CoronaEngine.object_spawn_tag(${template}, ${tag}, ${count}, ${x}, ${y}, ${z}, ${dx}, ${dy}, ${dz})\n`;
  };

  pythonGenerator.forBlock['object_delete_raycast_hit'] = function () {
    return 'CoronaEngine.object_delete_raycast_hit()\n';
  };

  pythonGenerator.forBlock['object_move_tag'] = function (block) {
    const tag = connectedValue(block, 'TAG')
      || pyString(block.getFieldValue('TAG_TEXT') ?? block.getFieldValue('TAG') ?? 'tag');
    const numberInput = (name) => connectedValue(block, name)
      || block.getFieldValue(`${name}_NUMBER`)
      || block.getFieldValue(name)
      || '0';
    return `CoronaEngine.object_move_tag(${tag}, ${numberInput('DX')}, ${numberInput('DY')}, ${numberInput('DZ')})
`;
  };


  const input = (block, name, fallback = '0') => connectedValue(block, name) || block.getFieldValue(`${name}_NUMBER`) || (block.getFieldValue(`${name}_TEXT`) != null ? pyString(block.getFieldValue(`${name}_TEXT`)) : '') || fallback;
  pythonGenerator.forBlock.object_clamp_axis = (block) => `CoronaEngine.object_clamp_axis(${input(block,'NAME',"''")}, '${block.getFieldValue('AXIS') || 'X'}', ${input(block,'MIN')}, ${input(block,'MAX')})\n`;
  pythonGenerator.forBlock.object_save_checkpoint = (block) => `CoronaEngine.object_save_checkpoint(${input(block,'NAME',"''")}, ${input(block,'CHECKPOINT',"'default'")}, ${block.getFieldValue('SAVE_VELOCITY') === 'TRUE' ? 'True' : 'False'})\n`;
  pythonGenerator.forBlock.object_restore_checkpoint = (block) => `CoronaEngine.object_restore_checkpoint(${input(block,'NAME',"''")}, ${input(block,'CHECKPOINT',"'default'")}, ${block.getFieldValue('CLEAR_VELOCITY') === 'TRUE' ? 'True' : 'False'})\n`;
  pythonGenerator.forBlock.object_move_to_lane = (block) => `CoronaEngine.object_move_to_lane(${input(block,'NAME',"''")}, '${block.getFieldValue('AXIS') || 'X'}', ${input(block,'LANE')}, ${input(block,'ORIGIN')}, ${input(block,'SPACING','1')})\n`;
  pythonGenerator.forBlock.object_lane_index = (block) => [`CoronaEngine.object_lane_index(${input(block,'NAME',"''")}, '${block.getFieldValue('AXIS') || 'X'}', ${input(block,'ORIGIN')}, ${input(block,'SPACING','1')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.object_set_random_position = (block) => `CoronaEngine.object_set_random_position(${input(block,'NAME',"''")}, ${['CX','CY','CZ','SX','SY','SZ'].map((key)=>input(block,key)).join(', ')})\n`;
  pythonGenerator.forBlock.object_spawn_random_box = (block) => `CoronaEngine.object_spawn_random_box(${input(block,'TEMPLATE',"''")}, ${input(block,'TAG',"''")}, ${input(block,'COUNT','1')}, ${['CX','CY','CZ','SX','SY','SZ'].map((key)=>input(block,key)).join(', ')})\n`;
  pythonGenerator.forBlock.object_scatter_tag = (block) => `CoronaEngine.object_scatter_tag(${input(block,'TAG',"''")}, ${['CX','CY','CZ','SX','SY','SZ'].map((key)=>input(block,key)).join(', ')})\n`;
  pythonGenerator.forBlock.object_recycle_tag_axis = (block) => `CoronaEngine.object_recycle_tag_axis(${input(block,'TAG',"''")}, '${block.getFieldValue('AXIS') || 'X'}', '${block.getFieldValue('DIRECTION') || 'LESS'}', ${input(block,'BOUNDARY')}, ${input(block,'RESET')}, '${block.getFieldValue('RANDOM_AXIS') || ''}', ${input(block,'RANDOM_MIN')}, ${input(block,'RANDOM_MAX')})\n`;
  pythonGenerator.forBlock.object_reset_tag = (block) => `CoronaEngine.object_reset_tag(${input(block,'TAG',"''")})\n`;
  pythonGenerator.forBlock.object_count_active_tag = (block) => [`CoronaEngine.object_count_active_tag(${input(block,'TAG',"''")})`, pythonGenerator.ORDER_FUNCTION_CALL];

  pythonGenerator.forBlock.object_reference = (block) => {
    const selected = block.getFieldValue('OBJECT') || '';
    const value = selected === '__manual__' ? block.getFieldValue('MANUAL') : selected;
    return [pyString(value || ''), pythonGenerator.ORDER_ATOMIC];
  };
  pythonGenerator.forBlock.object_set_logical_collision = (block) => `CoronaEngine.set_object_logical_collision(${input(block,'NAME',"''")}, ${block.getFieldValue('ENABLED') === 'FALSE' ? 'False' : 'True'})\n`;
  pythonGenerator.forBlock.object_logical_collision_enabled = (block) => [`CoronaEngine.object_logical_collision_enabled(${input(block,'NAME',"''")})`, pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.object_set_native_physics = (block) => `CoronaEngine.set_object_native_physics(${input(block,'NAME',"''")}, ${block.getFieldValue('ENABLED') === 'FALSE' ? 'False' : 'True'})\n`;
  pythonGenerator.forBlock.object_move_to_lane_smooth = (block) => `CoronaEngine.object_move_to_lane_smooth(${input(block,'NAME',"''")}, '${block.getFieldValue('AXIS') || 'X'}', ${input(block,'LANE')}, ${input(block,'ORIGIN')}, ${input(block,'SPACING','2')}, ${input(block,'SPEED','8')})\n`;
  pythonGenerator.forBlock.object_set_tag_velocity_axis = (block) => `CoronaEngine.set_tag_velocity_axis(${input(block,'TAG',"''")}, '${block.getFieldValue('AXIS') || 'X'}', ${input(block,'VALUE')})\n`;
  pythonGenerator.forBlock.object_randomize_mouse_pick = (block) => `CoronaEngine.object_randomize_mouse_pick(${['CX','CY','CZ','SX','SY','SZ'].map((key)=>input(block,key)).join(', ')})\n`;
  pythonGenerator.forBlock.object_delete_mouse_pick = () => 'CoronaEngine.object_delete_mouse_pick()\n';
  pythonGenerator.forBlock.object_reset_crossed_once = (block) => `CoronaEngine.reset_crossed_once(${input(block,'NAME',"''")}, ${input(block,'TRIGGER',"''")})\n`;

};
