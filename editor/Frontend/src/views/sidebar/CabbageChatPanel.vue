<template>
  <div class="cabbage-chat-shell flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden rounded-lg relative">
    <DockTitleBar
      v-if="!isDocked"
      title="包菜答疑"
      extraClass="bg-[#84A65B] rounded-t-md"
      routePath="/CabbageChat"
      @close="closeFloat"
    />

    <div class="context-strip">
      <div class="context-title">当前节点问题</div>
      <select v-model="selectedKey" :disabled="!assistant.tasks.length" class="context-select">
        <option value="">{{ assistant.tasks.length ? '全部未解决问题' : '当前没有未解决问题' }}</option>
        <option v-for="task in assistant.tasks" :key="task.issueKey" :value="task.issueKey">
          {{ task.title }}
        </option>
      </select>
      <span class="context-count">{{ assistant.tasks.length }}</span>
    </div>

    <div ref="historyRef" class="chat-history">
      <div v-if="!assistant.messages.length" class="chat-empty">
        <img src="@/assets/cabbage.png" alt="" />
        <strong>继续问包菜</strong>
        <p>可以询问当前节点问题为什么发生、积木应该接在哪里，或怎样确认已经修好。</p>
      </div>
      <article
        v-for="message in assistant.messages"
        :key="message.id"
        class="chat-message"
        :class="message.role"
      >
        <div class="chat-role">{{ message.role === 'assistant' ? '包菜' : '你' }}</div>
        <div class="chat-content">{{ message.content }}</div>
      </article>
      <article v-if="streamingContent" class="chat-message assistant streaming">
        <div class="chat-role">包菜</div>
        <div class="chat-content">{{ streamingContent }}</div>
      </article>
      <div v-if="assistant.chatBusy && !streamingContent" class="chat-pending">
        包菜正在查看当前节点逻辑…
      </div>
    </div>

    <div v-if="assistant.chatError" class="chat-error">{{ assistant.chatError }}</div>

    <form class="chat-composer" @submit.prevent="sendMessage">
      <textarea
        v-model="input"
        rows="3"
        maxlength="2000"
        placeholder="继续询问这个节点问题…"
        @keydown.enter.exact.prevent="sendMessage"
      />
      <div class="composer-actions">
        <button type="button" class="secondary" :disabled="assistant.chatBusy || !assistant.messages.length" @click="assistant.clearChat()">
          清空会话
        </button>
        <button v-if="assistant.chatBusy" type="button" class="danger" @click="stopWaiting">停止等待</button>
        <button v-else type="submit" class="primary" :disabled="!input.trim()">发送</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';
import { useDockPanel } from '@/composables/useDockPanel.js';
import { useCabbageAssistantStore } from '@/stores/cabbageAssistantStore.js';
import { aiService } from '@/utils/bridge.js';

const assistant = useCabbageAssistantStore();
const { closePanel, isDocked } = useDockPanel();
const input = ref('');
const historyRef = ref(null);
const streamingContent = ref('');
const activeTaskId = ref('');
let requestSequence = 0;
let pollTimer = null;

const selectedKey = computed({
  get: () => assistant.selectedTaskKey,
  set: (value) => assistant.selectTask(value),
});

function scrollToBottom() {
  nextTick(() => {
    if (historyRef.value) historyRef.value.scrollTop = historyRef.value.scrollHeight;
  });
}

function clearPollTimer() {
  if (pollTimer) window.clearTimeout(pollTimer);
  pollTimer = null;
}

function finishRequest(requestId, { error = '', keepPartial = false } = {}) {
  if (assistant.activeRequestId !== requestId) return;
  clearPollTimer();
  if (keepPartial && streamingContent.value.trim()) {
    assistant.appendMessage({ role: 'assistant', content: streamingContent.value.trim() });
  }
  streamingContent.value = '';
  activeTaskId.value = '';
  assistant.activeRequestId = '';
  assistant.chatBusy = false;
  assistant.chatError = error;
  scrollToBottom();
}

function scheduleStatusPoll(requestId, taskId, delay = 320) {
  clearPollTimer();
  pollTimer = window.setTimeout(() => pollStatus(requestId, taskId), delay);
}

async function pollStatus(requestId, taskId) {
  if (assistant.activeRequestId !== requestId || activeTaskId.value !== taskId) return;
  try {
    const response = await aiService.getNodeGraphReviewChatStatus(taskId);
    if (assistant.activeRequestId !== requestId || activeTaskId.value !== taskId) return;
    if (response?.success !== true) {
      finishRequest(requestId, { error: String(response?.message || '包菜答疑暂时不可用，请稍后再试。') });
      return;
    }

    streamingContent.value = String(response?.content || '');
    scrollToBottom();
    if (response.status === 'completed') {
      if (!streamingContent.value.trim()) {
        finishRequest(requestId, { error: 'DeepSeek 没有返回可显示的内容。' });
        return;
      }
      finishRequest(requestId, { keepPartial: true });
      return;
    }
    if (response.status === 'cancelled') {
      finishRequest(requestId, { error: '已停止等待本次回答。', keepPartial: true });
      return;
    }
    if (response.status === 'error') {
      finishRequest(requestId, { error: String(response?.message || '包菜答疑暂时不可用，请稍后再试。') });
      return;
    }
    scheduleStatusPoll(requestId, taskId);
  } catch (error) {
    if (assistant.activeRequestId === requestId) {
      finishRequest(requestId, { error: String(error?.message || '包菜答疑暂时不可用，请稍后再试。') });
    }
  }
}

