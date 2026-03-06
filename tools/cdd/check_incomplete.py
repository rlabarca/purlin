#!/usr/bin/env python3
"""Lists features where any role column is not in its 'done' state.

Reads /status.json from stdin. Outputs one line per incomplete feature:
  features/foo.md: arch=DONE build=TODO qa=CLEAN

Usage: tools/cdd/status.sh | python3 tools/cdd/check_incomplete.py
"""
import json
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print("Error: could not parse JSON from stdin", file=sys.stderr)
        sys.exit(1)

    features = data.get("features", [])
    incomplete = []
    for f in features:
        a = f.get("architect", "?")
        b = f.get("builder", "?")
        q = f.get("qa", "?")
        if a != "DONE" or b != "DONE" or q not in ("CLEAN", "N/A"):
            incomplete.append(f"{f.get('file', '?')}: arch={a} build={b} qa={q}")

    if incomplete:
        for line in incomplete:
            print(line)
    else:
        print("All features complete.")


if __name__ == "__main__":
    main()
