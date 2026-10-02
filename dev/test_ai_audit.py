"""Tests for the AI audit: `scripts/review/audit_run.py` and `ai_audit.py`.

The throwaway project is `dev/sign_project.py`'s, or the sample lab project
of `dev/sample_lab.py`, so a spec, a test file and the evidence are written
by the test and nothing reads this repository's own specs or audits its code.
No test reaches the real model: every call lands on a fake `claude`
that `dev/fake_claude.py` writes under the test's own temporary folder, first
on PATH, or on a runner handed in its place.

What each group holds:

*reading*   which rules the audit reads
*prompt*    the criteria file verbatim, then the rule, its proofs, each test's
            source, the spot tests' findings and the proofs a bug is asked for
*call*      one call per rule, with no tools, in an empty folder, the request
            on stdin and never in the arguments
*answer*    the model and the criteria named; the explanation and the notes
*verdict*   the spot tests and the planted bugs alone set it; the last line
*failure*   the ways the model cannot be reached, each with its reason
*writing*   reading, asking and printing a rule write no file
*command*   the command line: its exits and what it prints
*aim*       the bug aimed past the test, on the sample lab project: the
            request's instruction, the aim and the case, and the two findings
*settle*    `--settle`: a kept bug planted again and the test run as it
            stands, on the sample lab project and the small login project
"""

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import ai_audit as audit_module  # noqa: E402
import audit_run  # noqa: E402
import fake_claude  # noqa: E402
import marked_tests  # noqa: E402
import sample_lab  # noqa: E402
import suites  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from sign_project import (SPEC, TEST_FILE, Project, git,  # noqa: E402
                          write)

AI_AUDIT_PY = os.path.join(ROOT, 'scripts', 'review', 'ai_audit.py')
CRITERIA = os.path.join(ROOT, 'references', 'review_criteria.md')

FINDING = 'PROOF-2 asserts the status but never the body the rule names.'
CHECKS_NOTHING = ('tests/test_login.py::test_a_bad_password_is_denied: the '
                  'test checks nothing.')
TRAILING_COMMA = '{\n  "version": "0.10.0",\n}\n'
READ_BY = '  Read by unknown at 2026-09-13T12:05:00Z.'

# `src/login.py` with `return 401` on its line 12, where a planted bug goes.
LOGIN_SOURCE = (
    '"""Signing in with an email and a password."""\n'
    '\n'
    'USERS = {"ada": "secret"}\n'
    '\n'
    '\n'
    'def login(user, password):\n'
    '    """200 for the right password, 401 for any other."""\n'
    '    known = USERS.get(user)\n'
    '    if known is not None and password == known:\n'
    '        return 200\n'
    '    # A wrong password, or no such user.\n'
    '    return 401\n'
)

# A test for `PROOF-2` that holds no assertion at all.
CHECKS_NOTHING_TEST = TEST_FILE.replace(
    '    assert login("ada", "wrong") == 401\n',
    '    login("ada", "wrong")\n')

# A test for `PROOF-2` whose one check can fail but reads no status.
NOT_NONE_TEST = TEST_FILE.replace(
    '    assert login("ada", "wrong") == 401\n',
    '    assert login("ada", "wrong") is not None\n')


# The same tests under a fixture each takes, which calls `login` with a wrong
# password before the test's body runs.
FIXTURE_USES_LOGIN_TEST = TEST_FILE.replace(
    'from src.login import login\n',
    'from src.login import login\n\n\n'
    '@pytest.fixture(autouse=True)\ndef refused():\n'
    '    return login("ada", "wrong")\n', 1)


# What a part says its bug breaks: the proof's case, the result the proof
# names and the result the changed code gives.
CASE = 'a wrong password; the proof says 401; the changed code gives 200'


def bug(before, after, path='src/login.py', case=CASE):
    """The model's part naming one planted bug, with its case."""
    return fake_claude.change(path, before, after, case=case)


@contextlib.contextmanager
def passing_project(spec=SPEC, statuses=None, test_file=None, source=None):
    """A project whose tests ran with `statuses`, closed after.

    `test_file` replaces the test file and `source` the code before the
    evidence is taken. The suite is pytest on this interpreter, so a planted
    bug's test can run in the copy.
    """
    made = Project(spec=spec, config={'tests': [suites.pytest_suite()]})
    try:
        if source is not None:
            write(os.path.join(made.root, 'src', 'login.py'), source)
        if test_file is not None:
            made.edit_test(test_file)
        else:
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'chore: settings')
        made.evidence(statuses)
        yield made
    finally:
        made.close()


@pytest.fixture
def project():
    with passing_project() as made:
        yield made


@pytest.fixture
def claude(tmp_path, monkeypatch):
    """A fake `claude` first on PATH, under this test's own folder.

    Returns `(install, directory)`; `install(**settings)` rewrites what it
    answers. Before the first call `claude` resolves under `tmp_path`.
    """
    directory = tmp_path / 'claude'

    def install(**settings):
        fake_claude.install(directory, **settings)
        return directory

    install()
    monkeypatch.setenv('PATH', str(directory) + os.pathsep
                       + os.environ.get('PATH', ''))
    found = shutil.which('claude')
    assert found and os.path.realpath(found).startswith(
        os.path.realpath(str(tmp_path))), found
    return install, directory


def as_anchor(project):
    """Move `login` under `specs/_anchors/`, then take its evidence again."""
    os.makedirs(os.path.join(project.root, 'specs', '_anchors'))
    git(project.root, 'mv', 'specs/auth/login.md', 'specs/_anchors/login.md')
    git(project.root, 'commit', '-q', '-m', 'spec(login): an anchor')
    project.evidence()


def read(project, rule='RULE-1', findings=()):
    return audit_module.reading_for(project.root, None, 'login', rule,
                                    findings)


def criteria_text():
    with open(CRITERIA, encoding='utf-8') as handle:
        return handle.read()


def ask(project, rule='RULE-2'):
    """The model's reading of `rule`, asked of whichever `claude` is first."""
    return audit_module.audit_one(project.root, read(project, rule),
                                  criteria_text())


def to_read(project, again=False):
    """The `(feature, rule)` pairs the audit reads in `project`."""
    found = audit_run.rules_to_read(
        project.root, project.payload(),
        audit_run.specs_module.scan_specs(project.root), {'login'}, again)
    return [(feature, rule['id']) for feature, rule in found]


def audit(project, again=False):
    """`(exit code, printed text)` of the audit run over `login`."""
    out = io.StringIO()
    code = audit_run.run(project.root, None, ['login'], again=again, out=out)
    return code, out.getvalue()


def rules_printed(printed):
    """The rules the audit printed a line for, in order."""
    return re.findall(r'^login (RULE-\d+)   ', printed, re.M)


def rules_asked(directory):
    """The rule each call to the fake `claude` asked about, in order."""
    return [re.search(r'^login (RULE-\d+)$', call['prompt'], re.M).group(1)
            for call in fake_claude.calls(directory)]


def entry_of(project, rule='RULE-2'):
    """The audit entry the local evidence holds for `rule`."""
    path = os.path.join(project.root, '.purlin', 'evidence', 'local',
                        'login.json')
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)['audit']['rules'][rule]


def asked_for(call):
    """The proofs one call asked a planted bug for."""
    found = re.findall(r'^Plant one bug for each of: (.*)\.$', call['prompt'],
                       re.M)
    return [name.strip() for name in found[-1].split(',')] if found else []


def break_key_of(project, rule, proof):
    """The key a planted bug for `proof` carries for its test and code now."""
    tests = [{'file': test['file'], 'name': test['name'],
              'source': test['body']}
             for test in read(project, rule)['tests']
             if test['proof'] == proof]
    return audit_module.break_key(
        audit_run.test_source_hash(tests),
        purlin_fingerprint.code_part(project.root, {'scope': ['src/login.py']}))


def settle(project, rule, result='caught', findings=()):
    """An audit entry for `rule` as it stands now, with a planted bug on
    record for each of its proofs, so the audit has nothing left to read."""
    rel = project.audit(rule, findings=findings)
    path = os.path.join(project.root, *rel.split('/'))
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    data['audit']['rules'][rule]['breaks'] = {
        proof['id']: {'file': 'src/login.py', 'line': 12,
                      'before': '    return 401', 'after': '    return 200',
                      'result': result, 'why': '',
                      'break_key': break_key_of(project, rule, proof['id'])}
        for proof in project.rule(rule)['proofs']}
    write(path, json.dumps(data, indent=2, sort_keys=True))
    return rel


def code_of(project):
    return purlin_fingerprint.code_part(project.root,
                                        {'scope': ['src/login.py']})


def command(project, capsys, *args):
    """`(exit code, printed text)` for the command run on `project`."""
    code = audit_module.main(list(args) + ['--project-root', project.root])
    return code, capsys.readouterr().out


def files_under_purlin(root):
    """`{path: sha256}` for every file under `.purlin/`, runtime included."""
    found = {}
    for current, _dirs, names in os.walk(os.path.join(root, '.purlin')):
        for name in names:
            path = os.path.join(current, name)
            with open(path, 'rb') as handle:
                found[path] = hashlib.sha256(handle.read()).hexdigest()
    return found


# ---------------------------------------------------------------------------
# Which rules are read
# ---------------------------------------------------------------------------

