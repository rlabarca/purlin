#!/usr/bin/env python3
"""Tests for the /pl-update-purlin agent command.

Covers automated scenarios from features/pl_update_purlin.md:
- Auto-Fetch and Update When Behind
- Already Up to Date
- No Changes Since Last Sync
- Unmodified Command Files Auto-Updated
- Modified Command File with No Upstream Change
- Modified Command File with Upstream Conflict
- Init Refresh Handles CDD Symlinks
- Top-Level Script Updated Automatically
- Top-Level Script with Local Changes
- New Config Keys Added Upstream
- Stale Artifacts Detected and Cleaned
- Dry Run Shows Changes Without Applying
- pl-edit-base.md Excluded from Sync
- Unmodified Deleted-Upstream Command Auto-Removed
- Modified Deleted-Upstream Command Requires Confirmation
- Standalone Mode Guard Prevents Update in Purlin Repo
- Fast Path Completes Without Conflict Analysis

The agent command is a Claude skill defined in .claude/commands/pl-update-purlin.md.
These tests verify the command file structure, referenced infrastructure,
and behavioral invariants that the command depends on.
"""
import json
import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-update-purlin.md')

# Read command file content once for all tests
_command_content = None


def _get_command_content():
    global _command_content
    if _command_content is None:
        with open(COMMAND_FILE) as f:
            _command_content = f.read()
    return _command_content


# Known stale artifacts from the spec (Section 2.9)
KNOWN_STALE_ARTIFACTS = {
    'run_architect.sh': 'pl-run-architect.sh',
    'run_builder.sh': 'pl-run-builder.sh',
    'run_qa.sh': 'pl-run-qa.sh',
    'purlin_init.sh': 'pl-init.sh',
    'purlin_cdd_start.sh': 'pl-cdd-start.sh',
    'purlin_cdd_stop.sh': 'pl-cdd-stop.sh',
}

# Top-level scripts tracked by the update skill
TRACKED_SCRIPTS = [
    'pl-run-builder.sh',
    'pl-run-architect.sh',
    'pl-run-qa.sh',
]

# Merge strategies offered by the skill
MERGE_STRATEGIES = [
    'Accept upstream',
    'Keep current',
    'Smart merge',
]


class TestCommandFileExists(unittest.TestCase):
    """Verify the command file exists and has expected structure."""

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-update-purlin.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')

    def test_command_file_references_feature_spec(self):
        """Command file references the feature spec for implementation details."""
        content = _get_command_content()
        self.assertIn('features/pl_update_purlin.md', content)

    def test_command_file_has_behavior_section(self):
        """Command file contains a Behavior section with numbered steps."""
        content = _get_command_content()
        self.assertIn('**Behavior:**', content)


class TestAutoFetchAndUpdateWhenBehind(unittest.TestCase):
    """Scenario: Auto-Fetch and Update When Behind

    Given the submodule's local HEAD is behind the remote tracking branch
    When /pl-update-purlin is invoked
    Then the skill fetches from the submodule's remote
    And displays current version, target version, and commit count
    And prompts for confirmation
    """

    def test_command_references_git_fetch(self):
        """Command instructs fetching from submodule remote."""
        content = _get_command_content()
        self.assertIn('fetch', content)

    def test_command_references_remote_comparison(self):
        """Command instructs comparing local HEAD against remote."""
        content = _get_command_content()
        self.assertIn('remote tracking branch', content)

    def test_command_references_commits_behind(self):
        """Command references detecting how many commits behind."""
        content = _get_command_content()
        self.assertIn('behind', content.lower())

    def test_command_references_version_display(self):
        """Command references git describe for version detection."""
        content = _get_command_content()
        self.assertIn('describe', content.lower())


class TestAlreadyUpToDate(unittest.TestCase):
    """Scenario: Already Up to Date

    Given the submodule's local HEAD matches the remote tracking branch
    And .purlin/.upstream_sha matches current HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date." is printed
    And the skill exits successfully
    """

    def test_command_handles_already_current(self):
        """Command handles the already-current-with-remote case."""
        content = _get_command_content()
        self.assertIn('already current', content.lower())

    def test_command_references_sha_comparison(self):
        """Command references .upstream_sha comparison check."""
        content = _get_command_content()
        self.assertIn('.upstream_sha', content)

    def test_command_prints_already_up_to_date(self):
        """Command includes the 'Already up to date' exit message."""
        content = _get_command_content()
        self.assertIn('Already up to date', content)


