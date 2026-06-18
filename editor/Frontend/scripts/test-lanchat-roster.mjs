import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (path) => readFileSync(join(root, path), 'utf8');
const fail = (message) => {
  throw new Error(message);
};
const assertIncludes = (source, needle, message) => {
  if (!source.includes(needle)) fail(message);
};

const store = read('src/stores/lanchat.js');
const disclosureStore = read('src/stores/lanchatDisclosure.js');
const disclosureTest = read('src/stores/lanchatDisclosure.test.mjs');
const bridge = read('src/utils/bridge.js');
const roomPanel = read('src/views/sidebar/lanchat/RoomPanel.vue');
const memberList = read('src/views/sidebar/lanchat/MemberList.vue');
const cefBridge = read('../../src/systems/ui/cef/cef_query_bridge.cpp');
const networkHeader = read('../../include/corona/systems/network/network_system.h');
const networkSystem = read('../../src/systems/network/network_system.cpp');

assertIncludes(store, 'peerId:', 'lanchat store must track local peerId');
assertIncludes(store, 'memberDetails:', 'lanchat store must track memberDetails');
assertIncludes(store, 'normalizeMembers', 'lanchat store must normalize member snapshots');
assertIncludes(store, 'upsertMessage', 'lanchat store must upsert messages by message_id');
assertIncludes(store, 'sortMessages', 'lanchat store must sort messages by authoritative sequence');
assertIncludes(store, "case 'history_snapshot'", 'lanchat store must consume LANChat history snapshots');
assertIncludes(store, 'resetAfterJoinFailure', 'lanchat store must clear fake rooms after join failure');
assertIncludes(store, "event.code === 'ROOM_NOT_FOUND'", 'lanchat store must handle missing LANChat room errors');
assertIncludes(store, "event.code === 'JOIN_TIMEOUT'", 'lanchat store must handle LANChat join timeout errors');
assertIncludes(store, 'function isJoining', 'lanchat store must expose pending join state');
assertIncludes(store, "case 'history_snapshot':", 'history snapshot must be the join success signal');
assertIncludes(store, 'msg.sender_id === state.peerId', 'lanchat store must prefer peerId for self messages');
assertIncludes(store, 'state.agents = res.agents || []', 'joinRoom must initialize agent roster');
assertIncludes(store, 'event.member_details', 'member_update must consume member_details');
assertIncludes(store, 'function upsertAgent', 'lanchat store must support local agent roster upsert');
assertIncludes(store, 'upsertAgent(added)', 'addAgent must make new agents immediately mentionable');
assertIncludes(store, 'removeAgentFromRoster(agentId)', 'removeAgent must clear local mention roster optimistically');
assertIncludes(store, 'sender_type:', 'lanchat store must preserve LANChat message v2 sender_type');
assertIncludes(store, 'message_kind:', 'lanchat store must preserve LANChat message v2 message_kind');
assertIncludes(store, 'correlation_id:', 'lanchat store must preserve LANChat message v2 correlation_id');
assertIncludes(store, 'metadata: parseMetadata(msg)', 'lanchat store must parse LANChat message v2 metadata');
assertIncludes(store, 'function dismissDisclosureByProposal', 'lanchat store must support dismissing handled host confirmation disclosures');
assertIncludes(store, 'function proposalIdForDisclosure', 'lanchat store must normalize proposal ids for disclosure dismissal');
assertIncludes(store, 'item.metadata?.intervention?.proposal_id', 'lanchat store must dismiss nested final-adjustment/conflict proposal disclosures');
assertIncludes(store, 'dismissDisclosureByProposal,', 'lanchat store must export handled disclosure dismissal');
assertIncludes(store, 'state.disclosures = []', 'authoritative room/history resets must clear stale disclosures');
assertIncludes(store, 'function pruneDisclosures', 'lanchat store must prune disclosure state through a dedicated policy');
assertIncludes(store, 'function isPendingConfirmationDisclosure', 'lanchat store must identify host confirmations before pruning disclosures');
assertIncludes(store, 'item.requires_confirmation && proposalIdForDisclosure(item)', 'disclosure pruning must protect pending confirmation proposals');
assertIncludes(store, 'nickname: hostNickname', 'openRoom must send the host nickname to CEF');
assertIncludes(store, 'state.nickname = res.you || hostNickname', 'openRoom must preserve the final host nickname');

