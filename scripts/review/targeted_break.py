"""The planted bug: one change per proof, in a copy of the project.

The audit's third step. The model's one reply for a rule holds a part for each
proof a bug is asked for: the smallest change to one file the feature covers
that would break what the proof says, exactly

    file: src/age.py
    before:
    <the exact lines>
    after:
    <the lines>

or `no break: <why>`. The change is made in a copy of the project, built from
`git ls-files -co --exclude-standard -z` under a folder named `purlin-break-*`
in the system's temporary folder, never in the project. Only the proof's own
tests run there, through their suite's own `run` command, once before the
change and once with it in place; the copy is removed whatever they do.

    survived   every one of the proof's own tests still passes with the bug in place
    caught     a test of the proof's own ran and failed with the bug in place
    not run    anything else with the bug in place: a skip, a test not collected, a
               timeout. It is neither caught nor survived
    not made   the part is missing or names no change, the change cannot be applied
               exactly once to a file the feature's `> Scope:` reaches, it names a file
               that holds one of the proof's tests, it would write outside the copy, or
               the proof's tests do not pass in the copy before the change

`snapshot` takes the project's `git status --porcelain -z` and the hash of
every file it lists; the audit takes one before it asks the model and compares
it after each rule's bugs (`check_unchanged`). A difference raises
`ProjectChanged`, and the audit prints `STOPPED` and exits 1. This module
writes nothing in the project.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
for _path in (os.path.join(_SCRIPTS, 'mcp'), os.path.join(_SCRIPTS, 'run')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

STOPPED = ('The audit stopped: %s changed while the audit ran. Nothing in the '
           'project was written by the audit.')
SURVIVED = '%s: the test still passes when %s:%d reads "%s"'   # PROOF-N, file, line, the changed line

COPY_PREFIX = 'purlin-break-'
NO_CHANGE = 'the answer named no change'
OUTSIDE = '%s is outside the copy of the project'
NOT_IN_SCOPE = "%s is not a file the feature's scope names"
NO_FILE = '%s is not in the project'
NOT_FOUND = 'the lines before the change are not in %s'
FOUND_MORE = 'the lines before the change are in %s %d times, not once'
NO_DIFFERENCE = 'the change leaves %s as it was'
TEST_FILE = "%s holds one of the proof's tests"
NO_PART = 'it holds none'
BASELINE = 'the test does not pass in a copy of the project'

# Why no bug was planted, which the audit picks its sentence by.
MODEL_FOUND_NONE = 'model found none'
ANSWER_UNUSABLE = 'answer unusable'
TEST_DOES_NOT_PASS = 'test does not pass'
_OWN_WORDS = (NO_CHANGE, OUTSIDE, NOT_IN_SCOPE, NO_FILE, NOT_FOUND, FOUND_MORE,
              NO_DIFFERENCE, TEST_FILE, NO_PART)

_NO_BREAK_RE = re.compile(r'^\s*no break:\s*(.*?)\s*$', re.S)
_CHANGE_RE = re.compile(r'^file:[ \t]*(?P<file>[^\n]+?)[ \t]*\nbefore:[ \t]*\n(?P<before>.*?)\n'
                        r'after:[ \t]*\n?(?P<after>.*)$', re.S)


class ProjectChanged(Exception):
    """Carries the path; audit_run prints STOPPED."""

    def __init__(self, path):
        Exception.__init__(self, path)
        self.path = path


class _Refused(Exception):
    """A write to a path outside the copy."""


def parse_answer(text):
    """`('change', file, before, after)`, `('no break', why)`, or None for anything else."""
    text = (text or '').strip('\n')
    lines = text.split('\n')
    while lines and lines[0].strip().startswith('```'):
        lines.pop(0)
    while lines and lines[-1].strip().startswith('```'):
        lines.pop()
    text = '\n'.join(lines)
    found = _NO_BREAK_RE.match(text)
    if found and found.group(1):
        return ('no break', found.group(1))
    found = _CHANGE_RE.match(text.strip('\n'))
    if not found or not found.group('before').strip():
        return None
    return ('change', found.group('file').strip(), found.group('before'),
            found.group('after').rstrip('\n'))


def cause_of(why):
    """The cause a `not made` result's `why` names: `'test does not pass'` for
    `BASELINE`, `'answer unusable'` for this module's own words, and
    `'model found none'` for any other, which is the model's own reason."""
    why = str(why or '')
    if why == BASELINE:
        return TEST_DOES_NOT_PASS
    for words in _OWN_WORDS:
        pattern = re.escape(words).replace('%s', '.+').replace('%d', r'\d+')
        if re.fullmatch(pattern, why, re.S):
            return ANSWER_UNUSABLE
    return MODEL_FOUND_NONE


