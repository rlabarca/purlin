#!/usr/bin/env python3
"""Free structural checks on test bodies — no model required.

Reads the proof markers a test file carries, locates each marked test's body, and
reports the defects that can be seen without running anything. The extension
table below decides which of the five checkers — Python, JavaScript/TypeScript,
shell, C#, SQL — reads a file. Findings use one vocabulary and no other names:
`tautology`, `assert_true_literal`, `no_assertion`, `bare_except`,
`logic_mirroring`, `mock_of_target`. `deterministic_sweep` runs the same checks
over a whole project, reading `.purlin/runtime/proofs/`, and writes nothing.

Usage (see `_USAGE` below — it is the single source for this list):
    static_checks.py <test_file> <feature> [--project-root <path>] [--json]
    static_checks.py --sweep [--project-root <path>] [--json]
    static_checks.py --help

Exit codes (RULE-7): 0 for any completed analysis — a detected defect is reported
as `status: "fail"`, never as a non-zero exit. Non-zero is reserved for real
errors: 2 for bad arguments, a missing file, or malformed input.
"""

import ast
import collections
import contextlib
import glob
import json
import os
import re
import sys

_MCP_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin.console import force_utf8_stdio                    # noqa: E402

try:
    import fcntl  # POSIX only — absent on Windows
    _HAS_FCNTL = True
except ImportError:  # Windows: msvcrt locking, imported where it is used
    _HAS_FCNTL = False

# --- Markers, as each shipped proof plugin writes them ---------------------

_PROOF_MARKER_RE = re.compile(
    r'pytest\.mark\.proof\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,'
    r'\s*["\']([^"\']+)["\']')
_SHELL_PROOF_RE = re.compile(
    r'purlin_proof\s+"([^"]+)"\s+"(PROOF-\d+)"\s+"(RULE-\d+)"\s+(pass|fail)')
_ASSERT_KEYWORDS = {'assert', 'assertEqual', 'assertNotEqual', 'assertTrue',
                    'assertFalse', 'assertIs', 'assertIsNot', 'assertIn',
                    'assertNotIn', 'assertRaises', 'assertAlmostEqual',
                    'assertGreater', 'assertLess', 'assertRegex'}

# --- Python checks (ast-based) ---------------------------------------------
# ast.get_source_segment re-splits the whole file on every call, which made
# marker discovery quadratic, so the file is split once here and every segment is
# sliced from it. `_split_source_lines` and `_segment` replicate the stdlib byte
# for byte, which static_checks PROOF-69 pins.

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

def _python_parse(path, content):
    """`_python_proof_functions(content)` for `path`, memoized per run scope."""
    cache = _RUN_CACHE
    if cache is not None and path in cache.py_parses:
        result = cache.py_parses[path]
    else:
        try:
            result = _python_proof_functions(content)
        except SyntaxError as exc:
            result = exc
        if cache is not None:
            cache.py_parses[path] = result
    if isinstance(result, SyntaxError):
        raise result
    return result

def _has_assertion(node):
    """True when the function body contains any assertion statement."""
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.Call):
            func = child.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else '')
            # `raises` covers pytest.raises, called or used as a context.
            if name in _ASSERT_KEYWORDS or name.startswith('assert') \
                    or name == 'raises':
                return True
    return False

def _is_always_true(node):
    """True for a constant True, a comparison of two constants, or `not False`."""
    if isinstance(node, ast.Constant) and node.value is True:
        return True
    if isinstance(node, ast.Compare) and len(node.ops) == 1 \
            and len(node.comparators) == 1:
        def _constant_or_upper(n):
            return (isinstance(n, ast.Constant)
                    or (isinstance(n, ast.Name) and n.id.isupper()))
        if _constant_or_upper(node.left) and _constant_or_upper(node.comparators[0]):
            return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return isinstance(node.operand, ast.Constant) and not node.operand.value
    return False

def _check_assert_true(node):
    """The finding for an always-true assertion, or None."""
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            test = child.test
            if isinstance(test, ast.Constant) and test.value is True:
                return 'assert_true_literal'
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                for operand in test.values:
                    if _is_always_true(operand):
                        return ('assert_true_literal'
                                if isinstance(operand, ast.Constant)
                                and operand.value is True else 'tautology')
            if isinstance(test, ast.Compare) and len(test.ops) == 1 \
                    and len(test.comparators) == 1:
                op, comp = test.ops[0], test.comparators[0]
                if isinstance(op, ast.IsNot) and isinstance(comp, ast.Constant) \
                        and comp.value is None:
                    return 'tautology'
                if isinstance(op, ast.GtE) and isinstance(comp, ast.Constant) \
                        and comp.value == 0 and isinstance(test.left, ast.Call) \
                        and isinstance(test.left.func, ast.Name) \
                        and test.left.func.id == 'len':
                    return 'tautology'
        if isinstance(child, ast.Call):  # self.assertTrue(True)
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr == 'assertTrue' \
                    and child.args and isinstance(child.args[0], ast.Constant) \
                    and child.args[0].value is True:
                return 'assert_true_literal'
    return None

