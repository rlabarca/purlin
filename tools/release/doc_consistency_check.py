#!/usr/bin/env python3
"""Release audit: documentation consistency check.

Checks README.md for stale references to deleted files, missing feature
coverage, and references to tombstoned features.
See features/release_audit_automation.md Section 2.7.
Also folds in framework doc consistency checks (Section 2.10).
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


def extract_file_references(content):
    """Extract file path references from markdown content."""
    refs = set()
    # Match backtick-quoted paths
    for match in re.finditer(r'`([^`]*(?:\.(?:py|sh|md|json|css|html|js|mmd))[^`]*)`', content):
        refs.add(match.group(1))
    # Match paths in prose (tools/something, features/something, etc.)
    for match in re.finditer(r'(?:^|\s)((?:tools|features|\.purlin|tests|instructions)/[^\s,;)]+)', content):
        path = match.group(1).rstrip('.')
        refs.add(path)
    return refs


def check_stale_references(readme_path, project_root):
    """Check for file path references in README that don't exist on disk."""
    findings = []
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, OSError):
        return findings

    refs = extract_file_references(content)
    for ref in sorted(refs):
        full_path = os.path.join(project_root, ref)
        if not os.path.exists(full_path):
            # Check if it's a directory reference
            if not os.path.isdir(full_path.rstrip('/')):
                findings.append(make_finding(
                    "WARNING", "stale_reference",
                    "README.md",
                    f"References '{ref}' which does not exist",
                ))
    return findings


def check_feature_coverage(readme_path, features_dir):
    """Check which features are not mentioned in README."""
    findings = []
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except (IOError, OSError):
        return findings

    if not os.path.isdir(features_dir):
        return findings

    for fname in sorted(os.listdir(features_dir)):
        if not fname.endswith('.md') or fname.endswith('.impl.md') or fname.endswith('.discoveries.md'):
            continue
        # Skip anchor nodes (they're internal)
        if fname.startswith(('arch_', 'design_', 'policy_')):
            continue
        stem = fname.replace('.md', '')
        if stem not in readme_content and fname not in readme_content:
            findings.append(make_finding(
                "INFO", "coverage_gap",
                f"features/{fname}",
                f"Feature not mentioned in README.md",
            ))
    return findings


# Base instruction files for framework doc consistency checks
BASE_INSTRUCTION_FILES = [
    "instructions/HOW_WE_WORK_BASE.md",
    "instructions/ARCHITECT_BASE.md",
    "instructions/BUILDER_BASE.md",
    "instructions/QA_BASE.md",
    "features/policy_critic.md",
]

# Terminology groups: each tuple is (canonical_term, [deprecated_variants], context_pattern)
# context_pattern is optional regex that must also match the line for the finding to trigger
# (prevents false positives on unrelated uses of common words)
TERMINOLOGY_GROUPS = [
    # Section heading migration
    ("Unit Tests", ["Automated Scenarios"], r'###'),
    ("QA Scenarios", ["Manual Scenarios"], r'###'),
    # Role names -- only flag when used as a role designation, not in prose
    ("QA", ["Quality Assurance"], r'(?:role|agent|owned|only|verify)'),
    ("PM", ["Product Manager", "Project Manager"], r'(?:role|agent|owned|only)'),
    # Lifecycle status labels
    ("[Complete]", ["[COMPLETE]", "[DONE]"], None),
    ("[TODO]", ["[Todo]", "[todo]"], None),
    ("[TESTING]", ["[Testing]", "[IN_PROGRESS]", "[IN PROGRESS]"], None),
    # Discovery lifecycle
    ("SPEC_UPDATED", ["SPEC UPDATED", "spec_updated"], None),
]


def check_terminology_consistency(project_root):
    """Check base instruction files for deprecated terminology variants.

    Scans all 5 base instruction files for known deprecated term variants
    and flags mismatches. Each finding identifies the file, the deprecated
    term found, and the canonical replacement.
    """
    findings = []

    for rel_path in BASE_INSTRUCTION_FILES:
        full_path = os.path.join(project_root, rel_path)
        if not os.path.exists(full_path):
            continue
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (IOError, OSError):
            continue

        for line_no, line in enumerate(lines, 1):
            for canonical, variants, context_pat in TERMINOLOGY_GROUPS:
                if context_pat and not re.search(context_pat, line):
                    continue
                for variant in variants:
                    if variant in line:
                        findings.append(make_finding(
                            "WARNING", "terminology_mismatch",
                            rel_path,
                            f"Line {line_no}: uses '{variant}' "
                            f"(canonical: '{canonical}')",
                            line=line_no,
                        ))

    return findings


