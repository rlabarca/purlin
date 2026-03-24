#!/usr/bin/env python3
"""Release audit: Critic terminology and routing rule consistency.

Checks for deprecated terminology, routing rule consistency between
policy_critic.md and HOW_WE_WORK_BASE.md, and README Critic section accuracy.
See features/release_audit_automation.md Section 2.9.
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

# Deprecated terms and their replacements
DEPRECATED_TERMS = {
    "quality gate": "coordination engine",
}


def find_critic_related_files(project_root):
    """Find files related to Critic functionality."""
    files = []
    # Instruction files
    instructions_dir = os.path.join(project_root, "instructions")
    if os.path.isdir(instructions_dir):
        for fname in os.listdir(instructions_dir):
            if fname.endswith('.md'):
                files.append(os.path.join(instructions_dir, fname))

    # Policy files
    features_dir = os.path.join(project_root, "features")
    if os.path.isdir(features_dir):
        for fname in os.listdir(features_dir):
            if fname.endswith('.md') and ('critic' in fname.lower() or 'policy' in fname.lower()):
                files.append(os.path.join(features_dir, fname))

    # Override files
    purlin_dir = os.path.join(project_root, ".purlin")
    if os.path.isdir(purlin_dir):
        for fname in os.listdir(purlin_dir):
            if fname.endswith('.md'):
                files.append(os.path.join(purlin_dir, fname))

    # README
    readme = os.path.join(project_root, "README.md")
    if os.path.exists(readme):
        files.append(readme)

    return files


def check_deprecated_terms(project_root):
    """Scan Critic-related files for deprecated terminology."""
    findings = []
    files = find_critic_related_files(project_root)

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        rel = os.path.relpath(filepath, project_root)
        lines = content.split('\n')

        for deprecated, replacement in DEPRECATED_TERMS.items():
            for i, line in enumerate(lines, 1):
                # Case-insensitive match, skip lines that already have the replacement
                if re.search(re.escape(deprecated), line, re.IGNORECASE):
                    # Don't flag lines that mention the term in a correction context
                    if replacement.lower() in line.lower():
                        continue
                    findings.append(make_finding(
                        "CRITICAL", "deprecated_term",
                        rel,
                        f"Uses deprecated term '{deprecated}' "
                        f"(should be '{replacement}') on line {i}",
                        line=i,
                    ))
    return findings


def check_routing_consistency(project_root):
    """Cross-reference routing rules between policy and instruction files."""
    findings = []

    policy_path = os.path.join(project_root, "features", "policy_critic.md")
    hww_path = os.path.join(project_root, "instructions", "HOW_WE_WORK_BASE.md")

    if not os.path.exists(policy_path) or not os.path.exists(hww_path):
        return findings

    try:
        with open(policy_path, 'r', encoding='utf-8') as f:
            policy_content = f.read()
        with open(hww_path, 'r', encoding='utf-8') as f:
            hww_content = f.read()
    except (IOError, OSError):
        return findings

    # Check routing rules: BUG -> Builder, DISCOVERY -> Architect, etc.
    routing_rules = {
        "BUG": "Builder",
        "DISCOVERY": "Architect",
        "INTENT_DRIFT": "Architect",
        "SPEC_DISPUTE": "Architect",
    }

    for discovery_type, expected_role in routing_rules.items():
        # Check in policy
        policy_pattern = re.compile(
            rf'{discovery_type}.*?{expected_role}', re.IGNORECASE | re.DOTALL
        )
        hww_pattern = re.compile(
            rf'{discovery_type}.*?{expected_role}', re.IGNORECASE | re.DOTALL
        )

        in_policy = bool(policy_pattern.search(policy_content))
        in_hww = bool(hww_pattern.search(hww_content))

        if in_policy != in_hww:
            findings.append(make_finding(
                "CRITICAL", "routing_inconsistency",
                "features/policy_critic.md",
                f"Routing rule for {discovery_type} -> {expected_role} "
                f"{'found' if in_policy else 'missing'} in policy but "
                f"{'found' if in_hww else 'missing'} in HOW_WE_WORK_BASE.md",
            ))

    return findings


def check_readme_critic_section(project_root):
    """Phase 2: Verify README.md contains the required '## The Critic' section.

    Per spec Section 2.3, after a clean Phase 1, the README must have a
    '## The Critic' section placed after '## The Agents' and before
    '## Setup & Configuration'.
    """
    findings = []
    readme_path = os.path.join(project_root, "README.md")

    if not os.path.exists(readme_path):
        findings.append(make_finding(
            "CRITICAL", "readme_missing",
            "README.md",
            "README.md not found -- Phase 2 cannot verify Critic section",
        ))
        return findings

    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, OSError):
        findings.append(make_finding(
            "CRITICAL", "readme_unreadable",
            "README.md",
            "README.md could not be read -- Phase 2 cannot verify Critic section",
        ))
        return findings

    # Check for the required section heading
    if not re.search(r'^## The Critic\b', content, re.MULTILINE):
        findings.append(make_finding(
            "CRITICAL", "readme_missing_critic_section",
            "README.md",
            "README.md is missing the required '## The Critic' section "
            "(must be placed after '## The Agents' and before "
            "'## Setup & Configuration')",
        ))
        return findings

    # If section exists, verify ordering: Agents -> Critic -> Setup
    headings = re.findall(r'^(## .+)$', content, re.MULTILINE)
    heading_names = [h.strip() for h in headings]

    agents_idx = None
    critic_idx = None
    setup_idx = None

    for i, h in enumerate(heading_names):
        if h.startswith("## The Agents"):
            agents_idx = i
        elif h.startswith("## The Critic"):
            critic_idx = i
        elif h.startswith("## Setup & Configuration") or h.startswith("## Setup &"):
            setup_idx = i

    if agents_idx is not None and critic_idx is not None and critic_idx <= agents_idx:
        findings.append(make_finding(
            "WARNING", "readme_critic_ordering",
            "README.md",
            "'## The Critic' section should appear after '## The Agents'",
        ))

    if setup_idx is not None and critic_idx is not None and critic_idx >= setup_idx:
        findings.append(make_finding(
            "WARNING", "readme_critic_ordering",
            "README.md",
            "'## The Critic' section should appear before "
            "'## Setup & Configuration'",
        ))

    return findings


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    findings = []

    # Phase 1: Audit checks
    findings.extend(check_deprecated_terms(project_root))
    findings.extend(check_routing_consistency(project_root))

    # Phase 2: README Critic section check (only if Phase 1 has no CRITICAL)
    has_critical = any(f["severity"] == "CRITICAL" for f in findings)
    if not has_critical:
        findings.extend(check_readme_critic_section(project_root))

    result = make_output("critic_consistency_check", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
