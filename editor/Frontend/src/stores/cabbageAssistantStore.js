import { defineStore } from 'pinia';

const DEFAULT_PROFILE = Object.freeze({
  score: 0,
  source: 'deepseek',
  updatedAt: 0,
  reasonCodes: [],
  lastScoredEventCount: 0,
});

const OPTIMIZATION_TIP_DURATION_MS = 10000;
const OPTIMIZATION_TIP_COOLDOWN_MS = 60000;
const MAX_SHOWN_OPTIMIZATION_REVISIONS = 80;

function clone(value, fallback = {}) {
  try { return JSON.parse(JSON.stringify(value)); } catch (_) { return fallback; }
}

function clampScore(value) {
  const score = Number(value);
  return Number.isFinite(score) ? Math.max(0, Math.min(100, score)) : 0;
}

function normalizeProfile(raw = {}) {
  return {
    score: clampScore(raw.score ?? raw.fluencyScore),
    source: String(raw.source || 'deepseek').slice(0, 40),
    updatedAt: Math.max(0, Number(raw.updatedAt) || 0),
    reasonCodes: (Array.isArray(raw.reasonCodes) ? raw.reasonCodes : raw.fluencyReasonCodes || [])
      .map((item) => String(item || '').trim().slice(0, 80))
      .filter(Boolean)
      .slice(0, 12),
    lastScoredEventCount: Math.max(0, Number(raw.lastScoredEventCount ?? raw.lastClassifiedEventCount) || 0),
  };
}

function normalizeTask(raw, graphRevision = '', now = Date.now()) {
  if (!raw || typeof raw !== 'object') return null;
  const taskKey = String(raw.taskKey || raw.issueKey || raw.code || '').trim();
  if (!taskKey) return null;
  const type = raw.type === 'tutorial' ? 'tutorial' : 'node-issue';
  const defaultTitle = type === 'tutorial' ? '\u5f15\u5bfc\u4efb\u52a1' : '\u8282\u70b9\u903b\u8f91\u9700\u8981\u8c03\u6574';
  return {
    taskKey,
    issueKey: taskKey,
    type,
    // Track is retained only for backend tutorial sequencing. It is never shown as a user label.
    track: type === 'tutorial' ? String(raw.track || '').slice(0, 40) : '',
    order: Number(raw.order) || 0,
    status: String(raw.status || (type === 'tutorial' ? 'pending' : 'candidate')),
    code: String(raw.code || taskKey),
    severity: String(raw.severity || 'warning'),
    confidence: Number(raw.confidence ?? 0),
    nodeId: String(raw.nodeId || ''),
    blockId: String(raw.blockId || ''),
    title: String(raw.title || defaultTitle).trim().slice(0, 160) || defaultTitle,
    message: String(raw.message || '').trim().slice(0, 1600),
    suggestion: String(raw.suggestion || '').trim().slice(0, 1600),
    completionCriteria: String(raw.completionCriteria || '').trim().slice(0, 800),
    graphRevision: String(raw.graphRevision || graphRevision || ''),
    createdAt: Number(raw.createdAt) || now,
    firstDetectedAt: Number(raw.firstDetectedAt || raw.createdAt) || now,
    updatedAt: Number(raw.updatedAt) || now,
    completedAt: Number(raw.completedAt) || 0,
    resolvedAt: Number(raw.resolvedAt) || 0,
  };
}

function issueKey(issue = {}) {
  return String(
    issue.issueKey
      || `${issue.code || 'logic_issue'}|${issue.nodeId || ''}|${issue.blockId || ''}`
  ).trim();
}

export function assistanceDelay(profile = {}) {
  if (!Number(profile?.updatedAt)) return 10000;
  const score = clampScore(profile?.score ?? profile?.fluencyScore);
  if (score <= 50) return Math.round((score / 50) * 10000);
  if (score <= 70) return Math.round(10000 + ((score - 50) / 20) * 5000);
  return Math.round(15000 + ((score - 70) / 30) * 15000);
}

