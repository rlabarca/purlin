#!/usr/bin/env python3
"""Tests for Purlin Worktree Identity feature.

Validates:
1. Worktree label assignment (W1, W2, gap-filling)
2. Badge format (mode name alone, worktree label appended)
3. Terminal title format (<project> - <badge>)
4. set_agent_identity with project parameter
5. pl-run.sh launcher identity integration
6. Sub-agent worktree label exclusion
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
LAUNCHER_PATH = os.path.join(PROJECT_ROOT, 'pl-run.sh')

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
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    result = subprocess.run(
        ['bash', '-c', script_text],
        capture_output=True, text=True, env=merged_env, timeout=10
    )
    return result.stdout, result.stderr, result.returncode


# ============================================================
# Label Assignment Tests (simulate worktree label logic)
# ============================================================

def test_first_worktree_gets_w1():
    """Scenario: First worktree gets label W1"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # No existing label files — next label should be W1
        script = f"""
        _used_nums=()
        for _lf in "{tmpdir}"/*/.purlin_worktree_label; do
            [ -f "$_lf" ] || continue
            _n=$(tr -cd '0-9' < "$_lf")
            [ -n "$_n" ] && _used_nums+=("$_n")
        done
        _next=1
        while printf '%s\\n' "${{_used_nums[@]}}" 2>/dev/null | grep -qx "$_next"; do
            _next=$((_next + 1))
        done
        echo "W${{_next}}"
        """
        stdout, _, rc = run_bash(script)
        record(
            "First worktree gets label W1",
            rc == 0 and stdout.strip() == "W1",
            f"rc={rc}, label={repr(stdout.strip())}"
        )


