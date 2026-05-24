# Python 脚本系统重构 TODO

> **创建日期**: 2025年11月5日  
> **目标**: 将 Python API 重构为符合 CoronaEngine 架构的模块化系统

## 📋 概述

当前 Python API 存在以下问题：
- 直接在 `Engine::run()` 中创建和调用，未遵循系统架构
- 路径硬编码，缺乏配置管理
- 职责混乱，`PythonAPI` 类承担过多功能
- 生命周期管理不清晰
- 与 ECS 架构脱节（使用静态全局 `registry_`）
- 缺少抽象层，无法扩展其他脚本语言

**重构目标**: 将 Python 功能作为独立的 `ScriptSystem` 集成到引擎架构中，遵循系统化、模块化、事件驱动的设计原则。

---

## 🎯 重构阶段规划

### ✅ 阶段 0：准备工作
- [x] 分析现有代码结构
- [x] 识别架构问题
- [x] 制定重构方案
- [ ] 创建功能测试用例（保证重构后功能不变）
- [ ] 备份当前实现

---

### 📦 阶段 1：创建脚本系统抽象层

**目标**: 定义脚本系统的接口和基础架构

#### 1.1 定义脚本运行时接口
- [ ] 创建 `include/corona/systems/script/i_script_runtime.h`
  - [ ] 定义 `IScriptRuntime` 接口
  - [ ] 包含生命周期方法（`initialize`, `shutdown`）
  - [ ] 包含脚本执行方法（`execute_script`, `reload_scripts`）
  - [ ] 包含模块管理方法（`load_module`, `unload_module`）
  - [ ] 包含事件处理方法（`on_event`）

#### 1.2 创建 ScriptSystem
- [ ] 创建 `include/corona/systems/script_system.h`
  - [ ] 继承 `Kernel::SystemBase`
  - [ ] 设置优先级为 50（中等优先级）
  - [ ] 实现生命周期方法
  - [ ] 添加运行时依赖注入接口
- [ ] 创建 `src/systems/src/scriptsystem/script_system.cpp`
  - [ ] 实现 `initialize()` 方法
  - [ ] 实现 `update()` 方法（调用运行时更新）
  - [ ] 实现 `shutdown()` 方法
  - [ ] 实现事件监听器设置

#### 1.3 注册 ScriptSystem
- [ ] 在 `src/engine.cpp` 的 `register_systems()` 中添加 `ScriptSystem`
- [ ] 添加必要的头文件引用
- [ ] 移除旧的 `PythonAPI` 直接调用（暂时保留条件编译）

**验收标准**:
- ScriptSystem 能够成功注册并初始化
- 系统按优先级正确排序
- 日志显示 ScriptSystem 的生命周期事件

---

### 🐍 阶段 2：重构 Python 运行时

**目标**: 将现有 `PythonAPI` 重构为符合新架构的 `PythonRuntime`

#### 2.1 创建配置结构
- [ ] 创建 `include/corona/systems/script/python_config.h`
  - [ ] 定义 `PythonConfig` 结构体
  - [ ] 包含 Python 主目录路径
  - [ ] 包含模块搜索路径列表
  - [ ] 包含入口模块和函数名
  - [ ] 包含热重载配置（启用/间隔/监控模式）

#### 2.2 实现 PythonRuntime
- [ ] 创建 `include/corona/systems/script/python_runtime.h`
  - [ ] 实现 `IScriptRuntime` 接口
  - [ ] 使用 PIMPL 模式隐藏 Python.h 依赖
  - [ ] 添加配置注入构造函数
- [ ] 创建 `src/systems/src/scriptsystem/python/python_runtime.cpp`
  - [ ] 迁移 `PythonAPI::ensureInitialized()` 逻辑
  - [ ] 迁移 `PythonAPI::runPythonScript()` 逻辑
  - [ ] 迁移 `PythonAPI::invokeEntry()` 逻辑
  - [ ] 改进错误处理（发布事件而不是直接 cerr）

#### 2.3 拆分职责模块
- [ ] 创建 `PythonEnvironment` 类
  - [ ] 文件: `src/systems/src/scriptsystem/python/python_environment.h/cpp`
  - [ ] 负责 Python 解释器初始化和关闭
  - [ ] 管理 PyConfig
  - [ ] 管理模块搜索路径
  - [ ] 提供 GIL 状态查询

- [ ] 创建 `PythonModuleManager` 类
  - [ ] 文件: `src/systems/src/scriptsystem/python/python_module_manager.h/cpp`
  - [ ] 负责模块加载和缓存
  - [ ] 提供模块重载功能
  - [ ] 管理模块引用生命周期
  - [ ] 提供模块查询接口

