import importlib
import logging

logger = logging.getLogger(__name__)


def reimport():
    """
    注册显式 Python 后端服务。

    不再扫描 editor/plugins/*/main.py；Python 后端不按 Vue 页面拆分。
    """
    try:
        registry = None
        registry_errors = []
        for registry_module in ("backend.registry", "Backend.registry"):
            try:
                registry = importlib.import_module(registry_module)
                break
            except ModuleNotFoundError as e:
                package_name = registry_module.split(".", 1)[0]
                if e.name not in {package_name, registry_module}:
                    raise
                registry_errors.append(e)

        if registry is None:
            raise registry_errors[-1]

        registered = registry.register_python_backends()
        logger.info("Registered Python backends: %s", ", ".join(registered))
    except Exception as e:
        logger.error("注册 Python 后端失败: %s", e, exc_info=True)
