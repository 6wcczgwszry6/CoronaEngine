<template>
  <Teleport to="body">
    <transition name="bubble-pop">
      <div
        v-if="visible"
        ref="bubbleRef"
        class="fixed z-[9999] flex items-start gap-2"
        :style="bubbleStyle"
        @mouseenter="isHovering = true; cancelAutoHide"
        @mouseleave="isHovering = false; startAutoHide"
      >
        <!-- Cabbage avatar -->
        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-green-400 border-2 border-green-600 overflow-hidden shadow-md">
          <img
            src="@/assets/cabbage.png"
            class="w-full h-full object-cover"
            alt="cabbage"
          />
        </div>

        <!-- Bubble -->
        <div class="relative max-w-[220px] bg-gradient-to-br from-green-50 to-green-100 text-gray-800 px-3 py-2 rounded-2xl rounded-tl-sm shadow-lg border border-green-200">
          <!-- Loading state -->
          <div v-if="loading" class="flex items-center gap-1 py-1">
            <span class="w-2 h-2 bg-green-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-2 h-2 bg-green-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-2 h-2 bg-green-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
          </div>

          <!-- Hint text -->
          <p v-else class="text-sm leading-relaxed">{{ hintText }}</p>

          <!-- Auto-hide progress bar -->
          <div v-if="!loading" class="mt-1.5 h-0.5 bg-green-200 rounded-full overflow-hidden">
            <div
              class="h-full bg-green-400 rounded-full transition-all"
              :style="{ width: progressPercent + '%' }"
            ></div>
          </div>

          <!-- Close button -->
          <button
            v-if="!loading"
            class="absolute -top-1.5 -right-1.5 w-5 h-5 bg-white rounded-full shadow border border-gray-200 flex items-center justify-center hover:bg-gray-100 transition-colors"
            @click.stop="dismiss"
          >
            <span class="text-xs text-gray-400 leading-none">x</span>
          </button>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';

const props = defineProps({
  show: { type: Boolean, default: false },
  hintText: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  anchorEl: { type: Object, default: null },
  autoHideMs: { type: Number, default: 6000 },
});

const emit = defineEmits(['close']);
const bubbleRef = ref(null);
const visible = ref(false);
const dismissRequested = ref(false);
const isHovering = ref(false);
const progressPercent = ref(100);

let hideTimer = null;
let progressTimer = null;
let progressStart = 0;

const bubbleStyle = computed(() => {
  const pos = calcPosition();
  return {
    left: pos.x + 'px',
    top: pos.y + 'px',
  };
});

const calcPosition = () => {
  const anchor = props.anchorEl;
  if (anchor) {
    const rect = anchor.getBoundingClientRect();
    let x = rect.left - 220;
    let y = rect.top - 10;

    if (x < 10) x = rect.right + 10;
    if (y < 10) y = 10;
    if (y + 80 > window.innerHeight) y = window.innerHeight - 90;

    return { x, y };
  }

  // Default: bottom-left area
  return { x: 80, y: window.innerHeight - 160 };
};

const startAutoHide = () => {
  if (dismissRequested.value) return;
  cancelAutoHide();

  progressStart = Date.now();
  progressPercent.value = 100;

  progressTimer = setInterval(() => {
    const elapsed = Date.now() - progressStart;
    const remaining = Math.max(0, 100 - (elapsed / props.autoHideMs) * 100);
    progressPercent.value = remaining;
  }, 50);

  hideTimer = setTimeout(() => {
    dismiss();
  }, props.autoHideMs);
};

const cancelAutoHide = () => {
  if (hideTimer) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
};

const dismiss = () => {
  dismissRequested.value = true;
  cancelAutoHide();
  visible.value = false;
  // Emit close after leave transition completes (200ms)
  setTimeout(() => emit('close'), 220);
};

// Watch for show changes
watch(
  () => props.show,
  (val) => {
    if (val) {
      dismissRequested.value = false;
      nextTick(() => {
        visible.value = true;
        startAutoHide();
      });
    }
  },
  { immediate: true }
);

// 当 autoHideMs 改变时（如设置页修改），重启自动隐藏定时器
watch(
  () => props.autoHideMs,
  () => {
    if (visible.value && !dismissRequested.value && !isHovering.value) {
      startAutoHide();
    }
  }
);

onMounted(() => {
  if (props.show) {
    visible.value = true;
    startAutoHide();
  }
});

onUnmounted(() => {
  cancelAutoHide();
});
</script>

<style scoped>
.bubble-pop-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.bubble-pop-leave-active {
  transition: all 0.2s ease-in;
}
.bubble-pop-enter-from {
  opacity: 0;
  transform: scale(0.5) translateY(10px);
}
.bubble-pop-leave-to {
  opacity: 0;
  transform: scale(0.8) translateY(-5px);
}
</style>
