#!/usr/bin/env python3
import os
import re
import sys

"""
cleanup_orphaned_features.py
Identifies and optionally moves .md files in feature directories
that are not part of the dependency tree to a .trash folder.
"""

# Project root detection (Section 2.11, 2.14)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    # Climbing fallback: try FURTHER path first (submodule), then nearer (standalone)
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../'))
    for depth in ('../../', '../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break


def get_referenced_features(features_dir):
    if not os.path.exists(features_dir):
        return set()
    all_files = {f for f in os.listdir(features_dir) if f.endswith(".md") and not f.endswith(".impl.md")}
    is_prerequisite = set()

    for filename in all_files:
        path = os.path.join(features_dir, filename)
        with open(path, 'r') as f:
            content = f.read()
            # Find lines like: > Prerequisite: path/to/target.md
            # We match the filename regardless of the path prefix
            matches = re.findall(r'> Prerequisite:.*?/([a-zA-Z0-9_\-\.]+)', content)
            for m in matches:
                is_prerequisite.add(m)

    # Root nodes we want to keep even if nothing points to them:
    # - arch_*.md (Policies)
    # - RELEASE_*.md (Releases)
    protected_roots = {f for f in all_files if f.startswith("arch_") or f.startswith("RELEASE_")}

    orphans = all_files - is_prerequisite - protected_roots

    # Also detect orphaned companion files
    impl_files = {f for f in os.listdir(features_dir) if f.endswith(".impl.md")}
    for impl_file in impl_files:
        parent = impl_file.replace(".impl.md", ".md")
        if parent not in all_files or parent in orphans:
            orphans.add(impl_file)

    return orphans

def main():
    # Resolve features/ relative to detected project root (Section 2.14)
    features_dir = os.path.join(PROJECT_ROOT, "features")

    orphans = get_referenced_features(features_dir)

    if not orphans:
        print("No orphaned feature files found.")
        return

    print(f"Orphaned files in '{features_dir}':")
    for o in sorted(orphans):
        print(f"  - {o}")

    if "--fix" in sys.argv:
        trash_dir = os.path.join(features_dir, ".trash")
        if not os.path.exists(trash_dir):
            os.makedirs(trash_dir)
        for o in orphans:
            os.rename(os.path.join(features_dir, o), os.path.join(trash_dir, o))
        print(f"Moved {len(orphans)} files to {trash_dir}.")
    else:
        print("\nRun with '--fix' to move these to .trash for review.")

if __name__ == "__main__":
    main()
