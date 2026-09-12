#!/usr/bin/env python3
"""The verdict half of the Purlin pre-push hook.

    python3 scripts/hooks/pre_push_gate.py config --project-root DIR
    python3 scripts/hooks/pre_push_gate.py check  --project-root DIR --mode MODE

`config` prints what the shell half needs to do its job, one key per line:

    mode=warn
    frameworks=pytest,jest

`check` reads the structured status payload and decides whether the push may
proceed. Governed by specs/hooks/pre_push_hook.md.

WHAT THIS READS, AND WHAT IT DOES NOT
    The input is the structured payload from `purlin_server.read_report_payload`,
    the same dict the dashboard renders from, never the rendered summary table.
    The table's glyphs and column order are presentation: they move with the
    dashboard, and a verdict that parses them is coupled to a layout. The table
    parse this replaces also matched feature names by substring and read a
    fixed column index, so a renamed column or a feature whose name contained
    another feature's name changed the verdict.

TWO POLICIES, TWO ENTRY POINTS, ONE READER
    `scripts/ci/verify_gate.py` keys on `remote_verification` and answers "may
    this branch merge". This keys on `pre_push` and answers "may this push
    leave the machine". They are different policies with different modes, so
    they are different scripts; they read the same payload through the same
    function so they can never disagree about the evidence.

EXIT CODES
    0  push may proceed
    1  push is blocked
    2  bad invocation: unreadable project, missing payload, unknown mode

    Fails closed. An error reading the evidence is never a pass.

THIS SCRIPT NEVER WRITES. No file is created or modified, no proof or receipt
is touched. A gate that can edit the evidence it grades is not a gate.
"""

import argparse
import json
import os
import sys

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_BAD_INVOCATION = 2

MODES = ('warn', 'strict', 'off')

# Modes `check` can act on. `off` never reaches here: the shell half exits
# before the gate runs, so an `off` arriving at `check` means the caller lost
# track of the mode and the gate fails closed rather than guessing.
CHECK_MODES = ('warn', 'strict')

_VERIFIED = 'VERIFIED'
_FAILING = 'FAILING'

# Every framework the shell half has a runner arm for, plus the ones Purlin
# ships a proof plugin for. Detection order is the order of the Detection
# table in references/supported_frameworks.md.
KNOWN_FRAMEWORKS = ('pytest', 'vitest', 'jest', 'c', 'php', 'sql', 'shell')

_RULE = '=' * 63


def _server_dir():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp')


def _load_payload(project_root):
    """The structured payload, or None. Imports the server by path, not by
    package: a hook runs from a git checkout, it does not pip-install it."""
    server_dir = _server_dir()
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    try:
        import purlin_server
    except ImportError:
        return None
    return purlin_server.read_report_payload(project_root)


def _load_config(project_root):
    """The merged config dict, or None when it cannot be read at all."""
    server_dir = _server_dir()
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    try:
        import config_engine
    except ImportError:
        config_engine = None
    if config_engine is not None:
        return config_engine.resolve_config(project_root)
    # No plugin on sys.path is a broken install, but reading the one file the
    # mode lives in is better than refusing to name the mode at all.
    path = os.path.join(project_root, '.purlin', 'config.json')
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def _file_contains(path, needle):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            return needle in handle.read()
    except (IOError, OSError):
        return False


def detect_frameworks(project_root):
    """Every framework detected, in references/supported_frameworks.md order.

    All matches, not the first: a project can carry pytest for the server and
    jest for the client, and running only one of them would call a suite that
    never ran green. Shell has no detection heuristic, so it is the fallback
    when nothing else matches, which is what keeps a runner arm always present.
    """
    found = []
    if (os.path.isfile(os.path.join(project_root, 'conftest.py'))
            or _file_contains(os.path.join(project_root, 'pyproject.toml'),
                              '[tool.pytest]')):
        found.append('pytest')
    package_json = os.path.join(project_root, 'package.json')
    if _file_contains(package_json, 'vitest'):
        found.append('vitest')
    if _file_contains(package_json, 'jest'):
        found.append('jest')
    if (os.path.isfile(os.path.join(project_root, 'Makefile'))
            or os.path.isfile(os.path.join(project_root, 'CMakeLists.txt'))):
        found.append('c')
    if (os.path.isfile(os.path.join(project_root, 'composer.json'))
            or os.path.isfile(os.path.join(project_root, 'phpunit.xml'))):
        found.append('php')
    tests_dir = os.path.join(project_root, 'tests')
    if os.path.isdir(tests_dir):
        try:
            names = os.listdir(tests_dir)
        except OSError:
            names = []
        if any(name.endswith('.sql') for name in names):
            found.append('sql')
    if not found:
        found.append('shell')
    return found


