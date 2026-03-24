#!/usr/bin/env python3
"""Release audit: verify dependency integrity.

Checks: cycle detection, broken prerequisite links, reverse reference audit.
Reuses tools/cdd/graph.py for graph construction.
See features/release_audit_automation.md Section 2.4.
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Add parent paths so we can import graph.py and audit_common
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import (
    detect_project_root, make_finding, make_output, output_and_exit,
)
from tools.cdd.graph import parse_features, detect_cycles, run_full_generation


def ensure_cache_fresh(project_root, features_dir):
    """Check if dependency_graph.json is stale or absent; regenerate if needed.

    Per spec Section 2.1: if the cache file is absent or its modification time
    predates the most recently modified feature file, regenerate it before
    proceeding.

    Returns True if the cache was regenerated, False if it was already fresh.
    """
    cache_file = os.path.join(project_root, ".purlin", "cache",
                              "dependency_graph.json")

    # If cache file does not exist, regenerate
    if not os.path.exists(cache_file):
        run_full_generation(features_dir)
        return True

    cache_mtime = os.path.getmtime(cache_file)

    # Find the most recently modified feature file
    latest_feature_mtime = 0
    if os.path.isdir(features_dir):
        for filename in os.listdir(features_dir):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(features_dir, filename)
            if os.path.isfile(filepath):
                mtime = os.path.getmtime(filepath)
                if mtime > latest_feature_mtime:
                    latest_feature_mtime = mtime

    # If any feature file is newer than the cache, regenerate
    if latest_feature_mtime > cache_mtime:
        run_full_generation(features_dir)
        return True

    return False


def check_broken_links(features, features_dir):
    """Check that all prerequisite links resolve to existing feature files."""
    findings = []
    for node_id, data in sorted(features.items()):
        for prereq_id in data["prerequisites"]:
            # Check if the prerequisite exists as a parsed feature
            if prereq_id not in features:
                prereq_file = prereq_id.replace("_", ".") + ".md"
                # Also try underscore-only version
                if not os.path.exists(os.path.join(features_dir, prereq_file)):
                    prereq_file = prereq_id + ".md"
                findings.append(make_finding(
                    "CRITICAL", "broken_link",
                    os.path.join("features", data["filename"]),
                    f"Prerequisite '{prereq_file}' does not exist",
                ))
    return findings


def check_reverse_references(features, features_dir):
    """Check for parent features that reference child filenames in body text."""
    findings = []
    # Build parent -> children map (parent is the prerequisite, children depend on it)
    parent_to_children = {}
    for node_id, data in features.items():
        for prereq_id in data["prerequisites"]:
            if prereq_id in features:
                parent_to_children.setdefault(prereq_id, []).append(node_id)

    # For each parent, check if its body references any child filename
    for parent_id, child_ids in parent_to_children.items():
        parent_data = features[parent_id]
        parent_path = os.path.join(features_dir, parent_data["filename"])
        try:
            with open(parent_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError):
            continue

        # Skip prerequisite lines themselves
        lines = content.split('\n')
        body_lines = [
            l for l in lines
            if not l.strip().startswith('> Prerequisite:')
        ]
        body_text = '\n'.join(body_lines)

        for child_id in child_ids:
            child_filename = features[child_id]["filename"]
            if child_filename in body_text:
                findings.append(make_finding(
                    "CRITICAL", "reverse_reference",
                    os.path.join("features", parent_data["filename"]),
                    f"Parent references child '{child_filename}' in body text "
                    f"(structural reversal)",
                ))
    return findings


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    features_dir = os.path.join(project_root, "features")

    # Spec Section 2.1: check staleness of dependency_graph.json before use
    ensure_cache_fresh(project_root, features_dir)

    features = parse_features(features_dir)
    findings = []

    # 1. Cycle detection
    cycles = detect_cycles(features)
    for cycle_path in cycles:
        findings.append(make_finding(
            "CRITICAL", "cycle",
            "features/",
            f"Dependency cycle detected: {cycle_path}",
        ))

    # 2. Broken links
    findings.extend(check_broken_links(features, features_dir))

    # 3. Reverse reference audit
    findings.extend(check_reverse_references(features, features_dir))

    result = make_output("verify_dependency_integrity", findings)
    return result


if __name__ == "__main__":
    output_and_exit(main())
