# -*- coding: utf-8 -*-
"""
CoronaEngine Scratch 兼容层
提供 Scratch 风格的函数式 API，桥接 Blockly 生成的代码与底层 OOP 引擎。

此模块作为模块级函数使用，生成的 Python 代码以：
    from CoronaCore.utils import corona_engine_scratch as CoronaEngine
方式导入，然后调用 CoronaEngine.move(10) 等。

支持两种模式：
1. 独立模式（无参数 set_target）：自建内部 Actor（向后兼容）
2. 绑定模式（调用 set_target）：操作场景管理器中指定的真实 Actor
"""

import random as _random
import time as _time
import logging

_logger = logging.getLogger(__name__)

# ============================================================
# 内部状态（模块级单例）
# ============================================================

_x = 0.0
_y = 0.0
_z = 0.0
_size_val = 100.0
_cartoon_index = 0
_visible = True
_variables = {}  # var_name -> float

# 目标 Actor / Scene 引用
_target_scene_name = None
_target_actor_name = None
_target_scene = None
_target_actor = None

# 底层引擎对象
_geometry = None
_optics = None
_kinematics = None
_actor = None
_scene = None
_initialized = False

# 标记是否已设置外部目标
_external_target = False

# 脚本执行停止标志（线程安全）
_stop_requested = False


def set_target(scene_name: str, actor_name: str):
    """设置该模块操作的目标 Actor（绑定到场景中的真实物体）
    
    调用此函数后，所有操作将作用于场景管理器中的实际 Actor，
    而非自建的内部对象。
    
    Args:
        scene_name: 场景路径/名称，如 "Scene/main.scene"
        actor_name: Actor 名称
    """
    global _target_scene_name, _target_actor_name, _external_target, _initialized
    _target_scene_name = scene_name
    _target_actor_name = actor_name
    _external_target = True
    _initialized = False  # 强制重新初始化
    print(f"[ScratchWrapper] set_target: scene={scene_name}, actor={actor_name}", flush=True)


def _init_engine():
    """延迟初始化底层 CoronaEngine 对象
    
    如果已通过 set_target() 绑定了外部 Actor，则从 scene_manager 查找真实对象；
    否则自建内部 Actor（向后兼容）。
    """
    global _geometry, _optics, _kinematics, _actor, _scene, _initialized
    global _target_scene, _target_actor

    if _initialized:
        return
    _initialized = True

    if _external_target:
        _init_external_target()
    else:
        _init_internal_actor()


def _init_external_target():
    """绑定到场景管理器中的真实 Actor"""
    global _geometry, _optics, _kinematics, _actor, _scene
    global _target_scene, _target_actor

    print(f"[ScratchWrapper] _init_external_target: scene={_target_scene_name} actor={_target_actor_name}", flush=True)

    try:
        from CoronaCore.core.managers import scene_manager

        _target_scene = scene_manager.get(_target_scene_name)
        if _target_scene is None:
            print(f"[ScratchWrapper] 场景未找到，回退独立模式", flush=True)
            _init_internal_actor()
            return

        _target_actor = _target_scene.find_actor(_target_actor_name)
        if _target_actor is None:
            print(f"[ScratchWrapper] Actor未找到，回退独立模式", flush=True)
            _init_internal_actor()
            return

        print(f"[ScratchWrapper] Actor找到: type={type(_target_actor).__name__} id={id(_target_actor)}", flush=True)

        # 获取真实 Actor 的组件
        _actor = _target_actor
        _scene = _target_scene

        if hasattr(_target_actor, '_geometry') and _target_actor._geometry is not None:
            _geometry = _target_actor._geometry
            print(f"[ScratchWrapper] _geometry绑定: type={type(_geometry).__name__}", flush=True)
        else:
            print(f"[ScratchWrapper] _geometry未找到 (hasattr={hasattr(_target_actor, '_geometry')})", flush=True)

        if hasattr(_target_actor, '_optics') and _target_actor._optics is not None:
            _optics = _target_actor._optics
        if hasattr(_target_actor, '_kinematics') and _target_actor._kinematics is not None:
            _kinematics = _target_actor._kinematics

        # 同步内部状态到实际 Actor 的当前值
        try:
            pos = _target_actor.get_position()
            global _x, _y, _z
            _x, _y, _z = float(pos[0]), float(pos[1]), float(pos[2])
        except Exception:
            pass

        try:
            scl = _target_actor.get_scale()
            global _size_val
            _size_val = float(scl[0]) * 100.0
            print(f"[ScratchWrapper] 初始scale={scl}, _size_val={_size_val}", flush=True)
        except Exception:
            pass

        print(
            f"[ScratchWrapper] 已绑定: scene={_target_scene_name} "
            f"actor={_target_actor_name} pos=({_x:.2f},{_y:.2f},{_z:.2f}) size={_size_val:.1f}",
            flush=True,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ScratchWrapper] 绑定外部Actor异常: {e}", flush=True)
        _init_internal_actor()


