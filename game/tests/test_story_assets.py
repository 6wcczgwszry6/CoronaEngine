"""Shipped story assets/deployment checks, without loading any native engine."""
import contextlib
import importlib.util
import io
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "game/art/models"
NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


class StoryAssetTests(unittest.TestCase):
    def test_role_sources_are_animated_and_all_external_images_are_local(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to read the shared character configuration")
        result = subprocess.run([node, "--input-type=module", "-e",
            "import {STORY_CHARACTERS} from './game/frontend/storyCharacters.mjs'; "
            "console.log(JSON.stringify(STORY_CHARACTERS));"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=15)
        characters = json.loads(result.stdout)
        self.assertEqual([c["role"] for c in characters], ["player", "boss", "merchant", "prophet"])
        self.assertEqual(len({c["guid"] for c in characters}), 4)
        for character in characters:
            with self.subTest(role=character["role"]):
                model = (ART / character["asset"]).resolve()
                self.assertTrue(model.is_relative_to(ART))
                self.assertTrue(model.is_file(), str(model))
                document = ET.parse(model).getroot()
                self.assertTrue(document.findall("c:library_animations/c:animation", NS))
                for image in document.findall("c:library_images/c:image/c:init_from", NS):
                    image_uri = urlparse(image.text)
                    self.assertEqual(image_uri.scheme, "", image.text)
                    texture = (model.parent / unquote(image_uri.path)).resolve()
                    self.assertTrue(texture.is_relative_to(model.parent), str(texture))
                    self.assertTrue(texture.is_file(), str(texture))

    # Every game-owned art file must be an untouched copy of an engine asset. `cube` is a
    # hand-authored primitive, so it is registered here too: the invariant is "copied, not
    # edited", not "downloaded". `fragment` was missing from this table before.
    # `scene` is the story world map: its measurements are re-derived from the shipped GLB
    # below and compared with the placement the page actually runs.
    ART_SOURCES = {
        "player": ROOT / "assets/Maria WProp J J Ong",
        "boss": ROOT / "assets/dragon/dae",
        "merchant": ROOT / "assets/Maw J Laygo",
        "prophet": ROOT / "assets/model",
        "fragment": ROOT / "assets/model",
        "cube": ROOT / "assets/model",
        "scene": ROOT / "assets/model",
    }
    # A character folder carries one rigged model; props are plain meshes with no animation.
    CHARACTER_ART_ROLES = ("player", "boss", "merchant", "prophet")

    # The story world map. `scale` is the model's largest world-AABB axis in metres: the
    # engine normalises every static model into a unit cube, so that is exactly the
    # `geometry.scale` an actor needs to appear at its real size. `floorOffset` is where the
    # walkable courtyard sits relative to the model's own centre, and the placement removes
    # it so the surface lands on the engine floor y = 0 that the story uses for feet.
    # Both numbers live in the `map` block of game/data/prophet.json; the tests below
    # re-derive them from the shipped GLB so neither side can drift away from the art.
    STORY_WORLD_MAP = "scene/01_山门神殿_优化版.glb"
    STORY_WORLD_MAP_SPAWN_SITES = (
        ("player", 0, 0), ("boss", 0, 12), ("merchant", -30, -15), ("prophet", 30, -15),
    )

    def _map_placement(self) -> dict:
        """The authoritative `map` block of game/data/prophet.json."""
        return json.loads((ROOT / "game/data/prophet.json").read_text(encoding="utf-8"))["map"]

    @staticmethod
    def _glb_json(document: Path) -> tuple[dict, int]:
        """Return the JSON chunk and the byte offset of the BIN payload that follows it."""
        with document.open("rb") as stream:
            magic, version, total = struct.unpack("<4sII", stream.read(12))
            assert magic == b"glTF" and version == 2 and total == document.stat().st_size
            header = None
            while stream.tell() < total:
                length, kind = struct.unpack("<II", stream.read(8))
                if kind == 0x4E4F534A:
                    header = json.loads(stream.read(length).decode("utf-8"))
                    continue
                if kind == 0x004E4942 and header is not None:
                    return header, stream.tell()
                stream.seek(length, 1)
        raise AssertionError(f"{document} has no JSON chunk followed by a BIN chunk")

    @staticmethod
    def _mat4_multiply(lhs: list[float], rhs: list[float]) -> list[float]:
        """Column-major 4x4 product, matching glTF's matrix layout."""
        return [sum(lhs[k * 4 + row] * rhs[column * 4 + k] for k in range(4))
                for column in range(4) for row in range(4)]

    @classmethod
    def _node_matrices(cls, header: dict) -> dict[int, list[float]]:
        """World matrix of every node that carries a mesh, as the engine sees it."""
        identity = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]
        nodes = header.get("nodes", [])
        local: dict[int, list[float]] = {}
        for index, node in enumerate(nodes):
            if "matrix" in node:
                raw = node["matrix"]
                local[index] = [raw[column * 4 + row] for column in range(4) for row in range(4)]
                continue
            tx, ty, tz = node.get("translation", [0.0, 0.0, 0.0])
            qx, qy, qz, qw = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
            sx, sy, sz = node.get("scale", [1.0, 1.0, 1.0])
            rotation = [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy + qz * qw), 2 * (qx * qz - qy * qw), 0,
                        2 * (qx * qy - qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz + qx * qw), 0,
                        2 * (qx * qz + qy * qw), 2 * (qy * qz - qx * qw), 1 - 2 * (qx * qx + qy * qy), 0,
                        0, 0, 0, 1]
            # rotation is column-major: column c owns axis c, so scale column c by s[c].
            scales = (sx, sy, sz)
            column = [rotation[column_index * 4 + row] * (scales[column_index] if row < 3 and column_index < 3 else 1.0)
                      for column_index in range(4) for row in range(4)]
            column[12], column[13], column[14] = tx, ty, tz
            local[index] = column

        world: dict[int, list[float]] = {}
        scene = header.get("scenes", [{}])[header.get("scene", 0)]
        stack = [(index, identity) for index in scene.get("nodes", [])]
        while stack:
            index, parent = stack.pop()
            matrix = cls._mat4_multiply(parent, local[index])
            if "mesh" in nodes[index]:
                world[index] = matrix
            stack.extend((child, matrix) for child in nodes[index].get("children", []))
        return world

    @classmethod
    def _map_world_points(cls, document: Path) -> list[tuple[float, float, float]]:
        """Every vertex of the map in world space, through its full node hierarchy.

        The engine builds each static instance transform from the accumulated node
        matrix, so this is the geometry the collision mesh is actually built from.
        """
        header, binary = cls._glb_json(document)
        matrices = cls._node_matrices(header)
        mesh_matrices: dict[int, list[float]] = {}
        for index, node in enumerate(header.get("nodes", [])):
            if "mesh" in node and index in matrices:
                mesh_matrices[node["mesh"]] = matrices[index]
        points: list[tuple[float, float, float]] = []
        with document.open("rb") as stream:
            for mesh_index, mesh in enumerate(header.get("meshes", [])):
                matrix = mesh_matrices.get(mesh_index)
                for primitive in mesh.get("primitives", []):
                    accessor = header["accessors"][primitive["attributes"]["POSITION"]]
                    view = header["bufferViews"][accessor["bufferView"]]
                    stride = view.get("byteStride") or 12
                    start = binary + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                    stream.seek(start)
                    payload = stream.read((accessor["count"] - 1) * stride + 12)
                    for offset in range(0, len(payload), stride):
                        x, y, z = struct.unpack_from("<3f", payload, offset)
                        if matrix is None:
                            points.append((x, y, z))
                            continue
                        points.append(tuple(
                            matrix[0 * 4 + row] * x + matrix[4 + row] * y
                            + matrix[8 + row] * z + matrix[12 + row]
                            for row in range(3)))
        return points

    def test_story_world_map_measurements_match_what_the_runtime_places(self):
        """The map ships with the world, so its size and the line it is aligned to are facts
        the placement writes down: re-derive both from the shipped model here.

        The placement is `game/frontend/storyMap.mjs`, whose two measurements are the two
        numbers in the `map` block of `game/data/prophet.json`; this is what stops either
        side from drifting away from the model that is actually deployed.
        """
        placement = self._map_placement()
        document = ART / self.STORY_WORLD_MAP
        self.assertTrue(document.is_file(), str(document))
        copied = ART.parents[2] / "assets/model" / document.name
        self.assertTrue(copied.is_file(), str(copied))
        with document.open("rb") as current, copied.open("rb") as source:
            self.assertEqual(hashlib.file_digest(current, "sha256").digest(),
                             hashlib.file_digest(source, "sha256").digest())

        # The engine normalises every static model into a unit cube, so `geometry.scale`
        # must equal the model's largest world extent in metres for it to appear life-size.
        points = self._map_world_points(document)
        self.assertTrue(points, "the shipped map has no geometry")
        extent = [max(point[axis] for point in points) - min(point[axis] for point in points)
                  for axis in range(3)]
        self.assertAlmostEqual(max(extent), placement["scale"], delta=0.05)

        # The engine floor is y = 0 and the story puts character feet there. Two facts have to
        # hold: the courtyard really is `courtyardY` metres up in the model file, and the
        # position the runtime sends puts it exactly on y = 0. The engine moves the model's
        # AABB centre to the origin and scales the largest axis to 1, so the courtyard's
        # normalised height is `(courtyardY - centre_y) * scale_factor`, and `position` is in
        # that normalised frame — not in metres.
        low = [min(point[axis] for point in points) for axis in range(3)]
        high = [max(point[axis] for point in points) for axis in range(3)]
        centre_y = (low[1] + high[1]) / 2
        surface_y = min(point[1] for point in points if abs(point[0]) <= 3 and abs(point[2]) <= 3)
        self.assertAlmostEqual(surface_y, placement["courtyardY"], delta=0.05,
                               msg="courtyardY 必须是可行走庭院在模型文件里的高度")
        scale_factor = 1 / placement["scale"]
        position_y = 0.5 - placement["courtyardY"] / placement["scale"]
        self.assertAlmostEqual(position_y + (surface_y - centre_y) * scale_factor, 0.0, delta=0.05,
                               msg="摆位必须把可行走庭院压到引擎地面 y = 0")
        # `scale / 2` here would be a 209-metre error: position lives in the normalised frame.
        self.assertLess(abs(position_y), 0.01, "position.y 必须是归一化后的量级")

        for role, x, z in self.STORY_WORLD_MAP_SPAWN_SITES:
            with self.subTest(role=role):
                footprint = [point[1] for point in points
                             if abs(point[0] - x) <= 3 and abs(point[2] - z) <= 3]
                self.assertTrue(footprint, f"{role} spawn has no surface beneath it")
                self.assertLessEqual(min(footprint), surface_y + 0.2,
                                     f"{role} spawn floats above the map")
                self.assertGreaterEqual(min(footprint), surface_y - 1.5,
                                        f"{role} spawn sinks into the map")

    def test_the_map_actor_is_static_so_the_surface_is_solid(self):
        """`phantom` would let characters walk straight through the map.

        The map is created by the page on every entry (`game/frontend/storyMap.mjs`), not
        seeded into new worlds by native creation code, so that is where the body type lives.
        """
        source = (ROOT / "game/frontend/storyMap.mjs").read_text(encoding="utf-8")
        self.assertIn("body_type: 'static'", source)
        self.assertNotIn("'phantom'", source)
        self.assertNotIn('"phantom"', source)
        # The map must arrive with the world the player enters, not only with a new world.
        page = (ROOT / "editor/Frontend/src/views/layout/StoryWorld.vue").read_text(encoding="utf-8")
        self.assertIn("import { ensureStoryMap } from '../../../../../game/frontend/storyMap.mjs';", page)
        self.assertIn("await ensureStoryMap({", page)

    def test_models_and_supplied_sidecars_are_unchanged_copies_of_engine_assets(self):
        for role, source_root in self.ART_SOURCES.items():
            copied = [path for path in (ART / role).rglob("*") if path.is_file()]
            self.assertTrue(copied, role)
            if role in self.CHARACTER_ART_ROLES:
                self.assertEqual(len([path for path in copied if path.suffix == ".dae"]), 1, role)
            for path in copied:
                with self.subTest(file=str(path.relative_to(ART))):
                    original = source_root / path.relative_to(ART / role)
                    self.assertTrue(original.is_file(), str(original))
                    with path.open("rb") as current, original.open("rb") as source:
                        self.assertEqual(hashlib.file_digest(current, "sha256").digest(),
                                         hashlib.file_digest(source, "sha256").digest())
        # Every folder must be registered above, so a new one cannot quietly opt out.
        self.assertEqual({folder.name for folder in ART.iterdir() if folder.is_dir()},
                         set(self.ART_SOURCES))

    def test_cube_placement_and_fragment_catalogue_match_their_data_files(self):
        """The JSON is authoritative; the runtime projections must mirror it exactly."""
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to read the runtime projections")
        result = subprocess.run([node, "--input-type=module", "-e",
            "import {CUBE_PLACEMENT} from './game/frontend/storyCube.mjs'; "
            "import {MAP_PLACEMENT, mapOriginTransform} from './game/frontend/storyMap.mjs'; "
            "import {FRAGMENTS, WORLD_RULE_VERSION} from './game/frontend/storyWorldRules.mjs'; "
            "console.log(JSON.stringify({cube: CUBE_PLACEMENT, map: MAP_PLACEMENT, "
            "mapTransform: mapOriginTransform(), fragments: FRAGMENTS, "
            "ruleVersion: WORLD_RULE_VERSION}));"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=15)
        projection = json.loads(result.stdout)

        cube = json.loads((ROOT / "game/data/prophet.json").read_text(encoding="utf-8"))["cube"]
        for key, value in projection["cube"].items():
            self.assertIn(key, cube, key)
            self.assertEqual(value, cube[key], key)

        # The map is declared exactly like the cube, so it is mirrored the same way: every
        # field of the projection must exist in the data file with the same value.
        story_map = self._map_placement()
        self.assertEqual(projection["map"], {key: story_map[key] for key in projection["map"]},
                         "storyMap.mjs 的 MAP_PLACEMENT 必须逐字段等于 prophet.json 的 map 块")
        for key in ("asset", "guid", "modelRef", "scale", "courtyardY"):
            self.assertIn(key, story_map, key)
        # The transform the page sends is derived from those two numbers, never a third copy.
        transform = projection["mapTransform"]
        expected_y = 0.5 - story_map["courtyardY"] / story_map["scale"]
        self.assertAlmostEqual(transform["position"][1], expected_y, places=6)
        self.assertEqual(transform["position"][0], 0)
        self.assertEqual(transform["position"][2], 0)
        self.assertEqual(transform["scale"], [story_map["scale"]] * 3)
        self.assertEqual(transform["rotation"], [0, 0, 0])
        # ≈ 0.002: the courtyard sits 209.14 m below the model's AABB centre, and the engine
        # divides that back out by `scale` because `position` is in the normalised frame.
        # `scale / 2 - courtyardY` would be ~420 × too large and float the map in the air.
        self.assertAlmostEqual(expected_y, 0.0020485, places=6)
        self.assertLess(abs(expected_y), 0.01)

        catalogue = json.loads((ROOT / "game/data/fragments.json").read_text(encoding="utf-8"))
        self.assertEqual(projection["ruleVersion"], catalogue["version"])
        self.assertEqual(len(projection["fragments"]), len(catalogue["fragments"]))
        for projected, declared in zip(projection["fragments"], catalogue["fragments"]):
            for key in ("id", "name", "initial", "description", "rule"):
                self.assertEqual(projected[key], declared[key], f'{declared["id"]}.{key}')
        # The requirement's initial fragment must be the left/right sway, excluding the player.
        # `spin` (the z rotation) is initial too: no reward path exists yet that could grant a
        # fragment later, so it has to be owned from the start to be installable at all.
        self.assertEqual([f["id"] for f in catalogue["fragments"] if f["initial"]], ["sway", "spin"])
        rule = catalogue["fragments"][0]["rule"]
        self.assertEqual(rule["type"], "sway")
        self.assertEqual(rule["axis"], "x")
        self.assertIn("player", rule["excludeRoles"])
        self.assertGreater(rule["amplitude"], 0)
        self.assertGreater(rule["periodMs"], 0)
        # The second fragment turns objects around z, in degrees, and excludes the player too.
        spin = catalogue["fragments"][1]["rule"]
        self.assertEqual(spin["type"], "spin")
        self.assertEqual(spin["axis"], "z")
        self.assertIn("player", spin["excludeRoles"])
        self.assertGreater(spin["amplitude"], 0)
        self.assertLessEqual(spin["amplitude"], 100.0)
        self.assertGreater(spin["periodMs"], 0)

    def test_frontend_deployment_contains_every_module_and_cleans_stale_modules(self):
        spec = importlib.util.spec_from_file_location("story_asset_deployment", ROOT / "tools/build/editor_copy_and_build.py")
        deployment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deployment)
        with tempfile.TemporaryDirectory(prefix="story assets ") as temporary:
            root = Path(temporary)
            stale = root / "game/frontend/stale.mjs"
            stale.parent.mkdir(parents=True)
            stale.write_text("obsolete", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                deployment.copy_game_frontend(root / "CabbageEditor", ROOT)
            self.assertFalse(stale.exists())
            for source in (ROOT / "game/frontend").glob("*.mjs"):
                self.assertEqual(source.read_bytes(), (root / "game/frontend" / source.name).read_bytes())
            self.assertFalse((root / "game/tests").exists())


    def test_art_deployment_preserves_models_textures_and_attribution(self):
        spec = importlib.util.spec_from_file_location("story_art_deployment", ROOT / "tools/build/editor_copy_and_build.py")
        deployment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deployment)
        with tempfile.TemporaryDirectory(prefix="剧情美术 assets ") as temporary:
            root = Path(temporary)
            dest = root / "CabbageEditor"
            with contextlib.redirect_stdout(io.StringIO()):
                deployment.copy_game_art(dest, ROOT)
                deployment.copy_game_art(dest, ROOT)  # Incremental deployment is repeatable.
            expected = {p.relative_to(ROOT / "game/art") for p in (ROOT / "game/art").rglob("*") if p.is_file()}
            actual = {p.relative_to(root / "game/art") for p in (root / "game/art").rglob("*") if p.is_file()}
            self.assertEqual(actual, expected)
            for relative in expected:
                self.assertEqual((ROOT / "game/art" / relative).read_bytes(),
                                 (root / "game/art" / relative).read_bytes(), str(relative))
            self.assertFalse((root / "assets").exists())
            self.assertFalse((root / "game/tests").exists())
            with self.assertRaises(FileNotFoundError):
                deployment.copy_game_art(dest, root / "missing repository")
            with mock.patch.object(deployment.shutil, "copytree", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"), contextlib.redirect_stdout(io.StringIO()):
                    deployment.copy_game_art(dest, ROOT)


    def _prophet_data(self) -> dict:
        return json.loads((ROOT / "game/data/prophet.json").read_text(encoding="utf-8"))

    def _prophet_projection(self) -> dict:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to read the story dialogue projection")
        result = subprocess.run([node, "--input-type=module", "-e",
            "import {PROPHET_SCRIPT, PROPHET_PLACEMENT, describeProphetContract} "
            "from './game/frontend/storyDialogue.mjs'; "
            "console.log(JSON.stringify({script: PROPHET_SCRIPT, placement: PROPHET_PLACEMENT, "
            "contract: describeProphetContract()}));"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=15)
        return json.loads(result.stdout)

    def test_prophet_content_is_shared_between_the_data_file_and_the_runtime_projection(self):
        """game/data/prophet.json is authoritative; storyDialogue.mjs must mirror it exactly."""
        projection = self._prophet_projection()
        data = self._prophet_data()

        script, projected = data["script"], projection["script"]
        self.assertEqual(projected["lines"], script["lines"])
        self.assertEqual(projected["fragments"], script["fragments"])
        for key in ("id", "name", "title", "hint", "closing"):
            self.assertEqual(projected[key], script[key], key)
        # `lines` is the panel's wire format; `fragments` is the authoritative per-beat form.
        # Keeping them equal here is what makes a script rewrite a pure data edit.
        self.assertEqual(script["lines"], [fragment["text"] for fragment in script["fragments"]])
        self.assertEqual(len({fragment["id"] for fragment in script["fragments"]}),
                         len(script["fragments"]))
        self.assertTrue(all(fragment["id"] for fragment in script["fragments"]))

        # Every parameter the placer reads must come from here, not a second copy in code.
        placement = data["placement"]
        for key in ("model", "asset", "aheadDistance", "height", "yawOffset", "rotationPolicy"):
            self.assertEqual(projection["placement"][key], placement[key], key)

        contract, interaction = data["contract"], data["contract"]["interaction"]
        summary = projection["contract"]
        self.assertEqual(summary["version"], contract["version"])
        self.assertEqual(summary["worlds"], contract["worlds"])
        for key in ("key", "range", "prompt", "closeKey", "advanceKeys"):
            self.assertEqual(summary[key], interaction[key], key)
        self.assertEqual(summary["fragmentIds"], [f["id"] for f in script["fragments"]])
        self.assertEqual(summary["lineCount"], len(script["lines"]))

    def test_prophet_placement_matches_the_character_table(self):
        """storyCharacters.mjs must read the model and height the data file declares."""
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required to read the shared character configuration")
        result = subprocess.run([node, "--input-type=module", "-e",
            "import {STORY_CHARACTERS} from './game/frontend/storyCharacters.mjs'; "
            "console.log(JSON.stringify(STORY_CHARACTERS));"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", check=True, timeout=15)
        prophet = next(c for c in json.loads(result.stdout) if c["role"] == "prophet")
        placement = self._prophet_data()["placement"]
        self.assertEqual(prophet["asset"], placement["asset"])
        self.assertEqual(prophet["height"], placement["height"])

    def test_game_data_deployment_carries_the_story_content(self):
        spec = importlib.util.spec_from_file_location("story_data_deployment", ROOT / "tools/build/editor_copy_and_build.py")
        deployment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(deployment)
        with tempfile.TemporaryDirectory(prefix="story data ") as temporary:
            root = Path(temporary)
            dest = root / "CabbageEditor"
            with contextlib.redirect_stdout(io.StringIO()):
                deployment.copy_game_data(dest, ROOT)
                deployment.copy_game_data(dest, ROOT)  # Incremental deployment is repeatable.
            expected = {path.relative_to(ROOT / "game/data")
                        for path in (ROOT / "game/data").rglob("*") if path.is_file()}
            actual = {path.relative_to(root / "game/data")
                      for path in (root / "game/data").rglob("*") if path.is_file()}
            self.assertEqual(actual, expected)
            self.assertIn(Path("prophet.json"), expected)
            for relative in expected:
                self.assertEqual((ROOT / "game/data" / relative).read_bytes(),
                                 (root / "game/data" / relative).read_bytes(), str(relative))
            with self.assertRaises(FileNotFoundError):
                deployment.copy_game_data(dest, root / "missing repository")


if __name__ == "__main__":
    unittest.main()
