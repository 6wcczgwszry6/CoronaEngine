import { pythonGenerator } from 'blockly/python';

export const defineEngineGenerators = () => {
  pythonGenerator.forBlock['engine_move'] = function (block) {
    const steps = block.getFieldValue('STEPS');
    return `CoronaEngine.move(${steps})\n`;
  };

  pythonGenerator.forBlock['engine_rotateX'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `CoronaEngine.rotateX(${angle})\n`;
  };

  pythonGenerator.forBlock['engine_rotateY'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `CoronaEngine.rotateY(${angle})\n`;
  };

  pythonGenerator.forBlock['engine_rotateZ'] = function (block) {
    const angle = block.getFieldValue('ANGLE');
    return `CoronaEngine.rotateZ(${angle})\n`;
  };

  pythonGenerator.forBlock['engine_face'] = function (block) {
    const direction = block.getFieldValue('DIRECTION');
    return `CoronaEngine.face(${direction})\n`;
  };

  pythonGenerator.forBlock['engine_moveto'] = function (block) {
    const position = block.getFieldValue('POSITION');
    return `CoronaEngine.moveto("${position}")\n`;
  };

  pythonGenerator.forBlock['engine_movetoXYZ'] = function (block) {
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `CoronaEngine.movetoXYZtime(0, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['engine_movetoXYZtime'] = function (block) {
    const t = block.getFieldValue('TIME');
    const x = block.getFieldValue('X');
    const y = block.getFieldValue('Y');
    const z = block.getFieldValue('Z');
    return `CoronaEngine.movetoXYZtime(${t}, ${x}, ${y}, ${z})\n`;
  };

  pythonGenerator.forBlock['engine_X'] = function () {
    return ['CoronaEngine.X()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['engine_Y'] = function () {
    return ['CoronaEngine.Y()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['engine_Z'] = function () {
    return ['CoronaEngine.Z()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock.engine_rotationX = () => ['CoronaEngine.rotationX()', pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.engine_rotationY = () => ['CoronaEngine.rotationY()', pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.engine_rotationZ = () => ['CoronaEngine.rotationZ()', pythonGenerator.ORDER_FUNCTION_CALL];


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
  pythonGenerator.forBlock.engine_Xset = (block) => `CoronaEngine.Xset(${input(block, 'VALUE', 'X')})\n`;
  pythonGenerator.forBlock.engine_Yset = (block) => `CoronaEngine.Yset(${input(block, 'VALUE', 'Y')})\n`;
  pythonGenerator.forBlock.engine_Zset = (block) => `CoronaEngine.Zset(${input(block, 'VALUE', 'Z')})\n`;
  pythonGenerator.forBlock.engine_Xadd = (block) => `CoronaEngine.Xadd(${input(block, 'VALUE', 'DX')})\n`;
  pythonGenerator.forBlock.engine_Yadd = (block) => `CoronaEngine.Yadd(${input(block, 'VALUE', 'DY')})\n`;
  pythonGenerator.forBlock.engine_Zadd = (block) => `CoronaEngine.Zadd(${input(block, 'VALUE', 'DZ')})\n`;
  pythonGenerator.forBlock.engine_jump = (block) => `CoronaEngine.jump(${input(block, 'VALUE', 'POWER', '8')})\n`;
  pythonGenerator.forBlock.engine_set_game_speed = (block) => `CoronaEngine.set_game_speed(${input(block, 'VALUE', 'VALUE', '1')})\n`;
  pythonGenerator.forBlock.engine_set_velocity = (block) => `CoronaEngine.set_velocity(${input(block, 'VX', 'VX')}, ${input(block, 'VY', 'VY')}, ${input(block, 'VZ', 'VZ')})\n`;
  pythonGenerator.forBlock.engine_apply_impulse = (block) => `CoronaEngine.apply_impulse(${input(block, 'IX', 'IX')}, ${input(block, 'IY', 'IY')}, ${input(block, 'IZ', 'IZ')})\n`;
  pythonGenerator.forBlock.engine_set_velocity_axis = (block) => `CoronaEngine.set_velocity_axis('${block.getFieldValue('AXIS') || 'X'}', ${input(block, 'VALUE', 'VALUE_DEFAULT', '0')})\n`;
  pythonGenerator.forBlock.engine_bounce_last_collision = (block) => `CoronaEngine.bounce_last_collision(${input(block, 'FACTOR', 'FACTOR_DEFAULT', '1')})\n`;
  pythonGenerator.forBlock.engine_stop_motion = () => 'CoronaEngine.stop_motion()\n';

};
