"""Tests for drift RULE-12, RULE-13, and RULE-14 — external anchor staleness."""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server


def _git(args, cwd, check=True):
    """Run a git command in the given directory, capturing output."""
    return subprocess.run(
        ['git'] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


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
    shutil.rmtree(work_dir)
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
    shutil.rmtree(work_dir)
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

    _git(['init', '-q'], project_root)
    _git(['config', 'user.email', 'test@test.com'], project_root)
    _git(['config', 'user.name', 'Test'], project_root)
    _git(['add', '-A'], project_root)
    _git(['commit', '-m', 'verify: initial project'], project_root)


class TestDriftExternalAndLocalModification:
    """drift RULE-13 and RULE-14: external anchor staleness with local modification."""

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

    @pytest.mark.proof("drift", "PROOF-14", "RULE-13", tier="e2e")
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
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)

        # Verify external_anchor_drift has a stale entry for security_policy
        stale_entries = [
            e for e in data.get('external_anchor_drift', [])
            if e.get('anchor') == 'security_policy' and e.get('status') == 'stale'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 external_anchor_drift stale entry for security_policy, "
            f"got: {data.get('external_anchor_drift', [])}"
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

    @pytest.mark.proof("drift", "PROOF-16", "RULE-14", tier="e2e")
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
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('external_anchor_drift', [])
            if e.get('status') == 'stale'
        ]
        assert len(stale_entries) >= 1, (
            f"Expected at least 1 stale external_anchor_drift entry, "
            f"got: {data.get('external_anchor_drift', [])}"
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
    """drift RULE-12: mixed anchor staleness — external source advances, drift detects it."""

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

    @pytest.mark.proof("drift", "PROOF-12", "RULE-12", tier="e2e")
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
        _git(['init', '-q'], self.project_root)
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
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('external_anchor_drift', [])
            if e.get('anchor') == 'mixed_policy' and e.get('status') == 'stale'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 stale external_anchor_drift entry for mixed_policy, "
            f"got: {data.get('external_anchor_drift', [])}"
        )

    @pytest.mark.proof("drift", "PROOF-17", "RULE-12", tier="e2e")
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
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)

        stale_entries = [
            e for e in data.get('external_anchor_drift', [])
            if e.get('anchor') == 'external_anchor' and e.get('status') == 'stale'
        ]
        assert len(stale_entries) == 1, (
            f"Expected 1 stale external_anchor_drift entry for external_anchor, "
            f"got: {data.get('external_anchor_drift', [])}"
        )
        entry = stale_entries[0]
        assert 'remote_sha' in entry, (
            f"Expected remote_sha field in stale entry, got: {entry}"
        )
        # remote_sha is truncated to 7 chars in purlin_server.py
        assert len(entry['remote_sha']) == 7, (
            f"Expected remote_sha to be 7 chars (truncated), got: {entry['remote_sha']!r}"
        )
        # Verify the remote_sha matches the beginning of the actual new commit SHA
        assert new_sha.startswith(entry['remote_sha']), (
            f"Expected remote_sha {entry['remote_sha']!r} to be prefix of actual new SHA "
            f"{new_sha!r}"
        )
