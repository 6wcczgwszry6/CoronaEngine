import assert from 'node:assert/strict';

import {
  aiReplyAddressedUserName,
  aiReplyDisplayText,
  displaySenderName,
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

const memberDetails = [
  { member_id: 'u1', nickname: 'Alice' },
  { member_id: 'u2', nickname: 'Alice_1' },
];
const sourceMessages = [
  {
    message_id: 'ask-1',
    sender_id: 'u1',
    from: 'Alice',
    sender_type: 'user',
    message_kind: 'chat',
    target_agent_id: 'agent-merchant',
    correlation_id: 'corr-1',
    text: '@鍟嗕汉 方案一',
  },
  {
    message_id: 'ask-2',
    sender_id: 'u2',
    from: 'Alice_1',
    sender_type: 'user',
    message_kind: 'chat',
    target_agent_id: 'agent-merchant',
    correlation_id: 'corr-2',
    text: '@鍟嗕汉 方案二',
  },
];
assert.equal(
  aiReplyDisplayText(
    {
      sender_id: 'agent-merchant',
      sender_type: 'agent',
      message_kind: 'agent_reply',
      source_user_id: 'u1',
      correlation_id: 'corr-1',
      text: '回复一',
    },
    sourceMessages,
    memberDetails
  ),
  '@Alice 回复一'
);
assert.equal(
  aiReplyDisplayText(
    {
      sender_id: 'agent-merchant',
      sender_type: 'agent',
      message_kind: 'agent_reply',
      source_user_id: 'u2',
      correlation_id: 'corr-2',
      text: '回复二',
    },
    sourceMessages,
    memberDetails
  ),
  '@Alice_1 回复二'
);
assert.equal(
  displaySenderName({
    sender_id: 'agent-merchant',
    from: '商人',
    sender_type: 'agent',
    message_kind: 'agent_reply',
  }),
  '🤖商人'
);
assert.equal(
  displaySenderName({
    sender_id: 'u1',
    from: 'Alice',
    sender_type: 'user',
    message_kind: 'chat',
  }),
  'Alice'
);
assert.equal(
  aiReplyAddressedUserName(
    {
      sender_id: 'agent-merchant',
      sender_type: 'agent',
      message_kind: 'agent_reply',
      correlation_id: 'corr-2',
      text: '缺 source_user_id 时按 correlation 回找',
    },
    sourceMessages,
    []
  ),
  'Alice_1'
);
assert.equal(
  aiReplyDisplayText(
    { sender_id: 'u1', sender_type: 'user', message_kind: 'chat', text: '普通消息' },
    sourceMessages,
    memberDetails
  ),
  '普通消息'
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
