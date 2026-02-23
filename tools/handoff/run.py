"""Handoff checklist runner.

Resolves and evaluates handoff steps for a specific role.
Uses tools/release/resolve.py with checklist_type="handoff".
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


def filter_by_role(steps, role):
    """Filter steps to only those applicable to the given role."""
    result = []
    for step in steps:
        roles = step.get("roles")
        if roles is None:
            continue
        if "all" in roles or role in roles:
            result.append(step)
    return result


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


def infer_role_from_branch(project_root):
    """Infer the agent role from the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=project_root
        )
        branch = result.stdout.strip()
    except Exception:
        return None

    if branch.startswith("spec/"):
        return "architect"
    elif branch.startswith("build/"):
        return "builder"
    elif branch.startswith("qa/"):
        return "qa"
    return None


def run_handoff(role, project_root):
    """Run the handoff checklist for a role. Returns exit code."""
    from resolve import resolve_checklist

    # Compute explicit paths relative to the given project root
    global_path = os.path.join(
        project_root, "tools", "handoff", "global_steps.json")
    local_path = os.path.join(
        project_root, ".purlin", "handoff", "local_steps.json")
    config_path = os.path.join(
        project_root, ".purlin", "handoff", role, "config.json")
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

    # Filter by role
    steps = filter_by_role(resolved, role)

    if not steps:
        print(f"No handoff steps found for role: {role}")
        return 0

    print(f"Handoff checklist for {role} ({len(steps)} steps):\n")

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
    parser.add_argument("--role", choices=["architect", "builder", "qa"],
                        default=None)
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project_root = args.project_root or PROJECT_ROOT

    role = args.role
    if role is None:
        role = infer_role_from_branch(project_root)
        if role is None:
            print("Error: Cannot infer role from branch name. "
                  "Use --role <architect|builder|qa>", file=sys.stderr)
            sys.exit(1)

    sys.exit(run_handoff(role, project_root))


if __name__ == "__main__":
    main()
