"""Tests for verify_gate — 8 proofs covering the CI verification gate.

The gate decides whether a branch may merge, from the structured status
payload. Two things it must never do: parse the rendered summary table (which
couples a gate to a dashboard layout), and pass when it cannot read the
evidence.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'ci'))
sys.path.insert(0, DEV)

import verify_gate  # noqa: E402
import issue_receipts  # noqa: E402

GATE_PY = os.path.join(ROOT, 'scripts', 'ci', 'verify_gate.py')
WORKFLOW_DIR = os.path.join(ROOT, '.github', 'workflows')


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _spec(windows_proof=False):
    """A two-rule feature. RULE-2 is proved at unit tier either way; the
    optional extra @windows proof covers the SAME rule, so declaring it
    changes the awaiting list and nothing else: same rules, same executed
    proofs, same vhash, same receipt."""
    extra = ('- PROOF-3 (RULE-2): msvcrt path locks on a real windows runner '
             '@windows\n') if windows_proof else ''
    return (
        '# Feature: locking\n\n'
        '> Description: File locking.\n\n'
        '## Rules\n'
        '- RULE-1: Locks on POSIX\n'
        '- RULE-2: Locks on Windows\n\n'
        '## Proof\n'
        '- PROOF-1 (RULE-1): fcntl path locks @unit\n'
        '- PROOF-2 (RULE-2): msvcrt shim locks @unit\n'
        + extra
    )


def _make_project(mode='required', windows_proof=False, proofs_pass=True,
                  receipt=True):
    """A temp Purlin project. Returns its root."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin'))
    spec_dir = os.path.join(root, 'specs', 'app')
    os.makedirs(spec_dir)

    cfg = {'report': False, 'remote_verification': mode}
    with open(os.path.join(root, '.purlin', 'config.json'), 'w') as f:
        json.dump(cfg, f)
    with open(os.path.join(spec_dir, 'locking.md'), 'w') as f:
        f.write(_spec(windows_proof))

    status = 'pass' if proofs_pass else 'fail'
    entries = [
        {'feature': 'locking', 'id': 'PROOF-1', 'rule': 'RULE-1',
         'test_file': 'tests/test_lock.py', 'test_name': 'test_fcntl',
         'status': 'pass', 'tier': 'unit'},
        {'feature': 'locking', 'id': 'PROOF-2', 'rule': 'RULE-2',
         'test_file': 'tests/test_lock.py', 'test_name': 'test_shim',
         'status': status, 'tier': 'unit'},
    ]
    with open(os.path.join(spec_dir, 'locking.proofs-unit.json'), 'w') as f:
        json.dump({'tier': 'unit', 'proofs': entries}, f)

    subprocess.run(['git', 'init', '-q'], cwd=root, capture_output=True)
    for k, v in (('user.email', 't@e'), ('user.name', 't')):
        subprocess.run(['git', 'config', k, v], cwd=root, capture_output=True)
    subprocess.run(['git', 'add', '-A'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-q', '-m', 'init'], cwd=root,
                   capture_output=True)

    if receipt and proofs_pass:
        issue_receipts.main(root, quiet=True)
        subprocess.run(['git', 'add', '-A'], cwd=root, capture_output=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'verify'], cwd=root,
                       capture_output=True)
    return root


def _run(root):
    """Run the gate as a subprocess. Returns (exit_code, combined output).

    A subprocess, not an in-process call: the exit code is part of the
    contract, and `sys.exit(main())` is where an exit code gets lost.
    """
    r = subprocess.run(
        [sys.executable, GATE_PY, '--check', '--project-root', root],
        capture_output=True, text=True, cwd=ROOT, timeout=120)
    return r.returncode, r.stdout + r.stderr


