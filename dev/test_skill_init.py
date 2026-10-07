"""What the init skill, `skills/init/SKILL.md`, must name.

One test per proof of `specs/skills/skill_init.md`. Four read the skill's
text. One asks the setup script itself, `scripts/init/scaffold.py`, for its
usage and holds every flag the skill hands a reader to it, one runs the
script on a project 0.9.5 set up with the flags the skill's upgrade part
hands, and one runs it on a sample project this release set up and holds
each line the skill's restoring part quotes to what it prints. The readers
are in `dev/skill_checks.py`.
"""

import os
import re
import subprocess
import sys

from skill_checks import ROOT, flat, must_name, read, same_line, skill_path

SKILL = skill_path('init')
SCAFFOLD = ROOT / 'scripts' / 'init' / 'scaffold.py'

LOOKUP = 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"'
RUN_PATH = '"${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py"'

PATHS = ('.purlin/config.json', '.purlin/evidence/', 'specs/',
         'references/supported_frameworks.md',
         'references/formats/marker_format.md')

# A flag, as a person types it.
FLAG = re.compile(r'(?<![\w-])--[a-z][a-z-]*')


def handed_flags():
    """Every flag on a line that runs the script, and in the first column of
    the flag table."""
    handed = []
    for line in read(SKILL).splitlines():
        if 'scripts/init/scaffold.py' in line:
            handed.extend(FLAG.findall(line))
        elif line.startswith('| `--'):
            handed.extend(FLAG.findall(line.split('|')[1]))
    return handed


# purlin: skill_init PROOF-2
def test_one_line_runs_the_script_through_the_lookup_with_the_root():
    assert same_line(SKILL, [LOOKUP + ' ' + RUN_PATH, '--project-root']) == []
    # The line that runs setup, the one line that runs the script without
    # `--update`, is the script through the lookup with `--project-root` and
    # its folder, and nothing else; every line that runs the script passes
    # `--project-root`.
    runs = [line.strip() for line in read(SKILL).splitlines()
            if RUN_PATH in line]
    assert len(runs) == 3, runs
    assert [line for line in runs
            if not line.startswith(LOOKUP + ' ' + RUN_PATH + ' ')
            or not re.search(r'(?<![\w-])--project-root \S', line)] == []
    setup = [line for line in runs if '--update' not in line]
    assert len(setup) == 1, setup
    assert re.fullmatch(re.escape(LOOKUP + ' ' + RUN_PATH)
                        + r' --project-root \S+', setup[0]), setup


# purlin: skill_init PROOF-24
def test_every_flag_handed_is_one_the_usage_lists():
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    done = subprocess.run([sys.executable, str(SCAFFOLD), '--help'],
                          capture_output=True, encoding='utf-8', timeout=120,
                          env=env, stdin=subprocess.DEVNULL)
    assert done.returncode == 0
    handed = set(handed_flags())
    assert '--project-root' in handed and len(handed) > 1
    listed = set(FLAG.findall(done.stdout))
    assert sorted(handed - listed) == [], (handed, listed)
    # A line that tells the reader to run the script with flags it quotes,
    # as `--update --project-root . --yes`, hands them too: every flag in a
    # quoted span that opens with a flag is one the usage lists, each a
    # whole flag of the usage and not the start of one.
    listed = set(FLAG.findall(done.stdout))
    quoted = [flag for span in re.findall(r'`(--[^`]*)`', read(SKILL))
              for flag in FLAG.findall(span)]
    assert '--yes' in quoted and '--update' in quoted, quoted
    assert sorted(set(quoted) - listed) == []
    assert sorted(set(handed) | set(quoted)) == [
        '--apply', '--project-root', '--test-command', '--update', '--yes']
    # A quoted run of flags is one wherever it stands in its span: after
    # the command's own name, as `purlin:init --update --project-root .`,
    # as much as at its start. So every quoted span of the skill's
    # sentences that holds a flag is read, a flag being two dashes and what
    # follows them in either case. The one span set aside is the one that
    # names another command, whose flags are that command's.
    anywhere = re.compile(r'(?<![\w-])--[A-Za-z0-9][\w-]*')
    usage = sorted(set(anywhere.findall(done.stdout + done.stderr)))
    assert usage == ['--apply', '--help', '--project-root', '--test-command',
                     '--update', '--yes'], done.stdout
    sentences = re.sub(r'```.*?```', '', read(SKILL), flags=re.S)
    assert sentences.count('`') % 2 == 0
    runs = [span for span in re.findall(r'`([^`]*)`', sentences)
            if anywhere.search(span)]
    others = [span for span in runs if re.search(r'purlin:(?!init\b)', span)]
    assert others == ['→ Run: purlin:test --all --commit'], others
    in_sentences = [(flag, span) for span in runs if span not in others
                    for flag in anywhere.findall(span)]
    assert len(in_sentences) >= len(quoted)
    assert [(flag, span) for flag, span in in_sentences
            if flag not in usage] == []
    assert sorted(set(flag for flag, _span in in_sentences)) == [
        '--apply', '--project-root', '--test-command', '--update', '--yes']
    # A flag written with one dash is a flag handed too: every word of such
    # a span that opens with a dash is a flag of the usage, whole.
    dashed = [(word, span) for span in runs if span not in others
              for word in span.split() if word.startswith('-')]
    assert [(word, span) for word, span in dashed
            if word.rstrip('.,') not in usage] == []


