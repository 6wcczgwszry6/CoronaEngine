import { pythonGenerator } from 'blockly/python';

export const defineListGenerators = () => {
  pythonGenerator.forBlock['list_show'] = function (block) {
    const v = block.getFieldValue('v');
    return `CoronaEngine.list_show("${v}")\n`;
  };

  pythonGenerator.forBlock['list_hide'] = function (block) {
    const v = block.getFieldValue('v');
    return `CoronaEngine.list_hide("${v}")\n`;
  };
};