- [ ] 创建 `PythonHotReloader` 类
  - [ ] 文件: `src/systems/src/scriptsystem/python/python_hot_reloader.h/cpp`
  - [ ] 迁移现有 `PythonHotfix` 功能
  - [ ] 文件监控和变更检测
  - [ ] 依赖图构建和分析
  - [ ] 批量重载逻辑
  - [ ] 去除文件复制逻辑（改为直接监控运行时目录）

- [ ] 创建 `PythonGILGuard` RAII 类
  - [ ] 文件: `src/systems/src/scriptsystem/python/python_gil_guard.h`
  - [ ] 封装 `nanobind::gil_scoped_acquire`
  - [ ] 提供调试日志（可选）

#### 2.4 错误处理改进
- [ ] 创建 Python 错误转换工具
  - [ ] 将 `nanobind::python_error` 转换为引擎事件
  - [ ] 提取堆栈跟踪信息
  - [ ] 格式化错误消息
- [ ] 发布 `ScriptErrorEvent` 而不是直接输出到 cerr

**验收标准**:
- PythonRuntime 能够独立初始化 Python 环境
- 能够加载和执行 Python 脚本
- 热重载功能正常工作
- 错误通过事件系统报告

---

### 🔌 阶段 3：重构 C++ API 暴露层

**目标**: 解除 API 与全局状态的耦合，通过服务提供者模式访问引擎功能

#### 3.1 创建服务提供者接口
- [ ] 创建 `include/corona/script/i_script_service_provider.h`
  - [ ] 定义 `IScriptServiceProvider` 接口
  - [ ] 提供 ECS registry 访问方法
  - [ ] 提供事件总线发布方法
  - [ ] 提供资源加载方法
  - [ ] 提供日志访问方法
  - [ ] 提供场景管理方法

#### 3.2 实现服务提供者
- [ ] 创建 `src/script/src/script_service_provider.cpp`
  - [ ] 实现 `ScriptServiceProvider` 类
  - [ ] 在构造函数中注入 `ISystemContext`
  - [ ] 实现所有接口方法，委托给对应的系统

#### 3.3 重构 CoronaEngineAPI
- [ ] 修改 `include/corona/script/api/corona_engine_api.h`
  - [ ] 移除静态 `registry_` 成员
  - [ ] 为 `Actor` 和 `Scene` 类添加 `IScriptServiceProvider*` 成员
  - [ ] 修改构造函数签名，接受 service provider
- [ ] 修改 `src/script/src/corona_engine_api.cpp`
  - [ ] 更新所有方法，使用 `provider_->get_entity_registry()` 替代静态 registry
  - [ ] 通过 provider 发布事件
  - [ ] 通过 provider 访问资源管理器

#### 3.4 更新 Python 绑定
- [ ] 修改 `src/script/src/engine_bindings.cpp`
  - [ ] 使用闭包捕获 `IScriptServiceProvider*`
  - [ ] 修改类绑定，传递 provider
  - [ ] 添加事件发布 API 绑定
  - [ ] 添加组件访问 API 绑定

**验收标准**:
- CoronaEngineAPI 不再依赖全局状态
- Python 脚本可以通过 API 创建实体和场景
- Python 脚本可以发布事件
- 所有操作使用引擎的 ECS registry

---

### 📡 阶段 4：集成事件系统

**目标**: 使用事件总线替代直接调用和 `PythonBridge`

#### 4.1 定义脚本事件
- [ ] 创建 `include/corona/events/script_events.h`
  - [ ] `ScriptSystemInitializedEvent`
  - [ ] `ScriptReloadRequestedEvent`
  - [ ] `ScriptErrorEvent`
  - [ ] `ScriptModuleLoadedEvent`
  - [ ] `ScriptModuleUnloadedEvent`
  - [ ] `ScriptMessageEvent`（替代 PythonBridge）

#### 4.2 在 ScriptSystem 中处理事件
- [ ] 订阅 `ScriptReloadRequestedEvent`
  - [ ] 触发运行时重载
  - [ ] 发布重载结果事件
- [ ] 订阅场景和实体事件
  - [ ] `SceneLoadedEvent` -> 加载场景脚本
  - [ ] `EntityCreatedEvent` -> 附加实体脚本
- [ ] 发布脚本生命周期事件
  - [ ] 初始化完成
  - [ ] 模块加载/卸载
  - [ ] 错误事件

#### 4.3 替换 PythonBridge
- [ ] 移除 `include/corona/script/python/python_bridge.h`
- [ ] 移除 `src/script/src/python_bridge.cpp`
- [ ] 在 Python 绑定中添加事件发布接口
  ```python
  # Python 侧
  engine.publish_event("CustomEvent", {"key": "value"})
  ```
