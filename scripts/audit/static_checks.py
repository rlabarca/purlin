#!/usr/bin/env python3
"""Deterministic static checks for proof quality — no LLM required.

Catches structural test problems (assert True, no assertions, logic mirroring,
bare except, mock-target match) using Python's ast module and regex.

Usage (see _USAGE below — it is the single source for this list):
    static_checks.py <test_file> <feature_name> [--spec-path <path>]
    static_checks.py --check-proof-file --proof-path <path> [--spec-path <path>]
    static_checks.py --check-spec-coverage --spec-path <path>
    static_checks.py --compute-proof-hash --rule <text> --proof-desc <text> --test-code <text>
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
import datetime
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

def _get_python_proofs_and_functions(source, feature_name):
    """Parse Python file, return list of (proof_id, rule_id, test_name, func_node)."""
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test_'):
            continue
        for deco in node.decorator_list:
            src_line = ast.get_source_segment(source, deco) or ''
            m = _PROOF_MARKER_RE.search(src_line)
            if m and m.group(1) == feature_name:
                results.append((m.group(2), m.group(3), node.name, node))
    return results


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


def _check_mock_target_match(node, source, rule_desc):
    """Detect mock/patch targeting the function the rule describes."""
    if not rule_desc:
        return False
    rule_words = set(re.findall(r'[a-z_]\w+', rule_desc.lower()))
    rule_words -= {'the', 'and', 'or', 'is', 'are', 'must', 'should', 'will',
                   'with', 'for', 'not', 'that', 'this', 'from', 'have', 'has',
                   'rule', 'test', 'all', 'any', 'each', 'when', 'then', 'can',
                   'does', 'use', 'using', 'used', 'into', 'returns', 'return',
                   'code', 'file', 'function', 'method', 'class'}

    for deco in node.decorator_list:
        deco_src = ast.get_source_segment(source, deco) or ''
        # Look for @patch("some.module.func") or @mock.patch(...)
        patch_targets = re.findall(r'patch\(["\']([^"\']+)["\']', deco_src)
        for target in patch_targets:
            # Check both the basename and all parts of the dotted path
            parts = {p.lower() for p in target.split('.')}
            if parts & rule_words:
                return True

    # Also check mock.patch context managers in the body
    func_src = ast.get_source_segment(source, node) or ''
    ctx_targets = re.findall(r'mock\.patch\(["\']([^"\']+)["\']', func_src)
    for target in ctx_targets:
        parts = {p.lower() for p in target.split('.')}
        if parts & rule_words:
            return True

    return False


def check_python(filepath, feature_name, rule_descs=None):
    """Run all Python checks. Returns list of proof result dicts."""
    rule_descs = rule_descs or {}
    with open(filepath, encoding='utf-8') as f:
        source = f.read()
    proofs = _get_python_proofs_and_functions(source, feature_name)
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
        if rdesc and _check_mock_target_match(func_node, source, rdesc):
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

def check_shell(filepath, feature_name):
    """Run shell test checks. Returns list of proof result dicts."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
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
            # if/else pair — use the earlier line, treat as single proof
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
            # if/else pair — check that the segment has real test logic
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

        # Single proof — original logic (no \bif\b in pattern)
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


def check_js(filepath, feature_name):
    """Run JS/TS test checks. Returns list of proof result dicts."""
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    results = []
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
        proof_id = marker.group(1)
        rule_id = marker.group(2)

        body, after_body = _find_test_body(content, after_title)
        if body is None:
            # No block body to inspect — cannot run body checks; skip.
            i = after_title
            continue
        i = after_body

        # Check assert_true
        if re.search(r'expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)', body):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': title[:60], 'status': 'fail',
                'check': 'assert_true', 'reason': 'expect(true).toBe(true) is tautological',
                'literal': True,
            })
            continue

        # Check no_assertions
        if not re.search(r'expect\s*\(', body):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': title[:60], 'status': 'fail',
                'check': 'no_assertions', 'reason': 'test function has no expect() calls',
            })
            continue

        results.append({
            'proof_id': proof_id, 'rule_id': rule_id,
            'test_name': title[:60], 'status': 'pass',
            'reason': 'structural checks passed',
        })
    return results


