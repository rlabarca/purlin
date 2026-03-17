#!/usr/bin/env python3
"""Tests for continuous phase builder — exercises all 54 automated scenarios.

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


def run_launcher(tmpdir, mock_bin, extra_args=None, env_extra=None, stdin_input=None):
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

    kwargs = dict(
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        cwd=tmpdir,
    )
    if stdin_input is not None:
        kwargs['input'] = stdin_input

    proc = subprocess.run(cmd, **kwargs)
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

        # Check summary reports phases completed (new format: "Phases: N/M completed")
        ok = (
            proc.returncode == 0
            and "Phases:" in proc.stderr
            and "completed" in proc.stderr
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
            and "Phases:" in proc.stderr
            and "completed" in proc.stderr
        )
        record("All Phases Complete", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Bootstrap Scenarios (Section 2.15)
# ============================================================

def make_bootstrap_mock_claude(tmpdir, creates_plan=True, exit_code=0,
                               plan_text=None, eval_responses=None):
    """Create a mock claude for bootstrap tests.

    The first non-evaluator call is the bootstrap session.
    If creates_plan=True, the mock creates a delivery plan file.
    Subsequent non-evaluator calls are phase execution calls.
    """
    mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
    os.makedirs(mock_bin_dir, exist_ok=True)

    plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
    if plan_text is None:
        plan_text = make_plan([(1, "A", "PENDING", ["a.md"])])

    eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
    if eval_responses is None:
        eval_responses = [("stop", "All phases complete successfully")]
    with open(eval_seq_file, 'w') as f:
        for action, reason in eval_responses:
            f.write(f"{action}|{reason}\n")

    mock_script = os.path.join(mock_bin_dir, 'claude')
    with open(mock_script, 'w') as f:
        f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

# Evaluator calls
if echo "$@" | grep -q "json-schema"; then
    cat > /dev/null
    SEQ_FILE="{eval_seq_file}"
    COUNTER_FILE="{tmpdir}/.purlin/runtime/eval_counter"
    IDX=0
    [ -f "$COUNTER_FILE" ] && IDX=$(cat "$COUNTER_FILE")
    IDX=$((IDX + 1))
    echo "$IDX" > "$COUNTER_FILE"
    RESPONSE=$(sed -n "${{IDX}}p" "$SEQ_FILE")
    if [ -z "$RESPONSE" ]; then
        echo '{{"action": "stop", "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REASON="${{RESPONSE#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

# Track builder calls
CALL_FILE="{tmpdir}/.purlin/runtime/builder_call_count"
CALL_NUM=0
[ -f "$CALL_FILE" ] && CALL_NUM=$(cat "$CALL_FILE")
CALL_NUM=$((CALL_NUM + 1))
echo "$CALL_NUM" > "$CALL_FILE"

if [ "$CALL_NUM" -eq 1 ]; then
    # Bootstrap call
    CREATES_PLAN="{str(creates_plan).lower()}"
    if [ "$CREATES_PLAN" = "true" ]; then
        cat > "{plan_path}" << 'PLAN_EOF'
{plan_text}
PLAN_EOF
    fi
    echo "Bootstrap session complete."
    exit {exit_code}
fi

# Phase execution calls
echo "Phase complete"
exit 0
''')
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

    mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
    with open(mock_uuidgen, 'w') as f:
        f.write('#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n')
    os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

    mock_git = os.path.join(mock_bin_dir, 'git')
    with open(mock_git, 'w') as f:
        f.write(f'''#!/bin/bash
echo "$@" >> "{tmpdir}/.purlin/runtime/git_invocations.log"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
    os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

    mock_md5 = os.path.join(mock_bin_dir, 'md5')
    with open(mock_md5, 'w') as f:
        f.write('#!/bin/bash\nmd5sum "$2" 2>/dev/null | cut -d" " -f1 || echo "nohash"\n')
    os.chmod(mock_md5, os.stat(mock_md5).st_mode | stat.S_IEXEC)

    return mock_bin_dir


def test_bootstrap_creates_delivery_plan():
    """--continuous with no plan -> bootstrap creates plan, prints summary,
    bootstrap log written."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=True,
            eval_responses=[("stop", "All phases complete successfully")]
        )

        # Default stdin (empty) -> approval defaults to yes
        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        bootstrap_log = os.path.join(tmpdir, '.purlin', 'runtime',
                                     'continuous_build_bootstrap.log')
        log_exists = os.path.exists(bootstrap_log)
        has_summary = "Delivery plan created" in proc.stderr

        ok = log_exists and has_summary
        record("Bootstrap Creates Delivery Plan", ok,
               f"log={log_exists}, summary={has_summary}, "
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_plan_approved():
    """Bootstrap creates plan, user approves -> enters orchestration loop."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=True,
            eval_responses=[("stop", "All phases complete successfully")]
        )

        # Approve the plan via stdin
        proc = run_launcher(tmpdir, mock_bin, ['--continuous'], stdin_input="y\n")

        invocations = get_invocations(tmpdir)
        # Should have bootstrap call + at least one phase execution call
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]
        has_orchestration = "Entering continuous orchestration loop" in proc.stderr

        ok = has_orchestration and len(builder_calls) >= 2
        record("Bootstrap Plan Approved", ok,
               f"orchestration={has_orchestration}, calls={len(builder_calls)}, "
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_plan_declined():
    """Bootstrap creates plan, user declines -> exit 0, plan remains."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(tmpdir, creates_plan=True)

        # Decline the plan
        proc = run_launcher(tmpdir, mock_bin, ['--continuous'], stdin_input="n\n")

        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_exists = os.path.exists(plan_path)
        has_declined_msg = "declined" in proc.stderr.lower()

        ok = (
            proc.returncode == 0
            and plan_exists
            and has_declined_msg
        )
        record("Bootstrap Plan Declined", ok,
               f"rc={proc.returncode}, plan={plan_exists}, "
               f"declined={has_declined_msg}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_completes_work_directly():
    """Bootstrap with no plan needed -> Builder completes work directly,
    no plan created, exit 0."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=False, exit_code=0
        )

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_exists = os.path.exists(plan_path)
        has_direct_msg = "completed all work directly" in proc.stderr.lower()

        ok = (
            proc.returncode == 0
            and not plan_exists
            and has_direct_msg
        )
        record("Bootstrap Completes Work Directly", ok,
               f"rc={proc.returncode}, plan={plan_exists}, "
               f"direct={has_direct_msg}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_failure():
    """Bootstrap exits non-zero without creating plan -> error, non-zero exit."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=False, exit_code=1
        )

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        has_error_msg = "interactive" in proc.stderr.lower()

        ok = (
            proc.returncode != 0
            and has_error_msg
        )
        record("Bootstrap Failure", ok,
               f"rc={proc.returncode}, error={has_error_msg}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_distinct_system_prompt():
    """Bootstrap session uses distinct override text, NOT continuous/server overrides."""
    source = read_launcher()

    has_bootstrap_override = 'BOOTSTRAP MODE ACTIVE' in source
    has_bootstrap_heredoc = "BOOTSTRAP_OVERRIDE" in source

    # Verify bootstrap prompt file is distinct from the main PROMPT_FILE
    has_separate_file = 'BOOTSTRAP_PROMPT_FILE=$(mktemp)' in source

    # Verify bootstrap does NOT use $PROMPT_FILE (which has continuous overrides)
    # Bootstrap should use $BOOTSTRAP_PROMPT_FILE
    has_bootstrap_prompt_ref = '--append-system-prompt-file "$BOOTSTRAP_PROMPT_FILE"' in source

    ok = (has_bootstrap_override and has_bootstrap_heredoc and
          has_separate_file and has_bootstrap_prompt_ref)
    record("Bootstrap Uses Distinct System Prompt Override", ok,
           f"override={has_bootstrap_override}, heredoc={has_bootstrap_heredoc}, "
           f"separate={has_separate_file}, ref={has_bootstrap_prompt_ref}" if not ok else "")


def test_bootstrap_plan_validated_before_approval():
    """After bootstrap creates plan, phase analyzer validates before approval prompt."""
    source = read_launcher()

    # Verify the validation step exists between plan creation check and approval prompt
    # The pattern: check plan exists -> run analyzer -> check result -> prompt
    has_validate_msg = 'Validating' in source
    has_analyzer_call = 'PHASE_ANALYZER' in source

    # More structural: the bootstrap block runs the analyzer after detecting plan exists
    bootstrap_section = source[source.find('Bootstrap session when no delivery plan'):]
    bootstrap_section = bootstrap_section[:bootstrap_section.find('# --- Track initial')]
    has_validate_in_bootstrap = ('VALIDATE_RC' in bootstrap_section and
                                 'PHASE_ANALYZER' in bootstrap_section)

    ok = has_validate_msg and has_analyzer_call and has_validate_in_bootstrap
    record("Bootstrap Plan Validated Before Approval", ok,
           f"validate={has_validate_msg}, analyzer={has_analyzer_call}, "
           f"in_bootstrap={has_validate_in_bootstrap}" if not ok else "")


def test_bootstrap_plan_has_dependency_cycle():
    """Bootstrap creates plan, analyzer detects issues -> prints error, exit 0."""
    tmpdir = tempfile.mkdtemp()
    try:
        # No graph file -> analyzer will fail
        make_mock_project(tmpdir, None, None)
        mock_bin = make_bootstrap_mock_claude(tmpdir, creates_plan=True)

        # Remove the dependency graph so the analyzer fails
        graph_path = os.path.join(tmpdir, '.purlin', 'cache', 'dependency_graph.json')
        if os.path.exists(graph_path):
            os.remove(graph_path)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        has_validation_fail = "validation failed" in proc.stderr.lower()
        has_manual_edit_msg = "manual editing" in proc.stderr.lower()

        ok = (
            proc.returncode == 0
            and has_validation_fail
            and has_manual_edit_msg
        )
        record("Bootstrap Plan Has Dependency Cycle", ok,
               f"rc={proc.returncode}, fail={has_validation_fail}, "
               f"manual={has_manual_edit_msg}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_prefers_conservative_sizing():
    """Bootstrap override text includes sizing bias language."""
    source = read_launcher()

    has_sizing_bias = 'SIZING BIAS' in source
    has_more_phases = 'Prefer MORE phases over fewer' in source
    has_smaller = 'Prefer SMALLER phases over larger' in source
    has_parallelization = 'Maximize parallelization' in source

    ok = has_sizing_bias and has_more_phases and has_smaller and has_parallelization
    record("Bootstrap Prefers Conservative Phase Sizing", ok,
           f"bias={has_sizing_bias}, more={has_more_phases}, "
           f"smaller={has_smaller}, parallel={has_parallelization}" if not ok else "")


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
# Scenario: Exit Summary Lists Per-Phase Details
# ============================================================
def test_exit_summary_per_phase_details():
    """Exit summary includes status line, duration, phase count, per-phase details,
    retries, parallel groups, and log file location."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "Alpha", "PENDING", ["a.md"]),
            (2, "Beta", "PENDING", ["b.md"]),
        ])
        graph = make_graph([("a.md", []), ("b.md", ["a.md"])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete", phase_count=2,
                                   eval_responses=[
                                       ("continue", "Phase 1 done"),
                                       ("continue", "Phase 2 done"),
                                   ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        has_status_line = "Status: completed" in proc.stderr
        has_duration = "Duration:" in proc.stderr
        has_phase_count = "Phases:" in proc.stderr and "completed" in proc.stderr
        has_per_phase = "Phase 1 -- Alpha" in proc.stderr
        has_retries = "Retries:" in proc.stderr
        has_parallel = "Parallel groups:" in proc.stderr
        has_log_files = "Log files:" in proc.stderr
        has_complete_status = "COMPLETE" in proc.stderr
        has_features = "features:" in proc.stderr

        ok = (has_status_line and has_duration and has_phase_count and
              has_per_phase and has_retries and has_parallel and has_log_files and
              has_complete_status and has_features)
        record("Exit Summary Lists Per-Phase Details", ok,
               f"status={has_status_line}, dur={has_duration}, count={has_phase_count}, "
               f"per_phase={has_per_phase}, retries={has_retries}, parallel={has_parallel}, "
               f"logs={has_log_files}, complete={has_complete_status}, feats={has_features}, "
               f"stderr={proc.stderr[-800:]}" if not ok else "")
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

    # Check that parallel Builders are told not to modify the plan (in PARALLEL_OVERRIDE)
    has_no_modify_msg = 'Do NOT modify the delivery plan directly' in source

    # Check that the orchestrator has a plan update function
    has_update_function = 'update_plan_phase_status' in source

    # Check that plan amendment processing exists
    has_amendment_fn = 'apply_plan_amendments' in source

    ok = has_no_modify_msg and has_update_function and has_amendment_fn
    record("Delivery Plan Updated Centrally", ok,
           f"no_modify={has_no_modify_msg}, update_fn={has_update_function}, "
           f"amend_fn={has_amendment_fn}" if not ok else "")


# ============================================================
# Helper: create a mock claude that modifies the delivery plan
# ============================================================
def make_plan_modifying_mock(tmpdir, modifications, eval_responses):
    """Create a mock claude that modifies the delivery plan on specific calls.

    modifications: dict mapping call_number -> callable(plan_path, tmpdir)
        The callable modifies the delivery plan file on that call number.
    eval_responses: list of (action, reason) for evaluator calls.
    """
    mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
    os.makedirs(mock_bin_dir, exist_ok=True)

    # Write eval responses
    eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
    with open(eval_seq_file, 'w') as f:
        for action, reason in eval_responses:
            f.write(f"{action}|{reason}\n")

    # Write modification scripts as separate files
    for call_num, mod_fn in modifications.items():
        mod_script = os.path.join(tmpdir, '.purlin', 'runtime', f'mod_{call_num}.py')
        with open(mod_script, 'w') as f:
            f.write(mod_fn)

    plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')

    mock_script = os.path.join(mock_bin_dir, 'claude')
    mod_nums = ' '.join(str(n) for n in modifications.keys())
    with open(mock_script, 'w') as f:
        f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

# Evaluator calls
if echo "$@" | grep -q "json-schema"; then
    cat > /dev/null
    SEQ_FILE="{eval_seq_file}"
    COUNTER_FILE="{tmpdir}/.purlin/runtime/eval_counter"
    IDX=0
    [ -f "$COUNTER_FILE" ] && IDX=$(cat "$COUNTER_FILE")
    IDX=$((IDX + 1))
    echo "$IDX" > "$COUNTER_FILE"
    RESPONSE=$(sed -n "${{IDX}}p" "$SEQ_FILE")
    if [ -z "$RESPONSE" ]; then
        echo '{{"action": "stop", "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REASON="${{RESPONSE#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

# Builder calls — track call count and run modifications
CALL_FILE="{tmpdir}/.purlin/runtime/builder_call_count"
CALL_NUM=0
[ -f "$CALL_FILE" ] && CALL_NUM=$(cat "$CALL_FILE")
CALL_NUM=$((CALL_NUM + 1))
echo "$CALL_NUM" > "$CALL_FILE"

# Check if there's a modification script for this call
MOD_SCRIPT="{tmpdir}/.purlin/runtime/mod_${{CALL_NUM}}.py"
if [ -f "$MOD_SCRIPT" ]; then
    python3 "$MOD_SCRIPT" "{plan_path}" "{tmpdir}" 2>/dev/null
fi

echo "Phase $CALL_NUM complete"
exit 0
''')
    os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

    # Create mock uuidgen
    mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
    with open(mock_uuidgen, 'w') as f:
        f.write('#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n')
    os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

    # Create mock git
    mock_git = os.path.join(mock_bin_dir, 'git')
    with open(mock_git, 'w') as f:
        f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree)
        case "$2" in
            add) mkdir -p "$5" 2>/dev/null ;;
            remove) rm -rf "$3" 2>/dev/null ;;
        esac
        ;;
    merge) ;;
    branch) ;;
    diff) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
    os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

    # Create mock md5
    mock_md5 = os.path.join(mock_bin_dir, 'md5')
    with open(mock_md5, 'w') as f:
        f.write('#!/bin/bash\nmd5sum "$2" 2>/dev/null | cut -d" " -f1 || echo "nohash"\n')
    os.chmod(mock_md5, os.stat(mock_md5).st_mode | stat.S_IEXEC)

    return mock_bin_dir


# ============================================================
# Scenario: Builder Adds QA Fix Phase Mid-Execution
# ============================================================
def test_builder_adds_qa_fix_phase():
    """Builder completes Phase 1 and adds Phase 4 to the delivery plan.
    Re-analysis picks up the new phase."""
    tmpdir = tempfile.mkdtemp()
    try:
        # All phases sequential via dependency chain: a -> b -> c -> d
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
            ("d.md", ["c.md"]),  # Force Phase 4 after Phase 3
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE and add Phase 4
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 4 -- QA Fixes [PENDING]\\n**Features:** d.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        # Subsequent calls: mark current phase COMPLETE
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done, plan amended"),
                ("continue", "Phase 2 done"),
                ("continue", "Phase 3 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Should have 4 builder calls (3 original + 1 for Phase 4)
        ok = (
            proc.returncode == 0
            and len(builder_calls) >= 4
            and "amended" in proc.stderr.lower()
        )
        record("Builder Adds QA Fix Phase Mid-Execution", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Builder Splits Phase Into Two
# ============================================================
def test_builder_splits_phase():
    """Builder completes Phase 1, removes Phase 2, adds Phases 4 and 5.
    Re-analysis picks up the two new phases."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, remove Phase 2, add Phases 4 and 5
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
content = re.sub(r'(## Phase 2 -- .+?) \\[PENDING\\]', r'\\1 [REMOVED]', content)
new_phases = "\\n## Phase 4 -- B-part1 [PENDING]\\n**Features:** b1.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
new_phases += "\\n## Phase 5 -- B-part2 [PENDING]\\n**Features:** b2.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phases + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        # Update graph with new features
        graph["features"].extend([
            {"file": "features/b1.md", "label": "b1.md", "category": "test", "prerequisites": []},
            {"file": "features/b2.md", "label": "b2.md", "category": "test", "prerequisites": []},
        ])
        graph_path = os.path.join(tmpdir, '.purlin', 'cache', 'dependency_graph.json')
        with open(graph_path, 'w') as f:
            json.dump(graph, f)

        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done, plan split"),
                ("continue", "Phase 4 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Should have 3 builder calls (Phase 1, Phase 4, Phase 5)
        ok = (
            proc.returncode == 0
            and len(builder_calls) >= 3
        )
        record("Builder Splits Phase Into Two", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Builder Removes Remaining Phases
# ============================================================
def test_builder_removes_remaining_phases():
    """Builder completes Phase 1 and removes Phases 2 and 3.
    Re-analysis finds no PENDING phases, exits successfully."""
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

        # On call 1: mark Phase 1 COMPLETE, remove Phases 2 and 3
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
content = re.sub(r'(## Phase 2 -- .+?) \\[PENDING\\]', r'\\1 [REMOVED]', content)
content = re.sub(r'(## Phase 3 -- .+?) \\[PENDING\\]', r'\\1 [REMOVED]', content)
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1},
            eval_responses=[
                ("continue", "Phase 1 done, remaining removed"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Only 1 builder call, then re-analysis finds no PENDING -> exit 0
        ok = (
            proc.returncode == 0
            and len(builder_calls) == 1
            and "No pending phases" in proc.stderr
        )
        record("Builder Removes Remaining Phases", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: New Phase Has Dependencies on Completed Work
# ============================================================
def test_new_phase_depends_on_completed():
    """Builder adds Phase 4 which depends on Phase 1 features (already COMPLETE).
    Phase 4 is not blocked."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("d.md", ["a.md"]),  # d depends on a (Phase 1 features)
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, add Phase 4
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 4 -- D [PENDING]\\n**Features:** d.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Phase 4 depends on completed Phase 1, so not blocked
        ok = (
            proc.returncode == 0
            and len(builder_calls) >= 3  # Phase 1, Phase 2/4 (maybe parallel), rest
        )
        record("New Phase Has Dependencies on Completed Work", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: New Phase Creates New Dependency Chain
# ============================================================
def test_new_phase_creates_dependency_chain():
    """Builder adds Phase 5 which Phase 2 depends on.
    Re-analysis orders Phase 5 before Phase 2."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        # b depends on e, which will be in Phase 5
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["e.md"]),
            ("e.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, add Phase 5 with e.md
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 5 -- E [PENDING]\\n**Features:** e.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 5 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Phase 5 should be ordered before Phase 2
        ok = (
            proc.returncode == 0
            and len(builder_calls) >= 3
        )
        record("New Phase Creates New Dependency Chain", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Group Invalidated by Plan Amendment
# ============================================================
def test_parallel_group_invalidated():
    """During Phase 2, Builder adds Phase 6 which Phase 5 depends on.
    Re-analysis reorders Phase 6 before Phase 5."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Phase 1 sequential (a depends on nothing)
        # Phase 2 sequential (b depends on a)
        # After Phase 2 adds Phase 6, Phase 5 depends on f (Phase 6 feature)
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
            (5, "E", "PENDING", ["e.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
            ("e.md", ["f.md"]),
            ("f.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 2: mark Phase 2 COMPLETE, add Phase 6 with f.md
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mod_2 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
# Mark first PENDING as COMPLETE
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
# Add Phase 6
new_phase = "\\n## Phase 6 -- F [PENDING]\\n**Features:** f.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_generic, 2: mod_2, 3: mod_generic, 4: mod_generic, 5: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done, added Phase 6"),
                ("continue", "Phase done"),
                ("continue", "Phase done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = proc.returncode == 0
        record("Parallel Group Invalidated by Plan Amendment", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Builders Both Request Plan Amendments
# ============================================================
def test_parallel_both_request_amendments():
    """Two parallel Builders each write amendment request files.
    Orchestrator applies both amendments."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (3, "C", "PENDING", ["c.md"]),
            (5, "E", "PENDING", ["e.md"]),
        ])
        graph = make_graph([
            ("c.md", []),
            ("e.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # Create mock claude where parallel builders write amendment files
        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
        with open(eval_seq_file, 'w') as f:
            f.write("continue|Parallel group done\n")
            f.write("stop|All phases complete successfully\n")

        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')

        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

if echo "$@" | grep -q "json-schema"; then
    cat > /dev/null
    SEQ_FILE="{eval_seq_file}"
    COUNTER_FILE="{tmpdir}/.purlin/runtime/eval_counter"
    IDX=0
    [ -f "$COUNTER_FILE" ] && IDX=$(cat "$COUNTER_FILE")
    IDX=$((IDX + 1))
    echo "$IDX" > "$COUNTER_FILE"
    RESPONSE=$(sed -n "${{IDX}}p" "$SEQ_FILE")
    if [ -z "$RESPONSE" ]; then
        echo '{{"action": "stop", "reason": "done"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REASON="${{RESPONSE#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

# Write amendment files based on which phase we're assigned to
if echo "$@" | grep -q "Phase 3"; then
    cat > "{runtime_dir}/plan_amendment_phase_3.json" << 'AMEND'
{{"requesting_phase": 3, "amendments": [{{"action": "add", "phase_number": 7, "label": "QA fixes for Phase 3", "features": ["fix3.md"], "reason": "B2 failures"}}]}}
AMEND
elif echo "$@" | grep -q "Phase 5"; then
    cat > "{runtime_dir}/plan_amendment_phase_5.json" << 'AMEND'
{{"requesting_phase": 5, "amendments": [{{"action": "add", "phase_number": 8, "label": "QA fixes for Phase 5", "features": ["fix5.md"], "reason": "B2 failures"}}]}}
AMEND
fi

echo "Phase complete"
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        mock_uuidgen = os.path.join(mock_bin_dir, 'uuidgen')
        with open(mock_uuidgen, 'w') as f:
            f.write('#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n')
        os.chmod(mock_uuidgen, os.stat(mock_uuidgen).st_mode | stat.S_IEXEC)

        mock_git = os.path.join(mock_bin_dir, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree)
        case "$2" in
            add) mkdir -p "$5" 2>/dev/null ;;
            remove) rm -rf "$3" 2>/dev/null ;;
        esac
        ;;
    merge) ;;
    branch) ;;
    diff) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        mock_md5 = os.path.join(mock_bin_dir, 'md5')
        with open(mock_md5, 'w') as f:
            f.write('#!/bin/bash\nmd5sum "$2" 2>/dev/null | cut -d" " -f1 || echo "nohash"\n')
        os.chmod(mock_md5, os.stat(mock_md5).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        # Check that amendments were applied to the delivery plan
        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_content = ""
        if os.path.exists(plan_path):
            with open(plan_path) as f:
                plan_content = f.read()

        has_phase_7 = 'Phase 7' in plan_content
        has_phase_8 = 'Phase 8' in plan_content

        ok = has_phase_7 and has_phase_8
        record("Parallel Builders Both Request Plan Amendments", ok,
               f"phase7={has_phase_7}, phase8={has_phase_8}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Builder Amendment Requests Use Structured Files
# ============================================================
def test_parallel_amendment_structured_files():
    """Parallel Builders write JSON amendment files, not modify plan directly.
    Verified via launcher source code structure."""
    source = read_launcher()

    # Check for amendment file processing
    has_amendment_fn = 'apply_plan_amendments' in source
    has_amendment_file_pattern = 'plan_amendment_phase_' in source
    has_json_parsing = 'json.load' in source and 'amendments' in source

    # Check parallel prompt tells Builders about amendment files
    has_parallel_override = 'plan_amendment_phase_<N>.json' in source

    ok = has_amendment_fn and has_amendment_file_pattern and has_json_parsing and has_parallel_override
    record("Parallel Builder Amendment Requests Use Structured Files", ok,
           f"fn={has_amendment_fn}, pattern={has_amendment_file_pattern}, "
           f"json={has_json_parsing}, override={has_parallel_override}" if not ok else "")


# ============================================================
# Scenario: Phase Count Changes Reflected in Summary
# ============================================================
def test_phase_count_changes_in_summary():
    """Starting with 3 PENDING phases, Builder adds 2 more.
    Exit summary reports all phases completed and notes amendment."""
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
            ("d.md", []),
            ("e.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, add Phases 4 and 5
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phases = "\\n## Phase 4 -- D [PENDING]\\n**Features:** d.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
new_phases += "\\n## Phase 5 -- E [PENDING]\\n**Features:** e.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phases + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic, 5: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done"),
                ("continue", "Phase 3 done"),
                ("continue", "Phase 4 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Summary should mention amendment and show phase count
        has_amended = "amended" in proc.stderr.lower()
        has_phases = "Phases:" in proc.stderr and "completed" in proc.stderr

        ok = (
            proc.returncode == 0
            and has_phases
            and has_amended
        )
        record("Phase Count Changes Reflected in Summary", ok,
               f"rc={proc.returncode}, amended={has_amended}, phases={has_phases}, "
               f"stderr={proc.stderr[-500:]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Re-Analysis After Retry
# ============================================================
def test_reanalysis_after_retry():
    """Phase fails, evaluator returns retry, Builder amends plan during retry.
    After retry completes with continue, re-analysis picks up amendments."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("d.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # Call 1: fail (no plan change)
        # Call 2 (retry): mark Phase 1 COMPLETE, add Phase 4
        mod_2 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 4 -- D [PENDING]\\n**Features:** d.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={2: mod_2, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("retry", "Context exhausted"),
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Should have: call 1 (fail), call 2 (retry + amend), call 3 (Phase 2 or 4), call 4
        ok = (
            proc.returncode == 0
            and "Retrying" in proc.stderr
            and len(builder_calls) >= 4
        )
        record("Re-Analysis After Retry", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Builder Removes Some Phases But Not All
# ============================================================
def test_builder_removes_some_phases():
    """Builder completes Phase 1 and removes Phase 3 (not all).
    Re-analysis returns Phases 2 and 4 only."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
            (4, "D", "PENDING", ["d.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
            ("d.md", ["b.md"]),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, remove Phase 3
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
content = re.sub(r'(## Phase 3 -- .+?) \\[PENDING\\]', r'\\1 [REMOVED]', content)
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done"),
                ("stop", "All phases complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Phase 3 removed, so only 3 builder calls (Phase 1, 2, 4)
        ok = (
            proc.returncode == 0
            and len(builder_calls) == 3
        )
        record("Builder Removes Some Phases But Not All", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Non-Contiguous Phase Numbers After Amendment
# ============================================================
def test_non_contiguous_phase_numbers():
    """Builder adds Phase 7 (skipping 4-6). Analyzer handles non-contiguous numbering."""
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
            ("g.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, add Phase 7 (skip 4-6)
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 7 -- G [PENDING]\\n**Features:** g.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase done"),
                ("continue", "Phase done"),
                ("stop", "All complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        ok = proc.returncode == 0
        record("Non-Contiguous Phase Numbers After Amendment", ok,
               f"rc={proc.returncode}, stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Amendment Files Cleaned Up After Application
# ============================================================
def test_amendment_files_cleaned_up():
    """After parallel builders write amendment files, orchestrator
    applies them and deletes the files."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (3, "C", "PENDING", ["c.md"]),
            (5, "E", "PENDING", ["e.md"]),
        ])
        graph = make_graph([
            ("c.md", []),
            ("e.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
        os.makedirs(mock_bin_dir, exist_ok=True)

        eval_seq_file = os.path.join(runtime_dir, 'eval_responses')
        with open(eval_seq_file, 'w') as f:
            f.write("continue|Parallel done\n")
            f.write("stop|All complete successfully\n")

        mock_script = os.path.join(mock_bin_dir, 'claude')
        with open(mock_script, 'w') as f:
            f.write(f'''#!/bin/bash
INVOCATION_LOG="{tmpdir}/.purlin/runtime/claude_invocations.log"
echo "$@" >> "$INVOCATION_LOG"

if echo "$@" | grep -q "json-schema"; then
    cat > /dev/null
    COUNTER_FILE="{tmpdir}/.purlin/runtime/eval_counter"
    IDX=0
    [ -f "$COUNTER_FILE" ] && IDX=$(cat "$COUNTER_FILE")
    IDX=$((IDX + 1))
    echo "$IDX" > "$COUNTER_FILE"
    RESPONSE=$(sed -n "${{IDX}}p" "{eval_seq_file}")
    if [ -z "$RESPONSE" ]; then
        echo '{{"action": "stop", "reason": "done"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REASON="${{RESPONSE#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

if echo "$@" | grep -q "Phase 3"; then
    cat > "{runtime_dir}/plan_amendment_phase_3.json" << 'AMEND'
{{"requesting_phase": 3, "amendments": [{{"action": "add", "phase_number": 7, "label": "Fix3", "features": ["f3.md"], "reason": "test"}}]}}
AMEND
elif echo "$@" | grep -q "Phase 5"; then
    cat > "{runtime_dir}/plan_amendment_phase_5.json" << 'AMEND'
{{"requesting_phase": 5, "amendments": [{{"action": "add", "phase_number": 8, "label": "Fix5", "features": ["f5.md"], "reason": "test"}}]}}
AMEND
fi
echo "Phase complete"
exit 0
''')
        os.chmod(mock_script, os.stat(mock_script).st_mode | stat.S_IEXEC)

        for name in ['uuidgen', 'git', 'md5']:
            mock = os.path.join(mock_bin_dir, name)
            if name == 'uuidgen':
                content = '#!/bin/bash\necho "00000000-0000-0000-0000-$(date +%s%N)"\n'
            elif name == 'git':
                content = f'''#!/bin/bash
echo "$@" >> "{tmpdir}/.purlin/runtime/git_invocations.log"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
'''
            else:
                content = '#!/bin/bash\nmd5sum "$2" 2>/dev/null | cut -d" " -f1 || echo "nohash"\n'
            with open(mock, 'w') as f:
                f.write(content)
            os.chmod(mock, os.stat(mock).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin_dir, ['--continuous'])

        # Check that amendment files were deleted
        amend_3 = os.path.join(runtime_dir, 'plan_amendment_phase_3.json')
        amend_5 = os.path.join(runtime_dir, 'plan_amendment_phase_5.json')
        files_cleaned = not os.path.exists(amend_3) and not os.path.exists(amend_5)

        ok = files_cleaned
        record("Amendment Files Cleaned Up After Application", ok,
               f"amend_3_exists={os.path.exists(amend_3)}, "
               f"amend_5_exists={os.path.exists(amend_5)}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Sequential Builder Modifies Delivery Plan Directly
# ============================================================
def test_sequential_builder_modifies_plan_directly():
    """Sequential Builder modifies delivery plan directly (no amendment files).
    Re-analysis picks up the new phase."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("f.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, add Phase 6 directly in plan
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
new_phase = "\\n## Phase 6 -- F [PENDING]\\n**Features:** f.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("continue", "Phase 2 done"),
                ("stop", "All complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # No amendment files should exist (sequential modifies directly)
        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')
        has_amend_files = any(
            f.startswith('plan_amendment_phase_') for f in os.listdir(runtime_dir)
            if os.path.isfile(os.path.join(runtime_dir, f))
        )

        # Should have 3 builder calls (Phase 1, 2, 6)
        ok = (
            proc.returncode == 0
            and len(builder_calls) >= 3
            and not has_amend_files
            and "amended" in proc.stderr.lower()
        )
        record("Sequential Builder Modifies Delivery Plan Directly", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"amend_files={has_amend_files}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Removed Phase Had Dependents
# ============================================================
def test_removed_phase_had_dependents():
    """Builder removes Phase 2 which Phase 3 depended on.
    Phase 3's dependency on the removed phase no longer blocks it."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
            (3, "C", "PENDING", ["c.md"]),
        ])
        # c depends on b (Phase 2 feature)
        graph = make_graph([
            ("a.md", []),
            ("b.md", ["a.md"]),
            ("c.md", ["b.md"]),
        ])
        make_mock_project(tmpdir, plan, graph)

        # On call 1: mark Phase 1 COMPLETE, remove Phase 2
        mod_1 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
content = re.sub(r'(## Phase 1 -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
content = re.sub(r'(## Phase 2 -- .+?) \\[PENDING\\]', r'\\1 [REMOVED]', content)
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mod_generic = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
pending = re.findall(r'## Phase (\\d+) -- .+? \\[PENDING\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[PENDING\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic},
            eval_responses=[
                ("continue", "Phase 1 done"),
                ("stop", "All complete successfully"),
            ])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        invocations = get_invocations(tmpdir)
        builder_calls = [inv for inv in invocations if 'json-schema' not in inv]

        # Phase 2 removed, Phase 3 should still execute (dependency removed)
        # Only 2 builder calls: Phase 1, Phase 3
        ok = (
            proc.returncode == 0
            and len(builder_calls) == 2
        )
        record("Removed Phase Had Dependents", ok,
               f"rc={proc.returncode}, calls={len(builder_calls)}, "
               f"stderr={proc.stderr[:500]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Builder Output Visibility (Section 2.16) (6)
# ============================================================

def test_sequential_phase_output_streamed():
    """Sequential phase output is streamed to terminal via tee AND written to log file.
    Verifies that sequential execution uses '| tee' (not just > redirect)."""
    source = read_launcher()

    # Find the sequential execution section (after "SEQUENTIAL EXECUTION" comment)
    seq_section_start = source.find('# SEQUENTIAL EXECUTION')
    assert seq_section_start != -1, "Could not find SEQUENTIAL EXECUTION section"
    seq_section = source[seq_section_start:]
    # Limit to the sequential block (before the closing 'fi' of the parallel/sequential branch)
    seq_section = seq_section[:seq_section.find('\n    fi\ndone')]

    # Check that the run/retry path uses tee (not just > redirect)
    has_tee_run = bool(re.search(r'tee "\$LOG_FILE"', seq_section))

    # Also verify the log file is written (tee writes to both stdout and file)
    # Verify via an integration test
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
        log_content = ""
        if log_exists:
            with open(log_path) as f:
                log_content = f.read()

        # With tee, output goes to both stdout and log file
        # stdout should have the builder output (streamed via tee)
        stdout_has_output = "Phase 1 of" in proc.stdout
        log_has_output = "Phase 1 of" in log_content
        # Log and stdout should match
        log_matches_stdout = log_content.strip() == proc.stdout.strip() if log_content else False

        ok = has_tee_run and log_exists and stdout_has_output and log_has_output and log_matches_stdout
        record("Sequential Phase Output Streamed to Terminal", ok,
               f"tee_in_source={has_tee_run}, log={log_exists}, "
               f"stdout_output={stdout_has_output}, log_output={log_has_output}, "
               f"content_match={log_matches_stdout}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_bootstrap_output_streamed():
    """Bootstrap output is streamed to terminal via tee AND written to bootstrap log."""
    source = read_launcher()

    # Verify bootstrap uses tee for output streaming
    bootstrap_section_start = source.find('# --- Bootstrap session')
    assert bootstrap_section_start != -1, "Could not find bootstrap section"
    bootstrap_section = source[bootstrap_section_start:]
    bootstrap_section = bootstrap_section[:bootstrap_section.find('# --- Track initial')]

    has_tee_bootstrap = bool(re.search(r'tee "\$BOOTSTRAP_LOG"', bootstrap_section))
    has_pipestatus = 'PIPESTATUS' in bootstrap_section

    # Integration test
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=True,
            eval_responses=[("stop", "All phases complete successfully")]
        )

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        bootstrap_log = os.path.join(tmpdir, '.purlin', 'runtime',
                                     'continuous_build_bootstrap.log')
        log_exists = os.path.exists(bootstrap_log)
        log_content = ""
        if log_exists:
            with open(bootstrap_log) as f:
                log_content = f.read()

        # Bootstrap output should be in both stdout (streamed) and log file
        stdout_has_output = "Bootstrap session complete" in proc.stdout
        log_has_output = "Bootstrap session complete" in log_content

        ok = has_tee_bootstrap and has_pipestatus and log_exists and stdout_has_output and log_has_output
        record("Bootstrap Output Streamed to Terminal", ok,
               f"tee={has_tee_bootstrap}, pipestatus={has_pipestatus}, "
               f"log={log_exists}, stdout={stdout_has_output}, "
               f"log_output={log_has_output}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_parallel_heartbeat_during_execution():
    """Parallel group has a background heartbeat printing status to stderr every 15 seconds."""
    source = read_launcher()

    # Find the parallel execution section
    parallel_section_start = source.find('# PARALLEL EXECUTION')
    assert parallel_section_start != -1, "Could not find PARALLEL EXECUTION section"
    parallel_section = source[parallel_section_start:]
    # Limit scope
    parallel_section = parallel_section[:parallel_section.find('\n    else\n')]

    # Verify heartbeat process is started
    has_heartbeat_loop = 'sleep 15' in parallel_section
    has_heartbeat_output = 'Parallel group (' in parallel_section
    has_stderr_output = '>&2' in parallel_section
    has_log_size = 'wc -c' in parallel_section
    has_running_status = '(running,' in parallel_section
    has_done_status = '(done,' in parallel_section
    has_timestamp = 'date +%H:%M:%S' in parallel_section
    has_heartbeat_bg = 'HEARTBEAT_PID=$!' in parallel_section

    ok = (has_heartbeat_loop and has_heartbeat_output and has_stderr_output and
          has_log_size and has_running_status and has_done_status and
          has_timestamp and has_heartbeat_bg)
    record("Parallel Phase Heartbeat During Execution", ok,
           f"loop={has_heartbeat_loop}, output={has_heartbeat_output}, "
           f"stderr={has_stderr_output}, size={has_log_size}, "
           f"running={has_running_status}, done={has_done_status}, "
           f"timestamp={has_timestamp}, bg={has_heartbeat_bg}" if not ok else "")


def test_parallel_output_not_streamed():
    """Parallel Builder output stays in log files only — not streamed to terminal."""
    source = read_launcher()

    # Find the parallel builder invocation
    parallel_section_start = source.find('# PARALLEL EXECUTION')
    assert parallel_section_start != -1, "Could not find PARALLEL EXECUTION section"
    parallel_section = source[parallel_section_start:]
    parallel_section = parallel_section[:parallel_section.find('\n    else\n')]

    # The parallel claude call should use > redirect (NOT tee)
    # The invocation spans multiple lines with \ continuations, so use DOTALL
    has_redirect_only = bool(re.search(
        r'claude --print.*?> "\$LOG_FILE" 2>&1',
        parallel_section,
        re.DOTALL
    ))
    # Should NOT have tee in the parallel builder invocation subshell
    # Extract the subshell block (between '(' and ') &')
    subshell_start = parallel_section.find('(\n                cd "$WT_DIR"')
    subshell_end = parallel_section.find(') &', subshell_start) if subshell_start >= 0 else -1
    builder_subshell = parallel_section[subshell_start:subshell_end] if subshell_start >= 0 else ""
    has_no_tee_for_builder = 'tee' not in builder_subshell

    # Integration: verify parallel output does NOT appear on stdout
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "A", "PENDING", ["a.md"]),
            (2, "B", "PENDING", ["b.md"]),
        ])
        graph = make_graph([("a.md", []), ("b.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete", phase_count=2,
                                   eval_responses=[("continue", "Parallel group done")])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Parallel builder output should NOT be in stdout
        stdout_clean = "Phase 1 of" not in proc.stdout

        ok = has_redirect_only and has_no_tee_for_builder and stdout_clean
        record("Parallel Phase Output Not Streamed", ok,
               f"redirect={has_redirect_only}, no_tee={has_no_tee_for_builder}, "
               f"stdout_clean={stdout_clean}, stdout={proc.stdout[:200]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_heartbeat_stops_after_parallel_complete():
    """Heartbeat process is terminated immediately after all parallel Builders complete,
    before worktree merge begins."""
    source = read_launcher()

    # Find the parallel execution section
    parallel_section_start = source.find('# PARALLEL EXECUTION')
    assert parallel_section_start != -1, "Could not find PARALLEL EXECUTION section"
    parallel_section = source[parallel_section_start:]
    parallel_section = parallel_section[:parallel_section.find('\n    else\n')]

    # Verify heartbeat kill is after wait and before merge
    wait_pos = parallel_section.find('# Wait for all parallel builders')
    heartbeat_kill_pos = parallel_section.find('# Terminate heartbeat before merge')
    merge_pos = parallel_section.find('# Merge each worktree branch')

    has_kill_after_wait = wait_pos < heartbeat_kill_pos if (wait_pos >= 0 and heartbeat_kill_pos >= 0) else False
    has_kill_before_merge = heartbeat_kill_pos < merge_pos if (heartbeat_kill_pos >= 0 and merge_pos >= 0) else False

    # Verify the kill command targets the heartbeat PID
    has_kill_cmd = 'kill "$HEARTBEAT_PID"' in parallel_section
    # Verify it waits for the heartbeat to actually terminate
    has_wait_heartbeat = 'wait "$HEARTBEAT_PID"' in parallel_section

    # Also verify cleanup function kills heartbeat on unexpected exit
    cleanup_section = source[source.find('cleanup()'):source.find('trap cleanup')]
    has_cleanup_kill = 'HEARTBEAT_PID' in cleanup_section

    ok = (has_kill_after_wait and has_kill_before_merge and
          has_kill_cmd and has_wait_heartbeat and has_cleanup_kill)
    record("Heartbeat Stops After Parallel Group Completes", ok,
           f"after_wait={has_kill_after_wait}, before_merge={has_kill_before_merge}, "
           f"kill_cmd={has_kill_cmd}, wait_hb={has_wait_heartbeat}, "
           f"cleanup={has_cleanup_kill}" if not ok else "")


def test_resume_session_output_streamed_and_appended():
    """Resume session output is streamed via tee -a to append to existing log file."""
    source = read_launcher()

    # Find the sequential execution section
    seq_section_start = source.find('# SEQUENTIAL EXECUTION')
    assert seq_section_start != -1, "Could not find SEQUENTIAL EXECUTION section"
    seq_section = source[seq_section_start:]
    seq_section = seq_section[:seq_section.find('\n    fi\ndone')]

    # The resume path should use tee -a (append mode)
    has_tee_append = bool(re.search(r'tee -a "\$LOG_FILE"', seq_section))

    # Integration test: verify both initial and resumed output in log
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)

        # Custom mock: first call outputs approval prompt, resume outputs completion
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

STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -eq 1 ]; then
    echo "INITIAL_RUN_OUTPUT"
    echo "Ready to go, or would you like to adjust the plan?"
else
    echo "RESUMED_RUN_OUTPUT"
    echo "Phase 1 of 1 complete"
fi
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

        log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'continuous_build_phase_1.log')
        log_content = ""
        if os.path.exists(log_path):
            with open(log_path) as f:
                log_content = f.read()

        # Log should contain both initial and resumed output (tee -a appends)
        has_initial = "INITIAL_RUN_OUTPUT" in log_content
        has_resumed = "RESUMED_RUN_OUTPUT" in log_content
        # stdout should have both outputs (streamed via tee)
        stdout_has_initial = "INITIAL_RUN_OUTPUT" in proc.stdout
        stdout_has_resumed = "RESUMED_RUN_OUTPUT" in proc.stdout

        ok = (has_tee_append and has_initial and has_resumed and
              stdout_has_initial and stdout_has_resumed)
        record("Resume Session Output Streamed and Appended", ok,
               f"tee_append={has_tee_append}, log_initial={has_initial}, "
               f"log_resumed={has_resumed}, stdout_initial={stdout_has_initial}, "
               f"stdout_resumed={stdout_has_resumed}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Enhanced Heartbeat & Graceful Stop (Section 2.16) (7)
# ============================================================

def test_heartbeat_overwrites_previous_output():
    """Heartbeat uses ANSI cursor-up and clear-to-end for in-place overwrite when TTY."""
    source = read_launcher()

    parallel_start = source.find('# Start enhanced heartbeat')
    assert parallel_start != -1, "Could not find enhanced heartbeat section"
    heartbeat_section = source[parallel_start:source.find('HEARTBEAT_PID=$!', parallel_start) + 20]

    # Verify ANSI cursor-up sequence
    has_cursor_up = '\\033[%dA' in heartbeat_section
    # Verify clear-to-end sequence
    has_clear = '\\033[J' in heartbeat_section
    # Verify previous line count tracking
    has_prev_lines = 'PREV_LINES=' in heartbeat_section
    # Verify TTY check gates ANSI usage
    has_tty_check = '[ -t 2 ]' in heartbeat_section

    ok = has_cursor_up and has_clear and has_prev_lines and has_tty_check
    record("Heartbeat Overwrites Previous Output In Place", ok,
           f"cursor_up={has_cursor_up}, clear={has_clear}, prev_lines={has_prev_lines}, "
           f"tty_check={has_tty_check}" if not ok else "")


def test_heartbeat_falls_back_plain_output():
    """Heartbeat uses single-line append-only output without ANSI when not TTY."""
    source = read_launcher()

    parallel_start = source.find('# Start enhanced heartbeat')
    assert parallel_start != -1
    heartbeat_section = source[parallel_start:source.find('HEARTBEAT_PID=$!', parallel_start) + 20]

    # Verify non-TTY fallback path exists
    has_non_tty_branch = 'else' in heartbeat_section
    # Non-TTY path uses compact single-line format
    has_compact_parts = 'COMPACT_PARTS' in heartbeat_section
    # Non-TTY path does not use ANSI in the else branch
    # Find the else branch after TTY check
    else_idx = heartbeat_section.rfind('else')
    else_block = heartbeat_section[else_idx:] if else_idx >= 0 else ""
    has_no_ansi_in_else = '\\033[' not in else_block.split('done')[0] if 'done' in else_block else True

    ok = has_non_tty_branch and has_compact_parts and has_no_ansi_in_else
    record("Heartbeat Falls Back to Plain Output When Not a TTY", ok,
           f"non_tty={has_non_tty_branch}, compact={has_compact_parts}, "
           f"no_ansi={has_no_ansi_in_else}" if not ok else "")


def test_heartbeat_shows_current_activity():
    """Heartbeat extracts current activity from log file tail for running phases."""
    source = read_launcher()

    # Verify extract_activity function exists
    has_extract_fn = 'extract_activity()' in source
    # Verify it reads log tail
    has_tail = 'tail -20' in source
    # Verify it detects file editing
    has_editing = 'editing' in source
    # Verify activity is called from heartbeat
    heartbeat_start = source.find('# Start enhanced heartbeat')
    heartbeat_section = source[heartbeat_start:source.find('HEARTBEAT_PID=$!', heartbeat_start) + 20]
    has_activity_call = 'extract_activity' in heartbeat_section
    # Verify truncation to ~50 chars
    has_truncation = '%.50s' in source

    ok = has_extract_fn and has_tail and has_editing and has_activity_call and has_truncation
    record("Heartbeat Shows Current Builder Activity", ok,
           f"fn={has_extract_fn}, tail={has_tail}, editing={has_editing}, "
           f"call={has_activity_call}, trunc={has_truncation}" if not ok else "")


def test_heartbeat_warns_empty_log():
    """Heartbeat shows red warning for completed phases with 0K log size."""
    source = read_launcher()

    heartbeat_start = source.find('# Start enhanced heartbeat')
    assert heartbeat_start != -1
    heartbeat_section = source[heartbeat_start:source.find('HEARTBEAT_PID=$!', heartbeat_start) + 20]

    # Verify 0K check exists
    has_zero_k_check = '"$FSIZE" = "0K"' in heartbeat_section
    # Verify red color for 0K (ANSI red: \033[31m)
    has_red_color = '\\033[31m' in heartbeat_section
    # Verify green color for normal done (ANSI green: \033[32m)
    has_green_color = '\\033[32m' in heartbeat_section
    # Verify yellow for running (ANSI yellow: \033[33m)
    has_yellow_color = '\\033[33m' in heartbeat_section

    ok = has_zero_k_check and has_red_color and has_green_color and has_yellow_color
    record("Heartbeat Warns on Empty Log at Phase Completion", ok,
           f"zero_k={has_zero_k_check}, red={has_red_color}, "
           f"green={has_green_color}, yellow={has_yellow_color}" if not ok else "")


def test_graceful_stop_on_sigint():
    """SIGINT trap sets stop flag, kills builders and heartbeat, exits non-zero."""
    source = read_launcher()

    # Verify graceful_stop function exists
    has_handler = 'graceful_stop()' in source
    # Verify it sets STOP_REQUESTED
    has_stop_flag = 'STOP_REQUESTED=true' in source
    # Verify trap is set
    has_trap = 'trap graceful_stop INT' in source
    # Verify it kills parallel builder PIDs
    has_kill_pids = 'kill "$pid"' in source
    # Verify it kills heartbeat
    handler_start = source.find('graceful_stop() {')
    handler_end = source.find('\ntrap graceful_stop INT')
    handler_body = source[handler_start:handler_end] if handler_start >= 0 else ""
    has_kill_heartbeat = 'HEARTBEAT_PID' in handler_body
    # Verify trap reset for second SIGINT
    has_trap_reset = 'trap - INT' in handler_body
    # Verify STOP_REQUESTED check in loop causes break
    has_stop_check = '[ "$STOP_REQUESTED" = "true" ]' in source
    # Verify interrupted phases are recorded
    has_interrupted = '"INTERRUPTED"' in source

    ok = (has_handler and has_stop_flag and has_trap and has_kill_pids and
          has_kill_heartbeat and has_trap_reset and has_stop_check and has_interrupted)
    record("Graceful Stop on SIGINT", ok,
           f"handler={has_handler}, flag={has_stop_flag}, trap={has_trap}, "
           f"kill_pids={has_kill_pids}, kill_hb={has_kill_heartbeat}, "
           f"reset={has_trap_reset}, check={has_stop_check}, "
           f"interrupted={has_interrupted}" if not ok else "")


def test_second_sigint_forces_exit():
    """After first SIGINT, trap resets to default so second SIGINT terminates immediately."""
    source = read_launcher()

    # Find the graceful_stop handler
    handler_start = source.find('graceful_stop() {')
    assert handler_start != -1, "Could not find graceful_stop handler"
    # Find the closing brace of the function
    handler_section = source[handler_start:]
    brace_count = 0
    handler_end = handler_start
    for i, ch in enumerate(handler_section):
        if ch == '{':
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0:
                handler_end = i
                break
    handler_body = handler_section[:handler_end + 1]

    # Verify trap - INT is inside the handler (resets to default)
    has_trap_reset_in_handler = 'trap - INT' in handler_body
    # Verify STOP_REQUESTED is set (first action)
    has_stop_flag = 'STOP_REQUESTED=true' in handler_body
    # Verify the exit summary checks STOP_REQUESTED for "stopped" status
    has_stopped_status = 'stopped (user interrupt)' in source

    ok = has_trap_reset_in_handler and has_stop_flag and has_stopped_status
    record("Second SIGINT Forces Immediate Exit", ok,
           f"reset_in_handler={has_trap_reset_in_handler}, "
           f"stop_flag={has_stop_flag}, "
           f"stopped_status={has_stopped_status}" if not ok else "")


def test_post_run_status_refresh():
    """After exit summary, launcher runs tools/cdd/status.sh."""
    source = read_launcher()

    # Find exit summary section
    summary_start = source.find('# Exit Summary (Section 2.16)')
    assert summary_start != -1, "Could not find exit summary section"
    post_summary = source[summary_start:]

    # Verify CDD_STATUS variable is defined
    has_cdd_var = 'CDD_STATUS=' in source
    # Verify status.sh is invoked after the summary
    has_status_call = 'bash "$CDD_STATUS"' in post_summary
    # Verify it checks for file existence first
    has_file_check = '[ -f "$CDD_STATUS" ]' in post_summary
    # Verify it runs after the summary banner
    summary_end_pos = post_summary.find('================================')
    status_call_pos = post_summary.find('bash "$CDD_STATUS"')
    has_after_summary = (summary_end_pos >= 0 and status_call_pos >= 0 and
                        status_call_pos > summary_end_pos)

    ok = has_cdd_var and has_status_call and has_file_check and has_after_summary
    record("Post-Run Status Refresh", ok,
           f"var={has_cdd_var}, call={has_status_call}, "
           f"check={has_file_check}, after={has_after_summary}" if not ok else "")


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

    # Core scenarios (10)
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

    # Bootstrap scenarios (Section 2.15) (9)
    test_bootstrap_creates_delivery_plan()
    test_bootstrap_plan_approved()
    test_bootstrap_plan_declined()
    test_bootstrap_completes_work_directly()
    test_bootstrap_failure()
    test_bootstrap_distinct_system_prompt()
    test_bootstrap_plan_validated_before_approval()
    test_bootstrap_plan_has_dependency_cycle()
    test_bootstrap_prefers_conservative_sizing()

    # Remaining original scenarios (7)
    test_evaluator_failure_fallback()
    test_system_prompt_overrides()
    test_phase_specific_assignment()
    test_logging_per_phase()
    test_exit_summary_per_phase_details()
    test_worktree_cleanup()
    test_delivery_plan_central_update()

    # Dynamic Delivery Plan Handling (Section 2.12) (8)
    test_builder_adds_qa_fix_phase()
    test_builder_splits_phase()
    test_builder_removes_remaining_phases()
    test_new_phase_depends_on_completed()
    test_new_phase_creates_dependency_chain()
    test_builder_removes_some_phases()
    test_non_contiguous_phase_numbers()
    test_removed_phase_had_dependents()

    # Parallel Plan Amendments (Section 2.13) (4)
    test_parallel_both_request_amendments()
    test_parallel_amendment_structured_files()
    test_amendment_files_cleaned_up()
    test_sequential_builder_modifies_plan_directly()

    # Evaluator Amendment Detection (Section 2.14) (3)
    test_parallel_group_invalidated()
    test_phase_count_changes_in_summary()
    test_reanalysis_after_retry()

    # Builder Output Visibility (Section 2.16) (6)
    test_sequential_phase_output_streamed()
    test_bootstrap_output_streamed()
    test_parallel_heartbeat_during_execution()
    test_parallel_output_not_streamed()
    test_heartbeat_stops_after_parallel_complete()
    test_resume_session_output_streamed_and_appended()

    # Enhanced Heartbeat & Graceful Stop (Section 2.16) (7)
    test_heartbeat_overwrites_previous_output()
    test_heartbeat_falls_back_plain_output()
    test_heartbeat_shows_current_activity()
    test_heartbeat_warns_empty_log()
    test_graceful_stop_on_sigint()
    test_second_sigint_forces_exit()
    test_post_run_status_refresh()

    write_results()
    sys.exit(0 if results["failed"] == 0 else 1)
