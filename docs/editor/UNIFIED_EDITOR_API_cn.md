# C++ 统一 Editor API 设计与接入指南

> 状态：现行文档
> 适用范围：Vue/CEF 编辑器业务接口、C++ Editor API registry、Python 脚本层、编辑器事件与回调
> 结论：C++ 是唯一 Editor API 后端。JS 和 Python 只能消费 C++ 定义的方法、事件和 wrapper path。

## 1. 当前架构

当前业务调用链路为：

```text
Vue 业务组件
  -> editorApi.<typed wrapper>(...)
  -> editor/Frontend/src/utils/bridge.js
  -> cefQuery transport, payload = { api, args }
  -> src/systems/ui/cef/cef_query_bridge.cpp
  -> EditorApiRegistry
  -> NativeApiRegistry / C++ handler
  -> C++ service/system
  -> 可选：C++ 显式调用 Python script service
```

Python 不再作为 Editor API backend，也不接收 CEF fallback 分发。Python 只作为脚本运行层，用于 AI、角色、工具脚本等逻辑：

```text
C++ native handler
  -> invoke_python_script_service({ module, function, args })
  -> CoronaEditor.dispatch_script_request_from_cpp()
  -> Python script service
```

Python 脚本请求 payload 只能是 `{ module, function, args }`。如果 Python script dispatcher 收到 `{ api }`，会拒绝该请求，避免重新形成 Editor API 后门。

## 2. 唯一接口定义源

所有 Editor API 方法由 C++ 定义：

- `src/systems/ui/cef/cef_editor_api.h`
  - `EditorApiMethodSpec`
  - `EditorApiEventSpec`
  - `EditorApiRegistry`
  - `EditorApiCallbackRegistry`
- `src/systems/ui/cef/cef_editor_api.cpp`
  - `kEditorApiMethods`
  - `kEditorApiEvents`

一个方法 spec 包含：

| 字段 | 含义 |
|---|---|
| `api_name` | C++ 内部方法名，例如 `SceneTools.create_actor` |
| `native_module` / `native_function` | 交给 `NativeApiRegistry` dispatch 的内部模块和函数 |
| `params` | 参数 schema |
| `return_spec` | 返回值 schema |
| `js_wrapper` | Vue/JS 允许调用的 typed wrapper path |
| `python_wrapper` | Python 脚本允许调用的 wrapper path |
| `allowed_callers` | 允许的调用方，例如 CEF、PythonScript |

一个事件 spec 包含：

| 字段 | 含义 |
|---|---|
| `event_name` | C++ 事件名，例如 `SceneTools.actorChanged` |
| `payload_type` | payload schema |
| `js_wrapper` | JS 订阅 wrapper path |
| `python_wrapper` | Python 脚本订阅 wrapper path |
| `allowed_callers` | 允许订阅或发射的调用方 |

## 3. JS 侧规则

Vue 业务组件只能使用 `editorApi` typed wrapper：

```js
await editorApi.sceneTools.createActor(sceneName, objPath, "model");
const token = await editorApi.events.onActorChanged((payload) => {
  // ...
});
await editorApi.off(token);
```

`editor/Frontend/src/utils/bridge.js` 负责：

- 通过 `EditorApi.list_methods` 获取 C++ method manifest。
- 通过 `EditorApi.list_events` 获取 C++ event manifest。
- 校验 wrapper path 是否由 C++ 定义。
- 校验参数数量、参数类型和返回类型。
- 通过内部 `call_editor_api()` 使用 `cefQuery` transport。

禁止在 Vue 业务文件中使用：

- `window.cefQuery`
- `Bridge.callCEF`
- `editorApi.invoke`
- 手写 `{ module, function, args }`
- 手写 C++ API 名作为业务调用入口

`cefQuery` 可以保留在 `bridge.js` 内部，作为 transport 细节。

## 4. Python 侧规则

Python 侧入口为：

- `editor/CoronaCore/core/editor_api.py`
  - `CoronaEditorApi`
  - `_invoke_manifest_cpp_api(wrapper_path, args)`
  - `_register_manifest_editor_api_event_callback(wrapper_path, callback)`
  - `_emit_manifest_cpp_editor_api_event(wrapper_path, payload)`

Python 脚本调用 C++ Editor API 时，也只能使用 C++ manifest 中声明过的 `python_wrapper`：

```python
from CoronaCore.core.editor_api import CoronaEditorApi

tree = CoronaEditorApi.scene.list_actor_tree("default.scene")
token = CoronaEditorApi.events.on_actor_changed(callback)
CoronaEditorApi.editor.off(token)
```

Python 脚本层不允许：

- 实现 Editor API backend。
- 暴露任意 Python 函数给 CEF fallback 调用。
- 在业务 wrapper 中手写 `SceneTools.*`、`Network.*`、`AITool.*` 等 C++ API 名。
- 在业务事件 wrapper 中手写 `SceneTools.actorChanged` 等 C++ 事件名。

如果需要 Python 执行业务逻辑，应由 C++ native handler 显式调用 script service：

```text
JS -> C++ Editor API -> C++ handler -> invoke_python_script_service()
```

## 5. Native handler 与内部 dispatch

`NativeApiRegistry` 是 C++ 内部 dispatch 机制，不是公开 RPC 模型。

相关文件：

- `src/systems/ui/cef/cef_editor_native_api_registry.h`
- `src/systems/ui/cef/cef_editor_native_api_registry.cpp`
- `src/systems/ui/cef/cef_editor_native_api_handlers.cpp`

