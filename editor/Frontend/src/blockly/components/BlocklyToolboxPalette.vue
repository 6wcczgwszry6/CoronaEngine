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
      <div ref="blockdiv" class="palette-block-canvas" @mouseup.capture="handleBlockPick"></div>
      <div class="palette-hint">积木库：这里只展示可用积木，点击积木添加到右侧当前编辑区</div>
      <div v-if="loadingLabel" class="palette-overlay">{{ loadingLabel }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { TOOLBOX_CONFIG } from '@/blockly/configs/toolboxConfig.js';
import { useErrorHandler } from '@/composables/useErrorHandler.js';

const emit = defineEmits(['pick', 'ready']);

const { t, locale } = useI18n();
const { error: logError } = useErrorHandler('BlocklyToolboxPalette');

const blockdiv = ref(null);
const loadingLabel = ref('');
const activeCategoryName = ref('');

let workspace = null;
let BlocklyLib = null;
let blocklyCN = null;
let blocklyEN = null;
let resizeObserver = null;
let isRenderingPalette = false;
let blocksRegistered = false;

const categories = computed(() =>
  (TOOLBOX_CONFIG.contents || [])
    .filter((category) => category.kind === 'category')
    .map((category) => ({
      name: category.name,
      blocks: (category.contents || []).filter((item) => item.kind === 'block' && item.type),
    }))
    .filter((category) => category.blocks.length > 0)
);

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

function renderPaletteBlocks() {
  if (!workspace || !BlocklyLib) return;
  isRenderingPalette = true;
  try {
    workspace.clear();
    const category = activeCategory();
    let y = 18;
    for (const item of category?.blocks || []) {
      try {
        const block = workspace.newBlock(item.type);
        block.initSvg();
        block.render();
        block.moveBy(16, y);
        preparePaletteBlock(block);
        const size = block.getHeightWidth?.() || { height: 42 };
        y += Math.max(34, size.height || 42) + 16;
      } catch (e) {
        logError(`渲染积木预览失败: ${item.type}`, e);
      }
    }
    workspace.scrollbar?.resize?.();
    resizeBlockly();
  } finally {
    isRenderingPalette = false;
  }
}

function handleBlockPick(event) {
  if (!workspace || !BlocklyLib || isRenderingPalette) return;
  const blockElement = event.target?.closest?.('.blocklyDraggable');
  const blockId = blockElement?.getAttribute?.('data-id');
  let block = blockId ? workspace.getBlockById?.(blockId) : null;
  if (block?.type) {
    emit('pick', block.type);
    return;
  }
  window.setTimeout(() => {
    const selected = BlocklyLib.common?.getSelected?.() || BlocklyLib.getSelected?.();
    block = selected?.workspace === workspace ? selected : null;
    if (block?.type) emit('pick', block.type);
  }, 0);
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
    if (!activeCategoryName.value && categories.value[0]) activeCategoryName.value = categories.value[0].name;
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

onMounted(() => {
  initBlockly();
});

onBeforeUnmount(() => {
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
  height: 420px;
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr);
  gap: 6px;
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
}

.palette-hint {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  z-index: 2;
  padding: 6px 8px;
  border-radius: 8px;
  color: #cbd5e1;
  background: rgba(15, 23, 42, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.22);
  font-size: 10px;
  line-height: 1.35;
  pointer-events: none;
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
