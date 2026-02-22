"""Tests for release checklist resolution (features/release_checklist_core.md).

Covers all 5 automated scenarios:
1. Full resolution with defaults
2. Disabled step preserved
3. Auto-discovery appends new global step
4. Orphaned config entry skipped with warning
5. Local step with reserved prefix rejected
"""
import json
import os
import sys
import tempfile
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Project root detection
_env_root = os.environ.get('AGENTIC_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.agentic_devops')):
            PROJECT_ROOT = candidate
            break

TESTS_DIR = os.path.join(PROJECT_ROOT, "tests", "release_checklist_core")

# Import the module under test
sys.path.insert(0, SCRIPT_DIR)
from resolve import resolve_checklist, load_global_steps


class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def log_pass(self, msg):
        self.passed += 1
        print(f"  PASS: {msg}")

    def log_fail(self, msg):
        self.failed += 1
        self.errors.append(msg)
        print(f"  FAIL: {msg}")

    def total(self):
        return self.passed + self.failed

    def status(self):
        return "PASS" if self.failed == 0 else "FAIL"


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def make_sandbox():
    d = tempfile.mkdtemp()
    return d


def cleanup_sandbox(d):
    shutil.rmtree(d, ignore_errors=True)


# Build a small global steps fixture (9 steps matching spec Section 2.7)
GLOBAL_STEPS_PATH = os.path.join(SCRIPT_DIR, "global_steps.json")


def test_full_resolution_with_defaults(r):
    """Scenario: Full resolution with defaults."""
    print("\n[Scenario] Full resolution with defaults")
    sandbox = make_sandbox()
    try:
        # No local_steps, no config
        local_path = os.path.join(sandbox, "local_steps.json")
        config_path = os.path.join(sandbox, "config.json")

        resolved, warnings, errors = resolve_checklist(
            global_path=GLOBAL_STEPS_PATH,
            local_path=local_path,
            config_path=config_path,
        )

        if len(resolved) == 9:
            r.log_pass("Resolved list contains exactly 9 steps")
        else:
            r.log_fail(f"Expected 9 steps, got {len(resolved)}")

        all_enabled = all(s["enabled"] for s in resolved)
        if all_enabled:
            r.log_pass("All steps have enabled=true")
        else:
            disabled = [s["id"] for s in resolved if not s["enabled"]]
            r.log_fail(f"Some steps are disabled: {disabled}")

        # Verify order matches global_steps.json declaration order
        global_steps = load_global_steps(GLOBAL_STEPS_PATH)
        expected_ids = [s["id"] for s in global_steps]
        actual_ids = [s["id"] for s in resolved]
        if actual_ids == expected_ids:
            r.log_pass("Steps are in declared order from global_steps.json")
        else:
            r.log_fail(f"Order mismatch: expected {expected_ids}, got {actual_ids}")

        # Verify order field is 1-based
        orders = [s["order"] for s in resolved]
        if orders == list(range(1, 10)):
            r.log_pass("Order field is 1-based sequential")
        else:
            r.log_fail(f"Order field incorrect: {orders}")

    finally:
        cleanup_sandbox(sandbox)


def test_disabled_step_preserved(r):
    """Scenario: Disabled step preserved."""
    print("\n[Scenario] Disabled step preserved")
    sandbox = make_sandbox()
    try:
        local_path = os.path.join(sandbox, "local_steps.json")
        config_path = os.path.join(sandbox, "config.json")

        # Config with push_to_remote disabled
        global_steps = load_global_steps(GLOBAL_STEPS_PATH)
        config_entries = []
        for s in global_steps:
            enabled = s["id"] != "purlin.push_to_remote"
            config_entries.append({"id": s["id"], "enabled": enabled})

        write_json(config_path, {"steps": config_entries})

        resolved, warnings, errors = resolve_checklist(
            global_path=GLOBAL_STEPS_PATH,
            local_path=local_path,
            config_path=config_path,
        )

        push_step = [s for s in resolved if s["id"] == "purlin.push_to_remote"]
        if len(push_step) == 1:
            r.log_pass("purlin.push_to_remote is in the resolved list")
        else:
            r.log_fail("purlin.push_to_remote missing from resolved list")
            return

        if push_step[0]["enabled"] is False:
            r.log_pass("purlin.push_to_remote has enabled=false")
        else:
            r.log_fail("purlin.push_to_remote should be disabled")

    finally:
        cleanup_sandbox(sandbox)


def test_auto_discovery_appends_new_step(r):
    """Scenario: Auto-discovery appends new global step."""
    print("\n[Scenario] Auto-discovery appends new global step")
    sandbox = make_sandbox()
    try:
        local_path = os.path.join(sandbox, "local_steps.json")
        config_path = os.path.join(sandbox, "config.json")

        # Config listing 8 of 9 steps (omitting push_to_remote)
        global_steps = load_global_steps(GLOBAL_STEPS_PATH)
        config_entries = [
            {"id": s["id"], "enabled": True}
            for s in global_steps
            if s["id"] != "purlin.push_to_remote"
        ]
        write_json(config_path, {"steps": config_entries})

        resolved, warnings, errors = resolve_checklist(
            global_path=GLOBAL_STEPS_PATH,
            local_path=local_path,
            config_path=config_path,
        )

        if len(resolved) == 9:
            r.log_pass("All 9 steps present after auto-discovery")
        else:
            r.log_fail(f"Expected 9 steps, got {len(resolved)}")

        # push_to_remote should be appended at the end
        last_step = resolved[-1]
        if last_step["id"] == "purlin.push_to_remote":
            r.log_pass("purlin.push_to_remote appended at end of resolved list")
        else:
            r.log_fail(f"Last step should be push_to_remote, got {last_step['id']}")

        if last_step.get("enabled") is True:
            r.log_pass("Auto-discovered step has enabled=true")
        else:
            r.log_fail("Auto-discovered step should have enabled=true")

    finally:
        cleanup_sandbox(sandbox)


