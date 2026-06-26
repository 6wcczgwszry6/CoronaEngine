import { appService } from '@/utils/bridge.js';
import { getPluginManifest, PLUGIN_MANIFEST } from '@/config/pluginManifest.js';

export const FLOATING_PANEL_IDS = ['SceneTools', 'SceneDatas', 'AITalkBar'];

const POSITION_WHITELIST = new Set(['right_top', 'right_bottom', 'left_bottom', 'center']);

export function isFloatingPanel(panelId) {
  return FLOATING_PANEL_IDS.includes(panelId);
}

function normalizeFloatPosition(position) {
  return POSITION_WHITELIST.has(position) ? position : 'right_top';
}

export function floatingPanelManifests() {
  return PLUGIN_MANIFEST.filter(
    (panel) => panel.defaultOpenMode === 'external' && isFloatingPanel(panel.id)
  );
}

export async function openFloatingPanel(dockStore, panelId) {
  const manifest = getPluginManifest(panelId);
  if (!manifest || !dockStore?.panels?.[panelId]) {
    console.error('[panelWindows] Unknown panel:', panelId);
    return false;
  }

  const panelState = dockStore.panels[panelId];
  if (panelState.open && panelState.mode === 'external' && panelState.externalTabId) {
    return true;
  }

  const routePath = `#${manifest.routePath || ''}`;
  const width = manifest.defaultWidth || 400;
  const height = manifest.defaultHeight || 600;
  const dockingPos = normalizeFloatPosition(manifest.defaultFloatPosition);

  try {
    // Startup floating panels use the single-surface in-main-window path (createPanelTab).
    // The multi-surface detach path (createDetachedPanel) SIGABRTs when several windows are
    // created at once on startup; detach stays available via the manual ⤢ pop-out, which is
    // one window at a time. Revisit once the multi-surface GPU path is fixed.
    const result = await appService.createPanelTab(panelId, routePath, width, height, dockingPos);
    const tabId = result?.tab_id ?? result?.data?.tab_id;
    if (!Number.isInteger(tabId)) {
      throw new Error(`Invalid external tab id for ${panelId}`);
    }
    dockStore.setExternal(panelId, tabId);
    return true;
  } catch (error) {
    console.error(`[panelWindows] Failed to open floating panel ${panelId}:`, error);
    return false;
  }
}
