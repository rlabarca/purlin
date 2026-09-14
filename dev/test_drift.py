"""Tests for the drift report (specs/mcp/drift.md)."""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin import drift as purlin_drift


def _git(args, cwd, check=True):
    """Run a git command in the given directory, capturing output."""
    return subprocess.run(
        ['git'] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _rmtree(path):
    """Remove a tree that holds a git repository, on every operating system.

    Git marks loose objects and packs read-only. A read-only file inside a
    writable directory still unlinks on POSIX; on Windows it does not, and the
    removal raises PermissionError. Clearing the bit and retrying once is the
    whole difference.
    """
    def _retry(func, failed, _exc_info):
        os.chmod(failed, stat.S_IWRITE)
        func(failed)

    shutil.rmtree(path, onerror=_retry)


def _create_bare_repo(bare_path, initial_file='spec.md', initial_content='# initial'):
    """Create a bare git repo with one commit. Returns the initial commit SHA."""
    git_cmd = ['git', '-c', 'init.defaultBranch=main']
    subprocess.run(git_cmd + ['init', '--bare', '-q', bare_path], check=True,
                   capture_output=True)
    work_dir = bare_path + '_work'
    subprocess.run(['git', 'clone', '-q', bare_path, work_dir],
                   check=True, capture_output=True)
    with open(os.path.join(work_dir, initial_file), 'w') as f:
        f.write(initial_content)
    _git(['config', 'user.email', 'test@test.com'], work_dir)
    _git(['config', 'user.name', 'Test'], work_dir)
    _git(['add', '-A'], work_dir)
    _git(['commit', '-m', 'initial spec'], work_dir)
    # Push to bare — try main then master
    r = subprocess.run(['git', 'push', '-q', 'origin', 'main'],
                       cwd=work_dir, capture_output=True)
    if r.returncode != 0:
        subprocess.run(['git', 'push', '-q', 'origin', 'master'],
                       cwd=work_dir, capture_output=True, check=True)
    sha = _git(['rev-parse', 'HEAD'], work_dir).stdout.strip()
    _rmtree(work_dir)
    return sha


def _advance_bare_repo(bare_path, file_path='spec.md', new_content='# updated'):
    """Add a new commit to a bare repo. Returns the new HEAD SHA."""
    work_dir = bare_path + '_work2'
    subprocess.run(['git', 'clone', '-q', bare_path, work_dir],
                   check=True, capture_output=True)
    _git(['config', 'user.email', 'test@test.com'], work_dir)
    _git(['config', 'user.name', 'Test'], work_dir)
    with open(os.path.join(work_dir, file_path), 'w') as f:
        f.write(new_content)
    _git(['add', '-A'], work_dir)
    _git(['commit', '-m', 'update spec'], work_dir)
    r = subprocess.run(['git', 'push', '-q'],
                       cwd=work_dir, capture_output=True)
    if r.returncode != 0:
        subprocess.run(['git', 'push', '-q', 'origin', 'master'],
                       cwd=work_dir, capture_output=True, check=True)
    sha = _git(['rev-parse', 'HEAD'], work_dir).stdout.strip()
    _rmtree(work_dir)
    return sha


def _init_project(project_root, bare_path, anchor_name, pinned_sha):
    """Set up a minimal Purlin project with a single external anchor."""
    os.makedirs(os.path.join(project_root, '.purlin'))
    os.makedirs(os.path.join(project_root, 'specs', '_anchors'))

    anchor_path = os.path.join(project_root, 'specs', '_anchors', f'{anchor_name}.md')
    with open(anchor_path, 'w') as f:
        f.write(
            f'# Anchor: {anchor_name}\n\n'
            f'> Source: {bare_path}\n'
            f'> Pinned: {pinned_sha}\n\n'
            '## What it does\n\nExternal anchor for testing.\n\n'
            '## Rules\n\n'
            '- RULE-1: External constraint one\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Verify constraint one\n'
        )

    _git(['-c', 'init.defaultBranch=main', 'init', '-q'], project_root)
    _git(['config', 'user.email', 'test@test.com'], project_root)
    _git(['config', 'user.name', 'Test'], project_root)
    _git(['add', '-A'], project_root)
    _git(['commit', '-m', 'verify: initial project'], project_root)


class TestDriftExternalAndLocalModification:
    """drift RULE-9 and RULE-13: a pin behind its source, named by the anchor."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.bare_path = tempfile.mkdtemp()
        shutil.rmtree(self.bare_path)  # _create_bare_repo expects path to not exist

    def teardown_method(self):
        shutil.rmtree(self.project_root, ignore_errors=True)
        shutil.rmtree(self.bare_path, ignore_errors=True)
        work1 = self.bare_path + '_work'
        work2 = self.bare_path + '_work2'
        shutil.rmtree(work1, ignore_errors=True)
        shutil.rmtree(work2, ignore_errors=True)

    @pytest.mark.proof("drift", "PROOF-10", "RULE-9", tier="integration")
    def test_external_advance_plus_local_modification_surfaces_both(self):
        """Advance external source AND modify local anchor: drift returns both stale entry
        in external_anchor_drift AND a spec_changes entry with the new rule."""
        # Step 1: Create bare repo at a known SHA and project pinned to it
        initial_sha = _create_bare_repo(self.bare_path, 'spec.md', '# external policy v1')
        _init_project(self.project_root, self.bare_path, 'security_policy', initial_sha)

        # Step 2: Advance the external repo (making the pinned SHA stale)
        _advance_bare_repo(self.bare_path, 'spec.md', '# external policy v2 — new constraint')

        # Step 3: Modify the local anchor file — add a new rule (RULE-2)
        anchor_path = os.path.join(
            self.project_root, 'specs', '_anchors', 'security_policy.md'
        )
        with open(anchor_path, 'w') as f:
            f.write(
                f'# Anchor: security_policy\n\n'
                f'> Source: {self.bare_path}\n'
                f'> Pinned: {initial_sha}\n\n'
                '## What it does\n\nExternal anchor for testing.\n\n'
                '## Rules\n\n'
                '- RULE-1: External constraint one\n'
                '- RULE-2: New constraint added locally\n\n'
                '## Proof\n\n'
                '- PROOF-1 (RULE-1): Verify constraint one\n'
                '- PROOF-2 (RULE-2): Verify constraint two\n'
            )
        _git(['add', '-A'], self.project_root)
        _git(['commit', '-m', 'feat: add RULE-2 to local anchor'], self.project_root)

        # Step 4: Run drift and parse results
        result_text = purlin_drift.drift(self.project_root)
        data = json.loads(result_text)

        # Verify external_anchor_drift has a stale entry for security_policy
        stale_entries = [
            e for e in data.get('pins', [])
            if e.get('anchor') == 'security_policy' and e.get('status') == 'behind'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 pins entry that is behind for security_policy, "
            f"got: {data.get('pins', [])}"
        )

        # Verify spec_changes includes security_policy with new_rules containing RULE-2
        policy_changes = [
            c for c in data.get('spec_changes', [])
            if c.get('spec') == 'security_policy'
        ]
        assert len(policy_changes) == 1, (
            f"Expected 1 spec_changes entry for security_policy, "
            f"got: {data.get('spec_changes', [])}"
        )
        assert 'RULE-2' in policy_changes[0].get('new_rules', []), (
            f"Expected RULE-2 in new_rules, got: {policy_changes[0]}"
        )

    @pytest.mark.proof("drift", "PROOF-15", "RULE-13", tier="integration")
    def test_anchor_name_in_drift_matches_spec_name_not_repo_path(self):
        """The anchor field in external_anchor_drift uses the spec's anchor name
        (from '# Anchor: <name>'), not the external repo URL or file path."""
        # Step 1: Create bare repo and project with anchor named 'local_security'
        initial_sha = _create_bare_repo(self.bare_path, 'constraints.md', '# constraints v1')
        _init_project(self.project_root, self.bare_path, 'local_security', initial_sha)

        # Step 2: Advance the external repo to trigger a stale status
        _advance_bare_repo(self.bare_path, 'constraints.md', '# constraints v2')

        # Step 3: Add a commit so drift has a range to work with
        placeholder_path = os.path.join(self.project_root, 'placeholder.txt')
        with open(placeholder_path, 'w') as f:
            f.write('trigger drift range\n')
        _git(['add', '-A'], self.project_root)
        _git(['commit', '-m', 'feat: add placeholder'], self.project_root)

        # Step 4: Run drift and verify anchor name in result
        result_text = purlin_drift.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('pins', [])
            if e.get('status') == 'behind'
        ]
        assert len(stale_entries) >= 1, (
            f"Expected at least 1 pins entry that is behind, "
            f"got: {data.get('pins', [])}"
        )

        # The anchor field must be 'local_security' (the spec name),
        # not the bare_path (repo path) or 'constraints.md' (file path)
        anchor_names = [e.get('anchor') for e in stale_entries]
        assert 'local_security' in anchor_names, (
            f"Expected anchor='local_security' in stale entries, got anchor names: {anchor_names}. "
            f"Full entries: {stale_entries}"
        )
        for entry in stale_entries:
            assert entry.get('anchor') != self.bare_path, (
                f"anchor field must not be the repo path, got: {entry.get('anchor')}"
            )
            assert entry.get('anchor') != 'constraints.md', (
                f"anchor field must not be the file path, got: {entry.get('anchor')}"
            )


class TestDriftExternalAnchorStaleness:
    """drift RULE-10: the source advances past the pin, and the row says so."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        self.bare_path = tempfile.mkdtemp()
        shutil.rmtree(self.bare_path)  # _create_bare_repo expects path to not exist

    def teardown_method(self):
        shutil.rmtree(self.project_root, ignore_errors=True)
        shutil.rmtree(self.bare_path, ignore_errors=True)
        work1 = self.bare_path + '_work'
        work2 = self.bare_path + '_work2'
        shutil.rmtree(work1, ignore_errors=True)
        shutil.rmtree(work2, ignore_errors=True)

    @pytest.mark.proof("drift", "PROOF-12", "RULE-10", tier="integration")
    def test_mixed_anchor_stale_when_external_source_advances(self):
        """Mixed anchor (both > Source:/> Pinned: tracking and local rules): when the
        external source advances, drift returns an external_anchor_drift entry with
        status=stale for the anchor."""
        # Step 1: Create bare repo at a known SHA and project with a mixed anchor
        # A mixed anchor has both external tracking fields (Source, Pinned) AND local rules
        initial_sha = _create_bare_repo(self.bare_path, 'policy.md', '# policy v1')

        # Build a mixed anchor: external tracking + its own local rules
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        os.makedirs(os.path.join(self.project_root, 'specs', '_anchors'))
        anchor_path = os.path.join(
            self.project_root, 'specs', '_anchors', 'mixed_policy.md'
        )
        with open(anchor_path, 'w') as f:
            f.write(
                '# Anchor: mixed_policy\n\n'
                f'> Source: {self.bare_path}\n'
                f'> Pinned: {initial_sha}\n\n'
                '## What it does\n\n'
                'Mixed anchor with both external tracking and local rules.\n\n'
                '## Rules\n\n'
                '- RULE-1: Locally defined constraint one\n'
                '- RULE-2: Locally defined constraint two\n\n'
                '## Proof\n\n'
                '- PROOF-1 (RULE-1): Verify local constraint one\n'
                '- PROOF-2 (RULE-2): Verify local constraint two\n'
            )
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], self.project_root)
        _git(['config', 'user.email', 'test@test.com'], self.project_root)
        _git(['config', 'user.name', 'Test'], self.project_root)
        _git(['add', '-A'], self.project_root)
        _git(['commit', '-m', 'verify: initial project with mixed anchor'], self.project_root)

        # Step 2: Advance the external repo — the pinned SHA is now stale
        _advance_bare_repo(self.bare_path, 'policy.md', '# policy v2 — new constraint added')

        # Step 3: Make a local commit so drift has a range to compare
        placeholder = os.path.join(self.project_root, 'placeholder.txt')
        with open(placeholder, 'w') as f:
            f.write('trigger drift range\n')
        _git(['add', '-A'], self.project_root)
        _git(['commit', '-m', 'feat: add placeholder'], self.project_root)

        # Step 4: Run drift and verify external_anchor_drift has a stale entry
        result_text = purlin_drift.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('pins', [])
            if e.get('anchor') == 'mixed_policy' and e.get('status') == 'behind'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 pins entry that is behind for mixed_policy, "
            f"got: {data.get('pins', [])}"
        )

    @pytest.mark.proof("drift", "PROOF-11", "RULE-10", tier="integration")
    def test_stale_entry_includes_remote_sha(self):
        """When the external source advances past the pinned SHA, drift returns an
        external_anchor_drift entry with status=stale AND the remote_sha field populated
        with the actual new HEAD of the remote."""
        # Step 1: Create bare repo at initial SHA and project pinned to it
        initial_sha = _create_bare_repo(self.bare_path, 'spec.md', '# spec v1')
        _init_project(self.project_root, self.bare_path, 'external_anchor', initial_sha)

        # Step 2: Advance the external repo — get the new HEAD SHA
        new_sha = _advance_bare_repo(self.bare_path, 'spec.md', '# spec v2')

        # Step 3: Make a local commit so drift has a range
        placeholder = os.path.join(self.project_root, 'placeholder.txt')
        with open(placeholder, 'w') as f:
            f.write('trigger drift range\n')
        _git(['add', '-A'], self.project_root)
        _git(['commit', '-m', 'feat: add placeholder'], self.project_root)

        # Step 4: Run drift and verify both status=stale and remote_sha is present
        result_text = purlin_drift.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('pins', [])
            if e.get('anchor') == 'external_anchor' and e.get('status') == 'behind'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 pins entry that is behind for external_anchor, "
            f"got: {data.get('pins', [])}"
        )
        entry = stale_entries[0]
        assert 'remote_sha' in entry, (
            f"Expected remote_sha field in stale entry, got: {entry}"
        )
        # remote_sha is truncated to 7 characters by the pin check
        assert len(entry['remote_sha']) == 7, (
            f"Expected remote_sha to be 7 chars (truncated), got: {entry['remote_sha']!r}"
        )
        # Verify the remote_sha matches the beginning of the actual new commit SHA
        assert new_sha.startswith(entry['remote_sha']), (
            f"Expected remote_sha {entry['remote_sha']!r} to be prefix of actual new SHA "
            f"{new_sha!r}"
        )


