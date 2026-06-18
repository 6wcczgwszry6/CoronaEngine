/**
 * 局域网聊天室状态（轻量 composable，单例 reactive store）。
 *
 * 项目未使用 Pinia，这里用 Vue reactive 提供一个模块级单例，行为类似 store：
 * - 持有连接态、房间信息、成员、消息列表。
 * - 提供 open/join/leave/send 等动作（封装 lanChatService 调用）。
 * - 暴露 handleEvent(event) 供 AITalkBar 的 receiveAIMessageChunk 在
 *   channel === 'lanchat' 时分流调用，更新本 store。
 *
 * 不直接监听 window 回调；由 AITalkBar 统一分流，避免与 AI 流式回调争用。
 */
import { reactive, readonly } from 'vue';
import { lanChatService } from '../utils/bridge.js';
import {
  disclosureVisibleForRole,
  disclosureVisibleForRoom,
  extractDisclosureFromMessage,
} from './lanchatDisclosure.js';

// 连接状态机：idle（未进房）-> hosting/joined（在房）
const ROLE = { NONE: 'none', HOST: 'host', GUEST: 'guest' };

// 房主在房间内的显示昵称。必须与 C++ LANChat 快速通道保持一致；
// 房主消息由 NetworkSystem 用该名盖章，前端据此判定 self（消息气泡右对齐）。
const HOST_NICKNAME = '房主';

const state = reactive({
  role: ROLE.NONE, // none / host / guest
  mode: 'multi', // multi / single
  inRoom: false,
  connection: 'idle', // idle / connecting / syncing / connected / reconnecting
  room: '', // 房间号
  ip: '', // 房主显示用：本机 IP；加入方：房主 IP
  port: 27960,
  peerId: '',
  nickname: '',
  members: [], // string[]
  memberDetails: [], // [{ member_id, nickname, status }]
  messages: [], // { message_id, sender_id, room_id, seq, from, text, ts, self }
  disclosures: [], // safe stage/progress cards derived from metadata
  processedProposalIds: [], // proposal ids already confirmed/rejected locally or by GM reply
  error: '', // 最近一次错误码/信息
  agents: [], // [{agent_id, name, owner}] 来自房主 agent_roster，不含 persona
  myAgents: [], // 我添加的 agent 本地草稿 [{agent_id, name, persona}]，用于显示"我的"
});

function _resetRoom() {
  state.role = ROLE.NONE;
  state.mode = 'multi';
  state.inRoom = false;
  state.connection = 'idle';
  state.room = '';
  state.ip = '';
  state.peerId = '';
  state.nickname = '';
  state.members = [];
  state.memberDetails = [];
  state.messages = [];
  state.disclosures = [];
  state.processedProposalIds = [];
  state.error = '';
  state.agents = [];
  state.myAgents = [];
}

function resetAfterJoinFailure(code) {
  _resetRoom();
  state.error = code || 'JOIN_FAILED';
}

function isConnected() {
  return state.inRoom && state.connection === 'connected';
}

function isJoining() {
  return state.role === ROLE.GUEST && !state.inRoom && (
    state.connection === 'connecting' || state.connection === 'syncing'
  );
}

function messageSortKey(message) {
  const seq = Number(message.seq || 0);
  return seq > 0 ? seq : Number.MAX_SAFE_INTEGER;
}

function sortMessages() {
  state.messages.sort((a, b) => {
    const seqDiff = messageSortKey(a) - messageSortKey(b);
    if (seqDiff !== 0) return seqDiff;
    return String(a.message_id || '').localeCompare(String(b.message_id || ''));
  });
}

function messageSelf(msg, fallback = false) {
  if (msg.sender_id && state.peerId) {
    return msg.sender_id === state.peerId;
  }
  return fallback;
}

function parseMetadata(msg = {}) {
  if (msg.metadata && typeof msg.metadata === 'object') return msg.metadata;
  const raw = msg.metadata_json || '';
  if (!raw || typeof raw !== 'string') return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (e) {
    return {};
  }
}

function upsertDisclosureFromMessage(message) {
  const disclosure = extractDisclosureFromMessage(message, state.room, state.role);
  if (!disclosure || !disclosure.public_message) return;
  if (!disclosureVisibleForRoom(disclosure, state.room)) return;
  if (!disclosureVisibleForRole(disclosure, state.role)) return;
  const key = disclosure.event_id || `${disclosure.room_id}:${disclosure.stage}:${disclosure.created_at}`;
  const existing = state.disclosures.find((item) => (item.event_id || '') === key);
  if (existing) {
    Object.assign(existing, { ...disclosure, event_id: key });
  } else {
    state.disclosures.push({ ...disclosure, event_id: key });
  }
  if (state.disclosures.length > 20) {
    pruneDisclosures();
  }
}