def _check_bare_except(node):
    """True when `except: pass` or `except Exception: pass` swallows a failure."""
    for child in ast.walk(node):
        for handler in getattr(child, 'handlers', ()):
            catches_all = handler.type is None or (
                isinstance(handler.type, ast.Name) and handler.type.id == 'Exception')
            if catches_all and len(handler.body) == 1 \
                    and isinstance(handler.body[0], ast.Pass):
                return True
    return False

def _collect_call_names(node):
    """Every function-call base name within `node`."""
    return {c.func.id if isinstance(c.func, ast.Name) else c.func.attr
            for c in ast.walk(node) if isinstance(c, ast.Call)
            and isinstance(c.func, (ast.Name, ast.Attribute))}


# Calls that carry no logic of their own, so sharing one proves nothing.
_MIRROR_BENIGN = {'str', 'int', 'float', 'len', 'list', 'dict', 'set', 'tuple',
                  'type', 'repr', 'sorted'}

def _check_logic_mirroring(node):
    """True when the expected value is computed by the same call as the result."""
    assigns = {}
    for stmt in getattr(node, 'body', []):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    assigns[target.id] = _collect_call_names(stmt.value)
    for child in ast.walk(node):
        if not (isinstance(child, ast.Assert)
                and isinstance(child.test, ast.Compare)):
            continue
        calls = [assigns[part.id] if isinstance(part, ast.Name) and part.id in assigns
                 else _collect_call_names(part)
                 for part in [child.test.left] + child.test.comparators]
        for i in range(len(calls)):
            for j in range(i + 1, len(calls)):
                if (calls[i] & calls[j]) - _MIRROR_BENIGN:
                    return True
    return False


# Words too common in rule prose to identify what a mock targets.
_RULE_STOP_WORDS = {
    'the', 'and', 'or', 'is', 'are', 'must', 'should', 'will', 'with', 'for',
    'not', 'that', 'this', 'from', 'have', 'has', 'rule', 'test', 'all', 'any',
    'each', 'when', 'then', 'can', 'does', 'use', 'using', 'used', 'into',
    'returns', 'return', 'code', 'file', 'function', 'method', 'class'}

def _check_mock_of_target(node, lines, rule_desc):
    """True when a patch target names something the rule describes."""
    if not rule_desc:
        return False
    rule_words = set(re.findall(r'[a-z_]\w+', rule_desc.lower())) - _RULE_STOP_WORDS
    targets = []
    for deco in node.decorator_list:  # @patch("auth.bcrypt.checkpw")
        targets += re.findall(r'patch\(["\']([^"\']+)["\']',
                              _segment(lines, deco) or '')
    targets += re.findall(r'mock\.patch\(["\']([^"\']+)["\']',  # or in the body
                          _segment(lines, node) or '')
    return any({p.lower() for p in t.split('.')} & rule_words for t in targets)

def check_python(filepath, feature_name, rule_descs=None):
    """Run every Python check. Returns a list of proof result dicts."""
    rule_descs = rule_descs or {}
    entries, lines = _python_parse(filepath, _file_text(filepath))
    results = []
    for feature, proof_id, rule_id, test_name, node in entries:
        if feature != feature_name:
            continue
        found = next(((check, reason) for check, reason in (  # first is severest
            (_check_assert_true(node),
             'tautological assertion (assert True or equivalent)'),
            (not _has_assertion(node) and 'no_assertion',
             'test function has no assertion statements'),
            (_check_bare_except(node) and 'bare_except',
             'bare except:pass swallows failures'),
            (_check_logic_mirroring(node) and 'logic_mirroring',
             'expected value computed by same function as SUT'),
            (_check_mock_of_target(node, lines, rule_descs.get(rule_id, ''))
             and 'mock_of_target',
             'mock target matches the function the rule describes'),
        ) if check), None)
        base = {'proof_id': proof_id, 'rule_id': rule_id, 'test_name': test_name}
        results.append(dict(base, status='fail', check=found[0], reason=found[1])
                       if found else
                       dict(base, status='pass', reason='structural checks passed'))
    return results


# --- Shell checks (regex-based) --------------------------------------------
# A single `purlin_proof ... pass` needs test logic before it; an if/else pair
# recording the same proof id both ways has its logic in the if-condition.

