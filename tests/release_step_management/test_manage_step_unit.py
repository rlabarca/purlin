#!/usr/bin/env python3
"""Unit tests for manage_step.py internal functions and additional edge cases.

Supplements the integration-level scenario tests in tools/release/test_manage_step.py
by testing internal functions directly and covering edge cases beyond the 11 spec
scenarios.

Resolves [BUG] M52: manage_step.py has zero unit tests.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
MANAGE_STEP = os.path.join(PROJECT_ROOT, "tools", "release", "manage_step.py")

# Add project root to sys.path so we can import manage_step internals
sys.path.insert(0, PROJECT_ROOT)

TESTS_DIR = os.path.join(PROJECT_ROOT, "tests", "release_step_management")


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
    """Create a sandbox with .purlin structure and config pointing to real tools."""
    d = tempfile.mkdtemp()
    release_dir = os.path.join(d, ".purlin", "release")
    os.makedirs(release_dir, exist_ok=True)
    config_dir = os.path.join(d, ".purlin")
    write_json(os.path.join(config_dir, "config.json"), {
        "tools_root": os.path.relpath(
            os.path.join(PROJECT_ROOT, "tools"), d
        )
    })
    return d


def cleanup_sandbox(d):
    shutil.rmtree(d, ignore_errors=True)


def run_cmd(sandbox, args):
    """Run manage_step.py with PURLIN_PROJECT_ROOT set to sandbox."""
    env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
    result = subprocess.run(
        [sys.executable, MANAGE_STEP] + args,
        capture_output=True, text=True, env=env,
    )
    return result


def local_steps_path(sandbox):
    return os.path.join(sandbox, ".purlin", "release", "local_steps.json")


def config_path(sandbox):
    return os.path.join(sandbox, ".purlin", "release", "config.json")


def seed_local_step(sandbox, step):
    path = local_steps_path(sandbox)
    data = read_json(path)
    if data is None:
        data = {"steps": []}
    data["steps"].append(step)
    write_json(path, data)


def seed_config_entry(sandbox, entry):
    path = config_path(sandbox)
    data = read_json(path)
    if data is None:
        data = {"steps": []}
    data["steps"].append(entry)
    write_json(path, data)


# =====================================================================
# Section 1: Internal function tests (via import with patched paths)
# =====================================================================

def test_load_json_safe_nonexistent(r):
    """_load_json_safe returns None for non-existent file."""
    print("\n[Unit] _load_json_safe returns None for non-existent file")
    sandbox = make_sandbox()
    try:
        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        # Run as a subprocess that imports and tests the function directly
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_json_safe
result = _load_json_safe('/nonexistent/path/file.json')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] is None:
            r.log_pass("_load_json_safe returns None for non-existent file")
        else:
            r.log_fail(f"Expected None, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_load_json_safe_invalid_json(r):
    """_load_json_safe returns None for invalid JSON."""
    print("\n[Unit] _load_json_safe returns None for invalid JSON")
    sandbox = make_sandbox()
    try:
        bad_file = os.path.join(sandbox, "bad.json")
        with open(bad_file, 'w') as f:
            f.write("{not valid json")

        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_json_safe
result = _load_json_safe('{bad_file}')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] is None:
            r.log_pass("_load_json_safe returns None for invalid JSON")
        else:
            r.log_fail(f"Expected None, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_load_json_safe_valid_json(r):
    """_load_json_safe returns parsed data for valid JSON."""
    print("\n[Unit] _load_json_safe returns parsed data for valid JSON")
    sandbox = make_sandbox()
    try:
        good_file = os.path.join(sandbox, "good.json")
        write_json(good_file, {"key": "value"})

        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_json_safe
result = _load_json_safe('{good_file}')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == {"key": "value"}:
            r.log_pass("_load_json_safe returns parsed data for valid JSON")
        else:
            r.log_fail(f"Expected {{'key': 'value'}}, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_load_steps_absent_file(r):
    """_load_steps returns [] when file is absent."""
    print("\n[Unit] _load_steps returns [] when file is absent")
    sandbox = make_sandbox()
    try:
        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_steps
result = _load_steps('/nonexistent/path.json')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == []:
            r.log_pass("_load_steps returns [] when file is absent")
        else:
            r.log_fail(f"Expected [], got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_load_steps_empty_steps(r):
    """_load_steps returns [] for file with empty steps array."""
    print("\n[Unit] _load_steps returns [] for file with empty steps array")
    sandbox = make_sandbox()
    try:
        test_file = os.path.join(sandbox, "test.json")
        write_json(test_file, {"steps": []})

        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_steps
result = _load_steps('{test_file}')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == []:
            r.log_pass("_load_steps returns [] for file with empty steps array")
        else:
            r.log_fail(f"Expected [], got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_load_steps_with_data(r):
    """_load_steps returns steps array from valid file."""
    print("\n[Unit] _load_steps returns steps array from valid file")
    sandbox = make_sandbox()
    try:
        test_file = os.path.join(sandbox, "test.json")
        steps = [{"id": "a"}, {"id": "b"}]
        write_json(test_file, {"steps": steps})

        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _load_steps
result = _load_steps('{test_file}')
print(json.dumps({{"result": result}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == steps:
            r.log_pass("_load_steps returns steps array from valid file")
        else:
            r.log_fail(f"Expected {steps}, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_find_step_index_found(r):
    """_find_step_index returns correct index when step exists."""
    print("\n[Unit] _find_step_index returns correct index when step exists")
    sandbox = make_sandbox()
    try:
        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _find_step_index
steps = [{{"id": "a"}}, {{"id": "b"}}, {{"id": "c"}}]
idx = _find_step_index(steps, "b")
print(json.dumps({{"result": idx}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == 1:
            r.log_pass("_find_step_index returns 1 for 'b' at index 1")
        else:
            r.log_fail(f"Expected 1, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_find_step_index_not_found(r):
    """_find_step_index returns -1 when step does not exist."""
    print("\n[Unit] _find_step_index returns -1 when step does not exist")
    sandbox = make_sandbox()
    try:
        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _find_step_index
steps = [{{"id": "a"}}, {{"id": "b"}}]
idx = _find_step_index(steps, "z")
print(json.dumps({{"result": idx}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == -1:
            r.log_pass("_find_step_index returns -1 for missing step")
        else:
            r.log_fail(f"Expected -1, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


def test_find_step_index_empty_list(r):
    """_find_step_index returns -1 for empty steps list."""
    print("\n[Unit] _find_step_index returns -1 for empty steps list")
    sandbox = make_sandbox()
    try:
        env = dict(os.environ, PURLIN_PROJECT_ROOT=sandbox)
        code = f"""
