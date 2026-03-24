#!/usr/bin/env python3
"""Harness Runner Framework.

Reads a single scenario JSON file and executes it based on harness_type.
Writes enriched regression.json to tests/<feature_name>/regression.json.

Consumer-facing, submodule-safe.
See features/regression_testing.md Section 2.8 for full specification.

Usage:
    python3 tools/test_support/harness_runner.py <scenario_json_path> [--project-root <path>]
"""

import atexit
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request


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


# --- Progress output (Section 2.8 mandatory) ---

TIME_ESTIMATES = {
    'agent_behavior': (30, 60),   # seconds per scenario
    'web_test': (5, 10),
    'custom_script': (10, 30),
}


def format_time_estimate(harness_type, count):
    """Format a human-readable time estimate for a suite."""
    lo_per, hi_per = TIME_ESTIMATES.get(harness_type, (10, 30))
    lo_total = lo_per * count
    hi_total = hi_per * count
    if hi_total < 60:
        return f"~{lo_total}-{hi_total}s"
    lo_min = math.ceil(lo_total / 60)
    hi_min = math.ceil(hi_total / 60)
    if lo_min == hi_min:
        return f"~{lo_min} min"
    return f"~{lo_min}-{hi_min} min"


def format_elapsed(seconds):
    """Format elapsed seconds as human-readable string."""
    s = int(seconds)
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{s}s"


class ProgressReporter:
    """Mandatory progress output to stderr (Section 2.8)."""

    def __init__(self, feature_name, harness_type, scenario_count):
        self.feature_name = feature_name
        self.harness_type = harness_type
        self.total = scenario_count
        self.start_time = time.time()
        self.scenarios_passed = 0
        self.scenarios_failed = 0

    def print_startup(self):
        est = format_time_estimate(self.harness_type, self.total)
        print(
            f"{self.feature_name}: {self.total} scenarios "
            f"({self.harness_type}, {est})",
            file=sys.stderr, flush=True,
        )

    def print_running(self, index, name):
        print(
            f"  [{index}/{self.total}] {name} ... (running)",
            file=sys.stderr, flush=True,
        )

    def print_result(self, index, name, passed, elapsed_seconds):
        status = "PASS" if passed else "FAIL"
        if passed:
            self.scenarios_passed += 1
        else:
            self.scenarios_failed += 1
        print(
            f"  [{index}/{self.total}] {name} ... "
            f"{status} ({format_elapsed(elapsed_seconds)})",
            file=sys.stderr, flush=True,
        )

    def print_completion(self, output_path):
        elapsed = format_elapsed(time.time() - self.start_time)
        print(
            f"{self.feature_name}: {self.scenarios_passed}/{self.total} "
            f"passed ({elapsed} total)",
            file=sys.stderr, flush=True,
        )
        print(f"Results: {output_path}", file=sys.stderr, flush=True)


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


def parse_port_from_url(url):
    """Extract port number from a URL like http://localhost:9086/path."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.port
    except (ValueError, AttributeError):
        return None


def check_server_responsive(port):
    """Check if an HTTP server is responsive on the given port."""
    try:
        req = urllib.request.Request(
            f'http://localhost:{port}/status.json', method='GET')
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_free_port():
    """Get a free port from the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def poll_server_ready(port, attempts=10, interval=1):
    """Poll for server readiness. Returns True if server responds within attempts."""
    for i in range(attempts):
        if check_server_responsive(port):
            return True
        if i < attempts - 1:
            time.sleep(interval)
    return False


def read_port_file(root_dir):
    """Read the CDD port file. Returns port number or None."""
    port_file = os.path.join(root_dir, '.purlin', 'runtime', 'cdd.port')
    try:
        with open(port_file) as f:
            return int(f.read().strip())
    except (IOError, OSError, ValueError):
        return None


