#!/usr/bin/env python3
"""Deterministic static checks for proof quality — no LLM required.

Catches structural test problems (assert True, no assertions, logic mirroring,
bare except, mock-target match) using Python's ast module and regex. Every
language Purlin ships a proof plugin for has a checker here: Python, JS/TS
(.js .jsx .mjs .cjs .ts .tsx), shell, C#, PHP, SQL and C (.c .h). Which checker
reads which extension is decided in one place, the extension table below.

`deterministic_sweep` runs both deterministic halves (Pass 1 over every executed
proof backing, Pass D1 over every declared proof description) across a whole
project without an LLM and without reading or writing any cache, which is what
lets a CI job recompute the same verdict from a clean checkout.

Usage (see _USAGE below — it is the single source for this list):
    static_checks.py <test_file> <feature_name> [--spec-path <path>]
    static_checks.py --deterministic-sweep [--project-root <path>]
    static_checks.py --check-proof-file --proof-path <path> [--spec-path <path>]
    static_checks.py --check-spec-coverage --spec-path <path>
    static_checks.py --cache-key --feature <name> --proof-id PROOF-N [--project-root <path>]
    static_checks.py --resolve-source <test_name> [--project-root <path>] [--ext .cs]
    static_checks.py --load-criteria [--project-root <path>] [--extra <path>]
    static_checks.py --read-cache [--project-root <path>]
    static_checks.py --write-cache [--project-root <path>]      (JSON object on stdin)
    static_checks.py --clear-cache [--project-root <path>]
    static_checks.py --prune-cache --live-keys-file <path> [--project-root <path>]

Exit codes (RULE-7): 0 for any completed analysis — a detected defect is reported as
`status: "fail"` in the JSON, never as a non-zero exit. Non-zero is reserved for real
errors: 2 for bad arguments, missing files, or malformed input.
Output: JSON to stdout.
"""

import ast
import collections
import contextlib
import datetime
import glob
import hashlib
import json
import os
import re
import sys

try:
    import fcntl  # POSIX only — absent on Windows
    _HAS_FCNTL = True
except ImportError:  # Windows: fall back to msvcrt-based locking (imported lazily)
    _HAS_FCNTL = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROOF_MARKER_RE = re.compile(
    r'pytest\.mark\.proof\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']'
)

_ASSERT_KEYWORDS = {'assert', 'assertEqual', 'assertNotEqual', 'assertTrue',
                    'assertFalse', 'assertIs', 'assertIsNot', 'assertIn',
                    'assertNotIn', 'assertRaises', 'assertAlmostEqual',
                    'assertGreater', 'assertLess', 'assertRegex'}

_SHELL_PROOF_RE = re.compile(
    r'purlin_proof\s+"([^"]+)"\s+"(PROOF-\d+)"\s+"(RULE-\d+)"\s+(pass|fail)'
)

_JEST_PROOF_RE = re.compile(
    r'\[proof:([^:]+):(PROOF-\d+):(RULE-\d+)'
)

# ---------------------------------------------------------------------------
# Python checks (ast-based)
# ---------------------------------------------------------------------------

# ast.get_source_segment re-splits the whole file into lines on every call, in
# pure Python, so calling it once per decorator made marker discovery quadratic
# in file size: 79k calls and a minute of CPU on this repository's own suites.
# The file is split once here and every segment is sliced from that split.
# `_split_source_lines` and `_segment` replicate the stdlib byte-for-byte (a
# line ends at \n, \r\n or \r and nowhere else, never at a form feed;
# offsets are utf-8 byte offsets), which static_checks PROOF-69 pins.
_SOURCE_LINE_RE = re.compile(r'[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+')


def _split_source_lines(source):
    """The lines of `source` as ast.get_source_segment splits them, ends kept.

    The stdlib's own splitter is used when it exists so the two cannot drift;
    the regex is the same rule for an interpreter that has renamed it.
    """
    splitter = getattr(ast, '_splitlines_no_ff', None)
    if splitter is not None:
        return splitter(source)
    return _SOURCE_LINE_RE.findall(source)


def _segment(lines, node):
    """The source text of `node`, from lines split once by _split_source_lines.

    Byte-identical to `ast.get_source_segment(source, node)` for any node the
    parser produced, and None for a node with no end position, as the stdlib.
    """
    end_lineno = getattr(node, 'end_lineno', None)
    end_col = getattr(node, 'end_col_offset', None)
    if end_lineno is None or end_col is None:
        return None
    lineno = node.lineno - 1
    end = end_lineno - 1
    col = node.col_offset
    if end == lineno:
        return lines[lineno].encode()[col:end_col].decode()
    first = lines[lineno].encode()[col:].decode()
    last = lines[end].encode()[:end_col].decode()
    return ''.join([first] + lines[lineno + 1:end] + [last])


def _python_proof_functions(source):
    """Every marked test in a Python file, from one parse and one line split.

    Returns (entries, lines): `entries` is the list of
    (feature, proof_id, rule_id, test_name, func_node) in source order, one per
    marker, and `lines` is the split the caller slices function source from.
    Raises SyntaxError as ast.parse does.
    """
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
    """`_python_proof_functions(content)` for the file at `path`, memoized per scope.

    One `ast.parse` and one line split per file however many callers ask for it:
    Pass 1 (`check_python`) and the cache-key extractor (`_python_proof_sources`)
    both come through here, so a file carrying two features is parsed once inside
    a `run_scope()` rather than once per feature (RULE-42). Outside a scope
    nothing is memoized. A file that does not parse raises SyntaxError exactly as
    `ast.parse` does, and that failure is memoized too so a second caller inside
    the scope does not re-parse it.
    """
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
    """Check if a function body contains any assertion statement."""
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            return True
        if isinstance(child, ast.Call):
            func = child.func
            name = ''
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            if name in _ASSERT_KEYWORDS or name.startswith('assert') or name == 'raises':
                return True
            # pytest.raises
            if isinstance(func, ast.Attribute) and func.attr == 'raises':
                return True
        # Check for 'with pytest.raises'
        if isinstance(child, ast.With):
            for item in child.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Attribute):
                    if ctx.func.attr == 'raises':
                        return True
    return False


def _is_always_true(node):
    """Check if an AST node is a constant True or a comparison of two constants."""
    # Literal True / False-y
    if isinstance(node, ast.Constant) and node.value is True:
        return True
    # Comparison where both sides are constants or UPPER_CASE names (module-level)
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        left = node.left
        right = node.comparators[0]
        def _is_constant_or_uppername(n):
            if isinstance(n, ast.Constant):
                return True
            if isinstance(n, ast.Name) and n.id.isupper():
                return True
            return False
        if _is_constant_or_uppername(left) and _is_constant_or_uppername(right):
            return True
    # `not False` or `not 0`
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        if isinstance(node.operand, ast.Constant) and not node.operand.value:
            return True
    return False


def _check_assert_true(node, source):
    """Detect tautological assertions: assert True, assert x is not None, assert len(x) >= 0,
    and assert X or True / assert X or CONST_COMPARE (tautological escape hatch).

    Returns None if no tautological assertion found, or a dict with:
      'literal': True  — for assert True, assertTrue(True), assert X or True
      'literal': False — for assert x is not None, assert len(x) >= 0,
                         assert X or CONST_COMPARE (heuristic)
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            test = child.test
            # assert True
            if isinstance(test, ast.Constant) and test.value is True:
                return {'literal': True}
            # assert X or True / assert X or CONST_COMPARE (tautological escape hatch)
            if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
                for operand in test.values:
                    if _is_always_true(operand):
                        # `or True` is literal; `or CONST not in CONST` is heuristic
                        literal = isinstance(operand, ast.Constant) and operand.value is True
                        return {'literal': literal}
            # assert result is not None
            if isinstance(test, ast.Compare):
                if len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot):
                    if len(test.comparators) == 1:
                        comp = test.comparators[0]
                        if isinstance(comp, ast.Constant) and comp.value is None:
                            return {'literal': False}
                # assert len(x) >= 0
                if len(test.ops) == 1 and isinstance(test.ops[0], ast.GtE):
                    if len(test.comparators) == 1:
                        comp = test.comparators[0]
                        if isinstance(comp, ast.Constant) and comp.value == 0:
                            if isinstance(test.left, ast.Call):
                                fn = test.left.func
                                if isinstance(fn, ast.Name) and fn.id == 'len':
                                    return {'literal': False}
        # self.assertTrue(True)
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr == 'assertTrue':
                if child.args and isinstance(child.args[0], ast.Constant) and child.args[0].value is True:
                    return {'literal': True}
    return None


def _check_bare_except(node):
    """Detect bare except:pass or except Exception:pass around code under test."""
    for child in ast.walk(node):
        if isinstance(child, ast.Try):
            for handler in child.handlers:
                is_bare = handler.type is None
                is_exception = (isinstance(handler.type, ast.Name)
                                and handler.type.id == 'Exception') if handler.type else False
                if is_bare or is_exception:
                    if (len(handler.body) == 1
                            and isinstance(handler.body[0], ast.Pass)):
                        return True
    return False


def _collect_call_names(node):
    """Collect all function-call base names within a node."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _check_logic_mirroring(node):
    """Detect expected value computed by the same function as the SUT."""
    assigns = {}
    body = node.body if hasattr(node, 'body') else []
    for stmt in body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    assigns[target.id] = _collect_call_names(stmt.value)
    # Check assertions: if both sides of a comparison were computed by overlapping functions
    benign = {'str', 'int', 'float', 'len', 'list', 'dict', 'set', 'tuple', 'type', 'repr', 'sorted'}
    for child in ast.walk(node):
        if isinstance(child, ast.Assert) and isinstance(child.test, ast.Compare):
            all_parts = [child.test.left] + child.test.comparators
            # Resolve each part's call names (inline calls or via assigned variable)
            part_calls = []
            for part in all_parts:
                calls = set()
                if isinstance(part, ast.Name) and part.id in assigns:
                    calls = assigns[part.id]
                else:
                    calls = _collect_call_names(part)
                part_calls.append(calls)
            # Check each pair for overlapping non-trivial function calls
            for i in range(len(part_calls)):
                for j in range(i + 1, len(part_calls)):
                    overlap = (part_calls[i] & part_calls[j]) - benign
                    if overlap:
                        return True
    return False


def _check_mock_target_match(node, lines, rule_desc):
    """Detect mock/patch targeting the function the rule describes.

    `lines` is the one split `_python_parse` made of the file, so the decorator
    and function source come from `_segment` rather than from
    `ast.get_source_segment`, which re-splits the whole file on every call
    (RULE-42).
    """
    if not rule_desc:
        return False
    rule_words = set(re.findall(r'[a-z_]\w+', rule_desc.lower()))
    rule_words -= {'the', 'and', 'or', 'is', 'are', 'must', 'should', 'will',
                   'with', 'for', 'not', 'that', 'this', 'from', 'have', 'has',
                   'rule', 'test', 'all', 'any', 'each', 'when', 'then', 'can',
                   'does', 'use', 'using', 'used', 'into', 'returns', 'return',
                   'code', 'file', 'function', 'method', 'class'}

    for deco in node.decorator_list:
        deco_src = _segment(lines, deco) or ''
        # Look for @patch("some.module.func") or @mock.patch(...)
        patch_targets = re.findall(r'patch\(["\']([^"\']+)["\']', deco_src)
        for target in patch_targets:
            # Check both the basename and all parts of the dotted path
            parts = {p.lower() for p in target.split('.')}
            if parts & rule_words:
                return True

    # Also check mock.patch context managers in the body
    func_src = _segment(lines, node) or ''
    ctx_targets = re.findall(r'mock\.patch\(["\']([^"\']+)["\']', func_src)
    for target in ctx_targets:
        parts = {p.lower() for p in target.split('.')}
        if parts & rule_words:
            return True

    return False


def check_python(filepath, feature_name, rule_descs=None):
    """Run all Python checks. Returns list of proof result dicts."""
    rule_descs = rule_descs or {}
    source = _file_text(filepath)
    entries, lines = _python_parse(filepath, source)
    proofs = [(pid, rid, name, node)
              for feature, pid, rid, name, node in entries if feature == feature_name]
    results = []
    for proof_id, rule_id, test_name, func_node in proofs:
        checks_failed = []
        assert_true_result = _check_assert_true(func_node, source)
        if assert_true_result is not None:
            checks_failed.append(('assert_true', 'tautological assertion (assert True or equivalent)', assert_true_result.get('literal', True)))
        if not _has_assertion(func_node):
            checks_failed.append(('no_assertions', 'test function has no assertion statements', None))
        if _check_bare_except(func_node):
            checks_failed.append(('bare_except', 'bare except:pass swallows failures', None))
        if _check_logic_mirroring(func_node):
            checks_failed.append(('logic_mirroring', 'expected value computed by same function as SUT', None))
        rdesc = rule_descs.get(rule_id, '')
        if rdesc and _check_mock_target_match(func_node, lines, rdesc):
            checks_failed.append(('mock_target_match', 'mock target matches the function the rule describes', None))

        if checks_failed:
            # Report the first failure (most severe)
            check, reason, literal = checks_failed[0]
            result_dict = {
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_name, 'status': 'fail',
                'check': check, 'reason': reason,
            }
            if check == 'assert_true' and literal is not None:
                result_dict['literal'] = literal
            results.append(result_dict)
        else:
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_name, 'status': 'pass',
                'reason': 'structural checks passed',
            })
    return results

# ---------------------------------------------------------------------------
# Shell checks (regex-based)
# ---------------------------------------------------------------------------

