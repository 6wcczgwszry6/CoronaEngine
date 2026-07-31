import { reactive } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';
import { closeFloatingPanel, openFloatingPanel } from '@/utils/panelWindows.js';
import { getPluginManifest } from '@/config/pluginManifest.js';

const PANEL_ZONES = Object.freeze({
  MainPage: 'center',
  SceneTools: 'right',
  SceneDatas: 'right',
  EditorSettings: 'right',
  // Keep node guidance in the main-page DOM so the highlight can target nodes,
  // ports and blocks without falling back to the legacy bottom dock.
  NodeGraphPanel: 'center',
});

const SELECTOR_KEYS = Object.freeze({
  'main-viewport': '[data-guidance="main-viewport"]',
  'scene-shortcut': '[data-guidance="scene-shortcut"]',
  'node-shortcut': '[data-guidance="node-shortcut"]',
  'scene-import-model': '[data-guidance="scene-import-model"]',
  'scene-actor-list': '[data-guidance="scene-actor-list"]',
  'scene-lighting': '[data-guidance="scene-lighting"]',
  'scene-light-x': '[data-guidance="scene-light-x"]',
  'preview-start': '[data-guidance="preview-start"]',
  'preview-stop': '[data-guidance="preview-stop"]',
  'settings-viewport': '[data-guidance="settings-viewport"]',
  'settings-viewport-ui': '[data-guidance="settings-viewport-ui"]',
  'settings-camera-speed': '[data-guidance="settings-camera-speed"]',
  'settings-grid': '[data-guidance="settings-grid"]',
  'object-transform': '[data-guidance="object-transform"]',
  'object-position-x': '[data-guidance="object-position-x"]',
  'object-rotation-y': '[data-guidance="object-rotation-y"]',
  'object-scale-x': '[data-guidance="object-scale-x"]',
  'object-physics': '[data-guidance="object-physics"]',
  'object-physics-enabled': '[data-guidance="object-physics-enabled"]',
  'object-physics-mass': '[data-guidance="object-physics-mass"]',
  'node-run': '[data-guidance="node-run"]',
  'node-toolbox': '[data-guidance="node-toolbox"]',
  'node-state-tool': '[data-guidance="node-state-tool"]',
  'node-type-custom': '[data-guidance="node-type-custom"]',
  'node-canvas': '[data-guidance="node-canvas"]',
  'node-blockly-editor': '[data-guidance="node-blockly-editor"]',
  'node-transition-condition': '[data-guidance="node-transition-condition"]',
});

const state = reactive({
  active: false,
  guidance: null,
  stepIndex: 0,
  targetRect: null,
  fromRect: null,
  preparing: false,
});

let restoreState = null;
let rectTimer = null;
let lifecycleToken = 0;
let exactTargetSeen = false;
let exactTargetMissingTicks = 0;
let exactTargetPrepareTicks = 0;
let lifecycleGuardsAttached = false;

