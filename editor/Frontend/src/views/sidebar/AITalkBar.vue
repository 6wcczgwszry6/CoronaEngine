<template>
  <div class="ai-talk-shell flex flex-col flex-1 min-h-0 h-full w-full rounded-lg overflow-hidden relative">
    <DockTitleBar
      v-if="!isDocked"
      :title="t('plugins.AITalkBar')"
      extraClass="bg-[#84A65B]"
      routePath="/AITalkBar"
      @close="closeFloat"
    />

    <!-- 局域网聊天（单一模式） -->
    <div class="ai-talk-content w-full flex-1 min-h-0">
      <RoomPanel />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';
import RoomPanel from './lanchat/RoomPanel.vue';
import lanchat from '@/stores/lanchat.js';
import { useDockPanel } from '@/composables/useDockPanel.js';
import { coronaEventBus } from '@/utils/eventBus.js';

const { closePanel: closeDockPanel, isDocked } = useDockPanel();
const { t } = useI18n();

// 局域网聊天室事件：C++ NetworkSystem 经 __coronaEmit('lanchat-event', event) 推送，
// __coronaEmit → coronaEventBus.emit('lanchat-event', event) → 本 handler。
const onLanchatEvent = (payload) => {
  lanchat.handleEvent(payload);
};

onMounted(() => {
  coronaEventBus.on('lanchat-event', onLanchatEvent);
});

onUnmounted(() => {
  coronaEventBus.off('lanchat-event', onLanchatEvent);
});

function closeFloat() {
  closeDockPanel();
}
</script>

<style scoped>
.ai-talk-shell {
  background: rgba(40, 40, 40, 0.42);
}

.ai-talk-content {
  background: rgba(40, 40, 40, 0.24);
}
</style>
