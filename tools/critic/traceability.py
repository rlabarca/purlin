"""Traceability engine: Gherkin scenario-to-test keyword matching.

Extracts keywords from automated scenario titles, discovers test files,
and matches scenarios to test functions using a 2+ keyword threshold.
"""

import os
import re

# Words stripped from scenario titles before keyword extraction
STOP_WORDS = frozenset({
    # Articles
    'a', 'an', 'the',
    # Prepositions
    'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with', 'from', 'via',
    # Conjunctions
    'and', 'or', 'but',
})

# Minimum keyword overlap for a match
MATCH_THRESHOLD = 2


def extract_keywords(scenario_title):
    """Extract keywords from a scenario title.

    Strips articles, prepositions, and conjunctions. Returns lowercase
    keyword set.
    """
    words = re.findall(r'[a-zA-Z0-9_]+', scenario_title.lower())
    return {w for w in words if w not in STOP_WORDS}


def discover_test_files(project_root, feature_stem, tools_root='tools'):
    """Find test files for a feature.

    Looks in:
      1. tests/<feature_stem>/ directory
      2. Tool directories under tools_root matching the feature

    Discovers both test_*.py (Python) and test_*.sh (Bash) files.

    Returns list of absolute file paths.
    """
    test_files = []

    def _is_test_file(fname):
        return fname.startswith('test') and (
            fname.endswith('.py') or fname.endswith('.sh'))

    # Primary: tests/<feature_stem>/
    tests_dir = os.path.join(project_root, 'tests', feature_stem)
    if os.path.isdir(tests_dir):
        for fname in os.listdir(tests_dir):
            if _is_test_file(fname):
                test_files.append(os.path.join(tests_dir, fname))

    # Secondary: scan tools root and tool subdirectories for test files
    tools_abs = os.path.join(project_root, tools_root)
    if os.path.isdir(tools_abs):
        for entry in os.listdir(tools_abs):
            entry_path = os.path.join(tools_abs, entry)
            if os.path.isdir(entry_path):
                for fname in os.listdir(entry_path):
                    if _is_test_file(fname):
                        fpath = os.path.join(entry_path, fname)
                        if fpath not in test_files:
                            test_files.append(fpath)
            elif _is_test_file(entry):
                if entry_path not in test_files:
                    test_files.append(entry_path)

    return test_files


def extract_test_functions(filepath):
    """Extract test function names and bodies from a Python test file.

    Returns list of dicts: [{"name": "test_foo", "body": "..."}]
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except (IOError, OSError):
        return []

    functions = []
    # Match 'def test_...' at any indentation level
    pattern = re.compile(r'^( *)def (test_\w+)\s*\(', re.MULTILINE)

    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        indent = len(match.group(1))
        name = match.group(2)
        start = match.start()

        # Find end of function: next def at same or lower indent, or EOF
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)

        body = content[start:end]
        functions.append({'name': name, 'body': body})

    return functions


def extract_bash_test_scenarios(filepath):
    """Extract test scenario entries from a Bash test file.

    Parses lines matching echo "[Scenario] <title>" as entry points.
    Each entry = marker line + surrounding context up to next marker or EOF.

    Returns list of dicts: [{"name": "<title>", "body": "..."}]
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except (IOError, OSError):
        return []

    entries = []
    lines = content.split('\n')
    marker_pattern = re.compile(r'''echo\s+['"]?\[Scenario\]\s*(.+?)['"]?\s*$''')

    # Find all marker positions
    markers = []
    for i, line in enumerate(lines):
        match = marker_pattern.search(line.strip())
        if match:
            markers.append((i, match.group(1).strip()))

    for idx, (line_num, title) in enumerate(markers):
        # Context runs from marker to next marker or EOF
        if idx + 1 < len(markers):
            end_line = markers[idx + 1][0]
        else:
            end_line = len(lines)
        body = '\n'.join(lines[line_num:end_line])
        entries.append({'name': title, 'body': body})

    return entries


