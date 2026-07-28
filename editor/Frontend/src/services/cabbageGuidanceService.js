import { reactive } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';
import { closeFloatingPanel, openFloatingPanel } from '@/utils/panelWindows.js';

const PANEL_ZONES = Object.freeze({
  SceneTools: 'left',
  SceneDatas: 'left',
  NodeGraphPanel: 'bottom',
});

const SELECTOR_KEYS = Object.freeze({
  'scene-import-model': '[data-guidance="scene-import-model"]',
  'scene-lighting': '[data-guidance="scene-lighting"]',
  'object-transform': '[data-guidance="object-transform"]',
  'object-physics': '[data-guidance="object-physics"]',
  'node-run': '[data-guidance="node-run"]',
  'node-toolbox': '[data-guidance="node-toolbox"]',
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
  if (target.kind === 'node' && target.nodeId) return `[data-node-id="${safeId(target.nodeId)}"]`;
  if (target.kind === 'edge' && target.edgeId) return `[data-edge-id="${safeId(target.edgeId)}"]`;
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
  if (['node', 'edge', 'port'].includes(target.kind)) return SELECTOR_KEYS['node-canvas'];
  if (target.kind === 'block') return SELECTOR_KEYS['node-blockly-editor'];
  return '';
}

function rectForTarget(target = {}) {
  const selector = targetSelector(target);
  let element = selector ? document.querySelector(selector) : null;
  if (!element) {
    const fallback = fallbackSelector(target);
    element = fallback ? document.querySelector(fallback) : null;
  }
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
  const selector = targetSelector(target);
  return selector ? document.querySelector(selector) : null;
}

function refreshRects() {
  if (!state.active) return;
  const dockStore = useDockStore();
  const panel = dockStore.panels[state.guidance?.panelId];
  if (!panel?.open || panel.mode !== 'docked') {
    void stop({ restorePanelState: false });
    return;
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
  const dockStore = useDockStore();
  const panel = dockStore.panels[panelId];
  if (!panel) return false;
  restoreState = restoreState || { panelId, panel: clonePanelState(panel) };

  if (panel.open && panel.mode === 'external') await closeFloatingPanel(dockStore, panelId);
  dockStore.popIn(panelId);
  dockStore.setDockZone(panelId, PANEL_ZONES[panelId] || panel.dockZone || 'right');
  dockStore.openPanel(panelId);
  window.dispatchEvent(new CustomEvent('cabbage-guidance-prepare', {
    detail: { panelId, selectorKey },
  }));
  window.dispatchEvent(new Event('resize'));
  await wait(180);
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

const TUTORIAL_GUIDANCE = Object.freeze({
  'tutorial.import_model': {
    panelId: 'SceneTools',
    steps: [stepFor('scene-import-model', 'click', '打开场景管理中的导入入口，再选择要导入的模型。')],
  },
  'tutorial.transform_model': {
    panelId: 'SceneDatas',
    steps: [stepFor('object-transform', 'drag', '展开“变换”，修改位置、旋转或缩放中的任意一个参数。')],
  },
  'tutorial.adjust_lighting': {
    panelId: 'SceneTools',
    steps: [stepFor('scene-lighting', 'click', '在场景设置里切换光照，或修改光照方向的任意轴。')],
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
  create_node: TUTORIAL_GUIDANCE['tutorial.create_node'].steps[0],
  move_node: TUTORIAL_GUIDANCE['tutorial.move_node'].steps[0],
  connect_nodes: TUTORIAL_GUIDANCE['tutorial.connect_nodes'].steps[0],
  drag_block: TUTORIAL_GUIDANCE['tutorial.drag_block'].steps[0],
  edit_block_parameter: TUTORIAL_GUIDANCE['tutorial.edit_block_parameter'].steps[0],
  set_transition_condition: TUTORIAL_GUIDANCE['tutorial.set_transition_condition'].steps[0],
  run_node_graph: TUTORIAL_GUIDANCE['tutorial.run_node_graph'].steps[0],
  import_model: TUTORIAL_GUIDANCE['tutorial.import_model'].steps[0],
  transform_model: TUTORIAL_GUIDANCE['tutorial.transform_model'].steps[0],
  adjust_lighting: TUTORIAL_GUIDANCE['tutorial.adjust_lighting'].steps[0],
  adjust_physics: TUTORIAL_GUIDANCE['tutorial.adjust_physics'].steps[0],
});

function guidanceForTask(source = {}) {
  if (source.type === 'goal') {
    const intent = String(source.guidanceIntent || '');
    const template = CHAT_GUIDANCE[intent];
    if (!template) return null;
    const panelId = ['import_model', 'adjust_lighting'].includes(intent)
      ? 'SceneTools'
      : ['transform_model', 'adjust_physics'].includes(intent)
        ? 'SceneDatas'
        : 'NodeGraphPanel';
    return { panelId, steps: [{ ...template }] };
  }
  const taskKey = String(source.taskKey || source.issueKey || '');
  const tutorial = TUTORIAL_GUIDANCE[taskKey];
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

export const guidanceRegistry = {
  resolve(source = {}) {
    if (source?.steps && Array.isArray(source.steps) && source.panelId) return source;
    const sourceType = String(source.sourceType || source.type || 'node-issue');
    let resolved;
    if (sourceType === 'chat') {
      const template = CHAT_GUIDANCE[String(source.guidanceIntent || '')];
      if (!template) return null;
      const panelId = String(source.panelId || (
        ['import_model', 'adjust_lighting'].includes(source.guidanceIntent) ? 'SceneTools'
          : ['transform_model', 'adjust_physics'].includes(source.guidanceIntent) ? 'SceneDatas'
            : 'NodeGraphPanel'
      ));
      resolved = { panelId, steps: [{ ...template }] };
    } else if (sourceType === 'optimization-tip') {
      resolved = { panelId: 'NodeGraphPanel', steps: [stepFor('node-canvas', 'focus', source.message || '查看当前节点图中可以优化的控制流。')] };
    } else {
      resolved = guidanceForTask(source);
    }
    if (!resolved?.steps?.length) return null;
    return {
      guidanceId: String(source.guidanceId || source.taskKey || source.issueKey || source.tipKey || source.id || `guidance_${Date.now()}`),
      sourceType,
      title: String(source.title || '操作展示'),
      panelId: resolved.panelId,
      steps: resolved.steps.map((step) => ({ ...step })),
    };
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
      edgeId: String(step?.target?.edgeId || ''),
      portSide: String(step?.target?.portSide || ''),
      portIndex: Number.isFinite(Number(step?.target?.portIndex)) ? Number(step.target.portIndex) : null,
    },
  }));
  await wait(80);
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
