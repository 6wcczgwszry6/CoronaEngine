/**
 * The map every story world stands on (山门神殿).
 *
 * `game/data/prophet.json`'s `map` block is the authoritative content — designers edit that
 * file — and this module is the runtime projection of it, kept honest by
 * `game/tests/test_story_assets.py`, which diffs the two field by field and re-derives the
 * two measurements from the shipped GLB.
 *
 * The map arrives exactly the way the prophet's cube does: the page asks the engine to
 * create one actor for it when it enters the world. Nothing writes `scene.ini` for it, so
 * a world that already exists — including the small world, which is a copy of the main
 * scene — gets the map on its next entry just like a freshly created one. That is
 * deliberate: an earlier design seeded the actor from native world-creation code
 * (`seed_story_world_map`), which only ever affected new worlds.
 *
 * Everything geometric here is a pure function, so the placement can be tested without an
 * engine. The map is deliberately NOT a `STORY_CHARACTERS` entry: that list is asserted to
 * be exactly the four inhabitants, and the map is static scenery rather than a character.
 */

import { sceneSnapshot } from './storyCharacters.mjs';

/** Stable identity, so a second entry adopts the world's map instead of appending one. */
export const MAP_GUID = 'corona.story.world-map.v1';
export const MAP_MODEL_REF = 'corona.story.world-map.v1';

const COORD_LIMIT = 1e6;
const finiteNumber = value => typeof value === 'number' && Number.isFinite(value);
const positiveNumber = value => finiteNumber(value) && value > 0 && value <= COORD_LIMIT;

/** Mirrors the `map` block of game/data/prophet.json, field for field. */
export const MAP_PLACEMENT = Object.freeze({
  asset: 'scene/01_山门神殿_优化版.glb',
  guid: MAP_GUID,
  modelRef: MAP_MODEL_REF,
  scale: 420.0007,
  courtyardY: 0.8615,
});

/** Strict validation, so a bad edit in the JSON table fails loudly instead of drifting. */
export function validateMapPlacement(raw) {
  const source = raw && typeof raw === 'object' ? raw : {};
  if (typeof source.asset !== 'string' || !source.asset.trim()) throw new Error('地图资源路径无效');
  if (typeof source.guid !== 'string' || !source.guid.trim()) throw new Error('地图标识无效');
  if (typeof source.modelRef !== 'string' || !source.modelRef.trim()) throw new Error('地图版本标记无效');
  if (!positiveNumber(source.scale)) throw new Error('地图参数无效：scale');
  // The courtyard may sit exactly on the model's own y = 0, so 0 is legal here; a negative
  // height or one at/above the model's AABB centre would mean the map is not a ground.
  if (!finiteNumber(source.courtyardY) || source.courtyardY < 0 || source.courtyardY > COORD_LIMIT) {
    throw new Error('地图参数无效：courtyardY');
  }
  if (source.courtyardY >= source.scale / 2) throw new Error('地图庭院高度超出模型高度');
  return Object.freeze({
    asset: source.asset.trim(), guid: source.guid.trim(), modelRef: source.modelRef.trim(),
    scale: source.scale, courtyardY: source.courtyardY,
  });
}

validateMapPlacement(MAP_PLACEMENT);

/**
 * The map's actor transform, derived from the two measurements.
 *
 * The engine normalises every static model into a unit cube: the model's world AABB centre
 * is moved to the origin and the largest axis is scaled to 1
 * (`scale_factor = 1 / max_axis` in
 * `modules/corona_resource/src/resource/types/parse_common.h`, applied at
 * `parse_assimp.h`). An actor's `position` and `scale` are then applied to that normalised
 * geometry (`world_aabb_from_local_bounds` in `src/systems/mechanics/mechanics_system.cpp`),
 * and a model point at height `y` lands at:
 *
 *   world_y = position.y + (y - centre_y) * scale_factor * scale
 *
 * with `scale_factor * scale = 1` when `scale` is the model's real largest axis. So:
 *
 *   - `scale = scale` puts the map back at its real size in metres;
 *   - the courtyard (`courtyardY`, measured 0.8615 m) sits `scale / 2 - courtyardY` metres
 *     below the AABB centre — 209.14 m below for this 79.2 m-tall map whose centre is
 *     ~38.6 m above the courtyard. Because the engine works in the normalised frame, that
 *     becomes `(scale / 2 - courtyardY) / scale` — about 0.002, not 209. Writing the metre
 *     value here would lift the map 209 metres into the air.
 *   - `position.y = (scale / 2 - courtyardY) / scale` therefore puts the courtyard exactly
 *     on y = 0, which is the engine floor and the line
 *     `storyCharacters.characterTransform` puts character feet on.
 *
 * Returns a fresh object every call: the engine call and its read-back confirmation must
 * never share a mutable value.
 */
export function mapOriginTransform(placement = MAP_PLACEMENT) {
  return {
    position: [0, (placement.scale / 2 - placement.courtyardY) * (1 / placement.scale), 0],
    rotation: [0, 0, 0],
    scale: [placement.scale, placement.scale, placement.scale],
  };
}

/** True for the game-owned map only, so scenery and user-authored models are never touched. */
export function isMapActor(actor) {
  return actor?.actor_guid === MAP_PLACEMENT.guid || actor?.model_ref === MAP_PLACEMENT.modelRef;
}

