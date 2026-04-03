#!/usr/bin/env python3
"""Deterministic static checks for proof quality — no LLM required.

Catches structural test problems (assert True, no assertions, logic mirroring,
bare except, mock-target match) using Python's ast module and regex.

Usage:
    python3 scripts/audit/static_checks.py <test_file> <feature_name> [--spec-path <path>]

Exit code 0 = all proofs passed, 1 = at least one failed.
Output: JSON to stdout with per-proof results.
"""

import ast
import json
import os
import re
import sys

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


def _check_assert_true(node, source):
    """Detect tautological assertions: assert True, assert x is not None, assert len(x) >= 0."""
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            test = child.test
            # assert True
            if isinstance(test, ast.Constant) and test.value is True:
                return True
            # assert result is not None
            if isinstance(test, ast.Compare):
                if len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot):
                    if len(test.comparators) == 1:
                        comp = test.comparators[0]
                        if isinstance(comp, ast.Constant) and comp.value is None:
                            return True
                # assert len(x) >= 0
                if len(test.ops) == 1 and isinstance(test.ops[0], ast.GtE):
                    if len(test.comparators) == 1:
                        comp = test.comparators[0]
                        if isinstance(comp, ast.Constant) and comp.value == 0:
                            if isinstance(test.left, ast.Call):
                                fn = test.left.func
                                if isinstance(fn, ast.Name) and fn.id == 'len':
                                    return True
        # self.assertTrue(True)
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr == 'assertTrue':
                if child.args and isinstance(child.args[0], ast.Constant) and child.args[0].value is True:
                    return True
    return False


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
    with open(filepath) as f:
        source = f.read()
    proofs = _get_python_proofs_and_functions(source, feature_name)
    results = []
    for proof_id, rule_id, test_name, func_node in proofs:
        checks_failed = []
        if _check_assert_true(func_node, source):
            checks_failed.append(('assert_true', 'tautological assertion (assert True or equivalent)'))
        if not _has_assertion(func_node):
            checks_failed.append(('no_assertions', 'test function has no assertion statements'))
        if _check_bare_except(func_node):
            checks_failed.append(('bare_except', 'bare except:pass swallows failures'))
        if _check_logic_mirroring(func_node):
            checks_failed.append(('logic_mirroring', 'expected value computed by same function as SUT'))
        rdesc = rule_descs.get(rule_id, '')
        if rdesc and _check_mock_target_match(func_node, source, rdesc):
            checks_failed.append(('mock_target_match', 'mock target matches the function the rule describes'))

        if checks_failed:
            # Report the first failure (most severe)
            check, reason = checks_failed[0]
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_name, 'status': 'fail',
                'check': check, 'reason': reason,
            })
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
    with open(filepath) as f:
        content = f.read()
    lines = content.splitlines()
    results = []
    proof_locations = []
    for i, line in enumerate(lines):
        m = _SHELL_PROOF_RE.search(line)
        if m and m.group(1) == feature_name:
            proof_locations.append((i, m.group(2), m.group(3), m.group(4)))

    for idx, (line_no, proof_id, rule_id, status) in enumerate(proof_locations):
        # Check assert_true: hardcoded pass with no test logic before it
        if status == 'pass':
            # Look backwards for test logic between this proof and the previous one
            start = proof_locations[idx - 1][0] + 1 if idx > 0 else 0
            segment = '\n'.join(lines[start:line_no])
            has_logic = bool(re.search(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\|', segment))
            if not has_logic:
                results.append({
                    'proof_id': proof_id, 'rule_id': rule_id,
                    'test_name': f'line_{line_no + 1}', 'status': 'fail',
                    'check': 'assert_true', 'reason': 'hardcoded pass with no preceding test logic',
                })
                continue

        # Check no_assertions: no assertion commands between this and previous proof
        start = proof_locations[idx - 1][0] + 1 if idx > 0 else 0
        segment = '\n'.join(lines[start:line_no])
        has_assertion = bool(re.search(r'\btest\b|\[|\bgrep\b|\bdiff\b|\|\|', segment))
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
# JavaScript/TypeScript checks (regex-based)
# ---------------------------------------------------------------------------

def check_js(filepath, feature_name):
    """Run JS/TS test checks. Returns list of proof result dicts."""
    with open(filepath) as f:
        content = f.read()
    results = []
    # Find test blocks with proof markers
    test_pattern = re.compile(
        r'(?:it|test)\s*\(\s*["\']([^"\']*\[proof:' + re.escape(feature_name)
        + r':([^:\]]+):([^:\]]+)[^\]]*\][^"\']*)["\']'
        r'\s*,\s*(?:async\s*)?\(\s*\)\s*=>\s*\{(.*?)\}\s*\)',
        re.DOTALL
    )
    for m in test_pattern.finditer(content):
        test_title = m.group(1)
        proof_id = m.group(2)
        rule_id = m.group(3)
        body = m.group(4)

        # Check assert_true
        if re.search(r'expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)', body):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_title[:60], 'status': 'fail',
                'check': 'assert_true', 'reason': 'expect(true).toBe(true) is tautological',
            })
            continue

        if re.search(r'expect\s*\([^)]+\)\s*\.toBeTruthy\s*\(\s*\)', body) and not re.search(r'expect\s*\(', body.replace(re.search(r'expect\s*\([^)]+\)\s*\.toBeTruthy\s*\(\s*\)', body).group(), '', 1)):
            # Only flag if toBeTruthy is the sole expect and there's no meaningful setup
            pass

        # Check no_assertions
        if not re.search(r'expect\s*\(', body):
            results.append({
                'proof_id': proof_id, 'rule_id': rule_id,
                'test_name': test_title[:60], 'status': 'fail',
                'check': 'no_assertions', 'reason': 'test function has no expect() calls',
            })
            continue

        results.append({
            'proof_id': proof_id, 'rule_id': rule_id,
            'test_name': test_title[:60], 'status': 'pass',
            'reason': 'structural checks passed',
        })
    return results

# ---------------------------------------------------------------------------
# Spec reading (for mock_target_match)
# ---------------------------------------------------------------------------

_RULE_LINE_RE = re.compile(r'^-\s+(RULE-\d+):\s*(.+)', re.MULTILINE)


def _read_rule_descriptions(spec_path):
    """Read rule descriptions from a spec file."""
    if not spec_path or not os.path.isfile(spec_path):
        return {}
    with open(spec_path) as f:
        content = f.read()
    return {m.group(1): m.group(2).strip() for m in _RULE_LINE_RE.finditer(content)}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <test_file> <feature_name> [--spec-path <path>]", file=sys.stderr)
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
    ext = os.path.splitext(test_file)[1].lower()

    if ext == '.py':
        results = check_python(test_file, feature_name, rule_descs)
    elif ext == '.sh':
        results = check_shell(test_file, feature_name)
    elif ext in ('.js', '.ts', '.jsx', '.tsx'):
        results = check_js(test_file, feature_name)
    else:
        results = []

    output = {'proofs': results}
    print(json.dumps(output, indent=2))

    any_fail = any(r['status'] == 'fail' for r in results)
    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
