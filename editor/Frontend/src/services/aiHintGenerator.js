import { aiService } from '@/utils/bridge.js';
import { mouseTracker } from './mouseTracker.js';

// Track recent hints to prevent AI repetition
const RECENT_HINTS = [];
const MAX_RECENT = 10;

function pushRecent(text) {
  RECENT_HINTS.push(text);
  if (RECENT_HINTS.length > MAX_RECENT) RECENT_HINTS.shift();
}

/**
 * Build a stage summary prompt from accumulated user actions.
 *
 * Instead of "user is hovering at X", we tell the AI:
 * "In the last 30 seconds, the user did A, B, C. Predict their project goal."
 */
function buildStagePrompt(actions, visits) {
  const parts = [];

  // ═══ Core instruction ═══
  parts.push('用户正在用 Corona 可视化编辑器创作作品。以下是用户最近一段时间的操作记录。');
  parts.push('请根据这些操作推测：1) 用户在做什么类型的作品 2) 他当前处于创作哪个阶段 3) 他接下来最需要做什么。');
  parts.push('然后直接给出一条功能性操作建议（15字以内）。必须是可以立刻执行的具体操作。不要说"你可以试试"这类模糊话。');

  // ═══ Action summary ═══
  if (actions.length === 0) {
    parts.push('用户在这段时间内没有明显操作，可能正在浏览或思考。');
  } else {
    const actionDescs = actions.map(a => {
      switch (a.type) {
        case 'click': return `点击了「${a.label}」`;
        case 'dwell': return `在「${a.label}」停留了${a.detail}`;
        case 'key': return `在「${a.label}」按了 ${a.detail}`;
        default: return `${a.type}: ${a.label}`;
      }
    });
    parts.push(`用户操作序列：${actionDescs.join(' → ')}`);

    // Count actions by area for focus analysis
    const areaCounts = {};
    for (const a of actions) {
      areaCounts[a.area] = (areaCounts[a.area] || 0) + 1;
    }
    const topAreas = Object.entries(areaCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([area, n]) => `「${area}」${n}次`);
    parts.push(`操作集中在：${topAreas.join('，')}`);
  }

  // ═══ Visit summary (where they spent time) ═══
  if (visits.length > 0) {
    const significant = visits.filter(v => v.dwellMs >= 3000);
    if (significant.length > 0) {
      const descs = significant.slice(-5).map(v =>
        `在「${v.areaLabel}」停留${Math.round(v.dwellMs / 1000)}秒`
      );
      parts.push(`用户关注区域：${descs.join(' | ')}`);
    }
  }

  // ═══ Anti-repetition ═══
  if (RECENT_HINTS.length > 0) {
    parts.push(`最近说过的提示（严禁重复，必须完全不同）：${RECENT_HINTS.join(' | ')}`);
    parts.push('你的提示必须和上面所有已说过的话完全不同，换一个全新的角度给建议。');
  }

  return parts.join('\n');
}

/**
 * StageHintEngine — stage-based hint generation.
 *
 * Every STAGE_INTERVAL ms, collects accumulated user actions from mouseTracker,
 * summarizes them, calls the AI, and fires a callback with the result.
 */
class StageHintEngine {
  constructor() {
    this.running = false;
    this.stageMs = 10000;       // 30 seconds per stage
    this.hintShowMs = 8000;     // how long the hint bubble stays
    this._timer = null;
    this._onHint = null;        // callback(hintText)
    this._onStageStart = null;  // callback() — stage began, hide old bubble
    this._pending = false;
  }

  /**
   * Start stage-based hint generation.
   * @param {function} onHint - called with hint text when AI responds
   * @param {function} onStageStart - called when a new stage begins (hide old bubble)
   * @param {number} [hintShowMs] - optional display duration in ms (default keeps previous)
   */
  start(onHint, onStageStart, hintShowMs) {
    if (this.running) return;
    this.running = true;
    this._onHint = onHint;
    this._onStageStart = onStageStart;
    if (typeof hintShowMs === 'number' && hintShowMs > 0) {
      this.hintShowMs = hintShowMs;
    }
    this._scheduleNext();
  }

