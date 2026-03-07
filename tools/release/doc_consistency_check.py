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
        if not fname.endswith('.md') or fname.endswith('.impl.md'):
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

    result = make_output("doc_consistency_check", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