- [ ] 在 C++ 侧监听脚本消息事件

#### 4.4 添加脚本热键支持
- [ ] 监听键盘事件（如 `F5` 重载脚本）
- [ ] 发布 `ScriptReloadRequestedEvent`

**验收标准**:
- 脚本系统完全通过事件通信
- 可以从编辑器 UI 触发脚本重载
- Python 脚本可以发布和监听引擎事件
- PythonBridge 已完全移除

---

### ⚙️ 阶段 5：配置管理系统

**目标**: 移除硬编码路径，使用配置文件

#### 5.1 创建配置文件
- [ ] 创建 `config/script_config.json`
  - [ ] Python home 路径（支持环境变量）
  - [ ] 模块搜索路径列表
  - [ ] 入口模块配置
  - [ ] 热重载配置
  - [ ] 日志级别配置
- [ ] 创建 `config/script_config.schema.json`（可选）
  - [ ] JSON Schema 验证

#### 5.2 实现配置加载器
- [ ] 创建 `src/systems/src/scriptsystem/script_config_loader.h/cpp`
  - [ ] 从 JSON 文件加载配置
  - [ ] 解析环境变量（`${ENGINE_ROOT}`, `${RUNTIME_DIR}` 等）
  - [ ] 验证路径存在性
  - [ ] 提供默认配置回退

#### 5.3 移除 PathCfg 硬编码
- [ ] 从 `python_api.cpp` 中删除 `PathCfg` 命名空间
- [ ] 使用配置系统替代所有硬编码路径
- [ ] 移除正则表达式路径解析

#### 5.4 环境变量支持
- [ ] 支持 `CORONA_ENGINE_ROOT` 环境变量
- [ ] 支持 `CORONA_SCRIPT_PATH` 环境变量
- [ ] 在配置加载器中解析变量

**验收标准**:
- 所有路径从配置文件读取
- 不同环境可使用不同配置（开发/发布）
- 无硬编码路径或魔法字符串
- 配置文件语法错误有明确提示

---

### 🧹 阶段 6：清理和优化

**目标**: 移除旧代码，优化性能，完善文档

#### 6.1 移除旧实现
- [ ] 删除 `include/corona/script/python/python_api.h`
- [ ] 删除 `src/script/src/python_api.cpp`
- [ ] 删除 `include/corona/script/python/python_bridge.h`
- [ ] 删除 `src/script/src/python_bridge.cpp`
- [ ] 从 `src/engine.cpp` 移除 `PythonAPI` 引用
- [ ] 移除 `CORONA_ENABLE_PYTHON_API` 条件编译（改为运行时配置）

#### 6.2 CMake 构建更新
- [ ] 更新 `src/script/src/CMakeLists.txt`
  - [ ] 添加新的源文件
  - [ ] 移除旧的源文件
  - [ ] 调整头文件包含路径
- [ ] 更新 `src/systems/CMakeLists.txt`
  - [ ] 添加 ScriptSystem 相关文件
- [ ] 确保条件编译选项正确

#### 6.3 性能优化
- [ ] 优化 GIL 锁粒度
  - [ ] 分析哪些操作必须持有 GIL
  - [ ] 在 I/O 操作时释放 GIL
- [ ] 优化热重载性能
  - [ ] 使用文件监控 API（如 Windows `ReadDirectoryChangesW`）
  - [ ] 减少不必要的文件扫描
  - [ ] 优化依赖图计算
- [ ] 模块缓存优化
  - [ ] 缓存已编译的 .pyc 文件
  - [ ] 避免重复加载同一模块

#### 6.4 测试
- [ ] 编写单元测试
  - [ ] `PythonEnvironment` 初始化测试
  - [ ] `PythonModuleManager` 加载测试
  - [ ] `PythonHotReloader` 变更检测测试
  - [ ] `ScriptServiceProvider` 接口测试
- [ ] 编写集成测试
  - [ ] 完整脚本执行流程测试
  - [ ] 热重载功能测试
  - [ ] 事件通信测试
- [ ] 性能测试
  - [ ] 脚本执行开销
  - [ ] 热重载延迟
  - [ ] 内存泄漏检查

**验收标准**:
- 旧代码完全移除
- 构建系统正常工作
- 所有测试通过
- 无性能回退

---

### 📚 阶段 7：文档和示例

**目标**: 完善文档，提供使用示例

#### 7.1 更新架构文档
- [ ] 更新 `docs/architecture/ARCHITECTURE_cn.md`
  - [ ] 添加 ScriptSystem 章节
  - [ ] 更新系统交互图
  - [ ] 说明脚本事件流
