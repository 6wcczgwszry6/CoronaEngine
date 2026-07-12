<template>
  <div class="node-graph-workspace">
    <div class="ng-toolbar">
      <div class="ng-title">
        <span class="ng-badge">节点</span>
        <span class="ng-subtitle">{{ targetLabel }}</span>
        <span class="ng-save">{{ saveLabel }}</span>
      </div>
      <div class="ng-modes">
        <button
          type="button"
          class="ng-run"
          :class="{ running: codeRunning }"
          :disabled="runBusy"
          @click="handleToggleRun"
        >
          {{ codeRunning ? '停止' : '运行' }}
        </button>
        <span v-if="runStatus" class="ng-run-status">{{ runStatus }}</span>
        <button class="ng-mode" :class="{ active: mode === 'select' }" @click="setMode('select')">
          选择
        </button>
        <button
          class="ng-mode delete"
          :class="{ active: mode === 'delete' }"
          @click="setMode('delete')"
        >
          清除
        </button>
      </div>
    </div>
    <div v-if="!actorName" class="ng-empty">请先选中一个物体</div>
    <div v-else class="ng-body">
      <aside class="ng-panel ng-toolbox">
        <div class="ng-section-title">
          宏观节点
          <small>拖入中间</small>
        </div>
        <div
          class="ng-tool-card macro"
          draggable="true"
          @pointerdown.left="beginMacroPointerDrag($event, 'state')"
          @dragstart="startMacroDrag($event, 'state')"
        >
          <div class="ng-tool-icon">态</div>
          <div>
            <div class="ng-tool-name">状态节点</div>
            <div class="ng-tool-desc">开始 / 结束 / 自定义状态</div>
          </div>
        </div>
        <div class="ng-section-title mt">
          微观积木
          <small>Blockly 原生形状</small>
        </div>
        <BlocklyToolboxPalette
          class="ng-native-palette"
          @pick="handlePalettePick"
          @external-drag-start="handlePaletteDragStart"
          @external-drag-move="handlePaletteDragMove"
          @external-drag-end="handlePaletteDragEnd"
        />
      </aside>
      <main
        ref="canvasRef"
        class="ng-panel ng-canvas" :class="{ 'drop-active': macroDropActive }"
        @dragover.prevent
        @drop.prevent="handleCanvasDrop"
        @wheel.prevent="handleCanvasWheel"
        @pointermove="handleCanvasPointerMove"
        @pointerleave="handleCanvasPointerLeave"
        @click="handleCanvasClick"
      >
        <div class="ng-canvas-head">
          <div>
            <strong>节点编辑区</strong>
          </div>
          <div class="ng-canvas-actions">
            <span class="ng-pill">{{ nodes.length }} 节点 / {{ edges.length }} 连线</span>
            <span class="ng-zoom-value">{{ zoomText }}</span>
            <button type="button" class="ng-zoom-reset" @click.stop="resetZoom">恢复 100%</button>
          </div>
        </div>
        <div class="ng-world" :style="worldStyle">
          <div class="ng-grid"></div>
          <svg class="ng-edges" :width="canvasSize.width" :height="canvasSize.height">
          <defs>
            <marker
              id="ng-arrow"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path d="M0,0 L0,6 L9,3 z" fill="#60a5fa" />
            </marker>
          </defs>
          <path
            v-if="pendingEdgePath"
            class="ng-edge-preview"
            :d="pendingEdgePath"
          />
          <g v-for="edge in edges" :key="edge.id">
            <path
              class="ng-edge-hit"
              :d="edgePath(edge)"
              @click.stop="handleEdgeClick(edge)"
              @dblclick.stop="renameEdge(edge)"
            />
            <path
              class="ng-edge-line"
              :class="{
                selected: selectedKind === 'edge' && selectedId === edge.id,
                delete: mode === 'delete',
              }"
              :d="edgePath(edge)"
              marker-end="url(#ng-arrow)"
            />
          </g>
        </svg>
        <div
          v-for="edge in edges"
          :key="`${edge.id}-condition`"
          class="ng-condition-block"
          :class="{ selected: selectedKind === 'edge' && selectedId === edge.id }"
          :style="conditionStyle(edge)"
          @click.stop="selectEdge(edge)"
          @dblclick.stop="renameEdge(edge)"
        >
          {{ edge.name || '条件' }}
        </div>
        <div
          v-for="node in nodes"
          :key="node.id"
          class="ng-node"
          :class="[
            `type-${node.nodeType}`,
            {
              selected: selectedKind === 'node' && selectedId === node.id,
              delete: mode === 'delete',
            },
          ]"
          :style="nodeStyle(node)"
          @mousedown.left="startNodeDrag($event, node)"
          @click.stop="handleNodeClick(node)"
        >
          <div class="ng-node-head">
            <span class="ng-node-dot"></span>
            <select
              v-model="node.nodeType"
              class="ng-node-type"
              @change="onNodeTypeChange(node)"
              @mousedown.stop
              @click.stop
            >
              <option value="start">开始节点</option>
              <option value="end">结束节点</option>
              <option value="custom">自定义</option>
            </select>
          </div>
          <input
            v-if="node.nodeType === 'custom'"
            v-model="node.name"
            class="ng-node-name"
            placeholder="自定义名称"
            @input="scheduleSave"
            @mousedown.stop
            @click.stop
          />
          <div v-else class="ng-node-fixed-name">{{ nodeTypeLabel(node.nodeType) }}</div>
          <div class="ng-node-hint">点击编辑内部积木</div>
          <template v-if="selectedKind === 'node' && selectedId === node.id">
            <button
              v-for="port in visiblePorts(node)"
              :key="`${node.id}-${port.side}-${port.index}`"
              type="button"
              class="ng-port"
              :class="[
                port.side,
                {
                  occupied: isPortUsed(node.id, port),
                  pending:
                    pendingPort &&
                    pendingPort.nodeId === node.id &&
                    pendingPort.side === port.side &&
                    pendingPort.index === port.index,
                },
              ]"
              :style="portStyle(node, port)"
              :title="isPortUsed(node.id, port) ? '已连接' : '空连接点'"
              @click.stop="handlePortClick(node, port)"
            ></button>
          </template>
        </div>
        </div>
      </main>
      <aside class="ng-panel ng-inspector">
        <section class="ng-vars">
          <div class="ng-section-title">
            全局变量池
            <small>变量和列表在节点图启动时初始化</small>
          </div>
          <MiniBlocklyWorkspace
            ref="variablesBlocklyRef"
            :workspace-key="`${targetKey}:globals`"
            :initial-state="graph.globalVariablesWorkspace"
            :delete-mode="mode === 'delete'"
            @change="onGlobalWorkspaceChange"
          />
        </section>
        <section class="ng-editor">
          <div class="ng-section-title">
            {{ activeEditorTitle }}
            <small>{{ activeEditorSubtitle }}</small>
          </div>
          <MiniBlocklyWorkspace
            v-if="activeEditorKey"
            ref="activeBlocklyRef"
            :key="activeEditorKey"
            :workspace-key="activeEditorKey"
            :initial-state="activeEditorState"
            :delete-mode="mode === 'delete'"
            @change="onActiveWorkspaceChange"
          />
          <div v-else class="ng-editor-empty">选择节点或连线后可编辑内部积木</div>
        </section>
      </aside>
    </div>
    <div
      v-if="externalDrag.active"
      class="ng-drag-ghost"
      :style="dragGhostStyle"
    >
      {{ externalDrag.label }}
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import MiniBlocklyWorkspace from '@/blockly/components/MiniBlocklyWorkspace.vue';
import BlocklyToolboxPalette from '@/blockly/components/BlocklyToolboxPalette.vue';
import { useErrorHandler } from '@/composables/useErrorHandler.js';
import { scriptingService } from '@/utils/bridge.js';
import { nodeGraphToCode } from '@/blockly/generators/index.js';

