import { pythonGenerator } from 'blockly/python';

const pyString = (value) => JSON.stringify(String(value ?? ''));

export const defineCameraGenerators = () => {
  pythonGenerator.forBlock['camera_lock_mouse'] = function () {
    return 'CoronaEngine.lock_mouse()\n';
  };

  pythonGenerator.forBlock['camera_unlock_mouse'] = function () {
    return 'CoronaEngine.unlock_mouse()\n';
  };

  pythonGenerator.forBlock['camera_mouse_dx'] = function () {
    return ['CoronaEngine.mouse_dx()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['camera_mouse_dy'] = function () {
    return ['CoronaEngine.mouse_dy()', pythonGenerator.ORDER_ATOMIC];
  };

  pythonGenerator.forBlock['camera_set_fov'] = function (block) {
    const fov = block.getFieldValue('FOV');
    return `CoronaEngine.set_fov(${fov})\n`;
  };

  pythonGenerator.forBlock['camera_follow_object'] = function (block) {
    const name = pyString(block.getFieldValue('NAME'));
    const ox = block.getFieldValue('OX');
    const oy = block.getFieldValue('OY');
    const oz = block.getFieldValue('OZ');
    return `CoronaEngine.camera_follow_object(${name}, ${ox}, ${oy}, ${oz})\n`;
  };

  pythonGenerator.forBlock['camera_raycast'] = function (block) {
    return [`CoronaEngine.camera_raycast(${block.getFieldValue('MAX_DIST')})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['camera_raycast_object'] = function () {
    return ['CoronaEngine.camera_raycast_object()', pythonGenerator.ORDER_FUNCTION_CALL];
  };

  pythonGenerator.forBlock['camera_third_person_orbit'] = function (block) {
    const name = pyString(block.getFieldValue('NAME'));
    return `CoronaEngine.camera_third_person_orbit(${name}, ${block.getFieldValue('DISTANCE')}, ${block.getFieldValue('HEIGHT')}, ${block.getFieldValue('SENSITIVITY')})\n`;
  };

  pythonGenerator.forBlock['camera_first_person_follow'] = function (block) {
    return `CoronaEngine.camera_first_person_follow(${pyString(block.getFieldValue('NAME'))}, ${block.getFieldValue('HEIGHT')}, ${block.getFieldValue('SENSITIVITY')}, ${pyString(block.getFieldValue('WEAPON'))})\n`;
  };


};
