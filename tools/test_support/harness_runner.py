#!/usr/bin/env python3
"""Harness Runner Framework.

Reads a single scenario JSON file and executes it based on harness_type.
Writes enriched tests.json to tests/<feature_name>/tests.json.

Consumer-facing, submodule-safe.
See features/regression_testing.md Section 2.8 for full specification.

Usage:
    python3 tools/test_support/harness_runner.py <scenario_json_path> [--project-root <path>]
"""

import json
import os
import re
import subprocess
import sys


def resolve_project_root(explicit=None):
    """Resolve project root: explicit > env var > climbing fallback."""
    if explicit:
        return os.path.abspath(explicit)

    env_root = os.environ.get('PURLIN_PROJECT_ROOT')
    if env_root:
        return os.path.abspath(env_root)

    # Climbing fallback: prefer furthest features/ directory (submodule path)
    d = os.path.dirname(os.path.abspath(__file__))
    candidate = None
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, 'features')):
            candidate = d
        d = os.path.dirname(d)
    if candidate:
        return candidate

    print("Error: Could not detect project root", file=sys.stderr)
    sys.exit(1)


def run_fixture_checkout(project_root, fixture_tag):
    """Check out a fixture tag. Returns the checkout directory path."""
    fixture_sh = os.path.join(project_root, 'tools', 'test_support', 'fixture.sh')
    if not os.path.isfile(fixture_sh):
        return None

    # Resolve fixture repo path
    repo_path = os.path.join(project_root, '.purlin', 'runtime', 'fixture-repo')
    if not os.path.isdir(repo_path):
        return None

    try:
        result = subprocess.run(
            ['bash', fixture_sh, 'checkout', repo_path, fixture_tag],
            capture_output=True, text=True, timeout=60,
            cwd=project_root,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root},
        )
        if result.returncode == 0:
            checkout_dir = result.stdout.strip()
            if checkout_dir and os.path.isdir(checkout_dir):
                return checkout_dir
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def run_fixture_cleanup(project_root, checkout_dir):
    """Clean up a fixture checkout directory."""
    if not checkout_dir:
        return
    fixture_sh = os.path.join(project_root, 'tools', 'test_support', 'fixture.sh')
    if not os.path.isfile(fixture_sh):
        return
    try:
        subprocess.run(
            ['bash', fixture_sh, 'cleanup', checkout_dir],
            capture_output=True, text=True, timeout=30,
            cwd=project_root,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root},
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def run_setup_commands(commands, cwd=None):
    """Execute setup commands in order. Returns True if all succeed."""
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=60, cwd=cwd,
            )
            if result.returncode != 0:
                return False
        except (subprocess.TimeoutExpired, OSError):
            return False
    return True


def execute_agent_behavior(scenario, project_root, fixture_dir=None):
    """Execute an agent_behavior scenario. Returns (output, success)."""
    role = scenario.get('role', 'BUILDER')
    prompt = scenario.get('prompt', '')

    if not prompt:
        return ("Error: agent_behavior scenario requires 'prompt' field", False)

    # Build claude --print command
    cmd = ['claude', '--print', '-p', prompt]

    # Set working directory to fixture dir if available
    cwd = fixture_dir or project_root

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            cwd=cwd,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root},
        )
        output = result.stdout + result.stderr
        return (output, result.returncode == 0)
    except subprocess.TimeoutExpired:
        return ("Error: agent_behavior scenario timed out after 300s", False)
    except FileNotFoundError:
        return ("Error: 'claude' command not found", False)
    except OSError as e:
        return (f"Error: {e}", False)


def execute_web_test(scenario, project_root):
    """Execute a web_test scenario. Returns (output, success)."""
    url = scenario.get('web_test_url', '')
    if not url:
        return ("Error: web_test scenario requires 'web_test_url' field", False)

    # Web tests delegate to the web test infrastructure
    # For now, attempt a basic HTTP check and assertion evaluation
    try:
        import urllib.request
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=30) as resp:
            output = resp.read().decode('utf-8', errors='replace')
            return (output, resp.status == 200)
    except Exception as e:
        return (f"Error: web_test failed: {e}", False)


def execute_custom_script(scenario, project_root):
    """Execute a custom_script scenario. Returns (output, success, tests_json_path)."""
    script_path = scenario.get('script_path', '')
    if not script_path:
        return ("Error: custom_script scenario requires 'script_path' field", False, None)

    abs_script = os.path.join(project_root, script_path)
    if not os.path.isfile(abs_script):
        return (f"Error: script not found: {abs_script}", False, None)

    try:
        result = subprocess.run(
            ['bash', abs_script, '--write-results'],
            capture_output=True, text=True, timeout=300,
            cwd=project_root,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root},
        )
        output = result.stdout + result.stderr
        return (output, result.returncode == 0, None)
    except subprocess.TimeoutExpired:
        return ("Error: custom_script timed out after 300s", False, None)
    except OSError as e:
        return (f"Error: {e}", False, None)


