<template>
  <div
    :class="['mini-blockly-shell', { 'drop-active': dropActive, 'drop-invalid': dropInvalid }]"
    @dragover.prevent
    @drop.prevent="handleDrop"
    @mouseup.capture="handleDeleteModePointer"
  >
    <div ref="blockdiv" class="mini-blockly-canvas"></div>
    <div v-if="loadingLabel" class="mini-blockly-overlay">{{ loadingLabel }}</div>
    <div v-else-if="validationMessage" class="mini-blockly-validation">{{ validationMessage }}</div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useErrorHandler } from '@/composables/useErrorHandler.js';
import { registerDataNamesFromState } from '@/blockly/blocks/variable.js';

const props = defineProps({
  workspaceKey: { type: String, default: '' },
  initialState: { type: Object, default: () => ({}) },
  placeholder: { type: String, default: '将左侧微观积木拖入这里' },
  deleteMode: { type: Boolean, default: false },
  showToolbox: { type: Boolean, default: false },
  workspaceRole: { type: String, default: 'node' },
});

const emit = defineEmits(['change', 'ready', 'reject', 'block-added', 'block-changed']);

const { t, locale } = useI18n();
const { error: logError } = useErrorHandler('MiniBlocklyWorkspace');

const blockdiv = ref(null);
const loadingLabel = ref('');
const dropActive = ref(false);
const dropInvalid = ref(false);
const validationMessage = ref('');
const GLOBAL_ROOT_TYPES = new Set([
  'variable_define',
  'variable_set',
  'variable_add',
  'variable_show',
  'variable_hide',
  'list_define',
  'list_show',
  'list_hide',
]);

let workspace = null;
let BlocklyLib = null;
let blocklyCN = null;
let blocklyEN = null;
let resizeObserver = null;
let isLoadingWorkspace = false;
let changeListener = null;
let readyResolved = false;
let resolveReady;
const readyPromise = new Promise((resolve) => {
  resolveReady = resolve;
});

let blocksRegistered = false;

function loadedBlockSummary() {
  const blocks = workspace?.getAllBlocks?.(false) || [];
  return {
    blockCount: blocks.length,
    blockIds: blocks.map((block) => String(block?.id || '')).filter(Boolean),
  };
}

function settleReady(result) {
  if (readyResolved) return;
  readyResolved = true;
  resolveReady?.(result);
}

function isReady() {
  return Boolean(workspace && BlocklyLib);
}

function whenReady() {
  if (isReady()) return Promise.resolve({ success: true, ready: true, ...loadedBlockSummary() });
  return readyPromise;
}

function hasSerializedWorkspaceContent(state) {
  if (!state || typeof state !== 'object') return false;
  if (Array.isArray(state.blocks?.blocks) && state.blocks.blocks.length > 0) return true;
  if (Array.isArray(state.variables) && state.variables.length > 0) return true;
  return Object.keys(state).length > 0 && JSON.stringify(state) !== '{}';
}

function cloneState(state) {
  try {
    return JSON.parse(JSON.stringify(state || {}));
  } catch {
    return {};
  }
}

function blocklyMessageBundle() {
  const module = locale.value === 'en-US' ? blocklyEN : blocklyCN;
  return module?.default || module || {};
}

function applyBlocklyLocale() {
  if (!BlocklyLib) return;
  try {
    BlocklyLib.setLocale(blocklyMessageBundle());
  } catch (e) {
    logError('setLocale failed', e);
  }
}

async function registerBlocks() {
  if (blocksRegistered) return;
  const [
    { defineAudioBlocks },
    { defineCameraBlocks },
    { defineEngineBlocks },
    { defineAppearanceBlocks },
    { defineEventBlocks },
    { defineControlBlocks },
    { defineDetectBlocks },
    { defineMathBlocks },
    { defineVariableBlocks },
    { defineListBlocks },
    { defineObjectBlocks },
    { defineUiBlocks },
  ] = await Promise.all([
    import('@/blockly/blocks/audio.js'),
    import('@/blockly/blocks/camera.js'),
    import('@/blockly/blocks/engine.js'),
    import('@/blockly/blocks/appearance.js'),
    import('@/blockly/blocks/event.js'),
    import('@/blockly/blocks/control.js'),
    import('@/blockly/blocks/detect.js'),
    import('@/blockly/blocks/math.js'),
    import('@/blockly/blocks/variable.js'),
    import('@/blockly/blocks/list.js'),
    import('@/blockly/blocks/object.js'),
    import('@/blockly/blocks/ui.js'),
  ]);

  await import('blockly/blocks');
  defineAudioBlocks();
  defineCameraBlocks();
  defineEngineBlocks();
  defineAppearanceBlocks();
  defineEventBlocks(ref([]), () => {});
  defineControlBlocks();
  defineDetectBlocks();
  defineMathBlocks();
  defineVariableBlocks();
  defineListBlocks();
  defineObjectBlocks();
  defineUiBlocks();
  blocksRegistered = true;
}