# ---------------------------------------------------------------------------
# C# / .NET (xUnit / NUnit / MSTest) checks
# ---------------------------------------------------------------------------

def _read_csharp_balanced(content, i, opener, closer):
    """content[i] is `opener`. Return (inner_text, index_after_matching_close).

    Skips C# strings (regular, verbatim @"", interpolated $""), char literals,
    and // and /* */ comments so their contents never affect bracket depth.
    """
    n = len(content)
    depth = 0
    j = i
    start_inner = i + 1
    while j < n:
        c = content[j]
        if c == '/' and content[j + 1:j + 2] == '/':
            nl = content.find('\n', j)
            j = n if nl < 0 else nl
            continue
        if c == '/' and content[j + 1:j + 2] == '*':
            e = content.find('*/', j + 2)
            j = n if e < 0 else e + 2
            continue
        if c == '@' and content[j + 1:j + 2] == '"':  # verbatim string: "" escapes a quote
            j += 2
            while j < n:
                if content[j] == '"':
                    if content[j + 1:j + 2] == '"':
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            continue
        if c == '"':  # regular or interpolated string ($ prefix already passed over)
            j += 1
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == '"':
                    j += 1
                    break
                j += 1
            continue
        if c == "'":  # char literal
            j += 1
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == "'":
                    j += 1
                    break
                j += 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return content[start_inner:j], j + 1
        j += 1
    return content[start_inner:j], j  # unterminated


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


def check_csharp(filepath, feature_name, rule_descs=None):
    """Run C#/.NET (xUnit/NUnit/MSTest) test checks. Returns list of proof dicts.

    Parses `[Trait("PurlinProof", "feature:PROOF-N:RULE-N:tier")]` markers, finds
    each marked test method's body, and applies assert-true / no-assertion
    detection. Recognizes xUnit `Assert.*`, NUnit `Assert.That`, MSTest `Assert.*`,
    FluentAssertions `.Should()`, and Playwright `Expect(...).To*Async()` as assertions.
    """
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    results = []
    marker_re = re.compile(
        r'\[\s*Trait\s*\(\s*"PurlinProof"\s*,\s*"'
        + re.escape(feature_name)
        + r':([^:"\]]+):([^:"\]]+):[^"]*"\s*\)\s*\]'
    )
    for m in marker_re.finditer(content):
        proof_id = m.group(1)
        rule_id = m.group(2)
        body, _after, method_name = _find_csharp_body(content, m.end())
        if body is None:
            # No block body to inspect (expression-bodied or abstract) — skip.
            continue
        test_name = (method_name or proof_id)[:60]

        # assert_true: tautological assertions across the supported frameworks.
        if (re.search(r'Assert\s*\.\s*(?:True|IsTrue)\s*\(\s*true\s*\)', body)
                or re.search(r'Assert\s*\.\s*(?:Equal|AreEqual)\s*\(\s*true\s*,\s*true\s*\)', body)):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_name, 'status': 'fail',
                'check': 'assert_true', 'reason': 'Assert.True(true) is tautological',
                'literal': True,
            })
            continue

        # no_assertions: no recognized assertion call in the body.
        # xUnit/NUnit/MSTest `Assert.`, FluentAssertions `.Should(`, Moq `.Verify(`.
        has_assert = re.search(r'\bAssert\s*\.', body)
        has_should = re.search(r'\.\s*Should\s*\(', body)
        has_verify = re.search(r'\.\s*Verify\s*\(', body)
        # Playwright fluent assertions: Expect(...)/Assertions.Expect(...) chained to a
        # To<Matcher>Async() call (ToBeVisibleAsync, ToHaveTextAsync, ToContainTextAsync, ...).
        # Both tokens are required so a bare Expect(x) with no matcher is still flagged, and a
        # plain LINQ `.ToListAsync()` (no Expect) is not mistaken for an assertion.
        has_playwright = (re.search(r'\bExpect\s*\(', body)
                          and re.search(r'\.\s*To\w+Async\s*\(', body))
        if not (has_assert or has_should or has_verify or has_playwright):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_name, 'status': 'fail',
                'check': 'no_assertions',
                'reason': 'test method has no Assert./.Should()/.Verify()/Expect(...).To*Async() call',
            })
            continue

        results.append({
            'proof_id': proof_id, 'rule_id': rule_id,
            'test_name': test_name, 'status': 'pass',
            'reason': 'structural checks passed',
        })
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