function safeId(value) {
  return String(value || '').replace(/["\\]/g, '\\$&');
}

function clonePanelState(panel) {
  return panel ? {
    open: Boolean(panel.open),
    mode: String(panel.mode || 'docked'),
    dockZone: String(panel.dockZone || ''),
    order: Number(panel.order) || 0,
    width: Number(panel.width) || 0,
    height: Number(panel.height) || 0,
  } : null;
}

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function targetSelector(target = {}) {
  if (target.kind === 'selector' || target.kind === 'region') {
    return SELECTOR_KEYS[String(target.selectorKey || '')] || '';
  }
  if (target.kind === 'actor' && target.actorName) return `[data-actor-name="${safeId(target.actorName)}"]`;
  if (target.kind === 'node' && target.nodeId) return `[data-node-id="${safeId(target.nodeId)}"]`;
  if (target.kind === 'edge' && target.edgeId) return `[data-edge-id="${safeId(target.edgeId)}"]`;
  if (target.kind === 'block-type' && target.blockType) return `[data-block-type="${safeId(target.blockType)}"]`;
  if (target.kind === 'port' && target.nodeId) {
    const side = target.portSide ? `[data-port-side="${safeId(target.portSide)}"]` : '';
    const index = Number.isFinite(Number(target.portIndex))
      ? `[data-port-index="${safeId(target.portIndex)}"]`
      : '';
    return `[data-node-id="${safeId(target.nodeId)}"]${side}${index}`;
  }
  if (target.kind === 'block' && target.blockId) return `[data-block-id="${safeId(target.blockId)}"]`;
  return '';
}

function fallbackSelector(target = {}) {
  if (target.kind === 'actor') return SELECTOR_KEYS['scene-actor-list'];
  if (['node', 'edge', 'port'].includes(target.kind)) return SELECTOR_KEYS['node-canvas'];
  if (['block', 'block-type'].includes(target.kind)) return SELECTOR_KEYS['node-blockly-editor'];
  return '';
}

function elementForTarget(target = {}, { allowFallback = true } = {}) {
  const selector = targetSelector(target);
  let element = selector ? document.querySelector(selector) : null;
  if (!element && allowFallback) {
    const fallback = fallbackSelector(target);
    element = fallback ? document.querySelector(fallback) : null;
  }
  return element;
}

function rectForTarget(target = {}) {
  const element = elementForTarget(target);
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return null;
  return {
    left: Math.max(6, rect.left),
    top: Math.max(6, rect.top),
    width: Math.max(20, Math.min(rect.width, window.innerWidth - Math.max(6, rect.left) - 6)),
    height: Math.max(20, Math.min(rect.height, window.innerHeight - Math.max(6, rect.top) - 6)),
  };
}

function currentStep() {
  return state.guidance?.steps?.[state.stepIndex] || null;
}

function exactElementForTarget(target = {}) {
  return elementForTarget(target, { allowFallback: false });
}

function revealTarget(target = {}) {
  const element = elementForTarget(target);
  if (!element || typeof element.scrollIntoView !== 'function') return;
  const rect = element.getBoundingClientRect();
  const outsideViewport = rect.top < 8
    || rect.left < 8
    || rect.bottom > window.innerHeight - 8
    || rect.right > window.innerWidth - 8;
  if (outsideViewport) {
    element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
  }
}

function refreshRects() {
  if (!state.active) return;
  const panelId = state.guidance?.panelId;
  if (panelId !== 'MainPage') {
    const dockStore = useDockStore();
    const panel = dockStore.panels[panelId];
    if (!panel?.open || panel.mode !== 'docked') {
      void stop({ restorePanelState: false });
      return;
    }
  }

  const step = currentStep();
  const target = step?.target || {};
  const exactElement = exactElementForTarget(target);
  if (exactElement) {
    exactTargetSeen = true;
    exactTargetMissingTicks = 0;
    exactTargetPrepareTicks = 0;
  } else if (exactTargetSeen && ['node', 'block', 'edge', 'port'].includes(target.kind)) {
    exactTargetMissingTicks += 1;
    if (exactTargetMissingTicks >= 3) {
      void stop();
      return;
    }
  } else if (['node', 'block', 'edge', 'port'].includes(target.kind)) {
    exactTargetPrepareTicks += 1;
    if (exactTargetPrepareTicks <= 10 && exactTargetPrepareTicks % 3 === 1) {
      window.dispatchEvent(new CustomEvent('cabbage-guidance-prepare', {
        detail: {
          panelId: state.guidance?.panelId,
          selectorKey: String(target.selectorKey || ''),
          nodeId: String(target.nodeId || ''),
          blockId: String(target.blockId || ''),
          edgeId: String(target.edgeId || ''),
          portSide: String(target.portSide || ''),
          portIndex: Number.isFinite(Number(target.portIndex)) ? Number(target.portIndex) : null,
        },
      }));
    }
  }
  state.targetRect = rectForTarget(target);
  state.fromRect = rectForTarget(step?.fromTarget || {});
}

function startRectTracking() {
  stopRectTracking();
  refreshRects();
  rectTimer = window.setInterval(refreshRects, 180);
}

function stopRectTracking() {
  if (rectTimer) window.clearInterval(rectTimer);
  rectTimer = null;
}

async function ensurePanel(panelId, selectorKey = '') {
  if (!panelId) return false;
  if (panelId === 'MainPage') {
    restoreState = null;
    window.dispatchEvent(new CustomEvent('cabbage-guidance-prepare', {
      detail: { panelId, selectorKey },
    }));
    await wait(80);
    const selector = SELECTOR_KEYS[String(selectorKey || '')] || '';
    return selector ? Boolean(document.querySelector(selector)) : true;
  }
  const dockStore = useDockStore();
  const panel = dockStore.panels[panelId];
  if (!panel) return false;
  restoreState = restoreState || { panelId, panel: clonePanelState(panel) };

  if (panel.open && panel.mode === 'external') await closeFloatingPanel(dockStore, panelId);
  dockStore.popIn(panelId);
  dockStore.setDockZone(panelId, PANEL_ZONES[panelId] || panel.dockZone || 'right');

  if (panelId === 'NodeGraphPanel') {
    const manifest = getPluginManifest(panelId);
    const width = Number(manifest?.defaultFloatWidth || manifest?.defaultWidth || panel.width);
    const height = Number(manifest?.defaultFloatHeight || manifest?.defaultHeight || panel.height);
    dockStore.resizePanel(panelId, width, height);
  }

  dockStore.openPanel(panelId);
  window.dispatchEvent(new CustomEvent('cabbage-guidance-prepare', {
    detail: { panelId, selectorKey },
  }));
  window.dispatchEvent(new Event('resize'));
  await wait(panelId === 'NodeGraphPanel' ? 260 : 180);
  return Boolean(dockStore.panels[panelId]?.open && dockStore.panels[panelId]?.mode === 'docked');
}

async function restorePanel() {
  const saved = restoreState;
  restoreState = null;
  if (!saved?.panel) return;
  const dockStore = useDockStore();
  const panel = dockStore.panels[saved.panelId];
  if (!panel) return;

  panel.dockZone = saved.panel.dockZone || panel.dockZone;
  panel.order = saved.panel.order;
  if (saved.panel.width) panel.width = saved.panel.width;
  if (saved.panel.height) panel.height = saved.panel.height;

  if (!saved.panel.open) {
    dockStore.closePanel(saved.panelId);
  } else if (saved.panel.mode === 'external') {
    dockStore.closePanel(saved.panelId);
    await openFloatingPanel(dockStore, saved.panelId);
  } else {
    dockStore.popIn(saved.panelId);
    dockStore.openPanel(saved.panelId);
  }
  window.dispatchEvent(new Event('resize'));
}

function stepFor(selectorKey, action, text, extra = {}) {
  return {
    target: { kind: 'selector', selectorKey },
    action,
    text,
    ...extra,
  };
}

const LEGACY_TUTORIAL_GUIDANCE = Object.freeze({
  'tutorial.import_model': {
    panelId: 'SceneTools',
    steps: [stepFor('scene-import-model', 'click', '打开场景管理中的导入入口，再选择要导入的模型。')],
  },
  'tutorial.transform_model': {
    panelId: 'SceneDatas',
    steps: [stepFor('object-transform', 'drag', '展开“变换”，修改位置、旋转或缩放中的任意一个参数。')],
  },
  'tutorial.adjust_lighting': {
    panelId: 'MainPage',
    steps: [stepFor('scene-lighting', 'click', '在页面左上角切换光照，或修改光照方向的任意轴。')],
  },
  'tutorial.adjust_physics': {
    panelId: 'SceneDatas',
    steps: [stepFor('object-physics', 'click', '展开“物理”，启用物理或修改质量、弹性、阻尼和锁轴。')],
  },
  'tutorial.create_node': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-canvas', 'drag', '把左侧的状态节点拖到节点编辑区。', {
      fromTarget: { kind: 'selector', selectorKey: 'node-toolbox' },
    })],
  },
  'tutorial.move_node': {
    panelId: 'NodeGraphPanel',
    steps: [{ target: { kind: 'node' }, action: 'drag', text: '按住任意节点并拖到新的位置。' }],
  },
  'tutorial.connect_nodes': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-canvas', 'connect', '从一个节点的输出端口拖向另一个节点的输入端口。')],
  },
  'tutorial.drag_block': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-blockly-editor', 'drag', '先选中节点，再把左侧微观积木拖入节点内部编辑区。', {
      fromTarget: { kind: 'selector', selectorKey: 'node-toolbox' },
    })],
  },
  'tutorial.edit_block_parameter': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-blockly-editor', 'click', '选中节点内部的积木，然后修改它的下拉项、数值或文本参数。')],
  },
  'tutorial.set_transition_condition': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-transition-condition', 'connect', '选中一条连线，在条件编辑区接入一个返回 Boolean 的条件积木。')],
  },
  'tutorial.run_node_graph': {
    panelId: 'NodeGraphPanel',
    steps: [stepFor('node-run', 'click', '点击节点 Dock 顶部的“运行”按钮。展示不会真的启动逻辑。')],
  },
});


