<template>
  <div class="dock-panel">
    <div class="dock-panel-header">
      <span class="dock-panel-title">{{ manifest?.displayName ?? panelId }}</span>
      <div class="dock-panel-actions">
        <button class="dock-action-btn" title="弹出为独立窗口" @click="handlePopOut">&#x29C9;</button>
        <button class="dock-action-btn dock-action-close" title="关闭" @click="handleClose">&times;</button>
      </div>
    </div>
    <div class="dock-panel-body">
      <Suspense>
        <component :is="asyncComponent" v-if="asyncComponent" />
        <div v-else class="dock-panel-loading">加载中...</div>
      </Suspense>
    </div>
  </div>
</template>

<script setup>
import { defineAsyncComponent, shallowRef, watch, computed, provide } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';
import { getPluginManifest } from '@/config/pluginManifest.js';
import { appService } from '@/utils/bridge.js';

const props = defineProps({
  panelId: { type: String, required: true },
  component: { type: [Function, Object], default: null },
});

// 向下传递 panelId，子组件可通过 inject('dockPanelId') 获取
provide('dockPanelId', props.panelId);
provide('inDock', true);

const dockStore = useDockStore();
const manifest = computed(() => getPluginManifest(props.panelId));
const asyncComponent = shallowRef(null);

watch(
  () => props.component,
  (comp) => {
    if (comp) asyncComponent.value = defineAsyncComponent(comp);
  },
  { immediate: true }
);

function handleClose() {
  dockStore.closePanel(props.panelId);
}

async function handlePopOut() {
  const m = manifest.value;
  if (!m) return;
  try {
    const result = await appService.createPanelTab(
      props.panelId,
      '#' + (m.routePath || ''),
      m.defaultWidth || 400,
      m.defaultHeight || 600
    );
    const tabId = result?.data?.tab_id;
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
  background: #1e1e1e;
}
.dock-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 6px;
  background: #2d2d2d;
  border-bottom: 1px solid #3c3c3c;
  flex-shrink: 0;
  user-select: none;
}
.dock-panel-title {
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
  background: #3c3c3c;
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
}
.dock-panel-loading {
  padding: 1rem;
  color: #909090;
}
</style>
