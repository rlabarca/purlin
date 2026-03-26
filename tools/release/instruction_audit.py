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
    "PURLIN_OVERRIDES.md",
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


def _parse_sections(content):
    """Parse markdown content into section-indexed structure.

    Returns a list of dicts with keys:
        - heading: the section heading text (or '' for top-level)
        - level: heading depth (1 for #, 2 for ##, etc; 0 for top-level)
        - lines: list of (line_number, text) tuples in that section
        - rules: list of (line_number, text) tuples for lines containing
          imperative keywords (MUST, NEVER, ALWAYS, etc.)
    """
    sections = []
    current = {"heading": "", "level": 0, "lines": [], "rules": []}
    rule_pattern = re.compile(
        r'\b(?:MUST|NEVER|ALWAYS|FORBIDDEN|REQUIRED|SHALL|'
        r'Do NOT|MUST NOT|prohibited|required)\b'
    )

    for i, line in enumerate(content.split('\n'), 1):
        heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if heading_match:
            if current["lines"] or current["rules"]:
                sections.append(current)
            current = {
                "heading": heading_match.group(2).strip(),
                "level": len(heading_match.group(1)),
                "lines": [],
                "rules": [],
            }
        else:
            stripped = line.strip()
            if stripped:
                current["lines"].append((i, stripped))
                if rule_pattern.search(stripped):
                    current["rules"].append((i, stripped))

    if current["lines"] or current["rules"]:
        sections.append(current)
    return sections


def _heading_similarity(h1, h2):
    """Compute word-level similarity between two heading strings.

    Returns a float between 0.0 and 1.0.
    """
    words1 = set(re.findall(r'\b\w{3,}\b', h1.lower()))
    words2 = set(re.findall(r'\b\w{3,}\b', h2.lower()))
    if not words1 or not words2:
        return 0.0
    return len(words1 & words2) / min(len(words1), len(words2))


def _check_structural_contradictions(override_sections, base_sections,
                                     ofname, bfname):
    """Detect contradictions using structural section-level analysis.

    Matches override sections to base sections by heading similarity,
    then compares imperative rules within matched sections for negation
    patterns. This catches contradictions that keyword-only matching
    might miss when context words differ but the section scope is the same.
    """
    findings = []
    for osec in override_sections:
        # Find structurally matching base sections (same heading topic)
        matched_base = []
        for bsec in base_sections:
            if osec["heading"] and bsec["heading"]:
                sim = _heading_similarity(osec["heading"], bsec["heading"])
                if sim >= 0.5:
                    matched_base.append(bsec)
            elif osec["level"] == bsec["level"] == 0:
                # Both top-level; compare
                matched_base.append(bsec)

        if not matched_base:
            continue

        for oline_no, oline_text in osec["rules"]:
            for neg_pattern, base_pattern in NEGATION_PATTERNS:
                if not re.search(neg_pattern, oline_text):
                    continue
                for bsec in matched_base:
                    for bline_no, bline_text in bsec["rules"]:
                        if not re.search(base_pattern, bline_text):
                            continue
                        # Structural match: same section topic + opposing
                        # imperatives. Even 1 shared context word suffices
                        # since section scope already narrows the match.
                        o_words = set(
                            re.findall(r'\b\w{4,}\b', oline_text.lower()))
                        b_words = set(
                            re.findall(r'\b\w{4,}\b', bline_text.lower()))
                        overlap = o_words & b_words
                        if len(overlap) >= 1:
                            findings.append(make_finding(
                                "CRITICAL", "contradiction",
                                f".purlin/{ofname}",
                                f"Line {oline_no} structurally contradicts "
                                f"'{bfname}' section "
                                f"'{bsec['heading'][:40]}': override says "
                                f"'{oline_text[:80]}' vs base "
                                f"'{bline_text[:80]}'",
                                line=oline_no,
                            ))
                            break
    return findings


def check_contradictions(purlin_dir, instructions_dir):
    """Check for contradictions between override and base files.

    Uses both keyword heuristic matching (original) and structural
    section-level analysis (M42 fix) for comprehensive detection.
    """
    findings = []

    # Load base instruction files and their parsed sections
    base_files = {}
    base_sections = {}
    if os.path.isdir(instructions_dir):
        for fname in os.listdir(instructions_dir):
            if fname.endswith('.md'):
                path = os.path.join(instructions_dir, fname)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    base_files[fname] = content
                    base_sections[fname] = _parse_sections(content)
                except (IOError, OSError):
                    pass

    # Track already-reported contradiction pairs to avoid duplicates
    reported = set()

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

        override_sections_parsed = _parse_sections(override_content)

        # --- Heuristic keyword matching (original approach) ---
        override_lines = override_content.split('\n')
        for i, line in enumerate(override_lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue

            for neg_pattern, base_pattern in NEGATION_PATTERNS:
                if not re.search(neg_pattern, line_stripped):
                    continue
                line_words = set(re.findall(r'\b\w{4,}\b', line_stripped.lower()))
                for bfname, bcontent in base_files.items():
                    for bline in bcontent.split('\n'):
                        if not re.search(base_pattern, bline):
                            continue
                        bline_words = set(re.findall(r'\b\w{4,}\b', bline.strip().lower()))
                        overlap = line_words & bline_words
                        # Require at least 2 context words in common
                        if len(overlap) >= 2:
                            key = (ofname, i, bfname)
                            if key not in reported:
                                reported.add(key)
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

        # --- Structural section-level analysis (M42 fix) ---
        for bfname, bsecs in base_sections.items():
            structural = _check_structural_contradictions(
                override_sections_parsed, bsecs, ofname, bfname,
            )
            for finding in structural:
                key = (ofname, finding.get("line"), bfname)
                if key not in reported:
                    reported.add(key)
                    findings.append(finding)

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