import os, sys, json
os.environ['PURLIN_PROJECT_ROOT'] = '{sandbox}'
sys.path.insert(0, '{PROJECT_ROOT}')
from tools.release.manage_step import _find_step_index
idx = _find_step_index([], "any")
print(json.dumps({{"result": idx}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env,
        )
        output = json.loads(result.stdout.strip())
        if output["result"] == -1:
            r.log_pass("_find_step_index returns -1 for empty list")
        else:
            r.log_fail(f"Expected -1, got {output['result']}")
    finally:
        cleanup_sandbox(sandbox)


# =====================================================================
# Section 2: CLI argument parsing tests
# =====================================================================

def test_no_subcommand_shows_help(r):
    """Running with no subcommand exits 1 and shows help."""
    print("\n[Unit] No subcommand shows help and exits 1")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [])
        if result.returncode == 1:
            r.log_pass("Exit code 1 with no subcommand")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")
    finally:
        cleanup_sandbox(sandbox)


def test_create_missing_required_args(r):
    """Create without required args (--id, --name, --desc) exits non-zero."""
    print("\n[Unit] Create missing required args exits non-zero")
    sandbox = make_sandbox()
    try:
        # Missing --name and --desc
        result = run_cmd(sandbox, ["create", "--id", "test"])
        if result.returncode != 0:
            r.log_pass("Exit non-zero when --name and --desc missing")
        else:
            r.log_fail(f"Expected non-zero exit, got {result.returncode}")

        # Missing --id
        result = run_cmd(sandbox, ["create", "--name", "Test", "--desc", "Desc"])
        if result.returncode != 0:
            r.log_pass("Exit non-zero when --id missing")
        else:
            r.log_fail(f"Expected non-zero exit, got {result.returncode}")
    finally:
        cleanup_sandbox(sandbox)


def test_invalid_subcommand(r):
    """Running with an unknown subcommand exits non-zero."""
    print("\n[Unit] Invalid subcommand exits non-zero")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, ["foobar"])
        if result.returncode != 0:
            r.log_pass("Exit non-zero with invalid subcommand")
        else:
            r.log_fail(f"Expected non-zero exit, got {result.returncode}")
    finally:
        cleanup_sandbox(sandbox)


