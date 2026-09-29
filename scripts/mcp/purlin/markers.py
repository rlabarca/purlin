"""The marker comments in a project's tests, and the tests they sit above.

A marker is one comment, in the language's own comment syntax, on a line above
the test it marks:

    # purlin: login PROOF-4
    def test_rejects_a_wrong_password():

It names a feature and one of its proofs, or, where a rule has no proof, the
rule: `purlin: login RULE-2`. A test may carry several markers, one line each.
`purlin:` is read after any of `#`, `//`, `--`, `;`, `%` and `'`, and inside
`/* */` and `<!-- -->` on one line. `references/formats/marker_format.md` is
the one home of the contract; this module is the one reader of it.

The settings file names the suites under `tests`, each with the globs its test
files live under. Only a file one of those globs matches is read, so a
marker-shaped line in a file no suite runs is not a marker. How a marker is
tied to a test depends on the suite's format:

- `junit`, `trx` and `gotest`: the marker belongs to the next test declared
  after it. Blank lines, decorators, attributes and other comments may sit
  between the two, and every marker between the previous test's declaration
  and this one belongs to this one. A marker with no test after it is tied to
  none, and that is reported, never guessed at.
- `exit`: the file is the test, so every marker in it belongs to the file.

A test declaration is read per language: a Python function whose name starts
with `test` at module level or in a class; a JavaScript or TypeScript `it` or
`test` call with a literal title, inside any `describe` calls; a C# method
carrying `[Fact]`, `[Theory]`, `[Test]`, `[TestCase]` or `[TestMethod]`; a Go
`func TestX(t *testing.T)`. A Python comment is read with the tokenizer, so a
marker-shaped line inside a string is not a marker; a shell file's here
documents are stepped over for the same reason.

A comment that is nearly a marker ties nothing, and a run says nothing of it.
`near_misses` finds each one for `purlin:build`, which shows the fix, asks and
edits:

    python3 scripts/mcp/purlin/markers.py --near-misses [--project-root DIR]

prints one JSON array of `{"file", "line", "text", "fix", "why"}` and exits 0;
a wrong command line exits 2. A near miss is `purlin` misspelled by one
letter or in capitals, no space after the colon, a `purlin:` comment that
cannot be read (its `fix` is null), or a feature name, a PROOF or a RULE id
one edit from one that exists.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
import tokenize

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

# The four report formats a suite may name.
FORMATS = ('junit', 'trx', 'gotest', 'exit')

# Where Purlin asks a suite to write its report when the entry names none.
REPORTS_DIR = '.purlin/runtime/reports'
_REPORT_EXTENSIONS = {'junit': '.xml', 'trx': '', 'gotest': '.json'}

# Directories no test file is read from: dot directories are tool state,
# `node_modules` is other people's code, `bin` and `obj` are build output and
# `mutants/` is mutmut's copy of the project, tests included.
SKIP_DIRS = ('node_modules', 'bin', 'obj', 'mutants')

# One comment line holding `purlin:`, in any of the comment syntaxes.
_COMMENT_RE = re.compile(
    r"""^\s*(?:\#|//|--|;|%|'|/\*|<!--)\s*purlin:\s+(?P<rest>.*?)\s*"""
    r"""(?:\*/|-->)?\s*$""")
# What follows `purlin:` in a marker: a feature and one proof or rule id.
_BODY_RE = re.compile(r'^(?P<feature>\w+)\s+(?P<id>(?:PROOF|RULE)-\d+)$')

_PY_EXTENSIONS = ('.py',)
_JS_EXTENSIONS = ('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.mts',
                  '.cts')
_CS_EXTENSIONS = ('.cs',)
_GO_EXTENSIONS = ('.go',)
_SHELL_EXTENSIONS = ('.sh', '.bash', '.zsh')


class Marker(object):
    """One marker comment: `feature`, `id` (`PROOF-N` or `RULE-N`), `line`."""

    __slots__ = ('feature', 'id', 'line')

    def __init__(self, feature, marker_id, line):
        self.feature = feature
        self.id = marker_id
        self.line = line

    def key(self):
        return (self.feature, self.id)

    def __repr__(self):
        return 'Marker(%s %s @%d)' % (self.feature, self.id, self.line)


