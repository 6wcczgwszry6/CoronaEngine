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
        <button type="button" class="history-button" :class="{ active: historyVisible }" @click="toggleHistory">
          {{ historyVisible ? t('cabbageReview.backToTasks') : t('cabbageReview.history') }}
        </button>
      </header>

      <div v-if="historyVisible" class="task-list history-list">
        <article
          v-for="group in historyGroups"
          :key="group.key"
          class="chapter-card"
          :class="[`status-${group.status}`, { current: group.current }]"
        >
          <button type="button" class="chapter-summary" @click="toggleHistoryGroup(group.key)">
            <span class="chapter-summary-main">
              <span class="chapter-title">{{ group.title }}</span>
              <span class="chapter-status" :class="`status-${group.status}`">
                {{ historyStatusLabel(group.status) }}
              </span>
            </span>
            <span v-if="group.summary" class="chapter-description">{{ group.summary }}</span>
            <span class="chapter-summary-meta">
              <span>{{ group.completedCount }}/{{ group.total }}</span>
              <span v-if="group.completedAt">
                {{ t('cabbageReview.chapterCompletedAt') }} {{ formatTimestamp(group.completedAt) }}
              </span>
              <span class="task-chevron" :class="{ expanded: expandedHistoryGroups.has(group.key) }">&#8964;</span>
            </span>
          </button>

          <div v-if="expandedHistoryGroups.has(group.key)" class="chapter-steps">
            <div v-if="group.tasks.length" class="chapter-step-list">
              <article
                v-for="task in group.tasks"
                :key="historyTaskKey(task)"
                class="chapter-step"
                :class="{ expanded: expandedHistoryTasks.has(historyRowKey(group, task)) }"
              >
                <button
                  type="button"
                  class="chapter-step-summary"
                  @click="toggleHistoryTask(group, task)"
                >
                  <span class="chapter-step-order">{{ historyTaskOrder(task) }}</span>
                  <span class="chapter-step-content">
                    <strong>{{ localizedTaskField(task, 'title') }}</strong>
                    <small>
                      {{ taskCompletionTimestamp(task)
                        ? `${t('cabbageReview.stepCompletedAt')} ${formatTimestamp(taskCompletionTimestamp(task))}`
                        : t('cabbageReview.notCompleted') }}
                    </small>
                  </span>
                  <span class="chapter-step-check">
                    <span v-if="taskCompletionTimestamp(task)">&#10003;</span>
                    <span v-else>&#8226;</span>
                  </span>
                  <span
                    class="task-chevron"
                    :class="{ expanded: expandedHistoryTasks.has(historyRowKey(group, task)) }"
                  >&#8964;</span>
                </button>
                <div
                  v-if="expandedHistoryTasks.has(historyRowKey(group, task))"
                  class="chapter-step-detail"
                >
                  <p class="history-task-description">{{ taskDescription(task) }}</p>
                  <div class="task-suggestion">
                    <strong>{{ t('cabbageReview.howToComplete') }}</strong>
                    <p>{{ completionText(task) }}</p>
                  </div>
                  <div class="task-actions">
                    <button type="button" class="showcase-button" @click="showcase(task)">
                      {{ t('cabbageReview.showcase') }}
                    </button>
                    <button type="button" class="task-discuss" @click="openChat(task)">
                      {{ t('cabbageReview.continueDiscussion') }}
                    </button>
                  </div>
                </div>
              </article>
            </div>
            <div v-else class="chapter-empty">{{ t('cabbageReview.noChapterRecords') }}</div>
          </div>
        </article>

        <div v-if="!historyGroups.length" class="task-empty" aria-live="polite">
          <span class="task-empty-icon">✓</span>
          <span>{{ t('cabbageReview.emptyHistory') }}</span>
        </div>
      </div>

      <div v-else-if="completionNoticeVisible" class="task-list state-list">
        <article class="completion-card" :class="{ fading: completionNoticeFading }" aria-live="polite">
          <span class="completion-icon">✓</span>
          <strong>{{ t('cabbageReview.completionNotice') }}</strong>
        </article>
      </div>

      <div v-else-if="activeCards.length" class="task-list">
        <article
          v-for="(task, index) in activeCards"
          :key="activeRowKey(task, index)"
          class="task-item"
          :class="{
            tutorial: isBasicTutorial(task),
            'pre-warning': task.type === 'pre-warning',
            'optimization-opinion': task.type === 'optimization-tip',
          }"
        >
          <div v-if="isBasicTutorial(task)" class="tutorial-progress-head">
            <strong>{{ localizedTaskField(task, 'chapterTitle') }}</strong>
            <div class="tutorial-progress-lines">
              <span>{{ t('cabbageReview.overallProgress', { current: task.globalOrder, total: tutorialTotal }) }}</span>
              <span>{{ t('cabbageReview.chapterProgress', { current: task.chapterTaskOrder, total: chapterTotal(task.chapterKey) }) }}</span>
            </div>
          </div>

          <button
            type="button"
            class="task-summary"
            :class="{ selected: assistant.selectedTaskKey === taskKey(task) }"
            @click="toggleTask(task, index)"
          >
            <span class="task-summary-topline">
              <span v-if="transientLabel(task)" class="task-kind" :class="transientClass(task)">
                {{ transientLabel(task) }}
              </span>
              <span class="task-title-text">{{ localizedTaskField(task, 'title') }}</span>
              <span class="task-chevron" :class="{ expanded: expandedKeys.has(activeRowKey(task, index)) }">&#8964;</span>
            </span>
            <span class="task-introduction">{{ taskDescription(task) }}</span>
          </button>

          <div v-if="expandedKeys.has(activeRowKey(task, index))" class="task-detail">
            <div class="task-suggestion">
              <strong>{{ t('cabbageReview.howToComplete') }}</strong>
              <p>{{ completionText(task) }}</p>
            </div>
            <div class="task-actions">
              <button type="button" class="showcase-button" @click="showcase(task)">{{ t('cabbageReview.showcase') }}</button>
              <button type="button" class="task-discuss" @click="openChat(task)">{{ t('cabbageReview.continueDiscussion') }}</button>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="task-empty" aria-live="polite">
        <span class="task-empty-icon">✓</span>
        <span>{{ t('cabbageReview.emptyActive') }}</span>
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
import { cabbageContextService, publishCabbageAssistantContext } from '@/services/cabbageAssistantContextService.js';
import { guidanceService } from '@/services/cabbageGuidanceService.js';
import { translateUiText } from '@/i18n/domTranslator.js';

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  attentionToken: { type: Number, default: 0 },
  resident: { type: Boolean, default: false },
});

