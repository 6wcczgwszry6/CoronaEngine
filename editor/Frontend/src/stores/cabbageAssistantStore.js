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
const PRE_WARNING_DURATION_MS = 10000;
const MAX_SHOWN_PRE_WARNING_KEYS = 160;
const PRE_WARNING_CODES = new Set([
  'missing_actor_target',
  'actor_target_not_found',
  'start_node_count',
  'invalid_edge_endpoint',
  'invalid_visible_condition_count',
  'non_boolean_condition',
  'unknown_block_type',
  'missing_required_input',
]);
const PATTERN_FIELDS = ['blockType', 'workspaceRole', 'relationType', 'missingInput', 'objectRequirement', 'edgeId'];

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

function normalizeIssuePattern(raw = {}) {
  if (!raw || typeof raw !== 'object') return {};
  return Object.fromEntries(PATTERN_FIELDS
    .map((key) => [key, String(raw[key] || '').trim().slice(0, 160)])
    .filter(([, value]) => value));
}

function normalizeSteps(raw) {
  return (Array.isArray(raw) ? raw : [])
    .map((item) => String(item || '').trim().slice(0, 500))
    .filter(Boolean)
    .slice(0, 8);
}

function walkBlocks(value, result = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => walkBlocks(item, result));
  } else if (value && typeof value === 'object') {
    if (typeof value.type === 'string') result.push(value);
    Object.values(value).forEach((item) => walkBlocks(item, result));
  }
  return result;
}

function blockHasInput(block, inputName) {
  if (!inputName) return true;
  const input = block?.inputs?.[inputName];
  return Boolean(input && (input.block || input.shadow));
}

const ACTOR_PLACEHOLDERS = new Set([
  '', 'none', 'null', 'undefined', '__none__', '__manual__',
  '未选择', '请选择', '请选择对象', '任意物体',
]);

function normalizedActorName(value) {
  return String(value ?? '').trim();
}

function isMissingActorName(value) {
  return ACTOR_PLACEHOLDERS.has(normalizedActorName(value).toLocaleLowerCase('en-US'));
}

function connectedBlock(block, inputName) {
  const input = block?.inputs?.[inputName];
  if (!input || typeof input !== 'object') return null;
  const child = input.block && typeof input.block === 'object' ? input.block : input.shadow;
  return child && typeof child === 'object' ? child : null;
}

function actorReference(block, inputName) {
  if (!inputName) return { state: 'absent', name: '' };
  const child = connectedBlock(block, inputName);
  if (child) {
    const fields = child.fields && typeof child.fields === 'object' ? child.fields : {};
    if (child.type === 'text') {
      const name = normalizedActorName(fields.TEXT);
      return isMissingActorName(name) ? { state: 'missing', name: '' } : { state: 'resolved', name };
    }
    if (child.type === 'object_reference') {
      const selected = normalizedActorName(fields.OBJECT);
      const name = selected === '__manual__' ? normalizedActorName(fields.MANUAL) : selected;
      return isMissingActorName(name) ? { state: 'missing', name: '' } : { state: 'resolved', name };
    }
    return { state: 'dynamic', name: '' };
  }

  const fields = block?.fields && typeof block.fields === 'object' ? block.fields : {};
  const aliases = [inputName, `${inputName}_TEXT`];
  const present = aliases.some((key) => Object.prototype.hasOwnProperty.call(fields, key));
  for (const key of aliases) {
    const name = normalizedActorName(fields[key]);
    if (!isMissingActorName(name)) return { state: 'resolved', name };
  }
  return present ? { state: 'missing', name: '' } : { state: 'absent', name: '' };
}

function actorFieldMissing(block, inputName) {
  const state = actorReference(block, inputName).state;
  return state === 'missing' || state === 'absent';
}

function topLevelBlocks(workspace) {
  const blocks = workspace?.blocks?.blocks;
  return Array.isArray(blocks) ? blocks.filter((block) => block && typeof block === 'object') : [];
}