class Test(object):
    """One test declaration: its `name`, `line`, enclosing `scopes` and markers.

    `scopes` is the chain of names around the test, outermost first: the
    classes a Python or C# method sits in, the `describe` titles a JavaScript
    test sits in. `pattern` is set for a JavaScript title that a table fills
    in (`it.each`), and matches the titles the runner prints for it. `start`
    and `end` bound the declaration's source, as offsets into the file.
    """

    __slots__ = ('name', 'line', 'scopes', 'markers', 'pattern', 'start',
                 'end', 'namespace')

    def __init__(self, name, line, scopes=(), pattern=None, start=None,
                 end=None, namespace=''):
        self.name = name
        self.line = line
        self.scopes = list(scopes)
        self.markers = []
        self.pattern = pattern
        self.start = start
        self.end = end
        self.namespace = namespace

    def qualified(self, separator):
        return separator.join(self.scopes + [self.name])

    def __repr__(self):
        return 'Test(%s @%d)' % (self.qualified('.'), self.line)


class FileMarkers(object):
    """What one test file holds: its markers, its tests and how they tie.

    `tests` lists every test declared in the file, each with the markers tied
    to it. `untied` lists the markers no test follows. For a file of an
    `exit` suite `whole` is True and every marker belongs to the file.
    """

    __slots__ = ('path', 'format', 'markers', 'tests', 'untied', 'whole')

    def __init__(self, path, fmt):
        self.path = path
        self.format = fmt
        self.markers = []
        self.tests = []
        self.untied = []
        self.whole = fmt == 'exit'

    def features(self):
        return {marker.feature for marker in self.markers}


# ---------------------------------------------------------------------------
# The settings
# ---------------------------------------------------------------------------

class Suite(object):
    """One entry of the `tests` setting."""

    __slots__ = ('name', 'run', 'report', 'format', 'files')

    def __init__(self, name, run, report, fmt, files):
        self.name = name
        self.run = run
        self.report = report
        self.format = fmt
        self.files = list(files)

    def report_path(self):
        """Where this suite's report lands, `-` for standard output, or None.

        An `exit` suite has no report. An entry that names none is given a
        path under `.purlin/runtime/reports/`, named for the suite.
        """
        if self.format == 'exit':
            return None
        if self.report:
            return self.report
        return '%s/%s%s' % (REPORTS_DIR, self.name,
                            _REPORT_EXTENSIONS.get(self.format, ''))

    def matches(self, path):
        return any(glob_match(path, pattern) for pattern in self.files)

    def as_dict(self):
        return {'name': self.name, 'run': self.run, 'report': self.report,
                'format': self.format, 'files': list(self.files)}


def load_config(project_root):
    try:
        path = os.path.join(project_root, '.purlin', 'config.json')
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_suites(project_root, config=None):
    """`(suites, problems)` from the `tests` setting.

    An entry that is not an object, names no `run`, names a format outside
    the four, or names no `files` is left out, and `problems` says why in one
    line each. A project with no `tests` setting has no suites.
    """
    config = load_config(project_root) if config is None else config
    raw = config.get('tests')
    suites, problems = [], []
    if raw is None:
        return suites, problems
    if not isinstance(raw, list):
        return suites, ['"tests" in .purlin/config.json is not a list']
    names = set()
    for index, entry in enumerate(raw):
        label = 'tests[%d]' % index
        if not isinstance(entry, dict):
            problems.append('%s is not an object' % label)
            continue
        name = str(entry.get('name') or '').strip() or 'suite%d' % (index + 1)
        label = 'the %s suite' % name
        run = entry.get('run')
        fmt = str(entry.get('format') or '').strip()
        files = entry.get('files')
        if not isinstance(run, str) or not run.strip():
            problems.append('%s names no run command' % label)
            continue
        if fmt not in FORMATS:
            problems.append('%s names the format "%s", which is not one of %s'
                            % (label, fmt, ', '.join(FORMATS)))
            continue
        if not isinstance(files, list) or not [f for f in files
                                               if isinstance(f, str)]:
            problems.append('%s names no files' % label)
            continue
        if name in names:
            problems.append('%s is named twice; the second is left out'
                            % label)
            continue
        names.add(name)
        report = entry.get('report')
        suites.append(Suite(name, run.strip(), report if isinstance(
            report, str) and report.strip() else None, fmt,
            [f for f in files if isinstance(f, str) and f.strip()]))
    return suites, problems


def suite_of(path, suites):
    """The first suite whose globs match `path`, or None."""
    for suite in suites or ():
        if suite.matches(path):
            return suite
    return None