function applyRoleVisualStyle(block) {
  if (!block) return;
  if (props.workspaceRole === 'condition' && block.outputConnection) {
    try {
      block.setStyle('condition_blocks');
      if (block.rendered) block.render?.();
    } catch {}
  }
}

function applyWorkspaceRoleVisualStyles() {
  if (!workspace) return;
  for (const block of workspace.getAllBlocks?.(false) || []) applyRoleVisualStyle(block);
}

function getState() {
  if (!workspace || !BlocklyLib) return {};
  try {
    return BlocklyLib.serialization.workspaces.save(workspace);
  } catch (e) {
    logError('读取子工作区状态失败', e);
    return {};
  }
}

function loadState(state) {
  if (!workspace || !BlocklyLib) {
    return {
      success: false,
      ready: false,
      error: '积木工作区尚未初始化完成',
      blockCount: 0,
      blockIds: [],
    };
  }
  isLoadingWorkspace = true;
  try {
    workspace.clear();
    const nextState = cloneState(state);
    registerDataNamesFromState(nextState);
    if (hasSerializedWorkspaceContent(nextState)) {
      BlocklyLib.serialization.workspaces.load(nextState, workspace);
    }
    applyWorkspaceRoleVisualStyles();
    window.requestAnimationFrame(() => syncGuidanceBlockMetadata());
    return { success: true, ready: true, ...loadedBlockSummary() };
  } catch (e) {
    logError('加载子工作区状态失败', e);
    return {
      success: false,
      ready: true,
      error: String(e?.message || e),
      ...loadedBlockSummary(),
    };
  } finally {
    isLoadingWorkspace = false;
    resizeBlockly();
    validateWorkspace();
  }
}

function emitChange() {
  if (isLoadingWorkspace) return;
  emit('change', getState());
}

function deleteBlockById(blockId) {
  if (!workspace || !blockId) return false;
  const block = workspace.getBlockById?.(blockId);
  if (!block) return false;
  try {
    block.dispose(true, true);
    emitChange();
    validateWorkspace();
    return true;
  } catch (e) {
    logError('删除子工作区积木失败', e);
    return false;
  }
}

function maybeDeleteClickedBlock(event) {
  if (!props.deleteMode || isLoadingWorkspace || !workspace || !BlocklyLib) return false;
  const selectedEventType = BlocklyLib.Events?.SELECTED || 'selected';
  const clickEventType = BlocklyLib.Events?.CLICK || 'click';
  if (
    event?.type !== selectedEventType &&
    event?.type !== 'selected' &&
    event?.type !== clickEventType &&
    event?.type !== 'click'
  )
    return false;
  const blockId = event.newElementId || event.newValue || event.blockId;
  if (!blockId) return false;
  window.setTimeout(() => deleteBlockById(blockId), 0);
  return true;
}

function handleDeleteModePointer(event) {
  if (!props.deleteMode || !workspace || !BlocklyLib) return;
  const hitBlock = event.target?.closest?.('.blocklyDraggable');
  if (!hitBlock) return;
  window.setTimeout(() => {
    const selected = BlocklyLib.common?.getSelected?.() || BlocklyLib.getSelected?.();
    if (selected?.id) deleteBlockById(selected.id);
  }, 0);
}

function resizeBlockly() {
  if (!workspace || !BlocklyLib) return;
  try {
    BlocklyLib.svgResize(workspace);
  } catch {}
}

function syncGuidanceBlockMetadata() {
  if (!workspace) return;
  for (const block of workspace.getAllBlocks?.(false) || []) {
    const root = block.getSvgRoot?.();
    if (!root) continue;
    root.setAttribute('data-block-id', String(block.id || ''));
    root.setAttribute('data-block-type', String(block.type || ''));
  }
}

function focusBlock(blockId) {
  if (!workspace || !blockId) return false;
  const block = workspace.getBlockById?.(String(blockId));
  if (!block) return false;
  syncGuidanceBlockMetadata();
  try {
    workspace.centerOnBlock?.(block.id);
  } catch {}
  window.requestAnimationFrame(() => syncGuidanceBlockMetadata());
  return true;
}

function hasBlock(blockId) {
  return Boolean(workspace?.getBlockById?.(String(blockId || '')));
}

function hitTest(clientX, clientY) {
  const rect = blockdiv.value?.getBoundingClientRect?.();
  if (!rect) return false;
  return (
    clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom
  );
}

