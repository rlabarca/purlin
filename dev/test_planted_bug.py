"""The planted bug: one change per proof, made in a copy of the project and never in it."""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, 'scripts', 'review'))
sys.path.insert(0, _HERE)

import audit_run  # noqa: E402
import fake_claude  # noqa: E402
import targeted_break  # noqa: E402

RUN_SCRIPT = os.path.join(_ROOT, 'scripts', 'run', 'purlin_run.py')
EVIDENCE = '.purlin/evidence/local/age.json'

# `return days` is line 12.
AGE = '''\
"""How old a stamp is, in minutes."""


def minutes(stamp):
    return 90


def age(stamp):
    days = minutes(stamp)
    if stamp == "":
        return 0
    return days
'''

WEAK = 'assert age("2026-01-01") is not None'
STRONG = 'assert age("2026-01-01") == 90'
SCOPE = ['src/age.py']
PROOF = {'id': 'PROOF-1', 'text': 'has an age of `90` minutes', 'rule': 'RULE-1',
         'rule_text': 'A stamp has an age in minutes'}
BREAK = 'file: src/age.py\nbefore:\n    return days\nafter:\n    return 0\n'
# A bug that makes the test run past a limit of 2 seconds.
SLOW = ('file: src/age.py\nbefore:\n    return days\nafter:\n'
        '    __import__("time").sleep(20)\n    return days\n')


@pytest.fixture(autouse=True)
def own_claude(tmp_path, monkeypatch):
    """A fake `claude` under this test's own folder stands first on PATH, and the
    temporary folder the copies are made in is this test's own."""
    directory = fake_claude.install(str(tmp_path / 'claude-bin'))
    monkeypatch.setenv('PATH', directory + os.pathsep + os.environ.get('PATH', ''))
    assert os.path.realpath(shutil.which('claude')).startswith(os.path.realpath(str(tmp_path)))
    temporary = tmp_path / 'tmp'
    temporary.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(temporary))
    return directory


def write(root, path, text):
    full = os.path.join(str(root), *path.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as handle:
        handle.write(text)


def git(root, *args):
    return subprocess.run(('git', '-C', str(root)) + args, check=True, capture_output=True,
                          text=True).stdout


def project(tmp_path, tests, age=AGE, extra=''):
    """A git project: `src/age.py`, and one test per entry of `tests`, `{proof: body}`,
    each marked for that proof of `age`. `extra` is added to the top of the test file."""
    root = tmp_path / 'project'
    root.mkdir()
    write(root, 'src/__init__.py', '')
    write(root, 'src/age.py', age)
    lines = ['import time', 'from src.age import age', extra, '']
    for proof, body in tests.items():
        lines += ['', '# purlin: age %s' % proof,
                  'def test_%s():' % proof.lower().replace('-', '_')]
        lines += ['    ' + line for line in body.split('\n')]
    write(root, 'tests/test_age.py', '\n'.join(lines) + '\n')
    write(root, 'specs/age.md', '# Feature: age\n\n> Scope: src/age.py\n\n## Rules\n\n'
          '- RULE-1: A stamp has an age in minutes\n\n## Proof\n\n'
          + ''.join('- %s (RULE-1): it holds\n' % proof for proof in tests))
    write(root, '.purlin/config.json', json.dumps({'version': '0.10.0', 'tests': [
        {'name': 'pytest', 'run': 'python3 -m pytest -p no:cacheprovider {files} '
                                  '--junitxml={report}',
         'format': 'junit', 'files': ['tests/test_*.py']}]}))
    write(root, '.gitignore', '__pycache__/\n.purlin/runtime/\n')
    git(root, 'init', '-q')
    git(root, 'add', '-A')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'start')
    return str(root)


def own_test(proof='PROOF-1'):
    return [{'file': 'tests/test_age.py', 'name': 'test_%s' % proof.lower().replace('-', '_'),
             'source': ''}]


def audit(root):
    """`(exit code, printed lines, evidence bytes before, after)` of the audit
    over `age`, after one run of its tests has written the evidence."""
    done = subprocess.run([sys.executable, RUN_SCRIPT, '--project-root', root, '--all',
                           '--test'], capture_output=True, text=True, cwd=root)
    path = os.path.join(root, *EVIDENCE.split('/'))
    assert os.path.isfile(path), done.stdout + done.stderr
    with open(path, 'rb') as handle:
        before = handle.read()
    out = io.StringIO()
    code = audit_run.run(root, None, ['age'], out=out)
    with open(path, 'rb') as handle:
        return code, out.getvalue().splitlines(), before, handle.read()


