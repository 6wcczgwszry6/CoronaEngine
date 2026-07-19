<template>
  <div
    class="relative h-screen border-2 border-[#84a65b] bg-[#282828]/95 text-white overflow-hidden flex flex-col font-sans"
  >
    <div class="flex-1 min-h-0 p-20 bg-[#1e1e1e] flex flex-col">
      <div class="mb-10 shrink-0">
        <h2 class="text-5xl font-bold text-[#84a65b] mb-2">Corona Editor</h2>
        <p class="text-base text-gray-500">版本: {{ appVersion }}</p>
      </div>

      <div class="shrink-0 mb-6">
        <h3 class="text-base font-semibold text-gray-400 uppercase tracking-wider">
          最近项目
        </h3>
      </div>

      <div class="flex-1 min-h-0 overflow-y-auto pr-1">
        <div v-if="recentProjects.length > 0" class="space-y-3">
          <div
            v-for="proj in recentProjects"
            :key="proj.path"
            class="p-5 rounded bg-[#2d2d2d] transition-colors group flex items-center gap-6"
            :class="[
              proj.if_exists
                ? 'cursor-pointer hover:bg-[#3d3d3d]'
                : 'cursor-not-allowed opacity-60',
              selectedProject === proj.path
                ? 'border border-[#84a65b]'
                : 'border border-transparent',
            ]"
            @click="proj.if_exists && (selectedProject = proj.path)"
            @dblclick="proj.if_exists && handleOpenProject(proj.path, proj)"
          >
            <div class="min-w-0 flex-1">
              <div class="text-base font-medium truncate flex items-center gap-2">
                <span v-if="proj.if_exists">{{ proj.name }}</span>
                <span v-else class="text-red-500">{{ proj.name }} (路径异常)</span>
                <span
                  v-if="proj.if_exists"
                  class="shrink-0 text-[10px] px-2 py-0.5 rounded border"
                  :class="proj.legacy
                    ? 'text-amber-300 border-amber-500/50 bg-amber-500/10'
                    : 'text-emerald-300 border-emerald-500/50 bg-emerald-500/10'"
                >
                  {{ proj.legacy ? '旧格式' : '便携场景' }}
                </span>
              </div>
              <div class="text-xs text-gray-500 truncate mt-1">{{ proj.path }}</div>
              <button
                v-if="proj.if_exists && proj.legacy"
                class="mt-2 px-2 py-1 text-[10px] rounded bg-[#84a65b] hover:bg-[#95b86c]"
                @click.stop="migrateLegacyProject(proj)"
              >
                另存为便携场景
              </button>
            </div>
            <div class="shrink-0 min-w-40 text-right">
              <div class="text-[11px] text-gray-600 uppercase tracking-wider">上次编辑</div>
              <div class="text-sm text-gray-400 font-mono mt-1">{{ proj.last_edited || '-' }}</div>
            </div>
          </div>
        </div>
        <div
          v-else
          class="text-sm text-gray-600 italic p-6 text-center border border-dashed border-[#333] rounded"
        >
          暂无最近记录
        </div>
      </div>

      <div class="mt-6 pt-6 border-t border-[#333] flex items-center gap-3 shrink-0">
        <button
          class="flex-1 py-3 px-6 text-left text-base hover:bg-[#333] rounded flex items-center gap-3"
          @click="handleImport"
        >
          <span class="text-xl">📁</span>
          打开现有项目...
        </button>
        <button
          class="py-3 px-10 text-base rounded flex items-center justify-center gap-2 transition-colors shrink-0"
          :class="selectedProject ? 'bg-[#84a65b] text-white hover:bg-[#9bc46d]' : 'bg-[#333] text-gray-500 cursor-not-allowed'"
          :disabled="!selectedProject"
          @click="openSelectedProject"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          开始
        </button>
      </div>

      <div class="mt-6 shrink-0">
        <button
          class="px-5 py-3 text-base text-gray-400 hover:text-white hover:bg-[#333] rounded transition-colors inline-flex items-center gap-1 w-fit"
          @click="goBack"
        >
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          返回
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { projectLauncherService } from '@/utils/bridge';

const router = useRouter();

const appVersion = ref('V1.0.0');
const recentProjects = ref([]);
const selectedProject = ref(null);

const goBack = () => {
  router.push('/StartScreen');
};

onMounted(async () => {
  try {
    const version = await projectLauncherService.getAppVersion();
    if (version) appVersion.value = version.data;

    const saved = await projectLauncherService.getRecentProjects();
    if (saved) recentProjects.value = saved.data;
  } catch (error) {
    console.error('RecentGames 初始化失败:', error);
  }
});

const unwrapResponse = (response) => response?.data ?? response;

const migrationDiagnostics = (result) => (result?.diagnostics || [])
  .map((item) => `${item.actor || 'scene'}: ${item.path || ''} — ${item.message || ''}`)
  .join('\n');

const openSelectedProject = () => {
  const project = recentProjects.value.find((item) => item.path === selectedProject.value);
  if (project) handleOpenProject(project.path, project);
};

const migrateLegacyProject = async (project) => {
  if (!project?.path || !project.if_exists || !project.legacy) return false;
  try {
    const selected = await projectLauncherService.choosePortableSceneTarget();
    const targetPath = unwrapResponse(selected);
    if (!targetPath) return false;

    const migrated = await projectLauncherService.migrateLegacyScene({
      sourcePath: project.path,
      targetPath,
      sceneName: project.name || 'PortableScene',
    });
    const result = unwrapResponse(migrated);
    if (!result?.ok) {
      window.alert(`迁移失败：\n${migrationDiagnostics(result)}`);
      return false;
    }

    recentProjects.value = recentProjects.value.map((item) =>
      item.path === project.path
        ? { ...item, path: result.path, legacy: false, name: project.name }
        : item,
    );
    selectedProject.value = result.path;
    await handleOpenProject(result.path);
    return true;
  } catch (error) {
    console.error('旧项目迁移失败:', error);
    return false;
  }
};

const handleOpenProject = async (path, project = null) => {
  try {
    const result = await projectLauncherService.openProject(path);
    const opened = unwrapResponse(result);
    if (opened?.legacy) {
      const promptKey = `corona.legacyMigrationPrompted:${opened.path}`;
      if (!window.localStorage?.getItem(promptKey)) {
        window.localStorage?.setItem(promptKey, 'true');
        if (window.confirm('这是旧格式存档。是否另存为便携场景文件夹？')) {
          const migrated = await migrateLegacyProject({
            ...(project || {}),
            path: opened.path,
            if_exists: true,
            legacy: true,
            name: project?.name || opened.path.split(/[\\/]/).pop() || 'PortableScene',
          });
          if (migrated) return;
        }
      }
    }
    if (opened?.ok) {
      router.push('/');
    }
  } catch (error) {
    console.error('打开项目失败:', error);
  }
};

const handleImport = async () => {
  try {
    const result = await projectLauncherService.openProjectFile();
    if (result?.data?.path) {
      await handleOpenProject(result.data.path);
    }
  } catch (error) {
    console.error('打开现有项目失败:', error);
  }
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
