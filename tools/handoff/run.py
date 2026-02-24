"""Handoff checklist runner.

Resolves and evaluates handoff steps for the current worktree.
Uses tools/release/resolve.py with checklist_type="handoff".
No role filtering — all steps apply to all agents.
"""
import argparse
import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import resolve.py from the framework's release tools (sibling directory)
RELEASE_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'release'))
if RELEASE_DIR not in sys.path:
    sys.path.insert(0, RELEASE_DIR)

# Project root detection (Section 2.11 of submodule_bootstrap.md)
_env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
if _env_root and os.path.isdir(_env_root):
    PROJECT_ROOT = _env_root
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
    for depth in ('../../../', '../../'):
        candidate = os.path.abspath(os.path.join(SCRIPT_DIR, depth))
        if os.path.exists(os.path.join(candidate, '.purlin')):
            PROJECT_ROOT = candidate
            break


def evaluate_step(step, project_root):
    """Evaluate a step's code field.

    Returns: ("PASS", None) | ("FAIL", error_msg) | ("PENDING", None)
    """
    code = step.get("code")
    if not code:
        return "PENDING", None

    try:
        result = subprocess.run(
            code, shell=True, capture_output=True, text=True,
            cwd=project_root, timeout=30
        )
        if result.returncode == 0:
            return "PASS", None
        else:
            err = (result.stderr.strip() or result.stdout.strip()
                   or f"Exit code {result.returncode}")
            return "FAIL", err
    except subprocess.TimeoutExpired:
        return "FAIL", "Timed out after 30 seconds"
    except Exception as e:
        return "FAIL", str(e)


def run_handoff(project_root):
    """Run the handoff checklist. Returns exit code."""
    from resolve import resolve_checklist

    # Compute explicit paths relative to the given project root
    global_path = os.path.join(
        project_root, "tools", "handoff", "global_steps.json")
    local_path = os.path.join(
        project_root, ".purlin", "handoff", "local_steps.json")
    config_path = os.path.join(
        project_root, ".purlin", "handoff", "config.json")
    if not os.path.exists(config_path):
        config_path = None

    resolved, warnings, errors = resolve_checklist(
        global_path=global_path,
        local_path=local_path,
        config_path=config_path,
        checklist_type="handoff",
    )

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    steps = resolved

    if not steps:
        print("No handoff steps found.")
        return 0

    print(f"Handoff checklist ({len(steps)} steps):\n")

    # Evaluate each step
    results = []
    for step in steps:
        if not step.get("enabled", True):
            continue

        status, err = evaluate_step(step, project_root)
        results.append((step, status, err))

        name = step.get("friendly_name", step.get("id", "?"))
        if status == "PASS":
            print(f"  PASS  {name}")
        elif status == "FAIL":
            print(f"  FAIL  {name}: {err}")
        else:
            instructions = step.get("agent_instructions",
                                    "Manual verification required.")
            print(f"  PENDING  {name}")
            print(f"    -> {instructions}")

    # Summary
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    pending = sum(1 for _, s, _ in results if s == "PENDING")

    print(f"\nSummary: {passed} passed, {failed} failed, {pending} pending")

    if failed > 0 or pending > 0:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Handoff checklist runner")
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project_root = args.project_root or PROJECT_ROOT

    sys.exit(run_handoff(project_root))


if __name__ == "__main__":
    main()
