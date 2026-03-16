#!/usr/bin/env python3
"""Tests for continuous phase builder — exercises all 19 automated scenarios.

Tests validate the launcher script's structure and behavior by:
1. Parsing the script source to verify flag handling and code paths
2. Running the script with a mock `claude` command in isolated temp dirs
3. Verifying orchestration logic (evaluator, retry, worktree, logging)
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
LAUNCHER_PATH = os.path.join(PROJECT_ROOT, 'pl-run-builder.sh')

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


def read_launcher():
    """Read the launcher script source."""
    with open(LAUNCHER_PATH, 'r') as f:
        return f.read()


def make_mock_project(tmpdir, plan_text=None, graph_data=None):
    """Create a minimal project structure for testing.

    Sets up:
    - .purlin/runtime/ and .purlin/cache/ directories
    - Delivery plan and dependency graph (optional)
    - Mock instructions files
    - Mock config resolver
    - Mock claude command that records invocations
    """
    purlin_dir = os.path.join(tmpdir, '.purlin')
    cache_dir = os.path.join(purlin_dir, 'cache')
    runtime_dir = os.path.join(purlin_dir, 'runtime')
    instructions_dir = os.path.join(tmpdir, 'instructions')
    tools_dir = os.path.join(tmpdir, 'tools', 'delivery')
    config_dir = os.path.join(tmpdir, 'tools', 'config')

    for d in [cache_dir, runtime_dir, instructions_dir, tools_dir, config_dir]:
        os.makedirs(d, exist_ok=True)

    # Create minimal instruction files
    for fname in ['HOW_WE_WORK_BASE.md', 'BUILDER_BASE.md']:
        with open(os.path.join(instructions_dir, fname), 'w') as f:
            f.write(f"# {fname}\nTest content.\n")

    # Delivery plan
    if plan_text is not None:
        with open(os.path.join(cache_dir, 'delivery_plan.md'), 'w') as f:
            f.write(plan_text)

    # Dependency graph
    if graph_data is not None:
        with open(os.path.join(cache_dir, 'dependency_graph.json'), 'w') as f:
            json.dump(graph_data, f)

    # Copy phase_analyzer.py
    analyzer_src = os.path.join(SCRIPT_DIR, 'phase_analyzer.py')
    analyzer_dst = os.path.join(tools_dir, 'phase_analyzer.py')
    shutil.copy2(analyzer_src, analyzer_dst)

    # Create mock resolve_config.py that outputs defaults
    with open(os.path.join(config_dir, 'resolve_config.py'), 'w') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('print("AGENT_MODEL=\\"\\"")\n')
        f.write('print("AGENT_EFFORT=\\"\\"")\n')
        f.write('print("AGENT_BYPASS=\\"false\\"")\n')
        f.write('print("AGENT_STARTUP=\\"true\\"")\n')
        f.write('print("AGENT_RECOMMEND=\\"true\\"")\n')

    return tmpdir


def make_mock_claude(tmpdir, behavior="phase_complete", phase_count=1, exit_code=0,
                     eval_responses=None):
    """Create a mock claude command.

    Builder behaviors:
    - phase_complete: outputs "Phase N of M complete"
    - all_complete: deletes delivery plan and outputs success
    - infeasible: outputs INFEASIBLE escalation
    - noop: outputs nothing meaningful

    eval_responses: list of (action, reason) strings for evaluator calls.
    Each evaluator call pops the next response in order.
    Defaults to [("continue", "Phase completed")] if None.
    """
    bin_dir = os.path.join(tmpdir, 'mock_bin')
    os.makedirs(bin_dir, exist_ok=True)

    # Write evaluator response sequence to a file
    eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
    if eval_responses is None:
        eval_responses = [("continue", "Phase completed successfully")]
    with open(eval_seq_file, 'w') as f:
        for action, reason in eval_responses:
            f.write(f"{action}|{reason}\n")

    mock_script = os.path.join(bin_dir, 'claude')
    with open(mock_script, 'w') as f:
        f.write(f'''#!/bin/bash
# Mock claude command — records invocations and produces test output
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

BEHAVIOR="{behavior}"
PHASE_COUNT="{phase_count}"

# Check if this is an evaluator call (has --json-schema)
if echo "$@" | grep -q "json-schema"; then
    # Consume stdin (required for pipe)
    cat > /dev/null

    # Pop the next evaluator response from the sequence file
    SEQ_FILE="{eval_seq_file}"
    COUNTER_FILE="{tmpdir}/.purlin/runtime/eval_counter"
    IDX=0
    [ -f "$COUNTER_FILE" ] && IDX=$(cat "$COUNTER_FILE")
    IDX=$((IDX + 1))
    echo "$IDX" > "$COUNTER_FILE"

    RESPONSE=$(sed -n "${{IDX}}p" "$SEQ_FILE")
    if [ -z "$RESPONSE" ]; then
        # If we've run out of responses, return stop
        echo '{{"action": "stop", "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REASON="${{RESPONSE#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

# Builder invocation — produce output based on behavior
case "$BEHAVIOR" in
    phase_complete)
        echo "Phase 1 of $PHASE_COUNT complete"
        echo "Recommended next step: run QA to verify Phase 1 features."
        ;;
    all_complete)
        if [ -f "$PURLIN_PROJECT_ROOT/.purlin/cache/delivery_plan.md" ]; then
            rm -f "$PURLIN_PROJECT_ROOT/.purlin/cache/delivery_plan.md"
        fi
        echo "All phases complete. Delivery plan deleted."
        ;;
    infeasible)
        echo "INFEASIBLE: Cannot implement feature due to missing dependency."
        ;;
    noop)
        echo "Starting session..."
        ;;
esac

exit {exit_code}
''')
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

    # Also create mock uuidgen
    mock_uuidgen = os.path.join(bin_dir, 'uuidgen')
    with open(mock_uuidgen, 'w') as f:
        f.write('#!/bin/bash\necho "00000000-0000-0000-0000-000000000001"\n')
    os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

    # Create mock git for worktree operations
    mock_git = os.path.join(bin_dir, 'git')
    with open(mock_git, 'w') as f:
        f.write(f'''#!/bin/bash
# Mock git — pass through most commands, handle worktree specially
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"

# Skip -C flag if present
if [ "$1" = "-C" ]; then shift 2; fi

case "$1" in
    worktree)
        case "$2" in
            add)
                # git worktree add -b <branch> <dir> HEAD
                # $3=-b, $4=branch, $5=dir, $6=HEAD
                mkdir -p "$5" 2>/dev/null
                ;;
            remove)
                rm -rf "$3" 2>/dev/null
                ;;
        esac
        ;;
    merge)
        # Succeed by default
        ;;
    branch)
        ;;
    diff)
        ;;
    rev-parse)
        echo "abc1234"
        ;;
esac
exit 0
''')
    os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

    # Create mock md5 for plan hash
    mock_md5 = os.path.join(bin_dir, 'md5')
    with open(mock_md5, 'w') as f:
        f.write('#!/bin/bash\nmd5sum "$2" 2>/dev/null | cut -d" " -f1 || echo "nohash"\n')
    os.chmod(mock_md5, os.stat(mock_md5).st_mode | stat.S_IEXEC)

    return bin_dir


def make_plan(phases):
    """Build a delivery plan markdown.

    phases: list of (number, label, status, [feature_names])
    """
    lines = [
        "# Delivery Plan\n",
        "**Created:** 2026-01-01",
        f"**Total Phases:** {len(phases)}\n",
        "## Summary",
        "Test plan.\n",
    ]
    for num, label, status, feats in phases:
        feat_str = ', '.join(feats) if feats else '--'
        lines.append(f"## Phase {num} -- {label} [{status}]")
        lines.append(f"**Features:** {feat_str}")
        lines.append("**Completion Commit:** --")
        lines.append("**QA Bugs Addressed:** --\n")
    lines.append("## Plan Amendments")
    lines.append("_None._")
    return '\n'.join(lines)


def make_graph(features):
    """Build a minimal dependency graph."""
    return {
        "cycles": [],
        "features": [
            {
                "file": f"features/{name}",
                "label": name,
                "category": "test",
                "prerequisites": prereqs,
            }
            for name, prereqs in features
        ],
        "generated_at": "2026-01-01T00:00:00Z",
    }


def run_launcher(tmpdir, mock_bin, extra_args=None, env_extra=None):
    """Run the launcher script with mock PATH."""
    # Create a modified launcher that uses our test project
    launcher_copy = os.path.join(tmpdir, 'pl-run-builder.sh')
    shutil.copy2(LAUNCHER_PATH, launcher_copy)
    os.chmod(launcher_copy, os.stat(launcher_copy).st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env['PURLIN_PROJECT_ROOT'] = tmpdir
    # Prepend mock bin to PATH so mock claude/git are found first
    env['PATH'] = mock_bin + ':' + env.get('PATH', '')
    if env_extra:
        env.update(env_extra)

    cmd = ['bash', launcher_copy]
    if extra_args:
        cmd.extend(extra_args)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        cwd=tmpdir,
    )
    return proc


def get_invocations(tmpdir):
    """Read the claude invocation log."""
    log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'claude_invocations.log')
    if os.path.exists(log_path):
        with open(log_path) as f:
            return f.read().strip().split('\n')
    return []


# ============================================================
# Scenario: Continuous Flag Accepted
# ============================================================
def test_continuous_flag_accepted():
    """Given --continuous and a delivery plan with PENDING phases,
    the launcher runs the phase analyzer and enters the orchestration loop."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete")

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Should have run the phase analyzer and invoked claude
        invocations = get_invocations(tmpdir)
        has_builder_call = any(
            'Begin Builder session' in inv for inv in invocations
            if 'json-schema' not in inv
        )
        ok = proc.returncode == 0 and has_builder_call
        record("Continuous Flag Accepted", ok,
               f"rc={proc.returncode}, invocations={len(invocations)}, "
               f"stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Default Behavior Without Continuous Flag
# ============================================================
def test_default_behavior():
    """Without --continuous, behavior is identical to the current interactive launcher."""
    source = read_launcher()

    # The script must have a clear branch: if CONTINUOUS is false, use original behavior
    has_default_branch = 'if [ "$CONTINUOUS" = "false" ]' in source
    # The default path must invoke claude without --print (interactive mode)
    has_interactive_call = bool(re.search(
        r'claude.*--append-system-prompt-file.*"Begin Builder session\."',
        source
    ))
    # Must NOT invoke phase analyzer or evaluator in the default path
    # Check that phase_analyzer reference is only in the continuous section
    lines = source.split('\n')
    in_default_section = False
    analyzer_in_default = False
    for line in lines:
        if 'CONTINUOUS" = "false"' in line:
            in_default_section = True
        if in_default_section and 'exit $?' in line:
            in_default_section = False
        if in_default_section and 'phase_analyzer' in line:
            analyzer_in_default = True

    ok = has_default_branch and has_interactive_call and not analyzer_in_default
    record("Default Behavior Without Continuous Flag", ok,
           f"branch={has_default_branch}, interactive={has_interactive_call}, "
           f"analyzer_leak={analyzer_in_default}" if not ok else "")


# ============================================================
# Scenario: Sequential Phase Completion
# ============================================================
def test_sequential_completion():
    """3 sequential phases, evaluator returns continue after each."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
        ])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete", phase_count=3,
                                   eval_responses=[
                                       ("continue", "Phase 1 done"),
                                       ("continue", "Phase 2 done"),
                                       ("stop", "All phases complete successfully"),
                                   ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Check summary reports phases completed
        ok = (
            proc.returncode == 0
            and "Phases completed:" in proc.stderr
        )
        record("Sequential Phase Completion", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Phase Execution
# ============================================================
def test_parallel_execution():
    """Phases 1 and 2 independent -> parallel group; Phase 3 depends on both."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
            ("c.md", ["a.md", "b.md"]),
        ])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete", phase_count=3,
                                   eval_responses=[
                                       ("continue", "Parallel group done"),
                                       ("stop", "All phases complete successfully"),
                                   ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Check that parallel group was detected
        ok = (
            proc.returncode == 0
            and "parallel" in proc.stderr.lower()
        )
        record("Parallel Phase Execution", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Phase Merge Conflict
# ============================================================
def test_parallel_merge_conflict():
    """Parallel phases produce a merge conflict -> stop and report."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # Create mock git that fails on merge
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", "done")])
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
# Skip -C flag if present
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree)
        case "$2" in
            add) mkdir -p "$5" 2>/dev/null ;;
            remove) rm -rf "$3" 2>/dev/null ;;
        esac
        ;;
    merge)
        echo "CONFLICT" >&2
        exit 1
        ;;
    diff)
        echo "conflicting_file.py"
        ;;
    branch) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = (
            proc.returncode != 0
            and "merge conflict" in proc.stderr.lower()
        )
        record("Parallel Phase Merge Conflict", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Evaluator Returns Approve
# ============================================================
def test_evaluator_approve():
    """Builder outputs approval prompt -> evaluator returns approve ->
    launcher resumes the same session."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)

        # Mock claude that first outputs approval prompt, then on resume outputs completion
        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        state_file = os.path.join(tmpdir, '.purlin', 'runtime', 'call_count')
        with open(state_file, 'w') as f:
            f.write('0')

        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

# Evaluator calls — track eval count
EVAL_STATE="{tmpdir}/.purlin/runtime/eval_count"
if echo "$@" | grep -q "json-schema"; then
    INPUT=$(cat)
    ECOUNT=0
    [ -f "$EVAL_STATE" ] && ECOUNT=$(cat "$EVAL_STATE")
    ECOUNT=$((ECOUNT + 1))
    echo "$ECOUNT" > "$EVAL_STATE"

    if [ "$ECOUNT" -eq 1 ]; then
        echo '{{"action": "approve", "reason": "Builder waiting for approval"}}'
    else
        echo '{{"action": "stop", "reason": "All phases complete successfully"}}'
    fi
    exit 0
fi

# Builder calls — track state
STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -eq 1 ]; then
    echo "Ready to go, or would you like to adjust the plan?"
else
    echo "Phase 1 of 1 complete"
fi
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        # Copy uuidgen mock
        mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
        with open(mock_uuidgen, 'w') as f:
            f.write('#!/bin/bash\necho "00000000-0000-0000-0000-000000000001"\n')
        os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

        # Copy mock git
        mock_git = os.path.join(mock_bin_dir, 'git')
        with open(mock_git, 'w') as f:
            f.write('#!/bin/bash\necho "abc1234"\nexit 0\n')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        invocations = get_invocations(tmpdir)
        # Should have a resume call
        has_resume = any('resume' in inv for inv in invocations if 'json-schema' not in inv)

        ok = has_resume
        record("Evaluator Returns Approve", ok,
               f"rc={proc.returncode}, has_resume={has_resume}, "
               f"invocations={invocations}, stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Evaluator Returns Retry
# ============================================================
def test_evaluator_retry():
    """Builder exits with context exhaustion -> evaluator returns retry ->
    launcher starts a new session for the same phase."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)

        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        state_file = os.path.join(tmpdir, '.purlin', 'runtime', 'call_count')
        with open(state_file, 'w') as f:
            f.write('0')

        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

if echo "$@" | grep -q "json-schema"; then
    INPUT=$(cat)
    if echo "$INPUT" | grep -q "context exhaustion"; then
        echo '{{"action": "retry", "reason": "Context exhausted mid-phase"}}'
    elif echo "$INPUT" | grep -q "Phase .* of .* complete"; then
        echo '{{"action": "stop", "reason": "All phases complete successfully"}}'
    else
        echo '{{"action": "stop", "reason": "done"}}'
    fi
    exit 0
fi

STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -le 1 ]; then
    echo "Context limit approaching. Saving checkpoint."
    echo "context exhaustion"
else
    echo "Phase 1 of 1 complete"
fi
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
        with open(mock_uuidgen, 'w') as f:
            f.write('#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n')
        os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

        mock_git = os.path.join(mock_bin_dir, 'git')
        with open(mock_git, 'w') as f:
            f.write('#!/bin/bash\necho "abc1234"\nexit 0\n')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        invocations = get_invocations(tmpdir)
        # Should have multiple builder calls (original + retry)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]
        has_retry = len(builder_calls) >= 2

        ok = has_retry and "Retrying" in proc.stderr
        record("Evaluator Returns Retry", ok,
               f"rc={proc.returncode}, builder_calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Retry Limit Exceeded
# ============================================================
def test_retry_limit_exceeded():
    """Same phase retried 2 times, evaluator returns retry a third time -> exit."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)

        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        # Mock claude that always outputs context exhaustion
        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

if echo "$@" | grep -q "json-schema"; then
    INPUT=$(cat)
    echo '{{"action": "retry", "reason": "Context exhausted mid-phase"}}'
    exit 0
fi

echo "Context limit approaching. Saving checkpoint."
echo "context exhaustion"
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
        with open(mock_uuidgen, 'w') as f:
            f.write('#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n')
        os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

        mock_git = os.path.join(mock_bin_dir, 'git')
        with open(mock_git, 'w') as f:
            f.write('#!/bin/bash\necho "abc1234"\nexit 0\n')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Should have 3 builder calls (original + 2 retries) then stop
        ok = (
            proc.returncode != 0
            and "Retry limit exceeded" in proc.stderr
            and len(builder_calls) == 3
        )
        record("Retry Limit Exceeded", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Evaluator Returns Stop on Error
# ============================================================
def test_evaluator_stop_on_error():
    """Builder outputs INFEASIBLE -> evaluator returns stop -> non-zero exit."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "infeasible",
                                   eval_responses=[
                                       ("stop", "Error requiring human intervention"),
                                   ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = proc.returncode != 0
        record("Evaluator Returns Stop on Error", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: All Phases Complete
# ============================================================
def test_all_phases_complete():
    """Builder deletes delivery plan -> evaluator returns stop with success -> exit 0."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "all_complete",
                                   eval_responses=[
                                       ("stop", "All phases complete successfully"),
                                   ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = (
            proc.returncode == 0
            and "Phases completed:" in proc.stderr
        )
        record("All Phases Complete", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: No Delivery Plan at Launch
# ============================================================
def test_no_delivery_plan():
    """--continuous with no delivery plan -> error, non-zero exit."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create project but NO delivery plan
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_mock_claude(tmpdir, "noop")

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = (
            proc.returncode != 0
            and "delivery plan" in proc.stderr.lower()
        )
        record("No Delivery Plan at Launch", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Evaluator Failure Fallback
# ============================================================
def test_evaluator_failure_fallback():
    """Evaluator invocation fails -> fallback to delivery plan hash check."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)

        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        # Mock claude that fails on evaluator calls but succeeds for builder
        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

if echo "$@" | grep -q "json-schema"; then
    # Evaluator call — fail
    exit 1
fi

# Builder call — modify delivery plan to trigger fallback "continue"
# but since there's only 1 phase, the outer loop will end
echo "Phase 1 of 1 complete"
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
        with open(mock_uuidgen, 'w') as f:
            f.write('#!/bin/bash\necho "00000000-0000-0000-0000-000000000001"\n')
        os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

        mock_git = os.path.join(mock_bin_dir, 'git')
        with open(mock_git, 'w') as f:
            f.write('#!/bin/bash\necho "abc1234"\nexit 0\n')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        ok = "fallback" in proc.stderr.lower()
        record("Evaluator Failure Fallback", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Pass-Through Flags Forwarded
# ============================================================
def test_passthrough_flags():
    """--max-turns and --max-budget-usd forwarded to claude -p invocations."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", "done")])

        proc = run_launcher(tmpdir, mock_bin, [
            '--continuous', '--max-turns', '50', '--max-budget-usd', '10'
        ])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        has_max_turns = any('--max-turns 50' in inv for inv in builder_calls)
        has_max_budget = any('--max-budget-usd 10' in inv for inv in builder_calls)

        ok = has_max_turns and has_max_budget
        record("Pass-Through Flags Forwarded", ok,
               f"max_turns={has_max_turns}, max_budget={has_max_budget}, "
               f"calls={builder_calls}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: System Prompt Overrides Injected
# ============================================================
def test_system_prompt_overrides():
    """In continuous mode, prompt file includes auto-proceed and server overrides."""
    source = read_launcher()

    has_auto_proceed = 'CONTINUOUS PHASE MODE ACTIVE: You are running in non-interactive print mode.' in source
    has_server_override = 'CONTINUOUS PHASE MODE ACTIVE: You have permission to start, stop, and restart' in source

    # Verify overrides are only added when CONTINUOUS is true
    has_conditional = 'if [ "$CONTINUOUS" = "true" ]' in source

    ok = has_auto_proceed and has_server_override and has_conditional
    record("System Prompt Overrides Injected", ok,
           f"auto_proceed={has_auto_proceed}, server={has_server_override}, "
           f"conditional={has_conditional}" if not ok else "")


# ============================================================
# Scenario: Phase-Specific Builder Assignment
# ============================================================
def test_phase_specific_assignment():
    """Parallel Builder receives phase-specific initial message."""
    source = read_launcher()

    # Check that parallel Builders get phase-specific messages
    has_phase_assignment = 'you are assigned to Phase ${PHASE_NUM} ONLY' in source
    has_exclusive = 'Work exclusively on Phase ${PHASE_NUM} features' in source

    ok = has_phase_assignment and has_exclusive
    record("Phase-Specific Builder Assignment", ok,
           f"assignment={has_phase_assignment}, exclusive={has_exclusive}" if not ok else "")


# ============================================================
# Scenario: Logging Per Phase
# ============================================================
def test_logging_per_phase():
    """Each phase's output is written to a per-phase log file."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", "done")])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'continuous_build_phase_1.log')
        log_exists = os.path.exists(log_path)
        log_has_content = False
        if log_exists:
            with open(log_path) as f:
                log_has_content = len(f.read().strip()) > 0

        ok = log_exists and log_has_content
        record("Logging Per Phase", ok,
               f"exists={log_exists}, has_content={log_has_content}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Exit Summary
# ============================================================
def test_exit_summary():
    """Exit summary reports phases completed, groups, parallel groups, duration."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", "done")])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        has_phases = "Phases completed:" in proc.stderr
        has_groups = "Execution groups:" in proc.stderr
        has_retries = "Retries consumed:" in proc.stderr
        has_duration = "Total duration:" in proc.stderr

        ok = has_phases and has_groups and has_retries and has_duration
        record("Exit Summary", ok,
               f"phases={has_phases}, groups={has_groups}, retries={has_retries}, "
               f"duration={has_duration}, stderr={proc.stderr[-500:]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Worktree Cleanup on Error
# ============================================================
def test_worktree_cleanup():
    """On error during parallel group, all worktrees are cleaned up."""
    source = read_launcher()

    # Verify cleanup logic exists in the trap handler
    has_trap_cleanup = 'trap cleanup EXIT' in source
    has_worktree_cleanup = 'worktree remove' in source

    # Verify cleanup after merge failure
    has_post_merge_cleanup = bool(re.search(
        r'MERGE_FAILED.*?worktree remove',
        source,
        re.DOTALL
    ))

    ok = has_trap_cleanup and has_worktree_cleanup and has_post_merge_cleanup
    record("Worktree Cleanup on Error", ok,
           f"trap={has_trap_cleanup}, remove={has_worktree_cleanup}, "
           f"post_merge={has_post_merge_cleanup}" if not ok else "")


# ============================================================
# Scenario: Delivery Plan Updated Centrally
# ============================================================
def test_delivery_plan_central_update():
    """For parallel phases, orchestrator updates delivery plan centrally."""
    source = read_launcher()

    # Check that parallel Builders are told not to modify the plan
    has_no_modify_msg = 'Do not modify the delivery plan' in source

    # Check that the orchestrator has a plan update function
    has_update_function = 'update_plan_phase_status' in source

    ok = has_no_modify_msg and has_update_function
    record("Delivery Plan Updated Centrally", ok,
           f"no_modify={has_no_modify_msg}, update_fn={has_update_function}" if not ok else "")


def write_results():
    """Write tests.json to the correct location."""
    project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if not project_root:
        project_root = PROJECT_ROOT

    results_dir = os.path.join(project_root, 'tests', 'continuous_phase_builder')
    os.makedirs(results_dir, exist_ok=True)

    status = "PASS" if results["failed"] == 0 else "FAIL"
    output = {
        "status": status,
        "passed": results["passed"],
        "failed": results["failed"],
        "total": results["total"],
        "test_file": "tools/delivery/test_continuous_phase_builder.py",
        "details": results["details"],
    }

    results_path = os.path.join(results_dir, 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResults written to {results_path}")
    print(f"Status: {status} ({results['passed']}/{results['total']})")


if __name__ == '__main__':
    print("Running continuous_phase_builder tests...\n")

    test_continuous_flag_accepted()
    test_default_behavior()
    test_sequential_completion()
    test_parallel_execution()
    test_parallel_merge_conflict()
    test_evaluator_approve()
    test_evaluator_retry()
    test_retry_limit_exceeded()
    test_evaluator_stop_on_error()
    test_all_phases_complete()
    test_no_delivery_plan()
    test_evaluator_failure_fallback()
    test_passthrough_flags()
    test_system_prompt_overrides()
    test_phase_specific_assignment()
    test_logging_per_phase()
    test_exit_summary()
    test_worktree_cleanup()
    test_delivery_plan_central_update()

    write_results()
    sys.exit(0 if results["failed"] == 0 else 1)
