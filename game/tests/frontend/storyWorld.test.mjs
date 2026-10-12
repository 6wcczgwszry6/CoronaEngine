import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import test from 'node:test';
import { createPlayerController, VIEW_LABELS } from '../../frontend/playerController.mjs';
import { createPlayerSave } from '../../frontend/playerSave.mjs';
import { ensureStoryCharacters, syncPlacementActors } from '../../frontend/storyActors.mjs';
import * as gameplayModule from '../../frontend/storyGameplay.mjs';
import * as storyPropsModule from '../../frontend/storyProps.mjs';
import * as prophetDialogueModule from '../../frontend/prophetDialogue.mjs';
import * as storyCubeModule from '../../frontend/storyCube.mjs';
import * as storyWorldRulesModule from '../../frontend/storyWorldRules.mjs';
import * as storyProphetActionsModule from '../../frontend/storyProphetActions.mjs';
import { STORY_CHARACTERS, PROPHET_GUID, resolveStoryAssetPath, sceneSnapshot } from '../../frontend/storyCharacters.mjs';
import { actorFixture } from './fixtures.mjs';
import { createStoryNavigationController } from '../../frontend/storyNavigation.mjs';
import { createStoryCameraController } from '../../../editor/Frontend/src/utils/viewportStoryCamera.js';
import { editorApi } from '../../../editor/Frontend/src/api/editorApi.js';
import * as launcher from '../../../editor/Frontend/src/services/projectLauncherService.js';
import * as worldMode from '../../../editor/Frontend/src/services/worldModeService.js';
import { NAVIGATION_KEY } from '../../frontend/storyNavigation.mjs';
import { gameplayConfig, projectReady } from './fixtures.mjs';
import * as lifecycle from '../../../editor/Frontend/src/services/worldSessionLifecycle.js';
import lanchat from '../../../editor/Frontend/src/stores/lanchat.js';

const require = createRequire(new URL('../../../editor/Frontend/package.json', import.meta.url));
const vue = require('vue');
const { ref, proxyRefs, nextTick, watch, reactive, computed, withDirectives } = vue;
const { parse, compileScript, compileTemplate, babelParse } = require('vue/compiler-sfc');
const { descriptor } = parse(fs.readFileSync(new URL('../../../editor/Frontend/src/views/layout/StoryWorld.vue', import.meta.url), 'utf8'));
const compiled = compileScript(descriptor, { id: 'story-navigation-test', genDefaultAs: 'StoryWorld' });
let setupSource = compiled.content;
for (const node of babelParse(compiled.content, { sourceType: 'module' }).program.body
  .filter(node => node.type === 'ImportDeclaration').reverse()) {
  // 样式副作用导入在这里无需执行，直接摘除
  if (/\.css$/.test(node.source.value)) { setupSource = setupSource.slice(0, node.start) + setupSource.slice(node.end); continue; }
  const bindings = node.specifiers.map(specifier => `${JSON.stringify(specifier.imported.name)}: ${specifier.local.name}`).join(', ');
  setupSource = setupSource.slice(0, node.start) + `const { ${bindings} } = modules[${JSON.stringify(node.source.value)}];`
    + setupSource.slice(node.end);
}
const makeComponent = new Function('modules', `${setupSource}; return StoryWorld;`);
const template = compileTemplate({ source: descriptor.template.content, filename: 'StoryWorld.vue',
  id: 'story-ui-test', compilerOptions: { mode: 'function' } });
assert.deepEqual(template.errors, []);
const renderStory = new Function('Vue', template.code)(vue);
const styles = require('postcss').parse(descriptor.styles.map(style => style.content).join('\n'));
function findNode(node, predicate) {
  if (!node || typeof node !== 'object') return null;
  if (predicate(node)) return node;
  for (const child of Array.isArray(node.children) ? node.children : []) {
    const match = findNode(child, predicate);
    if (match) return match;
  }
  return null;
}
const turn = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const MAIN = 'D:/story', CHILD = `${MAIN}/.game/subworld`;
function clickWorld(page) { if (!page.instance.inventoryOpen.value) page.instance.toggleInventory(); void page.instance.navigateWorld(); }
const event = (props = {}) => ({ code: 'KeyO', preventDefault() { this.defaultPrevented = true; }, stopPropagation() {}, ...props });
const pose = position => ({ name: 'main', position, forward: [0, 0, 1], world_up: [0, 1, 0], fov: 65 });