def extract_test_entries(filepath):
    """Dispatch test entry extraction based on file type.

    .py files -> extract_test_functions (Python)
    .sh files -> extract_bash_test_scenarios (Bash)

    Returns list of dicts: [{"name": str, "body": str}]
    """
    if filepath.endswith('.py'):
        return extract_test_functions(filepath)
    elif filepath.endswith('.sh'):
        return extract_bash_test_scenarios(filepath)
    return []


def match_scenario_to_tests(scenario_keywords, test_functions):
    """Match a scenario's keywords against test functions.

    Returns list of matching test function names. A match requires
    MATCH_THRESHOLD or more keywords present in the test function name
    or body.
    """
    matches = []
    for func in test_functions:
        # Tokenize function name and body
        func_text = func['name'] + ' ' + func['body']
        func_words = set(re.findall(r'[a-zA-Z0-9_]+', func_text.lower()))

        # Also split snake_case names into parts
        name_parts = set(func['name'].lower().split('_'))
        func_words |= name_parts

        overlap = scenario_keywords & func_words
        if len(overlap) >= MATCH_THRESHOLD:
            matches.append(func['name'])

    return matches


def parse_traceability_overrides(impl_notes_text):
    """Parse traceability_overrides from Implementation Notes.

    Format: - traceability_override: "Scenario Title" -> test_function_name

    Returns dict: {"Scenario Title": "test_function_name"}
    """
    overrides = {}
    pattern = re.compile(
        r'-\s*traceability_override:\s*"([^"]+)"\s*->\s*(\S+)'
    )
    for match in pattern.finditer(impl_notes_text):
        overrides[match.group(1)] = match.group(2)
    return overrides


def run_traceability(scenarios, project_root, feature_stem,
                     tools_root='tools', impl_notes=''):
    """Run full traceability analysis for a feature.

    Args:
        scenarios: list of dicts with 'title' and 'is_manual' keys
        project_root: absolute path to project root
        feature_stem: feature file stem (e.g., 'cdd_status_monitor')
        tools_root: relative path to tools directory
        impl_notes: raw Implementation Notes text for override parsing

    Returns:
        dict with 'status', 'coverage', 'detail', 'matched', 'unmatched'
    """
    overrides = parse_traceability_overrides(impl_notes)

    # Discover test files and extract entries (Python functions or Bash scenarios)
    test_files = discover_test_files(project_root, feature_stem, tools_root)
    all_test_functions = []
    for tf in test_files:
        all_test_functions.extend(extract_test_entries(tf))

    automated = [s for s in scenarios if not s.get('is_manual', False)]
    if not automated:
        return {
            'status': 'PASS',
            'coverage': 1.0,
            'detail': 'No automated scenarios to trace.',
            'matched': [],
            'unmatched': [],
        }

    matched = []
    unmatched = []

    for scenario in automated:
        title = scenario['title']

        # Check overrides first
        if title in overrides:
            override_func = overrides[title]
            # Verify override target exists
            if any(f['name'] == override_func for f in all_test_functions):
                matched.append({
                    'scenario': title,
                    'tests': [override_func],
                    'via': 'override',
                })
                continue

        keywords = extract_keywords(title)
        if not keywords:
            unmatched.append({'scenario': title, 'reason': 'no keywords'})
            continue

        test_matches = match_scenario_to_tests(keywords, all_test_functions)
        if test_matches:
            matched.append({
                'scenario': title,
                'tests': test_matches,
                'via': 'keyword',
            })
        else:
            unmatched.append({
                'scenario': title,
                'reason': 'no matching tests',
                'keywords': sorted(keywords),
            })

    total = len(automated)
    matched_count = len(matched)
    coverage = matched_count / total if total > 0 else 1.0

    if coverage >= 1.0:
        status = 'PASS'
    elif coverage >= 0.8:
        status = 'WARN'
    else:
        status = 'FAIL'

    detail_parts = [f'{matched_count}/{total} automated scenarios traced']
    if unmatched:
        detail_parts.append(
            f'Unmatched: {", ".join(u["scenario"] for u in unmatched)}'
        )

    return {
        'status': status,
        'coverage': round(coverage, 4),
        'detail': '. '.join(detail_parts),
        'matched': matched,
        'unmatched': unmatched,
    }
