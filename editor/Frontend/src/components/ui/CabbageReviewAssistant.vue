<template>
  <div
    class="cabbage-review-root"
    @mousedown.stop
    @pointerdown.stop
    @click.stop
    @wheel.stop
  >

    <section class="task-board" aria-label="任务与提示">
      <header class="task-board-header">
        <span>任务与提示</span>
        <span class="task-count" :class="{ empty: displayItems.length === 0 }">{{ displayItems.length }}</span>
      </header>
      <div v-if="displayItems.length" class="task-list" aria-live="polite">
        <article v-for="task in displayItems" :key="task.taskKey || task.issueKey" class="task-item">
          <button
            type="button"
            class="task-title"
            :class="{ selected: isSelected(task) }"
            @click="toggleTask(task)"
          >
            <span class="task-title-text">{{ task.title }}</span>
            <span class="task-chevron" :class="{ expanded: expandedKeys.has(task.taskKey || task.issueKey) }">⌄</span>
          </button>
          <div v-if="expandedKeys.has(task.taskKey || task.issueKey)" class="task-detail">
            <p v-if="task.message">{{ task.message }}</p>
            <div v-if="task.suggestion" class="task-suggestion">
              <strong>{{ suggestionLabel(task) }}</strong>
              <p>{{ task.suggestion }}</p>
            </div>
            <div class="task-actions">
              <button type="button" class="showcase-button" @click="showcase({ ...task, sourceType: task.sourceType || task.type })">展示</button>
              <button v-if="!task.transient" type="button" class="task-discuss" @click="openChat(task)">和包菜继续讨论</button>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="task-empty" aria-live="polite">
        <span class="task-empty-icon">&#10003;</span>
        <span>当前没有待处理的任务或提示</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, watch } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';
import { useCabbageAssistantStore } from '@/stores/cabbageAssistantStore.js';
import { closeFloatingPanel } from '@/utils/panelWindows.js';
import { publishCabbageAssistantContext } from '@/services/cabbageAssistantContextService.js';
import { guidanceService } from '@/services/cabbageGuidanceService.js';

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  attentionToken: { type: Number, default: 0 },
});

const dockStore = useDockStore();
const assistant = useCabbageAssistantStore();
const expandedKeys = reactive(new Set());
const taskKey = (task) => String(task?.taskKey || task?.issueKey || '');
const displayItems = computed(() => {
  const items = [];
  if (assistant.preWarning) {
    const warning = assistant.preWarning;
    items.push({
      ...warning,
      taskKey: `pre-warning:${warning.warningKey || warning.graphRevision || warning.createdAt || 'current'}`,
      issueKey: `pre-warning:${warning.warningKey || warning.graphRevision || warning.createdAt || 'current'}`,
      type: 'pre-warning',
      sourceType: 'node-issue',
      transient: true,
    });
  }
  if (assistant.ephemeralTip) {
    const tip = assistant.ephemeralTip;
    items.push({
      ...tip,
      taskKey: `optimization-tip:${tip.tipKey || tip.graphRevision || tip.createdAt || 'current'}`,
      issueKey: `optimization-tip:${tip.tipKey || tip.graphRevision || tip.createdAt || 'current'}`,
      type: 'optimization-tip',
      sourceType: 'optimization-tip',
      transient: true,
    });
  }
  return [...items, ...props.tasks];
});
let optimizationTimer = null;
let preWarningTimer = null;

function clearOptimizationTimer() {
  if (optimizationTimer) window.clearTimeout(optimizationTimer);
  optimizationTimer = null;
}

function clearPreWarningTimer() {
  if (preWarningTimer) window.clearTimeout(preWarningTimer);
  preWarningTimer = null;
}

function showcase(source) {
  void guidanceService.start(source);
}

function isSelected(task) {
  const key = taskKey(task);
  return task?.transient ? expandedKeys.has(key) : assistant.selectedTaskKey === key;
}

function suggestionLabel(task) {
  if (task?.type === 'node-issue' || task?.type === 'pre-warning') return '这样修改';
  if (task?.type === 'optimization-tip') return '优化建议';
  return '这样完成';
}

function toggleTask(task) {
  const key = taskKey(task);
  if (!key) return;
  if (!task?.transient) {
    assistant.selectTask(key);
    publishCabbageAssistantContext(assistant);
  }
  if (expandedKeys.has(key)) expandedKeys.delete(key);
  else expandedKeys.add(key);
}

async function openChat(task) {
  assistant.selectTask(taskKey(task));
  publishCabbageAssistantContext(assistant);

  const panelId = 'CabbageChatPanel';
  const panel = dockStore.panels[panelId];
  if (!panel) return;

  // The answer panel now belongs to the right dock. If an older detached instance is
  // still alive, close it first so the same Vue panel cannot exist twice.
  if (panel.open && panel.mode === 'external') {
    await closeFloatingPanel(dockStore, panelId);
  }

  dockStore.popIn(panelId);
  dockStore.setDockZone(panelId, 'right');
  dockStore.openPanel(panelId);

  // Keep it directly below AI Talk when that panel is open. Other optional right-side
  // panels remain below the two AI panels.
  const rightIds = dockStore.panelsByZone('right')
    .map((item) => item.id)
    .filter((id) => id !== panelId);
  const aiTalkIndex = rightIds.indexOf('AITalkBar');
  const beforeId = aiTalkIndex >= 0 ? (rightIds[aiTalkIndex + 1] || null) : null;
  dockStore.movePanel(panelId, 'right', beforeId);
  window.dispatchEvent(new Event('resize'));
}