async function fixture(t, options = {}) {
  const globals = ['window', 'document', 'CustomEvent', 'ResizeObserver', 'requestAnimationFrame', 'cancelAnimationFrame'];
  const previous = Object.fromEntries(globals.map(key => [key, globalThis[key]]));
  const calls = [], alerts = [], frames = new Map(), pages = [];
  let frameTime = performance.now();
  let activePath = MAIN, route = '/', frameId = 0, page = null, handle = 10;
  const poses = new Map([[MAIN, pose([1, 2, 3])], [CHILD, pose([5, 6, 7])]]);
  const actors = new Map([MAIN, CHILD].map(path => [path, STORY_CHARACTERS.map(character => actorFixture(character))]));
  function surface() {
    const listeners = new Map();
    return {
      listeners,
      addEventListener(name, fn) { if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name).add(fn); },
      removeEventListener(name, fn) { listeners.get(name)?.delete(fn); },
      dispatchEvent(event) { for (const fn of listeners.get(event.type) || []) fn(event); },
    };
  }
  const bridge = Object.fromEntries(['actorTransform', 'cameraMove', 'setCameraViewport', 'setViewportGizmoTarget', 'setViewportUiMode', 'setViewportSystemCursorHidden']
    .map(name => [name, (...args) => { calls.push([name, ...args]); return true; }]));
  globalThis.window = Object.assign(surface(), { coronaBridge: bridge, devicePixelRatio: 1,
    location: { href: 'file:///D:/engine/editor/Frontend/dist/index.html' },
    localStorage: { setItem() {} }, alert: message => alerts.push(message) });
  globalThis.document = Object.assign(surface(), { hidden: false, hasFocus: () => true });
  globalThis.CustomEvent = class { constructor(type, options) { Object.assign(this, { type }, options); } };
  globalThis.ResizeObserver = class { observe() {} disconnect() { calls.push(['disconnect']); } };
  globalThis.requestAnimationFrame = callback => { frames.set(++frameId, callback); return frameId; };
  globalThis.cancelAnimationFrame = id => frames.delete(id);

  t.mock.method(editorApi.projectSettings, 'getActiveProjectInfo', async () => ({ project_path: activePath, mode: 'story' }));
  t.mock.method(editorApi.project, 'getProjectLoadStatus', async () => options.loadStatus ? options.loadStatus(activePath) : projectReady(activePath));
  t.mock.method(editorApi.main, 'onInit', async () => options.init ? options.init() : { scenes: [{ path: 'scene.ini' }], active_index: 0 });
  t.mock.method(editorApi.scene, 'setActorTransform', async (sceneId, guid, transform) => {
    const source = activePath;
    calls.push(['playerSave', source, sceneId, guid, structuredClone(transform)]);
    await options.save?.();
    assert.equal(activePath, source, 'a pending save must never cross native scene replacement');
    const actor = actors.get(source).find(item => item.actor_guid === guid);
    for (const key of ['position', 'rotation']) if (transform[key]) actor.geometry[key] = [...transform[key]];
    return { status: 'success', actor: structuredClone(actor) };
  });
  t.mock.method(editorApi.scene, 'getSnapshot', async () => ({ scene: 'scene.ini', active_camera_name: 'main',
    actors: structuredClone(actors.get(activePath)),
    cameras: [{ ...poses.get(activePath), handle: ++handle }] }));
  t.mock.method(editorApi.viewport, 'setCameraPose', async (sceneId, name, camera) => {
    calls.push(['pose', activePath, sceneId, name, camera]);
    await options.pose?.();
    poses.set(activePath, { name, ...structuredClone(camera) });
    return { data: { status: 'success' } };
  });
  t.mock.method(editorApi.sceneTools, 'setActorState', async (scene, guid, state) => {
    const actor = actors.get(activePath).find(item => item.actor_guid === guid);
    Object.assign(actor, state);
    return { status: 'success', actor: structuredClone(actor) };
  });
  // 世界碎片（红球）在快照里并不存在，由剧情建模流程创建：这里补上同一份建模夹具
  t.mock.method(editorApi.sceneTools, 'createActor', async (scene, path, type, data) => {
    calls.push(['create', activePath, scene, path, structuredClone(data)]);
    const character = [...STORY_CHARACTERS, gameplayModule.FRAGMENT].find(item => item.guid === data.actor_guid);
    // 陈列物（guid 形如 story.placement.0000）不是剧情角色：它由布局驱动创建，
    // 形状与名字来自 storyProps / syncPlacementActors 写下的字段，不能套用角色夹具。
    if (!character) {
      const index = storyPropsModule.placementIndex(data.actor_guid);
      assert.notEqual(index, null, `createActor 收到未知 GUID：${data.actor_guid}`);
      const prop = storyPropsModule.findProp(
        String(data.entity_id || '').slice(storyPropsModule.PLACEMENT_PREFIX.length));
      assert.ok(prop, `createActor 收到未知陈列物：${data.entity_id}`);
      assert.equal(data.semantic_role, 'placement');
      const actor = { ...actorFixture({ role: 'placement', name: data.name, guid: data.actor_guid,
        height: prop.height, rotation: [...data.rotation], x: 0, z: 0 }),
        model_ref: '', route: path,
        geometry: { position: [...data.position], rotation: [...data.rotation], scale: [...data.scale] } };
      actors.get(activePath).push(actor);
      return { status: 'success', actor: structuredClone(actor) };
    }
    const actor = { ...actorFixture(character), model_ref: data.model_ref || '',
      geometry: { position: [...data.position], rotation: [...data.rotation], scale: [...data.scale] } };
    actors.get(activePath).push(actor);
    return { status: 'success', actor: structuredClone(actor) };
  });
  // 陈列物退场：syncPlacementActors 用 removeActor 撤下布局里已经没有的那一件。
  t.mock.method(editorApi.sceneTools, 'removeActor', async (scene, guid) => {
    calls.push(['remove', activePath, scene, guid]);
    const list = actors.get(activePath);
    const index = list.findIndex(item => item.actor_guid === guid);
    if (index >= 0) list.splice(index, 1);
    return { status: 'success' };
  });
  t.mock.method(editorApi.scratch, 'sendKeyEvent', async (key, mods, displayKey) => {
    if (key === gameplayModule.GAMEPLAY_KEY) {
      const request = JSON.parse(displayKey);
      // 小世界的自有文档（陈列 / 世界规则 / 名册）在进入世界时各读一次，它们不是战斗操作，
      // 因此不交给用例的战斗桩：默认给一份合法的空文档，用例可用 options.documents 覆盖。
      const documents = { loadPlacements: { version: 1, placements: [] },
        loadWorldRules: { version: 1, rules: [] },
        loadSubworlds: { version: 1, subworlds: [] }, ...options.documents };
      if (documents[request.action]) {
        return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
          state: structuredClone(documents[request.action]) };
      }
      if (options.gameplay) return options.gameplay(request, activePath);
      return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
        state: { version: 2, revision: 0, rage: 0, boss: { hp: 0 }, drop: null, inventory: { worldFragment: 0 } },
        config: gameplayConfig };
    }
    calls.push(['key', key, mods, displayKey]);
    if (options.prepare) return options.prepare(key);
    const { direction } = JSON.parse(displayKey);
    assert.equal(key, NAVIGATION_KEY);
    if ((activePath === CHILD && direction === 'enter') || (activePath === MAIN && direction === 'exit')) return { status: 'noop' };
    return { data: { status: 'ok', navigation: { source: activePath, target: activePath === MAIN ? CHILD : MAIN,
      direction, mode: 'story' } } };
  });
  t.mock.method(editorApi.project, 'openProject', async path => {
    calls.push(['nativeOpen', path]);
    const response = options.open ? await options.open(path) : { ok: true, path };
    if (response?.ok) activePath = path;
    return response;
  });
  t.mock.method(lanchat, 'finishWorldSession', async () => { calls.push(['chatCleanup']); });
  const realOpen = launcher.projectLauncherService.openProject;
  t.mock.method(launcher.projectLauncherService, 'openProject', (...args) => {
    const result = realOpen(...args);
    page?.unmount(); // App.vue removes the routed component on beginOpen.
    return result;
  });
  await worldMode.worldModeService.resolve(MAIN, { force: true });
  function mount() {
    const mounted = [], unmounted = [];
    const component = makeComponent({
      vue: { ref, nextTick, watch, reactive, computed, withDirectives, onMounted: fn => mounted.push(fn), onUnmounted: fn => unmounted.push(fn) },
      'vue-router': { onBeforeRouteLeave() {}, useRouter: () => ({ replace: async path => { route = path; } }) },
      '@/api/editorApi.js': { editorApi },
      '@/services/worldModeService.js': worldMode,
      '@/services/projectLauncherService.js': launcher,
      '@/services/worldSessionLifecycle.js': lifecycle,
      '@/utils/viewportStoryCamera.js': { createStoryCameraController },
      '../../../../../game/frontend/storyNavigation.mjs': { createStoryNavigationController, NAVIGATION_KEY },
      '../../../../../game/frontend/storyActors.mjs': { ensureStoryCharacters, syncPlacementActors },
      '../../../../../game/frontend/playerController.mjs': { createPlayerController, VIEW_LABELS },
      '../../../../../game/frontend/playerSave.mjs': { createPlayerSave },
      '../../../../../game/frontend/storyGameplay.mjs': gameplayModule,
      '../../../../../game/frontend/storyCharacters.mjs': { STORY_CHARACTERS, PROPHET_GUID, resolveStoryAssetPath, sceneSnapshot },
      '../../../../../game/frontend/storyProps.mjs': storyPropsModule,
      '../../../../../game/frontend/prophetDialogue.mjs': prophetDialogueModule,
      '../../../../../game/frontend/storyCube.mjs': storyCubeModule,
      '../../../../../game/frontend/storyWorldRules.mjs': storyWorldRulesModule,
      '../../../../../game/frontend/storyProphetActions.mjs': storyProphetActionsModule,
    });
    const instance = component.setup({}, { expose() {} });
    instance.surface.value = { focus() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 600 }) };
    let disposed = false;
    page = { instance, mount: () => Promise.all(mounted.map(fn => fn())),
      unmount() { if (!disposed) { disposed = true; for (const fn of unmounted) fn(); } } };
    pages.push(page);
    return page;
  }
  t.after(async () => {
    for (const p of pages) p.unmount();
    await lifecycle.drainWorldSession();
    await lifecycle.flushWorldSessionSaves();
    worldMode.worldModeService.invalidate();
    Object.assign(globalThis, previous);
  });
  return { mount, calls, alerts, frames, poses, actors, get route() { return route; },
    step(ms = 50) { frameTime = Math.max(frameTime, performance.now()) + ms;
      const pending = [...frames.values()]; frames.clear(); pending.forEach(fn => fn(frameTime)); },
    opens: () => calls.filter(call => call[0] === 'nativeOpen').map(call => call[1]) };
}

test('real story page inventory button retains independent poses, stays story, and never reuses old handles', async t => {
  const f = await fixture(t);
  let page = f.mount(); await page.mount();
  page.instance.camera.wheel(event({ deltaY: -100 })); f.step();
  page.instance.onKeyDown(event({ code: 'KeyW' }));
  const stale = [...f.frames.values()][0];
  const mainPose = page.instance.camera.snapshotPose().camera;
  clickWorld(page);
  assert.equal(page.instance.navigation.busy, true);
  const afterLock = page.instance.camera.snapshotPose().camera;
  page.instance.camera.wheel(event({ deltaY: -100 }));
  assert.deepEqual(page.instance.camera.snapshotPose().camera, afterLock);
  await turn();
  assert.deepEqual(f.opens(), [CHILD]);
  assert.equal(f.frames.size, 0);
  const count = f.calls.length; stale(100);
  assert.equal(f.calls.length, count);
  assert.deepEqual(f.poses.get(MAIN).position, mainPose.position);
  assert.equal(worldMode.worldModeState.mode, 'story');
  assert.equal(f.route, '/');
  assert.equal(document.listeners.get('keydown').size, 0);
  assert.equal(window.listeners.get('pointermove').size, 0);

  page = f.mount(); await page.mount();
  page.instance.camera.pointerDown(event({ button: 2, clientX: 0, clientY: 0 }));
  page.instance.camera.pointerMove(event({ buttons: 2, clientX: 50, clientY: 20 }));
  page.instance.camera.wheel(event({ deltaY: -1 }));
  f.step();
  const childPose = page.instance.camera.snapshotPose().camera;
  clickWorld(page);
  await turn();
  assert.deepEqual(f.opens(), [CHILD, MAIN]);
  page = f.mount(); await page.mount();
  assert.deepEqual(page.instance.camera.snapshotPose().camera, mainPose);
  clickWorld(page); await turn();
  page = f.mount(); await page.mount();
  assert.deepEqual(page.instance.camera.snapshotPose().camera, childPose);
  // Rebinding must restore the controller orbit too, not just display one
  // saved frame before jumping back to default yaw/pitch on the next input.
  page.instance.onKeyDown(event({ code: 'KeyW' })); f.step();
  const resumedPose = page.instance.camera.snapshotPose().camera;
  for (let i = 0; i < 3; ++i) assert.ok(Math.abs(resumedPose.forward[i] - childPose.forward[i]) < 1e-9);
  assert.deepEqual(f.alerts, []);
  assert.ok(f.calls.filter(call => call[0] === 'setViewportUiMode').every(call => call[2] === 'flat2d'));
});