# ---------------------------------------------------------------------------
# Globs
# ---------------------------------------------------------------------------

_GLOB_CACHE = {}


def glob_match(path, pattern):
    """True when the `/` relative `path` matches the glob `pattern`.

    `*`, `?` and `[...]` match within one path segment, and `**` matches any
    number of segments, none included. A pattern with no `/` matches a file
    of that name in any directory, as a `.gitignore` line does.
    """
    path = path.replace('\\', '/').lstrip('/')
    pattern = pattern.replace('\\', '/').strip().lstrip('/')
    if pattern.startswith('./'):
        pattern = pattern[2:]
    if '/' not in pattern:
        pattern = '**/' + pattern
    compiled = _GLOB_CACHE.get(pattern)
    if compiled is None:
        compiled = re.compile(_glob_regex(pattern))
        _GLOB_CACHE[pattern] = compiled
    return compiled.match(path) is not None


def _glob_regex(pattern):
    parts = pattern.split('/')
    out = ''
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if part == '**':
            out += '(?:.*/)?' if not last else '.*'
            continue
        out += _segment_regex(part) + ('' if last else '/')
    return '^' + out + '$'


def _segment_regex(part):
    """One path segment of a glob as a regex that never crosses a `/`."""
    out = []
    index = 0
    while index < len(part):
        char = part[index]
        if char == '*':
            out.append('[^/]*')
        elif char == '?':
            out.append('[^/]')
        elif char == '[':
            close = part.find(']', index + 1)
            if close < 0:
                out.append(re.escape(char))
            else:
                body = part[index + 1:close]
                if body.startswith('!'):
                    body = '^' + body[1:]
                out.append('[%s]' % body.replace('\\', '\\\\'))
                index = close
        else:
            out.append(re.escape(char))
        index += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

def parse_comment(line):
    """`(feature, id)` for a marker line, else None."""
    found = _COMMENT_RE.match(line)
    if not found:
        return None
    body = _BODY_RE.match(found.group('rest'))
    if not body:
        return None
    return body.group('feature'), body.group('id')


def _python_comment_lines(text):
    """`[(line number, text)]` for each whole-line comment, read by the tokenizer."""
    lines = text.splitlines()
    out = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.COMMENT:
                continue
            row, col = token.start
            before = lines[row - 1][:col] if row - 1 < len(lines) else ''
            if before.strip():
                continue
            out.append((row, token.string))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    return out


_HEREDOC_RE = re.compile(r"""<<(-?)\s*(['"]?)([A-Za-z_]\w*)\2""")


def _shell_lines(text):
    """`[(line number, text)]` for every line outside a here document."""
    out = []
    ending = []
    for number, line in enumerate(text.splitlines(), 1):
        if ending:
            delimiter, strip = ending[0]
            if (line.lstrip('\t') if strip else line) == delimiter:
                ending.pop(0)
            continue
        out.append((number, line))
        for found in _HEREDOC_RE.finditer(line):
            ending.append((found.group(3), bool(found.group(1))))
    return out


def comment_lines(text, ext):
    """`[(line number, text)]` for the lines of one file a marker may sit on.

    A Python file's whole-line comments, as the tokenizer reads them; a
    shell file's lines outside its here documents; every line of any other.
    """
    if ext in _PY_EXTENSIONS:
        lines = _python_comment_lines(text)
        if lines is not None:
            return lines
    elif ext in _SHELL_EXTENSIONS:
        return _shell_lines(text)
    return list(enumerate(text.splitlines(), 1))


def comment_markers(text, ext):
    """The markers in one file's text, in line order."""
    markers = []
    for number, line in comment_lines(text, ext):
        if 'purlin:' not in line:
            continue
        parsed = parse_comment(line)
        if parsed is not None:
            markers.append(Marker(parsed[0], parsed[1], number))
    return markers


# ---------------------------------------------------------------------------
# Stepping over strings and comments
# ---------------------------------------------------------------------------

def read_string(text, index):
    """`text[index]` is a quote (`"`, `'` or a backtick). `(inner text, index after it)`."""
    quote = text[index]
    size = len(text)
    position = index + 1
    parts = []
    while position < size:
        char = text[position]
        if char == '\\':
            parts.append(text[position:position + 2])
            position += 2
        elif quote == '`' and char == '$' and text[position + 1:position + 2] == '{':
            end = _balanced_literal(text, position + 1)
            parts.append(text[position:end])
            position = end
        elif char == quote:
            return ''.join(parts), position + 1
        elif char == '\n' and quote != '`':
            return ''.join(parts), position
        else:
            parts.append(char)
            position += 1
    return ''.join(parts), position