def evaluate_assertions(output, assertions):
    """Evaluate assertions against captured output.
    Returns list of (assertion, passed, excerpt).
    """
    results = []
    for assertion in assertions:
        pattern = assertion.get('pattern', '')
        try:
            match = re.search(pattern, output, re.MULTILINE | re.DOTALL)
            passed = match is not None
        except re.error:
            passed = False

        excerpt = ''
        if not passed:
            excerpt = output[:500] if output else '(empty output)'

        results.append((assertion, passed, excerpt))
    return results


def process_scenario_file(scenario_path, project_root):
    """Process a single scenario JSON file. Returns (feature_name, details, passed, failed)."""
    with open(scenario_path) as f:
        data = json.load(f)

    feature_name = data.get('feature', '')
    harness_type = data.get('harness_type', '')
    scenarios = data.get('scenarios', [])
    details = []
    total_passed = 0
    total_failed = 0

    for scenario in scenarios:
        name = scenario.get('name', 'unnamed')
        fixture_tag = scenario.get('fixture_tag')
        setup_commands = scenario.get('setup_commands', [])
        assertions = scenario.get('assertions', [])

        fixture_dir = None

        # Step a: Fixture checkout
        if fixture_tag:
            fixture_dir = run_fixture_checkout(project_root, fixture_tag)

        # Step b: Setup commands
        if setup_commands:
            setup_cwd = fixture_dir or project_root
            run_setup_commands(setup_commands, cwd=setup_cwd)

        # Step c: Dispatch based on harness_type
        output = ''
        exec_success = True

        if harness_type == 'agent_behavior':
            output, exec_success = execute_agent_behavior(
                scenario, project_root, fixture_dir)
        elif harness_type == 'web_test':
            output, exec_success = execute_web_test(scenario, project_root)
        elif harness_type == 'custom_script':
            output, exec_success, _ = execute_custom_script(
                scenario, project_root)
        else:
            output = f"Error: unknown harness_type: {harness_type}"
            exec_success = False

        # Step d: Evaluate assertions
        if assertions and exec_success:
            assertion_results = evaluate_assertions(output, assertions)
        elif assertions:
            # Execution failed, all assertions fail
            assertion_results = [
                (a, False, output[:500] if output else '(execution failed)')
                for a in assertions
            ]
        else:
            # No assertions defined - pass/fail based on execution
            assertion_results = []

        # Build detail entries - one per assertion
        if assertion_results:
            for assertion, passed, excerpt in assertion_results:
                tier = assertion.get('tier')
                context = assertion.get('context', '')
                detail = {
                    'name': f"{name}:{context}" if context else name,
                    'status': 'PASS' if passed else 'FAIL',
                    'scenario_ref': f"features/{feature_name}.md:{name}",
                    'expected': context,
                }
                if tier in (1, 2, 3):
                    detail['assertion_tier'] = tier
                if not passed:
                    detail['actual_excerpt'] = excerpt
                    total_failed += 1
                else:
                    total_passed += 1
                details.append(detail)
        else:
            # No assertions - single entry based on execution success
            detail = {
                'name': name,
                'status': 'PASS' if exec_success else 'FAIL',
                'scenario_ref': f"features/{feature_name}.md:{name}",
                'expected': 'Scenario executes successfully',
            }
            if not exec_success:
                detail['actual_excerpt'] = output[:500] if output else '(no output)'
                total_failed += 1
            else:
                total_passed += 1
            details.append(detail)

        # Step e: Fixture cleanup
        if fixture_dir:
            run_fixture_cleanup(project_root, fixture_dir)

    return feature_name, details, total_passed, total_failed


def write_results(feature_name, details, passed, failed, project_root, test_file=''):
    """Write enriched tests.json to tests/<feature_name>/tests.json."""
    total = passed + failed
    status = 'PASS' if failed == 0 and total > 0 else 'FAIL'

    results = {
        'status': status,
        'passed': passed,
        'failed': failed,
        'total': total,
        'test_file': test_file,
        'details': details,
    }

    output_dir = os.path.join(project_root, 'tests', feature_name)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'tests.json')

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Harness Runner: execute scenario JSON files for regression testing')
    parser.add_argument('scenario_json', help='Path to the scenario JSON file')
    parser.add_argument('--project-root', help='Explicit project root path')
    args = parser.parse_args()

    project_root = resolve_project_root(args.project_root)
    scenario_path = args.scenario_json

    if not os.path.isabs(scenario_path):
        scenario_path = os.path.join(project_root, scenario_path)

    if not os.path.isfile(scenario_path):
        print(f"Error: scenario file not found: {scenario_path}", file=sys.stderr)
        sys.exit(1)

    try:
        feature_name, details, passed, failed = process_scenario_file(
            scenario_path, project_root)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: invalid scenario file: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = write_results(
        feature_name, details, passed, failed, project_root,
        test_file=os.path.relpath(scenario_path, project_root))

    total = passed + failed
    status = 'PASS' if failed == 0 and total > 0 else 'FAIL'
    print(f"{status}: {passed}/{total} passed for {feature_name}")
    print(f"Results: {output_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
