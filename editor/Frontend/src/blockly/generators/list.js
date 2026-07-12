import { pythonGenerator } from 'blockly/python';

export const defineListGenerators = () => {
  pythonGenerator.forBlock['list_show'] = function (block) {
    const v = block.getFieldValue('v') || '';
    const key = JSON.stringify(v);
    return `CoronaEngine.list_show(${key}, locals().get(${key}, globals().get(${key}, [])))\n`;
  };

  pythonGenerator.forBlock['list_hide'] = function (block) {
    const v = JSON.stringify(block.getFieldValue('v') || '');
    return `CoronaEngine.list_hide(${v})\n`;
  };
};
