"""The source of the test that backs a proof, read out of its file.

The AI audit sets a proof against the test that backs it, so the brief needs
that test's own source. This module finds it: it reads the proof marker each
shipped plugin writes, locates the marked test, and returns its source text.
It judges nothing about the test.

The extension table below decides which reader opens a file: Python through
the abstract syntax tree, JavaScript and TypeScript and C# by balancing braces
while stepping over strings, comments and regex literals, and SQL from one
marker to the next. Shell has no reader: a shell proof is one line inside a
script and has no body of its own.
"""

import ast
import os
import re

# --- Markers, as each shipped proof plugin writes them ---------------------

_PROOF_MARKER_RE = re.compile(
    r'pytest\.mark\.proof\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,'
    r'\s*["\']([^"\']+)["\']')

# --- Python (the abstract syntax tree) ------------------------------------
# ast.get_source_segment re-splits the whole file on every call, so the file is
# split once here and every segment is sliced from it. `_split_source_lines`
# and `_segment` replicate the standard library byte for byte.

_SOURCE_LINE_RE = re.compile(r'[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+')

def _split_source_lines(source):
    """The lines of `source` as ast.get_source_segment splits them, ends kept."""
    splitter = getattr(ast, '_splitlines_no_ff', None)
    return splitter(source) if splitter else _SOURCE_LINE_RE.findall(source)

def _segment(lines, node):
    """`node`'s source, sliced from one split; None when it has no end position."""
    end_lineno = getattr(node, 'end_lineno', None)
    end_col = getattr(node, 'end_col_offset', None)
    if end_lineno is None or end_col is None:
        return None
    lineno, end, col = node.lineno - 1, end_lineno - 1, node.col_offset
    if end == lineno:
        return lines[lineno].encode()[col:end_col].decode()
    first = lines[lineno].encode()[col:].decode()
    last = lines[end].encode()[:end_col].decode()
    return ''.join([first] + lines[lineno + 1:end] + [last])

def _python_proof_functions(source):
    """(entries, lines): one (feature, proof, rule, test name, node) per marker."""
    tree = ast.parse(source)
    lines = _split_source_lines(source)
    entries = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test_'):
            continue
        for deco in node.decorator_list:
            m = _PROOF_MARKER_RE.search(_segment(lines, deco) or '')
            if m:
                entries.append((m.group(1), m.group(2), m.group(3), node.name, node))
    return entries, lines


# --- JavaScript and TypeScript (brace-balancing reader) --------------------
# A flat regex cannot bound a JS/TS test: lazy `\}\s*\)` truncates at the first
# inner `}` and a `[^"']*` title class drops titles with apostrophes. These
# helpers character-walk the source, tracking literals and comments.

def _read_js_string(content, i):
    """content[i] is a quote (" ' `). (inner text, index after the close)."""
    quote = content[i]
    n = len(content)
    j = i + 1
    parts = []
    while j < n:
        c = content[j]
        if c == '\\':
            parts.append(content[j:j + 2])
            j += 2
        elif quote == '`' and c == '$' and content[j + 1:j + 2] == '{':
            _, j = _read_balanced(content, j + 1)  # balanced ${ ... }
        elif c == quote:
            return ''.join(parts), j + 1
        else:
            parts.append(c)
            j += 1
    return ''.join(parts), j  # unterminated — return what we have

def _regex_allowed(content, j):
    """Does a `/` at index j begin a regex literal rather than a division?"""
    k = j - 1
    while k >= 0 and content[k] in ' \t\r\n':
        k -= 1
    return k < 0 or not (content[k].isalnum() or content[k] in '_)]}')

def _skip_regex(content, j):
    """content[j] is the `/` of a regex literal. The index after it."""
    n = len(content)
    k = j + 1
    in_class = False
    while k < n:
        c = content[k]
        if c == '\\':
            k += 2
            continue
        if c == '[':
            in_class = True
        elif c == ']':
            in_class = False
        elif c == '\n':
            return j + 1  # a newline inside a "regex": it was division
        elif c == '/' and not in_class:
            k += 1
            while k < n and content[k].isalpha():  # trailing flags (gimsuy)
                k += 1
            return k
        k += 1
    return k

def _skip_js_noncode(content, i):
    """Index past the string, comment or regex literal at content[i], else None."""
    c = content[i]
    n = len(content)
    if c in '"\'`':
        return _read_js_string(content, i)[1]
    if c == '/' and content[i + 1:i + 2] == '/':
        nl = content.find('\n', i)
        return n if nl < 0 else nl
    if c == '/' and content[i + 1:i + 2] == '*':
        e = content.find('*/', i + 2)
        return n if e < 0 else e + 2
    if c == '/' and _regex_allowed(content, i):
        return _skip_regex(content, i)
    return None

