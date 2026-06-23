class PluginBase:
    module_name = ""

    @classmethod
    def register_web(cls, module_name: str):
        """
        旧装饰器兼容层：只标记模块名，不再注册 Python RPC。
        后端服务统一由 editor/backend/registry.py 显式注册。
        """
        def decorator(c_cls):
            c_cls.module_name = module_name
            return c_cls
        return decorator
