# 脚本系统说明

本文档用于承接脚本系统的长期说明。当前详细重构计划仍以 `SCRIPT_REFACTORING_TODO_cn.md` 为准。

## 范围

- `ScriptSystem` 的职责边界。
- Python 运行时初始化与热重载流程。
- C++/Python API 映射关系。
- 编辑器生成脚本与运行时脚本目录的关系。

## 当前入口

- `src/systems/script/script_system.cpp`
- `src/systems/script/python/python_path_config.cpp`
- `src/systems/script/python/corona_engine_api.cpp`
- `include/corona/systems/script/corona_engine_api.h`

## 相关文档

- `PYTHON_API_EXAMPLES.md`
- `PYTHON_API_STORAGE_MAPPING_cn.md`
- `SCRIPT_REFACTORING_TODO_cn.md`