import {
  aiReplyDisplayText,
  displaySenderName,
} from './routeSelection.js';

export const ROOM_ENTRY_GUIDE_MESSAGE = {
  renderKey: 'room-entry-guide',
  kind: 'room_entry_guide',
  self: false,
  displayFrom: '系统提示',
  displayText: '欢迎进入对话房间。可以直接输入内容与成员协作；输入 @ 可指定 AI 助手；需要执行生成时，先说明方案，再确认开始生成。',
};

export function buildDisplayMessages({
  messages = [],
  memberDetails = [],
  pendingReply = null,
} = {}) {
  const sourceMessages = Array.isArray(messages) ? messages : [];
  const displayed = sourceMessages.map((message, index) => ({
    ...message,
    displayFrom: displaySenderName(message),
    displayText: aiReplyDisplayText(message, sourceMessages, memberDetails),
    renderKey: message.message_id || `message-${index}`,
    kind: 'message',
  }));

  const result = [ROOM_ENTRY_GUIDE_MESSAGE, ...displayed];
  if (!pendingReply) return result;

  const pendingMessage = {
    ...pendingReply,
    renderKey: `pending-${pendingReply.correlationId}`,
    kind: 'pending_reply',
    self: false,
  };
  const anchorIndex = result.findIndex((message) => (
    message.kind === 'message' &&
    message.self &&
    pendingReply.correlationId &&
    message.correlation_id === pendingReply.correlationId
  ));
  if (anchorIndex >= 0) {
    return [
      ...result.slice(0, anchorIndex + 1),
      pendingMessage,
      ...result.slice(anchorIndex + 1),
    ];
  }
  return [...result, pendingMessage];
}
