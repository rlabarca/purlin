"""Read a test suite's report and tie each result to the markers above its test.

Purlin runs a project's own test command, the one the `tests` setting holds,
and reads the report that command writes. Four formats are read:

    junit    JUnit XML: every `<testcase>`, with its `classname`, `name` and,
             where the writer adds one, `file`; a `<failure>` or `<error>`
             child fails it and a `<skipped>` child skips it, its reason the
             child's `message`, else its text
    trx      what `dotnet test --logger trx` writes: each `UnitTestResult`'s
             `outcome`, joined through its `testId` to the `TestMethod` whose
             `className` and `name` it ran; a skip's reason is the result's
             `Output/ErrorInfo/Message`, else the last line of `Output/StdOut`
    gotest   the JSON stream `go test -json` writes: each event whose
             `Action` is `pass`, `fail` or `skip` and that names a `Test`; a
             skip's reason is the test's last `output` event before it, its
             leading `<file>:<line>: ` cut
    exit     no report: each test file is run on its own and passes when the
             command exits 0; a skip gives no reason

For each case in a report the file it belongs to is found (from the case's
file attribute where there is one, otherwise by resolving its class or package
name against the marked files of that suite), then the test's own name is
found in that file. A parametrised test's cases (`test_x[a]`, `TestX/a`,
`Method(x: 1)`) all belong to the one test, and every case must pass. A JavaScript title is read as the string it
makes: an escaped quote as the quote, pieces joined with `+` as one. A nested
title (`outer > inner > title`) is matched by its last part, then narrowed by
the outer parts when two tests share it. A case that matches more than one
test is not counted for any of them, and the run says so: Purlin never
guesses.

Beside its outcome each case carries what the report holds for it: its
name, how long it took and, where it failed, stopped on an error or was
skipped, the text the report holds for that. `reported` gives them as the
evidence keeps them for one test, and `sources` the bytes each case was
read from, which the run keeps under the file's sha256.

`references/formats/marker_format.md` is the contract.
"""

import json
import os
import re
import hashlib
import shlex
import sys
import xml.etree.ElementTree as ElementTree

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import markers as markers_module, notices         # noqa: E402
from purlin.markers import (                                  # noqa: E402
    NAMES_NOTHING, RULE_HAS_PROOFS, marker_problems)

# What a case's outcome is read as.
PASS, FAIL, SKIP = 'pass', 'fail', 'skip'

# What a marker's result is.
NOT_RUN = 'not run'

# The words the run prints about a marker it could not use, and about a case
# it could not count. Each line says what to do.
TIED_TO_NO_TEST = 'No test follows %s:%d.'
UNREADABLE_TITLE = 'It is not one plain string.'
UNREADABLE_TITLE_DO = 'Write it as one string.'
AMBIGUOUS = 'It matches %d tests in %s.'
AMBIGUOUS_DO = 'Give the tests different names, then run purlin:test.'

# The outcomes TRX writes that mean the test ran and did not pass, and those
# that mean the test itself ran and passed; any other outcome is a skip.
_TRX_FAIL = ('failed', 'error', 'timeout', 'aborted')
# Those of them that are an error and not a failure: the test stopped.
_TRX_ERROR = ('error', 'timeout', 'aborted')
_TRX_PASS = ('passed', 'passedbutrunaborted', 'warning', 'completed')


class Case(object):
    """One test result from a report.

    `reason` is the text the test tool gave for a skipped case, or None.
    `error` is true for a failed case its tool reports as an error and not
    as a failure: the test stopped, in its setup say, before it could fail.
    `duration` is how long the case took, in seconds, as the report gives
    it, or None; `text` is the whole text the report holds for a case that
    failed or stopped on an error, or None; `source` is the report file the
    case was read from, as `read_report` names it.
    """

    __slots__ = ('file', 'classname', 'name', 'outcome', 'package', 'reason',
                 'error', 'duration', 'text', 'source')

    def __init__(self, name, outcome, classname='', file=None, package=None,
                 reason=None, error=False, duration=None, text=None):
        self.name = name
        self.outcome = outcome
        self.classname = classname or ''
        self.file = file
        self.package = package
        self.reason = reason
        self.error = bool(error)
        self.duration = duration
        self.text = text
        self.source = None

    def __repr__(self):
        return 'Case(%s %s %s %s)' % (self.file or self.classname,
                                      self.name, self.outcome,
                                      self.package or '')


