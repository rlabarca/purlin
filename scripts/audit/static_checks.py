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
import hashlib
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
    """Detect tautological assertions: assert True, assert x is not None, assert len(x) >= 0.

    Returns None if no tautological assertion found, or a dict with:
      'literal': True  — for assert True, assertTrue(True)
      'literal': False — for assert x is not None, assert len(x) >= 0
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            test = child.test
            # assert True
            if isinstance(test, ast.Constant) and test.value is True:
                return {'literal': True}
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
    with open(filepath) as f:
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
    with open(filepath) as f:
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
                'literal': True,
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

_STRUCTURAL_RULE_RE = re.compile(
    r'grep|verify\s.*exist|verify\s.*present|verify\s.*section'
    r'|verify\s.*field|verify\s.*appear|verify\s.*contain'
    r'|file\s+exists|contains?\s+section|contains?\s+field',
    re.IGNORECASE,
)

_BEHAVIORAL_RULE_RE = re.compile(
    r'returns?|rejects?|blocks?|logs?|sends?|creates?|deletes?'
    r'|updates?|computes?|detects?|emits?|produces?|triggers?'
    r'|fails?|raises?|validates?|enforces?|prevents?',
    re.IGNORECASE,
)


def _read_rule_descriptions(spec_path):
    """Read rule descriptions from a spec file."""
    if not spec_path or not os.path.isfile(spec_path):
        return {}
    with open(spec_path) as f:
        content = f.read()
    return {m.group(1): m.group(2).strip() for m in _RULE_LINE_RE.finditer(content)}


def check_spec_coverage(spec_path):
    """Check whether a spec's rules are behavioral or structural-only.

    Returns dict with structural_only_spec, rule_count, behavioral_rule_count,
    plus per-rule structural/behavioral classification.
    """
    rules = _read_rule_descriptions(spec_path)
    if not rules:
        return {'structural_only_spec': False, 'rule_count': 0, 'behavioral_rule_count': 0,
                'structural_proofs': [], 'behavioral_proofs': [], 'structural_count': 0, 'behavioral_count': 0}

    structural_proofs = []
    behavioral_proofs = []
    for rule_id, desc in rules.items():
        if _BEHAVIORAL_RULE_RE.search(desc):
            behavioral_proofs.append(rule_id)
        elif _STRUCTURAL_RULE_RE.search(desc):
            structural_proofs.append(rule_id)
        else:
            # If it doesn't match structural patterns either, assume behavioral
            behavioral_proofs.append(rule_id)

    return {
        'structural_only_spec': len(behavioral_proofs) == 0,
        'rule_count': len(rules),
        'behavioral_rule_count': len(behavioral_proofs),
        'structural_proofs': sorted(structural_proofs),
        'behavioral_proofs': sorted(behavioral_proofs),
        'structural_count': len(structural_proofs),
        'behavioral_count': len(behavioral_proofs),
    }

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
            with open(cache_path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def write_audit_cache(project_root, cache):
    """Write audit cache atomically, pruning stale duplicates.

    When test code changes, the proof hash changes and a new entry is added
    but the old entry stays. This prunes duplicates by (feature, proof_id),
    keeping only the entry with the latest cached_at timestamp.
    """
    # Prune: keep only latest entry per (feature, proof_id)
    latest = {}  # (feature, proof_id) -> (hash_key, entry)
    for hash_key, entry in cache.items():
        if not isinstance(entry, dict):
            continue
        dedup_key = (entry.get('feature', ''), entry.get('proof_id', ''))
        existing = latest.get(dedup_key)
        if existing is None or entry.get('cached_at', '') > existing[1].get('cached_at', ''):
            latest[dedup_key] = (hash_key, entry)

    pruned = {hk: ent for hk, ent in latest.values()}

    cache_dir = os.path.join(project_root, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'audit_cache.json')
    tmp_path = cache_path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(pruned, f, indent=2)
    os.replace(tmp_path, cache_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
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
        print(f"Usage: {sys.argv[0]} <test_file> <feature_name> [--spec-path <path>]", file=sys.stderr)
        print(f"       {sys.argv[0]} --check-spec-coverage --spec-path <path>", file=sys.stderr)
        print(f"       {sys.argv[0]} --compute-proof-hash --rule <text> --proof-desc <text> --test-code <text>", file=sys.stderr)
        print(f"       {sys.argv[0]} --read-cache [--project-root <path>]", file=sys.stderr)
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

    # Exit 0 even when defects are found — findings are communicated via
    # JSON output ("status": "fail"), not exit codes.  Non-zero exits (2)
    # are reserved for real errors (bad args, missing files).
    sys.exit(0)


if __name__ == '__main__':
    main()