function disclosureRetentionKey(item = {}) {
  return String(item.event_id || proposalIdForDisclosure(item) || `${item.room_id}:${item.stage}:${item.created_at}`);
}

function isPendingConfirmationDisclosure(item = {}) {
  const proposalId = proposalIdForDisclosure(item);
  return Boolean(item.requires_confirmation && proposalId && !isProposalHandled(proposalId));
}

function pruneDisclosures(limit = 20) {
  const pending = state.disclosures.filter(isPendingConfirmationDisclosure).slice(-limit);
  const pendingKeys = new Set(pending.map(disclosureRetentionKey));
  const routineLimit = Math.max(0, limit - pending.length);
  const routine = state.disclosures
    .filter((item) => !pendingKeys.has(disclosureRetentionKey(item)))
    .slice(routineLimit > 0 ? -routineLimit : state.disclosures.length);
  const keepKeys = new Set([...pending, ...routine].map(disclosureRetentionKey));
  state.disclosures = state.disclosures.filter((item) => keepKeys.has(disclosureRetentionKey(item)));
}

function dismissDisclosureByProposal(proposalId = '') {
  const id = String(proposalId || '').trim();
  if (!id) return;
  markProposalHandled(id);
  state.disclosures = state.disclosures.filter((item) => proposalIdForDisclosure(item) !== id);
}

function proposalIdForDisclosure(item = {}) {
  return String(
    item.proposal_id ||
    item.metadata?.proposal_id ||
    item.metadata?.intervention?.proposal_id ||
    ''
  ).trim();
}

function normalizeProposalId(proposalId = '') {
  return String(proposalId || '').trim().toLowerCase();
}

function markProposalHandled(proposalId = '') {
  const id = normalizeProposalId(proposalId);
  if (!id || state.processedProposalIds.includes(id)) return;
  state.processedProposalIds.push(id);
  if (state.processedProposalIds.length > 100) {
    state.processedProposalIds.splice(0, state.processedProposalIds.length - 100);
  }
}

function isProposalHandled(proposalId = '') {
  const id = normalizeProposalId(proposalId);
  return Boolean(id && state.processedProposalIds.includes(id));
}

function rememberProcessedProposalFromMessage(message = {}) {
  const text = String(message.text || '');
  const kind = String(message.message_kind || '').toLowerCase();
  const ids = new Set();
  const metadataProposalId = message.metadata?.proposal_id || message.metadata?.intervention?.proposal_id;
  if (metadataProposalId && kind === 'confirmation') {
    ids.add(String(metadataProposalId));
  }
  const processedPattern = /(?:已确认|已取消|已拒绝|已处理|不会重复|不会执行)[\s\S]{0,40}\b((?:gm-\d+|fa-[\w.-]+|cr-[\w.-]+))\b|\b((?:gm-\d+|fa-[\w.-]+|cr-[\w.-]+))\b[\s\S]{0,40}(?:已确认|已取消|已拒绝|已处理|不会重复|不会执行)/gi;
  let match;
  while ((match = processedPattern.exec(text)) !== null) {
    ids.add(match[1] || match[2]);
  }
  for (const id of ids) {
    markProposalHandled(id);
    state.disclosures = state.disclosures.filter((item) => normalizeProposalId(proposalIdForDisclosure(item)) !== normalizeProposalId(id));
  }
}

function normalizeMessage(msg, self = false) {
  return {
    message_id: msg.message_id || '',
    sender_id: msg.sender_id || '',
    room_id: msg.room_id || state.room || '',
    seq: msg.seq || 0,
    from: msg.from || '?',
    text: msg.text || '',
    ts: msg.ts || Math.floor(Date.now() / 1000),
    sender_type: msg.sender_type || 'user',
    message_kind: msg.message_kind || 'chat',
    target_agent_id: msg.target_agent_id || '',
    source_user_id: msg.source_user_id || '',
    correlation_id: msg.correlation_id || '',
    metadata_json: msg.metadata_json || '',
    metadata: parseMetadata(msg),
    self: messageSelf(msg, self),
  };
}

function upsertMessage(msg, self = false) {
  const normalized = normalizeMessage(msg, self);
  rememberProcessedProposalFromMessage(normalized);
  const existing = normalized.message_id
    ? state.messages.find((m) => m.message_id === normalized.message_id)
    : null;
  if (existing) {
    Object.assign(existing, normalized);
  } else {
    state.messages.push(normalized);
  }
  sortMessages();
  upsertDisclosureFromMessage(normalized);
}

function applyHistorySnapshot(history = [], replace = false) {
  if (!Array.isArray(history)) return;
  if (replace) {
    state.messages = [];
    state.disclosures = [];
    state.processedProposalIds = [];
  }
  for (const message of history) {
    upsertMessage(message, messageSelf(message, message.from === state.nickname));
  }
}

