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
assertIncludes(store, "const scope = String(target.scope || '').trim()", 'lanchat store must allow an empty active target');
assertIncludes(store, 'if (target.scope) metadata.target_scope = target.scope', 'lanchat store must not serialize scene as the default target scope');
if (store.includes("setActiveTarget({ scope: 'group' })")) {
  fail('lanchat store must not default workspace mode changes to the all-assistant group target');
}
assertIncludes(store, 'sender_type:', 'lanchat store must preserve LANChat message v2 sender_type');
assertIncludes(store, 'message_kind:', 'lanchat store must preserve LANChat message v2 message_kind');
assertIncludes(store, 'correlation_id:', 'lanchat store must preserve LANChat message v2 correlation_id');
assertIncludes(store, 'metadata: parseMetadata(msg)', 'lanchat store must parse LANChat message v2 metadata');
assertIncludes(store, 'function dismissDisclosureByProposal', 'lanchat store must support dismissing handled host confirmation disclosures');
assertIncludes(store, 'processedProposalIds:', 'lanchat store must track processed proposal ids');
assertIncludes(store, 'function markProposalHandled', 'lanchat store must record handled proposal ids');
assertIncludes(store, 'function isProposalHandled', 'lanchat store must expose handled proposal lookup');
assertIncludes(store, 'rememberProcessedProposalFromMessage', 'lanchat store must learn handled proposal ids from GM replies');
assertIncludes(store, 'function proposalIdForDisclosure', 'lanchat store must normalize proposal ids for disclosure dismissal');
assertIncludes(store, 'item.metadata?.intervention?.proposal_id', 'lanchat store must dismiss nested final-adjustment/conflict proposal disclosures');
assertIncludes(store, 'dismissDisclosureByProposal,', 'lanchat store must export handled disclosure dismissal');
assertIncludes(store, 'isProposalHandled,', 'lanchat store must export proposal handled lookup');
assertIncludes(store, 'state.disclosures = []', 'authoritative room/history resets must clear stale disclosures');
assertIncludes(store, 'function pruneDisclosures', 'lanchat store must prune disclosure state through a dedicated policy');
assertIncludes(store, 'function isPendingConfirmationDisclosure', 'lanchat store must identify host confirmations before pruning disclosures');
assertIncludes(store, 'item.requires_confirmation && proposalId && !isProposalHandled(proposalId)', 'disclosure pruning must protect only unhandled pending confirmation proposals');
assertIncludes(store, 'extractDisclosureFromMessage(message, state.room, state.role)', 'lanchat store must resolve host-only disclosure fallback by current role');
assertIncludes(store, 'nickname: hostNickname', 'openRoom must send the host nickname to CEF');
assertIncludes(store, 'state.nickname = res.you || hostNickname', 'openRoom must preserve the final host nickname');
assertIncludes(store, 'mode:', 'lanchat store must track whether the room is single-player or multiplayer');
assertIncludes(store, 'async function openLocalRoom', 'lanchat store must support local single-player rooms');
assertIncludes(store, 'lanChatService.startLocalRoom', 'single-player rooms must use the local LANChat service path');
if (store.includes('await refreshRoomHistory()')) {
  fail('opening a LANChat room must not automatically load persisted history; users choose history explicitly');
}
if (store.includes('function applyHostRoomState') && store.slice(
  store.indexOf('function applyHostRoomState'),
  store.indexOf('async function refreshHistoryRooms'),
).includes('applyHistorySnapshot(res.history || [], true)')) {
  fail('host/local room startup must ignore persisted history returned by older native builds');
}
assertIncludes(store, 'historyRooms:', 'lanchat store must track persisted history room summaries');
assertIncludes(store, 'selectedHistoryRoom:', 'lanchat store must track the selected persisted history room');
assertIncludes(store, 'async function refreshHistoryRooms', 'lanchat store must load persisted history rooms before joining a room');
assertIncludes(store, 'async function loadHistoryRoom', 'lanchat store must load a selected persisted history transcript without opening a room');
assertIncludes(store, 'state.agents = Array.isArray(res.agents) ? res.agents : []', 'loading persisted history must restore its agent roster');
assertIncludes(store, "agent.owner === 'local-single-player'", 'single-player history agents must be treated as locally owned after restore');
assertIncludes(store, 'async function continueHistoryAsLocalRoom', 'lanchat store must let users continue a selected history as a single-player room');
assertIncludes(store, 'async function continueHistoryAsMultiRoom', 'lanchat store must let users continue a selected history as a multiplayer room');
assertIncludes(store, "state.workspaceMode = 'multiplayer_multi_agent'", 'continuing multiplayer history must keep the LAN collaboration workspace mode');
assertIncludes(store, 'restore_history: true', 'continuing a selected history must explicitly ask native to restore it into the active room');
assertIncludes(store, 'lanChatService.stopLocalRoom', 'single-player rooms must close without stopping collaboration networking');
assertIncludes(store, 'lanChatService.startRoom', 'multiplayer rooms must keep using the network room service path');