watch(
  () => assistant.ephemeralTip?.expiresAt || 0,
  (expiresAt) => {
    clearOptimizationTimer();
    if (!expiresAt) return;
    const remaining = Math.max(0, Number(expiresAt) - Date.now());
    optimizationTimer = window.setTimeout(() => assistant.clearOptimizationTip(), remaining);
  },
  { immediate: true }
);

watch(
  () => assistant.preWarning?.expiresAt || 0,
  (expiresAt) => {
    clearPreWarningTimer();
    if (!expiresAt) return;
    const remaining = Math.max(0, Number(expiresAt) - Date.now());
    preWarningTimer = window.setTimeout(() => assistant.clearPreWarning(), remaining);
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  clearOptimizationTimer();
  clearPreWarningTimer();
  void guidanceService.stop();
});

watch(
  () => displayItems.value.map((task) => taskKey(task)),
  (keys) => {
    const alive = new Set(keys);
    for (const key of Array.from(expandedKeys)) {
      if (!alive.has(key)) expandedKeys.delete(key);
    }
  }
);
</script>

<style scoped>
.cabbage-review-root {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 2147482500;
  display: flex;
  width: min(290px, calc(100% - 24px));
  max-height: calc(100% - 92px);
  flex-direction: column;
  align-items: stretch;
  gap: 9px;
  pointer-events: none;
}
.cabbage-review-root > * {
  pointer-events: auto;
}
.task-board {
  position: relative;
  width: 100%;
  max-height: min(330px, calc(100% - 70px));
  box-sizing: border-box;
  display: flex;
  flex: 0 1 auto;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #55431f;
  border-left: 3px solid #b8924a;
  border-radius: 9px;
  background: #11100d;
  color: #f2ead5;
  box-shadow: 0 18px 46px rgba(0, 0, 0, .62), 0 0 0 1px rgba(216, 184, 108, .08);
}
.task-board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  box-sizing: border-box;
  padding: 10px 12px 10px 13px;
  border-bottom: 1px solid #3f3018;
  background: #211d12;
  color: #f2ead5;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .02em;
}
.task-count {
  min-width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #9a7736;
  color: #fff3c8;
  font-size: 11px;
}
.task-count.empty {
  background: #3f3018;
  color: #b9ad8f;
}
.task-empty {
  display: flex;
  min-height: 56px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 12px;
  color: #9d9278;
  font-size: 12px;
  text-align: center;
}
.task-empty-icon {
  display: grid;
  width: 20px;
  height: 20px;
  place-items: center;
  border: 1px solid #665025;
  border-radius: 50%;
  color: #d8b86c;
  font-size: 11px;
}
.task-list {
  min-height: 0;
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 8px;
  scrollbar-width: thin;
  scrollbar-color: #8c6f36 #0b0a08;
}
.task-list::-webkit-scrollbar { width: 7px; }
.task-list::-webkit-scrollbar-track { background: #0b0a08; }
.task-list::-webkit-scrollbar-thumb { border-radius: 999px; background: #8c6f36; }
.task-item + .task-item { margin-top: 5px; }
.task-title {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #3f3018;
  border-radius: 6px;
  background: #15130d;
  color: #e5e7eb;
  padding: 9px 10px;
  text-align: left;
  transition: background .14s ease, border-color .14s ease;
}
.task-title:hover, .task-title.selected { border-color: #d8b86c; background: #2b230f; }
.task-title-text { min-width:0; flex:1; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; font-size:13px; font-weight:600; }
.task-chevron { color:#9ca3af; transform:rotate(0deg); transition:transform .14s ease; }
.task-chevron.expanded { transform:rotate(180deg); }
.task-detail { margin:-1px 5px 0; border:1px solid #3f3018; border-top:0; border-radius:0 0 6px 6px; background:#0f0e0a; padding:10px; color:#c9bea0; font-size:12px; line-height:1.65; }
.task-detail p { white-space:pre-wrap; overflow-wrap:anywhere; }
.task-suggestion { margin-top:8px; border-left:2px solid #d8b86c; padding-left:8px; }
.task-suggestion strong { color:#e5c77f; font-size:11px; }
.task-actions { margin-top:9px; display:flex; justify-content:flex-end; gap:7px; }
.showcase-button, .task-discuss { border:1px solid #665025; border-radius:5px; color:#fff7dc; padding:5px 9px; font-size:11px; transition:background .14s ease,border-color .14s ease; }
.showcase-button { flex:0 0 auto; background:#6d5226; }
.showcase-button:hover { border-color:#d8b86c; background:#8c6f36; }
.task-discuss { background:#4b391c; }
.task-discuss:hover { border-color:#b8924a; background:#624b25; }
.task-board-enter-active, .task-board-leave-active { transition: opacity .15s ease, transform .15s ease; transform-origin:center bottom; }
.task-board-enter-from, .task-board-leave-to { opacity:0; transform:translateY(8px) scale(.98); }

@media (max-height: 620px) {
  .cabbage-review-root { max-height: calc(100% - 68px); }
  .task-board { max-height: calc(100% - 54px); }
}
</style>