class TestWhichRulesAreRead:

    # purlin: ai_audit PROOF-4
    def test_a_rule_with_an_entry_for_its_text_proof_test_and_code_is_not_read(
            self, project, claude):
        _install, directory = claude
        settle(project, 'RULE-2')
        rule = project.rule('RULE-2')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['audit']['verdict'] == 'strong', rule
        assert rule['audit']['commit'] == project.head(), rule
        assert ('login', 'RULE-2') not in to_read(project)
        assert ('login', 'RULE-1') in to_read(project)
        # The audit itself, run without asking to read again, reads RULE-1
        # and leaves RULE-2 alone: no line for it and no call about it.
        code, printed = audit(project)
        assert code == 0, printed
        assert rules_printed(printed) == ['RULE-1'], printed
        assert rules_asked(directory) == ['RULE-1']

    # purlin: ai_audit PROOF-103
    def test_a_rule_whose_feature_code_changed_since_its_entry_is_read(self):
        source = LOGIN_SOURCE
        with passing_project(source=source) as made:
            settle(made, 'RULE-2')
            assert ('login', 'RULE-2') not in to_read(made)
            write(os.path.join(made.root, 'src', 'login.py'), source.replace(
                '    return 401\n', '    return 403 if locked else 401\n'))
            made.evidence()
            rule = made.rule('RULE-2')
            assert rule['cells']['passed']['word'] == 'passed', rule
            entry = audit_run.audit_entry(made.root, 'login', rule,
                                          code_of(made))
            assert entry['out_of_date'] == ['code'], entry
            assert ('login', 'RULE-2') in to_read(made)

    # purlin: ai_audit PROOF-51
    def test_a_rule_with_a_current_entry_is_read_when_asked_again(
            self, project, claude):
        _install, directory = claude
        settle(project, 'RULE-2')
        assert project.rule('RULE-2')['audit']
        assert ('login', 'RULE-2') not in to_read(project)
        assert ('login', 'RULE-2') in to_read(project, again=True)
        # The audit itself, asked to read again, reads RULE-2.
        code, printed = audit(project, again=True)
        assert code == 0, printed
        assert 'RULE-2' in rules_printed(printed), printed
        assert 'RULE-2' in rules_asked(directory)

    # purlin: ai_audit PROOF-122
    @pytest.mark.parametrize('why', [
        'claude exited with an error',
        'claude is not on PATH',
        'claude gave no answer'])
    def test_a_rule_the_model_was_not_reached_for_is_read_again_with_one_call(
            self, claude, monkeypatch, why):
        install, directory = claude
        reached = os.environ['PATH']
        # Each way the model is not reached: `claude` exits 1, no `claude`
        # is on PATH at all, or `claude` prints nothing.
        if why == 'claude exited with an error':
            install(exit_code=1)
        elif why == 'claude is not on PATH':
            monkeypatch.setenv('PATH', os.pathsep.join(
                folder for folder in reached.split(os.pathsep)
                if not shutil.which('claude', path=folder)))
            assert shutil.which('claude') is None
        else:
            install(raw='')
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            audit(made)
            entry = entry_of(made)
            assert entry['verdict'] == 'spot-checked', entry
            assert entry['no_bug'] == [
                'No bug was planted: the model could not be reached: %s.'
                % why], entry
            # Nothing has changed since, and the model now answers.
            assert to_read(made) == [('login', 'RULE-2')]
            monkeypatch.setenv('PATH', reached)
            install()
            code, printed = audit(made)
        assert code == 0, printed
        assert rules_printed(printed) == ['RULE-2'], printed
        # `claude` is started exactly 1 time, and it is asked about RULE-2.
        assert len(fake_claude.calls(directory)) == 1
        assert rules_asked(directory) == ['RULE-2']

    # purlin: ai_audit PROOF-160
    def test_a_rule_whose_call_timed_out_is_read_again_with_one_call(
            self, claude, monkeypatch):
        install, directory = claude
        # `claude` takes 3 seconds and the call is given 1.
        install(sleep=3)
        monkeypatch.setattr(audit_module, 'MODEL_TIMEOUT', 1)
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            audit(made)
            entry = entry_of(made)
            assert entry['verdict'] == 'spot-checked', entry
            assert entry['no_bug'] == [
                'No bug was planted: the model could not be reached: claude '
                'timed out after 1 s.'], entry
            # Nothing has changed since, and the model now answers at once.
            assert to_read(made) == [('login', 'RULE-2')]
            install()
            code, printed = audit(made)
        assert code == 0, printed
        assert rules_printed(printed) == ['RULE-2'], printed
        # `claude` is started exactly 1 time, and it is asked about RULE-2.
        assert len(fake_claude.calls(directory)) == 1
        assert rules_asked(directory) == ['RULE-2']


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------

class TestThePrompt:

    # purlin: ai_audit PROOF-11
    def test_the_prompt_is_the_criteria_then_the_rule_its_proof_and_test(
            self, project):
        prompt = audit_module.model_prompt(project.root,
                                           read(project, 'RULE-2'))
        assert prompt.startswith(criteria_text())
        after = prompt[len(criteria_text()):]
        order = ['login RULE-2',
                 'Invalid credentials return 401 and the body "denied"',
                 'POST /login with a bad password; verify 401 and the body '
                 '"denied"',
                 'test_a_bad_password_is_denied',
                 'assert login("ada", "wrong") == 401']
        at = [after.index(text) for text in order]
        assert at == sorted(at), after

    # purlin: ai_audit PROOF-106
    def test_the_prompt_holds_the_spot_tests_finding_after_the_test(
            self, claude):
        _install, directory = claude
        with passing_project(test_file=CHECKS_NOTHING_TEST) as made:
            settle(made, 'RULE-1')
            audit(made)
        readings = fake_claude.calls(directory)
        assert len(readings) == 1, readings
        prompt = readings[0]['prompt']
        assert 'login RULE-2' in prompt
        source = prompt.index('def test_a_bad_password_is_denied')
        assert prompt.index(CHECKS_NOTHING, source) > source, prompt[-600:]

    # purlin: ai_audit PROOF-114
    def test_the_request_holds_the_scopes_files_and_no_other(self, claude):
        _install, directory = claude
        with passing_project(source=LOGIN_SOURCE) as made:
            write(os.path.join(made.root, '.env'), 'KEY=s3cret\n')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'chore: a settings file')
            settle(made, 'RULE-1')
            audit(made)
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        prompt = calls[0]['prompt']
        assert 'login RULE-2' in prompt
        assert asked_for(calls[0]) == ['PROOF-2'], prompt[-900:]
        assert 'File: src/login.py\n' + LOGIN_SOURCE in prompt, prompt[-900:]
        assert 's3cret' not in prompt
        assert prompt.count('\nFile: ') == 1, prompt[-900:]


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

class TestTheCall:

    # purlin: ai_audit PROOF-82
    def test_the_prompt_goes_on_stdin_and_the_answer_is_read_to_the_end(
            self, project, claude, monkeypatch):
        install, directory = claude
        install(answers=['- read to the end'])
        # The fake is Python: it reads its input as UTF-8, as `claude` does,
        # and not in a Windows console's default character set.
        monkeypatch.setenv('PYTHONUTF8', '1')
        if os.name == 'nt':
            # Windows finds the stand-in by its ending, `claude.cmd`.
            found = audit_module.claude_path()
            assert os.path.normcase(found) == os.path.normcase(
                os.path.join(str(directory), 'claude.cmd')), found
        reading = read(project, 'RULE-2')
        found = audit_module.audit_one(project.root, reading,
                                       criteria_text())
        calls = fake_claude.calls(directory)
        assert found.get('explanation') == ['read to the end'], found
        assert len(calls) == 1, calls
        assert calls[0]['argv'][:7] == ['-p', '--output-format', 'json',
                                        '--max-turns', '1', '--tools', '']
        # The fake reads its standard input to the end before it answers.
        assert calls[0]['prompt'] == audit_module.model_prompt(
            project.root, reading, criteria_text())
        assert not any('Invalid credentials' in part
                       for part in calls[0]['argv'])

    # purlin: ai_audit PROOF-14
    def test_the_call_is_bare_given_300_seconds_and_the_request_on_stdin(
            self, project, tmp_path):
        seen = []
        # The request holds characters outside ASCII, as a rule or a
        # criteria file may.
        criteria = 'criteria: caf\u00e9 \u2192 \u65e5\u672c'
        stdin = str(tmp_path / 'stdin.bin')
        # Stands in for `/bin/claude`: it keeps the bytes of its standard
        # input, read to the end, and answers.
        keeps_stdin = (
            'import json, sys\n'
            'with open(sys.argv[1], "wb") as kept:\n'
            '    kept.write(sys.stdin.buffer.read())\n'
            'print(json.dumps({"result": "- The test reads the status."}))\n')

        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return subprocess.run([sys.executable, '-c', keeps_stdin, stdin],
                                  **kwargs)

        found = audit_module.audit_one(
            project.root, read(project, 'RULE-2'), criteria,
            command='/bin/claude', runner=runner)
        assert found.get('explanation') == ['The test reads the status.'], \
            found
        assert len(seen) == 1, seen
        command, kwargs = seen[0]
        assert command == [
            '/bin/claude', '-p', '--output-format', 'json', '--max-turns',
            '1', '--tools', '', '--strict-mcp-config', '--safe-mode',
            '--setting-sources', '', '--disable-slash-commands',
            '--no-session-persistence', '--system-prompt',
            "You review software tests for Purlin's audit. You have no "
            "tools. Answer in exactly the shape the request gives, and with "
            "nothing else."]
        assert kwargs['timeout'] == 300
        # `input=` writes the prompt and closes stdin behind it.
        request = audit_module.model_prompt(
            project.root, read(project, 'RULE-2'), criteria)
        assert kwargs['input'] == request
        assert 'stdin' not in kwargs
        # What arrived on standard input is the request, every character of
        # it, and nothing else.
        with open(stdin, 'rb') as handle:
            arrived = handle.read().decode('utf-8')
        assert arrived.replace('\r\n', '\n') == request

    # purlin: ai_audit PROOF-112
    def test_claude_is_started_in_an_empty_folder_outside_the_project(
            self, claude):
        _install, directory = claude
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            root = os.path.realpath(made.root)
            code, printed = audit(made)
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert 'login RULE-2' in calls[0]['prompt']
        folder = os.path.realpath(calls[0]['cwd'])
        assert folder != root and not folder.startswith(root + os.sep), folder
        assert calls[0]['listing'] == [], calls[0]['listing']
        assert calls[0]['env'] == '1', calls[0]
        assert not os.path.exists(calls[0]['cwd'])

    # purlin: ai_audit PROOF-113
    def test_one_call_holds_the_bugs_of_all_three_proofs(self, claude):
        _install, directory = claude
        with proofs_project(3) as made:
            assert to_read(made) == [('login', 'RULE-1')]
            code, printed = audit(made)
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert asked_for(calls[0]) == ['PROOF-1', 'PROOF-2', 'PROOF-3']

    # purlin: ai_audit PROOF-55
    def test_six_rules_are_each_asked_once_and_answered_in_order(
            self, project, claude):
        base = read(project, 'RULE-2')
        readings = [dict(base, rule='RULE-%d' % n,
                         rule_text='Rule number %d holds' % n)
                    for n in range(1, 7)]
        asked = []

        class Done(object):
            returncode = 0

        def runner(command, **kwargs):
            rule = re.search(r'^login (RULE-\d)$', kwargs['input'],
                             re.M).group(1)
            asked.append(rule)
            # The later the rule, the sooner it answers.
            time.sleep(0.05 * (7 - int(rule[5:])))
            done = Done()
            done.stdout = json.dumps({'result': '- saw %s' % rule})
            return done

        results = audit_module.audit_all(project.root, readings, 4,
                                         runner=runner)
        assert sorted(asked) == ['RULE-%d' % n for n in range(1, 7)], asked
        assert [found['explanation'] for found in results] == [
            ['saw RULE-%d' % n] for n in range(1, 7)], results
        assert results[0]['explanation'] == ['saw RULE-1']
        assert results[-1]['explanation'] == ['saw RULE-6']

        # The audit run whole over six rules, with nothing of the audit
        # replaced: it starts the `claude` on PATH itself. That `claude`
        # answers the same way, the later the rule the sooner, and keeps one
        # file for each time it is started.
        _install, directory = claude
        starts = os.path.join(str(directory), 'starts')
        os.mkdir(starts)
        with open(os.path.join(str(directory), 'claude'), 'w',
                  encoding='utf-8') as handle:
            handle.write(
                '#!%s\n'
                'import json, os, re, sys, time\n'
                'rule = re.search(r"^login (RULE-\\d)$", sys.stdin.read(),\n'
                '                 re.M).group(1)\n'
                'time.sleep(0.05 * (7 - int(rule[5:])))\n'
                'kept = os.path.join(%r, "%%s-%%d-%%d" %% (\n'
                '    rule, os.getpid(), time.time() * 1e6))\n'
                'with open(kept, "w") as start:\n'
                '    start.write(rule)\n'
                'sys.stdout.write(json.dumps({"result": "- saw %%s" %% rule}))\n'
                % (sys.executable, starts))
        with rules_project(['pass'] * 6) as made:
            code, printed = audit(made)
            entries = [entry_of(made, 'RULE-%d' % n) for n in range(1, 7)]
        assert code == 0, printed
        # `claude` was started exactly once for each rule: six starts, one
        # per rule, and no second request about any of them.
        started = sorted(name.split('-')[0] + '-' + name.split('-')[1]
                         for name in os.listdir(starts))
        assert started == ['RULE-%d' % n for n in range(1, 7)], started
        assert [entry['explanation'] for entry in entries] == [
            ['saw RULE-%d' % n] for n in range(1, 7)], entries


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