_SHELL_LOGIC_RE = re.compile(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\|')
_SHELL_PAIR_LOGIC_RE = re.compile(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\||\bif\b')

def check_shell(filepath, feature_name, rule_descs=None):
    """Run shell test checks. Returns a list of proof result dicts."""
    lines = _file_text(filepath).splitlines()
    found = [(i, m.group(2), m.group(3), m.group(4))
             for i, line in enumerate(lines)
             for m in [_SHELL_PROOF_RE.search(line)]
             if m and m.group(1) == feature_name]
    merged, seen = [], set()
    for idx, (line_no, proof_id, rule_id, status) in enumerate(found):
        if (proof_id, rule_id) in seen:
            continue
        seen.add((proof_id, rule_id))
        pair = next((o for j, o in enumerate(found)
                     if j != idx and o[1] == proof_id and o[2] == rule_id
                     and o[3] != status), None)
        # an if/else pair is one proof, judged at the earlier of its two lines
        merged.append((line_no, proof_id, rule_id, status) if pair is None
                      else (min(line_no, pair[0]), proof_id, rule_id, 'pair'))
    merged.sort()
    results = []
    for idx, (line_no, proof_id, rule_id, status) in enumerate(merged):
        start = merged[idx - 1][0] + 1 if idx > 0 else 0
        segment = '\n'.join(lines[start:line_no])
        base = {'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': f'line_{line_no + 1}'}
        if status == 'pair':
            if _SHELL_PAIR_LOGIC_RE.search(segment):
                results.append(dict(base, status='pass', reason=(
                    'structural checks passed (if/else pair with condition)')))
            else:
                results.append(dict(base, status='fail', check='tautology', reason=(
                    'if/else proof pair with no test logic in condition')))
        elif _SHELL_LOGIC_RE.search(segment):
            results.append(dict(base, status='pass', reason='structural checks passed'))
        elif status == 'pass':
            results.append(dict(base, status='fail', check='tautology',
                                reason='hardcoded pass with no preceding test logic'))
        else:
            results.append(dict(base, status='fail', check='no_assertion',
                                reason='no assertion commands before proof marker'))
    return results


# --- JavaScript/TypeScript checks (brace-balancing tokenizer) --------------
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

def check_js(filepath, feature_name, rule_descs=None):
    """Run JS/TS test checks. Returns a list of proof result dicts."""
    return _run_body_checks(filepath, feature_name, 'js')


# --- C# / .NET (xUnit / NUnit / MSTest) checks -----------------------------

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

def check_csharp(filepath, feature_name, rule_descs=None):
    """Run C#/.NET (xUnit/NUnit/MSTest) test checks. Returns proof result dicts."""
    return _run_body_checks(filepath, feature_name, 'csharp')


# --- SQL (sqlite3) checks --------------------------------------------------
# The same marker regex and block delimiting as `scripts/proof/sql_purlin.sh`: a
# block runs from its marker to the next marker or to the end of the file.

_SQL_MARKER_RE = re.compile(
    r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:[ \t]+(\w+))?', re.MULTILINE)
_SQL_TEST_NAME_RE = re.compile(r'^-- Test:\s*(.+)', re.MULTILINE)
# `SELECT 'PASS';` as a whole statement: no WHERE, so nothing decides it.
_SQL_PLAIN_PASS_RE = re.compile(r"SELECT\s+'PASS'\s*;?[ \t]*$",
                                re.IGNORECASE | re.MULTILINE)
_SQL_CASE_PASS_RE = re.compile(r"CASE\s+WHEN\s+(.*?)\s+THEN\s+'PASS'",
                               re.IGNORECASE | re.DOTALL)
_SQL_SELECT_RE = re.compile(r'\bSELECT\b', re.IGNORECASE)
_SQL_STRING_RE = re.compile(r"'(?:[^']|'')*'")
_SQL_WORD_RE = re.compile(r'[A-Za-z_]\w*')
# Words a predicate may use and still decide nothing: operators and literals, not
# data. Any other identifier reads a column, calls a function or opens a subquery.
_SQL_OPERATOR_WORDS = frozenset({
    'and', 'or', 'not', 'is', 'null', 'in', 'like', 'glob', 'between',
    'true', 'false', 'escape'})

def _sql_executable(block):
    """The block with its `--` comment lines removed, as the plugin runs it."""
    return '\n'.join(l for l in block.split('\n')
                     if not l.strip().startswith('--')).strip()

def _sql_strip_comments(sql):
    """`sql` with every `--` comment removed, string literals left untouched."""
    out = []
    i = 0
    n = len(sql)
    while i < n:
        if sql.startswith('--', i):
            nl = sql.find('\n', i)
            i = n if nl < 0 else nl
            continue
        if sql[i] == "'":
            m = _SQL_STRING_RE.match(sql, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                continue
        out.append(sql[i])
        i += 1
    return ''.join(out)

def _sql_constant_predicate(predicate):
    """True when a CASE predicate decides nothing: operators, but no identifier."""
    stripped = _SQL_STRING_RE.sub(' ', predicate)
    if any(w.lower() not in _SQL_OPERATOR_WORDS
           for w in _SQL_WORD_RE.findall(stripped)):
        return False
    return bool(predicate.strip())

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

def _sql_tautology(sql_exec):
    """The reason the block's first PASS is unconditional, or None."""
    candidates = [(m.start(), "an unconditional SELECT 'PASS'")
                  for m in _SQL_PLAIN_PASS_RE.finditer(sql_exec)]
    for m in _SQL_CASE_PASS_RE.finditer(sql_exec):
        constant = _sql_constant_predicate(m.group(1))
        candidates.append((m.start(), (
            f"CASE WHEN {' '.join(m.group(1).split())} THEN 'PASS' compares constants"
        ) if constant else None))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]

def check_sql(filepath, feature_name, rule_descs=None):
    """Run SQL (sqlite3) test checks. Returns a list of proof result dicts."""
    return _run_body_checks(filepath, feature_name, 'sql')


# --- One driver for the brace-body languages -------------------------------
# JS, C# and SQL ask the same two questions of a test body — is the assertion
# always true, does it assert at all — so the walk lives here once and only the
# columns of `_BODY_CHECKS` differ per language.

_JS_TAUTOLOGY_RE = re.compile(r'expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)')
_JS_EXPECT_RE = re.compile(r'expect\s*\(')
_CSHARP_TAUTOLOGY_RES = (
    re.compile(r'Assert\s*\.\s*(?:True|IsTrue)\s*\(\s*true\s*\)'),
    re.compile(r'Assert\s*\.\s*(?:Equal|AreEqual)\s*\(\s*true\s*,\s*true\s*\)'))
# xUnit/NUnit/MSTest `Assert.`, FluentAssertions `.Should(`, Moq `.Verify(`, and
# Playwright's Expect(...) chained to a To<Matcher>Async() call. Playwright needs
# both tokens, so a bare Expect(x) and a lone `.ToListAsync()` are not assertions.
_CSHARP_ASSERT_RES = (re.compile(r'\bAssert\s*\.'), re.compile(r'\.\s*Should\s*\('),
                      re.compile(r'\.\s*Verify\s*\('))
_CSHARP_EXPECT_RE = re.compile(r'\bExpect\s*\(')
_CSHARP_MATCHER_RE = re.compile(r'\.\s*To\w+Async\s*\(')

def _csharp_has_assertion(body):
    """True when a C# body asserts through any recognized framework."""
    return bool(any(r.search(body) for r in _CSHARP_ASSERT_RES)
                or (_CSHARP_EXPECT_RE.search(body)
                    and _CSHARP_MATCHER_RE.search(body)))

def _sql_tautology_reason(sql_exec):
    """The SQL tautology reason, phrased as the finding reads."""
    tautology = _sql_tautology(sql_exec)
    return f'{tautology} passes whatever the data holds' if tautology else None


# `subjects(content, feature)` yields (proof_id, rule_id, raw_name, subject);
# `prepare` turns the subject into the text both predicates read, or is None when
# it already is; `tautology` returns the reason the proof is always true, or None.
_BodyLang = collections.namedtuple(
    '_BodyLang', 'subjects prepare tautology has_assertion no_assertion_reason')

_BODY_CHECKS = {
    'js': _BodyLang(
        subjects=_iter_js_proof_bodies, prepare=None,
        tautology=lambda body: ('expect(true).toBe(true) is tautological'
                                if _JS_TAUTOLOGY_RE.search(body) else None),
        has_assertion=lambda body: bool(_JS_EXPECT_RE.search(body)),
        no_assertion_reason='test function has no expect() calls'),
    'csharp': _BodyLang(
        subjects=_iter_csharp_proof_bodies, prepare=None,
        tautology=lambda body: ('Assert.True(true) is tautological' if any(
            r.search(body) for r in _CSHARP_TAUTOLOGY_RES) else None),
        has_assertion=_csharp_has_assertion,
        no_assertion_reason=('test method has no Assert./.Should()/.Verify()/'
                             'Expect(...).To*Async() call')),
    'sql': _BodyLang(
        subjects=_iter_sql_proof_blocks,
        prepare=lambda block: _sql_strip_comments(_sql_executable(block)),
        tautology=_sql_tautology_reason,
        has_assertion=lambda sql: bool(_SQL_SELECT_RE.search(sql)),
        no_assertion_reason='proof block runs no SELECT, so it observes nothing'),
}

def _run_body_checks(filepath, feature_name, lang):
    """The checks for one brace-body language. Returns proof result dicts."""
    spec = _BODY_CHECKS[lang]
    results = []
    for proof_id, rule_id, raw_name, subject in spec.subjects(
            _file_text(filepath), feature_name):
        judged = spec.prepare(subject) if spec.prepare else subject
        base = {'proof_id': proof_id, 'rule_id': rule_id, 'test_name': raw_name[:60]}
        tautology = spec.tautology(judged)
        if tautology:
            results.append(dict(base, status='fail', check='tautology',
                                reason=tautology))
        elif not spec.has_assertion(judged):
            results.append(dict(base, status='fail', check='no_assertion',
                                reason=spec.no_assertion_reason))
        else:
            results.append(dict(base, status='pass', reason='structural checks passed'))
    return results


# --- The extension table ---------------------------------------------------
# One table decides which language reads a test file, and `_TEST_CODE_EXTENSIONS`
# is derived from it rather than listed again. There is no fallback branch, so an
# extension absent from the table reaches no checker and no extractor. Shell is
# the one checked language with no extractor: a shell proof has no body.

_JS_EXTENSIONS = frozenset({'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'})
_CHECKERS = dict(
    [('.py', check_python), ('.sh', check_shell), ('.cs', check_csharp),
     ('.sql', check_sql)] + [(e, check_js) for e in sorted(_JS_EXTENSIONS)])
_CHECKER_EXTENSIONS = frozenset(_CHECKERS)
_TEST_CODE_EXTENSIONS = _CHECKER_EXTENSIONS - {'.sh'}

def analyze_test_file(test_file, feature_name, rule_descs=None):
    """Dispatch a test file to the checker matching its extension."""
    checker = _CHECKERS.get(os.path.splitext(test_file)[1].lower())
    return [] if checker is None else checker(test_file, feature_name, rule_descs)


# --- Spec reading ----------------------------------------------------------

_RULE_LINE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)
_PROOF_DESC_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)', re.MULTILINE)
# A tag is metadata appended after a proof description: ` @e2e`, ` @manual(...)`.
# Prose that merely ends in an @word is not a tag, so a tag is read only when it
# does not follow a list connector (',' 'and' 'or').
_TIER_TAG_RE = re.compile(r'(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$')