test('O is ignored before bind; Escape cancels pending init and never binds a stale viewport', async t => {
  const init = deferred();
  const f = await fixture(t, { init: () => init.promise });
  const page = f.mount(); const mounted = page.mount(); await turn();
  clickWorld(page);
  assert.ok(!f.calls.some(call => call[0] === 'key'));
  page.instance.onKeyDown(event({ code: 'Escape' }));
  init.resolve({ path: 'scene.ini' }); await mounted; await turn();
  assert.equal(f.route, '/StartScreen');
  assert.ok(!f.calls.some(call => call[0] === 'setCameraViewport'));
});

test('real page filters repeated/editable/composition O and locks camera while preparation runs', async t => {
  const prep = deferred();
  const f = await fixture(t, { prepare: () => prep.promise });
  const page = f.mount(); await page.mount();
  for (const props of [{ repeat: true }, { ctrlKey: true }, { altKey: true }, { metaKey: true },
    { isComposing: true }, { target: { isContentEditable: true } }]) page.instance.onKeyDown(event(props));
  assert.ok(!f.calls.some(call => call[0] === 'pose'));
  clickWorld(page); await turn();
  const pose = page.instance.camera.snapshotPose();
  page.instance.onKeyDown(event({ code: 'KeyW' }));
  page.instance.camera.pointerDown(event({ button: 2 }));
  page.instance.camera.wheel(event({ deltaY: -1 }));
  clickWorld(page);
  assert.equal(f.frames.size, 0);
  assert.deepEqual(page.instance.camera.snapshotPose(), pose);
  prep.resolve({ status: 'error', message: 'copy failed' }); await turn();
  assert.deepEqual(f.opens(), []);
  assert.deepEqual(f.alerts, ['copy failed']);
  assert.equal(page.instance.navigation.busy, false);
});

test('Escape during copy ignores its late response and leaves the game page', async t => {
  const prep = deferred();
  const f = await fixture(t, { prepare: () => prep.promise });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  page.instance.onKeyDown(event({ code: 'Escape' }));
  prep.resolve({ status: 'ok', navigation: { source: MAIN, target: CHILD, direction: 'enter', mode: 'story' } });
  await turn();
  assert.deepEqual(f.opens(), []);
  assert.equal(f.route, '/StartScreen');
  assert.deepEqual(f.alerts, []);
});

test('a newer canonical open drains preparation and prevents late subworld navigation', async t => {
  const prep = deferred();
  const f = await fixture(t, { prepare: () => prep.promise });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  const other = launcher.projectLauncherService.openProject('D:/other'); await turn();
  assert.deepEqual(f.opens(), []); // Python still works against the source scene.
  prep.resolve({ status: 'ok', navigation: { source: MAIN, target: CHILD, direction: 'enter', mode: 'story' } });
  await other; await turn();
  assert.deepEqual(f.opens(), ['D:/other']);
  assert.equal(worldMode.worldModeState.projectPath, 'D:/other');
  assert.deepEqual(f.alerts, []);
});

test('failed target open recovers through canonical launcher after source disposal', async t => {
  const f = await fixture(t, { open: path => path === CHILD ? { ok: false, message: 'bad asset' } : { ok: true, path } });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  assert.deepEqual(f.opens(), [CHILD, MAIN]);
  assert.equal(worldMode.worldModeState.status, 'ready');
  assert.equal(worldMode.worldModeState.mode, 'story');
  assert.match(f.alerts[0], /已恢复来源世界.*bad asset/);
  const restored = f.mount(); await restored.mount();
  assert.ok(restored.instance.camera.snapshotPose());
});

test('failed recovery routes to launcher and explains both failures', async t => {
  const f = await fixture(t, { open: () => { throw new Error('native open failed'); } });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  assert.deepEqual(f.opens(), [CHILD, MAIN]);
  assert.equal(f.route, '/StartScreen');
  assert.match(f.alerts[0], /恢复来源世界也失败/);
});

test('global Escape during native open invalidates recovery and late mode changes', async t => {
  const opened = deferred();
  const f = await fixture(t, { open: () => opened.promise });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  launcher.cancelPendingProjectOpen(); // App.vue owns Escape after source-page removal.
  opened.reject(new Error('late failure')); await turn();
  assert.deepEqual(f.opens(), [CHILD]);
  assert.deepEqual(f.alerts, []);
  assert.notEqual(worldMode.worldModeState.status, 'ready');
});


test('Escape saves the final moved player once; reopening restores position and facing', async t => {
  const f = await fixture(t); let page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'KeyD' })); f.step();
  const moved = page.instance.camera.snapshotPlayer();
  assert.ok(moved.position[0] > 0);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 0);
  await page.instance.exitStory();
  assert.equal(f.route, '/StartScreen'); assert.equal(f.frames.size, 0);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 1);
  page.unmount(); await worldMode.worldModeService.resolve(MAIN, { force: true });
  page = f.mount(); await page.mount();
  assert.deepEqual(page.instance.camera.snapshotPlayer().position, moved.position);
  assert.deepEqual(page.instance.camera.snapshotPlayer().rotation, moved.rotation);
  assert.ok(page.instance.camera.snapshotPose().camera.position[0] < moved.position[0]);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 1);
});

test('failed exit save keeps the route and supports a successful retry', async t => {
  let fail = true;
  const f = await fixture(t, { save: async () => { if (fail) throw new Error('disk is full'); } });
  const page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'KeyW' })); f.step();
  await page.instance.exitStory();
  assert.equal(f.route, '/'); assert.deepEqual(f.opens(), []);
  assert.deepEqual(f.alerts, ['disk is full']); assert.equal(f.frames.size, 0);
  fail = false; await page.instance.exitStory();
  assert.equal(f.route, '/StartScreen'); assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 2);
});

test('canonical open waits for the old player save; later selections supersede earlier ones', async t => {
  const saved = deferred();
  const f = await fixture(t, { save: () => saved.promise }); const page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'KeyD' })); f.step();
  const stale = [...f.frames.values()][0];
  const first = launcher.projectLauncherService.openProject(CHILD); await turn();
  const second = launcher.projectLauncherService.openProject(MAIN); await turn();
  assert.deepEqual(f.opens(), []); assert.equal(f.frames.size, 0);
  const count = f.calls.length; stale(performance.now() + 100); assert.equal(f.calls.length, count);
  saved.resolve(); assert.equal((await first).status, 'superseded'); await second;
  assert.deepEqual(f.opens(), [MAIN]);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 1);
});

test('canonical open cannot replace a scene after save failure; retry retains the old pose', async t => {
  let fail = true;
  const f = await fixture(t, { save: async () => { if (fail) throw new Error('cannot write scene'); } });
  const page = f.mount(); await page.mount(); page.instance.onKeyDown(event({ code: 'KeyW' })); f.step();
  await assert.rejects(launcher.projectLauncherService.openProject(CHILD), /cannot write scene/);
  assert.deepEqual(f.opens(), []);
  fail = false; await launcher.projectLauncherService.openProject(CHILD);
  assert.deepEqual(f.opens(), [CHILD]);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 2);
});

test('a timed-out save blocks movement and replacement until its real acknowledgement', async t => {
  const saved = deferred();
  const f = await fixture(t, { save: () => saved.promise }); const page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'KeyW' })); f.step();
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const leaving = page.instance.exitStory(); await turn();
  t.mock.timers.tick(30_001); await leaving;
  assert.equal(f.route, '/'); assert.match(f.alerts[0], /超时/);
  page.instance.onKeyDown(event({ code: 'KeyW' })); assert.equal(f.frames.size, 0);
  const opening = launcher.projectLauncherService.openProject(CHILD); await turn();
  assert.deepEqual(f.opens(), []);
  saved.resolve(); await opening;
  assert.deepEqual(f.opens(), [CHILD]);
  assert.equal(f.calls.filter(c => c[0] === 'playerSave').length, 1);
});