def test_second_worktree_gets_w2():
    """Scenario: Second concurrent worktree gets label W2"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create W1 label
        wt1 = os.path.join(tmpdir, "wt1")
        os.makedirs(wt1)
        with open(os.path.join(wt1, ".purlin_worktree_label"), "w") as f:
            f.write("W1")

        script = f"""
        _used_nums=()
        for _lf in "{tmpdir}"/*/.purlin_worktree_label; do
            [ -f "$_lf" ] || continue
            _n=$(tr -cd '0-9' < "$_lf")
            [ -n "$_n" ] && _used_nums+=("$_n")
        done
        _next=1
        while printf '%s\\n' "${{_used_nums[@]}}" 2>/dev/null | grep -qx "$_next"; do
            _next=$((_next + 1))
        done
        echo "W${{_next}}"
        """
        stdout, _, rc = run_bash(script)
        record(
            "Second concurrent worktree gets label W2",
            rc == 0 and stdout.strip() == "W2",
            f"rc={rc}, label={repr(stdout.strip())}"
        )


def test_gap_filling_reuses_numbers():
    """Scenario: Gap-filling reuses cleaned-up numbers"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create W1 and W3 (W2 is missing — gap)
        for num, name in [(1, "wt1"), (3, "wt3")]:
            wt = os.path.join(tmpdir, name)
            os.makedirs(wt)
            with open(os.path.join(wt, ".purlin_worktree_label"), "w") as f:
                f.write(f"W{num}")

        script = f"""
        _used_nums=()
        for _lf in "{tmpdir}"/*/.purlin_worktree_label; do
            [ -f "$_lf" ] || continue
            _n=$(tr -cd '0-9' < "$_lf")
            [ -n "$_n" ] && _used_nums+=("$_n")
        done
        _next=1
        while printf '%s\\n' "${{_used_nums[@]}}" 2>/dev/null | grep -qx "$_next"; do
            _next=$((_next + 1))
        done
        echo "W${{_next}}"
        """
        stdout, _, rc = run_bash(script)
        record(
            "Gap-filling reuses cleaned-up numbers",
            rc == 0 and stdout.strip() == "W2",
            f"rc={rc}, label={repr(stdout.strip())}"
        )


# ============================================================
# Badge & Title Format Tests (pl-run.sh structure)
# ============================================================

def test_badge_format_without_worktree():
    """Scenario: Badge format without worktree"""
    launcher_src = read_file(LAUNCHER_PATH)
    # ROLE_DISPLAY should be MODE_NAME when no worktree label exists
    has_role_display_assignment = 'ROLE_DISPLAY="$MODE_NAME"' in launcher_src
    # set_agent_identity called with ROLE_DISPLAY
    has_identity_call = 'set_agent_identity "$ROLE_DISPLAY"' in launcher_src
    # --name passed as ROLE_DISPLAY
    has_name_arg = '--name "$ROLE_DISPLAY"' in launcher_src
    # MODE_NAME for engineer is "Engineer" (no prefix)
    has_engineer_mode = 'engineer) MODE_NAME="Engineer"' in launcher_src
    record(
        "Badge format without worktree",
        has_role_display_assignment and has_identity_call and has_name_arg and has_engineer_mode,
        f"role_display={has_role_display_assignment}, identity={has_identity_call}, "
        f"name={has_name_arg}, engineer={has_engineer_mode}"
    )


def test_badge_format_with_worktree():
    """Scenario: Badge format with worktree"""
    launcher_src = read_file(LAUNCHER_PATH)
    # When worktree label file exists, ROLE_DISPLAY should append label
    has_label_check = '.purlin_worktree_label' in launcher_src
    has_label_append = re.search(
        r'ROLE_DISPLAY="\$MODE_NAME \(\$WORKTREE_LABEL\)"', launcher_src
    )
    record(
        "Badge format with worktree",
        has_label_check and has_label_append is not None,
        f"label_check={has_label_check}, label_append={has_label_append is not None}"
    )


def test_open_mode_badge_in_worktree():
    """Scenario: Open mode badge in worktree"""
    launcher_src = read_file(LAUNCHER_PATH)
    # When no --mode is set, MODE_NAME should be "Purlin"
    has_default_purlin = re.search(r'\*\)\s+MODE_NAME="Purlin"', launcher_src)
    record(
        "Open mode badge in worktree",
        has_default_purlin is not None,
        f"default_purlin={has_default_purlin is not None}"
    )


def test_mode_switch_preserves_worktree_label():
    """Scenario: Mode switch preserves worktree label

    The agent reads .purlin_worktree_label on mode switch (Section 4.1.1 of
    the system prompt). This test validates the protocol: the identity.sh
    helper correctly formats badge and title when given the label.
    """
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
set_agent_identity "QA (W1)" "myproject"
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "Mode switch preserves worktree label",
        rc == 0 and "badge:QA (W1)" in stdout and "title:myproject - QA (W1)" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


def test_mode_switch_without_worktree_no_label():
    """Scenario: Mode switch without worktree has no label"""
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
set_agent_identity "QA" "myproject"
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "Mode switch without worktree has no label",
        rc == 0 and "badge:QA" in stdout and "title:myproject - QA" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


# ============================================================
# Sub-Agent Worktree Exclusion Test
# ============================================================

def test_sub_agent_worktrees_no_label():
    """Scenario: Sub-agent worktrees do not get label files

    The label assignment logic in pl-run.sh only writes .purlin_worktree_label
    inside .purlin/worktrees/ directories. Sub-agent worktrees created by the
    Claude Agent tool live under .claude/worktrees/ — a different path.
    This test verifies the launcher only scans .purlin/worktrees/.
    """
    launcher_src = read_file(LAUNCHER_PATH)
    # The label assignment block should reference .purlin/worktrees, not .claude/worktrees
    label_scan = re.search(
        r'for _lf in.*\.purlin/worktrees.*/\.purlin_worktree_label', launcher_src
    )
    no_claude_worktrees = '.claude/worktrees' not in launcher_src.split('# --- Worktree setup ---')[1].split('# --- Set terminal identity')[0] if '# --- Worktree setup ---' in launcher_src else True
    record(
        "Sub-agent worktrees do not get label files",
        label_scan is not None and no_claude_worktrees,
        f"purlin_scan={label_scan is not None}, no_claude_ref={no_claude_worktrees}"
    )


# ============================================================
# Terminal Title Format Tests
# ============================================================

def test_terminal_title_includes_project_and_badge():
    """Scenario: Terminal title includes project and badge"""
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
set_agent_identity "QA (W1)" "myapp"
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "Terminal title includes project and badge",
        rc == 0 and "title:myapp - QA (W1)" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


def test_set_agent_identity_backward_compatible():
    """set_agent_identity without project arg sets title = badge text (backward compat)"""
    script = f"""
