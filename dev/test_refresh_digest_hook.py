"""Tests for scripts/hooks/refresh_digest.py and its registration in
hooks/hooks.json (specs/mcp/server.md, RULE-13 to RULE-21)."""

import contextlib
import importlib
import io
import json
import os
import re
import subprocess
import sys
import time
import traceback

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HOOK = os.path.join(PROJECT_ROOT, 'scripts', 'hooks', 'refresh_digest.py')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
from purlin import drift as purlin_drift
from purlin import payload as purlin_payload
from purlin import specs as purlin_specs
from purlin import server as purlin_srv

STDIN = '{"tool_name": "Write", "tool_input": {"file_path": "specs/app/login.md"}}'

SPEC = (
    '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
    '- RULE-1: login rejects a bad password\n'
    '- RULE-2: login locks after five failures\n\n## Proof\n\n'
    '- PROOF-1 (RULE-1): call login with a bad password and verify 401 @unit\n'
    '- PROOF-2 (RULE-2): fail five times and verify the sixth call is 423 @unit\n'
)
ANCHOR = (
    '# Anchor: shared_rules\n\n> Source: https://github.com/example/rules.git\n'
    '> Pinned: abc1234\n\n## Rules\n\n- RULE-1: no secrets in logs\n\n'
    '## Proof\n\n- PROOF-1 (RULE-1): grep the logs @unit\n'
)


def _entry(pid, rule):
    return {'feature': 'login', 'id': pid, 'rule': rule, 'status': 'pass',
            'tier': 'unit', 'test_file': 'tests/test_login.py',
            'test_name': 'test_' + pid.lower().replace('-', '_')}


def _git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                          text=True, check=True)


def _project(tmp, digest='auto', git=True, anchor=False, config=None):
    os.makedirs(os.path.join(tmp, '.purlin'), exist_ok=True)
    if config is None:
        config = {'digest': digest}
    with open(os.path.join(tmp, '.purlin', 'config.json'), 'w') as f:
        json.dump(config, f)
    os.makedirs(os.path.join(tmp, 'specs', 'app'), exist_ok=True)
    with open(os.path.join(tmp, 'specs', 'app', 'login.md'), 'w') as f:
        f.write(SPEC)
    _write_proofs(tmp, [_entry('PROOF-1', 'RULE-1')])
    if anchor:
        os.makedirs(os.path.join(tmp, 'specs', '_anchors'), exist_ok=True)
        with open(os.path.join(tmp, 'specs', '_anchors', 'shared_rules.md'), 'w') as f:
            f.write(ANCHOR)
    if git:
        with open(os.path.join(tmp, '.gitignore'), 'w') as f:
            f.write('.purlin/runtime/\n')
        _git(tmp, '-c', 'init.defaultBranch=main', 'init', '-q')
        _git(tmp, 'config', 'user.email', 't@example.com')
        _git(tmp, 'config', 'user.name', 'T')
        _git(tmp, 'add', '.')
        _git(tmp, 'commit', '-q', '-m', 'init')
    return tmp


def _write_proofs(tmp, proofs):
    directory = os.path.join(tmp, '.purlin', 'runtime', 'proofs')
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, 'login.unit.json'), 'w') as f:
        json.dump({'tier': 'unit', 'proofs': proofs}, f)


def _passing(digest):
    """How many of the feature's rules have a passed cell that reads `passed`."""
    feature = next(f for f in digest['features'] if f['name'] == 'login')
    return sum(1 for rule in feature['rules']
               if rule['cells']['passed']['word'] == 'passed')


def _digest_path(tmp):
    return os.path.join(tmp, '.purlin', 'report-data.js')


def _read_digest(tmp):
    with open(_digest_path(tmp), encoding='utf-8') as f:
        content = f.read()
    assert content.startswith('const PURLIN_DATA = ')
    return json.loads(content[len('const PURLIN_DATA = '):].rstrip().rstrip(';'))