test('world replacement drains pending initialization and never binds its late result', async t => {
  const init = deferred(); const f = await fixture(t, { init: () => init.promise });
  const page = f.mount(); const mounting = page.mount(); await turn();
  const opening = launcher.projectLauncherService.openProject(CHILD); await turn();
  assert.deepEqual(f.opens(), []);
  init.resolve({ path: 'scene.ini' }); await mounting; await opening;
  assert.deepEqual(f.opens(), [CHILD]);
  assert.ok(!f.calls.some(c => ['setCameraViewport', 'actorTransform', 'playerSave'].includes(c[0])));
});


test('Escape fences a late O result even when the exit save fails', async t => {
  const prep = deferred();
  const f = await fixture(t, { prepare: () => prep.promise });
  const page = f.mount(); await page.mount();
  clickWorld(page); await turn();
  // Simulate a failed finalizer, independently of the already saved O snapshot.
  const failed = t.mock.method(page.instance.saveRegistration, 'flush', async () => { throw new Error('exit save failed'); });
  await page.instance.exitStory();
  assert.equal(f.route, '/');
  prep.resolve({ status: 'ok', navigation: { source: MAIN, target: CHILD, direction: 'enter', mode: 'story' } });
  await turn();
  assert.deepEqual(f.opens(), []);
  assert.deepEqual(f.alerts, ['exit save failed']);
  assert.equal(page.instance.navigation.busy, false);
  failed.mock.restore();
});

test('Tab captures gameplay, repeated Tab/F are ignored and Escape closes inventory first', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  page.instance.camera.pointerMove(event({ clientX: 799, clientY: 300 }));
  page.instance.onKeyDown(event({ code: 'Tab' }));
  assert.equal(page.instance.inventoryOpen.value, true); assert.equal(f.frames.size, 0);
  page.instance.onKeyDown(event({ code: 'Tab', repeat: true }));
  assert.equal(page.instance.inventoryOpen.value, true);
  const before = page.instance.camera.snapshotPose();
  page.instance.onKeyDown(event({ code: 'KeyW' }));
  page.instance.camera.pointerMove(event({ clientX: 600, clientY: 300 }));
  page.instance.onPointerDown(event({ button: 0 }));
  page.instance.onKeyDown(event({ code: 'KeyO' })); page.instance.onKeyDown(event({ code: 'KeyF' }));
  await turn();
  assert.deepEqual(page.instance.camera.snapshotPose(), before); assert.deepEqual(f.opens(), []);
  assert.equal(page.instance.actionBusy.value, false);
  page.instance.onKeyDown(event({ code: 'Escape' })); await turn();
  assert.equal(page.instance.inventoryOpen.value, false); assert.equal(f.route, '/');
  page.instance.onKeyDown(event({ code: 'KeyF', repeat: true }));
  assert.equal(page.instance.actionBusy.value, false);
  page.instance.onKeyDown(event({ code: 'Escape' })); await turn();
  assert.equal(f.route, '/StartScreen');
});

test('blur, hidden page and inventory close reseed mouse without a jump', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  page.instance.camera.pointerMove(event({ clientX: 799, clientY: 300 })); f.step();
  page.instance.onBlur(); assert.equal(f.frames.size, 0);
  const before = page.instance.camera.snapshotPose();
  page.instance.onFocus();
  page.instance.camera.pointerMove(event({ clientX: 400, clientY: 300 })); f.step();
  assert.deepEqual(page.instance.camera.snapshotPose(), before);
  page.instance.camera.pointerMove(event({ clientX: 799, clientY: 300 }));
  document.hidden = true; page.instance.onVisibilityChange(); assert.equal(f.frames.size, 0);
  document.hidden = false; page.instance.onFocus();
});

test('unacknowledged combat blocks native replacement; retry does not change operation identity', async t => {
  let fail = true; const commands = [];
  const state = { version: 2, revision: 0, rage: 0, boss: { hp: 200 }, drop: null, inventory: { worldFragment: 0 } };
  const config = gameplayConfig;
  const f = await fixture(t, { gameplay: async request => {
    if (request.action !== 'load') {
      commands.push(request);
      if (fail) throw new Error('combat disk full');
      state.boss.hp = 180; state.revision = 1;
    }
    return { status: 'ok', role: 'main', state: structuredClone(state), config };
  } });
  const page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'KeyW' }));
  for (let i = 0; i < 60; i++) f.step(50);
  page.instance.camera.keyUp(event({ code: 'KeyW' }));
  assert.equal(page.instance.bossNearby.value, true);
  page.instance.onPointerDown(event({ button: 0 })); await turn();
  assert.match(page.instance.gameplayError.value, /combat disk full/);
  assert.equal(page.instance.gameplay.needsSave, true);
  await assert.rejects(launcher.projectLauncherService.openProject(CHILD), /combat disk full/);
  assert.deepEqual(f.opens(), []);
  fail = false;
  await launcher.projectLauncherService.openProject(CHILD);
  assert.deepEqual(f.opens(), [CHILD]);
  assert.equal(new Set(commands.map(c => c.operationId)).size, 1);
  assert.ok(commands.every(c => c.projectPath === MAIN));
});


test('inventory template captures pointer input and its close button restores control without an attack or jump', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  const attack = t.mock.method(page.instance.gameplay, 'attack', async () => {});
  page.instance.camera.pointerMove(event({ clientX: 799, clientY: 300 })); f.step();
  page.instance.onKeyDown(event({ code: 'Tab' }));
  const before = page.instance.camera.snapshotPose();
  const tree = renderStory(proxyRefs(page.instance), []);
  const overlay = findNode(tree, node => node.props?.class === 'story-bag');
  const close = findNode(overlay, node => node.type === 'button' && node.props?.['aria-label'] === '合上行囊');
  assert.ok(overlay); assert.ok(close);

  for (const selector of ['.story-bag']) {
    let interactive = false;
    styles.walkRules(rule => {
      if (rule.selectors.includes(selector)) rule.walkDecls('pointer-events', declaration => {
        interactive = declaration.value === 'auto';
      });
    });
    assert.ok(interactive, `${selector} must explicitly participate in hit testing`);
  }
  for (const name of ['onPointerdown', 'onPointermove', 'onWheel']) {
    let stopped = false;
    const input = event({ button: 0, clientX: 799, clientY: 300, deltaY: 200,
      stopPropagation() { stopped = true; } });
    overlay.props[name](input);
    assert.ok(stopped, `${name} must not bubble into the viewport`);
    if (name === 'onWheel') assert.ok(input.defaultPrevented);
  }
  assert.equal(page.instance.inventoryOpen.value, true);
  assert.equal(f.frames.size, 0);
  close.props.onClick(event()); await turn();
  assert.equal(page.instance.inventoryOpen.value, false);
  assert.equal(attack.mock.callCount(), 0);
  assert.equal(f.route, '/');
  page.instance.camera.pointerMove(event({ clientX: 400, clientY: 300 })); f.step();
  assert.deepEqual(page.instance.camera.snapshotPose(), before);
});


