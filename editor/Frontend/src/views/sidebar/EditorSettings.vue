<template>
  <main class="esc-panel">
    <DockTitleBar
      v-if="!isDocked"
      title="暂停菜单"
      extraClass="bg-[#242724]"
      routePath="/SetUp"
      @close="handleContinue"
    />

    <section class="esc-body" aria-labelledby="esc-menu-title">
      <header class="esc-header">
        <div>
          <p class="esc-kicker">ESC</p>
          <h2 id="esc-menu-title">暂停菜单</h2>
        </div>
        <span class="esc-state" :class="{ offline: !runtimeState.available }">
          {{ runtimeState.available ? runtimeState.sceneId || '编辑中' : '面板模式' }}
        </span>
      </header>

      <p v-if="statusMessage" class="status-line" :class="statusKind">
        {{ statusMessage }}
      </p>

      <section class="settings-section">
        <div class="section-heading">
          <h3>常用</h3>
        </div>
        <div class="button-grid four">
          <button class="action-button primary" type="button" @click="handleContinue">
            继续编辑
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('ProjectSettings', '/ProjectSettings')"
          >
            项目设置
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('AITalkBar', '/AITalkBar')"
          >
            AI 对话
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('LogTool', '/LogView')"
          >
            日志
          </button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-heading">
          <h3>工具面板</h3>
        </div>
        <div class="button-grid tools">
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('SceneTools', '/SceneBar')"
          >
            场景管理
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('SceneDatas', '/Object')"
          >
            详情
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('FileManager', '/FileManager')"
          >
            文件管理器
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('Network', '/Network')"
          >
            网络协作
          </button>
          <button
            class="action-button"
            type="button"
            @click="openPanelOrRoute('LightFieldCalibration', '/LightFieldCalibration')"
          >
            光场标定
          </button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-heading split">
          <h3>运行</h3>
          <span>{{ runtimeState.previewStatusText || '就绪' }}</span>
        </div>
        <div class="button-grid four">
          <button
            class="action-button"
            type="button"
            :disabled="startPreviewDisabled"
            @click="startPreview"
          >
            开始预览
          </button>
          <button
            class="action-button"
            type="button"
            :disabled="stopPreviewDisabled"
            @click="stopPreview"
          >
            结束预览
          </button>
          <button
            class="action-button"
            type="button"
            :disabled="runtimeActionDisabled"
            @click="runProject"
          >
            运行项目
          </button>
          <button
            class="action-button"
            type="button"
            :disabled="runtimeActionDisabled"
            @click="runCurrentScene"
          >
            运行当前场景
          </button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-heading split">
          <h3>渲染</h3>
          <span>{{ runtimeState.renderLabel }}</span>
        </div>
        <div class="button-grid render">
          <button
            v-for="mode in runtimeState.renderModes"
            :key="mode.value"
            class="action-button"
            :class="{ selected: mode.active }"
            type="button"
            :disabled="renderModeDisabled(mode)"
            @click="selectRenderMode(mode)"
          >
            {{ mode.label }}
          </button>
        </div>
      </section>

      <section class="settings-section">
        <div class="section-heading split">
          <h3>物理</h3>
          <button
            class="text-button"
            type="button"
            :disabled="runtimeActionDisabled"
            @click="refreshPhysics"
          >
            刷新
          </button>
        </div>
        <div class="physics-grid">
          <label class="field">
            <span>重力 X</span>
            <input
              v-model.number="physicsForm.gravityX"
              type="number"
              step="0.1"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
          <label class="field">
            <span>重力 Y</span>
            <input
              v-model.number="physicsForm.gravityY"
              type="number"
              step="0.1"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
          <label class="field">
            <span>重力 Z</span>
            <input
              v-model.number="physicsForm.gravityZ"
              type="number"
              step="0.1"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
          <label class="field">
            <span>地面高度</span>
            <input
              v-model.number="physicsForm.floorY"
              type="number"
              step="0.1"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
          <label class="field">
            <span>弹性</span>
            <input
              v-model.number="physicsForm.floorRestitution"
              type="number"
              min="0"
              max="1"
              step="0.05"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
          <label class="field">
            <span>固定步长</span>
            <input
              v-model.number="physicsForm.fixedDt"
              type="number"
              min="0.001"
              step="0.001"
              :disabled="runtimeActionDisabled"
              @input="markPhysicsDirty"
            />
          </label>
        </div>
        <button
          class="action-button apply-button"
          type="button"
          :disabled="runtimeActionDisabled"
          @click="applyPhysics"
        >
          应用物理参数
        </button>
      </section>

      <section class="settings-section leave-section">
        <div class="section-heading">
          <h3>离开</h3>
        </div>
        <div class="home-panel" :class="{ confirming: confirmHome }">
          <template v-if="confirmHome">
            <p>确定回到主页？</p>
            <div class="confirm-actions">
              <button class="small-button" type="button" @click="cancelHome">取消</button>
              <button class="small-button danger" type="button" @click="goHome">
                确认回主页
              </button>
            </div>
          </template>
          <button v-else class="home-button" type="button" @click="confirmHome = true">
            回到主页
          </button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDockStore } from '@/stores/dockStore.js';
