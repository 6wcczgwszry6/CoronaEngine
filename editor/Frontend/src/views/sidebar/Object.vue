<template>
  <div class="object-panel-shell flex flex-col flex-1 min-h-0 h-full w-full rounded-lg overflow-hidden relative">
    <DockTitleBar
      v-if="!isDocked"
      title="对象"
      extraClass="bg-[#84A65B] rounded-t-md text-sm"
      routePath="/Object"
      @close="closeFloat"
    />

    <div v-if="loading" class="object-empty">正在读取对象属性…</div>
    <div v-else-if="!selectedActorName" class="object-empty">
      <strong>还没有选中对象</strong>
      <span>在 3D 视口或场景管理中选择一个模型后，这里会显示可调整的属性。</span>
    </div>

    <div v-else class="object-scroll">
      <header class="object-heading">
        <div>
          <span class="object-type">{{ actor.type || 'model' }}</span>
          <h2>{{ actor.name }}</h2>
        </div>
        <button type="button" class="save-button" :disabled="saving" @click="saveActor">
          {{ saving ? '保存中…' : '保存对象' }}
        </button>
      </header>

      <section class="property-section" data-assistant-title="对象名称" data-assistant-description="修改后可用新的对象名称在节点积木中准确引用这个模型。">
        <div class="section-title">模型</div>
        <div class="property-row">
          <label for="actor-alias">名称</label>
          <input id="actor-alias" v-model="aliasDraft" type="text" :disabled="aliasSaving" @keydown.enter.prevent="commitAlias" @keydown.esc.prevent="resetAlias" />
          <button type="button" class="inline-button" :disabled="!aliasDirty || aliasSaving" @click="commitAlias">应用</button>
        </div>
        <p v-if="aliasError" class="property-error">{{ aliasError }}</p>

        <div class="property-row">
          <label>渲染空间</label>
          <div class="segmented">
            <button type="button" :class="{ active: !actor.followCamera }" @click="setRenderSpace(false)">场景</button>
            <button type="button" :class="{ active: actor.followCamera }" @click="setRenderSpace(true)">屏幕 UI</button>
          </div>
        </div>

        <div class="property-row property-row-wide">
          <label>模型资源</label>
          <input :value="actor.modelPath" type="text" readonly placeholder="未设置模型资源" />
          <button type="button" class="inline-button" @click="selectModelFile">浏览</button>
        </div>
      </section>

      <section class="property-section" data-assistant-title="对象变换" data-assistant-description="修改模型在场景中的位置、旋转和大小。">
        <div class="section-title">变换</div>
        <div v-for="group in transformGroups" :key="group.key" class="vector-group">
          <span>{{ group.label }}</span>
          <label v-for="axis in axes" :key="axis" :class="`axis-${axis}`">
            <b>{{ axis.toUpperCase() }}</b>
            <input
              v-model.number="actor.transform[group.key][axis]"
              type="number"
              :step="group.step"
              :data-assistant-title="`${group.label} ${axis.toUpperCase()}`"
              @input="scheduleTransform(group.operation)"
              @change="applyTransform(group.operation)"
            />
          </label>
        </div>
      </section>

      <section class="property-section" data-assistant-title="摄像机跟随" data-assistant-description="启用后模型会按照偏移值跟随编辑器或游戏摄像机。">
        <div class="section-title section-title-row">
          <span>摄像机跟随</span>
          <label class="switch-label"><input v-model="actor.cameraLock.enabled" type="checkbox" @change="updateCameraLock" />启用</label>
        </div>
        <div v-if="actor.cameraLock.enabled" class="vector-group">
          <span>位置偏移</span>
          <label v-for="axis in axes" :key="axis" :class="`axis-${axis}`">
            <b>{{ axis.toUpperCase() }}</b>
            <input v-model.number="actor.cameraLock.position[axis]" type="number" step="0.1" @change="updateCameraLockOffset" />
          </label>
        </div>
      </section>

      <section class="property-section" data-assistant-title="碰撞设置" data-assistant-description="选择模型参与碰撞检测时使用的形状。">
        <div class="section-title">碰撞</div>
        <div class="property-row">
          <label for="actor-collision">碰撞形状</label>
          <select id="actor-collision" v-model="actor.collision" @change="updateCollision">
            <option value="none">无</option>
            <option value="box">包围盒</option>
            <option value="mesh">模型网格</option>
          </select>
        </div>
      </section>

      <section class="property-section" data-assistant-title="物理设置" data-assistant-description="控制模型是否参与物理模拟，以及质量、弹性、阻尼和轴向锁定。">
        <div class="section-title section-title-row">
          <span>物理</span>
          <label class="switch-label"><input v-model="actor.mechanics.physicsEnabled" type="checkbox" @change="updateMechanic('SetPhysicsEnabled', actor.mechanics.physicsEnabled)" />启用</label>
        </div>
        <div class="physics-grid" :class="{ disabled: !actor.mechanics.physicsEnabled }">
          <label>质量<input v-model.number="actor.mechanics.mass" type="number" min="0" step="0.1" :disabled="!actor.mechanics.physicsEnabled" @change="updateMechanic('SetMass', actor.mechanics.mass)" /></label>
          <label>弹性<input v-model.number="actor.mechanics.restitution" type="number" min="0" max="1" step="0.05" :disabled="!actor.mechanics.physicsEnabled" @change="updateMechanic('SetRestitution', actor.mechanics.restitution)" /></label>
          <label>阻尼<input v-model.number="actor.mechanics.damping" type="number" min="0" max="1" step="0.01" :disabled="!actor.mechanics.physicsEnabled" @change="updateMechanic('SetDamping', actor.mechanics.damping)" /></label>
        </div>
        <div class="lock-row">
          <span>锁定移动</span>
          <label v-for="(axis, index) in axes" :key="axis"><input v-model="actor.mechanics.linearLock[index]" type="checkbox" @change="updateLocks('SetLinearLock', actor.mechanics.linearLock)" />{{ axis.toUpperCase() }}</label>
        </div>
        <div class="lock-row">
          <span>锁定旋转</span>
          <label v-for="(axis, index) in axes" :key="axis"><input v-model="actor.mechanics.angularLock[index]" type="checkbox" @change="updateLocks('SetAngularLock', actor.mechanics.angularLock)" />{{ axis.toUpperCase() }}</label>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';
