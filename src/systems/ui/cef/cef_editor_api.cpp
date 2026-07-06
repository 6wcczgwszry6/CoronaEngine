#include "cef_editor_api.h"

#include <corona/kernel/core/i_logger.h>

#include <array>
#include <atomic>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace Corona::Systems::UI {
namespace {

constexpr std::uint32_t caller_mask(EditorApiCaller caller) {
    return static_cast<std::uint32_t>(caller);
}

constexpr std::uint32_t all_callers() {
    return caller_mask(EditorApiCaller::Cef) | caller_mask(EditorApiCaller::Python);
}

constexpr EditorApiReturnSpec returns(EditorApiValueType type) {
    return EditorApiReturnSpec{type};
}

constexpr EditorApiParamSpec param(const char* name, EditorApiValueType type, bool optional = false) {
    return EditorApiParamSpec{name, type, optional};
}

constexpr std::array<EditorApiParamSpec, 0> kNoParams = {};

constexpr std::array<EditorApiParamSpec, 1> kSceneNameParam = {{
    param("scene_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kSceneNameOptionalParam = {{
    param("scene_name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 1> kPathParam = {{
    param("path", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kPathOptionalParam = {{
    param("path", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 1> kObjectPayloadParam = {{
    param("payload", EditorApiValueType::Object),
}};

constexpr std::array<EditorApiParamSpec, 1> kAnyPayloadParam = {{
    param("payload", EditorApiValueType::Any),
}};

constexpr std::array<EditorApiParamSpec, 2> kAiToolGenerateHintParams = {{
    param("element_type", EditorApiValueType::String),
    param("context", EditorApiValueType::Object, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kMainViewImportResourceFileParams = {{
    param("scene_name", EditorApiValueType::String),
    param("file_type", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kMainViewUpdateViewToolStateParams = {{
    param("tool_id", EditorApiValueType::String),
    param("enabled", EditorApiValueType::Boolean),
}};

constexpr std::array<EditorApiParamSpec, 2> kFileManagerCreateFolderParams = {{
    param("path", EditorApiValueType::String),
    param("folder_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 3> kFileManagerCreateFileParams = {{
    param("path", EditorApiValueType::String),
    param("file_name", EditorApiValueType::String),
    param("file_type", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 2> kFileManagerRenameItemParams = {{
    param("old_path", EditorApiValueType::String),
    param("new_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 2> kFileManagerOpenFileParams = {{
    param("path", EditorApiValueType::String),
    param("file_type", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kCallerParam = {{
    param("caller", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 4> kResourceSearchFuzzySearchParams = {{
    param("query", EditorApiValueType::String),
    param("top_k", EditorApiValueType::Integer),
    param("type_filter", EditorApiValueType::String, true),
    param("caller", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 4> kResourceSearchImageSearchParams = {{
    param("image_b64", EditorApiValueType::String),
    param("top_k", EditorApiValueType::Integer),
    param("threshold", EditorApiValueType::Number),
    param("caller", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 2> kResourceSearchMarkIndexDirtyParams = {{
    param("reason", EditorApiValueType::String),
    param("caller", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 3> kResourceSearchFocusActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
    param("caller", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kActorGuidParam = {{
    param("actor_guid", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kProjectRootParam = {{
    param("project_root", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kPausedParam = {{
    param("paused", EditorApiValueType::Boolean),
}};

constexpr std::array<EditorApiParamSpec, 4> kNetworkStartSessionParams = {{
    param("instance_name", EditorApiValueType::String),
    param("project_id", EditorApiValueType::Integer),
    param("port", EditorApiValueType::Integer),
    param("role", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kNetworkConnectToPeerParams = {{
    param("ip", EditorApiValueType::String),
    param("port", EditorApiValueType::Integer),
    param("peer_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 4> kNetworkBroadcastActorCreateParams = {{
    param("actor_guid", EditorApiValueType::String),
    param("scene_name", EditorApiValueType::String),
    param("model_path", EditorApiValueType::String),
    param("actor_data", EditorApiValueType::Any, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kNetworkActorStateUpdateParams = {{
    param("actor_guid", EditorApiValueType::String),
    param("scene_name", EditorApiValueType::String),
    param("actor_data", EditorApiValueType::Any, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kNetworkBroadcastActorDeleteParams = {{
    param("actor_guid", EditorApiValueType::String),
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 2> kNetworkBroadcastSceneSnapshotParams = {{
    param("scene_name", EditorApiValueType::String),
    param("snapshot", EditorApiValueType::Any, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kNetworkRegisterActorIdentityParams = {{
    param("actor_guid", EditorApiValueType::String),
    param("actor_handle", EditorApiValueType::Any),
    param("locally_owned", EditorApiValueType::Boolean, true),
}};

constexpr std::array<EditorApiParamSpec, 1> kActorNameParam = {{
    param("actor_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 1> kResourceIdParam = {{
    param("resource_id", EditorApiValueType::Any),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 4> kSceneDatasActorOperationParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
    param("operation", EditorApiValueType::String),
    param("vector", EditorApiValueType::Any, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneDatasSelectModelFileParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
    param("file_type", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneCameraParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 4> kSceneToolsCreateActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("obj_path", EditorApiValueType::String),
    param("actor_type", EditorApiValueType::String, true),
    param("actor_data", EditorApiValueType::Any, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsRenameActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
    param("name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsFocusActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("actor_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSetRenderBackendParams = {{
    param("mode", EditorApiValueType::String),
    param("scene_name", EditorApiValueType::String, true),
    param("camera_name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsCameraOptionalParams = {{
    param("scene_name", EditorApiValueType::String, true),
    param("camera_name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSetVisionRenderModeParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String, true),
    param("mode", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsReloadSceneParams = {{
    param("scene_name", EditorApiValueType::String),
    param("project_path", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsCreateCameraViewParams = {{
    param("scene_name", EditorApiValueType::String),
    param("name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsRenameCameraViewParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String),
    param("name", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsUpdateCameraViewParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String),
    param("state", EditorApiValueType::Object),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSunDirectionParams = {{
    param("scene_name", EditorApiValueType::String),
    param("enabled", EditorApiValueType::Boolean),
    param("direction", EditorApiValueType::Array),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsFloorGridParams = {{
    param("scene_name", EditorApiValueType::String),
    param("enabled", EditorApiValueType::Boolean),
}};

constexpr std::array<EditorApiParamSpec, 5> kSceneToolsSetPhysicsParams = {{
    param("scene_name", EditorApiValueType::String),
    param("gravity", EditorApiValueType::Array, true),
    param("floor_y", EditorApiValueType::Number, true),
    param("floor_restitution", EditorApiValueType::Number, true),
    param("fixed_dt", EditorApiValueType::Number, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSaveScreenshotParams = {{
    param("scene_name", EditorApiValueType::String),
    param("path", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSetOutputModeParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String, true),
    param("mode", EditorApiValueType::String),
}};

constexpr std::array<EditorApiParamSpec, 3> kSceneToolsSetCameraBoolParams = {{
    param("scene_name", EditorApiValueType::String),
    param("camera_name", EditorApiValueType::String, true),
    param("enabled", EditorApiValueType::Boolean),
}};

constexpr std::array<EditorApiParamSpec, 5> kSceneToolsPickActorParams = {{
    param("scene_name", EditorApiValueType::String),
    param("x", EditorApiValueType::Number),
    param("y", EditorApiValueType::Number),
    param("viewport_width", EditorApiValueType::Number),
    param("viewport_height", EditorApiValueType::Number),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsPlayAudioParams = {{
    param("resource_id", EditorApiValueType::Any),
    param("loop", EditorApiValueType::Boolean, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kSceneToolsActorPlayAudioParams = {{
    param("actor_name", EditorApiValueType::String),
    param("loop", EditorApiValueType::Boolean, true),
}};

constexpr std::array<EditorApiParamSpec, 5> kScratchExecutePythonCodeParams = {{
    param("code", EditorApiValueType::String),
    param("mode", EditorApiValueType::Integer),
    param("scene_name", EditorApiValueType::String, true),
    param("actor_name", EditorApiValueType::String, true),
    param("target_type", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 3> kScratchKeyEventParams = {{
    param("key", EditorApiValueType::String),
    param("modifiers", EditorApiValueType::String, true),
    param("display_key", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 2> kScratchKeyReleaseParams = {{
    param("key", EditorApiValueType::String),
    param("display_key", EditorApiValueType::String, true),
}};

constexpr std::array<EditorApiParamSpec, 4> kScratchMouseEventParams = {{
    param("event_type", EditorApiValueType::String),
    param("button", EditorApiValueType::String, true),
    param("x", EditorApiValueType::Number),
    param("y", EditorApiValueType::Number),
}};

#define EDITOR_API_METHOD0(module, function, return_type) \
    {#module "." #function, #module, #function, nullptr, 0, returns(return_type), true, all_callers()}

#define EDITOR_API_METHOD1(module, function, param0_name, param0_type, return_type) \
    {#module "." #function, #module, #function, kSceneNameParam.data(), kSceneNameParam.size(), returns(return_type), true, all_callers()}

#define EDITOR_API_METHOD_SCHEMA(module, function, params_array, return_type) \
    {#module "." #function, #module, #function, params_array.data(), params_array.size(), returns(return_type), true, all_callers()}

constexpr std::array<EditorApiMethodSpec, 130> kEditorApiMethods = {{
    EDITOR_API_METHOD_SCHEMA(AITool, ai_rpc, kObjectPayloadParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(AITool, generate_hint, kAiToolGenerateHintParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(AITool, read_local_file_as_base64, kPathParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(AITool, send_message_to_ai_stream, kAnyPayloadParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(CoronaEditor, close_process, kNoParams, EditorApiValueType::Null),
    EDITOR_API_METHOD_SCHEMA(FileManager, create_file, kFileManagerCreateFileParams, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(FileManager, create_folder, kFileManagerCreateFolderParams, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(FileManager, delete_item, kPathParam, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(FileManager, get_file_tree, kPathOptionalParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(FileManager, get_files, kPathOptionalParam, EditorApiValueType::Array),
    EDITOR_API_METHOD_SCHEMA(FileManager, get_project_info, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(FileManager, open_file, kFileManagerOpenFileParams, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(FileManager, rename_item, kFileManagerRenameItemParams, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(LANChat, add_agent, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, get_history, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, get_local_ip, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, join_room, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, leave_room, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, list_agents, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, list_history_rooms, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, load_history_room, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, remove_agent, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, send_message, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, start_local_room, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, start_room, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, stop_local_room, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(LANChat, stop_room, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, get_menu_data, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, import_resource_file, kMainViewImportResourceFileParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, on_init, kPathOptionalParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, run_project, kPathOptionalParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, scene_save, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(MainView, update_view_tool_state, kMainViewUpdateViewToolStateParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, broadcast_actor_create, kNetworkBroadcastActorCreateParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, broadcast_actor_delete, kNetworkBroadcastActorDeleteParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, broadcast_actor_scene_snapshot, kNetworkBroadcastSceneSnapshotParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, broadcast_actor_state_update, kNetworkActorStateUpdateParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, broadcast_actor_transform, kNetworkActorStateUpdateParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, claim_actor_ownership, kActorGuidParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, connect_to_peer, kNetworkConnectToPeerParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, get_peer_count, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, get_session_info, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_create, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_delete, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_scene_snapshot, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_scene_snapshot_request, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_state_update, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, poll_pending_actor_transform, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, register_actor_identity, kNetworkRegisterActorIdentityParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, request_actor_scene_snapshot, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, set_project_root, kProjectRootParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, set_sync_paused, kPausedParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, start_session, kNetworkStartSessionParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(Network, stop_session, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, browse_folder, kPathOptionalParam, EditorApiValueType::String),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, create_multiplayer_project, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, create_project, kObjectPayloadParam, EditorApiValueType::String),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, create_world_project, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD0(ProjectLauncher, get_app_version, EditorApiValueType::String),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, get_default_project_path, kNoParams, EditorApiValueType::String),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, get_recent_projects, kNoParams, EditorApiValueType::Array),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, open_project, kPathParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, open_project_file, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectLauncher, set_project_mode, kObjectPayloadParam, EditorApiValueType::Boolean),
    EDITOR_API_METHOD_SCHEMA(ProjectSettings, browse_scene_file, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectSettings, get_active_project_info, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ProjectSettings, save_active_project_info, kObjectPayloadParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, focus_actor, kResourceSearchFocusActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, fuzzy_search, kResourceSearchFuzzySearchParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, get_stats, kCallerParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, image_search, kResourceSearchImageSearchParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, list_types, kCallerParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, mark_index_dirty, kResourceSearchMarkIndexDirtyParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, prepare_index, kCallerParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ResourceSearch, rebuild_index, kCallerParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneDatas, actor_operation, kSceneDatasActorOperationParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneDatas, get_actor, kSceneActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneDatas, get_scene, kSceneNameOptionalParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneDatas, save_actor, kSceneActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneDatas, select_model_file, kSceneDatasSelectModelFileParams, EditorApiValueType::String),
    EDITOR_API_METHOD_SCHEMA(SceneTools, actor_play_audio, kSceneToolsActorPlayAudioParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, actor_stop_audio, kActorNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, close_camera_view, kSceneCameraParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, create_actor, kSceneToolsCreateActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, create_camera_view, kSceneToolsCreateCameraViewParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, create_scene, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, delete_camera, kSceneCameraParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, floor_grid, kSceneToolsFloorGridParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, focus_actor, kSceneToolsFocusActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_output_mode, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_physics_params, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_render_backend, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_shadow_cascade_debug, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_ssao_enabled, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, get_vision_render_mode, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, is_vision_available, kNoParams, EditorApiValueType::Object),
    EDITOR_API_METHOD1(SceneTools, list_actor_tree, "scene_name", EditorApiValueType::String, EditorApiValueType::Array),
    EDITOR_API_METHOD_SCHEMA(SceneTools, list_camera_views, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, list_scene_tree, kSceneNameParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, load_vision_scene, kPathParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, open_actor, kSceneActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, open_camera_view, kSceneCameraParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, pick_actor_at_pixel, kSceneToolsPickActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, play_audio, kSceneToolsPlayAudioParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, reload_scene, kSceneToolsReloadSceneParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, remove_actor, kSceneActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, rename_actor, kSceneToolsRenameActorParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, rename_camera_view, kSceneToolsRenameCameraViewParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, save_screenshot, kSceneToolsSaveScreenshotParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, select_screenshot_path, kSceneToolsCameraOptionalParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_output_mode, kSceneToolsSetOutputModeParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_physics_params, kSceneToolsSetPhysicsParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_render_backend, kSceneToolsSetRenderBackendParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_shadow_cascade_debug, kSceneToolsSetCameraBoolParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_ssao_enabled, kSceneToolsSetCameraBoolParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, set_vision_render_mode, kSceneToolsSetVisionRenderModeParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, stop_audio, kResourceIdParam, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, sun_direction, kSceneToolsSunDirectionParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(SceneTools, update_camera_view, kSceneToolsUpdateCameraViewParams, EditorApiValueType::Object),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, execute_python_code, kScratchExecutePythonCodeParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, get_game_preview_status, kNoParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, get_script_status, kNoParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, key_event, kScratchKeyEventParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, key_release, kScratchKeyReleaseParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, load_blockly_target, kObjectPayloadParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, mouse_event, kScratchMouseEventParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, save_blockly_target, kObjectPayloadParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, start_game_preview, kObjectPayloadParam, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, stop_game_preview, kNoParams, EditorApiValueType::Any),
    EDITOR_API_METHOD_SCHEMA(ScratchTool, stop_script_execution, kNoParams, EditorApiValueType::Any),
}};

#undef EDITOR_API_METHOD_SCHEMA
#undef EDITOR_API_METHOD1
#undef EDITOR_API_METHOD0

constexpr std::array<EditorApiEventSpec, 2> kEditorApiEvents = {{
    {"SceneTools.actorChanged", EditorApiValueType::Object, all_callers()},
    {"ProjectLauncher.projectOpened", EditorApiValueType::Object, all_callers()},
}};

std::atomic<std::uint64_t> g_next_callback_token{1};
std::mutex g_callback_mutex;
std::mutex g_python_script_dispatcher_mutex;
PyObject* g_python_script_dispatcher = nullptr;

struct CallbackRecord {
    std::uint64_t token = 0;
    std::string event_name;
    nlohmann::json callback_spec = nlohmann::json::object();
    NativeContext context;
    bool python_script = false;
};

std::unordered_map<std::uint64_t, CallbackRecord> g_callbacks;

bool caller_allowed(const EditorApiMethodSpec& spec, EditorApiCaller caller) {
    return (spec.allowed_callers & caller_mask(caller)) != 0u;
}

bool event_caller_allowed(const EditorApiEventSpec& spec, EditorApiCaller caller) {
    return (spec.allowed_callers & caller_mask(caller)) != 0u;
}

bool json_matches_type(const nlohmann::json& value, EditorApiValueType type) {
    switch (type) {
        case EditorApiValueType::Any:
            return true;
        case EditorApiValueType::Null:
            return value.is_null();
        case EditorApiValueType::Boolean:
            return value.is_boolean();
        case EditorApiValueType::Integer:
            return value.is_number_integer() || value.is_number_unsigned();
        case EditorApiValueType::Number:
            return value.is_number();
        case EditorApiValueType::String:
            return value.is_string();
        case EditorApiValueType::Object:
            return value.is_object();
        case EditorApiValueType::Array:
            return value.is_array();
    }
    return false;
}

const char* value_type_name(EditorApiValueType type) {
    switch (type) {
        case EditorApiValueType::Any:
            return "any";
        case EditorApiValueType::Null:
            return "null";
        case EditorApiValueType::Boolean:
            return "boolean";
        case EditorApiValueType::Integer:
            return "integer";
        case EditorApiValueType::Number:
            return "number";
        case EditorApiValueType::String:
            return "string";
        case EditorApiValueType::Object:
            return "object";
        case EditorApiValueType::Array:
            return "array";
    }
    return "unknown";
}

NativeResult validate_editor_api_args(const EditorApiMethodSpec& spec, const nlohmann::json& args) {
    const auto normalized_args = args.is_null() ? nlohmann::json::array() : args;
    if (!normalized_args.is_array()) {
        return native_failure(std::string("invalid Editor API arguments for ") + spec.api_name +
                                  ": args must be an array",
                              400,
                              "editor-api");
    }
    if (spec.params == nullptr) {
        // Unspecified Editor API schema: keep existing argument compatibility
        // while modules are migrated to explicit C++ specs one by one.
        return native_success(nlohmann::json::object(), "editor-api");
    }
    if (normalized_args.size() > spec.param_count) {
        return native_failure(std::string("invalid Editor API arguments for ") + spec.api_name +
                                  ": too many arguments",
                              400,
                              "editor-api");
    }
    for (std::size_t index = 0; index < spec.param_count; ++index) {
        const auto& param_spec = spec.params[index];
        if (index >= normalized_args.size()) {
            if (param_spec.optional) {
                continue;
            }
            return native_failure(std::string("invalid Editor API arguments for ") + spec.api_name +
                                      ": missing " + param_spec.name,
                                  400,
                                  "editor-api");
        }
        const auto& value = normalized_args[index];
        if (value.is_null() && param_spec.optional) {
            continue;
        }
        if (!json_matches_type(value, param_spec.type)) {
            return native_failure(std::string("invalid Editor API arguments for ") + spec.api_name +
                                      ": " + param_spec.name + " must be " +
                                      value_type_name(param_spec.type),
                                  400,
                                  "editor-api");
        }
    }
    return native_success(nlohmann::json::object(), "editor-api");
}

NativeResult validate_editor_api_result(const EditorApiMethodSpec& spec, const nlohmann::json& data) {
    if (!json_matches_type(data, spec.return_spec.type)) {
        return native_failure(std::string("invalid Editor API result for ") + spec.api_name +
                                  ": result must be " + value_type_name(spec.return_spec.type),
                              500,
                              "editor-api");
    }
    return native_success(nlohmann::json::object(), "editor-api");
}

bool validate_editor_api_event_payload(const EditorApiEventSpec& spec,
                                       const nlohmann::json& payload) {
    if (json_matches_type(payload, spec.payload_type)) {
        return true;
    }
    CFW_LOG_WARNING("invalid Editor API event payload for {}: expected {}",
                    spec.event_name,
                    value_type_name(spec.payload_type));
    return false;
}

NativeResult invoke_native_api_method(const EditorApiMethodSpec& spec,
                                      const nlohmann::json& args,
                                      const NativeContext& context) {
    NativeRequest native_request;
    native_request.module = spec.legacy_module;
    native_request.function = spec.legacy_function;
    native_request.args = args.is_null() ? nlohmann::json::array() : args;

    auto result = NativeApiRegistry::instance().dispatch(native_request, context);
    if (!result) {
        return native_failure(std::string(spec.api_name) + " has no native implementation",
                              500,
                              "editor-api");
    }
    result->route = "editor-api";
    return *result;
}

std::optional<int> browser_identifier(const NativeContext& context) {
    if (!context.browser) {
        return std::nullopt;
    }
    return context.browser->GetIdentifier();
}

std::size_t emit_callbacks(std::string_view event_name,
                           const nlohmann::json& payload,
                           bool python_script) {
    std::vector<CallbackRecord> records;
    {
        std::lock_guard<std::mutex> lock(g_callback_mutex);
        for (const auto& [_, record] : g_callbacks) {
            if (record.python_script == python_script && record.event_name == event_name) {
                records.push_back(record);
            }
        }
    }

    std::size_t emitted = 0;
    for (const auto& record : records) {
        if (!python_script && record.context.frame) {
            nlohmann::json event_payload;
            event_payload["event"] = record.event_name;
            event_payload["payload"] = payload;
            event_payload["token"] = record.token;
            const auto script = "window.__coronaEditorApiDispatch && "
                                "window.__coronaEditorApiDispatch(" +
                                event_payload.dump() + ");";
            record.context.frame->ExecuteJavaScript(script, record.context.frame->GetURL(), 0);
        }
        ++emitted;
    }
    return emitted;
}

std::string python_script_request_json(const NativeRequest& request) {
    nlohmann::json payload;
    payload["module"] = request.module;
    payload["function"] = request.function;
    payload["args"] = request.args.is_null() ? nlohmann::json::array() : request.args;
    return payload.dump();
}

std::string python_script_error_message(const nlohmann::json& payload) {
    if (auto it = payload.find("error"); it != payload.end() && it->is_string()) {
        return it->get<std::string>();
    }
    if (auto it = payload.find("message"); it != payload.end() && it->is_string()) {
        return it->get<std::string>();
    }
    return "Python script service returned an error";
}

}  // namespace

EditorApiRegistry& EditorApiRegistry::instance() {
    static EditorApiRegistry registry;
    return registry;
}

const EditorApiMethodSpec* EditorApiRegistry::find(std::string_view api_name) const {
    for (const auto& spec : kEditorApiMethods) {
        if (api_name == spec.api_name) {
            return &spec;
        }
    }
    return nullptr;
}

std::vector<EditorApiMethodSpec> EditorApiRegistry::list_methods() const {
    return {kEditorApiMethods.begin(), kEditorApiMethods.end()};
}

NativeResult EditorApiRegistry::invoke(const EditorApiRequest& request,
                                       const NativeContext& context) const {
    const auto* spec = find(request.api_name);
    if (!spec) {
        return native_failure(request.api_name + " is not defined by C++ Editor API",
                              404,
                              "editor-api");
    }
    if (!caller_allowed(*spec, request.caller)) {
        return native_failure(request.api_name + " is not allowed for this caller",
                              403,
                              "editor-api");
    }
    auto args_validation = validate_editor_api_args(*spec, request.args);
    if (!args_validation.success) {
        return args_validation;
    }
    auto result = invoke_native_api_method(*spec, request.args, context);
    if (!result.success) {
        return result;
    }
    auto result_validation = validate_editor_api_result(*spec, result.data);
    if (!result_validation.success) {
        return result_validation;
    }
    return result;
}

NativeResult CefEditorApiEndpoint::invoke(const std::string& api_name,
                                          const nlohmann::json& args,
                                          const NativeContext& context) {
    return EditorApiRegistry::instance().invoke({api_name, args, EditorApiCaller::Cef}, context);
}

std::uint64_t CefEditorApiEndpoint::register_callback(const std::string& event_name,
                                                      const nlohmann::json& callback_spec,
                                                      const NativeContext& context) {
    return EditorApiCallbackRegistry::instance().register_cef_callback(event_name,
                                                                       callback_spec,
                                                                       context);
}

bool CefEditorApiEndpoint::unregister_callback(std::uint64_t callback_token) {
    return EditorApiCallbackRegistry::instance().unregister(callback_token);
}

NativeResult PythonEditorApiEndpoint::invoke(const std::string& api_name,
                                             const nlohmann::json& args,
                                             const NativeContext& context) {
    return EditorApiRegistry::instance().invoke({api_name, args, EditorApiCaller::Python}, context);
}

std::uint64_t PythonEditorApiEndpoint::register_callback(const std::string& event_name,
                                                         const nlohmann::json& callback_spec,
                                                         const NativeContext& context) {
    return EditorApiCallbackRegistry::instance().register_python_script_callback(event_name,
                                                                                callback_spec,
                                                                                context);
}

bool PythonEditorApiEndpoint::unregister_callback(std::uint64_t callback_token) {
    return EditorApiCallbackRegistry::instance().unregister(callback_token);
}

std::optional<EditorApiRequest> parse_editor_api_request(const nlohmann::json& payload,
                                                         EditorApiCaller caller) {
    if (!payload.is_object()) {
        return std::nullopt;
    }
    const auto api_it = payload.find("api");
    if (api_it == payload.end() || !api_it->is_string()) {
        return std::nullopt;
    }

    EditorApiRequest request;
    request.api_name = api_it->get<std::string>();
    request.caller = caller;
    if (auto args_it = payload.find("args"); args_it != payload.end()) {
        request.args = args_it->is_null() ? nlohmann::json::array() : *args_it;
    }
    return request;
}

EditorApiCallbackRegistry& EditorApiCallbackRegistry::instance() {
    static EditorApiCallbackRegistry registry;
    return registry;
}

std::uint64_t EditorApiCallbackRegistry::register_cef_callback(
    const std::string& event_name,
    const nlohmann::json& callback_spec,
    const NativeContext& context) {
    const auto event_spec = find_editor_api_event(event_name);
    if (!event_spec || !event_caller_allowed(*event_spec, EditorApiCaller::Cef)) {
        return 0;
    }
    const auto token = g_next_callback_token.fetch_add(1);
    CallbackRecord record;
    record.token = token;
    record.event_name = event_name;
    record.callback_spec = callback_spec;
    record.context = context;
    record.python_script = false;
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    g_callbacks[token] = std::move(record);
    return token;
}

std::uint64_t EditorApiCallbackRegistry::register_python_script_callback(
    const std::string& event_name,
    const nlohmann::json& callback_spec,
    const NativeContext& context) {
    const auto event_spec = find_editor_api_event(event_name);
    if (!event_spec || !event_caller_allowed(*event_spec, EditorApiCaller::Python)) {
        return 0;
    }
    const auto token = g_next_callback_token.fetch_add(1);
    CallbackRecord record;
    record.token = token;
    record.event_name = event_name;
    record.callback_spec = callback_spec;
    record.context = context;
    record.python_script = true;
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    g_callbacks[token] = std::move(record);
    return token;
}

bool EditorApiCallbackRegistry::unregister(std::uint64_t callback_token) {
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    return g_callbacks.erase(callback_token) > 0;
}

void EditorApiCallbackRegistry::clear_cef_callbacks_for_browser(int browser_id) {
    std::lock_guard<std::mutex> lock(g_callback_mutex);
    for (auto it = g_callbacks.begin(); it != g_callbacks.end();) {
        const auto record_browser_id = browser_identifier(it->second.context);
        if (!it->second.python_script && record_browser_id && *record_browser_id == browser_id) {
            it = g_callbacks.erase(it);
        } else {
            ++it;
        }
    }
}

std::size_t EditorApiCallbackRegistry::emit_editor_api_event(std::string_view event_name,
                                                             const nlohmann::json& payload) {
    const auto event_spec = find_editor_api_event(event_name);
    if (!event_spec || !event_caller_allowed(*event_spec, EditorApiCaller::Cef) ||
        !validate_editor_api_event_payload(*event_spec, payload)) {
        return 0;
    }
    return emit_callbacks(event_name, payload, false);
}

std::size_t EditorApiCallbackRegistry::emit_python_script_event(std::string_view event_name,
                                                                const nlohmann::json& payload) {
    const auto event_spec = find_editor_api_event(event_name);
    if (!event_spec || !event_caller_allowed(*event_spec, EditorApiCaller::Python) ||
        !validate_editor_api_event_payload(*event_spec, payload)) {
        return 0;
    }
    return emit_callbacks(event_name, payload, true);
}

std::optional<EditorApiEventSpec> find_editor_api_event(std::string_view event_name) {
    for (const auto& event_spec : kEditorApiEvents) {
        if (event_name == event_spec.event_name) {
            return event_spec;
        }
    }
    return std::nullopt;
}

std::size_t emit_editor_api_event(std::string_view event_name, const nlohmann::json& payload) {
    return EditorApiCallbackRegistry::instance().emit_editor_api_event(event_name, payload);
}

std::size_t emit_python_script_event(std::string_view event_name, const nlohmann::json& payload) {
    return EditorApiCallbackRegistry::instance().emit_python_script_event(event_name, payload);
}

void register_python_script_dispatcher(PyObject* dispatcher) {
    if (!Py_IsInitialized()) {
        return;
    }

    PyGILState_STATE state = PyGILState_Ensure();
    PyObject* old_dispatcher = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_python_script_dispatcher_mutex);
        if (dispatcher && PyCallable_Check(dispatcher)) {
            Py_INCREF(dispatcher);
            old_dispatcher = g_python_script_dispatcher;
            g_python_script_dispatcher = dispatcher;
        }
    }
    Py_XDECREF(old_dispatcher);
    PyGILState_Release(state);
}

void unregister_python_script_dispatcher() {
    if (!Py_IsInitialized()) {
        std::lock_guard<std::mutex> lock(g_python_script_dispatcher_mutex);
        g_python_script_dispatcher = nullptr;
        return;
    }

    PyGILState_STATE state = PyGILState_Ensure();
    PyObject* old_dispatcher = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_python_script_dispatcher_mutex);
        old_dispatcher = g_python_script_dispatcher;
        g_python_script_dispatcher = nullptr;
    }
    Py_XDECREF(old_dispatcher);
    PyGILState_Release(state);
}

NativeResult invoke_python_script_service(const NativeRequest& request, const char* route) {
    const std::string route_name = route && *route ? route : "python-script";
    if (!Py_IsInitialized()) {
        return native_failure("Python script runtime is not initialized",
                              503,
                              route_name);
    }

    PyGILState_STATE state = PyGILState_Ensure();
    PyObject* dispatcher = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_python_script_dispatcher_mutex);
        dispatcher = g_python_script_dispatcher;
        Py_XINCREF(dispatcher);
    }
    if (!dispatcher) {
        PyGILState_Release(state);
        return native_failure("Python script dispatcher is not registered",
                              503,
                              route_name);
    }

    PyObject* py_request = PyUnicode_FromString(python_script_request_json(request).c_str());
    PyObject* py_args = py_request ? PyTuple_Pack(1, py_request) : nullptr;
    Py_XDECREF(py_request);

    PyObject* object = py_args ? PyObject_CallObject(dispatcher, py_args) : nullptr;
    Py_DECREF(dispatcher);
    Py_XDECREF(py_args);

    if (!object) {
        PyErr_Print();
        PyGILState_Release(state);
        return native_failure("Python script function call failed",
                              500,
                              route_name);
    }

    PyObject* string_object = PyUnicode_Check(object) ? object : PyObject_Str(object);
    const char* result_chars = string_object ? PyUnicode_AsUTF8(string_object) : nullptr;
    const std::string result_text = result_chars ? result_chars : "";
    if (string_object != object) {
        Py_XDECREF(string_object);
    }
    Py_DECREF(object);
    PyGILState_Release(state);

    const auto parsed = nlohmann::json::parse(result_text, nullptr, false);
    if (parsed.is_discarded()) {
        return native_success(result_text, route_name);
    }
    if (parsed.is_object() && parsed.value("success", true) == false) {
        return native_failure(python_script_error_message(parsed),
                              500,
                              route_name);
    }
    if (parsed.is_object()) {
        if (auto it = parsed.find("data"); it != parsed.end()) {
            return native_success(*it, route_name);
        }
    }
    return native_success(parsed, route_name);
}

}  // namespace Corona::Systems::UI

