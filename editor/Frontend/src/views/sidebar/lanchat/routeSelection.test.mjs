import assert from 'node:assert/strict';

import {
  pendingReplyMatchesMessage,
  resolveSelectedTargetKey,
  routeGuardMessage,
  targetKeyFromMentionText,
  targetPayloadForKey,
} from './routeSelection.js';

const options = [
  { key: 'gm', label: '主持人', scope: 'gm', agentId: 'gm', agentName: 'GM' },
  { key: 'agent:elder', label: '长者', scope: 'agent', agentId: 'agent-elder', agentName: '长者' },
  { key: 'agent:girl', label: '小女孩', scope: 'agent', agentId: 'agent-girl', agentName: '小女孩' },
  { key: 'agent:merchant', label: '商人', scope: 'agent', agentId: 'agent-merchant', agentName: '商人' },
  { key: 'group', label: '全部AI助手', scope: 'group' },
];

assert.equal(resolveSelectedTargetKey('', options), '');
assert.equal(resolveSelectedTargetKey('agent:merchant', options), 'agent:merchant');
assert.equal(resolveSelectedTargetKey('missing', options), '');

assert.deepEqual(targetPayloadForKey('agent:merchant', options), {
  scope: 'agent',
  agentId: 'agent-merchant',
  agentName: '商人',
  planId: '',
});

assert.deepEqual(targetPayloadForKey('', options), {
  scope: '',
  agentId: '',
  agentName: '',
  planId: '',
});

assert.equal(targetKeyFromMentionText('@商人 帮我看看', options), 'agent:merchant');
assert.equal(targetKeyFromMentionText('帮我问 @GM', options), 'gm');
assert.equal(targetKeyFromMentionText('帮我问 @gm', options), 'gm');
assert.equal(targetKeyFromMentionText('问一下 @全部AI助手', options), 'group');
assert.equal(targetKeyFromMentionText('商人 帮我看看', options), '');

const pending = { correlationId: 'ui-1', targetAgentId: 'agent-merchant' };
assert.equal(
  pendingReplyMatchesMessage(
    { message_kind: 'agent_reply', correlation_id: 'ui-1', target_agent_id: 'agent-merchant' },
    pending
  ),
  true
);
assert.equal(
  pendingReplyMatchesMessage(
    { message_kind: 'chat', correlation_id: 'ui-1', target_agent_id: 'agent-merchant' },
    pending
  ),
  false
);
assert.equal(
  pendingReplyMatchesMessage(
    { message_kind: 'agent_reply', correlation_id: 'other', target_agent_id: 'agent-merchant' },
    pending
  ),
  false
);
assert.equal(
  pendingReplyMatchesMessage(
    { message_kind: 'agent_reply', correlation_id: 'ui-1', target_agent_id: 'agent-girl' },
    pending
  ),
  false
);

assert.equal(routeGuardMessage('chat', options[0]), '');
assert.equal(routeGuardMessage('plan', options[0]), '');
assert.equal(
  routeGuardMessage('plan', { key: 'group', label: '全部AI助手', scope: 'group' }),
  '生成方案需要先选择一个负责整理方案的 Agent。'
);
assert.equal(
  routeGuardMessage('generate', {}),
  '确认生成需要选择已有方案对应的 Agent。'
);
assert.equal(
  routeGuardMessage('supplement', { key: 'group', label: '全部AI助手', scope: 'group' }),
  '补充要求需要选择已有方案对应的 Agent。'
);
assert.equal(
  routeGuardMessage('plan', { key: 'group', label: '全部AI助手', scope: 'group' }, '@长者 帮我设计客厅'),
  ''
);

console.log('[OK] lanchat route selection keeps explicit target stable');
