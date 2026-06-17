"""Focused tests for RoleAgent template injection."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cai_extensions.agent.role_registry import (  # noqa: E402
    get_role_registry,
    inject_persona_voice,
    resolve_role_template,
)
from cai_extensions.agent.agent_adapter import MasterAgent  # noqa: E402


def test_builtin_role_has_structured_biases():
    tpl = resolve_role_template("小女孩")
    assert tpl is not None
    assert tpl.name == "小女孩"
    assert tpl.object_bias
    assert tpl.layout_bias
    assert tpl.forbidden_bias
    context = tpl.to_compose_context()
    assert "RoleAgent: 小女孩" in context
    assert "object_bias_reference_only" in context
    assert "do not add these as new objects" in context


def test_role_voice_injection_keeps_persona_visible():
    system = inject_persona_voice("base", "山贼")
    assert "【你的角色】山贼" in system
    assert "【偏好物件】" in system
    assert "【布局偏好】" in system
    assert "始终以该角色的口吻回复" in system


def test_custom_role_is_supported_without_overwriting_builtin():
    reg = get_role_registry()
    tpl = reg.register_custom("elder", "赛博商人", "霓虹、市井、会砍价", "偏好霓虹摊位")
    assert tpl.key == "elder_custom"
    resolved = resolve_role_template("elder_custom")
    assert resolved is tpl
    assert resolve_role_template("长者").name == "长者"


def test_master_agent_can_build_role_compose_context():
    ctx = MasterAgent()._role_compose_context("商人")
    assert "RoleAgent: 商人" in ctx
    assert "layout_bias" in ctx
    assert "SceneState, AABB, VLM and user intent have priority" in ctx


if __name__ == "__main__":
    test_builtin_role_has_structured_biases()
    test_role_voice_injection_keeps_persona_visible()
    test_custom_role_is_supported_without_overwriting_builtin()
    test_master_agent_can_build_role_compose_context()
    print("\n=== Role registry ALL PASS ===")