function normalizeTask(raw, graphRevision = '', now = Date.now()) {
  if (!raw || typeof raw !== 'object') return null;
  const taskKey = String(raw.taskKey || raw.issueKey || raw.code || '').trim();
  if (!taskKey) return null;
  const type = ['tutorial', 'goal', 'node-issue'].includes(raw.type)
    ? raw.type
    : 'node-issue';
  const defaultTitle = type === 'node-issue'
    ? '\u8282\u70b9\u903b\u8f91\u9700\u8981\u8c03\u6574'
    : '\u4e16\u754c\u5236\u4f5c\u4efb\u52a1';
  return {
    taskKey,
    issueKey: taskKey,
    type,
    // Track is retained only for backend task sequencing. It is never shown as a user label.
    track: type !== 'node-issue' ? String(raw.track || '').slice(0, 40) : '',
    order: Number(raw.order) || 0,
    status: String(raw.status || (type === 'node-issue' ? 'candidate' : 'pending')),
    code: String(raw.code || taskKey),
    severity: String(raw.severity || 'warning'),
    confidence: Number(raw.confidence ?? 0),
    nodeId: String(raw.nodeId || ''),
    blockId: String(raw.blockId || ''),
    edgeId: String(raw.edgeId || ''),
    pattern: normalizeIssuePattern(raw.pattern || {}),
    title: String(raw.title || defaultTitle).trim().slice(0, 160) || defaultTitle,
    message: String(raw.message || '').trim().slice(0, 1600),
    suggestion: String(raw.suggestion || '').trim().slice(0, 1600),
    completionCriteria: String(raw.completionCriteria || '').trim().slice(0, 800),
    completionSignal: String(raw.completionSignal || '').trim().slice(0, 80),
    requiredCount: Math.max(1, Number(raw.requiredCount) || 1),
    phase: String(raw.phase || '').trim().slice(0, 40),
    effectId: String(raw.effectId || '').trim().slice(0, 120),
    requiredBlockTypes: Array.isArray(raw.requiredBlockTypes)
      ? [...new Set(raw.requiredBlockTypes.map((item) => String(item || '').trim()).filter(Boolean))].slice(0, 20)
      : [],
    observedBlockTypes: Array.isArray(raw.observedBlockTypes)
      ? [...new Set(raw.observedBlockTypes.map((item) => String(item || '').trim()).filter(Boolean))].slice(0, 20)
      : [],
    guidanceIntent: String(raw.guidanceIntent || '').trim().slice(0, 80),
    graphRevision: String(raw.graphRevision || graphRevision || ''),
    createdAt: Number(raw.createdAt) || now,
    firstDetectedAt: Number(raw.firstDetectedAt || raw.createdAt) || now,
    updatedAt: Number(raw.updatedAt) || now,
    completedAt: Number(raw.completedAt) || 0,
    resolvedAt: Number(raw.resolvedAt) || 0,
  };
}