function setDropActive(active, valid = true) {
  dropActive.value = Boolean(active) && Boolean(valid);
  dropInvalid.value = Boolean(active) && !valid;
}

function outputChecks(block) {
  const checks = block?.outputConnection?.getCheck?.();
  return Array.isArray(checks) ? checks : [];
}

function hasKnownNonBooleanOutput(block) {
  const checks = outputChecks(block);
  return checks.length > 0 && !checks.includes('Boolean');
}

function inspectBlockAcceptance(block) {
  if (!block) return { accepted: false, message: '无法识别该积木' };
  if (props.workspaceRole === 'global') {
    if (GLOBAL_ROOT_TYPES.has(block.type) || block.outputConnection)
      return { accepted: true, message: '' };
    return { accepted: false, message: '此积木应放入节点内部编辑区' };
  }
  if (props.workspaceRole === 'condition' && !block.outputConnection) {
    return { accepted: false, message: '跳转条件只能放入返回值积木；多个判断请使用“与 / 或”组合' };
  }
  return { accepted: true, message: '' };
}

function canAcceptBlock(blockType) {
  if (!workspace || !blockType) return false;
  let probe = null;
  try {
    probe = workspace.newBlock(blockType);
    return inspectBlockAcceptance(probe).accepted;
  } catch {
    return false;
  } finally {
    try {
      probe?.dispose?.(false);
    } catch {}
  }
}

function validateWorkspace() {
  if (!workspace) return { valid: true, errors: [] };
  const errors = [];
  const topBlocks = workspace.getTopBlocks?.(true) || [];
  if (props.workspaceRole === 'global') {
    for (const block of topBlocks) {
      if (!GLOBAL_ROOT_TYPES.has(block.type)) {
        errors.push(
          block.outputConnection
            ? '全局变量池中的返回值积木必须连接到初始化积木'
            : '此积木应放入节点内部编辑区'
        );
      }
    }
  } else if (props.workspaceRole === 'condition') {
    if (topBlocks.length > 1) {
      errors.push('请使用“与 / 或”积木把多个判断连接成一个顶层条件');
    } else if (topBlocks.length === 1 && !topBlocks[0].outputConnection) {
      errors.push('跳转条件最外层必须是返回值积木');
    } else if (topBlocks.length === 1 && hasKnownNonBooleanOutput(topBlocks[0])) {
      errors.push('跳转条件必须返回真或假；请将数字、坐标或文本连接到比较积木');
    }
  }
  validationMessage.value = errors[0] || '';
  return { valid: errors.length === 0, errors };
}

function addBlock(blockType, clientX, clientY) {
  if (!workspace || !BlocklyLib || !blockType) return false;
  try {
    const block = workspace.newBlock(blockType);
    const acceptance = inspectBlockAcceptance(block);
    if (!acceptance.accepted) {
      block.dispose(false);
      validationMessage.value = acceptance.message;
      emit('reject', acceptance.message);
      window.setTimeout(() => {
        if (validationMessage.value === acceptance.message) validationMessage.value = '';
      }, 2400);
      return false;
    }
    applyRoleVisualStyle(block);
    block.initSvg();
    block.render();

    const rect = blockdiv.value?.getBoundingClientRect?.();
    const metrics = workspace.getMetrics?.();
    const scale = workspace.scale || 1;
    const hasScreenPoint = Number.isFinite(clientX) && Number.isFinite(clientY) && rect;
    const x =
      hasScreenPoint && metrics
        ? metrics.viewLeft + (clientX - rect.left) / scale
        : (metrics?.viewLeft || 0) + 24;
    const y =
      hasScreenPoint && metrics
        ? metrics.viewTop + (clientY - rect.top) / scale
        : (metrics?.viewTop || 0) + 24;
    block.moveBy(Math.max(0, x), Math.max(0, y));
    workspace.setSelected?.(block);
    emitChange();
    emit('block-added', {
      blockId: String(block.id || ''),
      blockType: String(block.type || blockType),
      workspaceRole: props.workspaceRole,
      interaction: hasScreenPoint ? 'drag' : 'pick',
    });
    return true;
  } catch (e) {
    logError(`创建积木失败: ${blockType}`, e);
    return false;
  }
}

function addBlockFromDrop(blockType, event) {
  return addBlock(blockType, event?.clientX ?? 24, event?.clientY ?? 24);
}

function handleDrop(event) {
  const raw = event.dataTransfer?.getData('application/x-corona-nodegraph');
  if (!raw) return;
  try {
    const payload = JSON.parse(raw);
    if (payload?.kind === 'micro-block') {
      addBlockFromDrop(payload.blockType, event);
    }
  } catch {}
}