class Outcome(str):
    """One case's outcome as `tie` gives it: `pass`, `fail` or `skip`,
    carrying the case's `reason` and whether it is an `error`, and `case`,
    the report's own case, where it was made from one."""

    def __new__(cls, outcome, reason=None, error=False, case=None):
        made = str.__new__(cls, outcome)
        made.reason = reason
        made.error = bool(error)
        made.case = case
        return made


def _text_of(text):
    """`text` stripped, or None where nothing is left."""
    text = (text or '').strip()
    return text or None


def _seconds(value):
    """A report's duration as seconds, a number, or None where it gives
    none that can be read. `0.012` and `1` are seconds as written;
    `00:00:01.5000000`, as TRX writes a duration, is 1.5."""
    text = str(value if value is not None else '').strip()
    if not text:
        return None
    try:
        if ':' in text:
            seconds = 0.0
            for part in text.split(':'):
                seconds = seconds * 60 + float(part)
        else:
            seconds = float(text)
    except ValueError:
        return None
    if seconds != seconds or seconds in (float('inf'), float('-inf')) \
            or seconds < 0:
        return None
    return round(seconds, 6)


def _whole(*parts):
    """The texts a report holds for one failure as one text: each part
    that says something, in order, one that a later part already holds left
    out, a blank line between two. None where no part says anything."""
    kept = []
    parts = [part.strip('\r\n') for part in parts
             if part and part.strip()]
    for index, part in enumerate(parts):
        if any(part.strip() in later for later in parts[index + 1:]):
            continue
        kept.append(part.rstrip())
    return '\n\n'.join(kept) or None


# ---------------------------------------------------------------------------
# Reading the four formats
# ---------------------------------------------------------------------------

def _local(tag):
    return tag.rsplit('}', 1)[-1]


def read_junit(text):
    """Every `<testcase>` in a JUnit XML document, in document order."""
    root = ElementTree.fromstring(text)
    cases = []

    def walk(node, suite_file):
        for child in list(node):
            tag = _local(child.tag)
            if tag == 'testsuite' or tag == 'testsuites':
                walk(child, child.get('file') or child.get('filepath')
                     or suite_file)
            elif tag == 'testcase':
                kinds = {_local(grand.tag): grand for grand in list(child)}
                reason = None
                text = None
                if set(kinds) & {'failure', 'error'}:
                    outcome = FAIL
                    text = _whole(*[part for grand in list(child)
                                    if _local(grand.tag) in ('failure',
                                                             'error')
                                    for part in (grand.get('message'),
                                                 grand.text)])
                elif 'skipped' in kinds:
                    outcome = SKIP
                    skipped = kinds['skipped']
                    reason = (_text_of(skipped.get('message'))
                              or _text_of(skipped.text))
                else:
                    outcome = PASS
                cases.append(Case(child.get('name') or '', outcome,
                                  child.get('classname') or '',
                                  child.get('file') or suite_file,
                                  reason=reason,
                                  error=('error' in kinds
                                         and 'failure' not in kinds),
                                  duration=_seconds(child.get('time')),
                                  text=text))
    if _local(root.tag) == 'testcase':
        wrapper = ElementTree.Element('testsuite')
        wrapper.append(root)
        root = wrapper
    walk(root, None)
    return cases