export const useCabbageAssistantStore = defineStore('cabbageAssistant', {
  state: () => ({
    worldId: '',
    projectScopeId: '',
    graphRevision: '',
    graphExcerpt: {},
    profile: clone(DEFAULT_PROFILE),
    profileHistory: [],
    issueMemory: {},
    metrics: {},
    activeTasks: [],
    taskHistory: [],
    recentOperationEvents: [],
    selectedTaskKey: '',
    attentionToken: 0,
    messages: [],
    chatBusy: false,
    chatError: '',
    activeRequestId: '',
    ephemeralTip: null,
    lastOptimizationTipAt: 0,
    shownOptimizationRevisions: [],
  }),

  getters: {
    tasks(state) {
      return state.activeTasks.filter((task) => (
        task.type === 'tutorial'
          ? ['pending', 'active'].includes(task.status)
          : task.status === 'active'
      ));
    },
    candidateTasks(state) {
      return state.activeTasks.filter((task) => task.type === 'node-issue' && task.status === 'candidate');
    },
    selectedTask() {
      return this.tasks.find((task) => task.taskKey === this.selectedTaskKey) || null;
    },
    taskCount() {
      return this.tasks.length;
    },
    assistanceProfile(state) {
      return {
        score: clampScore(state.profile?.score),
        updatedAt: Math.max(0, Number(state.profile?.updatedAt) || 0),
      };
    },
  },

  actions: {
    resetWorld(projectScopeId = '') {
      this.worldId = '';
      this.projectScopeId = String(projectScopeId || '');
      this.graphRevision = '';
      this.graphExcerpt = {};
      this.profile = clone(DEFAULT_PROFILE);
      this.profileHistory = [];
      this.issueMemory = {};
      this.metrics = {};
      this.activeTasks = [];
      this.taskHistory = [];
      this.recentOperationEvents = [];
      this.selectedTaskKey = '';
      this.messages = [];
      this.chatBusy = false;
      this.chatError = '';
      this.activeRequestId = '';
      this.ephemeralTip = null;
      this.lastOptimizationTipAt = 0;
      this.shownOptimizationRevisions = [];
    },

    clearForProjectChange(projectScopeId = '') {
      this.resetWorld(projectScopeId);
    },

    hydrateContext(snapshot = {}) {
      const context = snapshot.context && typeof snapshot.context === 'object' ? snapshot.context : snapshot;
      const scope = String(snapshot.projectScopeId || context.projectScopeId || this.projectScopeId || '');
      const worldId = String(context.worldId || '');
      if ((this.worldId && worldId && this.worldId !== worldId)
        || (this.projectScopeId && scope && this.projectScopeId !== scope)) {
        this.resetWorld(scope);
      }
      if (worldId) this.worldId = worldId;
      if (scope) this.projectScopeId = scope;
      if (snapshot.graphRevision !== undefined) this.graphRevision = String(snapshot.graphRevision || '');
      if (snapshot.graphExcerpt && typeof snapshot.graphExcerpt === 'object') {
        this.graphExcerpt = clone(snapshot.graphExcerpt, {});
      }
      this.profile = normalizeProfile(context.profile || {});
      this.profileHistory = clone(context.profileHistory || [], []);
      this.issueMemory = clone(context.issueMemory || {}, {});
      this.metrics = clone(context.metrics || {}, {});
      this.activeTasks = (Array.isArray(context.activeTasks) ? context.activeTasks : [])
        .map((task) => normalizeTask(task, this.graphRevision, Number(task?.updatedAt) || Date.now()))
        .filter(Boolean);
      this.taskHistory = (Array.isArray(context.taskHistory) ? context.taskHistory : [])
        .map((task) => normalizeTask(task, task?.graphRevision, Number(task?.updatedAt) || Date.now()))
        .filter(Boolean);
      this.messages = (Array.isArray(context.chatMessages) ? context.chatMessages : [])
        .map((message) => ({
          id: String(message?.id || `cabbage_msg_${Date.now()}_${Math.random()}`),
          role: message?.role === 'assistant' ? 'assistant' : 'user',
          content: String(message?.content || '').trim(),
          createdAt: Number(message?.createdAt) || Date.now(),
          taskKey: String(message?.taskKey || ''),
          issueCode: String(message?.issueCode || ''),
          nodeId: String(message?.nodeId || ''),
          blockId: String(message?.blockId || ''),
        }))
        .filter((message) => message.content);
      this.recentOperationEvents = clone(context.recentOperationEvents || [], []);
      if (this.selectedTaskKey && !this.tasks.some((task) => task.taskKey === this.selectedTaskKey)) {
        this.selectedTaskKey = '';
      }
    },

    applyReview(result = {}, { runtimeFailed = false } = {}) {
      const scope = String(result.projectScopeId || '');
      if (this.projectScopeId && scope && scope !== this.projectScopeId) return [];
      if (scope) this.projectScopeId = scope;
      this.graphRevision = String(result.graphRevision || '');
      this.graphExcerpt = result.graphExcerpt && typeof result.graphExcerpt === 'object'
        ? clone(result.graphExcerpt, {})
        : {};

      const existingNodeTasks = this.activeTasks.filter((task) => task.type === 'node-issue');
      const existingByKey = new Map(existingNodeTasks.map((task) => [task.taskKey, task]));
      const tutorialTasks = this.activeTasks.filter((task) => task.type === 'tutorial');
      const actions = [];
      const now = Date.now();

      let issues = result.hasProblems === true && Array.isArray(result.issues) ? result.issues : [];
      if (result.hasProblems === true && !issues.length && String(result.summary || '').trim()) {
        issues = [{
          issueKey: 'current_node_graph_logic',
          code: 'node_graph_logic_issue',
          title: '\u8282\u70b9\u903b\u8f91\u9700\u8981\u8c03\u6574',
          message: String(result.summary || '').trim(),
          suggestion: String(result.summary || '').trim(),
        }];
      }

      if (issues.length) this.clearOptimizationTip();
      const incomingKeys = new Set(issues.map(issueKey).filter(Boolean));
      for (const existing of existingNodeTasks) {
        if (!incomingKeys.has(existing.taskKey)) {
          actions.push({ action: 'resolve', task: { ...existing, graphRevision: this.graphRevision } });
        }
      }

      const nextNodeTasks = issues.map((issue) => {
        const key = issueKey(issue);
        if (!key) return null;
        const previous = existingByKey.get(key);
        const code = String(issue.code || key).trim();
        const memory = this.issueMemory?.[code] || {};
        const repeated = (!previous && Number(memory.occurrences || 0) >= 1)
          || Number(memory.chatDiscussionCount || 0) >= 1;
        const shouldShow = runtimeFailed || repeated || previous?.status === 'active';
        const summary = String(result.summary || '').trim();
        const task = normalizeTask({
          ...issue,
          taskKey: key,
          type: 'node-issue',
          status: shouldShow ? 'active' : 'candidate',
          title: issue.title || '\u8282\u70b9\u903b\u8f91\u9700\u8981\u8c03\u6574',
          message: issue.message || summary,
          suggestion: issue.suggestion || summary,
          graphRevision: this.graphRevision,
          createdAt: previous?.createdAt,
          firstDetectedAt: previous?.firstDetectedAt,
        }, this.graphRevision, now);
        actions.push({ action: task.status === 'candidate' ? 'candidate' : 'upsert', task });
        return task;
      }).filter(Boolean);

      const previousVisibleKeys = new Set(this.tasks.map((task) => task.taskKey));
      this.activeTasks = [...tutorialTasks, ...nextNodeTasks];
      const nextVisibleKeys = new Set(this.tasks.map((task) => task.taskKey));
      if ([...nextVisibleKeys].some((key) => !previousVisibleKeys.has(key))) this.attentionToken += 1;
      if (this.selectedTaskKey && !nextVisibleKeys.has(this.selectedTaskKey)) this.selectedTaskKey = '';

      if (!issues.length && result.optimizationTip) {
        this.showOptimizationTip(result.optimizationTip, this.graphRevision);
      }
      return actions;
    },

    promoteDueCandidates({ runtimeFailed = false, now = Date.now() } = {}) {
      const delay = assistanceDelay(this.profile);
      const promoted = [];
      for (const task of this.activeTasks) {
        if (task.type !== 'node-issue' || task.status !== 'candidate') continue;
        if (!runtimeFailed && now - Number(task.firstDetectedAt || task.createdAt || now) < delay) continue;
        task.status = 'active';
        task.updatedAt = now;
        promoted.push(clone(task));
      }
      if (promoted.length) this.attentionToken += 1;
      return promoted;
    },

    showOptimizationTip(tip = {}, graphRevision = '') {
      if (this.activeTasks.some((task) => task.type === 'node-issue')) return false;
      const revision = String(graphRevision || '').trim();
      const tipKey = String(tip.tipKey || '').trim().slice(0, 120);
      const title = String(tip.title || '').trim().slice(0, 80);
      const message = String(tip.message || '').trim().slice(0, 360);
      if (!revision || !tipKey || !title || !message) return false;
      if (this.shownOptimizationRevisions.includes(revision)) return false;
      const now = Date.now();
      if (this.lastOptimizationTipAt && now - this.lastOptimizationTipAt < OPTIMIZATION_TIP_COOLDOWN_MS) return false;
      this.ephemeralTip = {
        tipKey,
        title,
        message,
        graphRevision: revision,
        createdAt: now,
        expiresAt: now + OPTIMIZATION_TIP_DURATION_MS,
      };
      this.lastOptimizationTipAt = now;
      this.shownOptimizationRevisions = [
        ...this.shownOptimizationRevisions.filter((item) => item !== revision),
        revision,
      ].slice(-MAX_SHOWN_OPTIMIZATION_REVISIONS);
      this.attentionToken += 1;
      return true;
    },

    clearOptimizationTip() {
      this.ephemeralTip = null;
    },

    selectTask(taskKey = '') {
      const key = String(taskKey || '');
      this.selectedTaskKey = this.tasks.some((task) => task.taskKey === key) ? key : '';
    },

    appendMessage(message) {
      const content = String(message?.content || '').trim();
      if (!content) return null;
      const normalized = {
        id: String(message?.id || `cabbage_msg_${Date.now()}_${Math.random().toString(16).slice(2)}`),
        role: message?.role === 'assistant' ? 'assistant' : 'user',
        content,
        createdAt: Number(message?.createdAt) || Date.now(),
        taskKey: String(message?.taskKey || ''),
        issueCode: String(message?.issueCode || ''),
        nodeId: String(message?.nodeId || ''),
        blockId: String(message?.blockId || ''),
      };
      if (!this.messages.some((item) => item.id === normalized.id)) this.messages.push(normalized);
      return normalized;
    },

    clearChat() {
      // Only clear the current visible session. Persisted world history remains in context.json.
      this.messages = [];
      this.chatError = '';
      this.activeRequestId = '';
    },
  },
});