test('real story page settles airborne Tab, blur, pointerleave and hidden-page interruptions', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  const groundY = page.instance.camera.snapshotPlayer().position[1];
  const stopCases = [
    [() => page.instance.onKeyDown(event({ code: 'Tab' })), () => page.instance.toggleInventory()],
    [() => page.instance.onBlur(), () => page.instance.onFocus()],
    [() => page.instance.camera.pointerLeave(), () => {}],
    [() => { document.hidden = true; page.instance.onVisibilityChange(); },
      () => { document.hidden = false; page.instance.onVisibilityChange(); }],
  ];
  for (const [stop, resume] of stopCases) {
    page.instance.onKeyDown(event({ code: 'Space' })); f.step();
    const airborne = page.instance.camera.snapshotPlayer();
    assert.equal(airborne.grounded, false); assert.ok(airborne.position[1] > groundY);
    const stale = [...f.frames.values()][0]; stop();
    const landed = page.instance.camera.snapshotPlayer();
    assert.equal(landed.grounded, true); assert.equal(landed.position[1], groundY);
    assert.equal(landed.position[2], airborne.position[2]);
    assert.equal(f.frames.size, 0); const count = f.calls.length; stale(50000); assert.equal(f.calls.length, count);
    // Locks reject new Space; pointerleave instead clears held state.
    if (document.hidden || page.instance.inventoryOpen.value) {
      page.instance.onKeyDown(event({ code: 'Space' })); assert.equal(f.frames.size, 0);
    }
    resume();
    const camera = page.instance.camera.snapshotPose();
    page.instance.camera.pointerMove(event({ clientX: 400, clientY: 300 })); f.step();
    assert.deepEqual(page.instance.camera.snapshotPose(), camera);
  }
  await page.instance.saveRegistration.flush();
  assert.equal(f.actors.get(MAIN)[0].geometry.position[1], groundY);
  assert.deepEqual(f.alerts, []);
});
test('half-jump inventory travel saves ground and the corrected model once, preserves camera and keeps child combat hidden', async t => {
  const f = await fixture(t); let page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'Space' })); f.step(); f.step();
  const airborne = page.instance.camera.snapshotPlayer(), groundY = f.actors.get(MAIN)[0].geometry.position[1];
  clickWorld(page); await turn();
  assert.deepEqual(f.opens(), [CHILD]);
  const saved = f.actors.get(MAIN)[0].geometry;
  assert.equal(saved.position[1], groundY); assert.equal(saved.position[2], airborne.position[2]);
  assert.deepEqual(saved.rotation, airborne.rotation);
  const savedCamera = structuredClone(f.poses.get(MAIN));
  page = f.mount(); await page.mount();
  assert.equal(page.instance.bossNearby.value, false); assert.equal(f.actors.get(CHILD)[1].visible, false);
  clickWorld(page); await turn();
  page = f.mount(); await page.mount();
  const restored = page.instance.camera.snapshotPlayer();
  assert.equal(restored.grounded, true); assert.deepEqual(restored.position, saved.position);
  assert.deepEqual(restored.rotation, saved.rotation); assert.equal(restored.facingYaw, airborne.facingYaw);
  assert.deepEqual(page.instance.camera.snapshotPose().camera.position, savedCamera.position);
  assert.deepEqual(f.alerts, []);
});
test('half-jump Escape waits for the ground save, blocks Space and remains in world on save failure', async t => {
  const gate = deferred(); let fail = true, block = true;
  const f = await fixture(t, { save: async () => { if (block) await gate.promise; if (fail) throw new Error('landing disk full'); } });
  const page = f.mount(); await page.mount(); const groundY = page.instance.camera.snapshotPlayer().position[1];
  page.instance.onKeyDown(event({ code: 'Space' })); f.step();
  const before = page.instance.camera.snapshotPlayer(); page.instance.onKeyDown(event({ code: 'Escape' }));
  await turn(); assert.equal(f.route, '/');
  page.instance.onKeyDown(event({ code: 'Space' })); assert.equal(f.frames.size, 0);
  gate.resolve(); await turn();
  assert.equal(f.route, '/'); assert.match(page.instance.gameplayError.value, /landing disk full/);
  assert.equal(page.instance.camera.snapshotPlayer().position[1], groundY);
  const writes = f.calls.filter(c => c[0] === 'playerSave'); assert.equal(writes.length, 1);
  assert.equal(writes[0][4].position[1], groundY); assert.equal(writes[0][4].position[2], before.position[2]);
  fail = false; block = false; page.instance.onKeyDown(event({ code: 'Escape' })); await turn();
  assert.equal(f.route, '/StartScreen'); assert.deepEqual(f.actors.get(MAIN)[0].geometry.position, writes[0][4].position);
});
test('unrelated world replacement settles locally after invalidation and saves without using old handles', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  const groundY = page.instance.camera.snapshotPlayer().position[1];
  page.instance.onKeyDown(event({ code: 'Space' })); f.step();
  const before = page.instance.camera.snapshotPlayer(), stale = [...f.frames.values()][0];
  const index = f.calls.length;
  await launcher.projectLauncherService.openProject('D:/other'); stale(99999);
  assert.deepEqual(f.opens(), ['D:/other']);
  assert.ok(!f.calls.slice(index).some(c => ['actorTransform', 'cameraMove'].includes(c[0])));
  const write = f.calls.slice(index).find(c => c[0] === 'playerSave');
  assert.equal(write[1], MAIN); assert.equal(write[4].position[1], groundY);
  assert.equal(write[4].position[2], before.position[2]);
});
test('Space cannot start during an acknowledged save; a late save never leaves the player airborne', async t => {
  const gate = deferred(); const f = await fixture(t, { save: () => gate.promise });
  const page = f.mount(); await page.mount();
  page.instance.onKeyDown(event({ code: 'Space' })); f.step();
  const saved = page.instance.saveRegistration.flush(); await turn();
  page.instance.onKeyDown(event({ code: 'Space' })); clickWorld(page);
  assert.equal(f.frames.size, 0); assert.deepEqual(f.opens(), []);
  gate.resolve(); await saved;
  assert.equal(page.instance.camera.snapshotPlayer().grounded, true);
  assert.equal(page.instance.camera.snapshotPlayer().position[1], f.actors.get(MAIN)[0].geometry.position[1]);
});
test('HUD pins the boss plate top-center, vitals bottom-left and skills bottom-right, with Space listed in the left tip', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  // Mounted state so the whole HUD renders before its anchors are inspected.
  page.instance.gameplayState.value = { role: 'main', config: gameplayConfig,
    state: { revision: 0, rage: 40, boss: { hp: 200 }, drop: null, inventory: { worldFragment: 1 } } };
  page.instance.feedback.value = '获得 世界碎片 ×1'; page.instance.canPickup.value = true;
  page.instance.gameplayError.value = '保存失败，请重试';
  page.instance.bossNearby.value = true;
  const tree = renderStory(proxyRefs(page.instance), []);
  const bottom = findNode(tree, node => node.props?.class === 'story-bottom-stack');
  assert.deepEqual(bottom.children.filter(node => node.type !== vue.Comment).map(node => node.props?.class),
    ['gameplay-error', 'story-feedback']);
  const controls = findNode(tree, node => node.props?.class === 'story-controls tip');
  assert.match(JSON.stringify(controls, (key, value) => key === 'ctx' ? undefined : value), /Space/);
  const vitals = findNode(tree, node => node.props?.class === 'player-vitals vitals plate');
  const skills = findNode(tree, node => node.props?.class === 'skill-strip skills');
  const boss = findNode(tree, node => node.props?.class === 'boss-status plate');
  assert.ok(vitals && skills && boss, 'vitals, skills and the boss plate are independent HUD anchors');
  const declarations = selector => {
    const values = {};
    styles.walkRules(rule => { if (rule.parent.type === 'root' && rule.selectors.includes(selector))
      rule.walkDecls(d => { values[d.prop] = d.value; }); });
    return values;
  };
  assert.equal(declarations('.story-hud')['pointer-events'], 'none');
  // The notice stack owns the bottom-center lane only; vitals and skills anchor the corners.
  assert.equal(declarations('.story-bottom-stack')['pointer-events'], undefined);
  assert.match(declarations('.story-bottom-stack').bottom, /^calc\(/);
  assert.equal(declarations('.story-bottom-stack').position, 'absolute');
  assert.equal(declarations('.story-bottom-stack').left, '50%');
  assert.equal(declarations('.player-vitals').position, 'absolute');
  assert.equal(declarations('.player-vitals')['pointer-events'], 'auto');
  assert.match(declarations('.player-vitals').left, /^var\(--gap-edge\)$/);
  assert.match(declarations('.player-vitals').bottom, /^var\(--gap-edge\)$/);
  assert.equal(declarations('.skills').position, 'absolute');
  assert.equal(declarations('.skills')['pointer-events'], 'auto');
  assert.match(declarations('.skills').right, /^var\(--gap-edge\)$/);
  assert.match(declarations('.skills').bottom, /^var\(--gap-edge\)$/);
  assert.equal(declarations('.boss-status').position, 'absolute');
  assert.equal(declarations('.boss-status').top, 'var(--boss-top)');
  assert.equal(declarations('.tip').position, 'absolute');
  assert.equal(declarations('.story-controls')['display'], undefined);
  assert.equal(declarations('.tip span').display, 'flex');
  assert.equal(declarations('.tip').display, 'grid');
  assert.match(declarations('.tip').top, /^clamp\(/);
  assert.equal(declarations('.gameplay-error').position, undefined);
});


test('inventory arrows reach slots, close, locked tooltip and enabled world button; Tab/Esc close', async t => {
  const f = await fixture(t); const page = f.mount(); await page.mount();
  const node = label => ({ label, focus() { document.activeElement = this; } });
  const slots = Array.from({ length: 20 }, (_, i) => node(`slot-${i}`));
  const close = node('close'), hint = node('unlock-hint'), travel = node('travel');
  let locked = true;
  page.instance.inventoryPanel.value = {
    querySelectorAll: () => slots,
    querySelector: selector => selector === '[data-inventory-close]' ? close
      : selector === '[data-inventory-travel-focus]' ? hint : locked ? null : travel,
  };
  page.instance.toggleInventory(); await turn(); assert.equal(document.activeElement, close);
  const press = code => page.instance.onInventoryKey(event({ code }));
  press('ArrowDown'); assert.equal(document.activeElement, slots[0]);
  press('ArrowRight'); assert.equal(document.activeElement, slots[1]);
  press('ArrowDown'); assert.equal(document.activeElement, slots[6]);
  press('End'); assert.equal(document.activeElement, slots[19]);
  press('ArrowDown'); assert.equal(document.activeElement, hint);
  locked = false; press('ArrowUp'); assert.equal(document.activeElement, slots[19]);
  press('ArrowDown'); assert.equal(document.activeElement, travel);
  press('Home'); press('ArrowUp'); assert.equal(document.activeElement, close);
  page.instance.onKeyDown(event({ code: 'Tab' })); assert.equal(page.instance.inventoryOpen.value, false);
  page.instance.onKeyDown(event({ code: 'Tab' })); assert.equal(page.instance.inventoryOpen.value, true);
  page.instance.onKeyDown(event({ code: 'Escape' })); assert.equal(page.instance.inventoryOpen.value, false);
  assert.equal(f.route, '/'); assert.deepEqual(f.opens(), []);
});

test('the bag travel entry appears only after the world fragment is collected, then enters without a native open', async t => {
  // 小世界一览本来只有一条（主世界）；拾得碎片后才多出可出入的第二条。
  const state = { version: 2, revision: 0, rage: 20, boss: { hp: 20 }, drop: null, inventory: { worldFragment: 0 } };
  let pageInstance = null;
  const f = await fixture(t, { gameplay: async request => {
    if (request.action !== 'load') {
      state.revision += 1;
      if (request.action === 'pickupDrop') {
        state.drop.collected = true; state.inventory.worldFragment += 1;
      } else if (request.action === 'hitBoss' || request.hit) {
        state.boss.hp = Math.max(0, state.boss.hp - 100);
      }
      if (state.boss.hp === 0 && !state.drop) {
        // 红球落在玩家脚下，便于拾取
        const player = pageInstance?.instance.camera.snapshotPlayer().position || [0, 0, 0];
        state.drop = { id: 'story.boss.world-fragment', position: [player[0], 0, player[2]], collected: false };
      }
    }
    return { status: 'ok', role: 'main', config: gameplayConfig, state: structuredClone(state) };
  } });
  const page = f.mount(); pageInstance = page; await page.mount();
  const entry = () => findNode(renderStory(proxyRefs(page.instance), []),
    node => node.props?.['data-inventory-travel'] !== undefined);

  clickWorld(page); await turn();
  assert.equal(f.opens().length, 0, 'a living Boss cannot travel');
  assert.equal(entry(), null, 'no second world exists before the fragment is collected');

  // 走到 Boss 身前击败它，再拾起红色球（世界碎片）：一览里随即辟出第二界
  page.instance.inventoryOpen.value = false;
  page.instance.onKeyDown(event({ code: 'KeyW', key: 'w' }));
  for (let i = 0; i < 100 && page.instance.camera.snapshotPlayer().position[2] < 7.6; i++) f.step(50);
  page.instance.camera.keyUp(event({ code: 'KeyW', key: 'w' }));
  assert.ok(page.instance.camera.snapshotPlayer().position[2] >= 7.6, 'the player can reach the Boss');
  await page.instance.gameplay.attack();
  assert.equal(page.instance.gameplay.data.state.boss.hp, 0);
  await page.instance.gameplay.pickup();
  assert.equal(page.instance.gameplayState.value.state.inventory.worldFragment, 1);
  page.instance.inventoryOpen.value = true;
  const node = entry();
  assert.ok(node, 'the fragment opens a second small world');
  assert.equal(node.props.disabled, false);

  // 点它＝原来的「小世界」按钮：走既有换场景流程，并收起行囊
  await page.instance.bagTravel(1);
  await turn();
  assert.equal(page.instance.inventoryOpen.value, false);
  assert.equal(page.instance.gameplayError.value, '');
  assert.deepEqual(f.opens(), [CHILD]);
});

// 回归：F 的提示与 F 的动作必须永远一致。碎片只掉在主世界，先知只站在小世界，
// 所以两个世界各有一条 F；两条都必须「提示说什么，F 就做什么」。
test('the F prompt and the F key agree: near the pickup it picks up, near the prophet it talks', async t => {
  const state = { version: 2, revision: 0, rage: 20, boss: { hp: 0 },
    drop: { id: 'story.boss.world-fragment', position: [0, 0, 0], collected: false },
    inventory: { worldFragment: 0 } };
  const f = await fixture(t, { gameplay: async (request, activePath) => {
    if (request.action === 'pickupDrop') { state.drop.collected = true; state.inventory.worldFragment += 1; }
    return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
      config: gameplayConfig, state: structuredClone(state) };
  } });
  let page = f.mount(); await page.mount();

  // 主世界：碎片就在玩家脚下（距离 0 ≤ pickupRange 2），先知根本不在场。
  const p = () => page.instance;
  const hint = () => p().controlHints.value.find(([key]) => key === 'F')?.[1];
  p().updateProximity();
  assert.equal(p().fKeyAction.value.kind, 'pickup');
  assert.equal(hint(), '按 F 拾取');
  p().onKeyDown(event({ code: 'KeyF' }));
  await turn();
  assert.equal(p().gameplayState.value.state.inventory.worldFragment, 1, '提示说拾取，F 就必须拾取');
  assert.equal(p().dialogueOpen.value, false, '主世界没有先知可谈');

  // 小世界：碎片在主世界已经拾走，这里只可能谈先知。分两次进入同一份夹具：
  // 先知远在天边时 F 什么都不做，把它挪到玩家身边后提示与 F 一起变成交谈。
  const character = role => STORY_CHARACTERS.find(item => item.role === role);
  const childActor = role => f.actors.get(CHILD).find(item => item.actor_guid === character(role).guid);
  const prophetAt = [...childActor('prophet').geometry.position];
  clickWorld(page); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  assert.equal(p().fKeyAction.value.kind, null, '先知远在射程外，没有可执行的动作');
  assert.equal(hint(), undefined, '没有动作就没有 F 提示');
  p().onKeyDown(event({ code: 'KeyF' }));
  assert.equal(p().dialogueOpen.value, false, '够不着就不能交谈');

  // 让玩家站到先知面前：页面在挂载时把场景快照读进 prophetActor，所以摆位要在挂载前完成。
  childActor('player').geometry.position = [...prophetAt];
  page.unmount(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  assert.equal(p().fKeyAction.value.kind, 'prophet', '先知就在身上，裁决必须选它');
  assert.equal(hint(), 'F 与先知交谈');
  assert.ok(p().fKeyAction.value.distance <= 1, '先知确实在射程内');
  p().onKeyDown(event({ code: 'KeyF' }));
  assert.equal(p().dialogueOpen.value, true, '提示说交谈，F 就必须交谈');
  p().closeDialogue(); await turn();
  assert.equal(p().gameplayState.value.state.inventory.worldFragment, 1, '交谈不会顺手改动拾取进度');
});

// 回归（拾取失效）：F 的距离与射程必须和玩法模块自己那套逐字对齐。
// 上一条用例手写的 state 少了一整块盘上字段（operations / legacyRevision / inventory.block），
// 于是「页面的 state 是不是后端真的那份」从来没被验过：真存档多一个字段、少一个 position，
// 页面就会算出 Infinity 距离，提示不出现、F 静默什么都不做——玩家看到的就是「不能拾取物体」。
// 这里把 game/runtime/story_gameplay.py 的 initial_state() / CONFIG 原样取来当夹具，
// 再验同一条规则的两侧：距离用 state.drop.position，射程用 config.pickupRange。
function readPythonGameplay(t) {
  const python = process.env.CORONA_PYTHON || 'conda';
  const args = process.env.CORONA_PYTHON ? ['-c'] : ['run', '-n', 'coronaengine-dev', 'python', '-c'];
  try {
    const { execFileSync } = require('child_process');
    const output = execFileSync(python, [...args,
      'import json, sys; sys.path.insert(0, "."); '
      + 'from game.runtime import story_gameplay as m; '
      + "print(json.dumps({'config': m.CONFIG, 'state': m.initial_state()}))"],
    { encoding: 'utf8', cwd: new URL('../../..', import.meta.url) });
    return JSON.parse(output.trim().split(/\r?\n/).at(-1));
  } catch (error) {
    t.skip(`无法读取故事玩法的真实状态（需要一个可用的 Python 与 coronaengine-dev 环境）：${error.message}`);
    return null;
  }
}
test('the real save shape from story_gameplay.py picks up inside config.pickupRange and refuses outside it', async t => {
  const { config: realConfig, state: realState } = readPythonGameplay(t);
  if (!realConfig) return;
  // 盘上的初始存档形状：这些字段一个都不能少，否则页面拿到的不是后端真的那份 state。
  assert.deepEqual(Object.keys(realState).sort(),
    ['boss', 'drop', 'inventory', 'legacyRevision', 'operations', 'rage', 'revision', 'version'],
    '夹具必须就是 story_gameplay.initial_state() 的真实字段');
  assert.equal(realConfig.pickupRange, 2, '射程来自后端的 CONFIG，不是前端自己写的数');

  // 真存档的红球：position 是 [x, y, z]，收集标记是 collected；用后端自己的射程把它放在边界内。
  const state = structuredClone(realState);
  const range = realConfig.pickupRange;
  state.boss.hp = 0;
  state.drop = { id: 'story.boss.world-fragment', position: [range - 1, 0, 0], collected: false };
  const f = await fixture(t, { gameplay: async (request, activePath) => {
    if (request.action === 'pickupDrop') { state.drop.collected = true; state.inventory.worldFragment += 1; }
    return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
      config: realConfig, state: structuredClone(state) };
  } });
  const page = f.mount(); await page.mount(); await turn();
  const p = () => page.instance;
  const hint = () => p().controlHints.value.find(([key]) => key === 'F')?.[1];
  p().camera.snapshotPlayer().position = [0, 0, 0];
  p().updateProximity();

  assert.equal(p().fKeyAction.value.kind, 'pickup', '真实 state + 真实射程：边界内的红球必须可选');
  assert.equal(hint(), '按 F 拾取');
  p().onKeyDown(event({ code: 'KeyF' }));
  await turn();
  assert.equal(p().gameplayState.value.state.inventory.worldFragment, 1, '提示说拾取，F 就必须真的提交 pickupDrop');
  assert.equal(p().gameplayState.value.state.drop.collected, true);
});

