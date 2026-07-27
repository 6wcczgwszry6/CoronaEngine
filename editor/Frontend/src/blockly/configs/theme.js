import * as Blockly from 'blockly/core';

// ── 辅助：自动生成 secondary / tertiary（比主色暗 30% / 50%）──
function darker(hex, pct) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.round(((num >> 16) & 0xff) * (1 - pct));
  const g = Math.round(((num >> 8) & 0xff) * (1 - pct));
  const b = Math.round((num & 0xff) * (1 - pct));
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// ── 统一定义：每种分类色同时用于 blockStyle 和 categoryStyle ──
const COLOURS = {
  engine:     '#C49A45',
  motion:     '#D0AA59',
  physics:    '#9B7A38',
  condition:  '#D8B86C',
  gameplay:   '#B7791F',
  camera:     '#A9823F',
  appearance: '#C3A059',
  event:      '#A86E24',
  control:    '#E0B85B',
  detect:     '#AA8A4A',
  math:       '#D0A84B',
  variable:   '#A76E2E',
  list:       '#8E622C',
  text:       '#B39452',
  function:   '#9C7740',
  audio:      '#B07A48',
  object:     '#C6A14D',
  ui:         '#956B34',
};

// 生成标准格式的 blockStyle
function bs(hex) {
  return {
    colourPrimary: hex,
    colourSecondary: darker(hex, 0.3),
    colourTertiary: darker(hex, 0.5),
  };
}

export const CoronaTheme = Blockly.Theme.defineTheme('CoronaTheme', {
  base: Blockly.Themes.Classic,

  // Blockly v13 componentStyles：支持 CSS 变量驱动的组件样式（上游 #8274）
  // 深色主题配色，适配 CabbageEditor 整体暗色 UI
  componentStyles: {
    workspaceBackgroundColour: '#0f0e0a',
    toolboxBackgroundColour: '#15130d',
    toolboxForegroundColour: '#f2ead5',
    flyoutBackgroundColour: '#191711',
    flyoutForegroundColour: '#e9dfc5',
    flyoutOpacity: 1,
    scrollbarColour: '#8c6f36',
    scrollbarOpacity: 0.4,
    insertionMarkerColour: '#e5c77f',
    insertionMarkerOpacity: 0.15,
    cursorColour: '#e5c77f',
    blackoutColour: 'rgba(0, 0, 0, .7)',
    // v13 CSS 变量兼容：为未来版本预留的自定义属性
    selectedGlowColour: '#d8b86c',
    selectedGlowOpacity: 0.4,
    replacementGlowColour: '#fff3c8',
    replacementGlowOpacity: 0.3,
  },

  // ── 积木块样式（blockStyles）──
  // 每个 blockStyle 的 colourPrimary 都与其对应 categoryStyle 的 colour 一致
  blockStyles: {
    // ── CoronaEngine 自定义分类 ──
    engine_blocks:     bs(COLOURS.engine),
    motion_blocks:     bs(COLOURS.motion),
    physics_blocks:    bs(COLOURS.physics),
    condition_blocks:  bs(COLOURS.condition),
    gameplay_blocks:   bs(COLOURS.gameplay),
    camera_blocks:     bs(COLOURS.camera),
    appearance_blocks: bs(COLOURS.appearance),
    event_blocks:      bs(COLOURS.event),
    control_blocks:    bs(COLOURS.control),
    detect_blocks:     bs(COLOURS.detect),
    math_blocks:       bs(COLOURS.math),
    variable_blocks:   bs(COLOURS.variable),
    list_blocks:       bs(COLOURS.list),
    text_blocks:       bs(COLOURS.text),
    procedure_blocks:  bs(COLOURS.function),
    audio_blocks:      bs(COLOURS.audio),
    object_blocks:     bs(COLOURS.object),
    ui_blocks:         bs(COLOURS.ui),

    // ── 覆盖标准样式 → 归入对应分类颜色 ──
    logic_blocks:             bs(COLOURS.condition),
    loop_blocks:              bs(COLOURS.control),
    variable_dynamic_blocks:  bs(COLOURS.variable),
    colour_blocks:            bs('#9b7845'),
    hat_blocks:               bs('#665025'),
  },

  // ── 工具箱分类样式（categoryStyles）──
  categoryStyles: {
    engine_category:     { colour: COLOURS.engine },
    motion_category:     { colour: COLOURS.motion },
    physics_category:    { colour: COLOURS.physics },
    condition_category:  { colour: COLOURS.condition },
    gameplay_category:   { colour: COLOURS.gameplay },
    camera_category:     { colour: COLOURS.camera },
    appearance_category: { colour: COLOURS.appearance },
    event_category:      { colour: COLOURS.event },
    control_category:    { colour: COLOURS.control },
    detect_category:     { colour: COLOURS.detect },
    math_category:       { colour: COLOURS.math },
    variable_category:   { colour: COLOURS.variable },
    list_category:       { colour: COLOURS.list },
    text_category:       { colour: COLOURS.text },
    function_category:   { colour: COLOURS.function },
    audio_category:      { colour: COLOURS.audio },
    object_category:     { colour: COLOURS.object },
    ui_category:         { colour: COLOURS.ui },
  },

  fontStyle: {
    family: '"Microsoft YaHei", sans-serif',
    weight: 'normal',
    size: 12,
  },
});