def break_proof(project_root, feature, proof, tests, scope_files, answer, timeout=None):
    """One planted bug for one proof. `tests` is the proof's own tied tests. `answer` is
    the proof's part of the model's reply, or None where the reply holds none.
    Returns {'proof','file','line','before','after','result','why','cause','finding'}:
    result 'caught' | 'survived' | 'not run' | 'not made'; `cause` is '' or, for
    'not made', 'model found none', 'answer unusable' or 'test does not pass';
    finding is SURVIVED filled, or None.

    `proof` is `{'id', 'text'}` or its id; each of `tests` is `{'file', 'name',
    'source'}`. `timeout` bounds each run of the tests, in seconds, as
    `--arm-timeout` does.
    """
    return _plant(project_root, feature, proof, tests or [], scope_files or [], answer,
                  timeout)


def check_unchanged(project_root, before):
    """Raise `ProjectChanged` where the project differs from the snapshot `before`."""
    changed = _difference(before, snapshot(project_root))
    if changed is not None:
        raise ProjectChanged(changed)


# ---------------------------------------------------------------------------
# The bug
# ---------------------------------------------------------------------------

def _result(proof_id, result, why='', change=None, line=None, finding=None):
    change = change or (None, None, None)
    return {'proof': proof_id, 'file': change[0], 'line': line, 'before': change[1],
            'after': change[2], 'result': result, 'why': why,
            'cause': cause_of(why) if result == 'not made' else '', 'finding': finding}


def _plant(project_root, feature, proof, tests, scope_files, answer, timeout):
    if isinstance(proof, str):
        proof = {'id': proof}
    proof_id = proof.get('id')
    if answer is None:
        return _result(proof_id, 'not made', NO_PART)
    parsed = parse_answer(answer)
    if parsed is None:
        return _result(proof_id, 'not made', NO_CHANGE)
    if parsed[0] == 'no break':
        return _result(proof_id, 'not made', parsed[1])
    _kind, path, old, new = parsed
    change = (path, old, new)
    rel = path.replace('\\', '/')
    normal = os.path.normpath(rel).replace(os.sep, '/')
    if os.path.isabs(rel) or normal == '..' or normal.startswith('../'):
        return _result(proof_id, 'not made', OUTSIDE % path, change)
    own = {os.path.normpath(t['file']).replace(os.sep, '/') for t in tests if t.get('file')}
    if normal in own:
        return _result(proof_id, 'not made', TEST_FILE % path, change)
    scope = {os.path.normpath(p).replace(os.sep, '/') for p in scope_files}
    if normal not in scope:
        return _result(proof_id, 'not made', NOT_IN_SCOPE % path, change)
    copy = tempfile.mkdtemp(prefix=COPY_PREFIX)
    try:
        _copy_project(project_root, copy)
        try:
            text = _read_in(copy, normal)
        except _Refused:
            return _result(proof_id, 'not made', OUTSIDE % path, change)
        if text is None:
            return _result(proof_id, 'not made', NO_FILE % path, change)
        count = text.count(old)
        if count == 0:
            return _result(proof_id, 'not made', NOT_FOUND % path, change)
        if count > 1:
            return _result(proof_id, 'not made', FOUND_MORE % (path, count), change)
        if old == new:
            return _result(proof_id, 'not made', NO_DIFFERENCE % path, change)
        if _run_tests(copy, feature, proof_id, tests, timeout) != 'pass':
            return _result(proof_id, 'not made', BASELINE, change)
        at = text.index(old)
        changed = text[:at] + new + text[at + len(old):]
        try:
            stamp = os.stat(_inside(copy, normal)).st_mtime
            _write_in(copy, normal, changed)
            # The tests already ran here once: the changed file must read as newer,
            # or a cache keyed by time and size, such as Python's, serves the old code.
            os.utime(_inside(copy, normal), (stamp + 2, stamp + 2))
        except (_Refused, OSError):
            return _result(proof_id, 'not made', OUTSIDE % path, change)
        line, words = _changed_line(changed, at, old, new)
        ran = _run_tests(copy, feature, proof_id, tests, timeout)
        if ran == 'pass':
            return _result(proof_id, 'survived', '', change, line,
                           SURVIVED % (proof_id, path, line, words))
        return _result(proof_id, 'caught' if ran == 'fail' else 'not run', '', change, line)
    finally:
        shutil.rmtree(copy, ignore_errors=True)


def _changed_line(changed, at, old, new):
    """`(line number, the line's words)` of the first line the change made different."""
    first = changed.count('\n', 0, at) + 1
    old_lines, new_lines = old.split('\n'), new.split('\n')
    step = 0
    while step < min(len(old_lines), len(new_lines)) and old_lines[step] == new_lines[step]:
        step += 1
    if step >= len(new_lines):
        step = max(len(new_lines) - 1, 0)
    lines = changed.split('\n')
    number = first + step
    words = lines[number - 1].strip() if number - 1 < len(lines) else ''
    return number, words


