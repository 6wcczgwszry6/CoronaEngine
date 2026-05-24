<template>
  <div
    id="search"
    v-show="store.searchVisible.value"
    class="absolute right-10 top-10 z-[7]"
  >
    <div class="search-container flex border rounded-md overflow-hidden bg-white shadow-lg">
      <input
        type="text"
        :value="searchText"
        placeholder="搜索作品中的积木"
        class="flex-1 p-2 border-none outline-none text-gray-800"
        @input="handleInput"
        @keydown.enter="handlePressEnter"
      />
      <button
        class="px-2 py-1 text-gray-500 hover:text-gray-700 transition-colors"
        @click="store.searchVisible.value = false"
      >✕</button>
      <span v-if="searchText && matches.length > 0" class="flex items-center px-2 text-xs text-gray-500 bg-white">
        {{ currentIndex }}/{{ matches.length }}
      </span>
      <span v-else-if="searchText" class="flex items-center px-2 text-xs text-red-400 bg-white">
        无匹配
      </span>
      <div class="search-buttons flex">
        <button
          aria-label="上一个"
          class="p-2 border-none bg-white hover:bg-gray-100 text-gray-700"
          @click="handleUpClick"
        >
          ↑
        </button>
        <button
          aria-label="下一个"
          class="p-2 border-none bg-white hover:bg-gray-100 text-gray-700"
          @click="handleDownClick"
        >
          ↓
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useStore } from '../store/store.js';

const searchText = ref('');
const store = useStore();

const matches = ref([]);
const currentIndex = ref(0);

function findMatches(text) {
  if (!store.workspace.value || !text.trim()) {
    matches.value = [];
    currentIndex.value = 0;
    return;
  }
  const lower = text.toLowerCase();
  const blocks = store.workspace.value.getAllBlocks(false);
  matches.value = blocks.filter((block) => {
    const blockText = block.toString().toLowerCase();
    return blockText.includes(lower);
  });
  currentIndex.value = matches.value.length > 0 ? 1 : 0;
}

function highlightCurrent() {
  if (matches.value.length === 0) return;
  const block = matches.value[currentIndex.value - 1];
  if (block && store.workspace.value) {
    store.workspace.value.centerOnBlock(block.id);
    block.select();
  }
}

function clearHighlights() {
  matches.value.forEach((block) => {
    try { block.unselect(); } catch {}
  });
  matches.value = [];
  currentIndex.value = 0;
}

function handleInput(event) {
  searchText.value = event.target.value;
  if (!searchText.value.trim()) {
    clearHighlights();
    return;
  }
  findMatches(searchText.value);
  highlightCurrent();
}

function handlePressEnter() {
  next();
}

function handleUpClick() {
  previous();
}

function handleDownClick() {
  next();
}

function previous() {
  if (matches.value.length === 0) return;
  currentIndex.value = currentIndex.value <= 1 ? matches.value.length : currentIndex.value - 1;
  highlightCurrent();
}

function next() {
  if (matches.value.length === 0) return;
  currentIndex.value = currentIndex.value >= matches.value.length ? 1 : currentIndex.value + 1;
  highlightCurrent();
}

let keydownHandler = null;

function setupKeyboardShortcut(injectionDiv) {
  if (!injectionDiv) return;
  keydownHandler = (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'f') {
      // 如果焦点在文本输入框内（非 Blockly 输入），不拦截，让浏览器处理
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      const isTextInput = activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select';
      if (isTextInput) return;
      event.preventDefault();
      event.stopPropagation();
      store.searchVisible.value = !store.searchVisible.value;
    }
  };
  injectionDiv.addEventListener('keydown', keydownHandler);
}

function teardownKeyboardShortcut() {
  if (keydownHandler) {
    const injectionDiv = store.workspaceSvg.value?.injectionDiv;
    if (injectionDiv) {
      injectionDiv.removeEventListener('keydown', keydownHandler);
    }
    keydownHandler = null;
  }
}

onMounted(() => {
  watch(store.workspaceSvg, (svg) => {
    teardownKeyboardShortcut();
    if (svg?.injectionDiv) {
      setupKeyboardShortcut(svg.injectionDiv);
    }
  }, { immediate: true });

  watch(() => store.searchVisible.value, (visible) => {
    if (visible) {
      setTimeout(() => {
        const input = document.getElementById('search')?.querySelector('input');
        if (input) input.focus();
      }, 50);
    } else {
      clearHighlights();
      searchText.value = '';
    }
  });
});

onUnmounted(() => {
  teardownKeyboardShortcut();
});
</script>