assertIncludes(roomPanel, 'member.member_id !== s.peerId', 'mention candidates must filter local member_id');
assertIncludes(roomPanel, 'targetKey: `agent:${a.agent_id || a.name}`', 'mention candidates must include agents with route targets');
if (roomPanel.includes(':peer-id="s.peerId"') || memberList.includes('a.owner === peerId')) {
  fail('MemberList must allow every AI assistant row to show its delete action');
}
assertIncludes(roomPanel, 'text-[15px]', 'RoomPanel must keep readable 15px chat/input text for CEF validation');
assertIncludes(roomPanel, 'leading-relaxed', 'RoomPanel message bubbles must keep readable line height');
assertIncludes(roomPanel, 'overflow-x-hidden', 'RoomPanel message list must not grow horizontally for long messages');
assertIncludes(roomPanel, 'lanchat-message-bubble', 'RoomPanel message bubbles must use bounded wrapping styles');
assertIncludes(roomPanel, 'overflow-wrap: anywhere', 'RoomPanel message bubbles must wrap long continuous text');
assertIncludes(roomPanel, 'w-36 border-l', 'RoomPanel member rail must be wide enough for readable names');
assertIncludes(roomPanel, 'isJoining', 'RoomPanel must render pending join state');
assertIncludes(roomPanel, ':disabled="isJoining"', 'RoomPanel must disable join controls while pending');
assertIncludes(roomPanel, 'JOIN_TIMEOUT', 'RoomPanel must display join timeout errors');
assertIncludes(roomPanel, 'HOST_UNREACHABLE', 'RoomPanel must display unreachable host errors');
assertIncludes(roomPanel, 'function gmProposalId', 'RoomPanel must detect GM proposal ids');
assertIncludes(roomPanel, "message?.message_kind === 'gm_proposal'", 'RoomPanel must prefer LANChat v2 gm_proposal messages');
assertIncludes(roomPanel, 'String(message.correlation_id)', 'RoomPanel must use correlation_id as GM proposal id');
assertIncludes(roomPanel, "s.role === 'host'", 'RoomPanel must only show GM confirmation controls to host');
assertIncludes(roomPanel, 'function sendGmDecision', 'RoomPanel must send structured GM decisions');
assertIncludes(roomPanel, 'item.requires_confirmation &&', 'RoomPanel must prioritize pending host confirmations over routine progress disclosures');
assertIncludes(roomPanel, '!lanchat.isProposalHandled(item.proposal_id)', 'RoomPanel must not prioritize handled confirmations over routine progress disclosures');
assertIncludes(roomPanel, 'lanchat.dismissDisclosureByProposal(proposalId)', 'RoomPanel must locally clear handled GM confirmation disclosures');
assertIncludes(roomPanel, 'function isGmProposalActionable', 'RoomPanel must centralize actionable GM proposal checks');
assertIncludes(roomPanel, '!lanchat.isProposalHandled', 'RoomPanel must hide handled GM proposal buttons');
assertIncludes(roomPanel, 'lanchat.markProposalHandled(proposalId)', 'RoomPanel must immediately mark clicked GM proposals handled');
assertIncludes(roomPanel, 'buildGmDecisionMessage', 'RoomPanel must use the shared structured GM decision builder');
assertIncludes(roomPanel, 'buildGmDisclosureActionMessage', 'RoomPanel must use the shared GM disclosure action builder');
assertIncludes(roomPanel, 'buildManualGmMessageOptions', 'RoomPanel must use the shared manual GM options builder');
assertIncludes(roomPanel, 'buildParticipantDisclosureDraft', 'RoomPanel must use the shared participant intervention draft builder');
assertIncludes(roomPanel, 'function sendDisclosureAction', 'RoomPanel must send clickable disclosure actions through the shared builder');
assertIncludes(roomPanel, 'function isDisclosureActionSendable', 'RoomPanel must only render supported disclosure actions as buttons');
assertIncludes(roomPanel, 'const options = buildManualGmMessageOptions(s.role)', 'manual @GM messages must derive host identity through the shared builder');
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
assertIncludes(disclosureStore, 'metadata.host_disclosure', 'disclosure store must support host-only fallback metadata');
assertIncludes(disclosureTest, "extractDisclosureFromMessage(message, 'room-a', 'host')", 'disclosure test must cover host-only fallback recovery');
assertIncludes(disclosureTest, "extractDisclosureFromMessage(message, 'room-a', 'guest')", 'disclosure test must cover participant-safe fallback view');
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
assertIncludes(store, 'lanChatService.sendMessage(trimmed, withStructuredRouteOptions(options))', 'lanchat store must pass structured message options through');
assertIncludes(bridge, '{ text, ...(options || {}) }', 'LANChat bridge must preserve structured sendMessage options');
assertIncludes(bridge, "Bridge.callCEF('LANChat', 'send_message'", 'LANChat bridge must route sendMessage through CEF LANChat module');
assertIncludes(bridge, "Bridge.callCEF('LANChat', 'get_history'", 'LANChat bridge must expose explicit persisted history reload');
assertIncludes(bridge, "Bridge.callCEF('LANChat', 'list_history_rooms'", 'LANChat bridge must expose persisted history room listing');
assertIncludes(bridge, "Bridge.callCEF('LANChat', 'load_history_room'", 'LANChat bridge must expose loading a selected persisted history room');
assertIncludes(roomPanel, 'resourceDiagnosisText', 'RoomPanel must render safe resource diagnosis text');
assertIncludes(roomPanel, 'function resourceDiagnosisLabel', 'RoomPanel must map scheduler diagnosis to user-facing text');
assertIncludes(roomPanel, '资源状态：生成已停止', 'RoomPanel must translate stopped scheduler diagnosis without exposing internal codes');
assertIncludes(roomPanel, '资源状态：队列拥堵', 'RoomPanel must translate saturated scheduler diagnosis without exposing internal codes');
assertIncludes(disclosureTest, 'diagnosis', 'disclosure test must cover safe scheduler diagnosis metadata');
assertIncludes(roomPanel, '房主端口', 'RoomPanel must not imply LANChat always uses default 8770');
assertIncludes(roomPanel, 'port: 27960', 'RoomPanel join form must default to the Network collaboration port');
assertIncludes(roomPanel, 'form.port || 27960', 'RoomPanel join/create calls must fall back to the Network collaboration port');
if (roomPanel.includes('port: 8770') || roomPanel.includes('form.port || 8770')) {
  fail('RoomPanel must not default LANChat room ports to legacy 8770');
}
assertIncludes(roomPanel, "roomMode.value = 'single'", 'RoomPanel must offer a single-player room mode');
assertIncludes(roomPanel, "roomMode.value = 'multi'", 'RoomPanel must offer a multiplayer room mode');
assertIncludes(roomPanel, 'mode: roomMode.value', 'RoomPanel must pass the selected room mode when creating a room');
assertIncludes(roomPanel, "v-if=\"roomMode === 'multi'\"", 'RoomPanel must only show room/password inputs for multiplayer room creation');
assertIncludes(roomPanel, 'function makeLocalRoomId', 'RoomPanel must auto-generate an internal local room id for single-player rooms');
assertIncludes(roomPanel, "return `single-${datePart}-${timePart}-${suffix}`", 'new single-player rooms must get a fresh local room id');
assertIncludes(roomPanel, 'Math.random().toString(36)', 'single-player room ids must avoid reusing the same id within the same second');
if (roomPanel.includes("return 'single-default'")) {
  fail('new single-player room creation must not reuse the legacy fixed room id');
}
assertIncludes(roomPanel, 'function isLocalSingleRoomId', 'RoomPanel must still recognize local single-player history room ids');
assertIncludes(roomPanel, "value === 'single-default'", 'RoomPanel must keep old single-player history readable');
assertIncludes(roomPanel, "roomMode.value === 'single'", 'RoomPanel create flow must branch before requiring a manually typed room id');
assertIncludes(roomPanel, "s.mode === 'single' ? '单人聊天室' : s.room", 'RoomPanel must not expose internal local room ids as the single-player room title');
assertIncludes(roomPanel, 'onMounted(refreshHistoryRooms)', 'RoomPanel must load persisted history list when the dock opens');
assertIncludes(roomPanel, '历史记录', 'RoomPanel must show persisted history before entering a room');
assertIncludes(roomPanel, 'loadHistoryRoom', 'RoomPanel must let users choose which persisted history to display');
assertIncludes(roomPanel, 'const visibleHistoryRooms = computed(() => (s.historyRooms || []).slice(0, 2))', 'RoomPanel primary lobby must show at most two history rooms');
assertIncludes(roomPanel, 'const hasMoreHistoryRooms = computed(() => (s.historyRooms || []).length > 2)', 'RoomPanel must detect when more history rooms are available');
assertIncludes(roomPanel, 'mt-auto space-y-2 border-t border-gray-700 pt-3', 'RoomPanel primary history section must be pinned to the bottom of the lobby');
assertIncludes(roomPanel, 'v-if="hasMoreHistoryRooms"', 'RoomPanel must show the more history button only when needed');
assertIncludes(roomPanel, 'showAllHistory = true', 'RoomPanel must open a secondary all-history page');
assertIncludes(roomPanel, '全部历史记录', 'RoomPanel must label the secondary all-history page');
assertIncludes(roomPanel, 'v-for="room in visibleHistoryRooms"', 'RoomPanel primary history list must render the capped history collection');
assertIncludes(roomPanel, 'v-for="room in s.historyRooms"', 'RoomPanel secondary history page must render all history rooms');
assertIncludes(roomPanel, 'continueHistoryAsSingle', 'RoomPanel must let users continue a selected history as a single-player room');
assertIncludes(roomPanel, 'continueHistoryAsMulti', 'RoomPanel must let users continue multiplayer history as a LAN collaboration room');
assertIncludes(roomPanel, 'isLocalSingleRoomId(roomId)', 'RoomPanel must branch history restore by single-player room id');
assertIncludes(roomPanel, "lanchat.setWorkspaceMode('multiplayer_multi_agent')", 'RoomPanel must switch multiplayer history into LAN collaboration mode');
assertIncludes(roomPanel, '@dblclick="continueHistoryFromList(room)"', 'RoomPanel history lists must enter a history room on double click');
const historyDoubleClickCount = (roomPanel.match(/@dblclick="continueHistoryFromList\(room\)"/g) || []).length;
if (historyDoubleClickCount < 2) {
  fail('RoomPanel primary and all-history lists must both enter a history room on double click');
}
if (roomPanel.includes('作为单人聊天室继续')) {
  fail('RoomPanel history lists must not show the old continue-history detail panel');
}
assertIncludes(roomPanel, '`多人聊天室-${roomId}`', 'RoomPanel must label multiplayer history rooms with a multiplayer prefix');
if (roomPanel.includes("if (s.selectedHistoryRoom) return '继续所选历史'")) {
  fail('RoomPanel create button must not change into a continue-history action');
}
assertIncludes(cefBridge, 'const bool restore_history = payload_arg.value("restore_history", false)', 'CEF start_room must accept explicit history restore requests');
assertIncludes(cefBridge, 'restored_history = sys->lanchat_restore_history_room(history_room)', 'CEF start_room must restore selected multiplayer history into NetworkSystem');
assertIncludes(roomPanel, "s.mode === 'multi'", 'RoomPanel must only show host IP/port for multiplayer rooms');
assertIncludes(roomPanel, "label: '自己设计'", 'RoomPanel lobby must expose the solo design entry');
assertIncludes(roomPanel, "label: '多人共创'", 'RoomPanel lobby must expose the multiplayer co-creation entry');
assertIncludes(roomPanel, 'const defaultExpertRoleKeys = roleTemplates.map((role) => role.key)', 'RoomPanel must default-enable every built-in expert role');
assertIncludes(roomPanel, 'await addDefaultExpertGroup()', 'RoomPanel must add built-in experts when entering a room');
assertIncludes(roomPanel, 'networkService.requestSceneSnapshot(sceneName)', 'RoomPanel multiplayer join must request a scene snapshot for model transfer');
assertIncludes(roomPanel, 'function currentModelTransferSceneName', 'RoomPanel multiplayer join must resolve the current scene before requesting model transfer');
assertIncludes(roomPanel, "s.role !== 'guest' || s.mode !== 'multi'", 'RoomPanel model transfer request must only run for multiplayer guests');
assertIncludes(roomPanel, "s.connection !== 'connected'", 'RoomPanel model transfer request must wait until LANChat join is connected');
assertIncludes(roomPanel, 'v-if="s.mode === \'multi\'"', 'RoomPanel must only show connection status pill for multiplayer rooms');
assertIncludes(roomPanel, "s.mode === 'single' ? '退出聊天'", 'RoomPanel single-player close button must read as exiting chat');
if (roomPanel.includes("key: 'solo_multi_agent'")) {
  fail('RoomPanel first-level lobby must not expose a separate all-AI entry');
}

