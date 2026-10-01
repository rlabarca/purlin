"""The heuristic spot tests: what a test's own source shows, with no model.

The audit's first step. Each marked test is read as text, without running it,
against the six checks `references/review_criteria.md`, "Heuristic spot
tests", gives, and a check fires only on a pattern that is wrong in every
case. Python is read by its syntax tree; JavaScript, TypeScript, C#, Go and
shell by the token reading `markers` already uses. A check a language cannot
be read for is answered as `(check, None)`, and the audit prints `NOT_READ`
once per check and language. No model is called and no file is written.

    check(project_root, feature, proof, test)      one tied test
    check_project(project_root, features, out)     every marked test of a project

What each language is read for:

    Python, JavaScript, TypeScript, C#   all six checks
    Go                                   1, 2, 4 and 6
    shell                                1, 2 and 6
    any other                            6
"""

import ast
import os
import re
import subprocess
import sys
import textwrap

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import markers as markers_module                    # noqa: E402
from purlin import specs as specs_module                        # noqa: E402

CHECKS = ('The test checks nothing', 'The check cannot fail', 'The test swallows the error',
          'The test checks the code against itself', 'The test replaces what it is testing',
          'The test never checks the result the proof expects')
NOT_READ = '%s is not read in %s tests.'                 # check, 'shell'

NOTHING, CANNOT_FAIL, SWALLOWS, ITSELF, MOCKS, NEVER = CHECKS

CHECKS_NOTHING = '%s::%s: the test checks nothing.'
CANNOT_FAIL_AT = '%s::%s: the check cannot fail: %s.'
SWALLOWS_ERROR = '%s::%s: the test swallows the error the code raises.'
EXPECTED_FROM = '%s::%s: the expected value comes from %s(), the code under test.'
MOCKS_IT = '%s::%s: the test mocks %s(), the function it checks.'
NEVER_CHECKS = '%s::%s: the proof expects %s and the test never checks it.'

_LANGUAGES = {}
for _ext in ('.py',):
    _LANGUAGES[_ext] = 'Python'
for _ext in ('.js', '.jsx', '.mjs', '.cjs'):
    _LANGUAGES[_ext] = 'JavaScript'
for _ext in ('.ts', '.tsx', '.mts', '.cts'):
    _LANGUAGES[_ext] = 'TypeScript'
for _ext in ('.cs',):
    _LANGUAGES[_ext] = 'C#'
for _ext in ('.go',):
    _LANGUAGES[_ext] = 'Go'
for _ext in ('.sh', '.bash', '.zsh'):
    _LANGUAGES[_ext] = 'shell'

# The checks each language is read for, by their place in CHECKS.
_READ = {
    'Python': (0, 1, 2, 3, 4, 5),
    'JavaScript': (0, 1, 2, 3, 4, 5),
    'TypeScript': (0, 1, 2, 3, 4, 5),
    'C#': (0, 1, 2, 3, 4, 5),
    'Go': (0, 1, 3, 5),
    'shell': (0, 1, 5),
}

# What counts as an assertion of the test framework, read in a file's text.
_ASSERTS = {
    'Python': re.compile(r'\bassert\b|\.assert\w*\s*\(|\bpytest\.(raises|fail|warns)\b'),
    'JavaScript': re.compile(r'\bexpect\s*\(|\bassert\b'),
    'C#': re.compile(r'\b(Assert|CollectionAssert|StringAssert)\s*\.|\.Should\s*\('),
    'Go': re.compile(r'\bt\s*\.\s*(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\b'
                     r'|\b(assert|require)\s*\.'),
    'shell': re.compile(r'(^|[\s;&|(!])(\[\[?|test|grep\s+-\w*q|diff|cmp|fail|assert\w*)\s'
                        r'|\bexit\s+[1-9]', re.M),
}
_ASSERTS['TypeScript'] = _ASSERTS['JavaScript']