class TestNoChangesSinceLastSync(unittest.TestCase):
    """Scenario: No Changes Since Last Sync

    Given .purlin/.upstream_sha matches the current submodule HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date." is printed
    And the skill exits successfully
    """

    def test_command_references_already_up_to_date_message(self):
        """Command includes the 'Already up to date' exit message."""
        content = _get_command_content()
        self.assertIn('Already up to date', content)

    def test_upstream_sha_file_path_convention(self):
        """The .purlin/.upstream_sha path is referenced correctly."""
        content = _get_command_content()
        self.assertIn('.purlin/.upstream_sha', content)


class TestUnmodifiedCommandFilesAutoUpdated(unittest.TestCase):
    """Scenario: Unmodified Command Files Auto-Updated

    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md matches the old upstream version
    When /pl-update-purlin is invoked and update completes
    Then init.sh auto-copies pl-status.md from submodule
    """

    def test_command_references_auto_copy(self):
        """Command instructs auto-copying unmodified files."""
        content = _get_command_content()
        self.assertIn('auto-copied', content.lower())

    def test_command_references_command_file_changes(self):
        """Command has a section for command file change handling."""
        content = _get_command_content()
        self.assertIn('.claude/commands/', content)


class TestModifiedCommandFileWithNoUpstreamChange(unittest.TestCase):
    """Scenario: Modified Command File with No Upstream Change

    Given the consumer modified .claude/commands/pl-status.md locally
    And upstream did NOT change pl-status.md between old and new SHA
    When /pl-update-purlin is invoked and update completes
    Then pl-status.md is preserved with local modifications
    And no merge prompt is shown
    """

    def test_command_handles_no_upstream_change(self):
        """Command states no action needed when upstream didn't change a locally modified file."""
        content = _get_command_content()
        self.assertIn('upstream did NOT change', content)

    def test_command_references_old_sha_comparison(self):
        """Command references comparing against old upstream version."""
        content = _get_command_content()
        self.assertIn('old upstream', content.lower())


class TestModifiedCommandFileWithUpstreamConflict(unittest.TestCase):
    """Scenario: Modified Command File with Upstream Conflict

    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md has local modifications
    When /pl-update-purlin is invoked and update completes
    Then the skill shows a three-way diff
    And offers merge strategies
    """

    def test_command_references_three_way_diff(self):
        """Command references three-way diff (old upstream, new upstream, local)."""
        content = _get_command_content()
        self.assertIn('three-way diff', content.lower())

    def test_command_offers_merge_strategies(self):
        """Command offers the three merge strategies from the spec."""
        content = _get_command_content()
        for strategy in MERGE_STRATEGIES:
            self.assertIn(strategy, content,
                          f'Missing merge strategy: {strategy}')

    def test_command_references_old_and_new_upstream(self):
        """Command references comparing old upstream vs new upstream."""
        content = _get_command_content()
        self.assertIn('old upstream', content.lower())
        self.assertIn('new upstream', content.lower())


class TestInitRefreshHandlesCDDSymlinks(unittest.TestCase):
    """Scenario: Init Refresh Handles CDD Symlinks

    Given the submodule has been advanced to a newer commit
    When init.sh --quiet runs as part of the update
    Then pl-cdd-start.sh and pl-cdd-stop.sh are verified as correct symlinks
    And the skill does NOT directly read, compare, or modify these files
    """

    def test_command_excludes_cdd_symlinks(self):
        """Command explicitly warns not to touch CDD symlinks."""
        content = _get_command_content()
        # The command has a bold IMPORTANT note about CDD symlinks
        self.assertIn('SYMLINKS', content)
        self.assertIn('NEVER read, compare, copy, or modify', content)

    def test_command_references_init_refresh(self):
        """Command instructs running init.sh --quiet which handles symlinks."""
        content = _get_command_content()
        self.assertIn('init.sh --quiet', content)

    def test_init_script_exists(self):
        """The tools/init.sh script exists for post-update refresh."""
        init_path = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
        self.assertTrue(os.path.isfile(init_path),
                        f'init.sh not found: {init_path}')

    def test_command_references_cdd_symlink_names(self):
        """Command references the specific CDD symlink filenames."""
        content = _get_command_content()
        self.assertIn('pl-cdd-start.sh', content)
        self.assertIn('pl-cdd-stop.sh', content)