import { useDockPanel } from '@/composables/useDockPanel.js';
import { useErrorHandler } from '@/composables/useErrorHandler.js';
import { editorApi, sceneService } from '@/utils/bridge.js';
import { DEFAULT_SCENE_NAME } from '@/utils/constants.js';
import { getActorContext } from '@/blockly/composables/useActorContext.js';

const { closePanel, isDocked } = useDockPanel();
const { error: logError } = useErrorHandler('Object');
const axes = ['x', 'y', 'z'];
const transformGroups = [
  { key: 'position', label: '位置', operation: 'SetPosition', operationCode: 0, step: 0.1 },
  { key: 'rotation', label: '旋转', operation: 'SetRotation', operationCode: 1, step: 1 },
  { key: 'scale', label: '缩放', operation: 'SetScale', operationCode: 2, step: 0.05 },
];
const transformOperationCodes = Object.fromEntries(
  transformGroups.map((group) => [group.operation, group.operationCode])
);

const selectedSceneName = ref(DEFAULT_SCENE_NAME);
const selectedActorName = ref('');
const loading = ref(false);
const saving = ref(false);
const aliasDraft = ref('');
const aliasSaving = ref(false);
const aliasError = ref('');
let selectionToken = null;
let transformToken = null;
let loadSequence = 0;
const updateTimers = new Map();
const pendingTransformUpdates = new Map();
let transformFrameId = null;
let transformBridgeWarningShown = false;

const actor = reactive({
  name: '',
  type: '',
  handle: 0,
  modelPath: '',
  followCamera: false,
  transform: {
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: { x: 1, y: 1, z: 1 },
  },
  collision: 'none',
  mechanics: {
    physicsEnabled: true,
    mass: 1,
    restitution: 0.8,
    damping: 0.99,
    linearLock: [false, false, false],
    angularLock: [false, false, false],
  },
  cameraLock: {
    enabled: false,
    position: { x: 0, y: 0, z: 2 },
  },
});

const unwrap = (value) => value?.data ?? value ?? {};
const aliasDirty = computed(() => aliasDraft.value.trim() !== actor.name);
const numberAt = (value, index, fallback) => Number(value?.[index] ?? fallback);
const normalizeCollision = (value) => {
  const candidate = value?.type ?? value;
  return ['none', 'box', 'mesh'].includes(candidate) ? candidate : (candidate === false ? 'none' : 'box');
};
const readFollowCamera = (data) => data?.render_space === 'ui' || data?.follow_camera === true || data?.follow_camera === 1 || data?.follow_camera === 'true' || data?.follow_camera === '1';

function assignVector(target, value, fallback) {
  target.x = numberAt(value, 0, fallback.x);
  target.y = numberAt(value, 1, fallback.y);
  target.z = numberAt(value, 2, fallback.z);
}

