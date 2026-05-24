from CoronaCore.core.corona_editor import CoronaEditor


class PluginBase:
    module_name = ""
    route_path = ""
    cn_name = ""
    page_type = -1
    docking_pos = ""

    dock_width = 0
    dock_height = 0
    dock_fixed = False
    if_init = False
    is_open = False

    @classmethod
    def open(cls):
        CoronaEditor.open_browser(
            route_path=cls.route_path,
            docking_pos=cls.docking_pos,
            dock_width=cls.dock_width,
            dock_height=cls.dock_height,
            dock_fixed=cls.dock_fixed,
        )
        cls.is_open = True

    @classmethod
    def register_web(cls, module_name: str, route_path: str, cn_name: str, page_type: int = -1, docking_pos="", dock_width=0,
                     dock_height=0, dock_fixed=False, if_init=False):
        """
        装饰器：注册配置函数
        cn_name：中文名
        view_type：模块类型：0：视图 1：插件
        """

        def decorator(c_cls):
            c_cls.module_name = module_name
            c_cls.route_path = route_path
            c_cls.cn_name = cn_name
            c_cls.page_type = page_type
            c_cls.docking_pos = docking_pos
            c_cls.dock_width = dock_width
            c_cls.dock_height = dock_height
            c_cls.dock_fixed = dock_fixed
            c_cls.if_init = if_init
            CoronaEditor.register_page(module_name, c_cls)
            return c_cls

        return decorator