const props = defineProps({
  actorName: { type: String, default: '' },
  sceneName: { type: String, default: '' },
  targetType: { type: String, default: 'actor' },
});
const { error: logError } = useErrorHandler('NodeGraphWorkspace');
const NODE_WIDTH = 170,
  NODE_BASE_HEIGHT = 98,
  NODE_PORT_GAP = 20,
  SAVE_DELAY = 900;
const mode = ref('select'),
  selectedKind = ref(''),
  selectedId = ref(''),
  pendingPort = ref(null),
  saveLabel = ref('');
const canvasRef = ref(null),
  variablesBlocklyRef = ref(null),
  activeBlocklyRef = ref(null);
const canvasSize = reactive({ width: 900, height: 520 });
const viewport = reactive({ scale: 1, offsetX: 0, offsetY: 0 });
const connectionPointer = reactive({ active: false, x: 0, y: 0 });
const graph = reactive({ version: 1, nodes: [], edges: [], globalVariablesWorkspace: {} });
const codeRunning = ref(false);
const runBusy = ref(false);
const runStatus = ref('');
const macroDropActive = ref(false);
const externalDrag = reactive({
  active: false,
  kind: '',
  blockType: '',
  macroType: '',
  label: '',
  clientX: 0,
  clientY: 0,
  pointerId: null,
});
const zoomText = computed(() => `${Math.round(viewport.scale * 100)}%`);
const dragGhostStyle = computed(() => ({
  left: `${externalDrag.clientX + 14}px`,
  top: `${externalDrag.clientY + 14}px`,
}));
const worldStyle = computed(() => ({
  width: `${canvasSize.width}px`,
  height: `${canvasSize.height}px`,
  transform: `translate(${viewport.offsetX}px, ${viewport.offsetY}px) scale(${viewport.scale})`,
  transformOrigin: '0 0',
}));
let isLoading = false,
  saveTimer = null,
  resizeObserver = null,
  dragState = null,
  macroPointerDrag = null,
  runPollTimer = null,
  startedRunForTarget = false;
const targetKey = computed(
  () => `${props.targetType || 'actor'}:${props.sceneName || ''}:${props.actorName || ''}`
);
const targetLabel = computed(() =>
  props.actorName ? `${props.actorName} [${props.sceneName || '未命名场景'}]` : '未选择目标'
);
const nodes = computed(() => graph.nodes),
  edges = computed(() => graph.edges);
