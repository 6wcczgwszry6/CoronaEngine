// 生成的 Python 代码中使用的路径常量
// 集中管理，便于项目结构调整时统一修改

export const PYTHON_IMPORTS = {
  /** CoronaEngine Scratch 兼容层（提供 Scratch 风格函数式 API） */
  ENGINE_IMPORT: 'from CoronaCore.utils import corona_engine_scratch as CoronaEngine',

  /** 主窗口相关模块路径（键盘事件桥接用） */
  MAIN_WINDOW_IMPORT: 'from Backend.ui.main_window import get_window',

  /** PySide6 Slot 装饰器路径 */
  PYTHON_SLOT_IMPORT: 'from PySide6.QtCore import Slot',
};