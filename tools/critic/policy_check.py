"""Policy adherence scanner: FORBIDDEN pattern detection.

Discovers FORBIDDEN patterns from anchor node files (arch_*.md, design_*.md,
policy_*.md) and scans implementation files for violations. Supports both
inline FORBIDDEN: markers and structured FORBIDDEN Patterns sections with
Grepable pattern and Scan scope sub-fields.
"""

import glob as glob_module
import os
import re


def _is_anchor_node(fname):
    """Check if a filename is an anchor node (arch_*, design_*, policy_*)."""
    return (fname.startswith('arch_') or fname.startswith('design_')
            or fname.startswith('policy_'))


def discover_forbidden_patterns(features_dir):
    """Scan anchor node files for FORBIDDEN patterns.

    Supports two formats:
    1. Inline: ``FORBIDDEN: some_pattern`` on a single line
    2. Structured section: ``### FORBIDDEN Patterns`` heading with
       ``**Grepable pattern:**`` and ``**Scan scope:**`` sub-fields

    Returns dict: {anchor_file: [{"pattern": str, "line": int, "scope": str|None}]}
    """
    patterns = {}

    if not os.path.isdir(features_dir):
        return patterns

    for fname in sorted(os.listdir(features_dir)):
        if not (_is_anchor_node(fname) and fname.endswith('.md')):
            continue

        filepath = os.path.join(features_dir, fname)
        file_patterns = []

        try:
            with open(filepath, 'r') as f:
                lines = list(f)
        except (IOError, OSError):
            continue

        in_forbidden_section = False
        current_scope = None

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Format 1: Inline FORBIDDEN: markers
            inline_match = re.search(r'FORBIDDEN:\s*(.+)', stripped)
            if inline_match and not re.match(r'^#{2,4}\s+', stripped):
                pattern_text = inline_match.group(1).strip()
                pattern_text = pattern_text.rstrip('`').strip()
                if pattern_text:
                    file_patterns.append({
                        'pattern': pattern_text,
                        'line': line_num,
                        'scope': None,
                    })
                continue

            # Format 2: Structured FORBIDDEN Patterns section
            if re.match(r'^#{2,4}\s+.*FORBIDDEN\s+Patterns', stripped):
                in_forbidden_section = True
                current_scope = None
                continue

            if in_forbidden_section:
                # End of section: next heading at same or higher level
                if re.match(r'^#{2,4}\s+', stripped) and 'FORBIDDEN' not in stripped:
                    in_forbidden_section = False
                    current_scope = None
                    continue

                # Grepable pattern sub-field
                grepable = re.search(
                    r'\*\*Grepable pattern:\*\*.*?`([^`]+)`', stripped)
                if grepable:
                    pattern_text = grepable.group(1)
                    # Always None here; the following Scan scope line fills it
                    file_patterns.append({
                        'pattern': pattern_text,
                        'line': line_num,
                        'scope': None,
                    })
                    current_scope = None
                    continue

                # Scan scope sub-field
                scope_match = re.search(
                    r'\*\*Scan scope:\*\*.*?`([^`]+)`', stripped)
                if scope_match:
                    current_scope = scope_match.group(1)
                    # Attach scope to the most recent pattern
                    if file_patterns and file_patterns[-1]['scope'] is None:
                        file_patterns[-1]['scope'] = current_scope
                    continue

        if file_patterns:
            patterns[fname] = file_patterns

    return patterns


def resolve_scan_scope(project_root, scope_glob):
    """Resolve a scan scope glob pattern to absolute file paths.

    Args:
        project_root: absolute path to project root
        scope_glob: glob pattern like 'tools/**/*.{py,html,css,js}'

    Returns list of absolute file paths matching the glob.
    """
    # Expand brace patterns (glob doesn't support {a,b} natively)
    brace_match = re.search(r'\{([^}]+)\}', scope_glob)
    if brace_match:
        extensions = brace_match.group(1).split(',')
        base = scope_glob[:brace_match.start()]
        suffix = scope_glob[brace_match.end():]
        all_files = []
        for ext in extensions:
            pattern = os.path.join(project_root, base + ext.strip() + suffix)
            all_files.extend(glob_module.glob(pattern, recursive=True))
        return sorted(set(all_files))

    pattern = os.path.join(project_root, scope_glob)
    return sorted(glob_module.glob(pattern, recursive=True))


def get_feature_prerequisites(feature_content):
    """Extract anchor node prerequisite references from feature file content.

    Returns list of referenced anchor node filenames
    (e.g., ['arch_critic_policy.md', 'policy_critic.md']).
    """
    prereqs = []
    anchor_pattern = r'(?:arch_|design_|policy_)\w+\.md'
    for line in feature_content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('> Prerequisite:'):
            text = stripped[len('> Prerequisite:'):].strip()
            # Match anchor node filenames directly
            matches = re.findall(r'(' + anchor_pattern + r')', text)
            for m in matches:
                if m not in prereqs:
                    prereqs.append(m)
            # Also match features/<anchor>.md patterns
            matches = re.findall(r'features/(' + anchor_pattern + r')', text)
            for m in matches:
                if m not in prereqs:
                    prereqs.append(m)
    return prereqs