function taskGuidanceText(source, fallback) {
  return String(source?.guidanceText || source?.suggestion || source?.completionCriteria || source?.message || fallback || '');
}

function targetFromBinding(bindings, key, fallback) {
  const value = String(bindings?.[key] || '');
  if (!value) return fallback;
  if (key === 'modelActorName') return { kind: 'actor', actorName: value };
  if (key === 'edgeId') return { kind: 'edge', edgeId: value };
  if (key.endsWith('BlockId')) return { kind: 'block', blockId: value };
  return { kind: 'node', nodeId: value };
}

function tutorialStep(source, target, action, fallback, extra = {}) {
  const text = taskGuidanceText(source, fallback);
  return { target, action, text, textEn: text, ...extra };
}

function basicGuidance(panelId, target, action, fallback, extra = {}) {
  return (source) => ({ panelId, steps: [tutorialStep(source, target, action, fallback, extra)] });
}

const BASICS_TUTORIAL_GUIDANCE = Object.freeze({
  focus_viewport: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'click', 'Click the 3D viewport once.'),
  move_camera_forward_back: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'key', 'Focus the viewport, then press W or S until the camera moves.'),
  move_camera_left_right: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'key', 'Focus the viewport, then press A or D until the camera moves.'),
  move_camera_up_down: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'key', 'Focus the viewport, then press Q or E until the camera moves.'),
  rotate_camera: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'drag', 'Hold the right mouse button in the viewport and drag until the camera rotates.'),
  move_camera_wheel: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'main-viewport' }, 'wheel', 'Scroll the mouse wheel over the viewport until the camera moves.'),
  open_scene_manager: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'scene-shortcut' }, 'click', 'Click the Scene Manager shortcut yourself.'),
  import_model: basicGuidance('SceneTools', { kind: 'selector', selectorKey: 'scene-import-model' }, 'click', 'Import a model and wait for it to appear in the scene.'),
  select_model: (source) => ({ panelId: 'SceneTools', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'modelActorName', { kind: 'selector', selectorKey: 'scene-actor-list' }),
    'click',
    'Select the tutorial model in the scene tree or viewport.'
  )] }),
  set_position_x: basicGuidance('SceneDatas', { kind: 'selector', selectorKey: 'object-position-x' }, 'input', 'Set Position X to 1.'),
  set_rotation_y: basicGuidance('SceneDatas', { kind: 'selector', selectorKey: 'object-rotation-y' }, 'input', 'Set Rotation Y to 45.'),
  set_scale_x: basicGuidance('SceneDatas', { kind: 'selector', selectorKey: 'object-scale-x' }, 'input', 'Set Scale X to 1.5.'),
  enable_physics: basicGuidance('SceneDatas', { kind: 'selector', selectorKey: 'object-physics-enabled' }, 'click', 'Enable Physics Simulation.'),
  set_mass: basicGuidance('SceneDatas', { kind: 'selector', selectorKey: 'object-physics-mass' }, 'input', 'Set Mass to 10.'),
  set_light_x: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'scene-light-x' }, 'input', 'Set Scene Lighting Direction X to 0.5.'),
  open_nodes: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'node-shortcut' }, 'click', 'Click the Nodes shortcut yourself.'),
  confirm_start_node: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'startNodeId', { kind: 'selector', selectorKey: 'node-state-tool' }),
    'click',
    'Click the existing start node, or drag in a State Node if none exists.'
  )] }),
  create_custom_node: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    { kind: 'selector', selectorKey: 'node-canvas' },
    'drag',
    'Drag the State Node tool into the node canvas.',
    { fromTarget: { kind: 'selector', selectorKey: 'node-state-tool' } }
  )] }),
  move_custom_node: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'customNodeId', { kind: 'selector', selectorKey: 'node-canvas' }),
    'drag',
    'Drag the tutorial custom node to a new position.'
  )] }),
  connect_nodes: (source) => {
    const startNodeId = String(source.bindings?.startNodeId || '');
    const customNodeId = String(source.bindings?.customNodeId || '');
    const target = startNodeId && customNodeId
      ? { kind: 'port', nodeId: customNodeId, portSide: 'input', portIndex: 0 }
      : { kind: 'selector', selectorKey: 'node-canvas' };
    const extra = startNodeId && customNodeId
      ? { fromTarget: { kind: 'port', nodeId: startNodeId, portSide: 'output', portIndex: 0 } }
      : {};
    return { panelId: 'NodeGraphPanel', steps: [tutorialStep(source, target, 'connect', 'Connect the start node output to the custom node input.', extra)] };
  },
  open_custom_node: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'customNodeId', { kind: 'selector', selectorKey: 'node-canvas' }),
    'click',
    'Click the tutorial custom node to open its internal block editor.'
  )] }),
  add_when_enter: basicGuidance('NodeGraphPanel', { kind: 'block-type', blockType: 'node_when_enter' }, 'drag', 'Drag node_when_enter into the custom node workspace.'),
  add_wait: basicGuidance('NodeGraphPanel', { kind: 'block-type', blockType: 'control_wait' }, 'drag', 'Drag control_wait below node_when_enter and connect it.'),
  set_wait_seconds: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'waitBlockId', { kind: 'selector', selectorKey: 'node-blockly-editor' }),
    'input',
    'Set the Wait block SECONDS field to 2.'
  )] }),
  select_edge: (source) => ({ panelId: 'NodeGraphPanel', steps: [tutorialStep(
    source,
    targetFromBinding(source.bindings, 'edgeId', { kind: 'selector', selectorKey: 'node-canvas' }),
    'click',
    'Click the edge between the start and custom nodes.'
  )] }),
  add_true_condition: basicGuidance('NodeGraphPanel', { kind: 'block-type', blockType: 'logic_boolean' }, 'drag', 'Drag logic_boolean into the condition workspace and set it to TRUE.'),
  run_node_graph: basicGuidance('NodeGraphPanel', { kind: 'selector', selectorKey: 'node-run' }, 'click', 'Click Run and wait for run_succeeded.'),
  start_preview: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'preview-start' }, 'click', 'Click Start Preview and wait for running.'),
  stop_preview: basicGuidance('MainPage', { kind: 'selector', selectorKey: 'preview-stop' }, 'click', 'Click Stop Preview and wait for the scene to restore.'),
});

