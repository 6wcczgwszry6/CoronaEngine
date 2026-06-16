"""离线自验：半开放 ZoneAspect/manifest 驱动地形与装配。

这个测试刻意不验证“关键词命中某场景 profile”。M2 去特殊化要求代码侧
不再把场景身份写成 if-elif，场景差异由 LLM 输出的 aspects/params 提供。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cai_extensions.agent.scene_composer import (  # noqa: E402
    _aspect_params,
    _boundary_mtl_text,
    _build_fence_obj,
    _build_floor_obj,
    _build_disc_obj,
    _build_terrain_mesh_obj,
    _has_aspect,
    _normalize_aspect_dict,
    _shell_generation_hint,
    _select_interior_floor_shape,
    _surface_mtl_text,
    _terrain_mtl_text,
    _terrain_profile_from_spec,
    normalize_zone_aspects,
    resolve_zone_anchor,
)
from cai_extensions.agent.scene_session import PHASE_ORDER as SESSION_PHASE_ORDER  # noqa: E402
from cai_extensions.data_model.zone_tree import (  # noqa: E402
    CAPABILITY_MANIFEST,
    GENERATOR_MANIFEST,
    PHASE_ORDER as ZONE_PHASE_ORDER,
    TerrainProfile,
    Volume,
    Zone,
    ZoneAspect,
)


def _zone(enclosure="terrain", raw_aspects=None):
    z = Zone(
        zone_id="z0",
        name="测试区域",
        role="outdoor" if enclosure == "terrain" else "indoor",
        enclosure=enclosure,
        volume=Volume(center=[0.0, 0.0, 0.0], size=[20.0, 20.0, 0.0]),
    )
    z.metadata["raw_aspects"] = raw_aspects or []
    return z


def test_manifest_shape_and_phase_order():
    expected = {
        "ground_profile",
        "ground_cover",
        "boundary",
        "interior_surface",
        "entrance",
        "shell_dressing",
    }
    assert set(CAPABILITY_MANIFEST) == expected
    assert set(GENERATOR_MANIFEST) == expected
    assert "radius" in GENERATOR_MANIFEST["boundary"]["effective_params"]
    assert "margin" in GENERATOR_MANIFEST["boundary"]["effective_params"]
    assert "floor_shape" in GENERATOR_MANIFEST["interior_surface"]["effective_params"]
    assert "unsupported" not in CAPABILITY_MANIFEST
    assert SESSION_PHASE_ORDER == ["GROUND", "SHELL", "INTERIOR", "BOUNDARY", "OBJECTS", "DECORATION"]
    assert ZONE_PHASE_ORDER == SESSION_PHASE_ORDER
    print("[OK] manifest shape and PHASE_ORDER remain correct")


def test_unknown_capability_is_unsupported():
    aspect = _normalize_aspect_dict({"capability": "lava_flow", "params": {"color": "red"}})
    assert isinstance(aspect, ZoneAspect)
    assert aspect.capability == "unsupported"
    assert aspect.params["requested"] == "lava_flow"
    assert aspect.params["params"] == {"color": "red"}
    print("[OK] unknown capability is collected as unsupported")


def test_explicit_aspects_win_over_legacy_profile():
    z = _zone(raw_aspects=[
        {
            "capability": "ground_profile",
            "params": {
                "type": "rolling",
                "material": "grass",
                "amplitude": 0.8,
                "extent_factor": 6.0,
            },
        },
        {"capability": "ground_cover", "params": {"kind": "flowers", "density": 1.0}},
    ])
    z.terrain_profile = TerrainProfile(type="flat", material="stone", scatter="rocks")
    normalize_zone_aspects(z)

    profile = _aspect_params(z, "ground_profile")
    cover = _aspect_params(z, "ground_cover")
    assert profile["type"] == "rolling"
    assert profile["material"] == "grass"
    assert profile["amplitude"] == 0.8
    assert profile["extent_factor"] == 6.0
    assert cover["kind"] == "flowers"
    assert len([a for a in z.aspects if a.capability == "ground_profile"]) == 1
    print("[OK] explicit aspect params override legacy compatibility fields")


def test_fire_observatory_has_neutral_default_without_keyword_inference():
    terrain = {
        "id": "z0",
        "name": "火山口观测站外部",
        "role": "outdoor",
        "enclosure": "terrain",
    }
    p = _terrain_profile_from_spec(terrain, [terrain])
    assert p.type == "flat"
    assert p.material == "neutral"
    assert p.scatter == "none"
    assert p.style_tags == []
    assert "Kd 0.48 0.47 0.42" in _terrain_mtl_text("unknown_material")
    print("[OK] unfamiliar scenes default to neutral, not guessed grass")


def test_ground_cover_and_boundary_are_opt_in():
    z = _zone()
    z.terrain_profile = TerrainProfile()
    normalize_zone_aspects(z)
    assert _has_aspect(z, "ground_profile")
    assert not _has_aspect(z, "ground_cover")
    assert not _has_aspect(z, "boundary")

    with_cover = _zone(raw_aspects=[{"capability": "ground_cover", "params": {"kind": "grass"}}])
    normalize_zone_aspects(with_cover)
    assert _has_aspect(with_cover, "ground_cover")
    print("[OK] ground_cover/boundary only generate when declared")


def test_boundary_params_drive_kind_material_and_height():
    z = _zone(raw_aspects=[
        {"capability": "boundary", "params": {"kind": "wall", "material": "stone", "height": 1.8}},
    ])
    normalize_zone_aspects(z)
    boundary = _aspect_params(z, "boundary")
    assert boundary["kind"] == "wall"
    assert boundary["material"] == "stone"
    assert boundary["height"] == 1.8

    wall_obj = _build_fence_obj(4.0, kind="wall", height=1.8, mtl_lib="boundary.mtl")
    hedge_obj = _build_fence_obj(4.0, kind="hedge", height=0.8, mtl_lib="boundary.mtl")
    assert "# boundary kind=wall" in wall_obj
    assert "height=1.80" in wall_obj
    assert "# boundary kind=hedge" in hedge_obj
    assert "Kd 0.45 0.45 0.40" in _boundary_mtl_text("wall", "stone")
    assert "Kd 0.22 0.42 0.16" in _boundary_mtl_text("hedge", "greenery")
    print("[OK] boundary kind/material/height are generator-effective")


def test_resolve_zone_anchor_preserves_shell_path():
    class FakeComposer:
        _shell_aabb = {"shell0": {"half_x": 3.0, "half_z": 2.0}}
        _platform_radius = 0.0

    shell = _zone(enclosure="shell")
    shell.zone_id = "shell0"
    shell.volume.center = [5.0, 0.0, -4.0]
    anchor = resolve_zone_anchor(FakeComposer(), shell, "boundary")
    assert anchor["anchor_type"] == "shell"
    assert anchor["center"] == [0.0, 0.0, 0.0]
    assert anchor["ring_radius"] == 3.0 * 1.15 + 0.5
    assert anchor["half_x"] == 3.0
    assert anchor["half_z"] == 2.0
    print("[OK] shell boundary anchor keeps measured shell footprint path")


def test_resolve_zone_anchor_supports_platform_and_pure_outdoor_volume():
    class PlatformComposer:
        _shell_aabb = {}
        _platform_radius = 5.0

    terrain = _zone(raw_aspects=[
        {"capability": "boundary", "params": {"kind": "fence", "material": "wood"}},
    ])
    normalize_zone_aspects(terrain)
    platform_anchor = resolve_zone_anchor(PlatformComposer(), terrain, "boundary")
    assert platform_anchor["anchor_type"] == "platform"
    assert platform_anchor["ring_radius"] == 5.0 * 1.05 + 0.5

    class OutdoorComposer:
        _shell_aabb = {}
        _platform_radius = 0.0

    outdoor_anchor = resolve_zone_anchor(OutdoorComposer(), terrain, "boundary")
    assert outdoor_anchor["anchor_type"] == "zone_volume"
    assert outdoor_anchor["ring_radius"] == 9.0
    assert outdoor_anchor["half_x"] == 10.0
    assert outdoor_anchor["half_z"] == 10.0
    explicit_anchor = resolve_zone_anchor(
        OutdoorComposer(), terrain, "boundary", params={"radius": 6.25},
    )
    assert explicit_anchor["anchor_type"] == "zone_volume"
    assert explicit_anchor["ring_radius"] == 6.25
    obj = _build_fence_obj(outdoor_anchor["ring_radius"], kind="fence", mtl_lib="boundary.mtl")
    assert "# boundary kind=fence" in obj
    print("[OK] pure outdoor boundary can anchor to terrain platform or zone volume")


def test_style_context_is_preserved_without_code_inference():
    from cai_extensions.agent.scene_composer import SceneComposer  # noqa: E402

    specs = [
        {
            "id": "z0",
            "name": "火山口观测站外部",
            "role": "outdoor",
            "enclosure": "terrain",
            "style_context": {
                "main_building": "火山口观测站",
                "terrain_mood": "volcanic research site",
                "material_palette": ["dark stone", "metal", "concrete"],
                "functional_intent": "research",
            },
            "aspects": [
                {"capability": "ground_profile", "params": {"type": "flat", "material": "stone"}},
                {"capability": "unsupported", "params": {"requested": "lava_flow", "reason": "manifest lacks lava"}},
            ],
            "size": [30, 30, 0],
            "parent": None,
            "has_door": False,
        },
        {
            "id": "z1",
            "name": "观测站",
            "role": "indoor",
            "enclosure": "shell",
            "shell_asset": "观测站",
            "style_context": {
                "main_building": "火山口观测站",
                "terrain_mood": "volcanic research site",
                "material_palette": ["metal", "concrete"],
                "functional_intent": "research",
            },
            "aspects": [
                {"capability": "shell_dressing", "params": {"asset_id": "观测站", "style": "compact research outpost"}},
            ],
            "size": [6, 5, 3],
            "parent": "z0",
            "has_door": False,
        },
    ]
    tree = SceneComposer()._build_zone_tree(specs)
    zones = tree.list_all_zones()
    terrain, shell = zones[0], zones[1]
    assert terrain.style_context["main_building"] == "火山口观测站"
    assert terrain.style_context["material_palette"] == ["dark stone", "metal", "concrete"]
    assert not _has_aspect(terrain, "boundary")
    assert not _has_aspect(terrain, "ground_cover")
    assert any(a.capability == "unsupported" for a in terrain.aspects)
    hint = _shell_generation_hint(shell)
    assert "compact research outpost" in hint
    assert "metal" in hint
    assert "volcanic research site" in hint
    assert "毡布" not in hint
    print("[OK] style_context is preserved and only informs prompts, not code inference")


def test_decompose_snapshot_is_saved_for_f5_review():
    import json
    import os
    from cai_extensions.agent.scene_composer import SceneComposer  # noqa: E402

    specs = [
        {
            "id": "z0",
            "name": "纯室外集市",
            "role": "outdoor",
            "enclosure": "terrain",
            "aspects": [
                {"capability": "boundary", "params": {"kind": "fence", "radius": 8.0}},
            ],
            "size": [20, 20, 0],
            "parent": None,
            "has_door": False,
        },
    ]
    composer = SceneComposer(scene_name="m2_f5_test")
    tree = composer._build_zone_tree(specs)
    composer._save_zone_decompose_snapshot("纯室外集市", specs, tree)
    path = composer._last_zone_decompose_snapshot
    assert path and os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["raw_zones"][0]["name"] == "纯室外集市"
    assert payload["normalized_zones"][0]["aspects"][0]["capability"] == "boundary"
    assert payload["normalized_zones"][0]["aspects"][0]["params"]["radius"] == 8.0
    print("[OK] decompose snapshot is saved for F5 JSON review")


def test_entrance_and_interior_surface_are_aspect_driven():
    shell = _zone(enclosure="shell", raw_aspects=[
        {"capability": "shell_dressing", "params": {"asset_id": "欧式教堂", "style": "stone chapel"}},
    ])
    shell.primary_shell_asset_id = "欧式教堂"
    normalize_zone_aspects(shell)
    hint = _shell_generation_hint(shell)
    assert "stone chapel" in hint
    assert "毡布" not in hint
    assert "布帘" not in hint

    shell.metadata["raw_aspects"].append(
        {"capability": "entrance", "params": {"style": "archway", "hint": "stone archway entrance"}}
    )
    normalize_zone_aspects(shell)
    assert "stone archway entrance" in _shell_generation_hint(shell)
    assert "Kd 0.50 0.50 0.46" in _surface_mtl_text("stone")
    assert "Kd 0.58 0.56 0.50" in _surface_mtl_text("unknown_floor")
    print("[OK] entrance/interior_surface come from aspects with neutral fallback")


def test_interior_floor_shape_is_aspect_driven_with_geometry_fallback():
    assert _select_interior_floor_shape(6.0, 6.0, {"floor_shape": "quad"}) == "quad"
    assert _select_interior_floor_shape(6.0, 6.0, {"floor_shape": "disc"}) == "disc"
    assert _select_interior_floor_shape(8.0, 4.0, {}) == "quad"
    assert _select_interior_floor_shape(6.0, 5.8, {}) == "disc"
    quad = _build_floor_obj(mtl_lib="carpet.mtl", mtl_name="stone")
    disc = _build_disc_obj(mtl_lib="carpet.mtl", mtl_name="carpet")
    assert "# unit floor quad" in quad
    assert "# unit disc" in disc
    print("[OK] interior floor shape uses aspect params before geometry fallback")


def test_material_is_written_into_terrain_obj():
    p = TerrainProfile(type="rolling", material="snow", scatter="none", amplitude=0.8, frequency=0.25)
    obj = _build_terrain_mesh_obj(20.0, 20.0, p, 2.0, grid=2,
                                  mtl_lib="terrain_style.mtl", mtl_name="terrain")
    mtl = _terrain_mtl_text(p.material)
    assert "mtllib terrain_style.mtl" in obj
    assert "usemtl terrain" in obj
    assert "Kd 0.86 0.90 0.92" in mtl
    print("[OK] terrain OBJ/MTL uses explicit profile material")


if __name__ == "__main__":
    test_manifest_shape_and_phase_order()
    test_unknown_capability_is_unsupported()
    test_explicit_aspects_win_over_legacy_profile()
    test_fire_observatory_has_neutral_default_without_keyword_inference()
    test_ground_cover_and_boundary_are_opt_in()
    test_boundary_params_drive_kind_material_and_height()
    test_resolve_zone_anchor_preserves_shell_path()
    test_resolve_zone_anchor_supports_platform_and_pure_outdoor_volume()
    test_style_context_is_preserved_without_code_inference()
    test_decompose_snapshot_is_saved_for_f5_review()
    test_entrance_and_interior_surface_are_aspect_driven()
    test_interior_floor_shape_is_aspect_driven_with_geometry_fallback()
    test_material_is_written_into_terrain_obj()
    print("\n=== zone aspect / terrain profile ALL PASS ===")