const selectedNode = computed(() =>
  selectedKind.value === 'node' ? graph.nodes.find((n) => n.id === selectedId.value) : null
);
const selectedEdge = computed(() =>
  selectedKind.value === 'edge' ? graph.edges.find((e) => e.id === selectedId.value) : null
);
const pendingEdgePath = computed(() => {
  if (!pendingPort.value || !connectionPointer.active) return '';
  const node = graph.nodes.find((item) => item.id === pendingPort.value.nodeId);
  if (!node) return '';
  const source = portPoint(node, pendingPort.value);
  return previewEdgePath(source, connectionPointer, pendingPort.value.side);
});
const activeEditorKey = computed(() =>
  selectedNode.value
    ? `${targetKey.value}:node:${selectedNode.value.id}`
    : selectedEdge.value
      ? `${targetKey.value}:edge:${selectedEdge.value.id}:condition`
      : ''
);
const activeEditorState = computed(() =>
  selectedNode.value
    ? selectedNode.value.workspace || {}
    : selectedEdge.value
      ? selectedEdge.value.conditionWorkspace || {}
      : {}
);
const activeEditorTitle = computed(() =>
  selectedNode.value
    ? `节点内部编辑：${displayNodeName(selectedNode.value)}`
    : selectedEdge.value
      ? `连线条件编辑：${selectedEdge.value.name || '未命名连线'}`
      : '节点内部编辑'
);
const activeEditorSubtitle = computed(() =>
  selectedNode.value
    ? '拖入微观积木编辑该节点'
    : selectedEdge.value
      ? '拖入微观积木编辑条件块'
      : '未选择'
);
function setMode(v) {
  mode.value = v;
  pendingPort.value = null;
  connectionPointer.active = false;
}
function dragData(event, payload, text) {
  event.dataTransfer?.setData('application/x-corona-nodegraph', JSON.stringify(payload));
  event.dataTransfer?.setData('text/plain', text);
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy';
}
function startMacroDrag(e, macroType) {
  dragData(e, { kind: 'macro-node', macroType }, `macro-node:${macroType}`);
}
function pointInCanvas(clientX, clientY) {
  const rect = canvasRef.value?.getBoundingClientRect?.();
  return Boolean(
    rect &&
      clientX >= rect.left &&
      clientX <= rect.right &&
      clientY >= rect.top &&
      clientY <= rect.bottom
  );
}
function addMacroNodeAt(macroType, clientX, clientY) {
  if (!pointInCanvas(clientX, clientY)) return false;
  const world = screenToWorld(clientX, clientY);
  const node = {
    id: makeId('node'),
    macroType: macroType || 'state',
    nodeType: graph.nodes.length === 0 ? 'start' : 'custom',
    name: graph.nodes.length === 0 ? '开始' : `状态${graph.nodes.length + 1}`,
    x: Math.max(20, world.x - NODE_WIDTH / 2),
    y: Math.max(54, world.y - 32),
    workspace: {},
  };
  graph.nodes.push(node);
  selectNode(node);
  scheduleSave();
  return true;
}
function clearMacroPointerListeners() {
  window.removeEventListener('pointermove', moveMacroPointerDrag, true);
  window.removeEventListener('pointerup', finishMacroPointerDrag, true);
  window.removeEventListener('pointercancel', cancelMacroPointerDrag, true);
}
function beginMacroPointerDrag(event, macroType) {
  if (event.button !== 0) return;
  macroPointerDrag = {
    pointerId: event.pointerId,
    macroType,
    startX: event.clientX,
    startY: event.clientY,
    started: false,
  };
  event.preventDefault();
  window.addEventListener('pointermove', moveMacroPointerDrag, true);
  window.addEventListener('pointerup', finishMacroPointerDrag, true);
  window.addEventListener('pointercancel', cancelMacroPointerDrag, true);
}
function moveMacroPointerDrag(event) {
  if (!macroPointerDrag || event.pointerId !== macroPointerDrag.pointerId) return;
  const distance = Math.hypot(
    event.clientX - macroPointerDrag.startX,
    event.clientY - macroPointerDrag.startY
  );
  if (!macroPointerDrag.started && distance < 5) return;
  macroPointerDrag.started = true;
  externalDrag.active = true;
  externalDrag.kind = 'macro';
  externalDrag.macroType = macroPointerDrag.macroType;
  externalDrag.label = '状态节点';
  externalDrag.clientX = event.clientX;
  externalDrag.clientY = event.clientY;
  externalDrag.pointerId = event.pointerId;
  macroDropActive.value = pointInCanvas(event.clientX, event.clientY);
  event.preventDefault();
}
function finishMacroPointerDrag(event) {
  if (!macroPointerDrag || event.pointerId !== macroPointerDrag.pointerId) return;
  const drag = macroPointerDrag;
  macroPointerDrag = null;
  clearMacroPointerListeners();
  if (drag.started) addMacroNodeAt(drag.macroType, event.clientX, event.clientY);
  clearExternalDrag();
}
function cancelMacroPointerDrag(event) {
  if (!macroPointerDrag || (event?.pointerId != null && event.pointerId !== macroPointerDrag.pointerId)) return;
  macroPointerDrag = null;
  clearMacroPointerListeners();
  clearExternalDrag();
}
function clearWorkspaceDropHighlights() {
  activeBlocklyRef.value?.setDropActive?.(false);
  variablesBlocklyRef.value?.setDropActive?.(false);
}
function clearExternalDrag() {
  clearWorkspaceDropHighlights();
  macroDropActive.value = false;
  externalDrag.active = false;
  externalDrag.kind = '';
  externalDrag.blockType = '';
  externalDrag.macroType = '';
  externalDrag.label = '';
  externalDrag.pointerId = null;
}
function isGlobalWorkspaceBlock(blockType) {
  return (
    blockType === 'math_change' ||
    blockType.startsWith('variable') ||
    blockType.startsWith('variables_') ||
    blockType.startsWith('list_') ||
    blockType.startsWith('lists_')
  );
}
function updatePaletteDropTarget(clientX, clientY) {
  const activeHit = Boolean(activeBlocklyRef.value?.hitTest?.(clientX, clientY));
  const globalsHit = Boolean(
    isGlobalWorkspaceBlock(externalDrag.blockType) &&
      variablesBlocklyRef.value?.hitTest?.(clientX, clientY)
  );
  activeBlocklyRef.value?.setDropActive?.(activeHit);
  variablesBlocklyRef.value?.setDropActive?.(!activeHit && globalsHit);
  return activeHit ? activeBlocklyRef.value : globalsHit ? variablesBlocklyRef.value : null;
}
function handlePaletteDragStart(payload) {
  if (!payload?.blockType) return;
  externalDrag.active = true;
  externalDrag.kind = 'micro';
  externalDrag.blockType = payload.blockType;
  externalDrag.label = payload.blockType;
  externalDrag.clientX = payload.clientX;
  externalDrag.clientY = payload.clientY;
  updatePaletteDropTarget(payload.clientX, payload.clientY);
}
function handlePaletteDragMove(payload) {
  if (!externalDrag.active || externalDrag.kind !== 'micro') return;
  externalDrag.clientX = payload.clientX;
  externalDrag.clientY = payload.clientY;
  updatePaletteDropTarget(payload.clientX, payload.clientY);
}
function handlePaletteDragEnd(payload) {
  if (!externalDrag.active || externalDrag.kind !== 'micro') return;
  const target = payload?.cancelled ? null : updatePaletteDropTarget(payload.clientX, payload.clientY);
  if (target?.addBlock?.(payload.blockType, payload.clientX, payload.clientY)) {
    refreshEmbeddedWorkspaceStates();
    scheduleSave();
  }
  clearExternalDrag();
}
function handlePalettePick(blockType) {
  if (!blockType) return;
  const targetWorkspace = activeBlocklyRef.value ||
    (isGlobalWorkspaceBlock(blockType) ? variablesBlocklyRef.value : null);
  if (!targetWorkspace?.addBlock) {
    saveLabel.value = '\u8bf7\u5148\u9009\u62e9\u8282\u70b9\u6216\u8fde\u7ebf\uff1b\u5168\u5c40\u53d8\u91cf\u6c60\u53ea\u63a5\u53d7\u53d8\u91cf\u548c\u5217\u8868\u79ef\u6728';
    return;
  }
  targetWorkspace.addBlock(blockType);
  refreshEmbeddedWorkspaceStates();
  scheduleSave();
}
function makeId(p) {
  return `${p}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}
function screenToWorld(clientX, clientY) {
  const r = canvasRef.value?.getBoundingClientRect?.();
  if (!r) return { x: 0, y: 0 };
  return {
    x: (clientX - r.left - viewport.offsetX) / viewport.scale,
    y: (clientY - r.top - viewport.offsetY) / viewport.scale,
  };
}
function handleCanvasWheel(e) {
  if (!canvasRef.value) return;
  const r = canvasRef.value.getBoundingClientRect();
  const localX = e.clientX - r.left;
  const localY = e.clientY - r.top;
  const world = screenToWorld(e.clientX, e.clientY);
  const factor = e.deltaY < 0 ? 1.1 : 0.9;
  const nextScale = Math.min(2, Math.max(0.4, viewport.scale * factor));
  if (Math.abs(nextScale - viewport.scale) < 0.0001) return;
  viewport.scale = nextScale;
  viewport.offsetX = localX - world.x * nextScale;
  viewport.offsetY = localY - world.y * nextScale;
}
function resetZoom() {
  viewport.scale = 1;
  viewport.offsetX = 0;
  viewport.offsetY = 0;
}
function handleCanvasDrop(e) {
  const raw = e.dataTransfer?.getData('application/x-corona-nodegraph');
  if (!raw) return;
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    return;
  }
  if (payload?.kind === 'macro-node') addMacroNodeAt(payload.macroType, e.clientX, e.clientY);
}
function handleCanvasPointerMove(event) {
  if (!pendingPort.value) return;
  const world = screenToWorld(event.clientX, event.clientY);
  connectionPointer.x = world.x;
  connectionPointer.y = world.y;
  connectionPointer.active = true;
}
function handleCanvasPointerLeave() {
  connectionPointer.active = false;
}
function handleCanvasClick() {
  if (mode.value !== 'delete') {
    pendingPort.value = null;
    connectionPointer.active = false;
  }
}
function handleNodeClick(node) {
  if (mode.value === 'delete') {
    deleteNode(node.id);
    return;
  }
  selectNode(node);
}
function syncActiveBeforeSelection(nextKind, nextId) {
  if (
    selectedKind.value &&
    selectedId.value &&
    (selectedKind.value !== nextKind || selectedId.value !== nextId)
  )
    refreshEmbeddedWorkspaceStates();
}
function selectNode(node) {
  syncActiveBeforeSelection('node', node.id);
  selectedKind.value = 'node';
  selectedId.value = node.id;
  pendingPort.value = null;
  connectionPointer.active = false;
  nextTick(() => activeBlocklyRef.value?.resizeBlockly?.());
}
function selectEdge(edge) {
  if (mode.value === 'delete') {
    deleteEdge(edge.id);
    return;
  }
  syncActiveBeforeSelection('edge', edge.id);
  selectedKind.value = 'edge';
  selectedId.value = edge.id;
  pendingPort.value = null;
  connectionPointer.active = false;
  nextTick(() => activeBlocklyRef.value?.resizeBlockly?.());
}
function handleEdgeClick(edge) {
  if (mode.value === 'delete') {
    deleteEdge(edge.id);
    return;
  }
  selectEdge(edge);
}
function deleteNode(id) {
  const i = graph.nodes.findIndex((n) => n.id === id);
  if (i < 0) return;
  graph.nodes.splice(i, 1);
  graph.edges = graph.edges.filter((e) => e.source.nodeId !== id && e.target.nodeId !== id);
  if (selectedId.value === id) {
    selectedKind.value = '';
    selectedId.value = '';
  }
  pendingPort.value = null;
  scheduleSave();
}
function deleteEdge(id) {
  const i = graph.edges.findIndex((e) => e.id === id);
  if (i < 0) return;
  graph.edges.splice(i, 1);
  if (selectedKind.value === 'edge' && selectedId.value === id) {
    selectedKind.value = '';
    selectedId.value = '';
  }
  pendingPort.value = null;
  scheduleSave();
}
function renameEdge(edge) {
  if (mode.value === 'delete') return;
  const v = window.prompt('连线名称', edge.name || '');
  if (v === null) return;
  edge.name = v.trim();
  selectEdge(edge);
  scheduleSave();
}
function onNodeTypeChange(node) {
  if (node.nodeType === 'start' && !node.name) node.name = '开始';
  if (node.nodeType === 'end' && !node.name) node.name = '结束';
  if (node.nodeType === 'custom' && (!node.name || node.name === '开始' || node.name === '结束'))
    node.name = '自定义节点';
  scheduleSave();
}
function nodeTypeLabel(t) {
  return t === 'start' ? '开始节点' : t === 'end' ? '结束节点' : '自定义';
}
function displayNodeName(n) {
  return n ? (n.nodeType === 'custom' ? n.name || '自定义节点' : nodeTypeLabel(n.nodeType)) : '';
}
function nodeHeight(node) {
  const sidePortCount = Math.max(
    ...['left', 'right'].map(
      (side) => visiblePorts(node).filter((port) => port.side === side).length
    ),
    1
  );
  return Math.max(NODE_BASE_HEIGHT, 70 + sidePortCount * NODE_PORT_GAP);
}
function nodeStyle(n) {
  return {
    left: `${n.x}px`,
    top: `${n.y}px`,
    width: `${NODE_WIDTH}px`,
    minHeight: `${nodeHeight(n)}px`,
  };
}
function startNodeDrag(e, node) {
  if (mode.value !== 'select') return;
  if (e.target?.closest?.('input,select,button,.ng-port')) return;
  selectNode(node);
  const world = screenToWorld(e.clientX, e.clientY);
  dragState = { node, offsetX: world.x - node.x, offsetY: world.y - node.y };
  window.addEventListener('mousemove', onDragMove);
  window.addEventListener('mouseup', stopNodeDrag, { once: true });
}
function onDragMove(e) {
  if (!dragState || !canvasRef.value) return;
  const world = screenToWorld(e.clientX, e.clientY);
  dragState.node.x = Math.max(
    8,
    Math.min(canvasSize.width - NODE_WIDTH - 8, world.x - dragState.offsetX)
  );
  dragState.node.y = Math.max(
    48,
    Math.min(canvasSize.height - NODE_BASE_HEIGHT - 8, world.y - dragState.offsetY)
  );
}
function stopNodeDrag() {
  if (dragState) scheduleSave();
  dragState = null;
  window.removeEventListener('mousemove', onDragMove);
}
function usedPortIndexes(id, side) {
  const a = [];
  for (const e of graph.edges) {
    if (e.source.nodeId === id && e.source.side === side) a.push(e.source.index || 0);
    if (e.target.nodeId === id && e.target.side === side) a.push(e.target.index || 0);
  }
  return a;
}
function visiblePorts(node) {
  const ports = [];
  for (const side of ['left', 'right', 'bottom']) {
    const used = usedPortIndexes(node.id, side);
    const count = Math.max(1, Math.max(-1, ...used) + 2);
    for (let index = 0; index < count; index++) ports.push({ side, index });
  }
  return ports;
}
function isPortUsed(id, p) {
  return graph.edges.some(
    (e) =>
      (e.source.nodeId === id && e.source.side === p.side && (e.source.index || 0) === p.index) ||
      (e.target.nodeId === id && e.target.side === p.side && (e.target.index || 0) === p.index)
  );
}
function portStyle(node, p) {
  const pt = portPoint(node, p);
  return { left: `${pt.x - node.x - 6}px`, top: `${pt.y - node.y - 6}px` };
}
function portPoint(node, p) {
  const h = nodeHeight(node);
  if (p.side === 'left') return { x: node.x, y: node.y + 34 + p.index * NODE_PORT_GAP };
  if (p.side === 'right')
    return { x: node.x + NODE_WIDTH, y: node.y + 34 + p.index * NODE_PORT_GAP };
  const n = visiblePorts(node).filter((i) => i.side === 'bottom').length;
  return { x: node.x + (NODE_WIDTH / (n + 1)) * (p.index + 1), y: node.y + h };
}
function handlePortClick(node, p) {
  if (mode.value === 'delete' || isPortUsed(node.id, p)) return;
  const clicked = { nodeId: node.id, side: p.side, index: p.index };
  if (!pendingPort.value) {
    pendingPort.value = clicked;
    const point = portPoint(node, p);
    connectionPointer.x = point.x;
    connectionPointer.y = point.y;
    connectionPointer.active = true;
    return;
  }
  if (
    pendingPort.value.nodeId === clicked.nodeId &&
    pendingPort.value.side === clicked.side &&
    pendingPort.value.index === clicked.index
  ) {
    pendingPort.value = null;
    connectionPointer.active = false;
    return;
  }
  graph.edges.push({
    id: makeId('edge'),
    source: { ...pendingPort.value },
    target: clicked,
    name: '',
    conditionWorkspace: {},
  });
  pendingPort.value = null;
  connectionPointer.active = false;
  scheduleSave();
}
function getNode(id) {
  return graph.nodes.find((n) => n.id === id);
}
function edgeEndpoints(e) {
  const s = getNode(e.source.nodeId),
    t = getNode(e.target.nodeId);
  if (!s || !t) return null;
  return { source: portPoint(s, e.source), target: portPoint(t, e.target) };
}
function portVector(side) {
  if (side === 'left') return { x: -1, y: 0 };
  if (side === 'right') return { x: 1, y: 0 };
  return { x: 0, y: 1 };
}
function edgeCurve(source, target, sourceSide, targetSide) {
  const distance = Math.hypot(target.x - source.x, target.y - source.y);
  const handle = Math.max(52, Math.min(220, distance * 0.42));
  const sourceVector = portVector(sourceSide);
  const targetVector = portVector(targetSide);
  return {
    source,
    target,
    control1: {
      x: source.x + sourceVector.x * handle,
      y: source.y + sourceVector.y * handle,
    },
    control2: {
      x: target.x + targetVector.x * handle,
      y: target.y + targetVector.y * handle,
    },
  };
}
function curvePath(curve) {
  return `M ${curve.source.x} ${curve.source.y} C ${curve.control1.x} ${curve.control1.y}, ${curve.control2.x} ${curve.control2.y}, ${curve.target.x} ${curve.target.y}`;
}
function cubicPoint(curve, t = 0.5) {
  const mt = 1 - t;
  return {
    x:
      mt * mt * mt * curve.source.x +
      3 * mt * mt * t * curve.control1.x +
      3 * mt * t * t * curve.control2.x +
      t * t * t * curve.target.x,
    y:
      mt * mt * mt * curve.source.y +
      3 * mt * mt * t * curve.control1.y +
      3 * mt * t * t * curve.control2.y +
      t * t * t * curve.target.y,
  };
}
function edgeCurveFor(e) {
  const p = edgeEndpoints(e);
  return p ? edgeCurve(p.source, p.target, e.source.side, e.target.side) : null;
}
function edgePath(e) {
  const curve = edgeCurveFor(e);
  return curve ? curvePath(curve) : '';
}
function previewEdgePath(source, target, sourceSide) {
  const distance = Math.hypot(target.x - source.x, target.y - source.y);
  const handle = Math.max(48, Math.min(180, distance * 0.4));
  const sourceVector = portVector(sourceSide);
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  return curvePath({
    source,
    target,
    control1: {
      x: source.x + sourceVector.x * handle,
      y: source.y + sourceVector.y * handle,
    },
    control2: {
      x: target.x - (dx / length) * handle,
      y: target.y - (dy / length) * handle,
    },
  });
}
function edgeMidpoint(e) {
  const curve = edgeCurveFor(e);
  return curve ? cubicPoint(curve, 0.5) : { x: 0, y: 0 };
}
function conditionStyle(e) {
  const p = edgeMidpoint(e);
  return { left: `${p.x - 56}px`, top: `${p.y - 17}px` };
}
function onGlobalWorkspaceChange(s) {
  if (isLoading) return;
  graph.globalVariablesWorkspace = s || {};
  scheduleSave();
}
function onActiveWorkspaceChange(s) {
  if (isLoading) return;
  if (selectedNode.value) selectedNode.value.workspace = s || {};
  if (selectedEdge.value) selectedEdge.value.conditionWorkspace = s || {};
  scheduleSave();
}
function refreshEmbeddedWorkspaceStates() {
  const g = variablesBlocklyRef.value?.getState?.();
  if (g) graph.globalVariablesWorkspace = g;
  const a = activeBlocklyRef.value?.getState?.();
  if (a) {
    if (selectedNode.value) selectedNode.value.workspace = a;
    if (selectedEdge.value) selectedEdge.value.conditionWorkspace = a;
  }
}
function graphSnapshot() {
  refreshEmbeddedWorkspaceStates();
  try {
    return JSON.parse(
      JSON.stringify({
        version: 1,
        nodes: graph.nodes,
        edges: graph.edges,
        globalVariablesWorkspace: graph.globalVariablesWorkspace || {},
      })
    );
  } catch {
    return { version: 1, nodes: [], edges: [], globalVariablesWorkspace: {} };
  }
}
function normalizeEndpoint(e) {
  return {
    nodeId: e.nodeId || '',
    side: ['left', 'right', 'bottom'].includes(e.side) ? e.side : 'right',
    index: Number.isFinite(Number(e.index)) ? Number(e.index) : 0,
  };
}
function normalizeGraph(raw) {
  const n = raw && typeof raw === 'object' ? raw : {};
  return {
    version: 1,
    nodes: Array.isArray(n.nodes)
      ? n.nodes.map((node, i) => ({
          id: node.id || makeId('node'),
          macroType: node.macroType || 'state',
          nodeType: ['start', 'end', 'custom'].includes(node.nodeType)
            ? node.nodeType
            : i === 0
              ? 'start'
              : 'custom',
          name: node.name || (i === 0 ? '开始' : `状态${i + 1}`),
          x: Number.isFinite(Number(node.x)) ? Number(node.x) : 40 + i * 24,
          y: Number.isFinite(Number(node.y)) ? Number(node.y) : 80 + i * 24,
          workspace: node.workspace && typeof node.workspace === 'object' ? node.workspace : {},
        }))
      : [],
    edges: Array.isArray(n.edges)
      ? n.edges
          .filter((e) => e?.source && e?.target)
          .map((e) => ({
            id: e.id || makeId('edge'),
            source: normalizeEndpoint(e.source),
            target: normalizeEndpoint(e.target),
            name: e.name || '',
            conditionWorkspace:
              e.conditionWorkspace && typeof e.conditionWorkspace === 'object'
                ? e.conditionWorkspace
                : {},
          }))
      : [],
    globalVariablesWorkspace:
      n.globalVariablesWorkspace && typeof n.globalVariablesWorkspace === 'object'
        ? n.globalVariablesWorkspace
        : {},
  };
}
function getNodeFrom(list, id) {
  return list.find((n) => n.id === id);
}
function applyGraph(next) {
  graph.version = 1;
  graph.nodes = next.nodes;
  graph.edges = next.edges.filter(
    (e) => getNodeFrom(next.nodes, e.source.nodeId) && getNodeFrom(next.nodes, e.target.nodeId)
  );
  graph.globalVariablesWorkspace = next.globalVariablesWorkspace || {};
  selectedKind.value = graph.nodes.length ? 'node' : '';
  selectedId.value = graph.nodes[0]?.id || '';
  pendingPort.value = null;
}
function scheduleSave() {
  if (isLoading || !props.actorName) return;
  saveLabel.value = '未保存';
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveTimer = null;
    saveNow();
  }, SAVE_DELAY);
}
function storageKeyForTarget(target) {
  return `corona-nodegraph-ui:${target.targetType || 'actor'}:${target.sceneName || ''}:${target.actorName || ''}`;
}
function currentTarget() {
  return {
    targetType: props.targetType || 'actor',
    sceneName: props.sceneName || '',
    actorName: props.actorName || '',
  };
}
async function saveNow(targetOverride = null) {
  if (isLoading) return false;
  const target = targetOverride || currentTarget();
  if (!target.actorName) return false;
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  try {
    window.localStorage?.setItem(storageKeyForTarget(target), JSON.stringify(graphSnapshot()));
    saveLabel.value = `\u672c\u5730\u5df2\u4fdd\u5b58 ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
    return true;
  } catch (e) {
    logError('\u4fdd\u5b58\u672c\u5730\u8282\u70b9\u56fe\u5931\u8d25', e);
    saveLabel.value = '\u672c\u5730\u4fdd\u5b58\u5931\u8d25';
    return false;
  }
}
async function loadGraphForCurrentTarget() {
  resetZoom();
  if (!props.actorName) {
    applyGraph(normalizeGraph({}));
    return;
  }
  isLoading = true;
  saveLabel.value = '\u672c\u5730\u52a0\u8f7d\u4e2d...';
  try {
    const raw = window.localStorage?.getItem(storageKeyForTarget(currentTarget()));
    applyGraph(normalizeGraph(raw ? JSON.parse(raw) : {}));
    saveLabel.value = raw ? '\u672c\u5730\u5df2\u52a0\u8f7d' : '\u65b0\u8282\u70b9\u56fe\uff08\u672c\u5730\uff09';
  } catch (e) {
    logError('\u52a0\u8f7d\u672c\u5730\u8282\u70b9\u56fe\u5931\u8d25', e);
    applyGraph(normalizeGraph({}));
    saveLabel.value = '\u672c\u5730\u52a0\u8f7d\u5931\u8d25';
  } finally {
    isLoading = false;
    await nextTick();
    variablesBlocklyRef.value?.loadState?.(graph.globalVariablesWorkspace || {});
    activeBlocklyRef.value?.loadState?.(activeEditorState.value || {});
    updateCanvasSize();
  }
}
function bridgeResult(response) {
  return response?.data?.data ?? response?.data ?? response ?? {};
}
function clearRunPoll() {
  if (runPollTimer) window.clearInterval(runPollTimer);
  runPollTimer = null;
}
function startRunPoll() {
  clearRunPoll();
  runPollTimer = window.setInterval(async () => {
    if (!codeRunning.value) return;
    try {
      const status = bridgeResult(await scriptingService.getScriptStatus());
      if (status?.status !== 'running') {
        clearRunPoll();
        codeRunning.value = false;
        startedRunForTarget = false;
        runStatus.value = status?.status === 'error' ? '执行失败' : '已结束';
      }
    } catch (error) {
      clearRunPoll();
      codeRunning.value = false;
      startedRunForTarget = false;
      runStatus.value = '状态查询失败';
      logError('查询节点图运行状态失败', error);
    }
  }, 500);
}
async function stopNodeGraphRun(statusText = '已停止') {
  clearRunPoll();
  if (!startedRunForTarget && !codeRunning.value) return;
  try {
    await scriptingService.stopScriptExecution();
  } catch (error) {
    logError('停止节点图失败', error);
  } finally {
    startedRunForTarget = false;
    codeRunning.value = false;
    runStatus.value = statusText;
  }
}
async function handleToggleRun() {
  if (runBusy.value) return;
  runBusy.value = true;
  try {
    if (codeRunning.value) {
      await stopNodeGraphRun('已停止');
      return;
    }
    if (!props.actorName) {
      runStatus.value = '请先选择运行目标';
      return;
    }
    refreshEmbeddedWorkspaceStates();
    await saveNow();
    let code;
    try {
      code = nodeGraphToCode(graphSnapshot());
    } catch (error) {
      runStatus.value = `生成失败：${error?.message || error}`;
      logError('生成节点图代码失败', error);
      return;
    }
    runStatus.value = '启动中...';
    const response = bridgeResult(
      await scriptingService.executePythonCode(
        code,
        0,
        props.sceneName || '',
        props.actorName,
        props.targetType || 'actor'
      )
    );
    if (response?.status === 'error' || response?.success === false) {
      throw new Error(response?.message || '后端拒绝执行节点图');
    }
    startedRunForTarget = true;
    codeRunning.value = true;
    runStatus.value = '运行中';
    startRunPoll();
  } catch (error) {
    startedRunForTarget = false;
    codeRunning.value = false;
    clearRunPoll();
    runStatus.value = `执行失败：${error?.message || error}`;
    logError('执行节点图失败', error);
  } finally {
    runBusy.value = false;
  }
}
function updateCanvasSize() {
  const r = canvasRef.value?.getBoundingClientRect?.();
  if (!r) return;
  canvasSize.width = Math.max(720, r.width);
  canvasSize.height = Math.max(520, r.height);
}
watch(
  () => [props.sceneName, props.actorName, props.targetType],
  async (_n, old) => {
    const oldTarget = {
      targetType: old?.[2] || 'actor',
      sceneName: old?.[0] || '',
      actorName: old?.[1] || '',
    };
    if (startedRunForTarget || codeRunning.value) await stopNodeGraphRun('已停止');
    clearExternalDrag();
    cancelMacroPointerDrag();
    if (oldTarget.actorName && !isLoading) await saveNow(oldTarget);
    runStatus.value = '';
    await loadGraphForCurrentTarget();
  },
  { immediate: true }
);
onMounted(() => {
  resizeObserver = new ResizeObserver(updateCanvasSize);
  if (canvasRef.value) resizeObserver.observe(canvasRef.value);
  updateCanvasSize();
});
onBeforeUnmount(() => {
  if (saveTimer) clearTimeout(saveTimer);
  saveNow();
  resizeObserver?.disconnect?.();
  clearRunPoll();
  clearExternalDrag();
  cancelMacroPointerDrag();
  if (startedRunForTarget || codeRunning.value) scriptingService.stopScriptExecution().catch(() => {});
  window.removeEventListener('mousemove', onDragMove);
  window.removeEventListener('mouseup', stopNodeDrag);
});
</script>

