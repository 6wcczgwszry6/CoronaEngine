<template>
  <div class="node-graph-panel flex h-full min-h-0 w-full flex-1 flex-col overflow-hidden">
    <DockTitleBar
      v-if="!isDocked"
      title="节点"
      extraClass="bg-[#84A65B] rounded-t-md"
      routePath="/NodeGraph"
      @close="closeFloat"
    />
    <NodeGraphWorkspace
      class="min-h-0 flex-1"
      actor-name=""
      :scene-name="sceneName"
      target-type="project"
      :review-active="true"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import NodeGraphWorkspace from '@/blockly/components/NodeGraphWorkspace.vue';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';
import { useDockPanel } from '@/composables/useDockPanel.js';
import { projectService } from '@/utils/bridge.js';
import { DEFAULT_SCENE_NAME } from '@/utils/constants.js';

const { closePanel, isDocked } = useDockPanel();
const sceneName = ref(DEFAULT_SCENE_NAME);

onMounted(async () => {
  try {
    const response = await projectService.OnInit();
    const data = response?.data ?? response;
    const scenes = Array.isArray(data?.scenes) ? data.scenes : [];
    const index = Math.max(0, Number(data?.active_index) || 0);
    sceneName.value = scenes[index]?.path || scenes[index]?.name || data?.path || data?.name || DEFAULT_SCENE_NAME;
  } catch {
    sceneName.value = DEFAULT_SCENE_NAME;
  }
});

function closeFloat() {
  closePanel();
}
</script>

<style scoped>
.node-graph-panel {
  position: relative;
  z-index: 2147483100;
  background: rgba(40, 40, 40, 0.42);
  border: 1px solid rgba(58, 58, 58, 0.72);
  border-radius: 8px;
}
</style>



