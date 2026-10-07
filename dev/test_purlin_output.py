"""The checks of what Purlin prints and how its programs run.

`specs/instructions/purlin_output.md` holds four rules. No file under
`scripts/` or `templates/`, no skill definition and not the agent definition
carries a character with the Unicode property `Extended_Pictographic`, or
U+FE0F, other than `▶`: Python's own `re` cannot name that property, so the
ranges are written out below as a table, taken from Unicode's
`emoji-data.txt`, with adjacent ranges joined. Setup, a test run and the
status run on Python 3.9: every file under `scripts/` parses as 3.9, and a
test run and the status are run under a Python 3.9 in a scratch project,
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
import threading
import time
import tokenize
import uuid

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
                            cwd=root, capture_output=True)
    if listed.returncode == 0:
        return [rel for rel in listed.stdout.decode('utf-8').split('\0')
                if rel]
    # A copy of the project with no git in it: every file under the folders.
    found = []
    for folder in folders:
        for where, names, files in os.walk(os.path.join(root, folder)):
            names[:] = [name for name in names if name != '__pycache__']
            found += [os.path.relpath(os.path.join(where, name),
                                      root).replace(os.sep, '/')
                      for name in files]
    return sorted(found)


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


def skill_and_agent_files(root):
    """Each `skills/*/SKILL.md` and `agents/purlin.md`, relative to `root`."""
    skills = os.path.join(root, 'skills')
    rels = sorted('skills/%s/SKILL.md' % name for name in os.listdir(skills)
                  if os.path.isfile(os.path.join(skills, name, 'SKILL.md')))
    return rels + ['agents/purlin.md']


class TestNoPictograph:

    # purlin: purlin_output PROOF-1
    def test_no_tracked_file_under_scripts_or_templates_holds_a_pictograph(
            self, tmp_path):
        rels = tracked_files(ROOT)
        assert any(rel.startswith('scripts/') for rel in rels), rels
        assert any(rel.startswith('templates/') for rel in rels), rels
        assert pictographs(ROOT, rels) == [], 'a file Purlin ships holds one'
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


    # purlin: purlin_output PROOF-7
    def test_no_skill_and_not_the_agent_definition_holds_a_pictograph(
            self, tmp_path):
        rels = skill_and_agent_files(ROOT)
        assert 'skills/status/SKILL.md' in rels, rels
        assert rels[-1] == 'agents/purlin.md', rels
        assert pictographs(ROOT, rels) == []
        # A skill holding a check mark and a heart with its variation
        # selector is named, and the one glyph Purlin prints is not.
        (tmp_path / 'skills' / 'demo').mkdir(parents=True)
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills' / 'demo' / 'SKILL.md').write_text(
            '\u25b6 run it\n\u2705 done\n\u2764\ufe0f\n', encoding='utf-8')
        (tmp_path / 'agents' / 'purlin.md').write_text(
            'plain\n', encoding='utf-8')
        copy = skill_and_agent_files(str(tmp_path))
        assert pictographs(str(tmp_path), copy) == [
            'skills/demo/SKILL.md:2: U+2705', 'skills/demo/SKILL.md:3: U+2764',
            'skills/demo/SKILL.md:3: U+FE0F']


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


def f_strings_later_than_39(root, rels):
    """`<path>:<line>` for each f-string of the Python files `rels` that
    holds, inside a replacement field, a string in the f-string's own quote:
    Python 3.12 reads it and 3.9 rejects it, and `ast.parse` cannot tell.
    Read with this Python's own tokenizer; `[]` where it is older than 3.12
    and gives an f-string as one token."""
    opening = getattr(tokenize, 'FSTRING_START', None)
    if opening is None:
        return []
    found = []
    for rel in rels:
        if not rel.endswith('.py'):
            continue
        outer = []
        with open(os.path.join(root, rel), 'rb') as handle:
            for token in tokenize.tokenize(handle.readline):
                if token.type not in (opening, tokenize.STRING,
                                      tokenize.FSTRING_END):
                    continue
                if token.type == tokenize.FSTRING_END:
                    outer.pop()
                    continue
                quote = token.string.lstrip('rRbBfFuU')
                quote = quote[:3] if quote[:3] in ('"""', "'''") else quote[:1]
                if any(quote == held or (len(held) == 1 and quote[0] == held)
                       for held in outer):
                    found.append('%s:%d' % (rel, token.start[0]))
                if token.type == opening:
                    outer.append(quote)
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
    return run(python + [SCAFFOLD, '--project-root', str(root), '--yes'],
               root, new_session=new_session)


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
        assert python_files_that_do_not_parse_as_39(ROOT, rels) == [], (
            'a script does not parse as Python 3.9')
        # A file holding a `match` statement is named.
        (tmp_path / 'later.py').write_text(
            'command = "go"\n' + LATER_THAN_39, encoding='utf-8')
        found = python_files_that_do_not_parse_as_39(str(tmp_path),
                                                     ['later.py'])
        assert len(found) == 1 and found[0].startswith('later.py: '), found
        # An f-string that reuses its own quote inside a field, which 3.12
        # reads and 3.9 does not, is found too, and no script holds one.
        assert f_strings_later_than_39(ROOT, rels) == []
        (tmp_path / 'quoted.py').write_text(
            'row = {"error": "x"}\nline = f"{row["error"]}"\n',
            encoding='utf-8')
        if hasattr(tokenize, 'FSTRING_START'):
            assert f_strings_later_than_39(str(tmp_path), ['quoted.py']) == [
                'quoted.py:2']
        # Where the machine has a Python 3.9, its own compiler reads each
        # file: it refuses what a later Python's parser lets through under
        # a 3.9 setting, such as an assignment expression written without
        # parentheses as an index.
        python = python_39()
        if python is not None:
            (tmp_path / 'index.py').write_text(
                'row = [1]\nfirst = row[at := 0]\n', encoding='utf-8')
            reader = (
                'import sys\n'
                'for path in sys.argv[1:]:\n'
                '    with open(path, encoding="utf-8") as handle:\n'
                '        source = handle.read()\n'
                '    try:\n'
                '        compile(source, path, "exec")\n'
                '    except SyntaxError:\n'
                '        print(path)\n')
            scripts = [rel for rel in rels if rel.endswith('.py')]
            refused = subprocess.run(
                python + ['-c', reader, *scripts,
                          str(tmp_path / 'index.py')],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
            assert refused.returncode == 0, refused.stderr
            assert refused.stdout.splitlines() == [
                str(tmp_path / 'index.py')], refused.stdout

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
        # The whole row: one rule, one proof, and no rule passing yet.
        assert 'app   1      1       0 of 1' in text.splitlines(), text


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


def processes_carrying(mark):
    """`(pid, None, command line)` for every process whose environment
    holds the text `mark`, the one that lists them left out. Not Windows."""
    if os.path.isdir('/proc/self'):
        rows = []
        for name in os.listdir('/proc'):
            if not name.isdigit():
                continue
            try:
                with open('/proc/%s/environ' % name, 'rb') as handle:
                    held = handle.read()
                with open('/proc/%s/cmdline' % name, 'rb') as handle:
                    command = handle.read().replace(b'\0', b' ')
            except (IOError, OSError):
                continue
            if mark.encode('utf-8') in held:
                rows.append((int(name), None,
                             command.decode('utf-8', 'replace')))
        return rows
    # macOS and the BSDs: `-E` sets each process's environment after its
    # command line, for the processes this user may read.
    listing = subprocess.Popen(
        ['ps', '-A', '-E', '-ww', '-o', 'pid=,command='],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        errors='replace')
    listed, _ = listing.communicate(timeout=60)
    assert listing.returncode == 0, listed
    rows = []
    for line in listed.splitlines():
        pid, _, command = line.strip().partition(' ')
        if pid.isdigit() and int(pid) != listing.pid and mark in command:
            rows.append((int(pid), None, command.split(' ' + mark)[0]))
    return rows


def started_times():
    """`(pid, the time it started)` for every process running. Not Windows."""
    return {(pid, started) for pid, _, started in _parents()}


def _parents():
    """`(pid, parent pid, the time it started)` for every process."""
    listed = subprocess.run(['ps', '-A', '-o', 'pid=,ppid=,lstart='],
                            capture_output=True, text=True)
    rows = []
    for line in listed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2].strip()))
    return rows


