#!/usr/bin/env python3
import os
import re
import sys

"""
cleanup_orphaned_features.py
Identifies and optionally moves .md files in feature directories 
that are not part of the dependency tree to a .trash folder.
"""

def get_referenced_features(features_dir):
    if not os.path.exists(features_dir):
        return set()
    all_files = {f for f in os.listdir(features_dir) if f.endswith(".md")}
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
    
    return orphans

def main():
    # Check current directory features and framework features
    dirs_to_check = ["features"]
    
    all_orphans = {}
    
    for d in dirs_to_check:
        orphans = get_referenced_features(d)
        if orphans:
            all_orphans[d] = orphans

    if not all_orphans:
        print("No orphaned feature files found.")
        return

    for d, orphans in all_orphans.items():
        print(f"Orphaned files in '{d}':")
        for o in sorted(orphans):
            print(f"  - {o}")

    if "--fix" in sys.argv:
        for d, orphans in all_orphans.items():
            trash_dir = os.path.join(d, ".trash")
            if not os.path.exists(trash_dir):
                os.makedirs(trash_dir)
            for o in orphans:
                os.rename(os.path.join(d, o), os.path.join(trash_dir, o))
            print(f"Moved {len(orphans)} files in '{d}' to {trash_dir}.")
    else:
        print("
Run with '--fix' to move these to .trash for review.")

if __name__ == "__main__":
    main()