# purlin: skill_init PROOF-42
def test_a_reader_finds_the_files_setup_writes_and_the_two_references():
    text = flat(read(SKILL))
    assert [name for name in PATHS if name not in text] == []
    assert must_name('init', paths=PATHS) == []
    # Each is named whole, as its own quoted name: `marker_format.mdx` is
    # another file and does not name `marker_format.md`.
    assert [name for name in ('.purlin/config.json', '.purlin/evidence/',
                              'specs/', 'references/supported_frameworks.md',
                              'references/formats/marker_format.md')
            if '`%s`' % name not in text] == []


# --- bringing a 0.9.5 project forward ----------------------------------------

UPGRADE_HEADING = '## Bringing a 0.9.5 project forward'


def part(heading):
    """The skill's lines from `heading` to the next heading."""
    text = read(SKILL)
    start = text.index(heading)
    end = text.index('\n## ', start + 1)
    return text[start:end].splitlines()


def upgrade_part():
    return part(UPGRADE_HEADING)


def _line_with(lines, names):
    hits = [index for index, line in enumerate(lines)
            if all(name in line for name in names)]
    assert hits, names
    return hits[0]


# purlin: skill_init PROOF-99
def test_the_upgrade_part_lists_then_asks_then_passes_each_answer():
    lines = upgrade_part()
    listed = _line_with(lines, [RUN_PATH, '--update', '< /dev/null'])
    asked = _line_with(lines, ['**Stop and ask**', 'each migration',
                               'test command'])
    # The step names each migration and each proposed test command, not one
    # of them: both stand in the step's own sentence.
    step = flat(' '.join(lines[asked:asked + 3]))
    assert re.search(r'\*\*Stop and ask\*\* [^.:]*\beach migration\b[^.:]*'
                     r'\beach proposed test command\b', step), step
    # The step's opening line whole: both are things to ask about, joined
    # by `and`, with no word between that takes one of them back.
    assert lines[asked].strip() == (
        '2. **Stop and ask** the person about each migration listed and '
        'each proposed test command:'), lines[asked]
    applied = _line_with(lines, [RUN_PATH, '--update', '--apply',
                                 '--test-command'])
    assert listed < asked < applied