def _workflows_that_commit_proofs():
    """[(filename, text)] for every workflow that git-commits a proof file.

    Matched on the workflow actually running `git add`/`git commit` against a
    `*.proofs-*.json` path, so a workflow that merely mentions proofs is not
    counted and a new commit-back workflow is caught automatically.
    """
    found = []
    for fn in sorted(os.listdir(WORKFLOW_DIR)):
        if not fn.endswith(('.yml', '.yaml')):
            continue
        text = open(os.path.join(WORKFLOW_DIR, fn)).read()
        if re.search(r'git\s+add\s+\S*\.proofs-[\w*]+\.json', text) and \
                'git commit' in text:
            found.append((fn, text))
    return found


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGateReadsTheStructuredPayload:

    @pytest.mark.proof("verify_gate", "PROOF-1", "RULE-1")
    def test_gate_does_not_parse_the_rendered_table(self):
        """The table's glyphs are presentation. scripts/hooks/pre-push.sh
        parses them and is coupled to a layout as a result."""
        src = open(GATE_PY).read()
        for glyph in ('│', '┌', '─', '└', '├'):
            assert glyph not in src, (
                f"verify_gate.py contains the box-drawing glyph {glyph!r}; a gate "
                "that reads the rendered table breaks when the table moves")

        # And it must reach the payload through the builder, not by splitting
        # sync_status output.
        assert 'read_report_payload' in src, (
            "the gate must obtain features from the report-data builder")
        assert not re.search(r'sync_status\s*\(', src), (
            "the gate must not call the text-rendering entry point, whose "
            "output is a table")

        # The builder is the real one, and it returns the fields the gate reads.
        import purlin_server
        assert hasattr(purlin_server, 'read_report_payload')
        root = _make_project(mode='off')
        try:
            payload = purlin_server.read_report_payload(root)
            assert isinstance(payload, dict) and 'features' in payload
            assert 'remote_verification' in payload
            feat = payload['features'][0]
            for key in ('name', 'status', 'awaiting_runner', 'proved', 'total'):
                assert key in feat, f"payload feature is missing {key!r}"
        finally:
            shutil.rmtree(root)


class TestExitCodes:

    @pytest.mark.proof("verify_gate", "PROOF-2", "RULE-2", tier="integration")
    def test_zero_one_and_two_and_never_zero_on_an_unreadable_project(self):
        clean = _make_project(mode='required')
        broken = _make_project(mode='required', proofs_pass=False, receipt=False)
        empty = tempfile.mkdtemp()
        try:
            code, out = _run(clean)
            assert code == 0, f"a fully verified project must pass:\n{out}"

            code, out = _run(broken)
            assert code == 1, (
                f"an unverified feature under 'required' must fail with 1:\n{out}")

            code, out = _run(empty)
            assert code == 2, (
                f"a directory that is not a Purlin project is a bad "
                f"invocation, expected 2:\n{out}")
            assert code != 0, "a gate that cannot read the evidence must not pass"

            # A bad flag is also 2, never 0.
            r = subprocess.run([sys.executable, GATE_PY], capture_output=True,
                               text=True, cwd=ROOT, timeout=60)
            assert r.returncode == 2, (
                f"omitting --check must exit 2, got {r.returncode}")
        finally:
            for d in (clean, broken, empty):
                shutil.rmtree(d)


class TestModeDecidesTheVerdict:

    @pytest.mark.proof("verify_gate", "PROOF-3", "RULE-3", tier="integration")
    def test_same_finding_three_modes_three_verdicts(self):
        """One project, three configs. The finding is identical in all three so
        a project can read what 'required' would block before declaring it."""
        root = _make_project(mode='required', proofs_pass=False, receipt=False)
        cfg_path = os.path.join(root, '.purlin', 'config.json')
        try:
            expected = {'required': 1, 'optional': 0, 'off': 0}
            for mode, want in expected.items():
                with open(cfg_path, 'w') as f:
                    json.dump({'report': False, 'remote_verification': mode}, f)
                code, out = _run(root)
                assert code == want, (
                    f"mode {mode!r} expected exit {want}, got {code}:\n{out}")
                assert f'remote_verification = {mode}' in out, out
                # The finding itself does not change with the mode.
                assert 'locking' in out, (
                    f"mode {mode!r} must still name the finding:\n{out}")

            with open(cfg_path, 'w') as f:
                json.dump({'report': False, 'remote_verification': 'off'}, f)
            _, out = _run(root)
            assert re.search(r'(?i)disabled', out), (
                f"'off' must say the gate is disabled for this project:\n{out}")
        finally:
            shutil.rmtree(root)


class TestAwaitingRunnerBlocksUnderRequired:

    @pytest.mark.proof("verify_gate", "PROOF-4", "RULE-4", tier="integration")
    def test_a_verified_feature_awaiting_a_runner_fails_required(self):
        """The two projects differ only in one @windows proof line that covers
        a rule a @unit proof already proves: same rules, same executed proofs,
        same vhash, both VERIFIED. So the awaited runner is provably the only
        thing that can change the verdict."""
        awaiting = _make_project(mode='required', windows_proof=True)
        clean = _make_project(mode='required', windows_proof=False)
        try:
            import purlin_server
            for root, expect in ((awaiting, True), (clean, False)):
                payload = purlin_server.read_report_payload(root)
                feat = payload['features'][0]
                assert feat['status'] == 'VERIFIED', (
                    f"fixture must be VERIFIED to isolate the variable, got "
                    f"{feat['status']} in {root}")
                assert bool(feat['awaiting_runner']) is expect, (
                    f"{root}: awaiting_runner={feat['awaiting_runner']}")

            code, out = _run(awaiting)
            assert code == 1, (
                f"a VERIFIED feature awaiting a runner must fail 'required', "
                f"got {code}:\n{out}")
            assert 'PROOF-3' in out and 'windows' in out, (
                f"the gate must name the awaited proof and its tier:\n{out}")

            code, out = _run(clean)
            assert code == 0, (
                f"the same project without the awaited proof must pass:\n{out}")
        finally:
            shutil.rmtree(awaiting)
            shutil.rmtree(clean)


