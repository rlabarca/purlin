"""The checks of what Purlin prints and how its programs run.

`specs/instructions/purlin_output.md` holds three rules. No file under
`scripts/` or `templates/` carries a character with the Unicode property
`Extended_Pictographic`, or U+FE0F, other than `▶`: Python's own `re` cannot
name that property, so the ranges are written out below as a table, taken
from Unicode's `emoji-data.txt`, with adjacent ranges joined. Setup, a test
run and the status run on Python 3.9: every file under `scripts/` parses as
3.9, and each of the three is run under a Python 3.9 in a scratch project,
skipped where the machine has none. No command leaves a process of its own
running once it exits.
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suites  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FOLDERS = ('scripts', 'templates')

# Extended_Pictographic, from Unicode's emoji-data.txt: (first, last).
EXTENDED_PICTOGRAPHIC = (
    (0x00A9, 0x00A9), (0x00AE, 0x00AE), (0x203C, 0x203C), (0x2049, 0x2049),
    (0x2122, 0x2122), (0x2139, 0x2139), (0x2194, 0x2199), (0x21A9, 0x21AA),
    (0x231A, 0x231B), (0x2328, 0x2328), (0x2388, 0x2388), (0x23CF, 0x23CF),
    (0x23E9, 0x23F3), (0x23F8, 0x23FA), (0x24C2, 0x24C2), (0x25AA, 0x25AB),
    (0x25B6, 0x25B6), (0x25C0, 0x25C0), (0x25FB, 0x25FE), (0x2600, 0x2605),
    (0x2607, 0x2612), (0x2614, 0x2685), (0x2690, 0x2705), (0x2708, 0x2712),
    (0x2714, 0x2714), (0x2716, 0x2716), (0x271D, 0x271D), (0x2721, 0x2721),
    (0x2728, 0x2728), (0x2733, 0x2734), (0x2744, 0x2744), (0x2747, 0x2747),
    (0x274C, 0x274C), (0x274E, 0x274E), (0x2753, 0x2755), (0x2757, 0x2757),
    (0x2763, 0x2767), (0x2795, 0x2797), (0x27A1, 0x27A1), (0x27B0, 0x27B0),
    (0x27BF, 0x27BF), (0x2934, 0x2935), (0x2B05, 0x2B07), (0x2B1B, 0x2B1C),
    (0x2B50, 0x2B50), (0x2B55, 0x2B55), (0x3030, 0x3030), (0x303D, 0x303D),
    (0x3297, 0x3297), (0x3299, 0x3299), (0x1F000, 0x1F0FF),
    (0x1F10D, 0x1F10F), (0x1F12F, 0x1F12F), (0x1F16C, 0x1F171),
    (0x1F17E, 0x1F17F), (0x1F18E, 0x1F18E), (0x1F191, 0x1F19A),
    (0x1F1AD, 0x1F1E5), (0x1F201, 0x1F20F), (0x1F21A, 0x1F21A),
    (0x1F22F, 0x1F22F), (0x1F232, 0x1F23A), (0x1F23C, 0x1F23F),
    (0x1F249, 0x1F3FA), (0x1F400, 0x1F53D), (0x1F546, 0x1F64F),
    (0x1F680, 0x1F6FF), (0x1F774, 0x1F77F), (0x1F7D5, 0x1F7FF),
    (0x1F80C, 0x1F80F), (0x1F848, 0x1F84F), (0x1F85A, 0x1F85F),
    (0x1F888, 0x1F88F), (0x1F8AE, 0x1F8FF), (0x1F90C, 0x1F93A),
    (0x1F93C, 0x1F945), (0x1F947, 0x1FAFF), (0x1FC00, 0x1FFFD),
)
VARIATION_SELECTOR_16 = 0xFE0F
ALLOWED = {ord('▶')}  # the one glyph Purlin prints that is a pictograph


def is_pictograph(character):
    """True for U+FE0F and any character with Extended_Pictographic."""
    code = ord(character)
    if code == VARIATION_SELECTOR_16:
        return True
    return any(first <= code <= last for first, last in EXTENDED_PICTOGRAPHIC)


def tracked_files(root, folders=FOLDERS):
    """Every file git tracks under `folders`, as paths relative to `root`."""
    listed = subprocess.run(['git', 'ls-files', '-z', '--', *folders],
                            cwd=root, capture_output=True, check=True)
    return [rel for rel in listed.stdout.decode('utf-8').split('\0') if rel]


def pictographs(root, rels):
    """`<path>:<line>: U+XXXX` for each pictograph in the files `rels`."""
    found = []
    for rel in rels:
        with open(os.path.join(root, rel), 'rb') as handle:
            text = handle.read().decode('utf-8', errors='replace')
        for number, line in enumerate(text.splitlines(), 1):
            found += ['%s:%d: U+%04X' % (rel, number, ord(character))
                      for character in line
                      if is_pictograph(character)
                      and ord(character) not in ALLOWED]
    return found


class TestNoPictograph:

    # purlin: purlin_output PROOF-1
    def test_no_tracked_file_under_scripts_or_templates_holds_a_pictograph(
            self, tmp_path):
        rels = tracked_files(ROOT)
        assert any(rel.startswith('scripts/') for rel in rels), rels
        assert any(rel.startswith('templates/') for rel in rels), rels
        assert pictographs(ROOT, rels) == []
        # The glyphs Purlin prints pass; a check mark, a warning sign, a
        # rocket and a heart with its variation selector are each found.
        assert not any(is_pictograph(c) and ord(c) not in ALLOWED
                       for c in '→▼▲─·←▶')
        (tmp_path / 'out.py').write_text(
            'print("\u2705 done")\nprint("\u26a0 careful")\n'
            'print("\U0001f680")\nprint("\u2764\ufe0f")\n', encoding='utf-8')
        assert pictographs(str(tmp_path), ['out.py']) == [
            'out.py:1: U+2705', 'out.py:2: U+26A0', 'out.py:3: U+1F680',
            'out.py:4: U+2764', 'out.py:4: U+FE0F']


# --- Python 3.9 ------------------------------------------------------------

SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
RUN_SCRIPT = os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py')
SERVER = os.path.join(ROOT, 'scripts', 'mcp', 'purlin', 'server.py')


def python_files_that_do_not_parse_as_39(root, rels):
    """`<path>: <error>` for each Python file of `rels` that Python 3.9's
    grammar does not accept."""
    found = []
    for rel in rels:
        if not rel.endswith('.py'):
            continue
        with open(os.path.join(root, rel), encoding='utf-8') as handle:
            source = handle.read()
        try:
            ast.parse(source, filename=rel, feature_version=(3, 9))
        except SyntaxError as error:
            found.append('%s: %s' % (rel, error.msg))
    return found


def python_39():
    """The command that starts a Python 3.9 on this machine, or None."""
    candidates = [['python3.9'], ['/usr/bin/python3'], ['python3']]
    if os.name == 'nt':
        candidates.insert(0, ['py', '-3.9'])
    for command in candidates:
        if not os.path.isabs(command[0]) and not shutil.which(command[0]):
            continue
        if os.path.isabs(command[0]) and not os.path.isfile(command[0]):
            continue
        try:
            asked = subprocess.run(
                command + ['-c', 'import sys; print(sys.version_info[:2])'],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if asked.returncode == 0 and asked.stdout.strip() == '(3, 9)':
            return command
    return None


def needs_python_39():
    command = python_39()
    if command is None:
        pytest.skip('no Python 3.9 on this machine')
    return command


def clean_environment():
    """This process's environment, less what would point a Purlin program
    at another project or plugin, with git told to sign nothing."""
    env = dict(os.environ)
    for name in ('CLAUDE_PLUGIN_ROOT', 'PURLIN_PROJECT_ROOT'):
        env.pop(name, None)
    env.update({'GIT_CONFIG_COUNT': '1',
                'GIT_CONFIG_KEY_0': 'commit.gpgsign',
                'GIT_CONFIG_VALUE_0': 'false'})
    return env


def git(root, *args):
    return subprocess.run(['git', *args], cwd=str(root), capture_output=True,
                          text=True, check=True, env=clean_environment())


def new_repository(tmp_path):
    """A git repository holding one module and its one marked test."""
    root = tmp_path / 'scratch-project'
    (root / 'src').mkdir(parents=True)
    (root / 'tests').mkdir()
    git(root, '-c', 'init.defaultBranch=main', 'init', '-q', '.')
    git(root, 'config', 'user.name', 'Purlin Test')
    git(root, 'config', 'user.email', 'test@example.com')
    (root / 'src' / 'app.py').write_text(
        'def add(a, b):\n    return a + b\n', encoding='utf-8')
    (root / 'tests' / 'test_app.py').write_text(
        'import os\nimport sys\n\n'
        'sys.path.insert(0, os.path.join(os.path.dirname(__file__), '
        "'..', 'src'))\n"
        'from app import add  # noqa: E402\n\n\n'
        '# purlin: app PROOF-1\n'
        'def test_one_and_two_make_three():\n'
        '    assert add(1, 2) == 3\n', encoding='utf-8')
    return root


class Done:
    """What a finished command left: its process id, exit code and output."""

    def __init__(self, pid, returncode, stdout, stderr):
        self.pid, self.returncode = pid, returncode
        self.stdout, self.stderr = stdout, stderr


def run(command, root, stdin=None, new_session=False):
    """`command` from `root`, its input `stdin` or nothing. With
    `new_session` it starts a process group of its own, numbered as its own
    process id."""
    # The output goes to files, not pipes: a process left running would hold
    # a pipe open, and reading it to its end would wait for that process.
    with tempfile.TemporaryFile('w+', encoding='utf-8') as stdout, \
            tempfile.TemporaryFile('w+', encoding='utf-8') as stderr:
        process = subprocess.Popen(
            command, cwd=str(root), stdin=subprocess.PIPE, stdout=stdout,
            stderr=stderr, encoding='utf-8', env=clean_environment(),
            start_new_session=new_session)
        process.communicate(stdin if stdin is not None else '', timeout=600)
        stdout.seek(0)
        stderr.seek(0)
        return Done(process.pid, process.returncode, stdout.read(),
                    stderr.read())


def set_up(python, root, new_session=False):
    return run(python + [SCAFFOLD, '--project-root', str(root), '--gate',
                         'passed', '--yes'], root, new_session=new_session)


def give_it_a_spec(root):
    """The spec of the one feature and the project's own test command, the
    pytest this session runs, all committed."""
    (root / 'specs' / 'app').mkdir(parents=True, exist_ok=True)
    (root / 'specs' / 'app' / 'app.md').write_text(
        '# Feature: app\n\n> Scope: src/app.py\n\n## Rules\n\n'
        '- RULE-1: Adding one and two gives three\n\n## Proof\n\n'
        '- PROOF-1 (RULE-1): One plus two reads 3\n', encoding='utf-8')
    config_path = root / '.purlin' / 'config.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['tests'] = [suites.pytest_suite()]
    config_path.write_text(json.dumps(config, indent=2) + '\n',
                           encoding='utf-8')
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', 'the feature and its spec')


def a_test_run(python, root, *flags, new_session=False):
    return run(python + [RUN_SCRIPT, '--project-root', str(root), '--test',
                         '--all', *flags], root, new_session=new_session)


def status(python, root, new_session=False):
    """The status, asked of Purlin's server as the agent asks it, then the
    server's input closed."""
    requests = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
         'params': {'name': 'sync_status',
                    'arguments': {'project_root': str(root)}}}]
    return run(python + [SERVER], root,
               stdin=''.join(json.dumps(r) + '\n' for r in requests),
               new_session=new_session)


