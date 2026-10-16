<template>
  <div v-if="active && actor?.model_node_count > 0" class="model-node-hierarchy">
    <div class="model-node-title">模型节点（{{ actor.model_node_count }}）</div>
    <div v-if="loading && !flatRows.length" class="model-node-empty">正在读取节点…</div>
    <div v-else-if="!flatRows.length" class="model-node-empty">没有可编辑的模型节点</div>
    <div v-else ref="scrollElement" class="model-node-list" @scroll="onScroll">
      <div :style="{ height: `${flatRows.length * rowHeight}px` }"><div :style="{ transform: `translateY(${windowed.topSpacer}px)` }">
        <template v-for="row in renderedRows" :key="rowKey(row)">
          <button v-if="row.kind === 'more'" class="model-node-more" :style="{ paddingLeft: `${row.depth * 16 + 8}px` }" @click="loadMore(row.parentKey)">加载更多…</button>
          <div v-else class="model-node-line" :class="{ selected: isSelected(row.node), hidden: !row.node.effective_visible }" :style="{ paddingLeft: `${row.depth * 16 + 4}px` }" @click="select(row.node)">
            <button v-if="Number(row.node.child_count) > 0" class="model-node-button" @click.stop="toggleExpanded(row.node)">{{ expanded.has(Number(row.node.node_index)) ? '⌄' : '›' }}</button>
            <span v-else class="model-node-leaf">·</span><span class="model-node-name">{{ row.node.name || `节点 ${row.node.node_index}` }}</span>
            <button class="model-node-button" :title="row.node.visible ? '隐藏' : '显示'" @click.stop="toggleVisibility(row.node)">{{ row.node.visible ? '◉' : '○' }}</button>
          </div>
        </template>
      </div></div>
    </div>
    <div v-if="selectedNode" class="model-node-transform"><div class="model-node-title">局部变换</div>
      <label v-for="field in fields" :key="field.key">{{ field.label }}
        <span v-for="(value, axis) in selectedNode[field.key]" :key="axis"><input v-model.number="selectedNode[field.key][axis]" type="number" :step="field.step" @change="save(field.key)" /></span>
      </label>
    </div>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { editorApi } from '@/api/editorApi.js';