def _run(tmp, env=None, child=False):
    """The hook against `tmp`: its exit code and what it printed.

    The hook's `main()` runs in this process, so a mutation run can see which
    case caught a break, and an exception fails the case where the script's
    wrapper would have swallowed it. `child=True` starts the script the way
    Claude Code does, wrapper and all.
    """
    full_env = {k: v for k, v in os.environ.items() if k != 'PURLIN_SKIP_DIGEST'}
    full_env.update(env or {})
    if child:
        return subprocess.run([sys.executable, HOOK], cwd=tmp, input=STDIN,
                              capture_output=True, text=True, env=full_env,
                              timeout=120)
    module = _load_hook_module()
    saved = dict(os.environ)
    out, err = io.StringIO(), io.StringIO()
    code = 0
    os.environ.clear()
    os.environ.update(full_env)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                _main_in(tmp, module)
            except Exception:                                  # noqa: BLE001
                code = 1
                err.write(traceback.format_exc())
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return subprocess.CompletedProcess([HOOK], code, out.getvalue(),
                                       err.getvalue())


def _assert_silent_zero(result, label):
    assert result.returncode == 0, f'{label}: exit {result.returncode}\n{result.stderr}'
    assert result.stdout == '', f'{label}: stdout was {result.stdout!r}'
    assert result.stderr == '', f'{label}: stderr was {result.stderr!r}'


def _load_hook_module():
    """A fresh import of the hook, found the way any module on `sys.path` is.

    An import through `sys.path` goes through the import system's finders, so
    a mutation run's module rename applies to it; a file loaded by location
    would never switch a break on.
    """
    hooks = os.path.dirname(HOOK)
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    sys.modules.pop('refresh_digest', None)
    return importlib.import_module('refresh_digest')


def _main_in(tmp, module):
    """Run the hook's main() in-process with cwd and stdin as the harness sets them."""
    cwd = os.getcwd()
    stdin = sys.stdin
    os.chdir(tmp)
    sys.stdin = io.StringIO(STDIN)
    try:
        module.main()
    finally:
        os.chdir(cwd)
        sys.stdin = stdin


def _age(path, seconds=120):
    past = time.time() - seconds
    os.utime(path, (past, past))


class TestSilentAndNonBlocking:

    @pytest.mark.proof("server", "PROOF-13", "RULE-13", tier="integration")
    def test_every_path_exits_zero_and_prints_nothing(self, tmp_path):
        project = _project(str(tmp_path / 'p'))
        _assert_silent_zero(_run(project, child=True), 'fresh project')
        assert os.path.isfile(_digest_path(project)), 'the first run must write the digest'

        bare = str(tmp_path / 'not-git')
        os.makedirs(bare)
        _assert_silent_zero(_run(bare, child=True), 'not a git repository')
        assert not os.path.exists(os.path.join(bare, '.purlin'))
        _assert_silent_zero(_run(str(tmp_path / 'p')), 'fresh project, in process')
        _assert_silent_zero(_run(bare), 'not a git repository, in process')
        assert not os.path.exists(os.path.join(bare, '.purlin'))

        off = _project(str(tmp_path / 'off'), digest='off')
        _assert_silent_zero(_run(off, child=True), 'digest off')
        _assert_silent_zero(_run(off), 'digest off, in process')
        assert not os.path.exists(_digest_path(off))

        locked = _project(str(tmp_path / 'locked'))
        os.makedirs(os.path.join(locked, '.purlin', 'runtime'), exist_ok=True)
        hook = _load_hook_module()
        with open(os.path.join(locked, '.purlin', 'runtime', 'refresh_digest.lock'), 'a+') as lock:
            hook.lock_exclusive(lock)
            try:
                _assert_silent_zero(_run(locked, child=True), 'lock held')
            finally:
                hook.unlock(lock)
        assert not os.path.exists(_digest_path(locked))

        skipped = _project(str(tmp_path / 'skipped'))
        _assert_silent_zero(_run(skipped, env={'PURLIN_SKIP_DIGEST': '1'}, child=True),
                            'PURLIN_SKIP_DIGEST')
        _assert_silent_zero(_run(skipped, env={'PURLIN_SKIP_DIGEST': '1'}),
                            'PURLIN_SKIP_DIGEST, in process')
        assert not os.path.exists(_digest_path(skipped))


