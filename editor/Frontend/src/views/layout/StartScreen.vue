<template>
  <div class="relative min-h-screen bg-[#0d0d0d] text-white flex flex-col items-center justify-center font-sans overflow-hidden">
    <!-- Background decorations -->
    <div class="absolute inset-0 bg-gradient-to-b from-[#1a2a1a]/30 via-transparent to-transparent pointer-events-none"></div>
    <div class="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-[#84a65b]/[0.03] rounded-full blur-3xl pointer-events-none"></div>
    <div class="absolute bottom-0 left-1/4 w-[400px] h-[400px] bg-[#84a65b]/[0.02] rounded-full blur-3xl pointer-events-none"></div>

    <!-- Top-left Logo -->
    <div class="absolute top-6 left-8 z-10">
      <img src="@/assets/announcement.png" alt="Logo" class="w-32 h-32 object-contain" />
    </div>

    <!-- Logo & Title -->
    <div class="relative z-10 text-center mb-20">
      <h1 class="text-9xl font-extrabold tracking-[0.15em] mb-6" style="color: #84a65b;">
        CORONA
      </h1>
      <h2 class="text-5xl font-bold tracking-[0.3em] text-gray-400 mb-5">
        ENGINE
      </h2>
      <div class="w-20 h-px bg-[#84a65b]/40 mx-auto"></div>
    </div>

    <!-- Buttons -->
    <div class="relative z-10 flex flex-col gap-6 w-full max-w-xl px-8">
      <button
        class="group relative py-6 px-8 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-[#84a65b]/60 rounded-xl text-2xl font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(132,166,91,0.10)]"
        @click="handleStoryMode"
      >
        <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-[#84a65b] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
        <span class="flex items-center justify-center gap-3">
          <svg class="w-6 h-6 text-[#84a65b]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5A2.5 2.5 0 0 1 4 19.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/><path d="M8 15h5"/></svg>
          <span>剧情模式</span>
        </span>
      </button>

      <button
        class="group relative py-6 px-8 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-[#84a65b]/60 rounded-xl text-2xl font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(132,166,91,0.10)]"
        @click="handleCreativeMode"
      >
        <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-[#84a65b] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
        <span class="flex items-center justify-center gap-3">
          <svg class="w-6 h-6 text-[#84a65b]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z"/></svg>
          <span>创造模式</span>
        </span>
      </button>

      <button
        class="group relative py-6 px-8 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-[#84a65b]/60 rounded-xl text-2xl font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(132,166,91,0.10)]"
        @click="handleRecentGames"
      >
        <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-[#84a65b] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
        <span class="flex items-center justify-center gap-3">
          <svg class="w-6 h-6 text-[#84a65b]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <span>继续游戏</span>
        </span>
      </button>

      <div class="flex gap-6">
        <button
          class="group relative flex-1 py-5 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-[#84a65b]/60 rounded-xl text-lg font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(132,166,91,0.10)]"
        >
          <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-[#84a65b] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
          <span class="flex items-center justify-center gap-2">
            <svg class="w-5 h-5 text-[#84a65b]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            <span>选项/设置</span>
          </span>
        </button>

        <button
          class="group relative flex-1 py-5 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-[#84a65b]/60 rounded-xl text-lg font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(132,166,91,0.10)]"
        >
          <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-[#84a65b] rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
          <span class="flex items-center justify-center gap-2">
            <svg class="w-5 h-5 text-[#84a65b]/70" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            <span>登录/账户</span>
          </span>
        </button>
      </div>

      <button
        class="group relative py-6 px-8 bg-[#2a2a2a] border border-[#3a3a3a] hover:border-red-500/30 rounded-xl text-2xl font-medium transition-all duration-500 hover:bg-[#333333] hover:shadow-[0_0_40px_rgba(239,68,68,0.08)]"
        @click="handleExitGame"
      >
        <span class="absolute left-0 top-0 bottom-0 w-0.5 bg-red-500/50 rounded-l-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
        <span class="flex items-center justify-center gap-3">
          <svg class="w-6 h-6 text-gray-500 group-hover:text-red-400/70 transition-colors duration-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          <span>结束游戏</span>
        </span>
      </button>
    </div>

    <!-- Version -->
    <div class="relative z-10 mt-16 text-sm tracking-wider text-gray-700">
      v 1.2.0
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { appService } from '@/utils/bridge.js';

const router = useRouter();

function handleStoryMode() {
  router.push('/StoryMode');
}

function handleCreativeMode() {
  router.push('/CreateGame');
}

function handleRecentGames() {
  router.push('/RecentGames');
}

function handleExitGame() {
  appService.closeProcess();
}
</script>

<style scoped>
</style>
