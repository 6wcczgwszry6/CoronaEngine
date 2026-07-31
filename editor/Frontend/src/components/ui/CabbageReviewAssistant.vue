<template>
  <div
    class="cabbage-review-root"
    :class="{ resident: props.resident }"
    @mousedown.stop
    @pointerdown.stop
    @click.stop
    @wheel.stop
  >
    <section class="task-board" :aria-label="t('cabbageReview.title')">
      <header class="task-board-header">
        <span>{{ t('cabbageReview.title') }}</span>
        <div class="task-header-actions">
          <button type="button" class="history-button" :class="{ active: historyVisible }" @click="toggleHistory">
            {{ historyVisible ? t('cabbageReview.backToTasks') : t('cabbageReview.history') }}
          </button>
          <span class="task-count" :class="{ empty: visibleTasks.length === 0 }">{{ visibleTasks.length }}</span>
        </div>
      </header>

      <div v-if="visibleTasks.length" class="task-list">
        <article
          v-for="(task, index) in visibleTasks"
          :key="rowKey(task, index)"
          class="task-item"
          :class="{
            completed: historyVisible,
            'pre-warning': task.type === 'pre-warning',
            'optimization-opinion': task.type === 'optimization-tip',
          }"
        >
          <button
            type="button"
            class="task-summary"
            :class="{ selected: assistant.selectedTaskKey === taskKey(task) }"
            @click="toggleTask(task, index)"
          >
            <span class="task-summary-topline">
              <span
                class="task-discipline"
                :class="disciplineClass(task)"
              >
                {{ disciplineLabel(task) }}
              </span>
              <span class="task-title-text">{{ localizedTaskField(task, 'title') }}</span>
              <span v-if="historyVisible" class="task-completed-badge">{{ t('cabbageReview.completed') }}</span>
              <span class="task-chevron" :class="{ expanded: expandedKeys.has(rowKey(task, index)) }">&#8964;</span>
            </span>
            <span class="task-introduction">{{ taskDescription(task) }}</span>
          </button>

          <div v-if="expandedKeys.has(rowKey(task, index))" class="task-detail">
            <div class="task-suggestion">
              <strong>{{ t('cabbageReview.howToComplete') }}</strong>
              <p>{{ completionText(task) }}</p>
            </div>
            <div class="task-actions">
              <button type="button" class="showcase-button" @click="showcase({ ...task, sourceType: task.type })">
                {{ t('cabbageReview.showcase') }}
              </button>
              <button type="button" class="task-discuss" @click="openChat(task)">
                {{ t('cabbageReview.continueDiscussion') }}
              </button>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="task-empty" aria-live="polite">
        <span class="task-empty-icon">&#10003;</span>
        <span>{{ historyVisible ? t('cabbageReview.emptyHistory') : t('cabbageReview.emptyActive') }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useDockStore } from '@/stores/dockStore.js';
import { useCabbageAssistantStore } from '@/stores/cabbageAssistantStore.js';
import { closeFloatingPanel } from '@/utils/panelWindows.js';
import { publishCabbageAssistantContext } from '@/services/cabbageAssistantContextService.js';
import { guidanceService } from '@/services/cabbageGuidanceService.js';
import { translateUiText } from '@/i18n/domTranslator.js';

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  attentionToken: { type: Number, default: 0 },
  resident: { type: Boolean, default: false },
});

const { t, locale } = useI18n();
const dockStore = useDockStore();
const assistant = useCabbageAssistantStore();
const expandedKeys = reactive(new Set());
const historyVisible = ref(false);
const preWarningTask = computed(() => {
  const warning = assistant.preWarning;
  if (!warning) return null;
  return {
    ...warning,
    taskKey: String(warning.taskKey || warning.warningKey || `pre-warning:${warning.code || 'issue'}`),
    issueKey: String(warning.taskKey || warning.warningKey || `pre-warning:${warning.code || 'issue'}`),
    type: 'pre-warning',
    discipline: 'hint',
    status: 'active',
    transient: true,
    suggestion: String(warning.suggestion || warning.message || ''),
  };
});
const optimizationTask = computed(() => {
  const tip = assistant.ephemeralTip;
  if (!tip) return null;
  const key = String(tip.taskKey || `optimization:${tip.graphRevision || 'graph'}:${tip.tipKey || 'tip'}`);
  return {
    ...tip,
    taskKey: key,
    issueKey: key,
    type: 'optimization-tip',
    discipline: 'opinion',
    status: 'active',
    transient: true,
    suggestion: String(tip.suggestion || tip.message || ''),
  };
});
const visibleTasks = computed(() => {
  if (historyVisible.value) return assistant.completedTasks;
  return [preWarningTask.value, optimizationTask.value, ...props.tasks].filter(Boolean);
});
const taskKey = (task) => String(task?.taskKey || task?.issueKey || '');
let optimizationTimer = null;
let preWarningTimer = null;