def _read_rule_descriptions(spec_path):
    """{rule id: description} for a spec file, or {} when it is not on disk."""
    if not spec_path or not os.path.isfile(spec_path):
        return {}
    return {m.group(1): m.group(2).strip()
            for m in _RULE_LINE_RE.finditer(_file_text(spec_path))}

def _strip_proof_tags(desc):
    """A proof description with its trailing `@tag` metadata removed."""
    desc = desc.rstrip()
    while True:
        m = _TIER_TAG_RE.search(desc)
        if not m:
            return desc
        desc = desc[:m.start()].rstrip()

def _read_proof_descriptions(spec_path):
    """[{proof_id, rule_ids, description}] from a spec's `## Proof` section."""
    if not spec_path or not os.path.isfile(spec_path):
        return []
    section = re.search(r'^## Proof\s*\n(.*?)(?=^## |\Z)',
                        _file_text(spec_path), re.MULTILINE | re.DOTALL)
    if not section:
        return []
    return [{'proof_id': m.group(1), 'rule_ids': m.group(2),
             'description': _strip_proof_tags(m.group(3))}
            for m in _PROOF_DESC_RE.finditer(section.group(1))]

def check_spec_coverage(spec_path):
    """{rule_count, proof_count} for a spec."""
    rules = _read_rule_descriptions(spec_path)
    return {'rule_count': len(rules),
            'proof_count': len(_read_proof_descriptions(spec_path)) if rules else 0}

