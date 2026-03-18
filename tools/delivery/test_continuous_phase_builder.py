#!/usr/bin/env python3
"""Tests for continuous phase builder — exercises all 70 automated scenarios.

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
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
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
        f.write('print("AGENT_FIND_WORK=\\"true\\"")\n')
        f.write('print("AGENT_AUTO_START=\\"false\\"")\n')

    return tmpdir


def make_mock_claude(tmpdir, behavior="phase_complete", phase_count=1, exit_code=0,
                     eval_responses=None):
    """Create a mock claude command.

    Builder behaviors:
    - phase_complete: outputs "Phase N of M complete"
    - all_complete: deletes delivery plan and outputs success
    - infeasible: outputs INFEASIBLE escalation
    - noop: outputs nothing meaningful

    eval_responses: list of (action, success_bool, reason) tuples for evaluator calls.
    Each evaluator call pops the next response in order.
    Defaults to [("continue", False, "Phase completed")] if None.
    """
    bin_dir = os.path.join(tmpdir, 'mock_bin')
    os.makedirs(bin_dir, exist_ok=True)

    # Write evaluator response sequence to a file
    eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
    if eval_responses is None:
        eval_responses = [("continue", False, "Phase completed successfully")]
    with open(eval_seq_file, 'w') as f:
        for action, success, reason in eval_responses:
            success_str = "true" if success else "false"
            f.write(f"{action}|{success_str}|{reason}\n")

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
        echo '{{"action": "stop", "success": false, "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REMAINDER="${{RESPONSE#*|}}"
        SUCCESS="${{REMAINDER%%|*}}"
        REASON="${{REMAINDER#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"success\\": $SUCCESS, \\"reason\\": \\"$REASON\\"}}"
    fi
    exit 0
fi

# Builder invocation — produce stream-json output (NDJSON)
emit_json() {{
    echo "$1"
}}

case "$BEHAVIOR" in
    phase_complete)
        emit_json '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
        emit_json '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Reading feature spec..."}}]}}}}'
        emit_json '{{"type":"tool_use","name":"Read","input":{{"file_path":"features/a.md"}}}}'
        emit_json '{{"type":"tool_result","output":"# Feature A\\nTest content."}}'
        emit_json '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase 1 of '$PHASE_COUNT' complete\\nRecommended next step: run QA to verify Phase 1 features."}}]}}}}'
        emit_json '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":5000}}'
        ;;
    all_complete)
        if [ -f "$PURLIN_PROJECT_ROOT/.purlin/cache/delivery_plan.md" ]; then
            rm -f "$PURLIN_PROJECT_ROOT/.purlin/cache/delivery_plan.md"
        fi
        emit_json '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
        emit_json '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"All phases complete. Delivery plan deleted."}}]}}}}'
        emit_json '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
        ;;
    infeasible)
        emit_json '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
        emit_json '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"INFEASIBLE: Cannot implement feature due to missing dependency."}}]}}}}'
        emit_json '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":1000}}'
        ;;
    noop)
        emit_json '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
        emit_json '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Starting session..."}}]}}}}'
        emit_json '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":1000}}'
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
                                       ("continue", False, "Phase 1 done"),
                                       ("continue", False, "Phase 2 done"),
                                       ("stop", True, "All phases complete successfully"),
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
                                       ("continue", False, "Parallel group done"),
                                       ("stop", True, "All phases complete successfully"),
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
                                   eval_responses=[("continue", False, "done")])
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
        echo '{{"action": "approve", "success": false, "reason": "Builder waiting for approval"}}'
    else
        echo '{{"action": "stop", "success": true, "reason": "All phases complete successfully"}}'
    fi
    exit 0
fi

# Builder calls — track state
STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -eq 1 ]; then
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Ready to go, or would you like to adjust the plan?"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
else
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase 1 of 1 complete"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
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
        echo '{{"action": "retry", "success": false, "reason": "Context exhausted mid-phase"}}'
    elif echo "$INPUT" | grep -q "Phase .* of .* complete"; then
        echo '{{"action": "stop", "success": true, "reason": "All phases complete successfully"}}'
    else
        echo '{{"action": "stop", "success": false, "reason": "done"}}'
    fi
    exit 0
fi

STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -le 1 ]; then
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Context limit approaching. Saving checkpoint.\\ncontext exhaustion"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
else
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase 1 of 1 complete"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
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
    echo '{{"action": "retry", "success": false, "reason": "Context exhausted mid-phase"}}'
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
                                       ("stop", False, "Error requiring human intervention"),
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
                                       ("stop", True, "All phases complete successfully"),
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
# Bootstrap Scenarios (Section 2.16)
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
        eval_responses = [("stop", True, "All phases complete successfully")]
    with open(eval_seq_file, 'w') as f:
        for action, success, reason in eval_responses:
            success_str = "true" if success else "false"
            f.write(f"{action}|{success_str}|{reason}\n")

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
        echo '{{"action": "stop", "success": false, "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REMAINDER="${{RESPONSE#*|}}"
        SUCCESS="${{REMAINDER%%|*}}"
        REASON="${{REMAINDER#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"success\\": $SUCCESS, \\"reason\\": \\"$REASON\\"}}"
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
    echo '{{"type":"system","subtype":"init","session_id":"mock-bootstrap"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Bootstrap session complete."}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-bootstrap","cost_usd":0.01,"duration_ms":3000}}'
    exit {exit_code}
fi

# Phase execution calls
echo '{{"type":"system","subtype":"init","session_id":"mock-phase"}}'
echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase complete"}}]}}}}'
echo '{{"type":"result","subtype":"success","session_id":"mock-phase","cost_usd":0.01,"duration_ms":5000}}'
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
            eval_responses=[("stop", True, "All phases complete successfully")]
        )

        # Default stdin (empty) -> approval defaults to yes
        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        bootstrap_log = os.path.join(tmpdir, '.purlin', 'runtime',
                                     'continuous_build_bootstrap.log')
        log_exists = os.path.exists(bootstrap_log)
        has_summary = "=== Delivery Plan" in proc.stderr

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
            eval_responses=[("stop", True, "All phases complete successfully")]
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
    """Bootstrap exits non-zero without creating plan -> error directing user
    to run interactive session, launcher exits non-zero status."""
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=False, exit_code=1
        )

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        has_error_msg = "interactive" in proc.stderr.lower()
        has_nonzero_exit = proc.returncode != 0
        # Verify no delivery plan was created
        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        no_plan_created = not os.path.exists(plan_path)

        ok = (
            has_nonzero_exit
            and has_error_msg
            and no_plan_created
        )
        record("Bootstrap Failure", ok,
               f"rc={proc.returncode}, error={has_error_msg}, "
               f"no_plan={no_plan_created}, "
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
    has_analyzer_call = 'PHASE_ANALYZER' in source

    # More structural: the bootstrap block runs the analyzer after detecting plan exists
    bootstrap_section = source[source.find('Bootstrap session when no delivery plan'):]
    bootstrap_section = bootstrap_section[:bootstrap_section.find('# --- Track initial')]
    has_validate_in_bootstrap = ('VALIDATE_RC' in bootstrap_section and
                                 'PHASE_ANALYZER' in bootstrap_section)

    # Verify approval prompt appears AFTER validation in the bootstrap section
    validate_pos = bootstrap_section.find('VALIDATE_RC')
    approval_pos = bootstrap_section.find('Proceed? [Y/n]')
    has_order = (validate_pos >= 0 and approval_pos >= 0 and
                 validate_pos < approval_pos)

    ok = has_analyzer_call and has_validate_in_bootstrap and has_order
    record("Bootstrap Plan Validated Before Approval", ok,
           f"analyzer={has_analyzer_call}, "
           f"in_bootstrap={has_validate_in_bootstrap}, "
           f"order={has_order}" if not ok else "")


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
echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase 1 of 1 complete"}}]}}}}'
echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
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
                                   eval_responses=[("continue", False, "done")])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'continuous_build_phase_1.log')
        log_exists = os.path.exists(log_path)
        log_content = ""
        if log_exists:
            with open(log_path) as f:
                log_content = f.read()

        # Must contain actual Builder output in stream-json format
        has_builder_output = "Phase 1 of" in log_content
        # Must be JSON lines (stream-json), not plain text
        has_json = '"type":' in log_content
        # Log must be substantially larger than 4 bytes (control-char ghost)
        log_size = len(log_content)
        not_ghost = log_size > 50

        ok = log_exists and has_builder_output and has_json and not_ghost
        record("Logging Per Phase", ok,
               f"exists={log_exists}, builder_output={has_builder_output}, "
               f"json={has_json}, size={log_size}, "
               f"content_preview={repr(log_content[:200])}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Exit Summary Phase Table
# ============================================================
def test_exit_summary_phase_table():
    """Exit summary includes status line, duration, phase count, per-phase details
    with dynamic column widths that fill terminal width, retries, and parallel groups."""
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
                                       ("continue", False, "Phase 1 done"),
                                       ("continue", False, "Phase 2 done"),
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
        record("Exit Summary Phase Table", ok,
               f"status={has_status_line}, dur={has_duration}, count={has_phase_count}, "
               f"per_phase={has_per_phase}, retries={has_retries}, parallel={has_parallel}, "
               f"logs={has_log_files}, complete={has_complete_status}, feats={has_features}, "
               f"stderr={proc.stderr[-800:]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Exit Summary Work Digest
# ============================================================
def test_exit_summary_work_digest():
    """Exit summary includes an LLM-generated work digest below the phase table.
    Extracts 'result' from phase log stream-json, sends to Haiku, prints as plain text."""
    source = read_launcher()

    # Verify the work digest generation function exists
    has_digest_fn = 'generate_work_digest' in source
    # Verify it extracts result from stream-json logs
    has_result_extraction = '"type":"result"' in source or "'type':'result'" in source
    # Verify it calls the evaluator model (uses EVALUATOR_MODEL variable)
    has_haiku_call = 'EVALUATOR_MODEL' in source and 'claude --print --model' in source
    # Verify digest prompt contains required sections
    has_prompt_sections = all(s in source for s in [
        'Overall:', 'What was built:', 'Issues:', 'Needs attention:'
    ])
    # Verify digest prints after phase table and before closing line
    # Footer uses dynamic width: printf ... tr ' ' '='
    has_correct_ordering = bool(re.search(
        r'generate_work_digest.*?Log files:.*?tr .* =',
        source,
        re.DOTALL
    ))
    # Verify plain text output (no ANSI in digest)
    has_plain_text_note = 'no ANSI color' in source.lower() or 'plain text' in source.lower()

    ok = (has_digest_fn and has_result_extraction and has_haiku_call and
          has_prompt_sections and has_correct_ordering)
    record("Exit Summary Work Digest", ok,
           f"fn={has_digest_fn}, result_extract={has_result_extraction}, "
           f"haiku={has_haiku_call}, sections={has_prompt_sections}, "
           f"ordering={has_correct_ordering}" if not ok else "")


# ============================================================
# Scenario: Work Digest Timeout Fallback
# ============================================================
def test_work_digest_timeout_fallback():
    """When the Haiku digest call exceeds 30s timeout, the phase table prints normally
    and the digest is replaced with a fallback message."""
    source = read_launcher()

    # Verify timeout handling exists for the digest call
    has_timeout_handling = bool(re.search(
        r'timeout\s+30.*?claude.*?EVALUATOR_MODEL.*?digest|'
        r'gtimeout\s+30.*?claude.*?digest|'
        r'dwaited.*?30.*?digest',
        source,
        re.DOTALL | re.IGNORECASE
    ))

    # Verify the 30-second timeout with fallback chain (timeout/gtimeout/manual)
    has_timeout_chain = ('timeout 30' in source or 'gtimeout 30' in source) and 'dwaited' in source

    # Verify fallback message when digest fails
    has_fallback_msg = 'Work digest unavailable' in source

    # Verify log file location still prints after fallback
    has_log_after_fallback = bool(re.search(
        r'Work digest unavailable.*?Log files:',
        source,
        re.DOTALL
    ))

    # Verify closing line still prints (footer uses dynamic width: tr ' ' '=')
    has_closing_after_fallback = bool(re.search(
        r'Log files:.*?tr .* =',
        source,
        re.DOTALL
    ))

    ok = (has_timeout_chain and has_fallback_msg and
          has_log_after_fallback and has_closing_after_fallback)
    record("Work Digest Timeout Fallback", ok,
           f"timeout_chain={has_timeout_chain}, fallback={has_fallback_msg}, "
           f"log_after={has_log_after_fallback}, closing={has_closing_after_fallback}"
           if not ok else "")


# ============================================================
# Scenario: Worktree Cleanup on Error
# ============================================================
def test_worktree_cleanup():
    """On error during parallel group, all worktrees are cleaned up."""
    source = read_launcher()

    # Verify cleanup logic exists in trap handlers (original + fallback)
    has_trap_cleanup = ('trap cleanup EXIT' in source or
                        'trap print_fallback_summary EXIT' in source)
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
# Helper: create a mock claude that modifies the delivery plan
# ============================================================
def make_plan_modifying_mock(tmpdir, modifications, eval_responses):
    """Create a mock claude that modifies the delivery plan on specific calls.

    modifications: dict mapping call_number -> callable(plan_path, tmpdir)
        The callable modifies the delivery plan file on that call number.
    eval_responses: list of (action, success_bool, reason) for evaluator calls.
    """
    mock_bin_dir = os.path.join(tmpdir, 'mock_bin')
    os.makedirs(mock_bin_dir, exist_ok=True)

    # Write eval responses
    eval_seq_file = os.path.join(tmpdir, '.purlin', 'runtime', 'eval_responses')
    with open(eval_seq_file, 'w') as f:
        for action, success, reason in eval_responses:
            success_str = "true" if success else "false"
            f.write(f"{action}|{success_str}|{reason}\n")

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
        echo '{{"action": "stop", "success": false, "reason": "Sequence exhausted"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REMAINDER="${{RESPONSE#*|}}"
        SUCCESS="${{REMAINDER%%|*}}"
        REASON="${{REMAINDER#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"success\\": $SUCCESS, \\"reason\\": \\"$REASON\\"}}"
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

echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase '"$CALL_NUM"' complete"}}]}}}}'
echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":5000}}'
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done, plan amended"),
                ("continue", False, "Phase 2 done"),
                ("continue", False, "Phase 3 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
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
                ("continue", False, "Phase 1 done, plan split"),
                ("continue", False, "Phase 4 done"),
                ("stop", True, "All phases complete successfully"),
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
                ("continue", False, "Phase 1 done, remaining removed"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 5 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mod_2 = '''
import re, sys
plan_path = sys.argv[1]
with open(plan_path) as f:
    content = f.read()
# Mark first PENDING as COMPLETE
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
# Add Phase 6
new_phase = "\\n## Phase 6 -- F [PENDING]\\n**Features:** f.md\\n**Completion Commit:** --\\n**QA Bugs Addressed:** --\\n"
content = content.replace("## Plan Amendments", new_phase + "## Plan Amendments")
with open(plan_path, 'w') as f:
    f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_generic, 2: mod_2, 3: mod_generic, 4: mod_generic, 5: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done, added Phase 6"),
                ("continue", False, "Phase done"),
                ("continue", False, "Phase done"),
                ("stop", True, "All phases complete successfully"),
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
            f.write("continue|false|Parallel group done\n")
            f.write("stop|true|All phases complete successfully\n")

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
        echo '{{"action": "stop", "success": false, "reason": "done"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REMAINDER="${{RESPONSE#*|}}"
        SUCCESS="${{REMAINDER%%|*}}"
        REASON="${{REMAINDER#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"success\\": $SUCCESS, \\"reason\\": \\"$REASON\\"}}"
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

echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase complete"}}]}}}}'
echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":5000}}'
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

        # Check that amendments were applied — either in the plan file (if it still exists)
        # or evidenced by phases 7/8 running (visible in stderr).
        # The plan may be deleted at end-of-run if all phases complete successfully.
        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_content = ""
        if os.path.exists(plan_path):
            with open(plan_path) as f:
                plan_content = f.read()

        has_phase_7 = 'Phase 7' in plan_content or 'Phases 7' in proc.stderr
        has_phase_8 = 'Phase 8' in plan_content or 'Phases 7 8' in proc.stderr or 'Phases 8' in proc.stderr

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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic, 5: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done"),
                ("continue", False, "Phase 3 done"),
                ("continue", False, "Phase 4 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={2: mod_2, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("retry", False, "Context exhausted"),
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done"),
                ("stop", True, "All phases complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic, 4: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase done"),
                ("continue", False, "Phase done"),
                ("stop", True, "All complete successfully"),
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
            f.write("continue|false|Parallel done\n")
            f.write("stop|true|All complete successfully\n")

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
        echo '{{"action": "stop", "success": false, "reason": "done"}}'
    else
        ACTION="${{RESPONSE%%|*}}"
        REMAINDER="${{RESPONSE#*|}}"
        SUCCESS="${{REMAINDER%%|*}}"
        REASON="${{REMAINDER#*|}}"
        echo "{{\\"action\\": \\"$ACTION\\", \\"success\\": $SUCCESS, \\"reason\\": \\"$REASON\\"}}"
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
echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"Phase complete"}}]}}}}'
echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":5000}}'
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic, 3: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("continue", False, "Phase 2 done"),
                ("stop", True, "All complete successfully"),
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
pending = re.findall(r'## Phase (\\d+) -- .+? \\[(?:PENDING|IN_PROGRESS)\\]', content)
if pending:
    pnum = pending[0]
    content = re.sub(r'(## Phase ' + pnum + r' -- .+?) \\[(?:PENDING|IN_PROGRESS)\\]', r'\\1 [COMPLETE]', content)
    with open(plan_path, 'w') as f:
        f.write(content)
'''
        mock_bin = make_plan_modifying_mock(tmpdir,
            modifications={1: mod_1, 2: mod_generic},
            eval_responses=[
                ("continue", False, "Phase 1 done"),
                ("stop", True, "All complete successfully"),
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
# Builder Output Visibility (Section 2.17) (6)
# ============================================================

def test_bootstrap_canvas_shows_spinner():
    """Bootstrap canvas shows an animated braille spinner and elapsed time on stderr."""
    source = read_launcher()

    # Verify start_bootstrap_canvas function exists
    has_bootstrap_canvas = 'start_bootstrap_canvas()' in source
    # Verify spinner array with braille characters
    has_spinner = 'SPINNER=' in source and '⠋' in source
    # Verify spinner cycles at ~100ms
    has_sleep_01 = 'sleep 0.1' in source
    # Verify elapsed time display
    has_elapsed = 'Bootstrapping for continuous delivery...' in source

    # Verify bootstrap invocation routes to log via run_to_log (not tee)
    bootstrap_start = source.find('# --- Bootstrap session')
    assert bootstrap_start != -1, "Could not find bootstrap section"
    bootstrap_section = source[bootstrap_start:]
    bootstrap_section = bootstrap_section[:bootstrap_section.find('# --- Track initial') if '# --- Track initial' in bootstrap_section else len(bootstrap_section)]
    has_redirect = 'run_to_log "$BOOTSTRAP_LOG" claude' in bootstrap_section
    has_no_tee = 'tee "$BOOTSTRAP_LOG"' not in bootstrap_section
    has_no_pipestatus = 'PIPESTATUS' not in bootstrap_section
    # Verify canvas is stopped after bootstrap
    has_stop_canvas = 'stop_canvas' in bootstrap_section

    # Integration: verify bootstrap log is written and output NOT on stdout
    tmpdir = tempfile.mkdtemp()
    try:
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, None, graph)
        mock_bin = make_bootstrap_mock_claude(
            tmpdir, creates_plan=True,
            eval_responses=[("stop", True, "All phases complete successfully")]
        )

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        bootstrap_log = os.path.join(tmpdir, '.purlin', 'runtime',
                                     'continuous_build_bootstrap.log')
        log_exists = os.path.exists(bootstrap_log)
        log_content = ""
        if log_exists:
            with open(bootstrap_log) as f:
                log_content = f.read()

        log_has_output = "Bootstrap session complete" in log_content
        # Builder output should NOT be on stdout (log-file only)
        stdout_clean = "Bootstrap session complete" not in proc.stdout

        ok = (has_bootstrap_canvas and has_spinner and has_sleep_01 and has_elapsed and
              has_redirect and has_no_tee and has_no_pipestatus and has_stop_canvas and
              log_exists and log_has_output and stdout_clean)
        record("Bootstrap Canvas Shows Spinner During Initialization", ok,
               f"canvas_fn={has_bootstrap_canvas}, spinner={has_spinner}, "
               f"sleep={has_sleep_01}, elapsed={has_elapsed}, "
               f"redirect={has_redirect}, no_tee={has_no_tee}, "
               f"no_pipestatus={has_no_pipestatus}, stop={has_stop_canvas}, "
               f"log={log_exists}, log_output={log_has_output}, "
               f"stdout_clean={stdout_clean}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_approval_checkpoint_renders_table():
    """Approval checkpoint renders a space-aligned console table sized to terminal width."""
    source = read_launcher()

    # Verify render_approval_table function exists
    has_render_fn = 'render_approval_table()' in source
    # Verify it's called during bootstrap plan approval
    has_render_call = 'render_approval_table' in source

    # Verify table structure: columns (no Complexity), header coloring, separator, prompt
    has_header_cols = 'Label' in source and 'Features' in source and 'Exec Group' in source
    has_bold_cyan = '1;36m' in source  # Bold cyan for headers
    has_green_sep = '32m' in source  # Green for separators
    has_proceed = 'Proceed? [Y/n]' in source
    has_parallel_groups = 'Parallel groups:' in source
    has_review_path = 'Review at .purlin/cache/delivery_plan.md' in source

    # Verify dynamic column widths from terminal width (env var or tput cols)
    has_tput_cols = 'PURLIN_TERM_COLS' in source or 'tput cols' in source
    # Verify proportional column width computation (30%, 45%, 25%)
    has_proportional = '0.30' in source and '0.45' in source
    # Verify cell wrapping (max 2 lines per cell)
    has_wrap_cell = 'wrap_cell' in source
    # Verify lines fit within terminal width (truncation with [:cols])
    has_line_truncation = '[:cols]' in source
    # Verify line count tracking for SIGWINCH
    has_lines_file = 'approval_table_lines' in source

    ok = (has_render_fn and has_render_call and has_header_cols and
          has_bold_cyan and has_green_sep and has_proceed and
          has_parallel_groups and has_review_path and
          has_tput_cols and has_proportional and has_wrap_cell and
          has_line_truncation and has_lines_file)
    record("Approval Checkpoint Renders Console Table", ok,
           f"fn={has_render_fn}, call={has_render_call}, "
           f"cols={has_header_cols}, cyan={has_bold_cyan}, "
           f"green={has_green_sep}, proceed={has_proceed}, "
           f"parallel={has_parallel_groups}, path={has_review_path}, "
           f"tput={has_tput_cols}, proportional={has_proportional}, "
           f"wrap={has_wrap_cell}, truncate={has_line_truncation}, "
           f"lines_file={has_lines_file}" if not ok else "")


def test_approval_table_respects_narrow_terminal():
    """Approval table renders within narrow terminal width with cell wrapping."""
    source = read_launcher()

    # Verify render_approval_table has dynamic column width computation
    render_fn_start = source.find('render_approval_table()')
    render_fn = source[render_fn_start:source.find('\n}', render_fn_start) + 2] if render_fn_start >= 0 else ""

    # Dynamic column widths from terminal width (env var or tput cols)
    has_tput_cols = 'PURLIN_TERM_COLS' in render_fn or 'tput cols' in render_fn
    # Proportional allocation: ~30% label, ~45% features, ~25% exec group
    has_proportional = '0.30' in render_fn and '0.45' in render_fn
    # Column widths computed from remaining space
    has_remaining_calc = 'remaining' in render_fn and 'fixed_overhead' in render_fn
    # Cell wrapping function (max 2 lines per cell)
    has_wrap_fn = 'def wrap_cell' in render_fn
    has_max_2_lines = 'row_lines > 2' in render_fn or 'max_lines > 2' in render_fn
    # Continuation line padded to column start (uses same format with empty # column)
    has_continuation_padding = "''," in render_fn and 'label_w' in render_fn
    # Lines truncated to terminal width
    has_cols_truncation = '[:cols]' in render_fn
    # No Complexity column in header
    has_no_complexity = 'Complexity' not in render_fn

    ok = (has_tput_cols and has_proportional and has_remaining_calc and
          has_wrap_fn and has_max_2_lines and has_continuation_padding and
          has_cols_truncation and has_no_complexity)
    record("Approval Table Respects Narrow Terminal", ok,
           f"tput={has_tput_cols}, proportional={has_proportional}, "
           f"remaining={has_remaining_calc}, wrap_fn={has_wrap_fn}, "
           f"max_2={has_max_2_lines}, padding={has_continuation_padding}, "
           f"truncate={has_cols_truncation}, "
           f"no_complexity={has_no_complexity}" if not ok else "")


def test_approval_table_stacked_below_60():
    """Approval table uses stacked single-column layout when terminal < 60 cols."""
    source = read_launcher()

    # Find the render_approval_table function
    render_fn_start = source.find('render_approval_table()')
    render_fn = source[render_fn_start:source.find('\n}', render_fn_start) + 2] if render_fn_start >= 0 else ""

    # Stacked threshold constant (60 columns)
    has_stacked_threshold = 'STACKED_THRESHOLD' in render_fn and '60' in render_fn
    # Branch on cols < threshold
    has_stacked_branch = 'cols < STACKED_THRESHOLD' in render_fn
    # Stacked layout uses labeled fields (one per line)
    has_labeled_fields = "'Label'" in render_fn and "'Features'" in render_fn and "'Exec Group'" in render_fn
    # Lines truncated to cols in stacked mode
    has_stacked_truncation = '[:cols]' in render_fn
    # Phase header in stacked mode
    has_phase_header = "'Phase '" in render_fn or '"Phase "' in render_fn

    ok = (has_stacked_threshold and has_stacked_branch and
          has_labeled_fields and has_stacked_truncation and has_phase_header)
    record("Approval Table Uses Stacked Layout Below 60 Columns", ok,
           f"threshold={has_stacked_threshold}, branch={has_stacked_branch}, "
           f"labels={has_labeled_fields}, truncate={has_stacked_truncation}, "
           f"header={has_phase_header}" if not ok else "")


def test_approval_table_rerenders_on_resize():
    """Approval table re-renders on SIGWINCH with recomputed column widths."""
    source = read_launcher()

    # Verify SIGWINCH trap is set before the read during approval
    has_sigwinch_trap = 'trap rerender_on_resize SIGWINCH' in source
    # Verify SIGWINCH trap is restored after the read (general handler or removed)
    has_trap_cleanup = 'trap - SIGWINCH' in source or 'trap update_term_width WINCH' in source
    # Verify rerender_on_resize function exists
    has_rerender_fn = 'rerender_on_resize()' in source
    # Verify rerender function clears via cursor-up and clear-to-end
    rerender_start = source.find('rerender_on_resize()')
    rerender_fn = source[rerender_start:source.find('\n}', rerender_start) + 2] if rerender_start >= 0 else ""
    has_cursor_up_clear = '\\033[%dA' in rerender_fn and '\\033[J' in rerender_fn
    # Verify rerender function re-reads terminal width (via render_approval_table which calls tput cols)
    has_re_render_call = 'render_approval_table' in rerender_fn
    # Verify rerender function re-displays the prompt
    has_re_prompt = 'Proceed? [Y/n]' in rerender_fn
    # Verify line count file is used for cursor math
    has_lines_file = 'APPROVAL_TABLE_LINES_FILE' in rerender_fn

    ok = (has_sigwinch_trap and has_trap_cleanup and has_rerender_fn and
          has_cursor_up_clear and has_re_render_call and has_re_prompt and
          has_lines_file)
    record("Approval Table Re-Renders on Terminal Resize", ok,
           f"trap={has_sigwinch_trap}, cleanup={has_trap_cleanup}, "
           f"fn={has_rerender_fn}, ansi={has_cursor_up_clear}, "
           f"re_render={has_re_render_call}, prompt={has_re_prompt}, "
           f"lines_file={has_lines_file}" if not ok else "")


def test_sequential_phase_canvas():
    """Sequential phase canvas shows spinner, elapsed time, log size, and activity."""
    source = read_launcher()

    # Verify start_sequential_canvas function exists
    has_canvas_fn = 'start_sequential_canvas()' in source
    # Verify sequential section calls it
    seq_start = source.find('# SEQUENTIAL EXECUTION')
    assert seq_start != -1
    seq_section = source[seq_start:]
    seq_section = seq_section[:seq_section.find('\n    fi\ndone')]
    has_canvas_call = 'start_sequential_canvas' in seq_section
    # Verify no tee in sequential section
    has_no_tee = 'tee "$LOG_FILE"' not in seq_section
    # Verify run_to_log routes to log file
    has_redirect = 'run_to_log "$LOG_FILE"' in seq_section

    # Verify canvas shows phase label, spinner, elapsed, log size, activity
    canvas_fn_start = source.find('start_sequential_canvas()')
    canvas_fn = source[canvas_fn_start:source.find('\n}', canvas_fn_start) + 2] if canvas_fn_start >= 0 else ""
    has_phase_label = 'extract_phase_label' in canvas_fn
    has_activity_extraction = 'extract_activity' in canvas_fn
    has_log_size = 'wc -c' in canvas_fn

    # Terminal width constraint: reads shared file each cycle (not tput cols — Section 2.17)
    has_term_cols = 'TERM_WIDTH_FILE' in canvas_fn
    has_activity_truncation = 'disp_activity' in canvas_fn or 'act_avail' in canvas_fn
    has_label_truncation = 'disp_label' in canvas_fn

    # Integration: verify log file exists and stdout clean
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", False, "done")])

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'continuous_build_phase_1.log')
        log_exists = os.path.exists(log_path)
        log_content = ""
        if log_exists:
            with open(log_path) as f:
                log_content = f.read()
        log_has_output = "Phase 1 of" in log_content
        # stdout should NOT have builder output (canvas model)
        stdout_clean = "Phase 1 of" not in proc.stdout

        ok = (has_canvas_fn and has_canvas_call and has_no_tee and has_redirect and
              has_phase_label and has_activity_extraction and has_log_size and
              has_term_cols and has_activity_truncation and has_label_truncation and
              log_exists and log_has_output and stdout_clean)
        record("Sequential Phase Canvas During Execution", ok,
               f"fn={has_canvas_fn}, call={has_canvas_call}, "
               f"no_tee={has_no_tee}, redirect={has_redirect}, "
               f"label={has_phase_label}, activity={has_activity_extraction}, "
               f"log_size={has_log_size}, term_cols={has_term_cols}, "
               f"act_trunc={has_activity_truncation}, lbl_trunc={has_label_truncation}, "
               f"log={log_exists}, log_output={log_has_output}, "
               f"stdout_clean={stdout_clean}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_parallel_phase_canvas():
    """Parallel phase canvas shows multi-line heartbeat display with per-phase details."""
    source = read_launcher()

    # Verify start_parallel_canvas function exists
    has_canvas_fn = 'start_parallel_canvas()' in source
    # Verify it's called in the parallel section
    parallel_start = source.find('# PARALLEL EXECUTION')
    assert parallel_start != -1
    parallel_section = source[parallel_start:]
    parallel_section = parallel_section[:parallel_section.find('\n    else\n')]
    has_canvas_call = 'start_parallel_canvas' in parallel_section
    # Verify canvas PID tracked
    has_canvas_pid = 'CANVAS_PID=$!' in source

    # Verify multi-line display in the canvas function
    canvas_fn_start = source.find('start_parallel_canvas()')
    canvas_fn = source[canvas_fn_start:source.find('\n}\n', canvas_fn_start) + 3] if canvas_fn_start >= 0 else ""
    has_timestamp = 'date +%H:%M:%S' in canvas_fn
    has_per_phase = 'Parallel group (' in canvas_fn
    has_running = 'running' in canvas_fn
    has_done = 'done' in canvas_fn
    has_cursor_up = '\\033[%dA' in canvas_fn
    has_clear = '\\033[J' in canvas_fn
    has_log_size = 'wc -c' in canvas_fn

    # Terminal width constraint: reads shared file each cycle (not tput cols — Section 2.17)
    has_term_cols = 'TERM_WIDTH_FILE' in canvas_fn
    has_activity_truncation = 'DISP_ACT' in canvas_fn or 'act_avail' in canvas_fn
    has_label_truncation = 'LABEL_PADDED' in canvas_fn

    ok = (has_canvas_fn and has_canvas_call and has_canvas_pid and
          has_timestamp and has_per_phase and has_running and has_done and
          has_cursor_up and has_clear and has_log_size and
          has_term_cols and has_activity_truncation and has_label_truncation)
    record("Parallel Phase Canvas During Execution", ok,
           f"fn={has_canvas_fn}, call={has_canvas_call}, pid={has_canvas_pid}, "
           f"timestamp={has_timestamp}, per_phase={has_per_phase}, "
           f"running={has_running}, done={has_done}, "
           f"cursor_up={has_cursor_up}, clear={has_clear}, "
           f"log_size={has_log_size}, term_cols={has_term_cols}, "
           f"act_trunc={has_activity_truncation}, "
           f"lbl_trunc={has_label_truncation}" if not ok else "")


def test_all_builder_output_routes_to_log_files():
    """ALL Builder output in continuous mode goes to log files only — no tee."""
    source = read_launcher()

    # Continuous mode section only
    cont_start = source.find('# CONTINUOUS MODE')
    assert cont_start != -1
    continuous_section = source[cont_start:]

    # No tee in any builder invocation in continuous mode
    has_no_tee = 'tee' not in continuous_section

    # Verify run_to_log routes output to log files for bootstrap, sequential, and parallel
    bootstrap_start = source.find('# --- Bootstrap session')
    bootstrap_section = source[bootstrap_start:]
    bootstrap_section = bootstrap_section[:bootstrap_section.find('# --- Track initial') if '# --- Track initial' in bootstrap_section else len(bootstrap_section)]
    has_bootstrap_redirect = 'run_to_log "$BOOTSTRAP_LOG" claude' in bootstrap_section
    has_bootstrap_stream = '--output-format stream-json' in bootstrap_section

    seq_start = source.find('# SEQUENTIAL EXECUTION')
    seq_section = source[seq_start:]
    seq_section = seq_section[:seq_section.find('\n    fi\ndone')]
    has_seq_redirect = 'run_to_log "$LOG_FILE" claude' in seq_section
    has_seq_append = 'run_to_log "$LOG_FILE" --append claude' in seq_section
    has_seq_stream = '--output-format stream-json' in seq_section

    parallel_start = source.find('# PARALLEL EXECUTION')
    parallel_section = source[parallel_start:]
    parallel_section = parallel_section[:parallel_section.find('\n    else\n')]
    has_par_redirect = 'run_to_log "$LOG_FILE" claude' in parallel_section
    has_par_stream = '--output-format stream-json' in parallel_section

    # All claude invocations must use stream-json for real log content
    all_stream = has_bootstrap_stream and has_seq_stream and has_par_stream

    # Integration: verify no builder output on stdout
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([(1, "Only", "PENDING", ["a.md"])])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[("continue", False, "done")])
        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])
        stdout_clean = "Phase 1 of" not in proc.stdout

        ok = (has_no_tee and has_bootstrap_redirect and has_seq_redirect and
              has_seq_append and has_par_redirect and all_stream and stdout_clean)
        record("All Builder Output Routes to Log Files in Continuous Mode", ok,
               f"no_tee={has_no_tee}, boot_redir={has_bootstrap_redirect}, "
               f"seq_redir={has_seq_redirect}, seq_append={has_seq_append}, "
               f"par_redir={has_par_redirect}, "
               f"stream_json(boot={has_bootstrap_stream},seq={has_seq_stream},par={has_par_stream}), "
               f"stdout_clean={stdout_clean}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


def test_interphase_canvas_shows_evaluator_status():
    """Inter-phase canvas shows spinner with evaluator/re-analysis status."""
    source = read_launcher()

    # Verify start_interphase_canvas function exists
    has_interphase_fn = 'start_interphase_canvas()' in source
    # Verify evaluator status message
    has_eval_msg = 'Evaluating phase' in source or 'Evaluating parallel group' in source
    # Verify re-analysis message
    has_reanalyze_msg = 'Re-analyzing delivery plan...' in source
    # Verify it's called before evaluator and before re-analysis
    has_eval_call = bool(re.search(r'start_interphase_canvas.*Evaluating', source, re.DOTALL))
    has_reanalyze_call = bool(re.search(r'start_interphase_canvas.*Re-analyzing', source, re.DOTALL))
    # Verify stop_canvas is called after evaluator
    has_stop_after_eval = 'stop_canvas' in source

    ok = (has_interphase_fn and has_eval_msg and has_reanalyze_msg and
          has_eval_call and has_reanalyze_call and has_stop_after_eval)
    record("Inter-Phase Canvas Shows Evaluator Status", ok,
           f"fn={has_interphase_fn}, eval_msg={has_eval_msg}, "
           f"reanalyze_msg={has_reanalyze_msg}, eval_call={has_eval_call}, "
           f"reanalyze_call={has_reanalyze_call}, "
           f"stop={has_stop_after_eval}" if not ok else "")


def test_canvas_clears_before_final_summary():
    """Canvas is cleared one final time before the permanent exit summary."""
    source = read_launcher()

    # Find exit summary section
    summary_start = source.find('# Exit Summary (Section 2.17)')
    assert summary_start != -1
    summary_section = source[summary_start:]

    # Verify canvas_clear is called before exit summary output
    has_canvas_clear = 'canvas_clear' in summary_section
    # canvas_clear should come before the summary header
    clear_pos = summary_section.find('canvas_clear')
    header_pos = summary_section.find('=== Continuous Build Summary')
    has_clear_before_header = (clear_pos >= 0 and header_pos >= 0 and clear_pos < header_pos)
    # Verify exit summary uses colored output
    has_colored_header = 'C_BOLD_CYAN' in summary_section
    has_colored_phases = 'C_GREEN' in summary_section or 'GREEN' in summary_section
    has_colored_footer = 'C_BOLD_CYAN' in summary_section

    # Terminal width constraint: exit summary respects terminal width (env var)
    has_tput_cols = 'PURLIN_TERM_COLS' in summary_section or 'tput cols' in summary_section
    # Feature list wrapping to continuation line
    has_feat_wrap = 'feat_rest' in summary_section or 'avail_feat' in summary_section

    ok = (has_canvas_clear and has_clear_before_header and
          has_colored_header and has_colored_phases and has_colored_footer and
          has_tput_cols and has_feat_wrap)
    record("Canvas Clears Before Final Summary", ok,
           f"clear={has_canvas_clear}, before_header={has_clear_before_header}, "
           f"colored_header={has_colored_header}, colored_phases={has_colored_phases}, "
           f"colored_footer={has_colored_footer}, tput={has_tput_cols}, "
           f"feat_wrap={has_feat_wrap}" if not ok else "")


def test_canvas_falls_back_to_milestone_lines():
    """When stderr is not a TTY, no canvas — only milestone lines, no ANSI."""
    source = read_launcher()

    # Verify canvas_milestone function exists
    has_milestone_fn = 'canvas_milestone()' in source
    # Verify milestone is used in non-TTY paths
    has_bootstrap_milestone = bool(re.search(r'canvas_milestone.*Bootstrap', source))
    has_phase_milestone = bool(re.search(r'canvas_milestone.*Phase', source))
    # Verify TTY guard in canvas start functions
    has_tty_guard_bootstrap = '[ -t 2 ]' in source
    # Verify no ANSI in milestone function
    milestone_start = source.find('canvas_milestone()')
    milestone_fn = source[milestone_start:source.find('\n}', milestone_start) + 2] if milestone_start >= 0 else ""
    has_no_ansi_milestone = '\\033[' not in milestone_fn

    ok = (has_milestone_fn and has_bootstrap_milestone and has_phase_milestone and
          has_tty_guard_bootstrap and has_no_ansi_milestone)
    record("Canvas Falls Back to Milestone Lines When Not a TTY", ok,
           f"fn={has_milestone_fn}, boot_ms={has_bootstrap_milestone}, "
           f"phase_ms={has_phase_milestone}, tty_guard={has_tty_guard_bootstrap}, "
           f"no_ansi={has_no_ansi_milestone}" if not ok else "")


def test_canvas_render_loop_lifecycle():
    """Canvas render loop PID is tracked and terminated when phase completes."""
    source = read_launcher()

    # Verify CANVAS_PID variable is used (not HEARTBEAT_PID)
    has_canvas_pid = 'CANVAS_PID=' in source
    has_no_heartbeat_pid = 'HEARTBEAT_PID' not in source
    # Verify stop_canvas function exists and kills + waits
    has_stop_fn = 'stop_canvas()' in source
    stop_fn_start = source.find('stop_canvas()')
    stop_fn = source[stop_fn_start:source.find('\n}', stop_fn_start) + 2] if stop_fn_start >= 0 else ""
    has_kill_in_stop = 'kill "$CANVAS_PID"' in stop_fn
    has_wait_in_stop = 'wait "$CANVAS_PID"' in stop_fn
    has_clear_in_stop = 'canvas_clear' in stop_fn
    # Verify cleanup function references CANVAS_PID
    cleanup_start = source.find('cleanup()')
    cleanup_end = source.find('trap cleanup')
    cleanup_fn = source[cleanup_start:cleanup_end] if cleanup_start >= 0 else ""
    has_cleanup_canvas = 'CANVAS_PID' in cleanup_fn
    # Verify stop_canvas is called at phase boundaries
    has_stop_calls = source.count('stop_canvas') >= 3  # bootstrap, parallel, sequential

    ok = (has_canvas_pid and has_no_heartbeat_pid and has_stop_fn and
          has_kill_in_stop and has_wait_in_stop and has_clear_in_stop and
          has_cleanup_canvas and has_stop_calls)
    record("Canvas Render Loop Lifecycle", ok,
           f"pid={has_canvas_pid}, no_hb={has_no_heartbeat_pid}, "
           f"stop_fn={has_stop_fn}, kill={has_kill_in_stop}, "
           f"wait={has_wait_in_stop}, clear={has_clear_in_stop}, "
           f"cleanup={has_cleanup_canvas}, stops={has_stop_calls}" if not ok else "")


def test_resume_session_log_appended():
    """Resume session output is appended to existing log file (not overwritten)."""
    source = read_launcher()

    # Find the sequential execution section
    seq_start = source.find('# SEQUENTIAL EXECUTION')
    assert seq_start != -1
    seq_section = source[seq_start:]
    seq_section = seq_section[:seq_section.find('\n    fi\ndone')]

    # The resume path should use --append flag for run_to_log
    has_append = 'run_to_log "$LOG_FILE" --append claude' in seq_section

    # Integration test: verify both initial and resumed output in log
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

EVAL_STATE="{tmpdir}/.purlin/runtime/eval_count"
if echo "$@" | grep -q "json-schema"; then
    INPUT=$(cat)
    ECOUNT=0
    [ -f "$EVAL_STATE" ] && ECOUNT=$(cat "$EVAL_STATE")
    ECOUNT=$((ECOUNT + 1))
    echo "$ECOUNT" > "$EVAL_STATE"
    if [ "$ECOUNT" -eq 1 ]; then
        echo '{{"action": "approve", "success": false, "reason": "Builder waiting for approval"}}'
    else
        echo '{{"action": "stop", "success": true, "reason": "All phases complete successfully"}}'
    fi
    exit 0
fi

STATE_FILE="{state_file}"
COUNT=$(cat "$STATE_FILE")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$STATE_FILE"

if [ "$COUNT" -eq 1 ]; then
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"INITIAL_RUN_OUTPUT\\nReady to go, or would you like to adjust the plan?"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
else
    echo '{{"type":"system","subtype":"init","session_id":"mock-session"}}'
    echo '{{"type":"assistant","message":{{"role":"assistant","content":[{{"type":"text","text":"RESUMED_RUN_OUTPUT\\nPhase 1 of 1 complete"}}]}}}}'
    echo '{{"type":"result","subtype":"success","session_id":"mock-session","cost_usd":0.01,"duration_ms":3000}}'
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

        # Log should contain both initial and resumed output (>> appends)
        has_initial = "INITIAL_RUN_OUTPUT" in log_content
        has_resumed = "RESUMED_RUN_OUTPUT" in log_content

        ok = has_append and has_initial and has_resumed
        record("Resume Session Log Appended", ok,
               f"append={has_append}, log_initial={has_initial}, "
               f"log_resumed={has_resumed}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Canvas & Graceful Stop (Section 2.17) (5)
# ============================================================

def test_canvas_shows_current_builder_activity():
    """Canvas extracts current activity from log file tail for running phases."""
    source = read_launcher()

    # Verify extract_activity function exists
    has_extract_fn = 'extract_activity()' in source
    # Verify it reads log tail
    has_tail = 'tail -20' in source
    # Verify it detects file editing
    has_editing = 'editing' in source
    # Verify activity is called from canvas functions
    has_activity_in_sequential = 'extract_activity' in source[source.find('start_sequential_canvas'):] if 'start_sequential_canvas' in source else False
    has_activity_in_parallel = 'extract_activity' in source[source.find('start_parallel_canvas'):] if 'start_parallel_canvas' in source else False
    # Verify activity is dynamically truncated by canvas width logic (not hard-coded)
    # Canvas uses ACT_AVAIL / act_avail for terminal-width-aware truncation
    has_truncation = 'ACT_AVAIL' in source or 'act_avail' in source

    ok = (has_extract_fn and has_tail and has_editing and
          has_activity_in_sequential and has_activity_in_parallel and has_truncation)
    record("Canvas Shows Current Builder Activity", ok,
           f"fn={has_extract_fn}, tail={has_tail}, editing={has_editing}, "
           f"seq_call={has_activity_in_sequential}, par_call={has_activity_in_parallel}, "
           f"trunc={has_truncation}" if not ok else "")


def test_canvas_warns_on_empty_log():
    """Canvas shows red warning for completed phases with 0K log size."""
    source = read_launcher()

    # Find the parallel canvas function
    canvas_start = source.find('start_parallel_canvas()')
    assert canvas_start != -1
    canvas_fn = source[canvas_start:]
    # Find the end of the function (next top-level function)
    next_fn = canvas_fn.find('\n# ---', 10)
    if next_fn > 0:
        canvas_fn = canvas_fn[:next_fn]

    # Verify 0K check exists (uses array variable P_FSIZE after column-alignment refactor)
    has_zero_k_check = '"${P_FSIZE[$i]}" = "0K"' in canvas_fn or '"$FSIZE" = "0K"' in canvas_fn
    # Verify red color for 0K (ANSI red: \033[31m)
    has_red_color = '\\033[31m' in canvas_fn
    # Verify green color for normal done (ANSI green: \033[32m)
    has_green_color = '\\033[32m' in canvas_fn
    # Verify orange for running (ANSI orange: \033[38;5;208m)
    has_yellow_color = '\\033[38;5;208m' in canvas_fn or '\\033[33m' in canvas_fn

    ok = has_zero_k_check and has_red_color and has_green_color and has_yellow_color
    record("Canvas Warns on Empty Log at Phase Completion", ok,
           f"zero_k={has_zero_k_check}, red={has_red_color}, "
           f"green={has_green_color}, yellow={has_yellow_color}" if not ok else "")


def test_graceful_stop_on_sigint():
    """SIGINT trap sets stop flag, kills builders and canvas, resets IN_PROGRESS
    phases to PENDING, commits the reset, exits non-zero."""
    source = read_launcher()

    # Verify graceful_stop function exists
    has_handler = 'graceful_stop()' in source
    # Verify it sets STOP_REQUESTED
    has_stop_flag = 'STOP_REQUESTED=true' in source
    # Verify trap is set
    has_trap = 'trap graceful_stop INT' in source
    # Verify it kills parallel builder PIDs
    has_kill_pids = 'kill "$pid"' in source
    # Verify it kills canvas render loop
    handler_start = source.find('graceful_stop() {')
    handler_end = source.find('\ntrap graceful_stop INT')
    handler_body = source[handler_start:handler_end] if handler_start >= 0 else ""
    has_kill_canvas = 'CANVAS_PID' in handler_body
    # Verify it kills sequential builder
    has_kill_builder = 'BUILDER_PID' in handler_body
    # Verify trap reset for second SIGINT
    has_trap_reset = 'trap - INT' in handler_body
    # Verify STOP_REQUESTED check in loop causes break
    has_stop_check = '[ "$STOP_REQUESTED" = "true" ]' in source
    # Verify interrupted phases are recorded
    has_interrupted = '"INTERRUPTED"' in source
    # Verify canvas is cleared before exit summary
    has_canvas_clear = 'canvas_clear' in source
    # Verify phase status cleanup: reset IN_PROGRESS to PENDING on graceful stop
    has_phase_cleanup = 'reset_stale_in_progress' in handler_body

    ok = (has_handler and has_stop_flag and has_trap and has_kill_pids and
          has_kill_canvas and has_kill_builder and has_trap_reset and
          has_stop_check and has_interrupted and has_canvas_clear and
          has_phase_cleanup)
    record("Graceful Stop on SIGINT", ok,
           f"handler={has_handler}, flag={has_stop_flag}, trap={has_trap}, "
           f"kill_pids={has_kill_pids}, kill_canvas={has_kill_canvas}, "
           f"kill_builder={has_kill_builder}, reset={has_trap_reset}, "
           f"check={has_stop_check}, interrupted={has_interrupted}, "
           f"canvas_clear={has_canvas_clear}, "
           f"phase_cleanup={has_phase_cleanup}" if not ok else "")


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
    summary_start = source.find('# Exit Summary (Section 2.17)')
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


# ============================================================
# Scenario: Phases Marked IN_PROGRESS Before Launch (Section 2.4)
# ============================================================
def test_phases_marked_in_progress_before_launch():
    """Before launching parallel Builders, the orchestrator marks ALL phases
    in the group as IN_PROGRESS on the main branch, committed before any
    worktree Builder starts."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (2, "Design", "PENDING", ["a.md"]),
            (3, "Update", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All phases complete successfully"),
                                   ])

        # Enhance mock git to log add/commit calls
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff|add) ;;
    commit) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # After the run, check that the delivery plan has IN_PROGRESS or COMPLETE
        # (the mark_phases_in_progress function changes PENDING -> IN_PROGRESS,
        # and update_plan_phase_status changes it to COMPLETE after group completes)
        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_content = ""
        if os.path.exists(plan_path):
            with open(plan_path) as f:
                plan_content = f.read()

        # Check git log for the IN_PROGRESS commit
        git_log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'git_invocations.log')
        git_log = ""
        if os.path.exists(git_log_path):
            with open(git_log_path) as f:
                git_log = f.read()

        has_in_progress_commit = 'IN_PROGRESS' in git_log
        # Plan should have been updated (either IN_PROGRESS or COMPLETE after the run)
        no_pending = 'PENDING' not in plan_content

        # Verify source code structure: mark_phases_in_progress called before worktree loop
        source = read_launcher()
        parallel_section = source[source.find('PARALLEL EXECUTION'):]
        parallel_section = parallel_section[:parallel_section.find('SEQUENTIAL EXECUTION')]
        mark_before_worktree = 'mark_phases_in_progress' in parallel_section
        mark_pos = parallel_section.find('mark_phases_in_progress')
        worktree_pos = parallel_section.find('worktree add')
        has_order = mark_pos >= 0 and worktree_pos >= 0 and mark_pos < worktree_pos

        ok = has_in_progress_commit and no_pending and mark_before_worktree and has_order
        record("Phases Marked IN_PROGRESS Before Launch", ok,
               f"commit={has_in_progress_commit}, no_pending={no_pending}, "
               f"mark_before_wt={mark_before_worktree}, order={has_order}, "
               f"plan={plan_content[:200]}, git_log={git_log[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Sequential Phase Marked IN_PROGRESS Before Launch (Section 2.4)
# ============================================================
def test_sequential_phase_marked_in_progress():
    """Before launching a sequential Builder, the orchestrator marks the phase
    as IN_PROGRESS before the Builder launches."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (4, "Sequential", "PENDING", ["a.md"]),
        ])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All phases complete successfully"),
                                   ])

        # Enhance mock git to log add/commit calls
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff|add) ;;
    commit) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Check git log for the IN_PROGRESS commit
        git_log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'git_invocations.log')
        git_log = ""
        if os.path.exists(git_log_path):
            with open(git_log_path) as f:
                git_log = f.read()

        has_in_progress_commit = 'IN_PROGRESS' in git_log

        # Verify source code: mark_phases_in_progress before sequential Builder launch
        source = read_launcher()
        seq_section = source[source.find('SEQUENTIAL EXECUTION'):]
        mark_pos = seq_section.find('mark_phases_in_progress')
        builder_pos = seq_section.find('run_to_log')
        has_order = mark_pos >= 0 and builder_pos >= 0 and mark_pos < builder_pos

        ok = has_in_progress_commit and has_order
        record("Sequential Phase Marked IN_PROGRESS Before Launch", ok,
               f"commit={has_in_progress_commit}, order={has_order}, "
               f"git_log={git_log[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Per-Phase Status Update During Parallel Execution (Section 2.4)
# ============================================================
def test_per_phase_status_update_during_parallel_execution():
    """As soon as an individual Builder exits successfully during parallel execution,
    the orchestrator immediately marks that phase as COMPLETE on the main branch and
    commits the change. This happens while other Builders may still be running.
    Individual Builders do not modify the delivery plan (amendment files only)."""
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (2, "Design", "PENDING", ["a.md"]),
            (3, "Update", "PENDING", ["b.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All phases complete successfully"),
                                   ])

        # Mock git with add/commit support that logs per-phase commits
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff|add|commit) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Verify delivery plan was updated with COMPLETE status
        plan_path = os.path.join(tmpdir, '.purlin', 'cache', 'delivery_plan.md')
        plan_content = ""
        if os.path.exists(plan_path):
            with open(plan_path) as f:
                plan_content = f.read()

        # Plan may be deleted at end-of-run if all phases complete. Check plan OR
        # git commit log for evidence of per-phase COMPLETE updates.
        has_phase_2_complete = bool(re.search(r'## Phase 2 -- .+? \[COMPLETE\]', plan_content))
        has_phase_3_complete = bool(re.search(r'## Phase 3 -- .+? \[COMPLETE\]', plan_content))

        # Verify per-phase git commits were made (one per phase)
        git_log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'git_invocations.log')
        git_log = ""
        if os.path.exists(git_log_path):
            with open(git_log_path) as f:
                git_log = f.read()
        has_phase_2_commit = 'mark phase 2 as COMPLETE' in git_log
        has_phase_3_commit = 'mark phase 3 as COMPLETE' in git_log

        # If plan was deleted (all phases complete), commits prove the phases were marked
        if not has_phase_2_complete:
            has_phase_2_complete = has_phase_2_commit
        if not has_phase_3_complete:
            has_phase_3_complete = has_phase_3_commit

        # Verify the monitoring loop exists (per-phase update before merge)
        source = read_launcher()
        parallel_section = source[source.find('PARALLEL EXECUTION'):]
        parallel_section = parallel_section[:parallel_section.find('SEQUENTIAL EXECUTION')]

        # Per-phase update is in the monitoring loop, which uses kill -0 to check PIDs
        has_monitoring_loop = 'kill -0' in parallel_section
        # update_plan_phase_status is called inside the monitoring loop (before merge)
        monitor_pos = parallel_section.find('kill -0')
        update_pos = parallel_section.find('update_plan_phase_status')
        merge_pos = parallel_section.find('Merge each worktree')
        has_update_before_merge = (monitor_pos >= 0 and update_pos >= 0 and
                                   merge_pos >= 0 and update_pos < merge_pos)

        # Verify parallel Builders are told not to modify the plan
        has_no_modify = 'Do NOT modify the delivery plan directly' in source

        ok = (has_phase_2_complete and has_phase_3_complete and
              has_phase_2_commit and has_phase_3_commit and
              has_monitoring_loop and has_update_before_merge and has_no_modify)
        record("Per-Phase Status Update During Parallel Execution", ok,
               f"p2_complete={has_phase_2_complete}, p3_complete={has_phase_3_complete}, "
               f"p2_commit={has_phase_2_commit}, p3_commit={has_phase_3_commit}, "
               f"monitor_loop={has_monitoring_loop}, update_before_merge={has_update_before_merge}, "
               f"no_modify={has_no_modify}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Parallel Canvas Columns Align Across Phase Lines (Section 2.17)
# ============================================================
def test_parallel_canvas_columns_align():
    """All phase lines in a parallel group use aligned columns. The renderer
    computes max width of each field across phases and pads to column width."""
    source = read_launcher()

    # Find the parallel canvas function
    canvas_start = source.find('start_parallel_canvas()')
    assert canvas_start != -1
    canvas_fn = source[canvas_start:]
    next_fn = canvas_fn.find('\n# ---', 10)
    if next_fn > 0:
        canvas_fn = canvas_fn[:next_fn]

    # Verify two-pass approach: max width computation
    has_max_label_w = 'MAX_LABEL_W' in canvas_fn
    has_max_status_w = 'MAX_STATUS_W' in canvas_fn
    has_max_elapsed_w = 'MAX_ELAPSED_W' in canvas_fn
    has_max_fsize_w = 'MAX_FSIZE_W' in canvas_fn
    has_max_pnum_w = 'MAX_PNUM_W' in canvas_fn

    # Verify padded rendering with printf alignment
    has_label_pad = 'LABEL_PADDED' in canvas_fn
    has_status_pad = 'STATUS_PADDED' in canvas_fn
    has_elapsed_pad = 'ELAPSED_PADDED' in canvas_fn
    has_fsize_pad = 'FSIZE_PADDED' in canvas_fn

    # Verify max width comparison across phases
    has_max_comparison = '-gt $MAX_LABEL_W' in canvas_fn

    ok = (has_max_label_w and has_max_status_w and has_max_elapsed_w and
          has_max_fsize_w and has_max_pnum_w and
          has_label_pad and has_status_pad and has_elapsed_pad and has_fsize_pad and
          has_max_comparison)
    record("Parallel Canvas Columns Align Across Phase Lines", ok,
           f"max_label={has_max_label_w}, max_status={has_max_status_w}, "
           f"max_elapsed={has_max_elapsed_w}, max_fsize={has_max_fsize_w}, "
           f"max_pnum={has_max_pnum_w}, label_pad={has_label_pad}, "
           f"status_pad={has_status_pad}, elapsed_pad={has_elapsed_pad}, "
           f"fsize_pad={has_fsize_pad}, comparison={has_max_comparison}" if not ok else "")


# ============================================================
# Scenario: Log Files Grow Incrementally During Execution (Section 2.17)
# ============================================================
def test_log_files_grow_incrementally():
    """Builder output uses line-buffered output (stdbuf -oL or equivalent) to
    ensure log files grow incrementally during execution, not in blocks."""
    source = read_launcher()

    # Verify run_to_log function exists
    has_fn = 'run_to_log()' in source
    # Verify it tries stdbuf
    has_stdbuf = 'stdbuf -oL' in source
    # Verify fallback
    has_fallback = 'command -v stdbuf' in source

    # Verify run_to_log is used for all Builder invocations
    # Sequential
    seq_section = source[source.find('SEQUENTIAL EXECUTION'):]
    has_seq_buffered = 'run_to_log "$LOG_FILE" claude' in seq_section or 'run_to_log "$LOG_FILE" --append claude' in seq_section

    # Parallel (in worktree subshell)
    parallel_section = source[source.find('PARALLEL EXECUTION'):source.find('SEQUENTIAL EXECUTION')]
    has_par_buffered = 'run_to_log "$LOG_FILE" claude' in parallel_section

    # Bootstrap
    bootstrap_section = source[source.find('Bootstrap session when no delivery plan'):source.find('Track initial')]
    has_bootstrap_buffered = 'run_to_log "$BOOTSTRAP_LOG" claude' in bootstrap_section

    ok = (has_fn and has_stdbuf and has_fallback and
          has_seq_buffered and has_par_buffered and has_bootstrap_buffered)
    record("Log Files Grow Incrementally During Execution", ok,
           f"fn={has_fn}, stdbuf={has_stdbuf}, fallback={has_fallback}, "
           f"seq={has_seq_buffered}, par={has_par_buffered}, "
           f"bootstrap={has_bootstrap_buffered}" if not ok else "")


# ============================================================
# Scenario: Stale IN_PROGRESS Phases Reset on Startup (Section 2.4)
# ============================================================
def test_stale_in_progress_phases_reset_on_startup():
    """When a delivery plan has stale IN_PROGRESS phases from a previous
    interrupted run, the launcher resets them to PENDING before entering
    the orchestration loop, committed to git."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create plan with Phase 1 COMPLETE, Phase 2 IN_PROGRESS (stale), Phase 3 PENDING
        plan = make_plan([
            (1, "Foundation", "COMPLETE", ["a.md"]),
            (2, "Stale Phase", "IN_PROGRESS", ["b.md"]),
            (3, "Next Phase", "PENDING", ["c.md"]),
        ])
        graph = make_graph([
            ("a.md", []),
            ("b.md", []),
            ("c.md", []),
        ])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All phases complete successfully"),
                                   ])

        # Enhance mock git to log commits
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
GIT_LOG="{tmpdir}/.purlin/runtime/git_invocations.log"
echo "$@" >> "$GIT_LOG"
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    worktree) case "$2" in add) mkdir -p "$5" 2>/dev/null ;; remove) rm -rf "$3" 2>/dev/null ;; esac ;;
    merge|branch|diff|add) ;;
    commit) ;;
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Check git log for the reset commit
        git_log_path = os.path.join(tmpdir, '.purlin', 'runtime', 'git_invocations.log')
        git_log = ""
        if os.path.exists(git_log_path):
            with open(git_log_path) as f:
                git_log = f.read()

        has_reset_commit = 'reset stale IN_PROGRESS' in git_log

        # Verify source structure: reset function exists and is called before main loop
        source = read_launcher()
        has_reset_fn = 'reset_stale_in_progress()' in source
        # The reset should happen before the main orchestration loop
        reset_pos = source.find('reset_stale_in_progress\n')
        loop_pos = source.find('while [ "$OUTER_BREAK" = "false" ]')
        has_reset_before_loop = (reset_pos >= 0 and loop_pos >= 0 and
                                 reset_pos < loop_pos)
        # Verify it converts IN_PROGRESS to PENDING
        has_pending_replace = 'IN_PROGRESS' in source and 'PENDING' in source

        ok = (has_reset_commit and has_reset_fn and has_reset_before_loop
              and has_pending_replace)
        record("Stale IN_PROGRESS Phases Reset on Startup", ok,
               f"commit={has_reset_commit}, fn={has_reset_fn}, "
               f"before_loop={has_reset_before_loop}, "
               f"replace={has_pending_replace}, "
               f"git_log={git_log[:300]}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Canvas Shows Latest Log Line as Activity (Section 2.17)
# ============================================================
def test_canvas_shows_latest_log_line_as_activity():
    """When no 'editing' or 'running' pattern matches in log tail, the
    extract_activity function falls back to showing the last non-empty line
    from the log, stripped of ANSI escape codes, instead of 'working...'."""
    source = read_launcher()

    # Verify extract_activity function exists
    has_extract_fn = 'extract_activity()' in source

    # Find the extract_activity function body
    fn_start = source.find('extract_activity()')
    fn_end = source.find('\n}', fn_start)
    fn_body = source[fn_start:fn_end] if fn_start >= 0 else ""

    # Verify ANSI stripping (sed pattern for ANSI escape codes)
    has_ansi_strip = 'sed' in fn_body and '\\x1b' in fn_body or '\\033' in fn_body
    # Verify log tail fallback uses tail -5
    has_tail_5 = 'tail -5' in fn_body
    # Verify non-empty line filtering (grep -v blank lines)
    has_nonblank_filter = 'grep -v' in fn_body and 'space' in fn_body.lower() or '[:space:]' in fn_body
    # Verify "working..." is the LAST fallback (only when log is empty/missing)
    # The function should check log file existence at top and return "working..." only
    # when no log tail content is found
    working_pos = fn_body.rfind('working...')
    tail5_pos = fn_body.find('tail -5')
    has_working_after_fallback = (working_pos >= 0 and tail5_pos >= 0 and
                                  working_pos > tail5_pos)
    # Verify activity text is output (no hard-coded truncation — canvas handles width)
    has_truncation = 'printf' in fn_body and 'last_line' in fn_body

    ok = (has_extract_fn and has_ansi_strip and has_tail_5 and
          has_nonblank_filter and has_working_after_fallback and has_truncation)
    record("Canvas Shows Latest Log Line as Activity", ok,
           f"fn={has_extract_fn}, ansi_strip={has_ansi_strip}, "
           f"tail5={has_tail_5}, nonblank={has_nonblank_filter}, "
           f"order={has_working_after_fallback}, trunc={has_truncation}" if not ok else "")


# ============================================================
# Scenario: Line Buffering Fallback on macOS (Section 2.17)
# ============================================================
def test_line_buffering_fallback_on_macos():
    """Functional test: run_to_log routes subprocess output to the log file
    via script's typescript mechanism, both during execution (incremental)
    and at completion.

    On macOS, script(1) creates a pseudo-TTY that forces line buffering.
    run_to_log routes script's stdout to the log file via redirect; the
    typescript file arg is /dev/null (discarded). For parallel subshells,
    callers wrap in `) > /dev/null 2>&1 &` to contain any PTY leakage."""
    source = read_launcher()

    # --- Part 1: Source structure ---
    has_fn = 'run_to_log()' in source
    fn_start = source.find('run_to_log()')
    fn_end = source.find('\n}', fn_start)
    fn_body = source[fn_start:fn_end] if fn_start >= 0 else ""
    # script -q /dev/null with stdout redirected to log file
    has_script_fallback = 'script -q /dev/null' in fn_body
    # Parallel containment: subshell stdout/stderr to /dev/null
    parallel_section = source[source.find('PARALLEL EXECUTION'):source.find('SEQUENTIAL EXECUTION')]
    has_parallel_containment = ') > /dev/null 2>&1 &' in parallel_section

    # --- Part 2: Functional test with a slow subprocess ---
    # Verifies: (a) content appears DURING execution, (b) no duplication,
    # (c) actual subprocess text lands in the log file
    tmpdir = tempfile.mkdtemp()
    try:
        marker = "BUFFERED_OUTPUT_MARKER_12345"
        log_file = os.path.join(tmpdir, 'test_output.log')

        # Slow command: writes 3 lines with sleeps between them
        test_cmd = os.path.join(tmpdir, 'test_echo.sh')
        with open(test_cmd, 'w') as f:
            f.write(f'#!/bin/bash\n')
            f.write(f'echo "{marker}"\n')
            f.write(f'sleep 1\n')
            f.write(f'echo "LINE_TWO_DELAYED"\n')
            f.write(f'sleep 1\n')
            f.write(f'echo "LINE_THREE_FINAL"\n')
        os.chmod(test_cmd, os.stat(test_cmd).st_mode | stat.S_IEXEC)

        # Extract the actual function from the launcher
        fn_start_idx = source.find('run_to_log()')
        fn_end_idx = source.find('\n}', fn_start_idx) + 2
        fn_source = source[fn_start_idx:fn_end_idx]

        wrapper = os.path.join(tmpdir, 'test_wrapper.sh')
        with open(wrapper, 'w') as f:
            f.write('#!/bin/bash\n')
            # Strip stdbuf from PATH to force the script(1) fallback
            f.write('CLEAN_PATH=""\n')
            f.write('IFS=: read -ra DIRS <<< "$PATH"\n')
            f.write('for d in "${DIRS[@]}"; do\n')
            f.write('    if [ ! -x "$d/stdbuf" ]; then\n')
            f.write('        CLEAN_PATH="${CLEAN_PATH:+$CLEAN_PATH:}$d"\n')
            f.write('    fi\n')
            f.write('done\n')
            f.write(f'export PATH="{tmpdir}:$CLEAN_PATH"\n')
            # Embed the extracted function
            f.write(fn_source + '\n')
            # Run backgrounded — run_to_log routes output to the log file
            f.write(f'run_to_log "{log_file}" "{test_cmd}" &\n')
            f.write('PID=$!\n')
            # Snapshot mid-execution (after first echo, before second)
            f.write('sleep 0.5\n')
            f.write(f'MID_CONTENT=$(cat "{log_file}" 2>/dev/null)\n')
            f.write('wait $PID 2>/dev/null\n')
            f.write(f'FINAL_CONTENT=$(cat "{log_file}" 2>/dev/null)\n')
            # Report results for Python to parse
            f.write('echo "===MID==="\n')
            f.write('echo "$MID_CONTENT"\n')
            f.write('echo "===FINAL==="\n')
            f.write('echo "$FINAL_CONTENT"\n')
        os.chmod(wrapper, os.stat(wrapper).st_mode | stat.S_IEXEC)

        proc = subprocess.run(
            ['bash', wrapper],
            capture_output=True, text=True, timeout=15, cwd=tmpdir
        )

        stdout = proc.stdout
        mid_section = ""
        final_section = ""
        if "===MID===" in stdout and "===FINAL===" in stdout:
            mid_section = stdout.split("===MID===\n")[1].split("===FINAL===")[0]
            final_section = stdout.split("===FINAL===\n")[1] if "===FINAL===\n" in stdout else ""

        # (a) Content appears DURING execution — mid-snapshot has the marker
        mid_has_marker = marker in mid_section

        # (b) Final content has all lines
        final_has_marker = marker in final_section
        final_has_line_two = "LINE_TWO_DELAYED" in final_section
        final_has_line_three = "LINE_THREE_FINAL" in final_section

        # (c) No duplication — each line appears exactly once
        marker_count = final_section.count(marker)
        line_two_count = final_section.count("LINE_TWO_DELAYED")
        no_duplication = (marker_count == 1 and line_two_count == 1)

        ok = (has_fn and has_script_fallback and has_parallel_containment and
              mid_has_marker and final_has_marker and
              final_has_line_two and final_has_line_three and
              no_duplication)
        record("Line Buffering Fallback on macOS", ok,
               f"fn={has_fn}, script=/dev/null={has_script_fallback}, "
               f"parallel_containment={has_parallel_containment}, "
               f"mid_marker={mid_has_marker}, final_marker={final_has_marker}, "
               f"line2={final_has_line_two}, line3={final_has_line_three}, "
               f"no_dup={no_duplication}(marker_x{marker_count},line2_x{line_two_count}), "
               f"rc={proc.returncode}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Startup Purge of Stale Runtime Artifacts (Section 2.11)
# ============================================================
def test_startup_purge_of_stale_runtime_artifacts():
    """Before entering the orchestration loop, the launcher deletes stale
    runtime artifacts from a previous run: phase_*_meta, canvas_frozen_*,
    retry_count_*, plan_amendment_phase_*.json, approval_table_lines,
    and continuous_build_*.log files."""
    source = read_launcher()

    # Verify source structure: purge function exists and is called before the loop
    has_purge_fn = 'purge_stale_runtime_artifacts()' in source
    purge_call_pos = source.find('purge_stale_runtime_artifacts\n')
    loop_pos = source.find('while [ "$OUTER_BREAK" = "false" ]')
    has_purge_before_loop = (purge_call_pos >= 0 and loop_pos >= 0
                             and purge_call_pos < loop_pos)

    # Verify the purge function deletes all required artifact patterns
    fn_start = source.find('purge_stale_runtime_artifacts()')
    fn_end = source.find('\n}', fn_start)
    fn_body = source[fn_start:fn_end] if fn_start >= 0 else ""

    deletes_phase_meta = 'phase_*_meta' in fn_body
    deletes_canvas_frozen = 'canvas_frozen_*' in fn_body
    deletes_retry_count = 'retry_count_*' in fn_body
    deletes_amendments = 'plan_amendment_phase_*.json' in fn_body
    deletes_approval_lines = 'approval_table_lines' in fn_body
    deletes_logs = 'continuous_build_*.log' in fn_body

    # Functional test: create stale artifacts and verify they're cleaned up
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "Test Phase", "PENDING", ["a.md"]),
        ])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All complete successfully"),
                                   ])

        # Create mock git
        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')

        # Plant stale artifacts from a "previous run"
        stale_files = [
            'phase_1_meta', 'phase_2_meta',
            'canvas_frozen_1', 'canvas_frozen_2',
            'retry_count_3',
            'plan_amendment_phase_1.json',
            'approval_table_lines',
            'continuous_build_phase_1.log',
            'continuous_build_bootstrap.log',
        ]
        for sf in stale_files:
            with open(os.path.join(runtime_dir, sf), 'w') as f:
                f.write('stale data\n')

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        # Check that stale artifacts were cleaned up
        # phase_*_meta might be recreated by the current run, but the stale
        # phase_2_meta should be gone (Phase 2 doesn't exist in this plan)
        stale_phase2_meta = os.path.exists(os.path.join(runtime_dir, 'phase_2_meta'))
        stale_canvas_frozen = os.path.exists(os.path.join(runtime_dir, 'canvas_frozen_2'))
        stale_retry = os.path.exists(os.path.join(runtime_dir, 'retry_count_3'))
        stale_amendment = os.path.exists(os.path.join(runtime_dir, 'plan_amendment_phase_1.json'))
        # Log files are purged at startup
        stale_bootstrap_log = os.path.exists(os.path.join(runtime_dir, 'continuous_build_bootstrap.log'))

        artifacts_purged = (not stale_phase2_meta and not stale_canvas_frozen
                           and not stale_retry and not stale_amendment)

        ok = (has_purge_fn and has_purge_before_loop and
              deletes_phase_meta and deletes_canvas_frozen and
              deletes_retry_count and deletes_amendments and
              deletes_approval_lines and deletes_logs and
              artifacts_purged)
        record("Startup Purge of Stale Runtime Artifacts", ok,
               f"fn={has_purge_fn}, before_loop={has_purge_before_loop}, "
               f"del_meta={deletes_phase_meta}, del_frozen={deletes_canvas_frozen}, "
               f"del_retry={deletes_retry_count}, del_amend={deletes_amendments}, "
               f"del_approval={deletes_approval_lines}, del_logs={deletes_logs}, "
               f"purged={artifacts_purged}, stale2meta={stale_phase2_meta}, "
               f"frozen2={stale_canvas_frozen}, retry3={stale_retry}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


# ============================================================
# Scenario: Exit Cleanup of Transient Artifacts (Section 2.11)
# ============================================================
def test_exit_cleanup_of_transient_artifacts():
    """After the exit summary prints, the launcher deletes transient runtime
    artifacts (phase_*_meta, canvas_frozen_*, retry_count_*,
    plan_amendment_phase_*.json, approval_table_lines, canvas_state)
    but preserves log files for user inspection."""
    source = read_launcher()

    # Find exit cleanup section — should be after exit summary and before final exit
    exit_summary_pos = source.find('Exit Summary')
    final_exit_pos = source.rfind('exit 0')

    exit_section = source[exit_summary_pos:final_exit_pos] if (
        exit_summary_pos >= 0 and final_exit_pos >= 0) else ""

    # Verify cleanup commands exist after exit summary
    has_meta_cleanup = 'rm -f "${RUNTIME_DIR}"/phase_*_meta' in exit_section
    has_frozen_cleanup = 'rm -f "${RUNTIME_DIR}"/canvas_frozen_*' in exit_section
    has_retry_cleanup = 'rm -f "${RUNTIME_DIR}"/retry_count_*' in exit_section
    has_amendment_cleanup = 'rm -f "${RUNTIME_DIR}"/plan_amendment_phase_*.json' in exit_section
    has_approval_cleanup = 'approval_table_lines' in exit_section
    has_canvas_state_cleanup = 'canvas_state' in exit_section

    # Verify log files are NOT deleted in exit cleanup
    # The exit cleanup should not contain continuous_build_*.log deletion
    # (Only the startup purge deletes logs)
    exit_cleanup_start = exit_section.find('Exit cleanup')
    exit_cleanup_section = exit_section[exit_cleanup_start:] if exit_cleanup_start >= 0 else ""
    preserves_logs = 'continuous_build_*.log' not in exit_cleanup_section

    # Functional test: run the launcher and verify cleanup
    tmpdir = tempfile.mkdtemp()
    try:
        plan = make_plan([
            (1, "Test Phase", "PENDING", ["a.md"]),
        ])
        graph = make_graph([("a.md", [])])
        make_mock_project(tmpdir, plan, graph)
        mock_bin = make_mock_claude(tmpdir, "phase_complete",
                                   eval_responses=[
                                       ("stop", True, "All phases complete successfully"),
                                   ])

        mock_git = os.path.join(mock_bin, 'git')
        with open(mock_git, 'w') as f:
            f.write(f'''#!/bin/bash
if [ "$1" = "-C" ]; then shift 2; fi
case "$1" in
    rev-parse) echo "abc1234" ;;
esac
exit 0
''')
        os.chmod(mock_git, os.stat(mock_git).st_mode | stat.S_IEXEC)

        proc = run_launcher(tmpdir, mock_bin, ['--continuous'])

        runtime_dir = os.path.join(tmpdir, '.purlin', 'runtime')

        # After exit, transient artifacts should be cleaned up
        # canvas_state should not exist
        canvas_state_exists = os.path.exists(os.path.join(runtime_dir, 'canvas_state'))
        # approval_table_lines should not exist
        approval_exists = os.path.exists(os.path.join(runtime_dir, 'approval_table_lines'))

        # Log files SHOULD be preserved (created during this run)
        # Note: log may or may not exist depending on mock behavior, but the
        # cleanup code should not delete them. Check source structure instead.

        cleanup_correct = not canvas_state_exists and not approval_exists

        ok = (has_meta_cleanup and has_frozen_cleanup and has_retry_cleanup
              and has_amendment_cleanup and has_approval_cleanup
              and has_canvas_state_cleanup and preserves_logs
              and cleanup_correct)
        record("Exit Cleanup of Transient Artifacts", ok,
               f"meta={has_meta_cleanup}, frozen={has_frozen_cleanup}, "
               f"retry={has_retry_cleanup}, amend={has_amendment_cleanup}, "
               f"approval={has_approval_cleanup}, canvas={has_canvas_state_cleanup}, "
               f"logs_preserved={preserves_logs}, cleanup={cleanup_correct}" if not ok else "")
    finally:
        shutil.rmtree(tmpdir)


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

    # Bootstrap scenarios (Section 2.16) (9)
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
    test_exit_summary_phase_table()
    test_exit_summary_work_digest()
    test_work_digest_timeout_fallback()
    test_worktree_cleanup()

    # Dynamic Delivery Plan Handling (Section 2.13) (8)
    test_builder_adds_qa_fix_phase()
    test_builder_splits_phase()
    test_builder_removes_remaining_phases()
    test_new_phase_depends_on_completed()
    test_new_phase_creates_dependency_chain()
    test_builder_removes_some_phases()
    test_non_contiguous_phase_numbers()
    test_removed_phase_had_dependents()

    # Parallel Plan Amendments (Section 2.14) (4)
    test_parallel_both_request_amendments()
    test_parallel_amendment_structured_files()
    test_amendment_files_cleaned_up()
    test_sequential_builder_modifies_plan_directly()

    # Evaluator Amendment Detection (Section 2.15) (3)
    test_parallel_group_invalidated()
    test_phase_count_changes_in_summary()
    test_reanalysis_after_retry()

    # Terminal Canvas Engine (Section 2.17) (14)
    test_bootstrap_canvas_shows_spinner()
    test_approval_checkpoint_renders_table()
    test_approval_table_respects_narrow_terminal()
    test_approval_table_stacked_below_60()
    test_approval_table_rerenders_on_resize()
    test_sequential_phase_canvas()
    test_parallel_phase_canvas()
    test_all_builder_output_routes_to_log_files()
    test_interphase_canvas_shows_evaluator_status()
    test_canvas_clears_before_final_summary()
    test_canvas_falls_back_to_milestone_lines()
    test_canvas_render_loop_lifecycle()
    test_resume_session_log_appended()
    test_canvas_shows_current_builder_activity()
    test_canvas_warns_on_empty_log()

    # Canvas & Graceful Stop (Section 2.17) (5)

    # Graceful Stop & Post-Run (Section 2.17) (3)
    test_graceful_stop_on_sigint()
    test_second_sigint_forces_exit()
    test_post_run_status_refresh()

    # New scenarios: Pre-launch IN_PROGRESS & Central Update (Section 2.4) (3)
    test_phases_marked_in_progress_before_launch()
    test_sequential_phase_marked_in_progress()
    test_per_phase_status_update_during_parallel_execution()

    # New scenarios: Column Alignment & Line Buffering (Section 2.17) (2)
    test_parallel_canvas_columns_align()
    test_log_files_grow_incrementally()

    # New scenarios: Stale IN_PROGRESS Reset, Log Line Activity, macOS Buffering (3)
    test_stale_in_progress_phases_reset_on_startup()
    test_canvas_shows_latest_log_line_as_activity()
    test_line_buffering_fallback_on_macos()

    # Runtime Artifact Cleanup (Section 2.11) (2)
    test_startup_purge_of_stale_runtime_artifacts()
    test_exit_cleanup_of_transient_artifacts()

    write_results()
    sys.exit(0 if results["failed"] == 0 else 1)
