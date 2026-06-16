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
const roomPanel = read('src/views/sidebar/lanchat/RoomPanel.vue');
const memberList = read('src/views/sidebar/lanchat/MemberList.vue');

assertIncludes(store, 'peerId:', 'lanchat store must track local peerId');
assertIncludes(store, 'memberDetails:', 'lanchat store must track memberDetails');
assertIncludes(store, 'normalizeMembers', 'lanchat store must normalize member snapshots');
assertIncludes(store, 'state.agents = res.agents || []', 'joinRoom must initialize agent roster');
assertIncludes(store, 'event.member_details', 'member_update must consume member_details');

assertIncludes(roomPanel, 'member.member_id !== s.peerId', 'mention candidates must filter local member_id');
assertIncludes(roomPanel, 'a.name, isAgent: true', 'mention candidates must include agents');
assertIncludes(roomPanel, ':peer-id="s.peerId"', 'MemberList must receive stable peerId');

assertIncludes(memberList, 'peerId', 'MemberList must accept peerId prop');
assertIncludes(memberList, 'a.owner === peerId', 'agent remove visibility must compare owner to peerId');

console.log('LANChat roster constraints OK');