function normalizeMembers(payload = {}) {
  const memberDetails = Array.isArray(payload.member_details)
    ? payload.member_details
        .map((m) => ({
          member_id: m.member_id || m.id || '',
          nickname: m.nickname || m.name || '',
          status: m.status || 'online',
        }))
        .filter((m) => m.nickname)
    : [];
  const members = memberDetails.length
    ? memberDetails.map((m) => m.nickname)
    : (Array.isArray(payload.members) ? payload.members : [])
        .map((m) => (typeof m === 'string' ? m : (m.nickname || m.name || '')))
        .filter(Boolean);
  return { members, memberDetails };
}

function applyMemberSnapshot(payload = {}) {
  if (payload.peer_id) state.peerId = payload.peer_id;
  const normalized = normalizeMembers(payload);
  state.members = normalized.members;
  state.memberDetails = normalized.memberDetails;
}

function upsertAgent(agent = {}) {
  const agentId = agent.agent_id || agent.id || '';
  const name = agent.name || agent.agent_name || '';
  if (!agentId || !name) return;
  const normalized = {
    agent_id: agentId,
    name,
    owner: agent.owner || agent.owner_id || state.peerId || '',
    persona: agent.persona || '',
  };
  const existing = state.agents.find((item) => item.agent_id === agentId);
  if (existing) {
    Object.assign(existing, normalized);
  } else {
    state.agents.push(normalized);
  }
}

function removeAgentFromRoster(agentId) {
  state.agents = state.agents.filter((a) => a.agent_id !== agentId);
}

// ---- 动作 -----------------------------------------------------------------

function applyHostRoomState({ room, mode, res, hostNickname = HOST_NICKNAME }) {
  state.role = ROLE.HOST;
  state.mode = mode;
  state.inRoom = true;
  state.connection = 'connected';
  state.room = room;
  state.ip = res.ip || '';
  state.port = res.port || 0;
  state.peerId = res.peer_id || '';
  state.nickname = res.you || hostNickname;
  applyMemberSnapshot(res);
  if (!state.members.length) state.members = [state.nickname];
  state.messages = [];
  state.disclosures = [];
  state.agents = res.agents || [];
}

async function openLocalRoom({ room, password, nickname }) {
  state.error = '';
  const hostNickname = (nickname || HOST_NICKNAME).trim() || HOST_NICKNAME;
  const res = await lanChatService.startLocalRoom({
    room,
    password,
    mode: 'single',
    nickname: hostNickname,
  });
  if (res && res.ok) {
    applyHostRoomState({ room, mode: 'single', res, hostNickname });
  } else {
    state.error = (res && res.error) || 'START_FAILED';
  }
  return res;
}

/** 房主开房。返回 { ok, ip, port } 或 { ok:false, error }。 */
async function openRoom({ room, password, port, nickname, mode = 'multi' }) {
  if (mode === 'single') {
    return openLocalRoom({ room, password, nickname });
  }
  state.error = '';
  const hostNickname = (nickname || HOST_NICKNAME).trim() || HOST_NICKNAME;
  const res = await lanChatService.startRoom({
    room,
    password,
    port,
    nickname: hostNickname,
    mode: 'multi',
  });
  if (res && res.ok) {
    applyHostRoomState({ room, mode: 'multi', res, hostNickname });
  } else {
    state.error = (res && res.error) || 'START_FAILED';
  }
  return res;
}

/** 房主关房。 */
async function closeRoom() {
  if (state.mode === 'single') {
    await lanChatService.stopLocalRoom();
  } else {
    await lanChatService.stopRoom();
  }
  _resetRoom();
}

/** 加入方加入房间。 */
async function joinRoom({ ip, port, room, password, nickname }) {
  state.error = '';
  const res = await lanChatService.joinRoom({ ip, port, room, password, nickname });
  if (res && res.ok) {
    state.role = ROLE.GUEST;
    state.inRoom = false;
    state.connection = 'connecting';
    state.room = room;
    state.ip = ip;
    state.port = res.port || port;
    state.mode = 'multi';
    state.peerId = res.peer_id || '';
    // 服务器去重后的最终昵称（如 Alice -> Alice-2）
    state.nickname = res.you || nickname;
    applyMemberSnapshot(res);
    applyHistorySnapshot(res.history || [], true);
    state.agents = res.agents || [];
  } else {
    state.error = (res && res.code) || (res && res.error) || 'JOIN_FAILED';
  }
  return res;
}

/** 加入方离开房间。 */
async function leaveRoom() {
  await lanChatService.leaveRoom();
  _resetRoom();
}