async function sendMessage() {
  const content = input.value.trim();
  if (!content || assistant.chatBusy) return;
  input.value = '';
  assistant.appendMessage({ role: 'user', content });
  assistant.chatError = '';
  assistant.chatBusy = true;
  streamingContent.value = '';
  const requestId = `cabbage_chat_${Date.now()}_${++requestSequence}`;
  assistant.activeRequestId = requestId;
  scrollToBottom();

  try {
    const response = await aiService.startNodeGraphReviewChat({
      requestId,
      projectScopeId: assistant.projectScopeId,
      graphRevision: assistant.graphRevision,
      selectedTaskKey: assistant.selectedTaskKey,
      tasks: assistant.tasks,
      graphExcerpt: assistant.graphExcerpt,
      messages: assistant.messages.map(({ role, content: text }) => ({ role, content: text })),
    });
    if (assistant.activeRequestId !== requestId) return;
    if (response?.success !== true || !String(response?.taskId || '').trim()) {
      finishRequest(requestId, { error: String(response?.message || '包菜答疑暂时不可用，请稍后再试。') });
      return;
    }
    activeTaskId.value = String(response.taskId);
    scheduleStatusPoll(requestId, activeTaskId.value, 0);
  } catch (error) {
    if (assistant.activeRequestId === requestId) {
      finishRequest(requestId, { error: String(error?.message || '包菜答疑暂时不可用，请稍后再试。') });
    }
  }
}

async function stopWaiting() {
  const requestId = assistant.activeRequestId;
  const taskId = activeTaskId.value;
  if (!requestId) return;
  const partial = streamingContent.value.trim();
  clearPollTimer();
  assistant.activeRequestId = '';
  activeTaskId.value = '';
  streamingContent.value = '';
  assistant.chatBusy = false;
  assistant.chatError = '已停止等待本次回答。';
  if (partial) assistant.appendMessage({ role: 'assistant', content: partial });
  if (taskId) {
    try { await aiService.cancelNodeGraphReviewChat(taskId); } catch (_) {}
  }
  scrollToBottom();
}

function closeFloat() {
  closePanel();
}

watch(() => assistant.messages.length, scrollToBottom);
watch(streamingContent, scrollToBottom);

onBeforeUnmount(() => {
  clearPollTimer();
  const taskId = activeTaskId.value;
  assistant.activeRequestId = '';
  activeTaskId.value = '';
  streamingContent.value = '';
  assistant.chatBusy = false;
  if (taskId) aiService.cancelNodeGraphReviewChat(taskId).catch(() => {});
});
</script>

<style scoped>
.cabbage-chat-shell {
  z-index: 2147483200;
  color: #e5e7eb;
  background: rgba(40, 40, 40, 0.42);
  border: 1px solid rgba(58, 58, 58, 0.72);
}
.context-strip { display:flex; align-items:center; gap:8px; padding:10px; border-bottom:1px solid #3a3a3a; background:#282828; }
.context-title { color:#cfd5cc; font-size:12px; white-space:nowrap; }
.context-select { min-width:0; flex:1; border:1px solid #444; border-radius:5px; background:#1f1f1f; color:#e5e7eb; padding:6px 8px; font-size:12px; outline:none; }
.context-select:focus { border-color:#84A65B; box-shadow:0 0 0 1px rgba(132,166,91,.18); }
.context-count { min-width:22px; height:22px; display:grid; place-items:center; border-radius:999px; background:#3a3a3a; color:#dfead8; font-size:11px; }
.chat-history { flex:1; min-height:0; overflow:auto; padding:12px; display:flex; flex-direction:column; gap:10px; background:rgba(40,40,40,.24); }
.chat-empty { margin:auto; max-width:270px; text-align:center; color:#9ca3af; font-size:12px; line-height:1.7; }
.chat-empty img { width:62px; height:62px; margin:0 auto 10px; border-radius:50%; background:#b8dc91; }
.chat-empty strong { display:block; color:#e5e7eb; font-size:14px; }
.chat-message { max-width:88%; }
.chat-message.user { align-self:flex-end; }
.chat-role { margin:0 4px 3px; color:#8f9690; font-size:10px; }
.chat-message.user .chat-role { text-align:right; }
.chat-content { white-space:pre-wrap; overflow-wrap:anywhere; border:1px solid #3f3f3f; border-radius:8px; background:#2f2f2f; padding:9px 11px; font-size:13px; line-height:1.65; }
.chat-message.user .chat-content { border-color:#657d54; background:#43543b; }
.chat-message.streaming .chat-content { border-color:#64705e; }
.chat-pending { color:#a7bd97; font-size:12px; }
.chat-error { margin:0 10px 8px; border:1px solid #754b43; border-radius:5px; background:#412b27; color:#f4bbb0; padding:7px 9px; font-size:12px; }
.chat-composer { border-top:1px solid #3a3a3a; background:#282828; padding:10px; }
.chat-composer textarea { width:100%; resize:none; border:1px solid #444; border-radius:6px; background:#1f1f1f; color:#ecefec; padding:8px; font-size:13px; outline:none; }
.chat-composer textarea:focus { border-color:#84A65B; box-shadow:0 0 0 1px rgba(132,166,91,.2); }
.composer-actions { margin-top:8px; display:flex; justify-content:flex-end; gap:7px; }
.composer-actions button { border:1px solid #484848; border-radius:5px; padding:6px 11px; font-size:12px; transition:background .15s ease,border-color .15s ease; }
.composer-actions button:disabled { opacity:.45; cursor:not-allowed; }
.primary { border-color:#789663 !important; background:#729257; color:white; }
.primary:hover:not(:disabled) { background:#80a160; }
.secondary { background:#343434; color:#d1d5db; }
.secondary:hover:not(:disabled) { border-color:#666; background:#3d3d3d; }
.danger { border-color:#8b554b !important; background:#79433b; color:#fff; }
</style>