class TestTheAnswer:

    # purlin: ai_audit PROOF-20
    def test_the_answer_names_its_model_and_the_criteria_it_was_sent(
            self, project, claude):
        install, directory = claude
        install(model='claude-opus-4-1-20250805')
        found = ask(project)
        assert found['model'] == 'claude-opus-4-1-20250805'
        sent = fake_claude.calls(directory)[0]['prompt']
        assert sent.startswith(criteria_text())
        assert found['criteria'] == hashlib.sha256(
            criteria_text().encode('utf-8')).hexdigest()

    # purlin: ai_audit PROOF-58
    def test_an_answer_naming_no_model_names_unknown(self, project, claude):
        install, _directory = claude
        install(model=None)
        assert ask(project)['model'] == 'unknown'

    # purlin: ai_audit PROOF-21
    def test_the_model_that_wrote_most_is_named(self, project, claude):
        install, _directory = claude
        install(raw=json.dumps({'result': '- The test reads the status.',
                                'modelUsage': {
                                    'claude-haiku-3-5': {'outputTokens': 12},
                                    'claude-opus-4-1': {'outputTokens': 900}}}))
        assert ask(project)['model'] == 'claude-opus-4-1'

    # purlin: ai_audit PROOF-38
    def test_the_explanation_and_the_notes_are_kept_apart(self, project,
                                                          claude):
        install, _directory = claude
        install(answers=['- The test reads the status.\nnotes:\n'
                         '- PROOF-2 holds two cases.'])
        found = ask(project)
        assert found['explanation'] == ['The test reads the status.'], found
        assert found['notes'] == ['PROOF-2 holds two cases.'], found
        assert 'verdict' not in found, found