/** 发送一条消息。本地不乐观插入，统一由服务器广播回显，保证顺序与去重一致。 */
async function sendMessage(text, options = {}) {
  const trimmed = (text || '').trim();
  if (!trimmed || !state.inRoom) return;
  if (!isConnected()) {
    state.error = state.connection === 'syncing' ? 'SYNCING' : 'CONNECTING';
    return { ok: false, error: state.error };
  }
  const res = await lanChatService.sendMessage(trimmed, options);
  if (res && res.ok === false) {
    state.error = res.error || 'SEND_FAILED';
    if (state.error === 'CONNECTING') {
      state.connection = 'connecting';
    }
  } else {
    state.error = '';
  }
}

/** 添加 AI 助手。{ name, persona } */
async function addAgent({ name, persona }) {
  state.error = '';
  if (!isConnected()) {
    state.error = state.connection === 'syncing' ? 'SYNCING' : 'CONNECTING';
    return { ok: false, error: state.error };
  }
  let res;
  try {
    res = await lanChatService.addAgent({ name, persona });
  } catch (e) {
    state.error = 'ADD_AGENT_FAILED';
    return { ok: false, error: 'ADD_AGENT_FAILED' };
  }
  if (res && res.ok) {
    const added = { agent_id: res.agent_id, name: res.name || name, persona, owner: state.peerId };
    state.myAgents.push(added);
    upsertAgent(added);
  } else {
    state.error = (res && res.error) || 'ADD_AGENT_FAILED';
  }
  return res;
}

/** 移除 AI 助手。 */
async function removeAgent(agentId) {
  state.error = '';
  if (!isConnected()) {
    state.error = state.connection === 'syncing' ? 'SYNCING' : 'CONNECTING';
    return { ok: false };
  }
  try {
    await lanChatService.removeAgent(agentId);
  } catch (e) {
    state.error = 'REMOVE_AGENT_FAILED';
    return { ok: false };
  }
  state.myAgents = state.myAgents.filter((a) => a.agent_id !== agentId);
  removeAgentFromRoster(agentId);
  return { ok: true };
}

// ---- 事件分流（由 AITalkBar 调用）----------------------------------------

/**
 * 处理来自 C++ NetworkSystem 的聊天室事件（channel === 'lanchat'）。
 * @param {object} event - { channel, event, from, text, ts, members, history, code }
 */
function handleEvent(event) {
  if (!event || event.channel !== 'lanchat') return;
  switch (event.event) {
    case 'message':
      upsertMessage(event, event.from === state.nickname);
      break;
    case 'member_update':
      applyMemberSnapshot(event);
      if (state.role === ROLE.GUEST && state.connection === 'connecting') {
        state.connection = 'syncing';
        state.error = '';
      }
      break;
    case 'history_snapshot':
      applyHistorySnapshot(event.history || [], true);
      if (state.role === ROLE.GUEST && (state.connection === 'connecting' || state.connection === 'syncing')) {
        state.inRoom = true;
        state.connection = 'connected';
        state.error = '';
      }
      break;
    case 'agent_roster':
      state.agents = event.agents || [];
      break;
    case 'joined':
      applyMemberSnapshot(event);
      if (Array.isArray(event.history)) {
        applyHistorySnapshot(event.history, true);
      }
      break;
    case 'reconnecting':
      // 连接断开，正在自动重连：保留消息，仅切换状态供 UI 提示
      state.connection = 'reconnecting';
      state.error = '';
      break;
    case 'reconnected':
      // 重连成功：用服务器最新状态校正成员/历史与最终昵称
      state.connection = 'connected';
      state.error = '';
      if (event.you) state.nickname = event.you;
      applyMemberSnapshot({
        ...event,
        members: event.members || state.members,
        member_details: event.member_details || state.memberDetails,
      });
      if (Array.isArray(event.history)) {
        applyHistorySnapshot(event.history, true);
      }
      break;
    case 'room_closed':
      _resetRoom();
      state.error = 'ROOM_CLOSED';
      break;
    case 'error':
      state.error = event.code || 'ERROR';
      if (
        event.code === 'ROOM_NOT_FOUND' ||
        event.code === 'ROOM_MISMATCH' ||
        event.code === 'JOIN_TIMEOUT' ||
        event.code === 'HOST_UNREACHABLE'
      ) {
        resetAfterJoinFailure(event.code);
        break;
      }
      if (event.code === 'RECONNECT_FAILED' || event.code === 'RECONNECT_REJECTED') {
        state.connection = 'idle';
        state.inRoom = false;
      }
      break;
    default:
      break;
  }
}

export const lanchat = {
  state: readonly(state),
  ROLE,
  openRoom,
  openLocalRoom,
  closeRoom,
  joinRoom,
  leaveRoom,
  sendMessage,
  addAgent,
  removeAgent,
  handleEvent,
  isJoining,
  dismissDisclosureByProposal,
  markProposalHandled,
  isProposalHandled,
};

export default lanchat;
