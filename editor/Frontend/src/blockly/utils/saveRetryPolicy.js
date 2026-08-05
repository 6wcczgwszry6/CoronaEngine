function normalizeProjectPath(value) {
  return String(value || '')
    .trim()
    .replace(/\\/g, '/')
    .replace(/\/+$/, '')
    .toLocaleLowerCase('en-US');
}

export function nextSaveAction({ succeeded, saveQueued, graphDirty }) {
  return succeeded && (saveQueued || graphDirty) ? 'resave' : 'idle';
}

export function shouldResumeBlockedSave({ dirty, blockedProjectPath, eventProjectPath }) {
  if (!dirty) return false;
  const blocked = normalizeProjectPath(blockedProjectPath);
  const current = normalizeProjectPath(eventProjectPath);
  return Boolean(blocked && current && blocked === current);
}