# =====================================================================
# Section 3: Additional edge case tests beyond the 11 spec scenarios
# =====================================================================

def test_create_with_code_and_instructions(r):
    """Create with --code and --agent-instructions populates both fields."""
    print("\n[Unit] Create with --code and --agent-instructions")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "full_step", "--name", "Full Step",
            "--desc", "A step with everything",
            "--code", "echo hello",
            "--agent-instructions", "Do the thing"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        if step.get("code") == "echo hello":
            r.log_pass("code field set correctly")
        else:
            r.log_fail(f"Expected code='echo hello', got {step.get('code')}")

        if step.get("agent_instructions") == "Do the thing":
            r.log_pass("agent_instructions field set correctly")
        else:
            r.log_fail(f"Expected agent_instructions='Do the thing', got {step.get('agent_instructions')}")
    finally:
        cleanup_sandbox(sandbox)


def test_create_preserves_existing_steps(r):
    """Create appends to existing steps, does not overwrite."""
    print("\n[Unit] Create preserves existing steps")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "first_step",
            "friendly_name": "First",
            "description": "First step",
            "code": None,
            "agent_instructions": None,
        })
        seed_config_entry(sandbox, {"id": "first_step", "enabled": True})

        result = run_cmd(sandbox, [
            "create", "--id", "second_step", "--name", "Second", "--desc", "Second step"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        ids = [s.get("id") for s in local.get("steps", [])]
        if ids == ["first_step", "second_step"]:
            r.log_pass("Both steps present in correct order")
        else:
            r.log_fail(f"Expected ['first_step', 'second_step'], got {ids}")

        cfg = read_json(config_path(sandbox))
        cfg_ids = [e.get("id") for e in cfg.get("steps", [])]
        if cfg_ids == ["first_step", "second_step"]:
            r.log_pass("Both config entries present in correct order")
        else:
            r.log_fail(f"Expected ['first_step', 'second_step'], got {cfg_ids}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_description(r):
    """Modify updates description field."""
    print("\n[Unit] Modify updates description field")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Old desc",
            "code": None,
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, ["modify", "my_step", "--desc", "New desc"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        if step.get("description") == "New desc":
            r.log_pass("description updated")
        else:
            r.log_fail(f"Expected description='New desc', got {step.get('description')}")

        if step.get("friendly_name") == "My Step":
            r.log_pass("friendly_name unchanged")
        else:
            r.log_fail(f"friendly_name should be unchanged: {step.get('friendly_name')}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_set_code(r):
    """Modify sets code from null to a value."""
    print("\n[Unit] Modify sets code from null to a value")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, ["modify", "my_step", "--code", "bash run.sh"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        if step.get("code") == "bash run.sh":
            r.log_pass("code set to 'bash run.sh'")
        else:
            r.log_fail(f"Expected code='bash run.sh', got {step.get('code')}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_set_agent_instructions(r):
    """Modify sets agent_instructions from null to a value."""
    print("\n[Unit] Modify sets agent_instructions from null to a value")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })

        result = run_cmd(sandbox, [
            "modify", "my_step", "--agent-instructions", "Follow these steps"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        if step.get("agent_instructions") == "Follow these steps":
            r.log_pass("agent_instructions set correctly")
        else:
            r.log_fail(f"Expected 'Follow these steps', got {step.get('agent_instructions')}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_clear_agent_instructions(r):
    """Modify with --clear-agent-instructions sets field to null."""
    print("\n[Unit] Modify --clear-agent-instructions sets field to null")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": "Some instructions",
        })

        result = run_cmd(sandbox, ["modify", "my_step", "--clear-agent-instructions"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        if step.get("agent_instructions") is None:
            r.log_pass("agent_instructions set to null")
        else:
            r.log_fail(f"Expected null, got {step.get('agent_instructions')}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_mutual_exclusion_agent_instructions(r):
    """--agent-instructions and --clear-agent-instructions are mutually exclusive."""
    print("\n[Unit] --agent-instructions and --clear-agent-instructions mutual exclusion")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "My Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": "Old",
        })

        result = run_cmd(sandbox, [
            "modify", "my_step",
            "--agent-instructions", "New",
            "--clear-agent-instructions"
        ])
        if result.returncode == 1:
            r.log_pass("Exit code 1")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "--agent-instructions" in result.stderr and "--clear-agent-instructions" in result.stderr:
            r.log_pass("stderr identifies the mutually exclusive flags")
        else:
            r.log_fail(f"Expected mutual exclusion error: {result.stderr}")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_multiple_fields(r):
    """Modify updates multiple fields at once."""
    print("\n[Unit] Modify updates multiple fields at once")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "Old Name",
            "description": "Old desc",
            "code": "echo old",
            "agent_instructions": "Old instructions",
        })

        result = run_cmd(sandbox, [
            "modify", "my_step",
            "--name", "New Name",
            "--desc", "New desc",
            "--code", "echo new"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        step = local["steps"][0] if local and local.get("steps") else {}
        checks = [
            step.get("friendly_name") == "New Name",
            step.get("description") == "New desc",
            step.get("code") == "echo new",
            step.get("agent_instructions") == "Old instructions",
        ]
        if all(checks):
            r.log_pass("All specified fields updated, unmodified field preserved")
        else:
            r.log_fail(f"Fields not correctly updated: {step}")
    finally:
        cleanup_sandbox(sandbox)


def test_delete_nonexistent_step(r):
    """Delete of non-existent step exits 1."""
    print("\n[Unit] Delete non-existent step exits 1")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, ["delete", "ghost_step"])
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


def test_delete_preserves_other_steps(r):
    """Delete removes only the targeted step, preserves others."""
    print("\n[Unit] Delete preserves other steps")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "keep_step",
            "friendly_name": "Keep",
            "description": "Keeper",
            "code": None,
            "agent_instructions": None,
        })
        seed_local_step(sandbox, {
            "id": "remove_step",
            "friendly_name": "Remove",
            "description": "To remove",
            "code": None,
            "agent_instructions": None,
        })
        seed_config_entry(sandbox, {"id": "keep_step", "enabled": True})
        seed_config_entry(sandbox, {"id": "remove_step", "enabled": True})

        result = run_cmd(sandbox, ["delete", "remove_step"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        local_ids = [s.get("id") for s in local.get("steps", [])]
        if local_ids == ["keep_step"]:
            r.log_pass("Only keep_step remains in local_steps.json")
        else:
            r.log_fail(f"Expected ['keep_step'], got {local_ids}")

        cfg = read_json(config_path(sandbox))
        cfg_ids = [e.get("id") for e in cfg.get("steps", [])]
        if cfg_ids == ["keep_step"]:
            r.log_pass("Only keep_step remains in config.json")
        else:
            r.log_fail(f"Expected ['keep_step'], got {cfg_ids}")
    finally:
        cleanup_sandbox(sandbox)


def test_dry_run_create_shows_both_files(r):
    """Dry-run create shows proposed JSON for both files."""
    print("\n[Unit] Dry-run create shows proposed JSON for both files")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "dry_step", "--name", "Dry Step",
            "--desc", "Dry run test", "--dry-run"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        if "[DRY RUN] local_steps.json" in result.stdout:
            r.log_pass("stdout mentions local_steps.json")
        else:
            r.log_fail(f"Expected local_steps.json mention: {result.stdout}")

        if "[DRY RUN] config.json" in result.stdout:
            r.log_pass("stdout mentions config.json")
        else:
            r.log_fail(f"Expected config.json mention: {result.stdout}")

        if "dry_step" in result.stdout:
            r.log_pass("stdout contains the step ID in proposed JSON")
        else:
            r.log_fail(f"Expected 'dry_step' in stdout: {result.stdout}")
    finally:
        cleanup_sandbox(sandbox)


def test_dry_run_modify(r):
    """Dry-run modify shows proposed JSON without writing."""
    print("\n[Unit] Dry-run modify shows proposed JSON without writing")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "my_step",
            "friendly_name": "Old Name",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })

        # Capture file contents before
        before = read_json(local_steps_path(sandbox))

        result = run_cmd(sandbox, [
            "modify", "my_step", "--name", "New Name", "--dry-run"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        if "[DRY RUN]" in result.stdout:
            r.log_pass("stdout contains [DRY RUN]")
        else:
            r.log_fail(f"Expected [DRY RUN] in stdout: {result.stdout}")

        after = read_json(local_steps_path(sandbox))
        if before == after:
            r.log_pass("File not modified during dry-run")
        else:
            r.log_fail(f"File was modified during dry-run: before={before}, after={after}")
    finally:
        cleanup_sandbox(sandbox)


def test_dry_run_delete(r):
    """Dry-run delete shows proposed JSON without writing."""
    print("\n[Unit] Dry-run delete shows proposed JSON without writing")
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

        before_local = read_json(local_steps_path(sandbox))
        before_cfg = read_json(config_path(sandbox))

        result = run_cmd(sandbox, ["delete", "my_step", "--dry-run"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        if "[DRY RUN]" in result.stdout:
            r.log_pass("stdout contains [DRY RUN]")
        else:
            r.log_fail(f"Expected [DRY RUN] in stdout: {result.stdout}")

        after_local = read_json(local_steps_path(sandbox))
        after_cfg = read_json(config_path(sandbox))
        if before_local == after_local and before_cfg == after_cfg:
            r.log_pass("Files not modified during dry-run")
        else:
            r.log_fail("Files were modified during dry-run")
    finally:
        cleanup_sandbox(sandbox)


def test_create_empty_id(r):
    """Create with empty string ID exits 1."""
    print("\n[Unit] Create with empty ID exits 1")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "", "--name", "Test", "--desc", "Desc"
        ])
        if result.returncode == 1:
            r.log_pass("Exit code 1 for empty ID")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")

        if "empty" in result.stderr.lower():
            r.log_pass("stderr mentions empty")
        else:
            r.log_fail(f"Expected 'empty' in stderr: {result.stderr}")
    finally:
        cleanup_sandbox(sandbox)


def test_create_empty_name(r):
    """Create with empty name exits 1."""
    print("\n[Unit] Create with empty name exits 1")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "test_step", "--name", "", "--desc", "Desc"
        ])
        if result.returncode == 1:
            r.log_pass("Exit code 1 for empty name")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")
    finally:
        cleanup_sandbox(sandbox)


def test_create_empty_desc(r):
    """Create with empty description exits 1."""
    print("\n[Unit] Create with empty description exits 1")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "test_step", "--name", "Test", "--desc", ""
        ])
        if result.returncode == 1:
            r.log_pass("Exit code 1 for empty description")
        else:
            r.log_fail(f"Expected exit code 1, got {result.returncode}")
    finally:
        cleanup_sandbox(sandbox)


def test_create_output_message(r):
    """Create success message matches spec format."""
    print("\n[Unit] Create success message matches spec format")
    sandbox = make_sandbox()
    try:
        result = run_cmd(sandbox, [
            "create", "--id", "msg_step", "--name", "Msg Step", "--desc", "Test"
        ])
        expected = "Created step 'msg_step' in local_steps.json and config.json."
        if expected in result.stdout:
            r.log_pass("Success message matches spec format")
        else:
            r.log_fail(f"Expected '{expected}' in stdout: '{result.stdout}'")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_output_message(r):
    """Modify success message matches spec format."""
    print("\n[Unit] Modify success message matches spec format")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "msg_step",
            "friendly_name": "Old",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })
        result = run_cmd(sandbox, ["modify", "msg_step", "--name", "New"])
        expected = "Updated step 'msg_step' in local_steps.json."
        if expected in result.stdout:
            r.log_pass("Success message matches spec format")
        else:
            r.log_fail(f"Expected '{expected}' in stdout: '{result.stdout}'")
    finally:
        cleanup_sandbox(sandbox)