class TestGateNeverWrites:

    @pytest.mark.proof("verify_gate", "PROOF-5", "RULE-5")
    def test_no_file_and_no_commit_in_any_mode(self):
        """A gate that can edit the evidence it grades is not a gate."""
        root = _make_project(mode='required')
        cfg_path = os.path.join(root, '.purlin', 'config.json')
        try:
            def snapshot():
                entries = {}
                for dirpath, dirnames, filenames in os.walk(root):
                    if '.git' in dirnames:
                        dirnames.remove('.git')
                    for fn in filenames:
                        full = os.path.join(dirpath, fn)
                        st = os.stat(full)
                        entries[os.path.relpath(full, root)] = (
                            st.st_size, st.st_mtime_ns)
                head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
                                      capture_output=True, text=True).stdout
                porcelain = subprocess.run(
                    ['git', 'status', '--porcelain'], cwd=root,
                    capture_output=True, text=True).stdout
                return entries, head, porcelain

            for mode in ('required', 'optional', 'off'):
                with open(cfg_path, 'w') as f:
                    json.dump({'report': False, 'remote_verification': mode}, f)
                before = snapshot()
                _run(root)
                after = snapshot()
                assert before == after, (
                    f"mode {mode!r}: the gate changed the tree.\n"
                    f"added/changed: "
                    f"{set(after[0].items()) - set(before[0].items())}\n"
                    f"removed: {set(before[0]) - set(after[0])}\n"
                    f"HEAD before={before[1]!r} after={after[1]!r}")
        finally:
            shutil.rmtree(root)


class TestDeclarationVersusEnforcement:

    @pytest.mark.proof("verify_gate", "PROOF-6", "RULE-6", tier="integration")
    def test_output_and_source_both_name_branch_protection(self):
        root = _make_project(mode='required')
        try:
            _, out = _run(root)
            assert re.search(r'(?i)declared', out), (
                f"the output must call the field a declaration:\n{out}")
            assert 'branch protection' in out, (
                f"the output must name branch protection as the enforcement:"
                f"\n{out}")
            assert re.search(r'(?i)not the enforcement', out), (
                f"the output must say the field is not the enforcement:\n{out}")

            header = open(GATE_PY).read().split('"""')[1]
            assert 'branch protection' in header, (
                "the source header must carry the same split")
            assert re.search(r'(?i)declare', header), header[:400]
        finally:
            shutil.rmtree(root)


class TestRunnerWorkflowProvenance:

    @pytest.mark.proof("verify_gate", "PROOF-7", "RULE-7")
    def test_every_commit_back_workflow_stamps_the_runner(self):
        """The trailer is the only record of which runner proved a tier: proof
        entries carry no such field, by design."""
        workflows = _workflows_that_commit_proofs()
        assert workflows, (
            "no workflow commits a proof file back — this proof must not pass "
            "by matching nothing")
        for fn, text in workflows:
            assert 'Purlin-Runner:' in text, (
                f"{fn} commits a proof file with no Purlin-Runner trailer, so "
                "sync_status will report 'runner not recorded'")
            # The trailer must be on the commit, not in a comment.
            assert re.search(r'-m\s+["\']Purlin-Runner:', text), (
                f"{fn} mentions Purlin-Runner but not as a commit message "
                "trailer; git only reads it from the commit")

    @pytest.mark.proof("verify_gate", "PROOF-8", "RULE-8")
    def test_every_commit_back_workflow_carries_both_loop_guards(self):
        workflows = _workflows_that_commit_proofs()
        assert workflows, "no commit-back workflow found"
        for fn, text in workflows:
            assert 'paths-ignore' in text, (
                f"{fn} has no paths-ignore, so its own proof commit retriggers it")
            tiers = set(re.findall(r'\.proofs-(\w+)\.json', text))
            ignored = re.search(r'paths-ignore:(.*?)(?:\n\s*\w+:|\Z)', text,
                                re.S).group(1)
            assert any(t in ignored or '*' in ignored for t in tiers), (
                f"{fn} writes {sorted(tiers)} but its paths-ignore does not "
                f"cover them: {ignored!r}")
            assert '[skip ci]' in text, (
                f"{fn} has no [skip ci] in its commit subject; paths-ignore "
                "alone does not cover every trigger path")
