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
import { editorApi } from '@/utils/bridge.js';

const { closePanel: closeDockPanel, isDocked } = useDockPanel();
const { t } = useI18n();
let lanChatEventCallbackToken = null;

// 局域网聊天室事件由 C++ Editor API event registry 定义和分发。
const onLanchatEvent = (payload) => {
  lanchat.handleEvent(payload);
};

onMounted(async () => {
  lanChatEventCallbackToken = await editorApi.events.onLanChatEvent(onLanchatEvent);
});

onUnmounted(() => {
  if (lanChatEventCallbackToken) {
    editorApi.off(lanChatEventCallbackToken).finally(() => {
      lanChatEventCallbackToken = null;
    });
  }
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