def _init_internal_actor():
    """独立模式（无场景上下文）

    不创建引擎对象（避免加载不存在的模型文件报错），
    仅使用内部变量 _x/_y/_z/_size_val 追踪状态。
    所有 getter/setter 函数已对 None 做了安全保护。
    """
    global _geometry, _optics, _kinematics, _actor, _scene

    _geometry = None
    _optics = None
    _kinematics = None
    _actor = None
    _scene = None

    print("[ScratchWrapper] 独立模式（无渲染）", flush=True)


# ============================================================
# 运动 (Engine) — 16 个函数
# ============================================================

def move(steps):
    """向前移动 steps 步"""
    _init_engine()
    global _x
    _x += float(steps)
    _sync_position()


def rotateX(angle):
    """绕X轴旋转"""
    _init_engine()
    if _kinematics is not None:
        try:
            _kinematics.rotate_x(float(angle))
        except Exception:
            pass
    _logger.debug(f"[ScratchWrapper] rotateX({angle})")


def rotateY(angle):
    """绕Y轴旋转"""
    _init_engine()
    if _kinematics is not None:
        try:
            _kinematics.rotate_y(float(angle))
        except Exception:
            pass
    _logger.debug(f"[ScratchWrapper] rotateY({angle})")


def face(direction):
    """面向某个方向（0=右, 90=前, 180=左, 270=后，使用 Y 轴欧拉角设置绝对朝向）"""
    _init_engine()
    if _geometry is not None:
        try:
            # Geometry.set_rotation 使用欧拉角 ZYX: [pitch, yaw, roll]
            _geometry.set_rotation([0.0, float(direction), 0.0])
            print(f"[ScratchWrapper] face({direction}) -> set_rotation ok", flush=True)
        except Exception as e:
            print(f"[ScratchWrapper] face({direction}) FAILED: {e}", flush=True)


def moveto(position):
    """移动到预设位置"""
    _init_engine()
    global _x, _y, _z

    import random

    if position == 'random_position':
        _x = random.uniform(-10, 10)
        _y = random.uniform(-5, 5)
        _z = random.uniform(-10, 10)
    elif position == 'sight_position':
        _x, _y, _z = 0.0, 0.0, 0.0
    else:
        print(f"[ScratchWrapper] moveto 未知位置: {position}", flush=True)
        return

    _sync_position()
    print(f"[ScratchWrapper] moveto({position}) -> ({_x:.2f}, {_y:.2f}, {_z:.2f})", flush=True)


def movetoXYZ(position):
    """移动到 XYZ 位置"""
    _init_engine()
    _logger.debug(f"[ScratchWrapper] movetoXYZ({position})")


def movetoXYZtime(t, x1, x2, x3):
    """在 t 时间内移动到 (x1,x2,x3)"""
    _init_engine()
    global _x, _y, _z
    _x, _y, _z = float(x1), float(x2), float(x3)
    _sync_position()
    _logger.debug(f"[ScratchWrapper] movetoXYZtime(t={t}, x={x1},{x2},{x3})")


def Xset(x):
    """设置 X 坐标"""
    _init_engine()
    global _x
    _x = float(x)
    _sync_position()


def Yset(y):
    """设置 Y 坐标"""
    _init_engine()
    global _y
    _y = float(y)
    _sync_position()


def Zset(z):
    """设置 Z 坐标"""
    _init_engine()
    global _z
    _z = float(z)
    _sync_position()


def Xadd(dx):
    """X 坐标增加"""
    _init_engine()
    global _x
    _x += float(dx)
    _sync_position()