// 反向：超出射程一样要有提示与动作都要消失（这正是页面算距离、算射程两件事同时错才会漏掉的边界）。
test('a drop outside the real pickupRange offers neither the prompt nor the F action', async t => {
  const { config: realConfig, state: realState } = readPythonGameplay(t);
  if (!realConfig) return;
  const state = structuredClone(realState);
  state.boss.hp = 0;
  state.drop = { id: 'story.boss.world-fragment', position: [realConfig.pickupRange + 1, 0, 0], collected: false };
  const f = await fixture(t, { gameplay: async (request, activePath) => ({ status: 'ok',
    role: activePath === MAIN ? 'main' : 'child', config: realConfig, state: structuredClone(state) }) });
  const page = f.mount(); await page.mount(); await turn();
  const p = () => page.instance;
  p().camera.snapshotPlayer().position = [0, 0, 0];
  p().updateProximity();

  assert.equal(p().fKeyAction.value.kind, null, '射程外的红球不是候选');
  assert.equal(p().controlHints.value.find(([key]) => key === 'F'), undefined, '没有动作就没有 F 提示');
  p().onKeyDown(event({ code: 'KeyF' }));
  await turn();
  assert.equal(p().gameplayState.value.state.inventory.worldFragment, 0, '够不着就不许拾取');
});

