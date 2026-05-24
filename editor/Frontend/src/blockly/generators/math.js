import { pythonGenerator } from 'blockly/python';

export const defineMathGenerators = () => {
  pythonGenerator.forBlock['math_add'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} + ${x2})`, pythonGenerator.ORDER_ADDITION];
  };

  pythonGenerator.forBlock['math_mul'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} * ${x2})`, pythonGenerator.ORDER_MULTIPLICATION];
  };

  pythonGenerator.forBlock['math_div'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} / ${x2})`, pythonGenerator.ORDER_MULTIPLICATION];
  };

  pythonGenerator.forBlock['math_sub'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} - ${x2})`, pythonGenerator.ORDER_ADDITION];
  };

  pythonGenerator.forBlock['math_random'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`CoronaEngine.random(${x1},${x2})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['math_G'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} > ${x2})`, pythonGenerator.ORDER_RELATIONAL];
  };

  pythonGenerator.forBlock['math_L'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} < ${x2})`, pythonGenerator.ORDER_RELATIONAL];
  };

  pythonGenerator.forBlock['math_E'] = function (block) {
    const x1 = block.getFieldValue('x1');
    const x2 = block.getFieldValue('x2');
    return [`(${x1} == ${x2})`, pythonGenerator.ORDER_EQUALITY];
  };

  pythonGenerator.forBlock['math_AND'] = function (block) {
    const a = pythonGenerator.valueToCode(block, 'A', pythonGenerator.ORDER_LOGICAL_AND) || 'False';
    const b = pythonGenerator.valueToCode(block, 'B', pythonGenerator.ORDER_LOGICAL_AND) || 'False';
    return [a + ' and ' + b, pythonGenerator.ORDER_LOGICAL_AND];
  };

  pythonGenerator.forBlock['math_OR'] = function (block) {
    const a = pythonGenerator.valueToCode(block, 'A', pythonGenerator.ORDER_LOGICAL_OR) || 'False';
    const b = pythonGenerator.valueToCode(block, 'B', pythonGenerator.ORDER_LOGICAL_OR) || 'False';
    return [a + ' or ' + b, pythonGenerator.ORDER_LOGICAL_OR];
  };

  pythonGenerator.forBlock['math_NOT'] = function (block) {
    const a = pythonGenerator.valueToCode(block, 'A', pythonGenerator.ORDER_LOGICAL_NOT) || 'False';
    return ['not ' + a, pythonGenerator.ORDER_LOGICAL_NOT];
  };

  pythonGenerator.forBlock['math_connect'] = function (block) {
    const left = pythonGenerator.valueToCode(block, 'LEFT', pythonGenerator.ORDER_NONE) || "''";
    const right = pythonGenerator.valueToCode(block, 'RIGHT', pythonGenerator.ORDER_NONE) || "''";
    const leftStr = `str(${left})`;
    const rightStr = `str(${right})`;
    return [leftStr + ' + ' + rightStr, pythonGenerator.ORDER_ADDITION];
  };
};