def check_shell(filepath, feature_name, rule_descs=None):
    """Run shell test checks. Returns list of proof result dicts.

    `rule_descs` is accepted so every checker in the extension table has one
    signature; shell has no rule-aware check to spend it on.
    """
    content = _file_text(filepath)
    lines = content.splitlines()
    results = []
    proof_locations = []
    for i, line in enumerate(lines):
        m = _SHELL_PROOF_RE.search(line)
        if m and m.group(1) == feature_name:
            proof_locations.append((i, m.group(2), m.group(3), m.group(4)))

    # Detect if/else pairs: same (proof_id, rule_id) with one pass and one fail
    merged = []
    seen = set()
    for idx, (line_no, proof_id, rule_id, status) in enumerate(proof_locations):
        key = (proof_id, rule_id)
        if key in seen:
            continue
        # Look for a matching pair
        pair = None
        for idx2, (line_no2, pid2, rid2, status2) in enumerate(proof_locations):
            if idx2 != idx and pid2 == proof_id and rid2 == rule_id and status2 != status:
                pair = (idx2, line_no2, pid2, rid2, status2)
                break
        if pair is not None:
            # if/else pair: use the earlier line, treat as single proof
            earlier_line = min(line_no, pair[1])
            merged.append((earlier_line, proof_id, rule_id, 'pair'))
            seen.add(key)
        else:
            merged.append((line_no, proof_id, rule_id, status))
            seen.add(key)

    # Sort by line number
    merged.sort(key=lambda x: x[0])

    for idx, (line_no, proof_id, rule_id, status) in enumerate(merged):
        start = merged[idx - 1][0] + 1 if idx > 0 else 0
        segment = '\n'.join(lines[start:line_no])

        if status == 'pair':
            # if/else pair: check that the segment has real test logic
            # Include \bif\b since the if-condition IS the assertion for pairs
            has_logic = bool(re.search(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\||\bif\b', segment))
            if not has_logic:
                results.append({
                    'proof_id': proof_id, 'rule_id': rule_id,
                    'test_name': f'line_{line_no + 1}', 'status': 'fail',
                    'check': 'assert_true',
                    'reason': 'if/else proof pair with no test logic in condition',
                })
            else:
                results.append({
                    'proof_id': proof_id, 'rule_id': rule_id,
                    'test_name': f'line_{line_no + 1}', 'status': 'pass',
                    'reason': 'structural checks passed (if/else pair with condition)',
                })
            continue

        # Single proof: original logic (no \bif\b in pattern)
        has_logic = bool(re.search(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\|', segment))
        if status == 'pass':
            if not has_logic:
                results.append({
                    'proof_id': proof_id, 'rule_id': rule_id,
                    'test_name': f'line_{line_no + 1}', 'status': 'fail',
                    'check': 'assert_true', 'reason': 'hardcoded pass with no preceding test logic',
                })
                continue

        # Check no_assertions
        has_assertion = has_logic
        if not has_assertion:
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': f'line_{line_no + 1}', 'status': 'fail',
                'check': 'no_assertions', 'reason': 'no assertion commands before proof marker',
            })
            continue

        results.append({
            'proof_id': proof_id, 'rule_id': rule_id,
            'test_name': f'line_{line_no + 1}', 'status': 'pass',
            'reason': 'structural checks passed',
        })
    return results

# ---------------------------------------------------------------------------
# JavaScript/TypeScript checks (brace-balancing tokenizer)
#
# A flat regex cannot reliably bound a JS/TS test: lazy `\}\s*\)` truncates at
# the first inner `}` (options objects, destructured params, `as { x }` type
# assertions) and a `[^"']*` title class drops titles containing apostrophes.
# These helpers character-walk the source, tracking string/template/regex
# literals and comments, so braces and quotes are matched correctly.
# ---------------------------------------------------------------------------

def _read_js_string(content, i):
    """content[i] is a quote char (" ' `). Return (inner_text, index_after_closing_quote).

    Handles backslash escapes (so an apostrophe inside a double-quoted string
    does not terminate it) and ${...} interpolation inside template literals.
    """
    quote = content[i]
    n = len(content)
    j = i + 1
    parts = []
    while j < n:
        c = content[j]
        if c == '\\':
            parts.append(content[j:j + 2])
            j += 2
            continue
        if quote == '`' and c == '$' and content[j + 1:j + 2] == '{':
            # Skip the balanced ${ ... } interpolation (may itself contain strings).
            _, j = _read_balanced(content, j + 1)
            continue
        if c == quote:
            return ''.join(parts), j + 1
        parts.append(c)
        j += 1
    return ''.join(parts), j  # unterminated — return what we have


def _regex_allowed(content, j):
    """Heuristic: does a `/` at index j begin a regex literal (vs division)?

    A regex is allowed where an expression is expected — i.e. when the previous
    non-space character is not the end of an operand.
    """
    k = j - 1
    while k >= 0 and content[k] in ' \t\r\n':
        k -= 1
    if k < 0:
        return True
    prev = content[k]
    return not (prev.isalnum() or prev in '_)]}')


def _skip_regex(content, j):
    """content[j] is `/` starting a regex literal. Return index after it (+ flags)."""
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
            return j + 1  # newline inside a "regex" => it was division; bail
        elif c == '/' and not in_class:
            k += 1
            while k < n and content[k].isalpha():  # trailing flags (gimsuy)
                k += 1
            return k
        k += 1
    return k


def _read_balanced(content, i):
    """content[i] is one of { ( [. Return (inner_text, index_after_matching_close).

    Skips strings, template literals, regex literals, and // and /* */ comments
    so their contents never affect bracket depth.
    """
    pairs = {'{': '}', '(': ')', '[': ']'}
    opener = content[i]
    closer = pairs[opener]
    n = len(content)
    depth = 0
    j = i
    start_inner = i + 1
    while j < n:
        c = content[j]
        if c in '"\'`':
            _, j = _read_js_string(content, j)
            continue
        if c == '/' and content[j + 1:j + 2] == '/':
            nl = content.find('\n', j)
            j = n if nl < 0 else nl
            continue
        if c == '/' and content[j + 1:j + 2] == '*':
            e = content.find('*/', j + 2)
            j = n if e < 0 else e + 2
            continue
        if c == '/' and _regex_allowed(content, j):
            j = _skip_regex(content, j)
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return content[start_inner:j], j + 1
        j += 1
    return content[start_inner:j], j  # unterminated


def _find_test_body(content, i):
    """From index i (just after a test title), locate the callback's { body }.

    Returns (body_text, index_after_body), or (None, i) if no block body is
    found (e.g. an arrow with an expression body, or a title-only `it`).
    Balanced groups encountered before the callback (param lists, options
    objects) are skipped so their braces/arrows are not mistaken for the body.
    """
    n = len(content)
    saw_callback = False  # saw `=>` or `function` — next `{` is the body
    while i < n:
        c = content[i]
        if c in '"\'`':
            _, i = _read_js_string(content, i)
            continue
        if c == '/' and content[i + 1:i + 2] == '/':
            nl = content.find('\n', i)
            i = n if nl < 0 else nl
            continue
        if c == '/' and content[i + 1:i + 2] == '*':
            e = content.find('*/', i + 2)
            i = n if e < 0 else e + 2
            continue
        if c == '/' and _regex_allowed(content, i):
            i = _skip_regex(content, i)
            continue
        if content.startswith('=>', i):
            saw_callback = True
            i += 2
            continue
        if content.startswith('function', i):
            before = content[i - 1] if i > 0 else ' '
            after = content[i + 8] if i + 8 < n else ' '
            if not (before.isalnum() or before == '_') and not (after.isalnum() or after == '_'):
                saw_callback = True
                i += 8
                continue
        if c == '{':
            if saw_callback:
                return _read_balanced(content, i)
            _, i = _read_balanced(content, i)  # options object etc. — skip
            continue
        if c in '([':
            _, i = _read_balanced(content, i)  # param list / array — skip
            continue
        if c in ');':
            return None, i  # end of the it(...) call without a block body
        i += 1
    return None, i


def _iter_js_proof_bodies(content, feature_name):
    """Yield (proof_id, rule_id, title, body) for every marked test in a JS/TS file.

    The scan is the expensive part (string, comment and regex aware), and both
    Pass 1 and the cache-key resolver need the same bodies, so it lives here once
    rather than once per caller (CLAUDE.md deduplication rule).
    """
    call_re = re.compile(r'\b(?:it|test)\s*\(')
    marker_re = re.compile(
        r'\[proof:' + re.escape(feature_name) + r':([^:\]]+):([^:\]]+)'
    )
    n = len(content)
    i = 0
    while i < n:
        m = call_re.search(content, i)
        if not m:
            break
        # Skip whitespace after the '(' and require a string-literal title.
        j = m.end()
        while j < n and content[j] in ' \t\r\n':
            j += 1
        if j >= n or content[j] not in '"\'`':
            i = m.end()
            continue
        title, after_title = _read_js_string(content, j)
        marker = marker_re.search(title)
        if not marker:
            i = after_title
            continue
        body, after_body = _find_test_body(content, after_title)
        if body is None:
            # No block body to inspect: cannot run body checks; skip.
            i = after_title
            continue
        i = after_body
        yield marker.group(1), marker.group(2), title, body


def check_js(filepath, feature_name, rule_descs=None):
    """Run JS/TS test checks. Returns list of proof result dicts.

    `rule_descs` is accepted so every checker in the extension table has one
    signature; JS has no rule-aware check to spend it on.
    """
    return _run_body_checks(filepath, feature_name, 'js')


# ---------------------------------------------------------------------------
# C# / .NET (xUnit / NUnit / MSTest) checks
# ---------------------------------------------------------------------------

# C#, PHP and C all delimit a test body with braces and all hide braces inside
# strings and comments, so one scanner serves the three of them. The caller says
# which line-comment prefixes its language has and whether it has C#'s verbatim
# `@"..."` string; nothing else differs (CLAUDE.md deduplication rule).
_CSHARP_LINE_COMMENTS = ('//',)
_PHP_LINE_COMMENTS = ('//', '#')


def _skip_c_like_noncode(content, j, line_comment_prefixes=_CSHARP_LINE_COMMENTS,
                         verbatim_strings=True):
    """Index just past the comment, string or char literal starting at content[j].

    None when content[j] starts none of them, so the caller reads it as code.
    Escapes are backslash escapes, except inside a C# verbatim string where `""`
    escapes a quote.

    Not tracked: PHP heredoc/nowdoc (`<<<EOT ... EOT;`) and C# raw string
    literals. A brace inside one of those is counted as code, which can end a
    scanned body early, so a checker reading these bodies can only ever see less
    of the test than the author wrote.
    """
    n = len(content)
    c = content[j]
    for prefix in line_comment_prefixes:
        if content.startswith(prefix, j):
            nl = content.find('\n', j)
            return n if nl < 0 else nl
    if c == '/' and content[j + 1:j + 2] == '*':
        e = content.find('*/', j + 2)
        return n if e < 0 else e + 2
    if verbatim_strings and c == '@' and content[j + 1:j + 2] == '"':
        j += 2
        while j < n:
            if content[j] == '"':
                if content[j + 1:j + 2] == '"':
                    j += 2
                    continue
                return j + 1
            j += 1
        return n
    if c == '"' or c == "'":  # string, interpolated string, or char literal
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


def _read_c_like_balanced(content, i, opener, closer,
                          line_comment_prefixes=_CSHARP_LINE_COMMENTS,
                          verbatim_strings=True):
    """content[i] is `opener`. Return (inner_text, index_after_matching_close).

    Skips strings, char literals and comments so their contents never affect
    bracket depth. Unterminated input returns everything to the end of the file.
    """
    n = len(content)
    depth = 0
    j = i
    start_inner = i + 1
    while j < n:
        skipped = _skip_c_like_noncode(content, j, line_comment_prefixes,
                                       verbatim_strings)
        if skipped is not None:
            j = skipped
            continue
        c = content[j]
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return content[start_inner:j], j + 1
        j += 1
    return content[start_inner:j], j  # unterminated


def _read_csharp_balanced(content, i, opener, closer):
    """The C# reader: `_read_c_like_balanced` with C#'s comments and strings."""
    return _read_c_like_balanced(content, i, opener, closer)


def _strip_c_like_comments(text, line_comment_prefixes=_CSHARP_LINE_COMMENTS,
                           verbatim_strings=True):
    """`text` with every comment replaced by a space, strings left untouched.

    A checker that searches a body for assertion syntax must not read the
    author's prose: a `// no assert(true) here` comment would otherwise be a
    tautology, and a `// no throw = pass` comment an assertion. Strings are kept
    because an assertion's arguments are compared as written.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        is_comment = (text[i] == '/' and text[i + 1:i + 2] == '*') or any(
            text.startswith(prefix, i) for prefix in line_comment_prefixes)
        end = _skip_c_like_noncode(text, i, line_comment_prefixes, verbatim_strings)
        if end is None:
            out.append(text[i])
            i += 1
            continue
        out.append(' ' if is_comment else text[i:end])
        i = end
    return ''.join(out)


def _find_csharp_body(content, i):
    """From index i (just after a [Trait(...)] marker), locate the test method's
    { body }. Skips trailing attributes ([Fact], [InlineData(...)]) and the
    method signature/parameter list. Returns (body_text, index_after_body,
    method_name), or (None, i, method_name) for expression-bodied or abstract
    members with no block body.
    """
    n = len(content)
    method_name = None
    while i < n:
        c = content[i]
        if c == '/' and content[i + 1:i + 2] == '/':
            nl = content.find('\n', i)
            i = n if nl < 0 else nl
            continue
        if c == '/' and content[i + 1:i + 2] == '*':
            e = content.find('*/', i + 2)
            i = n if e < 0 else e + 2
            continue
        if c == '[':  # another attribute or an array — skip balanced [...]
            _, i = _read_csharp_balanced(content, i, '[', ']')
            continue
        if c == '(':  # the identifier just before this paren is the method name
            k = i - 1
            while k >= 0 and content[k].isspace():
                k -= 1
            end = k + 1
            while k >= 0 and (content[k].isalnum() or content[k] == '_'):
                k -= 1
            method_name = content[k + 1:end] or method_name
            _, i = _read_csharp_balanced(content, i, '(', ')')
            continue
        if content.startswith('=>', i):
            return None, i, method_name  # expression-bodied member — no block
        if c == ';':
            return None, i, method_name  # no body
        if c == '{':
            body, after = _read_csharp_balanced(content, i, '{', '}')
            return body, after, method_name
        i += 1
    return None, i, method_name


def _iter_csharp_proof_bodies(content, feature_name):
    """Yield (proof_id, rule_id, test_name, body) for every marked C# test method.

    The marker regex and the body finder are shared by Pass 1 and the cache-key
    resolver, so they live here once (CLAUDE.md deduplication rule).
    """
    marker_re = re.compile(
        r'\[\s*Trait\s*\(\s*"PurlinProof"\s*,\s*"'
        + re.escape(feature_name)
        + r':([^:"\]]+):([^:"\]]+):[^"]*"\s*\)\s*\]'
    )
    for m in marker_re.finditer(content):
        body, _after, method_name = _find_csharp_body(content, m.end())
        if body is None:
            # No block body to inspect (expression-bodied or abstract): skip.
            continue
        yield m.group(1), m.group(2), (method_name or m.group(1))[:60], body


def check_csharp(filepath, feature_name, rule_descs=None):
    """Run C#/.NET (xUnit/NUnit/MSTest) test checks. Returns list of proof dicts.

    Parses `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]` markers, finds
    each marked test method's body, and applies assert-true / no-assertion
    detection. Recognizes xUnit `Assert.*`, NUnit `Assert.That`, MSTest `Assert.*`,
    FluentAssertions `.Should()`, and Playwright `Expect(...).To*Async()` as assertions.
    """
    return _run_body_checks(filepath, feature_name, 'csharp')


# ---------------------------------------------------------------------------
# Constant-expression test, shared by the PHP and C checkers
# ---------------------------------------------------------------------------

_CONST_EXPR_LITERAL_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|/\*.*?\*/|//[^\n]*", re.DOTALL)
_CONST_EXPR_WORD_RE = re.compile(r'[A-Za-z_]\w*')
_CONST_EXPR_WORDS = frozenset({'true', 'false', 'null'})


def _is_constant_expression(text):
    """True when `text` is built only from literals, operators and parentheses.

    String and char literals are removed first, then any remaining word that is
    not `true`, `false` or `null` means the expression reads something: a
    variable, a call, a column. `1 == 1` and `'a' == 'a'` are constant;
    `validate(-1) == 0` and `$result` are not.

    Deliberately conservative in one direction: a hexadecimal or suffixed
    numeric literal (`0x1F`, `1UL`) leaves a word behind and so reads as
    non-constant. That under-reports a tautology, which is the safe error for a
    check whose `fail` verdict is HOLLOW with no override.
    """
    stripped = _CONST_EXPR_LITERAL_RE.sub(' ', text)
    if '$' in stripped:  # a PHP variable
        return False
    for word in _CONST_EXPR_WORD_RE.findall(stripped):
        if word.lower() not in _CONST_EXPR_WORDS:
            return False
    return bool(text.strip())


# ---------------------------------------------------------------------------
# PHP (PHPUnit-style) checks
# ---------------------------------------------------------------------------

# Copied byte for byte from the marker regex in scripts/proof/phpunit_purlin.php,
# `(?:public\s+)?function` quirk included, so the function Pass 1 reads is the
# function the plugin executed and recorded. Groups: feature, proof id, rule id,
# tier, declared platforms, function name.
_PHP_MARKER_RE = re.compile(
    r'@purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:\s+(?!on\()(\w+))?'
    r'(?:\s+on\(([^)]*)\))?.*?\n\s*(?:public\s+)?function\s+(\w+)',
    re.DOTALL)

# An assertion, in any of the shapes PHPUnit and plain PHP tests use. A test
# that raises on failure asserts through `throw`, which is how the shipped
# plugin decides pass or fail, so `throw` counts.
_PHP_ASSERTION_RE = re.compile(
    r'->\s*(?:assert\w*|fail|expectException\w*)\s*\('
    r'|::\s*(?:assert\w*|fail|expectException\w*)\s*\('
    r'|\bassert\s*\('
    r'|\bexpect\s*\('
    r'|\bthrow\b')

_PHP_LITERAL = (r"(?:'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\""
                r"|[+-]?\d+(?:\.\d+)?|true|false|null)")
_PHP_TAUTOLOGY_RES = (
    (re.compile(r'\bassertTrue\s*\(\s*true\s*[,)]'), 'assertTrue(true)'),
    (re.compile(r'\bassertFalse\s*\(\s*false\s*[,)]'), 'assertFalse(false)'),
    (re.compile(r'\bassertNotFalse\s*\(\s*true\s*[,)]'), 'assertNotFalse(true)'),
    (re.compile(r'(?<!\w)assert\s*\(\s*true\s*[,)]'), 'assert(true)'),
)
_PHP_IDENTICAL_ARGS_RE = re.compile(
    r'\bassert(?:Same|Equals)\s*\(\s*(' + _PHP_LITERAL + r')\s*,\s*('
    + _PHP_LITERAL + r')\s*[,)]')
_PHP_IF_RE = re.compile(r'(?<!\w)if\s*\(')


def _find_php_body(content, i):
    """The `{ ... }` body of the function whose name ends at `i`, or None.

    None for an abstract or interface method, which has no body to read.
    """
    n = len(content)
    while i < n and content[i] not in '({;':
        i += 1
    if i >= n or content[i] == ';':
        return None
    if content[i] == '(':  # the parameter list
        _params, i = _read_c_like_balanced(content, i, '(', ')',
                                           _PHP_LINE_COMMENTS, verbatim_strings=False)
    while i < n and content[i] != '{':  # a return type may sit between ) and {
        if content[i] == ';':
            return None
        i += 1
    if i >= n:
        return None
    body, _after = _read_c_like_balanced(content, i, '{', '}',
                                         _PHP_LINE_COMMENTS, verbatim_strings=False)
    return body


def _iter_php_proof_bodies(content, feature_name):
    """Yield (proof_id, rule_id, test_name, body) for every marked PHP test.

    Pass 1 and the cache-key extractor read the same bodies, so the marker regex
    and the body finder live here once (CLAUDE.md deduplication rule).
    """
    for m in _PHP_MARKER_RE.finditer(content):
        if m.group(1) != feature_name:
            continue
        body = _find_php_body(content, m.end())
        if body is None:
            continue
        yield m.group(2), m.group(3), m.group(6), body


def _php_constant_guard(body):
    """True when a constant `if` guards a throw: `if (true !== true) throw ...`.

    The guard never fires, so the test cannot fail, but `throw` in the body
    still satisfies the assertion search below. Only an `if` whose condition is
    a constant expression counts, so `if (!$r) throw ...` is a real assertion.
    """
    for m in _PHP_IF_RE.finditer(body):
        open_paren = m.end() - 1
        cond, after = _read_c_like_balanced(body, open_paren, '(', ')',
                                            _PHP_LINE_COMMENTS, verbatim_strings=False)
        if not _is_constant_expression(cond):
            continue
        while after < len(body) and body[after] in ' \t\r\n':
            after += 1
        if after < len(body) and body[after] == '{':
            guarded, _end = _read_c_like_balanced(body, after, '{', '}',
                                                  _PHP_LINE_COMMENTS,
                                                  verbatim_strings=False)
        else:
            end = body.find(';', after)
            guarded = body[after:] if end < 0 else body[after:end]
        if re.search(r'\bthrow\b', guarded):
            return True
    return False


def _php_tautology(body):
    """The reason a PHP test body asserts nothing falsifiable, or None."""
    for pattern, shown in _PHP_TAUTOLOGY_RES:
        if pattern.search(body):
            return f'{shown} is tautological'
    for m in _PHP_IDENTICAL_ARGS_RE.finditer(body):
        if m.group(1) == m.group(2):
            return (f'assertSame/assertEquals of two identical literals '
                    f'({m.group(1)}) is tautological')
    if _php_constant_guard(body):
        return 'a constant `if` guard on a throw can never fire'
    return None


def check_php(filepath, feature_name, rule_descs=None):
    """Run PHP (PHPUnit-style) test checks. Returns list of proof result dicts.

    Reads the `/** @purlin feature PROOF-N RULE-N */` docblocks the shipped
    plugin reads, finds each marked function's body, and applies assert-true and
    no-assertion detection. Known limit, shared with C#: a test that delegates
    every assertion to a helper method reads as `no_assertions` here.
    """
    return _run_body_checks(filepath, feature_name, 'php')


# ---------------------------------------------------------------------------
# SQL (sqlite3) checks
# ---------------------------------------------------------------------------

# The same marker regex and the same block delimiting as scripts/proof/sql_purlin.sh:
# a block runs from its marker to the next marker or to the end of the file.
_SQL_MARKER_RE = re.compile(
    r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:[ \t]+(?!on\()(\w+))?'
    r'(?:[ \t]+on\(([^)]*)\))?',
    re.MULTILINE)
_SQL_TEST_NAME_RE = re.compile(r'^-- Test:\s*(.+)', re.MULTILINE)

# `SELECT 'PASS';` as a whole statement: no WHERE, so nothing decides it.
_SQL_PLAIN_PASS_RE = re.compile(r"SELECT\s+'PASS'\s*;?[ \t]*$",
                                re.IGNORECASE | re.MULTILINE)
_SQL_CASE_PASS_RE = re.compile(r"CASE\s+WHEN\s+(.*?)\s+THEN\s+'PASS'",
                               re.IGNORECASE | re.DOTALL)
_SQL_SELECT_RE = re.compile(r'\bSELECT\b', re.IGNORECASE)
_SQL_STRING_RE = re.compile(r"'(?:[^']|'')*'")
_SQL_WORD_RE = re.compile(r'[A-Za-z_]\w*')
# Words a predicate may use and still decide nothing: they are operators and
# literals, not data. Any other identifier reads a column, calls a function or
# opens a subquery, so the predicate depends on something.
_SQL_OPERATOR_WORDS = frozenset({
    'and', 'or', 'not', 'is', 'null', 'in', 'like', 'glob', 'between',
    'true', 'false', 'escape',
})


def _sql_executable(block):
    """The block with its `--` comment lines removed, as the plugin runs it."""
    return '\n'.join(l for l in block.split('\n')
                     if not l.strip().startswith('--')).strip()


def _sql_strip_comments(sql):
    """`sql` with every `--` comment removed, string literals left untouched.

    `_sql_executable` drops whole comment lines, exactly as the shipped plugin
    does, but a trailing `-- then SELECT 'PASS'` survives it and sqlite ignores
    it. Reading one as SQL would flag a block that never runs it.
    """
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
    """True when a CASE predicate decides nothing: no identifier but operators."""
    stripped = _SQL_STRING_RE.sub(' ', predicate)
    for word in _SQL_WORD_RE.findall(stripped):
        if word.lower() not in _SQL_OPERATOR_WORDS:
            return False
    return bool(predicate.strip())


def _iter_sql_proof_blocks(content, feature_name):
    """Yield (proof_id, rule_id, test_name, block) for every marked SQL block.

    `block` is the raw text between markers, comments included: it is what the
    cache-key extractor keys on, and `_sql_executable` derives what sqlite3 sees.
    Shared by Pass 1 and the extractor (CLAUDE.md deduplication rule).
    """
    markers = list(_SQL_MARKER_RE.finditer(content))
    for i, m in enumerate(markers):
        if m.group(1) != feature_name:
            continue
        end = markers[i + 1].start() if i + 1 < len(markers) else len(content)
        block = content[m.end():end].strip()
        name_match = _SQL_TEST_NAME_RE.search(block)
        test_name = name_match.group(1).strip() if name_match else m.group(2)
        yield m.group(2), m.group(3), test_name, block


def _sql_tautology(sql_exec):
    """The reason the block's first PASS is unconditional, or None.

    Only the first `'PASS'` producer is judged: sqlite3 prints rows in statement
    order and the plugin reads the first line, so a later unconditional
    `SELECT 'PASS'` cannot rescue a block whose first check printed FAIL.
    """
    candidates = []
    for m in _SQL_PLAIN_PASS_RE.finditer(sql_exec):
        candidates.append((m.start(), "an unconditional SELECT 'PASS'"))
    for m in _SQL_CASE_PASS_RE.finditer(sql_exec):
        reason = None
        if _sql_constant_predicate(m.group(1)):
            reason = (f"CASE WHEN {' '.join(m.group(1).split())} THEN 'PASS' "
                      'compares constants')
        candidates.append((m.start(), reason))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def check_sql(filepath, feature_name, rule_descs=None):
    """Run SQL (sqlite3) test checks. Returns list of proof result dicts.

    A block passes at runtime when its output starts with `PASS`, so the checks
    here are about what produces that word: an unconditional `SELECT 'PASS'` or
    a `CASE WHEN` whose predicate compares constants proves nothing about the
    schema. A predicate naming any column, function or subquery is left alone.
    """
    return _run_body_checks(filepath, feature_name, 'sql')


# ---------------------------------------------------------------------------
# C checks
# ---------------------------------------------------------------------------

# purlin_proof(feature, id, rule, passed, test_name, test_file, tier) and its
# purlin_proof_on(..., platforms) sibling, per scripts/proof/c_purlin.h. The
# `\s*\(` is what keeps purlin_proof_finish() out of the scan.
_C_CALL_RE = re.compile(r'\bpurlin_proof(?:_on)?\s*\(')
_C_STRING_RE = re.compile(r'^"(?:[^"\\]|\\.)*"$')
_C_LINE_COMMENTS = ('//',)
_C_PROOF_MIN_ARGS = 7


def _split_c_arguments(argtext):
    """`argtext` split on its depth-0 commas, each argument stripped.

    Strings, char literals, comments and nested brackets are skipped, so a
    string argument holding a comma or a close paren stays one argument.
    """
    args = []
    depth = 0
    start = 0
    i = 0
    n = len(argtext)
    while i < n:
        skipped = _skip_c_like_noncode(argtext, i, _C_LINE_COMMENTS,
                                       verbatim_strings=False)
        if skipped is not None:
            i = skipped
            continue
        c = argtext[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 0:
            args.append(argtext[start:i])
            start = i + 1
        i += 1
    args.append(argtext[start:])
    return [a.strip() for a in args]


def _c_string_value(arg):
    """The text of a C string-literal argument, or None when it is not one."""
    if not _C_STRING_RE.fullmatch(arg):
        return None
    return arg[1:-1]


def _c_top_level_block(content, pos):
    """The outermost `{ ... }` block containing `pos`, or None.

    That is the enclosing function body for a call written at any nesting depth
    inside it. Keying a C proof on the whole block over-invalidates its cached
    grade when an unrelated line of `main` moves, which is the safe direction:
    the grade is recomputed rather than wrongly reused.
    """
    depth = 0
    start = None
    i = 0
    n = len(content)
    while i < n:
        skipped = _skip_c_like_noncode(content, i, _C_LINE_COMMENTS,
                                       verbatim_strings=False)
        if skipped is not None:
            i = skipped
            continue
        c = content[i]
        if c == '{':
            if depth == 0:
                start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth <= 0:
                if start is not None and start <= pos <= i:
                    return content[start:i + 1]
                depth = 0
                start = None
        i += 1
    return None


def _iter_c_proof_bodies(content, feature_name):
    """Yield (proof_id, rule_id, test_name, passed_arg, block) per C proof call.

    `passed_arg` is the call's fourth argument, the one the harness records as
    pass or fail; `block` is the enclosing top-level block, which is what the
    cache-key extractor keys on. Shared by Pass 1 and the extractor (CLAUDE.md
    deduplication rule).
    """
    for m in _C_CALL_RE.finditer(content):
        open_paren = m.end() - 1
        argtext, _after = _read_c_like_balanced(content, open_paren, '(', ')',
                                                _C_LINE_COMMENTS,
                                                verbatim_strings=False)
        args = _split_c_arguments(argtext)
        if len(args) < _C_PROOF_MIN_ARGS:
            continue
        if _c_string_value(args[0]) != feature_name:
            continue
        proof_id = _c_string_value(args[1])
        rule_id = _c_string_value(args[2])
        if not proof_id or not rule_id:
            continue
        test_name = _c_string_value(args[4])
        if test_name is None:
            test_name = args[4][:60]
        block = _c_top_level_block(content, m.start())
        yield proof_id, rule_id, test_name, args[3], block


def check_c(filepath, feature_name, rule_descs=None):
    """Run C test checks. Returns list of proof result dicts.

    One check only, and deliberately so: the harness records whatever the call's
    fourth argument evaluates to, so the single thing a regex can prove about a
    C proof is that the argument is a constant expression (`1`, `1 == 1`) and
    the recorded status therefore cannot depend on the code under test. A
    variable or a call there is an assertion computed before the call, which
    this checker passes without judging. There is no no-assertion check: a C
    test with no assertion is one whose `passed` argument is constant, which the
    constant check already catches.
    """
    return _run_body_checks(filepath, feature_name, 'c')


# ---------------------------------------------------------------------------
# The one brace-body driver, and the table the five languages differ in (RULE-52)
#
# JS/TS, C#, PHP, SQL and C all run the same Pass 1: read the file, walk the
# marked proof bodies, fail the first one that is tautological, fail the next
# that asserts nothing, pass the rest. Only six things differ per language, and
# they are the six columns of `_BODY_CHECKS` below. `check_js`, `check_csharp`,
# `check_php`, `check_sql` and `check_c` stay as named wrappers because the
# extension table and every proof call them by name.
# ---------------------------------------------------------------------------

_JS_TAUTOLOGY_RE = re.compile(
    r'expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)')
_JS_EXPECT_RE = re.compile(r'expect\s*\(')

_CSHARP_TAUTOLOGY_RES = (
    re.compile(r'Assert\s*\.\s*(?:True|IsTrue)\s*\(\s*true\s*\)'),
    re.compile(r'Assert\s*\.\s*(?:Equal|AreEqual)\s*\(\s*true\s*,\s*true\s*\)'),
)
# xUnit/NUnit/MSTest `Assert.`, FluentAssertions `.Should(`, Moq `.Verify(`, and
# Playwright's Expect(...)/Assertions.Expect(...) chained to a To<Matcher>Async()
# call (ToBeVisibleAsync, ToHaveTextAsync, ToContainTextAsync, ...). Playwright
# needs both tokens, so a bare Expect(x) with no matcher is still flagged and a
# plain LINQ `.ToListAsync()` with no Expect is not mistaken for an assertion.
_CSHARP_ASSERT_RE = re.compile(r'\bAssert\s*\.')
_CSHARP_SHOULD_RE = re.compile(r'\.\s*Should\s*\(')
_CSHARP_VERIFY_RE = re.compile(r'\.\s*Verify\s*\(')
_CSHARP_EXPECT_RE = re.compile(r'\bExpect\s*\(')
_CSHARP_MATCHER_RE = re.compile(r'\.\s*To\w+Async\s*\(')


def _same(value):
    """Identity: this language neither strips its bodies nor reshapes its names."""
    return value


def _js_tautology(body):
    return ('expect(true).toBe(true) is tautological'
            if _JS_TAUTOLOGY_RE.search(body) else None)


def _js_has_assertion(body):
    return bool(_JS_EXPECT_RE.search(body))


def _csharp_tautology(body):
    return ('Assert.True(true) is tautological'
            if any(r.search(body) for r in _CSHARP_TAUTOLOGY_RES) else None)


def _csharp_has_assertion(body):
    return bool(_CSHARP_ASSERT_RE.search(body)
                or _CSHARP_SHOULD_RE.search(body)
                or _CSHARP_VERIFY_RE.search(body)
                or (_CSHARP_EXPECT_RE.search(body)
                    and _CSHARP_MATCHER_RE.search(body)))


def _php_strip(raw_body):
    """The author's comments are prose, not code: `// no throw = pass` is not an
    assertion and `// never assert(true)` is not a tautology."""
    return _strip_c_like_comments(raw_body, _PHP_LINE_COMMENTS,
                                  verbatim_strings=False)


def _php_has_assertion(body):
    return bool(_PHP_ASSERTION_RE.search(body))


def _sql_executable_statements(block):
    return _sql_strip_comments(_sql_executable(block))


def _sql_tautology_reason(sql_exec):
    tautology = _sql_tautology(sql_exec)
    return f'{tautology} passes whatever the data holds' if tautology else None


def _sql_has_assertion(sql_exec):
    return bool(_SQL_SELECT_RE.search(sql_exec))


def _iter_c_proof_subjects(content, feature_name):
    """(proof_id, rule_id, test_name, passed_arg) per `purlin_proof` call. C is
    the one language whose subject is not a body: the checker judges the recorded
    `passed` argument, so the enclosing block that `_iter_c_proof_bodies` also
    yields (which the cache key wants) is dropped here."""
    for proof_id, rule_id, test_name, passed_arg, _block in _iter_c_proof_bodies(
            content, feature_name):
        yield proof_id, rule_id, test_name, passed_arg


def _c_constant_passed(passed_arg):
    if not _is_constant_expression(passed_arg):
        return None
    return (f'purlin_proof passed argument `{passed_arg}` is a '
            'constant expression, so the recorded status cannot '
            'depend on the code under test')


# `subjects(content, feature)` yields (proof_id, rule_id, raw_name, subject);
# `prepare` turns the subject into the text both predicates read; `tautology`
# returns the reason the proof is hollow, or None; `has_assertion` is None for a
# language with no no-assertion check (C, whose constant check already covers
# it); `test_name` shapes the name the iterator produced.
_BodyLang = collections.namedtuple(
    '_BodyLang',
    'subjects prepare tautology has_assertion no_assertion_reason test_name')


_BODY_CHECKS = {
    'js': _BodyLang(
        subjects=_iter_js_proof_bodies,
        prepare=_same,
        tautology=_js_tautology,
        has_assertion=_js_has_assertion,
        no_assertion_reason='test function has no expect() calls',
        test_name=lambda title: title[:60],
    ),
    'csharp': _BodyLang(
        subjects=_iter_csharp_proof_bodies,
        prepare=_same,
        tautology=_csharp_tautology,
        has_assertion=_csharp_has_assertion,
        no_assertion_reason=(
            'test method has no Assert./.Should()/.Verify()/Expect(...).To*Async() call'),
        test_name=_same,
    ),
    'php': _BodyLang(
        subjects=_iter_php_proof_bodies,
        prepare=_php_strip,
        tautology=_php_tautology,
        has_assertion=_php_has_assertion,
        no_assertion_reason='test function has no assert*/expect*/throw call',
        test_name=_same,
    ),
    'sql': _BodyLang(
        subjects=_iter_sql_proof_blocks,
        prepare=_sql_executable_statements,
        tautology=_sql_tautology_reason,
        has_assertion=_sql_has_assertion,
        no_assertion_reason='proof block runs no SELECT, so it observes nothing',
        test_name=_same,
    ),
    'c': _BodyLang(
        subjects=_iter_c_proof_subjects,
        prepare=_same,
        tautology=_c_constant_passed,
        has_assertion=None,
        no_assertion_reason='',
        test_name=_same,
    ),
}


def _run_body_checks(filepath, feature_name, lang):
    """Pass 1 for one brace-body language. Returns list of proof result dicts.

    The shape the five share: read the file once (RULE-51), walk the proof
    bodies the language's iterator finds, and report the first defect each one
    has, tautology before missing assertion, or pass.
    """
    spec = _BODY_CHECKS[lang]
    content = _file_text(filepath)
    results = []
    for proof_id, rule_id, raw_name, subject in spec.subjects(content, feature_name):
        judged = spec.prepare(subject)
        base = {'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': spec.test_name(raw_name)}
        tautology = spec.tautology(judged)
        if tautology:
            results.append(dict(base, status='fail', check='assert_true',
                                reason=tautology, literal=True))
            continue
        if spec.has_assertion is not None and not spec.has_assertion(judged):
            results.append(dict(base, status='fail', check='no_assertions',
                                reason=spec.no_assertion_reason))
            continue
        results.append(dict(base, status='pass',
                            reason='structural checks passed'))
    return results


# Build-output / vendored directories that never contain authored test source.
_SOURCE_SCAN_SKIP_DIRS = {'bin', 'obj', 'node_modules', '.git', '.purlin', 'dist', 'build'}


def resolve_test_file_from_name(test_name, project_root, ext='.cs'):
    """Resolve a test's source file from its fully-qualified test_name when the
    proof's test_file is empty.

    Some runners cannot surface a source path: the xUnit logger emits
    `MakeRelative(_root, tc.CodeFilePath ?? "")`, and under `dotnet test`
    CodeFilePath is often null (no source info / full PDBs), so test_file is "".
    The fully-qualified test_name (e.g. `Ns.Sub.AuthLogicTests.Evaluate_NullRow`)
    still identifies the declaring type, so we derive the type (the segment before
    the final `.method`) and search the project's `ext` files for its declaration.

    Returns the repo-relative POSIX path of the best match — preferring a file
    whose stem equals the type name — or '' if no declaration is found. Skips
    build-output and vendored directories.
    """
    if not test_name:
        return ''
    parts = test_name.split('.')
    if len(parts) < 2:
        return ''
    type_name = parts[-2]  # final segment is the method; the one before is the type
    if not type_name:
        return ''
    decl = re.compile(r'\b(?:class|struct|record|interface)\s+' + re.escape(type_name) + r'\b')
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
    matches.sort()  # determinism across platforms
    best = next((m for m in matches
                 if os.path.splitext(os.path.basename(m))[0] == type_name), matches[0])
    return os.path.relpath(best, project_root).replace(os.sep, '/')


# ---------------------------------------------------------------------------
# The extension table
#
# One table decides which language reads a test file. `analyze_test_file`
# dispatches from it, `_test_bodies` branches on the same sets, and
# `_TEST_CODE_EXTENSIONS` is derived from it rather than listed again, so an
# extension cannot reach one of the three and be missed by the others. There is
# no fallback branch: an extension absent from the table yields [] rather than
# being read by whichever checker happened to be last in an if-chain, which is
# how `.mjs` and `.cjs` were once handed to nobody and `.rb` to the JS scanner.
# ---------------------------------------------------------------------------

_JS_EXTENSIONS = frozenset({'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx'})
_C_EXTENSIONS = frozenset({'.c', '.h'})

_CHECKERS = dict(
    [('.py', check_python), ('.sh', check_shell), ('.cs', check_csharp),
     ('.php', check_php), ('.sql', check_sql)]
    + [(e, check_js) for e in sorted(_JS_EXTENSIONS)]
    + [(e, check_c) for e in sorted(_C_EXTENSIONS)]
)

# Every extension Pass 1 can read.
_CHECKER_EXTENSIONS = frozenset(_CHECKERS)

# Every extension whose test code this module can also extract for a cache key.
# Shell is the one checked language with no extractor: its proofs are keyed on
# rule text and proof description alone and the cache entry records
# `inputs.test_verifiable: false` rather than pretending a test edit would
# invalidate the grade.
_TEST_CODE_EXTENSIONS = _CHECKER_EXTENSIONS - {'.sh'}


def analyze_test_file(test_file, feature_name, rule_descs=None):
    """Dispatch a test file to the language checker matching its extension.

    Returns the list of proof result dicts, or [] for an extension no checker
    reads (a custom plugin's language). A file whose language has a checker but
    whose markers it cannot find returns [] too: the caller distinguishes the
    two through `_CHECKER_EXTENSIONS`.
    """
    ext = os.path.splitext(test_file)[1].lower()
    checker = _CHECKERS.get(ext)
    if checker is None:
        return []
    return checker(test_file, feature_name, rule_descs)


# ---------------------------------------------------------------------------
# Spec reading (for mock_target_match)
# ---------------------------------------------------------------------------

_RULE_LINE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)

def _read_rule_descriptions(spec_path):
    """Read rule descriptions from a spec file."""
    if not spec_path or not os.path.isfile(spec_path):
        return {}
    content = _file_text(spec_path)
    return {m.group(1): m.group(2).strip() for m in _RULE_LINE_RE.finditer(content)}


# A tier tag is metadata appended after the description: ` @e2e`, ` @manual(...)`.
# It must NOT match a description whose prose merely ends in an @word, e.g.
    # "verify spec_format.md documents @integration, @e2e, and @windows", which was
# read as tier=windows and had its last clause silently truncated. Requiring that
# the tag not follow a list connector (',' 'and' 'or') separates the two cases.
#
# purlin_server.py carries an identical pattern. The two modules are independent
# (the MCP server does not import this CLI), so they are kept in step by
# schema_spec_format PROOF-9 rather than by a shared import.
_TIER_TAG_BODY = r'(?<!\band)(?<!\bor)(?<!,)\s+@(\w+)(?:\(([^)]*)\))?\s*$'
_TIER_TAG_RE = re.compile(_TIER_TAG_BODY)

# A platform id becomes a proof filename, a workflow name and an environment
# variable, so the charset is what all three accept (schema_spec_format RULE-10).
_PLATFORM_ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')

# Proof-file discovery (schema_proof_format RULE-1/RULE-8). Character-identical in
# scripts/audit/static_checks.py. Groups: feature stem, tier, optional platform id.
_PROOF_FILE_RE = re.compile(r'^(.+)\.proofs-([A-Za-z0-9_]+)(?:@([a-z0-9][a-z0-9-]*))?\.json$')

# A file whose tier is really a platform (the pre-Format-Version-5 spelling
# `<feature>.proofs-windows.json`) is read as `unit@windows`; the caller is told
# so it can name the rename that `purlin:init --update` performs.
_LEGACY_PLATFORM_TIERS = frozenset({'windows'})


def _proof_file_parts(basename):
    """(feature_stem, tier, platform, legacy) for a proof filename, or None.

    `platform` is None for an agnostic file. `legacy` is True when the filename
    carried a platform where its tier belongs, in which case `tier` is already
    `unit` and `platform` is that name.
    """
    m = _PROOF_FILE_RE.match(basename)
    if not m:
        return None
    stem, tier, plat = m.group(1), m.group(2), m.group(3)
    if plat is None and tier in _LEGACY_PLATFORM_TIERS:
        return stem, 'unit', tier, True
    return stem, tier, plat, False


def _split_proof_tags(desc):
    """Split the trailing tags off a proof description.

    Returns (clean_desc, tier, platforms, warnings). Tags are read right to
    left: `@on(<platform-id>[, ...])` names the platforms the proof must be
    proved on, any other `@<name>` is the tier. At most one of each, in either
    order; a second tier tag or a second `@on` stops the scan and stays in the
    description, with a warning. `@on` alone means tier `unit`. `@on` on a
    `@manual` proof is dropped: a human stamp is not a platform result. A bare
    `@windows` tier is read as `@unit @on(windows)` with a warning naming the
    rewrite (one release of compatibility). Platform ids outside
    `[a-z0-9][a-z0-9-]*` are dropped with a warning; the survivors keep their
    order, deduplicated. `platforms` is `[]` for a platform-agnostic proof.

    The sibling module (purlin_server.py / static_checks.py) carries a
    character-identical copy of this helper and of _TIER_TAG_BODY. The two are
    independent by design: a shared import would couple the CLI to the server.
    schema_spec_format PROOF-9 keeps them in step.
    """
    desc = desc.rstrip()
    tier = None
    platforms = None
    warnings = []
    while True:
        m = _TIER_TAG_RE.search(desc)
        if not m:
            break
        name, args = m.group(1), m.group(2)
        if name == 'on':
            if platforms is not None:
                warnings.append('a second @on(...) precedes the trailing one; '
                                'only the trailing @on is read')
                break
            platforms = []
            ids = [p.strip() for p in (args or '').split(',') if p.strip()]
            if not ids:
                warnings.append('@on() names no platform: write @on(<platform-id>)')
            for pid in ids:
                if not _PLATFORM_ID_RE.match(pid):
                    warnings.append(f'platform id {pid!r} is not [a-z0-9][a-z0-9-]*; '
                                    'dropped (lower-case letters, digits and - only)')
                elif pid not in platforms:
                    platforms.append(pid)
        else:
            if tier is not None:
                warnings.append(f'a second tier tag @{name} precedes @{tier}; '
                                f'only the trailing tier tag is read')
                break
            tier = name
        desc = desc[:m.start()].rstrip()
    if tier == 'windows':
        warnings.append('@windows is a platform, not a tier: write @unit @on(windows)')
        tier = 'unit'
        if platforms is None:
            platforms = ['windows']
    if tier is None:
        tier = 'unit'
    if tier == 'manual' and platforms is not None:
        warnings.append('@on(...) on a @manual proof is ignored: '
                        'a human stamp is not a platform result')
        platforms = None
    return desc, tier, platforms or [], warnings


_PROOF_DESC_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)',
    re.MULTILINE,
)



def _read_proof_descriptions(spec_path):
    """Read proof descriptions from a spec file's ## Proof section.

    Returns list of dicts with proof_id, rule_ids, and description.
    """
    if not spec_path or not os.path.isfile(spec_path):
        return []
    content = _file_text(spec_path)
    proof_section_match = re.search(
        r'^## Proof\s*\n(.*?)(?=^## |\Z)',
        content, re.MULTILINE | re.DOTALL,
    )
    if not proof_section_match:
        return []
    proof_section = proof_section_match.group(1)
    results = []
    for m in _PROOF_DESC_RE.finditer(proof_section):
        desc = _split_proof_tags(m.group(3))[0]
        results.append({
            'proof_id': m.group(1),
            'rule_ids': m.group(2),
            'description': desc,
        })
    return results


# ---------------------------------------------------------------------------
# Pass D: Proof Design (deterministic half)
#
# Grades a proof DESCRIPTION against its rule. Reads no test code, so it runs on
# a spec-only project. The detectors are the authoring rules from
# references/spec_quality_guide.md made executable ("Recognizing Level 1 proofs",
# "Writing Proof Descriptions", "Edge Case Proof Specificity", "E2E proof
# descriptions").
#
# Deliberately conservative. A false UNPROVABLE tells someone to rewrite a proof
# that was already correct, which is worse than a miss, so anything needing real
    # interpretation is left to the LLM half (Pass D2), the same division of labour
# Pass 1 and Pass 2 already use. In particular, "this rule deserved a behavioural
# proof rather than a grep" requires understanding what the rule means, so a
# presence-only description is graded STRUCTURAL here and D2 decides whether the
# rule warranted more.
# ---------------------------------------------------------------------------

# The description's action is reading an artifact that exists independently of the
# test: no code ran to produce what is asserted on. That is the definition of a
# structural proof in references/audit_criteria.md.
_D_PRESENCE_ONLY_RE = re.compile(
    r'^\s*(?:grep|read|scan|glob|parse|extract|count|inspect|open)\b',
    re.IGNORECASE)

# An act step: code runs before the assertion, so the proof is behavioural.
_D_ACT_RE = re.compile(
    r'\b(?:call|invoke|run|write|create|POST|GET|PUT|DELETE|load|render|launch|'
    r'navigate|click|type|submit|execute|spawn|start|seed|patch|set|configure|'
    r'initialize|init|mock|simulate|trigger|send|drive)\b',
    re.IGNORECASE)

# "verify X exists" / "check Y is not null" / "assert Z is present"
_D_LEVEL1_RE = re.compile(
    r'\b(?:verify|check|assert|ensure)\b[^.;]{0,40}?'
    r'\b(?:exists?|is\s+not\s+(?:null|None)|is\s+present|are\s+present|'
    r'is\s+defined|is\s+truthy)\b',
    re.IGNORECASE)

# An assertion of ABSENCE is a FORBIDDEN-pattern proof, not a Level 1 proof.
_D_ABSENCE_RE = re.compile(
    r'\b(?:none\s+exist|no\s+matches|zero\s+matches|does\s+not\s+exist|'
    r'not\s+present|no\s+longer|absent|zero\b|removed|purged)\b',
    re.IGNORECASE)

_D_VAGUE_RE = re.compile(
    r'\b(?:works?|working|correctly|properly|as\s+expected|appropriately|'
    r'successfully|handles?\s+(?:it|them|errors?))\b',
    re.IGNORECASE)

# Evidence that a concrete expected value is named.
_D_CONCRETE_RE = re.compile(
    r'(?:\d|"[^"]+"|\'[^\']+\'|`[^`]+`|\bexactly\b|\bzero\b|\bempty\b|'
    r'\bnone\b|\btrue\b|\bfalse\b|[A-Z]{2,}(?:_[A-Z0-9]+)+)',
    re.IGNORECASE)

# An @e2e description must read as something a person does, not a function call.
_D_INTERNAL_CALL_RE = re.compile(
    r'\b(?:call|invoke)\b[^.;]{0,40}?\w+\(', re.IGNORECASE)


def _design_finding(proof_id, rule_id, level, check, reason):
    return {
        'proof_id': proof_id,
        'rule_id': rule_id,
        'level': level,
        'check': check,
        'reason': reason,
    }


def _read_proof_tags(spec_path):
    """(tiers, platforms) from a spec's ## Proof section.

    tiers maps proof_id -> tier (default 'unit'); platforms maps proof_id ->
    the `@on(...)` platform ids ([] when the proof is platform-agnostic).
    """
    tiers = {}
    platforms = {}
    if not spec_path or not os.path.isfile(spec_path):
        return tiers, platforms
    for m in _PROOF_DESC_RE.finditer(_file_text(spec_path)):
        _, tier, ids, _ = _split_proof_tags(m.group(3))
        tiers[m.group(1)] = tier
        platforms[m.group(1)] = ids
    return tiers, platforms


def check_proof_design(spec_path):
    """Grade each proof description as PROVABLE/LOOSE/UNPROVABLE/STRUCTURAL.

    Returns {'spec': path, 'proofs': [...]}. Requires only the spec file: no test
    code and no proof JSON, so it runs before anything is built. See
    references/audit_criteria.md, Pass D.
    """
    proofs = _read_proof_descriptions(spec_path)
    tiers, _platforms = _read_proof_tags(spec_path)

    results = []
    for entry in proofs:
        pid = entry['proof_id']
        first_rule = entry['rule_ids'].split(',')[0].strip()
        desc = entry['description']
        tier = tiers.get(pid, 'unit')

        has_act = bool(_D_ACT_RE.search(desc))
        concrete = bool(_D_CONCRETE_RE.search(desc))

        # STRUCTURAL first: nothing ran to produce what is being asserted on.
        if _D_PRESENCE_ONLY_RE.match(desc) and not has_act:
            results.append(_design_finding(
                pid, first_rule, 'STRUCTURAL', 'structural_presence_check',
                'Reads an artifact that exists independently of the test, so no code ran '
                'to produce what is asserted on. Excluded from the Design score rather '
                'than counted against it.'))
            continue

        # UNPROVABLE: an @e2e proof that reads as a function call, not a user action.
        if tier == 'e2e' and _D_INTERNAL_CALL_RE.search(desc):
            results.append(_design_finding(
                pid, first_rule, 'UNPROVABLE', 'e2e_names_internal_call',
                'An @e2e description must read as an observable flow (arrange -> act -> '
                'observe). "Call <function>(...)" is not something a person does — drive '
                'the real interface or retag the proof to the tier it actually exercises.'))
            continue

        # UNPROVABLE: existence is the whole assertion. Absence assertions are
        # FORBIDDEN-pattern proofs and are excluded, as are descriptions that name
        # a concrete expected value alongside the presence check.
        if (_D_LEVEL1_RE.search(desc)
                and not _D_ABSENCE_RE.search(desc)
                and not concrete):
            results.append(_design_finding(
                pid, first_rule, 'UNPROVABLE', 'level1_presence',
                'Existence is the entire assertion, so a faithful test proves nothing '
                'about behaviour. Name the input and the expected output instead.'))
            continue

        # LOOSE
        if _D_VAGUE_RE.search(desc) and not concrete:
            results.append(_design_finding(
                pid, first_rule, 'LOOSE', 'vague_verb_no_expected_value',
                'Vague verb with no expected value. A description should be '
                'copy-pasteable into a test without interpretation.'))
            continue
        if not concrete:
            results.append(_design_finding(
                pid, first_rule, 'LOOSE', 'no_expected_value',
                'No literal, number, quoted string or named constant, so almost any '
                'assertion would satisfy this description.'))
            continue

        results.append(_design_finding(
            pid, first_rule, 'PROVABLE', 'none',
            'Names an observable outcome with a concrete expected value.'))

    return {'spec': spec_path, 'proofs': results}


def audit_scope(project_root):
    """Report what exists, so purlin:audit can DERIVE its mode instead of guessing.

    For each feature: how many rules and declared proofs the spec has, how many
    proofs have actually executed (from specs/**/<feature>.proofs-*.json), whether
    the files in `> Scope:` exist on disk, and how many distinct test files back
    the executed proofs.

    `scope_files_exist` is the field that distinguishes "spec written, nothing
    built" from "code exists, tests missing" — a distinction nothing else in the
    toolchain could make, and the two states need different next steps.

    recommended_mode:
      design    — no proof has executed anywhere; only the spec side is measurable
      both      — every declared proof has executed
      both      — partial: Integrity is reported for the features that have proofs
    """
    spec_dir = os.path.join(project_root, 'specs')
    features = {}

    for spec_path in sorted(glob.glob(os.path.join(spec_dir, '**', '*.md'), recursive=True)):
        feature = os.path.splitext(os.path.basename(spec_path))[0]
        with open(spec_path, encoding='utf-8') as f:
            content = f.read()
        rules = _RULE_LINE_RE.findall(content)
        declared = _read_proof_descriptions(spec_path)

        scope_files, scope_present = [], 0
        m = re.search(r'^>\s*Scope:\s*(.+)$', content, re.MULTILINE)
        if m:
            for raw in m.group(1).split(','):
                rel = raw.strip()
                if not rel:
                    continue
                scope_files.append(rel)
                if glob.glob(os.path.join(project_root, rel), recursive=True):
                    scope_present += 1

        features[feature] = {
            'feature': feature,
            'spec': os.path.relpath(spec_path, project_root).replace(os.sep, '/'),
            'rules': len(rules),
            'proofs_declared': len(declared),
            'proofs_executed': 0,
            'test_files_present': 0,
            'scope_files': len(scope_files),
            'scope_files_exist': scope_present,
        }

    executed = {}
    tests = {}
    for pf in glob.glob(os.path.join(spec_dir, '**', '*.proofs-*.json'), recursive=True):
        parts = _proof_file_parts(os.path.basename(pf))
        if parts is None:
            continue
        _stem, file_tier, file_platform, is_legacy = parts
        try:
            with open(pf, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data.get('proofs', []):
            feat = entry.get('feature')
            if not feat:
                continue
            # Same in-memory stamp the server applies on read.
            entry['platform'] = file_platform
            if is_legacy:
                entry['tier'] = file_tier
            executed.setdefault(feat, set()).add(entry.get('id'))
            tf = entry.get('test_file')
            if tf:
                tests.setdefault(feat, set()).add(tf)

    for feat, ids in executed.items():
        if feat in features:
            features[feat]['proofs_executed'] = len(ids)
            features[feat]['test_files_present'] = len(tests.get(feat, ()))

    rows = [features[k] for k in sorted(features)]
    total_declared = sum(r['proofs_declared'] for r in rows)
    total_executed = sum(r['proofs_executed'] for r in rows)

    if total_executed == 0:
        mode, why = 'design', (
            'No proof has executed anywhere, so there is no test code to grade. '
            'Only Proof Design is measurable.')
    elif total_executed >= total_declared and total_declared > 0:
        mode, why = 'both', (
            'Every declared proof has executed. Design is cheap and bounds what '
            'Integrity can reach, so run both.')
    else:
        mode, why = 'both', (
            f'{total_executed} of {total_declared} declared proofs have executed. '
            'Run both, scoping Integrity to the features that have executed proofs.')

    return {
        'features': rows,
        'totals': {
            'features': len(rows),
            'rules': sum(r['rules'] for r in rows),
            'proofs_declared': total_declared,
            'proofs_executed': total_executed,
        },
        'recommended_mode': mode,
        'why': why,
    }


# ---------------------------------------------------------------------------
# The deterministic sweep
#
# Pass 1 and Pass D1 are the two halves of the audit that need no model, no
# judgment and no cache: Pass 1 grades executed test source, Pass D1 grades
# declared proof descriptions, and both are recomputed from the three files they
# read every time. `deterministic_sweep` is those two halves run over a whole
# project in one pass, so a CI job can recompute the same verdict from a clean
# checkout and a reader can tell what the machine proved from what a person
# judged. It reads no cache and opens nothing for writing, on purpose: a sweep
# that consulted `.purlin/cache/audit_cache.json` would report a grade somebody
# once stored rather than one this checkout supports.
# ---------------------------------------------------------------------------

# fail beats unmeasurable beats pass. A proof backed by two tests is only as
# good as its weakest backing, and "one of the two is hollow" is a defect, not a
# measurement gap, so a fail anywhere wins over an unmeasurable elsewhere.
_SWEEP_STATUS_RANK = {'pass': 0, 'unmeasurable': 1, 'fail': 2}


def _sweep_unmeasurable_reason(check, test_file, feature):
    """Why one backing could not be measured, in words a gate can print."""
    if check == 'no_checker':
        ext = os.path.splitext(test_file)[1].lower() or '(no extension)'
        return (f'No deterministic checker reads {ext} files, so Pass 1 never looked '
                'at this test. An unmeasurable proof is a gap in coverage, not a defect.')
    if check == 'missing_file':
        if not test_file:
            return ('The proof record names no test file and none could be resolved '
                    'from the test name, so there is no source to measure.')
        return (f'{test_file} is named by the proof record but is not on disk, so '
                'there is no source to measure.')
    return (f'{test_file} carries no {feature} marker for this proof, so the '
            'executed test could not be located in the file that recorded it.')


def _sweep_file_verdicts(project_root, feature, test_file, rule_descs):
    """({proof_id: Pass 1 result}, blanket) for one of `feature`'s test files.

    `blanket` is None when the file was analysed. Otherwise it is the
    `unmeasurable` check that applies to every proof the file backs:
    `no_checker` for an extension outside `_CHECKER_EXTENSIONS` (a custom
    plugin's language), `missing_file` for a path that is not on disk.
    """
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


def deterministic_sweep(project_root):
    """Grade every proof in `project_root` with the two model-free passes.

    For each `specs/**/*.md` feature: `check_proof_design` grades every declared
    proof description (Pass D1), and every executed backing from
    `_proof_backings` is graded by the Pass 1 checker for its language, one
    `analyze_test_file` call per (test file, feature) so a file carrying two
    features is still parsed once inside the single `run_scope()` this opens.

    A backing that Pass 1 cannot measure is `unmeasurable`, never a failure, and
    the `check` says which kind: `no_checker` for an extension outside
    `_CHECKER_EXTENSIONS`, `missing_file` for a path that is not on disk (a
    proof whose `test_file` is empty, as xUnit records when no source info is
    available, is first resolved through `resolve_test_file_from_name`), and
    `marker_not_found` for a file whose checker finds no marker for that proof.
    Across several backings `fail` wins over `unmeasurable` wins over `pass`.

    Two kinds of proof enter deliberately:

    * An anchor (`specs/_anchors/*.md`) is swept like any other feature. Its
      proofs execute as real tests and its proof files sit beside every other
      one, so excluding it would leave the cross-cutting constraints ungraded.
    * A proof stamped `@manual(...)` has no test to grade. It is graded by
      Pass D1 like every other description and simply has no backing, so it
      appears under `design` and never under `integrity`, `hollow` or
      `unmeasurable`. Counting a human stamp as unmeasurable would put every
      manual proof in a gate's "could not measure" column forever, and counting
      it as measured would claim a machine checked it.

    Returns::

        {'project_root': str,
         'features': {name: {'spec': str,
                             'design': {pid: {rule_id, level, check, reason}},
                             'integrity': {pid: {rule_id, status, check, reason,
                                                 test_file, test_name, backings}}}},
         'hollow': [...], 'unprovable': [...], 'unmeasurable': [...],
         'counts': {...}}

    where `backings` is how many executed backings the proof has and
    `test_file`/`test_name` name the one whose verdict was taken. The three
    lists are sorted by (feature, proof_id, test_file).

    Opens nothing for writing: no cache is read or written, no runtime file is
    created, and the working tree is byte-identical afterwards.
    """
    features = {}
    hollow, unprovable, unmeasurable = [], [], []
    declared_total = graded_total = backing_total = passing = 0

    with run_scope():
        spec_dir = os.path.join(project_root, 'specs')
        for spec_path in sorted(glob.glob(os.path.join(spec_dir, '**', '*.md'),
                                          recursive=True)):
            feature = os.path.splitext(os.path.basename(spec_path))[0]
            rule_descs = _read_rule_descriptions(spec_path)
            declared = _read_proof_descriptions(spec_path)
            declared_total += len(declared)
            first_rule = {d['proof_id']: d['rule_ids'].split(',')[0].strip()
                          for d in declared}

            design = {}
            for finding in check_proof_design(spec_path)['proofs']:
                proof_id = finding['proof_id']
                design[proof_id] = {
                    'rule_id': finding['rule_id'], 'level': finding['level'],
                    'check': finding['check'], 'reason': finding['reason'],
                }
                graded_total += 1
                if finding['level'] == 'UNPROVABLE':
                    unprovable.append({'feature': feature, 'proof_id': proof_id,
                                       **design[proof_id]})

            # Group the executed backings by the file they live in, so each
            # (test file, feature) pair is analysed exactly once.
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
                    backing_total += 1
                    result = results.get(proof_id)
                    if blanket is not None or result is None:
                        check = blanket or 'marker_not_found'
                        verdict = {
                            'status': 'unmeasurable', 'check': check,
                            'reason': _sweep_unmeasurable_reason(
                                check, test_file, feature),
                            'test_file': test_file, 'test_name': test_name or '',
                        }
                    else:
                        verdict = {
                            'status': 'fail' if result['status'] == 'fail' else 'pass',
                            'check': result.get('check', 'none'),
                            'reason': result.get('reason', ''),
                            'test_file': test_file,
                            'test_name': result.get('test_name') or test_name or '',
                        }
                    current = best.get(proof_id)
                    if current is None or (_SWEEP_STATUS_RANK[verdict['status']]
                                           > _SWEEP_STATUS_RANK[current['status']]):
                        best[proof_id] = verdict

            integrity = {}
            for proof_id in sorted(best):
                verdict = best[proof_id]
                integrity[proof_id] = {
                    'rule_id': first_rule.get(proof_id, ''),
                    'status': verdict['status'], 'check': verdict['check'],
                    'reason': verdict['reason'], 'test_file': verdict['test_file'],
                    'test_name': verdict['test_name'],
                    'backings': counted[proof_id],
                }
                row = {'feature': feature, 'proof_id': proof_id, **integrity[proof_id]}
                if verdict['status'] == 'fail':
                    hollow.append(row)
                elif verdict['status'] == 'unmeasurable':
                    unmeasurable.append(row)
                else:
                    passing += 1

            features[feature] = {
                'spec': os.path.relpath(spec_path, project_root).replace(os.sep, '/'),
                'design': design,
                'integrity': integrity,
            }

    def _order(row):
        return (row['feature'], row['proof_id'], row.get('test_file', ''))

    hollow.sort(key=_order)
    unprovable.sort(key=_order)
    unmeasurable.sort(key=_order)

    return {
        'project_root': project_root,
        'features': features,
        'hollow': hollow,
        'unprovable': unprovable,
        'unmeasurable': unmeasurable,
        'counts': {
            'features': len(features),
            'proofs_declared': declared_total,
            'proofs_graded': graded_total,
            'proofs_executed': sum(len(f['integrity']) for f in features.values()),
            'backings': backing_total,
            'pass': passing,
            'hollow': len(hollow),
            'unprovable': len(unprovable),
            'unmeasurable': len(unmeasurable),
        },
    }


def check_spec_coverage(spec_path):
    """Return rule and proof counts for a spec.

    Structural vs behavioral classification is handled by the LLM in Pass 2,
    not by regex. This function only counts rules and proofs.
    """
    rules = _read_rule_descriptions(spec_path)
    if not rules:
        return {'rule_count': 0, 'proof_count': 0}

    proof_entries = _read_proof_descriptions(spec_path)

    return {
        'rule_count': len(rules),
        'proof_count': len(proof_entries),
    }

# ---------------------------------------------------------------------------
# Proof-file structural checks (Pass 0.5: language-agnostic, JSON-only)
# ---------------------------------------------------------------------------

def check_proof_file(proof_json_path, spec_path=None):
    """Check proof JSON for structural issues — works for any language.

    Operates on proof JSON + spec data only. No source code reading.
    Returns list of finding dicts with check, severity, and details.
    """
    if not os.path.isfile(proof_json_path):
        return []

    with open(proof_json_path, encoding='utf-8') as f:
        data = json.load(f)

    proofs = data.get('proofs', [])
    if not proofs:
        return []

    findings = []

    # Check 1: proof_id_collision: same PROOF-N targeting different RULE-N values
    id_to_rules = {}
    for entry in proofs:
        pid = entry.get('id', '')
        rid = entry.get('rule', '')
        if pid:
            id_to_rules.setdefault(pid, set()).add(rid)

    for pid, rules in id_to_rules.items():
        if len(rules) > 1:
            findings.append({
                'check': 'proof_id_collision',
                'severity': 'MEDIUM',
                'proof_id': pid,
                'rules': sorted(rules),
                'reason': f'{pid} targets multiple rules: {", ".join(sorted(rules))}',
            })

    # Check 2: proof_rule_orphan: proof targets a rule not in the spec
    if spec_path and os.path.isfile(spec_path):
        spec_rules = set(_read_rule_descriptions(spec_path).keys())
        if spec_rules:
            for entry in proofs:
                rid = entry.get('rule', '')
                # Only check own rules (no "/" prefix: required rules come from anchors)
                if rid and '/' not in rid and rid not in spec_rules:
                    findings.append({
                        'check': 'proof_rule_orphan',
                        'severity': 'LOW',
                        'proof_id': entry.get('id', ''),
                        'rule': rid,
                        'reason': f'{rid} not found in spec (rule may have been removed)',
                    })

    return findings


# ---------------------------------------------------------------------------
# Audit cache helpers
# ---------------------------------------------------------------------------

def compute_proof_hash(spec_rule_text, proof_description, test_code):
    """Hash the inputs that determine an audit result."""
    # Use null byte separator to prevent input-shifting collisions
    # (e.g. "a|b" + "c" vs "a" + "b|c" would collide with | separator)
    payload = f"{spec_rule_text}\x00{proof_description}\x00{test_code}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


AUDIT_CACHE = 'audit_cache.json'
DESIGN_CACHE = 'design_cache.json'


def compute_design_hash(spec_rule_text, proof_description):
    """Hash the inputs that determine a Proof Design result.

    Deliberately excludes test code: a design grade is about the description, so
    it must survive test edits. Kept in a separate cache file from the audit
    cache so the two keyspaces cannot collide.
    """
    payload = f"{spec_rule_text}\x00{proof_description}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ProofInputsError(ValueError):
    """A (feature, proof_id) pair does not resolve against project state.

    Raised by resolve_proof_inputs. It is a hard error rather than a fallback:
    a cache entry whose key cannot be recomputed from the project is an
    assessment of something nobody can point at, and a silent fallback is how
    "self-invalidates" became a promise with no mechanism.
    """


def _read_project_config(project_root):
    """Read .purlin/config.json, or {} when absent or malformed."""
    config_path = os.path.join(project_root, '.purlin', 'config.json')
    if not os.path.isfile(config_path):
        return {}
    try:
        with open(config_path, encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _find_spec_path(project_root, feature):
    """The spec file declaring `feature`, or None."""
    if not feature:
        return None
    matches = sorted(glob.glob(
        os.path.join(project_root, 'specs', '**', f'{feature}.md'), recursive=True))
    return matches[0] if matches else None


# ---------------------------------------------------------------------------
# Run scope (RULE-42)
#
# A cache key is resolved from three files: the spec, the proof file and the
# test file. Validating a cache means resolving every entry's key, and the
# entries outnumber the files by thirty to one, so without a scope each spec
# was re-read, each proof file re-loaded and each test file re-parsed once per
# proof it backs (1333 parses of 45 files on this repository). Inside a scope
# every one of those is done once and the result reused; outside a scope
# nothing is memoized, so RULE-40's edit-then-recompute contract holds for a
# caller that never opens one. The scope is explicit rather than keyed on
# mtimes because a same-size edit inside one second is exactly what RULE-40's
# proof performs, and a key that depends on clock resolution is not
# "deterministic in the three inputs and nothing else".
# ---------------------------------------------------------------------------

class _RunCache:
    __slots__ = ('specs', 'proof_backings', 'texts', 'py_parses', 'py_sources',
                 'test_bodies', 'keys')

    def __init__(self):
        self.specs = {}           # feature -> (spec_path, declared, rule_descs)
        self.proof_backings = {}  # feature -> {proof_id: [(test_file, test_name)]}
        self.texts = {}          # abs path -> file text (RULE-51)
        self.py_parses = {}      # test path -> (entries, lines) | SyntaxError
        self.py_sources = {}     # abs test path -> {(feature, proof_id): src} | None
        self.test_bodies = {}    # (abs test path, feature) -> {proof_id: src} | None
        self.keys = {}           # (feature, proof_id, cache_name) -> (key, inputs)


_RUN_CACHE = None


def _file_text(path):
    """The UTF-8 text of `path`, read from disk once per scope (RULE-51).

    Every reader that takes a path rather than a feature comes through here: the
    three spec readers and every Pass 1 checker. Without it a sweep opened each
    spec once per reader that wanted it (four times over) and each test file once
    per feature declaring a proof in it, because those readers are called by path
    and so never reach the feature-keyed `_spec_inputs` memo.

    Keyed on the path and nothing else, for the reason `run_scope` gives above: a
    key that consults an mtime or a size cannot see a same-size edit inside one
    clock tick. Outside a scope nothing is memoized, so a caller that never opens
    one always reads what is on disk.
    """
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
    """Memoize spec, proof-file and test-file reads for the block's duration.

    Re-entrant: a scope opened inside another one shares it and never clears
    it, so a caller that wraps a batch can call helpers that wrap their own.
    """
    global _RUN_CACHE
    if _RUN_CACHE is not None:
        yield _RUN_CACHE
        return
    _RUN_CACHE = _RunCache()
    try:
        yield _RUN_CACHE
    finally:
        _RUN_CACHE = None


def _spec_inputs(project_root, feature):
    """(spec_path, declared proofs, rule descriptions) for `feature`, read once
    per scope. `spec_path` is None when no spec matches."""
    cache = _RUN_CACHE
    if cache is not None and feature in cache.specs:
        return cache.specs[feature]
    spec_path = _find_spec_path(project_root, feature)
    if spec_path:
        result = (spec_path, _read_proof_descriptions(spec_path),
                  _read_rule_descriptions(spec_path))
    else:
        result = (None, [], {})
    if cache is not None:
        cache.specs[feature] = result
    return result


def _proof_backings(project_root, feature):
    """{proof_id: [(test_file, test_name), ...]} for every executed proof of
    `feature`, in proof-file then source order.

    Reads the committed proof JSON, which is the only record of which test
    function backs a proof id. Files are read in sorted order and entries are
    deduplicated by (test_file, proof_id), so a proof re-run across tiers or
    platforms contributes one backing per distinct file rather than one per
    record, while a proof genuinely backed by tests in two files keeps both.
    That distinction is what `deterministic_sweep` grades: a proof is only as
    good as its weakest backing, so every one of them has to be visible.

    The cache-key resolver wants one answer, not a list, and takes the first
    backing (see `_proof_records`).
    """
    cache = _RUN_CACHE
    if cache is not None and feature in cache.proof_backings:
        return cache.proof_backings[feature]
    backings = {}
    seen = set()
    pattern = os.path.join(project_root, 'specs', '**', f'{feature}.proofs-*.json')
    for pf in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(pf, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data.get('proofs', []):
            if entry.get('feature') != feature or not entry.get('id'):
                continue
            test_file = entry.get('test_file') or None
            test_name = entry.get('test_name') or None
            dedup = (entry['id'], test_file)
            if dedup in seen:
                continue
            seen.add(dedup)
            backings.setdefault(entry['id'], []).append((test_file, test_name))
    if cache is not None:
        cache.proof_backings[feature] = backings
    return backings


def _proof_records(project_root, feature):
    """{proof_id: (test_file, test_name)} — the FIRST backing of every executed
    proof of `feature`, derived from `_proof_backings` so the two can never
    disagree about which record a proof id resolves to."""
    return {proof_id: entries[0]
            for proof_id, entries in _proof_backings(project_root, feature).items()}


def _find_proof_record(project_root, feature, proof_id):
    """(test_file, test_name) for an executed proof, or (None, None)."""
    return _proof_records(project_root, feature).get(proof_id, (None, None))


def _python_proof_sources(path, content):
    """{(feature, proof_id): source} for every marked test in a Python file,
    or None when it does not parse. One parse per path per scope."""
    cache = _RUN_CACHE
    if cache is not None and path in cache.py_sources:
        return cache.py_sources[path]
    try:
        entries, lines = _python_parse(path, content)
    except SyntaxError:
        sources = None
    else:
        sources = {}
        for feature, pid, _rid, _name, node in entries:
            sources.setdefault((feature, pid), _segment(lines, node))
    if cache is not None:
        cache.py_sources[path] = sources
    return sources


def _test_bodies(path, ext, feature):
    """{proof_id: source} for `feature`'s marked tests in the file at `path`,
    or None when the file cannot be read or parsed. Computed once per
    (path, feature) per scope."""
    cache = _RUN_CACHE
    memo_key = (path, feature)
    if cache is not None and memo_key in cache.test_bodies:
        return cache.test_bodies[memo_key]
    bodies = None
    try:
        with open(path, encoding='utf-8') as f:
            content = f.read()
    except OSError:
        content = None
    if content is not None:
        # One branch per language and no fallback: an extension with no branch
        # here is not extractable and returns None, instead of being handed to
        # whichever extractor the `else` happened to name (it was the JS one,
        # so every `.php`, `.sql` and `.c` file was scanned for `it(...)`).
        if ext == '.py':
            sources = _python_proof_sources(path, content)
            if sources is not None:
                bodies = {pid: src for (feat, pid), src in sources.items()
                          if feat == feature}
        elif ext == '.cs':
            bodies = {}
            for pid, _rid, _name, body in _iter_csharp_proof_bodies(content, feature):
                bodies.setdefault(pid, body)
        elif ext in _JS_EXTENSIONS:
            bodies = {}
            for pid, _rid, _title, body in _iter_js_proof_bodies(content, feature):
                bodies.setdefault(pid, body)
        elif ext == '.php':
            bodies = {}
            for pid, _rid, _name, body in _iter_php_proof_bodies(content, feature):
                bodies.setdefault(pid, body)
        elif ext == '.sql':
            bodies = {}
            for pid, _rid, _name, block in _iter_sql_proof_blocks(content, feature):
                bodies.setdefault(pid, block)
        elif ext in _C_EXTENSIONS:
            bodies = {}
            for pid, _rid, _name, _passed, block in _iter_c_proof_bodies(
                    content, feature):
                if block is not None:
                    bodies.setdefault(pid, block)
        else:
            bodies = None
    if cache is not None:
        cache.test_bodies[memo_key] = bodies
    return bodies


def _extract_test_code(project_root, feature, proof_id, test_file):
    """Source of the test function backing `proof_id`, or None.

    None means "not extractable here": no proof record, a file that is gone, a
    language with no extractor, or a marker the extractor cannot find.
    """
    if not test_file:
        return None
    ext = os.path.splitext(test_file)[1].lower()
    if ext not in _TEST_CODE_EXTENSIONS:
        return None
    path = os.path.join(project_root, *test_file.split('/'))
    if not os.path.isfile(path):
        return None
    bodies = _test_bodies(path, ext, feature)
    if not bodies:
        return None
    return bodies.get(proof_id)


def resolve_proof_inputs(project_root, feature, proof_id, include_test_code=True):
    """(rule_text, proof_description, test_code) read from project state.

    This is the ONE function that decides what an audit result is keyed on, and
    both the writer and every reader call it. The inputs used to be pasted in by
    the caller, which is why a cache entry could not be checked against anything:
    the key described whatever text the auditor happened to send, not the project.

    Raises ProofInputsError when the spec, the proof declaration or every rule the
    proof cites is missing. `test_code` is None when no test code is extractable
    (see _extract_test_code); the caller records that as
    `inputs.test_verifiable: false` so a reader knows a test edit cannot move the
    key for that entry. With `include_test_code` False the test file is never
    opened and `test_code` is None: the design key excludes test code by
    construction (RULE-37), so reading it would be work that cannot change the
    answer.
    """
    spec_path, declared, rule_descs = _spec_inputs(project_root, feature)
    if not spec_path:
        raise ProofInputsError(
            f'{feature}/{proof_id}: no spec file matches specs/**/{feature}.md')
    match = next((d for d in declared if d['proof_id'] == proof_id), None)
    if match is None:
        rel = os.path.relpath(spec_path, project_root).replace(os.sep, '/')
        raise ProofInputsError(
            f'{feature}/{proof_id}: {rel} declares no {proof_id}')
    cited = [r.strip() for r in match['rule_ids'].split(',') if r.strip()]
    texts = [rule_descs[r] for r in cited if r in rule_descs]
    if not texts:
        rel = os.path.relpath(spec_path, project_root).replace(os.sep, '/')
        raise ProofInputsError(
            f'{feature}/{proof_id}: cites {match["rule_ids"]}, and {rel} defines '
            'none of them')
    test_code = None
    if include_test_code:
        test_file, _test_name = _find_proof_record(project_root, feature, proof_id)
        test_code = _extract_test_code(project_root, feature, proof_id, test_file)
    return '\n'.join(texts), match['description'], test_code


def cache_key_for(project_root, feature, proof_id, cache_name=AUDIT_CACHE):
    """(key, inputs) for a proof, computed from project state.

    `inputs` records whether test code entered the key, so a reader can say why
    an entry survived a test edit instead of guessing. Raises ProofInputsError
    for an unresolvable pair.
    """
    cache = _RUN_CACHE
    memo_key = (feature, proof_id, cache_name)
    if cache is not None and memo_key in cache.keys:
        return cache.keys[memo_key]
    rule_text, description, test_code = resolve_proof_inputs(
        project_root, feature, proof_id,
        include_test_code=(cache_name != DESIGN_CACHE))
    # The proof's identity is part of the key. Without it two features whose
    # rule text and proof description happen to be byte-identical produce the
    # same key, and one grade silently overwrites the other in the cache dict
    # while the deduplication key says they are two different proofs. With it,
    # (feature, proof_id) -> key is injective and the cache cannot lose a grade
    # to a coincidence.
    identity = f'{feature}\x00{proof_id}\x00{rule_text}'
    if cache_name == DESIGN_CACHE:
        key = compute_design_hash(identity, description)
    else:
        key = compute_proof_hash(identity, description, test_code or '')
    result = (key, {'test_verifiable': test_code is not None})
    if cache is not None:
        cache.keys[memo_key] = result
    return result


def auditor_stamp(project_root):
    """Who graded: {name, command} from config.

    `audit_llm_name` or "claude" when nothing is configured, and the literal
    `audit_llm` command or null. A reader that can see the whole gauge came from
    one unnamed tool can weigh it accordingly; one that cannot, cannot.
    """
    config = _read_project_config(project_root)
    return {
        'name': config.get('audit_llm_name') or 'claude',
        'command': config.get('audit_llm') or None,
    }


def rekey_cache_entries(project_root, cache, cache_name=AUDIT_CACHE):
    """Re-key every entry from project state and stamp the auditor.

    The caller's key is ignored entirely. An entry naming a (feature, proof_id)
    that does not resolve is rejected the way a missing dedup field is (RULE-33):
    ValueError naming every offender, raised before the filesystem is touched.
    """
    stamp = auditor_stamp(project_root)
    rekeyed = {}
    unresolved = []
    resolved = []
    # One scope for the batch: every entry of one feature shares one spec read
    # and one parse of each test file (RULE-42).
    with run_scope():
        for _supplied_key, entry in cache.items():
            if not isinstance(entry, dict):
                continue
            try:
                resolved.append((entry, cache_key_for(
                    project_root, entry.get('feature'), entry.get('proof_id'),
                    cache_name)))
            except ProofInputsError as exc:
                unresolved.append(str(exc))
    for entry, (key, inputs) in resolved:
        new_entry = dict(entry)
        new_entry['inputs'] = inputs
        new_entry['auditor'] = stamp
        # Two entries in one batch for the same proof now collapse here rather
        # than in write_audit_cache's merge, so RULE-24's "keep the latest
        # cached_at" has to be honoured at this step too; dict insertion order
        # is not a timestamp.
        existing = rekeyed.get(key)
        if existing is None or new_entry.get('cached_at', '') >= existing.get('cached_at', ''):
            rekeyed[key] = new_entry
    if unresolved:
        raise ValueError(
            'audit cache entries name a (feature, proof_id) that does not '
            'resolve against the project, so their grades could never be '
            'rechecked:\n  ' + '\n  '.join(unresolved))
    return rekeyed


def read_audit_cache(project_root, cache_name=AUDIT_CACHE):
    """Read .purlin/cache/<cache_name>. Returns dict of proof_hash → assessment.

    Both gauges use the same entry shape and the same locking, so one pair of
    read/write functions serves the audit cache and the design cache.
    """
    cache_path = os.path.join(project_root, '.purlin', 'cache', cache_name)
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _lock_exclusive(lock_file):
    """Acquire an exclusive, blocking lock on an open file handle.

    POSIX uses fcntl.flock; Windows uses msvcrt.locking on a 1-byte region.
    On Windows, msvcrt.locking with LK_LOCK gives up after ~10s under
    contention, so we retry to match flock's indefinite-block semantics.
    """
    if _HAS_FCNTL:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        return
    import msvcrt
    # Ensure a byte exists at offset 0 to lock, then block until it is ours.
    lock_file.write('\0')
    lock_file.flush()
    lock_file.seek(0)
    while True:
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            return
        except OSError:
            continue


def try_lock_exclusive(lock_file):
    """Non-blocking twin of _lock_exclusive: True when the lock is now ours,
    False when another process holds it. Released with _unlock."""
    if _HAS_FCNTL:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True
    import msvcrt
    lock_file.write('\0')
    lock_file.flush()
    lock_file.seek(0)
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return False
    return True


def _unlock(lock_file):
    """Release a lock acquired by _lock_exclusive or try_lock_exclusive."""
    if _HAS_FCNTL:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        return
    import msvcrt
    lock_file.seek(0)
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


# Fields every audit-cache entry must carry. `feature` and `proof_id` form the
# deduplication key used here and by _read_audit_summary() in purlin_server.py;
# an entry missing either one keys under ('', ''), so a whole batch written that
# way collapses to one surviving row and the integrity score is then computed
# from a single proof. See references/audit_criteria.md, Required entry fields.
_CACHE_DEDUP_FIELDS = ('feature', 'proof_id')

# Every CLI form this script accepts. Kept adjacent to the dispatch chain in main()
# so the two cannot drift: RULE-34 asserts that every `--flag` main() dispatches on
    # appears here, which is what went wrong before: the help text had gone stale and
# omitted five real flags.
_USAGE = (
    "<test_file> <feature_name> [--spec-path <path>]",
    "--check-proof-file --proof-path <path> [--spec-path <path>]",
    "--check-spec-coverage --spec-path <path>",
    "--check-proof-design --spec-path <path>",
    "--audit-scope [--project-root <path>]",
    "--deterministic-sweep [--project-root <path>]",
    "--cache-key --feature <name> --proof-id PROOF-N [--project-root <path>] [--design]",
    "--resolve-source <test_name> [--project-root <path>] [--ext .cs]",
    "--load-criteria [--project-root <path>] [--extra <path>]",
    "--read-cache [--project-root <path>]",
    "--write-cache [--project-root <path>]      (JSON object of entries on stdin)",
    "--read-design-cache [--project-root <path>]",
    "--write-design-cache [--project-root <path>]  (JSON object of entries on stdin)",
    "--clear-cache [--project-root <path>]",
    "--prune-cache --live-keys-file <path> [--project-root <path>]",
)



def _validate_cache_entries(cache):
    """Reject entries that would collapse into the empty ('', '') dedup bucket.

    Raises ValueError naming every offending key, so a malformed batch fails
    loudly instead of silently merging into a plausible wrong percentage.
    """
    if not isinstance(cache, dict):
        raise ValueError(
            f"audit cache must be a JSON object of hash -> entry, got {type(cache).__name__}"
        )
    bad = []
    for hash_key, entry in cache.items():
        if not isinstance(entry, dict):
            bad.append(f"{hash_key!r}: not an object")
            continue
        missing = [f for f in _CACHE_DEDUP_FIELDS if not entry.get(f)]
        if missing:
            bad.append(f"{hash_key!r}: missing {', '.join(missing)}")
    if bad:
        raise ValueError(
            "audit cache entries are missing their deduplication key "
            "(feature, proof_id); these would all collapse into one entry and the "
            "integrity score would be computed from a single proof:\n  "
            + "\n  ".join(bad)
        )


def write_audit_cache(project_root, cache, cache_name=AUDIT_CACHE):
    """Merge new entries into audit cache atomically, pruning stale duplicates.

    Reads the existing cache from disk first, merges the new entries on top,
    then deduplicates by (feature, proof_id) keeping the latest cached_at.
    This ensures concurrent or sequential writers for different features
    don't overwrite each other's data.

    Stamps the real current UTC time on the entries this call supplies, so the
    dashboard's "last audit" reflects when an assessment was actually made and
    a caller-supplied cached_at cannot backdate it. Entries carried forward from
    disk keep their existing timestamp, so staleness remains detectable.

    The entire read→merge→write sequence is protected by an exclusive file lock
    (audit_cache.json.lock) so that concurrent subagent writers serialize
    correctly and no writer's entries are clobbered by a racing write.

    The write itself goes to `<cache>.tmp` and is renamed over the cache. If that
    rename raises, the temp file is removed and the original exception is
    re-raised, so a failed write leaves the durable cache byte-identical and no
    stray `.tmp` fragment beside it (RULE-43).
    """
    # Validate before touching the filesystem, so a rejected batch leaves the
    # cache on disk exactly as it was.
    _validate_cache_entries(cache)

    # The key is computed here, from the project, and the caller's key is
    # discarded. A caller-supplied key described whatever text the caller sent,
    # so nothing could ever be rechecked against it; re-keying is what makes the
    # reader's recompute meaningful (RULE-38). The auditor stamp lands in the
    # same pass (RULE-39).
    cache = rekey_cache_entries(project_root, cache, cache_name)

    cache_dir = os.path.join(project_root, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, cache_name)
    lock_path = cache_path + '.lock'

    with open(lock_path, 'w', encoding='utf-8') as lock_file:
        _lock_exclusive(lock_file)
        try:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Read existing cache from disk
            on_disk = read_audit_cache(project_root, cache_name)

            # Dedup in two phases: on-disk first, then new entries override.
            # This ensures new entries always win over on-disk for same (feature, proof_id),
            # while intra-batch dedup within each source uses timestamps.
            latest = {}  # (feature, proof_id) -> (hash_key, entry)

            # Phase 1: seed with on-disk entries
            for hash_key, entry in on_disk.items():
                if not isinstance(entry, dict):
                    continue
                dedup_key = (entry.get('feature', ''), entry.get('proof_id', ''))
                existing_entry = latest.get(dedup_key)
                if existing_entry is None or entry.get('cached_at', '') > existing_entry[1].get('cached_at', ''):
                    latest[dedup_key] = (hash_key, entry)

            # Phase 2: new entries always override on-disk for same (feature, proof_id);
            # intra-batch duplicates use timestamp
            new_keys = set()
            for hash_key, entry in cache.items():
                if not isinstance(entry, dict):
                    continue
                dedup_key = (entry.get('feature', ''), entry.get('proof_id', ''))
                existing_entry = latest.get(dedup_key)
                if existing_entry is None:
                    latest[dedup_key] = (hash_key, entry)
                    new_keys.add(dedup_key)
                elif dedup_key not in new_keys:
                    # First new entry for this (feature, proof_id): always beats on-disk
                    latest[dedup_key] = (hash_key, entry)
                    new_keys.add(dedup_key)
                elif entry.get('cached_at', '') > existing_entry[1].get('cached_at', ''):
                    # Intra-batch duplicate: use timestamp
                    latest[dedup_key] = (hash_key, entry)

            # Stamp the real write time on entries this call actually supplied, so
            # "last audit" reflects when an assessment was genuinely made. Entries
            # carried forward from disk keep their original cached_at: re-stamping
            # them made every surviving entry look freshly audited, which left the
            # 24h staleness check in purlin_server._read_audit_summary() unable to
            # ever fire and made last_audit always read as "now".
            pruned = {}
            for dedup_key, (hk, ent) in latest.items():
                if dedup_key in new_keys:
                    ent['cached_at'] = now_iso
                elif not ent.get('cached_at'):
                    # Legacy or hand-edited entry with no timestamp at all; stamping
                    # it is better than leaving the field absent for the reader.
                    ent['cached_at'] = now_iso
                pruned[hk] = ent

            tmp_path = cache_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(pruned, f, indent=2)
            try:
                os.replace(tmp_path, cache_path)
            except BaseException:
                # The rename failed, so the durable cache is still the old file
                # and this temp file holds a write nobody will ever read. Remove
                # it before re-raising: left behind, `.purlin/cache/` accumulates
                # one `<cache>.tmp` per failure, and the next reader listing the
                # directory cannot tell a dead fragment from a live cache
                # (RULE-43). A missing temp file is not an error here.
                try:
                    os.unlink(tmp_path)
                except FileNotFoundError:
                    pass
                raise
        finally:
            _unlock(lock_file)


def _find_plugin_root():
    """Find the Purlin plugin root (project root containing references/)."""
    env = os.environ.get('CLAUDE_PLUGIN_ROOT')
    if env and os.path.isdir(env):
        return env
    # Walk up from this file: scripts/audit/static_checks.py -> project root
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, 'references')):
        return root
    return None


class CriteriaError(RuntimeError):
    """The criteria a grade would be made against cannot be assembled.

    Raised rather than returning '' so an audit stops instead of grading against
    nothing and reporting a number indistinguishable from a real one.
    """


# The first line `purlin:init --sync-audit-criteria` writes into the cached
# additional criteria, naming the commit the file was read at.
_CRITERIA_SHA_RE = re.compile(r'^<!--\s*purlin-criteria-sha:\s*(\S+)\s*-->$')


def load_criteria(project_root, extra_path=None):
    """Load built-in audit criteria + any configured additional criteria.

    SINGLE SOURCE for criteria assembly. All skills call this function
    via --load-criteria instead of implementing their own loading logic.

    Returns the combined criteria text (built-in + optional additional + optional extra).
    """
    # 1. Always read built-in criteria. A missing built-in file is an error, not
    # an empty string: silently grading against no criteria at all produces a
    # number that looks like every other number.
    plugin_root = _find_plugin_root()
    if not plugin_root:
        raise CriteriaError(
            'cannot locate the Purlin plugin root, so references/audit_criteria.md '
            'cannot be read; set CLAUDE_PLUGIN_ROOT')
    builtin_path = os.path.join(plugin_root, 'references', 'audit_criteria.md')
    if not os.path.isfile(builtin_path):
        raise CriteriaError(
            f'built-in criteria missing: {builtin_path} does not exist, so there '
            'are no criteria to grade against')
    with open(builtin_path, encoding='utf-8') as f:
        criteria = f.read()

    # 2. Additional team criteria, cached by `purlin:init --sync-audit-criteria`.
    # When `audit_criteria` is configured the cache must be present and must
    # carry the pin that config records; a mismatch is an error the skill prints
    # rather than a silent fall back to the built-in criteria, which would grade
    # a regulated project against the wrong standard and say nothing (RULE-41).
    cached_path = os.path.join(project_root, '.purlin', 'cache', 'additional_criteria.md')
    config = _read_project_config(project_root)
    configured = config.get('audit_criteria')
    additional = None
    source = configured or 'team criteria'
    if configured:
        if not os.path.isfile(cached_path):
            raise CriteriaError(
                f'audit_criteria is set to {configured} but '
                '.purlin/cache/additional_criteria.md is missing; run '
                'purlin:init --sync-audit-criteria')
        with open(cached_path, encoding='utf-8') as f:
            cached = f.read()
        first_line, _, rest = cached.partition('\n')
        m = _CRITERIA_SHA_RE.match(first_line.strip())
        if not m:
            raise CriteriaError(
                '.purlin/cache/additional_criteria.md has no '
                '<!-- purlin-criteria-sha: <sha> --> first line, so the cached '
                'criteria cannot be matched to audit_criteria_pinned; run '
                'purlin:init --sync-audit-criteria')
        pinned = config.get('audit_criteria_pinned')
        if m.group(1) != pinned:
            raise CriteriaError(
                f'cached criteria are at {m.group(1)} but audit_criteria_pinned '
                f'is {pinned!r}; run purlin:init --sync-audit-criteria')
        additional = rest
    elif os.path.isfile(cached_path):
        # An orphaned cache left behind after `audit_criteria` was removed from
        # config. There is nothing to pin it against, so it is appended as it
        # was, minus its provenance header: the header is a record of where the
        # file came from, not a criterion, and an auditor must never be asked to
        # grade against a comment.
        with open(cached_path, encoding='utf-8') as f:
            cached = f.read()
        first_line, _, rest = cached.partition('\n')
        additional = rest if _CRITERIA_SHA_RE.match(first_line.strip()) else cached
    if additional is not None:
        criteria += f"\n\n---\n\n## Additional Team Criteria (from {source})\n\n{additional}"

    # 3. Append extra file if provided (--criteria flag)
    if extra_path and os.path.isfile(extra_path):
        with open(extra_path, encoding='utf-8') as f:
            extra = f.read()
        criteria += f"\n\n---\n\n## Additional Criteria (from {extra_path})\n\n{extra}"

    return criteria


def clear_audit_cache(project_root):
    """Atomically replace the audit cache with an empty dict.

    Takes the same exclusive lock as write_audit_cache: without it, a clear can
    interleave with a concurrent writer's read/merge/write cycle and the writer
    resurrects everything the clear just removed.
    """
    cache_dir = os.path.join(project_root, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'audit_cache.json')
    lock_path = cache_path + '.lock'
    tmp_path = cache_path + '.tmp'

    with open(lock_path, 'w', encoding='utf-8') as lock_file:
        _lock_exclusive(lock_file)
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            os.replace(tmp_path, cache_path)
        finally:
            _unlock(lock_file)
    return cache_path


def prune_audit_cache(project_root, live_keys):
    """Remove cache entries whose hash key is not in live_keys.

    Called after a full audit to sweep orphaned entries from deleted or
    renamed features.  Entries whose key IS in live_keys are preserved
    with all fields intact.  An empty live_keys set produces an empty
    cache (full sweep).

    The read/filter/write cycle is protected by the same exclusive lock as
    write_audit_cache. Unlocked, a prune could read the cache, a concurrent
    subagent's write could merge new entries, and the prune's write would then
    drop them — the audit skill launches up to three parallel auditors and
    prunes immediately afterwards, so the window is real.
    """
    cache_dir = os.path.join(project_root, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'audit_cache.json')
    lock_path = cache_path + '.lock'
    tmp_path = cache_path + '.tmp'

    with open(lock_path, 'w', encoding='utf-8') as lock_file:
        _lock_exclusive(lock_file)
        try:
            cache = read_audit_cache(project_root)
            pruned = {k: v for k, v in cache.items() if k in live_keys}
            removed = len(cache) - len(pruned)

            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(pruned, f, indent=2)
            os.replace(tmp_path, cache_path)
        finally:
            _unlock(lock_file)

    return {'pruned': removed, 'kept': len(pruned)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _force_utf8_stdio():
    """Reconfigure stdout/stderr to UTF-8 so output containing non-ASCII
    characters (criteria glyphs like ✓/⚠) prints regardless of the OS console
    codec (cp1252 / ASCII on Windows would otherwise raise UnicodeEncodeError).
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass  # not a reconfigurable text stream (e.g. captured/replaced)


def main():
    _force_utf8_stdio()
    # --load-criteria mode: output combined criteria (built-in + additional)
    if '--load-criteria' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        extra_path = None
        if '--extra' in sys.argv:
            idx = sys.argv.index('--extra')
            if idx + 1 < len(sys.argv):
                extra_path = sys.argv[idx + 1]
        try:
            print(load_criteria(project_root, extra_path=extra_path))
        except CriteriaError as exc:
            print(json.dumps({'error': str(exc)}), file=sys.stderr)
            sys.exit(2)
        sys.exit(0)

    # --resolve-source mode: locate a test's source file from its fully-qualified
    # test_name when the proof's test_file is empty (e.g. C#/xUnit under dotnet
    # test, where CodeFilePath is null). Prints JSON {test_name, test_file}.
    if '--resolve-source' in sys.argv:
        idx = sys.argv.index('--resolve-source')
        test_name = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ''
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            j = sys.argv.index('--project-root')
            if j + 1 < len(sys.argv):
                project_root = sys.argv[j + 1]
        ext = '.cs'
        if '--ext' in sys.argv:
            k = sys.argv.index('--ext')
            if k + 1 < len(sys.argv):
                ext = sys.argv[k + 1]
        print(json.dumps({
            "test_name": test_name,
            "test_file": resolve_test_file_from_name(test_name, project_root, ext=ext),
        }))
        sys.exit(0)

    # --cache-key mode: the ONLY way to obtain a cache key. It takes a
    # (feature, proof_id) and reads the rule text, the proof description and the
    # test code out of the project itself, so the key a caller looks up is the
    # key the writer and every reader compute for the same proof. The flag it
    # replaced, --compute-proof-hash, hashed text the caller pasted in, which is
    # why a cached grade could not be checked against anything.
    if '--cache-key' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        feature = proof_id = None
        if '--feature' in sys.argv:
            idx = sys.argv.index('--feature')
            if idx + 1 < len(sys.argv):
                feature = sys.argv[idx + 1]
        if '--proof-id' in sys.argv:
            idx = sys.argv.index('--proof-id')
            if idx + 1 < len(sys.argv):
                proof_id = sys.argv[idx + 1]
        if not feature or not proof_id:
            print(json.dumps({
                'error': '--cache-key requires --feature <name> --proof-id PROOF-N'}))
            sys.exit(2)
        cache_name = DESIGN_CACHE if '--design' in sys.argv else AUDIT_CACHE
        try:
            key, inputs = cache_key_for(project_root, feature, proof_id, cache_name)
        except ProofInputsError as exc:
            print(json.dumps({'error': str(exc)}))
            sys.exit(2)
        print(json.dumps({
            'feature': feature, 'proof_id': proof_id, 'cache': cache_name,
            'key': key, 'inputs': inputs,
        }))
        sys.exit(0)

    # --read-cache mode: read and print audit cache
    if '--read-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        cache = read_audit_cache(project_root)
        print(json.dumps(cache, indent=2))
        sys.exit(0)

    # --write-cache mode: read JSON from stdin and merge into audit cache
    if '--write-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        raw = sys.stdin.read()
        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(json.dumps({'error': f'--write-cache expects a JSON object on stdin: {exc}'}))
            sys.exit(2)
        try:
            write_audit_cache(project_root, entries)
        except ValueError as exc:
            print(json.dumps({'error': str(exc)}))
            sys.exit(2)
        print(json.dumps({'status': 'merged', 'entries': len(entries)}))
        sys.exit(0)

    # --read-design-cache / --write-design-cache: the Proof Design sibling of the
    # audit cache. Same entry shape, same lock, separate file.
    if '--read-design-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        print(json.dumps(read_audit_cache(project_root, DESIGN_CACHE), indent=2))
        sys.exit(0)

    if '--write-design-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        raw = sys.stdin.read()
        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(json.dumps({'error': f'--write-design-cache expects a JSON object on stdin: {exc}'}))
            sys.exit(2)
        try:
            write_audit_cache(project_root, entries, DESIGN_CACHE)
        except ValueError as exc:
            print(json.dumps({'error': str(exc)}))
            sys.exit(2)
        print(json.dumps({'status': 'merged', 'entries': len(entries)}))
        sys.exit(0)

    # --clear-cache mode: atomically replace cache with empty dict
    if '--clear-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        path = clear_audit_cache(project_root)
        print(json.dumps({'status': 'cleared', 'path': path}))
        sys.exit(0)

    # --prune-cache mode: remove entries not in live_keys set
    if '--prune-cache' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        live_keys_file = None
        if '--live-keys-file' in sys.argv:
            idx = sys.argv.index('--live-keys-file')
            if idx + 1 < len(sys.argv):
                live_keys_file = sys.argv[idx + 1]
        if not live_keys_file or not os.path.isfile(live_keys_file):
            print(json.dumps({'error': '--prune-cache requires --live-keys-file <path>'}))
            sys.exit(2)
        with open(live_keys_file, encoding='utf-8') as f:
            live_keys = set(line.strip() for line in f if line.strip())
        if not live_keys:
            # RULE-53: a live-keys file with nothing in it is an audit that
            # computed no key, not an instruction to delete every grade.
            print(json.dumps({'error': (
                f'--prune-cache refused: {live_keys_file} lists no live keys, '
                'and pruning against none would empty the cache')}))
            sys.exit(2)
        result = prune_audit_cache(project_root, live_keys)
        print(json.dumps(result))
        sys.exit(0)

    # --check-proof-design mode: grade proof descriptions, no test code needed
    if '--check-proof-design' in sys.argv:
        spec_path = None
        if '--spec-path' in sys.argv:
            idx = sys.argv.index('--spec-path')
            if idx + 1 < len(sys.argv):
                spec_path = sys.argv[idx + 1]
        if not spec_path or not os.path.isfile(spec_path):
            print(json.dumps({'error': '--check-proof-design requires --spec-path <path>'}))
            sys.exit(2)
        print(json.dumps(check_proof_design(spec_path), indent=2))
        sys.exit(0)

    # --audit-scope mode: report observable state so the audit can derive its mode
    if '--audit-scope' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        print(json.dumps(audit_scope(project_root), indent=2))
        sys.exit(0)

    # --deterministic-sweep mode: grade the whole project with the two model-free
    # passes and print the JSON. Reads no cache and writes nothing, so a CI job
    # can recompute the verdict from a clean checkout.
    if '--deterministic-sweep' in sys.argv:
        project_root = os.getcwd()
        if '--project-root' in sys.argv:
            idx = sys.argv.index('--project-root')
            if idx + 1 < len(sys.argv):
                project_root = sys.argv[idx + 1]
        print(json.dumps(deterministic_sweep(project_root), indent=2))
        sys.exit(0)

    # --check-proof-file mode: run proof-file structural checks (language-agnostic)
    if '--check-proof-file' in sys.argv:
        proof_path = None
        spec_path = None
        if '--proof-path' in sys.argv:
            idx = sys.argv.index('--proof-path')
            if idx + 1 < len(sys.argv):
                proof_path = sys.argv[idx + 1]
        if '--spec-path' in sys.argv:
            idx = sys.argv.index('--spec-path')
            if idx + 1 < len(sys.argv):
                spec_path = sys.argv[idx + 1]
        if not proof_path or not os.path.isfile(proof_path):
            print(json.dumps({'error': '--check-proof-file requires --proof-path <path>'}))
            sys.exit(2)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        print(json.dumps({'findings': findings}, indent=2))
        sys.exit(0)

    # --check-spec-coverage mode: only check spec rules, no test file needed
    if '--check-spec-coverage' in sys.argv:
        spec_path = None
        if '--spec-path' in sys.argv:
            idx = sys.argv.index('--spec-path')
            if idx + 1 < len(sys.argv):
                spec_path = sys.argv[idx + 1]
        if not spec_path or not os.path.isfile(spec_path):
            print(json.dumps({'error': '--check-spec-coverage requires --spec-path <path>'}))
            sys.exit(2)
        result = check_spec_coverage(spec_path)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if len(sys.argv) < 3:
        prog = os.path.basename(sys.argv[0])
        print(f"Usage: {prog} " + f"\n       {prog} ".join(_USAGE), file=sys.stderr)
        sys.exit(2)

    test_file = sys.argv[1]
    feature_name = sys.argv[2]
    spec_path = None
    if '--spec-path' in sys.argv:
        idx = sys.argv.index('--spec-path')
        if idx + 1 < len(sys.argv):
            spec_path = sys.argv[idx + 1]

    if not os.path.isfile(test_file):
        print(json.dumps({'error': f'File not found: {test_file}'}))
        sys.exit(2)

    rule_descs = _read_rule_descriptions(spec_path)
    results = analyze_test_file(test_file, feature_name, rule_descs)

    output = {'proofs': results}
    print(json.dumps(output, indent=2))

    # Exit 0 even when defects are found: findings are communicated via
    # JSON output ("status": "fail"), not exit codes.  Non-zero exits (2)
    # are reserved for real errors (bad args, missing files).
    sys.exit(0)


if __name__ == '__main__':
    main()
