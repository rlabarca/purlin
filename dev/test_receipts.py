"""Behavioural proofs for the receipt issuer and the receipt contract.

A receipt is the only artifact that claims a feature was verified, so what
refuses to write one matters as much as what writes it. These proofs drive the
real `dev/issue_receipts.py` against temp projects rather than asserting on a
hand-written receipt shape, which would be free to drift from the issuer's.

Covers `skill_verify` PROOF-11 and PROOF-12 (behavioural halves) and
`sync_status` PROOF-88.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SERVER = os.path.join(ROOT, 'scripts', 'mcp', 'purlin_server.py')
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, DEV)

import purlin_server as ps  # noqa: E402
import issue_receipts  # noqa: E402


LOCKING_SPEC = '''# Feature: locking

> Description: File locking.

## Rules
- RULE-1: Locks on POSIX
- RULE-2: Locks on the declared platform

## Proof
- PROOF-1 (RULE-1): fcntl path locks @unit
- PROOF-2 (RULE-2): msvcrt path locks on a real runner @unit @on(windows-2022)
'''

PLAIN_SPEC = '''# Feature: plain

> Description: Plain feature.

## Rules
- RULE-1: Does the thing

## Proof
- PROOF-1 (RULE-1): the thing happens @unit
'''

BROKEN_SPEC = '''# Feature: broken

> Description: Broken feature.

## Rules
- RULE-1: Does the thing

## Proof
- PROOF-1 (RULE-1): the thing happens @unit
'''


def _git(root, *args, **kw):
    return subprocess.run(['git'] + list(args), cwd=root,
                          capture_output=True, text=True, **kw)


def _entry(feature, pid, rule, test_file, test_name, status='pass',
           tier='unit'):
    return {'feature': feature, 'id': pid, 'rule': rule,
            'test_file': test_file, 'test_name': test_name,
            'status': status, 'tier': tier}


def _write_proofs(spec_dir, feature, entries, tier='unit', platform=None):
    suffix = f'{tier}@{platform}' if platform else tier
    path = os.path.join(spec_dir, f'{feature}.proofs-{suffix}.json')
    with open(path, 'w') as f:
        json.dump({'tier': tier, 'proofs': entries}, f, indent=2)
        f.write('\n')
    return path


def _make_project(with_broken=True):
    """A temp git project: one ordinary feature, one whose only uncovered rule
    is awaiting a runner, and (optionally) one failing feature."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin'))
    spec_dir = os.path.join(root, 'specs', 'app')
    os.makedirs(spec_dir)
    with open(os.path.join(root, '.purlin', 'config.json'), 'w') as f:
        json.dump({'report': False,
                   'platforms': {'windows-2022': {'os': 'windows'}}}, f)

    with open(os.path.join(spec_dir, 'locking.md'), 'w') as f:
        f.write(LOCKING_SPEC)
    _write_proofs(spec_dir, 'locking', [
        _entry('locking', 'PROOF-1', 'RULE-1', 'dev/t_lock.py', 'test_fcntl')])

    with open(os.path.join(spec_dir, 'plain.md'), 'w') as f:
        f.write(PLAIN_SPEC)
    _write_proofs(spec_dir, 'plain', [
        _entry('plain', 'PROOF-1', 'RULE-1', 'dev/t_plain.py', 'test_thing')])

    if with_broken:
        with open(os.path.join(spec_dir, 'broken.md'), 'w') as f:
            f.write(BROKEN_SPEC)
        _write_proofs(spec_dir, 'broken', [
            _entry('broken', 'PROOF-1', 'RULE-1', 'dev/t_broken.py',
                   'test_thing', status='fail')])

    _git(root, 'init', '-q')
    for k, v in (('user.email', 't@e'), ('user.name', 't')):
        _git(root, 'config', k, v)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-q', '-m', 'init')
    return root, spec_dir


def _receipt(root, feature):
    path = os.path.join(root, 'specs', 'app', f'{feature}.receipt.json')
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# skill_verify RULE-12: the run the receipt rests on
# ---------------------------------------------------------------------------