def Yadd(dy):
    """Y 坐标增加"""
    _init_engine()
    global _y
    _y += float(dy)
    _sync_position()


def Zadd(dz):
    """Z 坐标增加"""
    _init_engine()
    global _z
    _z += float(dz)
    _sync_position()


def X():
    """获取 X 坐标"""
    _init_engine()
    return _x


def Y():
    """获取 Y 坐标"""
    _init_engine()
    return _y


def Z():
    """获取 Z 坐标"""
    _init_engine()
    return _z


def _sync_position():
    """将内部坐标同步到引擎 Geometry"""
    if _geometry is not None:
        try:
            _geometry.set_position([_x, _y, _z])
            print(f"[ScratchWrapper] _sync_position: ({_x:.2f}, {_y:.2f}, {_z:.2f})", flush=True)
        except Exception as e:
            print(f"[ScratchWrapper] _sync_position FAILED: {e}", flush=True)
    elif _actor is not None and hasattr(_actor, 'set_position'):
        try:
            _actor.set_position([_x, _y, _z])
            print(f"[ScratchWrapper] _sync_position(actor): ({_x:.2f}, {_y:.2f}, {_z:.2f})", flush=True)
        except Exception as e:
            print(f"[ScratchWrapper] _sync_position(actor) FAILED: {e}", flush=True)
    else:
        print(f"[ScratchWrapper] _sync_position: SKIP (no geometry/actor)", flush=True)


# ============================================================
# 外观 (Appearance) — 11 个函数
# ============================================================

def cartoonSet(index):
    """切换到指定动画"""
    _init_engine()
    global _cartoon_index
    _cartoon_index = int(index)
    if _kinematics is not None:
        try:
            _kinematics.set_animation(int(index))
        except Exception:
            pass


def nextCartoon():
    """切换到下一个动画"""
    _init_engine()
    global _cartoon_index
    _cartoon_index += 1
    if _kinematics is not None:
        try:
            _kinematics.set_animation(_cartoon_index)
        except Exception:
            pass


def playCartoon():
    """播放动画"""
    _init_engine()
    if _kinematics is not None:
        try:
            _kinematics.play_animation()
        except Exception:
            pass


def stopCartoon():
    """停止动画"""
    _init_engine()
    if _kinematics is not None:
        try:
            _kinematics.stop_animation()
        except Exception:
            pass


def resetCartoon():
    """重置动画"""
    _init_engine()
    global _cartoon_index
    _cartoon_index = 0
    if _kinematics is not None:
        try:
            _kinematics.set_animation(0)
        except Exception:
            pass


def sizeAdd(ds):
    """大小增加"""
    _init_engine()
    global _size_val
    _size_val += float(ds)
    _sync_scale()


def sizeSet(sz):
    """设置大小"""
    _init_engine()
    global _size_val
    _size_val = float(sz)
    _sync_scale()


def show(v=None):
    """显示"""
    _init_engine()
    global _visible
    _visible = True
    if _optics is not None:
        try:
            _optics.set_visible(True)
        except Exception:
            pass
    elif _actor is not None and hasattr(_actor, 'set_visible'):
        try:
            _actor.set_visible(True)
        except Exception:
            pass


def hide(v=None):
    """隐藏"""
    _init_engine()
    global _visible
    _visible = False
    if _optics is not None:
        try:
            _optics.set_visible(False)
        except Exception:
            pass
    elif _actor is not None and hasattr(_actor, 'set_visible'):
        try:
            _actor.set_visible(False)
        except Exception:
            pass


def cartoon():
    """获取当前动画编号"""
    _init_engine()
    return _cartoon_index


def size():
    """获取当前大小"""
    _init_engine()
    return _size_val


def _sync_scale():
    s = _size_val / 100.0
    if _geometry is not None:
        try:
            _geometry.set_scale([s, s, s])
            print(f"[ScratchWrapper] _sync_scale: {s:.3f} (from _size_val={_size_val:.1f})", flush=True)
        except Exception as e:
            print(f"[ScratchWrapper] _sync_scale FAILED: {e}", flush=True)
    elif _actor is not None and hasattr(_actor, 'set_scale'):
        try:
            _actor.set_scale([s, s, s])
            print(f"[ScratchWrapper] _sync_scale(actor): {s:.3f}", flush=True)
        except Exception as e:
            print(f"[ScratchWrapper] _sync_scale(actor) FAILED: {e}", flush=True)
    else:
        print(f"[ScratchWrapper] _sync_scale: SKIP (no geometry/actor, _size_val={_size_val:.1f})", flush=True)