def check_proof_file(proof_json_path, spec_path=None):
    """Structural findings for one proof record file, in any language."""
    if not os.path.isfile(proof_json_path):
        return []
    with open(proof_json_path, encoding='utf-8') as f:
        proofs = json.load(f).get('proofs', [])
    findings = []
    id_to_rules = {}
    for entry in proofs:
        if entry.get('id'):
            id_to_rules.setdefault(entry['id'], set()).add(entry.get('rule', ''))
    for pid, rules in id_to_rules.items():
        if len(rules) > 1:
            findings.append({
                'check': 'proof_id_collision', 'severity': 'MEDIUM',
                'proof_id': pid, 'rules': sorted(rules),
                'reason': f'{pid} targets multiple rules: {", ".join(sorted(rules))}'})
    spec_rules = set(_read_rule_descriptions(spec_path)) if spec_path else set()
    for entry in proofs if spec_rules else []:
        rid = entry.get('rule', '')
        if rid and '/' not in rid and rid not in spec_rules:
            findings.append({
                'check': 'proof_rule_orphan', 'severity': 'LOW',
                'proof_id': entry.get('id', ''), 'rule': rid,
                'reason': f'{rid} not found in spec (rule may have been removed)'})
    return findings


# --- Run scope -------------------------------------------------------------
# A sweep resolves the same files over and over, so inside a scope every read and
# parse is done once; outside one nothing is memoized, and a caller that never
# opens a scope always sees what is on disk. The scope is explicit rather than
# keyed on mtimes: a same-size edit inside one clock tick must still be seen.

