#!/usr/bin/env python3
"""Deterministic CI verification gate for Purlin projects.

    python3 scripts/ci/verify_gate.py --check [--project-root DIR]

Reads the structured status payload (the same dict the dashboard renders from)
and decides whether the branch may merge. Governed by specs/ci/verify_gate.md.

WHAT THIS READS, AND WHAT IT DOES NOT
    The input is the structured payload from `purlin_server.read_report_payload`,
    never the rendered Unicode summary table. The table's glyphs and column
    order are presentation and move with the dashboard; `scripts/hooks/pre-push.sh`
    parses them and is coupled to a layout as a result. A gate must not be.

DECLARATION VERSUS ENFORCEMENT
    `.purlin/config.json`'s `remote_verification` field DECLARES the mode. It is
    not the enforcement: it is a file in the repository that the agent can edit,
    and `docs/regulated-environments.md` requires policy to live outside the repo,
    "not by config files the agent can edit". Enforcement is branch protection
    marking this job a required check, plus auto-merge gated on it. That setting
    lives in the forge, which is exactly why it is the enforcement.

EXIT CODES  (aligned with dev/bump_version.sh)
    0  gate passed
    1  gate failed
    2  bad invocation: unreadable project, missing payload, unknown mode

    Fails closed. An error reading the evidence is never a pass.

THIS SCRIPT NEVER WRITES. No file is created or modified, no commit is made, no
proof or receipt is touched. It is the CI counterpart of `purlin:verify`'s
read-only contract, for the same reason: a gate that can edit the evidence it
grades is not a gate.
"""

import argparse
import os
import sys

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_BAD_INVOCATION = 2

MODES = ('required', 'optional', 'off')

# A receipt is issued once every rule is proved, so VERIFIED is the only state
# that means "the evidence is complete and committed". PASSING is complete but
# unreceipted, which is a developer who has not run purlin:verify yet.
_VERIFIED = 'VERIFIED'

_ENFORCEMENT_NOTE = (
    'Note: remote_verification is DECLARED in .purlin/config.json, which the '
    'agent can edit. It is not the enforcement. Enforcement is branch protection '
    'marking this job a required check.'
)


def _load_payload(project_root):
    """The structured payload, or None. Imports the server by path, not by
    package: CI checks out the repo, it does not pip-install it."""
    server_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mcp')
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    try:
        import purlin_server
    except ImportError:
        return None
    return purlin_server.read_report_payload(project_root)


def _findings(payload):
    """(unverified, awaiting) as lists of report lines.

    `unverified` is every non-anchor feature that is not VERIFIED. `awaiting`
    is every proof declared `@on(<platform>)` with no result satisfying that
    platform: complete locally, unproved on a platform the project claims.
    """
    unverified, awaiting = [], []
    for feat in payload.get('features') or []:
        if feat.get('type') == 'anchor':
            continue
        name = feat.get('name', '?')
        if feat.get('status') != _VERIFIED:
            unverified.append(
                f"{name}: {feat.get('status', 'UNKNOWN')} "
                f"({feat.get('proved', 0)}/{feat.get('total', 0)} rules proved)")
        for entry in feat.get('awaiting_runner') or []:
            awaiting.append(
                f"{name}: {entry.get('id', '?')} declared "
                f"@on({entry.get('platform', '?')}) with no result there")
    return unverified, awaiting


def _by_platform(payload):
    """One report line per declared platform, from `platforms.summary`."""
    summary = (payload.get('platforms') or {}).get('summary') or {}
    lines = []
    for platform in sorted(summary):
        agg = summary[platform] or {}
        proofs = agg.get('proofs') or {}
        lines.append(
            f"{platform}: {proofs.get('proved', 0)} proved, "
            f"{proofs.get('awaiting', 0)} awaiting, "
            f"{proofs.get('failed', 0)} failing "
            f"({agg.get('features', 0)} feature"
            f"{'s' if agg.get('features', 0) != 1 else ''})")
    return lines