def descendants(of):
    """`(pid, the time it started)` for every process running now that
    descends from the process `of`. Not Windows."""
    rows = _parents()
    children = {}
    for pid, parent, _ in rows:
        children.setdefault(parent, []).append(pid)
    below, waiting = set(), [of]
    while waiting:
        for child in children.get(waiting.pop(), ()):
            if child not in below:
                below.add(child)
                waiting.append(child)
    return {(pid, started) for pid, _, started in rows if pid in below}


def stop(rows):
    for pid, _, _ in rows:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


class TestNoProcessLeft:

    # purlin: purlin_output PROOF-6
    def test_no_command_leaves_a_process_running(self, tmp_path, monkeypatch):
        python = [sys.executable]
        root = new_repository(tmp_path)
        # Every process a command starts inherits this variable, so one that
        # left its command's process group, and names nothing of the project
        # on its command line, is still found: by its environment.
        mark = 'PURLIN_TEST_STARTED_BY=%s' % uuid.uuid4().hex
        monkeypatch.setenv(*mark.split('='))
        # Each command starts a process group of its own, so a process it
        # leaves behind is found by its group even when its command line
        # names nothing of the project.
        # While the three run, every process that descends from this one is
        # written down with the time it started: a process a command starts
        # is its child for as long as the command runs, whatever session,
        # environment and command line it is given. Windows has no `ps`.
        seen, watching = set(), threading.Event()

        def watch():
            while not watching.is_set():
                seen.update(descendants(os.getpid()))
                time.sleep(0.01)

        watcher = threading.Thread(target=watch, daemon=True)
        if os.name != 'nt':
            watcher.start()
        try:
            ran = [set_up(python, root, new_session=True)]
            give_it_a_spec(root)
            ran.append(a_test_run(python, root, '--commit', new_session=True))
            ran.append(status(python, root, new_session=True))
        finally:
            watching.set()
            if watcher.is_alive():
                watcher.join(timeout=60)
        for done in ran:
            assert done.returncode == 0, done.stdout + done.stderr
        if os.name != 'nt':
            # Each of the three was seen, so the watcher did look.
            assert {done.pid for done in ran} <= {pid for pid, _ in seen}
            still = []
            for _ in range(3):
                still = sorted(seen & started_times())
                if not still:
                    break
                time.sleep(0.5)
            try:
                assert still == [], 'a process a command started still runs'
            finally:
                stop([(pid, None, '') for pid, _ in still])
        leftover = left_running(root, {done.pid for done in ran})
        try:
            assert leftover == []
        finally:
            stop(leftover)
        # No process any of the three started is still running, whatever
        # group it is in and whatever its command line reads. Windows shows
        # no other process's environment, so there the groups above stand.
        if os.name != 'nt':
            started = []
            for _ in range(3):
                started = [row for row in processes_carrying(mark)
                           if row[0] != os.getpid()]
                if not started:
                    break
                time.sleep(0.5)
            try:
                assert started == []
            finally:
                stop(started)
