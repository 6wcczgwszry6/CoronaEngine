# CoronaEngine

CoronaEngine 是一个模块化、多线程、数据驱动的 C++ 游戏引擎，构建在 CoronaFramework 的 `KernelContext` 之上，采用系统化架构组织渲染、几何、运动学、力学、声学、脚本和 UI 等能力。

## 文档入口

- 完整分类索引：`docs/README.md`
- 一页式总览：`docs/overview/ONE_PAGE_OVERVIEW_cn.md`
- 5 分钟上手：`docs/overview/QUICK_START_cn.md`
- 架构图速览：`docs/architecture/ARCHITECTURE_MAP_cn.md`
- 开发者指南：`docs/development/DEVELOPER_GUIDE_cn.md`
- 编辑器合并清单：`docs/editor/CABBAGE_EDITOR_MERGE_CHECKLIST_cn.md`

## 当前状态

- 核心入口位于 `src/engine.cpp` 和 `include/corona/engine.h`
- 当前已注册系统包括 `display`、`optics`、`geometry`、`kinematics`、`mechanics`、`acoustics`、`script`、`ui`
- 项目使用 `CMakePresets.json` 管理跨平台构建配置

## 快速构建

Windows + MSVC + Ninja：

```powershell
cmake --preset ninja-msvc
cmake --build --preset msvc-debug
```

第一次进入仓库，建议先看 `docs/README.md`、`docs/overview/ONE_PAGE_OVERVIEW_cn.md` 和 `docs/overview/QUICK_START_cn.md`。