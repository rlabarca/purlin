"""Read a test suite's report and tie each result to the markers above its test.

Purlin runs a project's own test command, the one the `tests` setting holds,
and reads the report that command writes. Four formats are read:

    junit    JUnit XML: every `<testcase>`, with its `classname`, `name` and,
             where the writer adds one, `file`; a `<failure>` or `<error>`
             child fails it and a `<skipped>` child skips it
    trx      what `dotnet test --logger trx` writes: each `UnitTestResult`'s
             `outcome`, joined through its `testId` to the `TestMethod` whose
             `className` and `name` it ran
    gotest   the JSON stream `go test -json` writes: each event whose
             `Action` is `pass`, `fail` or `skip` and that names a `Test`
    exit     no report: each test file is run on its own and passes when the
             command exits 0

For each case in a report the file it belongs to is found (from the case's
file attribute where there is one, otherwise by resolving its class or package
name against the marked files of that suite), then the test's own name is
found in that file. A parametrised test's cases (`test_x[a]`, `TestX/a`,
`Method(x: 1)`) all belong to the one test, and every case must pass. A nested
title (`outer > inner > title`) is matched by its last part, then narrowed by
the outer parts when two tests share it. A case that matches more than one
test is not counted for any of them, and the run says so: Purlin never
guesses.

`references/formats/marker_format.md` is the contract.
"""

import json
import os
import re
import shlex
import sys
import xml.etree.ElementTree as ElementTree

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import markers as markers_module                  # noqa: E402

# What a case's outcome is read as.
PASS, FAIL, SKIP = 'pass', 'fail', 'skip'

# What a marker's result is.
NOT_RUN = 'not run'

# The words the run prints about a marker it could not use.
TIED_TO_NO_TEST = 'purlin: %s %s at %s:%d is tied to no test'
NOT_A_MARKER = ('purlin: %s:%d is not a marker; write purlin: <feature> '
                'PROOF-<n>')
NO_SUCH_FEATURE = 'purlin: %s %s at %s:%d names a feature no spec has'
NO_SUCH_PROOF = 'purlin: %s %s at %s:%d names a proof no spec has'
NO_SUCH_RULE = 'purlin: %s %s at %s:%d names a rule no spec has'
RULE_HAS_PROOFS = ('purlin: %s %s at %s:%d names a rule that has proofs; '
                   'name one of them')
# The one line after them, naming what to do. A marker naming nothing a spec
# has fails the run.
FIX_ONE = 'Remove the comment, or write the proof it names.'
FIX_MANY = 'Remove each comment, or write the proof it names.'
AMBIGUOUS = ("purlin: the report's %s matches %d tests in %s, so its result "
             'is not counted')

# The outcomes TRX writes that mean the test ran and did not pass, and those
# that mean it did not run at all.
_TRX_FAIL = ('failed', 'error', 'timeout', 'aborted')
_TRX_PASS = ('passed', 'passedbutrunaborted', 'warning', 'completed')


class Case(object):
    """One test result from a report."""

    __slots__ = ('file', 'classname', 'name', 'outcome', 'package')

    def __init__(self, name, outcome, classname='', file=None, package=None):
        self.name = name
        self.outcome = outcome
        self.classname = classname or ''
        self.file = file
        self.package = package

    def __repr__(self):
        return 'Case(%s %s %s %s)' % (self.file or self.classname,
                                      self.name, self.outcome,
                                      self.package or '')


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
                kinds = {_local(grand.tag) for grand in list(child)}
                if kinds & {'failure', 'error'}:
                    outcome = FAIL
                elif 'skipped' in kinds:
                    outcome = SKIP
                else:
                    outcome = PASS
                cases.append(Case(child.get('name') or '', outcome,
                                  child.get('classname') or '',
                                  child.get('file') or suite_file))
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
        if outcome in _TRX_FAIL:
            result = FAIL
        elif outcome in _TRX_PASS:
            result = PASS
        else:
            result = SKIP
        classname, name = methods.get(node.get('testId'), ('', ''))
        if not name:
            # A result with no definition names its test in full.
            full = re.sub(r'\(.*\)$', '', node.get('testName') or '')
            classname, _, name = full.rpartition('.')
        cases.append(Case(name, result, classname))
    return cases