const sameVector = (a, b) => Array.isArray(a) && a.length === b.length
  && a.every((value, index) => Number.isFinite(value) && Math.abs(value - b[index]) < 1e-4);

/**
 * A map the world already carries and this version owns: nothing may be written for it.
 * An actor without this version's marker (an older entry, or a world made by the removed
 * native seeder) is not "ready" and is repaired in place instead.
 */
export function isMapReady(actor, placement = MAP_PLACEMENT) {
  return Number(actor?.handle) > 0 && actor?.load_status === 'loaded'
    && actor?.model_ref === placement.modelRef
    && sameVector(actor?.geometry?.scale, mapOriginTransform(placement).scale);
}

/** `static` is what builds the collision mesh; anything else can be walked through. */
export const isMapStatic = actor => actor?.mechanics?.body_type === 'static';

const unwrap = value => value?.data ?? value;

/** The same acknowledgement rule the other story actors use before the page trusts a reply. */
async function call(operation, invoke) {
  const data = unwrap(await invoke());
  if (!data || data.ok === false || !['success', 'loaded'].includes(data.status)) {
    throw new Error(`${operation}：${data?.message || data?.diagnostics?.[0]?.message || '引擎未确认成功'}`);
  }
  return data;
}

/**
 * Bring the world in line with the map table: create it when the world does not have it,
 * repair the transform in place when it carries an older one, switch it to a static body
 * when it is not walkable yet, and otherwise touch nothing at all.
 *
 * `static`, never a pass-through body: a static model gets a real triangle mesh and triangle
 * octree built over it (`src/systems/mechanics/mechanics_system.cpp`), which is what lets the
 * characters and monsters walk and collide on the surface. A pass-through body means falling
 * through, and a map you fall through is worse than no map.
 *
 * Idempotent: the world's own map is identified by its GUID and version marker, so a second
 * entry neither appends a second actor nor reshuffles the one that is already placed.
 */
export async function ensureStoryMap({ api, sceneId, frontendUrl, resolveAsset = null,
  placement = MAP_PLACEMENT, wait = ms => new Promise(resolve => setTimeout(resolve, ms)),
  confirmAttempts = 30 }) {
  const actors = sceneSnapshot(await api.scene.getSnapshot(sceneId))?.actors;
  let map = (Array.isArray(actors) ? actors : []).find(isMapActor) || null;

  if (!map) {
    const route = typeof resolveAsset === 'function' ? resolveAsset(frontendUrl, placement.asset) : null;
    if (!route) throw new Error('地图资源路径不可用');
    const created = await call('创建地图', () => api.sceneTools.createActor(sceneId, route, 'model', {
      name: '剧情世界地图', actor_guid: placement.guid, semantic_role: 'world-map',
      entity_id: 'story.world.map', entity_type: 'story_scenery',
      model_ref: placement.modelRef, follow_camera: false,
      // body_type, not physics_enabled: `create_actor` treats a missing body type as a
      // pass-through body, and one is walked straight through.
      body_type: 'static',
      ...mapOriginTransform(placement),
    }));
    map = created.actor;
  } else if (!isMapReady(map, placement)) {
    // The world already has this actor (an existing world, or one whose first creation was
    // interrupted): the same GUID plus `skip_if_exists` makes the engine move it instead of
    // appending a second map over the top of the first.
    const route = map.route || (typeof resolveAsset === 'function'
      ? resolveAsset(frontendUrl, placement.asset) : null);
    if (!route) throw new Error('地图资源路径不可用');
    const updated = await call('校正地图摆位', () => api.sceneTools.createActor(sceneId, route, 'model', {
      name: '剧情世界地图', actor_guid: placement.guid, semantic_role: 'world-map',
      entity_id: 'story.world.map', entity_type: 'story_scenery',
      model_ref: placement.modelRef, follow_camera: false, body_type: 'static',
      skip_if_exists: true, update_if_exists: true,
      ...mapOriginTransform(placement),
    }));
    map = updated.actor;
  }

  if (!map) throw new Error('引擎未返回地图');
  if (!isMapStatic(map)) {
    // A record restored from an older world can still be phantom; the map must be solid.
    const solidified = await call('设置地图碰撞', () => api.sceneTools.setActorPhysics(sceneId,
      placement.guid, { body_type: 'static' }));
    map = solidified.actor;
    if (!isMapStatic(map)) throw new Error('地图未被引擎确认为可站立（static）');
  }
  // Confirm on read-back that the engine really accepted the map, instead of trusting the
  // create call's reply: a world whose map never landed must say so rather than drop the
  // player onto nothing. The handle is acknowledged before the asynchronous import fills
  // the record, so a fresh actor needs a bounded wait rather than one read.
  for (let attempt = 0; ; attempt++) {
    const confirmed = sceneSnapshot(await api.scene.getSnapshot(sceneId))?.actors
      ?.find(item => item.actor_guid === placement.guid);
    if (isMapReady(confirmed, placement)) return confirmed;
    if (attempt >= confirmAttempts - 1) throw new Error('等待地图就位超时，请重试进入世界');
    await wait(200);
  }
}