def analyze_test_file(test_file, feature_name, rule_descs=None):
    """Dispatch a test file to the language checker matching its extension.

    Returns the list of proof result dicts, or [] for unsupported extensions.
    """
    ext = os.path.splitext(test_file)[1].lower()
    if ext == '.py':
        return check_python(test_file, feature_name, rule_descs)
    if ext == '.sh':
        return check_shell(test_file, feature_name)
    if ext in ('.js', '.ts', '.jsx', '.tsx'):
        return check_js(test_file, feature_name)
    if ext == '.cs':
        return check_csharp(test_file, feature_name, rule_descs)
    return []


# ---------------------------------------------------------------------------
# Spec reading (for mock_target_match)
# ---------------------------------------------------------------------------

_RULE_LINE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)

def _read_rule_descriptions(spec_path):
    """Read rule descriptions from a spec file."""
    if not spec_path or not os.path.isfile(spec_path):
        return {}
    with open(spec_path, encoding='utf-8') as f:
        content = f.read()
    return {m.group(1): m.group(2).strip() for m in _RULE_LINE_RE.finditer(content)}


_PROOF_DESC_RE = re.compile(
    r'^-\s+(PROOF-\d+)\s*\((RULE-\d+(?:,\s*RULE-\d+)*)\):\s*(.+)',
    re.MULTILINE,
)

_TIER_TAG_RE = re.compile(r'\s*@\w+(?:\([^)]*\))?\s*$')


def _read_proof_descriptions(spec_path):
    """Read proof descriptions from a spec file's ## Proof section.

    Returns list of dicts with proof_id, rule_ids, and description.
    """
    if not spec_path or not os.path.isfile(spec_path):
        return []
    with open(spec_path, encoding='utf-8') as f:
        content = f.read()
    proof_section_match = re.search(
        r'^## Proof\s*\n(.*?)(?=^## |\Z)',
        content, re.MULTILINE | re.DOTALL,
    )
    if not proof_section_match:
        return []
    proof_section = proof_section_match.group(1)
    results = []
    for m in _PROOF_DESC_RE.finditer(proof_section):
        desc = _TIER_TAG_RE.sub('', m.group(3)).strip()
        results.append({
            'proof_id': m.group(1),
            'rule_ids': m.group(2),
            'description': desc,
        })
    return results


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
# Proof-file structural checks (Pass 0.5 — language-agnostic, JSON-only)
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

    # Check 1: proof_id_collision — same PROOF-N targeting different RULE-N values
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

    # Check 2: proof_rule_orphan — proof targets a rule not in the spec
    if spec_path and os.path.isfile(spec_path):
        spec_rules = set(_read_rule_descriptions(spec_path).keys())
        if spec_rules:
            for entry in proofs:
                rid = entry.get('rule', '')
                # Only check own rules (no "/" prefix — required rules come from anchors)
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


def read_audit_cache(project_root):
    """Read .purlin/cache/audit_cache.json. Returns dict of proof_hash → assessment."""
    cache_path = os.path.join(project_root, '.purlin', 'cache', 'audit_cache.json')
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