def _balanced_literal(text, index):
    """The offset after the `}` closing the `${` at `index`, strings stepped over."""
    depth = 0
    size = len(text)
    position = index
    while position < size:
        after = skip_noncode(text, position)
        if after is not None:
            position = after
            continue
        if text[position] == '{':
            depth += 1
        elif text[position] == '}':
            depth -= 1
            if depth == 0:
                return position + 1
        position += 1
    return size


def _regex_allowed(text, index):
    """True when a `/` at `index` starts a regex literal rather than a division."""
    before = index - 1
    while before >= 0 and text[before] in ' \t\r\n':
        before -= 1
    return before < 0 or not (text[before].isalnum() or text[before] in '_)]}$')


def _skip_regex(text, index):
    size = len(text)
    position = index + 1
    in_class = False
    while position < size:
        char = text[position]
        if char == '\\':
            position += 2
            continue
        if char == '[':
            in_class = True
        elif char == ']':
            in_class = False
        elif char == '\n':
            return index + 1
        elif char == '/' and not in_class:
            position += 1
            while position < size and text[position].isalpha():
                position += 1
            return position
        position += 1
    return position


def skip_noncode(text, index):
    """The offset past the string, comment or regex literal at `index`, else None.

    JavaScript and TypeScript's rules, which also serve Go: a backtick string
    there is a raw string, and a rune literal reads as a one-character string.
    """
    char = text[index]
    size = len(text)
    if char in '"\'`':
        return read_string(text, index)[1]
    if char == '/' and text[index + 1:index + 2] == '/':
        newline = text.find('\n', index)
        return size if newline < 0 else newline
    if char == '/' and text[index + 1:index + 2] == '*':
        end = text.find('*/', index + 2)
        return size if end < 0 else end + 2
    if char == '/' and _regex_allowed(text, index):
        return _skip_regex(text, index)
    return None


def skip_csharp_noncode(text, index):
    """The offset past the comment, string or character literal at `index`, else None."""
    size = len(text)
    char = text[index]
    if text.startswith('//', index):
        newline = text.find('\n', index)
        return size if newline < 0 else newline
    if char == '/' and text[index + 1:index + 2] == '*':
        end = text.find('*/', index + 2)
        return size if end < 0 else end + 2
    if char == '@' and text[index + 1:index + 2] == '"':
        position = index + 2
        while position < size:
            if text[position] == '"':
                if text[position + 1:position + 2] != '"':
                    return position + 1
                position += 1
            position += 1
        return size
    if char in '"\'':
        position = index + 1
        while position < size:
            if text[position] == '\\':
                position += 2
                continue
            if text[position] == char:
                return position + 1
            if text[position] == '\n':
                return position
            position += 1
        return size
    return None


# ---------------------------------------------------------------------------
# Test declarations
# ---------------------------------------------------------------------------

def _line_of(text, offset):
    return text.count('\n', 0, offset) + 1