def status_text(done):
    """The text of the server's answer to the status call."""
    answers = [json.loads(line) for line in done.stdout.splitlines() if line]
    answer = next(a for a in answers if a.get('id') == 2)
    return answer['result']['content'][0]['text']


# Python 3.9 was released without these; `match` alone is enough to show
# the check reads the grammar and not just the words.
LATER_THAN_39 = ('match command:\n    case "go":\n        pass\n')


class TestPython39:

    # purlin: purlin_output PROOF-2
    def test_every_python_file_under_scripts_parses_as_39(self, tmp_path):
        rels = tracked_files(ROOT, ('scripts',))
        assert sum(rel.endswith('.py') for rel in rels) > 20, rels
        assert python_files_that_do_not_parse_as_39(ROOT, rels) == []
        # A file holding a `match` statement is named.
        (tmp_path / 'later.py').write_text(
            'command = "go"\n' + LATER_THAN_39, encoding='utf-8')
        found = python_files_that_do_not_parse_as_39(str(tmp_path),
                                                     ['later.py'])
        assert len(found) == 1 and found[0].startswith('later.py: '), found

    # purlin: purlin_output PROOF-3
    def test_setup_runs_on_39(self, tmp_path):
        python = needs_python_39()
        root = new_repository(tmp_path)
        done = set_up(python, root)
        assert done.returncode == 0, done.stdout + done.stderr
        assert (root / '.purlin' / 'config.json').is_file()

    # purlin: purlin_output PROOF-4
    def test_a_test_run_runs_on_39(self, tmp_path):
        python = needs_python_39()
        root = new_repository(tmp_path)
        assert set_up(python, root).returncode == 0
        give_it_a_spec(root)
        done = a_test_run(python, root)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'Markers: 1 tied to a test, 0 not tied.' in done.stdout, \
            done.stdout

    # purlin: purlin_output PROOF-5
    def test_the_status_runs_on_39(self, tmp_path):
        python = needs_python_39()
        root = new_repository(tmp_path)
        assert set_up(python, root).returncode == 0
        give_it_a_spec(root)
        done = status(python, root)
        assert done.returncode == 0, done.stdout + done.stderr
        text = status_text(done)
        assert re.search(r'^app +1 +1 ', text, re.M), text


