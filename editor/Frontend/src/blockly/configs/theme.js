import * as Blockly from 'blockly/core';

// Colour helpers: keep Zelos edges distinct without making connected blocks look muddy.
function darker(hex, pct) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.round(((num >> 16) & 0xff) * (1 - pct));
  const g = Math.round(((num >> 8) & 0xff) * (1 - pct));
  const b = Math.round((num & 0xff) * (1 - pct));
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// Semantic palette: the editor shell remains black/gold, while blocks use muted
// category colours so events, control flow, data, objects and physics stay readable.
const COLOURS = {
  engine:     '#5668AD', // indigo
  motion:     '#426AA1', // blue
  physics:    '#3C7552', // green
  condition:  '#32776E', // teal
  gameplay:   '#8F5F29', // copper
  camera:     '#496D97', // slate blue
  appearance: '#845A9B', // purple
  event:      '#965B32', // orange
  control:    '#8C742F', // amber
  detect:     '#38748A', // cyan blue
  math:       '#367467', // deep teal
  variable:   '#9B533D', // coral
  list:       '#9F5745', // brick
  text:       '#427753', // grass green
  function:   '#8C5892', // magenta purple
  audio:      '#A65778', // rose
  object:     '#34766E', // blue green
  ui:         '#9E574B', // warm red
};

function bs(hex) {
  return {
    colourPrimary: hex,
    colourSecondary: darker(hex, 0.18),
    colourTertiary: darker(hex, 0.32),
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
    colour_blocks:            bs('#6D5D85'),
    hat_blocks:               bs(COLOURS.event),
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
    size: 13,
  },
});
