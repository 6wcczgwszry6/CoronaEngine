<template>
  <div
    id="trashcan"
    ref="trashcanRef"
    class="absolute z-10 right-6 w-12 flex flex-col items-center select-none pointer-events-none"
    style="bottom: 88px; opacity: 0; transition: opacity 0.2s;"
  >
    <svg
      ref="lidRef"
      class="w-9 transition-transform duration-300"
      style="transition-timing-function: cubic-bezier(0.34, 0.69, 0.1, 1)"
      viewBox="0 0 36 12"
      fill="none"
    >
      <rect x="2" y="4" width="32" height="8" rx="2" fill="#888" />
      <rect x="8" y="0" width="20" height="6" rx="2" fill="#aaa" />
    </svg>
    <svg
      ref="bodyRef"
      class="w-9 transition-opacity duration-300"
      viewBox="0 0 36 30"
      fill="none"
    >
      <path d="M4 4h28l-2.5 25H6.5L4 4Z" fill="#888" />
      <rect x="2" y="1" width="32" height="4" rx="1" fill="#999" />
      <line x1="10" y1="10" x2="10" y2="24" stroke="#666" stroke-width="1.5" stroke-linecap="round" />
      <line x1="18" y1="10" x2="18" y2="24" stroke="#666" stroke-width="1.5" stroke-linecap="round" />
      <line x1="26" y1="10" x2="26" y2="24" stroke="#666" stroke-width="1.5" stroke-linecap="round" />
    </svg>
    <div
      ref="labelRef"
      class="text-sm text-gray-400 mt-1 whitespace-nowrap opacity-0 transition-opacity duration-200"
    >
      拖至此处删除
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useStore } from '../store/store';

const store = useStore();
const trashcanRef = ref();
const lidRef = ref();
const bodyRef = ref();
const labelRef = ref();

let changeListener = null;
let mouseTracker = null;
let hovering = false;
let unwatch = null;

function show() {
  if (trashcanRef.value) trashcanRef.value.style.opacity = '1';
}

function hide() {
  if (trashcanRef.value) trashcanRef.value.style.opacity = '0';
  closeLid();
}

function openLid() {
  if (lidRef.value) lidRef.value.style.transform = 'translateY(-4px) rotate(-12deg)';
  if (bodyRef.value) bodyRef.value.style.opacity = '1';
  if (labelRef.value) labelRef.value.style.opacity = '1';
}

function closeLid() {
  if (lidRef.value) lidRef.value.style.transform = '';
  hovering = false;
}

function isOverTrashcan(clientX, clientY) {
  if (!trashcanRef.value) return false;
  const r = trashcanRef.value.getBoundingClientRect();
  return clientX >= r.left && clientX <= r.right && clientY >= r.top - 30 && clientY <= r.bottom;
}

function startMouseTracking() {
  if (mouseTracker) return;
  mouseTracker = (e) => {
    const over = isOverTrashcan(e.clientX, e.clientY);
    if (over && !hovering) {
      hovering = true;
      openLid();
    } else if (!over && hovering) {
      hovering = false;
      closeLid();
    }
  };
  document.addEventListener('mousemove', mouseTracker);
}

function stopMouseTracking() {
  if (mouseTracker) {
    document.removeEventListener('mousemove', mouseTracker);
    mouseTracker = null;
  }
}

function canDelete(block) {
  try {
    if (!block || !block.workspace) return false;
    return block.isDeletable?.() ?? true;
  } catch {
    return false;
  }
}

function setupListeners(ws) {
  if (!ws) return;

  changeListener = (event) => {
    if (event.type === 'drag') {
      show();
      startMouseTracking();
    } else if (event.type === 'move' && event.oldCoordinate !== undefined) {
      if (hovering && event.blockId) {
        try {
          const block = ws.getBlockById(event.blockId);
          if (block && canDelete(block)) {
            block.dispose(false);
          }
        } catch {}
      }
      closeLid();
      hide();
      stopMouseTracking();
    }
  };
  ws.addChangeListener(changeListener);
}

onMounted(() => {
  unwatch = watch(store.workspaceSvg, (svg, oldSvg) => {
    if (changeListener && oldSvg) {
      try { oldSvg.removeChangeListener?.(changeListener); } catch {}
      changeListener = null;
    }
    stopMouseTracking();
    if (svg) {
      setupListeners(svg);
    }
  }, { immediate: true });
});

onUnmounted(() => {
  if (unwatch) { unwatch(); unwatch = null; }
  if (changeListener) {
    try { store.workspaceSvg.value?.removeChangeListener?.(changeListener); } catch {}
    changeListener = null;
  }
  stopMouseTracking();
});
</script>