def test_delete_output_message(r):
    """Delete success message matches spec format."""
    print("\n[Unit] Delete success message matches spec format")
    sandbox = make_sandbox()
    try:
        seed_local_step(sandbox, {
            "id": "msg_step",
            "friendly_name": "Msg Step",
            "description": "Desc",
            "code": None,
            "agent_instructions": None,
        })
        seed_config_entry(sandbox, {"id": "msg_step", "enabled": True})
        result = run_cmd(sandbox, ["delete", "msg_step"])
        expected = "Deleted step 'msg_step' from local_steps.json and config.json."
        if expected in result.stdout:
            r.log_pass("Success message matches spec format")
        else:
            r.log_fail(f"Expected '{expected}' in stdout: '{result.stdout}'")
    finally:
        cleanup_sandbox(sandbox)


def test_modify_preserves_step_order(r):
    """Modify preserves the order of steps in the array."""
    print("\n[Unit] Modify preserves step order")
    sandbox = make_sandbox()
    try:
        for step_id in ["a", "b", "c"]:
            seed_local_step(sandbox, {
                "id": step_id,
                "friendly_name": f"Step {step_id}",
                "description": "Desc",
                "code": None,
                "agent_instructions": None,
            })

        result = run_cmd(sandbox, ["modify", "b", "--name", "Updated B"])
        if result.returncode == 0:
            r.log_pass("Exit code 0")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        local = read_json(local_steps_path(sandbox))
        ids = [s.get("id") for s in local.get("steps", [])]
        if ids == ["a", "b", "c"]:
            r.log_pass("Step order preserved after modify")
        else:
            r.log_fail(f"Expected ['a', 'b', 'c'], got {ids}")

        step_b = local["steps"][1]
        if step_b.get("friendly_name") == "Updated B":
            r.log_pass("Step b name updated correctly")
        else:
            r.log_fail(f"Expected 'Updated B', got {step_b.get('friendly_name')}")
    finally:
        cleanup_sandbox(sandbox)


