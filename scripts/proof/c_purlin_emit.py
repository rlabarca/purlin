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

At the end of the run, the same moment the proof files are written, the
emitter writes or merges the project's run marker
`.purlin/runtime/test_run.json` (proof_common RULE-19), so a receipt issued
in a consumer project can record which run its evidence came from.
"""

import datetime
import glob
import json
import os
import platform
import subprocess
import sys
import time

_FAMILIES = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}


def _host_platform():
    """PURLIN_PLATFORM when set, else the OS family. The only host lookup here."""
    env = os.environ.get("PURLIN_PLATFORM", "").strip()
    if env:
        return env
    system = platform.system()
    return _FAMILIES.get(system, system.lower())


# ── The run marker (proof_common RULE-19) ───────────────────────────────────
# Written or merged at the same moment the proof files are written, so a
# consumer receipt can record which run its evidence came from.

_RUN_MARKER_REL = os.path.join(".purlin", "runtime", "test_run.json")


def _run_marker_commit(root):
    """HEAD in `root`, or None when `root` is not inside a git work tree."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                             capture_output=True, text=True)
    except OSError:
        return None
    return out.stdout.strip() or None


def _write_run_marker(root, sweep, test_files, passed, failed, skipped):
    """Write or merge `<root>/.purlin/runtime/test_run.json` (RULE-19).

    Nothing is written when `<root>/.purlin` is absent: that is not a Purlin
    project. An existing marker whose `commit` equals this run's commit is
    merged into: `test_files` unioned, the three counts summed, this run
    appended to `runs`, `ok` and-ed, and every other top-level field carried
    through untouched. A marker naming another commit is replaced. The file is
    written to a temp file in the same directory and renamed over the target,
    so a concurrent reader sees one whole marker or the other; a read that
    lands on unparsable JSON is retried before this run starts a fresh marker.
    """
    if not os.path.isdir(os.path.join(root, ".purlin")):
        return None
    path = os.path.join(root, _RUN_MARKER_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    commit = _run_marker_commit(root)
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    files = sorted({str(f).replace(os.sep, "/").replace("\\", "/")
                    for f in test_files if f})
    marker = {}
    for _attempt in range(3):
        try:
            with open(path) as f:
                existing = json.load(f)
            if isinstance(existing, dict) and existing.get("commit") == commit:
                marker = existing
            break
        except FileNotFoundError:
            break
        except (ValueError, OSError):
            # A concurrent writer is mid-replace: read again before giving up.
            time.sleep(0.05)
    runs = list(marker.get("runs") or [])
    runs.append({"plugin": sweep, "at": at, "test_files": files,
                 "passed": passed, "failed": failed, "skipped": skipped})
    marker.update({
        "at": at,
        "commit": commit,
        "sweep": sweep,
        "test_files": sorted(set(marker.get("test_files") or []) | set(files)),
        "passed": int(marker.get("passed") or 0) + passed,
        "failed": int(marker.get("failed") or 0) + failed,
        "skipped": int(marker.get("skipped") or 0) + skipped,
        "ok": bool(marker.get("ok", True)) and failed == 0,
        "runs": runs,
    })
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as f:
        json.dump(marker, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
    return marker


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

    # RULE-19: the run marker, written at the same moment as the proof
    # files. The emitter sees no skips (the C header records only calls the
    # runner made), so `skipped` is 0.
    all_entries = [e for group in grouped.values() for e in group]
    _write_run_marker(
        os.getcwd(),
        "c_purlin",
        [e["test_file"] for e in all_entries],
        sum(1 for e in all_entries if e["status"] == "pass"),
        sum(1 for e in all_entries if e["status"] != "pass"),
        0,
    )


if __name__ == "__main__":
    main()