def test_orphaned_config_entry_skipped(r):
    """Scenario: Orphaned config entry skipped with warning."""
    print("\n[Scenario] Orphaned config entry skipped with warning")
    sandbox = make_sandbox()
    try:
        local_path = os.path.join(sandbox, "local_steps.json")
        config_path = os.path.join(sandbox, "config.json")

        # Config with a nonexistent step ID
        global_steps = load_global_steps(GLOBAL_STEPS_PATH)
        config_entries = [{"id": s["id"], "enabled": True} for s in global_steps]
        config_entries.insert(2, {"id": "purlin.nonexistent_step", "enabled": True})
        write_json(config_path, {"steps": config_entries})

        resolved, warnings, errors = resolve_checklist(
            global_path=GLOBAL_STEPS_PATH,
            local_path=local_path,
            config_path=config_path,
        )

        # The orphaned entry should NOT be in resolved
        resolved_ids = [s["id"] for s in resolved]
        if "purlin.nonexistent_step" not in resolved_ids:
            r.log_pass("Orphaned entry absent from resolved list")
        else:
            r.log_fail("Orphaned entry should not appear in resolved list")

        # A warning should have been emitted
        orphan_warnings = [w for w in warnings if "purlin.nonexistent_step" in w]
        if len(orphan_warnings) > 0:
            r.log_pass("Warning logged identifying purlin.nonexistent_step as unknown")
        else:
            r.log_fail(f"Expected warning about orphaned step, got: {warnings}")

    finally:
        cleanup_sandbox(sandbox)


def test_local_step_reserved_prefix_rejected(r):
    """Scenario: Local step with reserved prefix rejected."""
    print("\n[Scenario] Local step with reserved prefix rejected")
    sandbox = make_sandbox()
    try:
        local_path = os.path.join(sandbox, "local_steps.json")
        config_path = os.path.join(sandbox, "config.json")

        # Local steps file with a reserved-prefix violation
        write_json(local_path, {
            "steps": [
                {
                    "id": "purlin.custom_deploy",
                    "friendly_name": "Custom Deploy",
                    "description": "Should be rejected",
                },
                {
                    "id": "myproject.deploy_staging",
                    "friendly_name": "Deploy Staging",
                    "description": "Valid local step",
                }
            ]
        })

        resolved, warnings, errors = resolve_checklist(
            global_path=GLOBAL_STEPS_PATH,
            local_path=local_path,
            config_path=config_path,
        )

        # The purlin.custom_deploy step should be excluded
        resolved_ids = [s["id"] for s in resolved]
        if "purlin.custom_deploy" not in resolved_ids:
            r.log_pass("purlin.custom_deploy excluded from resolved list")
        else:
            r.log_fail("purlin.custom_deploy should be excluded due to reserved prefix")

        # An error should identify the offending step
        prefix_errors = [e for e in errors if "purlin.custom_deploy" in e]
        if len(prefix_errors) > 0:
            r.log_pass("Error raised identifying purlin.custom_deploy as using reserved prefix")
        else:
            r.log_fail(f"Expected error about reserved prefix, got: {errors}")

        # The valid local step should still be present
        if "myproject.deploy_staging" in resolved_ids:
            r.log_pass("Valid local step myproject.deploy_staging included in resolved list")
        else:
            r.log_fail("Valid local step myproject.deploy_staging should be in resolved list")

    finally:
        cleanup_sandbox(sandbox)


def main():
    r = Results()

    print("=== Release Checklist Core Tests ===")

    # Verify global_steps.json exists first
    if not os.path.exists(GLOBAL_STEPS_PATH):
        r.log_fail(f"global_steps.json not found at {GLOBAL_STEPS_PATH}")
        write_results(r)
        return

    test_full_resolution_with_defaults(r)
    test_disabled_step_preserved(r)
    test_auto_discovery_appends_new_step(r)
    test_orphaned_config_entry_skipped(r)
    test_local_step_reserved_prefix_rejected(r)

    print(f"\n===============================")
    print(f"  Results: {r.passed}/{r.total()} passed")
    if r.failed > 0:
        print(f"\n  Failures:")
        for e in r.errors:
            print(f"  FAIL: {e}")
    print(f"===============================")

    write_results(r)


def write_results(r):
    os.makedirs(TESTS_DIR, exist_ok=True)
    result = {
        "status": r.status(),
        "passed": r.passed,
        "failed": r.failed,
        "total": r.total(),
    }
    with open(os.path.join(TESTS_DIR, "tests.json"), 'w') as f:
        json.dump(result, f)
    print(f"\ntests.json: {r.status()}")


if __name__ == "__main__":
    main()
