export function normalizeActorContextName(value) {
  const text = String(value ?? '').trim();
  try { return text.normalize('NFKC'); } catch (_) { return text; }
}

export function actorContextNameKey(value) {
  return normalizeActorContextName(value).toLocaleLowerCase('en-US');
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function compactVector3(value) {
  if (Array.isArray(value)) {
    const result = value.slice(0, 3).map(finiteNumber);
    return result.length === 3 && result.every((item) => item !== null) ? result : null;
  }
  if (value && typeof value === 'object') {
    const x = finiteNumber(value.x ?? value.X ?? value[0]);
    const y = finiteNumber(value.y ?? value.Y ?? value[1]);
    const z = finiteNumber(value.z ?? value.Z ?? value[2]);
    return [x, y, z].every((item) => item !== null) ? { x, y, z } : null;
  }
  return null;
}

function compactTransform(item) {
  const source = item?.geometry && typeof item.geometry === 'object'
    ? item.geometry
    : item?.transform && typeof item.transform === 'object'
      ? item.transform
      : {};
  const transform = {};
  const position = compactVector3(source.position ?? item?.position);
  const rotation = compactVector3(source.rotation ?? item?.rotation);
  const scale = compactVector3(source.scale ?? item?.scale);
  if (position) transform.position = position;
  if (rotation) transform.rotation = rotation;
  if (scale) transform.scale = scale;
  return Object.keys(transform).length ? transform : null;
}

export function actorAliasesFromSceneItem(item = {}) {
  const aliases = [];
  ['alias', 'displayName', 'display_name', 'nativeName', 'native_name', 'label'].forEach((field) => {
    const value = normalizeActorContextName(item?.[field]);
    if (value) aliases.push(value);
  });
  ['aliases', 'displayNames', 'display_names', 'names'].forEach((field) => {
    let values = item?.[field];
    if (values && typeof values === 'object' && !Array.isArray(values)) values = Object.values(values);
    if (!Array.isArray(values)) values = [values];
    values.forEach((value) => {
      const alias = normalizeActorContextName(value);
      if (alias) aliases.push(alias);
    });
  });
  return [...new Set(aliases)];
}

export function actorRecordFromSceneItem(item = {}) {
  if (!item || typeof item !== 'object') return null;
  const name = normalizeActorContextName(item.name ?? item.actor_name ?? item.actorName);
  if (!name) return null;
  const type = String(item.type ?? item.actor_type ?? item.actorType ?? 'actor').trim() || 'actor';
  if (['scene', 'folder', 'root'].includes(type.toLocaleLowerCase('en-US'))) return null;

  const actor = {
    name,
    type,
    tags: Array.isArray(item.tags)
      ? [...new Set(item.tags.map(normalizeActorContextName).filter(Boolean))]
      : [],
    aliases: actorAliasesFromSceneItem(item)
      .filter((alias) => actorContextNameKey(alias) !== actorContextNameKey(name)),
  };
  const semanticRole = normalizeActorContextName(
    item.semanticRole ?? item.semantic_role ?? item.entity_type,
  );
  const transform = compactTransform(item);
  const size = compactVector3(item.size);
  const collision = item.collision ?? item.collisionShape ?? item.collision_shape;
  const physicsEnabled = item.physicsEnabled
    ?? item.physics_enabled
    ?? item.mechanics?.physicsEnabled
    ?? item.mechanics?.physics_enabled;

  if (semanticRole) actor.semanticRole = semanticRole;
  if (transform) actor.transform = transform;
  if (size) actor.size = size;
  if (typeof collision === 'string' || (collision && typeof collision === 'object')) {
    actor.collision = collision;
  }
  if (typeof physicsEnabled === 'boolean') actor.physicsEnabled = physicsEnabled;
  return actor;
}

export function actorRecordsFromSceneTree(value) {
  const actors = [];
  const visited = new WeakSet();

  const visit = (item) => {
    if (Array.isArray(item)) {
      item.forEach(visit);
      return;
    }
    if (!item || typeof item !== 'object' || visited.has(item)) return;
    visited.add(item);

    const actor = actorRecordFromSceneItem(item);
    if (actor) actors.push(actor);

    ['actors', 'data', 'result', 'children', 'items'].forEach((field) => {
      const child = item[field];
      if (Array.isArray(child) || (child && typeof child === 'object')) visit(child);
    });
  };

  visit(value);
  return actors;
}

export function actorContextRevision(sceneName, actors) {
  return JSON.stringify({
    sceneName: normalizeActorContextName(sceneName),
    actors: (Array.isArray(actors) ? actors : []).map((actor) => ({
      name: actorContextNameKey(actor.name),
      type: String(actor.type || '').toLocaleLowerCase('en-US'),
      tags: (actor.tags || []).map(actorContextNameKey).sort(),
      aliases: (actor.aliases || []).map(actorContextNameKey).sort(),
      semanticRole: normalizeActorContextName(actor.semanticRole),
      transform: actor.transform || null,
      size: actor.size || null,
      collision: actor.collision ?? null,
      physicsEnabled: actor.physicsEnabled ?? null,
    })),
  });
}
