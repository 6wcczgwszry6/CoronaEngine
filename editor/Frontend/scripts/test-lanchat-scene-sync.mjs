import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const roomPanelPath = resolve(here, '../src/views/sidebar/lanchat/RoomPanel.vue');
const source = readFileSync(roomPanelPath, 'utf8');

const requiredTokens = [
  'sceneService.listActorTree',
  'sceneService.createActor',
  'skip_if_exists: true',
  'update_if_exists:',
  'pollPendingActorStateUpdate',
  'pollPendingActorTransform',
  'remoteAppliedActorVersions',
  'AI_SCENE_FRAMEWORK_SYNC_NAMES',
  "'__room_box'",
  "'__room_terrain'",
  "'__terrain_boundary'",
];

for (const token of requiredTokens) {
  assert.ok(source.includes(token), `RoomPanel scene sync is missing: ${token}`);
}

const forbiddenPlaceholders = [
  'SceneTools native snapshot interface is not connected',
  'native SceneTools apply is not connected',
  'native SceneTools create is not connected',
];

for (const placeholder of forbiddenPlaceholders) {
  assert.ok(!source.includes(placeholder), `RoomPanel still contains placeholder: ${placeholder}`);
}

assert.match(
  source,
  /version < appliedVersion \|\| \(version === appliedVersion && !update\)/,
  'stale remote actor versions must not overwrite newer state',
);

console.log('LANChat scene sync static checks passed');