def read_gotest(text):
    """Every test `go test -json` reported passing, failing or skipping."""
    cases = []
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
        if action not in (PASS, FAIL, SKIP):
            continue
        cases.append(Case(str(event['Test']), action,
                          package=str(event.get('Package') or '')))
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
    if report == '-':
        texts = [stdout or '']
    else:
        full = os.path.join(project_root, *report.split('/'))
        if os.path.isdir(full):
            texts = []
            for name in sorted(os.listdir(full)):
                if name.lower().endswith(_DIRECTORY_EXTENSIONS[fmt]):
                    texts.append(_read(os.path.join(full, name)))
            if not texts:
                return [], 'wrote no report in %s' % report
        elif os.path.isfile(full):
            texts = [_read(full)]
        else:
            return [], 'wrote no report at %s' % report
    cases = []
    for text in texts:
        if text is None:
            return [], 'wrote a report at %s that could not be read' % report
        try:
            cases.extend(reader(text.lstrip('﻿')))
        except (ElementTree.ParseError, ValueError) as error:
            return [], 'wrote a report at %s that is not %s: %s' % (
                report, fmt, error)
    return cases, None


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------

def command_for(suite, files, report=None):
    """The suite's `run` with `{files}` and `{report}` filled in.

    `files` is the list of test files to run, or empty for the whole suite.
    Each path is quoted for the shell the command runs in.
    """
    joined = ' '.join(shlex.quote(path) for path in files or ())
    text = suite.run.replace('{files}', joined)
    if report and report != '-':
        text = text.replace('{report}', shlex.quote(report))
    return ' '.join(text.split()) if '\n' not in text else text


def clear_report(project_root, report):
    """Delete a report before its suite runs, so a stale one is never read."""
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
    named = [test for test in tests if test.name == title
             or (test.pattern is not None and test.pattern.match(title))]
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
    # junit
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
    found = marked.get(path)
    if found is None:
        return []
    if path.endswith('.py'):
        title = _strip_parameters(title)
    return [(path, test) for test in _pick(found.tests, title, scopes, exact)]


def tie(project_root, suite, cases, marked):
    """`(outcomes, problems)` for one suite's cases.

    `outcomes` is `{(path, test line): [outcome, ...]}` for every marked test
    a case was tied to, and `problems` one line for each case that matched
    more than one test.
    """
    outcomes = {}
    problems = []
    cache = {}
    for case in cases:
        found = locate(project_root, suite, case, marked, cache)
        if len(found) == 1:
            path, test = found[0]
            outcomes.setdefault((path, test.line), []).append(case.outcome)
        elif len(found) > 1:
            line = AMBIGUOUS % (case.name, len(found),
                                ', '.join(sorted({path for path, _t in found})))
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


def test_name(path, test, fmt):
    """The name the evidence gives a test; a file of an `exit` suite is its own."""
    return markers_module.test_name(path, None if fmt == 'exit' else test)


# ---------------------------------------------------------------------------
# What the markers say
# ---------------------------------------------------------------------------

def malformed_lines(scan):
    """One line per `purlin:` comment that is not a marker, by file and line."""
    lines = []
    for path in sorted(scan):
        for line, _text in scan[path].malformed:
            lines.append(NOT_A_MARKER % (path, line))
    return lines


def marker_problems(scan, features):
    """One line per marker whose id counts for nothing, by file and line.

    A marker naming a feature, a proof or a rule no spec has, or naming a
    rule that has proofs, ties no result to any rule, and each one fails the
    run. `scan` is `markers.scan`'s answer and `features`
    `specs.scan_specs`'.
    """
    lines = []
    for path in sorted(scan):
        for marker in scan[path].markers:
            info = features.get(marker.feature)
            args = (marker.feature, marker.id, path, marker.line)
            if info is None:
                lines.append(NO_SUCH_FEATURE % args)
            elif marker.id.startswith('PROOF-'):
                if marker.id not in (info.get('proofs') or {}):
                    lines.append(NO_SUCH_PROOF % args)
            elif marker.id not in (info.get('rules') or {}):
                lines.append(NO_SUCH_RULE % args)
            elif (info.get('proofs_by_rule') or {}).get(marker.id):
                lines.append(RULE_HAS_PROOFS % args)
    return lines


def untied_lines(scan):
    """One line per marker no test follows, in file and line order."""
    lines = []
    for path in sorted(scan):
        for marker in scan[path].untied:
            lines.append(TIED_TO_NO_TEST % (marker.feature, marker.id, path,
                                            marker.line))
    return lines