async function initBlockly() {
  const container = blockdiv.value;
  if (!container) return;
  loadingLabel.value = '加载积木工作区...';
  try {
    BlocklyLib = await import('blockly/core');
    const { installCustomBlockLocalization } = await import('@/blockly/i18n/customBlockLocalization.js');
    installCustomBlockLocalization(BlocklyLib);
    blocklyCN = await import('blockly/msg/zh-hans');
    blocklyEN = await import('blockly/msg/en');
    applyBlocklyLocale();
    await registerBlocks();

    const { createWorkspaceConfig } = await import('@/blockly/configs/workspaceConfig.js');
    const config = createWorkspaceConfig(t);
    if (!props.showToolbox) delete config.toolbox;
    config.trashcan = true;
    config.contextMenu = true;
    config.zoom = { ...(config.zoom || {}), controls: false, wheel: true, startScale: 0.85 };
    config.move = { ...(config.move || {}), wheel: true, drag: true, scrollbars: true };

    workspace = BlocklyLib.inject(container, config);
    changeListener = (event) => {
      maybeDeleteClickedBlock(event);
      if (!isLoadingWorkspace) {
        const blockChangeType = BlocklyLib.Events?.BLOCK_CHANGE || 'change';
        if (
          (event?.type === blockChangeType || event?.type === 'change') &&
          event?.element === 'field' &&
          event?.oldValue !== event?.newValue
        ) {
          const block = workspace?.getBlockById?.(event.blockId);
          emit('block-changed', {
            blockId: String(event.blockId || ''),
            blockType: String(block?.type || ''),
            fieldName: String(event.name || ''),
            workspaceRole: props.workspaceRole,
          });
        }
      }
      if (props.workspaceRole === 'condition') applyWorkspaceRoleVisualStyles();
      window.requestAnimationFrame(() => syncGuidanceBlockMetadata());
      emitChange();
      validateWorkspace();
    };
    workspace.addChangeListener(changeListener);
    const initialLoad = loadState(props.initialState);

    resizeObserver = new ResizeObserver(() => resizeBlockly());
    resizeObserver.observe(container);
    await nextTick();
    resizeBlockly();
    syncGuidanceBlockMetadata();
    const readyResult = {
      success: true,
      ready: true,
      initialLoad,
      ...loadedBlockSummary(),
    };
    settleReady(readyResult);
    emit('ready', readyResult);
  } catch (e) {
    logError('初始化子 Blockly 工作区失败', e);
    loadingLabel.value = '积木工作区加载失败';
    settleReady({
      success: false,
      ready: false,
      error: String(e?.message || e),
      blockCount: 0,
      blockIds: [],
    });
    return;
  }
  loadingLabel.value = '';
}

watch(
  () => props.workspaceKey,
  () => {
    loadState(props.initialState);
  }
);

watch(locale, () => {
  if (!workspace || !BlocklyLib) return;
  const state = getState();
  applyBlocklyLocale();
  loadState(state);
});

onMounted(() => {
  initBlockly();
});

onBeforeUnmount(() => {
  dropActive.value = false;
  dropInvalid.value = false;
  try {
    if (workspace && changeListener) workspace.removeChangeListener(changeListener);
    resizeObserver?.disconnect?.();
    workspace?.dispose?.();
  } catch {}
  workspace = null;
});

defineExpose({
  getState,
  loadState,
  addBlock,
  addBlockFromDrop,
  hitTest,
  setDropActive,
  canAcceptBlock,
  validateWorkspace,
  deleteBlockById,
  resizeBlockly,
  focusBlock,
  hasBlock,
  isReady,
  whenReady,
  loadedBlockSummary,
});
</script>

<style scoped>
.mini-blockly-shell {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 120px;
  overflow: hidden;
  border-radius: 10px;
  background: #111827;
  border: 1px solid rgba(148, 163, 184, 0.25);
  transition:
    border-color 120ms ease,
    box-shadow 120ms ease;
}

.mini-blockly-shell.drop-active {
  border-color: #60a5fa;
  box-shadow:
    inset 0 0 0 2px rgba(96, 165, 250, 0.28),
    0 0 14px rgba(59, 130, 246, 0.22);
}

.mini-blockly-shell.drop-invalid {
  border-color: #ef4444;
  box-shadow: inset 0 0 0 2px rgba(239, 68, 68, 0.32);
}

.mini-blockly-validation {
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 10px;
  z-index: 4;
  padding: 7px 10px;
  border: 1px solid rgba(248, 113, 113, 0.65);
  border-radius: 7px;
  color: #fecaca;
  background: rgba(127, 29, 29, 0.92);
  font-size: 13px;
  pointer-events: none;
}

.mini-blockly-canvas {
  position: absolute;
  inset: 0;
}

.mini-blockly-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 13px;
  background: rgba(15, 23, 42, 0.72);
  z-index: 2;
}
</style>