class _RunCache:
    __slots__ = ('proof_backings', 'texts', 'py_parses', 'test_bodies')

    def __init__(self):
        self.proof_backings = {}  # feature -> {proof_id: [(test_file, test_name)]}
        self.texts = {}           # abs path -> file text
        self.py_parses = {}       # test path -> (entries, lines) | SyntaxError
        self.test_bodies = {}     # (test path, feature) -> {proof_id: src} | None


_RUN_CACHE = None

def _file_text(path):
    """The UTF-8 text of `path`, read from disk once per scope."""
    cache = _RUN_CACHE
    key = os.path.abspath(path)
    if cache is not None and key in cache.texts:
        return cache.texts[key]
    with open(path, encoding='utf-8') as f:
        content = f.read()
    if cache is not None:
        cache.texts[key] = content
    return content


@contextlib.contextmanager
def run_scope():
    """Memoize spec, record and test-file reads for the block's duration."""
    global _RUN_CACHE
    if _RUN_CACHE is not None:
        yield _RUN_CACHE
        return
    _RUN_CACHE = _RunCache()
    try:
        yield _RUN_CACHE
    finally:
        _RUN_CACHE = None

def _find_spec_path(project_root, feature):
    """The spec file declaring `feature`, or None."""
    if not feature:
        return None
    matches = sorted(glob.glob(
        os.path.join(project_root, 'specs', '**', f'{feature}.md'), recursive=True))
    return matches[0] if matches else None