const ISSUE_GUIDANCE = Object.freeze({
  missing_actor_target: { selectorKey: 'node-blockly-editor', action: 'connect', text: '定位到对应操作积木，把“对象[]”积木接到对象输入口并选择场景中的目标物体。' },
  actor_target_not_found: { selectorKey: 'node-blockly-editor', action: 'click', text: '定位到对象引用积木，改为当前场景中真实存在的物体。' },
  start_node_count: { selectorKey: 'node-canvas', action: 'focus', text: '检查节点编辑区，只保留一个开始节点，并让它连接到首个逻辑节点。' },
  invalid_edge_endpoint: { selectorKey: 'node-canvas', action: 'connect', text: '重新连接这条连线，确保起点和终点都连接到有效节点端口。' },
  invalid_visible_condition_count: { selectorKey: 'node-transition-condition', action: 'connect', text: '选中对应连线，只保留一个完整的条件表达式。' },
  non_boolean_condition: { selectorKey: 'node-transition-condition', action: 'connect', text: '把连线条件改为返回 Boolean 的判断积木。' },
  unknown_block_type: { selectorKey: 'node-blockly-editor', action: 'click', text: '删除当前不支持的积木，并从左侧工具箱换成已有积木。' },
  missing_required_input: { selectorKey: 'node-blockly-editor', action: 'connect', text: '给积木缺失的关键输入口连接匹配类型的积木。' },
});