import { useDockPanel } from '@/composables/useDockPanel.js';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';

const EDITOR_CONTROLS_KEY = '__coronaEditorControls';

const defaultPhysics = {
  gravityX: 0,
  gravityY: -9.8,
  gravityZ: 0,
  floorY: 0,
  floorRestitution: 0.6,
  fixedDt: 1 / 60,
};

const defaultRenderModes = [
  { value: 'native', backend: 'native', label: 'Native', active: true, disabled: false },
  {
    value: 'path_tracing',
    backend: 'vision',
    label: 'Vision Path Tracing',
    active: false,
    disabled: true,
  },
  { value: 'svgf', backend: 'vision', label: 'Vision SVGF', active: false, disabled: true },
  { value: 'ssat', backend: 'vision', label: 'Vision SSAT', active: false, disabled: true },
];

const router = useRouter();
const dockStore = useDockStore();
const { closePanel, isDocked } = useDockPanel();

const confirmHome = ref(false);
const statusMessage = ref('');
const statusKind = ref('info');
const busyAction = ref('');
const physicsDirty = ref(false);
const physicsForm = ref({ ...defaultPhysics });
const runtimeState = ref({
  available: false,
  sceneId: '',
  previewRunning: false,
  previewBusy: false,
  previewStatusText: '',
  visionAvailable: false,
  renderMode: 'native',
  renderLabel: 'Native',
  renderModes: defaultRenderModes,
  physics: { ...defaultPhysics },
});

let pollTimer = null;
let statusTimer = null;

const runtimeActionDisabled = computed(
  () => !runtimeState.value.available || Boolean(busyAction.value)
);
const startPreviewDisabled = computed(
  () =>
    runtimeActionDisabled.value ||
    runtimeState.value.previewBusy ||
    runtimeState.value.previewRunning
);
const stopPreviewDisabled = computed(
  () =>
    runtimeActionDisabled.value ||
    runtimeState.value.previewBusy ||
    !runtimeState.value.previewRunning
);

function getRuntimeControls() {
  if (typeof window === 'undefined') return null;
  return window[EDITOR_CONTROLS_KEY] || null;
}

function toNumber(value, fallback) {
  const next = Number(value);
  return Number.isFinite(next) ? next : fallback;
}

function normalizePhysics(physics = {}) {
  return {
    gravityX: toNumber(physics.gravityX, defaultPhysics.gravityX),
    gravityY: toNumber(physics.gravityY, defaultPhysics.gravityY),
    gravityZ: toNumber(physics.gravityZ, defaultPhysics.gravityZ),
    floorY: toNumber(physics.floorY, defaultPhysics.floorY),
    floorRestitution: toNumber(physics.floorRestitution, defaultPhysics.floorRestitution),
    fixedDt: Math.max(0.001, toNumber(physics.fixedDt, defaultPhysics.fixedDt)),
  };
}

function normalizeRenderModes(state = {}) {
  const reportedModes = Array.isArray(state.renderModes) ? state.renderModes : [];
  const activeMode = state.renderMode || 'native';
  return defaultRenderModes.map((fallback) => {
    const reported = reportedModes.find((mode) => mode.value === fallback.value) || {};
    const isVisionDisabled = fallback.backend === 'vision' && !state.visionAvailable;
    return {
      ...fallback,
      ...reported,
      active: reported.active ?? activeMode === fallback.value,
      disabled: Boolean(reported.disabled) || isVisionDisabled,
    };
  });
}

