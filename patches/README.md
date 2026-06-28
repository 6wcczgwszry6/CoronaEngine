=== Bug 审计补丁索引 ===
基准: c4a07b32 → HEAD
日期: 2026-06-26

应用顺序:
  1. F1_lock_order_violation.patch     (修改 geometry_system.cpp)
  2. F2_config_overwrite.patch         (修改 geometry_system.h + geometry_system.cpp + corona_engine_api.cpp)
  3. F3_put_rollback_data_loss.patch   (修改 lru_cache.cpp)
  4. S2_bvh_bounds_check.patch         (修改 geometry_system.cpp)
  5. S3_S4_unload_state_machine.patch  (修改 geometry_system.cpp)
  6. S5_disk_put_pin_bypass.patch      (修改 lru_cache.cpp)
  7. G1_G9_general_fixes.patch         (修改 geometry_system.h + geometry_system.cpp + lru_cache.cpp)

注意:
  - S1 已合并入 F1，不需单独应用
  - F1 和 G1_G9 都修改 geometry_system.cpp，如冲突需手动处理
  - 建议按顺序逐个应用，每应用一个检查编译

涉及文件:
  include/corona/systems/geometry/geometry_system.h
  src/systems/geometry/geometry_system.cpp
  src/systems/script/python/corona_engine_api.cpp
  modules/corona_resource/src/resource/cache/lru_cache.cpp