<style scoped>
.node-graph-workspace {
  height: 100%;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #dbe7f3;
  background: radial-gradient(circle at 28% 0, #1f2f46 0, #111923 42%, #0a0f15 100%);
  border: 1px solid #273244;
  border-radius: 12px;
}
.ng-toolbar {
  height: 42px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 10px;
  border-bottom: 1px solid #273244;
  background: rgba(26, 34, 45, 0.96);
}
.ng-title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.ng-badge {
  padding: 4px 9px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-weight: 800;
}
.ng-subtitle {
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ng-save {
  color: #94a3b8;
}
.ng-modes {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ng-run {
  height: 28px;
  min-width: 58px;
  padding: 0 13px;
  border: 1px solid #22c55e;
  border-radius: 8px;
  background: #166534;
  color: #f0fdf4;
  font-weight: 800;
  cursor: pointer;
}
.ng-run:hover:not(:disabled) {
  background: #15803d;
}
.ng-run.running {
  border-color: #fb7185;
  background: #9f1239;
}
.ng-run:disabled {
  opacity: 0.55;
  cursor: wait;
}
.ng-run-status {
  max-width: 240px;
  overflow: hidden;
  color: #cbd5e1;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ng-mode {
  height: 28px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #334155;
  background: #121922;
  color: #cbd5e1;
  cursor: pointer;
  font-size: 12px;
}
.ng-mode.active {
  background: #2563eb;
  border-color: #60a5fa;
  color: #fff;
}
.ng-mode.delete.active {
  background: #b91c1c;
  border-color: #f87171;
}
.ng-empty {
  height: 100%;
  display: grid;
  place-items: center;
  color: #94a3b8;
  font-size: 12px;
}
.ng-body {
  min-height: 0;
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: 300px minmax(360px, 1fr) 360px;
  gap: 8px;
  padding: 8px;
}
.ng-panel {
  min-height: 0;
  border: 1px solid #273244;
  background: rgba(16, 23, 33, 0.94);
  border-radius: 12px;
  overflow: hidden;
}
.ng-toolbox {
  padding: 10px;
  overflow: auto;
}
.ng-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 8px;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 800;
}
.ng-section-title.mt {
  margin-top: 14px;
}
.ng-section-title small {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 500;
}
.ng-tool-card {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 9px;
  margin-bottom: 8px;
  border-radius: 10px;
  border: 1px solid #2b3748;
  background: #17202b;
  cursor: grab;
}
.ng-tool-card.macro {
  border-color: rgba(96, 165, 250, 0.55);
}
.ng-tool-icon,
.ng-mini {
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #fff;
  font-weight: 900;
  background: #2563eb;
}
.ng-tool-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
}
.ng-tool-name {
  font-size: 13px;
  font-weight: 800;
  color: #f8fafc;
}
.ng-tool-desc {
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.35;
  color: #94a3b8;
}
.ng-cat {
  margin-bottom: 7px;
  border: 1px solid #263244;
  border-radius: 10px;
  overflow: hidden;
  background: #111923;
}
.ng-cat summary {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px;
  list-style: none;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}
.ng-cat summary::-webkit-details-marker {
  display: none;
}
.ng-cat-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #60a5fa;
}
.ng-count {
  margin-left: auto;
  color: #94a3b8;
  font-size: 10px;
}
.ng-block-list {
  display: grid;
  gap: 6px;
  padding: 0 7px 8px;
}
.ng-block-chip {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 7px;
  align-items: center;
  text-align: left;
  border: 1px solid #334155;
  background: #192331;
  color: #e5edf7;
  border-radius: 9px;
  padding: 6px;
  cursor: grab;
}
.ng-mini {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  font-size: 11px;
  background: #64748b;
}
.ng-block-chip b {
  display: block;
  font-size: 11px;
  line-height: 1.2;
}
.ng-block-chip small {
  display: block;
  margin-top: 1px;
  color: #8ca0b7;
  font-size: 9px;
  word-break: break-all;
}
.ng-canvas {
  position: relative;
  overflow: hidden;
  background: #0d131b;
  transition: box-shadow 120ms ease, border-color 120ms ease;
}
.ng-canvas.drop-active {
  border-color: #60a5fa;
  box-shadow: inset 0 0 0 3px rgba(96, 165, 250, 0.25);
}
.ng-drag-ghost {
  position: fixed;
  z-index: 10000;
  max-width: 220px;
  padding: 8px 12px;
  border: 1px solid rgba(147, 197, 253, 0.8);
  border-radius: 9px;
  background: rgba(30, 64, 175, 0.88);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
  color: #eff6ff;
  font-size: 12px;
  font-weight: 800;
  pointer-events: none;
  transform: translateZ(0);
}
.ng-world {
  position: absolute;
  inset: 0 auto auto 0;
  will-change: transform;
}
.ng-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 24px 24px;
}
.ng-canvas-head {
  position: absolute;
  z-index: 5;
  left: 12px;
  top: 10px;
  right: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  pointer-events: none;
}
.ng-canvas-head strong {
  display: block;
  font-size: 14px;
}
.ng-canvas-head span {
  display: block;
  color: #94a3b8;
  font-size: 11px;
  margin-top: 2px;
}
.ng-canvas-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  pointer-events: auto;
}
.ng-zoom-value {
  margin-top: 0 !important;
  min-width: 42px;
  text-align: center;
  color: #dbeafe !important;
}
.ng-zoom-reset {
  height: 26px;
  padding: 0 9px;
  border: 1px solid #3b4b64;
  border-radius: 7px;
  background: #172033;
  color: #dbeafe;
  font-size: 11px;
  cursor: pointer;
}
.ng-zoom-reset:hover {
  border-color: #60a5fa;
}
.ng-pill {
  max-width: 44%;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #34435a;
  background: #172033;
  color: #cbd5e1 !important;
  font-size: 11px !important;
}
.ng-edges {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}
.ng-edge-hit {
  fill: none;
  stroke: transparent;
  stroke-width: 18;
  pointer-events: stroke;
  cursor: pointer;
}
.ng-edge-line {
  fill: none;
  stroke: #60a5fa;
  stroke-width: 2.4;
  filter: drop-shadow(0 0 5px rgba(96, 165, 250, 0.55));
  pointer-events: none;
}
.ng-edge-line.selected {
  stroke: #facc15;
  stroke-width: 3;
  filter: drop-shadow(0 0 4px rgba(250, 204, 21, 0.45));
}
.ng-edge-hit:hover + .ng-edge-line {
  stroke: #93c5fd;
  stroke-width: 3;
}
.ng-edge-preview {
  fill: none;
  stroke: #facc15;
  stroke-width: 2.4;
  stroke-dasharray: 8 6;
  pointer-events: none;
  filter: drop-shadow(0 0 4px rgba(250, 204, 21, 0.35));
}
.ng-edge-line.delete {
  stroke: #fb7185;
}
.ng-node {
  position: absolute;
  z-index: 3;
  padding: 10px 11px;
  border-radius: 14px;
  border: 1px solid #3b82f6;
  background: linear-gradient(180deg, #1f2937, #111827);
  box-shadow: 0 12px 22px rgba(0, 0, 0, 0.35);
  cursor: grab;
  user-select: none;
}
.ng-node.selected {
  border-color: #facc15;
  box-shadow:
    0 0 0 2px rgba(250, 204, 21, 0.28),
    0 14px 24px rgba(0, 0, 0, 0.36);
}
.ng-node.delete {
  border-color: #fb7185;
  cursor: not-allowed;
}
.ng-node.type-start {
  border-color: #22c55e;
}
.ng-node.type-end {
  border-color: #fb7185;
}
.ng-node-head {
  display: flex;
  align-items: center;
  gap: 7px;
}
.ng-node-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #60a5fa;
}
.ng-node-type,
.ng-node-name {
  min-width: 0;
  width: 100%;
  border: 1px solid #334155;
  border-radius: 7px;
  background: #0f172a;
  color: #e5edf7;
  font-size: 11px;
  padding: 4px 6px;
}
.ng-node-name {
  margin-top: 8px;
}
.ng-node-fixed-name {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 900;
  color: #f8fafc;
}
.ng-node-hint {
  margin-top: 7px;
  color: #94a3b8;
  font-size: 10px;
}
.ng-port {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid #fff7aa;
  border-radius: 50%;
  background: #facc15;
  box-shadow: 0 0 0 3px rgba(250, 204, 21, 0.2);
  cursor: crosshair;
  z-index: 6;
}
.ng-port.occupied {
  background: #a16207;
  border-color: #fde68a;
  opacity: 0.78;
  cursor: not-allowed;
}
.ng-port.pending {
  background: #22c55e;
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.25);
}
.ng-condition-block {
  position: absolute;
  z-index: 4;
  min-width: 112px;
  max-width: 150px;
  height: 34px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #281600;
  background: #facc15;
  border: 1px solid #fde68a;
  font-size: 12px;
  font-weight: 900;
  clip-path: polygon(13% 0, 87% 0, 100% 50%, 87% 100%, 13% 100%, 0 50%);
  cursor: pointer;
  filter: drop-shadow(0 8px 15px rgba(0, 0, 0, 0.35));
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.ng-condition-block:hover {
  transform: translateY(-1px);
  filter: brightness(1.06) drop-shadow(0 5px 8px rgba(0, 0, 0, 0.24));
}
.ng-condition-block.selected {
  background: #fde047;
  outline: 2px solid rgba(250, 204, 21, 0.45);
}
.ng-inspector {
  display: grid;
  grid-template-rows: minmax(150px, 0.38fr) minmax(260px, 0.62fr);
  gap: 8px;
  padding: 8px;
  background: rgba(15, 23, 42, 0.9);
}
.ng-vars,
.ng-editor {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ng-vars :deep(.mini-blockly-shell),
.ng-editor :deep(.mini-blockly-shell) {
  flex: 1 1 auto;
  min-height: 0;
}
.ng-editor-empty {
  flex: 1 1 auto;
  display: grid;
  place-items: center;
  border-radius: 10px;
  border: 1px dashed rgba(148, 163, 184, 0.35);
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
  padding: 16px;
}
</style>