const CHAT_GUIDANCE = Object.freeze({
  connect_object_reference: ISSUE_GUIDANCE.missing_actor_target,
  select_existing_object: ISSUE_GUIDANCE.actor_target_not_found,
  create_node: LEGACY_TUTORIAL_GUIDANCE['tutorial.create_node'].steps[0],
  move_node: LEGACY_TUTORIAL_GUIDANCE['tutorial.move_node'].steps[0],
  connect_nodes: LEGACY_TUTORIAL_GUIDANCE['tutorial.connect_nodes'].steps[0],
  drag_block: LEGACY_TUTORIAL_GUIDANCE['tutorial.drag_block'].steps[0],
  edit_block_parameter: LEGACY_TUTORIAL_GUIDANCE['tutorial.edit_block_parameter'].steps[0],
  set_transition_condition: LEGACY_TUTORIAL_GUIDANCE['tutorial.set_transition_condition'].steps[0],
  run_node_graph: LEGACY_TUTORIAL_GUIDANCE['tutorial.run_node_graph'].steps[0],
  import_model: LEGACY_TUTORIAL_GUIDANCE['tutorial.import_model'].steps[0],
  transform_model: LEGACY_TUTORIAL_GUIDANCE['tutorial.transform_model'].steps[0],
  adjust_lighting: LEGACY_TUTORIAL_GUIDANCE['tutorial.adjust_lighting'].steps[0],
  adjust_physics: LEGACY_TUTORIAL_GUIDANCE['tutorial.adjust_physics'].steps[0],
});

