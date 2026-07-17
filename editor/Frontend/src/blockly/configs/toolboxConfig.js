// JSON 格式工具箱配置 —— 自定义 CoronaEngine 积木 + 标准 Blockly 积木
export const TOOLBOX_CONFIG = {
  kind: 'categoryToolbox',
  scrollbars: true,
  contents: [
    // ===================================================================
    // 1. 引擎 —— CoronaEngine 自定义运动/旋转/坐标积木
    // ===================================================================
    {
      kind: 'category',
      name: '\u4e8b\u4ef6',
      categorystyle: 'event_category',
      contents: [
        { kind: 'block', type: 'event_gameStart' },
        { kind: 'block', type: 'event_keyboard' },
        { kind: 'block', type: 'event_keyboard_combo' },
        { kind: 'block', type: 'event_mouse_click' },
        { kind: 'block', type: 'event_mouse_move' },
        { kind: 'block', type: 'event_mouse_wheel' },
        { kind: 'block', type: 'event_mouse_contextmenu' },
        { kind: 'block', type: 'event_RB' },
        { kind: 'block', type: 'event_broadcast' },
        { kind: 'block', type: 'event_broadcastWait' },
        { kind: 'block', type: 'node_when_enter', nodeGraphOnly: true },
        { kind: 'block', type: 'node_while_active', nodeGraphOnly: true },
        { kind: 'block', type: 'node_when_exit', nodeGraphOnly: true },
      ],
    },

    // ===================================================================
    // 2. Motion
    // ===================================================================
    {
      kind: 'category',
      name: '\u8fd0\u52a8',
      categorystyle: 'motion_category',
      contents: [
        { kind: 'block', type: 'engine_move' },
        { kind: 'block', type: 'engine_rotateX' },
        { kind: 'block', type: 'engine_rotateY' },
        { kind: 'block', type: 'engine_rotateZ' },
        { kind: 'block', type: 'engine_face' },
        { kind: 'block', type: 'engine_moveto' },
        { kind: 'block', type: 'engine_movetoXYZ' },
        { kind: 'block', type: 'engine_movetoXYZtime' },
        { kind: 'block', type: 'engine_Xset' },
        { kind: 'block', type: 'engine_Yset' },
        { kind: 'block', type: 'engine_Zset' },
        { kind: 'block', type: 'engine_Xadd' },
        { kind: 'block', type: 'engine_Yadd' },
        { kind: 'block', type: 'engine_Zadd' },
        { kind: 'block', type: 'engine_X' },
        { kind: 'block', type: 'engine_Y' },
        { kind: 'block', type: 'engine_Z' },
        { kind: 'block', type: 'engine_rotationX' },
        { kind: 'block', type: 'engine_rotationY' },
        { kind: 'block', type: 'engine_rotationZ' },
        { kind: 'block', type: 'object_set_position' },
        { kind: 'block', type: 'object_get_x' },
        { kind: 'block', type: 'object_get_y' },
        { kind: 'block', type: 'object_get_z' },
        { kind: 'block', type: 'object_move_tag' },
        { kind: 'block', type: 'object_clamp_axis' },
      ],
    },

    // ===================================================================
    // 3. Physics
    // ===================================================================
    {
      kind: 'category',
      name: '\u7269\u7406',
      categorystyle: 'physics_category',
      contents: [
        { kind: 'block', type: 'engine_set_velocity' },
        { kind: 'block', type: 'engine_set_velocity_axis' },
        { kind: 'block', type: 'engine_get_velocity' },
        { kind: 'block', type: 'engine_apply_impulse' },
        { kind: 'block', type: 'engine_stop_motion' },
        { kind: 'block', type: 'engine_set_gravity' },
        { kind: 'block', type: 'engine_jump' },
        { kind: 'block', type: 'engine_bounce_axis' },
        { kind: 'block', type: 'engine_bounce_last_collision' },
        { kind: 'block', type: 'object_set_native_physics' },
        { kind: 'block', type: 'object_set_logical_collision' },
        { kind: 'block', type: 'object_logical_collision_enabled' },
      ],
    },

    // ===================================================================
    // 2. 摄像机 —— FPS 视角控制积木（新增）
    // ===================================================================
    {
      kind: 'category',
      name: '\u6444\u50cf\u673a',
      categorystyle: 'camera_category',
      contents: [
        { kind: 'block', type: 'camera_lock_mouse' },
        { kind: 'block', type: 'camera_unlock_mouse' },
        { kind: 'block', type: 'camera_mouse_dx' },
        { kind: 'block', type: 'camera_mouse_dy' },
        { kind: 'block', type: 'camera_set_fov' },
        { kind: 'block', type: 'camera_follow_object' },
        { kind: 'block', type: 'camera_third_person_orbit' },
        { kind: 'block', type: 'camera_first_person_follow' },
        { kind: 'block', type: 'camera_raycast' },
        { kind: 'block', type: 'camera_raycast_object' },
      ],
    },

    // ===================================================================
    // 3. 外观 —— CoronaEngine 自定义动画/尺寸/显隐积木
    // ===================================================================
    {
      kind: 'category',
      name: '\u5916\u89c2',
      categorystyle: 'appearance_category',
      contents: [
        { kind: 'block', type: 'appearance_cartoonSet' },
        { kind: 'block', type: 'appearance_nextCartoon' },
        { kind: 'block', type: 'appearance_playCartoon' },
        { kind: 'block', type: 'appearance_stopCartoon' },
        { kind: 'block', type: 'appearance_resetCartoon' },
        { kind: 'block', type: 'appearance_sizeAdd' },
        { kind: 'block', type: 'appearance_sizeSet' },
        { kind: 'block', type: 'appearance_show' },
        { kind: 'block', type: 'appearance_hide' },
        { kind: 'block', type: 'appearance_cartoon' },
        { kind: 'block', type: 'appearance_size' },
        { kind: 'block', type: 'appearance_set_color' },
        { kind: 'block', type: 'appearance_set_alpha' },
      ],
    },

    // ===================================================================
    // 3. 事件 —— CoronaEngine 自定义事件积木

    // ===================================================================
    // Objects - common 3D demo object management blocks
    // ===================================================================
    {
      kind: 'category',
      name: '\u5bf9\u8c61',
      categorystyle: 'object_category',
      contents: [
        { kind: 'block', type: 'object_reference' },
        { kind: 'block', type: 'object_hide' },
        { kind: 'block', type: 'object_show' },
        { kind: 'block', type: 'object_delete' },
        { kind: 'block', type: 'object_delete_last_touched' },
        { kind: 'block', type: 'object_exists' },
        { kind: 'block', type: 'object_set_tag' },
        { kind: 'block', type: 'object_tag_numbered_range' },
        { kind: 'block', type: 'object_count_tag' },
        { kind: 'block', type: 'object_spawn' },
        { kind: 'block', type: 'object_spawn_tag' },
        { kind: 'block', type: 'object_delete_raycast_hit' },
        { kind: 'block', type: 'object_save_checkpoint' },
        { kind: 'block', type: 'object_restore_checkpoint' },
        { kind: 'block', type: 'object_reset_crossed_once' },
      ],
    },

    // ===================================================================
    // 5. 侦测 —— CoronaEngine 自定义感知积木
    // ===================================================================
    {
      kind: 'category',
      name: '\u4fa6\u6d4b',
      categorystyle: 'detect_category',
      contents: [
        { kind: 'block', type: 'detect_touch' },
        { kind: 'block', type: 'detect_not_touch' },
        { kind: 'block', type: 'detect_touch_any' },
        { kind: 'block', type: 'detect_not_touch_any' },
        { kind: 'block', type: 'detect_touch_tag' },
        { kind: 'block', type: 'detect_not_touch_tag' },
        { kind: 'block', type: 'detect_touch_started' },
        { kind: 'block', type: 'detect_touch_tag_started' },
        { kind: 'block', type: 'detect_last_touch_object' },
        { kind: 'block', type: 'detect_object_exists' },
        { kind: 'block', type: 'detect_object_not_exists' },
        { kind: 'block', type: 'detect_distance' },
        { kind: 'block', type: 'detect_ground_below' },
        { kind: 'block', type: 'detect_no_ground_below' },
        { kind: 'block', type: 'detect_passed_x' },
        { kind: 'block', type: 'detect_passed_z' },
        { kind: 'block', type: 'detect_crossed_x_once' },
        { kind: 'block', type: 'detect_crossed_z_once' },
        { kind: 'block', type: 'detect_outside_axis' },
        { kind: 'block', type: 'detect_inside_axis' },
        { kind: 'block', type: 'detect_inside_box' },
        { kind: 'block', type: 'detect_position_near' },
        { kind: 'block', type: 'detect_keyboard1' },
        { kind: 'block', type: 'detect_keyboard0' },
        { kind: 'block', type: 'detect_mouse1' },
        { kind: 'block', type: 'detect_mouse0' },
        { kind: 'block', type: 'detect_mouse_left_half' },
        { kind: 'block', type: 'detect_mouse_right_half' },
        { kind: 'block', type: 'detect_mouse_x_ratio' },
        { kind: 'block', type: 'detect_ask_answer' },
        { kind: 'block', type: 'detect_attribute' },
        { kind: 'block', type: 'detect_raycast' },
        { kind: 'block', type: 'detect_raycast_distance' },
        { kind: 'block', type: 'detect_raycast_object' },
        { kind: 'block', type: 'detect_raycast_point' },
        { kind: 'block', type: 'detect_raycast_hit_tag' },
        { kind: 'block', type: 'detect_last_collision_axis' },
        { kind: 'block', type: 'detect_last_collision_normal_x' },
        { kind: 'block', type: 'detect_last_collision_normal_y' },
        { kind: 'block', type: 'detect_last_collision_normal_z' },
        { kind: 'block', type: 'detect_mouse_pick_object' },
        { kind: 'block', type: 'detect_mouse_pick_hit_tag' },
      ],
    },

    // ===================================================================
    // 7. 运算 —— 自定义运算 + 标准数学
    // ===================================================================
    {
      kind: 'category',
      name: '\u63a7\u5236',
      categorystyle: 'control_category',
      contents: [
        { kind: 'block', type: 'control_run_project_script' },
        { kind: 'block', type: 'control_wait' },
        { kind: 'block', type: 'control_wait2' },
        { kind: 'block', type: 'control_for' },
        { kind: 'block', type: 'control_forX' },
        { kind: 'block', type: 'control_until' },
        { kind: 'block', type: 'control_if' },
        { kind: 'block', type: 'control_else' },
        { kind: 'block', type: 'control_stop' },
        { kind: 'block', type: 'control_cloneStart' },
        { kind: 'block', type: 'control_clone' },
        { kind: 'block', type: 'control_cloneDEL' },
        { kind: 'block', type: 'control_senceSet' },
        { kind: 'block', type: 'control_nextSence' },
        { kind: 'block', type: 'control_restart_level' },
        { kind: 'block', type: 'control_cooldown_ready' },
        { kind: 'block', type: 'control_start_cooldown' },
        { kind: 'block', type: 'control_reset_cooldown' },
      ],
    },

    // ===================================================================
    // 9. UI
    // ===================================================================
    {
      kind: 'category',
      name: '\u754c\u9762',
      categorystyle: 'ui_category',
      contents: [
        { kind: 'block', type: 'ui_set_score' },
        { kind: 'block', type: 'ui_add_score' },
        { kind: 'block', type: 'ui_score' },
        { kind: 'block', type: 'ui_set_lives' },
        { kind: 'block', type: 'ui_add_lives' },
        { kind: 'block', type: 'ui_lives' },
        { kind: 'block', type: 'ui_set_countdown' },
        { kind: 'block', type: 'ui_countdown_left' },
        { kind: 'block', type: 'ui_countdown_elapsed' },
        { kind: 'block', type: 'ui_countdown_finished' },
        { kind: 'block', type: 'ui_game_state' },
        { kind: 'block', type: 'ui_game_win' },
        { kind: 'block', type: 'ui_game_over' },
      ],
    },

    // ===================================================================
    // 10. Sound
    // ===================================================================
    {
      kind: 'category',
      name: '\u97f3\u6548',
      categorystyle: 'audio_category',
      contents: [
        { kind: 'block', type: 'audio_play' },
        { kind: 'block', type: 'audio_loop' },
        { kind: 'block', type: 'audio_stop' },
        { kind: 'block', type: 'audio_stop_all' },
      ],
    },

    // ===================================================================
    // 7. 变量 —— 自定义变量 + 标准变量
    // ===================================================================
    {
      kind: 'category',
      name: '\u53d8\u91cf',
      categorystyle: 'variable_category',
      contents: [
        { kind: 'block', type: 'variable_define' },
        { kind: 'block', type: 'variable_get' },
        { kind: 'block', type: 'variable_exists' },
        { kind: 'block', type: 'variable_set' },
        { kind: 'block', type: 'variable_add' },
        { kind: 'block', type: 'variable_show' },
        { kind: 'block', type: 'variable_hide' },
      ],
    },

    // ===================================================================
    // 8. 列表 —— 自定义列表 + 标准列表
    // ===================================================================
    {
      kind: 'category',
      name: '\u5217\u8868',
      categorystyle: 'list_category',
      contents: [
        { kind: 'block', type: 'list_define' },
        { kind: 'block', type: 'list_add_named' },
        { kind: 'block', type: 'list_insert_named' },
        { kind: 'block', type: 'list_remove_index_named' },
        { kind: 'block', type: 'list_remove_value_named' },
        { kind: 'block', type: 'list_clear_named' },
        { kind: 'block', type: 'list_item_named' },
        { kind: 'block', type: 'list_length_named' },
        { kind: 'block', type: 'list_contains_named' },
        { kind: 'block', type: 'list_show' },
        { kind: 'block', type: 'list_hide' },
        { kind: 'block', type: 'lists_create_empty' },
        { kind: 'block', type: 'lists_create_with' },
        { kind: 'block', type: 'lists_repeat' },
        { kind: 'block', type: 'lists_length' },
        { kind: 'block', type: 'lists_isEmpty' },
        { kind: 'block', type: 'lists_indexOf' },
        { kind: 'block', type: 'lists_getIndex' },
        { kind: 'block', type: 'lists_setIndex' },
        { kind: 'block', type: 'lists_getSublist' },
        { kind: 'block', type: 'lists_reverse' },
        { kind: 'block', type: 'lists_sort' },
        { kind: 'block', type: 'lists_split' },
      ],
    },

    // ===================================================================
    // 13. Operators
    // ===================================================================
    {
      kind: 'category',
      name: '\u8fd0\u7b97',
      categorystyle: 'math_category',
      contents: [
        { kind: 'block', type: 'logic_boolean' },
        { kind: 'block', type: 'logic_compare' },
        { kind: 'block', type: 'logic_operation' },
        { kind: 'block', type: 'logic_negate' },
        { kind: 'block', type: 'logic_null' },
        { kind: 'block', type: 'logic_ternary' },
        { kind: 'block', type: 'math_number' },
        { kind: 'block', type: 'math_arithmetic' },
        { kind: 'block', type: 'math_single' },
        { kind: 'block', type: 'math_trig' },
        { kind: 'block', type: 'math_constant' },
        { kind: 'block', type: 'math_number_property' },
        { kind: 'block', type: 'math_round' },
        { kind: 'block', type: 'math_on_list' },
        { kind: 'block', type: 'math_modulo' },
        { kind: 'block', type: 'math_constrain' },
        { kind: 'block', type: 'math_random_int' },
        { kind: 'block', type: 'math_random_float' },
        { kind: 'block', type: 'math_atan2' },
      ],
    },

    // ===================================================================
    // 14. Text
    // ===================================================================
    {
      kind: 'category',
      name: '\u6587\u672c',
      categorystyle: 'text_category',
      contents: [
        { kind: 'block', type: 'text' },
        { kind: 'block', type: 'text_join' },
        { kind: 'block', type: 'text_append' },
        { kind: 'block', type: 'text_length' },
        { kind: 'block', type: 'text_isEmpty' },
        { kind: 'block', type: 'text_indexOf' },
        { kind: 'block', type: 'text_charAt' },
        { kind: 'block', type: 'text_getSubstring' },
        { kind: 'block', type: 'text_changeCase' },
        { kind: 'block', type: 'text_trim' },
        { kind: 'block', type: 'text_count' },
        { kind: 'block', type: 'text_replace' },
        { kind: 'block', type: 'text_reverse' },
        { kind: 'block', type: 'text_print' },
        { kind: 'block', type: 'text_prompt_ext' },
      ],
    },

    // ===================================================================
    // 15. Functions
    // ===================================================================
    {
      kind: 'category',
      name: '\u51fd\u6570',
      categorystyle: 'function_category',
      contents: [
        { kind: 'block', type: 'procedures_defnoreturn' },
        { kind: 'block', type: 'procedures_defreturn' },
        { kind: 'block', type: 'procedures_callnoreturn' },
        { kind: 'block', type: 'procedures_callreturn' },
        { kind: 'block', type: 'procedures_ifreturn' },
      ],
    },

    // ===================================================================
    // 16. Gameplay Templates
    // ===================================================================
    {
      kind: 'category',
      name: '\u73a9\u6cd5\u6a21\u677f',
      categorystyle: 'gameplay_category',
      contents: [
        { kind: 'block', type: 'engine_set_game_speed' },
        { kind: 'block', type: 'engine_get_game_speed' },
        { kind: 'block', type: 'object_move_to_lane' },
        { kind: 'block', type: 'object_move_to_lane_smooth' },
        { kind: 'block', type: 'object_lane_index' },
        { kind: 'block', type: 'object_set_random_position' },
        { kind: 'block', type: 'object_spawn_random_box' },
        { kind: 'block', type: 'object_scatter_tag' },
        { kind: 'block', type: 'object_recycle_tag_axis' },
        { kind: 'block', type: 'object_reset_tag' },
        { kind: 'block', type: 'object_count_active_tag' },
        { kind: 'block', type: 'object_set_tag_velocity_axis' },
        { kind: 'block', type: 'object_randomize_mouse_pick' },
        { kind: 'block', type: 'object_delete_mouse_pick' },
        { kind: 'block', type: 'object_third_person_move' },
        { kind: 'block', type: 'object_arcade_jump' },
        { kind: 'block', type: 'object_collect_touching_tag' },
        { kind: 'block', type: 'object_breakout_reset_round' },
        { kind: 'block', type: 'object_breakout_paddle_control' },
        { kind: 'block', type: 'object_breakout_step' },
        { kind: 'block', type: 'object_first_person_move' },
        { kind: 'block', type: 'combat_set_tag_health' },
        { kind: 'block', type: 'combat_melee_attack' },
        { kind: 'block', type: 'combat_enemy_chase_tag' },
        { kind: 'block', type: 'combat_enemy_contact_damage' },
        { kind: 'block', type: 'combat_alive_count' },
      ],
    },

  ],
};