def python_tests(text):
    """Every test a Python file declares, in line order, or None when it does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    tests = []

    def visit(body, scopes):
        for node in body:
            if isinstance(node, ast.ClassDef):
                visit(node.body, scopes + [node.name])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith('test'):
                    start = min([node.lineno] + [d.lineno for d in
                                                 node.decorator_list])
                    tests.append(Test(node.name, node.lineno, scopes,
                                      start=start,
                                      end=getattr(node, 'end_lineno', None)))
    visit(tree.body, [])
    tests.sort(key=lambda test: test.line)
    return tests


def _mask(text, skipper):
    """`text` with every string, comment and regex literal blanked, newlines kept."""
    out = list(text)
    index = 0
    size = len(text)
    while index < size:
        after = skipper(text, index)
        if after is None:
            index += 1
            continue
        for position in range(index, min(after, size)):
            if out[position] != '\n':
                out[position] = ' '
        index = max(after, index + 1)
    return ''.join(out)


def _balanced(mask, index, opener, closer):
    """The offset after the `closer` matching the `opener` at `index`."""
    depth = 0
    size = len(mask)
    position = index
    while position < size:
        char = mask[position]
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return position + 1
        position += 1
    return size


# JavaScript and TypeScript -------------------------------------------------


_JS_CALL_RE = re.compile(
    r'(?<![\w$.])(describe|it|test)((?:\s*\.\s*[A-Za-z_]\w*)*)\s*\(')
_EACH_PLACEHOLDER_RE = re.compile(
    r'%[sdifjoOpc#%]|\$\{[^}]*\}|\$[A-Za-z_][\w.]*')


def _each_pattern(title):
    """A regex matching the titles a table test prints for `title`."""
    parts = []
    position = 0
    for found in _EACH_PLACEHOLDER_RE.finditer(title):
        parts.append(re.escape(title[position:found.start()]))
        parts.append('%' if found.group(0) == '%%' else '.*?')
        position = found.end()
    parts.append(re.escape(title[position:]))
    return re.compile('^' + ''.join(parts) + '$')


def js_tests(text):
    """Every `it` and `test` a JavaScript or TypeScript file declares, in order."""
    mask = _mask(text, skip_noncode)
    calls = []
    for found in _JS_CALL_RE.finditer(mask):
        kind, modifiers = found.group(1), found.group(2)
        open_paren = found.end() - 1
        table = '.each' in modifiers.replace(' ', '')
        title_at = found.end()
        if table:
            # `it.each(table)(title, fn)`: the title is in the second call.
            after = _balanced(mask, open_paren, '(', ')')
            rest = mask[after:]
            stripped = len(rest) - len(rest.lstrip())
            if not rest.lstrip().startswith('('):
                continue
            open_paren = after + stripped
            title_at = open_paren + 1
        while title_at < len(text) and text[title_at] in ' \t\r\n':
            title_at += 1
        if title_at >= len(text) or text[title_at] not in '"\'`':
            continue
        title, _after = read_string(text, title_at)
        end = _balanced(mask, open_paren, '(', ')')
        calls.append((kind, title, found.start(), end, table))
    describes = [(title, start, end) for kind, title, start, end, _t in calls
                 if kind == 'describe']
    tests = []
    for kind, title, start, end, table in calls:
        if kind == 'describe':
            continue
        scopes = [name for name, d_start, d_end in describes
                  if d_start < start < d_end]
        pattern = _each_pattern(title) if table else None
        tests.append(Test(title, _line_of(text, start), scopes, pattern,
                          start, end))
    tests.sort(key=lambda test: test.line)
    return tests


# C# ------------------------------------------------------------------------


_CS_ATTRIBUTE_RE = re.compile(
    r'\[\s*(?:[\w.]+\.)?(?:Fact|Theory|Test|TestCase|TestCaseSource|'
    r'TestMethod|DataTestMethod|SkippableFact|SkippableTheory)'
    r'(?:Attribute)?\s*(?:\(|\]|,)')
_CS_TYPE_RE = re.compile(r'\b(?:class|struct|record)\s+([A-Za-z_]\w*)')
_CS_NAMESPACE_RE = re.compile(r'\bnamespace\s+([\w.]+)\s*([;{])')
_CS_NAME_RE = re.compile(r'([A-Za-z_]\w*)\s*(?:<[^<>()]*>)?\s*\($')


def cs_tests(text):
    """Every test method a C# file declares, in order."""
    mask = _mask(text, skip_csharp_noncode)
    types = []
    for found in _CS_TYPE_RE.finditer(mask):
        brace = mask.find('{', found.end())
        semi = mask.find(';', found.end())
        if brace < 0 or (0 <= semi < brace):
            continue
        types.append((found.group(1), found.start(),
                      _balanced(mask, brace, '{', '}')))
    namespaces = []
    for found in _CS_NAMESPACE_RE.finditer(mask):
        if found.group(2) == ';':
            namespaces.append((found.group(1), found.start(), len(mask)))
        else:
            namespaces.append((found.group(1), found.start(),
                               _balanced(mask, found.end() - 1, '{', '}')))
    tests = []
    seen = set()
    for found in _CS_ATTRIBUTE_RE.finditer(mask):
        position = found.start()
        # Step over this and any further attributes to the method's name.
        name = None
        name_at = None
        index = position
        size = len(mask)
        while index < size:
            char = mask[index]
            if char == '[':
                index = _balanced(mask, index, '[', ']')
                continue
            if char == '(':
                named = _CS_NAME_RE.search(mask[:index + 1])
                if named:
                    name = named.group(1)
                    name_at = named.start(1)
                break
            if char in '{};=':
                break
            index += 1
        if not name or name_at in seen:
            continue
        seen.add(name_at)
        scopes = [type_name for type_name, t_start, t_end in types
                  if t_start < name_at < t_end]
        space = [space for space, s_start, s_end in namespaces
                 if s_start < name_at < s_end]
        brace = mask.find('{', name_at)
        arrow = mask.find('=>', name_at)
        end = None
        if brace >= 0 and (arrow < 0 or brace < arrow):
            end = _balanced(mask, brace, '{', '}')
        tests.append(Test(name, _line_of(text, name_at), scopes, start=position,
                          end=end, namespace='.'.join(space)))
    tests.sort(key=lambda test: test.line)
    return tests