def _read_balanced(content, i):
    """content[i] is one of { ( [. (inner text, index after the matching close)."""
    opener = content[i]
    closer = {'{': '}', '(': ')', '[': ']'}[opener]
    n = len(content)
    depth = 0
    j = i
    while j < n:
        skipped = _skip_js_noncode(content, j)
        if skipped is not None:
            j = skipped
            continue
        if content[j] == opener:
            depth += 1
        elif content[j] == closer:
            depth -= 1
            if depth == 0:
                return content[i + 1:j], j + 1
        j += 1
    return content[i + 1:j], j  # unterminated

def _find_test_body(content, i):
    """From just after a test title, (body, index after it) for the callback."""
    n = len(content)
    saw_callback = False  # saw `=>` or `function`: the next `{` is the body
    while i < n:
        skipped = _skip_js_noncode(content, i)
        if skipped is not None:
            i = skipped
            continue
        c = content[i]
        if content.startswith('=>', i):
            saw_callback = True
            i += 2
            continue
        if content.startswith('function', i):
            before = content[i - 1] if i > 0 else ' '
            after = content[i + 8] if i + 8 < n else ' '
            if not (before.isalnum() or before == '_') \
                    and not (after.isalnum() or after == '_'):
                saw_callback = True
                i += 8
                continue
        if c == '{' and saw_callback:
            return _read_balanced(content, i)
        if c in '{([':
            _, i = _read_balanced(content, i)  # options object, params, array
            continue
        if c in ');':
            return None, i  # the it(...) call ended with no block body
        i += 1
    return None, i

def _iter_js_proof_bodies(content, feature_name):
    """(proof_id, rule_id, title, body) for every marked test in a JS/TS file."""
    call_re = re.compile(r'\b(?:it|test)\s*\(')
    marker_re = re.compile(
        r'\[proof:' + re.escape(feature_name) + r':([^:\]]+):([^:\]]+)')
    n = len(content)
    i = 0
    while i < n:
        m = call_re.search(content, i)
        if not m:
            return
        j = m.end()
        while j < n and content[j] in ' \t\r\n':
            j += 1
        if j >= n or content[j] not in '"\'`':  # a title that is not a literal
            i = m.end()
            continue
        title, after_title = _read_js_string(content, j)
        marker = marker_re.search(title)
        if not marker:
            i = after_title
            continue
        body, after_body = _find_test_body(content, after_title)
        if body is None:  # no block body to inspect
            i = after_title
            continue
        i = after_body
        yield marker.group(1), marker.group(2), title, body


# --- C# / .NET (xUnit, NUnit, MSTest) ---------------------------------------

def _skip_csharp_noncode(content, j):
    """Index past the comment, string or char literal at content[j], else None."""
    n = len(content)
    c = content[j]
    if content.startswith('//', j):
        nl = content.find('\n', j)
        return n if nl < 0 else nl
    if c == '/' and content[j + 1:j + 2] == '*':
        e = content.find('*/', j + 2)
        return n if e < 0 else e + 2
    if c == '@' and content[j + 1:j + 2] == '"':
        j += 2
        while j < n:
            if content[j] == '"':
                if content[j + 1:j + 2] != '"':
                    return j + 1
                j += 1
            j += 1
        return n
    if c in '"\'':  # string, interpolated string, or char literal
        quote = c
        j += 1
        while j < n:
            if content[j] == '\\':
                j += 2
                continue
            if content[j] == quote:
                return j + 1
            j += 1
        return n
    return None

def _read_csharp_balanced(content, i, opener, closer):
    """content[i] is `opener`. (inner text, index after the matching close)."""
    n = len(content)
    depth = 0
    j = i
    while j < n:
        skipped = _skip_csharp_noncode(content, j)
        if skipped is not None:
            j = skipped
            continue
        if content[j] == opener:
            depth += 1
        elif content[j] == closer:
            depth -= 1
            if depth == 0:
                return content[i + 1:j], j + 1
        j += 1
    return content[i + 1:j], j  # unterminated

def _find_csharp_body(content, i):
    """From just after a `[Trait(...)]` marker, (body, index after it, name)."""
    n = len(content)
    method_name = None
    while i < n:
        skipped = _skip_csharp_noncode(content, i)
        if skipped is not None:
            i = skipped
            continue
        c = content[i]
        if c == '[':  # another attribute, or an array
            _, i = _read_csharp_balanced(content, i, '[', ']')
            continue
        if c == '(':  # the identifier before this paren is the method name
            named = re.search(r'([A-Za-z_]\w*)\s*$', content[:i])
            method_name = (named.group(1) if named else None) or method_name
            _, i = _read_csharp_balanced(content, i, '(', ')')
            continue
        if content.startswith('=>', i) or c == ';':
            return None, i, method_name
        if c == '{':
            body, after = _read_csharp_balanced(content, i, '{', '}')
            return body, after, method_name
        i += 1
    return None, i, method_name

