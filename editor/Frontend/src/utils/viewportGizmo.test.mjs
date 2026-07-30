import assert from 'node:assert/strict';
import test from 'node:test';

import { createViewportGizmoController } from './viewportGizmo.js';
import * as viewportGizmoModule from './viewportGizmo.js';

test('sets and clears the native gizmo target', () => {
  const calls = [];
  const bridge = {
    setViewportGizmoTarget: (...args) => calls.push(args),
  };
  const controller = createViewportGizmoController({
    getBridge: () => bridge,
    getCameraBinding: () => ({ cameraHandle: 11, sceneId: 'Scene/default.scene' }),
  });

  controller.setTarget({ handle: 22, name: 'Cube' });
  controller.clearTarget();

  assert.deepEqual(calls, [
    [11, 'Scene/default.scene', 'Cube', 22],
    [11, 'Scene/default.scene', '', 0],
  ]);
});

test('forwards viewport-local pointer coordinates and tracks consumed drag', () => {
  const calls = [];
  const bridge = {
    viewportGizmoPointer: (...args) => calls.push(args),
  };
  const controller = createViewportGizmoController({
    getBridge: () => bridge,
    getCameraBinding: () => ({ cameraHandle: 11, sceneId: 'Scene/default.scene' }),
    getHitRect: () => ({ left: 10, top: 20, width: 200, height: 100 }),
    getRenderRect: () => ({ left: 0, top: 0, width: 220, height: 140 }),
    makeRequestId: () => 'gizmo-1',
  });

  const requestId = controller.pointer(
    { clientX: 60, clientY: 70, button: 0, buttons: 1 },
    'pointerdown',
  );
  assert.equal(requestId, 'gizmo-1');
  assert.deepEqual(calls[0].slice(0, 7), [
    11, 'gizmo-1', 'pointerdown', 60, 70, 220, 140,
  ]);

  const result = controller.handleResult({
    requestId: 'gizmo-1',
    consumed: true,
    dragging: true,
    axis: 'x',
  });
  assert.equal(result.consumed, true);
  assert.equal(controller.isDragging(), true);
});

test('drag end is reported once for persistence', () => {
  const ended = [];
  const controller = createViewportGizmoController({
    getBridge: () => ({ viewportGizmoPointer() {} }),
    getCameraBinding: () => ({ cameraHandle: 11, sceneId: 'Scene/default.scene' }),
    getHitRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
    getRenderRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
    onDragEnd: (payload) => ended.push(payload),
    makeRequestId: () => 'gizmo-end',
  });
  controller.pointer({ clientX: 10, clientY: 10, button: 0, buttons: 1 }, 'pointerdown');
  controller.handleResult({ requestId: 'gizmo-end', consumed: true, dragging: true });
  controller.handleResult({ requestId: 'gizmo-end', consumed: true, ended: true });
  controller.handleResult({ requestId: 'gizmo-end', consumed: true, ended: true });
  assert.equal(ended.length, 1);
});

test('coalesces active drag moves to one animation frame', () => {
  const calls = [];
  const frames = [];
  let request = 0;
  const controller = createViewportGizmoController({
    getBridge: () => ({ viewportGizmoPointer: (...args) => calls.push(args) }),
    getCameraBinding: () => ({ cameraHandle: 11, sceneId: 'Scene/default.scene' }),
    getHitRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
    getRenderRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
    makeRequestId: () => `request-${++request}`,
    scheduleFrame: (callback) => frames.push(callback),
  });
  const down = controller.pointer(
    { clientX: 10, clientY: 10, button: 0, buttons: 1 },
    'pointerdown',
  );
  controller.handleResult({ requestId: down, consumed: true, dragging: true, axis: 'x' });
  controller.pointer({ clientX: 20, clientY: 10, buttons: 1 }, 'pointermove');
  controller.pointer({ clientX: 30, clientY: 10, buttons: 1 }, 'pointermove');

  assert.equal(calls.length, 1);
  assert.equal(frames.length, 1);
  frames[0]();
  assert.equal(calls.length, 2);
  assert.equal(calls[1][3], 30);
});

test('resolves the main viewport gizmo target from a successful pick', () => {
  assert.equal(
    typeof viewportGizmoModule.resolveViewportGizmoTarget,
    'function',
    'main viewport selection resolver must exist',
  );
  const target = viewportGizmoModule.resolveViewportGizmoTarget({
    sceneId: 'scene.ini',
    selection: { scene: 'scene.ini', actor: 'Ball', actor_type: 'model' },
    pickResult: { actor: { handle: 1176640039248, name: 'Ball', type: 'model' } },
    actorIndex: new Map(),
  });
  assert.deepEqual(target, {
    handle: 1176640039248,
    name: 'Ball',
    type: 'model',
  });
});

test('resolves a scene-tree selection through the actor index', () => {
  assert.equal(typeof viewportGizmoModule.resolveViewportGizmoTarget, 'function');
  const target = viewportGizmoModule.resolveViewportGizmoTarget({
    sceneId: 'scene.ini',
    selection: { scene: 'scene.ini', actor: 'Ball', actor_type: 'model' },
    actorIndex: new Map([
      [1176640039248, { name: 'Ball', type: 'model' }],
    ]),
  });
  assert.equal(target?.handle, 1176640039248);
});
