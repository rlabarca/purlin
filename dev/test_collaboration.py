"""The three-person test (specs/workflow/collaboration.md).

Pat (product), Quinn (QA) and Dana (dev) work at once in three clones of one
bare repository on disk, through git and the commands Purlin's skills give.
A script plays all three: no model is asked anything, no audit runs, and no
git host is reached. Every step's command and what it printed go to standard
output, which pytest shows when the test fails.

A Purlin command is run only after the test has found it in the output of
the step before it, or in the skill that gives it: `given` fails where the
words are absent, so a step nobody was told to take cannot pass.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SCRIPTS = os.path.join(ROOT, 'scripts')
SCAFFOLD = os.path.join(SCRIPTS, 'init', 'scaffold.py')
RUN = os.path.join(SCRIPTS, 'run', 'purlin_run.py')
SIGN = os.path.join(SCRIPTS, 'review', 'sign.py')
RENUMBER = os.path.join(SCRIPTS, 'spec', 'renumber.py')
WORDING = os.path.join(SCRIPTS, 'mcp', 'purlin', 'wording.py')
SERVER = os.path.join(SCRIPTS, 'mcp', 'purlin', 'server.py')

sys.path.insert(0, os.path.join(SCRIPTS, 'mcp'))
from purlin import drift as drift_module  # noqa: E402

VERSION = '0.1.0'
TAG = 'signed/' + VERSION
PACKAGE = '.purlin/evidence/package/%s.json' % VERSION
SIGNOFFS = '.purlin/evidence/package/%s.signoffs' % VERSION
SUGGESTED = 'Suggested tests setting: '
LAST_LINE = ('Every rule passes its tests on the committed evidence. To sign '
             'it: purlin:sign')
NO_KEY = 'No key to sign with. These commands set one up:'
HAND_CHECK = 'sample_age RULE-3'

# The three people, and whoever reads the result in a fresh clone at the end.
PEOPLE = {'pat': 'pat.product@labconnect.example',
          'quinn': 'quinn.qa@labconnect.example',
          'dana': 'dana.dev@labconnect.example',
          'reader': 'reader@labconnect.example'}

PYPROJECT = ('[project]\n'
             'name = "labconnect"\n'
             'version = "%s"\n\n'
             '[tool.pytest.ini_options]\n'
             'pythonpath = ["."]\n' % VERSION)


def spec(name, description, rules, proofs):
    """A spec's text; `rules` and `proofs` are whole lines after `- `, each
    numbered by the id it opens on."""
    highest = lambda lines: max(int(re.match(r'[A-Z]+-(\d+)', line).group(1))
                                for line in lines)
    return ('# Feature: %s\n\n'
            '> Description: %s\n'
            '> Scope: src/%s.py\n'
            '> Highest-Rule: %d\n'
            '> Highest-Proof: %d\n\n'
            '## Rules\n\n%s\n\n'
            '## Proof\n\n%s\n'
            % (name, description, name, highest(rules), highest(proofs),
               '\n'.join('- ' + line for line in rules),
               '\n'.join('- ' + line for line in proofs)))


AGE = 'specs/lab/sample_age.md'
AGE_ABOUT = 'How old a sample is, in whole days.'
AGE_RULES = [
    'RULE-1: `age_days(collected, today)` returns the whole days from the '
    'collection date to today',
    'RULE-2: A collection date after today is refused with `ValueError`',
    "RULE-3: The age printed on a tube's label is legible at arm's length",
]
AGE_PROOFS = [
    'PROOF-1 (RULE-1): `age_days(date(2026, 1, 1), date(2026, 1, 4))` '
    'returns 3',
    'PROOF-2 (RULE-2): `age_days(date(2026, 1, 4), date(2026, 1, 1))` '
    'raises `ValueError`',
    "PROOF-3 (RULE-3): Print the label of a sample 3 days old and hold it at "
    "arm's length; the age reads `3 days` @manual",
]
AGE_SAME_DAY = ('PROOF-4 (RULE-1): `age_days(date(2026, 1, 1), '
                'date(2026, 1, 1))` returns 0')
AGE_YEAR_END = ('(RULE-1): `age_days(date(2025, 12, 31), date(2026, 1, 1))` '
                'returns 1')

STABILITY = 'specs/lab/stability.md'
STABILITY_ABOUT = 'How many days a sample stays usable where it is stored.'
STABILITY_RULES = [
    'RULE-1: A frozen sample is stable for 30 days',
    'RULE-2: A sample at room temperature is stable for 2 days',
]
STABILITY_PROOFS = [
    'PROOF-1 (RULE-1): `stable_days("frozen")` returns 30',
    'PROOF-2 (RULE-2): `stable_days("room")` returns 2',
    'PROOF-3 (RULE-2): `stable_days("ROOM")` returns 2',
]
CHILLED_RULE = 'A refrigerated sample is stable for 7 days'
CHILLED_PROOF = '`stable_days("refrigerated")` returns 7'
UNKNOWN_RULE = 'A storage the lab does not use is refused with `ValueError`'
UNKNOWN_PROOF = '`stable_days("warm")` raises `ValueError`'

AGE_CODE = ('def age_days(collected, today):\n'
            '    if collected > today:\n'
            '        raise ValueError("collected after today")\n'
            '    return (today - collected).days\n')
AGE_TESTS = ('from datetime import date\n\n'
             'import pytest\n\n'
             'from src.sample_age import age_days\n\n\n'
             '# purlin: sample_age PROOF-1\n'
             'def test_three_days():\n'
             '    assert age_days(date(2026, 1, 1), date(2026, 1, 4)) == 3\n'
             '\n\n'
             '# purlin: sample_age PROOF-2\n'
             'def test_a_future_collection_is_refused():\n'
             '    with pytest.raises(ValueError):\n'
             '        age_days(date(2026, 1, 4), date(2026, 1, 1))\n')
AGE_SAME_DAY_TEST = ('\n\n# purlin: sample_age PROOF-4\n'
                     'def test_the_same_day_is_zero():\n'
                     '    assert age_days(date(2026, 1, 1), '
                     'date(2026, 1, 1)) == 0\n')
YEAR_END_TEST = ('from datetime import date\n\n'
                 'from src.sample_age import age_days\n\n\n'
                 '# purlin: sample_age PROOF-4\n'
                 'def test_across_a_year_end():\n'
                 '    assert age_days(date(2025, 12, 31), '
                 'date(2026, 1, 1)) == 1\n')

STABILITY_CODE = ('DAYS = {"frozen": 30, "room": 2}\n\n\n'
                  'def stable_days(storage):\n'
                  '    return DAYS[storage.lower()]\n')
STABILITY_CODE_UNKNOWN = ('DAYS = {"frozen": 30, "room": 2}\n\n\n'
                          'def stable_days(storage):\n'
                          '    if storage.lower() not in DAYS:\n'
                          '        raise ValueError(storage)\n'
                          '    return DAYS[storage.lower()]\n')
STABILITY_TESTS = ('import pytest\n\n'
                   'from src.stability import stable_days\n\n\n'
                   '# purlin: stability PROOF-1\n'
                   'def test_frozen():\n'
                   '    assert stable_days("frozen") == 30\n\n\n'
                   '# purlin: stability PROOF-2\n'
                   'def test_room():\n'
                   '    assert stable_days("room") == 2\n\n\n'
                   '# purlin: stability PROOF-3\n'
                   'def test_room_in_capitals():\n'
                   '    assert stable_days("ROOM") == 2\n')
UNKNOWN_TEST = ('\n\n# purlin: stability PROOF-4\n'
                'def test_an_unknown_storage_is_refused():\n'
                '    with pytest.raises(ValueError):\n'
                '        stable_days("warm")\n')
CHILLED_TEST = ('\n\n# purlin: stability PROOF-4\n'
                'def test_refrigerated():\n'
                '    assert stable_days("refrigerated") == 7\n')


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)


def flat(text):
    """`text` with every run of white space as one space, so a command a
    page wraps over two lines is still found."""
    return ' '.join(text.split())


def skill(name):
    return flat(read(os.path.join(ROOT, 'skills', name, 'SKILL.md')))


def given(where, *needles):
    """Fail unless `where`, an output or a skill's text, gives each needle."""
    text = flat(where)
    for needle in needles:
        assert flat(needle) in text, (
            'nothing told the person to run %r' % needle)