def files_of(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        for name in filenames:
            full = os.path.join(dirpath, name)
            with open(full, 'rb') as handle:
                out[os.path.relpath(full, root)] = handle.read()
    return out


def copies(tmp_path):
    return [name for name in os.listdir(str(tmp_path / 'tmp'))
            if name.startswith('purlin-break-')]


# purlin: planted_bug PROOF-1
def test_the_project_holds_the_same_bytes_after_a_bug(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    write(root, 'notes.txt', 'untracked\n')
    before = files_of(root)
    status = git(root, 'status', '--porcelain')
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        BREAK)
    assert result['file'] == 'src/age.py'
    assert files_of(root) == before
    assert git(root, 'status', '--porcelain') == status


# purlin: planted_bug PROOF-19
def test_the_project_holds_the_same_bytes_after_a_test_runs_past_its_limit(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    before = files_of(root)
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE, SLOW, timeout=2)
    assert files_of(root) == before
    assert result['after'].startswith('    __import__("time").sleep(20)'), result
    assert result['result'] == 'not run'


# purlin: planted_bug PROOF-2
def test_a_test_that_still_passes_reads_survived(tmp_path):
    root = project(tmp_path, {'PROOF-1': WEAK})
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        BREAK)
    assert result['line'] == 12
    assert result['result'] == 'survived'
    assert result['finding'] == 'PROOF-1: the test still passes when src/age.py:12 reads "return 0"'


# purlin: planted_bug PROOF-3
def test_a_test_that_fails_reads_caught(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        BREAK)
    assert result['result'] == 'caught'
    assert result['finding'] is None


# purlin: planted_bug PROOF-17
def test_a_test_that_can_no_longer_be_collected_reads_not_run(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    answer = 'file: src/age.py\nbefore:\ndef age(\nafter:\ndef age_(\n'
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE, answer)
    assert result['line'] == 8, result
    assert result['result'] == 'not run'
    assert result['result'] != 'caught'
    assert result['finding'] is None


# purlin: planted_bug PROOF-6
def test_a_file_outside_the_copy_is_not_made(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    answer = 'file: ../outside.py\nbefore:\n    return days\nafter:\n    return 0\n'
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE + ['../outside.py'],
                                        answer)
    assert result['result'] == 'not made'
    assert not os.path.exists(os.path.join(str(tmp_path), 'outside.py'))
    assert not os.path.exists(os.path.join(str(tmp_path), 'tmp', 'outside.py'))


# purlin: planted_bug PROOF-7
def test_a_project_that_changes_while_the_audit_runs_stops_the_audit(tmp_path, own_claude):
    root = project(tmp_path, {'PROOF-1': STRONG})
    fake_claude.install(own_claude, answers=[{'PROOF-1': BREAK}], writes=[
        os.path.join(root, 'src', 'age.py'), '# the model wrote here\n'])
    code, lines, before, after = audit(root)
    assert len(fake_claude.calls(own_claude)) == 1
    assert lines[-1] == ('The audit stopped: src/age.py changed while the audit ran. Nothing '
                         'in the project was written by the audit.'), lines
    assert code == 1
    assert after == before
    assert b'"audit"' not in after


# purlin: planted_bug PROOF-13
def test_three_bugs_with_nothing_else_touching_the_project(tmp_path, own_claude):
    root = project(tmp_path, {'PROOF-1': STRONG, 'PROOF-2': WEAK, 'PROOF-3': STRONG})
    fake_claude.install(own_claude, answers=[
        {'PROOF-1': BREAK, 'PROOF-2': BREAK, 'PROOF-3': BREAK}])
    code, lines, _before, after = audit(root)
    breaks = json.loads(after)['audit']['rules']['RULE-1']['breaks']
    assert {proof: made['result'] for proof, made in breaks.items()} == {
        'PROOF-1': 'caught', 'PROOF-2': 'survived', 'PROOF-3': 'caught'}
    assert not [line for line in lines if line.startswith('The audit stopped:')]
    assert code == 0


# purlin: planted_bug PROOF-8
def test_the_copy_is_removed_when_the_test_fails(tmp_path):
    seen = os.path.join(str(tmp_path), 'seen.txt')
    body = 'open(%r, "w").write(__import__("os").getcwd())\n%s' % (seen, STRONG)
    root = project(tmp_path, {'PROOF-1': body})
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        BREAK)
    assert result['result'] == 'caught'
    with open(seen, encoding='utf-8') as handle:
        ran_in = handle.read()
    assert os.path.basename(ran_in).startswith('purlin-break-')
    assert copies(tmp_path) == []