# Go ------------------------------------------------------------------------

_GO_TEST_RE = re.compile(
    r'^func\s+(Test[A-Za-z0-9_]*)\s*\(\s*\w+\s+\*testing\.T\s*\)', re.M)


def go_tests(text):
    """Every `func TestX(t *testing.T)` a Go file declares, in order."""
    mask = _mask(text, skip_noncode)
    tests = []
    for found in _GO_TEST_RE.finditer(mask):
        brace = mask.find('{', found.end())
        end = _balanced(mask, brace, '{', '}') if brace >= 0 else None
        tests.append(Test(found.group(1), _line_of(text, found.start()),
                          start=found.start(), end=end))
    return tests


def declared_tests(text, ext):
    """The tests a file declares, or None when its language has no reader."""
    if ext in _PY_EXTENSIONS:
        return python_tests(text)
    if ext in _JS_EXTENSIONS:
        return js_tests(text)
    if ext in _CS_EXTENSIONS:
        return cs_tests(text)
    if ext in _GO_EXTENSIONS:
        return go_tests(text)
    return None


# ---------------------------------------------------------------------------
# One file
# ---------------------------------------------------------------------------

def read_text(path, text, fmt):
    """`FileMarkers` for `text`, the content of `path`."""
    result = FileMarkers(path, fmt)
    ext = os.path.splitext(path)[1].lower()
    result.markers = comment_markers(text, ext)
    if fmt == 'exit':
        return result
    tests = declared_tests(text, ext) if result.markers else []
    result.tests = tests or []
    tie_markers(result)
    return result


def test_name(path, test):
    """The name the evidence gives a test: the file's own spelling of it.

    `Class::test_x` for Python, `outer > inner > title` for JavaScript and
    TypeScript, `Class.Method` for C#, `TestX` for Go, and the file's own
    name for a file that is one test.
    """
    if test is None:
        return path.rsplit('/', 1)[-1]
    if path.endswith('.py'):
        return test.qualified('::')
    if path.endswith('.cs'):
        return test.qualified('.')
    if path.endswith('.go'):
        return test.name
    return test.qualified(' > ')


def tie_markers(result):
    """Tie each marker to the next test declared after it; the rest are untied."""
    tests = sorted(result.tests, key=lambda test: test.line)
    for marker in result.markers:
        owner = None
        for test in tests:
            if test.line > marker.line:
                owner = test
                break
        if owner is None:
            result.untied.append(marker)
        else:
            owner.markers.append(marker)


# ---------------------------------------------------------------------------
# The project
# ---------------------------------------------------------------------------

def _skipped_dir(name):
    return name.startswith('.') or name in SKIP_DIRS


def _walk(project_root):
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = sorted(d for d in dirnames if not _skipped_dir(d))
        for name in sorted(filenames):
            yield os.path.relpath(os.path.join(dirpath, name),
                                  project_root).replace(os.sep, '/')


def _tracked(project_root):
    try:
        done = subprocess.run(['git', 'ls-files', '-z'], capture_output=True,
                              cwd=project_root, timeout=60)
    except (subprocess.SubprocessError, OSError):
        return None
    if done.returncode != 0:
        return None
    text = done.stdout.decode('utf-8', 'replace')
    return sorted(part for part in text.split('\0') if part
                  and not any(_skipped_dir(segment)
                              for segment in part.split('/')[:-1]))


def test_files(project_root, suites, tracked_only=False):
    """`{path: suite}` for every file a suite's globs match, sorted by path.

    From the disk, tracked or not, so a new test runs before anyone added it;
    `tracked_only` reads git's list instead, which is what the fingerprint
    hashes. A file two suites match belongs to the first.
    """
    if not suites:
        return {}
    paths = _tracked(project_root) if tracked_only else None
    if paths is None:
        paths = list(_walk(project_root))
        if tracked_only:
            paths = []
    out = {}
    for path in paths:
        suite = suite_of(path, suites)
        if suite is not None:
            out[path] = suite
    return out


