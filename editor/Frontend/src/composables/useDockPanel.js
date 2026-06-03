import { inject } from 'vue';
import { useDockStore } from '@/stores/dockStore.js';

/**
 * 面板组件在 Dock 内时使用的 composable
 * 返回 isDocked 标志和 closePanel 函数
 */
export function useDockPanel() {
  const dockPanelId = inject('dockPanelId', null);
  const inDock = inject('inDock', false);
  const dockStore = inDock ? useDockStore() : null;

  function closePanel() {
    if (dockPanelId && dockStore) {
      dockStore.closePanel(dockPanelId);
    }
  }

  return {
    isDocked: inDock,
    dockPanelId,
    closePanel,
  };
}
