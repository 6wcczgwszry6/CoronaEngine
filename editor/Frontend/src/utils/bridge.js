/**
 * Bridge Utility for QWebChannel
 * 封装了与 C++ Editor API 的通信，支持 Promise 调用
 */

export class Bridge {
  static async callEditorApi(apiName, args) {
    const request = {
      api: apiName,
      args: args || [],
    };

    return new Promise((resolve, reject) => {
      try {
        window.cefQuery({
          request: JSON.stringify(request),
          persistent: false,
          onSuccess: (response) => {
            try {
              const jsonResponse = typeof response === 'string' ? JSON.parse(response) : response;
              if (
                jsonResponse &&
                (jsonResponse.success === false ||
                  jsonResponse.status === 'error' ||
                  jsonResponse.type === 'error' ||
                  jsonResponse.error)
              ) {
                reject(new Error(jsonResponse.error || jsonResponse.message || 'Editor API error'));
              } else {
                resolve(jsonResponse);
              }
            } catch (e) {
              resolve(response);
            }
          },
          onFailure: (error_code, error_message) => {
            reject(new Error(`Editor API Error (${error_code}): ${error_message}`));
          },
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  static async callDockCommand(params) {
    const requestId = `dock_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const payload = {
      ...params,
      requestId,
    };

    return new Promise((resolve, reject) => {
      if (!window.coronaBridge || typeof window.coronaBridge.dockCommand !== 'function') {
        reject(new Error('coronaBridge.dockCommand is unavailable'));
        return;
      }

      const previousCallback = window.__dockCallback;
      window.__dockCallback = (id, error, result) => {
        if (id !== requestId) {
          if (typeof previousCallback === 'function') {
            previousCallback(id, error, result);
          }
          return;
        }

        window.__dockCallback = previousCallback;
        if (error) {
          reject(new Error(error.message || String(error)));
        } else {
          resolve(result);
        }
      };

      try {
        window.coronaBridge.dockCommand(JSON.stringify(payload));
      } catch (error) {
        window.__dockCallback = previousCallback;
        reject(error);
      }
    });
  }
}

const editorApiCallbacks = new Map();

if (typeof window !== 'undefined') {
  window.__coronaEditorApiDispatch = (event) => {
    const envelope = typeof event === 'string' ? JSON.parse(event) : event;
    const token = envelope?.token ?? envelope?.callback_token;
    const callback = editorApiCallbacks.get(token);
    if (typeof callback === 'function') {
      callback(envelope?.payload, envelope?.event);
    }
  };
}

const register_editor_api_callback = async (eventName, callback) => {
  const response = await Bridge.callEditorApi('EditorApi.register_callback', [
    eventName,
    { transport: 'cef-js' },
  ]);
  const callbackToken = response?.data?.callback_token ?? response?.callback_token;
  if (!callbackToken) {
    throw new Error(`Editor API event registration failed: ${eventName}`);
  }
  editorApiCallbacks.set(callbackToken, callback);
  return callbackToken;
};

const unregister_editor_api_callback = async (callbackToken) => {
  editorApiCallbacks.delete(callbackToken);
  return Bridge.callEditorApi('EditorApi.unregister_callback', [callbackToken]);
};

export const editorApi = {
  invoke: (apiName, args = []) => Bridge.callEditorApi(apiName, args),
  on: (eventName, callback) => register_editor_api_callback(eventName, callback),
  off: (callbackToken) => unregister_editor_api_callback(callbackToken),
  app: {
    closeProcess: () => Bridge.callEditorApi('CoronaEditor.close_process', []),
  },
  ai: {
    sendMessageToAIStream: (payload) => Bridge.callEditorApi('AITool.send_message_to_ai_stream', [payload]),
    readLocalFileAsBase64: (filePath) => Bridge.callEditorApi('AITool.read_local_file_as_base64', [filePath]),
    generateHint: (elementType, context = {}) =>
      Bridge.callEditorApi('AITool.generate_hint', [elementType, context || {}]),
    chatStream: (request) => Bridge.callEditorApi('AITool.ai_rpc', [request || {}]),
    cancelRequest: (requestId) =>
      Bridge.callEditorApi('AITool.ai_rpc', [
        {
          operation: 'request.cancel',
          request_id: requestId,
        },
      ]),
    getRequestStatus: (requestId) =>
      Bridge.callEditorApi('AITool.ai_rpc', [
        {
          operation: 'request.status',
          request_id: requestId,
        },
      ]),
  },
  files: {
    getProjectInfo: () => Bridge.callEditorApi('FileManager.get_project_info', []),
    getFiles: (relPath = '') => Bridge.callEditorApi('FileManager.get_files', [relPath || '']),
    getFileTree: (relPath = '') => Bridge.callEditorApi('FileManager.get_file_tree', [relPath || '']),
    createFolder: (path, folderName) =>
      Bridge.callEditorApi('FileManager.create_folder', [path, folderName]),
    createFile: (path, fileName, type) =>
      Bridge.callEditorApi('FileManager.create_file', [path, fileName, type]),
    deleteItem: (path) => Bridge.callEditorApi('FileManager.delete_item', [path]),
    renameItem: (oldPath, newName) =>
      Bridge.callEditorApi('FileManager.rename_item', [oldPath, newName]),
    openFile: (filePath, fileType) =>
      Bridge.callEditorApi('FileManager.open_file', [filePath, fileType]),
  },
  lanChat: {
    startRoom: (payload) => Bridge.callEditorApi('LANChat.start_room', [payload || {}]),
    startLocalRoom: (payload) => Bridge.callEditorApi('LANChat.start_local_room', [payload || {}]),
    stopRoom: () => Bridge.callEditorApi('LANChat.stop_room', []),
    stopLocalRoom: () => Bridge.callEditorApi('LANChat.stop_local_room', []),
    joinRoom: (payload) => Bridge.callEditorApi('LANChat.join_room', [payload || {}]),
    getHistory: () => Bridge.callEditorApi('LANChat.get_history', []),
    listHistoryRooms: () => Bridge.callEditorApi('LANChat.list_history_rooms', []),
    loadHistoryRoom: (room) => Bridge.callEditorApi('LANChat.load_history_room', [{ room }]),
    leaveRoom: () => Bridge.callEditorApi('LANChat.leave_room', []),
    sendMessage: (text, options = {}) =>
      Bridge.callEditorApi('LANChat.send_message', [{ text, ...(options || {}) }]),
    getLocalIp: () => Bridge.callEditorApi('LANChat.get_local_ip', []),
    addAgent: (payload) => Bridge.callEditorApi('LANChat.add_agent', [payload || {}]),
    removeAgent: (agentId) => Bridge.callEditorApi('LANChat.remove_agent', [{ agent_id: agentId }]),
    listAgents: () => Bridge.callEditorApi('LANChat.list_agents', []),
  },
  network: {
    startSession: (instanceName, projectId, port = 27960, role = 'host') =>
      Bridge.callEditorApi('Network.start_session', [instanceName, projectId, port, role]),
    stopSession: () => Bridge.callEditorApi('Network.stop_session', []),
    getPeerCount: () => Bridge.callEditorApi('Network.get_peer_count', []),
    getSessionInfo: () => Bridge.callEditorApi('Network.get_session_info', []),
    connectToPeer: (ip, port, peerName) =>
      Bridge.callEditorApi('Network.connect_to_peer', [ip, port, peerName]),
    setProjectRoot: (projectRoot) =>
      Bridge.callEditorApi('Network.set_project_root', [projectRoot]),
    broadcastActorCreate: (actorGuid, sceneName, modelPath, actorData) =>
      Bridge.callEditorApi('Network.broadcast_actor_create', [actorGuid, sceneName, modelPath, actorData]),
    broadcastActorTransform: (actorGuid, sceneName, actorData) =>
      Bridge.callEditorApi('Network.broadcast_actor_transform', [actorGuid, sceneName, actorData]),
    broadcastActorDelete: (actorGuid, sceneName, actorName) =>
      Bridge.callEditorApi('Network.broadcast_actor_delete', [actorGuid, sceneName, actorName]),
    requestSceneSnapshot: (sceneName) =>
      Bridge.callEditorApi('Network.request_actor_scene_snapshot', [sceneName]),
    broadcastSceneSnapshot: (sceneName, snapshot) =>
      Bridge.callEditorApi('Network.broadcast_actor_scene_snapshot', [sceneName, snapshot]),
    broadcastActorStateUpdate: (actorGuid, sceneName, actorData) =>
      Bridge.callEditorApi('Network.broadcast_actor_state_update', [actorGuid, sceneName, actorData]),
    pollPendingActorCreate: () => Bridge.callEditorApi('Network.poll_pending_actor_create', []),
    pollPendingActorTransform: () => Bridge.callEditorApi('Network.poll_pending_actor_transform', []),
    pollPendingActorDelete: () => Bridge.callEditorApi('Network.poll_pending_actor_delete', []),
    pollPendingSceneSnapshotRequest: () =>
      Bridge.callEditorApi('Network.poll_pending_actor_scene_snapshot_request', []),
    pollPendingSceneSnapshot: () => Bridge.callEditorApi('Network.poll_pending_actor_scene_snapshot', []),
    pollPendingActorStateUpdate: () => Bridge.callEditorApi('Network.poll_pending_actor_state_update', []),
    setSyncPaused: (paused) => Bridge.callEditorApi('Network.set_sync_paused', [!!paused]),
    registerActorIdentity: (actorGuid, actorHandle, locallyOwned = true) =>
      Bridge.callEditorApi('Network.register_actor_identity', [actorGuid, String(actorHandle || ''), !!locallyOwned]),
    claimActorOwnership: (actorGuid) =>
      Bridge.callEditorApi('Network.claim_actor_ownership', [actorGuid]),
  },
  project: {
    browseFolder: (defaultPath = '') =>
      Bridge.callEditorApi('ProjectLauncher.browse_folder', defaultPath ? [defaultPath] : []),
    createMultiplayerProject: (projectData) =>
      Bridge.callEditorApi('ProjectLauncher.create_multiplayer_project', [projectData || {}]),
    createProject: (projectData) =>
      Bridge.callEditorApi('ProjectLauncher.create_project', [projectData || {}]),
    createWorldProject: (worldData) =>
      Bridge.callEditorApi('ProjectLauncher.create_world_project', [worldData || {}]),
    getAppVersion: () => Bridge.callEditorApi('ProjectLauncher.get_app_version', []),
    getDefaultProjectPath: () => Bridge.callEditorApi('ProjectLauncher.get_default_project_path', []),
    getRecentProjects: () => Bridge.callEditorApi('ProjectLauncher.get_recent_projects', []),
    openProject: (projectPath) => Bridge.callEditorApi('ProjectLauncher.open_project', [projectPath]),
    openProjectFile: () => Bridge.callEditorApi('ProjectLauncher.open_project_file', []),
    setProjectMode: (mode, settings) =>
      Bridge.callEditorApi('ProjectLauncher.set_project_mode', [{ mode, settings }]),
  },
  scene: {
    listActorTree: (sceneName) => Bridge.callEditorApi('SceneTools.list_actor_tree', [sceneName]),
  },
  scratch: {
    executePythonCode: (code, mode, sceneName, actorName, targetType = 'actor') =>
      Bridge.callEditorApi('ScratchTool.execute_python_code', [
        code,
        mode ?? 0,
        sceneName ?? '',
        actorName ?? '',
        targetType || 'actor',
      ]),
    saveBlocklyTarget: (payload) => Bridge.callEditorApi('ScratchTool.save_blockly_target', [payload || {}]),
    loadBlocklyTarget: (payload) => Bridge.callEditorApi('ScratchTool.load_blockly_target', [payload || {}]),
    startGamePreview: (payload = { scope: 'project' }) =>
      Bridge.callEditorApi('ScratchTool.start_game_preview', [payload || { scope: 'project' }]),
    stopGamePreview: () => Bridge.callEditorApi('ScratchTool.stop_game_preview', []),
    getGamePreviewStatus: () => Bridge.callEditorApi('ScratchTool.get_game_preview_status', []),
    stopScriptExecution: () => Bridge.callEditorApi('ScratchTool.stop_script_execution', []),
    getScriptStatus: () => Bridge.callEditorApi('ScratchTool.get_script_status', []),
    sendKeyEvent: (key, modifiers, displayKey) =>
      Bridge.callEditorApi('ScratchTool.key_event', [key, modifiers || '', displayKey || key]),
    sendKeyUpEvent: (key, displayKey) =>
      Bridge.callEditorApi('ScratchTool.key_release', [key, displayKey || key]),
    sendMouseEvent: (eventType, button, x, y) =>
      Bridge.callEditorApi('ScratchTool.mouse_event', [eventType, button || '', x || 0, y || 0]),
  },
  sceneTools: {
    createScene: (sceneName) => Bridge.callEditorApi('SceneTools.create_scene', [sceneName]),
    listSceneTree: (sceneName) => Bridge.callEditorApi('SceneTools.list_scene_tree', [sceneName]),
    reloadScene: (sceneName, projectPath = '') =>
      Bridge.callEditorApi('SceneTools.reload_scene', projectPath ? [sceneName, projectPath] : [sceneName]),
    createActor: (sceneName, objPath, actorType = 'model', actorData = null) =>
      Bridge.callEditorApi('SceneTools.create_actor',
        actorData ? [sceneName, objPath, actorType, actorData] : [sceneName, objPath, actorType],
      ),
    removeActor: (sceneName, actorName) =>
      Bridge.callEditorApi('SceneTools.remove_actor', [sceneName, actorName]),
    renameActor: (sceneName, actorName, name) =>
      Bridge.callEditorApi('SceneTools.rename_actor', [sceneName, actorName, name]),
    openActor: (sceneName, actorName) =>
      Bridge.callEditorApi('SceneTools.open_actor', [sceneName, actorName]),
    focusActor: (sceneName, actorName, cameraName) =>
      Bridge.callEditorApi('SceneTools.focus_actor', [sceneName, actorName, cameraName]),
    setRenderBackend: (mode, sceneName = null, cameraId = null) =>
      Bridge.callEditorApi('SceneTools.set_render_backend', [mode, sceneName, cameraId]),
    getRenderBackend: (sceneName = null, cameraId = null) =>
      Bridge.callEditorApi('SceneTools.get_render_backend', [sceneName, cameraId]),
    setVisionRenderMode: (sceneName, cameraId = null, mode = 'path_tracing') =>
      Bridge.callEditorApi('SceneTools.set_vision_render_mode', [sceneName, cameraId, mode]),
    getVisionRenderMode: (sceneName, cameraId = null) =>
      Bridge.callEditorApi('SceneTools.get_vision_render_mode', [sceneName, cameraId]),
    createCameraView: (sceneName, name = null) =>
      Bridge.callEditorApi('SceneTools.create_camera_view', [sceneName, name]),
    openCameraView: (sceneName, cameraId) =>
      Bridge.callEditorApi('SceneTools.open_camera_view', [sceneName, cameraId]),
    closeCameraView: (sceneName, cameraId) =>
      Bridge.callEditorApi('SceneTools.close_camera_view', [sceneName, cameraId]),
    renameCameraView: (sceneName, cameraId, name) =>
      Bridge.callEditorApi('SceneTools.rename_camera_view', [sceneName, cameraId, name]),
    listCameraViews: (sceneName) =>
      Bridge.callEditorApi('SceneTools.list_camera_views', [sceneName]),
    updateCameraView: (sceneName, cameraId, state) =>
      Bridge.callEditorApi('SceneTools.update_camera_view', [sceneName, cameraId, state]),
    deleteCamera: (sceneName, cameraId) =>
      Bridge.callEditorApi('SceneTools.delete_camera', [sceneName, cameraId]),
    sunDirection: (sceneName, enable, direction) =>
      Bridge.callEditorApi('SceneTools.sun_direction', [sceneName, enable, direction]),
    floorGrid: (sceneName, enabled) =>
      Bridge.callEditorApi('SceneTools.floor_grid', [sceneName, enabled]),
    setPhysicsParams: (sceneName, params) =>
      Bridge.callEditorApi('SceneTools.set_physics_params', [
        sceneName,
        params.gravity,
        params.floor_y,
        params.floor_restitution,
        params.fixed_dt,
      ]),
    getPhysicsParams: (sceneName) => Bridge.callEditorApi('SceneTools.get_physics_params', [sceneName]),
    selectScreenshotPath: (sceneName, cameraName) =>
      Bridge.callEditorApi('SceneTools.select_screenshot_path', [sceneName, cameraName]),
    saveScreenshot: (sceneName, path, cameraName) =>
      Bridge.callEditorApi('SceneTools.save_screenshot', [sceneName, path, cameraName]),
    setOutputMode: (sceneName, cameraName, mode) =>
      Bridge.callEditorApi('SceneTools.set_output_mode', [sceneName, cameraName, mode]),
    getOutputMode: (sceneName, cameraName) =>
      Bridge.callEditorApi('SceneTools.get_output_mode', [sceneName, cameraName]),
    setShadowCascadeDebug: (sceneName, cameraName, enabled) =>
      Bridge.callEditorApi('SceneTools.set_shadow_cascade_debug', [sceneName, cameraName, !!enabled]),
    getShadowCascadeDebug: (sceneName, cameraName) =>
      Bridge.callEditorApi('SceneTools.get_shadow_cascade_debug', [sceneName, cameraName]),
    setSsaoEnabled: (sceneName, cameraName, enabled) =>
      Bridge.callEditorApi('SceneTools.set_ssao_enabled', [sceneName, cameraName, !!enabled]),
    getSsaoEnabled: (sceneName, cameraName) =>
      Bridge.callEditorApi('SceneTools.get_ssao_enabled', [sceneName, cameraName]),
    isVisionAvailable: () => Bridge.callEditorApi('SceneTools.is_vision_available', []),
    loadVisionScene: (path) => Bridge.callEditorApi('SceneTools.load_vision_scene', [path]),
    pickActor: (sceneName, x, y, vpWidth, vpHeight) =>
      Bridge.callEditorApi('SceneTools.pick_actor_at_pixel', [sceneName, x, y, vpWidth, vpHeight]),
    playAudio: (resourceId, loop) =>
      Bridge.callEditorApi('SceneTools.play_audio', [resourceId, loop]),
    stopAudio: (resourceId) =>
      Bridge.callEditorApi('SceneTools.stop_audio', [resourceId]),
    actorPlayAudio: (actorName, loop = false) =>
      Bridge.callEditorApi('SceneTools.actor_play_audio', [actorName, loop]),
    actorStopAudio: (actorName) =>
      Bridge.callEditorApi('SceneTools.actor_stop_audio', [actorName]),
  },
  main: {
    getMenuData: () => Bridge.callEditorApi('MainView.get_menu_data', []),
    importResourceFile: (sceneName, fileType) =>
      Bridge.callEditorApi('MainView.import_resource_file', [sceneName, fileType]),
    onInit: (projectPath = '') =>
      Bridge.callEditorApi('MainView.on_init', projectPath ? [projectPath] : []),
    runProject: (scenePath = '') =>
      Bridge.callEditorApi('MainView.run_project', scenePath ? [scenePath] : []),
    sceneSave: (sceneName) => Bridge.callEditorApi('MainView.scene_save', [sceneName]),
    updateViewToolState: (toolId, enabled) =>
      Bridge.callEditorApi('MainView.update_view_tool_state', [toolId, !!enabled]),
  },
  projectSettings: {
    getActiveProjectInfo: () => Bridge.callEditorApi('ProjectSettings.get_active_project_info', []),
    saveActiveProjectInfo: (settings) =>
      Bridge.callEditorApi('ProjectSettings.save_active_project_info', [settings || {}]),
    browseSceneFile: () => Bridge.callEditorApi('ProjectSettings.browse_scene_file', []),
  },
  resourceSearch: {
    prepareIndex: (caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.prepare_index', [caller]),
    fuzzySearch: (query, topK = 20, typeFilter = null, caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.fuzzy_search', [query, topK, typeFilter, caller]),
    imageSearch: (imageB64, topK = 20, threshold = 10, caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.image_search', [imageB64, topK, threshold, caller]),
    listTypes: (caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.list_types', [caller]),
    rebuildIndex: (caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.rebuild_index', [caller]),
    getStats: (caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.get_stats', [caller]),
    markIndexDirty: (reason = 'frontend', caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.mark_index_dirty', [reason, caller]),
    focusActor: (sceneName, actorName, caller = CURRENT_CALLER) =>
      Bridge.callEditorApi('ResourceSearch.focus_actor', [sceneName, actorName, caller]),
  },
  sceneDatas: {
    getScene: (sceneId) => Bridge.callEditorApi('SceneDatas.get_scene', [sceneId]),
    getActor: (sceneId, actorId) => Bridge.callEditorApi('SceneDatas.get_actor', [sceneId, actorId]),
    actorOperation: (sceneName, actorName, operation, vector) =>
      Bridge.callEditorApi('SceneDatas.actor_operation', [sceneName, actorName, operation, vector]),
    saveActor: (sceneName, actorName) =>
      Bridge.callEditorApi('SceneDatas.save_actor', [sceneName, actorName]),
    selectModelFile: (sceneId, actorId, fileType) =>
      Bridge.callEditorApi('SceneDatas.select_model_file', [sceneId, actorId, fileType]),
  },
};

// 快捷访问
export const sceneService = {
  createActor: (sceneName, objPath, actorType = 'model', actorData = null) =>
    editorApi.sceneTools.createActor(sceneName, objPath, actorType, actorData),
  removeActor: (sceneName, actorName) =>
    editorApi.sceneTools.removeActor(sceneName, actorName),
  renameActor: (sceneName, actorName, name) =>
    editorApi.sceneTools.renameActor(sceneName, actorName, name),
  createScene: (sceneName) =>
    editorApi.sceneTools.createScene(sceneName),

  sunDirection: (sceneName, enable, direction) =>
    editorApi.sceneTools.sunDirection(sceneName, enable, direction),
  floorGrid: (sceneName, enabled) =>
    editorApi.sceneTools.floorGrid(sceneName, enabled),
  setPhysicsParams: (sceneName, params) =>
    editorApi.sceneTools.setPhysicsParams(sceneName, params),
  getPhysicsParams: (sceneName) => editorApi.sceneTools.getPhysicsParams(sceneName),
  selectScreenshotPath: (sceneName, cameraName) =>
    editorApi.sceneTools.selectScreenshotPath(sceneName, cameraName),
  saveScreenshot: (sceneName, path, cameraName) =>
    editorApi.sceneTools.saveScreenshot(sceneName, path, cameraName),
  setOutputMode: (sceneName, cameraName, mode) =>
    editorApi.sceneTools.setOutputMode(sceneName, cameraName, mode),
  getOutputMode: (sceneName, cameraName) =>
    editorApi.sceneTools.getOutputMode(sceneName, cameraName),
  setShadowCascadeDebug: (sceneName, cameraName, enabled) =>
    editorApi.sceneTools.setShadowCascadeDebug(sceneName, cameraName, enabled),
  getShadowCascadeDebug: (sceneName, cameraName) =>
    editorApi.sceneTools.getShadowCascadeDebug(sceneName, cameraName),
  setSsaoEnabled: (sceneName, cameraName, enabled) =>
    editorApi.sceneTools.setSsaoEnabled(sceneName, cameraName, enabled),
  getSsaoEnabled: (sceneName, cameraName) =>
    editorApi.sceneTools.getSsaoEnabled(sceneName, cameraName),
  isVisionAvailable: () => editorApi.sceneTools.isVisionAvailable(),
  setRenderBackend: (mode, sceneName = null, cameraId = null) =>
    editorApi.sceneTools.setRenderBackend(mode, sceneName, cameraId),
  getRenderBackend: (sceneName = null, cameraId = null) =>
    editorApi.sceneTools.getRenderBackend(sceneName, cameraId),
  setVisionRenderMode: (sceneName, cameraId = null, mode = 'path_tracing') =>
    editorApi.sceneTools.setVisionRenderMode(sceneName, cameraId, mode),
  getVisionRenderMode: (sceneName, cameraId = null) =>
    editorApi.sceneTools.getVisionRenderMode(sceneName, cameraId),
  createCameraView: (sceneName, name = null) =>
    editorApi.sceneTools.createCameraView(sceneName, name),
  openCameraView: (sceneName, cameraId) =>
    editorApi.sceneTools.openCameraView(sceneName, cameraId),
  closeCameraView: (sceneName, cameraId) =>
    editorApi.sceneTools.closeCameraView(sceneName, cameraId),
  renameCameraView: (sceneName, cameraId, name) =>
    editorApi.sceneTools.renameCameraView(sceneName, cameraId, name),
  listCameraViews: (sceneName) =>
    editorApi.sceneTools.listCameraViews(sceneName),
  updateCameraView: (sceneName, cameraId, state) =>
    editorApi.sceneTools.updateCameraView(sceneName, cameraId, state),
  deleteCamera: (sceneName, cameraId) =>
    editorApi.sceneTools.deleteCamera(sceneName, cameraId),
  loadVisionScene: (path) => editorApi.sceneTools.loadVisionScene(path),
  reloadScene: (sceneName, projectPath = '') =>
    editorApi.sceneTools.reloadScene(sceneName, projectPath),
  listActorTree: (sceneName) => editorApi.scene.listActorTree(sceneName),
  listSceneTree: (sceneName) => editorApi.sceneTools.listSceneTree(sceneName),
  openSceneActor: (sceneName, actorName) =>
    editorApi.sceneTools.openActor(sceneName, actorName),
  focusActor: (sceneName, actorName, cameraName) =>
    editorApi.sceneTools.focusActor(sceneName, actorName, cameraName),
  /** 鼠标在3D视口中拾取物体（异步：首次调用设置拾取，~50ms后重试获取结果） */
  pickActor: (sceneName, x, y, vpWidth, vpHeight) =>
    editorApi.sceneTools.pickActor(sceneName, x, y, vpWidth, vpHeight),
  /** 播放已导入的音频资源 */
  playAudio: (resourceId, loop) =>
    editorApi.sceneTools.playAudio(resourceId, loop),
  /** 停止播放音频资源 */
  stopAudio: (resourceId) =>
    editorApi.sceneTools.stopAudio(resourceId),
  /** 在 audio Actor 的世界位置播放其绑定音频（空间音频） */
  actorPlayAudio: (actorName, loop = false) =>
    editorApi.sceneTools.actorPlayAudio(actorName, loop),
  /** 停止 audio Actor 的空间音频播放 */
  actorStopAudio: (actorName) =>
    editorApi.sceneTools.actorStopAudio(actorName),

  getScene: (sceneId) => editorApi.sceneDatas.getScene(sceneId),
  getActor: (sceneId, actorId) => editorApi.sceneDatas.getActor(sceneId, actorId),
  actorOperation: (scene_name, actor_name, operation, vector) =>
    editorApi.sceneDatas.actorOperation(scene_name, actor_name, operation, vector),
  /** 仅触发写盘：Transform 已由快速通道写入 SharedDataHub */
  saveActor: (sceneName, actorName) =>
    editorApi.sceneDatas.saveActor(sceneName, actorName),
  selectModelFileDialog: (sceneId, actorId, fileType) =>
    editorApi.sceneDatas.selectModelFile(sceneId, actorId, fileType),
  setCameraLock: (sceneName, actorName, enabled) =>
    editorApi.sceneDatas.actorOperation(sceneName, actorName, 'SetCameraLock', [enabled]),
  setCameraLockOffset: (sceneName, actorName, offset) =>
    editorApi.sceneDatas.actorOperation(sceneName, actorName, 'SetCameraLockOffset', offset),
  setCameraLockRotation: (sceneName, actorName, rotation) =>
    editorApi.sceneDatas.actorOperation(sceneName, actorName, 'SetCameraLockRotation', rotation),
};

export const projectService = {
  OnInit: (projectPath = window.localStorage?.getItem('corona.activeProjectPath') || '') =>
    editorApi.main.onInit(projectPath),
  importResourceFileByDialog: (sceneName, fileType) =>
    editorApi.main.importResourceFile(sceneName, fileType),
  sceneSave: (sceneName) => editorApi.main.sceneSave(sceneName),

  // 菜单数据接口
  getMenuData: () => editorApi.main.getMenuData(),
  updateViewToolState: (toolId, enabled) =>
    editorApi.main.updateViewToolState(toolId, enabled),

  runProject: (scenePath) =>
    editorApi.main.runProject(scenePath),

  setDragRegions: (Path, x, y, w, h) =>
    Bridge.callDockCommand({
      cmd: 'setDragRegions',
      tabId: null,
      regions: [{ x, y, w, h }],
    }),
  setCurrentTabDragRegions: (regions) =>
    Bridge.callDockCommand({
      cmd: 'setDragRegions',
      tabId: null,
      regions: Array.isArray(regions) ? regions : [],
    }),
};

export const appService = {
  createPanelTab: (panelId, routePath, width, height, dockingPos) =>
    Bridge.callDockCommand({ cmd: 'createPanelTab', panelId, routePath, width, height, dockingPos }),
  // Create a panel that is born directly as its own borderless OS window (skips the
  // main-window docked-rectangle stage, so no 1-frame flash). x/y/width/height are the
  // desired initial geometry in logical px. Returns { tab_id, panel_id }.
  createDetachedPanel: ({ panelId, routePath, width, height, x, y }) =>
    Bridge.callDockCommand({ cmd: 'createDetachedPanel', panelId, routePath, width, height, x, y }),
  closeThisTab: (panelId) =>
    Bridge.callDockCommand({ cmd: 'closeThisTab', panelId }),
  closePanelTab: (tabId, panelId) =>
    Bridge.callDockCommand({ cmd: 'closePanelTab', tabId, panelId }),
  // Detach the calling panel into its own borderless OS window (tabId omitted ⇒ C++
  // resolves it from the calling browser). x/y/width/height are optional desired geometry
  // in logical px; width/height default to the panel's current size on the C++ side.
  detachPanel: (opts = {}) =>
    Bridge.callDockCommand({ cmd: 'detachPanel', ...opts }),
  // Re-dock the calling panel back into the main window (destroys its secondary window).
  redockPanel: (opts = {}) =>
    Bridge.callDockCommand({ cmd: 'redockPanel', ...opts }),
  toggleMaximizeThisCameraView: (sceneId = '', cameraId = '') =>
    Bridge.callDockCommand({ cmd: 'toggleMaximizeThisCameraView', sceneId, cameraId }),
  cycleThisCameraViewWindowMode: (sceneId = '', cameraId = '') =>
    Bridge.callDockCommand({ cmd: 'cycleThisCameraViewWindowMode', sceneId, cameraId }),
  toggleBorderlessThisCameraView: (sceneId = '', cameraId = '') =>
    Bridge.callDockCommand({ cmd: 'toggleBorderlessThisCameraView', sceneId, cameraId }),
  resizeThisCameraView: (width, height, sceneId = '', cameraId = '') =>
    Bridge.callDockCommand({ cmd: 'resizeThisCameraView', width, height, sceneId, cameraId }),
  createCameraView: (camera) =>
    Bridge.callDockCommand({
      cmd: 'createCameraView',
      sceneId: camera.scene_id,
      cameraId: camera.camera_id || camera.id,
      cameraHandle: camera.handle,
      routePath: `/CameraView?scene=${encodeURIComponent(camera.scene_id)}&camera=${encodeURIComponent(camera.camera_id || camera.id)}`,
      width: camera.view_width || 960,
      height: camera.view_height || 540,
      x: camera.view_x || 120,
      y: camera.view_y || 120,
    }),
  closeCameraView: (sceneId, cameraId) =>
    Bridge.callDockCommand({ cmd: 'closeCameraView', sceneId, cameraId }),
  suspendCameraViews: (sceneId) =>
    Bridge.callDockCommand({ cmd: 'suspendCameraViews', sceneId }),
  crossTabBroadcast: (event, payload) =>
    Bridge.callDockCommand({ cmd: 'broadcast', event, payload }),
  closeProcess: () => editorApi.app.closeProcess(),
};

export const aiService = {
  sendMessageToAIStream: (payload) => editorApi.ai.sendMessageToAIStream(payload),
  readLocalFileAsBase64: (filePath) => editorApi.ai.readLocalFileAsBase64(filePath),
  generateHint: (elementType, context = {}) => editorApi.ai.generateHint(elementType, context),
};

export const aiClient = {
  chatStream: (request) => editorApi.ai.chatStream(request),
  cancelRequest: (requestId) => editorApi.ai.cancelRequest(requestId),
  getRequestStatus: (requestId) => editorApi.ai.getRequestStatus(requestId),
};

// 局域网聊天室：所有跨机传输在 C++ NetworkSystem 完成，前端只通过 cefQuery 调用。
// C++ 侧通过 __coronaEmit('lanchat-event', event) 把房间消息推回前端
// （coronaEventBus.on('lanchat-event')），事件信封带 channel: 'lanchat'。
//
// 注意：C++ 脚本服务会用 create_success_response 把返回值包成
// { success, data, timestamp }，业务结果在 .data 里。这里统一解包，
// 让 store 直接拿到 { ok, ip, ... } 业务对象（约定同 SceneBar：result?.data ?? result）。
const _unwrap = (res) => (res && res.data !== undefined ? res.data : res);

export const lanChatService = {
  // 房主开房：{ room, password, port? } -> { ok, ip, port, room } | { ok:false, error }
  startRoom: (payload) => editorApi.lanChat.startRoom(payload).then(_unwrap),
  // 单人本地房：不启动 NetworkSystem 协作会话
  startLocalRoom: (payload) => editorApi.lanChat.startLocalRoom(payload).then(_unwrap),
  // 房主关房 -> { ok }
  stopRoom: () => editorApi.lanChat.stopRoom().then(_unwrap),
  // 关闭单人本地房，不停止 NetworkSystem 协作会话
  stopLocalRoom: () => editorApi.lanChat.stopLocalRoom().then(_unwrap),
  // 加入房间：{ ip, port, room, password, nickname } -> { ok, members, history } | { ok:false, code }
  joinRoom: (payload) => editorApi.lanChat.joinRoom(payload).then(_unwrap),
  // 显式读取当前房间历史，用于开房后兜底恢复持久化记录
  getHistory: () => editorApi.lanChat.getHistory().then(_unwrap),
  // 读取持久化历史房间列表，打开 Dock 时展示给用户选择
  listHistoryRooms: () => editorApi.lanChat.listHistoryRooms().then(_unwrap),
  // 读取指定持久化房间历史，不自动进入该房间
  loadHistoryRoom: (room) => editorApi.lanChat.loadHistoryRoom(room).then(_unwrap),
  // 离开房间 -> { ok }
  leaveRoom: () => editorApi.lanChat.leaveRoom().then(_unwrap),
  // 发送消息：{ text } -> { ok } | { ok:false, error }
  sendMessage: (text, options = {}) =>
    editorApi.lanChat.sendMessage(text, options).then(_unwrap),
  // 获取本机局域网 IP -> { ok, ip, port }
  getLocalIp: () => editorApi.lanChat.getLocalIp().then(_unwrap),
  // 添加 AI 助手：{ name, persona } -> { ok, agent_id, name } | { ok:false, error }
  addAgent: (payload) => editorApi.lanChat.addAgent(payload).then(_unwrap),
  // 移除 AI 助手：{ agent_id } -> { ok }
  removeAgent: (agentId) => editorApi.lanChat.removeAgent(agentId).then(_unwrap),
  // 列出 agent 名册 -> { ok, agents:[{agent_id,name,owner}] }
  listAgents: () => editorApi.lanChat.listAgents().then(_unwrap),
};

export const scriptingService = {
  /**
   * 执行 Blockly 生成的 Python 代码
   * @param {string} code - Python 代码
   * @param {number} mode - 执行模式（0 = 编辑模式）
   * @param {string} sceneName - 目标场景名称（可选）
   * @param {string} actorName - 目标 Actor 名称（可选）
   */
  executePythonCode: (code, mode, sceneName, actorName, targetType = 'actor') =>
    editorApi.scratch.executePythonCode(code, mode, sceneName, actorName, targetType),

  saveBlocklyTarget: (payload) => editorApi.scratch.saveBlocklyTarget(payload),

  loadBlocklyTarget: (payload) => editorApi.scratch.loadBlocklyTarget(payload),

  startGamePreview: (payload = { scope: 'project' }) => editorApi.scratch.startGamePreview(payload),

  stopGamePreview: () => editorApi.scratch.stopGamePreview(),

  getGamePreviewStatus: () => editorApi.scratch.getGamePreviewStatus(),

  /**
   * 停止当前正在执行的脚本
   */
  stopScriptExecution: () => editorApi.scratch.stopScriptExecution(),

  /**
   * 查询当前脚本执行状态
   * @returns {Promise<{status: 'running'|'idle'}>}
   */
  getScriptStatus: () => editorApi.scratch.getScriptStatus(),

  /**
   * 发送键盘事件到积木脚本
   * @param {string} key - 按键名 (如 'KeyA', 'Space', 'ArrowUp')
   * @param {string} modifiers - 修饰键 (如 'Ctrl,Shift')
   */
  sendKeyEvent: (key, modifiers, displayKey) =>
    editorApi.scratch.sendKeyEvent(key, modifiers, displayKey),

  /**
   * 发送键盘释放事件到积木脚本
   */
  sendKeyUpEvent: (key, displayKey) =>
    editorApi.scratch.sendKeyUpEvent(key, displayKey),

  /**
   * 发送鼠标事件到积木脚本
   */
  sendMouseEvent: (eventType, button, x, y) =>
    editorApi.scratch.sendMouseEvent(eventType, button, x, y),
};

export const projectLauncherService = {
  // 获取默认项目路径
  getDefaultProjectPath: () => editorApi.project.getDefaultProjectPath(),
  // 浏览文件夹
  browseFolder: (default_path) =>
    editorApi.project.browseFolder(default_path),
  // 浏览并选择项目文件 (.ini)
  openProjectFile: () => editorApi.project.openProjectFile(),
  // 创建项目
  createProject: (projectData) =>
    editorApi.project.createProject(projectData),
  // 创建 AI 世界项目：自动命名 + 存到引擎 data 目录，无需 name/path
  // worldData: { mode: 'story'|'creative', prompt: string } -> { name, path }
  createWorldProject: (worldData) =>
    editorApi.project.createWorldProject(worldData),
  // 创建首页联机入口使用的临时项目：{ role: 'host'|'guest' } -> { name, path, role }
  createMultiplayerProject: (projectData) =>
    editorApi.project.createMultiplayerProject(projectData),
  // 打开项目（执行加载逻辑）
  openProject: (projectPath) =>
    editorApi.project.openProject(projectPath).then((result) => {
      const success = result?.data ?? result;
      const activeProjectPath = success?.path || projectPath;
      if (success && activeProjectPath) {
        window.localStorage?.setItem('corona.activeProjectPath', activeProjectPath);
      }
      return result;
    }),
  // 设置项目模式 (2D/3D/渲染)
  setProjectMode: (mode, settings) =>
    editorApi.project.setProjectMode(mode, settings),
  // 获取版本信息
  getAppVersion: () => editorApi.project.getAppVersion(),
  // 获取最近项目列表
  getRecentProjects: () => editorApi.project.getRecentProjects(),
};

export const fileService = {
  getProjectInfo: () => editorApi.files.getProjectInfo(),
  getFiles: (relPath) => editorApi.files.getFiles(relPath),
  getFileTree: (relPath) => editorApi.files.getFileTree(relPath),
  createFolder: (path, folderName) =>
    editorApi.files.createFolder(path, folderName),
  createFile: (path, fileName, type) =>
    editorApi.files.createFile(path, fileName, type),
  deleteItem: (path) => editorApi.files.deleteItem(path),
  renameItem: (oldPath, newName) =>
    editorApi.files.renameItem(oldPath, newName),
  openFile: (filePath, fileType) =>
    editorApi.files.openFile(filePath, fileType),
};

export const logService = {
  setLogReady: () => Promise.resolve({ success: true, disabled: true }),
  setLogClose: () => Promise.resolve({ success: true, disabled: true }),
};

/**
 * 场景栏资源智能搜索
 * - fuzzy_search: 模糊文本搜索(支持中文分词/拼音/编辑距离)
 * - image_search: 以图搜索(本地 pHash,无网络依赖)
 * - list_types / rebuild_index / get_stats: 索引元操作
 * - focus_actor: 搜索结果"定位"按钮 → 桥接 SceneTools
 */
// 当前模块的"调用方"标识(必须出现在后端 ALLOWED_CALLERS 白名单内)
// 任何后端接口调用都会自动附带此标识,供权限控制
const CURRENT_CALLER = 'SceneBar';
const RESOURCE_SEARCH_ENABLED = false;
const resourceSearchDisabled = () => Promise.resolve({
  success: true,
  data: {
    status: 'disabled',
    code: 'resource_search_disabled',
    message: 'ResourceSearch is disabled',
    items: [],
    total: 0,
  },
});

export const resourceService = {
  prepareIndex: () =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.prepareIndex()
      : resourceSearchDisabled(),
  fuzzySearch: (query, topK = 20, typeFilter = null) =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.fuzzySearch(query, topK, typeFilter)
      : resourceSearchDisabled(),
  imageSearch: (imageB64, topK = 20, threshold = 10) =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.imageSearch(imageB64, topK, threshold)
      : resourceSearchDisabled(),
  listTypes: () =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.listTypes()
      : resourceSearchDisabled(),
  rebuildIndex: () =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.rebuildIndex()
      : resourceSearchDisabled(),
  getStats: () =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.getStats()
      : resourceSearchDisabled(),
  markIndexDirty: (reason = 'frontend') =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.markIndexDirty(reason)
      : resourceSearchDisabled(),
  focusActor: (sceneName, actorName) =>
    RESOURCE_SEARCH_ENABLED
      ? editorApi.resourceSearch.focusActor(sceneName, actorName)
      : resourceSearchDisabled(),
};

export const projectSettingsService = {
  // 获取当前激活项目的配置
  getActiveProjectInfo: () => editorApi.projectSettings.getActiveProjectInfo(),
  // 保存当前激活项目的配置
  saveActiveProjectInfo: (settings) =>
    editorApi.projectSettings.saveActiveProjectInfo(settings),
  // 浏览当前项目中的场景文件
  browseSceneFile: () => editorApi.projectSettings.browseSceneFile(),
};

export const networkService = {
  startSession: (instanceName, projectId, port = 27960, role = 'host') =>
    editorApi.network.startSession(instanceName, projectId, port, role).then(_unwrap),
  stopSession: () => editorApi.network.stopSession().then(_unwrap),
  getPeerCount: () => editorApi.network.getPeerCount().then(_unwrap),
  getSessionInfo: () => editorApi.network.getSessionInfo().then(_unwrap),
  connectToPeer: (ip, port, peerName) =>
    editorApi.network.connectToPeer(ip, port, peerName).then(_unwrap),
  setProjectRoot: (projectRoot) =>
    editorApi.network.setProjectRoot(projectRoot).then(_unwrap),
  broadcastActorCreate: (actorGuid, sceneName, modelPath, actorData) =>
    editorApi.network.broadcastActorCreate(actorGuid, sceneName, modelPath, actorData).then(_unwrap),
  broadcastActorTransform: (actorGuid, sceneName, actorData) =>
    editorApi.network.broadcastActorTransform(actorGuid, sceneName, actorData).then(_unwrap),
  broadcastActorDelete: (actorGuid, sceneName, actorName) =>
    editorApi.network.broadcastActorDelete(actorGuid, sceneName, actorName).then(_unwrap),
  requestSceneSnapshot: (sceneName) =>
    editorApi.network.requestSceneSnapshot(sceneName).then(_unwrap),
  broadcastSceneSnapshot: (sceneName, snapshot) =>
    editorApi.network.broadcastSceneSnapshot(sceneName, snapshot).then(_unwrap),
  broadcastActorStateUpdate: (actorGuid, sceneName, actorData) =>
    editorApi.network.broadcastActorStateUpdate(actorGuid, sceneName, actorData).then(_unwrap),
  /** 轮询待创建的远程 Actor（文件传输完成后触发创建） */
  pollPendingActorCreate: () =>
    editorApi.network.pollPendingActorCreate().then(_unwrap),
  /** 轮询远程 Actor transform delta */
  pollPendingActorTransform: () =>
    editorApi.network.pollPendingActorTransform().then(_unwrap),
  pollPendingActorDelete: () =>
    editorApi.network.pollPendingActorDelete().then(_unwrap),
  pollPendingSceneSnapshotRequest: () =>
    editorApi.network.pollPendingSceneSnapshotRequest().then(_unwrap),
  pollPendingSceneSnapshot: () =>
    editorApi.network.pollPendingSceneSnapshot().then(_unwrap),
  pollPendingActorStateUpdate: () =>
    editorApi.network.pollPendingActorStateUpdate().then(_unwrap),
  /** 暂停/恢复同步（Actor 创建期间避免 seq_id 碰撞） */
  setSyncPaused: (paused) =>
    editorApi.network.setSyncPaused(paused).then(_unwrap),
  /** 注册 actor_guid -> 本地 Actor handle 映射，作为后续稳定同步的锚点 */
  registerActorIdentity: (actorGuid, actorHandle, locallyOwned = true) =>
    editorApi.network.registerActorIdentity(actorGuid, actorHandle, locallyOwned).then(_unwrap),
  claimActorOwnership: (actorGuid) =>
    editorApi.network.claimActorOwnership(actorGuid).then(_unwrap),
};