class TestDirtyCheck:

    @pytest.mark.proof("server", "PROOF-14", "RULE-14", tier="integration")
    @pytest.mark.proof("server", "PROOF-15", "RULE-15", tier="integration")
    def test_regenerates_only_when_an_input_is_newer(self, tmp_path):
        project = _project(str(tmp_path))
        _assert_silent_zero(_run(project), 'first')
        digest = _digest_path(project)
        first_bytes = open(digest, 'rb').read()
        stamp = os.stat(digest).st_mtime

        _assert_silent_zero(_run(project), 'nothing changed')
        assert open(digest, 'rb').read() == first_bytes
        assert os.stat(digest).st_mtime == stamp, 'a quiet run must not touch the digest'

        os.makedirs(os.path.join(project, '.purlin', 'runtime'), exist_ok=True)
        with open(os.path.join(project, '.purlin', 'runtime', 'test_run.json'), 'w') as f:
            f.write('{}')
        _assert_silent_zero(_run(project), 'runtime file newer')
        assert open(digest, 'rb').read() == first_bytes
        assert os.stat(digest).st_mtime == stamp, '.purlin/runtime/ is not an input'

        assert _passing(_read_digest(project)) == 1
        _write_proofs(project, [_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2')])
        _assert_silent_zero(_run(project), 'proof file newer')
        assert _passing(_read_digest(project)) == 2, \
            'a newer proof file must regenerate the digest'

        stamp = os.stat(digest).st_mtime
        time.sleep(0.01)
        os.utime(os.path.join(project, '.purlin', 'config.json'), None)
        _assert_silent_zero(_run(project), 'config newer')
        assert os.stat(digest).st_mtime > stamp, 'a newer config must trigger a run'

        # The spec directory is the literal `specs`, not a config field: the
        # retired `spec_dir` (`skill_init` RULE-76) must not come back as a
        # reader here, so a config naming another directory changes nothing.
        with io.open(HOOK, encoding='utf-8') as f:
            source = f.read()
        assert not re.search(r"config(?:\.get\(|\[)\s*['\"]spec_dir", source), \
            "the hook reads spec_dir out of the config again"
        config_path = os.path.join(project, '.purlin', 'config.json')
        with io.open(config_path, encoding='utf-8') as f:
            config = json.load(f)
        config['spec_dir'] = 'elsewhere'
        with open(config_path, 'w') as f:
            json.dump(config, f)
        stamp = os.stat(digest).st_mtime
        time.sleep(0.01)
        _write_proofs(project, [_entry('PROOF-1', 'RULE-1')])
        _assert_silent_zero(_run(project), 'spec_dir in the config is ignored')
        assert _passing(_read_digest(project)) == 1, \
            "a stray spec_dir in the config redirected the dirty check"
        assert os.stat(digest).st_mtime > stamp


class TestSingleFlight:

    @pytest.mark.proof("server", "PROOF-16", "RULE-16", tier="integration")
    def test_a_held_lock_means_leave(self, tmp_path):
        project = _project(str(tmp_path))
        os.makedirs(os.path.join(project, '.purlin', 'runtime'), exist_ok=True)
        lock_path = os.path.join(project, '.purlin', 'runtime', 'refresh_digest.lock')
        hook = _load_hook_module()
        with open(lock_path, 'a+') as lock:
            hook.lock_exclusive(lock)
            try:
                _assert_silent_zero(_run(project, child=True), 'lock held')
                assert not os.path.exists(_digest_path(project)), \
                    'a second instance must not generate while the first holds the lock'
            finally:
                hook.unlock(lock)
        _assert_silent_zero(_run(project), 'lock released')
        assert os.path.isfile(_digest_path(project))


class TestRecheckAfterWriting:

    @pytest.mark.proof("server", "PROOF-17", "RULE-17", tier="integration")
    def test_a_write_during_generation_is_picked_up(self, tmp_path, monkeypatch):
        project = _project(str(tmp_path))
        module = _load_hook_module()
        real = purlin_srv.generate_digest
        calls = []

        def once(root, **kw):
            path = real(root, **kw)
            if len(calls) == 0:
                time.sleep(0.02)
                _write_proofs(project, [_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2')])
            calls.append(kw)
            return path

        monkeypatch.setattr(purlin_srv, 'generate_digest', once)
        _main_in(project, module)
        assert len(calls) == 2, f'expected a second generation for the write that landed, got {len(calls)}'
        assert _passing(_read_digest(project)) == 2
        assert all(kw == {'generated_by': 'hook', 'network': False, 'only_if_changed': True}
                   for kw in calls), calls

        calls.clear()
        n = [2]

        def always(root, **kw):
            path = real(root, **kw)
            time.sleep(0.02)
            n[0] += 1
            _write_proofs(project, [_entry(f'PROOF-{i}', f'RULE-{1 + i % 2}') for i in range(1, n[0] + 1)])
            calls.append(kw)
            return path

        _age(_digest_path(project))
        os.utime(os.path.join(project, '.purlin', 'config.json'), None)
        monkeypatch.setattr(purlin_srv, 'generate_digest', always)
        _main_in(project, module)
        assert len(calls) == 3, f'the re-check is bounded at three runs, got {len(calls)}'


class TestSkipConditions:

    @pytest.mark.proof("server", "PROOF-18", "RULE-18", tier="integration")
    def test_each_skip_condition_writes_nothing(self, tmp_path):
        no_config = _project(str(tmp_path / 'no-config'))
        os.remove(os.path.join(no_config, '.purlin', 'config.json'))
        _assert_silent_zero(_run(no_config), 'no config')
        assert not os.path.exists(_digest_path(no_config))

        digest_off = _project(str(tmp_path / 'digest-off'), digest='off')
        _assert_silent_zero(_run(digest_off), 'digest off')
        assert not os.path.exists(_digest_path(digest_off))

        skip = _project(str(tmp_path / 'skip'))
        _assert_silent_zero(_run(skip, env={'PURLIN_SKIP_DIGEST': '1'}), 'skip env')
        assert not os.path.exists(_digest_path(skip))

        committing = _project(str(tmp_path / 'committing'))
        git_dir = _git(committing, 'rev-parse', '--absolute-git-dir').stdout.strip()
        index_lock = os.path.join(git_dir, 'index.lock')
        with open(index_lock, 'w') as f:
            f.write('')
        _assert_silent_zero(_run(committing, child=True), 'index.lock present')
        _assert_silent_zero(_run(committing), 'index.lock present, in process')
        assert not os.path.exists(_digest_path(committing)), \
            'a commit in flight belongs to the pre-commit hook'
        os.remove(index_lock)
        _assert_silent_zero(_run(committing), 'index.lock gone')
        assert os.path.isfile(_digest_path(committing))

    @pytest.mark.proof("server", "PROOF-19", "RULE-19", tier="integration")
    def test_a_config_in_the_template_shape_refreshes(self, tmp_path):
        """The skip conditions are the only skip conditions.

        `templates/config.json` is what `purlin:init` stamps into a new
        project. It carries none of the keys above, so a hook that needed one
        of them to be present would leave every freshly initialized project
        with an empty dashboard and nothing saying why.
        """
        with open(os.path.join(PROJECT_ROOT, 'templates', 'config.json'),
                  encoding='utf-8') as f:
            stamped = json.load(f)
        assert 'digest' not in stamped and 'report' not in stamped, (
            'the template gained a key this test assumes is absent: %s'
            % sorted(stamped))

        project = _project(str(tmp_path / 'stamped'), config=stamped)
        _assert_silent_zero(_run(project), 'template config')
        assert os.path.isfile(_digest_path(project)), (
            'a project initialized from templates/config.json never refreshes '
            'its dashboard data')
        assert _passing(_read_digest(project)) == 1


class TestGenerationContract:

    @pytest.mark.proof("server", "PROOF-20", "RULE-20", tier="integration")
    def test_no_network_named_producer_and_touch_instead_of_rewrite(self, tmp_path, monkeypatch):
        project = _project(str(tmp_path), anchor=True)
        module = _load_hook_module()
        argvs = []
        real_run = purlin_payload.subprocess.run

        def recording(argv, *a, **kw):
            argvs.append(list(argv))
            return real_run(argv, *a, **kw)

        for watched in (purlin_payload, purlin_drift, purlin_specs):
            monkeypatch.setattr(watched.subprocess, 'run', recording)
        _main_in(project, module)
        assert argvs, 'the build shells out to git, so the recorder must have seen something'
        assert not any('ls-remote' in argv for argv in argvs), \
            f'a background hook must never reach the network: {[a for a in argvs if "ls-remote" in a]}'
        digest = _read_digest(project)
        assert digest['generated_by'] == 'hook'
        anchor = next(f for f in digest['features'] if f['name'] == 'shared_rules')
        assert anchor['source'] == 'https://github.com/example/rules.git', anchor
        assert anchor['pinned'] == 'abc1234', anchor

        # The digest is tracked in a real project; commit it so its own
        # presence is not the thing that changes between two builds. Dating
        # the digest into the past is what forces a build with nothing new.
        _git(project, 'add', '-A')
        _git(project, 'commit', '-q', '-m', 'digest')
        path = _digest_path(project)
        _age(path)
        _main_in(project, module)
        before = open(path, 'rb').read()
        _age(path)
        stamp = os.stat(path).st_mtime
        _main_in(project, module)
        assert open(path, 'rb').read() == before, \
            'an unchanged payload must not rewrite the file (the tree would be dirtied)'
        assert os.stat(path).st_mtime > stamp, 'the touch is what clears the dirty check'


class TestRegistration:

    @pytest.mark.proof("server", "PROOF-21", "RULE-21")
    def test_hooks_json_registers_exactly_this_script_async_on_three_events(self):
        path = os.path.join(PROJECT_ROOT, 'hooks', 'hooks.json')
        with open(path, encoding='utf-8') as f:
            raw = f.read()
        manifest = json.loads(raw)
        hooks = manifest['hooks']
        assert set(hooks) == {'PostToolUse', 'SubagentStop', 'Stop'}, sorted(hooks)
        for forbidden in ('PreToolUse', 'PermissionRequest', 'UserPromptSubmit'):
            assert forbidden not in hooks
        assert hooks['PostToolUse'][0]['matcher'] == 'Bash|Write|Edit|MultiEdit'
        entries = [h for event in hooks.values() for group in event for h in group['hooks']]
        assert len(entries) == 3
        expected = ('sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" '
                    '"${CLAUDE_PLUGIN_ROOT}/scripts/hooks/refresh_digest.py"')
        for entry in entries:
            assert entry['type'] == 'command'
            assert entry.get('async') is True, entry
            assert isinstance(entry.get('timeout'), int), entry
            assert entry['command'] == expected, (
                'the hook command must go through the interpreter resolver, '
                f'not name one: {entry["command"]!r}')
        # The interpreter the command must not name. `python3` is absent from
        # a python.org install on Windows, so a hooks.json that names it
        # registers three hooks that cannot start there.
        assert 'python3' not in raw, (
            f'{path} still names an interpreter: '
            + next(line for line in raw.splitlines() if 'python3' in line))
