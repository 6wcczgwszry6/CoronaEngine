import { pythonGenerator } from 'blockly/python';

export const defineUiGenerators = () => {
  pythonGenerator.forBlock['ui_set_score'] = function (block) {
    return `CoronaEngine.set_score(${block.getFieldValue('VALUE')})\n`;
  };

  pythonGenerator.forBlock['ui_add_score'] = function (block) {
    return `CoronaEngine.add_score(${block.getFieldValue('DELTA')})\n`;
  };

  pythonGenerator.forBlock['ui_game_win'] = function () {
    return 'CoronaEngine.game_win()\n';
  };

  pythonGenerator.forBlock['ui_game_over'] = function () {
    return 'CoronaEngine.game_over()\n';
  };

  pythonGenerator.forBlock['ui_set_lives'] = function (block) {
    return `CoronaEngine.set_lives(${block.getFieldValue('VALUE')})\n`;
  };

  pythonGenerator.forBlock['ui_add_lives'] = function (block) {
    return `CoronaEngine.add_lives(${block.getFieldValue('DELTA')})\n`;
  };

  pythonGenerator.forBlock['ui_lives'] = function () {
    return ['CoronaEngine.lives()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['ui_set_countdown'] = function (block) {
    return `CoronaEngine.set_countdown(${block.getFieldValue('SECONDS')})\n`;
  };

  pythonGenerator.forBlock['ui_countdown_left'] = function () {
    return ['CoronaEngine.countdown_left()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['ui_countdown_finished'] = function () {
    return ['CoronaEngine.countdown_finished()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

};
