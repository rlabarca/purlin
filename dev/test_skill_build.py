"""What the build skill, `skills/build/SKILL.md`, must name, and what a
session does with it.

One test per proof of `specs/skills/skill_build.md`. The check of what the
skill names is `must_name` in `dev/skill_checks.py`.

The last two tests are of AI proofs: each hands the sample lab of
`dev/sample_lab.py` to a real session with this repository as its plugin,
through the helper the run names in `PURLIN_AI`, and asserts on the folder
the helper prints. They skip where `PURLIN_AI` is not set, so this file run
by hand, and the sweep, reach no model.
"""

import os
import re

import pytest

import sample_lab
from skill_checks import (flat, must_name, not_named, read, skill_path,
                          under_heading)

SKILL = skill_path('build')

COMMANDS = ('sync_status', 'purlin:test', 'purlin:test --all --commit',
            'purlin:spec', 'purlin:audit <feature> RULE-N --settle')
FILES = ('scripts/purlin_python.sh', 'scripts/mcp/purlin/markers.py',
         'scripts/mcp/purlin/wording.py', 'references/commit_conventions.md',
         'references/review_criteria.md')


# purlin: skill_build PROOF-51
def test_the_build_skill_holds_each_command_and_file_the_settle_included():
    text = flat(read(SKILL))
    assert 'purlin:audit <feature> RULE-N --settle' in COMMANDS
    assert 'references/review_criteria.md' in FILES
    assert [name for name in COMMANDS + FILES if name not in text] == []
    assert must_name('build', commands=COMMANDS, paths=FILES) == []


SOUND = ('purlin:audit <feature> RULE-N --settle --sound PROOF-N',
         'Never pass it for a test you did not read against its proof')


# purlin: skill_build PROOF-52
def test_the_build_skill_says_how_a_test_left_alone_is_settled():
    section = under_heading(read(SKILL), 'Strengthening a weak rule')
    assert section
    assert not_named(section, SOUND) == []


AI_TEST = ('references/purlin_commands.md', 'references/rule_examples.md',
           'One test makes one output.',
           "A graded proof's test then starts `grade` and asserts it exits 0.",
           'The test passes or skips when `PURLIN_AI` is not set')


# purlin: skill_build PROOF-53
def test_the_build_skill_says_how_the_test_of_an_ai_proof_is_written():
    section = under_heading(read(SKILL), 'The test of an AI proof')
    assert section
    assert not_named(section, AI_TEST) == []


SAYS_FIRST = ('Run `purlin:test --all` once the test is written, as '
              '`skills/test/SKILL.md` says to run it.')


# purlin: skill_build PROOF-54
def test_the_build_skill_runs_the_full_run_as_the_test_skill_says():
    section = under_heading(read(SKILL), 'The test of an AI proof')
    assert SAYS_FIRST in flat(section)


needs_the_helper = pytest.mark.skipif(not os.environ.get('PURLIN_AI'),
                                      reason=sample_lab.NOT_STARTED)

STRENGTHEN = ('Strengthen RULE-3 of sample_intake with purlin:build. Work '
              'only in this folder.')
EVIDENCE = '.purlin/evidence/local/sample_intake.json'
# The number 25, and not the 25 of another number.
THE_AGE = re.compile(r'(?<![\w.])25(?![\w.])')


def under(changed, folder):
    return [path for path in changed if path.startswith(folder + '/')]


# purlin: skill_build PROOF-55
@needs_the_helper
def test_a_session_strengthens_the_test_of_a_weak_rule_and_settles_it(
        tmp_path, no_real_model):
    root = sample_lab.for_a_session(tmp_path)
    assert not THE_AGE.search(sample_lab.marked(sample_lab.TESTS, 'PROOF-5'))
    output = sample_lab.session(root, STRENGTHEN, no_real_model)
    changed = sample_lab.files_of(output)
    assert 'tests/test_intake.py' in changed
    with open(os.path.join(output, 'files', 'tests', 'test_intake.py'),
              encoding='utf-8') as handle:
        assert THE_AGE.search(sample_lab.marked(handle.read(), 'PROOF-5'))
    assert under(changed, 'specs') == []
    assert EVIDENCE in changed
    rule = sample_lab.entries(os.path.join(output, 'files'))['RULE-3']
    assert rule['verdict'] == 'strong'
    assert rule['bugs']['PROOF-5']['result'] == 'caught'


# purlin: skill_build PROOF-56
@needs_the_helper
def test_a_session_stops_for_a_proof_that_names_too_little(
        tmp_path, no_real_model):
    root = sample_lab.for_a_session(tmp_path, loose=True)
    output = sample_lab.session(root, STRENGTHEN, no_real_model)
    changed = sample_lab.files_of(output)
    assert [under(changed, folder)
            for folder in ('specs', 'tests', 'src')] == [[], [], []]
    graded = sample_lab.grade('skill_build', 'PROOF-56', no_real_model)
    assert graded.returncode == 0, graded.stdout + graded.stderr