_DATA_FILE_RE = re.compile(r'["\'`]([^"\'`\s]+\.(?:json|ya?ml|csv|tsv|txt|xml|toml|ini))["\'`]')
_NUMBER_RE = re.compile(r'^-?\d+(?:\.\d+)?$')
_NUMBERS_RE = re.compile(r'-?\d+(?:\.\d+)?')
_BACKTICK_RE = re.compile(r'`([^`]+)`')
_PAIR_RE = re.compile(r'^([A-Za-z_][\w-]*)(?:=|: )(\S+)$')
_PLACEHOLDER_RE = re.compile(r'<[a-z][^<>]*>')
_CALL_NAME_RE = re.compile(r'([A-Za-z_$][\w$]*)\s*\(')
_KEYWORDS = frozenset((
    'if', 'for', 'while', 'switch', 'catch', 'return', 'function', 'typeof', 'new', 'await',
    'async', 'using', 'foreach', 'nameof', 'sizeof', 'lock', 'fixed', 'func', 'go', 'defer',
    'expect', 'assert', 'it', 'test', 'describe', 'else', 'try', 'throw', 'yield', 'void',
    'base', 'this', 'super', 'make', 'len', 'append', 'string', 'int'))


def language_of(path):
    """The language a test file is read as: `Python`, `JavaScript`, `TypeScript`, `C#`,
    `Go`, `shell`, or the file's extension without its dot."""
    ext = os.path.splitext(path)[1].lower()
    return _LANGUAGES.get(ext) or ext.lstrip('.') or 'unnamed'


def check(project_root, feature, proof, test):
    """[(check, finding)] for one tied test, from its source and the proof's words.
    `proof` is {'id', 'text'}; `test` is {'file', 'name', 'source'}. A check the test's
    language cannot be read for is given as (check, None)."""
    path = test['file']
    name = test['name']
    language = language_of(path)
    text = _read(project_root, path)
    if text is None:
        text = test.get('source') or ''
    read = _READ.get(language, (5,))
    reader = _PythonTest if language == 'Python' else _TokenTest
    found = reader(project_root, path, name, text, test.get('source') or '', language)
    out = []
    for index, title in enumerate(CHECKS):
        if index not in read:
            out.append((title, None))
            continue
        if index == 5:
            value = _value_never_checked(project_root, path, text, (proof or {}).get('text', ''))
            if value is not None:
                out.append((title, NEVER_CHECKS % (path, name, value)))
            continue
        finding = found.finding(index)
        if finding is not None:
            template, extra = finding
            out.append((title, template % ((path, name) + extra)))
    return out


def check_project(project_root, features=None, out=None):
    """Every marked test of the project, or of `features`, read against its proofs.

    Prints `NOT_READ` once per check and language to `out` (standard output by
    default). Answers one entry per finding:
    `{'feature', 'proof', 'file', 'name', 'check', 'finding'}`, by file and line.
    """
    global _cache
    out = out or sys.stdout
    _cache = {}
    try:
        return _check_project(project_root, features, out)
    finally:
        _cache = None


def _check_project(project_root, features, out):
    specs = specs_module.scan_specs(project_root)
    suites, _problems = markers_module.read_suites(project_root)
    scan = markers_module.scan(project_root, suites)
    wanted = set(features) if features else None
    said = set()
    findings = []
    for path in sorted(scan):
        found = scan[path]
        text = _read(project_root, path) or ''
        if found.whole:
            owners = [(None, found.markers)]
        else:
            owners = [(t, t.markers) for t in found.tests if t.markers]
        for owner, marks in owners:
            test = {'file': path, 'name': markers_module.test_name(path, owner),
                    'source': _source_of(text, path, owner)}
            for marker in marks:
                if wanted is not None and marker.feature not in wanted:
                    continue
                info = specs.get(marker.feature)
                if info is None:
                    continue
                proof = info['proofs'].get(marker.id)
                proof = {'id': marker.id, 'text': proof['text'] if proof else ''}
                for title, finding in check(project_root, marker.feature, proof, test):
                    if finding is None:
                        key = (title, language_of(path))
                        if key not in said:
                            said.add(key)
                            print(NOT_READ % key, file=out)
                        continue
                    findings.append({'feature': marker.feature, 'proof': marker.id,
                                     'file': path, 'name': test['name'], 'check': title,
                                     'finding': finding})
    return findings


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

# Within one `check_project` run the project's files are read once.
_cache = None


def _read(project_root, path):
    if _cache is not None:
        key = ('read', project_root, path)
        if key not in _cache:
            _cache[key] = _read_disk(project_root, path)
        return _cache[key]
    return _read_disk(project_root, path)


