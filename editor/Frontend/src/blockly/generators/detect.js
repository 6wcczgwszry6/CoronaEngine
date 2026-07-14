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

export const defineDetectGenerators = () => {
  pythonGenerator.forBlock['detect_touch'] = function (block) {
    return [`CoronaEngine.touch(${valueOrLegacyText(block, 'x')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_not_touch'] = function (block) {
    return [`(not CoronaEngine.touch(${valueOrLegacyText(block, 'NAME')}))`, pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['detect_touch_any'] = function () {
    return ['CoronaEngine.touch_any()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_not_touch_any'] = function () {
    return ['(not CoronaEngine.touch_any())', pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['detect_distance'] = function (block) {
    return [`CoronaEngine.distance(${valueOrLegacyText(block, 'x')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };


  pythonGenerator.forBlock['detect_touch_tag'] = function (block) {
    return [`CoronaEngine.touch_tag(${valueOrLegacyText(block, 'TAG', 'tag')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_not_touch_tag'] = function (block) {
    return [`(not CoronaEngine.touch_tag(${valueOrLegacyText(block, 'TAG', 'tag')}))`, pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['detect_last_touch_object'] = function () {
    return ['CoronaEngine.last_touch_object()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_ask'] = function (block) {
    const x = block.getFieldValue('x');
    return `CoronaEngine.ask("${x}")\n`;
  };

  pythonGenerator.forBlock['detect_keyboard1'] = function (block) {
    const x = block.getFieldValue('x');
    return [`CoronaEngine.keyboard("${x}")`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_keyboard0'] = function (block) {
    const x = block.getFieldValue('x');
    return [`CoronaEngine.keyboard0("${x}")`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_mouse1'] = function (block) {
    return [`CoronaEngine.mouse1()`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_mouse0'] = function (block) {
    return [`CoronaEngine.mouse0()`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_attribute'] = function (block) {
    const x = block.getFieldValue('x');
    return [`CoronaEngine.attribute('${x}')`, pythonGenerator.ORDER_ATOMIC];
  };

  // ── 射线检测生成器 ──

  pythonGenerator.forBlock['detect_raycast'] = function (block) {
    const ox = block.getFieldValue('OX');
    const oy = block.getFieldValue('OY');
    const oz = block.getFieldValue('OZ');
    const dx = block.getFieldValue('DX');
    const dy = block.getFieldValue('DY');
    const dz = block.getFieldValue('DZ');
    const maxDist = block.getFieldValue('MAX_DIST');
    const origin = `[${ox}, ${oy}, ${oz}]`;
    const direction = `[${dx}, ${dy}, ${dz}]`;
    return [`CoronaEngine.raycast_hit(${origin}, ${direction}, ${maxDist})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_raycast_distance'] = function () {
    return ['CoronaEngine.raycast_distance()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_raycast_object'] = function () {
    return ['CoronaEngine.raycast_hit_object()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_raycast_point'] = function (block) {
    const axis = block.getFieldValue('AXIS');
    const fn = axis === 'X' ? 'raycast_hit_point_x' : axis === 'Y' ? 'raycast_hit_point_y' : 'raycast_hit_point_z';
    return [`CoronaEngine.${fn}()`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_ground_below'] = function (block) {
    return [`CoronaEngine.ground_below(${valueOrLegacyNumber(block, 'DISTANCE', '1')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_no_ground_below'] = function (block) {
    return [`(not CoronaEngine.ground_below(${valueOrLegacyNumber(block, 'DISTANCE', '1')}))`, pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['detect_object_exists'] = function (block) {
    return [`CoronaEngine.object_exists(${valueOrLegacyText(block, 'NAME')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_object_not_exists'] = function (block) {
    return [`(not CoronaEngine.object_exists(${valueOrLegacyText(block, 'NAME')}))`, pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['detect_raycast_hit_tag'] = function (block) {
    return [`CoronaEngine.raycast_hit_tag(${valueOrLegacyText(block, 'TAG', 'tag')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_passed_x'] = function (block) {
    return [`CoronaEngine.object_passed_x(${valueOrLegacyText(block, 'NAME')}, ${valueOrLegacyNumber(block, 'X')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['detect_passed_z'] = function (block) {
    return [`CoronaEngine.object_passed_z(${valueOrLegacyText(block, 'NAME')}, ${valueOrLegacyNumber(block, 'Z')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };


  const value = (block, input, fallback) => connectedValue(block, input)
    || block.getFieldValue(input)
    || block.getFieldValue(`${input}_NUMBER`)
    || (block.getFieldValue(`${input}_TEXT`) != null ? pyString(block.getFieldValue(`${input}_TEXT`)) : '')
    || fallback;
  pythonGenerator.forBlock.detect_touch_started = (block) => [
    `CoronaEngine.touch_started(${value(block, 'NAME', "''")}, ${JSON.stringify(block.id)})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_touch_tag_started = (block) => [
    `CoronaEngine.touch_tag_started(${value(block, 'TAG', "''")}, ${JSON.stringify(block.id)})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  const crossedOnce = (axis) => (block) => [
    `CoronaEngine.crossed_axis_once(${value(block, 'NAME', "''")}, '${axis}', ${value(block, 'THRESHOLD', '0')}, '${block.getFieldValue('DIRECTION') || 'ANY'}', ${JSON.stringify(block.id)})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_crossed_x_once = crossedOnce('X');
  pythonGenerator.forBlock.detect_crossed_z_once = crossedOnce('Z');
  pythonGenerator.forBlock.detect_outside_axis = (block) => [
    `CoronaEngine.outside_axis(${value(block, 'NAME', "''")}, '${block.getFieldValue('AXIS') || 'X'}', ${value(block, 'MIN', '0')}, ${value(block, 'MAX', '0')})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_inside_axis = (block) => [
    `CoronaEngine.inside_axis(${valueOrLegacyText(block, 'NAME')}, '${block.getFieldValue('AXIS') || 'X'}', ${valueOrLegacyNumber(block, 'MIN')}, ${valueOrLegacyNumber(block, 'MAX', '10')})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_inside_box = (block) => [
    `CoronaEngine.inside_box(${value(block, 'NAME', "''")}, ${['CX','CY','CZ','SX','SY','SZ'].map((key) => value(block, key, '0')).join(', ')})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_last_collision_axis = () => ['CoronaEngine.last_collision_axis()', pythonGenerator.ORDER_FUNCTION_CALL];
  for (const axis of ['x','y','z']) pythonGenerator.forBlock[`detect_last_collision_normal_${axis}`] = () => [`CoronaEngine.last_collision_normal('${axis.toUpperCase()}')`, pythonGenerator.ORDER_FUNCTION_CALL];

  const valueOrText = (block, name, fallback="''") => connectedValue(block, name) || (block.getFieldValue(`${name}_TEXT`) != null ? pyString(block.getFieldValue(`${name}_TEXT`)) : '') || fallback;
  pythonGenerator.forBlock.detect_position_near = (block) => [
    `CoronaEngine.position_near(${valueOrText(block,'NAME')}, ${['X','Y','Z','TOLERANCE'].map((key)=>value(block,key,key === 'TOLERANCE' ? '0.1' : '0')).join(', ')})`,
    pythonGenerator.ORDER_FUNCTION_CALL,
  ];
  pythonGenerator.forBlock.detect_mouse_pick_object = () => ['CoronaEngine.mouse_pick_object()', pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.detect_mouse_pick_hit_tag = (block) => [`CoronaEngine.mouse_pick_hit_tag(${valueOrText(block,'TAG')})`, pythonGenerator.ORDER_FUNCTION_CALL];

};