function completionTimestamp(task) {
  return Math.max(
    Number(task?.completedAt) || 0,
    Number(task?.resolvedAt) || 0,
    Number(task?.updatedAt) || 0
  );
}

function rowKey(task, index = 0) {
  const key = taskKey(task) || `task_${index}`;
  return historyVisible.value ? `history:${key}:${completionTimestamp(task)}:${index}` : `active:${key}`;
}

function disciplineClass(task) {
  if (task?.discipline === 'hint') return 'hint';
  if (task?.discipline === 'opinion') return 'opinion';
  return task?.discipline === 'art' ? 'art' : 'programming';
}

function disciplineLabel(task) {
  if (task?.discipline === 'hint') return t('cabbageReview.disciplineHint');
  if (task?.discipline === 'opinion') return t('cabbageReview.disciplineOpinion');
  return task?.discipline === 'art'
    ? t('cabbageReview.disciplineArt')
    : t('cabbageReview.disciplineProgramming');
}

function localizedTaskField(task, field) {
  const source = String(task?.[field] || '');
  if (locale.value !== 'en-US') return source;
  const english = String(task?.[`${field}En`] || '').trim();
  return english || translateUiText(source);
}

function taskDescription(task) {
  return localizedTaskField(task, 'message')
    || localizedTaskField(task, 'completionCriteria')
    || t('cabbageReview.descriptionFallback');
}

function completionText(task) {
  return localizedTaskField(task, 'suggestion')
    || localizedTaskField(task, 'completionCriteria')
    || localizedTaskField(task, 'message')
    || t('cabbageReview.completionFallback');
}

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

function toggleHistory() {
  historyVisible.value = !historyVisible.value;
  expandedKeys.clear();
}

function toggleTask(task, index) {
  const logicalKey = taskKey(task);
  const displayKey = rowKey(task, index);
  if (!logicalKey) return;
  assistant.selectTask(logicalKey);
  if (task?.transient !== true) publishCabbageAssistantContext(assistant);
  if (expandedKeys.has(displayKey)) expandedKeys.delete(displayKey);
  else expandedKeys.add(displayKey);
}

