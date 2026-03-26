#!/usr/bin/env python3
"""Release audit: verify zero-queue mandate.

Checks that all features have architect: DONE, builder: DONE,
and qa in [CLEAN, N/A].
See features/release_audit_automation.md Section 2.5.

Uses tools/cdd/status.sh JSON output for per-feature role status.
"""
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import (
    detect_project_root, make_finding, make_output, output_and_exit,
    load_json_safe,
)


def _run_status_sh(project_root):
    """Run status.sh and return parsed JSON output.

    Returns the parsed JSON dict on success, or None on failure.
    """
    status_sh = os.path.join(project_root, "tools", "cdd", "status.sh")
    if not os.path.isfile(status_sh):
        return None
    try:
        result = subprocess.run(
            [status_sh],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "PURLIN_PROJECT_ROOT": project_root},
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def _load_cached_status(project_root):
    """Load the cached status.json written by status.sh.

    Falls back to running status.sh if the cache file does not exist.
    """
    cache_path = os.path.join(project_root, ".purlin", "cache", "status.json")
    data = load_json_safe(cache_path)
    if data is not None:
        return data
    return _run_status_sh(project_root)


def load_feature_status(project_root, status_data=None):
    """Load per-feature role status by running status.sh.

    Parses the flat features array from status.sh JSON output.
    Each feature entry has: file, label, architect, builder, qa fields.

    Args:
        project_root: Project root path.
        status_data: Pre-loaded status JSON dict (for testing). If None,
            runs status.sh or reads cached status.json.
    """
    if status_data is None:
        status_data = _load_cached_status(project_root)

    statuses = []
    if status_data is None:
        return statuses

    features = status_data.get("features", [])
    for feat in features:
        file_path = feat.get("file", "")
        # Extract feature stem from path like "features/foo.md"
        stem = os.path.splitext(os.path.basename(file_path))[0]
        # Skip tombstones
        if "tombstones/" in file_path or "tombstones\\" in file_path:
            continue
        statuses.append({
            "feature": stem,
            "file": file_path,
            "architect": feat.get("architect", "UNKNOWN"),
            "builder": feat.get("builder", "UNKNOWN"),
            "qa": feat.get("qa", "UNKNOWN"),
        })

    return statuses


def main(project_root=None, status_data=None):
    """Run zero-queue mandate verification.

    Args:
        project_root: Project root path. Auto-detected if None.
        status_data: Pre-loaded status JSON dict (for testing).
    """
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    statuses = load_feature_status(project_root, status_data=status_data)
    findings = []

    for feat in statuses:
        blocking_roles = []
        if feat["architect"] != "DONE":
            blocking_roles.append(f"architect: {feat['architect']}")
        if feat["builder"] != "DONE":
            blocking_roles.append(f"builder: {feat['builder']}")
        if feat["qa"] not in ("CLEAN", "N/A"):
            blocking_roles.append(f"qa: {feat['qa']}")

        if blocking_roles:
            findings.append(make_finding(
                "CRITICAL", "blocking_feature",
                feat.get("file", f"features/{feat['feature']}.md"),
                f"Feature blocks release: {', '.join(blocking_roles)}",
            ))

    total = len(statuses)
    result = make_output(
        "verify_zero_queue", findings,
        summary=(
            f"All {total} features meet zero-queue mandate"
            if not findings
            else f"{len(findings)} of {total} features block release"
        ),
    )
    return result


if __name__ == "__main__":
    output_and_exit(main())
