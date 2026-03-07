#!/usr/bin/env python3
"""Release audit: verify zero-queue mandate.

Checks that all features have architect: DONE, builder: DONE,
and qa in [CLEAN, N/A].
See features/release_audit_automation.md Section 2.5.
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


def load_feature_status(project_root):
    """Load per-feature role status from critic.json files in tests/."""
    tests_dir = os.path.join(project_root, "tests")
    statuses = []

    if not os.path.isdir(tests_dir):
        return statuses

    for entry in sorted(os.listdir(tests_dir)):
        critic_path = os.path.join(tests_dir, entry, "critic.json")
        data = load_json_safe(critic_path)
        if data is None:
            continue
        role_status = data.get("role_status", {})
        statuses.append({
            "feature": entry,
            "architect": role_status.get("architect", "UNKNOWN"),
            "builder": role_status.get("builder", "UNKNOWN"),
            "qa": role_status.get("qa", "UNKNOWN"),
        })

    return statuses


def main(project_root=None):
    if project_root is None:
        project_root = detect_project_root(SCRIPT_DIR)

    statuses = load_feature_status(project_root)
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
                f"features/{feat['feature']}.md",
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
