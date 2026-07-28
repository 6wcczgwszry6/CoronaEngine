const normalizeRect = (rect) => {
  if (!rect) return null;
  const left = Number(rect.left || 0);
  const top = Number(rect.top || 0);
  const width = Number(rect.width || 0);
  const height = Number(rect.height || 0);
  if (![left, top, width, height].every(Number.isFinite) || width <= 0 || height <= 0) {
    return null;
  }
  return { left, top, width, height };
};

const modifierMask = (event) =>
  (event?.shiftKey ? 1 : 0)
  | (event?.ctrlKey ? 2 : 0)
  | (event?.altKey ? 4 : 0)
  | (event?.metaKey ? 8 : 0);

export const resolveViewportGizmoTarget = ({
  sceneId = '',
  selection = {},
  pickResult = null,
  actorIndex = new Map(),
} = {}) => {
  const actorName = String(selection.actor || selection.actor_name || '').trim();
  const actorType = String(selection.actor_type || selection.type || '').trim();
  const selectedScene = String(selection.scene || selection.scene_id || sceneId).trim();
  if (!actorName || actorType === 'scene' || selectedScene !== String(sceneId || '').trim()) {
    return null;
  }

  const pickedActor = pickResult?.actor;
  const pickedHandle = Number(pickedActor?.handle || 0);
  if (
    Number.isFinite(pickedHandle)
    && pickedHandle > 0
    && String(pickedActor?.name || '') === actorName
  ) {
    return {
      handle: pickedHandle,
      name: actorName,
      type: String(pickedActor?.type || actorType || 'actor'),
    };
  }

  for (const [handleValue, actor] of actorIndex || []) {
    const handle = Number(handleValue || 0);
    if (Number.isFinite(handle) && handle > 0 && actor?.name === actorName) {
      return {
        handle,
        name: actorName,
        type: String(actor.type || actorType || 'actor'),
      };
    }
  }
  return null;
};

export const createViewportGizmoController = ({
  getBridge,
  getCameraBinding,
  getHitRect,
  getRenderRect,
  onDragEnd,
  onDragCancel,
  makeRequestId,
  scheduleFrame,
} = {}) => {
  let sequence = 0;
  let dragging = false;
  let activeAxis = 'none';
  let lastPointer = { clientX: 0, clientY: 0, button: 0, buttons: 0 };
  const pending = new Set();
  const completedEnds = new Set();
  let moveScheduled = false;
  let queuedMove = null;
  const nextRequestId =
    makeRequestId || (() => `gizmo-${Date.now()}-${++sequence}`);
  const enqueueFrame =
    scheduleFrame
    || ((callback) =>
      typeof window !== 'undefined' && window.requestAnimationFrame
        ? window.requestAnimationFrame(callback)
        : callback());

  const binding = () => getCameraBinding?.() || {};

  const controller = {
    setTarget(actor = {}) {
      const bridge = getBridge?.();
      const current = binding();
      const cameraHandle = Number(current.cameraHandle || 0);
      const actorHandle = Number(actor.handle || 0);
      if (!bridge?.setViewportGizmoTarget || cameraHandle <= 0 || actorHandle <= 0) {
        return false;
      }
      bridge.setViewportGizmoTarget(
        cameraHandle,
        String(current.sceneId || ''),
        String(actor.name || ''),
        actorHandle,
      );
      return true;
    },

    clearTarget() {
      const bridge = getBridge?.();
      const current = binding();
      const cameraHandle = Number(current.cameraHandle || 0);
      if (!bridge?.setViewportGizmoTarget || cameraHandle <= 0) return false;
      bridge.setViewportGizmoTarget(
        cameraHandle,
        String(current.sceneId || ''),
        '',
        0,
      );
      dragging = false;
      activeAxis = 'none';
      queuedMove = null;
      return true;
    },

    pointer(event = {}, eventType = event.type || 'pointermove') {
      let nativeEventType = String(eventType);
      if (nativeEventType === 'pointermove' && dragging) {
        queuedMove = {
          event: {
            clientX: event.clientX,
            clientY: event.clientY,
            button: event.button,
            buttons: event.buttons,
            shiftKey: event.shiftKey,
            ctrlKey: event.ctrlKey,
            altKey: event.altKey,
            metaKey: event.metaKey,
          },
        };
        if (!moveScheduled) {
          moveScheduled = true;
          enqueueFrame(() => {
            moveScheduled = false;
            const queued = queuedMove;
            queuedMove = null;
            if (queued) controller.pointer(queued.event, 'gizmo-pointermove-immediate');
          });
        }
        return 'queued';
      }
      if ((nativeEventType === 'pointerup' || nativeEventType === 'pointercancel') && queuedMove) {
        const queued = queuedMove;
        queuedMove = null;
        controller.pointer(queued.event, 'gizmo-pointermove-immediate');
      }
      if (nativeEventType === 'gizmo-pointermove-immediate') {
        nativeEventType = 'pointermove';
      }
      const bridge = getBridge?.();
      const current = binding();
      const cameraHandle = Number(current.cameraHandle || 0);
      const renderRect = normalizeRect(getRenderRect?.() || getHitRect?.());
      const hitRect = normalizeRect(getHitRect?.() || renderRect);
      if (!bridge?.viewportGizmoPointer || cameraHandle <= 0 || !renderRect) return false;

      const clientX = Number(event.clientX ?? lastPointer.clientX);
      const clientY = Number(event.clientY ?? lastPointer.clientY);
      if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return false;
      const inside =
        hitRect
        && clientX >= hitRect.left
        && clientY >= hitRect.top
        && clientX < hitRect.left + hitRect.width
        && clientY < hitRect.top + hitRect.height;
      if (!inside && !dragging && !String(eventType).includes('cancel') && eventType !== 'blur') {
        return false;
      }

      lastPointer = {
        clientX,
        clientY,
        button: Number(event.button ?? lastPointer.button ?? 0),
        buttons: Number(event.buttons ?? lastPointer.buttons ?? 0),
      };
      const requestId = nextRequestId();
      pending.add(requestId);
      bridge.viewportGizmoPointer(
        cameraHandle,
        requestId,
        nativeEventType,
        clientX - renderRect.left,
        clientY - renderRect.top,
        renderRect.width,
        renderRect.height,
        lastPointer.button,
        lastPointer.buttons,
        modifierMask(event),
      );
      return requestId;
    },

    cancel(reason = 'cancel') {
      if (!dragging) return false;
      queuedMove = null;
      return this.pointer(lastPointer, reason);
    },

    handleResult(payload = {}) {
      const requestId = String(payload.requestId || '');
      if (!requestId || !pending.has(requestId)) {
        return { status: 'stale', ...payload };
      }
      dragging = Boolean(payload.dragging);
      activeAxis = String(payload.axis || (dragging ? activeAxis : 'none'));

      if (payload.ended && !completedEnds.has(requestId)) {
        pending.delete(requestId);
        completedEnds.add(requestId);
        dragging = false;
        activeAxis = 'none';
        onDragEnd?.(payload);
      } else if (payload.cancelled) {
        pending.delete(requestId);
        dragging = false;
        activeAxis = 'none';
        onDragCancel?.(payload);
      } else if (!payload.dragging) {
        pending.delete(requestId);
      }
      return {
        status: payload.cancelled
          ? 'cancelled'
          : payload.ended
            ? 'ended'
            : payload.dragging
              ? 'dragging'
              : payload.consumed
                ? 'consumed'
                : 'miss',
        ...payload,
      };
    },

    isDragging: () => dragging,
    activeAxis: () => activeAxis,
  };
  return controller;
};
