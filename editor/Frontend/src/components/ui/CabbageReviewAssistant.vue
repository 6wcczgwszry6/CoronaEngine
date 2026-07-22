<template>
  <Teleport to="body">
    <div
      class="cabbage-review-root"
      @mousedown.stop
      @pointerdown.stop
      @click.stop
      @wheel.stop
    >
      <transition name="task-board">
        <section v-if="tasks.length" class="task-board" aria-label="节点问题任务">
          <header class="task-board-header">
            <span>待处理节点问题</span>
            <span class="task-count">{{ tasks.length }}</span>
          </header>
          <div class="task-list">
            <article v-for="task in tasks" :key="task.issueKey" class="task-item">
              <button
                type="button"
                class="task-title"
                :class="{ selected: assistant.selectedTaskKey === task.issueKey }"
                @click="toggleTask(task)"
              >
                <span class="task-dot"></span>
                <span class="task-title-text">{{ task.title }}</span>
                <span class="task-chevron" :class="{ expanded: expandedKeys.has(task.issueKey) }">⌄</span>
              </button>
              <div v-if="expandedKeys.has(task.issueKey)" class="task-detail">
                <p v-if="task.message">{{ task.message }}</p>
                <div v-if="task.suggestion" class="task-suggestion">
                  <strong>这样修改</strong>
                  <p>{{ task.suggestion }}</p>
                </div>
                <button type="button" class="task-discuss" @click="openChat(task)">和包菜继续讨论</button>
              </div>
            </article>
          </div>
        </section>
      </transition>

      <button
        type="button"
        class="cabbage-button"
        :class="{ active: chatOpen }"
        :title="chatOpen ? '关闭包菜答疑' : '打开包菜答疑'"
        :aria-pressed="chatOpen"
        @click="toggleChat"
      >
        <img src="@/assets/cabbage.png" alt="包菜答疑" />
        <span v-if="tasks.length" class="cabbage-badge">{{ tasks.length > 99 ? '99+' : tasks.length }}</span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';
import { useCabbageAssistantStore } from '@/stores/cabbageAssistantStore.js';
import { openFloatingPanel, toggleFloatingPanel } from '@/utils/panelWindows.js';

const props = defineProps({
  tasks: { type: Array, default: () => [] },
  attentionToken: { type: Number, default: 0 },
});

const dockStore = useDockStore();
const assistant = useCabbageAssistantStore();
const expandedKeys = reactive(new Set());
const chatOpen = computed(() => Boolean(dockStore.panels.CabbageChatPanel?.open));

function toggleTask(task) {
  assistant.selectTask(task.issueKey);
  if (expandedKeys.has(task.issueKey)) expandedKeys.delete(task.issueKey);
  else expandedKeys.add(task.issueKey);
}

async function toggleChat() {
  await toggleFloatingPanel(dockStore, 'CabbageChatPanel');
}

async function openChat(task) {
  assistant.selectTask(task.issueKey);
  await openFloatingPanel(dockStore, 'CabbageChatPanel');
}

watch(
  () => props.tasks.map((task) => task.issueKey),
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
  position: fixed;
  right: 16px;
  top: 50%;
  z-index: 2147483645;
  display: flex;
  align-items: center;
  gap: 10px;
  transform: translateY(-50%);
  pointer-events: auto;
}
.task-board {
  width: min(360px, calc(100vw - 112px));
  max-height: min(430px, calc(100vh - 72px));
  overflow: hidden;
  border: 1px solid #444b45;
  border-radius: 8px;
  background: #242824;
  color: #e5e9e4;
  box-shadow: 0 16px 44px rgba(0, 0, 0, .58);
}
.task-board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #3d443e;
  background: #2d322e;
  color: #dce6d7;
  font-size: 13px;
  font-weight: 600;
}
.task-count {
  min-width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #7d5d24;
  color: #fff3c8;
  font-size: 11px;
}
.task-list { max-height: 380px; overflow-y: auto; padding: 6px; }
.task-item + .task-item { margin-top: 5px; }
.task-title {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #3e4540;
  border-radius: 6px;
  background: #2b302c;
  color: #e5e7eb;
  padding: 9px 10px;
  text-align: left;
  transition: background .14s ease, border-color .14s ease;
}
.task-title:hover, .task-title.selected { border-color: #718663; background: #343c32; }
.task-dot { width: 8px; height: 8px; flex:0 0 auto; border-radius:50%; background:#f0ad3d; box-shadow:0 0 8px rgba(240,173,61,.35); }
.task-title-text { min-width:0; flex:1; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; font-size:13px; font-weight:600; }
.task-chevron { color:#9ca3af; transform:rotate(0deg); transition:transform .14s ease; }
.task-chevron.expanded { transform:rotate(180deg); }
.task-detail { margin:-1px 5px 0; border:1px solid #3e4540; border-top:0; border-radius:0 0 6px 6px; background:#202421; padding:10px; color:#cbd2c9; font-size:12px; line-height:1.65; }
.task-detail p { white-space:pre-wrap; overflow-wrap:anywhere; }
.task-suggestion { margin-top:8px; border-left:2px solid #83a36b; padding-left:8px; }
.task-suggestion strong { color:#aaca92; font-size:11px; }
.task-discuss { margin-top:9px; border-radius:5px; background:#526847; color:#eef8e8; padding:5px 9px; font-size:11px; }
.cabbage-button {
  position: relative;
  width: 66px;
  height: 66px;
  flex: 0 0 auto;
  overflow: visible;
  border: 2px solid rgba(110, 231, 183, .72);
  border-radius: 50%;
  background: #b8de93;
  box-shadow: 0 10px 32px rgba(16, 185, 129, .32);
  transition: transform .16s ease, border-color .16s ease;
}
.cabbage-button:hover, .cabbage-button.active { transform:scale(1.05); border-color:#d1fae5; }
.cabbage-button img { width:100%; height:100%; border-radius:50%; object-fit:cover; }
.cabbage-badge { position:absolute; right:-3px; top:-4px; min-width:22px; height:22px; display:grid; place-items:center; border:2px solid #1b211c; border-radius:999px; background:#e89a2e; color:white; padding:0 4px; font-size:10px; font-weight:700; }
.task-board-enter-active, .task-board-leave-active { transition: opacity .15s ease, transform .15s ease; transform-origin:right center; }
.task-board-enter-from, .task-board-leave-to { opacity:0; transform:translateX(8px) scale(.98); }
</style>
