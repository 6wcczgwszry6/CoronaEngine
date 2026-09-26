# 02：嵌入场景的 PT／SVGF 模式切换

状态：已复现，待修复。关联[总览](README.md)、[原始验收证据](../kitchen-aabb-acceptance.md)。

## 问题与原因

`SceneTools.set_vision_render_mode('scene.ini','view1','svgf')` 返回成功，但渲染线程尝试打开 `scene.ini.embedded`，报文件不存在；切回已存在的 PT runtime 后恢复。

当前 embedded JSON 与基目录保存在已有 runtime 中，新模式经 `ensure_external_vision_runtime()` 创建时走文件导入。场景身份 key 被误当成可加载的文件路径。模式字段更新成功并不代表新 pipeline 初始化成功。

## 解决方案

把来源描述提升到 `VisionSceneResource`，生命周期独立于某个渲染模式。拟定 `VisionSceneSourceDesc`：

| 字段 | 含义 |
|---|---|
| kind | 显式 File 或 Embedded，不根据后缀猜测 |
| file_path / scene_json | 文件来源路径或嵌入文档内容，按 kind 使用 |
| base_dir | 接收来源时确定的绝对资源基目录 |
| source_revision | 成功发布来源时递增，用于识别重载与内容变化 |

资源 key 继续用于身份查找，不承载来源类型。新增 runtime 按描述选择已有的 `import_vision_scene_from_data()` 或 `import_vision_scene_from_file()`。每个模式保留自己的 framebuffer、积分器及降噪历史。

## 生命周期和失败处理

1. 初次加载：校验来源、JSON 和基目录；形成完整描述，再初始化 runtime。
2. 切换模式：复用共享来源，按目标模式配置并创建 pipeline；必须确认实际初始化成功。
3. runtime 淘汰：释放其渲染资源，不删除仍被场景持有的来源描述。
4. 重载：校验新描述，递增来源版本并使旧 runtime 失效；重置加载缓存不能误清掉刚发布的来源。
5. 导入失败：保留明确错误，不能将新 runtime 标记为已加载；也不能让旧内容伪装成新来源版本。是否继续显示旧帧应明确标记为旧状态。

`reset_pipeline()` 当前会清空 runtime 的 `scene_json/base_dir`；修改时应确保依赖 embedded 标记的形状隐藏／增删逻辑仍能取得正确来源，优先读取共享描述，避免两处状态独立漂移。

## 修改位置

- `include/corona/systems/optics/vision_scene_resource.h`：来源描述、版本及重载语义。
- `src/systems/optics/optics_system.cpp`：接收 embedded 来源、选择导入器、runtime 重置／淘汰。
- `src/systems/optics/tests/test_vision_scene_resource.cpp`：来源生命周期。
- `src/systems/optics/tests/test_vision_render_mode_config.cpp`、`test_vision_geometry_gpu_resource.cpp`：模式与实际 pipeline 初始化。

## 实施与验收

- [ ] 构造只存在于内存的场景，不创建 `.embedded` 文件；旧实现创建第二模式失败，新实现 PT/SVGF 均可初始化。
- [ ] 验证相对贴图／模型路径使用来源 base_dir，改变进程工作目录不会改变解析结果。
- [ ] 覆盖 PT→SVGF→PT、隐藏后切换再显示、同 key 新 JSON 重载、runtime 淘汰重建、空／非法 JSON、缺失资源。
- [ ] 在 kitchen 中记录新模式 pipeline、实际产帧和渲染日志，不能只断言 API success 或 mode 字段。
- [ ] 不存在对 `.embedded` 逻辑 key 的文件读取尝试；模式初始化失败不重复假报成功。

本方案不引入虚假的 `.embedded` 磁盘文件，不重新启用逐帧路径解析。实现与测试独立提交，完成后再验证两个不同模式 runtime 的几何传播。
