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
          <p class="esc-kicker">ESC menu</p>
          <h2 id="esc-menu-title">暂停菜单</h2>
          <p>编辑器仍在运行，选择下一步操作。</p>
        </div>
        <span class="esc-state">编辑中</span>
      </header>

      <nav class="command-list" aria-label="暂停菜单操作">
        <button class="command-button command-button-primary" type="button" @click="handleContinue">
          <span>
            <strong>继续编辑</strong>
            <small>关闭此菜单并回到当前场景。</small>
          </span>
        </button>

        <button
          class="command-button"
          type="button"
          @click="openPanelOrRoute('ProjectSettings', '/ProjectSettings')"
        >
          <span>
            <strong>项目设置</strong>
            <small>打开项目名称、入口场景和版本配置。</small>
          </span>
        </button>

        <button
          class="command-button"
          type="button"
          @click="openPanelOrRoute('AITalkBar', '/AITalkBar')"
        >
          <span>
            <strong>AI 对话</strong>
            <small>打开 AI 对话面板。</small>
          </span>
        </button>

        <button
          class="command-button"
          type="button"
          @click="openPanelOrRoute('LogTool', '/LogView')"
        >
          <span>
            <strong>日志</strong>
            <small>查看 Engine、Python 和 Vue 的运行输出。</small>
          </span>
        </button>

        <button
          class="command-button"
          type="button"
          @click="openPanelOrRoute('Network', '/Network')"
        >
          <span>
            <strong>网络协作</strong>
            <small>打开联机会话、端口和连接状态。</small>
          </span>
        </button>
      </nav>

      <div class="home-panel" :class="{ confirming: confirmHome }">
        <template v-if="confirmHome">
          <div class="confirm-copy">
            <strong>回到主页？</strong>
            <span>当前编辑视图会离开，未保存内容请先在对应工具中保存。</span>
          </div>
          <div class="confirm-actions">
            <button class="small-button" type="button" @click="cancelHome">取消</button>
            <button class="small-button danger" type="button" @click="goHome">确认回主页</button>
          </div>
        </template>
        <button v-else class="home-button" type="button" @click="confirmHome = true">
          回到主页
        </button>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useDockStore } from '@/stores/dockStore.js';
import { useDockPanel } from '@/composables/useDockPanel.js';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';

const router = useRouter();
const dockStore = useDockStore();
const { closePanel, isDocked } = useDockPanel();

const confirmHome = ref(false);

function handleContinue() {
  confirmHome.value = false;
  closePanel();

  if (!isDocked && !canUseNativeDockCommand()) {
    router.push('/');
  }
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

function canUseNativeDockCommand() {
  return Boolean(window.coronaBridge && typeof window.coronaBridge.dockCommand === 'function');
}
</script>

<style scoped>
.esc-panel {
  --panel-bg: #151615;
  --panel-surface: #1d1f1d;
  --panel-surface-hover: #242824;
  --panel-border: #343934;
  --panel-border-strong: #495248;
  --text-main: #ecefe9;
  --text-muted: #9ca49a;
  --accent: #8aa36b;
  --accent-strong: #a1bb7a;
  --danger: #c07a6b;
  --danger-surface: #32211f;

  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 20% 0%, rgba(138, 163, 107, 0.1), transparent 36%),
    linear-gradient(180deg, #1a1b19 0%, var(--panel-bg) 100%);
  color: var(--text-main);
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  -webkit-font-smoothing: antialiased;
}

.esc-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(138, 163, 107, 0.45) transparent;
}

.esc-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--panel-border);
}

.esc-kicker {
  margin: 0 0 5px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.esc-header h2 {
  margin: 0;
  color: var(--text-main);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  text-wrap: balance;
}

.esc-header p {
  max-width: 24rem;
  margin: 7px 0 0;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
  text-wrap: pretty;
}

.esc-state {
  flex: 0 0 auto;
  margin-top: 3px;
  padding: 5px 8px;
  border: 1px solid rgba(138, 163, 107, 0.45);
  border-radius: 6px;
  color: var(--accent-strong);
  background: rgba(138, 163, 107, 0.08);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.command-list {
  display: grid;
  gap: 7px;
}

.command-button,
.home-button,
.small-button {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  font: inherit;
  cursor: pointer;
  transition:
    background-color 180ms ease,
    border-color 180ms ease,
    color 180ms ease,
    transform 180ms ease,
    box-shadow 180ms ease;
}

.command-button {
  width: 100%;
  min-height: 52px;
  padding: 9px 13px;
  display: flex;
  align-items: center;
  text-align: left;
  color: var(--text-main);
  background: rgba(29, 31, 29, 0.92);
}

.command-button:hover {
  background: var(--panel-surface-hover);
  border-color: var(--panel-border-strong);
  transform: translateY(-1px);
}

.command-button:active,
.home-button:active,
.small-button:active {
  transform: translateY(1px) scale(0.99);
}

.command-button:focus-visible,
.home-button:focus-visible,
.small-button:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}

.command-button-primary {
  border-color: rgba(138, 163, 107, 0.62);
  background: rgba(138, 163, 107, 0.13);
  box-shadow: 0 10px 24px rgba(28, 36, 24, 0.26);
}

.command-button-primary:hover {
  border-color: var(--accent-strong);
  background: rgba(138, 163, 107, 0.18);
}

.command-button strong {
  display: block;
  color: currentColor;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.25;
}

.command-button small {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-wrap: pretty;
}

.home-panel {
  min-height: 56px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--panel-border);
}

.home-panel.confirming {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid rgba(192, 122, 107, 0.38);
  border-radius: 8px;
  background: rgba(50, 33, 31, 0.55);
}

.home-button {
  width: 100%;
  min-height: 42px;
  color: #e8c1b8;
  background: rgba(50, 33, 31, 0.42);
  border-color: rgba(192, 122, 107, 0.35);
}

.home-button:hover {
  color: #f0d7d1;
  background: var(--danger-surface);
  border-color: rgba(192, 122, 107, 0.65);
}

.confirm-copy {
  display: grid;
  gap: 4px;
}

.confirm-copy strong {
  color: #f0d7d1;
  font-size: 14px;
  line-height: 1.3;
}

.confirm-copy span {
  color: #caa59d;
  font-size: 12px;
  line-height: 1.5;
  text-wrap: pretty;
}

.confirm-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.small-button {
  min-height: 36px;
  padding: 8px 10px;
  color: var(--text-main);
  background: rgba(29, 31, 29, 0.9);
}

.small-button:hover {
  background: var(--panel-surface-hover);
  border-color: var(--panel-border-strong);
}

.small-button.danger {
  color: #f0d7d1;
  background: rgba(192, 122, 107, 0.12);
  border-color: rgba(192, 122, 107, 0.55);
}

.small-button.danger:hover {
  background: rgba(192, 122, 107, 0.2);
  border-color: rgba(192, 122, 107, 0.8);
}

@media (max-width: 460px) {
  .esc-body {
    padding: 18px;
  }

  .esc-header {
    flex-direction: column;
    gap: 10px;
  }

  .esc-state {
    align-self: flex-start;
  }
}
</style>