assertIncludes(memberList, '<div class="text-sm">', 'MemberList must keep readable CEF font size');
assertIncludes(roomPanel, '@add-agent="showAddAgent = true"', 'RoomPanel must move add-agent entry into the member list');
assertIncludes(memberList, "defineEmits(['remove-agent', 'add-agent'])", 'MemberList must expose add-agent from the AI list');
assertIncludes(memberList, 'group-hover:opacity-100', 'MemberList agent remove button must appear only on hover');
assertIncludes(memberList, '添加助手', 'MemberList must render add assistant as the final AI list action');
if (roomPanel.includes('v-for="action in draftActions"') || roomPanel.includes('selectedDraftAction === action.key')) {
  fail('RoomPanel must not render the draft action button row above the target/agent row');
}
if (roomPanel.includes('v-for="target in targetQuickOptions"') || roomPanel.includes('targetQuickOptions')) {
  fail('RoomPanel must not render the target quick button row above the chat input');
}
assertIncludes(roomPanel, 'rows="2"', 'RoomPanel chat input must allow two visible lines');
assertIncludes(roomPanel, 'const DRAFT_MIN_ROWS = 2', 'RoomPanel chat input must default to two rows');
assertIncludes(roomPanel, 'const DRAFT_MAX_ROWS = 4', 'RoomPanel chat input must grow only up to four rows before scrolling');
assertIncludes(roomPanel, 'function resizeDraftInput', 'RoomPanel chat input must resize with draft content');
assertIncludes(roomPanel, "el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'", 'RoomPanel chat input must scroll only after four rows');
assertIncludes(roomPanel, 'class="self-stretch px-4 rounded bg-[#84A65B]', 'RoomPanel send button must stretch with the input height');
assertIncludes(roomPanel, 'toggleMentionPicker', 'RoomPanel input plus button must open the shared mention picker');
assertIncludes(roomPanel, 'ref="mentionRoot"', 'RoomPanel mention picker must know its root for outside-click close');
assertIncludes(roomPanel, "document.addEventListener('pointerdown', onDocumentPointerDown)", 'RoomPanel mention picker must close on outside pointer down');
assertIncludes(roomPanel, "document.removeEventListener('pointerdown', onDocumentPointerDown)", 'RoomPanel mention picker must clean up outside-click listener');
assertIncludes(roomPanel, 'max-h-64', 'RoomPanel mention picker must be taller than the old compact list');
assertIncludes(roomPanel, 'lanchat-scrollbar', 'RoomPanel mention picker must use the themed scrollbar');
assertIncludes(roomPanel, '全部AI助手', 'RoomPanel must rename the group target to all AI assistants');
assertIncludes(roomPanel, "return '输入@来指定AI助手~'", 'RoomPanel chat placeholder must guide users to @ AI assistants');
if (roomPanel.includes('pb-8 pl-10')) {
  fail('RoomPanel plus button must overlay the textarea instead of reserving a left column');
}
if (roomPanel.includes('专家组') || roomPanel.includes('当前场景') || roomPanel.includes('输入要问的问题')) {
  fail('RoomPanel must not show the old expert group, current scene, or question placeholder text');
}
assertIncludes(roomPanel, "selectedTargetKey = ref('')", 'RoomPanel default chat target must be empty direct send');
assertIncludes(roomPanel, 'syncSelectedTargetFromDraft(text)', 'RoomPanel must derive the structured target from the current draft text');
assertIncludes(roomPanel, 'targetKeyFromMentionText', 'RoomPanel must clear stale targets when @ text is removed');
assertIncludes(roomPanel, 'displayMessages', 'RoomPanel must render pending replies inside the message flow');
assertIncludes(roomPanel, "kind: 'pending_reply'", 'RoomPanel pending reply must be a virtual message entry');
assertIncludes(roomPanel, 'pendingReplyMatchesMessage', 'RoomPanel pending reply must clear only on the matching AI reply');
assertIncludes(roomPanel, "if (!target || !['agent', 'gm'].includes(target.scope)) return null", 'RoomPanel must not show thinking placeholder when no single AI helper is targeted');
assertIncludes(roomPanel, 'options.correlation_id = pending.correlationId', 'RoomPanel targeted messages must carry a correlation id for pending reply matching');
if (roomPanel.includes('showAiReplySpinner') || roomPanel.includes('pendingReplySinceMs')) {
  fail('RoomPanel must not use the old global AI reply spinner state');
}
if (roomPanel.includes('＋助手')) {
  fail('RoomPanel room header must not render the old add assistant button');
}
if (
  roomPanel.includes('快速模板') ||
  roomPanel.includes('夜市验证组') ||
  roomPanel.includes('selectRoleTemplate') ||
  roomPanel.includes('addRoleTemplateBundle')
) {
  fail('RoomPanel add assistant dialog must only keep custom name/persona inputs and actions');
}
assertIncludes(roomPanel, 'function onAddAgentBackdropPointerDown', 'RoomPanel add assistant backdrop must track pointer starts');
assertIncludes(roomPanel, 'function onAddAgentBackdropPointerUp', 'RoomPanel add assistant backdrop must not close after textarea resize drags');
if (roomPanel.includes('@click.self="showAddAgent = false"')) {
  fail('RoomPanel add assistant dialog must not close from click.self because textarea resize drags can end on the backdrop');
}

