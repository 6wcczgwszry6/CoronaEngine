<template>
  <div
    :class="['mini-blockly-shell', { 'drop-active': dropActive }]"
    @dragover.prevent
    @drop.prevent="handleDrop"
    @mouseup.capture="handleDeleteModePointer"
  >
    <div ref="blockdiv" class="mini-blockly-canvas"></div>
    <div v-if="loadingLabel" class="mini-blockly-overlay">{{ loadingLabel }}</div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useErrorHandler } from '@/composables/useErrorHandler.js';

const props = defineProps({
  workspaceKey: { type: String, default: '' },
  initialState: { type: Object, default: () => ({}) },
  placeholder: { type: String, default: '将左侧微观积木拖入这里' },
  deleteMode: { type: Boolean, default: false },
  showToolbox: { type: Boolean, default: false },
});

const emit = defineEmits(['change', 'ready']);

const { t, locale } = useI18n();
const { error: logError } = useErrorHandler('MiniBlocklyWorkspace');

const blockdiv = ref(null);
const loadingLabel = ref('');
const dropActive = ref(false);

let workspace = null;
let BlocklyLib = null;
let blocklyCN = null;
let blocklyEN = null;
let resizeObserver = null;
let isLoadingWorkspace = false;
let changeListener = null;

let blocksRegistered = false;

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
  if (!workspace || !BlocklyLib) return;
  isLoadingWorkspace = true;
  try {
    workspace.clear();
    const nextState = cloneState(state);
    if (hasSerializedWorkspaceContent(nextState)) {
      BlocklyLib.serialization.workspaces.load(nextState, workspace);
    }
  } catch (e) {
    logError('加载子工作区状态失败', e);
  } finally {
    isLoadingWorkspace = false;
    resizeBlockly();
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


function hitTest(clientX, clientY) {
  const rect = blockdiv.value?.getBoundingClientRect?.();
  if (!rect) return false;
  return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
}

function setDropActive(active) {
  dropActive.value = Boolean(active);
}

function addBlock(blockType, clientX, clientY) {
  if (!workspace || !BlocklyLib || !blockType) return false;
  try {
    const block = workspace.newBlock(blockType);
    block.initSvg();
    block.render();

    const rect = blockdiv.value?.getBoundingClientRect?.();
    const metrics = workspace.getMetrics?.();
    const scale = workspace.scale || 1;
    const hasScreenPoint = Number.isFinite(clientX) && Number.isFinite(clientY) && rect;
    const x = hasScreenPoint && metrics ? metrics.viewLeft + (clientX - rect.left) / scale : (metrics?.viewLeft || 0) + 24;
    const y = hasScreenPoint && metrics ? metrics.viewTop + (clientY - rect.top) / scale : (metrics?.viewTop || 0) + 24;
    block.moveBy(Math.max(0, x), Math.max(0, y));
    workspace.setSelected?.(block);
    emitChange();
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
      emitChange();
    };
    workspace.addChangeListener(changeListener);
    loadState(props.initialState);

    resizeObserver = new ResizeObserver(() => resizeBlockly());
    resizeObserver.observe(container);
    await nextTick();
    resizeBlockly();
    emit('ready');
  } catch (e) {
    logError('初始化子 Blockly 工作区失败', e);
    loadingLabel.value = '积木工作区加载失败';
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
  applyBlocklyLocale();
});

onMounted(() => {
  initBlockly();
});

onBeforeUnmount(() => {
  dropActive.value = false;
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
  deleteBlockById,
  resizeBlockly,
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
  transition: border-color 120ms ease, box-shadow 120ms ease;
}

.mini-blockly-shell.drop-active {
  border-color: #60a5fa;
  box-shadow: inset 0 0 0 2px rgba(96, 165, 250, 0.28), 0 0 14px rgba(59, 130, 246, 0.22);
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
  font-size: 12px;
  background: rgba(15, 23, 42, 0.72);
  z-index: 2;
}
</style>
