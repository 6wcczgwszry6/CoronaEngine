import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ROOM_ENTRY_GUIDE_MESSAGE,
  buildDisplayMessages,
} from './roomEntryGuide.js';

const createMessage = (overrides = {}) => ({
  message_id: 'm-1',
  from: '用户',
  text: '你好',
  self: false,
  ...overrides,
});

test('adds the room entry guide before chat messages', () => {
  const messages = buildDisplayMessages({
    messages: [createMessage()],
    memberDetails: [],
    pendingReply: null,
  });

  assert.equal(messages[0].kind, 'room_entry_guide');
  assert.equal(messages[0].renderKey, ROOM_ENTRY_GUIDE_MESSAGE.renderKey);
  assert.match(messages[0].displayText, /@/);
  assert.equal(messages[1].kind, 'message');
  assert.equal(messages[1].displayText, '你好');
});

test('keeps pending replies anchored after the matching user message', () => {
  const messages = buildDisplayMessages({
    messages: [
      createMessage({
        message_id: 'm-self',
        text: '@设计助手 帮我看看',
        self: true,
        correlation_id: 'reply-1',
      }),
    ],
    memberDetails: [],
    pendingReply: {
      correlationId: 'reply-1',
      targetLabel: '设计助手',
    },
  });

  assert.deepEqual(
    messages.map((message) => message.kind),
    ['room_entry_guide', 'message', 'pending_reply'],
  );
});