source "{IDENTITY_SCRIPT}"
CALLS=""
set_term_title() {{ CALLS="$CALLS title:$1"; }}
set_iterm_badge() {{ CALLS="$CALLS badge:$1"; }}
set_agent_identity "Builder"
echo "$CALLS"
"""
    stdout, _, rc = run_bash(script, env={"TERM_PROGRAM": "iTerm.app"})
    record(
        "set_agent_identity backward compatible (no project)",
        rc == 0 and "title:Builder" in stdout and "badge:Builder" in stdout,
        f"rc={rc}, calls={repr(stdout.strip())}"
    )


def test_launcher_passes_project_name():
    """pl-run.sh passes PROJECT_NAME to set_agent_identity"""
    launcher_src = read_file(LAUNCHER_PATH)
    # Should pass project name as second arg
    has_project_display = '_PROJECT_DISPLAY=' in launcher_src
    has_two_arg_call = 'set_agent_identity "$ROLE_DISPLAY" "$_PROJECT_DISPLAY"' in launcher_src
    record(
        "pl-run.sh passes project name to set_agent_identity",
        has_project_display and has_two_arg_call,
        f"project_display={has_project_display}, two_arg_call={has_two_arg_call}"
    )


def test_no_purlin_prefix_in_badge():
    """Badge never uses 'Purlin:' prefix in pl-run.sh"""
    launcher_src = read_file(LAUNCHER_PATH)
    # Check that no ROLE_DISPLAY or MODE_NAME starts with "Purlin:"
    has_purlin_prefix = re.search(r'(MODE_NAME|ROLE_DISPLAY)="Purlin:', launcher_src)
    record(
        "Badge never uses Purlin: prefix",
        has_purlin_prefix is None,
        f"Found Purlin: prefix in launcher" if has_purlin_prefix else ""
    )


# ============================================================
# Main
# ============================================================

if __name__ == '__main__':
    print("=== Purlin Worktree Identity Tests ===\n")

    print("--- Label Assignment ---")
    test_first_worktree_gets_w1()
    test_second_worktree_gets_w2()
    test_gap_filling_reuses_numbers()

    print("\n--- Badge & Title Format ---")
    test_badge_format_without_worktree()
    test_badge_format_with_worktree()
    test_open_mode_badge_in_worktree()

    print("\n--- Mode Switch ---")
    test_mode_switch_preserves_worktree_label()
    test_mode_switch_without_worktree_no_label()

    print("\n--- Sub-Agent Exclusion ---")
    test_sub_agent_worktrees_no_label()

    print("\n--- Terminal Title ---")
    test_terminal_title_includes_project_and_badge()
    test_set_agent_identity_backward_compatible()
    test_launcher_passes_project_name()
    test_no_purlin_prefix_in_badge()

    # Summary
    print(f"\n=== Results: {results['passed']}/{results['total']} passed ===")

    # Write tests.json
    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'purlin_worktree_identity')
    os.makedirs(tests_dir, exist_ok=True)
    tests_json = {
        "status": "PASS" if results["failed"] == 0 else "FAIL",
        "passed": results["passed"],
        "failed": results["failed"],
        "total": results["total"],
        "test_file": "tests/purlin_worktree_identity/test_worktree_identity.py",
        "details": results["details"]
    }
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump(tests_json, f, indent=2)
        f.write('\n')

    print(f"Tests written to tests/purlin_worktree_identity/tests.json")
    sys.exit(0 if results["failed"] == 0 else 1)