class TestIssuerRunMarker:

    @pytest.mark.proof("skill_verify", "PROOF-12", "RULE-12", tier="integration")
    def test_issuer_refuses_without_a_recorded_passing_run_at_head(self, capsys):
        """RULE-12: a receipt over proof files nobody re-ran is a claim about a
        file, not about a test. Three ways the evidence can be about a
        different tree, and the escape hatch that says so in the receipt."""
        root, spec_dir = _make_project()
        try:
            # 1. No marker at all.
            issued, _ = issue_receipts.main(root)
            out = capsys.readouterr().out
            assert issued == [], "no run marker must issue nothing"
            assert 'REFUSED' in out and 'no run marker' in out, out
            assert _receipt(root, 'plain') is None

            # 2. A marker for a run that failed.
            issue_receipts.write_run_marker(root, ok=False)
            issued, _ = issue_receipts.main(root)
            out = capsys.readouterr().out
            assert issued == [] and 'REFUSED' in out, out
            assert 'ok: false' in out, out
            assert _receipt(root, 'plain') is None

            # 3. A passing marker, but from another commit.
            issue_receipts.write_run_marker(root, commit='0' * 40)
            issued, _ = issue_receipts.main(root)
            out = capsys.readouterr().out
            assert issued == [] and 'REFUSED' in out, out
            assert 'HEAD is' in out, out
            assert _receipt(root, 'plain') is None

            # 4. A valid marker: the receipt cites that run.
            marker = issue_receipts.write_run_marker(root)
            issued, skipped = issue_receipts.main(root, quiet=True)
            names = [n for n, _, _ in issued]
            assert 'plain' in names and 'locking' in names, (issued, skipped)
            assert 'broken' not in names, "a failing feature earns no receipt"
            receipt = _receipt(root, 'plain')
            assert receipt['evidence']['test_run']['commit'] == marker['commit']
            assert receipt['evidence']['test_run']['sweep'] == 'dev/run_tests.sh'

            # 5. The override is not silent, and the receipt says so.
            os.remove(issue_receipts.marker_path(root))
            issued, _ = issue_receipts.main(root, run_check=False)
            out = capsys.readouterr().out
            assert 'WARNING' in out and '--no-run-check' in out, out
            assert [n for n, _, _ in issued], "the override must still issue"
            assert _receipt(root, 'plain')['evidence']['test_run'] is None, \
                "a receipt issued without a run must record no run"
        finally:
            shutil.rmtree(root)

    @pytest.mark.proof("skill_verify", "PROOF-12", "RULE-12", tier="integration")
    def test_issuer_skips_a_feature_whose_evidence_no_run_executed(self, capsys):
        """RULE-12: a proof file the recorded run did not execute and no runner
        committed is evidence with no witness."""
        root, spec_dir = _make_project(with_broken=False)
        try:
            # `plain`'s proof names a test file the recorded run never ran, and
            # its proof file was committed locally, so no runner vouches for it.
            issue_receipts.write_run_marker(
                root, test_files=['dev/t_lock.py'])
            issued, skipped = issue_receipts.main(root)
            out = capsys.readouterr().out
            names = [n for n, _, _ in issued]

            assert 'plain' not in names, \
                "unexecuted local evidence must not earn a receipt"
            assert 'SKIP' in out and 'plain' in out, out
            assert 'not executed in the recorded run' in out, out
            assert 'plain.proofs-unit.json' in out, \
                f"the skip must name the file: {out}"
            assert '1 proof' in out, f"the skip must name the count: {out}"
            assert _receipt(root, 'plain') is None
            assert 'locking' in names, \
                "the feature whose evidence WAS executed still gets a receipt"

            # A runner commit is the other witness: the same unexecuted entry
            # in a file a runner committed is accepted.
            _write_proofs(spec_dir, 'locking', [
                _entry('locking', 'PROOF-2', 'RULE-2', 'dev/t_win.py',
                       'test_msvcrt')], platform='windows-2022')
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'ci proofs',
                 '-m', 'Purlin-Runner: github-actions/windows-2022')
            issue_receipts.write_run_marker(root, test_files=['dev/t_lock.py'])
            issued, _ = issue_receipts.main(root, quiet=True)
            assert 'locking' in [n for n, _, _ in issued], \
                "a runner-committed file is evidence with a witness"
            rows = _receipt(root, 'locking')['evidence']['proof_files']
            by_platform = {r['platform']: r for r in rows}
            assert by_platform['windows-2022']['runner'] == \
                'github-actions/windows-2022'
            assert by_platform['windows-2022']['executed_in_test_run'] is False
            assert by_platform[None]['executed_in_test_run'] is True
        finally:
            shutil.rmtree(root)


# ---------------------------------------------------------------------------
# skill_verify RULE-11: what a stale receipt says
# ---------------------------------------------------------------------------

