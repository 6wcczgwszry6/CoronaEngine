"""
AI Hint Service — diversity-first prompt engine.

Every call cycles through a different "persona" so the AI never responds
the same way twice, even with identical context.
"""

import logging
import random
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ── 12 completely different system prompts (personas) ──
# Each approaches hint generation from a completely different angle.
PERSONAS = [
    # 0: 作品类型推测 → 功能建议
    """你是 Corona 编辑器的 AI 助手白菜。
根据用户的操作轨迹，推测他正在做什么类型的作品（平台游戏、动画短片、互动故事、物理模拟、益智游戏等），然后直接给一个推进这个作品的具体操作建议。
15字以内。必须是可以立刻执行的功能性建议。
只输出一句话，不要引号、标记、emoji。""",

    # 1: 创作阶段判断 → 下一步
    """你是 Corona 编辑器的 AI 助手白菜。
根据用户操作轨迹判断他处于创作的哪个阶段（搭框架、调细节、加特效、修bug、准备导出等），然后直接告诉他这个阶段最该做的下一步操作。
15字以内。建议必须推进他的作品完成度。
只输出一句话，不要引号、标记、emoji。""",

    # 2: 效率优化 → 功能捷径
    """你是 Corona 编辑器的 AI 助手白菜。
根据用户的操作轨迹，发现他在某个功能上花了很多时间。直接告诉他一个更高效的完成方式，帮他加快创作进度。
15字以内。给出更快完成当前任务的方法。
只输出一句话，不要引号、标记、emoji。""",

    # 3: 功能组合 → 创作技巧
    """你是 Corona 编辑器的 AI 助手白菜。
观察用户的操作轨迹，推测他想要实现的效果。建议一个功能组合来实现这个效果（比如"用克隆积木做弹幕"）。
15字以内。告诉用户用哪个功能配合哪个功能，做出什么效果。
只输出一句话，不要引号、标记、emoji。""",

    # 4: 瓶颈突破 → 具体方法
    """你是 Corona 编辑器的 AI 助手白菜。
用户在某处停留很久，说明遇到了创作瓶颈。根据他的操作轨迹推测他卡在哪里，直接给一个突破瓶颈的具体方法。
15字以内。像一个有经验的创作者给出的建议。
只输出一句话，不要引号、标记、emoji。""",

    # 5: 创意灵感 → 功能实现
    """你是 Corona 编辑器的 AI 助手白菜。
根据用户操作轨迹推测他作品的类型和风格，然后给一个让作品更有趣的功能创意（具体到用哪个积木或工具来实现）。
15字以内。创意要和他的作品直接相关。
只输出一句话，不要引号、标记、emoji。""",

    # 6: 进阶技巧 → 深度功能
    """你是 Corona 编辑器的 AI 助手白菜。
用户在当前区域停留，说明他可能需要这个区域的进阶用法。根据他的操作轨迹，推荐一个他能用上的深度功能。
15字以内。告诉用户一个普通用户不知道的用法。
只输出一句话，不要引号、标记、emoji。""",

    # 7: 老手经验 → 实战建议
    """你是 Corona 编辑器的 AI 助手白菜，做了三年游戏开发。
看用户的操作轨迹，你大概知道他在做什么类型的项目。分享一条你做类似项目时的实战经验（具体到操作）。
15字以内。像工作室里的同事随口给你的建议。
只输出一句话，不要引号、标记、emoji。""",

    # 8: 完整流程 → 当前环节
    """你是 Corona 编辑器的 AI 助手白菜。
创作一个作品有完整流程（设计→搭建→调试→美化→发布）。根据用户操作轨迹判断他在哪个环节，告诉他这个环节最关键的一步操作是什么。
15字以内。精准命中当前环节的核心操作。
只输出一句话，不要引号、标记、emoji。""",

    # 9: 问题预判 → 提前建议
    """你是 Corona 编辑器的 AI 助手白菜。
根据用户操作轨迹，预判他接下来可能会遇到什么问题或需要什么功能，提前给出建议，让他少走弯路。
15字以内。在问题出现之前就给出解决方案。
只输出一句话，不要引号、标记、emoji。""",

    # 10: 极简指令
    """你是 Corona 编辑器的 AI 助手白菜。
你只说最关键的动词+对象，像命令行一样精准。不给任何解释。
比如"拖运动积木到工作区"、"右键→复制积木"。
12字以内。可以立刻照做。
只输出一句话，不要引号、标记、emoji。""",

    # 11: 效果驱动
    """你是 Corona 编辑器的 AI 助手白菜。
不管用户现在鼠标在哪，根据他的操作轨迹思考：他做的这个作品，加什么效果会让它更出彩？然后告诉他具体怎么加这个效果。
15字以内。以最终作品效果为导向。
只输出一句话，不要引号、标记、emoji。""",
]


