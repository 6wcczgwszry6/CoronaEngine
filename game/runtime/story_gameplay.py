"""Small, durable story combat adapter over the existing Scratch string bridge."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import random
import tempfile
import threading
import uuid

from .subworlds import _exclusive, _plain, _relation, _require_story
from .story_navigation import _unwrap
from . import placements
from . import world_rules
from . import subworld_roster as roster

REQUEST_KEY = '__corona_story_gameplay_v1__'
SAVE_PATH = Path('.game/story-gameplay.json')
PLACEMENT_ACTIONS = ('loadPlacements', 'savePlacements', 'clearPlacements')
WORLD_RULE_ACTIONS = ('loadWorldRules', 'saveWorldRules', 'clearWorldRules')
ROSTER_ACTIONS = ('loadSubworlds', 'addSubworld', 'renameSubworld')
# Only ever read back from saves made before the boss reward became immediate; no new
# state or operation writes it.
DROP_ID = 'story.boss.world-fragment'
# The main world's non-boss creatures. Each has its own health pool so the page can show a
# bar per creature and the player can hunt them separately from the boss. Keys are the
# `role` values from `game/frontend/storyCharacters.mjs`; the names stay in the frontend.
MONSTER_HP = {
    'monster-em135': 180,
    'monster-em001-a': 120,
    'monster-em001-b': 120,
    'monster-em001-c': 120,
    'monster-em3': 160,
    'monster-em1': 80,
    'monster-em2': 90,
}
# Placeable models a monster may leave behind. The counter name is the prop id.
LOOT_PROPS = ('block', 'ball')
# Equipment a monster may leave behind, independently of the model roll. These ids must
# match `game/frontend/storyLoot.mjs`; the names and icons stay in the frontend.
MONSTER_EQUIPMENT = ('hunter-blade', 'hunter-helm', 'hunter-chest', 'hunter-boots')
CONFIG = {
    'playerHp': 100, 'rageMax': 100, 'ragePerHit': 10, 'bossHp': 200, 'damage': 20,
    'cooldownMs': 400, 'bossBarRadius': 10, 'monsterBarRadius': 10, 'meleeRange': 2.5,
    'meleeHalfAngle': math.pi / 3, 'monsterDropChance': 0.7,
    'monsterEquipmentChance': 0.5,
    'monsters': {role: {'hp': hp} for role, hp in MONSTER_HP.items()},
    'skills': {
        'heavy': {'name': '重斩', 'key': 'E', 'damage': 50, 'rageCost': 30,
                  'range': 2.5, 'halfAngle': math.pi / 3, 'cooldownMs': 1200},
        'sweep': {'name': '横扫', 'key': 'R', 'damage': 80, 'rageCost': 50,
                  'range': 3.5, 'halfAngle': math.pi, 'cooldownMs': 3000},
    },
}
_lock = threading.RLock()


# The boss hands the player a stack of blocks for the small world when it dies. The stack
# is a reward, not a starting item: the bag is empty of blocks until the fight is won.
BLOCK_REWARD = 64
# Backwards-compatible name for saves and tests written before the reward moved to the kill.
BLOCK_SEED = BLOCK_REWARD


def initial_inventory():
    return {'worldFragment': 0, 'block': 0, 'ball': 0,
            **{item: 0 for item in MONSTER_EQUIPMENT}}


def initial_monsters():
    return {role: {'hp': stats['hp']} for role, stats in CONFIG['monsters'].items()}


def initial_state():
    return {'version': 2, 'revision': 0, 'legacyRevision': 0, 'rage': 0, 'boss': {'hp': CONFIG['bossHp']},
            'drop': None, 'monsters': initial_monsters(),
            'inventory': initial_inventory(), 'operations': []}


def _vector(value):
    return (isinstance(value, list) and len(value) == 3
            and all(type(n) in (int, float) and math.isfinite(n) and abs(n) < 1e7 for n in value))


def _validate_v1(state):
    """Reject broken saves instead of resetting a previously earned reward."""
    if not isinstance(state, dict) or state.get('version') != 1:
        raise ValueError('不支持的玩法存档版本')
    hp = state['boss']['hp']
    count = state['inventory']['worldFragment']
    revision = state['revision']
    operations = state['operations']
    if (type(hp) is not int or not 0 <= hp <= CONFIG['bossHp'] or hp % CONFIG['damage']
            or type(count) is not int or count not in (0, 1)
            or type(revision) is not int or revision != (CONFIG['bossHp'] - hp) // CONFIG['damage'] + count
            or not isinstance(operations, list) or len(operations) != revision):
        raise ValueError('玩法状态或存档版本号无效')
    seen = set()
    for i, operation in enumerate(operations):
        if (not isinstance(operation, dict) or operation.get('expectedRevision') != i
                or operation.get('action') != ('hitBoss' if i < CONFIG['bossHp'] // CONFIG['damage'] else 'pickupDrop')):
            raise ValueError('玩法操作记录无效')
        ident = operation['operationId']
        if str(uuid.UUID(ident)) != ident or ident in seen:
            raise ValueError('玩法操作标识无效')
        seen.add(ident)
    drop = state['drop']
    if hp > 0:
        if drop is not None or count:
            raise ValueError('Boss 存活时不能存在奖励')
    elif (not isinstance(drop, dict) or drop.get('id') != DROP_ID
          or not _vector(drop.get('position')) or type(drop.get('collected')) is not bool
          or drop['collected'] != bool(count)):
        raise ValueError('世界碎片状态无效')
    return state


def _operation(request, *, stored=False):
    """Canonical durable command; clients never choose damage or resource costs.

    `stored=True` reads a command that is already in the save's operation log. The only
    difference is the server-decided `loot` field: a fresh request must never be able to
    choose its own drop, but replaying a stored kill has to reproduce the same item.
    """
    action = request.get('action')
    if action not in ('hitBoss', 'hitMonster', 'castSkill', 'pickupDrop'):
        raise ValueError('未知玩法操作')
    ident, revision = request.get('operationId'), request.get('expectedRevision')
    if not isinstance(ident, str) or str(uuid.UUID(ident)) != ident:
        raise ValueError('无效的玩法操作 ID')
    if type(revision) is not int or revision < 0:
        raise ValueError('无效的玩法存档版本号')
    operation = {'operationId': ident, 'action': action, 'expectedRevision': revision}
    if action == 'hitMonster' and request.get('monsterId') not in CONFIG['monsters']:
        raise ValueError('未知的怪物')
    if action == 'castSkill':
        if request.get('skillId') not in CONFIG['skills'] or type(request.get('hit')) is not bool:
            raise ValueError('无效的技能或命中结果')
        operation.update(skillId=request['skillId'], hit=request['hit'])
    # The boss position used to decide where the red ball landed. New commands never
    # carry it (the reward is immediate), but old operation logs still do, so a valid
    # legacy field is preserved verbatim instead of being rejected.
    if action == 'hitBoss' or (action == 'castSkill' and operation['hit']):
        position = request.get('bossPosition')
        if position is not None:
            if not _vector(position):
                raise ValueError('Boss 掉落位置无效')
            operation['bossPosition'] = position
    if action in ('hitMonster', 'castSkill') and request.get('monsterId') is not None:
        if request.get('monsterId') not in CONFIG['monsters']:
            raise ValueError('未知的怪物')
        operation['monsterId'] = request['monsterId']
    if action == 'pickupDrop':
        if request.get('dropId') != DROP_ID:
            raise ValueError('未知的世界碎片')
        operation['dropId'] = DROP_ID
    if stored and 'loot' in request:
        loot = request['loot']
        # `pillar` is the retired prop id; old logs keep it so replay is byte-identical,
        # while the live effect is mapped to the ball in `_drop_monster_loot`.
        if loot is not None and loot not in (*LOOT_PROPS, 'pillar'):
            raise ValueError('未知的掉落物')
        operation['loot'] = loot
    if stored and 'gear' in request:
        gear = request['gear']
        if gear is not None and gear not in MONSTER_EQUIPMENT:
            raise ValueError('未知的装备掉落')
        operation['gear'] = gear
    return operation


def _drop_monster_loot(state, operation, *, live):
    """Roll a monster's drops once, then store the outcome in the operation.

    A live kill rolls twice, independently: a 70% chance for a placeable model and a 50%
    chance for equipment. Replaying a stored operation must not roll again, which is why
    both outcomes are written into the operation itself. They are only accepted from the
    save log, never from a fresh client request.
    """
    if live:
        loot = random.choice(LOOT_PROPS) if random.random() < CONFIG['monsterDropChance'] else None
        gear = (random.choice(MONSTER_EQUIPMENT)
                if random.random() < CONFIG['monsterEquipmentChance'] else None)
        operation['loot'] = loot
        operation['gear'] = gear
    else:
        # Operations saved before equipment drops have no `gear` key; they must not roll
        # equipment retroactively when the save is replayed.
        loot = operation.get('loot') if 'loot' in operation else None
        gear = operation.get('gear') if 'gear' in operation else None
    # The retired pillar prop becomes the ball; old operations keep their original id in
    # the log, but the inventory counter and the bag only know about balls.
    if loot == 'pillar':
        loot = 'ball'
    if loot is not None:
        state['inventory'][loot] = state['inventory'].get(loot, 0) + 1
    if gear is not None:
        state['inventory'][gear] = state['inventory'].get(gear, 0) + 1


def _damage_monster(state, monster_id, damage, operation, *, live):
    monster = state['monsters'].get(monster_id)
    if not isinstance(monster, dict):
        raise ValueError('未知的怪物')
    if monster['hp'] <= 0:
        raise ValueError('怪物已死亡')
    monster['hp'] = max(0, monster['hp'] - damage)
    if monster['hp'] == 0:
        _drop_monster_loot(state, operation, live=live)


def _apply(state, operation, *, legacy=False, live=False):
    action, damage, monster_id = operation['action'], 0, operation.get('monsterId')
    if action == 'hitBoss':
        if state['boss']['hp'] <= 0:
            raise ValueError('Boss 已死亡')
        damage = CONFIG['damage']
        if not legacy:
            state['rage'] = min(CONFIG['rageMax'], state['rage'] + CONFIG['ragePerHit'])
    elif action == 'hitMonster':
        if legacy:
            raise ValueError('旧版操作记录不能包含怪物攻击')
        damage = CONFIG['damage']
        state['rage'] = min(CONFIG['rageMax'], state['rage'] + CONFIG['ragePerHit'])
    elif action == 'castSkill':
        if legacy:
            raise ValueError('旧版操作记录不能包含技能')
        skill = CONFIG['skills'][operation['skillId']]
        if state['rage'] < skill['rageCost']:
            raise ValueError('怒气不足')
        if operation['hit']:
            if monster_id:
                if state['monsters'][monster_id]['hp'] <= 0:
                    raise ValueError('怪物已死亡，不能再次命中')
            elif state['boss']['hp'] <= 0:
                raise ValueError('Boss 已死亡，不能再次命中')
        state['rage'] -= skill['rageCost']
        damage = skill['damage'] if operation['hit'] else 0
    else:
        # Legacy command: older saves recorded the red ball as a separate pickup. The
        # boss now hands the fragment over the moment it dies, so replaying that old
        # pickup must be a no-op rather than a failure.
        if state['drop'] is None:
            if state['inventory']['worldFragment'] < 1:
                raise ValueError('世界碎片不可拾取')
            return
        if state['drop']['collected']:
            raise ValueError('世界碎片不可拾取')
        state['drop']['collected'] = True
        state['inventory']['worldFragment'] += 1
    if damage:
        if monster_id:
            _damage_monster(state, monster_id, damage, operation, live=live)
        else:
            state['boss']['hp'] = max(0, state['boss']['hp'] - damage)
            if state['boss']['hp'] == 0:
                # 小世界开启的凭证随 Boss 倒下直接进入背包：不再在世界里生成红球，
                # 也没有需要按 F 拾取的一步。同一击也把 64 个方块交给行囊，
                # 小世界物品栏从此有东西可放。
                state['inventory']['worldFragment'] = max(1, state['inventory']['worldFragment'])
                state['inventory']['block'] = state['inventory'].get('block', 0) + BLOCK_REWARD
                state['drop'] = None


def _validate(state):
    if not isinstance(state, dict) or type(state.get('version')) is not int:
        raise ValueError('不支持的玩法存档版本')
    if state['version'] == 1:
        _validate_v1(state)
        state = deepcopy(state)
        state.update(version=2, legacyRevision=state['revision'], rage=0)
    if state['version'] != 2:
        raise ValueError('不支持的玩法存档版本')
    revision, boundary, operations = state['revision'], state['legacyRevision'], state['operations']
    # A world saved before the block counter existed lacks it. Zero is the pre-kill default;
    # the normalization below gives the reward only to a save whose boss actually fell.
    # Loot counters and the monster roster are newer than the original save shape, so a
    # missing entry means "not earned yet" / "still alive at full health".
    if isinstance(state.get('inventory'), dict):
        # `pillar` was retired because it reused the block's cube model. Old saves keep
        # the count, but it is a ball now; replay maps the old operation loot the same way.
        legacy_pillar = state['inventory'].pop('pillar', 0)
        if type(legacy_pillar) is not int or legacy_pillar < 0:
            raise ValueError('玩法状态或存档版本号无效')
        for prop in (*LOOT_PROPS, *MONSTER_EQUIPMENT):
            state['inventory'].setdefault(prop, 0)
        state['inventory']['ball'] += legacy_pillar
    if not isinstance(state.get('monsters'), dict):
        state['monsters'] = initial_monsters()
    else:
        for role, stats in CONFIG['monsters'].items():
            state['monsters'].setdefault(role, {'hp': stats['hp']})
    if (type(revision) is not int or revision < 0 or type(boundary) is not int
            or not 0 <= boundary <= min(revision, 11) or not isinstance(operations, list)
            or len(operations) != revision or type(state['rage']) is not int
            or type(state['boss']['hp']) is not int
            or set(state['monsters']) != set(CONFIG['monsters'])
            or any(not isinstance(monster, dict) or type(monster.get('hp')) is not int
                   or not 0 <= monster['hp'] <= CONFIG['monsters'][role]['hp']
                   for role, monster in state['monsters'].items())
            or type(state['inventory'].get('worldFragment')) is not int
            or any(type(state['inventory'].get(prop)) is not int
                   for prop in (*LOOT_PROPS, *MONSTER_EQUIPMENT))):
        raise ValueError('玩法状态或存档版本号无效')
    replay, seen = initial_state(), set()
    for i, operation in enumerate(operations):
        if not isinstance(operation, dict) or _operation(operation, stored=True) != operation:
            raise ValueError('玩法操作记录无效')
        ident = operation['operationId']
        if ident in seen or operation['expectedRevision'] != i:
            raise ValueError('玩法操作记录无效')
        seen.add(ident)
        _apply(replay, operation, legacy=i < boundary)
    # Older saves still carry the red ball and the `pickupDrop` operation that claimed
    # it. Fold that record into the inventory before replaying, so a save made by the
    # previous flow opens with the small world already unlocked instead of losing the
    # reward. New states store `drop: None` and never reach this branch.
    drop = state.get('drop')
    if drop is not None:
        if (not isinstance(drop, dict) or drop.get('id') != DROP_ID
                or not _vector(drop.get('position')) or type(drop.get('collected')) is not bool):
            raise ValueError('世界碎片状态无效')
        state['drop'] = None
        if state['boss']['hp'] == 0:
            state['inventory']['worldFragment'] = max(1, state['inventory']['worldFragment'])
    # The boss stack is now part of the killing-blow reward, while monster loot adds to
    # the same counter. Old saves seeded 64 from the start, so rebuild the counter from
    # the two authoritative sources instead of trusting the stored number.
    block_loot = sum(1 for operation in operations if operation.get('loot') == 'block')
    state['inventory']['block'] = (0 if state['boss']['hp'] > 0 else BLOCK_REWARD) + block_loot
    for key in ('boss', 'drop', 'monsters', 'inventory', 'rage'):
        if replay[key] != state[key]:
            raise ValueError('玩法状态与操作记录不一致')
    if state['drop'] is not None:
        raise ValueError('世界碎片状态无效')
    return state


def _read(root):
    path = root / SAVE_PATH
    _plain(path)
    if not path.exists():
        return initial_state()
    try:
        if path.stat().st_size > 65536:
            raise ValueError('存档超过大小限制')
        return _validate(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise ValueError(f'玩法存档损坏，未覆盖原文件：{error}') from error


def _write(root, state, assert_source):
    folder = root / '.game'
    fd, temporary = tempfile.mkstemp(prefix='.story-gameplay-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        assert_source()
        _plain(root / SAVE_PATH)
        os.replace(temporary, root / SAVE_PATH)
    finally:
        Path(temporary).unlink(missing_ok=True)


def handle_placement_request(request, source, api):
    """Exhibits belong to the small world, so the main world reads an empty layout.

    A small world keeps its own arrangement, which is why the file lives beside the
    copied scene instead of in the main world.
    """
    action = request['action']

    def assert_source():
        active = _unwrap(api.project_settings.get_active_project_info())
        if (not isinstance(active, dict) or active.get('mode') != 'story'
                or not active.get('project_path')
                or Path(active['project_path']).resolve() != source):
            raise ValueError('当前世界已改变，已拒绝旧世界陈列请求')

    with _lock:
        assert_source()
        _require_story(source)
        role, target, _ = _relation(source)
        # The link owner keeps the metadata for both worlds, and its `.game` folder is
        # the only one the navigation lock guards. Storing a small world's layout
        # beside `story-link.json` therefore keeps reads and writes mutually exclusive
        # with the copy/restore transaction that owns that same folder.
        owner = target if role == 'child' else source

        def response(state, status='ok'):
            return {'status': status, 'role': role, 'state': state}

        if role != 'child':
            if action != 'loadPlacements':
                raise ValueError('只有小世界可以陈列主世界取得的物质')
            return response(placements.initial_state())
        with _exclusive(owner):
            assert_source()
            if action == 'loadPlacements':
                return response(placements.load(owner))
            if action == 'clearPlacements':
                return response(placements.clear(owner))
            listed = request.get('placements')
            if not isinstance(listed, list):
                raise ValueError('陈列列表无效')
            return response(placements.save(owner, listed))


def _roster_root(source):
    """The link owner keeps the roster beside the navigation metadata, exactly like
    the exhibition layout: a small world's roster and the main world's roster are
    the same document, so neither world can fork it into a divergent list."""
    role, target, _ = _relation(source)
    return target if role == 'child' else source


def handle_roster_request(request, source, api):
    """Small-world roster: read, add one entry, rename one entry. Written one
    operation at a time under the same lock as the navigation metadata so a copy/
    restore transaction can never observe a half-saved roster."""
    action = request['action']

    def assert_source():
        active = _unwrap(api.project_settings.get_active_project_info())
        if (not isinstance(active, dict) or active.get('mode') != 'story'
                or not active.get('project_path')
                or Path(active['project_path']).resolve() != source):
            raise ValueError('当前世界已改变，已拒绝旧世界名册请求')

    with _lock:
        assert_source()
        _require_story(source)
        owner = _roster_root(source)

        def response(state, status='ok'):
            return {'status': status, 'role': _relation(source)[0], 'state': state}

        with _exclusive(owner):
            assert_source()
            if action == 'loadSubworlds':
                return response(roster.load(owner))
            if action == 'addSubworld':
                return response(roster.add(owner))
            if action == 'renameSubworld':
                ident = request.get('subworldId')
                name = request.get('name')
                return response(roster.rename(owner, ident, name))
            raise ValueError('未知名册操作')


def handle_world_rule_request(request, source, api):
    """World rules belong to the small world whose prophet installed them.

    Ownership mirrors placements: the rule set is written beside the link owner's
    `story-link.json`, so writes stay mutually exclusive with the copy/restore
    transaction that owns that folder, and the main world only ever reads an empty set.
    """
    action = request['action']

    def assert_source():
        active = _unwrap(api.project_settings.get_active_project_info())
        if (not isinstance(active, dict) or active.get('mode') != 'story'
                or not active.get('project_path')
                or Path(active['project_path']).resolve() != source):
            raise ValueError('当前世界已改变，已拒绝旧世界世界规则请求')

    with _lock:
        assert_source()
        _require_story(source)
        role, target, _ = _relation(source)
        owner = target if role == 'child' else source

        def response(state, status='ok'):
            return {'status': status, 'role': role, 'state': state}

        if role != 'child':
            if action != 'loadWorldRules':
                raise ValueError('只有小世界可以装载碎片规则')
            return response(world_rules.initial_state())
        with _exclusive(owner):
            assert_source()
            if action == 'loadWorldRules':
                return response(world_rules.load(owner))
            if action == 'clearWorldRules':
                return response(world_rules.clear(owner))
            listed = request.get('rules')
            if not isinstance(listed, list):
                raise ValueError('世界规则列表无效')
            return response(world_rules.save(owner, listed))


def handle_gameplay_request(payload: str, *, api=None):
    """Only bounded domain actions; no caller-selected write path or arbitrary code."""
    try:
        if not isinstance(payload, str) or len(payload) > 65536:
            raise ValueError('玩法请求格式无效')
        request = json.loads(payload)
        # `pickupDrop` is deliberately absent: the boss reward no longer leaves a red
        # ball behind, so there is nothing for the client to pick up.
        known = ('load', 'hitBoss', 'hitMonster', 'castSkill', *PLACEMENT_ACTIONS,
                 *WORLD_RULE_ACTIONS, *ROSTER_ACTIONS)
        if not isinstance(request, dict) or request.get('action') not in known:
            raise ValueError('未知玩法操作')
        if not isinstance(request.get('projectPath'), str) or not request['projectPath'].strip():
            raise ValueError('缺少来源世界')
        if api is None:
            from api.editor_api import CoronaEditorApi
            api = CoronaEditorApi
        source = Path(request['projectPath']).absolute()
        _plain(source)
        source = source.resolve(strict=True)
        if request['action'] in PLACEMENT_ACTIONS:
            return handle_placement_request(request, source, api)
        if request['action'] in WORLD_RULE_ACTIONS:
            return handle_world_rule_request(request, source, api)
        if request['action'] in ROSTER_ACTIONS:
            return handle_roster_request(request, source, api)

        def assert_source():
            active = _unwrap(api.project_settings.get_active_project_info())
            if (not isinstance(active, dict) or active.get('mode') != 'story'
                    or not active.get('project_path')
                    or Path(active['project_path']).resolve() != source):
                raise ValueError('当前世界已改变，已拒绝旧世界玩法请求')

        with _lock:
            assert_source()
            _require_story(source)
            role, target, _ = _relation(source)
            owner = target if role == 'child' else source
            with _exclusive(owner):
                assert_source()
                state = _read(owner)

                def response(status='ok', **extra):
                    return {'status': status, 'role': role, 'state': state, 'config': dict(CONFIG), **extra}

                action = request['action']
                if action == 'load':
                    return response()
                if role != 'main':
                    raise ValueError('子世界没有 Boss 或战斗掉落')
                operation = _operation(request)
                operation_id = operation['operationId']
                expected = operation['expectedRevision']
                prior = next((item for item in state['operations'] if item['operationId'] == operation_id), None)
                if prior is not None:
                    # `loot` is chosen by the server after the request was accepted, so a
                    # retry (which does not carry it) must still match the stored command.
                    stored = {key: value for key, value in prior.items()
                              if key not in ('loot', 'gear')}
                    if stored != operation:
                        raise ValueError('同一操作 ID 不能用于不同请求')
                    return response()  # A committed request whose reply was lost.
                if expected != state['revision']:
                    return response('error', code='REVISION_CONFLICT', message='玩法进度已更新，已重新同步，请重试')
                next_state = deepcopy(state)
                _apply(next_state, operation, live=True)
                next_state['revision'] += 1
                next_state['operations'].append(operation)
                _validate(next_state)
                _write(owner, next_state, assert_source)
                state = next_state
                return response()
    except Exception as error:
        return {'status': 'error', 'message': f'玩法存档操作失败：{error}'}