class Team(object):
    """The bare repository, the three people, and every exit code seen."""

    def __init__(self, base):
        self.base = base
        self.host = os.path.join(base, 'labconnect.git')
        self.codes = []      # (who, what, exit code, the code expected)
        self.warned = []     # every warning a status carried along the way
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main',
                        self.host], check=True, capture_output=True)

    def person(self, name):
        return Person(self, name)


class Person(object):
    """One person: a clone of the host, an identity and a home of their own."""

    def __init__(self, team, name):
        self.team = team
        self.name = name
        self.email = PEOPLE[name]
        self.home = os.path.join(team.base, 'home-' + name)
        self.root = os.path.join(team.base, name, 'labconnect')
        # A home that has used SSH before: the `ssh-keygen` line the sign-off
        # prints writes into `~/.ssh` and does not make the folder.
        os.makedirs(os.path.join(self.home, '.ssh'), mode=0o700)
        os.makedirs(os.path.dirname(self.root))
        subprocess.run(['git', 'clone', '-q', team.host, self.root],
                       check=True, capture_output=True, env=self.env())
        for key, value in (('user.email', self.email),
                           ('user.name', name.capitalize()),
                           ('pull.rebase', 'false'),
                           ('commit.gpgsign', 'false'),
                           ('init.defaultBranch', 'main')):
            self.git('config', key, value)

    def env(self):
        """This person's environment: their own home, no variable of a git
        host's runner, and this interpreter first on the search path, so the
        suggested `python3 -m pytest` finds pytest."""
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('GITHUB_', 'SYSTEM_', 'BUILD_',
                                      'RUNNER_', 'GIT_'))
               and key not in ('TF_BUILD', 'CLAUDE_PLUGIN_ROOT',
                               'PURLIN_PROJECT_ROOT', 'XDG_CONFIG_HOME')}
        env['PATH'] = os.path.dirname(sys.executable) + os.pathsep + env['PATH']
        env['HOME'] = self.home
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        env['GIT_TERMINAL_PROMPT'] = '0'
        return env

    def path(self, rel):
        return os.path.join(self.root, *rel.split('/'))

    def write(self, rel, text):
        write(self.path(rel), text)

    def append(self, rel, text):
        self.write(rel, read(self.path(rel)) + text)

    def git(self, *args, **kwargs):
        """A plain git step; it must succeed unless `check=False`."""
        done = subprocess.run(['git'] + list(args), cwd=self.root,
                              capture_output=True, encoding='utf-8',
                              env=self.env(), stdin=subprocess.DEVNULL)
        if kwargs.get('check', True):
            assert done.returncode == 0, (self.name, args, done.stdout,
                                          done.stderr)
        return done.stdout.strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def merge_to_main(self, branch):
        """Bring `branch` onto `main` and push it, as a merged pull request."""
        self.git('checkout', '-q', 'main')
        self.git('pull', '-q', '--no-edit', 'origin', 'main')
        self.git('merge', '-q', '--no-edit', '--no-ff', branch)
        self.git('push', '-q', 'origin', 'main')

    def run(self, what, argv, expect=0):
        """One command of Purlin's; its exit code is kept beside the one
        expected, and what it printed is shown when the test fails."""
        done = subprocess.run(argv, cwd=self.root, capture_output=True,
                              encoding='utf-8', env=self.env(),
                              stdin=subprocess.DEVNULL, timeout=300)
        out = done.stdout + done.stderr
        print('--- %s: %s (exit %d)\n%s' % (self.name, what, done.returncode,
                                            out))
        self.team.codes.append((self.name, what, done.returncode, expect))
        return out

    def script(self, what, path, *args, **kwargs):
        return self.run(what, [sys.executable, path] + list(args)
                        + ['--project-root', self.root], **kwargs)

    def tool(self, name, **arguments):
        """One Purlin tool call through the server, naming this checkout."""
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': name, 'arguments': dict(
                       arguments, project_root=self.root)}}
        done = subprocess.run([sys.executable, SERVER],
                              input=json.dumps(request) + '\n',
                              cwd=self.team.base, capture_output=True,
                              encoding='utf-8', env=self.env(), timeout=300)
        answers = [json.loads(line) for line in done.stdout.splitlines()
                   if line.strip()]
        assert done.returncode == 0 and len(answers) == 1, (
            name, done.stdout, done.stderr)
        result = answers[0]['result']
        text = result['content'][0]['text']
        print('--- %s: the tool %s\n%s' % (self.name, name, text))
        self.team.codes.append((self.name, 'tool ' + name,
                                int(bool(result.get('isError'))), 0))
        return text

    def status(self):
        """`purlin:status`: the tool's text, its warnings kept for the end."""
        given(skill('status'), 'sync_status`')
        text = self.tool('sync_status')
        data = read(self.path('.purlin/report-data.js'))
        payload = json.loads(data[data.index('{'):].rstrip().rstrip(';'))
        self.team.warned.extend(payload['warnings'])
        return text

    def drift(self):
        given(skill('drift'), 'purlin:drift', '`project_root`')
        return self.tool('drift')

    def test(self, *flags, **kwargs):
        """`purlin:test` with `flags`, as the test skill runs it."""
        given(skill('test'), 'scripts/run/purlin_run.py" --test --project-root .')
        return self.script('purlin:test ' + ' '.join(flags), RUN, '--test',
                           *flags, **kwargs)

    def renumber(self, feature, told):
        """The dry run, then the renumbering on a yes, as the spec skill
        gives them and as `told`, the output before, sent the person there.
        The dry run changes nothing; the run stages and commits nothing."""
        given(told, 'purlin:spec')
        given(skill('spec'), 'scripts/spec/renumber.py" <name> --dry-run',
              'Do it? [y/N]')
        before = self.git('status', '--porcelain')
        dry = self.script('renumber --dry-run', RENUMBER, feature, '--dry-run')
        assert 'Nothing is changed: this is a dry run.' in dry
        assert self.git('status', '--porcelain') == before
        done = self.script('renumber --yes', RENUMBER, feature, '--yes')
        assert 'Renumbered in %s' % feature in done
        return done

    def sign(self, *args, **kwargs):
        return self.script('purlin:sign ' + ' '.join(args), SIGN, *args,
                           **kwargs)

    def answers(self):
        """The answers file the sign skill writes: the hand check answered
        with nothing, and the signature with yes."""
        given(skill('sign'), '.purlin/runtime/signoff-answers.json')
        rel = '.purlin/runtime/signoff-answers.json'
        self.write(rel, json.dumps({
            'audit': 'go on',
            'stops': {HAND_CHECK: {'answer': 'note', 'note': ''}},
            'sign': self.email}))
        return rel

    def set_up_the_key(self, printed):
        """Run the commands the key block printed, as printed."""
        lines = printed.splitlines()
        block = [line.strip() for line in lines[lines.index(NO_KEY) + 1:]
                 if line.startswith('  ')]
        assert [line.split()[0] for line in block] == [
            'ssh-keygen', 'git', 'git'], block
        for line in block:
            done = subprocess.run(line, shell=True, cwd=self.root,  # noqa: S602
                                  capture_output=True, encoding='utf-8',
                                  env=self.env(), stdin=subprocess.DEVNULL)
            assert done.returncode == 0, (line, done.stdout, done.stderr)