class TestStaleReceiptDetail:

    @pytest.mark.proof("skill_verify", "PROOF-11", "RULE-11", tier="integration")
    def test_stale_receipt_names_reworded_rules_and_reproved_platforms(self):
        """RULE-11: `vhash mismatch` alone sends the reader to diff two hashes.
        The receipt records rule text and per-file provenance, so it can say
        which rule moved and which platform was re-proved."""
        root, spec_dir = _make_project(with_broken=False)
        try:
            # Prove the platform rule so `locking` has a scoped file whose
            # provenance the receipt records.
            _write_proofs(spec_dir, 'locking', [
                _entry('locking', 'PROOF-2', 'RULE-2', 'dev/t_win.py',
                       'test_msvcrt')], platform='windows-2022')
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'windows proofs')
            issue_receipts.write_run_marker(root)
            issue_receipts.main(root, quiet=True)
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'verify')

            baseline = ps.sync_status(root)
            assert 'locking: VERIFIED' in baseline, baseline

            # A reworded rule is named, by id.
            spec_path = os.path.join(spec_dir, 'locking.md')
            original = open(spec_path).read()
            with open(spec_path, 'w') as f:
                f.write(original.replace('- RULE-1: Locks on POSIX',
                                         '- RULE-1: Locks on POSIX hosts'))
            out = ps.sync_status(root)
            assert 'Receipt stale' in out, out
            assert 'Rule text changed since last verification: RULE-1' in out, out
            assert 'RULE-2' not in out.split('Rule text changed')[1].split('\n')[0], \
                "only the rule that moved may be named"

            # Reflowing the same words is not a change.
            with open(spec_path, 'w') as f:
                f.write(original.replace('- RULE-1: Locks on POSIX',
                                         '- RULE-1:   Locks  on POSIX'))
            out = ps.sync_status(root)
            assert 'Rule text changed since last verification' not in out, out

            # A platform re-proved after the receipt is named.
            with open(spec_path, 'w') as f:
                f.write(original)
            _write_proofs(spec_dir, 'locking', [
                _entry('locking', 'PROOF-2', 'RULE-2', 'dev/t_win.py',
                       'test_msvcrt_v2')], platform='windows-2022')
            _git(root, 'add', '-A')
            _git(root, 'commit', '-q', '-m', 'windows proofs again')
            out = ps.sync_status(root)
            assert 'windows-2022 re-proved since receipt' in out, out
        finally:
            shutil.rmtree(root)


# ---------------------------------------------------------------------------
# sync_status RULE-54: one verdict function
# ---------------------------------------------------------------------------

def _call_sites(tree, name):
    """[(enclosing function, lineno)] for every call to `name` in the module."""
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and \
                    isinstance(inner.func, ast.Name) and inner.func.id == name:
                sites.append((node.name, inner.lineno))
    return sites


class TestOneVerdictFunction:

    @pytest.mark.proof("sync_status", "PROOF-88", "RULE-54", tier="integration")
    def test_vhash_and_active_rules_have_exactly_one_call_site(self):
        """RULE-54: counted by AST, not by grep, so a call inside a comment or
        a string cannot pad or hide the count."""
        with open(SERVER) as f:
            tree = ast.parse(f.read())

        for name in ('_compute_vhash', '_active_rule_entries'):
            sites = _call_sites(tree, name)
            assert len(sites) == 1, (
                f"{name} must be called from exactly one place in "
                f"purlin_server.py; found {len(sites)}: {sites}")
            assert sites[0][0] == '_feature_verdict', (
                f"{name} is called from {sites[0][0]}, not _feature_verdict")

        verdict_callers = {fn for fn, _ in _call_sites(tree, '_feature_verdict')}
        for caller in ('_report_feature', 'sync_status', '_build_report_data',
                       '_compute_drift'):
            assert caller in verdict_callers, (
                f"{caller} must read its verdict from _feature_verdict, not "
                f"rebuild it")

    @pytest.mark.proof("sync_status", "PROOF-88", "RULE-54", tier="integration")
    def test_issuer_and_payload_agree_on_every_vhash(self):
        """RULE-54: the parity the duplication used to break, including the
        feature whose only uncovered rule is awaiting a runner: the issuer
        skipped it as unproved while sync_status read it PASSING."""
        root, _spec_dir = _make_project()
        try:
            issue_receipts.write_run_marker(root)
            issued, skipped = issue_receipts.main(root, quiet=True)
            names = {n for n, _, _ in issued}

            assert 'locking' in names, (
                "a feature whose only uncovered rule is awaiting a runner is "
                "PASSING and must be issued, not skipped as unproved")
            assert 'plain' in names
            assert 'broken' not in names and \
                any(n == 'broken' for n, _ in skipped), skipped

            payload = ps.read_report_payload(root)
            by_name = {f['name']: f for f in payload['features']}
            for name, vhash, _aw in issued:
                assert by_name[name]['vhash'] == vhash, (
                    f"{name}: receipt vhash {vhash} != payload vhash "
                    f"{by_name[name]['vhash']}")
                assert by_name[name]['status'] == 'VERIFIED', (
                    f"{name}: a receipt the payload agrees with must read "
                    f"VERIFIED, got {by_name[name]['status']}")

            # The awaiting-only rule is still reported, not hidden by the
            # receipt it did not block.
            assert _receipt(root, 'locking')['awaiting_runner'] == [
                {'id': 'PROOF-2', 'tier': 'unit', 'platform': 'windows-2022'}]
        finally:
            shutil.rmtree(root)