class TestTheJavaScriptReader:
    """Each case is a tricky test followed by a plain one in one file."""

    NEXT = ('it("the next test", () => {\n'
            '  expect(2).toBe(2);\n'
            '});\n', 'expect(2).toBe(2)')

    def _both(self, tmp_path, first):
        """The source found for the first and the second marked test."""
        text = ('import { it, expect } from "vitest";\n\n'
                '// purlin: rx PROOF-1\n' + first + '\n'
                '// purlin: rx PROOF-2\n' + self.NEXT[0])
        (tmp_path / 'tests').mkdir(exist_ok=True)
        (tmp_path / 'tests' / 'rx.test.ts').write_text(text, encoding='utf-8')
        return [marked_tests.source(str(tmp_path), 'rx', proof,
                                    'tests/rx.test.ts')
                for proof in ('PROOF-1', 'PROOF-2')]

    def _check(self, tmp_path, first, token):
        found, after = self._both(tmp_path, first)
        assert found is not None and after is not None, (found, after)
        assert token in found, found
        assert self.NEXT[1] not in found, found
        assert self.NEXT[1] in after, after
        assert token not in after, after

    # purlin: ai_audit PROOF-9
    def test_an_options_object_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("passes options", () => {\n'
                    '  const out = execSync("ls", { cwd: ".", encoding: '
                    '"utf8" });\n'
                    '  expect(out).toMatch(/./);\n'
                    '});\n', 'expect(out).toMatch')

    # purlin: ai_audit PROOF-67
    def test_an_apostrophe_in_a_title_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("cd\'s into a sibling", () => {\n'
                    '  expect(1).toBe(1);\n'
                    '});\n', 'expect(1).toBe(1)')

    # purlin: ai_audit PROOF-10
    def test_a_division_across_a_line_does_not_cut_a_body(self, tmp_path):
        self._check(tmp_path,
                    'it("division across a line", () => {\n'
                    '  const s = "a" +\n'
                    '    / 2;\n'
                    '  expect(s).toBe("a");\n'
                    '});\n', 'expect(s).toBe("a")')


# ---------------------------------------------------------------------------
# The verdict and the last line
# ---------------------------------------------------------------------------

def _rules_spec(count):
    """A spec of `count` rules, one proof each."""
    lines = ['# Feature: login', '',
             '> Description: Signing in, in %d steps.' % count,
             '> Scope: src/login.py', '', '## Rules', '']
    lines += ['- RULE-%d: Step %d holds' % (n, n) for n in range(1, count + 1)]
    lines += ['', '## Proof', '']
    lines += ['- PROOF-%d (RULE-%d): Take step %d; verify it returns %d'
              % (n, n, n, n) for n in range(1, count + 1)]
    return '\n'.join(lines) + '\n'


def _rules_tests(count):
    """A test file with one passing test per proof of `_rules_spec`."""
    text = 'import pytest\n'
    for n in range(1, count + 1):
        text += ('\n\n# purlin: login PROOF-%d\n'
                 'def test_step_%d():\n'
                 '    assert %d + 0 == %d\n' % (n, n, n, n))
    return text


def _rules_evidence(project, results, rule_of=None):
    """A local section naming `test_step_<n>` with `results[n - 1]`, each
    proof under the rule of its own number, or under `rule_of`."""
    rel = '.purlin/evidence/local/login.json'
    os_name = purlin_evidence.host_os()
    data = {'schema': purlin_evidence.SCHEMA, 'feature': 'login',
            'source': 'local', 'spec': 'specs/auth/login.md',
            'audit': {'rules': {}},
            'platforms': {os_name: {
                'commit': project.head(), 'dirty': False,
                'at': '2026-09-13T12:00:00Z', 'runner': 'ada',
                'email': 'ada@example.com', 'machine': 'jane-laptop',
                'fingerprint': purlin_fingerprint.fingerprint(project.root,
                                                              'login'),
                'rules': {},
                'proofs': [{'id': 'PROOF-%d' % n,
                            'rule': rule_of or 'RULE-%d' % n,
                            'result': result, 'env': None, 'manual': False,
                            'test': 'tests/test_login.py::test_step_%d' % n}
                           for n, result in enumerate(results, 1)]}}}
    write(os.path.join(project.root, *rel.split('/')),
          json.dumps(data, indent=2, sort_keys=True))
    git(project.root, 'add', '-A')
    git(project.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')


@contextlib.contextmanager
def rules_project(results, weak=(), strong=()):
    """A project of `len(results)` rules whose tests read `results`, with an
    audit entry reading `weak` or `strong` for each rule named."""
    made = Project(spec=_rules_spec(len(results)))
    try:
        made.edit_test(_rules_tests(len(results)))
        _rules_evidence(made, results)
        for rule in weak:
            settle(made, rule, findings=['%s: the test checks nothing.' % rule])
        for rule in strong:
            settle(made, rule)
        git(made.root, 'add', '-A')
        git(made.root, 'commit', '-q', '-m', 'purlin: audit at abc1234')
        yield made
    finally:
        made.close()


# `step(n)` answers `n`, each on a line of its own.
STEPS_SOURCE = ('def step(n):\n'
                '    if n == 1:\n'
                '        return 1\n'
                '    if n == 2:\n'
                '        return 2\n'
                '    return n\n')


@contextlib.contextmanager
def proofs_project(count):
    """A project whose one rule, `RULE-1`, has `count` proofs, each with a
    passing test of its own that calls `step`."""
    lines = ['# Feature: login', '', '> Description: Signing in, in steps.',
             '> Scope: src/login.py', '', '## Rules', '',
             '- RULE-1: Every step holds', '', '## Proof', '']
    lines += ['- PROOF-%d (RULE-1): Take step %d; verify it returns %d'
              % (n, n, n) for n in range(1, count + 1)]
    tests = 'from src.login import step\n'
    for n in range(1, count + 1):
        tests += ('\n\n# purlin: login PROOF-%d\n'
                  'def test_step_%d():\n'
                  '    assert step(%d) == %d\n' % (n, n, n, n))
    made = Project(spec='\n'.join(lines) + '\n',
                   config={'tests': [suites.pytest_suite()]})
    try:
        write(os.path.join(made.root, 'src', 'login.py'), STEPS_SOURCE)
        write(os.path.join(made.root, 'src', '__init__.py'), '')
        made.edit_test(tests)
        _rules_evidence(made, ['pass'] * count, rule_of='RULE-1')
        yield made
    finally:
        made.close()


WINDOWS_SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in on Windows.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-8: A path with a drive letter is accepted\n\n'
    '## Proof\n\n'
    '- PROOF-38 (RULE-8): Sign in from `C:\\Users\\ada`; verify 200 '
    '@env(windows)\n'
)

WINDOWS_TEST = (
    'from src.login import login\n'
    '\n'
    '\n'
    '# purlin: login PROOF-38\n'
    'def test_a_drive_letter_is_accepted():\n'
    '    assert login("C:\\\\Users\\\\ada", "secret") == 200\n'
)


class TestTheVerdict:

    # purlin: ai_audit PROOF-95
    def test_a_spot_finding_makes_the_rule_weak_though_its_bug_was_caught(
            self, claude):
        install, directory = claude
        install(answers=[{'PROOF-2': bug('    return 401',
                                         '    raise RuntimeError("planted")'),
                          'reading': '- The test calls login.'}])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=CHECKS_NOTHING_TEST) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry
        assert entry['verdict'] == 'weak', entry
        assert CHECKS_NOTHING in entry['findings'], entry
        assert len(fake_claude.calls(directory)) == 1

    # purlin: ai_audit PROOF-96
    def test_a_bug_that_survives_makes_the_rule_weak_with_its_finding(
            self, claude):
        install, _directory = claude
        install(answers=[{'PROOF-2': bug('    return 401', '    return 200'),
                          'reading': '- The test reads no status.'}])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=NOT_NONE_TEST) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['breaks']['PROOF-2']['result'] == 'survived', entry
        assert entry['verdict'] == 'weak', entry
        assert entry['findings'] == [
            'PROOF-2: the test still passes when src/login.py:12 reads '
            '"return 200"',
            'PROOF-2: the AI says this breaks: a wrong password; the proof '
            'says 401; the changed code gives 200'], entry

    # purlin: ai_audit PROOF-97
    def test_no_spot_finding_and_every_bug_caught_is_strong_whatever_claude_says(
            self, claude):
        install, directory = claude
        install(answers=[{'PROOF-2': bug('    return 401', '    return 200'),
                          'reading': '- This rule is weak.'}])
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert len(fake_claude.calls(directory)) == 1
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry
        assert entry['findings'] == [], entry
        assert entry['no_bug'] == [], entry
        assert entry['explanation'] == ['This rule is weak.'], entry
        assert entry['verdict'] == 'strong', entry

    # purlin: ai_audit PROOF-118
    def test_no_spot_finding_and_no_bug_to_plant_is_spot_checked(self, claude):
        install, _directory = claude
        install(answers=[{'PROOF-2': 'no break: the proof names no value the '
                                     'code computes'}])
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['findings'] == [], entry
        assert entry['verdict'] == 'spot-checked', entry
        assert entry['no_bug'] == [
            'No bug was planted: the model found no change that would break '
            'PROOF-2: the proof names no value the code computes.'], entry

    # purlin: ai_audit PROOF-124
    def test_a_test_that_ends_in_an_error_leaves_the_rule_spot_checked(
            self, claude):
        install, _directory = claude
        install(answers=[{'PROOF-2': bug('    return 401',
                                         '    raise KeyError(user)')}])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=FIXTURE_USES_LOGIN_TEST) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['breaks']['PROOF-2']['result'] == 'not run', entry
        assert entry['verdict'] == 'spot-checked', entry
        assert entry['no_bug'] == [
            'A bug was planted for PROOF-2 and its test ended in an error, '
            'not a failure.'], entry

    # purlin: ai_audit PROOF-98
    def test_the_findings_and_the_explanation_are_kept_apart(self, claude):
        install, _directory = claude
        # The answer is that one line and nothing else.
        install(answers=['- The test calls login and reads no status.'])
        with passing_project(test_file=CHECKS_NOTHING_TEST) as made:
            settle(made, 'RULE-1')
            audit(made)
            entry = entry_of(made)
        assert entry['findings'] == [CHECKS_NOTHING], entry
        assert entry['explanation'] == [
            'The test calls login and reads no status.'], entry

    # purlin: ai_audit PROOF-99
    def test_four_strong_of_five_is_eighty_percent(self, claude):
        with rules_project(['pass'] * 5, weak=['RULE-3'],
                           strong=['RULE-1', 'RULE-2', 'RULE-4',
                                   'RULE-5']) as made:
            code, printed = audit(made)
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 4 of 5 rules strong (80%): 4 strong, 1 weak.'), \
            printed

    # purlin: ai_audit PROOF-104
    def test_a_rule_whose_test_fails_is_not_counted(self, claude):
        with rules_project(['pass', 'pass', 'pass', 'pass', 'fail'],
                           weak=['RULE-4'],
                           strong=['RULE-1', 'RULE-2', 'RULE-3']) as made:
            assert made.rule('RULE-5')['cells']['passed']['word'] == 'failed'
            code, printed = audit(made)
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 3 of 4 rules strong (75%): 3 strong, 1 weak.'), \
            printed

    # purlin: ai_audit PROOF-137
    def test_the_last_line_counts_a_rule_with_a_hand_check_as_the_status_does(
            self, claude):
        spec = _rules_spec(2) + '- PROOF-3 (RULE-2): Read the page @manual\n'
        made = Project(spec=spec)
        try:
            made.edit_test(_rules_tests(2))
            _rules_evidence(made, ['pass', 'pass'])
            settle(made, 'RULE-1')
            settle(made, 'RULE-2')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: audit at abc1234')
            cells = made.rule('RULE-2')['cells']
            assert cells['passed']['word'] == 'passed', cells
            assert cells['strong']['word'] == 'checked at sign-off', cells
            code, printed = audit(made)
            status = audit_run.summary_module.audit_line(
                made.payload()['summary']['audit'])
        finally:
            made.close()
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 1 of 1 rules strong (100%): 1 strong.'), printed
        assert printed.splitlines()[-1] == status

    # purlin: ai_audit PROOF-100
    def test_a_caught_bug_is_kept_while_its_test_and_code_stand(self, claude):
        _install, directory = claude
        with passing_project(source=LOGIN_SOURCE) as made:
            # The bug planted for PROOF-2 was caught, for this test and code.
            settle(made, 'RULE-2')
            settle(made, 'RULE-1')
            # Only RULE-2's text changes, so the audit reads it again.
            made.spec(SPEC.replace('return 401 and the body',
                                   'return 401 with the body'))
            made.evidence()
            assert to_read(made) == [('login', 'RULE-2')]
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert asked_for(calls[0]) == [], calls[0]['prompt'][-600:]
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry
        assert entry['breaks']['PROOF-2']['after'] == '    return 200', entry

    # purlin: ai_audit PROOF-136
    def test_a_kept_entry_with_no_aim_or_case_is_written_back_with_both(
            self, claude):
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-2')
            settle(made, 'RULE-1')
            kept = entry_of(made)['breaks']['PROOF-2']
            assert 'aim' not in kept and 'case' not in kept, kept
            # Only RULE-2's text changes, so the audit reads it again.
            made.spec(SPEC.replace('return 401 and the body',
                                   'return 401 with the body'))
            made.evidence()
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        made_now = entry['breaks']['PROOF-2']
        assert made_now['result'] == 'caught', entry
        assert made_now.get('aim') == 'plain', made_now
        assert made_now.get('case') == '', made_now

    # purlin: ai_audit PROOF-115
    def test_a_changed_test_has_its_bug_asked_for_again(self, claude):
        _install, directory = claude
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-2')
            settle(made, 'RULE-1')
            before = entry_of(made)['breaks']['PROOF-2']['break_key']
            assert to_read(made) == []
            made.edit_test(TEST_FILE.replace('== 401', '== 403'))
            made.evidence()
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert 'login RULE-2' in calls[0]['prompt']
        assert asked_for(calls[0]) == ['PROOF-2']
        after = entry['breaks']['PROOF-2']['break_key']
        assert after and after != before, entry

    # purlin: ai_audit PROOF-102
    def test_an_anchors_rule_gets_no_planted_bug(self, claude):
        _install, directory = claude
        with passing_project() as made:
            as_anchor(made)
            made.audit('RULE-1', no_bug=[
                "No bug was planted: no bug is planted for an anchor's "
                "rule."])
            assert made.rule('RULE-2')['cells']['passed']['word'] == 'passed'
            assert to_read(made) == [('login', 'RULE-2')]
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert asked_for(calls[0]) == [], calls[0]['prompt'][-600:]
        assert entry['verdict'] == 'spot-checked', entry
        assert entry['no_bug'] == [
            "No bug was planted: no bug is planted for an anchor's rule."], \
            entry
        assert entry['breaks'] == {}, entry

    # purlin: ai_audit PROOF-159
    def test_an_audit_of_an_anchor_alone_ends_on_what_it_found(self, claude):
        with passing_project() as made:
            as_anchor(made)
            code, printed = audit(made)
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 2 spot-checked.'), printed

    # purlin: ai_audit PROOF-116
    def test_a_proof_tagged_for_another_system_gets_no_planted_bug(
            self, claude, monkeypatch):
        _install, directory = claude
        if purlin_evidence.host_os() == 'windows':
            # The case is a machine that is not Windows.
            monkeypatch.setattr(purlin_evidence, 'host_os', lambda: 'linux')
        here = purlin_evidence.os_word(purlin_evidence.host_os())
        made = Project(spec=WINDOWS_SPEC,
                       config={'tests': [suites.pytest_suite()]})
        try:
            made.edit_test(WINDOWS_TEST)
            rel = '.purlin/evidence/local/login.json'
            write(os.path.join(made.root, *rel.split('/')), json.dumps({
                'schema': purlin_evidence.SCHEMA, 'feature': 'login',
                'source': 'local', 'spec': 'specs/auth/login.md',
                'audit': {'rules': {}},
                'platforms': {'windows': {
                    'commit': made.head(), 'dirty': False,
                    'at': '2026-09-13T12:00:00Z', 'runner': 'ada',
                    'email': 'ada@example.com', 'machine': 'build-7',
                    'fingerprint': purlin_fingerprint.fingerprint(made.root,
                                                                  'login'),
                    'rules': {},
                    'proofs': [{'id': 'PROOF-38', 'rule': 'RULE-8',
                                'result': 'pass', 'env': 'windows',
                                'manual': False,
                                'test': 'tests/test_login.py::'
                                        'test_a_drive_letter_is_accepted'}]}}},
                indent=2, sort_keys=True))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
            assert made.rule('RULE-8')['cells']['passed']['word'] == 'passed'
            assert to_read(made) == [('login', 'RULE-8')]
            code, printed = audit(made)
            entry = entry_of(made, 'RULE-8')
        finally:
            made.close()
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert len(calls) == 1, calls
        assert asked_for(calls[0]) == [], calls[0]['prompt'][-600:]
        assert entry['verdict'] == 'spot-checked', entry
        assert entry['breaks'] == {}, entry
        assert entry['no_bug'] == [
            'No bug was planted: PROOF-38 needs Windows, and this machine is '
            '%s.' % here], entry

    # purlin: ai_audit PROOF-120
    def test_a_proof_the_reply_leaves_out_has_no_bug_and_the_other_is_planted(
            self, claude):
        install, directory = claude
        install(answers=[{'PROOF-1': bug('        return 1',
                                         '        return 0'),
                          'reading': '- The first step is checked.'}])
        with proofs_project(2) as made:
            code, printed = audit(made)
            entry = entry_of(made, 'RULE-1')
        assert code == 0, printed
        calls = fake_claude.calls(directory)
        assert asked_for(calls[0]) == ['PROOF-1', 'PROOF-2']
        assert entry['verdict'] == 'strong', entry
        assert entry['breaks']['PROOF-1']['result'] == 'caught', entry
        assert entry['no_bug'] == [
            "No bug was planted: the model's answer for PROOF-2 could not be "
            "used: it holds none."], entry


