import { pythonGenerator } from 'blockly/python';

const pyString = (value) => JSON.stringify(String(value ?? ''));

export const defineObjectGenerators = () => {
  pythonGenerator.forBlock['object_hide'] = function (block) {
    return `CoronaEngine.object_hide(${pyString(block.getFieldValue('NAME'))})\n`;
  };

  pythonGenerator.forBlock['object_show'] = function (block) {
    return `CoronaEngine.object_show(${pyString(block.getFieldValue('NAME'))})\n`;
  };

  pythonGenerator.forBlock['object_delete'] = function (block) {
    return `CoronaEngine.object_delete(${pyString(block.getFieldValue('NAME'))})\n`;
  };

  pythonGenerator.forBlock['object_delete_last_touched'] = function () {
    return 'CoronaEngine.object_delete_last_touched()\n';
  };

  pythonGenerator.forBlock['object_set_position'] = function (block) {
    const name = pyString(block.getFieldValue('NAME'));
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `CoronaEngine.object_set_position(${name}, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['object_get_x'] = function (block) {
    return [`CoronaEngine.object_x(${pyString(block.getFieldValue('NAME'))})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_get_y'] = function (block) {
    return [`CoronaEngine.object_y(${pyString(block.getFieldValue('NAME'))})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_get_z'] = function (block) {
    return [`CoronaEngine.object_z(${pyString(block.getFieldValue('NAME'))})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_exists'] = function (block) {
    return [`CoronaEngine.object_exists(${pyString(block.getFieldValue('NAME'))})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_set_tag'] = function (block) {
    const name = pyString(block.getFieldValue('NAME'));
    const tag = pyString(block.getFieldValue('TAG'));
    return `CoronaEngine.object_set_tag(${name}, ${tag})\n`;
  };

  pythonGenerator.forBlock['object_count_tag'] = function (block) {
    return [`CoronaEngine.object_count_tag(${pyString(block.getFieldValue('TAG'))})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['object_spawn'] = function (block) {
    const template = pyString(block.getFieldValue('TEMPLATE'));
    const name = pyString(block.getFieldValue('NAME'));
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `CoronaEngine.object_spawn(${template}, ${name}, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['object_spawn_tag'] = function (block) {
    const template = pyString(block.getFieldValue('TEMPLATE'));
    const tag = pyString(block.getFieldValue('TAG'));
    const count = block.getFieldValue('COUNT');
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    const dx = block.getFieldValue('DX');
    const dy = block.getFieldValue('DY');
    const dz = block.getFieldValue('DZ');
    return `CoronaEngine.object_spawn_tag(${template}, ${tag}, ${count}, ${x}, ${y}, ${z}, ${dx}, ${dy}, ${dz})\n`;
  };

  pythonGenerator.forBlock['object_delete_raycast_hit'] = function () {
    return 'CoronaEngine.object_delete_raycast_hit()\n';
  };

  pythonGenerator.forBlock['object_move_tag'] = function (block) {
    const tag = pyString(block.getFieldValue('TAG'));
    const dx = block.getFieldValue('DX');
    const dy = block.getFieldValue('DY');
    const dz = block.getFieldValue('DZ');
    return `CoronaEngine.object_move_tag(${tag}, ${dx}, ${dy}, ${dz})\n`;
  };

};