const TUTORIAL_TOTAL = 39;
const CHAPTER_TOTALS = Object.freeze({
  chapter_viewport: 6,
  chapter_scene: 9,
  chapter_nodes: 20,
  chapter_ai: 4,
});
const REMOVED_TUTORIAL_TASK_KEYS = new Set([
  'tutorial.basics.start_preview',
  'tutorial.basics.stop_preview',
  'tutorial.basics.add_wait',
  'tutorial.basics.set_wait_seconds',
  'tutorial.basics.select_edge',
  'tutorial.basics.add_true_condition',
  'tutorial.basics.choose_select_tool',
  'tutorial.basics.choose_clear_tool',
]);
const NOTICE_FADE_MS = 650;
const { t, locale } = useI18n();
const dockStore = useDockStore();
const assistant = useCabbageAssistantStore();
const expandedKeys = reactive(new Set());
const expandedHistoryGroups = reactive(new Set());
const expandedHistoryTasks = reactive(new Set());
const historyVisible = ref(false);
const completionClock = ref(Date.now());
const completionNoticeFading = ref(false);
let optimizationTimer = null;
let preWarningTimer = null;
let completionFadeTimer = null;
let completionExpireTimer = null;
let completionDismissRequestKey = '';

const tutorialTotal = computed(() => {
  const maximum = assistant.activeTasks.concat(assistant.taskHistory).filter(isBasicTutorial)
    .reduce((value, task) => Math.max(value, Number(task.globalOrder) || 0), 0);
  return Math.max(TUTORIAL_TOTAL, maximum);
});
const tutorialStatus = computed(() => String(assistant.tutorialSession?.status || ''));
const completionNoticeExpiresAt = computed(() => Math.max(0, Number(assistant.tutorialSession?.completionNoticeExpiresAt) || 0));