// 端到端：这就是玩家真实的拾取动作序列（与盘上 story_world_*\.game\story-gameplay.json 一致：
// Boss 死在 [0,0,12]，红球落在同一处，玩家站在 z≈11.6）。走到球上，提示必须变成拾取，F 必须真的拾起来。
test('walking onto the drop the dead boss left turns the F prompt into a real pickup', async t => {
  const { config: realConfig, state: realState } = readPythonGameplay(t);
  if (!realConfig) return;
  const bossPosition = [gameplayModule.FRAGMENT.x, 0, gameplayModule.FRAGMENT.z];
  const state = structuredClone(realState);
  const f = await fixture(t, { gameplay: async (request, activePath) => {
    if (request.action === 'hitBoss' || request.hit) {
      state.revision += 1;
      state.boss.hp = Math.max(0, state.boss.hp - realConfig.damage);
      if (state.boss.hp === 0) {
        state.drop = { id: 'story.boss.world-fragment', position: [...bossPosition], collected: false };
      }
    } else if (request.action === 'pickupDrop') {
      state.revision += 1;
      state.drop.collected = true; state.inventory.worldFragment += 1;
    }
    return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
      config: realConfig, state: structuredClone(state) };
  } });
  const page = f.mount(); await page.mount(); await turn();
  const p = () => page.instance;
  const hint = () => p().controlHints.value.find(([key]) => key === 'F')?.[1];

  // Boss 还活着：没有红球，就没有拾取这一行。
  assert.equal(hint(), undefined, 'Boss 未死时不该出现拾取提示');

  // 走到 Boss 面前把它打死：红球落在 Boss 倒下的位置。攻击受冷却限制，
  // 因此把玩法模块读的那个时钟（performance.now）接到本用例手里，而不是忙等。
  let clock = 0;
  t.mock.method(performance, 'now', () => clock);
  // 走到 Boss 面前（用真实的按键移动路径，而不是改一份快照副本）。
  p().onKeyDown(event({ code: 'KeyW', key: 'w' }));
  for (let i = 0; i < 200 && p().camera.snapshotPlayer().position[2] < gameplayModule.FRAGMENT.z; i++) f.step(50);
  p().camera.keyUp(event({ code: 'KeyW', key: 'w' }));
  assert.ok(p().camera.snapshotPlayer().position[2] >= gameplayModule.FRAGMENT.z, '玩家必须能走到 Boss 脚下');
  const swings = Math.ceil(realConfig.bossHp / realConfig.damage);
  for (let i = 0; i < swings; i++) { clock += realConfig.cooldownMs; await p().gameplay.attack(); await turn(); }
  assert.equal(state.boss.hp, 0, '打满次数后 Boss 必须倒下');
  assert.ok(state.drop && state.drop.collected === false, 'Boss 死后必须留下未拾取的红球');

  // 玩家就站在红球上：提示与 F 都必须是拾取。
  p().updateProximity();
  assert.equal(p().fKeyAction.value.kind, 'pickup', '站在红球上，F 的裁决必须是拾取');
  assert.equal(hint(), '按 F 拾取', '站在红球上必须给出拾取提示');
  p().onKeyDown(event({ code: 'KeyF' }));
  await turn();
  assert.equal(p().gameplayState.value.state.inventory.worldFragment, 1, '按 F 必须真的把红球捡起来');
  assert.equal(p().gameplayState.value.state.drop.collected, true);
});