function issueKey(issue = {}) {
  if (issue.issueKey) return String(issue.issueKey).trim();
  const base = `${issue.code || 'logic_issue'}|${issue.nodeId || ''}|${issue.blockId || ''}`;
  return String(issue.edgeId ? `${base}|${issue.edgeId}` : base).trim();
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
    worldGoal: {},
    goalTaskPlan: {},
    goalSignalCounts: {},
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
    contextUpdatedAt: 0,
    preWarning: null,
    shownPreWarningKeys: [],
  }),

  getters: {
    tasks(state) {
      return state.activeTasks.filter((task) => (
        task.type === 'node-issue'
          ? task.status === 'active'
          : ['pending', 'active'].includes(task.status)
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
      this.worldGoal = {};
      this.goalTaskPlan = {};
      this.goalSignalCounts = {};
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
      this.contextUpdatedAt = 0;
      this.preWarning = null;
      this.shownPreWarningKeys = [];
    },

    clearForProjectChange(projectScopeId = '') {
      this.resetWorld(projectScopeId);
    },

    hydrateContext(snapshot = {}) {
      const context = snapshot.context && typeof snapshot.context === 'object' ? snapshot.context : snapshot;
      const scope = String(snapshot.projectScopeId || context.projectScopeId || this.projectScopeId || '');
      const worldId = String(context.worldId || '');
      const incomingUpdatedAt = Math.max(0, Number(context.updatedAt || snapshot.updatedAt) || 0);
      const sameContext = (!worldId || !this.worldId || worldId === this.worldId)
        && (!scope || !this.projectScopeId || scope === this.projectScopeId);
      if (sameContext && incomingUpdatedAt && this.contextUpdatedAt && incomingUpdatedAt < this.contextUpdatedAt) return false;
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
      this.worldGoal = clone(context.worldGoal || {}, {});
      this.goalTaskPlan = clone(context.goalTaskPlan || {}, {});
      this.goalSignalCounts = clone(context.goalSignalCounts || {}, {});
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
          needsShowcase: message?.needsShowcase === true,
          guidanceIntent: String(message?.guidanceIntent || ''),
          steps: normalizeSteps(message?.steps),
        }))
        .filter((message) => message.content);
      this.recentOperationEvents = clone(context.recentOperationEvents || [], []);
      if (this.selectedTaskKey && !this.tasks.some((task) => task.taskKey === this.selectedTaskKey)) {
        this.selectedTaskKey = '';
      }
      this.contextUpdatedAt = Math.max(this.contextUpdatedAt, incomingUpdatedAt);
      return true;
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
      const guidanceTasks = this.activeTasks.filter((task) => task.type !== 'node-issue');
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
      this.activeTasks = [...guidanceTasks, ...nextNodeTasks];
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

    showPreWarning(warning = {}) {
      const code = String(warning.code || '').trim();
      const revision = String(warning.graphRevision || this.graphRevision || '').trim();
      const patternKey = JSON.stringify(normalizeIssuePattern(warning.pattern || {}));
      const warningKey = `${revision}|${code}|${patternKey}`;
      if (!revision || !PRE_WARNING_CODES.has(code) || this.shownPreWarningKeys.includes(warningKey)) return false;
      const now = Date.now();
      this.preWarning = {
        warningKey,
        code,
        title: String(warning.title || '编辑提醒').trim().slice(0, 80),
        message: String(warning.message || '').trim().slice(0, 360),
        nodeId: String(warning.nodeId || ''),
        blockId: String(warning.blockId || ''),
        edgeId: String(warning.edgeId || ''),
        pattern: normalizeIssuePattern(warning.pattern || {}),
        graphRevision: revision,
        createdAt: now,
        expiresAt: now + PRE_WARNING_DURATION_MS,
      };
      this.shownPreWarningKeys = [...this.shownPreWarningKeys, warningKey].slice(-MAX_SHOWN_PRE_WARNING_KEYS);
      this.attentionToken += 1;
      return true;
    },

    clearPreWarning() {
      this.preWarning = null;
    },

    evaluateRememberedIssuePatterns(workspace = {}, graphRevision = '', projectContext = {}) {
      const revision = String(graphRevision || '').trim();
      if (!revision || !workspace || typeof workspace !== 'object') return null;
      const nodes = Array.isArray(workspace.nodes) ? workspace.nodes.filter(Boolean) : [];
      const edges = Array.isArray(workspace.edges) ? workspace.edges.filter(Boolean) : [];
      const nodeIds = new Set(nodes.map((node) => String(node?.id || '')).filter(Boolean));
      const actorContextAvailable = Array.isArray(projectContext?.actors);
      const knownActors = new Set((projectContext?.actors || [])
        .map((actor) => normalizedActorName(actor?.name).toLocaleLowerCase('en-US'))
        .filter(Boolean));
      const scopedBlocks = [];
      nodes.forEach((node) => walkBlocks(node?.workspace || {}).forEach((block) => scopedBlocks.push({ nodeId: String(node?.id || ''), block })));
      edges.forEach((edge) => walkBlocks(edge?.conditionWorkspace || {}).forEach((block) => scopedBlocks.push({ edgeId: String(edge?.id || ''), block })));
      walkBlocks(workspace.globalVariablesWorkspace || {}).forEach((block) => scopedBlocks.push({ block }));

      const enabled = Object.entries(this.issueMemory || {})
        .filter(([code, memory]) => {
          const occurrences = Number(memory?.occurrences || 0);
          const discussions = Number(memory?.chatDiscussionCount || 0);
          return PRE_WARNING_CODES.has(code) && occurrences >= 1 && occurrences + discussions >= 2;
        })
        .sort((a, b) => Number(b[1]?.lastSeenAt || 0) - Number(a[1]?.lastSeenAt || 0));
      for (const [code, memory] of enabled) {
        const pattern = normalizeIssuePattern(memory?.pattern || {});
        let match = null;
        if (code === 'start_node_count') {
          const count = nodes.filter((node) => node?.nodeType === 'start').length;
          if (count !== 1) match = { message: '开始节点似乎又不是唯一的，继续编辑前先保留一个开始节点会更稳妥。' };
        } else if (code === 'invalid_edge_endpoint') {
          const edge = edges.find((item) => !nodeIds.has(String(item?.source?.nodeId || '')) || !nodeIds.has(String(item?.target?.nodeId || '')));
          if (edge) match = { edgeId: String(edge.id || ''), message: '这条连线可能又指向了无效节点，继续编辑前先重新连接两个真实节点。' };
        } else if (code === 'invalid_visible_condition_count') {
          const edge = edges.find((item) => topLevelBlocks(item?.conditionWorkspace || {}).length !== 1);
          if (edge) {
            match = {
              edgeId: String(edge.id || ''),
              message: '跳转条件可能又没有保持唯一可见返回值，先整理条件积木再连线。',
            };
          }
        } else if (code === 'non_boolean_condition') {
          if (pattern.blockType) {
            const edge = edges.find((item) => {
              const topBlocks = topLevelBlocks(item?.conditionWorkspace || {});
              return topBlocks.length === 1 && String(topBlocks[0]?.type || '') === pattern.blockType;
            });
            if (edge) {
              const block = topLevelBlocks(edge.conditionWorkspace || {})[0];
              match = {
                edgeId: String(edge.id || ''),
                blockId: String(block?.id || ''),
                message: '这条跳转条件可能又不是 Boolean 值，先接上比较或逻辑积木。',
              };
            }
          }
        } else {
          const scoped = scopedBlocks.find(({ block }) => {
            if (pattern.blockType && String(block?.type || '') !== pattern.blockType) return false;
            const actorInput = pattern.missingInput || (pattern.objectRequirement ? 'OBJECT' : '');
            if (code === 'missing_actor_target') return actorFieldMissing(block, actorInput);
            if (code === 'actor_target_not_found') {
              if (!actorContextAvailable || !actorInput) return false;
              const reference = actorReference(block, actorInput);
              return reference.state === 'resolved'
                && !knownActors.has(reference.name.toLocaleLowerCase('en-US'));
            }
            if (code === 'missing_required_input') return !blockHasInput(block, pattern.missingInput);
            if (code === 'unknown_block_type') return Boolean(pattern.blockType && String(block?.type || '') === pattern.blockType);
            return false;
          });
          if (scoped) {
            const messages = {
              missing_actor_target: '这里可能又缺少具体对象，继续连接操作逻辑前，可以先给对象输入口接上“对象[]”积木。',
              actor_target_not_found: '这里可能又引用了当前场景不存在的对象，继续编辑前先把“对象[]”改成场景中已有的物体。',
              missing_required_input: '这个积木可能又缺少必要输入，先补齐输入再继续连接会更安全。',
              unknown_block_type: '这里可能又使用了当前引擎不支持的积木，可以先换成工具箱中的可用积木。',
            };
            match = {
              nodeId: String(scoped.nodeId || ''), edgeId: String(scoped.edgeId || ''),
              blockId: String(scoped.block?.id || ''), message: messages[code] || '这里可能又出现了之前的逻辑问题。',
            };
          }
        }
        if (match) {
          const warning = { code, pattern, graphRevision: revision, title: '可能重复的逻辑问题', ...match };
          return this.showPreWarning(warning) ? this.preWarning : null;
        }
      }
      return null;
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
        needsShowcase: message?.needsShowcase === true,
        guidanceIntent: String(message?.guidanceIntent || ''),
        steps: normalizeSteps(message?.steps),
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
