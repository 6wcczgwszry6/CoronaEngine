"""从 CAI 迁出的 LangGraph 工作流集合。

每个子模块导出 ``WORKFLOWS: Dict[int, CompiledStateGraph]``。
由 :mod:`cai_extensions.register` 在 ``install()`` 中统一注册到
CAI 的 ``WorkflowRegistry``。
"""
