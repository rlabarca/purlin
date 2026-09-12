"""Tests for verify_gate: 9 proofs covering the CI verification gate.

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
import purlin_server  # noqa: E402

GATE_PY = os.path.join(ROOT, 'scripts', 'ci', 'verify_gate.py')
WORKFLOW_DIR = os.path.join(ROOT, '.github', 'workflows')


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _spec(windows_proof=False):
    """A two-rule feature. RULE-2 is proved at unit tier either way; the
    optional extra `@unit @on(windows-2022)` proof covers the SAME rule, so
    declaring it changes the awaiting list and nothing else: same rules, same
    executed proofs, same vhash, same receipt."""
    extra = ('- PROOF-3 (RULE-2): msvcrt path locks on a real windows runner '
             '@unit @on(windows-2022)\n') if windows_proof else ''
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
                  receipt=True, platforms=None):
    """A temp Purlin project. Returns its root.

    The config registers `windows-2022` (the id `_spec` declares) unless
    `platforms` overrides the registry."""
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, '.purlin'))
    spec_dir = os.path.join(root, 'specs', 'app')
    os.makedirs(spec_dir)

    cfg = {'report': False, 'remote_verification': mode,
           'platforms': {'windows-2022': {'os': 'windows'}}
           if platforms is None else platforms}
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
        # A receipt rests on a recorded run (skill_verify RULE-12), so the
        # fixture writes one through the issuer's own helper rather than
        # hand-rolling the marker shape here.
        issue_receipts.write_run_marker(root)
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
        # The scoped form carries `@<platform-id>` before `.json`, so the
        # pattern has to admit it or a platform workflow drops out of every
        # scan that uses this helper.
        if re.search(r'git\s+add\s+\S*\.proofs-[\w*]+(?:@[\w.*-]+)?\.json', text) and \
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

        # The workflow that runs the gate fires on every workflow change, so a
        # runner workflow edit re-runs the gate that reads its output.
        text = open(os.path.join(WORKFLOW_DIR, 'verify-gate.yml')).read()
        for trigger in ('push', 'pull_request'):
            block = re.search(rf'^  {trigger}:\n((?:    .*\n)+)', text, re.M)
            assert block, f"verify-gate.yml has no {trigger} trigger with paths"
            assert "- '.github/workflows/**'" in block.group(1), (
                f"verify-gate.yml {trigger} paths must include .github/workflows/**:"
                f"\n{block.group(1)}")


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
                # Both hold a current receipt over the same vhash. The clean
                # one reads VERIFIED; the awaiting one is held at PASSING by
                # report_data RULE-35, which is the honest reading of a
                # platform that never ran and is itself what the gate must
                # refuse under `required`.
                assert feat['receipt'] and feat['receipt']['stale'] is False, (
                    f"fixture must hold a current receipt to isolate the "
                    f"variable, got {feat['receipt']} in {root}")
                assert feat['status'] == ('PASSING' if expect else 'VERIFIED'), (
                    f"fixture status {feat['status']} in {root}")
                assert bool(feat['awaiting_runner']) is expect, (
                    f"{root}: awaiting_runner={feat['awaiting_runner']}")

            code, out = _run(awaiting)
            assert code == 1, (
                f"a VERIFIED feature awaiting a runner must fail 'required', "
                f"got {code}:\n{out}")
            assert 'PROOF-3' in out and '@on(windows-2022)' in out, (
                f"the gate must name the awaited proof and its platform:\n{out}")

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
            assert 'Purlin-Platform:' in text, (
                f"{fn} commits a proof file with no Purlin-Platform trailer, so "
                "sync_status cannot cross-check the platform against the filename")
            # The trailers must be on the commit, not in a comment, and in
            # ONE -m: git builds a paragraph per -m and parses trailers out of
            # the last paragraph only.
            both = re.search(
                r'-m\s+"[^"]*Purlin-Runner:[^"]*?(?:\\n|\n)\s*'
                r'Purlin-Platform:[^"]*"', text)
            assert both, (
                f"{fn} does not carry both trailers in a single -m argument; "
                "a trailer in its own -m is a paragraph of its own and "
                "git log --format=%(trailers:key=...) returns nothing for it")

        # Why one -m, proved rather than asserted: the same two trailers, once
        # split across two -m flags and once in one, read back differently.
        repo = tempfile.mkdtemp()
        try:
            subprocess.run(['git', 'init', '-q', repo], check=True)
            for k, v in (('user.email', 't@e'), ('user.name', 't')):
                subprocess.run(['git', 'config', k, v], cwd=repo, check=True)
            open(os.path.join(repo, 'f'), 'w').write('x')
            subprocess.run(['git', 'add', 'f'], cwd=repo, check=True)

            def _runner_trailer():
                return subprocess.run(
                    ['git', 'log', '-1',
                     '--format=%(trailers:key=Purlin-Runner,valueonly)'],
                    cwd=repo, capture_output=True, text=True).stdout.strip()

            subprocess.run(['git', 'commit', '-q', '-m', 'split [skip ci]',
                            '-m', 'Purlin-Runner: gha/windows-2022',
                            '-m', 'Purlin-Platform: windows-2022'],
                           cwd=repo, check=True)
            assert _runner_trailer() == '', (
                "two -m flags must leave Purlin-Runner unreadable; if this "
                "ever changes, RULE-7's single -m requirement can relax")

            open(os.path.join(repo, 'f'), 'w').write('y')
            subprocess.run(['git', 'add', 'f'], cwd=repo, check=True)
            subprocess.run(['git', 'commit', '-q', '-m', 'joined [skip ci]',
                            '-m', 'Purlin-Runner: gha/windows-2022\n'
                                  'Purlin-Platform: windows-2022'],
                           cwd=repo, check=True)
            assert _runner_trailer() == 'gha/windows-2022', (
                "both trailers in one -m must read back as trailers")
        finally:
            shutil.rmtree(repo, ignore_errors=True)

    @pytest.mark.proof("verify_gate", "PROOF-8", "RULE-8")
    def test_every_commit_back_workflow_carries_both_loop_guards(self):
        workflows = _workflows_that_commit_proofs()
        assert workflows, "no commit-back workflow found"
        for fn, text in workflows:
            assert 'paths-ignore' in text, (
                f"{fn} has no paths-ignore, so its own proof commit retriggers it")
            # The scoped form is `.proofs-<tier>@<platform-id>.json`, so the
            # tier group has to stop at the `@` or a platform workflow reads
            # as writing no proof files at all.
            tiers = set(re.findall(r'\.proofs-([\w*]+)(?:@[\w.*-]+)?\.json', text))
            ignored = re.search(r'paths-ignore:(.*?)(?:\n\s*\w+:|\Z)', text,
                                re.S).group(1)
            assert any(t in ignored or '*' in ignored for t in tiers), (
                f"{fn} writes {sorted(tiers)} but its paths-ignore does not "
                f"cover them: {ignored!r}")
            assert '[skip ci]' in text, (
                f"{fn} has no [skip ci] in its commit subject; paths-ignore "
                "alone does not cover every trigger path")


class TestRegistryErrorsAndByPlatform:

    @pytest.mark.proof("verify_gate", "PROOF-9", "RULE-9", tier="integration")
    def test_registry_errors_exit_two_in_every_mode_and_by_platform_counts(self):
        """Evidence read through a broken registry is unreadable evidence: a
        proof naming a dropped id may match every host of its family or
        nothing at all, and the gate cannot tell which."""
        root = _make_project(mode='required', windows_proof=True)
        cfg_path = os.path.join(root, '.purlin', 'config.json')
        spec_dir = os.path.join(root, 'specs', 'app')
        try:
            # Healthy registry: the By platform section counts the awaited proof.
            code, out = _run(root)
            assert code == 1, out
            assert 'By platform (1):' in out, out
            assert 'windows-2022: 0 proved, 1 awaiting, 0 failing (1 feature)' in out, out

            # A scoped result arrives: the same line now reads proved.
            with open(os.path.join(spec_dir, 'locking.proofs-unit@windows-2022.json'),
                      'w') as f:
                json.dump({'tier': 'unit', 'platform': 'windows-2022', 'proofs': [
                    {'feature': 'locking', 'id': 'PROOF-3', 'rule': 'RULE-2',
                     'test_file': 'tests/test_lock.py', 'test_name': 'test_msvcrt',
                     'status': 'pass', 'tier': 'unit', 'platform': 'windows-2022'}]}, f)
            code, out = _run(root)
            assert 'windows-2022: 1 proved, 0 awaiting, 0 failing (1 feature)' in out, out
            assert 'Awaiting a runner' not in out, out

            # Break the registry: exit 2 under every mode, with the error named.
            for mode in ('required', 'optional', 'off'):
                with open(cfg_path, 'w') as f:
                    json.dump({'report': False, 'remote_verification': mode,
                               'platforms': {'windows-2022': {'os': 'windows',
                                                              'vresion': '10'}}}, f)
                code, out = _run(root)
                assert code == 2, (
                    f"mode {mode!r}: a registry error must be a bad invocation "
                    f"(2), got {code}:\n{out}")
                assert 'windows-2022' in out and 'vresion' in out, (
                    f"mode {mode!r}: the error must be printed:\n{out}")
                assert 'PASS' not in out, (
                    f"mode {mode!r}: unreadable evidence must never pass:\n{out}")
        finally:
            shutil.rmtree(root)


class TestCommitBackPushSurvivesARace:

    @pytest.mark.proof("verify_gate", "PROOF-10", "RULE-10", tier="integration")
    def test_every_commit_back_workflow_retries_its_push(self):
        """One branch, several platform workflows, one push target. A plain
        `git push` fails a race it did nothing wrong to lose, and the job goes
        red over scheduling rather than over a proof."""
        workflows = [(fn, text) for fn, text in _workflows_that_commit_proofs()
                     if 'proofs' in fn]
        assert workflows, (
            "no *proofs*.yml workflow commits a proof file back; this proof "
            "must not pass by matching nothing")
        for fn, text in workflows:
            # The push is inside a retry loop, not on its own.
            loop = re.search(r'for\s+attempt\s+in\s+([\d\s]+);\s*do(.*?)\bdone\b',
                             text, re.S)
            assert loop, (
                f"{fn} pushes its proof commit without a retry loop; a second "
                "platform runner committing first turns this job red")
            attempts = loop.group(1).split()
            assert len(attempts) == 3, (
                f"{fn} retries {len(attempts)} times, not 3: an unbounded loop "
                "hides a genuinely broken push and a single attempt loses "
                "every race")
            body = loop.group(2)
            assert re.search(r'git pull --rebase origin "\$GITHUB_REF_NAME"',
                             body), (
                f"{fn}'s retry loop does not rebase onto the branch before "
                "pushing, so the retry loses the same race again")
            assert re.search(r'git push origin "HEAD:\$GITHUB_REF_NAME"', body), (
                f"{fn}'s retry loop does not push inside the loop")

            after = text[loop.end():]
            assert re.search(r'^\s*exit 1\s*$', after, re.M), (
                f"{fn} exits 0 after three failed pushes, so a genuinely "
                "broken push reports success")

            # The loop and the provenance trailers are required together,
            # and the trailers share one -m (RULE-7).
            assert re.search(
                r'-m\s+"[^"]*Purlin-Runner:[^"]*?(?:\\n|\n)\s*'
                r'Purlin-Platform:[^"]*"', text), (
                f"{fn} retries its push but records no readable provenance "
                "trailers")


class TestCommitBackWorkflowsPreflightTheMigration:

    @pytest.mark.proof("verify_gate", "PROOF-11", "RULE-11", tier="integration")
    def test_preflight_runs_before_the_proofs_and_fails_only_on_real_gaps(self):
        """RULE-11: the runner is the machine nobody watches. Stale plugin
        copies there write agnostic files that satisfy nothing, and the job
        still goes green."""
        workflows = [(fn, text) for fn, text in _workflows_that_commit_proofs()
                     if fn.endswith('-proofs.yml')]
        assert workflows, (
            "no *-proofs.yml workflow commits a proof file back; this proof "
            "must not pass by matching nothing")
        for fn, text in workflows:
            m = re.search(r'run:.*scripts/update/migrate\.py.*--check', text)
            if m is None:
                m = re.search(r'scripts/update/migrate\.py[^\n]*\n?[^\n]*--check',
                              text)
            assert m, f"{fn} runs the proofs without the migrate.py --check preflight"
            run_steps = [rm.start() for rm in
                         re.finditer(r'(?m)^\s+- name:\s+Run\b', text)]
            assert run_steps, f"{fn} has no step whose name begins with Run"
            assert m.start() < min(run_steps), (
                f"{fn} runs its preflight after the proofs; a stale plugin copy "
                "would already have written the files by then")

        # The script's own verdict: blocking ids fail, advisory ids do not.
        migrate = os.path.join(ROOT, 'scripts', 'update', 'migrate.py')

        def _check(root):
            result = subprocess.run(
                [sys.executable, migrate, '--check', '--project-root', root],
                capture_output=True, text=True)
            return result.returncode, json.loads(result.stdout)['pending']

        blocking = tempfile.mkdtemp()
        advisory = tempfile.mkdtemp()
        try:
            for root in (blocking, advisory):
                os.makedirs(os.path.join(root, '.purlin', 'plugins'))
                os.makedirs(os.path.join(root, 'specs', 'app'))
                config = dict(json.load(open(os.path.join(
                    ROOT, 'templates', 'config.json'))))
                config['version'] = purlin_server._read_version()
                with open(os.path.join(root, '.purlin', 'config.json'), 'w') as f:
                    json.dump(config, f)
                with open(os.path.join(root, 'specs', 'app', 'demo.md'), 'w') as f:
                    f.write('# Feature: demo\n\n## Rules\n- RULE-1: does it\n\n'
                            '## Proof\n- PROOF-1 (RULE-1): assert it @unit\n')

            # Blocking: a stale plugin copy and a legacy proof file.
            shutil.copyfile(
                os.path.join(ROOT, 'scripts', 'proof', 'pytest_purlin.py'),
                os.path.join(blocking, '.purlin', 'plugins', 'pytest_purlin.py'))
            with open(os.path.join(blocking, '.purlin', 'plugins',
                                   'pytest_purlin.py'), 'a') as f:
                f.write('\n# drift\n')
            legacy_name = 'demo.proofs-' + 'win' + 'dows' + '.json'
            with open(os.path.join(blocking, 'specs', 'app', legacy_name),
                      'w') as f:
                json.dump({'tier': 'win' + 'dows', 'proofs': []}, f)
            code, pending = _check(blocking)
            ids = {entry['id'] for entry in pending}
            assert code == 1, (code, pending)
            assert {'plugin-copies-stale', 'legacy-proof-file'} <= ids, ids

            # Advisory only: a version 1 receipt is reported and passes.
            with open(os.path.join(advisory, 'specs', 'app',
                                   'demo.receipt.json'), 'w') as f:
                json.dump({'feature': 'demo', 'vhash': 'x', 'rules': ['RULE-1'],
                           'proofs': []}, f)
            code, pending = _check(advisory)
            ids = {entry['id'] for entry in pending}
            assert ids == {'receipt-v1'}, ids
            assert code == 0, (
                "a version 1 receipt must not fail the preflight: it says "
                "nothing about the run that is about to happen")
        finally:
            shutil.rmtree(blocking, ignore_errors=True)
            shutil.rmtree(advisory, ignore_errors=True)