# ---------------------------------------------------------------------------
# The copy: every write goes through one function that stays inside it
# ---------------------------------------------------------------------------

def _inside(copy, rel):
    root = os.path.realpath(copy)
    full = os.path.realpath(os.path.join(root, *rel.split('/')))
    if not full.startswith(root + os.sep):
        raise _Refused(rel)
    return full


def _write_in(copy, rel, data):
    """Write `data` at `rel` under the copy; a path that leaves the copy is refused."""
    full = _inside(copy, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(full, mode, **({} if isinstance(data, bytes) else {'encoding': 'utf-8',
                                                                   'newline': ''})) as handle:
        handle.write(data)


def _read_in(copy, rel):
    full = _inside(copy, rel)
    try:
        with open(full, 'r', encoding='utf-8', newline='') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _listed(project_root):
    done = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard', '-z'],
                          capture_output=True, cwd=project_root, timeout=120)
    if done.returncode != 0:
        return []
    return [p for p in os.fsdecode(done.stdout).split('\0') if p]


def _copy_project(project_root, copy):
    for rel in _listed(project_root):
        source = os.path.join(project_root, *rel.split('/'))
        if os.path.islink(source) or not os.path.isfile(source):
            continue
        with open(source, 'rb') as handle:
            data = handle.read()
        _write_in(copy, rel, data)
        os.chmod(_inside(copy, rel), os.stat(source).st_mode & 0o777)


# ---------------------------------------------------------------------------
# The proof's own tests, run in the copy
# ---------------------------------------------------------------------------

def _run_tests(copy, feature, proof_id, tests, timeout):
    """`fail` where a test of the proof's own ran and failed; `pass` where every one
    reads `pass` and no suite reported a failure; else `not run`."""
    import purlin_run
    from purlin import markers as markers_module
    suites, _problems = markers_module.read_suites(copy)
    scan = markers_module.scan(copy, suites)
    wanted_files = sorted({t['file'] for t in tests}) if tests else sorted(
        path for path, found in scan.items()
        if any(m.key() == (feature, proof_id) for m in found.markers))
    by_suite = {}
    for path in wanted_files:
        suite = markers_module.suite_of(path, suites)
        if suite is None:
            return 'not run'
        by_suite.setdefault(suite.name, (suite, []))[1].append(path)
    if not by_suite:
        return 'not run'
    log = []
    runs = []
    for name in sorted(by_suite):
        suite, files = by_suite[name]
        runs.append(purlin_run.run_suite(
            copy, suite, files, log,
            timeout=timeout or purlin_run.ARM_TIMEOUT_DEFAULT, marked=scan, action='audit'))
    entries = purlin_run.marker_results(scan, suites, runs).get((feature, proof_id), [])
    if tests:
        named = {(t['file'], t.get('name')) for t in tests}
        own = [e for e in entries if (e['test_file'], e['test_name']) in named]
        files = {t['file'] for t in tests}
        entries = own or [e for e in entries if e['test_file'] in files]
    if any(e['status'] == 'fail' for e in entries):
        return 'fail'
    if entries and all(e['status'] == 'pass' for e in entries) and not any(
            run.failures for run in runs):
        return 'pass'
    return 'not run'


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------

def snapshot(project_root):
    """`(git status --porcelain -z, {path: hash of its bytes})` for every path it lists."""
    done = subprocess.run(['git', 'status', '--porcelain', '-z'], capture_output=True,
                          cwd=project_root, timeout=120)
    status = done.stdout
    paths = []
    parts = os.fsdecode(status).split('\0')
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in 'RC':
            paths.append(parts[index])
            index += 1
    return status, {path: _hash(os.path.join(project_root, *path.rstrip('/').split('/')))
                    for path in paths}


def _hash(full):
    digest = hashlib.sha256()
    if os.path.isdir(full):
        for dirpath, dirnames, filenames in os.walk(full):
            dirnames.sort()
            for name in sorted(filenames):
                digest.update(os.fsencode(name))
                digest.update(_hash(os.path.join(dirpath, name)).encode())
        return digest.hexdigest()
    try:
        with open(full, 'rb') as handle:
            digest.update(handle.read())
    except (IOError, OSError):
        return 'absent'
    return digest.hexdigest()


def _difference(before, after):
    """The first path whose status or bytes differ between two snapshots, or None."""
    if before == after:
        return None
    old, new = before[1], after[1]
    for path in sorted(set(old) | set(new)):
        if old.get(path) != new.get(path):
            return path.rstrip('/')
    return sorted(set(old) | set(new))[0].rstrip('/') if (old or new) else '.'