# ---------------------------------------------------------------------------
# When the model cannot be reached
# ---------------------------------------------------------------------------

class TestWhenTheModelCannotBeReached:

    # purlin: ai_audit PROOF-23
    def test_no_claude_on_the_path_starts_nothing(self, project, claude,
                                                  monkeypatch, tmp_path):
        _install, directory = claude
        empty = tmp_path / 'empty'
        empty.mkdir()
        monkeypatch.setenv('PATH', str(empty))
        results = audit_module.audit_all(project.root,
                                         [read(project, 'RULE-1'),
                                          read(project, 'RULE-2')])
        assert results == [{'why': 'claude is not on PATH'}] * 2
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-24
    def test_a_non_zero_exit_is_named(self, project, claude):
        install, _directory = claude
        install(exit_code=1, answers=['- The test reads the status.'])
        assert ask(project) == {'why': 'claude exited with an error'}

    # purlin: ai_audit PROOF-25
    def test_a_call_past_its_limit_is_named(self, project, claude,
                                            monkeypatch):
        install, _directory = claude
        install(sleep=3)
        monkeypatch.setattr(audit_module, 'MODEL_TIMEOUT', 1)
        assert ask(project) == {'why': 'claude timed out after 1 s'}

    UNREACHED = ('The model could not be reached: claude exited with an '
                 'error.%s Run purlin:audit again.')

    @staticmethod
    def _entries(made):
        """Every audit entry the local evidence of `login` holds."""
        path = os.path.join(made.root, '.purlin', 'evidence', 'local',
                            'login.json')
        with open(path, encoding='utf-8') as handle:
            return (json.load(handle).get('audit') or {}).get('rules') or {}

    # purlin: ai_audit PROOF-108
    def test_a_rule_that_passed_the_spot_tests_alone_is_spot_checked(
            self, claude):
        install, directory = claude
        install(exit_code=1, answers=['- The test reads the status.'])
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            assert to_read(made) == [('login', 'RULE-2')]
            code, printed = audit(made)
            entries = self._entries(made)
        assert code == 0, printed
        assert fake_claude.calls(directory), 'the fake claude was not asked'
        assert sorted(entries) == ['RULE-1', 'RULE-2'], entries
        assert entries['RULE-2']['verdict'] == 'spot-checked', entries
        assert entries['RULE-2']['breaks'] == {}, entries
        lines = printed.splitlines()
        assert 'login RULE-2   spot-checked' in lines, printed
        # Once: no second copy of the line, indented or not. The line under
        # the rule says `the model could not be reached`, in lower case.
        assert [line for line in lines
                if 'The model could not be reached' in line] == [
            self.UNREACHED % ' 1 rule is spot-checked alone.'], printed

    # purlin: ai_audit PROOF-117
    def test_a_claude_that_answers_nothing_is_the_model_not_reached(
            self, claude):
        install, directory = claude
        install(raw='')
        with passing_project(source=LOGIN_SOURCE) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert len(fake_claude.calls(directory)) == 1
        assert entry['verdict'] == 'spot-checked', entry
        assert ('The model could not be reached: claude gave no answer. 1 '
                'rule is spot-checked alone. Run purlin:audit again.'
                ) in printed.splitlines(), printed

    # purlin: ai_audit PROOF-109
    def test_a_spot_finding_is_still_written_weak(self, claude):
        install, _directory = claude
        install(exit_code=1, answers=['- The test calls login.'])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=CHECKS_NOTHING_TEST) as made:
            settle(made, 'RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['verdict'] == 'weak', entry
        assert entry['findings'] == [CHECKS_NOTHING], entry
        assert entry['breaks'] == {}, entry
        assert entry['model'] == 'unknown', entry
        lines = printed.splitlines()
        assert 'login RULE-2   weak' in lines, printed
        assert [line for line in lines if 'could not be reached' in line
                and not line.startswith(' ')] == [
            self.UNREACHED % ''], printed

    # purlin: ai_audit PROOF-110
    def test_two_rules_are_spot_checked_and_none_is_counted_strong(
            self, claude):
        install, _directory = claude
        install(exit_code=1, answers=['- The test reads the status.'])
        with passing_project(source=LOGIN_SOURCE) as made:
            assert to_read(made) == [('login', 'RULE-1'), ('login', 'RULE-2')]
            code, printed = audit(made)
            entries = self._entries(made)
        assert code == 0, printed
        assert {rule: entry['verdict'] for rule, entry in entries.items()} == {
            'RULE-1': 'spot-checked', 'RULE-2': 'spot-checked'}, entries
        assert [line for line in printed.splitlines()
                if 'could not be reached' in line
                and not line.startswith(' ')] == [
            self.UNREACHED % ' 2 rules are spot-checked alone.'], printed

    # purlin: ai_audit PROOF-123
    def test_two_spot_checked_rules_are_counted_and_none_strong(self, claude):
        install, _directory = claude
        install(exit_code=1, answers=['- The test reads the status.'])
        with passing_project(source=LOGIN_SOURCE) as made:
            assert to_read(made) == [('login', 'RULE-1'), ('login', 'RULE-2')]
            code, printed = audit(made)
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 0 of 2 rules strong (0%): 0 strong, '
            '2 spot-checked.'), printed

    # purlin: ai_audit PROOF-119
    def test_a_kept_bug_that_survived_still_makes_the_rule_weak(self, claude):
        install, _directory = claude
        install(exit_code=1)
        with passing_project(source=LOGIN_SOURCE,
                             test_file=NOT_NONE_TEST) as made:
            settle(made, 'RULE-1')
            settle(made, 'RULE-2', result='survived')
            code, printed = audit(made, again=True)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['verdict'] == 'weak', entry
        assert entry['findings'] == [
            'PROOF-2: the test still passes when src/login.py:12 reads '
            '"return 200"'], entry


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

