#!/usr/bin/env python3
"""Deterministic CI verification gate for Purlin projects.

    python3 scripts/ci/verify_gate.py --check [--project-root DIR]

Reads the structured status payload (the same dict the dashboard renders from)
and decides whether the branch may merge. Governed by specs/ci/verify_gate.md.

WHAT THIS READS, AND WHAT IT DOES NOT
    The input is the structured payload from `purlin_server.read_report_payload`,
    never the rendered Unicode summary table. The table's glyphs and column
    order are presentation and move with the dashboard, so nothing that decides
    what may merge or push reads them: this gate reads the payload, and
    `scripts/hooks/pre-push.sh` shells to `scripts/hooks/pre_push_gate.py`,
    which reads the same payload and hands the hook its exit code.

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

A `required` DECLARATION WITH NOTHING REMOTE IN IT
    A project can declare `required` while no proof anywhere declares a
    platform. That is not the unreadable-registry case above: the gate knows
    exactly what the evidence means, which is that nothing is platform-scoped,
    and an empty `platforms` registry is a configuration the reference blesses
    ("Family ids need no configuration"). So the gate names it in one line and
    leaves the verdict alone: an unverified feature still exits 1, a clean tree
    still exits 0, and neither becomes a 2. The line is what stops the other
    failure, a PASS under the strictest mode with no By-platform section to say
    that nothing remote was ever checked.

QUALITY GATE
    Off unless the project asks for it. `.purlin/config.json`'s `quality_gate`
    field DECLARES whether the two model-free quality passes are read as a
    gate: `off` (the default, and what a project that never set the field
    gets) reports nothing beyond one line, and `deterministic` runs
    `scripts/audit/static_checks.py`'s `deterministic_sweep` and exits 1 on a
    HOLLOW executed proof or an UNPROVABLE proof description. Both passes are
    deterministic and cacheless, so CI recomputes every grade from the source
    it checked out. It is not the enforcement, for the same reason the mode
    above is not: the field is a file in the repository the agent can edit.
    Enforcement is branch protection marking this job a required check.

    A proof the sweep cannot measure (a language no shipped checker reads, a
    test file that is not on disk, a marker the checker cannot find) is
    reported and never fails the gate: an unmeasurable proof is a gap in
    coverage, not a defect. The remote verdict and the quality verdict are
    independent; either one failing fails the branch.

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

# The quality gate is opt-in: a project that never wrote the field reads `off`,
# which is the mode that computes nothing. `deterministic` names the two passes
# that need no model and no cache (Pass 1 over test source, Pass D1 over proof
# descriptions), which is exactly why they can be a gate: CI recomputes every
# grade from the checkout in front of it.
QUALITY_MODES = ('off', 'deterministic')

# A receipt is issued once every rule is proved, so VERIFIED is the only state
# that means "the evidence is complete and committed". PASSING is complete but
# unreceipted, which is a developer who has not run purlin:verify yet.
_VERIFIED = 'VERIFIED'

_ENFORCEMENT_NOTE = (
    'Note: remote_verification is DECLARED in .purlin/config.json, which the '
    'agent can edit. It is not the enforcement. Enforcement is branch protection '
    'marking this job a required check.'
)

_QUALITY_ENFORCEMENT_NOTE = (
    'Note: quality_gate is DECLARED in .purlin/config.json, which the agent '
    'can edit. It is not the enforcement. Enforcement is branch protection '
    'marking this job a required check.'
)

_UNMEASURABLE_NOTE = (
    '  An unmeasurable proof is a gap in coverage, not a defect: it never '
    'fails the gate.'
)

# `required` is the declaration that verified-everywhere is the bar. When no
# proof declares a platform there is no "everywhere": the registry, empty or
# populated, has nothing in it being verified and no runner will be dispatched
# for anything. That is a declaration with nothing remote in it, not evidence
# the gate cannot read, so it is named and the verdict is left to RULE-3 and
# RULE-4 (verify_gate RULE-13).
_NO_PLATFORM_NOTE = (
    'verify-gate: no proof declares a platform, so nothing in '
    '.purlin/config.json\'s "platforms" registry is being verified: '
    "'required' is a verified-here bar only."
)
_NO_PLATFORM_FIX = (
    'verify-gate: that is reported, not failed. An empty registry is a '
    'supported configuration (references/remote_verification.md, "Family ids '
    'need no configuration"), so the fix is a proof declaring @on(<platform>) '
    'where this project means verified-everywhere.'
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


def _load_static_checks():
    """The deterministic checker module, or None.

    Imported by path for `_load_payload`'s reason: CI checks out the repo, it
    does not pip-install it. Imported only under `deterministic`, so a project
    with the gate off never loads it.
    """
    audit_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audit')
    if audit_dir not in sys.path:
        sys.path.insert(0, audit_dir)
    try:
        import static_checks
    except ImportError:
        return None
    return static_checks


def _quality_finding_line(row, kind):
    """One report line for a sweep finding.

    `kind` is `HOLLOW`, `UNPROVABLE` or `unmeasurable`. A hollow proof names
    the test the verdict was taken from, because the reader's next move is to
    open it; an unprovable description has no test to name; an unmeasurable
    proof names why it could not be measured, because that is the whole of
    what the gate learned about it.
    """
    head = f"{row['feature']}: {row['proof_id']} {kind}"
    if kind == 'unmeasurable':
        return f"{head} ({_unmeasurable_because(row)})"
    head = f"{head} ({row['check']})"
    if kind == 'UNPROVABLE':
        return head
    name = row.get('test_name') or '?'
    return f"{head} {row.get('test_file') or '?'}::{name}"


def _unmeasurable_because(row):
    """Why one proof could not be measured, in one clause."""
    check = row.get('check')
    test_file = row.get('test_file') or ''
    if check == 'no_checker':
        ext = os.path.splitext(test_file)[1].lower() or '(no extension)'
        return f"{test_file}: no deterministic checker for {ext}"
    if check == 'missing_file':
        if not test_file:
            return 'no test file is recorded for it'
        return f"{test_file}: named by the proof record but not on disk"
    if check == 'marker_not_found':
        return f"{test_file}: carries no marker for this proof"
    return f"{test_file}: {check}"


def _quality_section(sweep, out):
    """Print the quality-gate section. Returns True when the gate fails."""
    hollow = sweep.get('hollow') or []
    unprovable = sweep.get('unprovable') or []
    unmeasurable = sweep.get('unmeasurable') or []
    print(f"\nQuality gate (deterministic): {len(hollow)} HOLLOW, "
          f"{len(unprovable)} UNPROVABLE, {len(unmeasurable)} unmeasurable",
          file=out)
    for row in hollow:
        print(f"  {_quality_finding_line(row, 'HOLLOW')}", file=out)
    for row in unprovable:
        print(f"  {_quality_finding_line(row, 'UNPROVABLE')}", file=out)
    for row in unmeasurable:
        print(f"  {_quality_finding_line(row, 'unmeasurable')}", file=out)
    if unmeasurable:
        print(_UNMEASURABLE_NOTE, file=out)
    return bool(hollow or unprovable)


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
    """One report line per declared platform, from `platforms.summary`.

    An id whose row reads `platform_kind` `environment` is marked
    `<id> (environment)` (verify_gate RULE-12). The gate's reader is looking
    at a failed build asking who has to act: a line that reads like every OS
    row sends them to wait for a runner that will never be dispatched, when
    what the id needs is a person running the suite with `PURLIN_PLATFORM`
    set. The word is read off the payload and never recomputed here
    (`report_data` RULE-42).
    """
    summary = (payload.get('platforms') or {}).get('summary') or {}
    lines = []
    for platform in sorted(summary):
        agg = summary[platform] or {}
        # The host row (report_data RULE-41) covers the results that name no
        # platform. It declares nothing, so it gets no line here: the gate
        # reports whether each DECLARED id was proved, and the agnostic
        # results are already the project's own proved and failing counts.
        if agg.get('host'):
            continue
        proofs = agg.get('proofs') or {}
        kind = (' (environment)'
                if agg.get('platform_kind') == 'environment' else '')
        lines.append(
            f"{platform}{kind}: {proofs.get('proved', 0)} proved, "
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

    quality = payload.get('quality_gate', 'off')
    if quality not in QUALITY_MODES:
        print(f"verify-gate: quality_gate is {quality!r}, which is not a "
              f"recognized mode ({' | '.join(QUALITY_MODES)}).", file=out)
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
    # One line under `off` too: a reader of a job log must be able to tell a
    # project that declined the quality gate from one running a build old
    # enough not to have had it, and the note only belongs where it applies.
    print(f"verify-gate: quality_gate = {quality}", file=out)
    if quality == 'deterministic':
        print(_QUALITY_ENFORCEMENT_NOTE, file=out)

    if mode == 'off':
        print("verify-gate: disabled for this project. Reporting only.", file=out)

    # Read off the payload's own flag (`platform_testing` is true when any proof
    # declares a platform), never recomputed from the registry here, so the gate
    # cannot disagree with the report that sent the reader to it.
    if mode == 'required' and not payload.get('platform_testing'):
        print(_NO_PLATFORM_NOTE, file=out)
        print(_NO_PLATFORM_FIX, file=out)

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

    quality_fail = False
    if quality == 'deterministic':
        static_checks = _load_static_checks()
        if static_checks is None:
            print("\nverify-gate: quality_gate is 'deterministic' but "
                  "scripts/audit/static_checks.py could not be imported.",
                  file=out)
            print("verify-gate: failing closed. A gate that cannot run the "
                  "checks it declares does not pass the branch.", file=out)
            return EXIT_BAD_INVOCATION
        try:
            sweep = static_checks.deterministic_sweep(project_root)
        except Exception as exc:  # noqa: BLE001 - any failure is unread evidence
            print(f"\nverify-gate: scripts/audit/static_checks.py raised "
                  f"{type(exc).__name__}: {exc}", file=out)
            print("verify-gate: failing closed. A gate that cannot run the "
                  "checks it declares does not pass the branch.", file=out)
            return EXIT_BAD_INVOCATION
        quality_fail = _quality_section(sweep, out)

    # The two verdicts are independent: the remote gate asks whether the
    # evidence is complete everywhere it was declared, the quality gate asks
    # whether the evidence is worth anything. Either one failing fails the
    # branch, and when both hold both lines are printed, because a reader who
    # fixes one and pushes again should not discover the other on the next run.
    remote_fail = mode == 'required' and bool(unverified or awaiting)

    if remote_fail:
        print("\nverify-gate: FAIL. This project declares remote_verification "
              "'required', which is the declaration that verified-everywhere is "
              "the bar.", file=out)
    if quality_fail:
        print("\nverify-gate: FAIL. This project declares quality_gate "
              "'deterministic', which is the declaration that no proof may be "
              "HOLLOW or its description UNPROVABLE.", file=out)
    if remote_fail or quality_fail:
        return EXIT_GATE_FAILED

    if mode != 'required':
        print(f"\nverify-gate: PASS (mode is {mode}; findings never block).",
              file=out)
        return EXIT_OK

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