def test_atomic_write_creates_parent_dirs(r):
    """Create works when local_steps.json parent directory does not exist yet."""
    print("\n[Unit] Atomic write creates parent directories")
    sandbox = make_sandbox()
    try:
        # Remove the release directory to force creation
        release_dir = os.path.join(sandbox, ".purlin", "release")
        shutil.rmtree(release_dir)

        result = run_cmd(sandbox, [
            "create", "--id", "dir_step", "--name", "Dir Step", "--desc", "Test"
        ])
        if result.returncode == 0:
            r.log_pass("Exit code 0 even when release dir absent")
        else:
            r.log_fail(f"Expected exit code 0, got {result.returncode}: {result.stderr}")

        if os.path.exists(local_steps_path(sandbox)):
            r.log_pass("local_steps.json created with parent dirs")
        else:
            r.log_fail("local_steps.json was not created")
    finally:
        cleanup_sandbox(sandbox)


def main():
    r = Results()

    print("=== Release Step Management Unit Tests ===")

    # Section 1: Internal function tests
    test_load_json_safe_nonexistent(r)
    test_load_json_safe_invalid_json(r)
    test_load_json_safe_valid_json(r)
    test_load_steps_absent_file(r)
    test_load_steps_empty_steps(r)
    test_load_steps_with_data(r)
    test_find_step_index_found(r)
    test_find_step_index_not_found(r)
    test_find_step_index_empty_list(r)

    # Section 2: CLI argument parsing tests
    test_no_subcommand_shows_help(r)
    test_create_missing_required_args(r)
    test_invalid_subcommand(r)

    # Section 3: Additional edge case tests
    test_create_with_code_and_instructions(r)
    test_create_preserves_existing_steps(r)
    test_modify_description(r)
    test_modify_set_code(r)
    test_modify_set_agent_instructions(r)
    test_modify_clear_agent_instructions(r)
    test_modify_mutual_exclusion_agent_instructions(r)
    test_modify_multiple_fields(r)
    test_delete_nonexistent_step(r)
    test_delete_preserves_other_steps(r)
    test_dry_run_create_shows_both_files(r)
    test_dry_run_modify(r)
    test_dry_run_delete(r)
    test_create_empty_id(r)
    test_create_empty_name(r)
    test_create_empty_desc(r)
    test_create_output_message(r)
    test_modify_output_message(r)
    test_delete_output_message(r)
    test_modify_preserves_step_order(r)
    test_atomic_write_creates_parent_dirs(r)

    print(f"\n===============================")
    print(f"  Results: {r.passed}/{r.total()} passed")
    if r.failed > 0:
        print(f"\n  Failures:")
        for e in r.errors:
            print(f"    FAIL: {e}")
    print(f"===============================")

    write_results(r)
    return r


def write_results(r):
    os.makedirs(TESTS_DIR, exist_ok=True)
    result = {
        "status": r.status(),
        "passed": r.passed,
        "failed": r.failed,
        "total": r.total(),
        "test_file": "tests/release_step_management/test_manage_step_unit.py"
    }
    with open(os.path.join(TESTS_DIR, "tests.json"), 'w') as f:
        json.dump(result, f)
    print(f"\ntests.json: {r.status()}")


if __name__ == "__main__":
    r = main()
    sys.exit(0 if r.failed == 0 else 1)