assertIncludes(roomPanel, 'member.member_id !== s.peerId', 'mention candidates must filter local member_id');
assertIncludes(roomPanel, 'a.name, isAgent: true', 'mention candidates must include agents');
assertIncludes(roomPanel, ':peer-id="s.peerId"', 'MemberList must receive stable peerId');
assertIncludes(roomPanel, 'isJoining', 'RoomPanel must render pending join state');
assertIncludes(roomPanel, ':disabled="isJoining"', 'RoomPanel must disable join controls while pending');
assertIncludes(roomPanel, 'JOIN_TIMEOUT', 'RoomPanel must display join timeout errors');
assertIncludes(roomPanel, 'HOST_UNREACHABLE', 'RoomPanel must display unreachable host errors');
assertIncludes(roomPanel, 'function gmProposalId', 'RoomPanel must detect GM proposal ids');
assertIncludes(roomPanel, "message?.message_kind === 'gm_proposal'", 'RoomPanel must prefer LANChat v2 gm_proposal messages');
assertIncludes(roomPanel, 'String(message.correlation_id)', 'RoomPanel must use correlation_id as GM proposal id');
assertIncludes(roomPanel, "s.role === 'host'", 'RoomPanel must only show GM confirmation controls to host');
assertIncludes(roomPanel, 'function sendGmDecision', 'RoomPanel must send structured GM decisions');
assertIncludes(roomPanel, "item.requires_confirmation && item.proposal_id", 'RoomPanel must prioritize pending host confirmations over routine progress disclosures');
assertIncludes(roomPanel, 'lanchat.dismissDisclosureByProposal(proposalId)', 'RoomPanel must locally clear handled GM confirmation disclosures');
assertIncludes(roomPanel, 'buildGmDecisionMessage', 'RoomPanel must use the shared structured GM decision builder');
assertIncludes(roomPanel, 'buildGmDisclosureActionMessage', 'RoomPanel must use the shared GM disclosure action builder');
assertIncludes(roomPanel, 'buildManualGmMessageOptions', 'RoomPanel must use the shared manual GM options builder');
assertIncludes(roomPanel, 'buildParticipantDisclosureDraft', 'RoomPanel must use the shared participant intervention draft builder');
assertIncludes(roomPanel, 'function sendDisclosureAction', 'RoomPanel must send clickable disclosure actions through the shared builder');
assertIncludes(roomPanel, 'function isDisclosureActionSendable', 'RoomPanel must only render supported disclosure actions as buttons');
assertIncludes(roomPanel, 'return buildManualGmMessageOptions(s.role)', 'manual @GM messages must derive host identity through the shared builder');
assertIncludes(roomPanel, 'ref="draftInput"', 'RoomPanel must be able to focus input after participant quick-action draft');
assertIncludes(roomPanel, 'draft.value = draftText', 'RoomPanel participant quick actions must prefill the chat draft instead of sending vague empty actions');
assertIncludes(roomPanel, "reject_conflict_resolution: '拒绝仲裁'", 'RoomPanel must translate reject conflict action without leaking internal ids');
assertIncludes(roomPanel, "}[action] || '查看状态'", 'RoomPanel must hide unknown disclosure action enums behind a user-facing fallback');
if (roomPanel.includes('}[action] || action')) {
  fail('RoomPanel must not render unknown disclosure action enums directly');
}
assertIncludes(disclosureStore, 'export function buildGmDecisionMessage', 'disclosure store must expose structured GM decision builder');
assertIncludes(disclosureStore, 'export function buildGmDisclosureActionMessage', 'disclosure store must expose safe GM action message builder');
assertIncludes(disclosureStore, 'export function buildManualGmMessageOptions', 'disclosure store must expose manual GM options builder');
assertIncludes(disclosureStore, 'export function buildParticipantDisclosureDraft', 'disclosure store must expose participant intervention draft builder');
assertIncludes(disclosureStore, 'add_note: `说明：${suffix}`', 'participant note draft must not use add-like wording that Coordinator may classify as add');
assertIncludes(disclosureStore, "request_clarification: '@GM 需要补充关键意图，请先澄清后再确认。'", 'GM action builder must support clarification requests');
assertIncludes(disclosureStore, "pause_discussion: '@GM 先讨论，不要生成'", 'GM action builder must support discussion pause');
assertIncludes(disclosureTest, 'clarify.options.sender_role', 'disclosure test must cover explicit host role in GM action options');
assertIncludes(disclosureTest, 'pause.options.metadata.sender_role', 'disclosure test must cover explicit host role in GM action metadata');
assertIncludes(disclosureStore, 'request_add: `新增：${suffix}`', 'participant draft builder must support add intervention');
assertIncludes(disclosureStore, 'report_issue: `问题：${suffix}`', 'participant draft builder must support issue reports');
assertIncludes(disclosureStore, "message_kind: 'confirmation'", 'GM confirmation builder must send structured confirmation');
assertIncludes(disclosureStore, 'correlation_id: id', 'GM confirmation builder must preserve proposal correlation_id');
assertIncludes(disclosureStore, "sender_role: 'host'", 'GM confirmation builder must carry explicit host role');
assertIncludes(disclosureStore, 'is_host: true', 'GM confirmation builder must carry explicit host boolean');
assertIncludes(disclosureTest, 'confirm.options.sender_role', 'disclosure test must cover explicit host role in GM confirmation options');
assertIncludes(disclosureTest, "buildManualGmMessageOptions('guest')", 'disclosure test must cover participant manual GM role options');
assertIncludes(store, 'lanChatService.sendMessage(trimmed, options)', 'lanchat store must pass structured message options through');
assertIncludes(bridge, '{ text, ...(options || {}) }', 'LANChat bridge must preserve structured sendMessage options');
assertIncludes(bridge, "Bridge.callCEF('LANChat', 'send_message'", 'LANChat bridge must route sendMessage through CEF LANChat module');
assertIncludes(roomPanel, 'resourceDiagnosisText', 'RoomPanel must render safe resource diagnosis text');
assertIncludes(roomPanel, 'function resourceDiagnosisLabel', 'RoomPanel must map scheduler diagnosis to user-facing text');
assertIncludes(roomPanel, '资源状态：生成已停止', 'RoomPanel must translate stopped scheduler diagnosis without exposing internal codes');
assertIncludes(roomPanel, '资源状态：队列拥堵', 'RoomPanel must translate saturated scheduler diagnosis without exposing internal codes');
assertIncludes(disclosureTest, 'diagnosis', 'disclosure test must cover safe scheduler diagnosis metadata');
assertIncludes(roomPanel, '房主端口', 'RoomPanel must not imply LANChat always uses default 8770');

