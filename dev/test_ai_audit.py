"""Tests for the AI audit: `scripts/review/audit_run.py` and `ai_audit.py`.

The throwaway project is `dev/sign_project.py`'s, so a spec, a test file and
the evidence are written by the test and nothing reads this repository's own
specs. No test reaches the real model: every call lands on a fake `claude`
that `dev/fake_claude.py` writes under the test's own temporary folder, first
on PATH, or on a runner handed in its place.

What each group holds:

*reading*   which rules the audit reads
*prompt*    the criteria file verbatim, then the rule, its proofs, each test's
            source and the findings of the spot tests and the planted bugs
*call*      one call per rule, the prompt on stdin and never in the arguments
*answer*    the model and the criteria named; the explanation and the notes
*verdict*   the spot tests and the planted bugs alone set it; the last line
*failure*   the three ways the model cannot be reached, each with its reason
*writing*   reading, asking and printing a rule write no file
*command*   the command line: its exits and what it prints
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


def bug(before, after, path='src/login.py'):
    """The model's answer naming one planted bug."""
    return 'file: %s\nbefore:\n%s\nafter:\n%s\n' % (path, before, after)


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


def entry_of(project, rule='RULE-2'):
    """The audit entry the local evidence holds for `rule`."""
    path = os.path.join(project.root, '.purlin', 'evidence', 'local',
                        'login.json')
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)['audit']['rules'][rule]


def bug_calls(directory):
    """The calls that asked the fake for a planted bug."""
    first = audit_module.BUG_INSTRUCTION[0]
    return [call for call in fake_claude.calls(directory)
            if call['prompt'].startswith(first)]


def reading_calls(directory):
    """The calls that asked the fake to read a rule."""
    return [call for call in fake_claude.calls(directory)
            if call['prompt'].startswith(criteria_text())]


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
            self, project):
        project.audit('RULE-2')
        rule = project.rule('RULE-2')
        assert rule['cells']['passed']['word'] == 'passed', rule
        assert rule['audit']['verdict'] == 'strong', rule
        assert rule['audit']['commit'] == project.head(), rule
        assert ('login', 'RULE-2') not in to_read(project)
        assert ('login', 'RULE-1') in to_read(project)

    # purlin: ai_audit PROOF-103
    def test_a_rule_whose_feature_code_changed_since_its_entry_is_read(self):
        source = LOGIN_SOURCE
        with passing_project(source=source) as made:
            made.audit('RULE-2')
            assert ('login', 'RULE-2') not in to_read(made)
            write(os.path.join(made.root, 'src', 'login.py'), source.replace(
                '    return 401\n', '    return 403 if locked else 401\n'))
            made.evidence()
            rule = made.rule('RULE-2')
            assert rule['cells']['passed']['word'] == 'passed', rule
            assert rule['audit'], rule
            assert ('login', 'RULE-2') in to_read(made)

    # purlin: ai_audit PROOF-51
    def test_a_rule_with_a_current_entry_is_read_when_asked_again(
            self, project):
        project.audit('RULE-2')
        assert project.rule('RULE-2')['audit']
        assert ('login', 'RULE-2') not in to_read(project)
        assert ('login', 'RULE-2') in to_read(project, again=True)


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
            made.audit('RULE-1')
            audit(made)
        readings = reading_calls(directory)
        assert len(readings) == 1, fake_claude.calls(directory)
        prompt = readings[0]['prompt']
        assert 'login RULE-2' in prompt
        source = prompt.index('def test_a_bad_password_is_denied')
        assert prompt.index(CHECKS_NOTHING, source) > source, prompt[-600:]


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
        assert calls[0]['argv'] == ['-p', '--output-format', 'json']
        # The fake reads its standard input to the end before it answers.
        assert calls[0]['prompt'] == audit_module.model_prompt(
            project.root, reading, criteria_text())
        assert not any('Invalid credentials' in part
                       for part in calls[0]['argv'])

    # purlin: ai_audit PROOF-14
    def test_a_call_is_given_300_seconds_and_stdin_closes_after_the_prompt(
            self, project):
        seen = []

        class Done(object):
            returncode = 0
            stdout = json.dumps({'result': '- The test reads the status.'})

        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return Done()

        audit_module.audit_one(project.root, read(project, 'RULE-2'),
                               'criteria', command='/bin/claude',
                               runner=runner)
        assert len(seen) == 1, seen
        command, kwargs = seen[0]
        assert command == ['/bin/claude', '-p', '--output-format', 'json']
        assert kwargs['timeout'] == 300
        # `input=` writes the prompt and closes stdin behind it.
        assert kwargs['input'] == audit_module.model_prompt(
            project.root, read(project, 'RULE-2'), 'criteria')
        assert 'stdin' not in kwargs

    # purlin: ai_audit PROOF-55
    def test_six_rules_six_calls_each_answer_beside_its_rule(self, project):
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


