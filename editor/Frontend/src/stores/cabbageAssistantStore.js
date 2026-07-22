import { defineStore } from 'pinia';

const MAX_CHAT_MESSAGES = 60;

function normalizeTask(issue, graphRevision, now = Date.now()) {
  const issueKey = String(issue?.issueKey || issue?.code || `${issue?.nodeId || 'graph'}:${issue?.blockId || ''}:${issue?.title || 'issue'}`).trim();
  if (!issueKey) return null;
  const title = String(issue?.title || issue?.message || '节点逻辑需要调整').trim().slice(0, 80);
  const message = String(issue?.message || '').trim().slice(0, 600);
  const suggestion = String(issue?.suggestion || '').trim().slice(0, 600);
  return {
    issueKey,
    code: String(issue?.code || issueKey),
    severity: String(issue?.severity || 'warning'),
    confidence: Number(issue?.confidence ?? 1),
    nodeId: String(issue?.nodeId || ''),
    blockId: String(issue?.blockId || ''),
    title: title || '节点逻辑需要调整',
    message,
    suggestion,
    graphRevision: String(graphRevision || ''),
    createdAt: Number(issue?.createdAt) || now,
    updatedAt: now,
  };
}

export const useCabbageAssistantStore = defineStore('cabbageAssistant', {
  state: () => ({
    projectScopeId: '',
    graphRevision: '',
    graphExcerpt: {},
    tasks: [],
    selectedTaskKey: '',
    attentionToken: 0,
    messages: [],
    chatBusy: false,
    chatError: '',
    activeRequestId: '',
  }),

  getters: {
    selectedTask(state) {
      return state.tasks.find((task) => task.issueKey === state.selectedTaskKey) || null;
    },
    taskCount(state) {
      return state.tasks.length;
    },
  },

  actions: {
    applyReview(result = {}) {
      const scope = String(result.projectScopeId || '');
      if (this.projectScopeId && scope && scope !== this.projectScopeId) this.clearForProjectChange(scope);
      if (scope) this.projectScopeId = scope;
      this.graphRevision = String(result.graphRevision || '');
      this.graphExcerpt = result.graphExcerpt && typeof result.graphExcerpt === 'object'
        ? JSON.parse(JSON.stringify(result.graphExcerpt))
        : {};

      if (result.hasProblems !== true) {
        this.tasks = [];
        this.selectedTaskKey = '';
        return;
      }

      const now = Date.now();
      const previousByKey = new Map(this.tasks.map((task) => [task.issueKey, task]));
      let issues = Array.isArray(result.issues) ? result.issues : [];
      if (!issues.length && String(result.summary || '').trim()) {
        issues = [{
          issueKey: 'current_node_graph_logic',
          code: 'node_graph_logic_issue',
          title: '当前节点逻辑需要调整',
          message: String(result.summary || '').trim(),
        }];
      }
      const next = issues
        .map((issue) => {
          const key = String(issue?.issueKey || issue?.code || `${issue?.nodeId || 'graph'}:${issue?.blockId || ''}:${issue?.title || 'issue'}`).trim();
          return normalizeTask({ ...issue, createdAt: previousByKey.get(key)?.createdAt }, this.graphRevision, now);
        })
        .filter(Boolean);
      const changed = JSON.stringify(next.map(({ updatedAt, ...task }) => task))
        !== JSON.stringify(this.tasks.map(({ updatedAt, ...task }) => task));
      this.tasks = next;
      if (this.selectedTaskKey && !next.some((task) => task.issueKey === this.selectedTaskKey)) {
        this.selectedTaskKey = '';
      }
      if (changed) this.attentionToken += 1;
    },

    clearForProjectChange(projectScopeId = '') {
      this.projectScopeId = String(projectScopeId || '');
      this.graphRevision = '';
      this.graphExcerpt = {};
      this.tasks = [];
      this.selectedTaskKey = '';
      this.messages = [];
      this.chatBusy = false;
      this.chatError = '';
      this.activeRequestId = '';
    },

    hydrateContext(snapshot = {}) {
      const scope = String(snapshot.projectScopeId || '');
      if (this.projectScopeId && scope && scope !== this.projectScopeId) {
        this.clearForProjectChange(scope);
      }
      if (scope) this.projectScopeId = scope;
      this.graphRevision = String(snapshot.graphRevision || '');
      this.graphExcerpt = snapshot.graphExcerpt && typeof snapshot.graphExcerpt === 'object'
        ? JSON.parse(JSON.stringify(snapshot.graphExcerpt))
        : {};
      this.tasks = (Array.isArray(snapshot.tasks) ? snapshot.tasks : [])
        .map((task) => normalizeTask(task, this.graphRevision, Number(task?.updatedAt) || Date.now()))
        .filter(Boolean);
      const selectedTaskKey = String(snapshot.selectedTaskKey || '');
      this.selectedTaskKey = this.tasks.some((task) => task.issueKey === selectedTaskKey)
        ? selectedTaskKey
        : '';
    },

    selectTask(issueKey = '') {
      this.selectedTaskKey = String(issueKey || '');
    },

    appendMessage(message) {
      const content = String(message?.content || '').trim();
      if (!content) return;
      this.messages.push({
        id: String(message?.id || `cabbage_msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`),
        role: message?.role === 'assistant' ? 'assistant' : 'user',
        content,
        createdAt: Number(message?.createdAt) || Date.now(),
      });
      if (this.messages.length > MAX_CHAT_MESSAGES) {
        this.messages.splice(0, this.messages.length - MAX_CHAT_MESSAGES);
      }
    },

    clearChat() {
      this.messages = [];
      this.chatError = '';
      this.activeRequestId = '';
    },
  },
});
