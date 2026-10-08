"""What the agent definition, `agents/purlin.md`, must name, and seven checks
on what every skill, the agent definition and the references tell an agent
to run.

One test per proof of `specs/instructions/purlin_agent.md`. The readers are
in `dev/skill_checks.py`. The checks read the skills and the references as they stand, so
a skill that names a path the repository does not hold, or passes a flag its
script does not take, fails here with the file and what it named.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from skill_checks import (AGENT, ROOT, absent_paths, dev_paths,
                          json_block_under, named_paths, not_named, read,
                          reference_files, sentences_with, skill_files,
                          skill_path, status_unnamed, unknown_flags)
from sign_project import git, signing_key, write

sys.path.insert(0, str(ROOT / 'scripts' / 'mcp'))

from purlin import PURLIN_VERSION, frameworks  # noqa: E402

COMMANDS = ('sync_status', 'purlin:drift', 'purlin:spec', 'purlin:build',
            'purlin:test', 'purlin:test --all --commit', 'purlin:status',
            'purlin:audit', 'purlin:sign')
FILES = ('references/glossary.md', 'references/evidence_and_signoff.md',
         'references/spec_quality_guide.md',
         'references/formats/marker_format.md',
         '.purlin/evidence/<source>/<name>.json')


# purlin: purlin_agent PROOF-49
def test_the_agent_definition_holds_each_command_and_file():
    # A name a letter or a digit runs into is another name: `async_status`
    # is not `sync_status`, and `mcp__plugin_purlin_purlin__sync_status` is.
    names = sorted(COMMANDS + FILES, key=len, reverse=True)
    run_into = re.compile(r'[^\W_](?:%s)' % '|'.join(
        r'\s+'.join(re.escape(word) for word in name.split(' '))
        for name in names))
    assert not_named(run_into.sub(' ', read(AGENT)), COMMANDS + FILES) == []


# purlin: purlin_agent PROOF-60
def test_a_name_is_held_whole_with_each_space_as_written():
    agent = read(AGENT)
    plural, changed = re.subn(r'purlin:spec(?![\w-])', 'purlin:specs', agent)
    assert changed
    assert not_named(plural, COMMANDS + FILES) == ['purlin:spec']
    assert 'purlin:test --all --commit' in agent
    spaced = agent.replace('purlin:test --all --commit',
                           'purlin:test  --all --commit')
    assert not_named(spaced, COMMANDS + FILES) == [
        'purlin:test --all --commit']


# purlin: purlin_agent PROOF-50
def test_one_sentence_names_a_worktree_merging_the_status_and_the_main_checkout():
    # The command is held whole: `purlin:statusline` is not `purlin:status`.
    status = re.compile(r'(?<![\w:-])purlin:status(?![\w:-])')
    # A sentence ends at `?` and `!` as it does at `.`.
    names = ('worktree', 'merge', 'main checkout')
    found = [sentence for part in sentences_with(AGENT, ())
             for sentence in re.split(r'(?<=[?!])\s+', part)
             if all(name in sentence for name in names)
             and status.search(sentence)]
    assert len(found) == 1, found
    assert '`purlin:status`' in found[0], found


# --- what the skills tell an agent to run -------------------------------------

def _found(files, check):
    """`{file: what the check lists}` for each file where it lists anything."""
    return {rel: check(read(rel)) for rel in files if check(read(rel))}


# purlin: purlin_agent PROOF-51
def test_every_path_a_skill_or_the_agent_definition_names_exists():
    files = skill_files() + [AGENT]
    assert len(files) == 11, files
    for rel in files:
        assert named_paths(read(rel)), '%s names no path' % rel
    assert _found(files, absent_paths) == {}
    sign = read(skill_path('sign'))
    assert 'scripts/review/sign.py' in sign
    copy = sign.replace('scripts/review/sign.py', 'scripts/review/signoff.py')
    assert absent_paths(copy) == ['scripts/review/signoff.py']


# purlin: purlin_agent PROOF-61
def test_a_path_is_looked_for_letter_for_letter():
    agent = read(AGENT)
    assert 'references/glossary.md' in agent
    copy = agent.replace('references/glossary.md', 'references/Glossary.md')
    assert absent_paths(copy) == ['references/Glossary.md']


# purlin: purlin_agent PROOF-52
def test_every_flag_a_skill_passes_is_one_its_script_takes():
    assert _found(skill_files(), unknown_flags) == {}
    copy, changed = re.subn(r'(scripts/run/purlin_run\.py"?)', r'\1 --nonesuch',
                            read(skill_path('test')), count=1)
    assert changed == 1
    assert unknown_flags(copy) == [('scripts/run/purlin_run.py', '--nonesuch')]


ANSWERS = '.purlin/runtime/signoff-answers.json'
SIGNER = 'quinn.qa@labconnect.example'
# A spec with one hand check and one tested rule: its name, then the two
# rule numbers.
HAND_SPEC = ('# Feature: %s\n\n'
             '> Description: A screen a person reads and a value a test '
             'reads.\n'
             '> Scope: src/%s.py\n\n'
             '## Rules\n\n'
             '- RULE-%d: The screen shows the colour of the tube\n'
             '- RULE-%d: The value is 1\n\n'
             '## Proof\n\n'
             '- PROOF-1 (RULE-%d): Open the screen for a red tube; it reads '
             '`red` @manual\n'
             '- PROOF-2 (RULE-%d): Call `value()`; it returns `1`\n')
HAND_TEST = ('from src.%s import value\n\n\n'
             '# purlin: %s PROOF-2\n'
             'def test_the_value_is_1():\n'
             '    assert value() == 1\n')


def _hand_check_project():
    """A project whose hand checks are `accession_screen RULE-1` and
    `sample_age RULE-6`, every other rule passing in evidence a real run
    committed, with a throwaway key to sign with."""
    root = tempfile.mkdtemp()
    for name, manual, tested in (('accession_screen', 1, 2),
                                 ('sample_age', 6, 5)):
        write(os.path.join(root, 'specs', 'lab', name + '.md'),
              HAND_SPEC % (name, name, manual, tested, manual, tested))
        write(os.path.join(root, 'src', name + '.py'),
              'def value():\n    return 1\n')
        write(os.path.join(root, 'tests', 'test_%s.py' % name),
              HAND_TEST % (name, name))
    write(os.path.join(root, 'src', '__init__.py'), '')
    write(os.path.join(root, 'VERSION'), '0.1.0\n')
    write(os.path.join(root, '.gitignore'),
          '.purlin/runtime/\n__pycache__/\n.pytest_cache/\n')
    write(os.path.join(root, '.purlin', 'config.json'),
          json.dumps({'version': PURLIN_VERSION,
                      'tests': frameworks.suggest(root)}))
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'config', 'user.email', 'dev@example.com')
    git(root, 'config', 'user.name', 'Dev')
    git(root, 'config', 'commit.gpgsign', 'false')
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', 'chore: project under test')
    ran = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'run' / 'purlin_run.py'),
         '--all', '--test', '--commit', '--project-root', root],
        capture_output=True, text=True, encoding='utf-8')
    assert ran.returncode == 0, ran.stdout + ran.stderr
    signing_key(root, SIGNER)
    return root


# purlin: purlin_agent PROOF-53
def test_the_answers_file_the_sign_skill_shows_is_walked():
    answers = json_block_under(read(skill_path('sign')), 'Step 5')
    root = _hand_check_project()
    try:
        write(os.path.join(root, *ANSWERS.split('/')), json.dumps(answers))
        walk = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'review' / 'sign.py'),
             '--answers', ANSWERS], cwd=root,
            capture_output=True, text=True, encoding='utf-8')
        assert walk.returncode == 0, walk.stdout + walk.stderr
        signoffs = glob.glob(os.path.join(
            root, '.purlin', 'evidence', 'package', '0.1.0.signoffs',
            '*.json'))
        assert len(signoffs) == 1, signoffs
        with open(signoffs[0], encoding='utf-8') as handle:
            notes = json.load(handle)['notes']
        assert {'feature': 'accession_screen', 'rule': 'RULE-1',
                'note': 'the tube is red'} in notes
        assert [(note['feature'], note['rule']) for note in notes] == [
            ('accession_screen', 'RULE-1'), ('sample_age', 'RULE-6')]
    finally:
        shutil.rmtree(root, ignore_errors=True)


# purlin: purlin_agent PROOF-54
def test_no_skill_agent_definition_or_reference_names_a_path_under_dev():
    files = skill_files() + [AGENT] + reference_files()
    assert 'references/formats/spec_format.md' in files
    assert _found(files, dev_paths) == {}
    assert dev_paths('Send the output to `/dev/null`.') == []
    line = 'Run `dev/test_x.py` to see it.'
    copy = read(skill_path('build')) + line + '\n'
    assert dev_paths(copy) == [line]


# purlin: purlin_agent PROOF-55
def test_every_skill_naming_the_status_names_the_tool_and_the_script():
    holding = [rel for rel in skill_files() if 'sync_status' in read(rel)]
    assert skill_path('build') in holding, holding
    problems = [line for rel in holding
                for line in status_unnamed(rel.split('/')[1], read(rel))]
    assert problems == []
    build = read(skill_path('build'))
    copy = '\n'.join(line for line in build.splitlines()
                     if 'scripts/run/purlin_status.py' not in line)
    assert copy != build
    assert status_unnamed('build', copy) == [
        'build does not name scripts/run/purlin_status.py']


SETTLE = 'purlin:audit <feature> RULE-N --settle'


# purlin: purlin_agent PROOF-56
def test_the_command_reference_and_the_glossary_name_the_settle_command():
    assert not_named(read('references/purlin_commands.md'), (SETTLE,)) == []
    assert not_named(read('references/glossary.md'), (SETTLE,)) == []
    # The command as it is typed, one space between its words: only the end
    # of a wrapped line may stand for a space.
    for rel in ('references/purlin_commands.md', 'references/glossary.md'):
        joined = re.sub(r'[ \t]*\n[ \t]*', ' ', read(rel))
        assert SETTLE in joined, rel


AI_PROOF = ('AI proof', '@ai(<model>)', 'references/spec_quality_guide.md',
            'references/purlin_commands.md')


# purlin: purlin_agent PROOF-57
def test_one_sentence_says_what_an_ai_proof_is_and_where_to_read():
    assert len(sentences_with(AGENT, AI_PROOF)) == 1


HELPER_LINES = (
    'purlin_ai.py run --skill <folder> | --plugin <folder> | '
    '--instructions <file>...',
    'purlin_ai.py record --from <folder> [--model <name>]',
    'purlin_ai.py grade --feature <name> --proof PROOF-N')


# purlin: purlin_agent PROOF-58
def test_the_command_reference_gives_the_helpers_three_lines():
    lines = read('references/purlin_commands.md').splitlines()
    assert [line for line in HELPER_LINES if line not in lines] == []


HELPER_OPTIONS = ('--instructions', '--from <folder>', '--proof PROOF-N')


def helper_options(text):
    """Each option of the helper's command line the text holds."""
    return [name for name in HELPER_OPTIONS if name in text]


# purlin: purlin_agent PROOF-59
def test_no_skill_and_no_agent_definition_restates_the_helpers_line():
    assert _found(skill_files() + [AGENT], helper_options) == {}
    copy = (read(skill_path('build'))
            + 'purlin_ai.py record --from <folder>\n')
    assert helper_options(copy) == ['--from <folder>']
