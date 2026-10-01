"""What the init skill, `skills/init/SKILL.md`, must name.

One test per proof of `specs/skills/skill_init.md`. Two read the skill's
text. The third asks the setup script itself, `scripts/init/scaffold.py`, for
its usage and holds every flag the skill hands a reader to it. The readers
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