def read_trx(text):
    """Every `UnitTestResult` in a TRX document, joined to its test method."""
    root = ElementTree.fromstring(text)
    methods = {}
    for node in root.iter():
        if _local(node.tag) != 'UnitTest':
            continue
        for child in node.iter():
            if _local(child.tag) == 'TestMethod':
                methods[node.get('id')] = (child.get('className') or '',
                                           child.get('name') or '')
    cases = []
    for node in root.iter():
        if _local(node.tag) != 'UnitTestResult':
            continue
        outcome = str(node.get('outcome') or '').lower()
        reason = None
        text = None
        if outcome in _TRX_FAIL:
            result = FAIL
            said = _trx_output(node)
            text = _whole(said.get('message'), said.get('trace'))
        elif outcome in _TRX_PASS:
            result = PASS
        else:
            result = SKIP
            reason = _trx_reason(node)
        classname, name = methods.get(node.get('testId'), ('', ''))
        if not name:
            # A result with no definition names its test in full.
            full = re.sub(r'\(.*\)$', '', node.get('testName') or '')
            classname, _, name = full.rpartition('.')
        cases.append(Case(name, result, classname, reason=reason,
                          error=outcome in _TRX_ERROR,
                          duration=_seconds(node.get('duration')),
                          text=text))
    return cases


def _trx_output(result):
    """What a TRX result's `Output` holds: `stdout`, and its `ErrorInfo`'s
    `message` and `trace`, each present only where the result holds it."""
    found = {}
    for output in list(result):
        if _local(output.tag) != 'Output':
            continue
        for child in list(output):
            if _local(child.tag) == 'StdOut':
                found.setdefault('stdout', child.text)
            elif _local(child.tag) == 'ErrorInfo':
                for grand in list(child):
                    if _local(grand.tag) == 'Message':
                        found.setdefault('message', grand.text)
                    elif _local(grand.tag) == 'StackTrace':
                        found.setdefault('trace', grand.text)
    return found


def _trx_reason(result):
    """A skipped TRX result's reason: `Output/ErrorInfo/Message`, else the
    last line of `Output/StdOut`; None where it holds neither."""
    found = _trx_output(result)
    message = _text_of(found.get('message'))
    if message:
        return message
    lines = [line.strip() for line in (found.get('stdout') or '').splitlines()
             if line.strip()]
    return lines[-1] if lines else None


# The lines `go test` writes about a test itself, which are not its output.
_GO_OWN_LINE = re.compile(r'^\s*(?:---|===) ')
# The `<file>:<line>: ` a `t.Skip` or `t.Log` line opens on.
_GO_WHERE = re.compile(r'^\s*\S+?\.go:\d+: ')


def read_gotest(text):
    """Every test `go test -json` reported passing, failing or skipping."""
    cases = []
    said = {}
    printed = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or not event.get('Test'):
            continue
        action = event.get('Action')
        key = (str(event.get('Package') or ''), str(event['Test']))
        if action == 'output':
            output = str(event.get('Output') or '')
            if output.strip() and not _GO_OWN_LINE.match(output):
                said[key] = output
                printed.setdefault(key, []).append(output)
            continue
        if action not in (PASS, FAIL, SKIP):
            continue
        reason = None
        if action == SKIP and key in said:
            reason = _text_of(_GO_WHERE.sub('', said[key], count=1))
        cases.append(Case(str(event['Test']), action,
                          package=str(event.get('Package') or ''),
                          reason=reason,
                          duration=_seconds(event.get('Elapsed')),
                          text=(_whole(''.join(printed.get(key) or ()))
                                if action == FAIL else None)))
    return cases


READERS = {'junit': read_junit, 'trx': read_trx, 'gotest': read_gotest}

# The files a report directory is read for, per format.
_DIRECTORY_EXTENSIONS = {'junit': ('.xml',), 'trx': ('.trx',),
                         'gotest': ('.json', '.jsonl', '.txt')}