const preWarningTask = computed(() => {
  const warning = assistant.preWarning;
  if (!warning) return null;
  const key = String(warning.taskKey || warning.warningKey || `pre-warning:${warning.code || 'issue'}`);
  return { ...warning, taskKey: key, issueKey: key, type: 'pre-warning', status: 'active', transient: true, suggestion: String(warning.suggestion || warning.message || '') };
});
const optimizationTask = computed(() => {
  const tip = assistant.ephemeralTip;
  if (!tip) return null;
  const key = String(tip.taskKey || `optimization:${tip.graphRevision || 'graph'}:${tip.tipKey || 'tip'}`);
  return { ...tip, taskKey: key, issueKey: key, type: 'optimization-tip', status: 'active', transient: true, suggestion: String(tip.suggestion || tip.message || '') };
});
const activeCards = computed(() => [preWarningTask.value, optimizationTask.value, ...props.tasks].filter(Boolean));
const activeWorldTasks = computed(() => assistant.activeTasks.filter((task) => task.type === 'goal' && ['active', 'pending'].includes(String(task.status || ''))));
const completionNoticeVisible = computed(() => tutorialStatus.value === 'completed'
  && completionNoticeExpiresAt.value > completionClock.value && activeCards.value.length === 0);

const basicTaskCatalog = computed(() => {
  const tasksByKey = new Map();
  for (const task of [...assistant.activeTasks, ...assistant.taskHistory]) {
    if (!isBasicTutorial(task)) continue;
    const key = taskKey(task);
    const previous = tasksByKey.get(key);
    if (!previous || taskCompletionTimestamp(task) >= taskCompletionTimestamp(previous)) tasksByKey.set(key, task);
  }
  return [...tasksByKey.values()].sort((left, right) => Number(left.globalOrder || left.order) - Number(right.globalOrder || right.order));
});
const currentTutorialTask = computed(() => assistant.activeTasks.find((task) => isBasicTutorial(task) && task.status === 'active') || null);
const completedBasicTasks = computed(() => assistant.taskHistory
  .filter((task) => isBasicTutorial(task) && taskCompletionTimestamp(task) > 0)
  .slice().sort((left, right) => Number(left.globalOrder || left.order) - Number(right.globalOrder || right.order)));

const chapterGroups = computed(() => {
  const chapterMap = new Map();
  for (const task of basicTaskCatalog.value) {
    const key = String(task.chapterKey || '');
    if (!key) continue;
    if (!chapterMap.has(key)) chapterMap.set(key, { key, order: Number(task.chapterOrder) || 0, titleTask: task });
  }
  const currentKey = String(currentTutorialTask.value?.chapterKey || '');
  return [...chapterMap.values()].sort((left, right) => left.order - right.order).map((chapter) => {
    const tasks = completedBasicTasks.value.filter((task) => task.chapterKey === chapter.key);
    const total = chapterTotal(chapter.key);
    const completedCount = Math.min(total, tasks.length);
    const finalChapter = chapter.key === 'chapter_ai';
    let status = completedCount >= total ? 'cleared' : (chapter.key === currentKey ? 'in_progress' : 'not_started');
    const completedAt = status === 'cleared'
      ? (finalChapter ? Number(assistant.tutorialSession?.completedAt) || Number(assistant.tutorialSession?.restoredAt) || latestCompletion(tasks) : latestCompletion(tasks))
      : 0;
    return {
      key: chapter.key,
      title: localizedTaskField(chapter.titleTask, 'chapterTitle'),
      summary: localizedTaskField(chapter.titleTask, 'chapterSummary'),
      total,
      completedCount,
      completedAt,
      tasks,
      status,
      current: chapter.key === currentKey,
    };
  });
});