def check(project_root, out=sys.stdout):
    """Run the gate. Returns an exit code; writes nothing but its report."""
    payload = _load_payload(project_root)
    if payload is None:
        print(f"verify-gate: cannot read a Purlin project at {project_root!r}.",
              file=out)
        print("verify-gate: failing closed. A gate that cannot read the evidence "
              "does not pass the branch.", file=out)
        return EXIT_BAD_INVOCATION

    mode = payload.get('remote_verification', 'off')
    if mode not in MODES:
        print(f"verify-gate: remote_verification is {mode!r}, which is not a "
              f"recognized mode ({' | '.join(MODES)}).", file=out)
        print("verify-gate: failing closed rather than assuming 'off'. A typo in "
              "the mode must not disable the declaration invisibly.", file=out)
        return EXIT_BAD_INVOCATION

    # A malformed `platforms` entry was dropped from the registry, so a proof
    # naming it may be matching every host of its family or nothing at all.
    # Evidence read through a broken registry is unreadable evidence: exit 2
    # in every mode, the same way a missing payload does.
    registry_errors = (payload.get('platforms') or {}).get('errors') or []
    if registry_errors:
        print(f"verify-gate: the platforms registry in .purlin/config.json has "
              f"{len(registry_errors)} invalid entr"
              f"{'ies' if len(registry_errors) != 1 else 'y'}:", file=out)
        for error in registry_errors:
            print(f"  {error}", file=out)
        print("verify-gate: failing closed. A gate that cannot resolve the "
              "platforms the evidence names cannot read the evidence.", file=out)
        return EXIT_BAD_INVOCATION

    unverified, awaiting = _findings(payload)
    by_platform = _by_platform(payload)

    print(f"verify-gate: remote_verification = {mode}", file=out)
    print(_ENFORCEMENT_NOTE, file=out)

    if mode == 'off':
        print("verify-gate: disabled for this project. Reporting only.", file=out)

    if by_platform:
        print(f"\nBy platform ({len(by_platform)}):", file=out)
        for line in by_platform:
            print(f"  {line}", file=out)

    # The findings are printed identically in all three modes. Only the verdict
    # differs, so a project can read what 'required' would have blocked before
    # it declares 'required'.
    if unverified:
        print(f"\nNot VERIFIED ({len(unverified)}):", file=out)
        for line in unverified:
            print(f"  {line}", file=out)
    if awaiting:
        print(f"\nAwaiting a runner ({len(awaiting)}):", file=out)
        for line in awaiting:
            print(f"  {line}", file=out)
        print("  A receipt carrying awaiting_runner is a verified-here claim, "
              "not a verified-everywhere one.", file=out)
    if not unverified and not awaiting:
        print("\nEvery feature is VERIFIED and nothing is awaiting a runner.",
              file=out)

    if mode != 'required':
        print(f"\nverify-gate: PASS (mode is {mode}; findings never block).",
              file=out)
        return EXIT_OK

    if unverified or awaiting:
        print("\nverify-gate: FAIL. This project declares remote_verification "
              "'required', which is the declaration that verified-everywhere is "
              "the bar.", file=out)
        return EXIT_GATE_FAILED

    print("\nverify-gate: PASS.", file=out)
    return EXIT_OK


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='verify_gate.py',
        description='Deterministic CI verification gate for Purlin projects.')
    parser.add_argument('--check', action='store_true',
                        help='Run the gate and exit 0 (pass) or 1 (fail).')
    parser.add_argument('--project-root', default='.',
                        help='Project root to check (default: cwd).')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on a usage error, which is already this script's
        # bad-invocation code. Keep it rather than letting it surface as 0.
        return EXIT_BAD_INVOCATION

    if not args.check:
        parser.print_usage(sys.stderr)
        print('verify_gate.py: --check is required.', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if not os.path.isdir(args.project_root):
        print(f'verify_gate.py: not a directory: {args.project_root!r}',
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    return check(args.project_root)


if __name__ == '__main__':
    sys.exit(main())