function normalizeState(state = {}) {
  const physics = normalizePhysics(state.physics);
  return {
    available: true,
    sceneId: state.sceneId || '',
    previewRunning: Boolean(state.previewRunning),
    previewBusy: Boolean(state.previewBusy),
    previewStatusText: state.previewStatusText || '',
    visionAvailable: Boolean(state.visionAvailable),
    renderMode: state.renderMode || 'native',
    renderLabel: state.renderLabel || 'Native',
    renderModes: normalizeRenderModes(state),
    physics,
  };
}

function syncPhysicsForm(physics) {
  physicsForm.value = { ...normalizePhysics(physics) };
  physicsDirty.value = false;
}

function setStatus(message, kind = 'info') {
  statusMessage.value = message;
  statusKind.value = kind;
  if (statusTimer) {
    clearTimeout(statusTimer);
  }
  statusTimer = window.setTimeout(() => {
    statusMessage.value = '';
    statusTimer = null;
  }, 3200);
}

function refreshRuntime({ syncPhysics = false } = {}) {
  const controls = getRuntimeControls();
  if (!controls || typeof controls.getState !== 'function') {
    runtimeState.value = {
      ...runtimeState.value,
      available: false,
      previewRunning: false,
      previewBusy: false,
      previewStatusText: '',
      renderModes: defaultRenderModes,
    };
    return;
  }

  try {
    const nextState = normalizeState(controls.getState());
    runtimeState.value = nextState;
    if (syncPhysics || !physicsDirty.value) {
      syncPhysicsForm(nextState.physics);
    }
  } catch (error) {
    console.error('刷新 ESC 运行状态失败', error);
    runtimeState.value = {
      ...runtimeState.value,
      available: false,
      previewRunning: false,
      previewBusy: false,
      previewStatusText: '',
      renderModes: defaultRenderModes,
    };
  }
}

async function runRuntimeAction(actionName, successMessage, ...args) {
  const controls = getRuntimeControls();
  if (!controls || typeof controls[actionName] !== 'function') {
    refreshRuntime();
    setStatus('当前没有主编辑器上下文', 'warn');
    return false;
  }

  busyAction.value = actionName;
  try {
    const result = await controls[actionName](...args);
    const succeeded = result !== false;
    refreshRuntime({ syncPhysics: actionName === 'applyPhysics' && succeeded });
    if (!succeeded) {
      setStatus('操作失败，请查看日志', 'error');
      return false;
    }
    setStatus(successMessage, 'success');
    return true;
  } catch (error) {
    console.error(`ESC 执行 ${actionName} 失败`, error);
    refreshRuntime();
    setStatus('操作失败，请查看日志', 'error');
    return false;
  } finally {
    busyAction.value = '';
  }
}

function markPhysicsDirty() {
  physicsDirty.value = true;
}

function renderModeDisabled(mode) {
  return runtimeActionDisabled.value || Boolean(mode.disabled);
}

function startPreview() {
  if (startPreviewDisabled.value) return;
  runRuntimeAction('startPreview', '已开始预览');
}

function stopPreview() {
  if (stopPreviewDisabled.value) return;
  runRuntimeAction('stopPreview', '已结束预览');
}

function runProject() {
  if (runtimeActionDisabled.value) return;
  runRuntimeAction('runProject', '已运行项目');
}

function runCurrentScene() {
  if (runtimeActionDisabled.value) return;
  runRuntimeAction('runCurrentScene', '已运行当前场景');
}

function selectRenderMode(mode) {
  if (renderModeDisabled(mode)) return;
  runRuntimeAction('selectRenderMode', `已切换到 ${mode.label}`, mode.value);
}