def read_report(fmt, project_root, report, stdout=''):
    """`(cases, problem)` for one suite's report.

    `report` is the path the suite's entry names, relative to the project
    root, or `-` for the command's standard output, which is `stdout`. A
    path that is a directory is read file by file, every file of the
    format's extension in it. `problem` is one sentence when there is no
    report or it cannot be read, else None.
    """
    reader = READERS[fmt]
    files, problem = _report_files(fmt, project_root, report)
    if problem:
        return [], problem
    cases = []
    for source, full in files:
        text = (stdout or '') if full is None else _read(full)
        if text is None:
            return [], '%s could not be read.' % report
        try:
            found = reader(text.lstrip('\ufeff'))
        except (ElementTree.ParseError, ValueError):
            return [], '%s is not %s.' % (report, fmt)
        for case in found:
            case.source = source
        cases.extend(found)
    return cases, None


def _report_files(fmt, project_root, report):
    """`([(source, full path)], problem)` for the files one report is read
    from. `source` is the file's path relative to the project root, `/`
    separated, and `-` with no full path for the command's standard
    output."""
    if report == '-':
        return [('-', None)], None
    full = os.path.join(project_root, *report.split('/'))
    if os.path.isdir(full):
        files = [('%s/%s' % (report.rstrip('/'), name),
                  os.path.join(full, name))
                 for name in sorted(os.listdir(full))
                 if name.lower().endswith(_DIRECTORY_EXTENSIONS[fmt])]
        if not files:
            return [], 'It wrote no report in %s.' % report
        return files, None
    if os.path.isfile(full):
        return [(report, full)], None
    return [], 'It wrote no report at %s.' % report


# The extension a kept copy of the command's standard output is given.
_STDOUT_EXTENSIONS = {'junit': '.xml', 'trx': '.trx', 'gotest': '.json'}


def sources(fmt, project_root, report, stdout=''):
    """`{source: (sha256, bytes, extension)}` for the files `read_report`
    read one report from, as the suite left them: the bytes of each file,
    and of the standard output, encoded as UTF-8, for a report of `-`.
    `extension` is the file's own, the format's for the standard output.
    A file that cannot be read is left out."""
    found = {}
    files, _problem = _report_files(fmt, project_root, report)
    for source, full in files:
        if full is None:
            data = (stdout or '').encode('utf-8')
            extension = _STDOUT_EXTENSIONS[fmt]
        else:
            try:
                with open(full, 'rb') as handle:
                    data = handle.read()
            except (IOError, OSError):
                continue
            extension = os.path.splitext(full)[1].lower()
        found[source] = (hashlib.sha256(data).hexdigest(), data, extension)
    return found


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def command_for(suite, files, report=None, option=''):
    """The suite's `run` with `{files}` and `{report}` filled in.

    `files` is the list of test files to run, or empty for the whole suite.
    Each path is quoted for the shell the command runs in. `option` is the
    tool's own option that leaves the slow tests out, already quoted: it
    goes after the files, or at the command's end where it names none.
    """
    joined = ' '.join(shlex.quote(path) for path in files or ())
    if option and '{files}' in suite.run:
        joined = (joined + ' ' + option).strip()
    text = suite.run.replace('{files}', joined)
    if option and '{files}' not in suite.run:
        text = text.rstrip() + ' ' + option
    if report and report != '-':
        text = text.replace('{report}', shlex.quote(report))
    return ' '.join(text.split()) if '\n' not in text else text


def clear_report(project_root, report):
    """Delete a report before its suite runs, so an old one is never read."""
    if not report or report == '-':
        return
    full = os.path.join(project_root, *report.split('/'))
    if os.path.isdir(full):
        import shutil
        shutil.rmtree(full, ignore_errors=True)
    elif os.path.lexists(full):
        try:
            os.remove(full)
        except OSError:
            pass
    parent = os.path.dirname(full)
    if parent:
        os.makedirs(parent, exist_ok=True)


# ---------------------------------------------------------------------------
# Tying a case to a test
# ---------------------------------------------------------------------------

def _normalise_file(project_root, path):
    path = str(path or '').replace('\\', '/')
    root = os.path.abspath(project_root).replace('\\', '/')
    if os.path.isabs(path) or re.match(r'^[A-Za-z]:/', path):
        absolute = os.path.abspath(path).replace('\\', '/')
        if absolute.lower().startswith(root.lower() + '/'):
            path = absolute[len(root) + 1:]
    while path.startswith('./'):
        path = path[2:]
    return path


