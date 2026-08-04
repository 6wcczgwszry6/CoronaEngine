import logging
from typing import Dict, Any, List



try:
    # AITool adds its directory to sys.path and executes Quasar as a top-level
    # package. Register settings in that same namespace so chat and Runtime
    # tools do not observe different collector singletons.
    from Quasar.ai_service.entrance import ai_entrance
    from Quasar.ai_config.ai_config import reload_ai_config

    @ai_entrance.collector.register_setting("chat")
    def CHAT_SETTINGS() -> Dict[str, Any]:
        return {
            "provider": "dmxapi",
            "model": "gpt-5.5",
            "layout_model": "gpt-5.5",
            "system_prompt": """你是一个 AI 助手，可以帮助用户完成各种任务。""",
        }

    @ai_entrance.collector.register_setting("providers")
    def PROVIDERS() -> List[Dict[str, Any]]:
        return [
            {
                "name": "deepseek",
                "type": "openai-compatible",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-f3a2455ca5ab406f896995a1bc397ce6",
            },
            {
                "name": "dmx_image",
                "type": "dmx",
                "base_url": "https://www.dmxapi.cn/v1/images/generations",
                "api_key": "sk-rXnByZNBJ00vyRfjE4DBeqNRm3gdqdFH3a440099bsFcU5gy",
            },
            # {
            #     "name": "grsai_image",
            #     "type": "grsai",
            #     "base_url": "https://grsai.dakka.com.cn/v1/api/generate",
            #     "api_key": "sk-13e382852c4948f6b5c717535a5a1a0c",
            # },
            {
                "name": "dmxapi",
                "type": "openai-compatible",
                "base_url": "https://www.dmxapi.cn/v1",
                "api_key": "sk-rXnByZNBJ00vyRfjE4DBeqNRm3gdqdFH3a440099bsFcU5gy",
            },
        ]

    @ai_entrance.collector.register_setting("image")
    def IMAGE_SETTINGS() -> Dict[str, Any]:
        return {
            "enable": True,
            "provider": "dmx_image",
            "model": "gpt-image-2",
            "base_url": "https://www.dmxapi.cn/v1/images/generations",
        }

    @ai_entrance.collector.register_setting("omni")
    def OMNI_SETTINGS() -> Dict[str, Any]:
        return {
            "enable": True,
            "provider": "dmxapi",
            "model": "gpt-5.5",
            "request_timeout": 180.0,
            "image_detail": "auto",
        }

    @ai_entrance.collector.register_setting("hunyuan3d")
    def HUNYUAN_3D_SETTINGS() -> Dict[str, Any]:
        return {
            "enable": True,
            "api_key": "sk-S1bc5LI8kFJ8ZgK1QDLUQEf5IiGZydZS5eBQSe8CNleZ1i1B",
            "api_keys": [
                "sk-1RH8TDkGYaa8ZyOY8gZNnrwtOSfvkgwQ9KViyQbFxJuinK1m",
                "sk-z2rIl9cCvOp9oSQouogE0UB9nwRzgKBpfaupWHMYWgj4hcXb"
            ],
            "region": "ap-guangzhou",
            "endpoint": "api.ai3d.cloud.tencent.com",
            "version": "pro",
            "result_format": "GLB",
            "enable_pbr": True,
            "model": "3.0",
            "generate_type": "Normal",
            "face_count": 20000,
            "request_timeout": 300.0,
            "poll_interval": 3.0,
            "poll_timeout": 600.0,
            "max_concurrent_generations": 2,
        }

    reload_ai_config()

    # 强制工具注册表重新发现（用户配置可能在 warmup 之后加载）
    from Quasar.ai_tools.registry import get_tool_registry
    get_tool_registry().reset_discovery()
    from Quasar.ai_agent.executor import reset_cached_agent
    reset_cached_agent()

except ImportError as e:
    logging.error(e)