公开业务入口必须先进入 `EditorApiRegistry`。`NativeApiRegistry` 只负责把已通过 C++ spec 校验的请求交给具体 C++ handler。

## 6. 新增方法流程

### 6.1 实现 C++ handler

在 `cef_editor_native_api_handlers.cpp` 中添加或扩展 native handler：

```cpp
{"new_method", [](const NativeRequest& request, const NativeContext& context) {
    const auto scene_name = arg_string(request.args, 0);
    return native_success({{"ok", true}, {"scene", scene_name}});
}}
```

### 6.2 在 C++ registry 定义 schema 和 wrapper

在 `cef_editor_api.cpp` 中添加参数 schema 和 method spec：

```cpp
constexpr std::array<EditorApiParamSpec, 1> kSceneNameParam = {{
    param("scene_name", EditorApiValueType::String),
}};

EDITOR_API_METHOD_SCHEMA_WRAPPED(
    SceneTools,
    new_method,
    kSceneNameParam,
    "sceneTools.newMethod",
    "scene_tools.new_method",
    EditorApiValueType::Object
),
```

### 6.3 添加 JS typed wrapper

在 `bridge.js` 中添加：

```js
sceneTools: {
  newMethod: (sceneName) =>
    call_manifest_editor_api("sceneTools.newMethod", [sceneName]),
}
```

Vue 调用：

```js
await editorApi.sceneTools.newMethod(sceneName);
```

### 6.4 Python wrapper

如果使用动态 wrapper，一般无需手写。调用方式：

```python
CoronaEditorApi.scene_tools.new_method(scene_name)
```

如果需要显式静态 wrapper，应只写 wrapper path：

```python
def new_method(scene_name):
    return _invoke_manifest_cpp_api("scene_tools.new_method", [scene_name])
```

## 7. 新增事件流程

### 7.1 在 C++ registry 定义事件

在 `cef_editor_api.cpp` 的 `kEditorApiEvents` 中添加：

```cpp
{"SceneTools.myEvent", EditorApiValueType::Object, all_callers(),
 "events.onMyEvent", "events.on_my_event"},
```

### 7.2 C++ 发射事件

```cpp
emit_editor_api_event("SceneTools.myEvent", payload);
```

### 7.3 添加 JS 订阅 wrapper

```js
events: {
  onMyEvent: (callback) =>
    register_manifest_editor_api_callback("events.onMyEvent", callback),
}
```

### 7.4 Python 脚本订阅

动态 wrapper 可直接使用：

```python
token = CoronaEditorApi.events.on_my_event(callback)
```

如果需要历史 Python 脚本事件转发到 Editor API 事件，应在 `CoronaEditor.emit_editor_event()` 中映射到 `python_wrapper`，不要映射到 C++ `event_name`：

```python
"legacy-event": ("events.on_my_event", lambda values: {...})
```

## 8. 回调生命周期

回调由 C++ `EditorApiCallbackRegistry` 统一管理：

- JS 订阅返回 callback token。
- Python 脚本订阅返回 callback token。
- `editorApi.off(token)` 或 `CoronaEditorApi.editor.off(token)` 用于取消订阅。
- CEF browser 销毁时清理 JS callbacks。
- Python shutdown 时清理 Python callbacks。

业务层不要自己维护跨语言 callback 协议。

## 9. 不属于 Editor API 的通道

以下通道不是本轮业务 Editor API：

- Dock/window 内部命令：`coronaBridge.dockCommand`
- viewport/input/realtime 内部通道：`cef_realtime_bridge.cpp`
- CEF transport 细节：`cefQuery`
- Python OOP 引擎绑定：`CoronaEngine.Scene`、`Actor`、`Geometry` 等脚本 API

这些通道可以存在，但不应被描述为业务 Editor API。

## 10. 验证命令

修改接口后至少运行：

```powershell
third_party\Python-3.13.7\python.exe -m unittest editor.plugins.SceneTools.tests.test_native_screenshot_rpc
third_party\Python-3.13.7\python.exe -m py_compile editor\CoronaCore\core\editor_api.py editor\CoronaCore\core\corona_editor.py editor\backend\registry.py
third_party\node-v22.19.0-win-x64\node.exe --check editor\Frontend\src\utils\bridge.js
```

涉及前端业务文件时运行：

```powershell
D:\CoronaEngine\third_party\node-v22.19.0-win-x64\npm.cmd run build
```

涉及 C++ 时运行：

```powershell
cmd.exe /d /s /c '"C:\Program Files\Microsoft Visual Studio\18\Community\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64 >nul && cmake --build D:/CoronaEngine/build --config RelWithDebInfo --target corona_engine -- --quiet'
```

## 11. 静态红线

新增或修改接口时，应确认：

- 前端业务文件不出现 `window.cefQuery`。
- 前端业务文件不出现 `Bridge.callCEF`。
- 前端业务文件不直接调用 `editorApi.invoke`。
- Python Editor API wrapper 不手写 C++ 业务 API 名。
- Python Editor API event wrapper 不手写 C++ event name。
- CEF query bridge 不 import Python，不查找 Python fallback。
- C++ 不再出现 `EditorApiBackend::Python`。

这些红线已纳入 `editor/plugins/SceneTools/tests/test_native_screenshot_rpc.py` 的静态测试。
