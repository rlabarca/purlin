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
    assert sorted(handed - set(FLAG.findall(done.stdout))) == []


# purlin: skill_init PROOF-42
def test_a_reader_finds_the_files_setup_writes_and_the_two_references():
    text = flat(read(SKILL))
    assert [name for name in PATHS if name not in text] == []
    assert must_name('init', paths=PATHS) == []


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
    applied = _line_with(lines, [RUN_PATH, '--update', '--apply',
                                 '--test-command'])
    assert listed < asked < applied


# purlin: skill_init PROOF-100
def test_the_flags_the_upgrade_part_hands_apply_one_migration_unasked(
        tmp_path):
    import shutil
    sys.path.insert(0, str(ROOT / 'scripts' / 'init'))
    import update
    lines = upgrade_part()
    handed = FLAG.findall(lines[_line_with(lines, [RUN_PATH, '--apply'])])
    assert sorted(handed) == ['--apply', '--project-root', '--test-command',
                              '--update']
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
    asked = _line_with(lines, ['**Stop and ask**', 'restore'])
    restored = _line_with(lines, ['--update', '--yes'])
    assert listed < asked < restored


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
