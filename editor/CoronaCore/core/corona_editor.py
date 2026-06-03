import json
import math
import os
import sys

from CoronaCore.core.corona_engine import get_corona_engine
from CoronaCore.utils import settings
from CoronaCore.utils.response_utils import *

import logging

logger = logging.getLogger(__name__)

# 高频 UI 心跳类回调，日志降到 DEBUG，避免淹没业务日志
_NOISY_FUNCTIONS = frozenset({
    "update_drag_regions",
    "on_init",
    "get_menu_data",
})


class CoronaEditor:
    CoronaEngine = get_corona_engine()
    url = settings.core_path.frontend_dist
    tab_list = {}
    module_list = {}

    _selected_scene = None
    _selected_actor = None

    @classmethod
    def deal_func_from_js(cls, json_str):
        try:
            request = json.loads(json_str)
            module_name = request.get('module', None)
            func_name = request.get('function', None)
            args = request.get('args', [])
            log_level = logging.DEBUG if func_name in _NOISY_FUNCTIONS else logging.INFO
            logger.log(log_level, f"func_name: {func_name} module_name: {module_name} args: {args}")
            if not module_name or not func_name:
                return create_error_response(f"Please input module and function")

            if module_name not in cls.module_list or not hasattr(cls.module_list[module_name], func_name):
                return create_error_response(f"Not find module or function")

            module = cls.module_list.get(module_name, None)
            result = getattr(module, func_name)(*args)
            return create_success_response(result)
        except json.JSONDecodeError as e:
            return create_error_response(f"Invalid JSON: {str(e)}")
        except Exception as e:
            return create_error_response(f"Error processing request: {str(e)}")

    @classmethod
    def open_browser(cls, route_path="", docking_pos="", dock_width=100, dock_height=100, dock_fixed=False):
        if cls.CoronaEngine:
            try:
                logger.debug(f"open browser: {cls.tab_list}")
                path = route_path.split("?")[0]

                # 检查是否已存在相同路径的标签页
                if path in cls.tab_list:
                    tab_id = cls.tab_list[path]

                    # 尝试恢复最小化的标签页（如果存在）
                    if hasattr(cls.CoronaEngine, 'restore_browser_tab'):
                        cls.CoronaEngine.restore_browser_tab(tab_id)

                    # 调用 fragment changed
                    cls.js_call_func(path, "onFragmentChanged", [route_path])
                else:
                    # 创建新标签页
                    tab_id = cls.CoronaEngine.create_browser_tab(
                        cls.url, route_path, docking_pos, dock_width, dock_height, dock_fixed)
                    cls.tab_list[path] = tab_id
                    cls._inject_camera_panel()

                return f"Opened: {path}"
            except Exception as e:
                return f"Failed to open browser: {str(e)}"
        else:
            return f"CoronaEngine not available. Would open: {route_path}"

    @classmethod
    def close_browser_for_js(cls, module_name, if_close=False):
        """提供ui关闭tab的能力"""
        if module_name in cls.module_list:
            cls.module_list[module_name].is_open = False
            return cls.minimize_browser(cls.module_list[module_name].route_path, if_close)
        else:
            return f"Module not found: {module_name}"

    @classmethod
    def minimize_browser(cls, route_path, if_close=False):
        """最小化指定路径的浏览器标签页"""
        if cls.CoronaEngine:
            try:
                path = route_path.split("?")[0]
                if path in cls.tab_list:
                    tab_id = cls.tab_list[path]
                    if hasattr(cls.CoronaEngine, 'minimize_browser_tab'):
                        result = cls.CoronaEngine.minimize_browser_tab(tab_id, if_close)
                        if result:
                            return f"Minimized: {path}"
                        else:
                            return f"Failed to minimize: {path}"
                return f"Tab not found: {path}"
            except Exception as e:
                return f"Failed to minimize browser: {str(e)}"
        else:
            return f"CoronaEngine not available. Would minimize: {route_path}"

    @classmethod
    def js_call_func(cls, path, function_name, args):
        if cls.CoronaEngine:
            try:
                if path in cls.tab_list:
                    tab_id = cls.tab_list[path]
                else:
                    return f"tab_url not available. Would open: {path}"
                args_str = ', '.join(
                    json.dumps(arg, ensure_ascii=False)
                    for arg in args
                )
                js_code = f"""
                                if (window.{function_name}) {{
                                    window.{function_name}({args_str});
                                }}
                            """
                cls.CoronaEngine.execute_javascript(tab_id, js_code)
                result = f"Called js function '{function_name}' with args: {args_str}"
                return result
            except Exception as e:
                return f"Failed to open browser: {str(e)}"
        else:
            return f"CoronaEngine not available. Would call js: {function_name}"

    @classmethod
    def start_corona_engine(cls):
        for route_path in ("/ProjectLauncher", "/StartScreen", "/RecentGames"):
            cls.minimize_browser(route_path, True)
        cls.module_list["MainView"].open()
        for name, module in cls.module_list.items():
            if hasattr(module, "if_init") and module.if_init:
                module.open()

    @classmethod
    def register_page(cls, module_name: str, c_cls: object):
        """
        装饰器：注册配置函数
        module_name:模块名
        """
        # def decorator(c_cls):
        if module_name not in cls.module_list:
            cls.module_list[module_name] = c_cls
            # return c_cls
        # return decorator

    @classmethod
    def reload_frontend(cls):
        """强制刷新所有浏览器标签页（用于前端更新后无需重启）"""
        if cls.CoronaEngine:
            for path, tab_id in list(cls.tab_list.items()):
                try:
                    cls.CoronaEngine.execute_javascript(tab_id, "location.reload(true)")
                except Exception:
                    pass
            return "Frontend reloaded"
        return "CoronaEngine not available"

    @classmethod
    def camera_lock_set(cls, enabled, ox=0.0, oy=0.0, oz=2.0, rx=0.0, ry=0.0, rz=0.0):
        """JS面板调用：启用后摄像机跟随选中物体，保持相对位置不变。WASD键控制物体。"""
        if not enabled:
            cls._camera_follow_actor = None
            cls._camera_follow_scene = None
            cls._held_keys.clear()
            logger.info("Camera follow disabled")
            return {"ok": True}
        scene_name = cls._selected_scene
        actor_name = cls._selected_actor
        if not scene_name and not actor_name:
            return {"ok": False, "error": "请先在Object面板选中一个物体"}
        try:
            from CoronaCore.core.managers import scene_manager, actor_manager
            if scene_name:
                scene = scene_manager.get(scene_name)
                actor = scene.find_actor(actor_name) if scene else None
            else:
                scene = None
                actor = actor_manager.get(actor_name)
            if actor is None:
                return {"ok": False, "error": f"未找到物体: {actor_name}"}
            # 获取摄像机
            if scene:
                cam = scene.get_active_camera()
            else:
                cam = None
                for s_name in scene_manager.list_all():
                    s = scene_manager.get(s_name)
                    if s:
                        cam = s.get_active_camera()
                        if cam:
                            break
            if cam is None:
                return {"ok": False, "error": "未找到摄像机"}
            cam_pos = cam.get_position()
            obj_pos = actor.get_position()
            # 首次启用：记录世界偏移（摄像机 - 物体）
            world_offset = [
                cam_pos[0] - obj_pos[0],
                cam_pos[1] - obj_pos[1],
                cam_pos[2] - obj_pos[2],
            ]
            # 如果已在跟随同一物体，且用户通过"应用"传入了非默认值，则使用输入值作为世界偏移
            if cls._camera_follow_actor == actor_name and (ox != 0.0 or oy != 0.0 or oz != 2.0):
                cls._camera_follow_offset = [ox, oy, oz]
            else:
                cls._camera_follow_offset = world_offset
            cls._camera_follow_actor = actor_name
            cls._camera_follow_scene = scene_name
            cls._follow_debug_once = True  # 每次开启时重置调试输出
            logger.info("Camera following %s (offset=%s)", actor_name, cls._camera_follow_offset)
            return {"ok": True, "offset": cls._camera_follow_offset}
        except Exception as e:
            logger.error("camera_lock_set failed: %s", e)
            return {"ok": False, "error": str(e)}

    # 摄像机跟随物体
    _camera_follow_actor = None
    _camera_follow_scene = None
    _camera_follow_offset = [0.0, 0.0, 2.0]  # 世界空间偏移（摄像机 - 物体）
    _held_keys = set()  # JS端填充的WASD按键状态

    # 鼠标右键环绕相关
    _follow_rmb_down = False
    _follow_prev_mouse = None       # 上一帧鼠标屏幕坐标 (x, y)
    _follow_orbit_sensitivity = 0.004  # 每像素弧度
    _follow_cam_look_at = True      # 是否让相机始终注视锁定物体

    @classmethod
    def object_key_down(cls, key):
        """JS调用：按下WASD键"""
        cls._held_keys.add(key.lower())
        return {"ok": True}

    @classmethod
    def object_key_up(cls, key):
        """JS调用：松开WASD键"""
        cls._held_keys.discard(key.lower())
        return {"ok": True}

    _cam_panel_injected = False

    @classmethod
    def _inject_camera_panel(cls):
        """仅向 MainView 标签注入一个可拖拽小圆点 + 隐藏面板"""
        if cls._cam_panel_injected:
            return
        if not cls.CoronaEngine or not cls.tab_list:
            return
        # 只注入 MainView 标签
        tab_id = cls.tab_list.get("/MainView")
        if tab_id is None:
            return
        try:
            js = r"""
(function() {
    if (window.__camPanelLoaded) return;
    window.__camPanelLoaded = true;

    function tryInit() {
        if (!document.body) { setTimeout(tryInit, 50); return; }

        var style = document.createElement('style');
        style.textContent = '@keyframes __camPulse{0%,100%{box-shadow:0 0 6px #ec4899;}50%{box-shadow:0 0 18px #ec4899,0 0 28px #ec4899;}}';
        document.head.appendChild(style);

        var dot = document.createElement('div');
        dot.id = '__cam_toggle_dot';
        dot.title = '相机跟随 - 按住拖拽移动，点击展开';
        dot.style.cssText = 'position:fixed;top:12px;right:12px;z-index:100000;width:24px;height:24px;border-radius:50%;background:#ec4899;cursor:grab;opacity:0.85;border:2px solid #fff;animation:__camPulse 1.5s ease-in-out infinite;font-size:14px;line-height:24px;text-align:center;color:#fff;user-select:none;';
        dot.textContent = '●';
        document.body.appendChild(dot);

        var panel = document.createElement('div');
        panel.id = '__camlock_ctrl';
        panel.style.cssText = 'display:none;position:fixed;top:42px;right:12px;z-index:99999;background:#2d2d2d;border:2px solid #ec4899;border-radius:8px;padding:12px;color:#e0e0e0;font-size:12px;min-width:220px;box-shadow:0 4px 16px rgba(0,0,0,0.6);';
        panel.innerHTML =
            '<div style="font-weight:bold;margin-bottom:8px;color:#ec4899;">相机跟随</div>' +
            '<label style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">' +
            '<span>启用</span><input id="__camlock_checkbox" type="checkbox" style="accent-color:#ec4899;"></label>' +
            '<div style="margin-top:4px;font-size:10px;color:#909090;">偏移 ' +
            'X<input id="__camlock_ox" type="number" value="0" step="0.1" style="width:50px;background:#1a1a1a;color:#e0e0e0;border:1px solid #3c3c3c;border-radius:3px;margin:0 2px;padding:1px 3px;">' +
            'Y<input id="__camlock_oy" type="number" value="0" step="0.1" style="width:50px;background:#1a1a1a;color:#e0e0e0;border:1px solid #3c3c3c;border-radius:3px;margin:0 2px;padding:1px 3px;">' +
            'Z<input id="__camlock_oz" type="number" value="2" step="0.1" style="width:50px;background:#1a1a1a;color:#e0e0e0;border:1px solid #3c3c3c;border-radius:3px;margin:0 2px;padding:1px 3px;">' +
            '</div>' +
            '<button id="__camlock_apply" style="margin-top:8px;width:100%;padding:4px;background:#ec4899;color:white;border:none;border-radius:4px;cursor:pointer;font-size:11px;">应用</button>';
        document.body.appendChild(panel);

        // ---- 拖拽 ----
        var dragging = false, startX, startY, startLeft, startTop;
        dot.addEventListener('mousedown', function(e) {
            if (e.button !== 0) return;
            dragging = true;
            startX = e.clientX;
            startY = e.clientY;
            var rect = dot.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            dot.style.cursor = 'grabbing';
            dot.style.right = 'auto';
            dot.style.left = startLeft + 'px';
            dot.style.top = startTop + 'px';
            dot.style.animation = 'none';
            e.preventDefault();
        });
        window.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            dot.style.left = (startLeft + e.clientX - startX) + 'px';
            dot.style.top = (startTop + e.clientY - startY) + 'px';
        });
        window.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            dot.style.cursor = 'grab';
            dot.style.animation = '__camPulse 1.5s ease-in-out infinite';
            // 面板跟随圆点
            var r = dot.getBoundingClientRect();
            panel.style.right = 'auto';
            panel.style.left = (r.left - 220 + 24) + 'px';
            panel.style.top = (r.top + 30) + 'px';
        });

        // ---- 点击展开/收起面板 ----
        var wasDragged = false;
        dot.addEventListener('mousedown', function() { wasDragged = false; });
        dot.addEventListener('mousemove', function() { if (dragging) wasDragged = true; });
        dot.addEventListener('mouseup', function() {
            if (!wasDragged) {
                var cur = panel.style.display;
                panel.style.display = (cur === 'none' || cur === '') ? 'block' : 'none';
                if (panel.style.display === 'block') {
                    var r = dot.getBoundingClientRect();
                    panel.style.right = 'auto';
                    panel.style.left = Math.max(0, r.left - 220 + 24) + 'px';
                    panel.style.top = (r.top + 30) + 'px';
                }
            }
        });

        var following = false;

        function setFollowingUI(active) {
            if (active) {
                dot.style.background = '#4caf50';
            } else {
                dot.style.background = '#ec4899';
            }
        }

        function applyLock() {
            var enabled = document.getElementById('__camlock_checkbox').checked;
            var ox = parseFloat(document.getElementById('__camlock_ox').value) || 0;
            var oy = parseFloat(document.getElementById('__camlock_oy').value) || 0;
            var oz = parseFloat(document.getElementById('__camlock_oz').value) || 2;
            window.cefQuery({
                request: JSON.stringify({ module: 'CoronaEditor', function: 'camera_lock_set', args: [enabled, ox, oy, oz, 0, 0, 0] }),
                persistent: false,
                onSuccess: function(r) {
                    try {
                        var resp = JSON.parse(r);
                        if (resp.success) {
                            var data = resp.data;
                            if (data && data.ok) {
                                following = enabled;
                                if (enabled && data.offset) {
                                    document.getElementById('__camlock_ox').value = data.offset[0].toFixed(1);
                                    document.getElementById('__camlock_oy').value = data.offset[1].toFixed(1);
                                    document.getElementById('__camlock_oz').value = data.offset[2].toFixed(1);
                                }
                                setFollowingUI(enabled);
                            } else {
                                document.getElementById('__camlock_checkbox').checked = false;
                                following = false;
                                setFollowingUI(false);
                            }
                        }
                    } catch(e) {}
                },
                onFailure: function(e) {
                    document.getElementById('__camlock_checkbox').checked = false;
                    following = false;
                    setFollowingUI(false);
                }
            });
        }

        function updateOffset() {
            if (!following) return;
            var ox = parseFloat(document.getElementById('__camlock_ox').value) || 0;
            var oy = parseFloat(document.getElementById('__camlock_oy').value) || 0;
            var oz = parseFloat(document.getElementById('__camlock_oz').value) || 2;
            window.cefQuery({
                request: JSON.stringify({ module: 'CoronaEditor', function: 'camera_lock_set', args: [true, ox, oy, oz, 0, 0, 0] }),
                persistent: false,
                onSuccess: function(r) {},
                onFailure: function(e) {}
            });
        }

        // 键盘：ESC 退出 / WASD 移动物体
        var wasdKeys = { w:1, a:1, s:1, d:1 };
        document.addEventListener('keydown', function(e) {
            var k = e.key.toLowerCase();
            if (k === 'escape' && following) {
                e.preventDefault();
                e.stopImmediatePropagation();
                document.getElementById('__camlock_checkbox').checked = false;
                applyLock();
                return;
            }
            if (wasdKeys[k] && following) {
                e.preventDefault();
                e.stopImmediatePropagation();
                window.cefQuery({
                    request: JSON.stringify({ module: 'CoronaEditor', function: 'object_key_down', args: [k] }),
                    persistent: false,
                    onSuccess: function() {},
                    onFailure: function() {}
                });
            }
        }, true);
        document.addEventListener('keyup', function(e) {
            var k = e.key.toLowerCase();
            if (wasdKeys[k] && following) {
                e.preventDefault();
                e.stopImmediatePropagation();
                window.cefQuery({
                    request: JSON.stringify({ module: 'CoronaEditor', function: 'object_key_up', args: [k] }),
                    persistent: false,
                    onSuccess: function() {},
                    onFailure: function() {}
                });
            }
        }, true);

        document.getElementById('__camlock_checkbox').onchange = applyLock;
        document.getElementById('__camlock_apply').onclick = updateOffset;
    }
    tryInit();
})();
"""
            cls.CoronaEngine.execute_javascript(tab_id, js)
            cls._cam_panel_injected = True
            logger.info("Camera follow panel injected into MainView")
        except Exception as e:
            logger.warning("Failed to inject panel into MainView: %s", e)

    _follow_frame_count = 0
    _follow_logged_init = False

    @classmethod
    def _update_camera_follow(cls):
        """每帧更新：WASD移动物体 + 摄像机跟随物体（保持相对位置不变）"""
        cls._follow_frame_count += 1
        if not cls._follow_logged_init:
            cls._follow_logged_init = True
            logger.info("[CAMFOLLOW] _update_camera_follow is being called")
        if not cls._camera_follow_actor:
            return
        if cls._follow_frame_count % 60 == 0:
            logger.info("[CAMFOLLOW] actor=%s held_keys=%s offset=%s", cls._camera_follow_actor, cls._held_keys, cls._camera_follow_offset)
        try:
            from CoronaCore.core.managers import scene_manager, actor_manager
            actor = None
            scene = None
            if cls._camera_follow_scene:
                scene = scene_manager.get(cls._camera_follow_scene)
                if scene:
                    actor = scene.find_actor(cls._camera_follow_actor)
            if actor is None:
                actor = actor_manager.get(cls._camera_follow_actor)
            if actor is None:
                return
            if scene:
                cam = scene.get_active_camera()
            else:
                cam = None
                for s_name in scene_manager.list_all():
                    s = scene_manager.get(s_name)
                    if s:
                        cam = s.get_active_camera()
                        if cam: break
            if cam is None:
                return
            obj_pos = actor.get_position()

            # WASD检测：Win32 GetAsyncKeyState
            w_down = a_down = s_down = d_down = 0
            try:
                import ctypes
                w_down = ctypes.windll.user32.GetAsyncKeyState(0x57) & 0x8000
                a_down = ctypes.windll.user32.GetAsyncKeyState(0x41) & 0x8000
                s_down = ctypes.windll.user32.GetAsyncKeyState(0x53) & 0x8000
                d_down = ctypes.windll.user32.GetAsyncKeyState(0x44) & 0x8000
            except Exception:
                pass
            # WASD检测：JS填充的 _held_keys
            for k in list(cls._held_keys):
                if k == 'w': w_down = 0x8000
                elif k == 'a': a_down = 0x8000
                elif k == 's': s_down = 0x8000
                elif k == 'd': d_down = 0x8000

            if w_down or a_down or s_down or d_down:
                # 从 offset 推断相机朝向，确保 WASD 方向与观察方向一致
                ox, oy, oz = cls._camera_follow_offset
                look_dir = cls._normalize([-ox, -oy, -oz])
                # 取水平分量
                fwd_xz = cls._normalize([look_dir[0], 0.0, look_dir[2]])
                # 用世界 up 叉乘 forward 得到 right
                right_xz = cls._normalize(cls._cross(fwd_xz, [0.0, 1.0, 0.0]))
                move = [0.0, 0.0, 0.0]
                step = 0.5
                if w_down: move[0] += fwd_xz[0] * step; move[2] += fwd_xz[2] * step
                if s_down: move[0] -= fwd_xz[0] * step; move[2] -= fwd_xz[2] * step
                if a_down: move[0] -= right_xz[0] * step; move[2] -= right_xz[2] * step
                if d_down: move[0] += right_xz[0] * step; move[2] += right_xz[2] * step
                obj_pos = [obj_pos[0] + move[0], obj_pos[1] + move[1], obj_pos[2] + move[2]]
                actor.set_position(obj_pos, if_init=True)
                logger.info("[CAMFOLLOW] WASD move to %s", obj_pos)

            # === 鼠标右键：围绕物体环绕相机（轨道控制）===
            rmb_down = False
            try:
                rmb_down = ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000
            except Exception:
                pass

            if rmb_down:
                # 获取当前鼠标屏幕位置
                cur_mouse = None
                try:
                    class POINT(ctypes.Structure):
                        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                    pt = POINT()
                    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                    cur_mouse = (pt.x, pt.y)
                except Exception:
                    pass

                if not cls._follow_rmb_down:
                    # RMB 刚按下：记录起始位置
                    cls._follow_rmb_down = True
                    cls._follow_prev_mouse = cur_mouse
                else:
                    # RMB 持续按下：计算鼠标增量，环绕相机
                    if cur_mouse and cls._follow_prev_mouse:
                        dx = cur_mouse[0] - cls._follow_prev_mouse[0]
                        dy = cur_mouse[1] - cls._follow_prev_mouse[1]
                        cls._follow_prev_mouse = cur_mouse

                        if dx != 0 or dy != 0:
                            sensitivity = cls._follow_orbit_sensitivity
                            ox, oy, oz = cls._camera_follow_offset

                            # Yaw（水平）：绕世界 Y 轴旋转 offset
                            angle_y = -dx * sensitivity
                            cos_y = math.cos(angle_y)
                            sin_y = math.sin(angle_y)
                            new_ox = ox * cos_y - oz * sin_y
                            new_oz = ox * sin_y + oz * cos_y
                            ox, oz = new_ox, new_oz

                            # Pitch（俯仰）：绕水平 right 轴旋转 offset
                            horiz = math.sqrt(ox * ox + oz * oz)
                            if horiz > 1e-8:
                                # right = normalize(cross([ox,0,oz], [0,1,0]))
                                rx = oz / horiz
                                rz = -ox / horiz
                                angle_x = -dy * sensitivity
                                cos_x = math.cos(angle_x)
                                sin_x = math.sin(angle_x)
                                new_h = horiz * cos_x - oy * sin_x
                                new_oy = horiz * sin_x + oy * cos_x
                                ox = ox / horiz * new_h
                                oz = oz / horiz * new_h
                                oy = new_oy

                            cls._camera_follow_offset = [ox, oy, oz]
            else:
                cls._follow_rmb_down = False
                cls._follow_prev_mouse = None

            # 摄像机跟随（位置 + 注视）
            ox, oy, oz = cls._camera_follow_offset
            cam.set_position([obj_pos[0] + ox, obj_pos[1] + oy, obj_pos[2] + oz])

            # 让摄像机始终注视物体
            if cls._follow_cam_look_at:
                look_dir = cls._normalize([-ox, -oy, -oz])
                cam.set_forward(look_dir)
                cam.set_world_up([0.0, 1.0, 0.0])

        except Exception as e:
            logger.error("[CAMFOLLOW] error: %s", e)


    @classmethod
    def close_process(cls) -> None:
        os._exit(0)
        # TODO 通知c++关闭

    scripts_mgr = None  # 由 main.py 在初始化时设置
    _scripts_initialized = False

    # ================================================================
    # 向量工具（摄像机跟随等运行时逻辑共用）
    # ================================================================
    @staticmethod
    def _normalize(v):
        length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
        if length < 1e-10:
            return [0.0, 0.0, 1.0]
        return [v[0] / length, v[1] / length, v[2] / length]

    @staticmethod
    def _cross(a, b):
        return [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]

    # ================================================================

    @classmethod
    def show_log_on_js(cls):
        # ---- 懒初始化：等项目加载后补初始化脚本系统 ----
        if not cls._scripts_initialized and cls.CoronaEngine is not None:
            try:
                project_path = getattr(cls.CoronaEngine, 'active_project_path', None)
                if not project_path:
                    from utils.settings import settings_manager as _sm
                    project_path = _sm.active_project_path

                if project_path:
                    from CoronaCore.core.managers import scene_manager
                    scenes = scene_manager.list_all()
                    if scenes:
                        from CoronaCore.core.scripts_system.scripts_manager import ScriptsManager
                        import os as _os
                        if cls.scripts_mgr is None:
                            cls.scripts_mgr = ScriptsManager()
                        project_script = _os.path.join(project_path, 'Scripts', 'project_script.py')
                        scene = scene_manager.get(scenes[0])
                        if scene:
                            cls.scripts_mgr.initialize_project(project_script, scene)
                            logger.info(f"ScriptsManager: 懒初始化完成，场景={scene.name}")
                        cls._scripts_initialized = True
            except Exception:
                pass

        # ---- 每帧更新脚本管理器 ----
        if cls.scripts_mgr is not None:
            try:
                import time as _time
                now = _time.perf_counter()
                delta = now - getattr(cls, '_last_script_update', now)
                cls._last_script_update = now
                cls.scripts_mgr.update(min(delta, 0.1))
            except Exception:
                pass

        # ---- 注入相机跟随面板（仅第一个 tab） ----
        try:
            cls._inject_camera_panel()
        except Exception:
            pass

        # ---- 摄像机跟随物体更新 ----
        try:
            cls._update_camera_follow()
        except Exception:
            pass

        if "LogTool" in cls.module_list and cls.CoronaEngine:
            cls.module_list["LogTool"].show_log()
        return True

    @classmethod
    def update_drag_regions(cls, path, x, y, w, h):
        try:
            if path in cls.tab_list:
                tab_id = cls.tab_list[path]
            else:
                return f"tab_url not available. Would open: {path}"
            cls.CoronaEngine.set_tab_drag_regions(tab_id, [{'x': x, 'y': y, 'w': w, 'h': h}])
            return "Regions updated"
        except Exception as e:
            return str(e)