assertIncludes(networkHeader, 'session_port() const', 'NetworkSystem must expose the active ENet listen port');
assertIncludes(networkHeader, 'lanchat_start_local_room', 'NetworkSystem must expose a local LANChat room path that does not start collaboration networking');
assertIncludes(networkHeader, 'lanchat_stop_local_room', 'NetworkSystem must expose a local room close path that does not stop collaboration networking');
assertIncludes(networkHeader, 'lanchat_restore_history_room', 'NetworkSystem must expose explicit selected-history restore for local continuation');
assertIncludes(networkSystem, 'if (impl_->session_role != SessionRole::Host) return;', 'clients must not process LANChat join packets');
assertIncludes(networkSystem, 'bool NetworkSystem::lanchat_start_local_room', 'NetworkSystem must implement local LANChat rooms');
assertIncludes(networkSystem, 'void NetworkSystem::lanchat_stop_local_room', 'NetworkSystem must implement local LANChat room close');
const localRoomStartForHistory = networkSystem.indexOf('bool NetworkSystem::lanchat_start_local_room');
const multiRoomStartForHistory = networkSystem.indexOf('bool NetworkSystem::lanchat_start_room');
const stopLocalForHistory = networkSystem.indexOf('void NetworkSystem::lanchat_stop_local_room');
if (localRoomStartForHistory < 0 || multiRoomStartForHistory < 0 || stopLocalForHistory < 0) {
  fail('NetworkSystem must expose local and multiplayer LANChat room paths');
}
const startRoomBodiesForHistory = networkSystem.slice(localRoomStartForHistory, stopLocalForHistory);
if (startRoomBodiesForHistory.includes('restore_lanchat_history(room_id)')) {
  fail('opening a LANChat room must not automatically restore persisted history');
}
assertIncludes(networkSystem, 'persist_lanchat_message(result.message)', 'NetworkSystem must persist accepted LANChat messages');
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
assertIncludes(cefBridge, 'func == "start_local_room"', 'LANChat bridge must expose start_local_room for single-player rooms');
assertIncludes(cefBridge, 'func == "stop_local_room"', 'LANChat bridge must expose stop_local_room for single-player rooms');
assertIncludes(cefBridge, 'func == "get_history"', 'LANChat bridge must expose get_history for explicit history reload');
assertIncludes(cefBridge, 'func == "list_history_rooms"', 'LANChat bridge must expose persisted history room listing');
assertIncludes(cefBridge, 'func == "load_history_room"', 'LANChat bridge must expose loading selected persisted history rooms');
assertIncludes(cefBridge, 'sys->lanchat_load_history_agents(room)', 'LANChat load_history_room must return the persisted agent roster');
assertIncludes(cefBridge, '{"persona", agent.persona}', 'LANChat agent JSON must include persona for restored agents');
assertIncludes(cefBridge, 'payload_arg.value("restore_history", false)', 'LANChat start_local_room must require explicit restore_history before applying persisted history');
assertIncludes(cefBridge, 'sys->lanchat_restore_history_room', 'LANChat start_local_room must restore selected history only when requested');
assertIncludes(cefBridge, 'payload_arg.value("port", 27960)', 'LANChat bridge must default room ports to the Network collaboration port');
assertIncludes(cefBridge, 'sys->session_port() != 0 ? sys->session_port() : 27960', 'LANChat get_local_ip must return the Network collaboration port fallback');
if (cefBridge.includes('data["port"] = 8770;')) {
  fail('LANChat bridge must not hard-code get_local_ip port to 8770');
}
if (cefBridge.includes('payload_arg.value("port", 8770)') || cefBridge.includes(': 8770')) {
  fail('LANChat bridge must not default room ports to legacy 8770');
}
const localRoomStart = networkSystem.indexOf('bool NetworkSystem::lanchat_start_local_room');
const multiplayerRoomStart = networkSystem.indexOf('bool NetworkSystem::lanchat_start_room');
if (localRoomStart < 0 || multiplayerRoomStart < 0) {
  fail('NetworkSystem must implement both local and multiplayer LANChat room start paths');
}
const localRoomBody = networkSystem.slice(localRoomStart, multiplayerRoomStart);
if (localRoomBody.includes('start_session(')) {
  fail('Local LANChat rooms must not start NetworkSystem collaboration sessions');
}
const startRoomBranch = cefBridge.slice(
  cefBridge.indexOf('if (func == "start_room")'),
  cefBridge.indexOf('if (func == "stop_room")'),
);
if (startRoomBranch.includes('sys->lanchat_load_history_room')) {
  fail('LANChat start_room/start_local_room responses must not load persisted history implicitly');
}
const localStopStart = networkSystem.indexOf('void NetworkSystem::lanchat_stop_local_room');
const leaveRoomStart = networkSystem.indexOf('void NetworkSystem::lanchat_leave_room');
if (localStopStart < 0 || leaveRoomStart < 0) {
  fail('NetworkSystem must implement separate local and network LANChat close paths');
}
const localStopBody = networkSystem.slice(localStopStart, leaveRoomStart);
if (localStopBody.includes('stop_session(') || localStopBody.includes('build_chat_leave(')) {
  fail('Local LANChat close must not stop collaboration sessions or broadcast leave packets');
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
