import assert from 'node:assert/strict';

import {
  createViewportPickController,
  indexActorsByHandle,
} from './viewportPick.js';

const actorIndex = indexActorsByHandle([
  { name: 'Box', type: 'model', handle: 101 },
  { name: 'Ignored', type: 'actor', handle: 0 },
]);

const makeController = ({ viewportRect } = {}) => {
  const calls = [];
  const emitted = [];
  const timers = [];

  const controller = createViewportPickController({
    retryDelayMs: 60,
    getBridge: () => ({
      pickActor: (...args) => {
        calls.push(args);
        return true;
      },
    }),
    getCameraBinding: () => ({
      cameraHandle: 77,
      sceneId: 'demo.scene',
    }),
    getViewportRect: () => viewportRect,
    getViewportSize: () => ({ width: 1280, height: 720 }),
    getActorIndex: () => actorIndex,
    emitActorChange: (...args) => {
      emitted.push(args);
    },
    setTimeoutFn: (fn, delay) => {
      timers.push({ fn, delay });
      return timers.length;
    },
    clearTimeoutFn: () => {},
    makeRequestId: (() => {
      let next = 10;
      return () => `pick-${next++}`;
    })(),
  });

  return { controller, calls, emitted, timers };
};

{
  const { controller, calls, emitted, timers } = makeController({
    viewportRect: { left: 100, top: 50, width: 640, height: 360 },
  });

  const didStart = controller.pickAt({ clientX: 112, clientY: 84 });

  assert.equal(didStart, true);
  assert.deepEqual(calls, [[77, 'demo.scene', 'pick-10', 12, 34, 640, 360]]);
  assert.equal(timers.length, 1);
  assert.equal(timers[0].delay, 60);

  timers[0].fn();
  assert.deepEqual(calls[1], [77, 'demo.scene', 'pick-10', 12, 34, 640, 360]);

  controller.handlePickResult({
    status: 'success',
    sceneId: 'demo.scene',
    requestId: 'stale',
    actorHandle: 101,
  });
  assert.deepEqual(emitted, []);

  controller.handlePickResult({
    status: 'success',
    sceneId: 'demo.scene',
    requestId: 'pick-10',
    actorHandle: 101,
  });
  assert.deepEqual(emitted, [['model', 'demo.scene', 'Box']]);

  controller.handlePickResult({
    status: 'success',
    sceneId: 'demo.scene',
    requestId: 'pick-10',
    actorHandle: 404,
  });
  assert.deepEqual(emitted, [['model', 'demo.scene', 'Box']]);

  assert.equal(controller.pickAt({ clientX: 1, clientY: 2 }, {
    bridge: { pickActor: () => { throw new Error('must not fallback'); } },
  }), false);
}

{
  const { controller, calls, timers } = makeController({
    viewportRect: { left: 100, top: 50, width: 640, height: 360 },
  });

  assert.equal(controller.pickAt({ clientX: 99, clientY: 84 }), false);
  assert.equal(controller.pickAt({ clientX: 112, clientY: 49 }), false);
  assert.equal(controller.pickAt({ clientX: 740, clientY: 84 }), false);
  assert.equal(controller.pickAt({ clientX: 112, clientY: 410 }), false);
  assert.deepEqual(calls, []);
  assert.deepEqual(timers, []);
}

console.log('viewport pick tests passed');
