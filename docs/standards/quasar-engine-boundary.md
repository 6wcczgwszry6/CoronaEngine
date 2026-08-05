# Quasar 与 CoronaEngine AI 代码边界规范

状态：强制执行  
适用范围：Quasar 通用 AI 库、CoronaEngine `editor/plugins/AITool` 及两者的集成代码

## 1. 目标

Quasar 是可独立安装、测试和嵌入不同宿主的通用 AI 库。CoronaEngine 是 Quasar 的一个宿主，负责编辑器、引擎、项目和产品领域能力。

本规范确保：

- Quasar 不因 CoronaEngine 的目录、类型或生命周期而无法独立运行。
- Engine 能通过明确的 protocol、provider、adapter 和 plugin 接入 Quasar。
- 代码归属由责任和依赖决定，不由“代码当前在哪里能跑”决定。

## 2. 核心规则

依赖方向必须是：

```text
CoronaEngine / AITool / cai_extensions
                    ↓
                  Quasar
```

Quasar 不得导入或动态查找：

- `CoronaCore`、`CoronaEngine`、`CabbageEditor`、`plugins.AITool`、Engine `services`；
- Scene、Actor、Camera、CEF、Dock、Editor selection 等宿主概念；
- Engine 项目 schema、资源导入器、截图、网络同步或线程亲和 API；
- `Backend` / `Frontend` 等特定产品目录结构。

禁止通过 `try/except ImportError`、字符串导入或路径回退隐藏反向依赖。“宿主不存在时忽略错误”仍然属于边界违规。

## 3. 代码归属

### 3.1 Quasar 负责

- 与产品无关的 LLM / VLM / 图像 / 视频 / 语音 / 3D 模型 provider 客户端。
- 通用 Agent 执行、会话、工作流、媒体资源和工具注册基础设施。
- 只包含纯数据的 request / response / stream / error 协议。
- 通用的取消、deadline、retry、并发、缓存和存储抽象。
- 可被多个宿主实现的 capability protocol、provider 和 plugin 接口。
- 不含宿主默认值的通用配置类型和序列化规则。

### 3.2 CoronaEngine 负责

- Scene、Actor、Camera、Transform、Material、Geometry 和 Engine resource 操作。
- CEF / Editor 请求、面板、选择状态、进度和错误展示。
- Engine 项目路径、场景格式、截图、导入、保存和热重载策略。
- Engine 线程、GIL、请求队列、网络同步和 shutdown 协调。
- CoronaEngine 专用 prompt、场景生成 workflow、MCP 工具和产品策略。
- Quasar protocol 的 Engine adapter 和宿主 plugin 安装入口。

### 3.3 决策表

| 问题 | 是 | 否 |
|---|---|---|
| 离开 CoronaEngine 后能否保持完整语义？ | 继续判断 | 放 Engine |
| 是否至少有两种不同宿主可合理实现？ | 可在 Quasar 定义 protocol | 放 Engine |
| 是否需要 Actor / Scene / CEF / Engine 项目事实？ | 放 Engine | 继续判断 |
| 是否只是 provider 协议或纯数据转换？ | 放 Quasar | 继续判断 |
| 默认值是否含产品目录、项目 schema 或 UI 概念？ | 实现放 Engine | 可在 Quasar |

无法确定时，默认先放 Engine；等第二个真实宿主出现后再提取通用接口。

## 4. 集成模式

### 4.1 Protocol 与 adapter

Quasar 可定义最小 protocol：

```python
class StorageProvider(Protocol):
    def save(self, payload: bytes, metadata: Mapping[str, object]) -> str: ...
```

Engine 实现并注入：

```python
class CoronaProjectStorageProvider:
    def save(self, payload, metadata):
        # Engine 项目路径、资源 ID 和写入队列仅出现在这里。
        ...
```

Protocol 名称必须表达能力，不得使用 `Corona*`、`Cabbage*`、`Actor*` 等宿主名称。Engine adapter 则应明确使用宿主名称。

### 4.2 Plugin 与 hook

- Quasar 只保存 plugin manager、capability registry 和通用生命周期。
- Engine 的 `cai_extensions` 注册路径 provider、Engine tool、workflow 和同步 scope。
- hook 必须可清除、可替换、线程安全，且 shutdown 后拒绝新调用。
- Quasar 不得为某个 Engine plugin 预注册默认实现。

### 4.3 数据边界

跨库边界只传递：

- dataclass / TypedDict / JSON 可表示的纯数据；
- 明确的不透明 token 或 resource ID；
- 不持有 Engine 对象的 callback、protocol 实现或 context manager。

不得跨边界传递 Engine 对象、CEF frame、nanobind object、未受管 Future 或带 GIL 所有权的对象。

## 5. 文件系统与配置

- Quasar 可使用库自身的 config/cache/data 目录，或由宿主注入通用 storage/path provider。
- `active_project`、`Backend`、`Frontend`、`Scene`、`Models`、`Screenshots` 等产品路径不能成为 Quasar 默认结构。
- Quasar 不创建 Engine 项目目录，不解析 Engine 项目配置。
- Engine 在 adapter 中完成路径规范化、权限校验和项目生命周期同步。

## 6. 生命周期与并发

- Quasar 提供通用 `initialize / request_shutdown / shutdown / snapshot` 语义。
- Engine 决定何时启动、停止、路由线程和设置总 deadline。
- Quasar 中的长时任务必须支持通用 stop token 或 cancellation protocol。
- Engine 后台线程不能直接操作 Quasar 内的 Python 对象；必须经 Engine Python runtime coordinator。

## 7. 测试和门禁

Quasar 变更至少要满足：

1. 在不安装 CoronaEngine 模块的环境中可 import 公共 facade。
2. Quasar 生产代码不包含 Engine 包的直接或字符串导入。
3. 通用 protocol 使用 fake provider 可独立测试。
4. 无宿主 plugin 时不创建宿主目录、不连接 Engine service。
5. 取消、超时和 shutdown 不依赖 Engine 全局状态。

Engine 集成变更还要满足：

1. adapter 注册和清理成对。
2. 项目切换不残留旧 provider / callback / workflow scope。
3. Engine 对象仅在 Engine 线程或现有请求队列上使用。
4. Quasar 升级后公共 contract 测试和 Engine adapter 测试同时通过。

## 8. 评审清单

新增或移动 AI 代码时必须回答：

- [ ] 该能力离开 CoronaEngine 是否仍有完整语义？
- [ ] Quasar 是否导入或查找了宿主模块？
- [ ] 宿主对象是否被包装为通用 protocol 或纯数据？
- [ ] 默认路径和配置是否包含 Engine 产品假设？
- [ ] Engine adapter 是否有注册、取消和 shutdown 测试？
- [ ] 公共 Quasar API 是否真的需要被多宿主使用？

## 9. 例外和迁移

- 例外必须在代码评审中记录原因、负责人、到期时间和退出路径。
- 不允许以“历史兼容”作为无期限的反向依赖理由。
- 迁移顺序为：先增加通用 contract 和测试，再在 Engine 实现 adapter，然后切换调用，最后删除 Quasar 中的宿主代码。
- 本地边界审计和迁移清单不是公共规范的一部分，不得提交到远端。