# ============================================================
# 侦测 (Detect) — 8 个函数
# ============================================================

def touch(target):
    """检测是否碰到目标"""
    return False


def distance(target):
    """到目标的距离"""
    return 0.0


def ask(question):
    """询问并等待回答"""
    _logger.info(f"[ScratchWrapper] ask: {question}")
    try:
        return input(question)
    except (EOFError, OSError):
        return ""


def keyboard(key):
    """检测按键是否按下"""
    return False


def keyboard0(key):
    """检测按键是否未按下"""
    return False


def mouse1():
    """检测鼠标是否按下"""
    return False


def mouse0():
    """检测鼠标是否未按下"""
    return False


def attribute(name):
    """获取属性值"""
    return 0.0


# ============================================================
# 控制 (Control) — 7 个函数
# ============================================================

def wait(seconds):
    """等待指定秒数"""
    _time.sleep(float(seconds))


def stop(option):
    """停止脚本
    option 可能值:
      - 'ALL_SCRIPTS' / 'all' → 停止所有脚本（退出进程）
      - 'CURRENT_SCRIPT' / 'this' → 停止当前脚本
      - 'OTHER_SCRIPTS_OF_ACTOR' → 停止该角色的其他脚本（单脚本模式下同 this）
    """
    if option in ("ALL_SCRIPTS", "all"):
        import sys
        sys.exit(0)
    raise SystemExit(0)


def cloneStart():
    """当作为克隆体启动时"""
    _logger.debug("[ScratchWrapper] cloneStart")


def clone(name):
    """克隆自身"""
    _logger.debug(f"[ScratchWrapper] clone({name})")


def deleteClone():
    """删除此克隆体"""
    _logger.debug("[ScratchWrapper] deleteClone")


def setScene(name):
    """切换场景"""
    _logger.debug(f"[ScratchWrapper] setScene({name})")


def nextScene():
    """下一个场景"""
    _logger.debug("[ScratchWrapper] nextScene")


# ============================================================
# 事件 (Event) — 4 个函数
# ============================================================

def gameStart():
    """游戏开始事件标记"""
    _logger.debug("[ScratchWrapper] gameStart")


def RB(message):
    """发送消息（广播）"""
    _logger.debug(f"[ScratchWrapper] RB: {message}")


def broadcast(message):
    """广播消息"""
    _logger.debug(f"[ScratchWrapper] broadcast: {message}")


def broadcastWait(message):
    """广播消息并等待"""
    _logger.debug(f"[ScratchWrapper] broadcastWait: {message}")


# ============================================================
# 数学 (Math)
# ============================================================

def random(a, b):
    """返回 a 到 b 之间的随机数"""
    return _random.uniform(float(a), float(b))


# ============================================================
# 变量 (Variable)
# ============================================================

def var_add(name, value):
    """变量增加"""
    _variables[name] = _variables.get(name, 0.0) + float(value)


def var_set(name, value):
    """设置变量值"""
    _variables[name] = float(value)


def var_show(name):
    """显示变量"""
    _logger.info(f"[ScratchWrapper] var_show: {name} = {_variables.get(name, 0.0)}")


def var_hide(name):
    """隐藏变量"""
    _logger.debug(f"[ScratchWrapper] var_hide: {name}")


# ============================================================
# 列表 (List)
# ============================================================

def list_show(name):
    """显示列表"""
    _logger.debug(f"[ScratchWrapper] list_show: {name}")


def list_hide(name):
    """隐藏列表"""
    _logger.debug(f"[ScratchWrapper] list_hide: {name}")


# ============================================================
# 脚本停止控制
# ============================================================

def request_stop():
    """请求停止当前正在执行的脚本"""
    global _stop_requested
    _stop_requested = True
    _logger.info("[ScratchWrapper] 停止请求已发送")


def reset_stop():
    """重置停止标志（新脚本执行前调用）"""
    global _stop_requested
    _stop_requested = False


def is_stop_requested():
    """检查是否已请求停止"""
    return _stop_requested