class TestTopLevelScriptUpdatedAutomatically(unittest.TestCase):
    """Scenario: Top-Level Script Updated Automatically

    Given pl-run-builder.sh changed upstream
    And the consumer's pl-run-builder.sh matches the old version
    When /pl-update-purlin is invoked
    Then init.sh regenerates pl-run-builder.sh
    """

    def test_command_tracks_launcher_scripts(self):
        """Command references all tracked top-level scripts."""
        content = _get_command_content()
        for script in TRACKED_SCRIPTS:
            self.assertIn(script, content,
                          f'Missing tracked script reference: {script}')


class TestTopLevelScriptWithLocalChanges(unittest.TestCase):
    """Scenario: Top-Level Script with Local Changes

    Given pl-run-builder.sh changed upstream
    And the consumer has modified pl-run-builder.sh locally
    When /pl-update-purlin is invoked
    Then the skill shows the diff and offers merge strategies
    """

    def test_command_handles_modified_scripts(self):
        """Command handles the case where user modified a tracked script."""
        content = _get_command_content()
        self.assertIn('diff', content.lower())
        self.assertIn('same three-way approach', content.lower())


class TestNewConfigKeysAddedUpstream(unittest.TestCase):
    """Scenario: New Config Keys Added Upstream

    Given upstream added new config keys
    When /pl-update-purlin completes
    Then the config sync step adds new keys to config.local.json
    """

    def test_command_references_config_sync(self):
        """Command instructs running config sync after update."""
        content = _get_command_content()
        self.assertIn('sync_config', content)

    def test_command_references_config_local_json(self):
        """Command references config.local.json for local overrides."""
        content = _get_command_content()
        self.assertIn('config.local.json', content)

    def test_resolve_config_module_exists(self):
        """The resolve_config.py module exists for config sync."""
        module_path = os.path.join(
            PROJECT_ROOT, 'tools', 'config', 'resolve_config.py')
        self.assertTrue(os.path.isfile(module_path),
                        f'resolve_config.py not found: {module_path}')


class TestStaleArtifactsDetectedAndCleaned(unittest.TestCase):
    """Scenario: Stale Artifacts Detected and Cleaned

    Given the consumer project has legacy-named scripts
    When /pl-update-purlin completes the update
    Then stale artifacts are detected and user is prompted for removal
    """

    def test_command_lists_known_stale_artifacts(self):
        """Command references known stale artifact names."""
        content = _get_command_content()
        for legacy, current in KNOWN_STALE_ARTIFACTS.items():
            self.assertIn(legacy, content,
                          f'Missing stale artifact reference: {legacy}')

    def test_command_prompts_before_deletion(self):
        """Command instructs prompting before deleting stale files."""
        content = _get_command_content()
        self.assertIn('Remove these files', content)

    def test_command_handles_declined_cleanup(self):
        """Command handles when user declines cleanup."""
        content = _get_command_content()
        self.assertIn('remove them manually later', content.lower())


class TestDryRunShowsChangesWithoutApplying(unittest.TestCase):
    """Scenario: Dry Run Shows Changes Without Applying

    Given the submodule is behind the remote
    When /pl-update-purlin --dry-run is invoked
    Then changes are analyzed but no files are modified
    """

    def test_command_supports_dry_run_flag(self):
        """Command documents the --dry-run flag."""
        content = _get_command_content()
        self.assertIn('--dry-run', content)

    def test_command_dry_run_prevents_modification(self):
        """Command specifies that dry-run does not modify files."""
        content = _get_command_content()
        self.assertIn('list stale artifacts but do not delete', content.lower())


class TestPlEditBaseMdExcludedFromSync(unittest.TestCase):
    """Scenario: pl-edit-base.md Excluded from Sync

    Given pl-edit-base.md changed upstream
    When /pl-update-purlin is invoked
    Then pl-edit-base.md is silently excluded
    """

    def test_command_excludes_pl_edit_base(self):
        """Command explicitly excludes pl-edit-base.md from sync."""
        content = _get_command_content()
        self.assertIn('pl-edit-base.md', content)
        self.assertIn('NEVER synced', content)