class AIHintService:
    def __init__(self) -> None:
        self._ai: Optional[Callable[[str], Optional[str]]] = None
        self._idx = random.randint(0, len(PERSONAS) - 1)
        self._last_raw_hints: list[str] = []  # track what AI returned recently

    def set_ai_caller(self, caller: Callable[[str], Optional[str]]) -> None:
        self._ai = caller

    def generate_hint(self, element_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        ctx = context or {}
        context_prompt = ctx.get("contextPrompt", "")

        if self._ai and context_prompt:
            result = self._call_ai(context_prompt)
            if result:
                return result

        return self._fallback(element_type)

    def _call_ai(self, context_prompt: str) -> Optional[str]:
        # Pick a persona (rotate, never repeat adjacent)
        persona = PERSONAS[self._idx % len(PERSONAS)]
        self._idx = (self._idx + 1) % len(PERSONAS)

        # Build full prompt
        full = f"""{persona}

【当前上下文】
{context_prompt}

请根据以上所有信息，输出一句提示："""

        try:
            result = self._ai(full)
            if result and isinstance(result, str):
                text = result.strip().strip('"''""').strip()
                if len(text) > 60:
                    text = text[:60]
                if text and text not in self._last_raw_hints[-5:]:
                    self._last_raw_hints.append(text)
                    if len(self._last_raw_hints) > 20:
                        self._last_raw_hints = self._last_raw_hints[-20:]
                    return text
                # If duplicate, still track but return it — better than nothing
                if text:
                    self._last_raw_hints.append(text)
                    return text
        except Exception as exc:
            logger.debug("AI hint failed: %s", exc)
        return None

    def _fallback(self, element_type: str) -> str:
        pool = _FALLBACKS.get(element_type, _FALLBACKS["_default"])
        return random.choice(pool)


_FALLBACKS: Dict[str, list] = {
    "blockly-toolbox": [
        "从左边拖一个运动类积木到工作区",
        "点击分类名展开，拖一个积木出来",
        "外观类积木可以改角色造型，拖个试试",
        "事件类积木放在最顶部，选一个拖进去",
    ],
    "blockly-category": [
        "点击这个分类，把里面的积木拖到工作区",
        "双击分类名可以展开/收起",
        "找到你需要的积木，拖到右边拼起来",
    ],
    "blockly-flyout": [
        "往下滚还有更多积木，拖一个到工作区",
        "选中一个积木拖到右边空白处",
    ],
    "blockly-block": [
        "把这块积木拖到另一块下面拼起来",
        "右键这块积木可以复制一份",
        "点击积木上的小箭头切换模式",
        "拖动积木到其他积木的凹槽里拼合",
    ],
    "blockly-workspace": [
        "从左边工具箱拖一个积木进来开始编程",
        "右键工作区可以粘贴或清理积木",
        "Ctrl+滚轮缩放，拖拽空白处平移视角",
        "把不要的积木拖到右下角垃圾桶",
    ],
    "blockly-trash": [
        "把不要的积木拖到这里就能删除",
        "选中积木后按 Delete 键更快",
    ],
    "blockly-zoom": [
        "按住Ctrl+滚轮可以缩放工作区",
        "点击+/-按钮或直接用滚轮缩放",
    ],
    "menubar": [
        "点击「运行」菜单可以执行你的程序",
        "点击「项目」菜单导入素材",
        "点击「视图」切换面板布局",
    ],
    "menu-button": [
        "点击这个菜单按钮展开选项",
        "点击展开后选择你需要的功能",
    ],
    "menu-item": [
        "点击这里立即执行该功能",
        "直接点击就能用，试试看效果",
    ],
    "tab-bar": [
        "点击 + 号新建一个场景",
        "双击场景标签打开场景管理器",
        "右键场景标签可以重命名或删除",
    ],
    "scene-tab": [
        "点击切换到这个场景开始编辑",
        "双击这个标签打开场景管理面板",
        "右键可以重命名或关闭场景",
    ],
    "camera-speed": [
        "拖动滑块调节视角移动速度",
        "Shift+滚轮也能快速调速度",
        "按住右键旋转视角，滚轮缩放",
    ],
    "physics-param": [
        "修改重力值后点「应用物理参数」生效",
        "调大弹性值让碰撞更有弹力",
        "改完参数一定要点应用按钮",
    ],
    "modal-overlay": [
        "按 Esc 键可以关闭这个弹窗",
        "点击遮罩区域也能关闭弹窗",
    ],
    "modal-input": [
        "输入名称后按回车确认",
        "给场景起一个好记的名字，输入后回车",
    ],
    "ai-talk": [
        "在这里打字让我帮你生成代码",
        "试试让我帮你调试积木程序的错误",
        "上传一张图片让我帮你分析",
        "告诉我你想做什么功能，我帮你写积木",
    ],
    "file-manager": [
        "右键文件可以重命名或删除",
        "把图片文件拖到场景中直接导入",
        "双击文件打开，拖拽文件整理目录",
    ],
    "scene-manager": [
        "拖入图片或模型文件到场景中",
        "选中场景中的对象后右键调整属性",
        "点击场景名切换到该场景编辑",
    ],
    "object-panel": [
        "点中场景里的对象后在这里改坐标",
        "修改X/Y值可以移动对象位置",
        "调整缩放值改变对象大小",
    ],
    "log-view": [
        "红色文字是错误提示，点击可定位问题",
        "看到红色报错就点一下查看详情",
    ],
    "project-settings": [
        "修改分辨率可以改变画面大小",
        "设置好后点击保存按钮生效",
    ],
    "project-launcher": [
        "点击项目卡片打开已有项目",
        "点击「新建项目」创建一个空白项目",
    ],
    "cabbage": [
        "试试把积木拖到工作区开始编程",
        "在左边工具箱找运动类积木开始吧",
        "右键工作区可以清理积木",
        "按Ctrl+滚轮缩放工作区视角",
    ],
    "dock-titlebar": [
        "拖拽标题栏可以移动整个面板",
        "双击标题栏最小化面板",
        "右键标题栏可以关闭面板",
    ],
    "ui-button": [
        "点击这个按钮执行操作",
        "放心点下去，看看会发生什么",
    ],
    "ui-input": [
        "在这里输入内容后按回车确认",
        "按 Tab 键跳到下一个输入框",
    ],
    "ui-slider": [
        "拖动滑块调整数值大小",
        "按住 Shift 拖动可以微调数值",
    ],
    "ui-select": [
        "点击展开下拉列表选择选项",
        "直接打字可以搜索选项",
    ],
    "_default": [
        "从左边工具箱拖一个积木到工作区",
        "试试右键，可能有你需要的功能",
        "按Ctrl+Z可以撤销上一步操作",
        "Ctrl+滚轮缩放，拖拽平移视角",
        "选中积木后按Delete键可以删除",
        "把两个积木拼在一起看看效果",
        "点击左上角菜单栏探索更多功能",
        "试试拖拽图片文件到场景中",
    ],
}

# ── Global singleton ──
_hint_service: Optional[AIHintService] = None


def get_hint_service() -> AIHintService:
    global _hint_service
    if _hint_service is None:
        _hint_service = AIHintService()
    return _hint_service
