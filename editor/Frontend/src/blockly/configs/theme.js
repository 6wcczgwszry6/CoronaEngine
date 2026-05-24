import * as Blockly from 'blockly/core';

export const CoronaTheme = Blockly.Theme.defineTheme('CoronaTheme', {
  base: Blockly.Themes.Dark,

  componentStyles: {
    workspaceBackgroundColour: '#1e1e1e',
    toolboxBackgroundColour: '#252526',
    toolboxForegroundColour: '#ffffff',
    flyoutBackgroundColour: '#252526',
    flyoutForegroundColour: '#cccccc',
    flyoutOpacity: 1,
    scrollbarColour: '#797979',
    insertionMarkerColour: '#ffffff',
    insertionMarkerOpacity: 0,
    scrollbarOpacity: 0.4,
    cursorColour: '#d0d0d0',
    blackoutColour: 'rgba(0, 0, 0, .7)',
  },

  categoryStyles: {
    engine_category: {
      colour: '#5631E4',
    },
    appearance_category: {
      colour: '#C501F6',
    },
    event_category: {
      colour: '#FFDE59',
    },
    control_category: {
      colour: '#FFAB19',
    },
    detect_category: {
      colour: '#4CBFE6',
    },
    math_category: {
      colour: '#59C059',
    },
    variable_category: {
      colour: '#FF8C1A',
    },
    list_category: {
      colour: '#FF661A',
    },
  },
  fontStyle: {
    family: '"Microsoft YaHei", sans-serif',
    weight: 'normal',
    size: 12,
  },
});