def _proof_backings(project_root, feature):
    """{proof_id: [(test_file, test_name), ...]} for every executed proof."""
    cache = _RUN_CACHE
    if cache is not None and feature in cache.proof_backings:
        return cache.proof_backings[feature]
    backings, seen = {}, set()
    pattern = os.path.join(project_root, '.purlin', 'runtime', 'proofs',
                           f'{feature}.*.json')
    for record in sorted(glob.glob(pattern)):
        try:
            with open(record, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data.get('proofs', []):
            if entry.get('feature') != feature or not entry.get('id'):
                continue
            test_file = entry.get('test_file') or None
            if (entry['id'], test_file) in seen:
                continue
            seen.add((entry['id'], test_file))
            backings.setdefault(entry['id'], []).append(
                (test_file, entry.get('test_name') or None))
    if cache is not None:
        cache.proof_backings[feature] = backings
    return backings

def _test_bodies(path, ext, feature):
    """{proof_id: [(test name, source), ...]} for `feature`'s marked tests at `path`.

    Every marked test is kept, in file order, because one proof may be backed by
    several tests and each of them has its own source.
    """
    cache = _RUN_CACHE
    memo_key = (path, feature)
    if cache is not None and memo_key in cache.test_bodies:
        return cache.test_bodies[memo_key]
    bodies = None
    try:
        content = _file_text(path)
    except OSError:
        content = ''
    if content and ext == '.py':
        try:
            entries, lines = _python_parse(path, content)
        except SyntaxError:
            entries = ()
        bodies = {}
        for feat, pid, _rid, name, node in sorted(
                entries, key=lambda entry: entry[4].lineno):
            if feat == feature:
                bodies.setdefault(pid, []).append((name, _segment(lines, node)))
    elif content:
        iterator = {'.cs': _iter_csharp_proof_bodies,
                    '.sql': _iter_sql_proof_blocks}.get(
                        ext, _iter_js_proof_bodies if ext in _JS_EXTENSIONS else None)
        if iterator is not None:
            bodies = {}
            for pid, _rid, name, body in iterator(content, feature):
                bodies.setdefault(pid, []).append((name, body))
    if cache is not None:
        cache.test_bodies[memo_key] = bodies
    return bodies

# A recorded name carries what the runner added to the name in the source: a
# pytest parameter id, an xUnit theory's arguments, a class or namespace prefix,
# and in JS the proof marker the title holds.
_NAME_ARGS_RE = re.compile(r'(?:\[.*\]|\(.*\))\s*$')
_NAME_MARKER_RE = re.compile(r'\[proof:[^\]]*\]')

def _test_name_key(name):
    return ' '.join(_NAME_MARKER_RE.sub(' ', name or '').split())

def test_name_matches(test_name, names):
    """The indexes in `names` that are the test a proof file recorded as `test_name`.

    An exact name wins, then the name without its arguments, then a name the
    recorded one ends with after a class, namespace or describe prefix. Empty
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
    found = test_name_matches(test_name, [name for name, _body in candidates])
    if found:
        return candidates[found[0]][1]
    return candidates[0][1] if len(candidates) == 1 else None

def _extract_test_code(project_root, feature, proof_id, test_file, test_name=None):
    """The source of the test named `test_name` backing `proof_id`, or None."""
    ext = os.path.splitext(test_file or '')[1].lower()
    if not test_file or ext not in _TEST_CODE_EXTENSIONS:
        return None
    path = os.path.join(project_root, *test_file.split('/'))
    if not os.path.isfile(path):
        return None
    bodies = _test_bodies(path, ext, feature)
    return _pick_test_body((bodies or {}).get(proof_id), test_name)


# --- The whole-project sweep -----------------------------------------------

_SWEEP_STATUS_RANK = {'pass': 0, 'unmeasurable': 1, 'fail': 2}
# Build-output and vendored directories that never hold authored test source.
_SOURCE_SCAN_SKIP_DIRS = {'bin', 'obj', 'node_modules', '.git', '.purlin',
                          'dist', 'build'}

def resolve_test_file_from_name(test_name, project_root, ext='.cs'):
    """The source file of a test, resolved from its fully-qualified test name."""
    parts = (test_name or '').split('.')
    type_name = parts[-2] if len(parts) >= 2 else ''
    if not type_name:
        return ''
    decl = re.compile(r'\b(?:class|struct|record|interface)\s+'
                      + re.escape(type_name) + r'\b')
    matches = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in _SOURCE_SCAN_SKIP_DIRS]
        for fn in files:
            if not fn.endswith(ext):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, encoding='utf-8') as f:
                    if decl.search(f.read()):
                        matches.append(path)
            except (OSError, UnicodeDecodeError):
                continue
    if not matches:
        return ''
    matches.sort()  # the same answer on every operating system
    best = next((m for m in matches
                 if os.path.splitext(os.path.basename(m))[0] == type_name), matches[0])
    return os.path.relpath(best, project_root).replace(os.sep, '/')

def _sweep_unmeasurable_reason(check, test_file, feature):
    """Why one backing could not be measured, in words a report can print."""
    if check == 'no_checker':
        ext = os.path.splitext(test_file)[1].lower() or '(no extension)'
        return (f'No free checker reads {ext} files, so nothing looked at this '
                'test. An unmeasurable proof is a gap in coverage, not a defect.')
    if check == 'missing_file':
        if not test_file:
            return ('The proof record names no test file and none could be '
                    'resolved from the test name, so there is no source to read.')
        return (f'{test_file} is named by the proof record but is not on disk, so '
                'there is no source to read.')
    return (f'{test_file} carries no {feature} marker for this proof, so the '
            'executed test could not be located in the file that recorded it.')

def _sweep_file_verdicts(project_root, feature, test_file, rule_descs):
    """({proof_id: result}, blanket) for one of `feature`'s test files."""
    if not test_file:
        return {}, 'missing_file'
    ext = os.path.splitext(test_file)[1].lower()
    if ext not in _CHECKER_EXTENSIONS:
        return {}, 'no_checker'
    path = os.path.join(project_root, *test_file.split('/'))
    if not os.path.isfile(path):
        return {}, 'missing_file'
    results = {}
    for result in analyze_test_file(path, feature, rule_descs):
        results.setdefault(result['proof_id'], result)
    return results, None

def _sweep_feature(project_root, feature, rule_descs):
    """({proof_id: verdict}, {proof_id: backing count}) for one feature."""
    by_file = {}
    for proof_id, entries in _proof_backings(project_root, feature).items():
        for test_file, test_name in entries:
            resolved = test_file
            if not resolved and test_name:
                resolved = resolve_test_file_from_name(test_name, project_root)
            by_file.setdefault(resolved or '', []).append((proof_id, test_name))
    best, counted = {}, {}
    for test_file in sorted(by_file):
        results, blanket = _sweep_file_verdicts(
            project_root, feature, test_file, rule_descs)
        for proof_id, test_name in sorted(by_file[test_file]):
            counted[proof_id] = counted.get(proof_id, 0) + 1
            result = results.get(proof_id)
            if blanket is not None or result is None:
                check = blanket or 'marker_not_found'
                verdict = {'status': 'unmeasurable', 'check': check,
                           'reason': _sweep_unmeasurable_reason(
                               check, test_file, feature),
                           'test_file': test_file, 'test_name': test_name or ''}
            else:
                verdict = {
                    'status': 'fail' if result['status'] == 'fail' else 'pass',
                    'check': result.get('check', 'none'),
                    'reason': result.get('reason', ''), 'test_file': test_file,
                    'test_name': result.get('test_name') or test_name or ''}
            current = best.get(proof_id)
            if current is None or (_SWEEP_STATUS_RANK[verdict['status']]
                                   > _SWEEP_STATUS_RANK[current['status']]):
                best[proof_id] = verdict
    return best, counted

def deterministic_sweep(project_root):
    """Run the free checks over every proof in `project_root`."""
    features = {}
    failing, unmeasurable = [], []
    declared_total = backing_total = passing = 0
    with run_scope():
        for spec_path in sorted(glob.glob(
                os.path.join(project_root, 'specs', '**', '*.md'), recursive=True)):
            feature = os.path.splitext(os.path.basename(spec_path))[0]
            declared = _read_proof_descriptions(spec_path)
            declared_total += len(declared)
            first_rule = {d['proof_id']: d['rule_ids'].split(',')[0].strip()
                          for d in declared}
            best, counted = _sweep_feature(
                project_root, feature, _read_rule_descriptions(spec_path))
            proofs = {}
            for proof_id in sorted(best):
                verdict = best[proof_id]
                backing_total += counted[proof_id]
                proofs[proof_id] = dict(verdict, rule_id=first_rule.get(proof_id, ''),
                                        backings=counted[proof_id])
                row = {'feature': feature, 'proof_id': proof_id, **proofs[proof_id]}
                if verdict['status'] == 'fail':
                    failing.append(row)
                elif verdict['status'] == 'unmeasurable':
                    unmeasurable.append(row)
                else:
                    passing += 1
            features[feature] = {
                'spec': os.path.relpath(spec_path, project_root).replace(os.sep, '/'),
                'proofs': proofs}
    def _order(row):
        return (row['feature'], row['proof_id'], row.get('test_file', ''))
    failing.sort(key=_order)
    unmeasurable.sort(key=_order)
    return {
        'project_root': project_root, 'features': features,
        'failing': failing, 'unmeasurable': unmeasurable,
        'counts': {'features': len(features), 'proofs_declared': declared_total,
                   'proofs_executed': sum(len(f['proofs']) for f in features.values()),
                   'backings': backing_total, 'pass': passing,
                   'failing': len(failing), 'unmeasurable': len(unmeasurable)},
    }


# --- File locking ----------------------------------------------------------
# The one check in this repository that must be proved on Windows as well as
# POSIX: Windows has no fcntl, so the lock is taken with msvcrt on one byte.

def lock_exclusive(path):
    """Take an exclusive, blocking lock on `path`. Returns the open handle."""
    handle = open(path, 'a+', encoding='utf-8')
    if _HAS_FCNTL:
        fcntl.flock(handle, fcntl.LOCK_EX)
        return handle
    import msvcrt
    handle.write('\0')  # a byte must exist at offset 0 to lock
    handle.flush()
    handle.seek(0)
    while True:
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            return handle
        except OSError:
            continue

def unlock(handle):
    """Release a lock taken by `lock_exclusive` and close its handle."""
    try:
        if _HAS_FCNTL:
            fcntl.flock(handle, fcntl.LOCK_UN)
        else:
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


# --- Command line ----------------------------------------------------------
# Every form this script accepts, kept next to the dispatch chain in main():
# RULE-34 asserts that every `--flag` main() dispatches on appears here.

_USAGE = (
    "<test_file> <feature> [--project-root <path>] [--json]",
    "--sweep [--project-root <path>] [--json]",
    "--help",
)

def _argument_after(flag, fallback=None):
    """The argument following `flag` on the command line, or `fallback`."""
    idx = sys.argv.index(flag) + 1 if flag in sys.argv else 0
    return sys.argv[idx] if 0 < idx < len(sys.argv) else fallback

def main():
    force_utf8_stdio()
    usage = (f"Usage: {os.path.basename(sys.argv[0])} "
             + f"\n       {os.path.basename(sys.argv[0])} ".join(_USAGE))
    as_json = '--json' in sys.argv
    if '--help' in sys.argv:
        print(usage)
        print('\nExit codes: 0 for a completed analysis, however weak the test it '
              'read;\n2 for a real error: bad arguments, a missing file, or '
              'malformed input.')
        sys.exit(0)

    if '--sweep' in sys.argv:
        result = deterministic_sweep(_argument_after('--project-root', os.getcwd()))
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            counts = result['counts']
            print(', '.join(f'{counts[k]} {k}' for k in (
                'features', 'backings', 'pass', 'failing', 'unmeasurable')))
            for row in result['failing'] + result['unmeasurable']:
                print(f"  {row['feature']}: {row['proof_id']} {row['status']} "
                      f"({row['check']}) {row['test_file']}")
        sys.exit(0)

    positional = [a for a in sys.argv[1:] if not a.startswith('--')]
    project_root = _argument_after('--project-root', os.getcwd())
    if project_root in positional:
        positional.remove(project_root)
    if len(positional) < 2:
        print(usage, file=sys.stderr)
        sys.exit(2)
    test_file, feature = positional[0], positional[1]
    if not os.path.isfile(test_file):
        print(json.dumps({'error': f'File not found: {test_file}'}))
        sys.exit(2)

    results = analyze_test_file(
        test_file, feature,
        _read_rule_descriptions(_find_spec_path(project_root, feature)))
    if as_json:
        print(json.dumps({'proofs': results}, indent=2))
    else:
        for r in results:
            print(f"pass {r['proof_id']} {r['test_name']}" if r['status'] == 'pass'
                  else f"fail {r['proof_id']} {r['check']}: {r['reason']}")
    sys.exit(0)


if __name__ == '__main__':
    main()