async function refreshPhysics() {
  const controls = getRuntimeControls();
  if (!controls || typeof controls.refreshPhysics !== 'function') {
    refreshRuntime();
    setStatus('当前没有主编辑器上下文', 'warn');
    return;
  }

  busyAction.value = 'refreshPhysics';
  try {
    const nextState = await controls.refreshPhysics();
    if (nextState === false) {
      refreshRuntime();
      setStatus('刷新失败，请查看日志', 'error');
      return;
    }
    runtimeState.value = normalizeState(nextState);
    syncPhysicsForm(runtimeState.value.physics);
    setStatus('已刷新物理参数', 'success');
  } catch (error) {
    console.error('刷新物理参数失败', error);
    setStatus('刷新失败，请查看日志', 'error');
  } finally {
    busyAction.value = '';
  }
}

async function applyPhysics() {
  if (runtimeActionDisabled.value) return;
  const applied = await runRuntimeAction('applyPhysics', '已应用物理参数', { ...physicsForm.value });
  if (applied) {
    physicsDirty.value = false;
  }
}

function handleContinue() {
  confirmHome.value = false;
  closePanel();

  if (!isDocked && !hasNativeDockCommand()) {
    router.push('/');
  }
}

function hasNativeDockCommand() {
  return Boolean(
    typeof window !== 'undefined' &&
      window.coronaBridge &&
      typeof window.coronaBridge.dockCommand === 'function'
  );
}

function openPanelOrRoute(panelId, routePath) {
  confirmHome.value = false;

  if (isDocked) {
    dockStore.openPanel(panelId);
    closePanel();
    return;
  }

  router.push(routePath);
}

function cancelHome() {
  confirmHome.value = false;
}

function goHome() {
  confirmHome.value = false;
  dockStore.closePanel('EditorSettings');
  router.push('/StartScreen');
}

onMounted(() => {
  refreshRuntime({ syncPhysics: true });
  pollTimer = window.setInterval(() => refreshRuntime(), 700);
});

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  if (statusTimer) {
    clearTimeout(statusTimer);
    statusTimer = null;
  }
});
</script>

<style scoped>
.esc-panel {
  --panel-bg: #151715;
  --panel-surface: #1c1f1c;
  --panel-surface-hover: #242924;
  --panel-border: #313731;
  --panel-border-strong: #4e5a4b;
  --text-main: #eef1eb;
  --text-muted: #9da79a;
  --accent: #8ca96f;
  --accent-strong: #a8c783;
  --danger: #c7826f;
  --danger-surface: #30201d;
  --warn: #d3aa68;

  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #1b1d1b 0%, var(--panel-bg) 100%);
  color: var(--text-main);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  -webkit-font-smoothing: antialiased;
}

.esc-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(140, 169, 111, 0.42) transparent;
}

.esc-header,
.section-heading,
.section-heading.split,
.confirm-actions {
  display: flex;
  align-items: center;
}

.esc-header {
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--panel-border);
}

.esc-kicker {
  margin: 0 0 4px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.esc-header h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
}