- [ ] 更新 `docs/architecture/ARCHITECTURE_en.md`（英文版）

#### 7.2 编写脚本系统文档
- [ ] 更新 `docs/scripting/SCRIPT_SYSTEM_cn.md`
  - [ ] 系统概述
  - [ ] 配置说明
  - [ ] API 参考
  - [ ] 热重载使用指南
  - [ ] 最佳实践
  - [ ] 故障排查

#### 7.3 创建示例
- [ ] 创建 `examples/script/basic_usage/`
  - [ ] 基础脚本示例
  - [ ] 实体创建和操作
  - [ ] 场景管理
- [ ] 创建 `examples/script/hot_reload/`
  - [ ] 热重载演示
  - [ ] 模块依赖示例
- [ ] 创建 `examples/script/events/`
  - [ ] 事件监听和发布
  - [ ] 自定义事件示例
- [ ] 创建 `examples/script/advanced/`
  - [ ] 多线程脚本
  - [ ] 异步操作
  - [ ] 性能优化技巧

#### 7.4 更新开发者指南
- [ ] 更新 `docs/development/DEVELOPER_GUIDE_cn.md`
  - [ ] 添加脚本系统开发指南
  - [ ] 如何扩展脚本 API
  - [ ] 如何添加新的脚本语言支持

**验收标准**:
- 文档完整且准确
- 示例代码可运行
- 新开发者能够根据文档使用脚本系统

---

## 🔄 可选扩展（Future Work）

### 扩展 1：其他脚本语言支持
- [ ] 设计通用的脚本绑定生成器
- [ ] 添加 Lua 运行时实现
- [ ] 添加 JavaScript (V8) 运行时实现
- [ ] 支持多运行时共存

### 扩展 2：脚本调试支持
- [ ] 集成 Python 调试器（pdb）
- [ ] 提供远程调试接口
- [ ] 在编辑器中显示断点和调用栈

### 扩展 3：脚本性能分析
- [ ] 集成 Python profiler
- [ ] 提供脚本性能监控面板
- [ ] 热点函数分析

### 扩展 4：脚本安全沙箱
- [ ] 限制脚本访问权限
- [ ] 禁止危险操作（如文件系统访问）
- [ ] 资源使用限制（CPU/内存）

---

## 📊 进度跟踪

| 阶段 | 进度 | 预计时间 | 状态 |
|------|------|----------|------|
| 阶段 0: 准备工作 | 75% | 1 天 | 🟡 进行中 |
| 阶段 1: 抽象层 | 0% | 2 天 | ⚪ 未开始 |
| 阶段 2: Python 运行时 | 0% | 3-4 天 | ⚪ 未开始 |
| 阶段 3: API 暴露层 | 0% | 2-3 天 | ⚪ 未开始 |
| 阶段 4: 事件系统 | 0% | 2 天 | ⚪ 未开始 |
| 阶段 5: 配置管理 | 0% | 1-2 天 | ⚪ 未开始 |
| 阶段 6: 清理优化 | 0% | 2-3 天 | ⚪ 未开始 |
| 阶段 7: 文档示例 | 0% | 2 天 | ⚪ 未开始 |

**总预计时间**: 15-20 天

---

## 🎯 关键里程碑

1. **Milestone 1**: ScriptSystem 框架搭建完成（阶段 1）
2. **Milestone 2**: Python 功能迁移完成（阶段 2）
3. **Milestone 3**: API 解耦完成（阶段 3）
4. **Milestone 4**: 事件驱动通信完成（阶段 4）
5. **Milestone 5**: 配置系统完成（阶段 5）
6. **Milestone 6**: 重构完成，旧代码清理（阶段 6）
7. **Milestone 7**: 文档和示例完善（阶段 7）

---

## 📝 注意事项

### 风险和挑战
1. **兼容性**: 确保重构不影响现有 Python 脚本
2. **性能**: 确保新架构不引入性能问题
3. **线程安全**: 特别注意 Python GIL 和引擎多线程的交互
4. **内存管理**: 注意 Python 对象生命周期管理

### 测试策略
- 每个阶段完成后进行功能验证
- 保持现有测试用例通过
- 添加新的测试覆盖新功能
- 在真实场景中测试热重载

### 代码审查检查点
- [ ] 阶段 1 完成后审查接口设计
- [ ] 阶段 2 完成后审查运行时实现
- [ ] 阶段 3 完成后审查 API 设计
- [ ] 阶段 6 完成后最终审查

---

## 📞 联系和讨论

如有问题或建议，请在以下位置讨论：
- GitHub Issues
- 团队内部讨论频道
- 代码审查评论

---

**最后更新**: 2025年11月5日