_PATHLIKE = re.compile(r'[/\\]|\.(?:py|[cm]?[jt]sx?|cs|go)$')


def _python_owner(classname, marked):
    """`(path, class chain)` for a dotted pytest classname, or `(None, [])`."""
    parts = [part for part in classname.split('.') if part]
    modules = {}
    for path in marked:
        if path.endswith('.py'):
            modules.setdefault(path[:-3].replace('/', '.'), []).append(path)
    for cut in range(len(parts), 0, -1):
        module = '.'.join(parts[:cut])
        found = [path for dotted, paths in modules.items() for path in paths
                 if dotted == module or dotted.endswith('.' + module)]
        if len(found) == 1:
            return found[0], parts[cut:]
        if len(found) > 1:
            exact = modules.get(module) or []
            if len(exact) == 1:
                return exact[0], parts[cut:]
            return None, []
    return None, []


def _go_package(project_root, path, cache):
    """The import path of the package a Go file sits in, read from `go.mod`."""
    directory = os.path.dirname(path)
    probe = directory
    while True:
        mod = cache.get(probe)
        if mod is None:
            text = _read(os.path.join(project_root, *(probe.split('/') if probe
                                                      else []), 'go.mod'))
            found = re.search(r'^module\s+(\S+)', text or '', re.M)
            mod = found.group(1) if found else ''
            cache[probe] = mod
        if mod:
            below = directory[len(probe):].strip('/') if probe else directory
            return mod + ('/' + below if below else '')
        if not probe:
            return directory
        probe = os.path.dirname(probe)


def _strip_parameters(name):
    """`test_x` for `test_x[a-1]`, `Method` for `Method(x: 1)`."""
    return re.sub(r'(?:\[.*\]|\(.*\))$', '', name).strip()


def _split_title(name):
    parts = [part.strip() for part in name.split(' > ')]
    return parts[-1], parts[:-1]


def _pick(tests, title, outer, exact_scope):
    """The tests named `title`, narrowed by the outer scopes when two share it."""
    named = [test for test in tests if test.plain and (
        test.name == title
        or (test.pattern is not None and test.pattern.match(title)))]
    if len(named) <= 1:
        return named
    if outer:
        ending = [test for test in named
                  if test.scopes[-len(outer):] == list(outer)]
        if ending:
            named = ending
    if len(named) > 1 or exact_scope:
        exact = [test for test in named if test.scopes == list(outer)]
        if exact:
            named = exact
    return named


def locate(project_root, suite, case, marked, go_cache=None):
    """`[(path, test)]` for the marked tests a case can be, or `[]`.

    More than one answer means the case is ambiguous. A case whose file
    carries no marker answers `[]`: a test with no marker is ignored.
    """
    candidates = []
    if suite.format == 'gotest':
        cache = {} if go_cache is None else go_cache
        title = case.name.split('/')[0]
        for path, found in marked.items():
            if not path.endswith('.go'):
                continue
            package = _go_package(project_root, path, cache)
            if case.package and package != case.package \
                    and not case.package.endswith('/' + os.path.dirname(path)):
                continue
            candidates.extend((path, test) for test in
                              _pick(found.tests, title, [], False))
        return candidates
    if suite.format == 'trx':
        title = _strip_parameters(case.name)
        chain = case.classname.replace('+', '.').split('.')
        namespace = ''
        for path, found in marked.items():
            for test in _pick(found.tests, title, [], False):
                scopes = test.scopes
                if scopes and scopes == chain[-len(scopes):]:
                    candidates.append((path, test))
                    namespace = namespace or '.'.join(chain[:-len(scopes)])
        if len(candidates) > 1:
            narrowed = [(path, test) for path, test in candidates
                        if test.namespace == '.'.join(
                            chain[:len(chain) - len(test.scopes)])]
            if narrowed:
                candidates = narrowed
        return candidates
    path, title, scopes, exact = _junit_place(project_root, case, marked)
    found = marked.get(path)
    if found is None:
        return []
    return [(path, test) for test in _pick(found.tests, title, scopes, exact)]