class TestDriftSinceValidation:
    """drift RULE-1: the `since` argument is validated before any subprocess."""

    def _repo(self, root):
        os.makedirs(os.path.join(root, '.purlin'))
        os.makedirs(os.path.join(root, 'specs', 'mcp'))
        with open(os.path.join(root, 'specs', 'mcp', 'thing.md'), 'w') as f:
            f.write('# Feature: thing\n\n> Scope: src/thing.py\n\n'
                    '## Rules\n\n- RULE-1: Does the thing\n\n'
                    '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n')
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
        _git(['config', 'user.email', 'test@test.com'], root)
        _git(['config', 'user.name', 'Test'], root)
        for i in range(3):
            with open(os.path.join(root, f'f{i}.txt'), 'w') as f:
                f.write(str(i))
            _git(['add', '-A'], root)
            _git(['commit', '-q', '-m', f'chore: commit {i}'], root)

    @pytest.mark.proof("drift", "PROOF-1", "RULE-1", tier="integration")
    def test_hostile_since_is_refused_before_any_subprocess(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        self._repo(root)

        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args) if isinstance(args, (list, tuple)) else [args])
            return real_run(args, *rest, **kwargs)

        purlin_drift.subprocess.run = spy
        try:
            refused = json.loads(purlin_drift.drift(root, since='--output=/tmp/x'))
            refused_calls = list(calls)
            calls.clear()
            allowed = json.loads(purlin_drift.drift(root, since='2'))
            allowed_calls = list(calls)
        finally:
            purlin_drift.subprocess.run = real_run

        assert refused.get('error') == 'rejected since', refused
        reason = refused.get('reason', '')
        assert 'digits only' in reason and 'YYYY-MM-DD' in reason, reason
        assert refused_calls == [], (
            f"a refused since still reached a subprocess: {refused_calls}")

        # Control: a valid since does resolve, and does run git.
        assert 'commits' in allowed, allowed
        assert allowed_calls, "the control call ran no subprocess at all"


