from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

EDITOR_DIR = Path(__file__).resolve().parents[5]
AITOOL_DIR = EDITOR_DIR / "plugins" / "AITool"
for candidate in (EDITOR_DIR, AITOOL_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from Quasar.ai_modules.three_d_generate.tools import model_tools


class CapturingHunyuanClient:
    created: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        self.api_key = kwargs.get("api_key", "")
        CapturingHunyuanClient.created.append(self.kwargs)

    def run_to_download_urls(self, **_kwargs):
        raise AssertionError("test should not invoke the real Hunyuan API")


def _config(api_keys: list[str], *, api_key: str = "", max_concurrent: int = 2) -> SimpleNamespace:
    return SimpleNamespace(
        hunyuan3d=SimpleNamespace(
            enable=True,
            api_key=api_key,
            api_keys=api_keys,
            region="ap-guangzhou",
            endpoint="api.ai3d.cloud.tencent.com",
            request_timeout=300.0,
            version="pro",
            max_concurrent_generations=max_concurrent,
            poll_interval=3.0,
            poll_timeout=600.0,
            result_format="GLB",
            enable_pbr=True,
            generate_type="Normal",
            model="3.0",
            face_count=500000,
        )
    )


def test_hunyuan_limits_each_account_to_one_generation(monkeypatch) -> None:
    CapturingHunyuanClient.created.clear()
    monkeypatch.setattr(model_tools, "Hunyuan3DClient", CapturingHunyuanClient)

    tools = model_tools.load_hunyuan3d_tools(_config(["key-a", "key-b", "key-c"], max_concurrent=2))

    assert [tool.name for tool in tools] == ["hunyuan_generate_3d"]
    assert len(CapturingHunyuanClient.created) == 3
    assert [client["api_key"] for client in CapturingHunyuanClient.created] == ["key-a", "key-b", "key-c"]
    assert [client["max_concurrent"] for client in CapturingHunyuanClient.created] == [1, 1, 1]


def test_hunyuan_single_key_fallback_is_one_total_slot(monkeypatch) -> None:
    CapturingHunyuanClient.created.clear()
    monkeypatch.setattr(model_tools, "Hunyuan3DClient", CapturingHunyuanClient)

    model_tools.load_hunyuan3d_tools(_config([], api_key="fallback-key", max_concurrent=3))

    assert len(CapturingHunyuanClient.created) == 1
    assert CapturingHunyuanClient.created[0]["api_key"] == "fallback-key"
    assert CapturingHunyuanClient.created[0]["max_concurrent"] == 1
