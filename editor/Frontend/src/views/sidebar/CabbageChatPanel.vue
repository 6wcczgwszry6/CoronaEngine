<template>
  <div class="cabbage-chat-shell flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden rounded-lg relative">
    <DockTitleBar
      v-if="!isDocked"
      title="包菜答疑"
      routePath="/CabbageChat"
      @close="closeFloat"
    />

    <div class="context-strip">
      <div class="context-title">当前任务</div>
      <select v-model="selectedKey" :disabled="!assistant.tasks.length" class="context-select">
        <option value="">{{ assistant.tasks.length ? '全部待处理任务' : '当前没有待处理任务' }}</option>
        <option v-for="task in assistant.tasks" :key="task.taskKey || task.issueKey" :value="task.taskKey || task.issueKey">
          {{ task.title }}
        </option>
      </select>
      <span class="context-count">{{ assistant.tasks.length }}</span>
    </div>

    <div ref="historyRef" class="chat-history">
      <div v-if="!assistant.messages.length" class="chat-empty">
        <img src="@/assets/cabbage.png" alt="" />
        <strong>继续问包菜</strong>
        <p>可以询问当前任务为什么发生、积木应该接在哪里，或怎样确认已经修好。</p>
      </div>
      <article
        v-for="message in assistant.messages"
        :key="message.id"
        class="chat-message"
        :class="message.role"
      >
        <div class="chat-role">{{ message.role === 'assistant' ? '包菜' : '你' }}</div>
        <div class="chat-content">{{ message.role === 'assistant' ? cleanAssistantText(message.content) : message.content }}</div>
      </article>
      <article v-if="streamingContent" class="chat-message assistant streaming">
        <div class="chat-role">包菜</div>
        <div class="chat-content">{{ cleanedStreamingContent }}</div>
      </article>
      <div v-if="assistant.chatBusy && !streamingContent" class="chat-pending">
        包菜正在查看当前世界与任务…
      </div>
    </div>

    <div v-if="assistant.chatError" class="chat-error">{{ assistant.chatError }}</div>

    <form class="chat-composer" @submit.prevent="sendMessage">
      <textarea
        v-model="input"
        rows="3"
        maxlength="2000"
        placeholder="可以答疑，也可以让包菜生成、制作或编辑游戏节点逻辑…"
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';
import { useDockPanel } from '@/composables/useDockPanel.js';
import { useCabbageAssistantStore } from '@/stores/cabbageAssistantStore.js';
import { aiService } from '@/utils/bridge.js';
import { reviewScopeId } from '@/services/nodeGraphReviewService.js';
import {
  cancelActiveNodeGraphGeneration,
  generateNodeGraphFromInstruction,
  nodeGraphGenerationIntent,
} from '@/services/nodeGraphGenerationService.js';
import {
  cabbageContextService,
  publishCabbageAssistantContext,
  subscribeCabbageAssistantContext,
} from '@/services/cabbageAssistantContextService.js';

const assistant = useCabbageAssistantStore();
const { closePanel, isDocked } = useDockPanel();
const input = ref('');
const historyRef = ref(null);
const streamingContent = ref('');
const activeTaskId = ref('');
const activeRequestKind = ref('');
let requestSequence = 0;
let pollTimer = null;
let unsubscribeAssistantContext = null;
let activeMessageContext = null;

const selectedKey = computed({
  get: () => assistant.selectedTaskKey,
  set: (value) => {
    assistant.selectTask(value);
    publishCabbageAssistantContext(assistant);
  },
});