assertIncludes(memberList, 'peerId', 'MemberList must accept peerId prop');
assertIncludes(memberList, 'a.owner === peerId', 'agent remove visibility must compare owner to peerId');

assertIncludes(networkHeader, 'session_port() const', 'NetworkSystem must expose the active ENet listen port');
assertIncludes(networkSystem, 'if (impl_->session_role != SessionRole::Host) return;', 'clients must not process LANChat join packets');
assertIncludes(networkSystem, 'MessageType::CHAT_HISTORY_SNAPSHOT', 'NetworkSystem must handle LANChat history snapshots');
assertIncludes(networkSystem, 'MessageType::CHAT_JOIN_REJECT', 'NetworkSystem must handle LANChat join rejection');
assertIncludes(networkSystem, 'lanchat_join_pending', 'NetworkSystem must track pending LANChat joins');
assertIncludes(networkSystem, 'JOIN_TIMEOUT', 'NetworkSystem must emit LANChat join timeout errors');
assertIncludes(networkSystem, 'ROOM_NOT_FOUND', 'NetworkSystem must reject joins when no LANChat room is open');
assertIncludes(networkSystem, 'uint16_t NetworkSystem::session_port() const', 'NetworkSystem must return the active ENet listen port');
assertIncludes(networkSystem, 'effective_port', 'LANChat join must prefer the already-connected collaboration host port');
assertIncludes(networkSystem, 'send_lanchat_join_to_ready_peer', 'LANChat join must send CHAT_JOIN on existing ready peers');
assertIncludes(networkSystem, 'complete_lanchat_join_if_ready', 'LANChat join completion must be shared by member and history snapshots');
assertIncludes(networkSystem, 'send_to_connected_host_peer(packet)', 'clients must send LANChat packets to the connected host instead of broadcasting loops');
assertIncludes(networkSystem, 'result = impl_->lanchat.record_message', 'host must assign authoritative LANChat message sequence');
assertIncludes(networkSystem, 'result = impl_->lanchat.apply_remote_message', 'clients must only apply authoritative LANChat messages');
assertIncludes(networkSystem, 'skipped history snapshot', 'missing join peer must not fall back to broadcasting history');
assertIncludes(cefBridge, 'payload["listen_port"] = sys->session_port()', 'Network bridge must expose the local ENet listen port');
assertIncludes(cefBridge, 'payload_arg["metadata"].dump()', 'LANChat send_message must serialize structured metadata for native delivery');
assertIncludes(cefBridge, 'const std::string message_kind = payload_arg.value("message_kind", "chat")', 'LANChat send_message must preserve structured message_kind');
assertIncludes(cefBridge, 'const std::string target_agent_id = payload_arg.value("target_agent_id", "")', 'LANChat send_message must preserve target_agent_id for GM/agent routing');
assertIncludes(cefBridge, 'const std::string source_user_id = payload_arg.value("source_user_id", "")', 'LANChat send_message must preserve source_user_id for Coordinator audit');
assertIncludes(cefBridge, 'const std::string correlation_id = payload_arg.value("correlation_id", "")', 'LANChat send_message must preserve proposal correlation_id');
assertIncludes(cefBridge, 'text, message_kind, target_agent_id, source_user_id', 'LANChat send_message must pass structured routing fields into NetworkSystem');
assertIncludes(cefBridge, 'correlation_id, metadata_json', 'LANChat send_message must pass correlation_id and metadata_json into NetworkSystem');
assertIncludes(cefBridge, 'const uint16_t actual_port = sys->session_port() != 0 ? sys->session_port() : port', 'LANChat start_room must return the actual session port');
assertIncludes(cefBridge, 'const std::string nickname = payload_arg.value("nickname", "房主")', 'LANChat start_room must read host nickname from payload');
assertIncludes(cefBridge, 'data["you"] = host_nickname', 'LANChat start_room must return the final host nickname');
assertIncludes(cefBridge, 'sys->session_port() != 0 ? sys->session_port() : 8770', 'LANChat get_local_ip must return the active session port when available');
if (cefBridge.includes('data["port"] = 8770;')) {
  fail('LANChat bridge must not hard-code get_local_ip port to 8770');
}
const chatJoinBranch = networkSystem.slice(
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_JOIN) {'),
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_JOIN_REJECT) {'),
);
if (chatJoinBranch.includes('impl_->lanchat.open_room(')) {
  fail('CHAT_JOIN handling must not implicitly create a LANChat room');
}
const memberUpdateBranch = networkSystem.slice(
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_MEMBER_UPDATE) {'),
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_HISTORY_SNAPSHOT ||'),
);
assertIncludes(memberUpdateBranch, 'complete_lanchat_join_if_ready', 'member snapshots must complete pending joins when history arrived first');
const historySnapshotBranchCpp = networkSystem.slice(
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_HISTORY_SNAPSHOT ||'),
  networkSystem.indexOf('} else if (mt == MessageType::CHAT_MESSAGE ||'),
);
assertIncludes(historySnapshotBranchCpp, 'complete_lanchat_join_if_ready', 'history snapshots must complete pending joins when members arrived first');
const joinRoomStart = store.indexOf('async function joinRoom');
const sendMessageStart = store.indexOf('async function sendMessage');
const joinRoomBody = store.slice(joinRoomStart, sendMessageStart);
if (joinRoomBody.includes('state.inRoom = true')) {
  fail('joinRoom must not mark the user in-room before history_snapshot');
}
const historySnapshotStart = store.indexOf("case 'history_snapshot':");
const agentRosterStart = store.indexOf("case 'agent_roster':");
const historySnapshotBranch = store.slice(historySnapshotStart, agentRosterStart);
if (!historySnapshotBranch.includes('state.inRoom = true')) {
  fail('history_snapshot must mark the user in-room');
}
const applyHistoryStart = store.indexOf('function applyHistorySnapshot');
const normalizeMembersStart = store.indexOf('function normalizeMembers');
const applyHistoryBody = store.slice(applyHistoryStart, normalizeMembersStart);
const replaceBranch = applyHistoryBody.slice(
  applyHistoryBody.indexOf('if (replace)'),
  applyHistoryBody.indexOf('for (const message of history)')
);
assertIncludes(replaceBranch, 'state.messages = []', 'authoritative history replacement must clear old messages');
assertIncludes(replaceBranch, 'state.disclosures = []', 'authoritative history replacement must clear stale disclosure state');
const upsertDisclosureStart = store.indexOf('function upsertDisclosureFromMessage');
const dismissDisclosureStart = store.indexOf('function dismissDisclosureByProposal');
const disclosurePruningBody = store.slice(upsertDisclosureStart, dismissDisclosureStart);
assertIncludes(disclosurePruningBody, 'pruneDisclosures()', 'disclosure overflow must use confirmation-aware pruning');
if (disclosurePruningBody.includes('state.disclosures = state.disclosures.slice(-20)')) {
  fail('disclosure overflow must not blindly slice off pending host confirmations');
}

console.log('LANChat roster constraints OK');