def start_cdd_server(project_root, port=None, target_dir=None):
    """Start a CDD server via start.sh.

    Args:
        project_root: The actual project root (where tools/ lives).
        port: Port to use (None for auto-select).
        target_dir: Directory to serve (fixture_dir or project_root).
                    If None, uses project_root.

    Returns:
        The port the server started on, or None if failed.
    """
    target = target_dir or project_root
    start_sh = os.path.join(project_root, 'tools', 'cdd', 'start.sh')

    if not os.path.isfile(start_sh):
        return None

    # Ensure .purlin/ exists in target dir (needed for start.sh root detection)
    os.makedirs(os.path.join(target, '.purlin'), exist_ok=True)

    cmd = ['bash', start_sh]
    if port:
        cmd.extend(['-p', str(port)])

    env = {**os.environ, 'PURLIN_PROJECT_ROOT': target}

    try:
        subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
            cwd=project_root, env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    # Read the actual port from the port file
    actual_port = read_port_file(target)
    if actual_port is None:
        return None

    # Poll for readiness (Section 2.8.1: 10 attempts, 1 second apart)
    if not poll_server_ready(actual_port):
        return None

    return actual_port


def stop_cdd_server(project_root, target_dir=None):
    """Stop the CDD server for a target directory."""
    target = target_dir or project_root
    stop_sh = os.path.join(project_root, 'tools', 'cdd', 'stop.sh')

    if not os.path.isfile(stop_sh):
        return

    env = {**os.environ, 'PURLIN_PROJECT_ROOT': target}

    try:
        subprocess.run(
            ['bash', stop_sh],
            capture_output=True, text=True, timeout=15,
            cwd=project_root, env=env,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def construct_system_prompt(fixture_dir, role):
    """Build the 4-layer system prompt from fixture instruction files.

    Returns path to temp file containing concatenated prompt, or None.
    Caller must delete the temp file after use.
    """
    layers = [
        os.path.join(fixture_dir, 'instructions', 'HOW_WE_WORK_BASE.md'),
        os.path.join(fixture_dir, 'instructions', f'{role}_BASE.md'),
        os.path.join(fixture_dir, '.purlin', 'HOW_WE_WORK_OVERRIDES.md'),
        os.path.join(fixture_dir, '.purlin', f'{role}_OVERRIDES.md'),
    ]

    content = ''
    for layer_path in layers:
        if os.path.isfile(layer_path):
            with open(layer_path) as f:
                content += f.read() + '\n\n'

    if not content.strip():
        return None

    fd, path = tempfile.mkstemp(suffix='.md', prefix='purlin_prompt_')
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path


def copy_skill_files(project_root, fixture_dir):
    """Copy .claude/commands/ from project root to fixture dir if absent."""
    src = os.path.join(project_root, '.claude', 'commands')
    dst = os.path.join(fixture_dir, '.claude', 'commands')
    if os.path.isdir(src) and not os.path.isdir(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src, dst)


def scan_fixture_features(fixture_dir):
    """Scan fixture features directory for lifecycle status.

    Returns dict with lists of feature labels grouped by status.
    """
    features_dir = os.path.join(fixture_dir, 'features')
    if not os.path.isdir(features_dir):
        return {'todo': [], 'testing': [], 'complete': []}

    result = {'todo': [], 'testing': [], 'complete': []}

    for fname in sorted(os.listdir(features_dir)):
        if not fname.endswith('.md'):
            continue
        if fname.endswith(('.impl.md', '.discoveries.md')):
            continue
        if fname.startswith(('arch_', 'design_', 'policy_')):
            continue

        fpath = os.path.join(features_dir, fname)
        try:
            with open(fpath) as f:
                content = f.read(2000)
        except (IOError, OSError):
            continue

        label_match = re.search(r'> Label:\s*"([^"]+)"', content)
        label = label_match.group(1) if label_match else fname[:-3]

        if '[TODO]' in content:
            result['todo'].append(label)
        elif '[TESTING]' in content:
            result['testing'].append(label)
        elif '[COMPLETE]' in content:
            result['complete'].append(label)

    return result


def build_print_mode_context(fixture_dir, project_root, role, prompt):
    """Build supplementary context for claude --print mode.

    In --print mode the model cannot use tools (Read, Bash, etc.).
    This pre-loads data that agents normally obtain via tool calls:
    command tables, feature status, and skill content.
    """
    sections = []
    role_lower = role.lower()

    # 1. Feature status FIRST (normally obtained via status.sh)
    #    Placed before the command table so the model outputs feature
    #    names early, before the long command table consumes output budget.
    status = scan_fixture_features(fixture_dir)
    total = sum(len(v) for v in status.values())
    if total > 0:
        lines = [f'# Pre-loaded: Project Status ({total} features)\n']
        lines.append(
            'CRITICAL: You MUST include these feature names in your '
            'output. Print "TODO: <name>" or "TESTING: <name>" for each '
            'feature listed below. Do this IMMEDIATELY after the command '
            'table. This is required — do NOT skip it.\n')
        if status['todo']:
            lines.append(f'TODO ({len(status["todo"])}):')
            for name in status['todo']:
                lines.append(f'  - {name}')
        if status['testing']:
            lines.append(f'TESTING ({len(status["testing"])}):')
            for name in status['testing']:
                lines.append(f'  - {name}')
        if status['complete']:
            lines.append(f'COMPLETE ({len(status["complete"])}):')
            for name in status['complete']:
                lines.append(f'  - {name}')
        sections.append('\n'.join(lines))

    # 2. Command table (normally obtained via Read tool at startup)
    for base in (fixture_dir, project_root):
        cmd_path = os.path.join(
            base, 'instructions', 'references', f'{role_lower}_commands.md')
        if os.path.isfile(cmd_path):
            try:
                with open(cmd_path) as f:
                    table_content = f.read()
                sections.append(
                    '# Pre-loaded: Command Table\n\n'
                    'Print the Main Branch Variant below VERBATIM '
                    '(including the ━━━ border characters) when starting '
                    'a session or when /pl-help is invoked.\n\n'
                    + table_content)
            except (IOError, OSError):
                pass
            break

    # 3. Skill content (for skill-dispatch prompts like /pl-help, /pl-status)
    if prompt.startswith('/'):
        skill_name = prompt.split()[0].lstrip('/')
        for base in (fixture_dir, project_root):
            skill_path = os.path.join(
                base, '.claude', 'commands', f'{skill_name}.md')
            if os.path.isfile(skill_path):
                try:
                    with open(skill_path) as f:
                        skill_content = f.read()
                    sections.append(
                        f'# Pre-loaded: Skill Content ({prompt})\n\n'
                        f'The user invoked `{prompt}`. Execute the skill '
                        f'instructions below.\n\n' + skill_content)
                except (IOError, OSError):
                    pass
                break

    # 4. Role enforcement reinforcement (compensates for missing
    #    tool-level guardrails in --print mode)
    role_mandates = {
        'ARCHITECT': (
            'You are the Architect. You have a ZERO CODE MANDATE: you MUST '
            'NEVER write, edit, fix, debug, or modify code files, scripts, '
            'or tests. This includes fixing imports, changing return values, '
            'updating variable names, or any other code change no matter '
            'how small. If the user asks you to fix, edit, or change ANY '
            'code file, you MUST REFUSE the request and explain that all '
            'code changes are Builder-owned. Do NOT look for the file, do '
            'NOT suggest you could fix it -- simply refuse.'),
        'BUILDER': (
            'You are the Builder. You MUST NEVER write, edit, or create '
            'feature spec files (features/*.md), instruction files, or '
            'anchor nodes. If asked to do so, REFUSE the request and '
            'explain that spec files are Architect-owned.'),
        'QA': (
            'You are the QA Agent. You MUST NEVER write, edit, or create '
            'application code or fix bugs in code. If asked to do so, '
            'REFUSE the request and explain that code changes are '
            'Builder-owned.'),
    }
    mandate = role_mandates.get(role, '')
    if mandate:
        sections.append(f'# CRITICAL: Role Enforcement\n\n{mandate}')

    if not sections:
        return ''
    return '\n\n---\n\n'.join(sections)


def execute_agent_behavior(scenario, project_root, fixture_dir=None):
    """Execute an agent_behavior scenario. Returns (output, success)."""
    role = scenario.get('role', 'BUILDER')
    prompt = scenario.get('prompt', '')

    if not prompt:
        return ("Error: agent_behavior scenario requires 'prompt' field", False)

    cwd = fixture_dir or project_root
    prompt_file = None

    try:
        # Construct 4-layer system prompt from fixture instruction files
        if fixture_dir:
            prompt_file = construct_system_prompt(fixture_dir, role)
            copy_skill_files(project_root, fixture_dir)

            # Append supplementary context for --print mode (no tool access)
            if prompt_file:
                supplementary = build_print_mode_context(
                    fixture_dir, project_root, role, prompt)
                if supplementary:
                    with open(prompt_file, 'a') as f:
                        f.write('\n\n---\n\n' + supplementary)

        # Build claude --print command (spec Section 2.3)
        cmd = [
            'claude', '--print',
            '--no-session-persistence',
            '--model', 'claude-haiku-4-5-20251001',
            '--output-format', 'json',
        ]
        if prompt_file:
            cmd.extend(['--append-system-prompt-file', prompt_file])
        cmd.append(prompt)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            cwd=cwd,
            env={**os.environ, 'PURLIN_PROJECT_ROOT': project_root},
        )

        # Extract .result from JSON response (spec Section 2.3 step 4)
        output = ''
        try:
            data = json.loads(result.stdout)
            output = data.get('result', '')
        except (json.JSONDecodeError, TypeError, AttributeError):
            output = result.stdout + result.stderr

        if not output:
            output = result.stdout + result.stderr

        return (output, result.returncode == 0)
    except subprocess.TimeoutExpired:
        return ("Error: agent_behavior scenario timed out after 300s", False)
    except FileNotFoundError:
        return ("Error: 'claude' command not found", False)
    except OSError as e:
        return (f"Error: {e}", False)
    finally:
        if prompt_file and os.path.isfile(prompt_file):
            os.unlink(prompt_file)