.esc-state {
  max-width: 48%;
  padding: 5px 9px;
  border: 1px solid rgba(140, 169, 111, 0.42);
  border-radius: 6px;
  overflow: hidden;
  color: var(--accent-strong);
  background: rgba(140, 169, 111, 0.08);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.esc-state.offline {
  color: var(--warn);
  border-color: rgba(211, 170, 104, 0.42);
  background: rgba(211, 170, 104, 0.08);
}

.status-line {
  margin: 0;
  min-height: 28px;
  padding: 6px 9px;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  color: var(--text-main);
  background: rgba(28, 31, 28, 0.86);
  font-size: 12px;
  line-height: 1.35;
}

.status-line.success {
  color: var(--accent-strong);
  border-color: rgba(140, 169, 111, 0.45);
}

.status-line.warn {
  color: var(--warn);
  border-color: rgba(211, 170, 104, 0.45);
}

.status-line.error {
  color: #e2afa3;
  border-color: rgba(199, 130, 111, 0.5);
}

.settings-section {
  display: grid;
  gap: 9px;
  padding: 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: rgba(28, 31, 28, 0.66);
}

.section-heading {
  justify-content: space-between;
  min-height: 20px;
  gap: 10px;
}

.section-heading h3 {
  margin: 0;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.2;
}

.section-heading span {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.button-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.button-grid.four,
.button-grid.tools {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.button-grid.render {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.action-button,
.home-button,
.small-button,
.text-button {
  border: 1px solid var(--panel-border);
  border-radius: 7px;
  font: inherit;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    transform 160ms ease,
    box-shadow 160ms ease;
}

.action-button {
  min-height: 40px;
  padding: 8px 10px;
  overflow: hidden;
  color: var(--text-main);
  background: rgba(24, 27, 24, 0.94);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.2;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-button.primary,
.apply-button {
  color: #eff7e8;
  border-color: rgba(140, 169, 111, 0.58);
  background: rgba(140, 169, 111, 0.18);
}

.action-button.selected {
  color: #eff7e8;
  border-color: var(--accent-strong);
  background: rgba(140, 169, 111, 0.2);
  box-shadow: inset 0 0 0 1px rgba(168, 199, 131, 0.12);
}

.action-button:hover:not(:disabled),
.home-button:hover:not(:disabled),
.small-button:hover:not(:disabled),
.text-button:hover:not(:disabled) {
  color: #f6f8f3;
  background: var(--panel-surface-hover);
  border-color: var(--panel-border-strong);
  transform: translateY(-1px);
}

.action-button.primary:hover:not(:disabled),
.apply-button:hover:not(:disabled) {
  background: rgba(140, 169, 111, 0.24);
  border-color: var(--accent-strong);
}

.action-button:active:not(:disabled),
.home-button:active:not(:disabled),
.small-button:active:not(:disabled),
.text-button:active:not(:disabled) {
  transform: translateY(1px) scale(0.99);
}

.action-button:focus-visible,
.home-button:focus-visible,
.small-button:focus-visible,
.text-button:focus-visible,
.field input:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}

.action-button:disabled,
.home-button:disabled,
.small-button:disabled,
.text-button:disabled,
.field input:disabled {
  cursor: not-allowed;
  opacity: 0.44;
}

.text-button {
  min-height: 28px;
  padding: 4px 8px;
  color: var(--accent-strong);
  background: transparent;
  font-size: 12px;
}

.physics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.field {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.field span {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.2;
}

.field input {
  width: 100%;
  min-width: 0;
  height: 34px;
  padding: 6px 8px;
  border: 1px solid var(--panel-border);
  border-radius: 6px;
  color: var(--text-main);
  background: rgba(17, 19, 17, 0.96);
  font: inherit;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.field input:hover:not(:disabled) {
  border-color: var(--panel-border-strong);
}

.apply-button {
  width: 100%;
}

.leave-section {
  margin-bottom: 2px;
}

.home-panel {
  min-height: 42px;
}

.home-panel.confirming {
  display: grid;
  gap: 10px;
  padding: 10px;
  border: 1px solid rgba(199, 130, 111, 0.38);
  border-radius: 8px;
  background: rgba(48, 32, 29, 0.66);
}

.home-panel p {
  margin: 0;
  color: #e8beb4;
  font-size: 13px;
  line-height: 1.4;
}

.home-button {
  width: 100%;
  min-height: 40px;
  color: #e8beb4;
  background: rgba(48, 32, 29, 0.42);
  border-color: rgba(199, 130, 111, 0.38);
}

.home-button:hover:not(:disabled) {
  background: var(--danger-surface);
  border-color: rgba(199, 130, 111, 0.7);
}

.confirm-actions {
  gap: 8px;
}

.small-button {
  flex: 1;
  min-height: 36px;
  padding: 7px 10px;
  color: var(--text-main);
  background: rgba(24, 27, 24, 0.94);
  font-size: 13px;
}

.small-button.danger {
  color: #f0d2cb;
  background: rgba(199, 130, 111, 0.12);
  border-color: rgba(199, 130, 111, 0.55);
}

.small-button.danger:hover:not(:disabled) {
  background: rgba(199, 130, 111, 0.2);
  border-color: rgba(199, 130, 111, 0.82);
}

@media (max-width: 620px) {
  .esc-body {
    padding: 16px;
  }

  .button-grid.four,
  .button-grid.tools {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .physics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 430px) {
  .esc-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .esc-state {
    max-width: 100%;
  }

  .button-grid,
  .button-grid.four,
  .button-grid.tools,
  .button-grid.render,
  .physics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