def _junit_place(project_root, case, marked):
    """`(path, title, scopes, exact)` for a `junit` case: the file it
    belongs to, None where none is found, its test's own name and the
    names around it."""
    title, outer = _split_title(case.name)
    path = None
    scopes = list(outer)
    exact = False
    if case.file:
        path = _normalise_file(project_root, case.file)
        if case.classname and not _PATHLIKE.search(case.classname) \
                and _normalise_file(project_root, case.classname) != path:
            if path.endswith('.py'):
                _owner, chain = _python_owner(case.classname, [path])
                scopes = chain + scopes
            else:
                scopes = [part.strip() for part in
                          case.classname.split(' > ') if part.strip()] + scopes
        exact = True
    elif _PATHLIKE.search(case.classname):
        path = _normalise_file(project_root, case.classname)
        exact = True
    else:
        path, chain = _python_owner(case.classname, marked)
        scopes = chain + scopes
        exact = True
    if path and path.endswith('.py'):
        title = _strip_parameters(title)
    return path, title, scopes, exact


# What two spellings of one title may differ by: white space, quotes, the
# backslash that escapes one and the `+` that joins two pieces.
_LOOSE = re.compile(r'[\s\'"`\\+]')


def ran_as(project_root, suite, cases, marked, outcomes):
    """`{(path, test line): name}` for each marked test no case was tied
    to, where the report holds a passing or failing case in the test's own
    file whose name differs from the test's title only by white space,
    quotes or joined pieces. `name` is the case's. Only a `junit` report
    names a test by a title; `outcomes` is `tie`'s answer.
    """
    found = {}
    if suite.format != 'junit':
        return found
    for case in cases:
        if case.outcome not in (PASS, FAIL):
            continue
        path, title, _scopes, _exact = _junit_place(project_root, case,
                                                    marked)
        holder = marked.get(path)
        if holder is None or locate(project_root, suite, case, marked):
            continue
        loose = _LOOSE.sub('', title)
        for test in holder.tests:
            if test.markers and (path, test.line) not in outcomes \
                    and _LOOSE.sub('', test.name) == loose:
                found.setdefault((path, test.line), title)
    return found


def tie(project_root, suite, cases, marked):
    """`(outcomes, problems)` for one suite's cases.

    `outcomes` is `{(path, test line): [outcome, ...]}` for every marked test
    a case was tied to, each an `Outcome` carrying its case's reason, and
    `problems` one line for each case that matched more than one test.
    """
    outcomes = {}
    problems = []
    cache = {}
    for case in cases:
        found = locate(project_root, suite, case, marked, cache)
        if len(found) == 1:
            path, test = found[0]
            outcomes.setdefault((path, test.line), []).append(
                Outcome(case.outcome, case.reason, case.error, case))
        elif len(found) > 1:
            line = notices.line('ambiguous', case.name, AMBIGUOUS % (
                len(found), ', '.join(sorted({path for path, _t in found}))),
                AMBIGUOUS_DO)
            if line not in problems:
                problems.append(line)
    return outcomes, problems


def result_of(outcomes):
    """`pass`, `fail` or `not run` for the cases one test had.

    Every case passed: `pass`. Any failed or errored: `fail`. All skipped,
    some skipped and none failed, or no case at all: `not run`.
    """
    if not outcomes:
        return NOT_RUN
    if FAIL in outcomes:
        return FAIL
    if all(outcome == PASS for outcome in outcomes):
        return PASS
    return NOT_RUN


def errored(outcomes):
    """True where a case of the test failed and every case that failed is an
    error: the test stopped before it could fail. A normal run reads such a
    test as `fail` all the same; the audit's planted bug reads it apart."""
    failed = [outcome for outcome in outcomes or () if outcome == FAIL]
    return bool(failed) and all(getattr(outcome, 'error', False)
                                for outcome in failed)


