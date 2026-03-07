#!/usr/bin/env python3
"""Release audit: instruction file consistency checks.

Checks override presence, contradiction scan, stale path references,
and terminology consistency.
See features/release_audit_automation.md Section 2.8.
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import (
    detect_project_root, make_finding, make_output, output_and_exit,
)

EXPECTED_OVERRIDES = [
    "HOW_WE_WORK_OVERRIDES.md",
    "ARCHITECT_OVERRIDES.md",
    "BUILDER_OVERRIDES.md",
    "QA_OVERRIDES.md",
]

# Contradiction detection: override keywords that negate base rules
NEGATION_PATTERNS = [
    (r'\bNEVER\b', r'\bALWAYS\b'),
    (r'\bALWAYS\b', r'\bNEVER\b'),
    (r'\bMUST NOT\b', r'\bMUST\b'),
    (r'\bMUST\b', r'\bMUST NOT\b'),
    (r'\bFORBIDDEN\b', r'\bREQUIRED\b'),
    (r'\bDo NOT\b', r'\bMUST\b'),
    (r'\bprohibited\b', r'\brequired\b'),
]


def check_override_presence(purlin_dir):
    """Verify all 4 override files exist."""
    findings = []
    for fname in EXPECTED_OVERRIDES:
        path = os.path.join(purlin_dir, fname)
        if not os.path.exists(path):
            findings.append(make_finding(
                "WARNING", "missing_override",
                f".purlin/{fname}",
                f"Expected override file '{fname}' not found",
            ))
    return findings


def check_stale_paths(purlin_dir, project_root):
    """Scan override files for file path references that don't resolve."""
    findings = []
    for fname in EXPECTED_OVERRIDES:
        path = os.path.join(purlin_dir, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        # Extract backtick-quoted paths
        for match in re.finditer(r'`([^`]*(?:\.(?:py|sh|md|json|css|html|js))[^`]*)`', content):
            ref = match.group(1)
            full = os.path.join(project_root, ref)
            if not os.path.exists(full):
                findings.append(make_finding(
                    "WARNING", "stale_path",
                    f".purlin/{fname}",
                    f"References '{ref}' which does not exist",
                ))
    return findings


def check_contradictions(purlin_dir, instructions_dir):
    """Check for direct negation patterns between override and base files."""
    findings = []

    # Load base instruction files
    base_files = {}
    if os.path.isdir(instructions_dir):
        for fname in os.listdir(instructions_dir):
            if fname.endswith('.md'):
                path = os.path.join(instructions_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        base_files[fname] = f.read()
                except (IOError, OSError):
                    pass

    # For each override, check for contradictions with base files
    for ofname in EXPECTED_OVERRIDES:
        opath = os.path.join(purlin_dir, ofname)
        if not os.path.exists(opath):
            continue
        try:
            with open(opath, 'r', encoding='utf-8') as f:
                override_content = f.read()
        except (IOError, OSError):
            continue

        override_lines = override_content.split('\n')
        for i, line in enumerate(override_lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue

            for neg_pattern, base_pattern in NEGATION_PATTERNS:
                if not re.search(neg_pattern, line_stripped):
                    continue
                # Check if base files have the opposing pattern
                # with similar context words
                line_words = set(re.findall(r'\b\w{4,}\b', line_stripped.lower()))
                for bfname, bcontent in base_files.items():
                    for bline in bcontent.split('\n'):
                        if not re.search(base_pattern, bline):
                            continue
                        bline_words = set(re.findall(r'\b\w{4,}\b', bline.strip().lower()))
                        overlap = line_words & bline_words
                        # Require at least 2 context words in common
                        if len(overlap) >= 2:
                            findings.append(make_finding(
                                "CRITICAL", "contradiction",
                                f".purlin/{ofname}",
                                f"Line {i} may contradict "
                                f"'{bfname}': override says "
                                f"'{line_stripped[:80]}' vs base "
                                f"'{bline.strip()[:80]}'",
                                line=i,
                            ))
                            break
    return findings


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    purlin_dir = os.path.join(project_root, ".purlin")
    instructions_dir = os.path.join(project_root, "instructions")
    findings = []

    findings.extend(check_override_presence(purlin_dir))
    findings.extend(check_stale_paths(purlin_dir, project_root))
    findings.extend(check_contradictions(purlin_dir, instructions_dir))

    result = make_output("instruction_audit", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
