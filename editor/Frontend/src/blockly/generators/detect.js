import { pythonGenerator } from 'blockly/python';

export const defineDetectGenerators = () => {
  pythonGenerator.forBlock['detect_touch'] = function (block) {
    const x = block.getFieldValue('x');
    return [`CoronaEngine.touch("${x}")`, pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['detect_distance'] = function (block) {
    const x = block.getFieldValue('x');
    return [`CoronaEngine.distance("${x}")`, pythonGenerator.ORDER_ATOMIC];
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
};