  /** Update hint display duration after engine has started */
  setHintShowMs(ms) {
    if (typeof ms === 'number' && ms > 0) {
      this.hintShowMs = ms;
    }
  }

  stop() {
    this.running = false;
    if (this._timer) { clearTimeout(this._timer); this._timer = null; }
    this._pending = false;
  }

  _scheduleNext() {
    if (!this.running) return;
    this._timer = setTimeout(() => this._processStage(), this.stageMs);
  }

  async _processStage() {
    if (!this.running || this._pending) return;
    this._pending = true;

    try {
      // Collect stage data
      const actions = mouseTracker.getActionLog();
      const visits = mouseTracker.getVisitHistory();
      mouseTracker.resetActionLog();

      // Only generate if there's meaningful activity
      if (actions.length === 0 && visits.length < 2) {
        // Not enough data — skip this stage, schedule next
        this._pending = false;
        this._scheduleNext();
        return;
      }

      // Notify that a new stage is starting (hide old bubble)
      if (this._onStageStart) this._onStageStart();

      // Build prompt and call AI
      const prompt = buildStagePrompt(actions, visits);
      let text = null;

      try {
        const result = await aiService.generateHint('stage', { contextPrompt: prompt });
        if (result && typeof result === 'string' && result.trim()) {
          text = result.trim();
          pushRecent(text);
        }
      } catch (e) {
        console.debug('[StageHint] AI failed:', e);
      }

      // Fallback
      if (!text) {
        text = _stageFallback(actions, visits);
        pushRecent(text);
      }

      // Show hint, then schedule next stage after display time
      if (this._onHint && text) this._onHint(text);

      this._pending = false;
      // Schedule next stage after hint display time
      this._timer = setTimeout(() => this._processStage(), this.stageMs + this.hintShowMs);
    } catch (e) {
      console.error('[StageHint] error:', e);
      this._pending = false;
      this._scheduleNext();
    }
  }
}

function _stageFallback(actions, visits) {
  // Build a contextual fallback from what the user actually did
  if (actions.length > 0) {
    const lastAction = actions[actions.length - 1];
    switch (lastAction.type) {
      case 'click':
        return `点击了「${lastAction.label}」后，试试右键看看更多选项`;
      case 'dwell':
        return `在「${lastAction.label}」停了好久，试试直接操作看看`;
      case 'key':
        return `用了快捷键${lastAction.detail}，继续搭配其他操作`;
    }
  }
  if (visits.length > 0) {
    const last = visits[visits.length - 1];
    return `在「${last.areaLabel}」试试拖拽或右键操作`;
  }
  return '从左边工具箱拖一个积木到工作区开始创作';
}

// Singleton
const engine = new StageHintEngine();

/**
 * Start stage-based hint mode.
 * @param {function} onHint - called with hint text when ready
 * @param {function} onStageStart - called when new stage begins (hide bubble)
 */
export function startStageHints(onHint, onStageStart, hintShowMs) {
  engine.start(onHint, onStageStart, hintShowMs);
}

export function stopStageHints() {
  engine.stop();
}

export function setHintShowMs(ms) {
  engine.setHintShowMs(ms);
}

// Also export for manual use
export { buildStagePrompt, RECENT_HINTS };

// Keep the old generateAIHint for backward compat
export async function generateAIHint() {
  const snap = mouseTracker.currentSnapshot();
  if (!snap) return null;

  const actions = mouseTracker.getActionLog();
  const visits = mouseTracker.getVisitHistory();
  const prompt = buildStagePrompt(actions, visits);

  try {
    const result = await aiService.generateHint('stage', { contextPrompt: prompt });
    if (result && typeof result === 'string' && result.trim()) {
      const text = result.trim();
      pushRecent(text);
      return text;
    }
  } catch (e) {
    console.debug('[AIHint] backend failed:', e);
  }

  const fb = _stageFallback(actions, visits);
  pushRecent(fb);
  return fb;
}

export function resetHintUsage() {
  RECENT_HINTS.length = 0;
}