class TestWriting:

    # purlin: ai_audit PROOF-72
    def test_asking_the_model_writes_no_file(self, project, claude):
        install, directory = claude
        install(answers=['- The test reads the status.'])
        # A run's log sits under `.purlin/runtime/`, so the walk reaches it.
        write(os.path.join(project.root, '.purlin', 'runtime', 'run.log'),
              'a run\n')
        before = files_under_purlin(project.root)
        assert any('runtime' in path for path in before), before
        found = audit_module.audit_all(project.root,
                                       [read(project, 'RULE-2')])
        assert found[0]['explanation'] == ['The test reads the status.']
        assert len(fake_claude.calls(directory)) == 1
        assert files_under_purlin(project.root) == before

    # purlin: ai_audit PROOF-73
    def test_printing_the_feature_writes_no_file(self, project, capsys):
        write(os.path.join(project.root, '.purlin', 'runtime', 'run.log'),
              'a run\n')
        before = files_under_purlin(project.root)
        code, printed = command(project, capsys, '--feature', 'login')
        assert code == 0
        assert 'login RULE-1' in printed and 'login RULE-2' in printed
        assert files_under_purlin(project.root) == before


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    # purlin: ai_audit PROOF-74
    def test_an_unknown_option_exits_two(self, capsys):
        assert audit_module.main(['--nope']) == 2
        assert 'ai_audit.py: unexpected argument --nope' in \
            capsys.readouterr().err.splitlines()

    # purlin: ai_audit PROOF-76
    def test_an_unknown_rule_exits_one(self, project, capsys):
        code, printed = command(project, capsys, '--feature', 'login',
                                '--rule', 'RULE-99')
        assert code == 1
        assert printed == ('login RULE-99 is not a rule any spec has. Run '
                           'purlin:status login to see its rules.\n'), printed

    # purlin: ai_audit PROOF-81
    def test_a_settings_file_that_cannot_be_read_stops_it(self, project,
                                                          capsys):
        config = os.path.join(project.root, '.purlin', 'config.json')
        with open(config, 'w', encoding='utf-8') as handle:
            handle.write(TRAILING_COMMA)
        before = files_under_purlin(project.root)
        code, printed = command(project, capsys, '--feature', 'login')
        assert code == 1
        # The JSON reader's own words and line, which differ by Python version.
        with pytest.raises(ValueError) as reader:
            json.loads(TRAILING_COMMA)
        assert printed == (
            '.purlin/config.json cannot be read: %s at line %d. Fix the file '
            'by hand; nothing ran and nothing was saved.\n'
            % (reader.value.msg, reader.value.lineno)), printed
        assert files_under_purlin(project.root) == before

    # purlin: ai_audit PROOF-29
    def test_the_printed_rule_names_what_the_audit_found(self, project,
                                                          capsys):
        project.audit('RULE-2', findings=[FINDING])
        code, printed = command(project, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        lines = printed.splitlines()
        assert lines[0] == 'login RULE-2', printed
        for line in ('  Invalid credentials return 401 and the body "denied"',
                     '  PROOF-2: POST /login with a bad password; verify 401 '
                     'and the body "denied"',
                     '  PROOF-2  tests/test_login.py::'
                     'test_a_bad_password_is_denied',
                     '        assert login("ada", "wrong") == 401'):
            assert line in lines, (line, printed)
        found = lines[lines.index('What the audit found') + 1:]
        assert found[:3] == ['  Weak.', '  %s' % FINDING, READ_BY], printed
        assert not [line for line in lines
                    if line.strip().startswith('Note:')], printed

    # purlin: ai_audit PROOF-111
    def test_the_printed_rule_holds_the_explanation_under_the_finding(
            self, project, capsys):
        explanation = 'The test calls login and reads no status.'
        rel = project.audit('RULE-2', findings=[FINDING])
        path = os.path.join(project.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        data['audit']['rules']['RULE-2']['explanation'] = [explanation]
        write(path, json.dumps(data, indent=2, sort_keys=True))
        code, printed = command(project, capsys, '--feature', 'login',
                                '--rule', 'RULE-2')
        assert code == 0
        lines = printed.splitlines()
        found = lines[lines.index('What the audit found') + 1:]
        assert found[:4] == ['  Weak.', '  %s' % FINDING,
                             '    %s' % explanation, READ_BY], printed

    # purlin: ai_audit PROOF-87
    def test_a_proof_with_no_marked_test_prints_no_test_yet_under_test(
            self, capsys):
        # RULE-3's one proof, PROOF-3, has no test marked for it.
        spec = SPEC.replace(
            '- RULE-2:', '- RULE-3: A session ends after an hour\n- RULE-2:'
        ) + '- PROOF-3 (RULE-3): A session an hour old is refused\n'
        with passing_project(spec=spec) as made:
            code, printed = command(made, capsys, '--feature', 'login',
                                    '--rule', 'RULE-3')
        assert code == 0, printed
        lines = printed.splitlines()
        assert lines[lines.index('Test') + 1] == (
            '  No test yet. Run purlin:build login.'), printed

    # purlin: ai_audit PROOF-33
    def test_the_script_runs_as_a_command_and_starts_no_claude(self, project,
                                                               claude):
        _install, directory = claude
        result = subprocess.run(
            [sys.executable, AI_AUDIT_PY, '--feature', 'login', '--rule',
             'RULE-1', '--project-root', project.root],
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout.splitlines()[0] == 'login RULE-1'
        assert fake_claude.calls(directory) == []


# ---------------------------------------------------------------------------
# The bug aimed past the test, on the sample lab project
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def lab(tmp_path_factory):
    """The sample lab project, audited twice with the fake `claude`
    answering what `sample_lab.REPLY` holds."""
    return sample_lab.audited(tmp_path_factory.mktemp('lab'))


def flat(text):
    """`text` with each run of white space, line ends included, as one
    space, so a sentence the request wraps is found whole."""
    return ' '.join(text.split())


CASE_5 = ('a sample collected at 2026-03-01T08:00 and received at '
          '2026-03-02T09:30; the proof names an age of 25 hours; the changed '
          'code gives 26 hours')
SURVIVED_5 = ('PROOF-5: the test still passes when src/intake.py:17 reads '
              '"return int(round(seconds / 3600))"')
AI_SAYS_5 = 'PROOF-5: the AI says this breaks: ' + CASE_5


class TestTheBugAimedPastTheTest:

    @staticmethod
    def _asked(lab):
        """The request for `RULE-3` from where it asks for the bug, flat."""
        request = lab.request(lab.first, 'RULE-3')
        source = request.index('def test_age_is_whole_hours')
        return flat(request[request.index(
            'Plant one bug for each of: PROOF-5.\n', source):])

    # purlin: ai_audit PROOF-125
    def test_the_request_says_the_test_is_shown_and_the_case_must_change(
            self, lab):
        asked = self._asked(lab)
        assert asked.startswith('Plant one bug for each of: PROOF-5. Each '
                                "proof's test is shown above."), asked[:200]
        assert ('the case the proof names gives a different result from the '
                'one it names') in asked, asked[:600]

    # purlin: ai_audit PROOF-126
    def test_the_request_says_to_choose_the_change_the_test_would_miss(
            self, lab):
        assert ("Choose the change the proof's test, as it is written, is "
                'most likely to miss: a value it never compares, a case other '
                "than the proof's, an expected value taken from the code."
                ) in self._asked(lab)

    # purlin: ai_audit PROOF-127
    def test_the_request_asks_for_a_plain_bug_where_the_test_leaves_no_way(
            self, lab):
        asked = self._asked(lab)
        assert ("Where the test checks the proof's case and its result, make "
                'the plainest such change.') in asked, asked[:900]
        assert ("Never a change that leaves the proof's case as it was, and "
                'no comment about the bug.') in asked, asked[:900]

    # purlin: ai_audit PROOF-128
    def test_the_request_shows_a_part_with_its_aim_and_its_case(self, lab):
        request = lab.request(lab.first, 'RULE-3')
        assert ('\n=== PROOF-5 ===\n'
                'aim: <past the test, or plain>\n'
                "case: <the proof's case; the result the proof names; the "
                'result the changed code gives>\n'
                'file: <the path, as given above>\n') in request, \
            request[-900:]

    # purlin: ai_audit PROOF-129
    def test_the_entry_of_a_bug_holds_its_aim_and_its_case(self, lab):
        assert sample_lab.REPLY['PROOF-5'].startswith(
            'aim: past the test\ncase: %s\n' % CASE_5)
        made = lab.first['entries']['RULE-3']['breaks']['PROOF-5']
        assert made['aim'] == 'past the test', made
        assert made['case'] == CASE_5, made

    # purlin: ai_audit PROOF-130
    def test_the_entry_of_a_plain_bug_reads_plain(self, lab):
        assert sample_lab.REPLY['PROOF-6'].startswith('aim: plain\n')
        made = lab.first['entries']['RULE-4']['breaks']['PROOF-6']
        assert made['aim'] == 'plain', made

    # purlin: ai_audit PROOF-131
    def test_a_bug_in_the_helper_the_test_trusts_survives(self, lab):
        # The test's expected age is what the code's own helper answers.
        assert ("assert record['age_hours'] == age_hours(collected, received)"
                ) in lab.request(lab.first, 'RULE-3')
        entry = lab.first['entries']['RULE-3']
        assert entry['breaks']['PROOF-5']['after'] == (
            '    return int(round(seconds / 3600))'), entry
        assert entry['breaks']['PROOF-5']['result'] == 'survived', entry
        assert entry['verdict'] == 'weak', entry
        assert 'sample_intake RULE-3   weak' in lab.first['lines']
        assert entry['findings'][0] == SURVIVED_5, entry

    # purlin: ai_audit PROOF-132
    def test_the_case_the_ai_named_is_printed_on_the_line_after_the_finding(
            self, lab):
        under = lab.under(lab.first, 'RULE-3')
        at = under.index('  ' + SURVIVED_5)
        assert under[at + 1] == '  ' + AI_SAYS_5, under

    # purlin: ai_audit PROOF-133
    def test_the_second_finding_carries_the_models_case_word_for_word(
            self, lab):
        entry = lab.first['entries']['RULE-2']
        made = entry['breaks']['PROOF-3']
        assert made['before'] == ('        self.received[barcode] = record\n'
                                  '        return record'), made
        assert made['after'] == '        return record', made
        assert made['result'] == 'survived', made
        assert sample_lab.CASE_3.endswith(
            "never stores it, so the bench's `received` stays empty")
        assert len(entry['findings']) == 2, entry
        assert entry['findings'][0].startswith(
            'PROOF-3: the test still passes when src/intake.py:'), entry
        assert entry['findings'][1] == (
            'PROOF-3: the AI says this breaks: ' + sample_lab.CASE_3), entry

    # purlin: ai_audit PROOF-134
    def test_a_kept_bug_that_survived_adds_both_findings_again(self, lab):
        assert lab.again['code'] == 0, lab.again['lines']
        assert len(lab.again['calls']) == 8, len(lab.again['calls'])
        assert 'Plant one bug' not in lab.request(lab.again, 'RULE-3')
        entry = lab.again['entries']['RULE-3']
        assert entry['breaks']['PROOF-5']['result'] == 'survived', entry
        assert entry['findings'] == [SURVIVED_5, AI_SAYS_5], entry
        assert lab.first['entries']['RULE-3']['findings'] == [
            SURVIVED_5, AI_SAYS_5]
        under = lab.under(lab.again, 'RULE-3')
        assert under[:2] == ['  ' + SURVIVED_5, '  ' + AI_SAYS_5], under

    # purlin: ai_audit PROOF-135
    def test_a_bug_the_test_catches_adds_no_finding(self, lab):
        # The test hands in the proof's own case and reads its result.
        request = lab.request(lab.first, 'RULE-4')
        assert "at('2026-03-04T09:00'))" in request
        assert sample_lab.REPLY['PROOF-6'].startswith('aim: plain\n')
        entry = lab.first['entries']['RULE-4']
        assert entry['breaks']['PROOF-6']['after'] == 'MAX_AGE_HOURS = 73'
        assert entry['breaks']['PROOF-6']['result'] == 'caught', entry
        assert entry['verdict'] == 'strong', entry
        assert 'sample_intake RULE-4   strong' in lab.first['lines']
        assert entry['findings'] == [], entry
        assert [line for line in lab.first['lines']
                if 'PROOF-6' in line] == [], lab.first['lines']


# ---------------------------------------------------------------------------
# Settling a finding: `--settle`, on the sample lab and the login project
# ---------------------------------------------------------------------------

ROUNDED = 'return int(round(seconds / 3600))'
NOW_CATCHES_5 = ('  PROOF-5: the test now catches the bug it missed at '
                 'src/intake.py:17.')
DROPPED_5 = ('  PROOF-5: the bug at src/intake.py:17 did not break what the '
             'proof says.')
TWO_SURVIVED = "two planted bugs left the proof's check passing"
NO_BUG_CAUGHT_5 = 'No bug was caught for PROOF-5: %s.' % TWO_SURVIVED


@pytest.fixture(scope='module')
def built_lab(tmp_path_factory):
    """The sample lab, built and never audited: `(root, fake claude)`."""
    folder = str(tmp_path_factory.mktemp('built'))
    return (sample_lab.build(folder),
            fake_claude.install(os.path.join(folder, 'claude')))


@pytest.fixture(scope='module')
def strengthened(tmp_path_factory):
    """`RULE-3` settled after its test was changed to expect `25`."""
    return sample_lab.settled(tmp_path_factory.mktemp('strengthened'),
                              change=sample_lab.strengthen)


@pytest.fixture(scope='module')
def second_caught(tmp_path_factory):
    """`RULE-3` settled with its test as it was, and a second bug that
    test catches."""
    return sample_lab.settled(tmp_path_factory.mktemp('second-caught'),
                              answers=[sample_lab.SECOND_CAUGHT])


@pytest.fixture(scope='module')
def second_survived(tmp_path_factory):
    """`RULE-3` settled with its test as it was, and a second bug that
    survives too; then every rule read again, with nothing changed."""
    made = sample_lab.settled(tmp_path_factory.mktemp('second-survived'),
                              answers=[sample_lab.SECOND_SURVIVES])
    fake_claude.install(made.directory)
    previous = os.environ['PATH']
    os.environ['PATH'] = made.directory + os.pathsep + previous
    try:
        code, lines = sample_lab.audit(made.root, again=True)
    finally:
        os.environ['PATH'] = previous
    made.again = {'code': code, 'lines': lines,
                  'entries': sample_lab.entries(made.root),
                  'calls': fake_claude.calls(made.directory)}
    return made


@pytest.fixture(scope='module')
def two_rules(tmp_path_factory):
    """`RULE-2` and `RULE-4` named with `--settle`, nothing changed, and a
    model that names no bug."""
    return sample_lab.settled(tmp_path_factory.mktemp('two-rules'),
                              rules=('RULE-2', 'RULE-4'))


@contextlib.contextmanager
def weak_login(claude):
    """The login project with a bug kept as `survived` for `PROOF-2`, whose
    test reads no status; the fake then answers that it plants no bug."""
    install, directory = claude
    install(answers=[{'PROOF-2': bug('    return 401', '    return 200')}])
    with passing_project(source=LOGIN_SOURCE,
                         test_file=NOT_NONE_TEST) as made:
        settle(made, 'RULE-1')
        audit(made)
        assert entry_of(made)['breaks']['PROOF-2']['result'] == 'survived'
        install()
        yield made


def settle_run(project, *rules):
    """`(exit code, printed lines)` of the audit settling `rules` of
    `login`."""
    out = io.StringIO()
    code = audit_run.run(project.root, None, ['login'], out=out,
                         settle=list(rules))
    return code, out.getvalue().splitlines()


# The test of `PROOF-2` skips, where the status is not the one it expects.
SKIPS_ON_THE_BUG = TEST_FILE.replace(
    '    assert login("ada", "wrong") == 401\n',
    '    if login("ada", "wrong") != 401:\n'
    '        pytest.skip("not the status this test reads")\n'
    '    assert login("ada", "wrong") == 401\n')


# The same test under a setup that raises where the status is not `401`, so
# with the kept bug in place the test ends in an error and not a failure.
ERRORS_ON_THE_BUG = NOT_NONE_TEST.replace(
    'from src.login import login\n',
    'from src.login import login\n\n\n'
    '@pytest.fixture(autouse=True)\ndef refused():\n'
    '    if login("ada", "wrong") != 401:\n'
    '        raise ValueError("not the status this test reads")\n', 1)

CHECKS_NOTHING_11 = ('tests/test_intake.py::test_accession_numbers_count_up: '
                     'the test checks nothing.')


@pytest.fixture(scope='module')
def another_test_changed(tmp_path_factory):
    """`RULE-4` settled after both its tests changed: `PROOF-7`, whose bug
    survived, now hands in the proof's own case, and `PROOF-6`, whose bug was
    caught, now checks only that a status is stored. Then `sample_intake` is
    audited without `--settle`, by a model that answers `REPLY`."""
    made = sample_lab.settled(
        tmp_path_factory.mktemp('another-test'), rules=('RULE-4',),
        reply=sample_lab.MORE_SURVIVE,
        change=sample_lab.change_both_tests_of_rule_4)
    fake_claude.install(made.directory, answers=[sample_lab.REPLY])
    code, lines, _errors = sample_lab.run_script(
        made.root, made.directory, '--audit', '--feature', 'sample_intake')
    made.next = {'code': code, 'lines': lines,
                 'entries': sample_lab.entries(made.root),
                 'calls': fake_claude.calls(made.directory)}
    return made


class TestSettlingAFinding:

    # purlin: ai_audit PROOF-138
    def test_settle_without_audit_is_refused(self, built_lab):
        root, directory = built_lab
        code, lines, errors = sample_lab.run_script(
            root, directory, '--test', '--feature', 'sample_intake',
            '--settle', 'RULE-3')
        assert code == 2, (lines, errors)
        assert errors[0] == 'purlin: --settle goes with --audit.', errors
        assert 'Running the pytest suite.' not in lines

    # purlin: ai_audit PROOF-139
    def test_settle_without_a_feature_is_refused(self, built_lab):
        root, directory = built_lab
        code, lines, errors = sample_lab.run_script(
            root, directory, '--audit', '--settle', 'RULE-3')
        assert code == 2, (lines, errors)
        assert errors[0] == ('purlin: --settle needs exactly one '
                             '--feature.'), errors
        assert 'Running the pytest suite.' not in lines

    # purlin: ai_audit PROOF-140
    def test_settle_with_two_features_is_refused(self, built_lab):
        root, directory = built_lab
        code, lines, errors = sample_lab.run_script(
            root, directory, '--audit', '--feature', 'sample_intake',
            '--feature', 'billing', '--settle', 'RULE-3')
        assert code == 2, (lines, errors)
        assert errors[0] == ('purlin: --settle needs exactly one '
                             '--feature.'), errors
        assert 'Running the pytest suite.' not in lines

    # purlin: ai_audit PROOF-141
    def test_settle_naming_a_rule_the_spec_does_not_have_exits_one(
            self, built_lab):
        root, directory = built_lab
        before = sample_lab.evidence_text(root)
        code, lines, errors = sample_lab.run_script(
            root, directory, '--audit', '--feature', 'sample_intake',
            '--settle', 'RULE-99')
        assert code == 1, (lines, errors)
        assert lines == ['sample_intake RULE-99 is not a rule any spec has. '
                         'Run purlin:status sample_intake to see its rules.']
        assert sample_lab.evidence_text(root) == before
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-142
    def test_only_the_rules_named_are_read(self, two_rules):
        assert two_rules.code == 0, two_rules.lines
        # RULE-3 holds a surviving bug too, and it was not named.
        assert two_rules.before['RULE-3']['verdict'] == 'weak'
        assert len(two_rules.rule_lines('RULE-2')) == 1, two_rules.lines
        assert two_rules.rule_lines('RULE-3') == [], two_rules.lines
        assert two_rules.entries['RULE-3'] == two_rules.before['RULE-3']
        assert [call['prompt'].count('\nsample_intake RULE-2\n')
                for call in two_rules.calls] == [1]

    # purlin: ai_audit PROOF-143
    def test_a_test_that_now_catches_its_kept_bug_makes_the_rule_strong(
            self, strengthened):
        assert strengthened.code == 0, strengthened.lines
        kept = strengthened.before['RULE-3']['breaks']['PROOF-5']
        assert kept['result'] == 'survived', kept
        entry = strengthened.entries['RULE-3']
        made = entry['breaks']['PROOF-5']
        assert made['result'] == 'caught', made
        assert made['after'] == '    ' + ROUNDED, made
        assert {key: made[key] for key in
                ('file', 'line', 'before', 'after', 'aim', 'case')} == {
            key: kept[key] for key in
            ('file', 'line', 'before', 'after', 'aim', 'case')}
        assert made['break_key'] != kept['break_key'], made
        assert entry['findings'] == [], entry
        assert entry['verdict'] == 'strong', entry
        assert strengthened.rule_lines('RULE-3') == [
            'sample_intake RULE-3   strong'], strengthened.lines
        # No model was asked.
        assert strengthened.calls == []

    # purlin: ai_audit PROOF-144
    def test_the_audit_says_the_test_now_catches_the_bug(self, strengthened):
        assert strengthened.under('RULE-3') == [NOW_CATCHES_5], \
            strengthened.lines

    # purlin: ai_audit PROOF-145
    def test_a_wrong_finding_is_replaced_by_one_new_bug(self, second_caught):
        assert second_caught.code == 0, second_caught.lines
        assert len(second_caught.calls) == 1, len(second_caught.calls)
        assert asked_for(second_caught.calls[0]) == ['PROOF-5']
        entry = second_caught.entries['RULE-3']
        made = entry['breaks']['PROOF-5']
        assert made['after'] == (
            '        age = age_hours(collected, received) + 1'), made
        assert made['result'] == 'caught', made
        assert entry['findings'] == [], entry
        assert entry['verdict'] == 'strong', entry
        assert second_caught.rule_lines('RULE-3') == [
            'sample_intake RULE-3   strong'], second_caught.lines

    # purlin: ai_audit PROOF-146
    def test_the_audit_says_the_bug_did_not_break_what_the_proof_says(
            self, second_caught):
        assert second_caught.under('RULE-3') == [
            DROPPED_5 + ' A new bug was planted.'], second_caught.lines

    # purlin: ai_audit PROOF-147
    def test_a_second_survivor_is_not_kept_and_the_entry_says_why(
            self, second_survived):
        assert second_survived.code == 0, second_survived.lines
        assert len(second_survived.calls) == 1, len(second_survived.calls)
        entry = second_survived.entries['RULE-3']
        made = entry['breaks']['PROOF-5']
        assert (made['result'], made['why']) == ('not made', TWO_SURVIVED)
        assert made['break_key'] == second_survived.before['RULE-3'][
            'breaks']['PROOF-5']['break_key'], made
        assert entry['no_bug'] == [NO_BUG_CAUGHT_5], entry

    # purlin: ai_audit PROOF-158
    def test_a_second_survivor_leaves_the_rule_spot_checked_and_says_why(
            self, second_survived):
        entry = second_survived.entries['RULE-3']
        assert entry['findings'] == [], entry
        assert entry['verdict'] == 'spot-checked', entry
        assert second_survived.rule_lines('RULE-3') == [
            'sample_intake RULE-3   spot-checked'], second_survived.lines
        assert second_survived.under('RULE-3') == [
            DROPPED_5 + ' A new bug was planted.',
            '  The spot tests found nothing. ' + NO_BUG_CAUGHT_5], \
            second_survived.lines

    # purlin: ai_audit PROOF-148
    def test_a_later_audit_plants_nothing_for_that_proof(
            self, second_survived):
        again = second_survived.again
        assert again['code'] == 0, again['lines']
        asked = [call['prompt'] for call in again['calls']
                 if '\nsample_intake RULE-3\n' in call['prompt']]
        assert len(asked) == 1, len(asked)
        assert 'Plant one bug' not in asked[0]
        entry = again['entries']['RULE-3']
        assert entry['verdict'] == 'spot-checked', entry
        assert entry['no_bug'] == [NO_BUG_CAUGHT_5], entry
        assert 'sample_intake RULE-3   spot-checked' in again['lines']

    # purlin: ai_audit PROOF-149
    def test_a_dropped_bug_is_nowhere_in_the_evidence(self, second_survived):
        before = json.dumps(second_survived.before)
        assert ROUNDED in before
        assert ROUNDED not in second_survived.text
        assert 'return int(seconds // 3600) + 1' not in second_survived.text
        assert 'the AI says this breaks' not in json.dumps(
            second_survived.entries['RULE-3'])

    # purlin: ai_audit PROOF-150
    def test_no_new_bug_named_is_said_as_in_any_audit(self, claude):
        install, _directory = claude
        with weak_login(claude) as made:
            install(answers=[{'PROOF-2': 'no break: nothing breaks it'}])
            code, lines = settle_run(made, 'RULE-2')
            entry = entry_of(made)
        assert code == 0, lines
        at = lines.index('login RULE-2   spot-checked')
        assert lines[at + 1:at + 3] == [
            '  PROOF-2: the bug at src/login.py:12 did not break what the '
            'proof says.',
            '  The spot tests found nothing. No bug was planted: the model '
            'found no change that would break PROOF-2: nothing breaks it.'
            ], lines
        assert entry['breaks']['PROOF-2']['result'] == 'not made', entry
        assert entry['verdict'] == 'spot-checked', entry

    # purlin: ai_audit PROOF-151
    def test_a_model_not_reached_after_a_drop_is_said_as_in_any_audit(
            self, claude):
        install, _directory = claude
        with weak_login(claude) as made:
            install(exit_code=1)
            code, lines = settle_run(made, 'RULE-2')
            entry = entry_of(made)
        assert code == 0, lines
        assert entry['breaks'] == {}, entry
        assert entry['no_bug'] == [
            'No bug was planted: the model could not be reached: claude '
            'exited with an error.'], entry
        assert entry['verdict'] == 'spot-checked', entry
        assert ('  PROOF-2: the bug at src/login.py:12 did not break what '
                'the proof says.') in lines, lines

    # purlin: ai_audit PROOF-152
    def test_a_test_that_does_not_run_with_the_kept_bug_reads_not_run(
            self, claude):
        _install, directory = claude
        with weak_login(claude) as made:
            made.edit_test(SKIPS_ON_THE_BUG)
            made.evidence()
            code, lines = settle_run(made, 'RULE-2')
            entry = entry_of(made)
        assert code == 0, lines
        made_now = entry['breaks']['PROOF-2']
        assert made_now['after'] == '    return 200', made_now
        assert made_now['result'] == 'not run', made_now
        assert entry['no_bug'] == [
            'A bug was planted for PROOF-2 and its test did not run.'], entry
        assert entry['verdict'] == 'spot-checked', entry
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-153
    def test_a_kept_bug_that_can_no_longer_be_planted_is_asked_for_anew(
            self, tmp_path):
        made = sample_lab.settled(
            tmp_path, change=sample_lab.rewrite_the_helper,
            answers=[sample_lab.AFTER_THE_REWRITE])
        assert made.code == 0, made.lines
        assert len(made.calls) == 1, len(made.calls)
        assert asked_for(made.calls[0]) == ['PROOF-5']
        entry = made.entries['RULE-3']
        bug_now = entry['breaks']['PROOF-5']
        assert bug_now['after'] == '    hours = seconds // 3600 + 1', bug_now
        assert bug_now['result'] == 'survived', bug_now
        assert entry['verdict'] == 'weak', entry
        assert made.under('RULE-3') == [
            '  PROOF-5: the test still passes when src/intake.py:17 reads '
            '"hours = seconds // 3600 + 1"', '  ' + AI_SAYS_5], made.lines

    # purlin: ai_audit PROOF-154
    def test_a_proof_with_no_surviving_bug_keeps_its_entry(self, two_rules):
        before = two_rules.before['RULE-2']['breaks']
        assert before['PROOF-3']['result'] == 'survived', before
        assert before['PROOF-4']['result'] == 'not made', before
        assert asked_for(two_rules.calls[0]) == ['PROOF-3']
        assert two_rules.entries['RULE-2']['breaks']['PROOF-4'] == \
            before['PROOF-4']

    # purlin: ai_audit PROOF-155
    def test_a_rule_with_no_surviving_bug_has_nothing_to_settle(
            self, two_rules):
        assert two_rules.before['RULE-4']['verdict'] == 'strong'
        assert two_rules.lines.count(
            'sample_intake RULE-4 has no planted bug that survived: nothing '
            'to settle.') == 1, two_rules.lines
        assert two_rules.rule_lines('RULE-4') == [], two_rules.lines
        assert two_rules.entries['RULE-4'] == two_rules.before['RULE-4']

    # purlin: ai_audit PROOF-156
    def test_a_rule_whose_test_fails_is_not_settled(self, tmp_path):
        made = sample_lab.settled(tmp_path, change=sample_lab.expect_24)
        assert made.code == 1, made.lines
        assert ('sample_intake RULE-3 fails: tests/test_intake.py::'
                'test_age_is_whole_hours. Run purlin:build sample_intake.'
                ) in made.lines, made.lines
        assert made.rule_lines('RULE-3') == [], made.lines
        assert not [line for line in made.lines
                    if 'nothing to settle' in line], made.lines
        assert made.entries['RULE-3'] == made.before['RULE-3']
        assert made.calls == []

    # purlin: ai_audit PROOF-157
    def test_an_audit_without_settle_replays_nothing(self, tmp_path):
        made = sample_lab.settled(
            tmp_path, rules=(), change=sample_lab.strengthen,
            answers=[sample_lab.ANOTHER_BUG])
        assert made.code == 0, made.lines
        assert len(made.calls) == 1, len(made.calls)
        assert asked_for(made.calls[0]) == ['PROOF-5']
        bug_now = made.entries['RULE-3']['breaks']['PROOF-5']
        assert bug_now['after'] == '    return int(seconds // 1800)', bug_now
        assert bug_now['result'] == 'caught', bug_now
        assert made.under('RULE-3') == [], made.lines
        assert ROUNDED not in made.text

    # purlin: ai_audit PROOF-161
    def test_a_result_taken_on_another_test_is_left_out_of_the_entry(
            self, another_test_changed):
        made = another_test_changed
        assert made.code == 0, made.lines
        before = made.before['RULE-4']['breaks']
        assert (before['PROOF-6']['result'], before['PROOF-7']['result']) == (
            'caught', 'survived'), before
        entry = made.entries['RULE-4']
        assert sorted(entry['breaks']) == ['PROOF-7'], entry
        assert entry['breaks']['PROOF-7']['result'] == 'caught', entry
        assert entry['verdict'] == 'strong', entry
        assert made.rule_lines('RULE-4') == [
            'sample_intake RULE-4   strong'], made.lines
        assert made.calls == []

    # purlin: ai_audit PROOF-162
    def test_the_next_audit_plants_a_bug_for_the_proof_left_out(
            self, another_test_changed):
        after = another_test_changed.next
        assert after['code'] == 0, after['lines']
        assert [asked_for(call) for call in after['calls']] == [['PROOF-6']]
        entry = after['entries']['RULE-4']
        made = entry['breaks']['PROOF-6']
        assert made['after'] == 'MAX_AGE_HOURS = 73', made
        assert made['result'] == 'survived', made
        assert entry['verdict'] == 'weak', entry
        assert 'sample_intake RULE-4   weak' in after['lines'], after['lines']

    # purlin: ai_audit PROOF-163
    def test_a_settle_runs_the_spot_tests(self, tmp_path):
        made = sample_lab.settled(tmp_path, rules=('RULE-7',),
                                  reply=sample_lab.MORE_SURVIVE)
        assert made.code == 0, made.lines
        kept = made.before['RULE-7']['breaks']['PROOF-11']
        assert kept['result'] == 'survived', kept
        entry = made.entries['RULE-7']
        assert entry['findings'] == [CHECKS_NOTHING_11], entry
        assert entry['verdict'] == 'weak', entry
        assert made.rule_lines('RULE-7') == [
            'sample_intake RULE-7   weak'], made.lines
        assert '  ' + CHECKS_NOTHING_11 in made.under('RULE-7'), made.lines

    # purlin: ai_audit PROOF-164
    def test_a_test_that_ends_in_an_error_with_the_kept_bug_says_so(
            self, claude):
        _install, directory = claude
        with weak_login(claude) as made:
            made.edit_test(ERRORS_ON_THE_BUG)
            made.evidence()
            code, lines = settle_run(made, 'RULE-2')
            entry = entry_of(made)
        assert code == 0, lines
        made_now = entry['breaks']['PROOF-2']
        assert (made_now['result'], made_now['why']) == (
            'not run', 'the test ended in an error, not a failure'), made_now
        assert entry['no_bug'] == [
            'A bug was planted for PROOF-2 and its test ended in an error, '
            'not a failure.'], entry
        assert entry['verdict'] == 'spot-checked', entry
        assert fake_claude.calls(directory) == []

    # purlin: ai_audit PROOF-165
    def test_a_settle_that_asks_no_model_writes_no_explanation(
            self, strengthened):
        before = strengthened.before['RULE-3']
        assert before['explanation'] == [
            'PROOF-5: the test takes its expected age from the code.'], before
        assert before['model'] == 'claude-fake-1', before
        entry = strengthened.entries['RULE-3']
        assert strengthened.calls == []
        assert entry['explanation'] == [], entry
        assert entry['model'] == 'claude-fake-1', entry
        assert entry['criteria'] == before['criteria'], entry

    # purlin: ai_audit PROOF-166
    def test_a_kept_bug_in_a_file_the_scope_no_longer_names_is_asked_for_anew(
            self, tmp_path):
        made = sample_lab.settled(
            tmp_path, change=sample_lab.scope_without_the_code)
        assert made.code == 0, (made.lines, made.errors)
        kept = made.before['RULE-3']['breaks']['PROOF-5']
        assert (kept['file'], kept['result']) == (
            'src/intake.py', 'survived'), kept
        assert [asked_for(call) for call in made.calls] == [['PROOF-5']]
        assert [line for line in made.lines
                if 'did not break what the proof says' in line] == [], \
            made.lines
        bug_now = made.entries['RULE-3']['breaks']['PROOF-5']
        assert (bug_now['result'], bug_now['after']) == ('not made', None), \
            bug_now
        assert made.under('RULE-3') == [
            '  The spot tests found nothing. No bug was planted: the model '
            'found no change that would break PROOF-5: the fake model plants '
            'no bug.'], made.lines