def _read_disk(project_root, path):
    full = os.path.join(project_root, *path.split('/'))
    try:
        with open(full, 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _source_of(text, path, test):
    if test is None or test.start is None:
        return text
    if path.endswith('.py'):
        lines = text.splitlines(True)
        return ''.join(lines[test.start - 1:test.end or len(lines)])
    return text[test.start:test.end]


def _project_files(project_root):
    if _cache is not None:
        key = ('files', project_root)
        if key not in _cache:
            _cache[key] = _list_files(project_root)
        return _cache[key]
    return _list_files(project_root)


def _list_files(project_root):
    try:
        done = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard', '-z'],
                              capture_output=True, cwd=project_root, timeout=60)
        if done.returncode == 0:
            return [p for p in done.stdout.decode('utf-8', 'replace').split('\0') if p]
    except (subprocess.SubprocessError, OSError):
        pass
    return list(markers_module._walk(project_root))


_DEFINES = {
    'Python': r'^\s*(?:async\s+)?def\s+%s\s*\(',
    'JavaScript': r'(?:\bfunction\s*\*?\s*%s\s*\(|\b%s\s*[:=]\s*(?:async\s*)?(?:function\b|\())',
    'C#': r'\b[\w<>\[\],]+\s+%s\s*(?:<[^<>()]*>)?\s*\([^;]*\)\s*(?:\{|=>)',
    'Go': r'^func\s+(?:\([^)]*\)\s*)?%s\s*\(',
}
_DEFINES['TypeScript'] = _DEFINES['JavaScript']


def _helper_elsewhere_asserts(project_root, path, language, names):
    """True when one of `names` is defined in another file of the project, in the
    same language, and that file holds an assertion: such a helper may assert."""
    pattern = _DEFINES.get(language)
    if not pattern or not names:
        return False
    asserts = _ASSERTS[language]
    for other in _project_files(project_root):
        if other == path or language_of(other) != language:
            continue
        text = _read(project_root, other)
        if not text or not asserts.search(text):
            continue
        for name in names:
            escaped = re.escape(name)
            if re.search(pattern.replace('%s', escaped), text, re.M):
                return True
    return False


def _value_never_checked(project_root, path, text, proof_text):
    """The first value the proof marks in backticks, where the test's file and the data
    files it names hold none of them; else None."""
    values = [v.strip() for v in _BACKTICK_RE.findall(proof_text or '') if v.strip()]
    if not values:
        return None
    held = [text]
    if language_of(path) == 'Python':
        # A value written across adjacent string literals is one string to Python.
        held.append(_python_strings(text))
    here = os.path.dirname(path)
    for named in _DATA_FILE_RE.findall(text):
        for candidate in (named, os.path.join(here, named)):
            data = _read(project_root, os.path.normpath(candidate).replace(os.sep, '/'))
            if data is not None:
                held.append(data)
                break
    for value in values:
        if any(_holds(body, value) for body in held):
            return None
    return values[0]


def _python_strings(text):
    """Every string a Python file holds, each as Python joins its adjacent literals."""
    tree = _parsed(text)[0]
    if tree is None:
        return ''
    return '\n'.join(repr(node.value) + '\n' + node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str))


def _holds(body, value):
    """True when `body` holds `value`: the same number written another way; the same
    words; a `NAME=value` or `Name: value` pair whose two sides stand as two strings;
    or, for a value with a `<placeholder>`, each of its other parts."""
    if _NUMBER_RE.match(value):
        wanted = float(value)
        return any(float(n) == wanted for n in _NUMBERS_RE.findall(body))
    if value in body:
        return True
    pair = _PAIR_RE.match(value)
    if pair and all(repr(side) in body or '"%s"' % side in body
                    for side in pair.group(1, 2)):
        return True
    parts = [part.strip() for part in _PLACEHOLDER_RE.split(value)]
    if len(parts) > 1 and sum(len(part) for part in parts) >= 8:
        return all(part in body for part in parts if part)
    return False


def _flat(text):
    return ' '.join(text.split())


# ---------------------------------------------------------------------------
# Python, by its syntax tree
# ---------------------------------------------------------------------------