function guidanceForTask(source = {}) {
  if (source.type === 'goal') {
    const intent = String(source.guidanceIntent || '');
    const template = CHAT_GUIDANCE[intent];
    if (!template) return null;
    const panelId = intent === 'adjust_lighting'
      ? 'MainPage'
      : intent === 'import_model'
        ? 'SceneTools'
      : ['transform_model', 'adjust_physics'].includes(intent)
        ? 'SceneDatas'
        : 'NodeGraphPanel';
    return { panelId, steps: [{ ...template }] };
  }
  const intent = String(source.guidanceIntent || '');
  const basicsFactory = BASICS_TUTORIAL_GUIDANCE[intent];
  if (basicsFactory) return basicsFactory(source);
  const taskKey = String(source.taskKey || source.issueKey || '');
  const tutorial = LEGACY_TUTORIAL_GUIDANCE[taskKey];
  if (tutorial) return { ...tutorial, steps: tutorial.steps.map((step) => ({ ...step })) };

  const issue = ISSUE_GUIDANCE[String(source.code || '')] || ISSUE_GUIDANCE.missing_required_input;
  const preciseTarget = source.blockId
    ? { kind: 'block', blockId: String(source.blockId) }
    : source.nodeId
      ? { kind: 'node', nodeId: String(source.nodeId) }
      : source.edgeId
        ? { kind: 'edge', edgeId: String(source.edgeId) }
        : { kind: 'selector', selectorKey: issue.selectorKey };
  return {
    panelId: 'NodeGraphPanel',
    steps: [{ target: preciseTarget, action: issue.action, text: issue.text }],
  };
}

function panelIdForTarget(target = {}) {
  const selectorKey = String(target.selectorKey || '');
  if (['main-viewport', 'scene-shortcut', 'node-shortcut', 'scene-lighting', 'scene-light-x', 'preview-start', 'preview-stop'].includes(selectorKey)) return 'MainPage';
  if (selectorKey.startsWith('scene-')) return 'SceneTools';
  if (selectorKey.startsWith('settings-')) return 'EditorSettings';
  if (selectorKey.startsWith('object-')) return 'SceneDatas';
  if (selectorKey.startsWith('node-')) return 'NodeGraphPanel';
  if (target.kind === 'actor') return 'SceneTools';
  if (['node', 'block', 'block-type', 'edge', 'port'].includes(String(target.kind || ''))) {
    return 'NodeGraphPanel';
  }
  return '';
}

function normalizeGuidanceStep(step = {}) {
  return {
    ...step,
    target: step?.target ? { ...step.target } : {},
    ...(step?.fromTarget ? { fromTarget: { ...step.fromTarget } } : {}),
  };
}

function normalizeGuidance(source, sourceType, resolved) {
  const steps = (resolved?.steps || []).map(normalizeGuidanceStep);
  if (!steps.length) return null;
  const inferredPanelId = steps
    .map((step) => panelIdForTarget(step.target) || panelIdForTarget(step.fromTarget))
    .find(Boolean);
  const panelId = inferredPanelId || String(resolved?.panelId || source?.panelId || '');
  if (!PANEL_ZONES[panelId]) return null;
  return {
    guidanceId: String(source.guidanceId || source.taskKey || source.issueKey || source.tipKey || source.id || `guidance_${Date.now()}`),
    sourceType,
    title: String(source.title || '\u64cd\u4f5c\u5c55\u793a'),
    panelId,
    steps,
  };
}