# purlin: skill_init PROOF-100
def test_the_flags_the_upgrade_part_hands_apply_one_migration_unasked(
        tmp_path):
    import shutil
    sys.path.insert(0, str(ROOT / 'scripts' / 'init'))
    import update
    import shlex
    lines = upgrade_part()
    handed = FLAG.findall(lines[_line_with(lines, [RUN_PATH, '--apply'])])
    assert sorted(handed) == ['--apply', '--project-root', '--test-command',
                              '--update']
    # The words the skill's own line gives after the script, split as a
    # shell splits them: the flags and their values, in the line's order.
    words = shlex.split(lines[_line_with(lines, [RUN_PATH, '--apply'])])
    assert words[:3] == [
        'sh', '${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh',
        '${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py'], words
    given = words[3:]
    assert given == ['--update', '--project-root', '.', '--apply',
                     '<id>,<id>', '--test-command', 'pytest=<command>'], given
    root = str(tmp_path / 'project')
    shutil.copytree(str(ROOT / 'dev' / 'fixtures' / 'upgrade-0.9.5'), root)
    os.rename(os.path.join(root, '_gitignore'),
              os.path.join(root, '.gitignore'))
    for args in (['-c', 'init.defaultBranch=main', 'init', '-q'],
                 ['config', 'user.name', 'Test Person'],
                 ['config', 'user.email', 'test@example.com'],
                 ['config', 'commit.gpgsign', 'false'],
                 ['add', '-A'], ['commit', '-qm', 'init']):
        subprocess.run(['git'] + args, cwd=root, check=True,
                       capture_output=True)
    before = [item['id'] for item in update.pending(root)]
    assert 'evidence' in before
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)
    done = subprocess.run(
        [sys.executable, str(SCAFFOLD), '--update', '--project-root', root,
         '--apply', 'evidence', '--test-command', 'pytest=pytest {files}'],
        capture_output=True, encoding='utf-8', timeout=300, env=env,
        stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stdout + done.stderr
    assert '[y/N]' not in done.stdout
    # What ran is the line's own words, each placeholder filled in: the
    # folder for `.`, one migration for the ids, a command for `<command>`.
    filled = {'.': root, '<id>,<id>': 'evidence',
              'pytest=<command>': 'pytest=pytest {files}'}
    assert [filled.get(word, word) for word in given] == done.args[2:]
    assert [item['id'] for item in update.pending(root)] == [
        name for name in before if name != 'evidence']


# --- restoring a file setup writes --------------------------------------------

RESTORE_HEADING = '## Restoring a file setup writes'
RESTORED = ('.gitignore', '.purlin/evidence/README.md', '.purlin/config.json',
            'the dashboard page')
NOTHING_RESTORED = 'Nothing was restored. Add --yes to restore each file.'


# purlin: skill_init PROOF-101
def test_the_restoring_part_names_the_files_then_lists_asks_and_restores():
    lines = part(RESTORE_HEADING)
    text = flat('\n'.join(lines))
    assert [name for name in RESTORED if name not in text] == []
    listed = _line_with(lines, ['**List.**'])
    # The four are named before the `List` step.
    opening = flat('\n'.join(lines[:listed]))
    at = [opening.find(name) for name in (
        '`.gitignore`', '`.purlin/evidence/README.md`',
        '`.purlin/config.json`', 'the dashboard page')]
    assert -1 not in at, (at, opening)
    asked = _line_with(lines, ['**Stop and ask**', 'restore'])
    restored = _line_with(lines, ['--update', '--yes'])
    assert listed < asked < restored
    assert re.search(r'(?<![\w-])--update(?![\w-])', lines[restored])
    assert re.search(r'(?<![\w-])--yes(?![\w-])', lines[restored])


# purlin: skill_init PROOF-102
def test_the_lines_the_restoring_part_quotes_are_the_ones_the_script_prints(
        tmp_path):
    sys.path.insert(0, str(ROOT / 'dev'))
    import sample_lab
    text = flat('\n'.join(part(RESTORE_HEADING)))
    quoted = ['`<n> files to restore in <folder>:`', '`' + NOTHING_RESTORED
              + '`', '`Restoring <n> files: <files>.`',
              '`restored <file>: <what the file is for>`',
              '`chore(update): restore <files>`']
    assert [line for line in quoted if line not in text] == []
    root = sample_lab.build(tmp_path)
    for args in (['config', 'user.name', 'Test Person'],
                 ['config', 'user.email', 'test@example.com'],
                 ['config', 'commit.gpgsign', 'false']):
        subprocess.run(['git'] + args, cwd=root, check=True,
                       capture_output=True)
    env = dict(os.environ)
    env.pop('CLAUDE_PLUGIN_ROOT', None)

    def run(*flags):
        done = subprocess.run(
            [sys.executable, str(SCAFFOLD), '--update', '--project-root',
             root] + list(flags), capture_output=True, encoding='utf-8',
            timeout=300, env=env, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        return done.stdout.splitlines()

    listing = run()
    assert listing[0] == '2 files to restore in %s:' % os.path.abspath(root)
    assert listing[-1] == NOTHING_RESTORED
    printed = run('--yes')
    assert printed[0] == ('Restoring 2 files: .gitignore, '
                          '.purlin/evidence/README.md.')
    assert printed[2] == ('  restored .purlin/evidence/README.md: says what '
                          'the evidence folder holds')
    assert printed[3].endswith('as chore(update): restore .gitignore, '
                               '.purlin/evidence/README.md')


TAGS_THAT_STAY = ('; `@manual`, `@slow`, `@env(...)`, `@ai(...)` and '
                  '`@graded(...)` stay;')
NO_RUNS = ('Setup writes no `runs`: where a project wants another count '
           'than 3, write it with the `purlin_config` tool.')


# purlin: skill_init PROOF-103
def test_a_reader_finds_the_tags_that_stay_and_who_writes_runs():
    text = flat(read(SKILL))
    assert TAGS_THAT_STAY in text
    assert NO_RUNS in text