def _callee(node):
    """`age` for `age(s)`, `lib.age(s)` and `self.lib.age(s)`; None otherwise."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return '.'.join(reversed(parts))


def _has_call(node):
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


def _string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _parse_python(text):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None, {}
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(node.name, node)
    return tree, defs


def _parsed(text):
    """`(tree, {function name: its first definition})`, once per text in a run."""
    if _cache is None:
        return _parse_python(text)
    key = ('ast', text)
    if key not in _cache:
        _cache[key] = _parse_python(text)
    return _cache[key]


class _PythonTest(object):
    def __init__(self, project_root, path, name, text, source, language):
        self.project_root = project_root
        self.path = path
        self.text = text
        self.node = None
        self.defs = {}
        tree, self.defs = _parsed(text)
        if tree is not None:
            self.node = self._locate(tree, name.split('::'))
        if self.node is None and source:
            try:
                tree = ast.parse(textwrap.dedent(source))
                self.text = textwrap.dedent(source)
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.node = node
                        break
            except (SyntaxError, ValueError):
                pass

    @staticmethod
    def _locate(tree, parts):
        body = tree.body
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            match = None
            for node in body:
                if last and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and node.name == part:
                    match = node
                elif not last and isinstance(node, ast.ClassDef) and node.name == part:
                    match = node
            if match is None:
                return None
            if last:
                return match
            body = match.body
        return None

    def _segment(self, node):
        return _flat(ast.get_source_segment(self.text, node) or ast.unparse(node))

    def finding(self, index):
        if self.node is None:
            return None
        return (self._nothing, self._cannot_fail, self._swallows, self._itself,
                self._mocks)[index]()

    # -- what the test asserts ------------------------------------------------

    @staticmethod
    def _is_assert_call(node):
        if not isinstance(node, ast.Call):
            return False
        name = _callee(node) or ''
        dotted = _dotted(node.func)
        return (name.startswith('assert') or name in ('raises', 'warns', 'fail')
                and dotted.startswith('pytest') or name == 'expect')

    @staticmethod
    def _raises_assertion(node):
        if not isinstance(node, ast.Raise) or node.exc is None:
            return False
        exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        return _dotted(exc).rsplit('.', 1)[-1] == 'AssertionError'

    def _asserts(self, node, seen):
        for child in ast.walk(node):
            if isinstance(child, ast.Assert) or self._is_assert_call(child) or \
                    self._raises_assertion(child):
                return True
        for child in ast.walk(node):
            name = None
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    name = child.func.id
                elif isinstance(child.func, ast.Attribute) and \
                        isinstance(child.func.value, ast.Name) and \
                        child.func.value.id in ('self', 'cls'):
                    name = child.func.attr
            if name and name in self.defs and name not in seen:
                seen.add(name)
                if self._asserts(self.defs[name], seen):
                    return True
        return False

    def _called_elsewhere(self):
        names = set()
        for child in ast.walk(self.node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) \
                    and child.func.id not in self.defs:
                names.add(child.func.id)
            elif isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                names.add(child.func.attr)
        return sorted(names)

    def _nothing(self):
        if self._asserts(self.node, {self.node.name}):
            return None
        if _helper_elsewhere_asserts(self.project_root, self.path, 'Python',
                                     self._called_elsewhere()):
            return None
        return CHECKS_NOTHING, ()

    def _assertions(self):
        """Each assertion of the test: `(node, [the values it compares], kind)`."""
        out = []
        for child in ast.walk(self.node):
            if isinstance(child, ast.Assert):
                test = child.test
                if isinstance(test, ast.Compare) and len(test.ops) == 1:
                    out.append((child, [test.left, test.comparators[0]], test.ops[0]))
                else:
                    out.append((child, [test], None))
            elif isinstance(child, ast.Call) and (_callee(child) or '').startswith('assert'):
                out.append((child, list(child.args), _callee(child)))
        return out

    def _cannot_fail(self):
        for node, values, kind in self._assertions():
            if self._always_true(values, kind):
                return CANNOT_FAIL_AT, (self._segment(node),)
        return None

    @staticmethod
    def _always_true(values, kind):
        if len(values) == 1 and kind in (None, 'assertTrue'):
            value = values[0]
            return (isinstance(value, ast.Constant) and bool(value.value)
                    and not isinstance(value.value, str))
        if len(values) < 2:
            return False
        left, right = values[0], values[1]
        same = (ast.dump(left) == ast.dump(right) and not _has_call(left))
        if same and (isinstance(kind, (ast.Eq, ast.Is, ast.LtE, ast.GtE)) or kind in (
                'assertEqual', 'assertEquals', 'assertIs', 'assertGreaterEqual',
                'assertLessEqual', 'assertDictEqual', 'assertListEqual')):
            return True
        zero = lambda n: isinstance(n, ast.Constant) and n.value == 0   # noqa: E731
        size = lambda n: _callee(n) == 'len' and isinstance(n.func, ast.Name)  # noqa: E731
        if isinstance(kind, ast.GtE) or kind == 'assertGreaterEqual':
            return size(left) and zero(right)
        if isinstance(kind, ast.LtE) or kind == 'assertLessEqual':
            return zero(left) and size(right)
        return False

    def _swallows(self):
        try_types = tuple(t for t in (getattr(ast, 'Try', None), getattr(ast, 'TryStar', None))
                          if t is not None)
        for child in ast.walk(self.node):
            if not isinstance(child, try_types) or not child.handlers:
                continue
            if not any(_has_call(stmt) for stmt in child.body):
                continue
            for handler in child.handlers:
                if all(isinstance(stmt, ast.Pass) or
                       isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                       for stmt in handler.body):
                    return SWALLOWS_ERROR, ()
        return None

    def _bindings(self):
        bound = {}
        for child in ast.walk(self.node):
            if isinstance(child, ast.Assign) and len(child.targets) == 1 and \
                    isinstance(child.targets[0], ast.Name) and \
                    isinstance(child.value, ast.Call):
                bound[child.targets[0].id] = child.value
        return bound

    def _acted_between(self, call, node):
        """True when a call stands between the line binding `call` and the assertion
        `node`: the value was taken, something was done, and it was taken again, which
        compares a state before and after, not the code against itself."""
        after = getattr(call, 'end_lineno', call.lineno)
        if after >= node.lineno:
            return False
        return any(isinstance(child, ast.Call) and after < child.lineno < node.lineno
                   for child in ast.walk(self.node))

    def _call_of(self, node, bound):
        if isinstance(node, ast.Call):
            return node
        if isinstance(node, ast.Name):
            return bound.get(node.id)
        return None

    def _itself(self):
        bound = self._bindings()
        for node, values, kind in self._assertions():
            if len(values) < 2 or not (isinstance(kind, (ast.Eq, ast.Is)) or kind in (
                    'assertEqual', 'assertEquals', 'assertIs', 'assertDictEqual',
                    'assertListEqual', 'assertAlmostEqual')):
                continue
            if ast.dump(values[0]) == ast.dump(values[1]) and not _has_call(values[0]):
                continue    # a value compared with itself: the check cannot fail
            first = self._call_of(values[0], bound)
            second = self._call_of(values[1], bound)
            if first is None or second is None:
                continue
            if _callee(first) and ast.dump(first) == ast.dump(second) and not any(
                    self._acted_between(c, node) for c in (first, second) if c not in values):
                return EXPECTED_FROM, (_callee(first),)
        return None

    def _checked(self):
        """The functions whose results the test asserts on."""
        bound = self._bindings()
        names = set()
        for _node, values, _kind in self._assertions():
            for value in values:
                for child in ast.walk(value):
                    if isinstance(child, ast.Call):
                        names.add(_callee(child))
                    elif isinstance(child, ast.Name) and child.id in bound:
                        names.add(_callee(bound[child.id]))
        names.discard(None)
        return names

    def _mocked(self):
        targets = []
        for child in ast.walk(self.node):
            if not isinstance(child, ast.Call):
                continue
            dotted = _dotted(child.func)
            parts = dotted.split('.')
            target = None
            if parts[-1] == 'patch' and child.args:
                target = _string(child.args[0])
                target = target.rsplit('.', 1)[-1] if target else None
            elif parts[-1] == 'object' and len(parts) > 1 and parts[-2] == 'patch' \
                    and len(child.args) > 1:
                target = _string(child.args[1])
            elif parts[-1] == 'setattr' and len(parts) > 1 and child.args:
                first = _string(child.args[0])
                if first is not None:
                    target = first.rsplit('.', 1)[-1]
                elif len(child.args) > 1:
                    target = _string(child.args[1])
            if target:
                targets.append(target)
        return targets

    def _mocks(self):
        checked = self._checked()
        for target in self._mocked():
            if target in checked:
                return MOCKS_IT, (target,)
        return None


# ---------------------------------------------------------------------------
# JavaScript, TypeScript, C#, Go and shell, by their tokens
# ---------------------------------------------------------------------------

def _split_args(raw, mask):
    """The top-level arguments of a call, `raw` and `mask` being its inside."""
    out = []
    depth = 0
    start = 0
    for index, char in enumerate(mask):
        if char in '([{':
            depth += 1
        elif char in ')]}':
            depth -= 1
        elif char == ',' and depth == 0:
            out.append(raw[start:index].strip())
            start = index + 1
    tail = raw[start:].strip()
    if tail or out:
        out.append(tail)
    return out


class _Call(object):
    """One call found in a body: its head, its arguments, and where it ends."""

    def __init__(self, body, mask, head_start, open_paren):
        close = markers_module._balanced(mask, open_paren, '(', ')')
        self.start = head_start
        self.end = close
        self.head = _flat(body[head_start:open_paren])
        self.raw = body[head_start:close]
        self.args = _split_args(body[open_paren + 1:close - 1], mask[open_paren + 1:close - 1])


def _calls(body, mask, pattern):
    for found in pattern.finditer(mask):
        yield _Call(body, mask, found.start(), found.end() - 1)


def _norm(text):
    return re.sub(r'\s+', '', text)


def _call_text(text):
    """`(callee, normalised call)` where `text` is wholly one call, else None."""
    text = text.strip().rstrip(';').strip()
    found = re.match(r'^((?:[A-Za-z_$][\w$]*\s*\.\s*)*([A-Za-z_$][\w$]*))\s*\(', text)
    if not found or not text.endswith(')'):
        return None
    mask = markers_module._mask(text, markers_module.skip_noncode)
    if markers_module._balanced(mask, found.end() - 1, '(', ')') != len(text):
        return None
    return found.group(2), _norm(text)


_BIND_RES = {
    'JavaScript': re.compile(r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=;]+)?=\s*'),
    'C#': re.compile(r'\b(?:var|[A-Z][\w<>\[\],]*|int|long|double|float|decimal|string|bool)'
                     r'\s+([A-Za-z_]\w*)\s*=\s*'),
    'Go': re.compile(r'\b([A-Za-z_]\w*)\s*:=\s*'),
}
_BIND_RES['TypeScript'] = _BIND_RES['JavaScript']

# The assertions read for checks 2 and 4: (head, which arguments are compared).
_JS_EXPECT_RE = re.compile(r'(?<![\w$.])expect\s*\(')
_JS_ASSERT_RE = re.compile(r'(?<![\w$.])assert(?:\s*\.\s*(\w+))?\s*\(')
_CS_ASSERT_RE = re.compile(r'(?<![\w.])Assert\s*\.\s*(\w+)\s*\(')
_GO_ASSERT_RE = re.compile(r'(?<![\w.])(?:assert|require)\s*\.\s*(\w+)\s*\(')
_EQUALS = frozenset(('toBe', 'toEqual', 'toStrictEqual', 'equal', 'strictEqual', 'deepEqual',
                     'deepStrictEqual', 'Equal', 'AreEqual', 'Same', 'AreSame', 'Equals',
                     'EqualValues', 'Exactly'))
_TRUES = frozenset(('true', '1', '!0', '!false'))


class _TokenTest(object):
    def __init__(self, project_root, path, name, text, source, language):
        self.project_root = project_root
        self.path = path
        self.language = language
        self.text = text
        skipper = (markers_module.skip_csharp_noncode if language == 'C#'
                   else markers_module.skip_noncode)
        self.body = self._locate(path, name, text) or source or text
        if language == 'shell':
            self.mask = '\n'.join('' if line.lstrip().startswith('#') else line
                                  for line in self.body.split('\n'))
            self.file_mask = self.mask
        else:
            self.mask = markers_module._mask(self.body, skipper)
            self.file_mask = markers_module._mask(text, skipper)
        self.assertions = self._read_assertions() if language != 'shell' else []

    @staticmethod
    def _locate(path, name, text):
        ext = os.path.splitext(path)[1].lower()
        tests = markers_module.declared_tests(text, ext)
        for test in tests or ():
            if markers_module.test_name(path, test) == name or test.name == name or \
                    name.endswith('.' + test.qualified('.')):
                if test.start is not None and test.end is not None:
                    return text[test.start:test.end]
        return None

    def finding(self, index):
        return (self._nothing, self._cannot_fail, self._swallows, self._itself,
                self._mocks)[index]()

    # -- the assertions ------------------------------------------------------

    def _read_assertions(self):
        """Each assertion: `{'text', 'kind', 'actual', 'expected', 'args'}`."""
        out = []
        body, mask = self.body, self.mask
        if self.language in ('JavaScript', 'TypeScript'):
            for call in _calls(body, mask, _JS_EXPECT_RE):
                chain = re.match(r'\s*\.\s*(not\s*\.\s*)?(\w+)\s*\(', mask[call.end:])
                if not chain:
                    continue
                open_paren = call.end + chain.end() - 1
                matcher = _Call(body, mask, call.end, open_paren)
                out.append({'text': _flat(body[call.start:matcher.end]),
                            'raw': body[call.start:matcher.end],
                            'kind': None if chain.group(1) else chain.group(2),
                            'actual': call.args[0] if call.args else '',
                            'expected': matcher.args[0] if matcher.args else None,
                            'args': call.args + matcher.args})
            for found in _JS_ASSERT_RE.finditer(mask):
                call = _Call(body, mask, found.start(), found.end() - 1)
                out.append(self._plain(call, found.group(1) or 'ok', 0))
        elif self.language == 'C#':
            for found in _CS_ASSERT_RE.finditer(mask):
                call = _Call(body, mask, found.start(), found.end() - 1)
                out.append(self._plain(call, found.group(1), 0))
        elif self.language == 'Go':
            for found in _GO_ASSERT_RE.finditer(mask):
                call = _Call(body, mask, found.start(), found.end() - 1)
                out.append(self._plain(call, found.group(1), 1))
        return out

    @staticmethod
    def _plain(call, kind, skip):
        args = call.args[skip:]
        entry = {'text': call.head + '(' + ', '.join(call.args) + ')', 'kind': kind,
                 'raw': call.raw,
                 'actual': None, 'expected': None, 'args': args}
        if kind in _EQUALS and len(args) >= 2:
            # assert.equal(actual, expected); Assert.Equal(expected, actual)
            entry['actual'], entry['expected'] = args[0], args[1]
        elif args:
            entry['actual'] = args[0]
        return entry

    # -- the checks ----------------------------------------------------------

    def _nothing(self):
        asserts = _ASSERTS[self.language]
        if asserts.search(self.mask):
            return None
        if self.language == 'shell':
            return CHECKS_NOTHING, ()
        local, elsewhere = set(), set()
        pattern = _DEFINES[self.language]
        for name in set(_CALL_NAME_RE.findall(self.mask)) - _KEYWORDS:
            found = re.search(pattern.replace('%s', re.escape(name)), self.file_mask, re.M)
            if found:
                local.add((name, found))
            else:
                elsewhere.add(name)
        for name, found in local:
            brace = self.file_mask.find('{', found.end() - 1)
            arrow = self.file_mask.find('=>', found.end() - 1)
            start = brace if brace >= 0 else arrow
            if start < 0:
                continue
            end = markers_module._balanced(self.file_mask, start, '{', '}') \
                if self.file_mask[start] == '{' else self.file_mask.find('\n', start)
            if asserts.search(self.file_mask[start:end]):
                return None
        if _helper_elsewhere_asserts(self.project_root, self.path, self.language,
                                     sorted(elsewhere)):
            return None
        return CHECKS_NOTHING, ()

    def _cannot_fail(self):
        if self.language == 'shell':
            found = re.search(r'\[\[?\s+("?)([^\s"\]]+)\1\s+(=|==|-eq|-le|-ge)\s+("?)\2\4\s+\]\]?',
                              self.mask)
            if found and not found.group(2).startswith('$('):
                return CANNOT_FAIL_AT, (found.group(0),)
            return None
        for entry in self.assertions:
            if self._always_true(entry):
                return CANNOT_FAIL_AT, (entry['text'],)
        return None

    @staticmethod
    def _always_true(entry):
        kind, actual, expected = entry['kind'], entry['actual'], entry['expected']
        if kind is None:
            return False
        if kind in ('toBeTruthy', 'ok', 'True', 'IsTrue', 'That') and actual is not None \
                and _norm(actual) in _TRUES:
            return True
        if kind in _EQUALS and actual is not None and expected is not None:
            if _norm(actual) == _norm(expected) and '(' not in actual:
                return True
        if kind in ('toBeGreaterThanOrEqual', 'GreaterOrEqual') and actual is not None \
                and expected is not None and _norm(expected) == '0' and \
                re.search(r'\.(length|Length|Count)$|^len\(', _norm(actual)):
            return True
        if kind in ('True', 'IsTrue', 'ok') and actual is not None and re.match(
                r'^[\w.]+\.(length|Length|Count)>=0$|^len\([\w.]+\)>=0$', _norm(actual)):
            return True
        return False

    def _swallows(self):
        mask = self.mask
        for found in re.finditer(r'(?<![\w.])try\s*\{', mask):
            open_brace = found.end() - 1
            close = markers_module._balanced(mask, open_brace, '{', '}')
            if not _CALL_NAME_RE.search(mask[open_brace:close]):
                continue
            position = close
            while True:
                handler = re.match(r'\s*catch\b\s*(?:\([^)]*\))?\s*(?:when\s*\([^)]*\)\s*)?\{',
                                   mask[position:])
                if not handler:
                    break
                start = position + handler.end() - 1
                end = markers_module._balanced(mask, start, '{', '}')
                if not mask[start + 1:end - 1].strip():
                    return SWALLOWS_ERROR, ()
                position = end
        return None

    def _bindings(self):
        bound = {}
        pattern = _BIND_RES.get(self.language)
        if pattern is None:
            return bound
        for found in pattern.finditer(self.mask):
            rest = self.mask[found.end():]
            stop = min([i for i in (rest.find(';'), rest.find('\n')) if i >= 0] or [len(rest)])
            value = self.body[found.end():found.end() + stop]
            call = _call_text(value)
            if call:
                bound[found.group(1)] = call + (found.end() + stop,)
        return bound

    def _call_of(self, text, bound):
        if text is None:
            return None
        call = _call_text(text)
        if call:
            return call + (None,)
        return bound.get(text.strip())

    def _acted_between(self, bound_at, entry):
        """True when a call stands between the binding and the assertion."""
        if bound_at is None:
            return False
        start = self.body.find(entry['raw'], bound_at) if entry.get('raw') else -1
        between = self.mask[bound_at:start] if start > bound_at else ''
        return bool(set(_CALL_NAME_RE.findall(between)) - _KEYWORDS)

    def _itself(self):
        bound = self._bindings()
        for entry in self.assertions:
            if entry['kind'] not in _EQUALS:
                continue
            if entry['actual'] is None or entry['expected'] is None or (
                    _norm(entry['actual']) == _norm(entry['expected'])
                    and '(' not in entry['actual']):
                continue    # a value compared with itself: the check cannot fail
            first = self._call_of(entry['actual'], bound)
            second = self._call_of(entry['expected'], bound)
            if first and second and first[1] == second[1] and not (
                    self._acted_between(first[2], entry)
                    or self._acted_between(second[2], entry)):
                return EXPECTED_FROM, (first[0],)
        return None

    def _checked(self):
        bound = self._bindings()
        names = set()
        for entry in self.assertions:
            for arg in entry['args']:
                if arg is None:
                    continue
                mask = markers_module._mask(arg, markers_module.skip_noncode)
                names.update(set(_CALL_NAME_RE.findall(mask)) - _KEYWORDS)
                if arg.strip() in bound and bound[arg.strip()]:
                    names.add(bound[arg.strip()][0])
        return names

    def _mocked(self):
        targets = []
        body, mask = self.body, self.mask
        if self.language in ('JavaScript', 'TypeScript'):
            spy = re.compile(r'(?<![\w$])(?:(?:jest|vi)\s*\.\s*spyOn|sinon\s*\.\s*(?:stub|spy|replace)'
                             r'|td\s*\.\s*replace)\s*\(')
            for call in _calls(body, mask, spy):
                if len(call.args) > 1:
                    targets.append(call.args[1].strip().strip('\'"`'))
            for found in re.finditer(r'([A-Za-z_$][\w$.]*)\s*=\s*(?:jest|vi|sinon)\s*\.\s*'
                                     r'(?:fn|stub)\s*\(', mask):
                targets.append(found.group(1).rsplit('.', 1)[-1])
        elif self.language == 'C#':
            for found in re.finditer(r'\.\s*Setup\w*\s*\(\s*\(?\s*\w+\s*\)?\s*=>\s*\w+\s*\.\s*'
                                     r'(\w+)', mask):
                targets.append(found.group(1))
        return targets

    def _mocks(self):
        checked = self._checked()
        for target in self._mocked():
            if target in checked:
                return MOCKS_IT, (target,)
        return None