async function loadActor(sceneName, actorName) {
  if (!sceneName || !actorName) return;
  const sequence = ++loadSequence;
  loading.value = true;
  selectedSceneName.value = sceneName;
  selectedActorName.value = actorName;
  try {
    const data = unwrap(await sceneService.getActor(sceneName, actorName));
    if (sequence !== loadSequence || selectedActorName.value !== actorName) return;
    if (!data || data.status === 'error') throw new Error(data?.message || '无法读取对象属性');
    actor.name = String(data.name || actorName);
    actor.type = String(data.actor_type || data.type || 'model');
    actor.handle = Number(data.handle || 0);
    actor.modelPath = String(data.model || data.path || data.file || '');
    actor.followCamera = readFollowCamera(data);
    const geometry = data.geometry || {};
    assignVector(actor.transform.position, geometry.position, { x: 0, y: 0, z: 0 });
    assignVector(actor.transform.rotation, geometry.rotation, { x: 0, y: 0, z: 0 });
    assignVector(actor.transform.scale, geometry.scale, { x: 1, y: 1, z: 1 });
    actor.collision = normalizeCollision(data.collision);
    const mechanics = data.mechanics || {};
    actor.mechanics.physicsEnabled = mechanics.physics_enabled !== false;
    actor.mechanics.mass = Number(mechanics.mass ?? 1);
    actor.mechanics.restitution = Number(mechanics.restitution ?? 0.8);
    actor.mechanics.damping = Number(mechanics.damping ?? 0.99);
    actor.mechanics.linearLock = axes.map((_, index) => Boolean(mechanics.linear_lock?.[index]));
    actor.mechanics.angularLock = axes.map((_, index) => Boolean(mechanics.angular_lock?.[index]));
    const cameraLock = data.camera_lock || {};
    actor.cameraLock.enabled = Boolean(cameraLock.lock_to_camera);
    assignVector(actor.cameraLock.position, cameraLock.position_offset, { x: 0, y: 0, z: 2 });
    aliasDraft.value = actor.name;
    aliasError.value = '';
  } catch (error) {
    if (sequence === loadSequence) logError('加载对象数据失败', error);
  } finally {
    if (sequence === loadSequence) loading.value = false;
  }
}

function resetAlias() {
  aliasDraft.value = actor.name;
  aliasError.value = '';
}

async function commitAlias() {
  const nextName = aliasDraft.value.trim();
  const currentName = selectedActorName.value;
  if (!nextName || !currentName || aliasSaving.value) {
    if (!nextName) aliasError.value = '名称不能为空';
    return;
  }
  if (nextName === actor.name) return resetAlias();
  aliasSaving.value = true;
  aliasError.value = '';
  try {
    const result = unwrap(await sceneService.renameActor(selectedSceneName.value, currentName, nextName));
    if (result?.status === 'error') throw new Error(result.message || '修改名称失败');
    const savedName = String(result?.actor?.name || result?.new_name || nextName);
    selectedActorName.value = savedName;
    actor.name = savedName;
    aliasDraft.value = savedName;
  } catch (error) {
    aliasError.value = error?.message || '修改名称失败';
    aliasDraft.value = actor.name;
    logError('修改对象名称失败', error);
  } finally {
    aliasSaving.value = false;
  }
}

function vectorFor(operation) {
  const key = operation === 'SetPosition' ? 'position' : operation === 'SetRotation' ? 'rotation' : 'scale';
  const value = actor.transform[key];
  return [Number(value.x) || 0, Number(value.y) || 0, Number(value.z) || 0];
}

function schedule(key, callback, delay = 120) {
  clearTimeout(updateTimers.get(key));
  updateTimers.set(key, window.setTimeout(() => {
    updateTimers.delete(key);
    callback();
  }, delay));
}

function flushTransformUpdates() {
  transformFrameId = null;
  const bridge = window.coronaBridge;
  if (!bridge || typeof bridge.actorTransform !== 'function') {
    pendingTransformUpdates.clear();
    if (!transformBridgeWarningShown) {
      transformBridgeWarningShown = true;
      logError('更新对象变换失败', new Error('coronaBridge.actorTransform 不可用'));
    }
    return;
  }

  for (const update of pendingTransformUpdates.values()) {
    try {
      bridge.actorTransform(update.handle, update.operationCode, update.vector);
    } catch (error) {
      logError('更新对象变换失败', error);
    }
  }
  pendingTransformUpdates.clear();
}

function scheduleTransform(operation) {
  const operationCode = transformOperationCodes[operation];
  if (!selectedActorName.value || !actor.handle || operationCode === undefined) return;
  pendingTransformUpdates.set(operation, {
    handle: actor.handle,
    operationCode,
    vector: vectorFor(operation),
  });
  if (transformFrameId === null) {
    transformFrameId = window.requestAnimationFrame(flushTransformUpdates);
  }
}

