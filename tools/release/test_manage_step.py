#!/usr/bin/env python3
"""Tests for manage_step.py (features/release_step_management.md).

Covers all 11 automated scenarios:
1.  Create valid local step
2.  Reject purlin. prefix on create
3.  Reject duplicate local ID on create
4.  Reject duplicate global ID on create
5.  Modify existing step name
6.  Modify clears optional field
7.  Delete step removes from both files
8.  Modify non-existent step
9.  Dry-run does not modify files
10. Modify with no field flags fails
11. Mutually exclusive flags rejected
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MANAGE_STEP = os.path.join(SCRIPT_DIR, "manage_step.py")

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

TESTS_DIR = os.path.join(PROJECT_ROOT, "tests", "release_step_management")
GLOBAL_STEPS_PATH = os.path.join(SCRIPT_DIR, "global_steps.json")


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
        f.write('\n')


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


def make_sandbox():
    """Create a sandbox with .agentic_devops structure and config pointing to real tools."""
    d = tempfile.mkdtemp()
    release_dir = os.path.join(d, ".agentic_devops", "release")
    os.makedirs(release_dir, exist_ok=True)
    # Write config.json so manage_step.py can resolve tools_root
    config_dir = os.path.join(d, ".agentic_devops")
    write_json(os.path.join(config_dir, "config.json"), {
        "tools_root": os.path.relpath(
            os.path.join(PROJECT_ROOT, "tools"), d
        )
    })
    return d


def cleanup_sandbox(d):
    shutil.rmtree(d, ignore_errors=True)


def run_cmd(sandbox, args):
    """Run manage_step.py with AGENTIC_PROJECT_ROOT set to sandbox."""
    env = dict(os.environ, AGENTIC_PROJECT_ROOT=sandbox)
    result = subprocess.run(
        [sys.executable, MANAGE_STEP] + args,
        capture_output=True, text=True, env=env,
    )
    return result


def local_steps_path(sandbox):
    return os.path.join(sandbox, ".agentic_devops", "release", "local_steps.json")


def config_path(sandbox):
    return os.path.join(sandbox, ".agentic_devops", "release", "config.json")


def seed_local_step(sandbox, step):
    """Seed a local step into the sandbox."""
    path = local_steps_path(sandbox)
    data = read_json(path)
    if data is None:
        data = {"steps": []}
    data["steps"].append(step)
    write_json(path, data)


def seed_config_entry(sandbox, entry):
    """Seed a config entry into the sandbox."""
    path = config_path(sandbox)
    data = read_json(path)
    if data is None:
        data = {"steps": []}
    data["steps"].append(entry)
    write_json(path, data)


# === Scenario Tests ===

def test_create_valid_local_step(r):
    """Scenario: Create valid local step."""
    print("\n[Scenario] Create valid local step")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "my_step", "--name", "My Step", "--desc", "Does something"
        ])

        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        if local and len(local.get("steps", [])) == 1:
            step = local["steps"][0]
            checks = [
                step.get("id") == "my_step",
                step.get("friendly_name") == "My Step",
                step.get("description") == "Does something",
                step.get("code") is None,
                step.get("agent_instructions") is None,
            ]
            if all(checks):
                r.log_pass("local_steps.json contains correct step definition")
            else:
                r.log_fail(f"Step fields incorrect: {step}")
        else:
            r.log_fail(f"Expected 1 step in local_steps.json, got: {local}")

        cfg = read_json(config_path(sandbox))
        if cfg:
            cfg_entries = [e for e in cfg.get("steps", []) if e.get("id") == "my_step"]
            if len(cfg_entries) == 1 and cfg_entries[0].get("enabled") is True:
                r.log_pass("config.json contains enabled entry for my_step")
            else:
                r.log_fail(f"config.json entry incorrect: {cfg}")
        else:
            r.log_fail("config.json not created")

    finally:
        cleanup_sandbox(sandbox)


def test_reject_purlin_prefix(r):
    """Scenario: Reject purlin. prefix on create."""
    print("\n[Scenario] Reject purlin. prefix on create")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "purlin.custom", "--name", "Custom", "--desc", "Custom step"
        ])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "purlin." in result.stderr:
            r.log_pass("stderr identifies reserved purlin. prefix")
        else:
            r.log_fail(f"Expected purlin. prefix error in stderr: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        if local is None:
            r.log_pass("No files created or modified")
        else:
            if len(local.get("steps", [])) == 0:
                r.log_pass("No files created or modified")
            else:
                r.log_fail(f"local_steps.json should not have been created: {local}")

    finally:
        cleanup_sandbox(sandbox)


def test_reject_duplicate_local_id(r):
    """Scenario: Reject duplicate local ID on create."""
    print("\n[Scenario] Reject duplicate local ID on create")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "existing_step",
            "friendly_name": "Existing",
            "description": "Already here",
            "code": None,
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, [
            "create", "--id", "existing_step", "--name", "Dupe", "--desc", "Duplicate"
        ])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "local" in result.stderr.lower() and "existing_step" in result.stderr:
            r.log_pass("stderr identifies existing_step as already existing in local steps")
        else:
            r.log_fail(f"Expected local conflict error: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        if local and len(local.get("steps", [])) == 1:
            r.log_pass("local_steps.json unchanged")
        else:
            r.log_fail(f"local_steps.json should have exactly 1 step: {local}")

    finally:
        cleanup_sandbox(sandbox)


def test_reject_duplicate_global_id(r):
    """Scenario: Reject duplicate global ID on create."""
    print("\n[Scenario] Reject duplicate global ID on create")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "purlin.push_to_remote",
            "--name", "Push", "--desc", "Custom push"
        ])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        # The purlin. prefix check fires first per the spec
        if "purlin." in result.stderr:
            r.log_pass("stderr identifies the conflict (prefix check fires first)")
        else:
            r.log_fail(f"Expected conflict error in stderr: {result.stderr}")

    finally:
        cleanup_sandbox(sandbox)


def test_modify_existing_step_name(r):
    """Scenario: Modify existing step name."""
    print("\n[Scenario] Modify existing step name")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "Old Name",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })
        seed_config_entry(sandbox, {"id": "my_step", "enabled": False})

        result = run_cmd(sandbox, ["modify", "my_step", "--name", "New Name"])

        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local else {}
        if step.get("friendly_name") == "New Name":
            r.log_pass("friendly_name updated to 'New Name'")
        else:
            r.log_fail(f"friendly_name should be 'New Name': {step}")

        if step.get("description") == "Desc" and step.get("code") is None:
            r.log_pass("Other fields unchanged")
        else:
            r.log_fail(f"Other fields should be unchanged: {step}")

        cfg = read_json(config_path(sandbox))
        cfg_entry = [e for e in cfg.get("steps", []) if e.get("id") == "my_step"]
        if len(cfg_entry) == 1 and cfg_entry[0].get("enabled") is False:
            r.log_pass("config.json unchanged (enabled state preserved)")
        else:
            r.log_fail(f"config.json should be unchanged: {cfg}")

    finally:
        cleanup_sandbox(sandbox)


def test_modify_clears_optional_field(r):
    """Scenario: Modify clears optional field."""
    print("\n[Scenario] Modify clears optional field")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": "echo hello",
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, ["modify", "my_step", "--clear-code"])

        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local else {}
        if step.get("code") is None:
            r.log_pass("code set to null")
        else:
            r.log_fail(f"code should be null: {step.get('code')}")

        if step.get("friendly_name") == "My Step" and step.get("description") == "Desc":
            r.log_pass("Other fields unchanged")
        else:
            r.log_fail(f"Other fields should be unchanged: {step}")

    finally:
        cleanup_sandbox(sandbox)


def test_delete_step_removes_from_both(r):
    """Scenario: Delete step removes from both files."""
    print("\n[Scenario] Delete step removes from both files")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })
        seed_config_entry(sandbox, {"id": "my_step", "enabled": True})

        result = run_cmd(sandbox, ["delete", "my_step"])

        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        local_ids = [s.get("id") for s in local.get("steps", [])] if local else []
        if "my_step" not in local_ids:
            r.log_pass("my_step removed from local_steps.json")
        else:
            r.log_fail(f"my_step should be removed from local_steps.json: {local_ids}")

        cfg = read_json(config_path(sandbox))
        cfg_ids = [e.get("id") for e in cfg.get("steps", [])] if cfg else []
        if "my_step" not in cfg_ids:
            r.log_pass("my_step removed from config.json")
        else:
            r.log_fail(f"my_step should be removed from config.json: {cfg_ids}")

    finally:
        cleanup_sandbox(sandbox)


def test_modify_nonexistent_step(r):
    """Scenario: Modify non-existent step."""
    print("\n[Scenario] Modify non-existent step")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, ["modify", "ghost_step", "--name", "New Name"])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "step not found: ghost_step" in result.stderr:
            r.log_pass("stderr contains 'step not found: ghost_step'")
        else:
            r.log_fail(f"Expected 'step not found' in stderr: {result.stderr}")

    finally:
        cleanup_sandbox(sandbox)


def test_dry_run_no_modification(r):
    """Scenario: Dry-run does not modify files."""
    print("\n[Scenario] Dry-run does not modify files")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "my_step", "--name", "My Step",
            "--desc", "Desc", "--dry-run"
        ])

        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        if local is None or len(local.get("steps", [])) == 0:
            r.log_pass("local_steps.json not created")
        else:
            r.log_fail(f"local_steps.json should not have been created: {local}")

        if "[DRY RUN]" in result.stdout:
            r.log_pass("stdout contains [DRY RUN] with proposed JSON")
        else:
            r.log_fail(f"Expected [DRY RUN] in stdout: {result.stdout}")

    finally:
        cleanup_sandbox(sandbox)


def test_modify_no_field_flags(r):
    """Scenario: Modify with no field flags fails."""
    print("\n[Scenario] Modify with no field flags fails")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, ["modify", "my_step"])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if result.stderr:
            r.log_pass("stderr contains usage message")
        else:
            r.log_fail("Expected usage message in stderr")

    finally:
        cleanup_sandbox(sandbox)


def test_mutually_exclusive_flags(r):
    """Scenario: Mutually exclusive flags rejected."""
    print("\n[Scenario] Mutually exclusive flags rejected")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": "echo hi",
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, [
            "modify", "my_step", "--code", "echo bye", "--clear-code"
        ])

        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "--code" in result.stderr and "--clear-code" in result.stderr:
            r.log_pass("stderr identifies --code and --clear-code as mutually exclusive")
        else:
            r.log_fail(f"Expected mutual exclusivity error: {result.stderr}")

    finally:
        cleanup_sandbox(sandbox)


def main():
    r = Results()

    print("=== Release Step Management Tests ===")

    test_create_valid_local_step(r)
    test_reject_purlin_prefix(r)
    test_reject_duplicate_local_id(r)
    test_reject_duplicate_global_id(r)
    test_modify_existing_step_name(r)
    test_modify_clears_optional_field(r)
    test_delete_step_removes_from_both(r)
    test_modify_nonexistent_step(r)
    test_dry_run_no_modification(r)
    test_modify_no_field_flags(r)
    test_mutually_exclusive_flags(r)

    print(f"\n===============================")
    print(f"  Results: {r.passed}/{r.total()} passed")
    if r.failed > 0:
        print(f"\n  Failures:")
        for e in r.errors:
            print(f"    FAIL: {e}")
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