def _extract_role_focus_phrases(content):
    """Extract role -> focus phrase mappings from instruction file content.

    Looks for patterns like: **Focus:** "The What and The Why".
    Returns dict mapping role name to focus phrase.
    """
    roles = {}
    current_role = None
    for line in content.splitlines():
        # Detect role headings like "### The Architect Agent"
        role_match = re.match(r'###\s+The\s+(\w+)\s+Agent', line)
        if role_match:
            current_role = role_match.group(1)
            continue
        # Also detect "### The Human Executive"
        exec_match = re.match(r'###\s+The\s+Human\s+Executive', line)
        if exec_match:
            current_role = "Human Executive"
            continue
        # Extract focus phrase
        if current_role:
            focus_match = re.search(r'\*\*Focus:\*\*\s*"([^"]+)"', line)
            if focus_match:
                roles[current_role] = focus_match.group(1)
                current_role = None
    return roles


def check_readme_instruction_consistency(readme_path, project_root):
    """Check README against instruction files for content drift.

    Verifies that README accurately describes instruction-file-governed
    behavior: role definitions, focus phrases, and critic architecture.
    """
    findings = []
    hww_path = os.path.join(project_root, "instructions", "HOW_WE_WORK_BASE.md")

    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except (IOError, OSError):
        return findings

    if not os.path.exists(hww_path):
        return findings

    try:
        with open(hww_path, 'r', encoding='utf-8') as f:
            hww_content = f.read()
    except (IOError, OSError):
        return findings

    # Check 1: Role focus phrases from HOW_WE_WORK_BASE appear in README
    role_phrases = _extract_role_focus_phrases(hww_content)
    for role, phrase in role_phrases.items():
        if role == "Human Executive":
            continue  # Human Executive may not appear in README
        if phrase not in readme_content:
            findings.append(make_finding(
                "WARNING", "readme_instruction_drift",
                "README.md",
                f"{role} focus phrase '{phrase}' from "
                f"HOW_WE_WORK_BASE.md not found in README",
            ))

    # Check 2: Every agent role in HOW_WE_WORK_BASE has a README section
    for role in role_phrases:
        if role == "Human Executive":
            continue
        # Look for a heading or bold reference like "### The Builder" or
        # "**The Builder:**"
        pattern = re.compile(
            r'(?:###\s+The\s+' + re.escape(role) + r'|'
            r'\*\*The\s+' + re.escape(role) + r')'
        )
        if not pattern.search(readme_content):
            findings.append(make_finding(
                "WARNING", "readme_instruction_drift",
                "README.md",
                f"Role '{role}' defined in HOW_WE_WORK_BASE.md "
                f"has no section in README",
            ))

    # Check 3: Critic dual-gate architecture consistency
    hww_has_dual_gate = (
        "Spec Gate" in hww_content and "Implementation Gate" in hww_content
    )
    readme_has_dual_gate = (
        "Dual-Gate" in readme_content or "dual-gate" in readme_content
        or ("Before coding" in readme_content
            and "After coding" in readme_content)
    )
    if hww_has_dual_gate and not readme_has_dual_gate:
        findings.append(make_finding(
            "WARNING", "readme_instruction_drift",
            "README.md",
            "HOW_WE_WORK_BASE.md defines Spec Gate / Implementation Gate "
            "dual-gate model but README does not describe it",
        ))

    return findings


def check_tombstone_references(readme_path, tombstones_dir, project_root):
    """Check for references to tombstoned features in README."""
    findings = []
    if not os.path.isdir(tombstones_dir):
        return findings

    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except (IOError, OSError):
        return findings

    for fname in os.listdir(tombstones_dir):
        if not fname.endswith('.md'):
            continue
        stem = fname.replace('.md', '')
        if stem in readme_content:
            findings.append(make_finding(
                "WARNING", "tombstone_reference",
                "README.md",
                f"References tombstoned feature '{stem}'",
            ))
    return findings


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    readme_path = os.path.join(project_root, "README.md")
    features_dir = os.path.join(project_root, "features")
    tombstones_dir = os.path.join(project_root, "features", "tombstones")
    findings = []

    if not os.path.exists(readme_path):
        result = make_output(
            "doc_consistency_check", [],
            summary="No README.md found; skipping documentation checks",
        )
        return result

    findings.extend(check_stale_references(readme_path, project_root))
    findings.extend(check_feature_coverage(readme_path, features_dir))
    findings.extend(check_tombstone_references(readme_path, tombstones_dir, project_root))
    findings.extend(check_terminology_consistency(project_root))
    findings.extend(check_readme_instruction_consistency(readme_path, project_root))

    result = make_output("doc_consistency_check", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
