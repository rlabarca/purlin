#!/usr/bin/env python3
"""Purlin proof emitter for C tests.

Reads JSON proof output from a C test runner (via stdin) and writes
feature-scoped proof JSON files next to the corresponding specs.

Usage:
    ./test_runner | python3 scripts/proof/c_purlin_emit.py
"""

import glob
import json
import os
import sys


def main():
    data = json.load(sys.stdin)
    proofs_raw = data.get("proofs", [])
    if not proofs_raw:
        return

    # Build feature -> spec directory mapping
    spec_dirs = {}
    for spec in glob.glob("specs/**/*.md", recursive=True):
        stem = os.path.splitext(os.path.basename(spec))[0]
        spec_dirs[stem] = os.path.dirname(spec)

    # Group by (feature, tier)
    grouped = {}
    for entry in proofs_raw:
        key = (entry["feature"], entry.get("tier", "unit"))
        grouped.setdefault(key, []).append(entry)

    # Write proof files (feature-scoped overwrite)
    for (feature, tier), new_entries in grouped.items():
        spec_dir = spec_dirs.get(feature)
        if spec_dir is None:
            print(
                f'WARNING: No spec found for feature "{feature}" — writing proofs '
                f"to specs/{feature}.proofs-{tier}.json. Create a spec with: "
                f"purlin:spec {feature}",
                file=sys.stderr,
            )
            spec_dir = "specs"
        path = os.path.join(spec_dir, f"{feature}.proofs-{tier}.json")

        existing = []
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f).get("proofs", [])

        kept = [e for e in existing if e.get("feature") != feature]

        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump({"tier": tier, "proofs": kept + new_entries}, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)


if __name__ == "__main__":
    main()