def conflict_lines(text):
    return [line for line in text.splitlines()
            if line.startswith(('<<<<<<<', '=======', '>>>>>>>'))]


def numbers(text, kind):
    """Every `RULE-N` or `PROOF-N` a spec's lines open on, in order."""
    return [int(n) for n in re.findall(r'^- %s-(\d+)' % kind, text, re.M)]


def highest(text, kind):
    return int(re.search(r'^> Highest-%s: (\d+)$' % kind.capitalize(), text,
                         re.M).group(1))


def opening(status):
    """The two facts a status opens on, after its first line."""
    lines = status.splitlines()
    assert lines[0].startswith('Purlin status: labconnect, plugin '), lines[0]
    return lines[1], lines[2]


# purlin: collaboration PROOF-1
def test_three_people_reach_a_signed_version(tmp_path):
    if not shutil.which('ssh-keygen'):
        pytest.skip('ssh-keygen is not on this machine')
    team = Team(os.path.realpath(str(tmp_path)))

    # 1. Pat starts the project and sets Purlin up.
    pat = team.person('pat')
    pat.git('checkout', '-q', '-b', 'main')
    pat.write('pyproject.toml', PYPROJECT)
    pat.write('.gitignore', '__pycache__/\n.pytest_cache/\n')
    pat.commit('chore: the project')
    given(skill('init'), 'scripts/init/scaffold.py" --project-root .', '--yes')
    out = pat.script('purlin:init', SCAFFOLD, '--yes')
    assert pat.git('log', '-1', '--format=%s') == 'chore(init): set up Purlin'
    assert pat.git('status', '--porcelain') == ''
    pat.git('push', '-q', '-u', 'origin', 'main')

    # 2. Pat writes the two specs on a branch, merged and pushed.
    pat.git('checkout', '-q', '-b', 'product/specs')
    pat.write(AGE, spec('sample_age', AGE_ABOUT, AGE_RULES, AGE_PROOFS))
    pat.write(STABILITY, spec('stability', STABILITY_ABOUT, STABILITY_RULES,
                              STABILITY_PROOFS))
    pat.commit('spec(sample_age): the age of a sample, and how long it keeps')
    pat.merge_to_main('product/specs')

    # 3. Dana builds both, takes the suggested test command, runs and commits.
    dana = team.person('dana')
    dana.git('checkout', '-q', '-b', 'dev/build')
    dana.write('src/__init__.py', '')
    dana.write('src/sample_age.py', AGE_CODE)
    dana.write('src/stability.py', STABILITY_CODE)
    dana.write('tests/test_sample_age.py', AGE_TESTS)
    dana.write('tests/test_stability.py', STABILITY_TESTS)
    dana.commit('feat(sample_age): the age and the stability of a sample')
    out = dana.test(expect=1)
    (line,) = [line for line in out.splitlines() if line.startswith(SUGGESTED)]
    given(skill('test'), 'write that array as the `tests` setting with the '
                         '`purlin_config` tool, then run Step 1 again')
    dana.tool('purlin_config', action='write', key='tests',
              value=json.loads(line[len(SUGGESTED):]))
    given(skill('test'), 'purlin:test --commit')
    out = dana.test('--commit')
    assert 'Markers: 5 tied to a test, 0 not tied.' in out
    dana.merge_to_main('dev/build')

    # 4. Collision one, QA first. Quinn and Dana both add stability RULE-3
    #    and PROOF-4; Quinn's is merged first.
    quinn = team.person('quinn')
    quinn.git('checkout', '-q', '-b', 'qa/refrigerated')
    quinn.write(STABILITY, spec(
        'stability', STABILITY_ABOUT,
        STABILITY_RULES + ['RULE-3: ' + CHILLED_RULE],
        STABILITY_PROOFS + ['PROOF-4 (RULE-3): ' + CHILLED_PROOF]))
    quinn.commit('spec(stability): a refrigerated sample')

    dana.git('checkout', '-q', '-b', 'dev/unknown-storage')
    dana.write(STABILITY, spec(
        'stability', STABILITY_ABOUT,
        STABILITY_RULES + ['RULE-3: ' + UNKNOWN_RULE],
        STABILITY_PROOFS + ['PROOF-4 (RULE-3): ' + UNKNOWN_PROOF]))
    dana.write('src/stability.py', STABILITY_CODE_UNKNOWN)
    dana.append('tests/test_stability.py', UNKNOWN_TEST)
    dana.commit('feat(stability): an unknown storage is refused')
    quinn.merge_to_main('qa/refrigerated')

    #    Dana pulls, and git stops on the rule lines and on the proof lines.
    #    She edits no line of the conflict: the status and drift send her to
    #    the renumbering, which keeps both sides and then renumbers hers.
    stopped = dana.git('pull', '--no-edit', 'origin', 'main', check=False)
    assert 'CONFLICT' in stopped, stopped
    assert len(conflict_lines(read(dana.path(STABILITY)))) == 6
    status = dana.status()
    assert opening(status)[0] == 'Tests: not met'
    assert '1 spec to repair: purlin:spec' in status
    drift = dana.drift()
    assert 'RULE-3' in drift and 'PROOF-4' in drift
    assert drift_module.MERGE_LINE in json.loads(drift)['view']['lines']
    given(skill('drift'), 'follow `Renumbering` in')
    done = dana.renumber('stability', status)
    assert 'stability: the conflict at line ' in done
    assert 'Resolved 2 conflicts in stability.' in done
    assert conflict_lines(read(dana.path(STABILITY))) == []
    assert dana.git('status', '--porcelain').splitlines()[0] == (
        'UU ' + STABILITY)
    text = read(dana.path(STABILITY))
    assert '- RULE-3: ' + CHILLED_RULE in text
    assert '- RULE-4: ' + UNKNOWN_RULE in text
    assert '- PROOF-4 (RULE-3): ' + CHILLED_PROOF in text
    assert '- PROOF-5 (RULE-4): ' + UNKNOWN_PROOF in text
    assert '# purlin: stability PROOF-5\ndef test_an_unknown_storage' in read(
        dana.path('tests/test_stability.py'))
    #    Her commit finishes the merge, and drift no longer names one.
    dana.commit('spec(stability): renumber the rule and the proof written twice')
    assert len(dana.git('rev-list', '--parents', '-n', '1', 'HEAD').split()) == 3
    assert drift_module.MERGE_LINE not in dana.drift()

    #    The status now names Quinn's rule, which has no test; Dana builds it.
    status = dana.status()
    assert '1 rule to write a test for: purlin:build' in status
    dana.write('src/stability.py', STABILITY_CODE_UNKNOWN.replace(
        '"room": 2}', '"room": 2, "refrigerated": 7}'))
    dana.append('tests/test_stability.py', CHILLED_TEST)
    dana.commit('feat(stability): a refrigerated sample keeps 7 days')
    dana.test('--commit')
    dana.merge_to_main('dev/unknown-storage')

    # 5. Collision two, dev first. Both add sample_age PROOF-4; Quinn pushes
    #    her branch, Dana's is merged first, and Quinn renumbers.
    quinn.git('checkout', '-q', 'main')
    quinn.git('pull', '-q', '--no-edit', 'origin', 'main')
    quinn.git('checkout', '-q', '-b', 'qa/year-end')
    quinn.write(AGE, spec('sample_age', AGE_ABOUT, AGE_RULES,
                          AGE_PROOFS + ['PROOF-4 ' + AGE_YEAR_END]))
    before_renumber = quinn.commit('spec(sample_age): an age across a year end')
    quinn.git('push', '-q', 'origin', 'qa/year-end')

    dana.git('checkout', '-q', '-b', 'dev/same-day')
    dana.write(AGE, spec('sample_age', AGE_ABOUT, AGE_RULES,
                         AGE_PROOFS + [AGE_SAME_DAY]))
    dana.append('tests/test_sample_age.py', AGE_SAME_DAY_TEST)
    dana.commit('test(sample_age): the same day is zero days')
    dana.test('--commit')
    dana.merge_to_main('dev/same-day')

    # 6. Dana, from Quinn's commit before the renumbering, marks a test for
    #    the proof as Quinn numbered it.
    dana.git('fetch', '-q', 'origin')
    dana.git('checkout', '-q', '-b', 'dev/year-end', before_renumber)
    dana.write('tests/test_year_end.py', YEAR_END_TEST)
    dana.commit('test(sample_age): an age across a year end')

    stopped = quinn.git('pull', '--no-edit', 'origin', 'main', check=False)
    assert 'CONFLICT' in stopped, stopped
    quinn.write(AGE, spec('sample_age', AGE_ABOUT, AGE_RULES, AGE_PROOFS + [
        AGE_SAME_DAY, 'PROOF-4 ' + AGE_YEAR_END]))
    quinn.git('add', '-A')
    quinn.git('commit', '-q', '--no-edit')
    status = quinn.status()
    assert opening(status)[0] == 'Tests: not met'
    assert '1 spec to repair: purlin:spec' in status
    assert 'PROOF-4' in quinn.drift()
    quinn.renumber('sample_age', status)
    text = read(quinn.path(AGE))
    assert '- ' + AGE_SAME_DAY in text
    assert '- PROOF-5 ' + AGE_YEAR_END in text
    quinn.commit('spec(sample_age): renumber the proof written twice')
    quinn.merge_to_main('qa/year-end')

    #    Dana's test still names PROOF-4, which now reads another proof.
    dana.git('pull', '-q', '--no-edit', 'origin', 'main')
    status = dana.status()
    assert opening(status)[0] == 'Tests: not met'
    stale = [line for line in status.splitlines()
             if line.startswith('tests/test_year_end.py:')]
    assert len(stale) == 1 and stale[0].endswith(
        'Its old wording is now PROOF-5: move the comment there.'), status
    assert 'names sample_age PROOF-4, whose wording changed after the test ' \
           'was last changed in ' in stale[0]
    assert '1 test comment to correct: purlin:build' in status
    given(skill('build'), 'moves as `purlin:spec`\'s "Renumbering" says')
    given(skill('spec'), "a test comment whose proof's old wording now stands "
                         'under another id')
    given(skill('spec'), 'scripts/spec/renumber.py" <name> --dry-run')
    dana.script('renumber --dry-run', RENUMBER, 'sample_age', '--dry-run')
    dana.script('renumber --yes', RENUMBER, 'sample_age', '--yes')
    assert '# purlin: sample_age PROOF-5\ndef test_across_a_year_end' in read(
        dana.path('tests/test_year_end.py'))
    dana.commit('spec(sample_age): the year-end test names PROOF-5')
    status = dana.status()
    assert not [line for line in status.splitlines()
                if line.startswith('tests/test_year_end.py:')]
    assert 'test comment to correct' not in status
    dana.merge_to_main('dev/year-end')

    # 7. The hand-off: Dana runs everything on main and commits the results.
    given(skill('test'), 'purlin:test --all --commit The hand-off')
    out = dana.test('--all', '--commit')
    assert 'Markers: 9 tied to a test, 0 not tied.' in out
    assert out.rstrip().endswith(LAST_LINE), out
    status = dana.status()
    assert opening(status) == ('Tests: met', 'Sign-off: not signed')
    dana.git('push', '-q', 'origin', 'main')
    pat.git('checkout', '-q', 'main')
    pat.git('pull', '-q', '--no-edit', 'origin', 'main')

    # 8. Quinn signs: the walk shown, a key set up as printed, the hand check
    #    answered with nothing, and the push the sign-off names.
    quinn.git('pull', '-q', '--no-edit', 'origin', 'main')
    given(status, 'To sign it: purlin:sign')
    given(skill('sign'), 'scripts/review/sign.py" --show',
          'scripts/review/sign.py" --answers .purlin/runtime/'
          'signoff-answers.json')
    shown = quinn.sign('--show')
    head7 = quinn.git('rev-parse', 'HEAD')[:7]
    assert 'Signing %s at %s.' % (VERSION, head7) in shown
    assert '%s   hand check' % HAND_CHECK in shown
    assert NO_KEY not in shown
    answers = quinn.answers()
    printed = quinn.sign('--answers', answers, expect=1)
    assert NO_KEY in printed and not quinn.git('tag', '-l')
    quinn.set_up_the_key(printed)
    signed = quinn.sign('--answers', answers)
    assert 'Signed %s as %s with the key ending ...' % (
        VERSION, quinn.email) in signed
    tagged = quinn.git('rev-parse', 'HEAD')
    assert 'Tagged %s at %s.' % (TAG, tagged[:7]) in signed
    push = 'git push origin main ' + TAG
    assert signed.rstrip().endswith('Push the branch and the tag: ' + push)
    quinn.git(*push.split()[1:])

    # 9. Pat, still on main as it stood before Quinn signed, is refused,
    #    pulls as the refusal says, and signs second.
    pat.git('fetch', '-q', '--tags', 'origin')
    answers = pat.answers()
    refused = pat.sign('--answers', answers, expect=1)
    assert refused.strip() == (
        'No sign-off: %s is at %s, which this checkout does not hold. Pull, '
        'then run purlin:sign.' % (TAG, tagged[:7]))
    pat.git('pull', '-q', '--no-edit', 'origin', 'main')
    printed = pat.sign('--answers', answers, expect=1)
    pat.set_up_the_key(printed)
    second = pat.sign('--answers', answers)
    assert 'Signed %s as %s with the key ending ...' % (
        VERSION, pat.email) in second
    stays = ('%s stays at %s; this sign-off is added after it. Push it: '
             'git push origin main' % (TAG, tagged[:7]))
    assert second.rstrip().endswith(stays)
    pat.git('push', 'origin', 'main')

    # 10. The end, read in a fresh clone.
    check = team.person('reader')
    fresh = check.root

    #     The tag is on the host, on the commit Quinn signed.
    on_host = dict(reversed(line.split()) for line in check.git(
        'ls-remote', '--tags', 'origin').splitlines())
    assert on_host['refs/tags/%s^{}' % TAG] == tagged
    assert check.git('rev-list', '-n', '1', TAG) == tagged

    #     The package at the tag matches its fingerprint and describes the
    #     code under the tag: nothing but the package lies between them.
    given(skill('sign'), 'scripts/review/sign.py" --check '
                         '.purlin/evidence/package/<version>.json')
    at_tag = os.path.join(team.base, 'package-at-tag.json')
    write(at_tag, check.git('show', '%s:%s' % (TAG, PACKAGE)) + '\n')
    assert check.run('purlin:sign --check', [
        sys.executable, SIGN, '--check', at_tag]).strip() == (
            'The package matches its fingerprint.')
    package = json.loads(read(check.path(PACKAGE)))
    assert package == json.loads(read(at_tag))
    assert package['tag'] == TAG and package['version'] == VERSION
    assert package['met'] is True
    between = check.git('diff', '--name-only', package['commit'], TAG)
    assert between and all(path.startswith('.purlin/evidence/package/')
                           for path in between.splitlines()), between

    #     Both sign-offs count, and the hand check's note reads `no note`.
    sys.path.insert(0, os.path.join(SCRIPTS, 'mcp'))
    from purlin import signatures
    signoffs = signatures.load_signoffs(fresh, VERSION)
    assert sorted((entry['signer'], entry['counts']) for entry in signoffs) == [
        (pat.email, True), (quinn.email, True)], signoffs
    for entry in signoffs:
        assert entry['notes'] == [{'feature': 'sample_age', 'rule': 'RULE-3',
                                   'note': 'no note'}], entry

    #     The status opens on both facts and carries no warning seen before.
    status = check.status()
    assert opening(status) == ('Tests: met',
                               'Sign-off: signed %s at %s' % (VERSION,
                                                             tagged[:7]))
    data = read(check.path('.purlin/report-data.js'))
    payload = json.loads(data[data.index('{'):].rstrip().rstrip(';'))
    assert team.warned, 'the collisions raised no warning to resolve'
    assert payload['warnings'] == []
    assert [item['kind'] for item in payload['left']] == []

    #     No spec holds a number twice or a conflict line, and each spec's
    #     highest-number lines cover its numbers.
    listed = 0
    #     Stability's lines stand as the renumbering kept them: Dana's
    #     side first, then Quinn's.
    for rel, rules, proofs in ((AGE, [1, 2, 3], [1, 2, 3, 4, 5]),
                               (STABILITY, [1, 2, 4, 3], [1, 2, 3, 5, 4])):
        text = read(check.path(rel))
        assert conflict_lines(text) == []
        assert numbers(text, 'RULE') == rules
        assert numbers(text, 'PROOF') == proofs
        assert highest(text, 'rule') >= max(rules)
        assert highest(text, 'proof') >= max(proofs)
        listed += len(rules)

    #     Every test comment is tied and names the proof it was marked
    #     against.
    assert check.script('wording', WORDING).strip() == (
        'No test comment to correct.')
    comments = {}
    for name in sorted(os.listdir(check.path('tests'))):
        for proof in re.findall(r'^# purlin: (\w+ PROOF-\d+)$',
                                read(check.path('tests/' + name)), re.M):
            comments[proof] = comments.get(proof, 0) + 1
    assert comments == {
        'sample_age PROOF-1': 1, 'sample_age PROOF-2': 1,
        'sample_age PROOF-4': 1, 'sample_age PROOF-5': 1,
        'stability PROOF-1': 1, 'stability PROOF-2': 1,
        'stability PROOF-3': 1, 'stability PROOF-4': 1,
        'stability PROOF-5': 1}

    #     The package lists every rule.
    assert package['rules'] == listed == 7
    in_package = sorted('%s %s' % (feature['name'], rule['id'])
                        for feature in package['features']
                        for rule in feature['rules'])
    assert in_package == ['sample_age RULE-1', 'sample_age RULE-2',
                          'sample_age RULE-3', 'stability RULE-1',
                          'stability RULE-2', 'stability RULE-3',
                          'stability RULE-4']

    #     No command failed but the ones planned, each named here: the first
    #     test run with no test command set, the two sign-offs asked for with
    #     no key, and Pat's before the pull.
    assert [entry for entry in team.codes if entry[2] != entry[3]] == []
    assert [entry[:2] for entry in team.codes if entry[2] != 0] == [
        ('dana', 'purlin:test '),
        ('quinn', 'purlin:sign --answers ' + answers),
        ('pat', 'purlin:sign --answers ' + answers),
        ('pat', 'purlin:sign --answers ' + answers)]