const CATEGORY_KEYS = {
  '\u4e8b\u4ef6': 'blocklyToolbox.event',
  '\u8fd0\u52a8': 'blocklyToolbox.motion',
  '\u7269\u7406': 'blocklyToolbox.physics',
  '\u6444\u50cf\u673a': 'blocklyToolbox.camera',
  '\u5916\u89c2': 'blocklyToolbox.appearance',
  '\u5bf9\u8c61': 'blocklyToolbox.object',
  '\u4fa6\u6d4b': 'blocklyToolbox.detect',
  '\u63a7\u5236': 'blocklyToolbox.control',
  '\u754c\u9762': 'blocklyToolbox.ui',
  '\u97f3\u6548': 'blocklyToolbox.audio',
  '\u53d8\u91cf': 'blocklyToolbox.variable',
  '\u5217\u8868': 'blocklyToolbox.list',
  '\u8fd0\u7b97': 'blocklyToolbox.math',
  '\u6587\u672c': 'blocklyToolbox.text',
  '\u51fd\u6570': 'blocklyToolbox.functions',
  '\u73a9\u6cd5\u6a21\u677f': 'blocklyToolbox.gameplay',
};

export function createToolboxConfig(t = (key) => key) {
  const clone = structuredClone(TOOLBOX_CONFIG);
  for (const category of clone.contents || []) {
    if (category.kind === 'category') {
      category.contents = (category.contents || []).filter((item) => !item.nodeGraphOnly);
      if (CATEGORY_KEYS[category.name]) category.name = t(CATEGORY_KEYS[category.name]);
    }
  }
  return clone;
}
