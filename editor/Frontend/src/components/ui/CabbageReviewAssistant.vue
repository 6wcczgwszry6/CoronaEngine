<template>
  <Teleport to="body">
    <div class="fixed bottom-4 left-4 z-[2147483645] pointer-events-none">
      <transition name="assistant-panel">
        <section
          v-if="open"
          class="pointer-events-auto mb-3 flex h-[min(420px,calc(100vh-112px))] w-[min(400px,calc(100vw-32px))] flex-col overflow-hidden rounded-lg border border-[#3c3c3c] bg-[#1e1e1e] text-gray-100 shadow-[0_14px_42px_rgba(0,0,0,0.58)]"
          role="region"
          aria-label="包菜助手节点逻辑检查"
          @mousedown.stop
          @click.stop
          @wheel.stop
        >
          <header class="flex items-center gap-3 border-b border-[#3c3c3c] bg-[#2d2d2d] px-4 py-3">
            <div class="h-11 w-11 flex-shrink-0 overflow-hidden rounded-full border-2 border-emerald-400/60 bg-emerald-300 shadow-md">
              <img src="@/assets/cabbage.png" alt="包菜助手" class="h-full w-full object-cover" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <h2 class="truncate text-base font-semibold text-white">包菜助手</h2>
                <span class="inline-flex items-center gap-1 rounded-full border border-[#48614d] bg-[#26352a] px-2 py-0.5 text-[11px] text-emerald-200">
                  <span class="h-1.5 w-1.5 rounded-full" :class="tasks.length ? 'bg-amber-400' : 'bg-emerald-400'"></span>
                  {{ tasks.length ? '逻辑有问题' : '逻辑正常' }}
                </span>
              </div>
            </div>
            <button
              type="button"
              class="flex h-8 w-8 items-center justify-center rounded-md text-lg text-gray-400 transition hover:bg-[#3d3d3d] hover:text-white"
              title="收起包菜助手"
              aria-label="收起包菜助手"
              @click="setOpen(false)"
            >
              −
            </button>
          </header>

          <div ref="scrollRef" class="min-h-0 flex-1 overflow-y-auto px-3 py-3 assistant-scrollbar">
            <div v-if="!tasks.length" class="flex h-full min-h-48 flex-col items-center justify-center px-6 text-center">
              <div class="mb-3 h-16 w-16 overflow-hidden rounded-full border border-emerald-400/30 bg-emerald-300/90 opacity-90">
                <img src="@/assets/cabbage.png" alt="" class="h-full w-full object-cover" />
              </div>
              <p class="text-sm font-medium text-gray-200">当前逻辑没有发现问题</p>
            </div>

            <ol v-else class="space-y-3">
              <li
                v-for="task in tasks"
                :key="task.issueKey"
                class="rounded-md border border-[#454545] border-l-2 border-l-amber-500 bg-[#262626] px-3.5 py-3 shadow-sm"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="h-2 w-2 flex-shrink-0 rounded-full bg-amber-400"></span>
                      <h3 class="truncate text-sm font-semibold text-gray-100">{{ task.title }}</h3>
                    </div>
                  </div>
                  <time class="flex-shrink-0 text-[10px] text-gray-600" :datetime="toIso(task.updatedAt)">
                    {{ formatTime(task.updatedAt) }}
                  </time>
                </div>
                <p v-if="task.message" class="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-gray-300">
                  {{ task.message }}
                </p>
              </li>
            </ol>
          </div>

          <footer class="flex items-center justify-between border-t border-[#3c3c3c] bg-[#252525] px-3.5 py-2.5 text-xs text-gray-500">
            <span>当前节点逻辑</span>
            <span>{{ tasks.length ? '等待修改' : '检查通过' }}</span>
          </footer>
        </section>
      </transition>

      <button
        type="button"
        class="pointer-events-auto relative flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border-2 border-emerald-400/70 bg-emerald-300 shadow-[0_10px_32px_rgba(16,185,129,0.35)] transition duration-200 hover:scale-105 hover:border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-300/70"
        :title="open ? '收起包菜助手' : '打开包菜助手'"
        :aria-expanded="open"
        aria-label="包菜助手"
        @click="setOpen(!open)"
      >
        <img src="@/assets/cabbage.png" alt="包菜助手" class="h-full w-full object-cover" />
        <span
          v-if="unreadCount > 0 && !open"
          class="absolute right-0 top-0 flex min-h-5 min-w-5 items-center justify-center rounded-full border-2 border-[#151b18] bg-amber-500 px-1 text-[10px] font-bold leading-none text-white"
        >
          {{ unreadCount > 99 ? '99+' : unreadCount }}
        </span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';

const props = defineProps({
  open: { type: Boolean, default: false },
  tasks: { type: Array, default: () => [] },
  attentionToken: { type: Number, default: 0 },
});

const emit = defineEmits(['update:open']);
const scrollRef = ref(null);
const unreadCount = ref(0);

function setOpen(value) {
  emit('update:open', value);
  if (value) {
    unreadCount.value = 0;
    scrollToLatest();
  }
}

function scrollToLatest() {
  nextTick(() => {
    const el = scrollRef.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

function formatTime(value) {
  const date = new Date(Number(value) || Date.now());
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}

function toIso(value) {
  const date = new Date(Number(value) || Date.now());
  return Number.isNaN(date.getTime()) ? '' : date.toISOString();
}

watch(
  () => props.attentionToken,
  (value, oldValue) => {
    if (!value || value === oldValue) return;
    if (props.open) {
      scrollToLatest();
      return;
    }
    unreadCount.value += 1;
    emit('update:open', true);
    unreadCount.value = 0;
    scrollToLatest();
  }
);

watch(
  () => props.open,
  (value) => {
    if (value) {
      unreadCount.value = 0;
      scrollToLatest();
    }
  }
);

watch(
  () => props.tasks.length,
  () => {
    if (props.open) scrollToLatest();
  }
);

onMounted(() => {
  if (props.open) scrollToLatest();
});
</script>

<style scoped>
.assistant-panel-enter-active,
.assistant-panel-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
  transform-origin: left bottom;
}
.assistant-panel-enter-from,
.assistant-panel-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}
.assistant-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: rgba(52, 211, 153, 0.35) rgba(255, 255, 255, 0.04);
}
.assistant-scrollbar::-webkit-scrollbar {
  width: 7px;
}
.assistant-scrollbar::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.04);
}
.assistant-scrollbar::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(52, 211, 153, 0.35);
}
</style>
