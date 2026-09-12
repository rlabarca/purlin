#!/usr/bin/env python3
"""Purlin proof emitter for C tests.

Reads JSON proof output from a C test runner (via stdin) and writes
write-scoped proof JSON files next to the corresponding specs.

Usage:
    ./test_runner | python3 scripts/proof/c_purlin_emit.py

An entry the header recorded with `purlin_proof_on(..., "a,b")` carries a
non-empty `platforms` string. Such an entry is written to
`<feature>.proofs-<tier>@<host>.json`, where `<host>` is `PURLIN_PLATFORM`
when set and otherwise the detected OS family (`windows`, `macos`, `linux`),
with an eighth field `platform` equal to `<host>`. An entry with no platforms
declared goes to the agnostic `<feature>.proofs-<tier>.json` with the seven
standard fields, whatever `PURLIN_PLATFORM` says. The emitter never evaluates
version constraints.
"""

import glob
import json
import os
import platform
import sys

_FAMILIES = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}


def _host_platform():
    """PURLIN_PLATFORM when set, else the OS family. The only host lookup here."""
    env = os.environ.get("PURLIN_PLATFORM", "").strip()
    if env:
        return env
    system = platform.system()
    return _FAMILIES.get(system, system.lower())


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

    # Group by (feature, tier, platform); platform is None for an agnostic entry.
    grouped = {}
    for raw in proofs_raw:
        tier = raw.get("tier") or "unit"
        declared = [p.strip() for p in (raw.get("platforms") or "").split(",") if p.strip()]
        plat = _host_platform() if declared else None
        entry = {
            "feature": raw["feature"],
            "id": raw["id"],
            "rule": raw["rule"],
            # Forward slashes on every OS (proof_common RULE-15).
            "test_file": (raw.get("test_file") or "").replace(os.sep, "/").replace("\\", "/"),
            "test_name": raw.get("test_name", ""),
            "status": raw.get("status", "fail"),
            "tier": tier,
        }
        if plat is not None:
            entry["platform"] = plat
        grouped.setdefault((raw["feature"], tier, plat), []).append(entry)

    # Write proof files (write-scoped overwrite)
    for (feature, tier, plat), new_entries in grouped.items():
        suffix = f"{tier}@{plat}" if plat is not None else tier
        spec_dir = spec_dirs.get(feature)
        if spec_dir is None:
            print(
                f'WARNING: No spec found for feature "{feature}" — writing proofs '
                f"to specs/{feature}.proofs-{suffix}.json. Create a spec with: "
                f"purlin:spec {feature}",
                file=sys.stderr,
            )
            spec_dir = "specs"
        path = os.path.join(spec_dir, f"{feature}.proofs-{suffix}.json")

        existing = []
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f).get("proofs", [])

        # Write-scoped overwrite keyed by (feature, tier, platform, test_file), per
        # proof_common RULE-4 (the file carries tier and platform, so within it the
        # key is (feature, test_file)), plus orphan reaping of vanished test files (RULE-11).
        run_files = {e.get("test_file") for e in new_entries}
        kept = [
            e
            for e in existing
            if e.get("feature") != feature
            or (
                e.get("test_file") not in run_files
                and os.path.exists(e.get("test_file") or "")
            )
        ]

        payload = {"tier": tier}
        if plat is not None:
            payload["platform"] = plat
        payload["proofs"] = kept + new_entries

        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)


if __name__ == "__main__":
    main()
