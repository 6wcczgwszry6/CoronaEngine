export function resolveSelectedTargetKey(currentKey, options = []) {
  const key = String(currentKey || '').trim();
  const list = Array.isArray(options) ? options : [];
  if (key && list.some((item) => item.key === key)) return key;
  return list[0]?.key || 'scene';
}

export function targetPayloadForKey(key, options = []) {
  const list = Array.isArray(options) ? options : [];
  const target = list.find((item) => item.key === key) || list[0] || {};
  return {
    scope: target.scope || 'scene',
    agentId: target.agentId || '',
    agentName: target.agentName || '',
    planId: target.planId || '',
  };
}

export function isGenerationStartText(text = '') {
  const value = String(text || '').trim();
  if (!value) return false;
  return /(确认开始|确认生成|开始生成|直接生成|开始执行|执行生成|按.*方案.*生成|按这个方案生成|就按方案生成)/.test(value);
}

export function effectiveDraftAction(action, text = '') {
  if (isGenerationStartText(text)) return 'generate';
  return String(action || '').trim();
}

export function routeGuardMessage(action, target = {}, text = '') {
  const value = String(text || '').trim();
  if (/^@([^\s，,：:]+)/.test(value)) return '';
  if (isGenerationStartText(value)) return '';
  const draftAction = effectiveDraftAction(action, value);
  const scope = String(target?.scope || '').trim();
  if (draftAction === 'plan' && scope === 'group') {
    return '整理方案需要先选择一个负责出方案的 Agent。';
  }
  if (draftAction === 'supplement' && scope !== 'agent' && scope !== 'plan') {
    return '补充方案需要选择已有方案对应的 Agent。';
  }
  if (draftAction === 'generate' && scope !== 'agent' && scope !== 'plan') {
    return '开始生成需要选择已有方案对应的 Agent。';
  }
  return '';
}