class TestDriftBatchedDiffStat:
    """drift RULE-6: one numstat over the range, not one subprocess per file."""

    FILE_COUNT = 12

    def _repo(self, root):
        os.makedirs(os.path.join(root, '.purlin'))
        os.makedirs(os.path.join(root, 'specs', 'mcp'))
        with open(os.path.join(root, 'specs', 'mcp', 'thing.md'), 'w') as f:
            f.write('# Feature: thing\n\n> Scope: src/thing.py\n\n'
                    '## Rules\n\n- RULE-1: Does the thing\n\n'
                    '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n')
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
        _git(['config', 'user.email', 'test@test.com'], root)
        _git(['config', 'user.name', 'Test'], root)
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'chore: baseline'], root)
        # One commit adding FILE_COUNT files, each with a different line count.
        os.makedirs(os.path.join(root, 'src'))
        for i in range(self.FILE_COUNT):
            with open(os.path.join(root, 'src', f'mod{i}.py'), 'w') as f:
                f.write('\n'.join(f'line {j}' for j in range(i + 1)) + '\n')
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'feat: twelve modules'], root)

    @pytest.mark.proof("drift", "PROOF-7", "RULE-6", tier="integration")
    def test_one_numstat_call_covers_every_changed_file(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        self._repo(root)

        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args) if isinstance(args, (list, tuple)) else [args])
            return real_run(args, *rest, **kwargs)

        purlin_drift.subprocess.run = spy
        try:
            data = json.loads(purlin_drift.drift(root, since='1'))
        finally:
            purlin_drift.subprocess.run = real_run

        numstat_calls = [c for c in calls if '--numstat' in c]
        assert len(numstat_calls) == 1, (
            f"expected exactly 1 numstat subprocess for {self.FILE_COUNT} files, "
            f"got {len(numstat_calls)}: {numstat_calls}")

        entries = {e['path']: e['diff_stat'] for e in data['files']
                   if e['path'].startswith('src/mod')}
        assert len(entries) == self.FILE_COUNT, entries
        for path, stat in entries.items():
            assert re.match(r'^\+\d+ -\d+$', stat), (path, stat)

        # Every value equals what a per-file numstat reports for that path.
        for path, stat in entries.items():
            r = real_run(['git', 'diff', '--numstat', 'HEAD~1..HEAD', '--', path],
                         cwd=root, capture_output=True, text=True)
            parts = r.stdout.strip().split('\t')
            assert stat == f'+{parts[0]} -{parts[1]}', (path, stat, r.stdout)


