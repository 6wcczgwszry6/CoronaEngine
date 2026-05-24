<template>
  <div class="navigat-bar">
    <button class="nav-btn" @click="handleNewClick">新建</button>
    <button class="nav-btn" @click="handleSaveClick">保存</button>
    <button class="nav-btn" @click="handleOpenClick">打开</button>
    <div class="flex-1"></div>
    <button class="nav-btn" @click="handleSearchClick">查找</button>
    <button class="nav-btn" @click="handleSettingsClick">设置</button>
    <Settings ref="settingsModal" />
  </div>
</template>

<script setup>
import * as Blockly from 'blockly/core';
import { ref } from 'vue';
import { useStore } from '../store/store';
import { currentSceneName, currentActorName } from '../composables/useActorContext';
import Settings from './Settings.vue';

const store = useStore();
const settingsModal = ref();
const emit = defineEmits(['new-canvas']);

function handleNewClick() {
  const actor = currentActorName.value || '未选择物体';
  if (!confirm(`确定要清空「${actor}」的所有积木吗？此操作不可恢复。`)) return;

  // 通知 BlocklyWorkspace 处理持久化状态清理
  emit('new-canvas');
}

function handleSearchClick() {
  store.searchVisible.value = !store.searchVisible.value;
}

function handleSettingsClick() {
  settingsModal.value.handleClick();
}

async function handleSaveClick() {
  if (!store.workspace.value) return;
  const data = Blockly.serialization.workspaces.save(store.workspace.value);
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });

  if (window.showSaveFilePicker) {
    try {
      const opts = {
        types: [{ description: 'Blockly 项目文件', accept: { 'application/json': ['.blockly'] } }],
        suggestedName: `project_${Date.now()}.blockly`,
      };
      const handle = await window.showSaveFilePicker(opts);
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
    } catch {}
  } else {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `project_${Date.now()}.blockly`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    setTimeout(() => URL.revokeObjectURL(url), 150);
  }
}

function handleOpenClick() {
  const input = document.createElement('input');
  input.setAttribute('type', 'file');
  input.setAttribute('accept', '.blockly');
  input.addEventListener('change', function () {
    const file = this.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.blockly')) {
      alert('仅支持 .blockly 格式的文件');
      return;
    }
    if (!store.workspace.value) {
      alert('工作区尚未初始化');
      return;
    }
    const reader = new FileReader();
    reader.addEventListener('load', function () {
      let text = this.result;
      // 移除 BOM（UTF-8: EF BB BF → U+FEFF; UTF-16: U+FEFF）
      if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);

      // 第一步：解析 JSON
      let json;
      try {
        json = JSON.parse(text);
      } catch (e) {
        console.error('[Blockly] JSON 解析失败：', e, '文件内容前100字符：', text.slice(0, 100));
        alert('文件格式不正确，无法解析 JSON：' + (e.message || ''));
        return;
      }

      // 第二步：验证 JSON 结构（必须包含 blocks 字段）
      if (!json || typeof json !== 'object') {
        alert('文件格式不正确：JSON 根节点必须是对象');
        return;
      }
      if (!json.blocks) {
        console.warn('[Blockly] JSON 缺少 blocks 字段，尝试直接加载');
      }

      // 第三步：加载到工作区（Blockly load 内部会先 clear 各序列化器，无需手动 clear）
      try {
        Blockly.serialization.workspaces.load(json, store.workspace.value);
      } catch (e) {
        console.error('[Blockly] 工作区加载失败：', e);
        alert('工作区加载失败：' + (e.message || '未知错误'));
      }
    });
    reader.addEventListener('error', function () {
      alert('文件读取失败，请确认文件未损坏');
    });
    reader.readAsText(file, 'UTF-8');
  });
  input.click();
}
</script>

<style scoped>
.navigat-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px 6px;
  background: #2a2a2a;
  border-bottom: 1px solid #444;
}

.nav-btn {
  padding: 2px 10px;
  font-size: 12px;
  color: #ccc;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  line-height: 1.6;
}

.nav-btn:hover {
  color: #fff;
  background: #3a3a3a;
  border-color: #555;
}
</style>