def _rules_evidence(project, results):
    """A local section naming `test_step_<n>` with `results[n - 1]`."""
    rel = '.purlin/evidence/local/login.json'
    os_name = purlin_evidence.host_os()
    data = {'schema': purlin_evidence.SCHEMA, 'feature': 'login',
            'source': 'local', 'spec': 'specs/auth/login.md',
            'audit': {'rules': {}},
            'platforms': {os_name: {
                'commit': project.head(), 'dirty': False,
                'at': '2026-09-13T12:00:00Z', 'runner': 'ada',
                'machine': 'jane-laptop', 'hostname': 'runner-17',
                'fingerprint': purlin_fingerprint.fingerprint(project.root,
                                                              'login'),
                'rules': {},
                'proofs': [{'id': 'PROOF-%d' % n, 'rule': 'RULE-%d' % n,
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
            made.audit(rule, findings=['%s: the test checks nothing.' % rule])
        for rule in strong:
            made.audit(rule)
        git(made.root, 'add', '-A')
        git(made.root, 'commit', '-q', '-m', 'purlin: audit at abc1234')
        yield made
    finally:
        made.close()


class TestTheVerdict:

    # purlin: ai_audit PROOF-95
    def test_a_spot_finding_makes_the_rule_weak_though_its_bug_was_caught(
            self, claude):
        install, directory = claude
        install(answers=[bug('    return 401',
                             '    raise RuntimeError("planted")'),
                         '- The test calls login.'])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=CHECKS_NOTHING_TEST) as made:
            made.audit('RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry
        assert entry['verdict'] == 'weak', entry
        assert CHECKS_NOTHING in entry['findings'], entry
        assert len(bug_calls(directory)) == 1

    # purlin: ai_audit PROOF-96
    def test_a_bug_that_survives_makes_the_rule_weak_with_its_finding(
            self, claude):
        install, _directory = claude
        install(answers=[bug('    return 401', '    return 200'),
                         '- The test reads no status.'])
        with passing_project(source=LOGIN_SOURCE,
                             test_file=NOT_NONE_TEST) as made:
            made.audit('RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert entry['breaks']['PROOF-2']['result'] == 'survived', entry
        assert entry['verdict'] == 'weak', entry
        assert entry['findings'] == [
            'PROOF-2: the test still passes when src/login.py:12 reads '
            '"return 200"'], entry

    # purlin: ai_audit PROOF-97
    def test_no_spot_finding_and_every_bug_caught_is_strong_whatever_claude_says(
            self, claude):
        install, directory = claude
        install(answers=[bug('    return 401', '    return 200'),
                         '- This rule is weak.'])
        with passing_project(source=LOGIN_SOURCE) as made:
            made.audit('RULE-1')
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert len(reading_calls(directory)) == 1
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry
        assert entry['findings'] == [], entry
        assert entry['explanation'] == ['This rule is weak.'], entry
        assert entry['verdict'] == 'strong', entry

    # purlin: ai_audit PROOF-98
    def test_the_findings_and_the_explanation_are_kept_apart(self, claude):
        install, _directory = claude
        install(answers=['no break: the proof names no value the code '
                         'computes',
                         '- The test calls login and reads no status.'])
        with passing_project(test_file=CHECKS_NOTHING_TEST) as made:
            made.audit('RULE-1')
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
            'The audit found 4 of 5 rules strong (80%).'), printed

    # purlin: ai_audit PROOF-104
    def test_a_rule_whose_test_fails_is_not_counted(self, claude):
        with rules_project(['pass', 'pass', 'pass', 'pass', 'fail'],
                           weak=['RULE-4'],
                           strong=['RULE-1', 'RULE-2', 'RULE-3']) as made:
            assert made.rule('RULE-5')['cells']['passed']['word'] == 'failed'
            code, printed = audit(made)
        assert code == 0, printed
        assert printed.splitlines()[-1] == (
            'The audit found 3 of 4 rules strong (75%).'), printed

    # purlin: ai_audit PROOF-100
    def test_a_caught_bug_is_kept_while_its_test_and_code_stand(self, claude):
        _install, directory = claude
        with passing_project(source=LOGIN_SOURCE) as made:
            # The bug planted for PROOF-2 was caught, for this test and code.
            rel = made.audit('RULE-2')
            reading = read(made, 'RULE-2')
            tests = [{'file': t['file'], 'name': t['name'],
                      'source': t['body']} for t in reading['tests']]
            key = audit_module.break_key(
                audit_run.test_source_hash(tests),
                purlin_fingerprint.code_part(
                    made.root, {'scope': ['src/login.py']}))
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            data['audit']['rules']['RULE-2']['breaks'] = {'PROOF-2': {
                'file': 'src/login.py', 'line': 12, 'before': '    return 401',
                'after': '    return 200', 'result': 'caught', 'why': '',
                'break_key': key}}
            write(path, json.dumps(data, indent=2, sort_keys=True))
            made.audit('RULE-1')
            # Only RULE-2's text changes, so the audit reads it again.
            made.spec(SPEC.replace('return 401 and the body',
                                   'return 401 with the body'))
            made.evidence()
            assert to_read(made) == [('login', 'RULE-2')]
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert bug_calls(directory) == []
        assert len(reading_calls(directory)) == 1
        assert entry['breaks']['PROOF-2']['result'] == 'caught', entry

    # purlin: ai_audit PROOF-102
    def test_an_anchors_rule_gets_no_planted_bug(self, claude):
        _install, directory = claude
        with passing_project() as made:
            as_anchor(made)
            made.audit('RULE-1')
            assert made.rule('RULE-2')['cells']['passed']['word'] == 'passed'
            assert to_read(made) == [('login', 'RULE-2')]
            code, printed = audit(made)
            entry = entry_of(made)
        assert code == 0, printed
        assert bug_calls(directory) == []
        assert entry['verdict'] == 'strong', entry
        assert entry['breaks'] == {}, entry


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
            capsys.readouterr().err

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

    # purlin: ai_audit PROOF-87
    def test_a_rule_with_no_test_names_the_command(self, capsys):
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