def resolve_frameworks(project_root, raw):
    """(frameworks, unknown) from the `test_framework` config value.

    The value is a comma separated list because `purlin:init` writes one when
    it detects more than one framework. Order is the order the user wrote,
    duplicates collapse, and `auto` expands in place to everything detected.
    """
    frameworks, unknown = [], []
    for part in str(raw or '').split(','):
        name = part.strip()
        if not name:
            continue
        if name == 'auto':
            for detected in detect_frameworks(project_root):
                if detected not in frameworks:
                    frameworks.append(detected)
        elif name in KNOWN_FRAMEWORKS:
            if name not in frameworks:
                frameworks.append(name)
        else:
            unknown.append(name)
    if not frameworks:
        for detected in detect_frameworks(project_root):
            if detected not in frameworks:
                frameworks.append(detected)
    return frameworks, unknown


def config(project_root, out=sys.stdout, err=sys.stderr):
    """Print `mode=` and `frameworks=`. Returns an exit code."""
    resolved = _load_config(project_root)
    if resolved is None:
        print(f"pre-push: cannot read .purlin/config.json under "
              f"{project_root!r}.", file=err)
        print("pre-push: failing closed. A hook that cannot read its own mode "
              "does not let the push through.", file=err)
        return EXIT_BAD_INVOCATION

    mode = resolved.get('pre_push', 'warn')
    if mode not in MODES:
        print(f"pre-push: \"pre_push\" is {mode!r}, which is not a recognized "
              f"mode ({' | '.join(MODES)}).", file=err)
        print("pre-push: failing closed rather than assuming 'warn'. A typo in "
              "the mode must not change what the hook enforces invisibly.",
              file=err)
        return EXIT_BAD_INVOCATION

    frameworks, unknown = resolve_frameworks(
        project_root, resolved.get('test_framework', 'auto'))
    for name in unknown:
        print(f"pre-push: \"test_framework\" names {name!r}, which is not a "
              f"framework Purlin knows ({', '.join(KNOWN_FRAMEWORKS)}); "
              f"dropping it. No tests will run for it.", file=err)

    print(f"mode={mode}", file=out)
    print("frameworks=" + ','.join(frameworks), file=out)
    return EXIT_OK


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

def _coverage(feature):
    proved = feature.get('proved', 0)
    total = feature.get('total', 0)
    return f"{proved}/{total} rules proved"


def _findings(payload):
    """(failing, not_verified, informational, awaiting) as report material.

    `failing` is every feature carrying a FAIL proof, anchors included: a
    failing anchor rule is a failing rule of every feature that requires it.
    `not_verified` is what strict mode blocks on: non-anchor features that are
    not VERIFIED, PASSING included. `informational` is what warn mode lists
    without blocking. `awaiting` counts proofs declared on a platform with no
    result there.
    """
    failing, not_verified, informational = [], [], []
    awaiting_count, awaiting_platforms = 0, set()
    for feature in payload.get('features') or []:
        name = feature.get('name', '?')
        is_anchor = feature.get('type') == 'anchor'
        label = f"{name} (anchor)" if is_anchor else name
        status = feature.get('status', 'UNKNOWN')

        for entry in feature.get('awaiting_runner') or []:
            awaiting_count += 1
            awaiting_platforms.add(str(entry.get('platform', '?')))

        if status == _FAILING:
            failing.append((name, f"{label} ({_coverage(feature)})"))
            continue
        if status == _VERIFIED:
            continue
        informational.append(f"{label}: {status} ({_coverage(feature)})")
        if not is_anchor:
            not_verified.append(f"{label}: {status} ({_coverage(feature)})")
    return failing, not_verified, informational, (awaiting_count,
                                                  sorted(awaiting_platforms))


def _failing_names(failing):
    """Feature names for the recovery steps, matched whole.

    Whole name, never substring: a project with `system` and `auth_system`
    would otherwise be told to re-run one of them and never the other, because
    one name occurs inside the other.
    """
    names, seen = [], set()
    for name, _line in failing:
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _report_failing(failing, out):
    print('', file=out)
    print(_RULE, file=out)
    print('PUSH BLOCKED: failing proofs detected', file=out)
    print('', file=out)
    print('Failing rules:', file=out)
    for _name, line in failing:
        print(f"  {line}", file=out)
    print('', file=out)
    print('RECOVERY STEPS', file=out)
    print('', file=out)
    print('Proofs may be stale (tests pass but proof files still record a',
          file=out)
    print('prior failure). Re-emitting proofs will fix this. If the tests',
          file=out)
    print('themselves are broken, fix the code first.', file=out)
    print('', file=out)
    print('1. Re-run tests to re-emit proofs for each failing feature:',
          file=out)
    for name in _failing_names(failing):
        print(f"     /purlin:test {name}", file=out)
    print('', file=out)
    print('2. Confirm all rules pass:', file=out)
    print('     /purlin:status', file=out)
    print('', file=out)
    print('3. If any rules still show FAIL, the test is genuinely broken.',
          file=out)
    print('   Fix with /purlin:build <feature>, then repeat from step 1.',
          file=out)
    print('', file=out)
    print('4. Once status shows PASSING (no FAILs), retry the push.', file=out)
    print(_RULE, file=out)


