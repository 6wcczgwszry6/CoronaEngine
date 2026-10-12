"""World rules installed into a small world: validation, atomic write, and safe reads."""
import json
from pathlib import Path
import tempfile
import unittest

from game.runtime import world_rules


def sway_rule(**overrides):
    rule = {'fragmentId': 'sway', 'type': 'sway', 'axis': 'x', 'amplitude': 0.25, 'periodMs': 2400}
    rule.update(overrides)
    return rule


def spin_rule(**overrides):
    """A rotation rule: the amplitude is degrees, the axis is always z."""
    rule = {'fragmentId': 'spin', 'type': 'spin', 'axis': 'z', 'amplitude': 15.0, 'periodMs': 3600}
    rule.update(overrides)
    return rule


class WorldRuleValidationTests(unittest.TestCase):
    def test_initial_state_is_an_empty_versioned_rule_set(self):
        self.assertEqual(world_rules.initial_state(), {'version': 1, 'rules': []})

    def test_a_good_rule_is_kept_field_for_field(self):
        self.assertEqual(world_rules.validate_rule(sway_rule()), sway_rule())
        # Both rule types are accepted, and a spin keeps its degrees untouched.
        self.assertEqual(world_rules.validate_rule(spin_rule()), spin_rule())
        self.assertEqual(world_rules.validate_rule(spin_rule(amplitude=15))['amplitude'], 15)

    def test_the_axis_must_match_the_rule_type(self):
        # Mirrors _TYPE_AXES (world_rules.py:27): sway moves along any axis, spin only z.
        for axis in ('x', 'y', 'z'):
            self.assertEqual(world_rules.validate_rule(sway_rule(axis=axis))['axis'], axis)
        self.assertEqual(world_rules.validate_rule(spin_rule(axis='z'))['axis'], 'z')
        for case in [spin_rule(axis='x'), spin_rule(axis='y'), spin_rule(axis='w')]:
            with self.subTest(case=case):
                with self.assertRaises(world_rules.WorldRuleError):
                    world_rules.validate_rule(case)

    def test_malformed_rules_are_rejected_rather_than_clamped(self):
        cases = [
            None, [], 'sway',
            sway_rule(fragmentId=''), sway_rule(fragmentId='x' * 65), sway_rule(fragmentId=7),
            sway_rule(type='orbit'), sway_rule(type=None), sway_rule(type=7),
            spin_rule(type='orbit'), spin_rule(type=None),
            sway_rule(axis='w'), sway_rule(axis='X'), spin_rule(axis='w'), spin_rule(axis='X'),
            sway_rule(amplitude=0), sway_rule(amplitude=-0.25), sway_rule(amplitude=float('nan')),
            sway_rule(amplitude=float('inf')), sway_rule(amplitude='0.25'), sway_rule(amplitude=True),
            sway_rule(amplitude=1e6),
            spin_rule(amplitude=0), spin_rule(amplitude=-15), spin_rule(amplitude='15'),
            spin_rule(amplitude=True), spin_rule(amplitude=100.1),
            sway_rule(periodMs=0), sway_rule(periodMs=-2400), sway_rule(periodMs='2400'),
            sway_rule(periodMs=10 ** 9),
            spin_rule(periodMs=0), spin_rule(periodMs=-3600), spin_rule(periodMs='3600'),
            spin_rule(periodMs=10 ** 9),
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(world_rules.WorldRuleError):
                    world_rules.validate_rule(case)

    def test_state_requires_the_supported_version_and_unique_fragments(self):
        self.assertEqual(world_rules.validate_state({'version': 1, 'rules': [sway_rule()]}),
                         {'version': 1, 'rules': [sway_rule()]})
        # A world may carry both rules at once, each on its own fragment.
        self.assertEqual(world_rules.validate_state({'version': 1, 'rules': [sway_rule(), spin_rule()]}),
                         {'version': 1, 'rules': [sway_rule(), spin_rule()]})
        for case in [None, [], {}, {'version': 2, 'rules': []}, {'version': 1},
                     {'version': 1, 'rules': {}}, {'version': 1, 'rules': [sway_rule()] * 2},
                     {'version': 1, 'rules': [spin_rule(), spin_rule()]},
                     {'version': 1, 'rules': [sway_rule(), spin_rule(axis='x')]},
                     {'version': 1, 'rules': [sway_rule()] * (world_rules.MAX_RULES + 1)}]:
            with self.subTest(case=case):
                with self.assertRaises(world_rules.WorldRuleError):
                    world_rules.validate_state(case)
        # The bounds are inclusive, exactly as _positive() says: the limit itself is legal
        # and the mirrored frontend bounds must reach it and not one step further.
        self.assertEqual(world_rules.validate_rule(spin_rule(amplitude=100.0))['amplitude'], 100.0)
        self.assertEqual(world_rules.validate_rule(spin_rule(periodMs=600_000))['periodMs'], 600_000)
        with self.assertRaises(world_rules.WorldRuleError):
            world_rules.validate_rule(spin_rule(amplitude=100.0 + 1e-9))
        with self.assertRaises(world_rules.WorldRuleError):
            world_rules.validate_rule(spin_rule(periodMs=600_000 + 1))


class WorldRuleStorageTests(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory(prefix='world rules ')
        self.root = Path(self._temporary.name)

    def tearDown(self):
        self._temporary.cleanup()

    def save_path(self):
        return self.root / world_rules.SAVE_PATH

    def test_a_world_without_the_file_has_no_rules(self):
        self.assertEqual(world_rules.load(self.root), world_rules.initial_state())
        self.assertFalse(self.save_path().exists())

    def test_save_then_load_round_trips_and_creates_the_game_folder(self):
        world_rules.save(self.root, [sway_rule()])
        self.assertTrue(self.save_path().is_file())
        self.assertTrue((self.root / '.game').is_dir())
        self.assertEqual(world_rules.load(self.root), {'version': 1, 'rules': [sway_rule()]})
        written = json.loads(self.save_path().read_text(encoding='utf-8'))
        self.assertEqual(written, {'version': 1, 'rules': [sway_rule()]})

    def test_saved_rules_keep_chinese_readable(self):
        world_rules.save(self.root, [sway_rule(fragmentId='浮动')])
        self.assertIn('浮动', self.save_path().read_text(encoding='utf-8'))
        self.assertEqual(world_rules.load(self.root)['rules'][0]['fragmentId'], '浮动')

    def test_a_world_may_keep_a_sway_and_a_spin_at_the_same_time(self):
        world_rules.save(self.root, [sway_rule(), spin_rule()])
        self.assertEqual(world_rules.load(self.root),
                         {'version': 1, 'rules': [sway_rule(), spin_rule()]})
        written = json.loads(self.save_path().read_text(encoding='utf-8'))
        self.assertEqual([rule['type'] for rule in written['rules']], ['sway', 'spin'])
        self.assertEqual([rule['axis'] for rule in written['rules']], ['x', 'z'])
        # A spin with a non-z axis is refused by the same path that refuses a bad sway.
        for bad in [[spin_rule(axis='x')], [sway_rule(), spin_rule(axis='y')],
                    [spin_rule(amplitude=0)]]:
            with self.subTest(bad=bad):
                with self.assertRaises(world_rules.WorldRuleError):
                    world_rules.save(self.root, bad)
        self.assertEqual(world_rules.load(self.root)['rules'], [sway_rule(), spin_rule()],
                         '被拒绝的保存不会覆盖盘上已有的好规则')

    def test_save_refuses_invalid_input_so_garbage_never_reaches_the_disk(self):
        for bad in [[sway_rule(axis='w')], [sway_rule()] * 2, 'nope', [sway_rule(amplitude=0)]]:
            with self.subTest(bad=bad):
                with self.assertRaises(world_rules.WorldRuleError):
                    world_rules.save(self.root, bad)
        self.assertFalse(self.save_path().exists())

    def test_clear_leaves_an_empty_rule_set(self):
        world_rules.save(self.root, [sway_rule()])
        self.assertEqual(world_rules.clear(self.root), world_rules.initial_state())
        self.assertEqual(world_rules.load(self.root), world_rules.initial_state())

    def test_a_corrupt_file_is_reported_and_never_overwritten(self):
        self.save_path().parent.mkdir(parents=True, exist_ok=True)
        self.save_path().write_text('{ not json', encoding='utf-8')
        with self.assertRaises(world_rules.WorldRuleError) as raised:
            world_rules.load(self.root)
        self.assertIn('未覆盖原文件', str(raised.exception))
        self.assertEqual(self.save_path().read_text(encoding='utf-8'), '{ not json')

    def test_an_oversized_file_is_refused(self):
        self.save_path().parent.mkdir(parents=True, exist_ok=True)
        self.save_path().write_text('x' * (world_rules.MAX_BYTES + 1), encoding='utf-8')
        with self.assertRaises(world_rules.WorldRuleError):
            world_rules.load(self.root)

    def test_a_failed_write_leaves_no_temporary_file_behind(self):
        world_rules.save(self.root, [sway_rule()])
        leftovers = [path.name for path in (self.root / '.game').iterdir()
                     if path.name != 'story-world-rules.json']
        self.assertEqual(leftovers, [], leftovers)


if __name__ == '__main__':
    unittest.main()
