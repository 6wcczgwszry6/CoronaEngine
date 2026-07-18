<template>
  <div class="blockly-toolbox-palette">
    <div class="palette-tabs">
      <button
        v-for="category in categories"
        :key="category.name"
        class="palette-tab"
        :class="{ active: category.name === activeCategoryName }"
        type="button"
        @click="selectCategory(category.name)"
      >
        {{ category.name }}
      </button>
    </div>
    <div class="palette-shelf">
      <div ref="blockdiv" class="palette-block-canvas" @pointerdown.capture="beginExternalDrag"></div>
      <div v-if="loadingLabel" class="palette-overlay">{{ loadingLabel }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TOOLBOX_CONFIG } from '@/blockly/configs/toolboxConfig.js';
import { useErrorHandler } from '@/composables/useErrorHandler.js';

const props = defineProps({
  workspaceRole: { type: String, default: 'node' },
});

const emit = defineEmits([
  'pick',
  'ready',
  'external-drag-start',
  'external-drag-move',
  'external-drag-end',
]);

const { t, locale } = useI18n();
const { error: logError } = useErrorHandler('BlocklyToolboxPalette');

const blockdiv = ref(null);
const loadingLabel = ref('');
const activeCategoryName = ref('');
const returnValueBlocks = ref([]);

let workspace = null;
let BlocklyLib = null;
let blocklyCN = null;
let blocklyEN = null;
let resizeObserver = null;
let isRenderingPalette = false;
let blocksRegistered = false;
let externalDrag = null;
let paletteLayoutFrame = null;
let paletteRenderGeneration = 0;
const DRAG_THRESHOLD = 5;

const normalCategories = computed(() =>
  (TOOLBOX_CONFIG.contents || [])
    .filter((category) => category.kind === 'category')
    .map((category) => ({
      name: category.name,
      blocks: (category.contents || []).filter((item) => item.kind === 'block' && item.type),
    }))
    .filter((category) => category.blocks.length > 0)
);

const categories = computed(() =>
  props.workspaceRole === 'condition'
    ? [{ name: '返回值', blocks: returnValueBlocks.value }]
    : normalCategories.value
);

const CONDITION_BLOCK_PRIORITY = new Map([
  ['math_AND', 0],
  ['math_OR', 1],
  ['math_NOT', 2],
  ['logic_operation', 3],
  ['logic_negate', 4],
  ['logic_compare', 5],
  ['math_E', 6],
  ['math_G', 7],
  ['math_L', 8],
  ['logic_boolean', 9],
  ['math_number', 10],
  ['text', 11],
]);

function outputChecks(block) {
  const checks = block?.outputConnection?.getCheck?.();
  return Array.isArray(checks) ? checks : [];
}

function collectReturnValueBlocks() {
  if (!BlocklyLib) return;
  const itemsByType = new Map();
  for (const category of normalCategories.value) {
    for (const item of category.blocks) {
      if (!itemsByType.has(item.type)) itemsByType.set(item.type, item);
    }
  }

  const probeWorkspace = new BlocklyLib.Workspace();
  const discovered = [];
  try {
    for (const item of itemsByType.values()) {
      let block = null;
      try {
        block = probeWorkspace.newBlock(item.type);
        if (!block.outputConnection) continue;
        const checks = outputChecks(block);
        discovered.push({
          item,
          isBoolean: checks.includes('Boolean'),
          priority: CONDITION_BLOCK_PRIORITY.get(item.type) ?? Number.MAX_SAFE_INTEGER,
        });
      } catch (e) {
        logError(`检查返回值积木失败: ${item.type}`, e);
      } finally {
        try { block?.dispose?.(false); } catch {}
      }
    }
  } finally {
    probeWorkspace.dispose();
  }

  discovered.sort((a, b) =>
    a.priority - b.priority ||
    Number(b.isBoolean) - Number(a.isBoolean) ||
    a.item.type.localeCompare(b.item.type)
  );
  returnValueBlocks.value = discovered.map(({ item }) => item);
}