async function openChat(task) {
  assistant.selectTask(taskKey(task));
  if (task?.transient !== true) publishCabbageAssistantContext(assistant);

  if (props.resident) {
    window.dispatchEvent(new CustomEvent('cabbage-chat-focus-request', {
      detail: { taskKey: taskKey(task) },
    }));
    return;
  }

  const panelId = 'CabbageChatPanel';
  const panel = dockStore.panels[panelId];
  if (!panel) return;

  if (panel.open && panel.mode === 'external') {
    await closeFloatingPanel(dockStore, panelId);
  }

  dockStore.popIn(panelId);
  dockStore.setDockZone(panelId, 'right');
  dockStore.openPanel(panelId);

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

watch(
  () => visibleTasks.value.map((task, index) => rowKey(task, index)),
  (keys) => {
    const alive = new Set(keys);
    for (const key of Array.from(expandedKeys)) {
      if (!alive.has(key)) expandedKeys.delete(key);
    }
  }
);

watch(
  () => `${assistant.projectScopeId}:${assistant.worldId}`,
  () => {
    historyVisible.value = false;
    expandedKeys.clear();
  }
);

onBeforeUnmount(() => {
  clearOptimizationTimer();
  clearPreWarningTimer();
  void guidanceService.stop();
});
</script>

<style scoped>
.cabbage-review-root {
  position: absolute;
  left: 12px;
  bottom: 12px;
  z-index: 2147482500;
  display: flex;
  width: min(418px, calc(100% - 24px));
  max-height: min(470px, calc(100% - 92px));
  flex-direction: column;
  align-items: stretch;
  gap: 9px;
  pointer-events: none;
}
.cabbage-review-root > * { pointer-events: auto; }
.cabbage-review-root.resident {
  position: relative;
  left: auto;
  bottom: auto;
  z-index: auto;
  width: 100%;
  max-height: min(470px, 46vh);
  min-height: 0;
  flex: 0 1 470px;
}
.cabbage-review-root.resident .task-board { max-height: 100%; }
.task-board {
  position: relative;
  width: 100%;
  max-height: min(470px, calc(100% - 70px));
  box-sizing: border-box;
  display: flex;
  flex: 1 1 auto;
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
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  min-height: 46px;
  box-sizing: border-box;
  padding: 9px 10px 9px 13px;
  border-bottom: 1px solid #3f3018;
  background: #211d12;
  color: #f2ead5;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .02em;
}
.task-header-actions { display: flex; align-items: center; gap: 8px; }
.history-button {
  border: 1px solid #665025;
  border-radius: 5px;
  background: #302713;
  color: #e5c77f;
  padding: 5px 9px;
  font-size: 11px;
  transition: background .14s ease, border-color .14s ease, color .14s ease;
}
.history-button:hover, .history-button.active { border-color: #d8b86c; background: #57421f; color: #fff7dc; }
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
.task-count.empty { background: #3f3018; color: #b9ad8f; }
.task-empty {
  display: flex;
  min-height: 78px;
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
  padding: 9px;
  scrollbar-width: thin;
  scrollbar-color: #8c6f36 #0b0a08;
}
.task-list::-webkit-scrollbar { width: 7px; }
.task-list::-webkit-scrollbar-track { background: #0b0a08; }
.task-list::-webkit-scrollbar-thumb { border-radius: 999px; background: #8c6f36; }
.task-item + .task-item { margin-top: 7px; }
.task-item {
  overflow: hidden;
  border: 1px solid #3f3018;
  border-radius: 7px;
  background: #15130d;
  transition: border-color .14s ease, background .14s ease;
}
.task-item:hover, .task-item:has(.task-summary.selected) { border-color: #d8b86c; background: #1d190f; }
.task-item.completed { border-color: #51462b; }
.task-summary {
  width: 100%;
  display: block;
  border: 0;
  background: transparent;
  color: #e5e7eb;
  padding: 10px 11px;
  text-align: left;
}
.task-summary-topline { display: flex; align-items: center; gap: 8px; min-width: 0; }
.task-discipline, .task-completed-badge {
  flex: 0 0 auto;
  border: 1px solid;
  border-radius: 999px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
}
.task-discipline.programming { border-color: #6d7f9d; background: #1a2433; color: #b9d2ff; }
.task-discipline.art { border-color: #8d674f; background: #312018; color: #f0c4a4; }
.task-discipline.hint { border-color: #b74747; background: #3a1717; color: #ffb4aa; }
.task-discipline.opinion { border-color: #4f8a72; background: #13271f; color: #a9e7c9; }
.task-item.pre-warning { border-color: #7f3030; background: #211010; }
.task-item.pre-warning:hover, .task-item.pre-warning:has(.task-summary.selected) { border-color: #cf5f52; background: #2a1312; }
.task-item.optimization-opinion { border-color: #315f4c; background: #101d18; }
.task-item.optimization-opinion:hover, .task-item.optimization-opinion:has(.task-summary.selected) { border-color: #57977c; background: #14271f; }
.task-completed-badge { border-color: #637b42; background: #1c2913; color: #c8e6a1; }
.task-title-text { min-width: 0; flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 13px; font-weight: 700; }
.task-chevron { flex: 0 0 auto; color: #9ca3af; transform: rotate(0deg); transition: transform .14s ease; }
.task-chevron.expanded { transform: rotate(180deg); }
.task-introduction {
  display: block;
  margin-top: 8px;
  color: #bdb49d;
  font-size: 12px;
  line-height: 1.55;
  white-space: normal;
  overflow-wrap: anywhere;
}
.task-detail {
  margin: 0 8px 8px;
  border-top: 1px solid #3f3018;
  background: #0f0e0a;
  padding: 10px;
  color: #c9bea0;
  font-size: 12px;
  line-height: 1.65;
}
.task-detail p { margin: 5px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.task-suggestion { border-left: 2px solid #d8b86c; padding-left: 8px; }
.task-suggestion strong { color: #e5c77f; font-size: 11px; }
.task-actions { margin-top: 11px; display: flex; justify-content: flex-end; gap: 7px; }
.showcase-button, .task-discuss {
  border: 1px solid #665025;
  border-radius: 5px;
  color: #fff7dc;
  padding: 5px 9px;
  font-size: 11px;
  transition: background .14s ease, border-color .14s ease;
}
.showcase-button { flex: 0 0 auto; background: #6d5226; }
.showcase-button:hover { border-color: #d8b86c; background: #8c6f36; }
.task-discuss { background: #4b391c; }
.task-discuss:hover { border-color: #b8924a; background: #624b25; }
.task-board-enter-active, .task-board-leave-active { transition: opacity .15s ease, transform .15s ease; transform-origin: center bottom; }
.task-board-enter-from, .task-board-leave-to { opacity: 0; transform: translateY(8px) scale(.98); }

@media (max-width: 720px) {
  .cabbage-review-root { width: min(418px, calc(100% - 24px)); }
}
@media (max-height: 680px) {
  .cabbage-review-root { max-height: calc(100% - 68px); }
  .cabbage-review-root.resident { max-height: min(400px, 44vh); flex-basis: 400px; }
  .task-board { max-height: 100%; }
}
</style>