class TestDriftCompactPayload:
    """drift RULE-17: the payload serializes compact, since no person reads it."""

    def _repo(self, root):
        os.makedirs(os.path.join(root, '.purlin'))
        os.makedirs(os.path.join(root, 'specs', 'mcp'))
        with open(os.path.join(root, 'specs', 'mcp', 'thing.md'), 'w') as f:
            f.write('# Feature: thing\n\n> Scope: src/thing.py\n\n'
                    '## Rules\n\n- RULE-1: Does the thing\n\n'
                    '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n')
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
        _git(['config', 'user.email', 'test@test.com'], root)
        _git(['config', 'user.name', 'Test'], root)
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'chore: baseline'], root)
        os.makedirs(os.path.join(root, 'src'))
        with open(os.path.join(root, 'src', 'thing.py'), 'w') as f:
            f.write('def thing():\n    return 1\n')
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'feat: thing'], root)

    @pytest.mark.proof("drift", "PROOF-19", "RULE-17", tier="integration")
    def test_payload_carries_no_pretty_printing_whitespace(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        self._repo(root)

        text = purlin_drift.drift(root, since='1')

        assert '\n  ' not in text, "payload still carries indentation"
        assert '": ' not in text, "payload still carries a space after the key separator"

        data = json.loads(text)
        assert isinstance(data, dict), type(data)
        for key in ('since', 'commits', 'files', 'spec_changes', 'pins',
                    'rule_details', 'roles'):
            assert key in data, (key, sorted(data))

        indented = json.dumps(data, indent=2)
        assert len(text) < len(indented), (len(text), len(indented))


# Rule-level detail for specs with changed behavior files (RULE-16).

_LEDGER_LONG_RULE = (
    "A posting is refused when its debits and credits do not balance to the "
    "cent, when the account it names is closed, or when the value date falls "
    "outside the open period; the rejection names the first of the failing "
    "checks and the ledger is left exactly as it was before the call, with no "
    "partial entry written and no identifier consumed, so a retry after the "
    "caller fixes the input lands the same entry once and only once in the "
    "journal file for that day. The refusal text is the same on each retry, "
    "the journal keeps the bytes it held, and nothing downstream is replayed "
    "or reconciled by hand later on"
)


def _write(path, text):
    """Write `text` to `path`, creating the parent directory."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        fh.write(text)


def _proof_file(root, feature, rule_ids):
    """Write a unit proof file marking each of `rule_ids` as passing."""
    path = os.path.join(root, '.purlin', 'runtime', 'proofs',
                        '%s.unit.json' % feature)
    _write(path, json.dumps({'tier': 'unit', 'proofs': [
        {'feature': feature, 'id': 'PROOF-%s' % rid.split('-')[1],
         'rule': rid, 'test_file': 'tests/test_%s.py' % feature,
         'test_name': 'test_%s' % rid.lower().replace('-', '_'),
         'status': 'pass', 'tier': 'unit'}
        for rid in rule_ids]}))


class TestDriftRuleDetails:
    """drift RULE-16: one verdict behind the counts, and one stable order."""

    def _repo(self, root):
        os.makedirs(os.path.join(root, '.purlin'))

        # An anchor of 3 rules, all proved, required by `ledger`.
        _write(os.path.join(root, 'specs', '_anchors', 'money_anchor.md'),
               '# Anchor: money_anchor\n\n'
               '> Type: schema\n'
               '> Description: Money handling every ledger feature inherits\n\n'
               '## Rules\n\n'
               '- RULE-1: Amounts are integer cents, never floats\n'
               '- RULE-2: Every amount carries an ISO 4217 currency code\n'
               '- RULE-3: Rounding is half up, applied once, at the boundary\n\n'
               '## Proof\n\n'
               '- PROOF-1 (RULE-1): Post 0.1 plus 0.2 and verify 30 cents\n'
               '- PROOF-2 (RULE-2): Post without a code and verify the refusal\n'
               '- PROOF-3 (RULE-3): Split 10 cents three ways and verify 4/3/3\n')
        _proof_file(root, 'money_anchor', ['RULE-1', 'RULE-2', 'RULE-3'])

        # `ledger`: 4 own rules, 3 of them proved, requiring the anchor.
        _write(os.path.join(root, 'specs', 'ledger', 'ledger.md'),
               '# Feature: ledger\n\n'
               '> Requires: money_anchor\n'
               '> Description: Double entry journal\n'
               '> Scope: src/ledger/posting.py\n\n'
               '## Rules\n\n'
               '- RULE-1: Every posting writes one debit and one credit row\n'
               '- RULE-2: A posting identifier is never reused\n'
               '- RULE-3: The journal file is appended, never rewritten\n'
               '- RULE-4: %s\n\n'
               '## Proof\n\n'
               '- PROOF-1 (RULE-1): Post once and verify two rows\n'
               '- PROOF-2 (RULE-2): Post twice and verify two identifiers\n'
               '- PROOF-3 (RULE-3): Post twice and verify the first bytes hold\n'
               '- PROOF-4 (RULE-4): Post an unbalanced entry and verify refusal\n'
               % _LEDGER_LONG_RULE)
        _proof_file(root, 'ledger', ['RULE-1', 'RULE-2', 'RULE-3'])

        # Two more features with changed scope files, so the order of
        # `rule_details` is something a run can get wrong.
        for name, src in (('money_gateway', 'gateway.py'),
                          ('posting_api', 'api.py')):
            _write(os.path.join(root, 'specs', 'ledger', '%s.md' % name),
                   '# Feature: %s\n\n'
                   '> Description: %s\n'
                   '> Scope: src/ledger/%s\n\n'
                   '## Rules\n\n'
                   '- RULE-1: Returns the settled balance\n\n'
                   '## Proof\n\n'
                   '- PROOF-1 (RULE-1): Call it and verify the balance\n'
                   % (name, name, src))
            _proof_file(root, name, ['RULE-1'])

        for src in ('posting.py', 'gateway.py', 'api.py'):
            _write(os.path.join(root, 'src', 'ledger', src), 'def run():\n    return 0\n')

        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
        _git(['config', 'user.email', 'test@test.com'], root)
        _git(['config', 'user.name', 'Test'], root)
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'verify: initial'], root)

        # Change every scope file, so all three features carry changed behavior.
        for src in ('posting.py', 'gateway.py', 'api.py'):
            _write(os.path.join(root, 'src', 'ledger', src),
                   'def run():\n    return 0\n\n\ndef batch():\n    return 1\n')
        _git(['add', '-A'], root)
        _git(['commit', '-q', '-m', 'feat: batch posting'], root)

    def _rule_details_under_seed(self, root, seed):
        """Return the rule_details JSON text from a fresh process, hash seed set."""
        env = dict(os.environ)
        env['PYTHONHASHSEED'] = seed
        code = (
            'import json, sys\n'
            'sys.path.insert(0, %r)\n'
            'from purlin import drift\n'
            "data = json.loads(drift.drift(%r))\n"
            "sys.stdout.write(json.dumps(data['rule_details'], sort_keys=False))\n"
            % (os.path.dirname(os.path.dirname(
                os.path.abspath(purlin_drift.__file__))), root)
        )
        r = subprocess.run([sys.executable, '-c', code], cwd=root, env=env,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout

    @pytest.mark.proof("drift", "PROOF-18", "RULE-16", tier="integration")
    def test_rule_details_counts_one_rule_set_in_one_order(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        self._repo(root)

        data = json.loads(purlin_drift.drift(root))
        details = data['rule_details']

        assert 'ledger' in details, sorted(details)
        ledger = details['ledger']

        # Both counts come from the one verdict, so they count the same rules:
        # 4 own plus the anchor's 3, of which 3 own and all 3 anchor rules pass.
        assert ledger['total_rules'] == 7, (
            "total_rules counted %s, not the 4 own plus 3 inherited rules the "
            "one payload counts" % ledger['total_rules'])

        # One id per rule worth naming, and nothing for the other six.
        assert ledger['unproved'] == ['RULE-4'], ledger['unproved']
        assert ledger['lowest_state'] == 'Drafted', ledger['lowest_state']
        assert ledger['spec_path'] == 'specs/ledger/ledger.md', ledger['spec_path']

        # Own rules, in RULE number order, id and description and nothing else.
        assert [r['rule_id'] for r in ledger['rules']] == [
            'RULE-1', 'RULE-2', 'RULE-3', 'RULE-4'], ledger['rules']
        assert len(ledger['rules']) == 4, ledger['rules']
        for rule in ledger['rules']:
            assert set(rule) == {'rule_id', 'description', 'state', 'risk',
                                 'origin'}, sorted(rule)

        # The long description is cut on a word boundary and says it was cut;
        # the short ones come back whole.
        assert len(_LEDGER_LONG_RULE) == 600, len(_LEDGER_LONG_RULE)
        capped = ledger['rules'][3]['description']
        assert len(capped) == 204, (len(capped), capped)
        assert capped.endswith(' ...'), capped
        assert capped.startswith('A posting is refused when its debits'), capped
        assert capped[:-4] == _LEDGER_LONG_RULE[:200], capped
        assert ledger['rules'][0]['description'] == (
            'Every posting writes one debit and one credit row')
        assert ledger['rules'][1]['description'] == (
            'A posting identifier is never reused')
        assert ledger['rules'][2]['description'] == (
            'The journal file is appended, never rewritten')

        assert 'src/ledger/posting.py' in ledger['changed_files'], ledger

        # Specs in name order.
        assert list(details) == ['ledger', 'money_gateway', 'posting_api'], \
            list(details)

        # Two processes whose string hashes fall in different orders return the
        # same bytes. An unsorted walk of the changed-behavior set passes within
        # one process and fails here.
        first = self._rule_details_under_seed(root, '0')
        second = self._rule_details_under_seed(root, '1')
        assert first == second, (
            "rule_details is not byte identical across two runs:\n%s\n%s"
            % (first[:400], second[:400]))


# The anchor a report measures from, how a changed file is classified, what
# the report carries, and what a pin says when it is not behind (RULE-2 to
# RULE-5, RULE-7, RULE-8 and RULE-10).

def _commit(root, message):
    _git(['add', '-A'], root)
    _git(['commit', '-q', '-m', message], root)


def _new_repo(root):
    """A git repository holding `.purlin/config.json` as its first commit."""
    os.makedirs(root, exist_ok=True)
    _write(os.path.join(root, '.purlin', 'config.json'), '{}')
    _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
    _git(['config', 'user.email', 'test@test.com'], root)
    _git(['config', 'user.name', 'Test'], root)
    _commit(root, 'chore: purlin init')
    return root


class TestDriftSinceAnchor:
    """drift RULE-2: the last record, then the last tag, then the setup commit."""

    @pytest.mark.proof("drift", "PROOF-3", "RULE-2", tier="integration")
    def test_the_anchor_walks_the_record_then_the_tag_then_the_setup_commit(
            self, tmp_path):
        with_record = _new_repo(str(tmp_path / 'with_record'))
        _write(os.path.join(with_record, '.purlin', 'records', 'thing',
                            '20260913T120000Z-abc1234-ci.json'), '{}')
        _commit(with_record, 'purlin: record for abc1234')
        record_sha = _git(['rev-parse', 'HEAD'], with_record).stdout.strip()
        ref, description = purlin_drift.resolve_since(with_record)
        assert ref == record_sha, (ref, record_sha)
        assert description.startswith('last record'), description

        with_tag = _new_repo(str(tmp_path / 'with_tag'))
        _git(['tag', 'v1.0.0'], with_tag)
        _write(os.path.join(with_tag, 'a.txt'), 'a\n')
        _commit(with_tag, 'chore: after the tag')
        ref, description = purlin_drift.resolve_since(with_tag)
        assert ref == 'v1.0.0', (ref, description)
        assert description.startswith('v1.0.0 ('), description

        fresh = _new_repo(str(tmp_path / 'fresh'))
        init_sha = _git(['rev-parse', 'HEAD'], fresh).stdout.strip()
        for index in range(2):
            _write(os.path.join(fresh, 'f%d.txt' % index), str(index))
            _commit(fresh, 'chore: commit %d' % index)
        ref, description = purlin_drift.resolve_since(fresh)
        assert ref == init_sha, (ref, init_sha)
        assert description == 'since purlin:init (2 commits)', description

        for index in range(2, 32):
            _write(os.path.join(fresh, 'f%d.txt' % index), str(index))
            _commit(fresh, 'chore: commit %d' % index)
        ref, payload = purlin_drift.resolve_since(fresh)
        assert ref is None, ref
        assert json.loads(payload)['recommendation'] == 'spec-from-code', payload


class TestDriftClassification:
    """drift RULE-3, RULE-4 and RULE-5: what category a changed file lands in."""

    def _repo(self, root):
        _new_repo(root)
        _write(os.path.join(root, 'specs', 'mcp', 'thing.md'),
               '# Feature: thing\n\n> Scope: src/thing.py\n\n'
               '## Rules\n\n- RULE-1: Does the thing\n\n'
               '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n')
        for path, text in (('src/thing.py', 'def thing():\n    return 1\n'),
                           ('src/other.py', 'def other():\n    return 2\n'),
                           ('tests/test_thing.py', 'def test_thing():\n    pass\n'),
                           ('designs/thing/mock.svg', '<svg></svg>\n'),
                           ('README.md', '# thing\n')):
            _write(os.path.join(root, *path.split('/')), text)
        _commit(root, 'chore: the project under test')
        return root

    @pytest.mark.proof("drift", "PROOF-4", "RULE-3", tier="integration")
    def test_every_changed_file_lands_in_one_category(self, tmp_path):
        root = self._repo(str(tmp_path / 'proj'))
        _write(os.path.join(root, 'specs', 'mcp', 'thing.md'),
               '# Feature: thing\n\n> Scope: src/thing.py\n\n'
               '## Rules\n\n- RULE-1: Does the thing\n'
               '- RULE-2: Does it twice\n\n'
               '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n'
               '- PROOF-2 (RULE-2): Call it twice and verify 2\n')
        for path, text in (('src/thing.py', 'def thing():\n    return 2\n'),
                           ('src/other.py', 'def other():\n    return 3\n'),
                           ('tests/test_thing.py',
                            'def test_thing():\n    assert 1\n'),
                           ('designs/thing/mock.svg', '<svg><rect/></svg>\n'),
                           ('README.md', '# thing, revised\n')):
            _write(os.path.join(root, *path.split('/')), text)
        _commit(root, 'feat: move everything')

        data = json.loads(purlin_drift.drift(root, since='1'))
        found = {entry['path']: entry['category'] for entry in data['files']}
        assert found == {
            'specs/mcp/thing.md': 'CHANGED_SPECS',
            'tests/test_thing.py': 'TESTS_CHANGED',
            'src/thing.py': 'CHANGED_BEHAVIOR',
            'designs/thing/mock.svg': 'CHANGED_DESIGNS',
            'README.md': 'NO_IMPACT',
            'src/other.py': 'NEW_BEHAVIOR',
        }, found

    @pytest.mark.proof("drift", "PROOF-5", "RULE-4", tier="integration")
    def test_a_behaviour_directory_is_never_no_impact(self, tmp_path):
        root = self._repo(str(tmp_path / 'proj'))
        for path in ('skills/build/SKILL.md', 'agents/reviewer.md',
                     '.claude/agents/helper.md'):
            _write(os.path.join(root, *path.split('/')), '# behaviour\n')
        _commit(root, 'feat: three behaviour files')

        data = json.loads(purlin_drift.drift(root, since='1'))
        found = {entry['path']: entry['category'] for entry in data['files']}
        assert found == {
            'skills/build/SKILL.md': 'NEW_BEHAVIOR',
            'agents/reviewer.md': 'NEW_BEHAVIOR',
            '.claude/agents/helper.md': 'NEW_BEHAVIOR',
        }, found

    @pytest.mark.proof("drift", "PROOF-6", "RULE-5", tier="integration")
    def test_a_directory_scope_matches_the_files_under_it(self, tmp_path):
        root = _new_repo(str(tmp_path / 'proj'))
        _write(os.path.join(root, 'specs', 'api', 'api.md'),
               '# Feature: api\n\n> Scope: src/api/\n\n'
               '## Rules\n\n- RULE-1: Every response carries a type\n\n'
               '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1 header\n')
        _write(os.path.join(root, 'src', 'api', 'login.js'),
               'function login() { return 200; }\n')
        _commit(root, 'chore: the api')
        _write(os.path.join(root, 'src', 'api', 'login.js'),
               'function login() { return 401; }\n')
        _commit(root, 'fix: login')

        data = json.loads(purlin_drift.drift(root, since='1'))
        entry = next(e for e in data['files'] if e['path'] == 'src/api/login.js')
        assert entry['category'] == 'CHANGED_BEHAVIOR', entry
        assert entry['spec'] == 'api', entry


class TestDriftReportShape:
    """drift RULE-7 and RULE-8: what the report carries, and what is gone."""

    @pytest.mark.proof("drift", "PROOF-8", "RULE-7", tier="integration")
    @pytest.mark.proof("drift", "PROOF-9", "RULE-8", tier="integration")
    def test_the_report_names_its_keys_and_the_scope_paths_that_are_gone(
            self, tmp_path):
        root = _new_repo(str(tmp_path / 'proj'))
        _write(os.path.join(root, 'specs', 'mcp', 'thing.md'),
               '# Feature: thing\n\n> Scope: src/thing.py, src/gone.py\n\n'
               '## Rules\n\n- RULE-1: Does the thing\n\n'
               '## Proof\n\n- PROOF-1 (RULE-1): Call it and verify 1\n')
        _write(os.path.join(root, 'src', 'thing.py'),
               'def thing():\n    return 1\n')
        _commit(root, 'chore: the project under test')
        _write(os.path.join(root, 'src', 'thing.py'),
               'def thing():\n    return 2\n')
        _commit(root, 'fix: thing')

        data = json.loads(purlin_drift.drift(root, since='1'))
        assert sorted(data) == sorted([
            'since', 'commits', 'files', 'spec_changes', 'broken_scopes',
            'pins', 'rule_details', 'states', 'review_list',
            'roles']), sorted(data)
        assert data['broken_scopes'] == [
            {'spec': 'thing', 'missing_paths': ['src/gone.py']}], \
            data['broken_scopes']


class TestDriftPinStatus:
    """drift RULE-10: unpinned, unreadable, and a pin that is still current."""

    @pytest.mark.proof("drift", "PROOF-20", "RULE-10", tier="integration")
    def test_a_pin_is_unpinned_an_error_or_not_reported_at_all(self, tmp_path):
        root = _new_repo(str(tmp_path / 'proj'))

        unpinned = purlin_drift.check_pin(
            root, 'https://github.com/acme/p.git', None)
        assert unpinned == {'status': 'unpinned', 'remote_sha': None}, unpinned

        unreadable = purlin_drift.check_pin(
            root, os.path.join(str(tmp_path), 'nope.git'), 'abc1234')
        assert unreadable['status'] == 'error', unreadable
        assert unreadable['error'], unreadable

        bare = os.path.join(str(tmp_path), 'anchor.git')
        sha = _create_bare_repo(bare, 'policy.md', '# policy v1')
        current = purlin_drift.check_pin(root, bare, sha)
        assert current == {'status': 'current', 'remote_sha': sha}, current

        features = {'policy': {'is_anchor': True, 'source': bare,
                               'pinned': sha}}
        assert purlin_drift.pin_report(root, features) == [], (
            'an anchor still at its pin must not be reported')
        shutil.rmtree(bare + '_work', ignore_errors=True)
