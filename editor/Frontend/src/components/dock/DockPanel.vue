<template>
  <div class="dock-panel" :data-dock-panel-id="panelId">
    <div class="dock-panel-header" @pointerdown="onHeaderPointerDown">
      <span class="dock-panel-title" :title="panelTitle">{{ panelTitle }}</span>
      <div class="dock-panel-actions">
        <button class="dock-action-btn" :title="t('dock.popOut')" @click="handlePopOut">&#x29C9;</button>
        <button class="dock-action-btn dock-action-close" :title="t('dock.close')" @click="handleClose">&times;</button>
      </div>
    </div>
    <div class="dock-panel-body">
      <component :is="component" v-if="component" />
      <div v-else class="dock-panel-loading">{{ t('dock.componentMissing', { panelId }) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, provide } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDockStore } from '@/stores/dockStore.js';
import { getPluginDisplayName, getPluginManifest } from '@/config/pluginManifest.js';
import { appService } from '@/utils/bridge.js';

const props = defineProps({
  panelId: { type: String, required: true },
  component: { type: Object, default: null },
});

// 向下传递 panelId，子组件可通过 inject('dockPanelId') 获取
provide('dockPanelId', props.panelId);
provide('inDock', true);

const { t, locale } = useI18n();
const dockStore = useDockStore();
const manifest = computed(() => getPluginManifest(props.panelId));
const panelTitle = computed(() => {
  locale.value;
  return getPluginDisplayName(manifest.value) || props.panelId;
});

// ============================================================================
// 标题栏拖动重排 / 跨区（Pointer Events 自管，刻意不用 HTML5 原生 DnD）。
//
// 为什么用 Pointer Events 而非 draggable+dragstart：docked 面板内部可能嵌入 Blockly
// 等大量使用原生 HTML5 拖放的组件，原生 DnD 会与之共用同一套全局 drag 事件通道而互相
// 干扰。Pointer Events 走独立通道，作用域严格限定在 header，零冲突。全程在主窗口这一个
// CEF 页面 / 一个 JS 上下文内完成，不跨 CEF、不发 IPC、不碰 C++。
// ============================================================================

// 起拖阈值（px）：超过才视为拖动，否则当作普通点击（保留 header 上的点击语义）。
const DRAG_THRESHOLD = 5;

let drag = null; // { startX, startY, active, pointerId } | null

function onHeaderPointerDown(e) {
  // 只接管鼠标左键 / 单指触摸。
  if (e.button !== undefined && e.button !== 0) return;
  // 护栏：从按钮或任何 Blockly 元素上起的指针，绝不拦截（让其原生行为生效）。
  if (e.target.closest('.dock-panel-actions')) return;
  if (e.target.closest('[class*="blockly"]')) return;

  drag = {
    startX: e.clientX,
    startY: e.clientY,
    active: false,
    pointerId: e.pointerId,
  };
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerUp);
}

function onPointerMove(e) {
  if (!drag) return;
  if (!drag.active) {
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    if (dx * dx + dy * dy < DRAG_THRESHOLD * DRAG_THRESHOLD) return;
    // 越过阈值：正式进入拖动。
    drag.active = true;
    dockStore.setDraggingId(props.panelId);
  }
  // 实时高亮指针所在的放置区。
  const target = resolveDropTarget(e.clientX, e.clientY);
  dockStore.setDragOverZone(target ? target.zone : null);
}

function onPointerUp(e) {
  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerUp);
  window.removeEventListener('pointercancel', onPointerUp);

  const wasActive = drag && drag.active;
  drag = null;

  if (!wasActive) {
    dockStore.setDraggingId(null);
    dockStore.setDragOverZone(null);
    return; // 未越过阈值：视为点击，不做任何移动。
  }

  const target = resolveDropTarget(e.clientX, e.clientY);
  if (target && target.zone) {
    dockStore.movePanel(props.panelId, target.zone, target.beforeId);
  }
  dockStore.setDraggingId(null);
  dockStore.setDragOverZone(null);
}