function cleanAssistantText(value = '') {
  return String(value || '')
    .replace(/^\s*```[^\n]*$/gm, '')
    .replace(/^\s*#{1,6}\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/^\s*[-*_]{3,}\s*$/gm, '')
    .replace(/\[([^\]]+)\]\([^\s)]+\)/g, '$1')
    .replace(/\*\*|__/g, '')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

const cleanedStreamingContent = computed(() => cleanAssistantText(streamingContent.value));

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
  const completedContent = cleanAssistantText(streamingContent.value);
  if (keepPartial && completedContent) {
    const message = assistant.appendMessage({
      role: 'assistant',
      content: completedContent,
      ...(activeMessageContext || {}),
    });
    if (message) void cabbageContextService.appendMessage(message);
  }
  streamingContent.value = '';
  activeTaskId.value = '';
  activeRequestKind.value = '';
  assistant.activeRequestId = '';
  assistant.chatBusy = false;
  assistant.chatError = error;
  activeMessageContext = null;
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
  const selectedTask = assistant.selectedTask;
  const messageContext = {
    taskKey: String(selectedTask?.taskKey || ''),
    issueCode: selectedTask?.type === 'node-issue' ? String(selectedTask?.code || '') : '',
    nodeId: String(selectedTask?.nodeId || ''),
    blockId: String(selectedTask?.blockId || ''),
  };
  activeMessageContext = messageContext;
  const userMessage = assistant.appendMessage({ role: 'user', content, ...messageContext });
  if (userMessage) void cabbageContextService.appendMessage(userMessage);
  assistant.chatError = '';
  assistant.chatBusy = true;
  streamingContent.value = '';
  const requestId = `cabbage_chat_${Date.now()}_${++requestSequence}`;
  assistant.activeRequestId = requestId;
  scrollToBottom();

  const generationIntent = nodeGraphGenerationIntent(content);
  if (generationIntent.matched) {
    activeRequestKind.value = 'generation';
    // The progress sentence is UI-only and is never persisted as chat history.
    streamingContent.value = '\u5305\u83dc\u6b63\u5728\u8bfb\u53d6\u79ef\u6728\u6587\u6863\u5e76\u751f\u6210\u5f53\u524d\u8282\u70b9\u903b\u8f91\u2026';
    try {
      const generated = await generateNodeGraphFromInstruction(content, generationIntent.operation);
      if (assistant.activeRequestId !== requestId || activeRequestKind.value !== 'generation') return;
      streamingContent.value = String(generated.summary || '\u8282\u70b9\u903b\u8f91\u5df2\u7ecf\u751f\u6210\u5e76\u4fdd\u5b58\u3002');
      finishRequest(requestId, { keepPartial: true });
    } catch (error) {
      if (assistant.activeRequestId === requestId) {
        finishRequest(requestId, {
          error: `${String(error?.message || '\u8282\u70b9\u903b\u8f91\u751f\u6210\u5931\u8d25\u3002')} \u5f53\u524d\u8282\u70b9\u56fe\u6ca1\u6709\u88ab\u4fee\u6539\u3002`,
        });
      }
    }
    return;
  }

  activeRequestKind.value = 'chat';
  try {
    const response = await aiService.startNodeGraphReviewChat({
      requestId,
      worldId: assistant.worldId,
      projectScopeId: assistant.projectScopeId,
      graphRevision: assistant.graphRevision,
      assistanceProfile: assistant.assistanceProfile,
      selectedTaskKey: messageContext.taskKey,
      tasks: assistant.tasks,
      graphExcerpt: assistant.graphExcerpt,
      messages: assistant.messages.map(({ role, content: text }) => ({ role, content: text })),
    });
    if (assistant.activeRequestId !== requestId) return;
    if (response?.success !== true || !String(response?.taskId || '').trim()) {
      finishRequest(requestId, { error: String(response?.message || '\u5305\u83dc\u7b54\u7591\u6682\u65f6\u4e0d\u53ef\u7528\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002') });
      return;
    }
    activeTaskId.value = String(response.taskId);
    scheduleStatusPoll(requestId, activeTaskId.value, 0);
  } catch (error) {
    if (assistant.activeRequestId === requestId) {
      finishRequest(requestId, { error: String(error?.message || '\u5305\u83dc\u7b54\u7591\u6682\u65f6\u4e0d\u53ef\u7528\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002') });
    }
  }
}

async function stopWaiting() {
  const requestId = assistant.activeRequestId;
  const taskId = activeTaskId.value;
  const requestKind = activeRequestKind.value;
  if (!requestId) return;
  const partial = requestKind === 'chat' ? cleanAssistantText(streamingContent.value) : '';
  clearPollTimer();
  assistant.activeRequestId = '';
  activeTaskId.value = '';
  activeRequestKind.value = '';
  streamingContent.value = '';
  assistant.chatBusy = false;
  assistant.chatError = '\u5df2\u505c\u6b62\u7b49\u5f85\u672c\u6b21\u56de\u7b54\u3002';
  if (partial) {
    const message = assistant.appendMessage({ role: 'assistant', content: partial, ...(activeMessageContext || {}) });
    if (message) void cabbageContextService.appendMessage(message);
  }
  activeMessageContext = null;
  if (requestKind === 'generation') {
    await cancelActiveNodeGraphGeneration();
  } else if (taskId) {
    try { await aiService.cancelNodeGraphReviewChat(taskId); } catch (_) {}
  }
  scrollToBottom();
}

function closeFloat() {
  closePanel();
}

watch(() => assistant.messages.length, scrollToBottom);
watch(streamingContent, scrollToBottom);

onMounted(() => {
  const currentProjectScopeId = () => reviewScopeId(
    String(window.localStorage?.getItem('corona.activeProjectPath') || '')
  );
  unsubscribeAssistantContext = subscribeCabbageAssistantContext(
    (snapshot) => assistant.hydrateContext(snapshot),
    { projectScopeId: currentProjectScopeId, emitCurrent: true }
  );
});

onBeforeUnmount(() => {
  unsubscribeAssistantContext?.();
  unsubscribeAssistantContext = null;
  clearPollTimer();
  const taskId = activeTaskId.value;
  const requestKind = activeRequestKind.value;
  assistant.activeRequestId = '';
  activeTaskId.value = '';
  activeRequestKind.value = '';
  streamingContent.value = '';
  assistant.chatBusy = false;
  if (requestKind === 'generation') cancelActiveNodeGraphGeneration().catch(() => {});
  else if (taskId) aiService.cancelNodeGraphReviewChat(taskId).catch(() => {});
});
</script>

<style scoped>
.cabbage-chat-shell {
  z-index: 2147483200;
  color: #e7ece3;
  background: linear-gradient(180deg, rgba(38, 42, 38, 0.96), rgba(26, 30, 27, 0.95));
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.34);
}

.context-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 7px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: linear-gradient(180deg, rgba(34, 39, 35, 0.88), rgba(29, 33, 30, 0.78));
}

.context-title {
  color: #b9c5b4;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.context-select {
  min-width: 0;
  flex: 1;
  height: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  background: rgba(20, 23, 21, 0.72);
  color: #e3e9df;
  padding: 0 8px;
  font-size: 11px;
  outline: none;
}

.context-select:hover:not(:disabled) {
  border-color: rgba(138, 166, 106, 0.42);
}

.context-select:focus {
  border-color: #84a65b;
  box-shadow: 0 0 0 2px rgba(132, 166, 91, 0.13);
}

.context-select:disabled {
  color: #7f887d;
  cursor: default;
}

.context-count {
  min-width: 23px;
  height: 23px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(138, 166, 106, 0.28);
  border-radius: 999px;
  background: rgba(132, 166, 91, 0.13);
  color: #cfe0c4;
  font-size: 10px;
  font-weight: 700;
}

.chat-history {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 13px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 11px;
  background:
    radial-gradient(circle at 50% 0%, rgba(132, 166, 91, 0.06), transparent 38%),
    rgba(25, 29, 26, 0.48);
  scrollbar-color: rgba(132, 166, 91, 0.48) transparent;
  scrollbar-width: thin;
}

.chat-history::-webkit-scrollbar {
  width: 6px;
}

.chat-history::-webkit-scrollbar-track {
  background: transparent;
}

.chat-history::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(132, 166, 91, 0.42);
}

.chat-empty {
  margin: auto;
  max-width: 280px;
  padding: 22px 18px;
  text-align: center;
  color: #9da79a;
  font-size: 12px;
  line-height: 1.7;
}

.chat-empty img {
  width: 64px;
  height: 64px;
  margin: 0 auto 11px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 50%;
  background: #b8dc91;
  box-shadow: 0 9px 24px rgba(0, 0, 0, 0.26);
}

.chat-empty strong {
  display: block;
  color: #edf2e9;
  font-size: 14px;
  font-weight: 600;
}

.chat-empty p {
  margin: 6px 0 0;
}

.chat-message {
  max-width: 88%;
}

.chat-message.user {
  align-self: flex-end;
}

.chat-role {
  margin: 0 5px 4px;
  color: #899386;
  font-size: 10px;
  font-weight: 600;
}

.chat-message.user .chat-role {
  text-align: right;
}

.chat-content {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px 8px 8px 3px;
  background: linear-gradient(180deg, rgba(50, 56, 51, 0.94), rgba(40, 45, 41, 0.94));
  box-shadow: 0 5px 16px rgba(0, 0, 0, 0.14);
  padding: 9px 11px;
  color: #e3e9df;
  font-size: 12px;
  line-height: 1.65;
}

.chat-message.user .chat-content {
  border-color: rgba(151, 182, 116, 0.32);
  border-radius: 8px 8px 3px 8px;
  background: linear-gradient(180deg, rgba(111, 142, 85, 0.94), rgba(82, 108, 66, 0.96));
  color: #ffffff;
}

.chat-message.streaming .chat-content {
  border-color: rgba(138, 166, 106, 0.38);
}

.chat-pending {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 7px;
  color: #adc39e;
  font-size: 11px;
}

.chat-pending::before {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #8aa66a;
  box-shadow: 0 0 0 4px rgba(138, 166, 106, 0.1);
  content: '';
  animation: cabbage-pulse 1.1s ease-in-out infinite;
}

.chat-error {
  margin: 0 10px 8px;
  border: 1px solid rgba(197, 112, 94, 0.42);
  border-radius: 6px;
  background: rgba(86, 43, 37, 0.72);
  color: #f2c1b7;
  padding: 8px 10px;
  font-size: 11px;
  line-height: 1.5;
}

.chat-composer {
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  background: linear-gradient(180deg, rgba(34, 38, 35, 0.9), rgba(28, 32, 29, 0.95));
  padding: 10px;
}

.chat-composer textarea {
  width: 100%;
  resize: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  background: rgba(19, 22, 20, 0.76);
  color: #edf1ea;
  padding: 9px 10px;
  font-size: 12px;
  line-height: 1.55;
  outline: none;
  transition: border-color 140ms ease, box-shadow 140ms ease, background-color 140ms ease;
}

.chat-composer textarea::placeholder {
  color: #778075;
}

.chat-composer textarea:hover {
  background: rgba(22, 25, 23, 0.88);
}

.chat-composer textarea:focus {
  border-color: #84a65b;
  box-shadow: 0 0 0 2px rgba(132, 166, 91, 0.13);
}

.composer-actions {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  gap: 7px;
}

.composer-actions button {
  min-height: 27px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 5px;
  padding: 5px 11px;
  color: #dce4d8;
  font-size: 11px;
  font-weight: 600;
  transition: background-color 140ms ease, border-color 140ms ease, color 140ms ease, transform 140ms ease;
}

.composer-actions button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.composer-actions button:active:not(:disabled) {
  transform: translateY(1px);
}

.primary {
  border-color: rgba(151, 182, 116, 0.52) !important;
  background: #789a5c;
  color: #ffffff !important;
}

.primary:hover:not(:disabled) {
  background: #86a968;
}

.secondary {
  background: rgba(255, 255, 255, 0.055);
}

.secondary:hover:not(:disabled) {
  border-color: rgba(138, 166, 106, 0.38);
  background: rgba(138, 166, 106, 0.12);
  color: #ffffff;
}

.danger {
  border-color: rgba(197, 112, 94, 0.48) !important;
  background: rgba(121, 67, 59, 0.92);
  color: #ffffff !important;
}

.danger:hover:not(:disabled) {
  background: rgba(145, 76, 66, 0.96);
}

@keyframes cabbage-pulse {
  0%, 100% { opacity: 0.45; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1); }
}
</style>
