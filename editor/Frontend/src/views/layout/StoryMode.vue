<template>
  <div
    class="relative min-h-screen border-2 border-[#84a65b] bg-[#282828]/95 text-white overflow-hidden flex flex-col font-sans"
  >
    <DockTitleBar
      title="剧情模式"
      extraClass="bg-[#84A65B]"
      routePath="/StoryMode"
      @close="closeFloat"
    />

    <!-- Tab content -->
    <div class="flex-1 p-12 bg-[#252525] flex flex-col overflow-y-auto">
      <div class="max-w-3xl space-y-8">
        <h2 class="text-2xl font-light mb-4">基础信息</h2>
        <div class="space-y-2">
          <label class="text-sm text-gray-400">项目名称</label>
          <input v-model="projectName" type="text"
            class="w-full bg-[#1a1a1a] border border-[#444] rounded p-3 text-base focus:border-[#84a65b] outline-none transition-all"
            placeholder="请输入项目名称..." />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-400">存储位置</label>
          <div class="flex gap-2">
            <input v-model="projectPath" type="text" readonly
              class="flex-1 bg-[#1a1a1a] border border-[#444] rounded p-3 text-base text-gray-400" />
            <button class="px-6 bg-[#3d3d3d] hover:bg-[#4d4d4d] rounded transition-colors text-base" @click="browseFolder">浏览</button>
          </div>
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-400">游戏标题</label>
          <input v-model="storySettings.gameTitle" type="text"
            class="w-full bg-[#1a1a1a] border border-[#444] rounded p-3 text-base focus:border-[#84a65b] outline-none transition-all"
            placeholder="在此显示的游戏标题..." />
        </div>
        <div class="space-y-2">
          <label class="text-sm text-gray-400">作者 / 团队</label>
          <input v-model="storySettings.author" type="text"
            class="w-full bg-[#1a1a1a] border border-[#444] rounded p-3 text-base focus:border-[#84a65b] outline-none transition-all"
            placeholder="作者或团队名称..." />
        </div>
      </div>
    </div>

    <!-- Bottom buttons -->
    <div class="shrink-0 px-12 py-6 bg-[#1e1e1e] border-t border-[#333] flex justify-between items-center">
      <button class="px-5 py-3 text-base text-gray-400 hover:text-white hover:bg-[#333] rounded transition-colors inline-flex items-center gap-1 w-fit" @click="goBack">
        <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        返回
      </button>
      <div class="flex gap-4 items-center">
        <button class="px-10 py-3 text-base text-gray-400 hover:text-white transition-colors" @click="closeFloat">取消</button>
        <button
          :disabled="!projectName || !projectPath"
          class="px-14 py-3 bg-[#84a65b] hover:bg-[#95b86c] disabled:bg-gray-600 disabled:cursor-not-allowed rounded font-bold transition-all shadow-lg text-base"
          @click="handleCreateProject">
          创建项目
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { projectLauncherService, appService } from '@/utils/bridge';
import DockTitleBar from '@/components/ui/DockTitleBar.vue';

const router = useRouter();

const projectName = ref('New_Corona_Project');
const projectPath = ref('');
const activeTab = ref('basic');

const tabs = [
  { id: 'basic', label: '基础信息' },
  { id: 'narrative', label: '叙事设定' },
  { id: 'cinematics', label: '演出配置' },
  { id: 'audio', label: '音频设计' },
];

const activeTabLabel = computed(() => {
  const t = tabs.find(t => t.id === activeTab.value);
  return t ? `步骤 ${tabs.indexOf(t) + 1}/${tabs.length}` : '';
});

const narrativeTypes = [
  { id: 'linear', label: '线性叙事', desc: '单线剧情，无分支' },
  { id: 'branching', label: '分支叙事', desc: '多分支路线与结局' },
  { id: 'open', label: '开放叙事', desc: '碎片化叙事，自由探索' },
];

const dialogueStyles = [
  { id: 'vn', label: '视觉小说', desc: '立绘+文本框经典AVG' },
  { id: 'free', label: '自由对话', desc: '非固定位置对话气泡' },
  { id: 'timeline', label: '时间轴', desc: '时间线驱动对话事件' },
];

const consequenceScopes = [
  { id: 'chapter', label: '章节内影响', desc: '选择仅影响当前章节' },
  { id: 'global', label: '全局影响', desc: '选择贯穿整个故事' },
  { id: 'none', label: '无影响', desc: '纯观赏性选择' },
];

const cameraStyles = [
  { id: 'static', label: '静态镜头', desc: '固定视角切换' },
  { id: 'cinematic', label: '电影化运镜', desc: '推拉摇移动态镜头' },
  { id: 'first_person', label: '第一人称', desc: '主角视角叙事' },
];

const uiThemes = [
  { id: 'dark', label: '暗色主题', desc: '深色背景适配剧情' },
  { id: 'light', label: '亮色主题', desc: '浅色清新风格' },
  { id: 'custom', label: '自定义', desc: '后续自行配置' },
];

const voiceOptions = [
  { id: 'none', label: '仅文本', desc: '无语音，纯文字演出' },
  { id: 'partial', label: '部分语音', desc: '关键场景配音' },
  { id: 'full', label: '全程语音', desc: '全文本配音覆盖' },
];

const storySettings = ref({
  gameTitle: '',
  author: '',
  narrativeType: 'linear',
  dialogueStyle: 'vn',
  consequenceScope: 'chapter',
  cameraStyle: 'static',
  textSpeed: 3,
  autoPlay: false,
  skipEnabled: true,
  uiTheme: 'dark',
  bgmVolume: 80,
  sfxVolume: 100,
  voiceOption: 'partial',
  ambientPreset: 'none',
});

onMounted(async () => {
  try {
    const path = await projectLauncherService.getDefaultProjectPath();
    if (path) projectPath.value = path.data;
  } catch (error) {
    console.error('StoryMode 初始化失败:', error);
  }
});

const goBack = () => {
  router.push('/StartScreen');
};

const browseFolder = async () => {
  const path = await projectLauncherService.browseFolder(projectPath.value);
  if (path.data) projectPath.value = path.data;
};

const handleCreateProject = async () => {
  if (!projectName.value || !projectPath.value) return;

  try {
    const projectData = {
      name: projectName.value,
      path: projectPath.value,
      mode: 'story',
      settings: {
        ...storySettings.value,
        defaultScene: 'story_basic',
        realTimeRender: false,
      },
    };

    const result = await projectLauncherService.createProject(projectData);

    if (result.success === true) {
      await handleOpenProject(result.data);
    } else {
      alert('创建失败: ' + result.message);
    }
  } catch (error) {
    console.error('创建项目异常:', error);
  }
};

const handleOpenProject = async (path) => {
  try {
    await projectLauncherService.setProjectMode('story', storySettings.value);
    const success = await projectLauncherService.openProject(path);
    if (success.data) {
      await appService.start_engine();
      router.push('/');
    }
  } catch (error) {
    console.error('打开项目失败:', error);
  }
};

const closeFloat = async () => {
  window.close();
};
</script>

<style scoped>
::-webkit-scrollbar {
  width: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: #84a65b;
}
</style>