export const guidanceRegistry = {
  resolve(source = {}) {
    const sourceType = String(source.sourceType || source.type || 'node-issue');
    if (source?.steps && Array.isArray(source.steps)) {
      // Persisted worlds may contain legacy panelId/dockZone values. Re-infer the
      // current panel from the target so old data cannot reopen the old layout.
      return normalizeGuidance(source, sourceType, source);
    }
    let resolved;
    if (sourceType === 'chat') {
      const template = CHAT_GUIDANCE[String(source.guidanceIntent || '')];
      if (!template) return null;
      const panelId = String(source.panelId || (
        source.guidanceIntent === 'adjust_lighting' ? 'MainPage'
          : source.guidanceIntent === 'import_model' ? 'SceneTools'
          : ['transform_model', 'adjust_physics'].includes(source.guidanceIntent) ? 'SceneDatas'
            : 'NodeGraphPanel'
      ));
      resolved = { panelId, steps: [{ ...template }] };
    } else if (sourceType === 'optimization-tip') {
      resolved = { panelId: 'NodeGraphPanel', steps: [stepFor('node-canvas', 'focus', source.message || '\u67e5\u770b\u5f53\u524d\u8282\u70b9\u56fe\u4e2d\u53ef\u4ee5\u4f18\u5316\u7684\u63a7\u5236\u6d41\u3002')] };
    } else {
      resolved = guidanceForTask(source);
    }
    return normalizeGuidance(source, sourceType, resolved);
  },
};

async function showStep(index) {
  if (!state.guidance?.steps?.length) return;
  state.stepIndex = Math.max(0, Math.min(index, state.guidance.steps.length - 1));
  exactTargetSeen = false;
  exactTargetMissingTicks = 0;
  exactTargetPrepareTicks = 0;
  const step = currentStep();
  window.dispatchEvent(new CustomEvent('cabbage-guidance-prepare', {
    detail: {
      panelId: state.guidance.panelId,
      selectorKey: String(step?.target?.selectorKey || ''),
      nodeId: String(step?.target?.nodeId || ''),
      blockId: String(step?.target?.blockId || ''),
      blockType: String(step?.target?.blockType || ''),
      edgeId: String(step?.target?.edgeId || ''),
      portSide: String(step?.target?.portSide || ''),
      portIndex: Number.isFinite(Number(step?.target?.portIndex)) ? Number(step.target.portIndex) : null,
    },
  }));
  await wait(80);
  revealTarget(step?.target || {});
  await wait(120);
  refreshRects();
}

function handleProjectChanged() {
  if (state.active || state.preparing) void stop({ restorePanelState: false });
}

function handlePageUnload() {
  stopRectTracking();
  restoreState = null;
  state.active = false;
  state.preparing = false;
}

function attachLifecycleGuards() {
  if (lifecycleGuardsAttached) return;
  lifecycleGuardsAttached = true;
  window.addEventListener('corona-active-project-changed', handleProjectChanged);
  window.addEventListener('beforeunload', handlePageUnload);
}

function detachLifecycleGuards() {
  if (!lifecycleGuardsAttached) return;
  lifecycleGuardsAttached = false;
  window.removeEventListener('corona-active-project-changed', handleProjectChanged);
  window.removeEventListener('beforeunload', handlePageUnload);
}

async function start(source) {
  const guidance = guidanceRegistry.resolve(source);
  if (!guidance) return false;
  if (state.active || state.preparing) await stop();
  const token = ++lifecycleToken;
  state.preparing = true;
  attachLifecycleGuards();
  const panelReady = await ensurePanel(guidance.panelId, guidance.steps[0]?.target?.selectorKey || '');
  if (token !== lifecycleToken || !panelReady) {
    if (token === lifecycleToken) await stop({ restorePanelState: false });
    return false;
  }
  state.guidance = guidance;
  state.stepIndex = 0;
  state.active = true;
  state.preparing = false;
  await showStep(0);
  if (token !== lifecycleToken) return false;
  startRectTracking();
  return true;
}

async function stop({ restorePanelState = true } = {}) {
  ++lifecycleToken;
  stopRectTracking();
  state.active = false;
  state.guidance = null;
  state.stepIndex = 0;
  state.targetRect = null;
  state.fromRect = null;
  state.preparing = false;
  exactTargetSeen = false;
  exactTargetMissingTicks = 0;
  exactTargetPrepareTicks = 0;
  detachLifecycleGuards();
  if (restorePanelState) await restorePanel();
  else restoreState = null;
}

function next() {
  if (!state.active) return;
  if (state.stepIndex >= state.guidance.steps.length - 1) {
    void stop();
    return;
  }
  void showStep(state.stepIndex + 1);
}

function previous() {
  if (!state.active || state.stepIndex <= 0) return;
  void showStep(state.stepIndex - 1);
}

export const guidanceService = {
  state,
  start,
  next,
  previous,
  stop,
  refreshTarget: refreshRects,
};