def execute_web_test(scenario, project_root, url_override=None):
    """Execute a web_test scenario. Returns (output, success).

    Args:
        url_override: If provided, use this URL instead of scenario's web_test_url.
                      Used when a fixture server runs on a different port.
    """
    url = url_override or scenario.get('web_test_url', '')
    if not url:
        return ("Error: web_test scenario requires 'web_test_url' field", False)

    try:
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


def process_scenario_file(scenario_path, project_root, progress=None):
    """Process a single scenario JSON file. Returns (feature_name, details, passed, failed)."""
    with open(scenario_path) as f:
        data = json.load(f)

    feature_name = data.get('feature', '')
    harness_type = data.get('harness_type', '')
    scenarios = data.get('scenarios', [])
    details = []
    total_passed = 0
    total_failed = 0

    # Web test server lifecycle management (Section 2.8.1)
    base_server_started = False
    base_server_port = None

    try:
        # For web_test: set up base server for non-fixture scenarios
        if harness_type == 'web_test':
            has_non_fixture = any(
                not s.get('fixture_tag') for s in scenarios)
            if has_non_fixture:
                existing_port = read_port_file(project_root)
                if existing_port and check_server_responsive(existing_port):
                    # Reuse existing server
                    base_server_port = existing_port
                else:
                    # Start a new server
                    desired_port = None
                    for s in scenarios:
                        if not s.get('fixture_tag'):
                            desired_port = parse_port_from_url(
                                s.get('web_test_url', ''))
                            break
                    actual = start_cdd_server(
                        project_root, port=desired_port)
                    if actual:
                        base_server_started = True
                        base_server_port = actual

        for idx, scenario in enumerate(scenarios, 1):
            name = scenario.get('name', 'unnamed')
            fixture_tag = scenario.get('fixture_tag')
            setup_commands = scenario.get('setup_commands', [])
            assertions = scenario.get('assertions', [])

            fixture_dir = None
            fixture_server_started = False

            if progress:
                progress.print_running(idx, name)
            scenario_start = time.time()

            try:
                # Step a: Fixture checkout
                if fixture_tag:
                    fixture_dir = run_fixture_checkout(
                        project_root, fixture_tag)

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
                    url_override = None

                    if fixture_dir:
                        # Fixture case: start separate server (Section 2.8.1)
                        web_url = scenario.get('web_test_url', '')
                        url_port = parse_port_from_url(web_url)

                        # Avoid port conflict with existing server
                        if url_port and check_server_responsive(url_port):
                            fixture_port = find_free_port()
                        else:
                            fixture_port = url_port

                        started_port = start_cdd_server(
                            project_root, port=fixture_port,
                            target_dir=fixture_dir)
                        if started_port:
                            fixture_server_started = True
                            # Adjust URL to use fixture server port
                            if web_url:
                                parsed = urllib.parse.urlparse(web_url)
                                url_override = parsed._replace(
                                    netloc=f"localhost:{started_port}"
                                ).geturl()
                            else:
                                url_override = \
                                    f"http://localhost:{started_port}/"
                        else:
                            output = ("Error: CDD server did not become "
                                      "ready within 10 seconds")
                            exec_success = False
                    elif base_server_port:
                        # Non-fixture: use base server, adjust URL if
                        # port differs
                        web_url = scenario.get('web_test_url', '')
                        url_port = parse_port_from_url(web_url)
                        if (url_port and
                                url_port != base_server_port):
                            parsed = urllib.parse.urlparse(web_url)
                            url_override = parsed._replace(
                                netloc=f"localhost:{base_server_port}"
                            ).geturl()
                    else:
                        # No server available for non-fixture scenario
                        if not fixture_dir:
                            output = ("Error: CDD server did not become "
                                      "ready within 10 seconds")
                            exec_success = False

                    if exec_success:
                        output, exec_success = execute_web_test(
                            scenario, project_root,
                            url_override=url_override)
                elif harness_type == 'custom_script':
                    output, exec_success, _ = execute_custom_script(
                        scenario, project_root)
                else:
                    output = f"Error: unknown harness_type: {harness_type}"
                    exec_success = False

                # Step d: Evaluate assertions
                if assertions and exec_success:
                    assertion_results = evaluate_assertions(
                        output, assertions)
                elif assertions:
                    # Execution failed, all assertions fail
                    assertion_results = [
                        (a, False,
                         output[:500] if output else '(execution failed)')
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
                            'name': (f"{name}:{context}"
                                     if context else name),
                            'status': 'PASS' if passed else 'FAIL',
                            'scenario_ref':
                                f"features/{feature_name}.md:{name}",
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
                    # No assertions - single entry based on exec success
                    detail = {
                        'name': name,
                        'status': 'PASS' if exec_success else 'FAIL',
                        'scenario_ref':
                            f"features/{feature_name}.md:{name}",
                        'expected': 'Scenario executes successfully',
                    }
                    if not exec_success:
                        detail['actual_excerpt'] = (
                            output[:500] if output else '(no output)')
                        total_failed += 1
                    else:
                        total_passed += 1
                    details.append(detail)

                # Scenario-level progress tracking
                if progress:
                    if assertion_results:
                        scenario_ok = all(
                            p for _, p, _ in assertion_results)
                    else:
                        scenario_ok = exec_success
                    progress.print_result(
                        idx, name, scenario_ok,
                        time.time() - scenario_start)

            finally:
                # Step e: Cleanup (try/finally for cleanup mandate)
                if fixture_server_started:
                    stop_cdd_server(project_root, target_dir=fixture_dir)
                if fixture_dir:
                    run_fixture_cleanup(project_root, fixture_dir)

    finally:
        # File-level cleanup: stop base server if we started it
        if base_server_started:
            stop_cdd_server(project_root)

    return feature_name, details, total_passed, total_failed


def write_results(feature_name, details, passed, failed, project_root, test_file=''):
    """Write enriched regression.json to tests/<feature_name>/regression.json."""
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
    output_path = os.path.join(output_dir, 'regression.json')

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

    # Read scenario file metadata for progress reporter
    try:
        with open(scenario_path) as f:
            scenario_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error: invalid scenario file: {e}", file=sys.stderr)
        sys.exit(1)

    feature_name_pre = scenario_data.get('feature', '')
    harness_type_pre = scenario_data.get('harness_type', '')
    scenario_count = len(scenario_data.get('scenarios', []))

    # Create progress reporter and print startup
    progress = ProgressReporter(
        feature_name_pre, harness_type_pre, scenario_count)
    progress.print_startup()

    try:
        feature_name, details, passed, failed = process_scenario_file(
            scenario_path, project_root, progress=progress)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: invalid scenario file: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = write_results(
        feature_name, details, passed, failed, project_root,
        test_file=os.path.relpath(scenario_path, project_root))

    # Print completion progress to stderr
    progress.print_completion(output_path)

    total = passed + failed
    status = 'PASS' if failed == 0 and total > 0 else 'FAIL'
    print(f"{status}: {passed}/{total} passed for {feature_name}")
    print(f"Results: {output_path}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