import { flattenLoadedNodes, virtualNodeWindow } from '@/utils/modelHierarchy.js';
const props = defineProps({ active: Boolean, sceneName: String, actor: Object, selection: Object });
const emit = defineEmits(['select']); const pageSize = 100; const rowHeight = 28;
const scrollElement = ref(null); const pages = ref({}); const expanded = ref(new Set()); const loading = ref(false); const scrollTop = ref(0); const viewportHeight = ref(280); let request = 0; let resizeObserver;
const fields = [{ key: 'position', label: '位置', step: 0.1 }, { key: 'rotation', label: '旋转', step: 1 }, { key: 'scale', label: '缩放', step: 0.05 }];
const flatRows = computed(() => flattenLoadedNodes(pages.value, expanded.value));
const windowed = computed(() => virtualNodeWindow(flatRows.value, scrollTop.value, viewportHeight.value, rowHeight));
const renderedRows = computed(() => flatRows.value.slice(windowed.value.start, windowed.value.end)); const actorName = computed(() => props.actor?.name || '');
const pageKey = (parentIndex) => String(parentIndex); const responseData = (result) => result?.data ?? result ?? {}; const rowKey = (row) => row.kind === 'more' ? `more-${row.parentKey}` : `node-${row.node.node_index}`;
const isSelected = (node) => Number(node.node_index) === Number(props.selection?.nodeIndex) && props.selection?.actorName === actorName.value;
const selectedNode = computed(() => flatRows.value.find((row) => row.node && isSelected(row.node))?.node || null);
const applyNode = (node) => { if (!node) return; const next = {}; for (const [key, page] of Object.entries(pages.value)) next[key] = { ...page, items: (page.items || []).map((item) => Number(item.node_index) === Number(node.node_index) ? { ...item, ...node } : item) }; pages.value = next; };
const loadPage = async (parentIndex, offset = 0) => { if (!props.active || !actorName.value) return; const key = pageKey(parentIndex); if (pages.value[key]?.loading) return; const token = ++request; pages.value = { ...pages.value, [key]: { ...(pages.value[key] || {}), loading: true } }; loading.value = true; try { const data = responseData(await editorApi.sceneTools.getModelNodes(props.sceneName, actorName.value, parentIndex, offset, pageSize)); if (token !== request) return; const previous = pages.value[key]?.items || []; const incoming = Array.isArray(data.nodes) ? data.nodes : []; pages.value = { ...pages.value, [key]: { items: offset ? [...previous, ...incoming] : incoming, has_more: data.has_more === true, next_offset: Number(data.next_offset || 0), loading: false } }; } catch { if (token === request) pages.value = { ...pages.value, [key]: { ...(pages.value[key] || {}), loading: false } }; } finally { if (token === request) loading.value = false; } };
const reset = () => { request++; pages.value = {}; expanded.value = new Set(); scrollTop.value = 0; };
const toggleExpanded = async (node) => { const index = Number(node.node_index); const next = new Set(expanded.value); if (next.has(index)) next.delete(index); else { next.add(index); if (!pages.value[pageKey(index)]) await loadPage(index); } expanded.value = next; };
const loadMore = (parentKey) => { const page = pages.value[parentKey]; return loadPage(Number(parentKey), Number(page?.next_offset || 0)); };
const select = (node) => emit('select', { actorName: actorName.value, nodeIndex: Number(node.node_index), node_index: Number(node.node_index) });
const toggleVisibility = async (node) => { const data = responseData(await editorApi.sceneTools.setModelNodeState(props.sceneName, actorName.value, Number(node.node_index), { visible: !node.visible })); applyNode(data.node); select(data.node || node); };
const save = async (key) => { const node = selectedNode.value; if (!node) return; const data = responseData(await editorApi.sceneTools.setModelNodeState(props.sceneName, actorName.value, Number(node.node_index), { [key]: [...node[key]] })); applyNode(data.node); };
const onScroll = (event) => { scrollTop.value = event.target.scrollTop; viewportHeight.value = event.target.clientHeight; };
watch(() => [props.active, props.sceneName, actorName.value], async () => { reset(); if (props.active && actorName.value) await loadPage(-1); }, { immediate: true });
onMounted(async () => { await nextTick(); if (scrollElement.value && typeof ResizeObserver !== 'undefined') { resizeObserver = new ResizeObserver(() => { viewportHeight.value = scrollElement.value?.clientHeight || 280; }); resizeObserver.observe(scrollElement.value); } }); onUnmounted(() => { request++; resizeObserver?.disconnect(); });
</script>
<style scoped>
.model-node-hierarchy{margin:2px 0 8px 18px;color:#bbb;font-size:11px}.model-node-title{color:#888;padding:4px 0}.model-node-empty{padding:4px;color:#777}.model-node-list{height:280px;overflow:auto;border:1px solid #333;border-radius:3px}.model-node-line,.model-node-more{height:28px;box-sizing:border-box;display:flex;gap:5px;align-items:center;width:100%;border:0;border-radius:3px;color:inherit;background:transparent;cursor:pointer;text-align:left}.model-node-line:hover,.model-node-more:hover{background:#333}.model-node-line.selected{background:#265c90;color:#fff}.model-node-line.hidden{opacity:.55}.model-node-button{border:0;background:transparent;color:inherit;cursor:pointer;width:16px}.model-node-leaf{width:16px;text-align:center}.model-node-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}.model-node-transform label{display:flex;align-items:center;gap:3px;margin:3px 0}.model-node-transform label>span{display:flex;width:33%}.model-node-transform input{width:100%;background:#262626;border:1px solid #444;color:#ddd;padding:2px}
</style>