def scan(project_root, suites=None, tracked_only=False):
    """`{path: FileMarkers}` for every test file that carries a marker."""
    if suites is None:
        suites = read_suites(project_root)[0]
    out = {}
    for path, suite in test_files(project_root, suites, tracked_only).items():
        full = os.path.join(project_root, *path.split('/'))
        if tracked_only and not os.path.isfile(full):
            continue
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if 'purlin:' not in text:
            continue
        found = read_text(path, text, suite.format)
        if found.markers:
            out[path] = found
    return out


def tied_ids(project_root, found=None):
    """`{(feature, id)}` for every marker tied to a test declaration.

    Read from the test files as they are on disk, so a proof whose marked
    test exists has a test whether or not anything has run it yet. A marker
    no test follows ties nothing. `found` is `scan`'s answer where the caller
    already has one.
    """
    if found is None:
        found = scan(project_root)
    tied = set()
    for markers in found.values():
        loose = set(id(marker) for marker in markers.untied)
        for marker in markers.markers:
            if id(marker) not in loose:
                tied.add((marker.feature, marker.id))
    return tied


def marker_index(project_root):
    """`{feature: [paths]}` for every tracked test file carrying a marker of it."""
    index = {}
    for path, found in scan(project_root, tracked_only=True).items():
        for feature in found.features():
            index.setdefault(feature, set()).add(path)
    return {name: sorted(paths) for name, paths in index.items()}


# ---------------------------------------------------------------------------
# Comments that name nothing
# ---------------------------------------------------------------------------

# A marker naming a feature, a proof or a rule no spec has fails the run, and
# its line says what to do.
NAMES_NOTHING = ('%s:%d names %s %s, which no spec has. Correct the comment, '
                 'or run purlin:build to repair it.')
RULE_HAS_PROOFS = ('purlin: %s %s at %s:%d names a rule that has proofs; '
                   'name one of them')


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
            known = ({} if info is None else
                     (info.get('proofs') if marker.id.startswith('PROOF-')
                      else info.get('rules')) or {})
            if marker.id not in known:
                lines.append(NAMES_NOTHING % (path, marker.line,
                                              marker.feature, marker.id))
            elif (not marker.id.startswith('PROOF-')
                  and (info.get('proofs_by_rule') or {}).get(marker.id)):
                lines.append(RULE_HAS_PROOFS % (marker.feature, marker.id,
                                                path, marker.line))
    return lines


# ---------------------------------------------------------------------------
# Comments that are nearly a marker
# ---------------------------------------------------------------------------

# A comment whose first word, followed by a colon, may be `purlin` misspelled.
_LOOSE_RE = re.compile(
    r"""^(?P<lead>\s*(?:\#|//|--|;|%|'|/\*|<!--)\s*)"""
    r"""(?P<word>[A-Za-z0-9]{5,7}):(?P<gap>\s*)(?P<rest>.*?)"""
    r"""(?P<tail>\s*(?:\*/|-->)?\s*)$""")
# What follows the colon, with an id of any spelling.
_LOOSE_BODY_RE = re.compile(r'^(?P<feature>\w+)\s+(?P<kind>[A-Za-z]+)-'
                            r'(?P<number>\d+)$')
_KINDS = ('PROOF', 'RULE')

# Why a `purlin:` comment that cannot be read is a near miss.
UNREADABLE = ('the comment names no `<feature> PROOF-<n>` or '
              '`<feature> RULE-<n>`')

NEAR_MISSES_USAGE = ('Usage: markers.py --near-misses '
                     '[--project-root DIR]')


def one_edit(one, other):
    """True when changing, adding or removing one character makes `other`."""
    if one == other or abs(len(one) - len(other)) > 1:
        return False
    if len(one) == len(other):
        return sum(a != b for a, b in zip(one, other)) == 1
    short, long_ = (one, other) if len(one) < len(other) else (other, one)
    for index in range(len(long_)):
        if long_[:index] + long_[index + 1:] == short:
            return True
    return False


def _only(candidates):
    """The one candidate, or None when there are none or several."""
    return candidates[0] if len(candidates) == 1 else None


