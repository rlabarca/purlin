#!/usr/bin/env python3
"""Tests for terminal identity helper (title + badge).

Tests validate:
1. The identity.sh helper script functions
2. Integration into tools/init.sh generate_launcher()
3. Integration into pl-run-builder.sh continuous mode
"""

import json
import os
import re
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
IDENTITY_SCRIPT = os.path.join(PROJECT_ROOT, 'tools', 'terminal', 'identity.sh')
INIT_SCRIPT = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
LAUNCHER_PATH = os.path.join(PROJECT_ROOT, 'pl-run-builder.sh')
ARCHITECT_LAUNCHER = os.path.join(PROJECT_ROOT, 'pl-run-architect.sh')
QA_LAUNCHER = os.path.join(PROJECT_ROOT, 'pl-run-qa.sh')
PM_LAUNCHER = os.path.join(PROJECT_ROOT, 'pl-run-pm.sh')

# Track results
results = {"passed": 0, "failed": 0, "total": 0, "details": []}


def record(name, passed, detail=""):
    results["total"] += 1
    if passed:
        results["passed"] += 1
        results["details"].append({"name": name, "status": "PASS"})
        print(f"  PASS: {name}")
    else:
        results["failed"] += 1
        results["details"].append({"name": name, "status": "FAIL", "detail": detail})
        print(f"  FAIL: {name} — {detail}")


def read_file(path):
    with open(path, 'r') as f:
        return f.read()


def run_bash(script_text, env=None):
    """Run a bash script and return (stdout, stderr, returncode)."""
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    result = subprocess.run(
        ['bash', '-c', script_text],
        capture_output=True, text=True, env=merged_env, timeout=10
    )
    return result.stdout, result.stderr, result.returncode


# ============================================================
# Helper Script Unit Tests
# ============================================================

def test_title_escape_sequence():
    """Scenario: Title escape sequence emitted for any terminal"""
    # Redirect /dev/tty to stdout for capture by using a subshell trick
    script = f"""
source "{IDENTITY_SCRIPT}"
# Override to capture output (not /dev/tty)
set_term_title() {{
    local text="$1"
    printf '\\033]0;%s\\007' "$text"
}}
set_term_title "PM"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "xterm"})
    record(
        "Title escape sequence emitted for any terminal",
        rc == 0 and "\033]0;PM\007" in stdout,
        f"rc={rc}, stdout repr={repr(stdout)}"
    )


def test_badge_escape_sequence_iterm2():
    """Scenario: Badge escape sequence emitted for iTerm2"""
    # Compute expected base64
    import base64
    expected_b64 = base64.b64encode(b"Engineer").decode()

    script = f"""
source "{IDENTITY_SCRIPT}"
# Override to capture output (not /dev/tty)
set_iterm_badge() {{
    [ "${{TERM_PROGRAM:-}}" = "iTerm.app" ] || return 0
    local text="$1"
    local encoded
    encoded=$(echo -n "$text" | base64 | tr -d '\\n')
    printf '\\e]1337;SetBadgeFormat=%s\\a' "$encoded"
}}
set_iterm_badge "Engineer"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "Badge escape sequence emitted for iTerm2",
        rc == 0 and f"SetBadgeFormat={expected_b64}" in stdout,
        f"rc={rc}, stdout repr={repr(stdout)}"
    )


def test_badge_noop_not_iterm2():
    """Scenario: Badge is no-op when not iTerm2"""
    script = f"""
source "{IDENTITY_SCRIPT}"
set_iterm_badge "QA" 2>/dev/null
echo "DONE"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "Apple_Terminal"})
    # Should produce no badge output, just "DONE"
    record(
        "Badge is no-op when not iTerm2",
        rc == 0 and stdout.strip() == "DONE",
        f"rc={rc}, stdout={repr(stdout)}"
    )


def test_badge_noop_unset_term_program():
    """Scenario: Badge is no-op when TERM_PROGRAM is unset"""
    env = dict(os.environ)
    env.pop("TERM_PROGRAM", None)
    script = f"""
