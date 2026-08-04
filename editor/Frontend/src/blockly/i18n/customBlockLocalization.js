import { translateUiText } from '@/i18n/domTranslator.js';

const installedBlocklyInstances = new WeakSet();

function translateDropdownOptions(options) {
  if (!Array.isArray(options)) return options;
  return options.map((option) => {
    if (!Array.isArray(option) || typeof option[0] !== 'string') return option;
    const label = translateUiText(option[0]);
    return label === option[0] ? option : [label, ...option.slice(1)];
  });
}

export function installCustomBlockLocalization(blocklyModule) {
  const Blockly = blocklyModule?.default || blocklyModule;
  if (!Blockly || installedBlocklyInstances.has(Blockly)) return;

  const inputPrototype = Blockly.Input?.prototype;
  if (inputPrototype?.appendField) {
    const appendField = inputPrototype.appendField;
    inputPrototype.appendField = function localizedAppendField(field, name) {
      const localizedField = typeof field === 'string' ? translateUiText(field) : field;
      return appendField.call(this, localizedField, name);
    };
  }

  const dropdownPrototype = Blockly.FieldDropdown?.prototype;
  if (dropdownPrototype?.getOptions) {
    const getOptions = dropdownPrototype.getOptions;
    dropdownPrototype.getOptions = function localizedGetOptions(useCache) {
      return translateDropdownOptions(getOptions.call(this, useCache));
    };
  }

  const blockPrototype = Blockly.Block?.prototype;
  if (blockPrototype?.setTooltip) {
    const setTooltip = blockPrototype.setTooltip;
    blockPrototype.setTooltip = function localizedSetTooltip(tooltip) {
      if (typeof tooltip === 'string') {
        return setTooltip.call(this, translateUiText(tooltip));
      }
      if (typeof tooltip === 'function') {
        return setTooltip.call(this, (...args) => translateUiText(tooltip.apply(this, args)));
      }
      return setTooltip.call(this, tooltip);
    };
  }

  installedBlocklyInstances.add(Blockly);
}
