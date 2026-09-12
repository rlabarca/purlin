"""Tests for scripts/hooks/refresh_digest.py and its registration in
hooks/hooks.json (specs/hooks/refresh_digest_hook.md)."""

import importlib.util
import io
import json
import os
import subprocess
import sys
import time

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HOOK = os.path.join(PROJECT_ROOT, 'scripts', 'hooks', 'refresh_digest.py')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'audit'))
import purlin_server
import static_checks

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


def _project(tmp, report=True, digest='auto', git=True, anchor=False):
    os.makedirs(os.path.join(tmp, '.purlin'), exist_ok=True)
    with open(os.path.join(tmp, '.purlin', 'config.json'), 'w') as f:
        json.dump({'report': report, 'digest': digest, 'spec_dir': 'specs'}, f)
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
        _git(tmp, 'init', '-q')
        _git(tmp, 'config', 'user.email', 't@example.com')
        _git(tmp, 'config', 'user.name', 'T')
        _git(tmp, 'add', '.')
        _git(tmp, 'commit', '-q', '-m', 'init')
    return tmp


def _write_proofs(tmp, proofs):
    with open(os.path.join(tmp, 'specs', 'app', 'login.proofs-unit.json'), 'w') as f:
        json.dump({'tier': 'unit', 'proofs': proofs}, f)


def _digest_path(tmp):
    return os.path.join(tmp, '.purlin', 'report-data.js')


def _read_digest(tmp):
    with open(_digest_path(tmp), encoding='utf-8') as f:
        content = f.read()
    assert content.startswith('const PURLIN_DATA = ')
    return json.loads(content[len('const PURLIN_DATA = '):].rstrip().rstrip(';'))


def _run(tmp, env=None):
    full_env = {k: v for k, v in os.environ.items() if k != 'PURLIN_SKIP_DIGEST'}
    full_env.update(env or {})
    return subprocess.run([sys.executable, HOOK], cwd=tmp, input=STDIN,
                          capture_output=True, text=True, env=full_env,
                          timeout=120)


def _assert_silent_zero(result, label):
    assert result.returncode == 0, f'{label}: exit {result.returncode}\n{result.stderr}'
    assert result.stdout == '', f'{label}: stdout was {result.stdout!r}'
    assert result.stderr == '', f'{label}: stderr was {result.stderr!r}'


