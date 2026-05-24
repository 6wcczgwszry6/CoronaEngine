<template>
  <div>
    <div v-for="node in nodes" :key="node.path" class="tree-node">
      <div
        class="flex items-center gap-1 py-1 px-2 hover:bg-[#84a65b]/20 cursor-pointer group transition-colors rounded"
        :style="{ paddingLeft: level * 16 + 8 + 'px' }"
        @click="handleClick(node)"
        @dblclick="handleDoubleClick(node)"
        @contextmenu.prevent="handleContextMenu($event, node)"
      >
        <!-- 展开/收起图标（仅文件夹） -->
        <span v-if="node.isDirectory" class="w-4 text-center text-gray-400">
          {{ node.expanded ? '▼' : '▶' }}
        </span>
        <span v-else class="w-4"></span>

        <!-- 文件/文件夹图标 -->
        <span class="text-lg">{{ getIcon(node) }}</span>

        <!-- 名称 -->
        <div class="flex-1 min-w-0">
          <div class="text-xs truncate group-hover:text-white">{{ node.name }}</div>
          <div v-if="!node.isDirectory" class="text-[9px] text-gray-500">
            {{ formatSize(node.size) }} | {{ node.mtime }}
          </div>
        </div>
      </div>

      <!-- 子节点（递归） -->
      <FileTreeNode
        v-if="node.isDirectory && node.expanded && node.children"
        :nodes="node.children"
        :level="level + 1"
        @node-click="$emit('node-click', $event)"
        @node-dblclick="$emit('node-dblclick', $event)"
        @contextmenu="handleChildContextMenu"
        @refresh="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  nodes: {
    type: Array,
    default: () => [],
  },
  level: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(['node-click', 'node-dblclick', 'contextmenu', 'refresh']);

// 处理单击
const handleClick = (node) => {
  emit('node-click', node);
};

// 处理双击
const handleDoubleClick = (node) => {
  emit('node-dblclick', node);
};

// 处理右键菜单
const handleContextMenu = (event, node) => {
  emit('contextmenu', event, node);
};

// 处理子节点的右键菜单（确保事件正确传递）
const handleChildContextMenu = (event, node) => {
  emit('contextmenu', event, node);
};

// 获取图标
const getIcon = (node) => {
  if (node.isDirectory) return '📁';
  const ext = node.name.split('.').pop().toLowerCase();
  const iconMap = {
    scene: '🎬',
    actor: '👤',
    png: '🖼️',
    jpg: '🖼️',
    jpeg: '🖼️',
    gif: '🖼️',
    mp3: '🎵',
    wav: '🎵',
    mp4: '🎬',
    avi: '🎬',
    txt: '📝',
    json: '📊',
    xml: '📋',
    ini: '⚙️',
    py: '🐍',
    js: '📜',
    html: '🌐',
    css: '🎨',
  };
  return iconMap[ext] || '📄';
};

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};
</script>