const legacyTutorialGroup = computed(() => {
  const tasks = assistant.taskHistory.filter((task) => task.type === 'tutorial' && !isBasicTutorial(task)).slice().sort(sortHistoryRecords);
  if (!tasks.length) return null;
  return {
    key: 'legacy-tutorial', title: t('cabbageReview.legacyTutorial'), summary: t('cabbageReview.legacyTutorialDescription'),
    total: tasks.length, completedCount: tasks.filter((task) => taskCompletionTimestamp(task) > 0).length,
    completedAt: latestCompletion(tasks), tasks, status: 'archived', current: false,
  };
});
const otherHistoryGroup = computed(() => {
  const tasks = assistant.taskHistory.filter((task) => task.type !== 'tutorial').slice().sort(sortHistoryRecords);
  if (!tasks.length) return null;
  return {
    key: 'other-records', title: t('cabbageReview.otherRecords'), summary: t('cabbageReview.otherRecordsDescription'),
    total: tasks.length, completedCount: tasks.filter((task) => taskCompletionTimestamp(task) > 0).length,
    completedAt: latestCompletion(tasks), tasks, status: 'archived', current: false,
  };
});
const historyGroups = computed(() => [...chapterGroups.value, legacyTutorialGroup.value, otherHistoryGroup.value].filter(Boolean));