def _iter_csharp_proof_bodies(content, feature_name):
    """(proof_id, rule_id, test_name, body) for every marked C# test method."""
    marker_re = re.compile(
        r'\[\s*Trait\s*\(\s*"PurlinProof"\s*,\s*"' + re.escape(feature_name)
        + r':([^:"\]]+):([^:"\]]+):[^"]*"\s*\)\s*\]')
    for m in marker_re.finditer(content):
        body, _after, method_name = _find_csharp_body(content, m.end())
        if body is not None:  # expression-bodied and abstract members have none
            yield m.group(1), m.group(2), method_name or m.group(1), body


# --- SQL (sqlite3) ----------------------------------------------------------
# The same marker regex and block delimiting as `scripts/proof/sql_purlin.sh`: a
# block runs from its marker to the next marker or to the end of the file.

_SQL_MARKER_RE = re.compile(
    r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:[ \t]+(\w+))?', re.MULTILINE)
_SQL_TEST_NAME_RE = re.compile(r'^-- Test:\s*(.+)', re.MULTILINE)

def _iter_sql_proof_blocks(content, feature_name):
    """(proof_id, rule_id, test_name, block) for every marked SQL block."""
    markers = list(_SQL_MARKER_RE.finditer(content))
    for i, m in enumerate(markers):
        if m.group(1) != feature_name:
            continue
        end = markers[i + 1].start() if i + 1 < len(markers) else len(content)
        block = content[m.end():end].strip()
        named = _SQL_TEST_NAME_RE.search(block)
        yield (m.group(2), m.group(3),
               named.group(1).strip() if named else m.group(2), block)


# --- The extension table ---------------------------------------------------
# One table decides which reader opens a test file. There is no fallback, so an
# extension absent from it yields no source.

_JS_EXTENSIONS = frozenset({'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'})
EXTENSIONS = frozenset({'.py', '.cs', '.sql'} | _JS_EXTENSIONS)


def _file_text(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def _test_bodies(path, ext, feature):
    """{proof_id: [(test name, source), ...]} for `feature`'s marked tests at `path`.

    Every marked test is kept, in file order, because one proof may be backed by
    several tests and each of them has its own source.
    """
    try:
        content = _file_text(path)
    except OSError:
        content = ''
    if not content:
        return None
    bodies = {}
    if ext == '.py':
        try:
            entries, lines = _python_proof_functions(content)
        except SyntaxError:
            entries, lines = (), []
        for feat, pid, _rid, name, node in sorted(
                entries, key=lambda entry: entry[4].lineno):
            if feat == feature:
                bodies.setdefault(pid, []).append((name, _segment(lines, node)))
        return bodies
    iterator = {'.cs': _iter_csharp_proof_bodies,
                '.sql': _iter_sql_proof_blocks}.get(
                    ext, _iter_js_proof_bodies if ext in _JS_EXTENSIONS else None)
    if iterator is None:
        return None
    for pid, _rid, name, body in iterator(content, feature):
        bodies.setdefault(pid, []).append((name, body))
    return bodies


# A name a record carries holds what the runner added to the name in the source: a
# pytest parameter id, an xUnit theory's arguments, a class or namespace prefix,
# and in JS the proof marker the title holds.
_NAME_ARGS_RE = re.compile(r'(?:\[.*\]|\(.*\))\s*$')
_NAME_MARKER_RE = re.compile(r'\[proof:[^\]]*\]')

def _test_name_key(name):
    return ' '.join(_NAME_MARKER_RE.sub(' ', name or '').split())

def name_matches(test_name, names):
    """The indexes in `names` that are the test a proof file names as `test_name`.

    An exact name wins, then the name without its arguments, then a name the
    written one ends with after a class, namespace or describe prefix. Empty
    when none is that test.
    """
    wanted = _test_name_key(test_name)
    bare = _NAME_ARGS_RE.sub('', wanted).strip()
    keys = [_test_name_key(name) for name in names]
    for key in (wanted, bare):
        found = [i for i, name in enumerate(keys) if key and name == key]
        if found:
            return found
    return [i for i, name in enumerate(keys)
            if name and any(bare.endswith(sep + name) for sep in ('::', '.', ' '))]

def _pick_test_body(candidates, test_name):
    """The source in `candidates` whose name is `test_name`, or None.

    With no name asked for, the first. A name that matches nothing still finds
    the one test when the proof has only one in the file; among several it finds
    none, because showing another test's source under this name misleads.
    """
    if not candidates:
        return None
    if test_name is None:
        return candidates[0][1]
    found = name_matches(test_name, [name for name, _body in candidates])
    if found:
        return candidates[found[0]][1]
    return candidates[0][1] if len(candidates) == 1 else None


def source(project_root, feature, proof_id, test_file, test_name=None):
    """The source of the test named `test_name` backing `proof_id`, or None."""
    ext = os.path.splitext(test_file or '')[1].lower()
    if not test_file or ext not in EXTENSIONS:
        return None
    path = os.path.join(project_root, *test_file.split('/'))
    if not os.path.isfile(path):
        return None
    bodies = _test_bodies(path, ext, feature)
    return _pick_test_body((bodies or {}).get(proof_id), test_name)