class TestUnmodifiedDeletedUpstreamCommandAutoRemoved(unittest.TestCase):
    """Scenario: Unmodified Deleted-Upstream Command Auto-Removed

    Given pl-old-command.md exists in .claude/commands/ and matches old upstream
    And the new upstream no longer includes it
    When /pl-update-purlin is invoked
    Then the file is auto-deleted
    """

    def test_command_handles_deleted_upstream_unmodified(self):
        """Command instructs auto-deleting unmodified files deleted upstream."""
        content = _get_command_content()
        self.assertIn('auto-delete', content.lower())

    def test_command_reports_removed_files(self):
        """Command includes removal reporting format."""
        content = _get_command_content()
        self.assertIn('no longer in upstream', content.lower())


class TestModifiedDeletedUpstreamCommandRequiresConfirmation(unittest.TestCase):
    """Scenario: Modified Deleted-Upstream Command Requires Confirmation

    Given pl-old-command.md exists with local modifications
    And the new upstream no longer includes it
    When /pl-update-purlin is invoked
    Then the user is prompted to confirm deletion
    """

    def test_command_handles_deleted_upstream_modified(self):
        """Command prompts user for modified files deleted upstream."""
        content = _get_command_content()
        self.assertIn('modified locally', content.lower())

    def test_command_preserves_on_user_decline(self):
        """Command preserves file if user declines deletion."""
        content = _get_command_content()
        self.assertIn('preserve', content.lower())


class TestStandaloneModeGuardPreventsUpdateInPurlinRepo(unittest.TestCase):
    """Scenario: Standalone Mode Guard Prevents Update in Purlin Repo

    Given the current project IS the Purlin repository
    And .purlin/.upstream_sha does not exist
    And purlin-config-sample/ exists at the project root
    When /pl-update-purlin is invoked
    Then the skill prints an error and exits without changes
    """

    def test_command_has_standalone_mode_guard(self):
        """Command includes standalone mode guard as the first step."""
        content = _get_command_content()
        self.assertIn('Standalone Mode Guard', content)

    def test_command_checks_upstream_sha_absence(self):
        """Guard checks that .upstream_sha does not exist."""
        content = _get_command_content()
        self.assertIn('.upstream_sha', content)

    def test_command_checks_purlin_config_sample(self):
        """Guard checks that purlin-config-sample/ exists."""
        content = _get_command_content()
        self.assertIn('purlin-config-sample', content)

    def test_command_prints_consumer_only_message(self):
        """Guard prints the correct error message."""
        content = _get_command_content()
        self.assertIn(
            'only for consumer projects using Purlin as a submodule',
            content)

    def test_purlin_config_sample_exists_in_this_repo(self):
        """purlin-config-sample/ exists in this repo (confirms this IS Purlin repo)."""
        sample_dir = os.path.join(PROJECT_ROOT, 'purlin-config-sample')
        self.assertTrue(os.path.isdir(sample_dir),
                        f'purlin-config-sample/ not found: {sample_dir}')


class TestFastPathCompletesWithoutConflictAnalysis(unittest.TestCase):
    """Scenario: Fast Path Completes Without Conflict Analysis

    Given the submodule is behind by 5 commits
    And no command files or launcher scripts have been locally modified
    When /pl-update-purlin is invoked and the user confirms
    Then the conflict resolution step is skipped entirely
    """

    def test_command_skips_conflict_analysis_when_clean(self):
        """Command instructs skipping conflict resolution when no flags."""
        content = _get_command_content()
        self.assertIn('skip this step entirely if no conflicts', content.lower())

    def test_command_references_init_refresh_in_summary(self):
        """Fast path still runs init refresh and shows summary."""
        content = _get_command_content()
        self.assertIn('Init refresh completed', content)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    failed = len(result.failures) + len(result.errors)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': 'PASS' if result.wasSuccessful() else 'FAIL',
            'passed': result.testsRun - failed,
            'failed': failed,
            'total': result.testsRun,
        }, f)
    sys.exit(0 if result.wasSuccessful() else 1)