// 回归（Bug 1）：小世界的陈列是盘上的权威数据，进入世界时必须读回来。它一度一份也没读回来
// （`load()` 里对兄弟方法的裸调用抛 ReferenceError，被空 catch 吞掉），于是玩家放下的方块全部
// 回到行囊：离开再回来，物品栏又显示 64。这里走完整的换场景流程断言 64 − 3 = 61。
test('leaving and re-entering the small world shows the saved block count, not the seed again', async t => {
  const placements = { version: 1, placements: [0, 1, 2].map(index => ({ propId: 'block', index,
    siteId: null, position: [index, 0, 0], rotation: [0, 0, 0], scale: 1 })) };
  const f = await fixture(t, {
    documents: { loadPlacements: placements },
    gameplay: async (request, activePath) => ({ status: 'ok',
      role: activePath === MAIN ? 'main' : 'child', config: gameplayConfig,
      state: { version: 2, revision: 0, rage: 0, boss: { hp: 0 }, drop: null,
        inventory: { worldFragment: 1, block: 64 } } }),
  });
  let page = f.mount(); await page.mount(); await turn();
  const blockCount = () => page.instance.hotbarSlots.value[0];
  const countText = () => {
    const texts = [];
    const walk = node => {
      if (!node || typeof node !== 'object') return;
      if (node.props?.class === 'hotbar__count') texts.push(node.children);
      for (const child of Array.isArray(node.children) ? node.children : []) walk(child);
    };
    walk(renderStory(proxyRefs(page.instance), []));
    return texts;
  };

  // 主世界里陈列是空的（主世界只显示空布局），进小世界才读得回来。
  clickWorld(page); await turn(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  assert.deepEqual(page.instance.placements.value.map(entry => entry.propId), ['block', 'block', 'block']);
  assert.deepEqual(blockCount(), { slot: 0, id: 'block', name: '方块',
    description: '主世界带回的方块，可直接在小世界中摆放。',
    owned: 64, placed: 3, available: 61, empty: false });
  assert.deepEqual(countText(), ['61'], '物品栏上那个数字必须就是 61');

  // 回到主世界，再进一次：同一份盘上布局，数量不许回到 64。
  clickWorld(page); await turn(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  clickWorld(page); await turn(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  assert.deepEqual(f.opens(), [CHILD, MAIN, CHILD]);
  assert.equal(page.instance.hotbarSlots.value[0].placed, 3);
  assert.equal(page.instance.hotbarSlots.value[0].available, 61);
  assert.deepEqual(countText(), ['61']);
});

// 回归（小世界里无法取回方块）：小世界没有红球可用，唯一能被 F 拿回来的东西就是玩家自己
// 放下的方块——取回就是摆放的逆操作。这里走完整的玩家动作序列：进小世界、按 B 在身前放一块、
// 提示变成「按 F 取回方块」、按 F 之后布局少一项、物品栏的可用数回到摆放前，而且场景里的 actor
// 是由既有的陈列 reconcile 路径退场的（没有第二条撤下路径）。
test('the small world takes a placed block back: the 取回 prompt, F removes it, and the count returns', async t => {
  let layout = { version: 1, placements: [] };
  const saved = [];
  const state = { version: 2, revision: 0, rage: 0, boss: { hp: 0 }, drop: null,
    inventory: { worldFragment: 1, block: 4 } };
  const f = await fixture(t, {
    documents: { loadPlacements: layout },
    gameplay: async (request, activePath) => {
      if (request.action === 'savePlacements') {
        saved.push(structuredClone(request.placements));
        layout = { version: 1, placements: structuredClone(request.placements) };
        return { status: 'ok', role: 'child', state: structuredClone(layout) };
      }
      return { status: 'ok', role: activePath === MAIN ? 'main' : 'child',
        config: gameplayConfig, state: structuredClone(state) };
    },
  });
  let page = f.mount(); await page.mount(); await turn();
  const p = () => page.instance;
  const hint = () => p().controlHints.value.find(([key]) => key === 'F')?.[1];
  const available = () => p().hotbarSlots.value[0].available;

  // 主世界：读到的是空布局，那里没有可摆放的陈列物，也就没有取回这一行。
  assert.deepEqual(p().placements.value, []);
  assert.equal(hint(), undefined, '主世界没有陈列物，F 就没有取回');
  assert.equal(available(), 4);

  // 进小世界：布局还是盘上那一份（空）。
  clickWorld(page); await turn(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();
  assert.equal(p().roleRef.value, 'child');
  assert.deepEqual(p().placements.value, []);
  assert.equal(available(), 4);
  assert.equal(hint(), undefined, '身边什么都没有时没有 F 提示');

  // 按 B 在身前 2 米放下一个方块：玩家站着不动，它就在取回的射程里。
  p().onKeyDown(event({ code: 'KeyB', key: 'b' }));
  await turn(); await turn(); await turn();
  assert.equal(p().gameplayError.value, '', '摆放不能报错');
  assert.deepEqual(p().placements.value.map(entry => entry.propId), ['block']);
  assert.deepEqual(saved.at(-1).map(entry => entry.propId), ['block'], '布局必须先落盘');
  assert.equal(available(), 3, '放下一个方块，可用数就该少一');
  const guid = storyPropsModule.placementGuid(p().placements.value[0].index);
  assert.ok(f.actors.get(CHILD).some(actor => actor.actor_guid === guid), '方块必须真的进了场景');

  // 站在方块旁边：F 的裁决与那一行提示一起变成取回。
  p().updateProximity();
  assert.equal(p().fKeyAction.value.kind, 'block', '身边自己放下的方块必须是 F 的目标');
  assert.ok(p().fKeyAction.value.distance <= storyPropsModule.PLACED_BLOCK_REACH, '方块确实在射程内');
  assert.equal(hint(), '按 F 取回方块');

  // 按 F：布局少一项、可用数回到 4、场景里的 actor 由既有陈列路径退场。
  p().onKeyDown(event({ code: 'KeyF' }));
  await turn(); await turn(); await turn();
  assert.equal(p().gameplayError.value, '', '取回不能报错');
  assert.deepEqual(p().placements.value, []);
  assert.deepEqual(saved.at(-1), [], '取回必须把「少了一件」的布局存回去');
  assert.equal(available(), 4, '取回之后可用数必须回到摆放前的数字');
  assert.equal(f.calls.filter(call => call[0] === 'remove' && call[3] === guid).length, 1,
    '撤下走的是 syncPlacementActors 的既有路径');
  assert.ok(!f.actors.get(CHILD).some(actor => actor.actor_guid === guid), '方块必须从场景里消失');
  assert.equal(p().fKeyAction.value.kind, null, '方块没了，取回的裁决也随之消失');
  assert.equal(hint(), undefined, '没有目标就没有 F 提示');
  assert.equal(p().gameplayState.value.state.inventory.block, 4, '取回不动盘上的持有数');
  assert.equal(available(), p().hotbarSlots.value[0].owned, '手里的方块又全都能用了');
});

// 回归（Bug 2）：碎片规则是盘上的数据。它一度在进入世界时一份也没读回来，于是碎片显示未装填、
// 「调整」子屏只回一句「先装填该碎片再调整」，按 1-4 一个字节都不写盘。这里断言规则随世界回来、
// 按 1 后新数字既落盘又真的交给了规则引擎（而不是「改了但看不出来」）。
test('a saved fragment rule comes back with the world, and 1 in 调整 reaches the sway runner', async t => {
  let rules = { version: 1, rules: [{ fragmentId: 'sway', type: 'sway', axis: 'x', amplitude: 0.25, periodMs: 2400 }] };
  const saved = [];
  const f = await fixture(t, {
    documents: { loadWorldRules: rules },
    gameplay: async (request, activePath) => {
      if (request.action === 'saveWorldRules') {
        saved.push(structuredClone(request.rules));
        rules = { version: 1, rules: structuredClone(request.rules) };
        return { status: 'ok', role: 'child', state: structuredClone(rules) };
      }
      return { status: 'ok', role: activePath === MAIN ? 'main' : 'child', config: gameplayConfig,
        state: { version: 2, revision: 0, rage: 0, boss: { hp: 0 }, drop: null,
          inventory: { worldFragment: 1, block: 64 } } };
    },
  });
  let page = f.mount(); await page.mount(); await turn();
  clickWorld(page); await turn(); await turn();
  page = f.mount(); await page.mount(); await turn(); await turn();

  assert.deepEqual(page.instance.installedRules.value.map(rule => [rule.amplitude, rule.periodMs]),
    [[0.25, 2400]], '已装填的碎片必须随世界回来');
  assert.equal(page.instance.worldRuleRunner.isRunning(), true, '规则引擎按保存的数字运行');
  // 「碎片」屏上的「调整」行：子屏必须认出这块碎片已装填，并显示盘上的数字（而不是退回目录默认值）。
  page.instance.dialogueOpen.value = true;
  page.instance.openFragmentAdjust(page.instance.fragmentList.value[0]);
  assert.equal(page.instance.prophetScreen.value, 'fragment-adjust');
  assert.equal(page.instance.fragmentAdjust.value.installed, true);
  assert.match(page.instance.fragmentAdjust.value.amplitudeLabel, /0\.25/);

  // 「调整」子屏上按 1：先落盘，再把新数字交给正在运行的规则引擎。
  const captured = [];
  const runner = page.instance.worldRuleRunner;
  const original = runner.setRules;
  runner.setRules = list => { captured.push(structuredClone(list)); return original(list); };
  page.instance.onKeyDown(event({ code: 'Digit1', key: '1' }));
  await turn(); await turn();
  assert.deepEqual(saved, [[{ fragmentId: 'sway', type: 'sway', axis: 'x', amplitude: 0.3, periodMs: 2400 }]],
    '幅度 0.25 + 0.05 必须落盘');
  assert.deepEqual(captured.at(-1), [{ type: 'sway', axis: 'x', amplitude: 0.3, periodMs: 2400,
    excludeRoles: ['player'] }], '规则引擎收到的是新幅度');
  assert.match(page.instance.actionFeedback.value, /0\.30/);
  assert.equal(page.instance.worldRuleRunner.isRunning(), true);
});