def _unlock(lock_file):
    """Release a lock acquired by _lock_exclusive."""
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
# appears here, which is what went wrong before — the help text had gone stale and
# omitted five real flags.
_USAGE = (
    "<test_file> <feature_name> [--spec-path <path>]",
    "--check-proof-file --proof-path <path> [--spec-path <path>]",
    "--check-spec-coverage --spec-path <path>",
    "--compute-proof-hash --rule <text> --proof-desc <text> --test-code <text>",
    "--resolve-source <test_name> [--project-root <path>] [--ext .cs]",
    "--load-criteria [--project-root <path>] [--extra <path>]",
    "--read-cache [--project-root <path>]",
    "--write-cache [--project-root <path>]      (JSON object of entries on stdin)",
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


def write_audit_cache(project_root, cache):
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
    """
    # Validate before touching the filesystem, so a rejected batch leaves the
    # cache on disk exactly as it was.
    _validate_cache_entries(cache)

    cache_dir = os.path.join(project_root, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'audit_cache.json')
    lock_path = cache_path + '.lock'

    with open(lock_path, 'w', encoding='utf-8') as lock_file:
        _lock_exclusive(lock_file)
        try:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Read existing cache from disk
            on_disk = read_audit_cache(project_root)

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
                    # First new entry for this (feature, proof_id) — always beats on-disk
                    latest[dedup_key] = (hash_key, entry)
                    new_keys.add(dedup_key)
                elif entry.get('cached_at', '') > existing_entry[1].get('cached_at', ''):
                    # Intra-batch duplicate — use timestamp
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
            os.replace(tmp_path, cache_path)
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


def load_criteria(project_root, extra_path=None):
    """Load built-in audit criteria + any configured additional criteria.

    SINGLE SOURCE for criteria assembly. All skills call this function
    via --load-criteria instead of implementing their own loading logic.

    Returns the combined criteria text (built-in + optional additional + optional extra).
    """
    # 1. Always read built-in criteria
    plugin_root = _find_plugin_root()
    if not plugin_root:
        return ''
    builtin_path = os.path.join(plugin_root, 'references', 'audit_criteria.md')
    if not os.path.isfile(builtin_path):
        return ''
    with open(builtin_path, encoding='utf-8') as f:
        criteria = f.read()

    # 2. Check for cached additional criteria (saved by purlin:init --sync-audit-criteria)
    cached_path = os.path.join(project_root, '.purlin', 'cache', 'additional_criteria.md')
    if os.path.isfile(cached_path):
        with open(cached_path, encoding='utf-8') as f:
            additional = f.read()
        # Read source URL from config for the separator header
        source = 'team criteria'
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        if os.path.isfile(config_path):
            try:
                with open(config_path, encoding='utf-8') as f:
                    config = json.load(f)
                source = config.get('audit_criteria', source)
            except (json.JSONDecodeError, OSError):
                pass
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
        print(load_criteria(project_root, extra_path=extra_path))
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

    # --compute-proof-hash mode: hash inputs for cache key
    if '--compute-proof-hash' in sys.argv:
        rule_text = ''
        proof_desc = ''
        test_code = ''
        if '--rule' in sys.argv:
            idx = sys.argv.index('--rule')
            if idx + 1 < len(sys.argv):
                rule_text = sys.argv[idx + 1]
        if '--proof-desc' in sys.argv:
            idx = sys.argv.index('--proof-desc')
            if idx + 1 < len(sys.argv):
                proof_desc = sys.argv[idx + 1]
        if '--test-code' in sys.argv:
            idx = sys.argv.index('--test-code')
            if idx + 1 < len(sys.argv):
                test_code = sys.argv[idx + 1]
        print(compute_proof_hash(rule_text, proof_desc, test_code))
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
        result = prune_audit_cache(project_root, live_keys)
        print(json.dumps(result))
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

    # Exit 0 even when defects are found — findings are communicated via
    # JSON output ("status": "fail"), not exit codes.  Non-zero exits (2)
    # are reserved for real errors (bad args, missing files).
    sys.exit(0)


if __name__ == '__main__':
    main()