async function applyTransform(operation) {
  if (!selectedActorName.value) return;
  scheduleTransform(operation);
  clearTimeout(updateTimers.get(`save:${operation}`));
  updateTimers.delete(`save:${operation}`);
  schedule(`save:${operation}`, async () => {
    try {
      await sceneService.saveActor(selectedSceneName.value, selectedActorName.value);
    } catch (error) {
      logError('保存对象变换失败', error);
    }
  }, 180);
}

async function setRenderSpace(enabled) {
  if (!selectedActorName.value || actor.followCamera === enabled) return;
  const previous = actor.followCamera;
  actor.followCamera = enabled;
  try {
    await sceneService.actorOperation(selectedSceneName.value, selectedActorName.value, 'SetFollowCamera', [Boolean(enabled)]);
    if (enabled) actor.mechanics.physicsEnabled = false;
  } catch (error) {
    actor.followCamera = previous;
    logError('更新对象渲染空间失败', error);
  }
}

async function selectModelFile() {
  if (!selectedActorName.value) return;
  try {
    const raw = await sceneService.selectModelFileDialog(selectedSceneName.value, selectedActorName.value, 'model');
    const payload = unwrap(raw);
    const path = typeof payload === 'string' ? payload : payload?.path || payload?.data || '';
    if (path) actor.modelPath = String(path);
  } catch (error) {
    logError('选择模型资源失败', error);
  }
}

async function updateCollision() {
  try {
    await sceneService.actorOperation(selectedSceneName.value, selectedActorName.value, 'SetCollision', [actor.collision]);
  } catch (error) {
    logError('更新对象碰撞失败', error);
  }
}

async function updateMechanic(operation, value) {
  if (!selectedActorName.value) return;
  try {
    await sceneService.actorOperation(selectedSceneName.value, selectedActorName.value, operation, [value]);
  } catch (error) {
    logError('更新对象物理属性失败', error);
  }
}

async function updateLocks(operation, values) {
  if (!selectedActorName.value) return;
  try {
    await sceneService.actorOperation(
      selectedSceneName.value,
      selectedActorName.value,
      operation,
      values.map((value) => value ? 1 : 0)
    );
  } catch (error) {
    logError('更新对象轴锁失败', error);
  }
}

async function updateCameraLock() {
  try {
    await sceneService.setCameraLock(selectedSceneName.value, selectedActorName.value, actor.cameraLock.enabled);
  } catch (error) {
    logError('更新摄像机跟随失败', error);
  }
}

async function updateCameraLockOffset() {
  const value = actor.cameraLock.position;
  try {
    await sceneService.setCameraLockOffset(selectedSceneName.value, selectedActorName.value, [Number(value.x) || 0, Number(value.y) || 0, Number(value.z) || 0]);
  } catch (error) {
    logError('更新摄像机偏移失败', error);
  }
}

async function saveActor() {
  if (!selectedActorName.value || saving.value) return;
  saving.value = true;
  try {
    await sceneService.saveActor(selectedSceneName.value, selectedActorName.value);
  } catch (error) {
    logError('保存对象失败', error);
  } finally {
    saving.value = false;
  }
}

function handleSelection(payload = {}) {
  const type = String(payload.actor_type || payload.type || '');
  const sceneName = String(payload.scene || selectedSceneName.value || DEFAULT_SCENE_NAME);
  const actorName = String(payload.actor || '');
  if (type === 'scene' || !actorName) {
    selectedSceneName.value = sceneName;
    selectedActorName.value = '';
    actor.name = '';
    aliasDraft.value = '';
    return;
  }
  loadActor(sceneName, actorName);
}

function handleTransform(payload = {}) {
  if (!selectedActorName.value || payload.actor !== selectedActorName.value || payload.scene !== selectedSceneName.value) return;
  assignVector(actor.transform.position, payload.position, actor.transform.position);
  assignVector(actor.transform.rotation, payload.rotation, actor.transform.rotation);
  assignVector(actor.transform.scale, payload.scale, actor.transform.scale);
}

function closeFloat() {
  closePanel();
}

onMounted(async () => {
  // Actor selection is stored before this panel opens. Read it without invoking
  // MainView.on_init, which would reinitialize the scene and main camera.
  const actorContext = getActorContext();
  selectedSceneName.value = actorContext.scene || DEFAULT_SCENE_NAME;
  if (actorContext.actor) {
    await loadActor(selectedSceneName.value, actorContext.actor);
  }
  selectionToken = await editorApi.events.onActorSelectionChanged(handleSelection);
  transformToken = await editorApi.events.onActorTransformUpdated(handleTransform);
});