def discover_implementation_files(project_root, feature_stem, tools_root='tools'):
    """Find implementation files for a feature.

    Looks in tool directories that might correspond to the feature.
    Returns list of absolute file paths.
    """
    impl_files = []

    # Map feature stems to likely tool directories
    # e.g., 'critic_tool' -> 'critic', 'cdd_status_monitor' -> 'cdd'
    possible_dirs = set()
    possible_dirs.add(feature_stem)

    # Strip common suffixes
    for suffix in ('_tool', '_status_monitor', '_generator', '_sync',
                   '_bootstrap'):
        if feature_stem.endswith(suffix):
            possible_dirs.add(feature_stem[:len(feature_stem) - len(suffix)])

    tools_abs = os.path.join(project_root, tools_root)
    if not os.path.isdir(tools_abs):
        return impl_files

    for entry in os.listdir(tools_abs):
        tool_dir = os.path.join(tools_abs, entry)
        if not os.path.isdir(tool_dir):
            continue

        # Check if this tool dir matches the feature
        if entry in possible_dirs or feature_stem.startswith(entry):
            for fname in os.listdir(tool_dir):
                fpath = os.path.join(tool_dir, fname)
                if os.path.isfile(fpath) and not fname.startswith('.'):
                    impl_files.append(fpath)

    return impl_files


def scan_file_for_violations(filepath, patterns):
    """Scan a single file for FORBIDDEN pattern matches.

    Args:
        filepath: absolute path to the file to scan
        patterns: list of pattern strings

    Returns list of violations: [{"pattern": str, "file": str, "line": int, "text": str}]
    """
    violations = []

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except (IOError, OSError, UnicodeDecodeError):
        return violations

    for pattern_text in patterns:
        try:
            regex = re.compile(pattern_text)
        except re.error:
            # Treat as literal string match if not valid regex
            regex = re.compile(re.escape(pattern_text))

        for line_num, line in enumerate(lines, 1):
            if regex.search(line):
                violations.append({
                    'pattern': pattern_text,
                    'file': filepath,
                    'line': line_num,
                    'text': line.strip(),
                })

    return violations


def run_policy_check(feature_content, project_root, feature_stem,
                     features_dir=None, tools_root='tools'):
    """Run full policy adherence check for a feature.

    Args:
        feature_content: raw feature file text
        project_root: absolute path to project root
        feature_stem: feature file stem (e.g., 'critic_tool')
        features_dir: absolute path to features directory (default: project_root/features)
        tools_root: relative path to tools directory

    Returns:
        dict with 'status', 'violations', 'detail'
    """
    if features_dir is None:
        features_dir = os.path.join(project_root, 'features')

    # Find which policies this feature is anchored to
    prereqs = get_feature_prerequisites(feature_content)
    if not prereqs:
        return {
            'status': 'PASS',
            'violations': [],
            'detail': 'No policy prerequisites defined.',
        }

    # Get FORBIDDEN patterns from referenced policies
    all_patterns = discover_forbidden_patterns(features_dir)
    relevant_entries = []
    for prereq_file in prereqs:
        if prereq_file in all_patterns:
            relevant_entries.extend(all_patterns[prereq_file])

    if not relevant_entries:
        return {
            'status': 'PASS',
            'violations': [],
            'detail': 'No FORBIDDEN patterns in referenced policies.',
        }

    # Group patterns by scope for efficient scanning
    # Patterns with a scope use that scope; patterns without scope use
    # the feature's discovered implementation files.
    scoped_patterns = {}  # scope_glob -> [pattern_str]
    unscoped_patterns = []
    for entry in relevant_entries:
        if entry.get('scope'):
            scoped_patterns.setdefault(entry['scope'], []).append(
                entry['pattern'])
        else:
            unscoped_patterns.append(entry['pattern'])

    all_violations = []
    files_scanned = set()

    # Scan scoped patterns against their declared file scope
    for scope_glob, patterns in scoped_patterns.items():
        scope_files = resolve_scan_scope(project_root, scope_glob)
        for fpath in scope_files:
            files_scanned.add(fpath)
            violations = scan_file_for_violations(fpath, patterns)
            for v in violations:
                v['file'] = os.path.relpath(v['file'], project_root)
            all_violations.extend(violations)

    # Scan unscoped patterns against discovered implementation files
    if unscoped_patterns:
        impl_files = discover_implementation_files(
            project_root, feature_stem, tools_root
        )
        for fpath in impl_files:
            files_scanned.add(fpath)
            violations = scan_file_for_violations(fpath, unscoped_patterns)
            for v in violations:
                v['file'] = os.path.relpath(v['file'], project_root)
            all_violations.extend(violations)

    if not files_scanned:
        return {
            'status': 'PASS',
            'violations': [],
            'detail': 'No implementation files found to scan.',
        }

    if all_violations:
        detail = f'{len(all_violations)} FORBIDDEN violation(s) detected'
        return {
            'status': 'FAIL',
            'violations': all_violations,
            'detail': detail,
        }

    return {
        'status': 'PASS',
        'violations': [],
        'detail': f'Scanned {len(files_scanned)} file(s), no violations.',
    }