# purlin: planted_bug PROOF-14
def test_the_copy_is_removed_when_the_test_runs_past_its_limit(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        SLOW, timeout=2)
    assert result['result'] == 'not run'
    assert copies(tmp_path) == []


# purlin: planted_bug PROOF-9
def test_claude_resolves_under_this_tests_own_folder(tmp_path):
    found = shutil.which('claude')
    assert found is not None
    assert os.path.realpath(found).startswith(os.path.realpath(str(tmp_path)))


# purlin: planted_bug PROOF-12
def test_only_the_proofs_own_test_runs_against_its_bug(tmp_path):
    root = project(tmp_path, {'PROOF-1': WEAK, 'PROOF-2': STRONG})
    result = targeted_break.break_proof(root, 'age', PROOF, own_test('PROOF-1'), SCOPE,
                                        BREAK)
    other = targeted_break.break_proof(root, 'age', dict(PROOF, id='PROOF-2'),
                                       own_test('PROOF-2'), SCOPE, BREAK)
    assert other['result'] == 'caught'
    assert result['result'] == 'survived'


def ran_marker(tmp_path):
    ran = os.path.join(str(tmp_path), 'ran.txt')
    return ran, 'open(%r, "w").write("ran")\n%s' % (ran, STRONG)


# purlin: planted_bug PROOF-5
def test_a_change_that_matches_twice_is_not_made(tmp_path):
    ran, body = ran_marker(tmp_path)
    twice = AGE + '\n\ndef older(stamp):\n    days = minutes(stamp) * 2\n    return days\n'
    root = project(tmp_path, {'PROOF-1': body}, age=twice)
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        BREAK)
    assert result['result'] == 'not made'
    assert not os.path.exists(ran)


# purlin: planted_bug PROOF-15
def test_a_file_the_scope_does_not_name_is_not_made(tmp_path):
    ran, body = ran_marker(tmp_path)
    root = project(tmp_path, {'PROOF-1': body})
    write(root, 'README.md', 'return days\n')
    answer = 'file: README.md\nbefore:\nreturn days\nafter:\nreturn 0\n'
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE,
                                        answer)
    assert result['result'] == 'not made'
    assert not os.path.exists(ran)


# purlin: planted_bug PROOF-10
def test_an_answer_of_no_break_is_not_made_with_its_reason(tmp_path):
    root = project(tmp_path, {'PROOF-1': STRONG})
    result = targeted_break.break_proof(
        root, 'age', PROOF, own_test(), SCOPE,
        'no break: the proof names no value the code computes')
    assert result['result'] == 'not made'
    assert result['why'] == 'the proof names no value the code computes'
    assert result['cause'] == 'model found none'


# purlin: planted_bug PROOF-18
def test_a_change_to_the_proofs_own_test_file_is_not_made(tmp_path):
    ran, body = ran_marker(tmp_path)
    body = body.replace(STRONG, 's = "2026-01-01"\nassert age(s) == 90')
    root = project(tmp_path, {'PROOF-1': body})
    answer = ('file: tests/test_age.py\nbefore:\n    assert age(s) == 90\nafter:\n'
              '    assert age(s) == 0\n')
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(),
                                        SCOPE + ['tests/test_age.py'], answer)
    assert result['result'] == 'not made'
    assert result['why'] == "tests/test_age.py holds one of the proof's tests"
    assert not os.path.exists(ran)


# purlin: planted_bug PROOF-16
def test_a_test_that_does_not_pass_in_the_copy_has_no_bug_planted(tmp_path):
    body = 'assert __import__("json").load(open("data/built.json")) == [90]\n' + STRONG
    root = project(tmp_path, {'PROOF-1': body})
    write(root, '.gitignore', '__pycache__/\n.purlin/runtime/\ndata/\n')
    git(root, '-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qam',
        'ignore data')
    write(root, 'data/built.json', '[90]\n')
    assert git(root, 'status', '--porcelain') == ''
    result = targeted_break.break_proof(root, 'age', PROOF, own_test(), SCOPE, BREAK)
    assert result['result'] == 'not made'
    assert result['result'] != 'caught'
    assert result['why'] == 'the test does not pass in a copy of the project'
    assert result['cause'] == 'test does not pass'