function taskKey(task) { return String(task?.taskKey || task?.issueKey || ''); }
function isBasicTutorial(task) {
  const key = taskKey(task);
  return task?.type === 'tutorial' && key.startsWith('tutorial.basics.') && !REMOVED_TUTORIAL_TASK_KEYS.has(key);
}
function chapterTotal(chapterKey) {
  const catalogCount = basicTaskCatalog.value.filter((task) => task.chapterKey === chapterKey).length;
  return Math.max(Number(CHAPTER_TOTALS[chapterKey]) || 0, catalogCount);
}
function taskCompletionTimestamp(task) {
  return Math.max(
    Number(task?.completedAt) || 0,
    Number(task?.resolvedAt) || 0,
    ['completed', 'resolved'].includes(String(task?.status || ''))
      ? Number(task?.updatedAt) || 0
      : 0
  );
}
function latestCompletion(tasks) { return tasks.reduce((value, task) => Math.max(value, taskCompletionTimestamp(task)), 0); }
function sortHistoryRecords(left, right) { return taskCompletionTimestamp(right) - taskCompletionTimestamp(left); }
function activeRowKey(task, index = 0) { return `active:${taskKey(task) || `task_${index}`}`; }
function historyTaskKey(task) { return `${taskKey(task)}:${taskCompletionTimestamp(task)}`; }
function historyRowKey(group, task) { return `${group?.key || 'history'}:${historyTaskKey(task)}`; }
function historyTaskOrder(task) { return Number(task.chapterTaskOrder || task.globalOrder || task.order) || '·'; }
function localizedTaskField(task, field) {
  const source = String(task?.[field] || '');
  if (locale.value !== 'en-US') return source;
  const english = String(task?.[`${field}En`] || '').trim();
  return english || translateUiText(source);
}
function taskDescription(task) {
  return localizedTaskField(task, 'message') || localizedTaskField(task, 'completionCriteria') || t('cabbageReview.descriptionFallback');
}
function completionText(task) {
  return localizedTaskField(task, 'suggestion') || localizedTaskField(task, 'completionCriteria')
    || localizedTaskField(task, 'message') || t('cabbageReview.completionFallback');
}
function transientLabel(task) {
  if (task?.type === 'pre-warning') return t('cabbageReview.reminder');
  if (task?.type === 'optimization-tip') return t('cabbageReview.suggestion');
  return '';
}
function transientClass(task) { return task?.type === 'pre-warning' ? 'reminder' : 'suggestion'; }
function historyStatusLabel(status) {
  const labels = {
    in_progress: 'cabbageReview.inProgress', cleared: 'cabbageReview.chapterCleared',
    not_started: 'cabbageReview.notStarted', archived: 'cabbageReview.archived',
  };
  return t(labels[status] || labels.archived);
}
function formatTimestamp(timestamp) {
  const value = Number(timestamp) || 0;
  if (!value) return '';
  try {
    return new Intl.DateTimeFormat(locale.value === 'en-US' ? 'en-US' : 'zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    }).format(new Date(value));
  } catch (_) { return new Date(value).toLocaleString(); }
}
function clearOptimizationTimer() { if (optimizationTimer) window.clearTimeout(optimizationTimer); optimizationTimer = null; }
function clearPreWarningTimer() { if (preWarningTimer) window.clearTimeout(preWarningTimer); preWarningTimer = null; }
function clearCompletionTimers() {
  if (completionFadeTimer) window.clearTimeout(completionFadeTimer);
  if (completionExpireTimer) window.clearTimeout(completionExpireTimer);
  completionFadeTimer = null;
  completionExpireTimer = null;
  completionNoticeFading.value = false;
}
function scheduleCompletionNotice() {
  clearCompletionTimers();
  completionClock.value = Date.now();
  const remaining = completionNoticeExpiresAt.value - completionClock.value;
  if (tutorialStatus.value !== 'completed' || remaining <= 0) return;
  if (remaining <= NOTICE_FADE_MS) completionNoticeFading.value = true;
  else completionFadeTimer = window.setTimeout(() => { completionNoticeFading.value = true; }, remaining - NOTICE_FADE_MS);
  completionExpireTimer = window.setTimeout(() => {
    completionClock.value = Date.now();
    completionNoticeFading.value = false;
  }, remaining + 20);
}
function showcase(task) {
  const bindings = assistant.tutorialSession?.bindings || {};
  void guidanceService.start({
    ...task,
    sourceType: task.type,
    title: localizedTaskField(task, 'title'),
    guidanceText: completionText(task),
    bindings: { ...bindings },
  });
}
function toggleHistory() {
  historyVisible.value = !historyVisible.value;
  expandedKeys.clear();
  if (!historyVisible.value) return;
  expandedHistoryGroups.clear();
  expandedHistoryTasks.clear();
  const current = historyGroups.value.find((group) => group.current);
  if (current) expandedHistoryGroups.add(current.key);
}
function toggleHistoryGroup(key) {
  if (expandedHistoryGroups.has(key)) expandedHistoryGroups.delete(key);
  else expandedHistoryGroups.add(key);
}
function toggleHistoryTask(group, task) {
  const key = historyRowKey(group, task);
  if (expandedHistoryTasks.has(key)) expandedHistoryTasks.delete(key);
  else expandedHistoryTasks.add(key);
  assistant.selectTask(taskKey(task));
}
function toggleTask(task, index) {
  const key = activeRowKey(task, index);
  if (expandedKeys.has(key)) expandedKeys.delete(key); else expandedKeys.add(key);
  assistant.selectTask(taskKey(task));
}
async function openChat(task) {
  assistant.selectTask(taskKey(task));
  publishCabbageAssistantContext(assistant);
  if (props.resident) {
    window.dispatchEvent(new CustomEvent('cabbage-chat-focus-request', { detail: { taskKey: taskKey(task) } }));
    return;
  }
  const panelId = 'CabbageChatPanel';
  const panel = dockStore.panels[panelId];
  if (!panel) return;
  if (panel.open && panel.mode === 'external') await closeFloatingPanel(dockStore, panelId);
  dockStore.popIn(panelId);
  dockStore.setDockZone(panelId, 'right');
  dockStore.openPanel(panelId);
  const rightIds = dockStore.panelsByZone('right').map((item) => item.id).filter((id) => id !== panelId);
  const aiTalkIndex = rightIds.indexOf('AITalkBar');
  const beforeId = aiTalkIndex >= 0 ? (rightIds[aiTalkIndex + 1] || null) : null;
  dockStore.movePanel(panelId, 'right', beforeId);
  window.dispatchEvent(new Event('resize'));
}

watch(() => assistant.ephemeralTip?.expiresAt || 0, (expiresAt) => {
  clearOptimizationTimer();
  if (!expiresAt) return;
  optimizationTimer = window.setTimeout(() => assistant.clearOptimizationTip(), Math.max(0, Number(expiresAt) - Date.now()));
}, { immediate: true });
watch(() => assistant.preWarning?.expiresAt || 0, (expiresAt) => {
  clearPreWarningTimer();
  if (!expiresAt) return;
  preWarningTimer = window.setTimeout(() => assistant.clearPreWarning(), Math.max(0, Number(expiresAt) - Date.now()));
}, { immediate: true });
watch(
  () => `${tutorialStatus.value}:${completionNoticeExpiresAt.value}:${assistant.projectScopeId}:${assistant.worldId}`,
  scheduleCompletionNotice,
  { immediate: true }
);
watch(
  () => `${assistant.projectScopeId}:${assistant.worldId}:${completionNoticeExpiresAt.value}:${activeWorldTasks.value.map(taskKey).join(',')}`,
  () => {
    const expiresAt = completionNoticeExpiresAt.value;
    if (!activeWorldTasks.value.length || tutorialStatus.value !== 'completed' || expiresAt <= Date.now()) return;
    const requestKey = `${assistant.projectScopeId}:${assistant.worldId}:${expiresAt}`;
    if (completionDismissRequestKey === requestKey) return;
    completionDismissRequestKey = requestKey;
    void cabbageContextService.recordEvent({
      type: 'tutorial_completion_notice_dismissed', category: 'tutorial', success: true,
      details: { sessionId: String(assistant.tutorialSession?.sessionId || '') },
    });
  },
  { immediate: true }
);
watch(() => activeCards.value.map((task, index) => activeRowKey(task, index)), (keys) => {
  const alive = new Set(keys);
  for (const key of Array.from(expandedKeys)) if (!alive.has(key)) expandedKeys.delete(key);
  if (keys.length === 1 && !expandedKeys.size) expandedKeys.add(keys[0]);
}, { immediate: true });
watch(() => `${assistant.projectScopeId}:${assistant.worldId}`, () => {
  historyVisible.value = false;
  expandedKeys.clear();
  expandedHistoryGroups.clear();
  expandedHistoryTasks.clear();
  completionDismissRequestKey = '';
  clearCompletionTimers();
  scheduleCompletionNotice();
});
onBeforeUnmount(() => {
  clearOptimizationTimer();
  clearPreWarningTimer();
  clearCompletionTimers();
  void guidanceService.stop();
});
</script>
<style scoped>
.cabbage-review-root {
  position: absolute; left: 12px; bottom: 12px; z-index: 2147482500; display: flex;
  width: min(430px, calc(100% - 24px)); max-height: min(520px, calc(100% - 92px));
  flex-direction: column; align-items: stretch; pointer-events: none;
}
.cabbage-review-root > * { pointer-events: auto; }
.cabbage-review-root.resident {
  position: relative; left: auto; bottom: auto; z-index: auto; width: 100%; max-height: min(520px, 50vh);
  min-height: 0; flex: 0 1 520px;
}
.cabbage-review-root.resident .task-board { max-height: 100%; }
.task-board {
  position: relative; width: 100%; max-height: min(520px, calc(100% - 70px)); box-sizing: border-box;
  display: flex; flex: 1 1 auto; flex-direction: column; overflow: hidden; border: 1px solid #55431f;
  border-left: 3px solid #b8924a; border-radius: 9px; background: #11100d; color: #f2ead5;
  box-shadow: 0 18px 46px rgba(0, 0, 0, .62), 0 0 0 1px rgba(216, 184, 108, .08);
}
.task-board-header {
  display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; min-height: 46px;
  box-sizing: border-box; padding: 9px 10px 9px 13px; border-bottom: 1px solid #3f3018;
  background: #211d12; color: #f2ead5; font-size: 14px; font-weight: 700; letter-spacing: .02em;
}
.history-button {
  border: 1px solid #665025; border-radius: 5px; background: #302713; color: #e5c77f;
  padding: 5px 10px; font-size: 12px; transition: background .14s ease, border-color .14s ease, color .14s ease;
}
.history-button:hover, .history-button.active { border-color: #d8b86c; background: #57421f; color: #fff7dc; }
.task-list {
  min-height: 0; flex: 1 1 auto; overflow-y: auto; padding: 9px;
  scrollbar-width: thin; scrollbar-color: #8c6f36 #0b0a08;
}
.task-list::-webkit-scrollbar { width: 7px; }
.task-list::-webkit-scrollbar-track { background: #0b0a08; }
.task-list::-webkit-scrollbar-thumb { border-radius: 999px; background: #8c6f36; }
.task-item + .task-item, .chapter-card + .chapter-card { margin-top: 8px; }
.task-item {
  overflow: hidden; border: 1px solid #3f3018; border-radius: 8px; background: #15130d;
  transition: border-color .14s ease, background .14s ease;
}
.task-item:hover, .task-item:has(.task-summary.selected) { border-color: #d8b86c; background: #1d190f; }
.task-item.tutorial { border-color: #806329; box-shadow: inset 0 1px rgba(242, 207, 115, .05); }
.task-item.pre-warning { border-color: #7f3030; background: #211010; }
.task-item.optimization-opinion { border-color: #315f4c; background: #101d18; }
.tutorial-progress-head { padding: 10px 11px 9px; border-bottom: 1px solid #49391d; background: linear-gradient(135deg, #302713, #1b170e); }
.tutorial-progress-head > strong { display: block; color: #f4dc9b; font-size: 13px; line-height: 1.4; }
.tutorial-progress-lines { display: flex; flex-wrap: wrap; gap: 6px 12px; margin-top: 7px; color: #bfb08b; font-size: 11px; }
.task-summary { width: 100%; display: block; border: 0; background: transparent; color: #e5e7eb; padding: 10px 11px; text-align: left; }
.task-summary-topline { display: flex; align-items: center; gap: 8px; min-width: 0; }
.task-kind {
  flex: 0 0 auto; border: 1px solid; border-radius: 999px; padding: 2px 7px;
  font-size: 11px; font-weight: 700; line-height: 1.2;
}
.task-kind.reminder { border-color: #b74747; background: #3a1717; color: #ffb4aa; }
.task-kind.suggestion { border-color: #4f8a72; background: #13271f; color: #a9e7c9; }
.task-title-text { min-width: 0; flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font-size: 14px; font-weight: 700; }
.task-chevron { flex: 0 0 auto; color: #9ca3af; transform: rotate(0deg); transition: transform .14s ease; }
.task-chevron.expanded { transform: rotate(180deg); }
.task-introduction { display: block; margin-top: 8px; color: #bdb49d; font-size: 13px; line-height: 1.55; white-space: normal; overflow-wrap: anywhere; }
.task-detail {
  margin: 0 8px 8px; border-top: 1px solid #3f3018; background: #0f0e0a; padding: 10px;
  color: #c9bea0; font-size: 13px; line-height: 1.65;
}
.task-detail p { margin: 5px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.task-suggestion { border-left: 2px solid #d8b86c; padding-left: 8px; }
.task-suggestion strong { color: #e5c77f; font-size: 12px; }
.task-actions { margin-top: 11px; display: flex; justify-content: flex-end; gap: 7px; }
.showcase-button, .task-discuss {
  border: 1px solid #665025; border-radius: 5px; color: #fff7dc; padding: 6px 10px; font-size: 12px;
  transition: background .14s ease, border-color .14s ease, opacity .14s ease;
}
.showcase-button { background: #6d5226; }
.showcase-button:hover { border-color: #d8b86c; background: #8c6f36; }
.task-discuss { background: #4b391c; }
.task-discuss:hover { border-color: #b8924a; background: #624b25; }
.task-empty {
  display: flex; min-height: 90px; align-items: center; justify-content: center; gap: 8px;
  padding: 12px; color: #9d9278; font-size: 13px; text-align: center;
}
.task-empty-icon {
  display: grid; width: 22px; height: 22px; place-items: center; border: 1px solid #665025;
  border-radius: 50%; color: #d8b86c; font-size: 12px;
}
.state-list { display: flex; align-items: stretch; }
.completion-card {
  width: 100%; min-height: 118px; box-sizing: border-box; display: flex; align-items: center; gap: 13px;
  border: 1px solid #665025; border-radius: 9px; padding: 16px; background: #17140d;
}
.completion-icon {
  flex: 0 0 auto; display: grid; width: 36px; height: 36px; place-items: center;
  border: 1px solid currentColor; border-radius: 50%; color: #d8b86c; font-size: 20px; font-weight: 800;
}
.completion-card {
  justify-content: center; border-color: #6f8d42;
  background: radial-gradient(circle at top, rgba(124, 157, 73, .23), transparent 62%), #13190d;
  color: #dff1ba; text-align: center; opacity: 1; transform: translateY(0);
  transition: opacity .65s ease, transform .65s ease;
}
.completion-card strong { max-width: 290px; font-size: 16px; line-height: 1.55; }
.completion-card .completion-icon { color: #bde37e; }
.completion-card.fading { opacity: 0; transform: translateY(6px); }
.chapter-card { overflow: hidden; border: 1px solid #3f3018; border-radius: 8px; background: #15130d; }
.chapter-card.current { border-color: #a17c35; }
.chapter-card.status-cleared { border-color: #526737; }
.chapter-summary { width: 100%; border: 0; background: transparent; color: inherit; padding: 11px; text-align: left; }
.chapter-summary-main, .chapter-summary-meta { display: flex; align-items: center; gap: 8px; }
.chapter-title { min-width: 0; flex: 1; color: #ece1c5; font-size: 13px; font-weight: 750; }
.chapter-status {
  flex: 0 0 auto; border: 1px solid #5b4d2e; border-radius: 999px; padding: 2px 7px;
  color: #b9ad8f; font-size: 10px; font-weight: 700;
}
.chapter-status.status-in_progress { border-color: #9b7833; color: #f0ce7d; }
.chapter-status.status-cleared { border-color: #657d43; color: #c9e6a3; }
.chapter-description { display: block; margin-top: 7px; color: #a79d87; font-size: 12px; line-height: 1.45; }
.chapter-summary-meta { margin-top: 8px; color: #897f6a; font-size: 10px; }
.chapter-summary-meta .task-chevron { margin-left: auto; }
.chapter-steps { border-top: 1px solid #352a17; padding: 8px; background: #0e0d09; }
.chapter-step-list { display: flex; flex-direction: column; gap: 5px; }
.chapter-step { overflow: hidden; border: 1px solid #292317; border-radius: 6px; background: #15130d; }
.chapter-step.expanded { border-color: #58451f; background: #19160e; }
.chapter-step-summary {
  width: 100%; display: flex; align-items: center; gap: 8px; border: 0; padding: 8px;
  background: transparent; color: inherit; text-align: left;
}
.chapter-step-summary:hover { background: rgba(216, 184, 108, .045); }
.chapter-step-order {
  flex: 0 0 auto; display: grid; width: 22px; height: 22px; place-items: center;
  border-radius: 50%; background: #302713; color: #d9bd78; font-size: 10px;
}
.chapter-step-content { min-width: 0; flex: 1; }
.chapter-step-content strong { display: block; color: #d8cfb7; font-size: 12px; font-weight: 650; }
.chapter-step-content small { display: block; margin-top: 3px; color: #776f5e; font-size: 10px; }
.chapter-step-check { flex: 0 0 auto; color: #9fc66c; font-size: 13px; }
.chapter-step-summary .task-chevron { flex: 0 0 auto; }
.chapter-step-detail { border-top: 1px solid #302817; padding: 9px 10px 10px 40px; background: #100f0a; }
.history-task-description { margin: 0 0 9px; color: #bdb49d; font-size: 12px; line-height: 1.55; }
.chapter-step-detail .task-suggestion { margin-top: 0; }
.chapter-step-detail .task-actions { margin-top: 9px; }
.chapter-empty { padding: 13px 8px; color: #746c5c; font-size: 11px; text-align: center; }
@media (max-width: 720px) { .cabbage-review-root { width: min(430px, calc(100% - 24px)); } }
@media (max-height: 680px) {
  .cabbage-review-root { max-height: calc(100% - 68px); }
  .cabbage-review-root.resident { max-height: min(430px, 46vh); flex-basis: 430px; }
  .task-board { max-height: 100%; }
}
</style>