def near_miss(line, features):
    """`(fix, why)` for a comment that is nearly a marker, else None.

    `features` is `specs.scan_specs`' answer. `fix` is the line as it should
    read, or None where the comment cannot be read; `why` is one sentence.
    An id one character from a rule offers the rule where it has no proof,
    its proof where it has one, and nothing where it has two or more.
    """
    found = _LOOSE_RE.match(line)
    if not found:
        return None
    word = found.group('word')
    if word != 'purlin' and not one_edit(word.lower(), 'purlin') \
            and word.lower() != 'purlin':
        return None
    why = []
    if word.lower() == 'purlin' and word != 'purlin':
        why.append('`%s` is `purlin` in capitals' % word)
    elif word != 'purlin':
        why.append('`%s` is one letter from `purlin`' % word)
    if not found.group('gap'):
        why.append('there is no space after the colon')
    body = _LOOSE_BODY_RE.match(found.group('rest'))
    kind = body.group('kind') if body else ''
    fixed = kind.upper() if kind.upper() in _KINDS else _only(
        [name for name in _KINDS if one_edit(kind.upper(), name)])
    if fixed is None:
        why.append(UNREADABLE)
        return None, _sentence(why)
    if kind.upper() != fixed:
        why.append('`%s` is one character from `%s`' % (kind, fixed))
    elif kind != fixed:
        why.append('`%s` is `%s` in lower case' % (kind, fixed))
    kind = fixed
    feature = body.group('feature')
    if feature not in features:
        fixed = _only(sorted(name for name in features
                             if one_edit(feature, name)))
        if fixed is not None:
            why.append('`%s` is one character from the feature `%s`'
                       % (feature, fixed))
            feature = fixed
    marker_id = '%s-%s' % (kind, body.group('number'))
    info = features.get(feature)
    if info is not None:
        known = set(info.get('proofs') or {}) | set(info.get('rules') or {})
        if marker_id not in known:
            fixed = _only(sorted(name for name in known
                                 if one_edit(marker_id, name)))
            proofs = [] if fixed is None or fixed.startswith('PROOF-') else \
                list((info.get('proofs_by_rule') or {}).get(fixed) or ())
            if fixed is not None and len(proofs) < 2:
                # A comment may name a proof, or a rule that has none; a
                # rule with one proof is named by that proof.
                reason = ('`%s` is one character from `%s`, which %s has'
                          % (marker_id, fixed, feature))
                if proofs:
                    reason += '; a comment names its one proof, `%s`' % (
                        proofs[0])
                    fixed = proofs[0]
                why.append(reason)
                marker_id = fixed
    if not why:
        return None
    fix = '%spurlin: %s %s%s' % (found.group('lead'), feature, marker_id,
                                 found.group('tail'))
    return fix.strip(), _sentence(why)


def _sentence(parts):
    """The reasons as one sentence: joined, the first letter raised, a stop."""
    text = '; '.join(parts)
    return text[:1].upper() + text[1:] + '.'


def near_misses(project_root, features, suites=None):
    """`[{file, line, text, fix, why}]`, one per comment nearly a marker.

    Only a file one suite's globs match is read, as for a marker, in path
    and line order.
    """
    if suites is None:
        suites = read_suites(project_root)[0]
    out = []
    for path in test_files(project_root, suites):
        full = os.path.join(project_root, *path.split('/'))
        try:
            with open(full, 'r', encoding='utf-8') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if ':' not in text:
            continue
        ext = os.path.splitext(path)[1].lower()
        for number, line in comment_lines(text, ext):
            if ':' not in line:
                continue
            miss = near_miss(line, features)
            if miss is None:
                continue
            out.append({'file': path, 'line': number, 'text': line.strip(),
                        'fix': miss[0], 'why': miss[1]})
    return out


def main(argv):
    """`--near-misses [--project-root DIR]`: print the near misses as JSON."""
    root = '.'
    args = list(argv)
    if '--near-misses' not in args:
        args = None
    else:
        args.remove('--near-misses')
        if args[:1] == ['--project-root'] and len(args) == 2 \
                and args[1].strip():
            root = args[1]
            args = []
    if args is None or args or not os.path.isdir(root):
        print(NEAR_MISSES_USAGE, file=sys.stderr)
        return 2
    from purlin import specs as specs_module
    features = specs_module.scan_specs(root)
    print(json.dumps(near_misses(root, features)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
