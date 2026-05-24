<template>
  <div id="zoom" class="absolute right-10 bottom-10 w-max" style="color: #1f2937;">
    <div
      class="relative z-10 inline-flex items-center justify-evenly mr-2.5 bg-gray-100 border border-gray-300 rounded-md"
      style="color: #1f2937;"
    >
      <div class="button-group">
        <button
          aria-label="整理"
          title="整理"
          class="bg-transparent hover:bg-gray-200 active:bg-gray-300 p-2 border-none rounded text-gray-800"
          @click="handleCleanUpClick"
        >
          整理
        </button>
      </div>
      <div class="button-group">
        <button
          aria-label="代码区"
          title="代码区"
          class="bg-transparent hover:bg-gray-200 active:bg-gray-300 p-2 border-none rounded text-gray-800"
          @click="handleCodespace"
        >
          代码区
        </button>
      </div>
      <div class="button-group flex items-center">
        <button
          aria-label="缩小"
          title="缩小"
          class="bg-transparent hover:bg-gray-200 active:bg-gray-300 p-2 border-none rounded text-gray-800"
          @click="handleSmallerClick"
        >
          -
        </button>
        <button
          aria-label="恢复为100%"
          title="恢复为100%"
          class="px-1.5 bg-transparent hover:bg-gray-200 active:bg-gray-300 p-2 border-none rounded"
          @click="handleResetClick"
        >
          <span class="text-gray-800">{{ scaleText }}</span>
        </button>
        <button
          aria-label="放大"
          title="放大"
          class="bg-transparent hover:bg-gray-200 active:bg-gray-300 p-2 border-none rounded text-gray-800"
          @click="handleBiggerClick"
        >
          +
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useStore } from '../store/store.js';

const scaleText = ref('100%');
const store = useStore();

// Blockly 11.x 中 cleanUp() 已被废弃移除，使用 try-catch 保护
function handleCleanUpClick() {
  const ws = store.workspace.value;
  if (!ws) return;
  try {
    if (typeof ws.cleanUp === 'function') {
      ws.cleanUp();
    }
  } catch (e) {
    console.warn('[Blockly] cleanUp() 不可用:', e.message);
  }
}

function handleCodespace() {
  store.hasLayoutSider.value = !store.hasLayoutSider.value;
}

function handleSmallerClick() {
  if (store.workspace.value) {
    store.workspace.value.zoom(0, 0, -0.15);
  }
}

function handleResetClick() {
  store.workspace.value?.zoomTo(0, 0, 1.0);
}

function handleBiggerClick() {
  if (store.workspace.value) {
    store.workspace.value.zoom(0, 0, 0.15);
  }
}

function updateScale() {
  const ws = store.workspace.value;
  if (ws) {
    scaleText.value = Math.floor((ws.scale || 1.0) * 100) + '%';
  }
}

// 保存取消监听的函数引用，确保组件销毁时正确清理
let unwatchWorkspace = null;

onMounted(() => {
  unwatchWorkspace = watch(store.workspace, (ws, oldWs) => {
    if (oldWs) {
      try { oldWs.removeChangeListener?.(updateScale); } catch {}
    }
    if (ws) {
      updateScale();
      ws.addChangeListener(updateScale);
    }
  }, { immediate: true });
});

onUnmounted(() => {
  // 停止 watch
  if (unwatchWorkspace) {
    unwatchWorkspace();
    unwatchWorkspace = null;
  }
  // 移除工作区上的 changeListener，防止泄漏
  const ws = store.workspace.value;
  if (ws) {
    try { ws.removeChangeListener?.(updateScale); } catch {}
  }
});
</script>