def _report_strict(not_verified, out):
    print('', file=out)
    print(_RULE, file=out)
    print('PUSH BLOCKED (strict mode): features are not VERIFIED', file=out)
    print('', file=out)
    for line in not_verified:
        print(f"  {line}", file=out)
    print('', file=out)
    print('RECOVERY STEPS', file=out)
    print('', file=out)
    print('Strict mode requires every feature to be VERIFIED: all rules proved',
          file=out)
    print('AND a current verification receipt. A feature showing PASSING has',
          file=out)
    print('the proofs but not the receipt, so strict mode blocks it too.',
          file=out)
    print('', file=out)
    print('1. Run tests for features that are not fully proved:', file=out)
    print('     /purlin:test <feature>', file=out)
    print('', file=out)
    print('2. Check status to confirm all rules pass:', file=out)
    print('     /purlin:status', file=out)
    print('', file=out)
    print('3. If any rules show FAIL, fix with /purlin:build <feature>,',
          file=out)
    print('   then re-run /purlin:test <feature>.', file=out)
    print('', file=out)
    print('4. Once all features show PASSING, issue verification receipts:',
          file=out)
    print('     /purlin:verify', file=out)
    print('', file=out)
    print('5. Retry the push.', file=out)
    print('', file=out)
    print('To switch to warn mode (allows PARTIAL, UNTESTED and PASSING):',
          file=out)
    print('  Set "pre_push": "warn" in .purlin/config.json', file=out)
    print(_RULE, file=out)


def check(project_root, mode, out=sys.stdout):
    """Run the gate. Returns an exit code; writes nothing but its report."""
    if mode not in CHECK_MODES:
        print(f"pre-push: mode {mode!r} is not a mode this gate can check "
              f"({' | '.join(MODES)}).", file=out)
        print("pre-push: failing closed. A hook that does not know which "
              "policy it is enforcing does not let the push through.",
              file=out)
        return EXIT_BAD_INVOCATION

    payload = _load_payload(project_root)
    if payload is None:
        print(f"pre-push: cannot read a Purlin project at {project_root!r}.",
              file=out)
        print("pre-push: failing closed. A hook that cannot read the evidence "
              "does not let the push through.", file=out)
        return EXIT_BAD_INVOCATION

    failing, not_verified, informational, awaiting = _findings(payload)
    awaiting_count, awaiting_platforms = awaiting

    verified = [f.get('name', '?') for f in payload.get('features') or []
                if f.get('status') == _VERIFIED]
    if verified:
        print('purlin: verified features:', file=out)
        for name in verified:
            print(f"  {name}", file=out)

    if informational and mode != 'strict':
        print('purlin: partial coverage, untested or unreceipted '
              '(not blocking in warn mode):', file=out)
        for line in informational:
            print(f"  {line}", file=out)

    # One line, and only ever a line. A proof declared on a platform this host
    # is not is a fact about the fleet, not a defect in the push.
    if awaiting_count:
        print(f"purlin: {awaiting_count} proof"
              f"{'s' if awaiting_count != 1 else ''} declared on "
              f"{', '.join(awaiting_platforms)} with no result there; "
              f"advisory only, this never blocks a push.", file=out)

    if failing:
        _report_failing(failing, out)
        return EXIT_BLOCKED

    if mode == 'strict' and not_verified:
        _report_strict(not_verified, out)
        return EXIT_BLOCKED

    return EXIT_OK


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='pre_push_gate.py',
        description='The verdict half of the Purlin pre-push hook.')
    sub = parser.add_subparsers(dest='command')

    config_parser = sub.add_parser(
        'config', help='Print mode= and frameworks= for the shell half.')
    config_parser.add_argument('--project-root', default='.')

    check_parser = sub.add_parser(
        'check', help='Decide whether the push may proceed.')
    check_parser.add_argument('--project-root', default='.')
    check_parser.add_argument('--mode', default='warn')

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on a usage error, which is already this script's
        # bad-invocation code. Keep it rather than letting it surface as 0.
        return EXIT_BAD_INVOCATION

    if not args.command:
        parser.print_usage(sys.stderr)
        print('pre_push_gate.py: a subcommand is required (config | check).',
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if not os.path.isdir(args.project_root):
        print(f'pre_push_gate.py: not a directory: {args.project_root!r}',
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if args.command == 'config':
        return config(args.project_root)
    return check(args.project_root, args.mode)


if __name__ == '__main__':
    sys.exit(main())
