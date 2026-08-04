import { pythonGenerator } from 'blockly/python';

export const defineEngineGenerators = () => {
  const objectTarget = (block) => block.getInput('OBJECT')
    ? pythonGenerator.valueToCode(block, 'OBJECT', pythonGenerator.ORDER_NONE)
    : '';
  const callWithObject = (name, args, target) => {
    const values = target ? [...args, target] : args;
    return `CoronaEngine.${name}(${values.join(', ')})`;
  };

  pythonGenerator.forBlock['engine_move'] = function (block) {
    const steps = block.getFieldValue('STEPS');
    return `${callWithObject('move', [steps], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_rotateX'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `${callWithObject('rotateX', [angle], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_rotateY'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `${callWithObject('rotateY', [angle], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_rotateZ'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `${callWithObject('rotateZ', [angle], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_face'] = function (block) {
    const direction = block.getFieldValue('DIRECTION');
    return `${callWithObject('face', [direction], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_moveto'] = function (block) {
    const position = block.getFieldValue('POSITION');
    return `${callWithObject('moveto', [JSON.stringify(position)], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_movetoXYZ'] = function (block) {
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `${callWithObject('movetoXYZtime', ['0', x, y, z], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_movetoXYZtime'] = function (block) {
    const t = block.getFieldValue('TIME');
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `${callWithObject('movetoXYZtime', [t, x, y, z], objectTarget(block))}\n`;
  };

  pythonGenerator.forBlock['engine_X'] = function (block) {
    return [callWithObject('X', [], objectTarget(block)), pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['engine_Y'] = function (block) {
    return [callWithObject('Y', [], objectTarget(block)), pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['engine_Z'] = function (block) {
    return [callWithObject('Z', [], objectTarget(block)), pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock.engine_rotationX = (block) => [callWithObject('rotationX', [], objectTarget(block)), pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.engine_rotationY = (block) => [callWithObject('rotationY', [], objectTarget(block)), pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.engine_rotationZ = (block) => [callWithObject('rotationZ', [], objectTarget(block)), pythonGenerator.ORDER_FUNCTION_CALL];


  // ── 物理扩展生成器 ──

  pythonGenerator.forBlock['engine_get_velocity'] = function (block) {
    const axis = block.getFieldValue('AXIS');
    return [`CoronaEngine.get_velocity('${axis}')`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['engine_set_gravity'] = function (block) {
    const enabled = block.getFieldValue('ENABLED') === 'TRUE' ? 'True' : 'False';
    const strength = block.getFieldValue('STRENGTH');
    return `CoronaEngine.set_gravity(${enabled}, ${strength})\n`;
  };

  pythonGenerator.forBlock['engine_bounce_axis'] = function (block) {
    const axis = block.getFieldValue('AXIS');
    const factor = block.getFieldValue('FACTOR');
    return `CoronaEngine.bounce_axis('${axis}', ${factor})\n`;
  };

  pythonGenerator.forBlock['engine_get_game_speed'] = function () {
    return ['CoronaEngine.game_speed()', pythonGenerator.ORDER_FUNCTION_CALL];
  };


  const input = (block, name, legacy, fallback = '0') =>
    pythonGenerator.valueToCode(block, name, pythonGenerator.ORDER_NONE) || block.getFieldValue(legacy) || fallback;
  pythonGenerator.forBlock.engine_Xset = (block) => `${callWithObject('Xset', [input(block, 'VALUE', 'X')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_Yset = (block) => `${callWithObject('Yset', [input(block, 'VALUE', 'Y')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_Zset = (block) => `${callWithObject('Zset', [input(block, 'VALUE', 'Z')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_Xadd = (block) => `${callWithObject('Xadd', [input(block, 'VALUE', 'DX')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_Yadd = (block) => `${callWithObject('Yadd', [input(block, 'VALUE', 'DY')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_Zadd = (block) => `${callWithObject('Zadd', [input(block, 'VALUE', 'DZ')], objectTarget(block))}\n`;
  pythonGenerator.forBlock.engine_jump = (block) => `CoronaEngine.jump(${input(block, 'VALUE', 'POWER', '8')})\n`;
  pythonGenerator.forBlock.engine_set_game_speed = (block) => `CoronaEngine.set_game_speed(${input(block, 'VALUE', 'VALUE', '1')})\n`;
  pythonGenerator.forBlock.engine_set_velocity = (block) => `CoronaEngine.set_velocity(${input(block, 'VX', 'VX')}, ${input(block, 'VY', 'VY')}, ${input(block, 'VZ', 'VZ')})\n`;
  pythonGenerator.forBlock.engine_apply_impulse = (block) => `CoronaEngine.apply_impulse(${input(block, 'IX', 'IX')}, ${input(block, 'IY', 'IY')}, ${input(block, 'IZ', 'IZ')})\n`;
  pythonGenerator.forBlock.engine_set_velocity_axis = (block) => `CoronaEngine.set_velocity_axis('${block.getFieldValue('AXIS') || 'X'}', ${input(block, 'VALUE', 'VALUE_DEFAULT', '0')})\n`;
  pythonGenerator.forBlock.engine_bounce_last_collision = (block) => `CoronaEngine.bounce_last_collision(${input(block, 'FACTOR', 'FACTOR_DEFAULT', '1')})\n`;
  pythonGenerator.forBlock.engine_stop_motion = () => 'CoronaEngine.stop_motion()\n';

};