def _load_hook_module():
    spec = importlib.util.spec_from_file_location('refresh_digest', HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    @pytest.mark.proof("refresh_digest_hook", "PROOF-1", "RULE-1", tier="integration")
    def test_every_path_exits_zero_and_prints_nothing(self, tmp_path):
        project = _project(str(tmp_path / 'p'))
        _assert_silent_zero(_run(project), 'fresh project')
        assert os.path.isfile(_digest_path(project)), 'the first run must write the digest'

        bare = str(tmp_path / 'not-git')
        os.makedirs(bare)
        _assert_silent_zero(_run(bare), 'not a git repository')
        assert not os.path.exists(os.path.join(bare, '.purlin'))

        off = _project(str(tmp_path / 'off'), report=False)
        _assert_silent_zero(_run(off), 'report false')
        assert not os.path.exists(_digest_path(off))

        locked = _project(str(tmp_path / 'locked'))
        os.makedirs(os.path.join(locked, '.purlin', 'runtime'))
        with open(os.path.join(locked, '.purlin', 'runtime', 'refresh_digest.lock'), 'a+') as lock:
            static_checks._lock_exclusive(lock)
            try:
                _assert_silent_zero(_run(locked), 'lock held')
            finally:
                static_checks._unlock(lock)
        assert not os.path.exists(_digest_path(locked))

        skipped = _project(str(tmp_path / 'skipped'))
        _assert_silent_zero(_run(skipped, env={'PURLIN_SKIP_DIGEST': '1'}), 'PURLIN_SKIP_DIGEST')
        assert not os.path.exists(_digest_path(skipped))


class TestDirtyCheck:

    @pytest.mark.proof("refresh_digest_hook", "PROOF-2", "RULE-2", tier="integration")
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

        assert _read_digest(project)['features'][0]['proved'] == 1
        _write_proofs(project, [_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2')])
        _assert_silent_zero(_run(project), 'proof file newer')
        assert _read_digest(project)['features'][0]['proved'] == 2, \
            'a newer proof file must regenerate the digest'

        stamp = os.stat(digest).st_mtime
        time.sleep(0.01)
        os.utime(os.path.join(project, '.purlin', 'config.json'), None)
        _assert_silent_zero(_run(project), 'config newer')
        assert os.stat(digest).st_mtime > stamp, 'a newer config must trigger a run'


class TestSingleFlight:

    @pytest.mark.proof("refresh_digest_hook", "PROOF-3", "RULE-3", tier="integration")
    def test_a_held_lock_means_leave(self, tmp_path):
        project = _project(str(tmp_path))
        os.makedirs(os.path.join(project, '.purlin', 'runtime'))
        lock_path = os.path.join(project, '.purlin', 'runtime', 'refresh_digest.lock')
        with open(lock_path, 'a+') as lock:
            static_checks._lock_exclusive(lock)
            try:
                _assert_silent_zero(_run(project), 'lock held')
                assert not os.path.exists(_digest_path(project)), \
                    'a second instance must not generate while the first holds the lock'
            finally:
                static_checks._unlock(lock)
        _assert_silent_zero(_run(project), 'lock released')
        assert os.path.isfile(_digest_path(project))


class TestRecheckAfterWriting:

    @pytest.mark.proof("refresh_digest_hook", "PROOF-4", "RULE-4", tier="integration")
    def test_a_write_during_generation_is_picked_up(self, tmp_path, monkeypatch):
        project = _project(str(tmp_path))
        module = _load_hook_module()
        real = purlin_server.generate_digest
        calls = []

        def once(root, **kw):
            path = real(root, **kw)
            if len(calls) == 0:
                time.sleep(0.02)
                _write_proofs(project, [_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2')])
            calls.append(kw)
            return path

        monkeypatch.setattr(purlin_server, 'generate_digest', once)
        _main_in(project, module)
        assert len(calls) == 2, f'expected a second generation for the write that landed, got {len(calls)}'
        assert _read_digest(project)['features'][0]['proved'] == 2
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
        monkeypatch.setattr(purlin_server, 'generate_digest', always)
        _main_in(project, module)
        assert len(calls) == 3, f'the re-check is bounded at three runs, got {len(calls)}'


class TestSkipConditions:

    @pytest.mark.proof("refresh_digest_hook", "PROOF-5", "RULE-5", tier="integration")
    def test_each_skip_condition_writes_nothing(self, tmp_path):
        no_config = _project(str(tmp_path / 'no-config'))
        os.remove(os.path.join(no_config, '.purlin', 'config.json'))
        _assert_silent_zero(_run(no_config), 'no config')
        assert not os.path.exists(_digest_path(no_config))

        report_off = _project(str(tmp_path / 'report-off'), report=False)
        _assert_silent_zero(_run(report_off), 'report false')
        assert not os.path.exists(_digest_path(report_off))

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
        _assert_silent_zero(_run(committing), 'index.lock present')
        assert not os.path.exists(_digest_path(committing)), \
            'a commit in flight belongs to the pre-commit hook'
        os.remove(index_lock)
        _assert_silent_zero(_run(committing), 'index.lock gone')
        assert os.path.isfile(_digest_path(committing))


class TestGenerationContract:

    @pytest.mark.proof("refresh_digest_hook", "PROOF-6", "RULE-6", tier="integration")
    def test_no_network_named_producer_and_touch_instead_of_rewrite(self, tmp_path, monkeypatch):
        project = _project(str(tmp_path), anchor=True)
        module = _load_hook_module()
        argvs = []
        real_run = purlin_server.subprocess.run

        def recording(argv, *a, **kw):
            argvs.append(list(argv))
            return real_run(argv, *a, **kw)

        monkeypatch.setattr(purlin_server.subprocess, 'run', recording)
        _main_in(project, module)
        assert argvs, 'the build shells out to git, so the recorder must have seen something'
        assert not any('ls-remote' in argv for argv in argvs), \
            f'a background hook must never reach the network: {[a for a in argvs if "ls-remote" in a]}'
        digest = _read_digest(project)
        assert digest['generated_by'] == 'hook'
        anchor = next(f for f in digest['features'] if f['name'] == 'shared_rules')
        assert anchor['ext_status'] == 'unchecked'

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

    @pytest.mark.proof("refresh_digest_hook", "PROOF-7", "RULE-7", tier="unit")
    def test_hooks_json_registers_exactly_this_script_async_on_three_events(self):
        with open(os.path.join(PROJECT_ROOT, 'hooks', 'hooks.json'), encoding='utf-8') as f:
            manifest = json.load(f)
        hooks = manifest['hooks']
        assert set(hooks) == {'PostToolUse', 'SubagentStop', 'Stop'}, sorted(hooks)
        for forbidden in ('PreToolUse', 'PermissionRequest', 'UserPromptSubmit'):
            assert forbidden not in hooks
        assert hooks['PostToolUse'][0]['matcher'] == 'Bash|Write|Edit|MultiEdit'
        entries = [h for event in hooks.values() for group in event for h in group['hooks']]
        assert len(entries) == 3
        for entry in entries:
            assert entry['type'] == 'command'
            assert entry.get('async') is True, entry
            assert isinstance(entry.get('timeout'), int), entry
            assert 'scripts/hooks/refresh_digest.py' in entry['command'], entry
            assert '${CLAUDE_PLUGIN_ROOT}' in entry['command'], entry
