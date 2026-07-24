import { pythonGenerator } from 'blockly/python';

export const defineUiGenerators = () => {

  pythonGenerator.forBlock['ui_game_win'] = function () {
    return 'CoronaEngine.game_win()\n';
  };

  pythonGenerator.forBlock['ui_game_over'] = function () {
    return 'CoronaEngine.game_over()\n';
  };

  pythonGenerator.forBlock['ui_lives'] = function () {
    return ['CoronaEngine.lives()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['ui_countdown_left'] = function () {
    return ['CoronaEngine.countdown_left()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['ui_countdown_finished'] = function () {
    return ['CoronaEngine.countdown_finished()', pythonGenerator.ORDER_FUNCTION_CALL];
  };


  const value = (block, input, legacy, fallback = '0') => pythonGenerator.valueToCode(block, input, pythonGenerator.ORDER_NONE) || block.getFieldValue(legacy) || fallback;
  pythonGenerator.forBlock.ui_set_score = (block) => `CoronaEngine.set_score(${value(block,'VALUE_INPUT','VALUE')})\n`;
  pythonGenerator.forBlock.ui_add_score = (block) => `CoronaEngine.add_score(${value(block,'VALUE_INPUT','DELTA','1')})\n`;
  pythonGenerator.forBlock.ui_set_lives = (block) => `CoronaEngine.set_lives(${value(block,'VALUE_INPUT','VALUE','3')})\n`;
  pythonGenerator.forBlock.ui_add_lives = (block) => `CoronaEngine.add_lives(${value(block,'VALUE_INPUT','DELTA','1')})\n`;
  pythonGenerator.forBlock.ui_set_countdown = (block) => `CoronaEngine.set_countdown(${value(block,'VALUE_INPUT','SECONDS','30')})\n`;
  pythonGenerator.forBlock.ui_score = () => ['CoronaEngine.score()', pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.ui_game_state = () => ['CoronaEngine.game_state()', pythonGenerator.ORDER_FUNCTION_CALL];
  pythonGenerator.forBlock.ui_countdown_elapsed = () => ['CoronaEngine.countdown_elapsed()', pythonGenerator.ORDER_FUNCTION_CALL];

};