function syncActiveCategory() {
  const preferredName = props.workspaceRole === 'condition' ? '返回值' : categories.value[0]?.name;
  if (!categories.value.some((category) => category.name === activeCategoryName.value)) {
    activeCategoryName.value = preferredName || '';
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

function activeCategory() {
  return categories.value.find((category) => category.name === activeCategoryName.value) || categories.value[0];
}

function selectCategory(name) {
  activeCategoryName.value = name;
  renderPaletteBlocks();
}

function resizeBlockly() {
  if (!workspace || !BlocklyLib) return;
  try {
    BlocklyLib.svgResize(workspace);
  } catch {}
}

function preparePaletteBlock(block) {
  try {
    block.setMovable?.(false);
    block.setDeletable?.(false);
    block.setEditable?.(false);
    block.setDisabledReason?.(false, 'palette');
  } catch {}
}

function paletteBlockSize(block) {
  const root = block.getSvgRoot?.();
  try {
    const box = root?.getBBox?.();
    if (box && Number.isFinite(box.height) && box.height > 0) {
      return { width: box.width || 180, height: box.height };
    }
  } catch {}
  const size = block.getHeightWidth?.() || {};
  return {
    width: Number(size.width) || 180,
    height: Number(size.height) || 42,
  };
}

function cancelPaletteLayout() {
  paletteRenderGeneration += 1;
  if (paletteLayoutFrame != null) window.cancelAnimationFrame(paletteLayoutFrame);
  paletteLayoutFrame = null;
}

function renderPaletteBlocks() {
  if (!workspace || !BlocklyLib) return;
  cancelPaletteLayout();
  const generation = paletteRenderGeneration;
  isRenderingPalette = true;
  const renderedBlocks = [];
  try {
    workspace.clear();
    const category = activeCategory();
    let provisionalY = 18;
    for (const item of category?.blocks || []) {
      try {
        const block = workspace.newBlock(item.type);
        block.initSvg();
        block.render();
        block.moveBy(16, provisionalY);
        preparePaletteBlock(block);
        renderedBlocks.push(block);
        provisionalY += 72;
      } catch (e) {
        logError(`渲染积木预览失败: ${item.type}`, e);
      }
    }

    // Blockly reports incomplete dimensions for some statement/C-shaped blocks
    // during the same render tick. Measure the real SVG bounds on the next frame
    // and lay every category out with consistent non-overlapping spacing.
    paletteLayoutFrame = window.requestAnimationFrame(() => {
      paletteLayoutFrame = null;
      if (!workspace || generation !== paletteRenderGeneration) return;
      let y = 20;
      for (const block of renderedBlocks) {
        if (block.isDisposed?.()) continue;
        const current = block.getRelativeToSurfaceXY?.() || { x: 0, y: 0 };
        block.moveBy(16 - current.x, y - current.y);
        const size = paletteBlockSize(block);
        const isStatementShape =
          block.type.startsWith('control_') ||
          block.type.startsWith('controls_') ||
          Boolean(block.getInput?.('DO')) ||
          Boolean(block.getInput?.('DO0'));
        y += Math.max(44, size.height) + (isStatementShape ? 26 : 18);
      }
      resizeBlockly();
      workspace.resizeContents?.();
      workspace.scrollbar?.resize?.();
      isRenderingPalette = false;
    });
  } catch (error) {
    isRenderingPalette = false;
    throw error;
  }
}

function paletteBlockFromEvent(event) {
  if (!workspace || !BlocklyLib || isRenderingPalette) return null;

  // Palette blocks are deliberately non-movable, so Blockly may remove the
  // `blocklyDraggable` class. Resolve the block from any SVG root carrying a
  // data-id first, then fall back to checking every rendered block root.
  const path = event.composedPath?.() || [];
  for (const element of path) {
    const blockId = element?.getAttribute?.('data-id');
    const block = blockId ? workspace.getBlockById?.(blockId) : null;
    if (block) return block;
  }

  const target = event.target;
  return (
    workspace
      .getAllBlocks?.(false)
      .find((block) => block.getSvgRoot?.()?.contains?.(target)) || null
  );
}

function removeExternalDragListeners() {
  window.removeEventListener('pointermove', moveExternalDrag, true);
  window.removeEventListener('pointerup', finishExternalDrag, true);
  window.removeEventListener('pointercancel', cancelExternalDrag, true);
}

function beginExternalDrag(event) {
  if (event.button !== 0) return;
  const block = paletteBlockFromEvent(event);
  if (!block?.type) return;
  externalDrag = {
    blockType: block.type,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    started: false,
  };
  event.preventDefault();
  event.stopPropagation();
  window.addEventListener('pointermove', moveExternalDrag, true);
  window.addEventListener('pointerup', finishExternalDrag, true);
  window.addEventListener('pointercancel', cancelExternalDrag, true);
}

function moveExternalDrag(event) {
  if (!externalDrag || event.pointerId !== externalDrag.pointerId) return;
  const distance = Math.hypot(
    event.clientX - externalDrag.startX,
    event.clientY - externalDrag.startY,
  );
  if (!externalDrag.started && distance >= DRAG_THRESHOLD) {
    externalDrag.started = true;
    emit('external-drag-start', {
      blockType: externalDrag.blockType,
      clientX: event.clientX,
      clientY: event.clientY,
    });
  }
  if (!externalDrag.started) return;
  event.preventDefault();
  emit('external-drag-move', {
    blockType: externalDrag.blockType,
    clientX: event.clientX,
    clientY: event.clientY,
  });
}

function finishExternalDrag(event) {
  if (!externalDrag || event.pointerId !== externalDrag.pointerId) return;
  const drag = externalDrag;
  externalDrag = null;
  removeExternalDragListeners();
  if (drag.started) {
    event.preventDefault();
    emit('external-drag-end', {
      blockType: drag.blockType,
      clientX: event.clientX,
      clientY: event.clientY,
      cancelled: false,
    });
  } else {
    emit('pick', drag.blockType);
  }
}

function cancelExternalDrag(event) {
  if (!externalDrag || (event?.pointerId != null && event.pointerId !== externalDrag.pointerId)) return;
  const drag = externalDrag;
  externalDrag = null;
  removeExternalDragListeners();
  if (drag.started) {
    emit('external-drag-end', {
      blockType: drag.blockType,
      clientX: event?.clientX ?? drag.startX,
      clientY: event?.clientY ?? drag.startY,
      cancelled: true,
    });
  }
}

async function initBlockly() {
  const container = blockdiv.value;
  if (!container) return;
  loadingLabel.value = '加载积木库...';
  try {
    BlocklyLib = await import('blockly/core');
    blocklyCN = await import('blockly/msg/zh-hans');
    blocklyEN = await import('blockly/msg/en');
    applyBlocklyLocale();
    await registerBlocks();
    collectReturnValueBlocks();
    syncActiveCategory();

    const { createWorkspaceConfig } = await import('@/blockly/configs/workspaceConfig.js');
    const config = createWorkspaceConfig(t);
    delete config.toolbox;
    config.trashcan = false;
    config.contextMenu = false;
    config.readOnly = false;
    config.grid = { spacing: 0, length: 0, colour: 'transparent', snap: false };
    config.zoom = { controls: false, wheel: false, startScale: 0.82, maxScale: 0.82, minScale: 0.82 };
    config.move = { wheel: true, drag: false, scrollbars: true };

    workspace = BlocklyLib.inject(container, config);
    syncActiveCategory();
    renderPaletteBlocks();

    resizeObserver = new ResizeObserver(() => resizeBlockly());
    resizeObserver.observe(container);
    await nextTick();
    resizeBlockly();
    emit('ready');
  } catch (e) {
    logError('初始化积木库失败', e);
    loadingLabel.value = '积木库加载失败';
    return;
  }
  loadingLabel.value = '';
}

watch(locale, () => {
  applyBlocklyLocale();
  renderPaletteBlocks();
});

watch(
  () => props.workspaceRole,
  () => {
    cancelExternalDrag();
    syncActiveCategory();
    renderPaletteBlocks();
  }
);

onMounted(() => {
  initBlockly();
});

onBeforeUnmount(() => {
  cancelExternalDrag();
  cancelPaletteLayout();
  try {
    resizeObserver?.disconnect?.();
    workspace?.dispose?.();
  } catch {}
  workspace = null;
});

defineExpose({ resizeBlockly });
</script>

<style scoped>
.blockly-toolbox-palette {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  gap: 8px;
}

.palette-tabs {
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
}

.palette-tab {
  width: 100%;
  margin-bottom: 5px;
  padding: 6px 4px;
  border: 1px solid #2b3748;
  border-radius: 8px;
  color: #cbd5e1;
  background: #111923;
  font-size: 11px;
  cursor: pointer;
}

.palette-tab.active {
  color: #fff;
  border-color: #60a5fa;
  background: #1d4ed8;
}

.palette-shelf {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 10px;
  background: #111827;
}

.palette-block-canvas {
  position: absolute;
  inset: 0;
  touch-action: none;
}

:deep(.blocklyBlockCanvas > g[data-id]) {
  cursor: grab !important;
}


.palette-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 12px;
  background: rgba(15, 23, 42, 0.72);
  z-index: 3;
}

:deep(.blocklyMainBackground) {
  stroke: transparent;
  fill: #111827;
}

:deep(.blocklyScrollbarHandle) {
  fill: #475569;
}
</style>