onUnmounted(() => {
  loadSequence += 1;
  for (const timer of updateTimers.values()) clearTimeout(timer);
  updateTimers.clear();
  pendingTransformUpdates.clear();
  if (transformFrameId !== null) window.cancelAnimationFrame(transformFrameId);
  transformFrameId = null;
  if (selectionToken) editorApi.off(selectionToken).catch(() => {});
  if (transformToken) editorApi.off(transformToken).catch(() => {});
  selectionToken = null;
  transformToken = null;
});
</script>

<style scoped>
.object-panel-shell {
  color: #e5e7eb;
  background: rgba(40, 40, 40, 0.42);
  border: 1px solid rgba(58, 58, 58, 0.72);
}
.object-empty {
  display: flex;
  flex: 1;
  min-height: 180px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #9ca3af;
  text-align: center;
  font-size: 12px;
  line-height: 1.65;
  background: rgba(40, 40, 40, 0.24);
}
.object-empty strong { color: #e5e7eb; font-size: 14px; }
.object-scroll { min-height: 0; flex: 1; overflow-y: auto; padding: 10px; background: rgba(40, 40, 40, 0.24); }
.object-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; padding:10px 11px; border:1px solid #3a3a3a; border-radius:7px; background:#282828; }
.object-heading h2 { margin:2px 0 0; color:#f3f4f6; font-size:15px; overflow-wrap:anywhere; }
.object-type { color:#9fbd88; font-size:10px; text-transform:uppercase; }
.save-button,.inline-button { border:1px solid #4a4a4a; border-radius:5px; background:#343434; color:#e5e7eb; padding:5px 9px; font-size:11px; transition:background .15s ease,border-color .15s ease; }
.save-button:hover:not(:disabled),.inline-button:hover:not(:disabled) { border-color:#84A65B; background:#3d4938; color:#fff; }
.save-button { border-color:#789663; background:#6f8e55; color:#fff; }
.save-button:hover:not(:disabled) { background:#7c9d60; }
.save-button:disabled,.inline-button:disabled { opacity:.45; cursor:not-allowed; }
.property-section { margin-bottom:8px; padding:10px; border:1px solid #3a3a3a; border-radius:7px; background:#282828; }
.section-title { margin-bottom:8px; color:#d1d5db; font-size:12px; font-weight:700; }
.section-title-row { display:flex; align-items:center; justify-content:space-between; }
.property-row { display:grid; grid-template-columns:72px minmax(0,1fr) auto; align-items:center; gap:7px; margin-top:7px; }
.property-row-wide { grid-template-columns:72px minmax(0,1fr) auto; }
.property-row>label { color:#aeb4ad; font-size:11px; }
input[type='text'],input[type='number'],select { min-width:0; width:100%; border:1px solid #444; border-radius:4px; background:#1f1f1f; color:#e5e7eb; padding:5px 6px; font-size:11px; outline:none; }
input:focus,select:focus { border-color:#84A65B; box-shadow:0 0 0 1px rgba(132,166,91,.18); }
.property-error { margin:5px 0 0 79px; color:#ff9e91; font-size:10px; }
.segmented { display:flex; width:max-content; padding:2px; border:1px solid #3a3a3a; border-radius:5px; background:#1f1f1f; }
.segmented button { border-radius:4px; color:#9ca3af; padding:4px 8px; font-size:10px; }
.segmented button:hover { color:#f3f4f6; }
.segmented button.active { background:#526846; color:#fff; }
.vector-group { display:grid; grid-template-columns:58px repeat(3,minmax(0,1fr)); align-items:center; gap:5px; margin-top:7px; }
.vector-group>span { color:#aeb4ad; font-size:11px; }
.vector-group label { display:grid; grid-template-columns:12px minmax(0,1fr); align-items:center; gap:3px; }
.vector-group b { font-size:9px; }
.axis-x b { color:#f28b82; }.axis-y b { color:#8ab4f8; }.axis-z b { color:#81c995; }
.switch-label { display:flex; align-items:center; gap:5px; color:#c0c5bf; font-size:10px; }
.physics-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; }
.physics-grid label { color:#aeb4ad; font-size:10px; }
.physics-grid input { margin-top:3px; }
.physics-grid.disabled { opacity:.56; }
.lock-row { display:flex; align-items:center; gap:10px; margin-top:9px; color:#adb3ac; font-size:10px; }
.lock-row>span { min-width:64px; }
.lock-row label { display:flex; align-items:center; gap:3px; }
</style>