// 用 elementFromPoint 命中落点：找到目标 zone，并在 zone 内确定插入到哪个面板之前
// （指针位于某面板上半部 ⇒ 插其前；下半部 ⇒ 插其后）。返回 { zone, beforeId|null }。
function resolveDropTarget(x, y) {
  const el = document.elementFromPoint(x, y);
  if (!el) return null;

  const zoneEl = el.closest('[data-dock-zone]');
  if (!zoneEl) return null;
  const zone = zoneEl.getAttribute('data-dock-zone');

  const panelEl = el.closest('[data-dock-panel-id]');
  if (!panelEl) {
    // 落在 zone 空白处：追加到末尾。
    return { zone, beforeId: null };
  }
  const overId = panelEl.getAttribute('data-dock-panel-id');
  if (overId === props.panelId) {
    return { zone, beforeId: null }; // 落在自己身上：无操作意图。
  }
  // 上半 ⇒ 插在该面板之前；下半 ⇒ 插在其之后（即下一个面板之前）。
  const rect = panelEl.getBoundingClientRect();
  const isVerticalZone = zone === 'left' || zone === 'right';
  const before = isVerticalZone
    ? y < rect.top + rect.height / 2
    : x < rect.left + rect.width / 2;
  return { zone, beforeId: before ? overId : nextPanelId(zone, overId) };
}

// 返回 zone 内排在 afterId 之后的面板 id（用于“插在 afterId 之后”=“插在其后继之前”）。
function nextPanelId(zone, afterId) {
  const list = dockStore.panelsByZone(zone).map((p) => p.id);
  const idx = list.indexOf(afterId);
  return idx >= 0 && idx + 1 < list.length ? list[idx + 1] : null;
}

function handleClose() {
  dockStore.closePanel(props.panelId);
}

async function handlePopOut() {
  const m = manifest.value;
  if (!m) return;
  try {
    // NOTE: Phase 9 detached pop-out (createDetachedPanel → own borderless OS window) is
    // disabled pending the multi-surface GPU crash fix (startup auto-detach of 3 panels
    // SIGABRTs on the per-surface present path). Reverted to createPanelTab — the panel
    // floats as a main-window rectangle (single surface, verified path). Re-enable via
    // createDetachedPanel once the multi-surface render/present path is fixed.
    const result = await appService.createPanelTab(
      props.panelId,
      '#' + (m.routePath || ''),
      m.defaultWidth || 400,
      m.defaultHeight || 600,
      m.defaultFloatPosition || 'right_top'
    );
    const tabId = result?.tab_id ?? result?.data?.tab_id;
    dockStore.setExternal(props.panelId, tabId);
  } catch (e) {
    console.error('[DockPanel] pop-out failed:', e);
  }
}
</script>

<style scoped>
.dock-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex: 1;
  min-height: 0;
  border-bottom: 1px solid #3c3c3c;
  background: rgba(30, 30, 30, 0.52);
  contain: layout style;
}
.dock-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 6px;
  background: rgba(45, 45, 45, 0.62);
  border-bottom: 1px solid #3c3c3c;
  flex-shrink: 0;
  user-select: none;
}
.dock-panel-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #c0c0c0;
  font-size: 12px;
  font-weight: 500;
}
.dock-panel-actions {
  display: flex;
  gap: 2px;
}
.dock-action-btn {
  background: transparent;
  border: none;
  color: #909090;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
  border-radius: 3px;
  line-height: 1;
}
.dock-action-btn:hover {
  background: rgba(60, 60, 60, 0.72);
  color: #e0e0e0;
}
.dock-action-close:hover {
  background: #c0392b;
  color: #fff;
}
.dock-panel-body {
  flex: 1;
  overflow: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.dock-panel-loading {
  padding: 1rem;
  color: #ff6b6b;
}
</style>