# --- No process left behind -------------------------------------------------

def processes():
    """`(pid, process group, command line)` for every process running."""
    if os.name == 'nt':
        listed = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             'Get-CimInstance Win32_Process | ForEach-Object '
             '{ "$($_.ProcessId)`t$($_.CommandLine)" }'],
            capture_output=True, text=True, check=True)
        rows = []
        for line in listed.stdout.splitlines():
            pid, _, command = line.partition('\t')
            if pid.strip().isdigit():
                rows.append((int(pid), None, command))
        return rows
    listed = subprocess.run(['ps', '-A', '-ww', '-o', 'pid=,pgid=,command='],
                            capture_output=True, text=True, check=True)
    rows = []
    for line in listed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]),
                         parts[2] if len(parts) > 2 else ''))
    return rows


def left_running(root, groups):
    """The processes still running that name `root` on their command line
    or belong to one of the process groups `groups`, looked at three times
    over a second and a half so that one on its way out is not counted."""
    for _ in range(3):
        left = [row for row in processes()
                if row[0] != os.getpid()
                and (str(root) in row[2] or row[1] in groups)]
        if not left:
            return []
        time.sleep(0.5)
    return left


def stop(rows):
    for pid, _, _ in rows:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


class TestNoProcessLeft:

    # purlin: purlin_output PROOF-6
    def test_no_command_leaves_a_process_running(self, tmp_path):
        python = [sys.executable]
        root = new_repository(tmp_path)
        # Each command starts a process group of its own, so a process it
        # leaves behind is found by its group even when its command line
        # names nothing of the project.
        ran = [set_up(python, root, new_session=True)]
        give_it_a_spec(root)
        ran.append(a_test_run(python, root, '--commit', new_session=True))
        ran.append(status(python, root, new_session=True))
        for done in ran:
            assert done.returncode == 0, done.stdout + done.stderr
        leftover = left_running(root, {done.pid for done in ran})
        try:
            assert leftover == []
        finally:
            stop(leftover)