def reason_of(outcomes):
    """The reason the tool gave where every case one test had was skipped:
    the first skipped case's that gave one; None otherwise."""
    if not outcomes or any(outcome != SKIP for outcome in outcomes):
        return None
    for outcome in outcomes:
        reason = getattr(outcome, 'reason', None)
        if reason:
            return reason
    return None


# The longest text the evidence keeps for one case, in characters. A
# longer one keeps its first and its last `TEXT_LIMIT // 2` characters
# around `TEXT_CUT`, and its case says how many were left out.
TEXT_LIMIT = 20000
TEXT_CUT = '\n[... %d characters cut ...]\n'

# What a case reads in the evidence: an error apart from a failure.
ERROR = 'error'


def cut_text(text):
    """`(text, cut)`: `text` as the evidence keeps it, and how many
    characters were left out of its middle, 0 for a text within
    `TEXT_LIMIT`."""
    text = str(text)
    if len(text) <= TEXT_LIMIT:
        return text, 0
    half = TEXT_LIMIT // 2
    cut = len(text) - 2 * half
    return text[:half] + TEXT_CUT % cut + text[-half:], cut


def reported(outcomes, hashes=None):
    """What the report holds for one test, as the evidence keeps it, or
    None where no case of a report was tied to it.

    `{cases, report}`. `cases` is one entry per case, in the report's
    order: `name`, the case's name as the report gives it; `class`, the
    class, module or package the report names for it, where it names one;
    `outcome`, `pass`, `fail`, `error` or `skip`; `duration`, in seconds,
    where the report gives one; `text`, the whole text the report holds for
    a failure, an error or a skip, where it holds one, and `cut`, how many
    characters `cut_text` left out of it, where it left some out. `report`
    is `{file, sha256}`, the report file the first case was read from and
    the sha256 of its bytes, `hashes` being `{source: sha256}`; None where
    the file's bytes were not read.
    """
    cases = []
    source = None
    for outcome in outcomes or ():
        case = getattr(outcome, 'case', None)
        if case is None:
            continue
        if source is None:
            source = case.source
        entry = {'name': case.name}
        where = case.classname or case.package
        if where:
            entry['class'] = where
        entry['outcome'] = (ERROR if case.outcome == FAIL and case.error
                            else case.outcome)
        if case.duration is not None:
            entry['duration'] = case.duration
        text = case.text if case.outcome == FAIL else (
            case.reason if case.outcome == SKIP else None)
        if text:
            entry['text'], cut = cut_text(text)
            if cut:
                entry['cut'] = cut
        cases.append(entry)
    if not cases:
        return None
    sha = (hashes or {}).get(source)
    return {'cases': cases,
            'report': {'file': source, 'sha256': sha} if sha else None}


def test_name(path, test, fmt):
    """The name the evidence gives a test; a file of an `exit` suite is its own."""
    return markers_module.test_name(path, None if fmt == 'exit' else test)


# ---------------------------------------------------------------------------
# What the markers say
# ---------------------------------------------------------------------------

def untied_lines(scan):
    """One line per marker tied to no test, in file and line order.

    A marker no test follows is named with its feature and id. A test whose
    title is not one plain string is named once, by its own line, however
    many markers sit above it.
    """
    lines = []
    for path in sorted(scan):
        found = scan[path]
        titles = {id(marker): test for marker, test in found.unreadable}
        for marker in found.untied:
            test = titles.get(id(marker))
            if test is None:
                line = notices.line(
                    'untied', '%s %s' % (marker.feature, marker.id),
                    TIED_TO_NO_TEST % (path, marker.line),
                    notices.run('purlin:build'), feature=marker.feature)
            else:
                line = notices.line('title_unread',
                                    '%s:%d' % (path, test.line),
                                    UNREADABLE_TITLE, UNREADABLE_TITLE_DO)
            if line not in lines:
                lines.append(line)
    return lines