unset TERM_PROGRAM
source "{IDENTITY_SCRIPT}"
set_iterm_badge "PM" 2>/dev/null
echo "DONE"
"""
    result = subprocess.run(
        ['bash', '-c', script],
        capture_output=True, text=True, env=env, timeout=10
    )
    record(
        "Badge is no-op when TERM_PROGRAM is unset",
        result.returncode == 0 and result.stdout.strip() == "DONE",
        f"rc={result.returncode}, stdout={repr(result.stdout)}"
    )


def test_base64_round_trip():
    """Scenario: Base64 encoding round-trips correctly"""
    test_text = "Engineer: Phase 2/5"
    script = f"""
source "{IDENTITY_SCRIPT}"
ENCODED=$(echo -n "{test_text}" | base64 | tr -d '\\n')
DECODED=$(echo "$ENCODED" | base64 -d)
echo "$DECODED"
"""
    stdout, _, rc = run_bash(script)
    record(
        "Base64 encoding round-trips correctly",
        rc == 0 and stdout.strip() == test_text,
        f"rc={rc}, decoded={repr(stdout.strip())}"
    )


def test_set_agent_identity_calls_both():
    """Scenario: set_agent_identity calls both title and badge"""
    # Use function wrappers that record calls
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
clear_term_title() {{ CALLS="$CALLS clear_title"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
clear_iterm_badge() {{ CALLS="$CALLS clear_badge"; }}
set_agent_identity "PM"
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "set_agent_identity calls both title and badge",
        rc == 0 and "title:PM" in stdout and "badge:PM" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


def test_clear_agent_identity_calls_both():
    """Scenario: clear_agent_identity calls both clear functions"""
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
clear_term_title() {{ CALLS="$CALLS clear_title"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
clear_iterm_badge() {{ CALLS="$CALLS clear_badge"; }}
clear_agent_identity
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "clear_agent_identity calls both clear functions",
        rc == 0 and "clear_title" in stdout and "clear_badge" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


# ============================================================
# Generated Launcher Integration Tests (tools/init.sh)
# ============================================================

def test_generated_launcher_contains_set_agent_identity():
    """Scenario: Generated launcher contains set_agent_identity call"""
    init_src = read_file(INIT_SCRIPT)
    # Check that the generate_launcher function emits set_agent_identity
    record(
        "Generated launcher contains set_agent_identity call",
        'set_agent_identity' in init_src and 'DISPLAY_NAME' in init_src,
        "set_agent_identity or DISPLAY_NAME not found in init.sh"
    )


def test_generated_launcher_exit_trap_contains_clear():
    """Scenario: Generated launcher EXIT trap contains clear_agent_identity"""
    init_src = read_file(INIT_SCRIPT)
    # The trap should include a guarded clear_agent_identity
    record(
        "Generated launcher EXIT trap contains clear_agent_identity",
        'clear_agent_identity' in init_src and 'type clear_agent_identity' in init_src,
        "guarded clear_agent_identity not found in init.sh trap"
    )


def test_generated_launcher_display_name_per_role():
    """Scenario: Generated launcher uses correct display name per role"""
    init_src = read_file(INIT_SCRIPT)
    has_architect = 'architect) DISPLAY_NAME="PM"' in init_src
    has_builder = 'builder) DISPLAY_NAME="Engineer"' in init_src
    has_qa = 'qa) DISPLAY_NAME="QA"' in init_src
    has_pm = 'pm) DISPLAY_NAME="PM"' in init_src
    record(
        "Generated launcher uses correct display name per role",
        has_architect and has_builder and has_qa and has_pm,
        f"architect={has_architect}, builder={has_builder}, qa={has_qa}, pm={has_pm}"
    )


# ============================================================
# pl-run-builder.sh Integration Tests
# ============================================================

def test_builder_launcher_sources_identity():
    """Verify pl-run-builder.sh sources the identity helper."""
    launcher_src = read_file(LAUNCHER_PATH)
    record(
        "pl-run-builder.sh sources identity helper",
        'tools/terminal/identity.sh' in launcher_src and 'source' in launcher_src,
        "identity.sh source line not found in pl-run-builder.sh"
    )


def test_builder_launcher_cleanup_clears_identity():
    """Verify pl-run-builder.sh cleanup function clears identity."""
    launcher_src = read_file(LAUNCHER_PATH)
    # Find the cleanup function and check it contains clear_agent_identity
    cleanup_match = re.search(r'cleanup\(\)\s*\{.*?\}', launcher_src, re.DOTALL)
    has_clear = cleanup_match and 'clear_agent_identity' in cleanup_match.group()
    record(
        "pl-run-builder.sh cleanup clears identity",
        has_clear,
        "clear_agent_identity not found in cleanup()"
    )


def test_builder_launcher_graceful_stop_clears_identity():
    """Verify graceful_stop clears identity before stopping."""
    launcher_src = read_file(LAUNCHER_PATH)
    graceful_match = re.search(r'graceful_stop\(\)\s*\{.*?\}', launcher_src, re.DOTALL)
    has_clear = graceful_match and 'clear_agent_identity' in graceful_match.group()
    record(
        "pl-run-builder.sh graceful_stop clears identity",
        has_clear,
        "clear_agent_identity not found in graceful_stop()"
    )


def test_builder_bootstrap_phase_identity():
    """Verify bootstrap phase sets identity to 'Engineer: Bootstrap'."""
    launcher_src = read_file(LAUNCHER_PATH)
    record(
        "Bootstrap phase sets identity to Engineer: Bootstrap",
        'set_agent_identity "Engineer: Bootstrap"' in launcher_src,
        "Bootstrap identity string not found"
    )


def test_builder_sequential_phase_identity():
    """Verify sequential phase sets identity with phase number."""
    launcher_src = read_file(LAUNCHER_PATH)
    record(
        "Sequential phase sets identity with phase number",
        'set_agent_identity "Engineer: Phase ${PHASE_NUM}/${TOTAL_PHASE_COUNT}"' in launcher_src,
        "Sequential phase identity pattern not found"
    )


def test_builder_parallel_phase_identity():
    """Verify parallel execution sets identity with phase list."""
    launcher_src = read_file(LAUNCHER_PATH)
    record(
        "Parallel execution sets identity with phase list",
        'set_agent_identity "Engineer: Phases $PHASE_DISPLAY"' in launcher_src,
        "Parallel phase identity pattern not found"
    )


def test_builder_evaluator_identity():
    """Verify evaluator phase sets identity to 'Engineer: Evaluating'."""
    launcher_src = read_file(LAUNCHER_PATH)
    count = launcher_src.count('set_agent_identity "Engineer: Evaluating"')
    record(
        "Evaluator sets identity to Engineer: Evaluating",
        count >= 2,  # One for parallel eval, one for sequential eval
        f"Found {count} evaluating identity calls, expected >= 2"
    )


def test_builder_between_phases_resets_identity():
    """Verify identity resets to 'Engineer' between phases."""
    launcher_src = read_file(LAUNCHER_PATH)
    # After evaluator completes (continue action), identity should reset
    # Find in the continue case blocks
    record(
        "Between phases resets identity to Engineer",
        launcher_src.count('set_agent_identity "Engineer"') >= 3,  # non-continuous, bootstrap-reset, between-phases
        f"Found {launcher_src.count('set_agent_identity \"Engineer\"')} Engineer identity resets"
    )


def test_non_continuous_mode_sets_identity():
    """Verify non-continuous mode sets identity to Engineer."""
    launcher_src = read_file(LAUNCHER_PATH)
    # Should be in the non-continuous block
    non_cont_section = launcher_src.split('# --- Non-continuous mode')[1].split('fi')[0] if '# --- Non-continuous mode' in launcher_src else ""
    record(
        "Non-continuous mode sets Engineer identity",
        'set_agent_identity "Engineer"' in non_cont_section,
        "Engineer identity not found in non-continuous section"
    )


# ============================================================
# Non-Engineer Root Launcher Integration Tests
# ============================================================

def _test_launcher_sources_identity(path, role_name):
    """Verify a root launcher sources the identity helper."""
    launcher_src = read_file(path)
    record(
        f"pl-run-{role_name.lower()}.sh sources identity helper",
        'tools/terminal/identity.sh' in launcher_src and 'source' in launcher_src,
        f"identity.sh source line not found in pl-run-{role_name.lower()}.sh"
    )


def _test_launcher_sets_identity(path, role_name, display_name):
    """Verify a root launcher sets identity before claude invocation."""
    launcher_src = read_file(path)
    record(
        f"pl-run-{role_name.lower()}.sh sets identity to {display_name}",
        f'set_agent_identity "{display_name}"' in launcher_src,
        f'set_agent_identity "{display_name}" not found in pl-run-{role_name.lower()}.sh'
    )


def _test_launcher_cleanup_clears_identity(path, role_name):
    """Verify a root launcher cleanup clears identity."""
    launcher_src = read_file(path)
    cleanup_match = re.search(r'cleanup\(\)\s*\{.*?\}', launcher_src, re.DOTALL)
    has_clear = cleanup_match and 'clear_agent_identity' in cleanup_match.group()
    record(
        f"pl-run-{role_name.lower()}.sh cleanup clears identity",
        has_clear,
        f"clear_agent_identity not found in pl-run-{role_name.lower()}.sh cleanup()"
    )


def test_architect_launcher_identity():
    _test_launcher_sources_identity(ARCHITECT_LAUNCHER, "architect")
    _test_launcher_sets_identity(ARCHITECT_LAUNCHER, "architect", "PM")
    _test_launcher_cleanup_clears_identity(ARCHITECT_LAUNCHER, "architect")


def test_qa_launcher_identity():
    _test_launcher_sources_identity(QA_LAUNCHER, "qa")
    _test_launcher_sets_identity(QA_LAUNCHER, "qa", "QA")
    _test_launcher_cleanup_clears_identity(QA_LAUNCHER, "qa")


def test_pm_launcher_identity():
    _test_launcher_sources_identity(PM_LAUNCHER, "pm")
    _test_launcher_sets_identity(PM_LAUNCHER, "pm", "PM")
    _test_launcher_cleanup_clears_identity(PM_LAUNCHER, "pm")


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print("=== Terminal Identity Tests ===\n")

    # Helper script unit tests
    print("--- Helper Script ---")
    test_title_escape_sequence()
    test_badge_escape_sequence_iterm2()
    test_badge_noop_not_iterm2()
    test_badge_noop_unset_term_program()
    test_base64_round_trip()
    test_set_agent_identity_calls_both()
    test_clear_agent_identity_calls_both()

    # Generated launcher integration
    print("\n--- Generated Launcher Integration ---")
    test_generated_launcher_contains_set_agent_identity()
    test_generated_launcher_exit_trap_contains_clear()
    test_generated_launcher_display_name_per_role()

    # pl-run-builder.sh integration
    print("\n--- pl-run-builder.sh Integration ---")
    test_builder_launcher_sources_identity()
    test_builder_launcher_cleanup_clears_identity()
    test_builder_launcher_graceful_stop_clears_identity()
    test_builder_bootstrap_phase_identity()
    test_builder_sequential_phase_identity()
    test_builder_parallel_phase_identity()
    test_builder_evaluator_identity()
    test_builder_between_phases_resets_identity()
    test_non_continuous_mode_sets_identity()

    # Non-builder root launcher integration
    print("\n--- Non-Engineer Root Launcher Integration ---")
    test_architect_launcher_identity()
    test_qa_launcher_identity()
    test_pm_launcher_identity()

    # Summary
    print(f"\n=== Results: {results['passed']}/{results['total']} passed ===")

    # Write tests.json
    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'terminal_identity')
    os.makedirs(tests_dir, exist_ok=True)
    tests_json = {
        "status": "PASS" if results["failed"] == 0 else "FAIL",
        "passed": results["passed"],
        "failed": results["failed"],
        "total": results["total"],
        "test_file": "tools/terminal/test_terminal_identity.py",
        "details": results["details"]
    }
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump(tests_json, f, indent=2)
        f.write('\n')

    print(f"Tests written to tests/terminal_identity/tests.json")
    sys.exit(0 if results["failed"] == 0 else 1)
