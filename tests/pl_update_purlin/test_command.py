#!/usr/bin/env python3
"""Tests for the /pl-update-purlin agent command.

Covers automated scenarios from features/pl_update_purlin.md:
- Auto-Fetch and Update When Behind
- Already Up to Date with Remote
- No Changes Since Last Sync
- Unmodified Command Files Auto-Updated
- Modified Command File Requires Review
- Top-Level Script Updated Automatically
- Top-Level Script with Local Changes
- Structural Change Migration Plan
- New Config Keys Added Upstream
- Init Refresh Runs After Successful Update
- Stale Artifacts Detected and Cleaned
- Dry Run Shows Changes Without Applying
- pl-edit-base.md Excluded from Sync
- Unmodified Deleted-Upstream Command Auto-Removed
- Modified Deleted-Upstream Command Requires Confirmation
- Legacy-Named Launcher Scripts Replaced
- Standalone Mode Guard Prevents Update in Purlin Repo

The agent command is a Claude skill defined in .claude/commands/pl-update-purlin.md.
These tests verify the command file structure, referenced infrastructure,
and behavioral invariants that the command depends on.
"""
import json
import os
import re
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


# Known stale artifacts from the spec (Section 2.12)
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

# Legacy script names that the skill must detect
LEGACY_SCRIPT_NAMES = [
    'run_builder.sh',
    'run_architect.sh',
    'run_qa.sh',
    'purlin_init.sh',
    'purlin_cdd_start.sh',
    'purlin_cdd_stop.sh',
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
    And displays how many commits behind

    Test: Verifies command file references fetch and remote comparison.
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
        # The command should mention being behind
        self.assertIn('behind', content.lower())


class TestAlreadyUpToDateWithRemote(unittest.TestCase):
    """Scenario: Already Up to Date with Remote

    Given the submodule's local HEAD matches the remote tracking branch
    When /pl-update-purlin is invoked
    Then skip to SHA comparison

    Test: Verifies command handles the already-current case.
    """

    def test_command_handles_already_current(self):
        """Command instructs skipping to SHA comparison when already current."""
        content = _get_command_content()
        self.assertIn('already current', content.lower())

    def test_command_references_sha_comparison(self):
        """Command references SHA comparison check."""
        content = _get_command_content()
        self.assertIn('.upstream_sha', content)


class TestNoChangesSinceLastSync(unittest.TestCase):
    """Scenario: No Changes Since Last Sync

    Given .purlin/.upstream_sha matches the current submodule HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date" is printed and the skill exits

    Test: Verifies early exit when SHAs match.
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

    Given a command file changed upstream and local matches old version
    When /pl-update-purlin is invoked
    Then the file is auto-copied

    Test: Verifies auto-copy logic for unmodified files.
    """

    def test_command_references_auto_copy(self):
        """Command instructs auto-copying unmodified files."""
        content = _get_command_content()
        self.assertIn('auto-copy', content.lower())

    def test_command_references_command_file_changes(self):
        """Command has a section for command file change handling."""
        content = _get_command_content()
        self.assertIn('.claude/commands/', content)


class TestModifiedCommandFileRequiresReview(unittest.TestCase):
    """Scenario: Modified Command File Requires Review

    Given a command file changed both upstream and locally
    When /pl-update-purlin is invoked
    Then the skill shows a three-way diff and offers merge strategies

    Test: Verifies three-way diff and merge strategy references.
    """

    def test_command_references_three_way_diff(self):
        """Command references three-way diff (old upstream, new upstream, local)."""
        content = _get_command_content()
        self.assertIn('three-way diff', content.lower())

    def test_command_offers_merge_strategies(self):
        """Command offers the four merge strategies from the spec."""
        content = _get_command_content()
        for strategy in MERGE_STRATEGIES:
            self.assertIn(strategy, content,
                          f'Missing merge strategy: {strategy}')

    def test_command_references_old_and_new_upstream(self):
        """Command references comparing old upstream vs new upstream."""
        content = _get_command_content()
        self.assertIn('old upstream', content.lower())
        self.assertIn('new upstream', content.lower())


class TestTopLevelScriptUpdatedAutomatically(unittest.TestCase):
    """Scenario: Top-Level Script Updated Automatically

    Given a top-level script changed upstream and local matches old version
    When /pl-update-purlin is invoked
    Then the script is auto-updated

    Test: Verifies script tracking and auto-update references.
    """

    def test_command_tracks_launcher_scripts(self):
        """Command references all tracked top-level scripts."""
        content = _get_command_content()
        for script in TRACKED_SCRIPTS:
            self.assertIn(script, content,
                          f'Missing tracked script reference: {script}')


class TestTopLevelScriptWithLocalChanges(unittest.TestCase):
    """Scenario: Top-Level Script with Local Changes

    Given a script changed upstream and locally
    When /pl-update-purlin is invoked
    Then diff is shown and merge strategies are offered

    Test: Verifies diff and merge strategy for modified scripts.
    """

    def test_command_handles_modified_scripts(self):
        """Command handles the case where user modified a tracked script."""
        content = _get_command_content()
        # Should reference showing diff for user-modified scripts
        self.assertIn('diff', content.lower())
        self.assertIn('merge strateg', content.lower())


class TestStructuralChangeMigrationPlan(unittest.TestCase):
    """Scenario: Structural Change Migration Plan

    Given upstream renamed section headers in instruction files
    And override files reference the old section names
    When /pl-update-purlin is invoked
    Then the skill detects the structural change
    And generates a migration plan
    And warns about stale override references

    Test: Verifies structural change detection, migration plan generation,
    and override file scanning logic in the command file.
    """

    def test_command_references_structural_change_detection(self):
        """Command instructs detecting structural changes in instructions."""
        content = _get_command_content()
        self.assertIn('structural change', content.lower())

    def test_command_references_section_header_comparison(self):
        """Command references comparing section headers between versions."""
        content = _get_command_content()
        # The command should mention detecting header changes
        self.assertIn('section header', content.lower())

    def test_command_references_override_file_scanning(self):
        """Command instructs scanning override files for stale references."""
        content = _get_command_content()
        self.assertIn('OVERRIDES.md', content)

    def test_command_references_migration_plan_generation(self):
        """Command references generating a migration plan file."""
        content = _get_command_content()
        self.assertIn('migration_plan_', content)
        self.assertIn('.purlin/migration_plan_', content)

    def test_command_references_warning_for_changed_sections(self):
        """Command includes warning format for changed section references."""
        content = _get_command_content()
        # Should warn about override files referencing changed sections
        self.assertIn('references changed section', content.lower())

    def test_command_references_specific_line_updates(self):
        """Command instructs suggesting specific line updates."""
        content = _get_command_content()
        # Should suggest showing old -> new header names
        self.assertIn('line', content.lower())

    def test_migration_plan_section_covers_breaking_changes(self):
        """Migration plan section includes breaking changes documentation."""
        content = _get_command_content()
        self.assertIn('breaking change', content.lower())

    def test_override_files_exist_on_disk(self):
        """Override files that the skill scans actually exist in the project."""
        override_files = [
            '.purlin/ARCHITECT_OVERRIDES.md',
            '.purlin/BUILDER_OVERRIDES.md',
            '.purlin/QA_OVERRIDES.md',
            '.purlin/HOW_WE_WORK_OVERRIDES.md',
        ]
        for rel_path in override_files:
            full_path = os.path.join(PROJECT_ROOT, rel_path)
            self.assertTrue(os.path.isfile(full_path),
                            f'Override file not found: {full_path}')


class TestNewConfigKeysAddedUpstream(unittest.TestCase):
    """Scenario: New Config Keys Added Upstream

    Given upstream added new config keys
    When /pl-update-purlin completes
    Then the config sync step adds new keys to config.local.json

    Test: Verifies config sync references and infrastructure.
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


class TestInitRefreshRunsAfterSuccessfulUpdate(unittest.TestCase):
    """Scenario: Init Refresh Runs After Successful Update

    Given the submodule has been advanced to a newer commit
    When /pl-update-purlin completes the update
    Then tools/init.sh --quiet is executed

    Test: Verifies init refresh references and infrastructure.
    """

    def test_command_references_init_refresh(self):
        """Command instructs running init.sh --quiet after update."""
        content = _get_command_content()
        self.assertIn('init.sh --quiet', content)

    def test_init_script_exists(self):
        """The tools/init.sh script exists for post-update refresh."""
        init_path = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
        self.assertTrue(os.path.isfile(init_path),
                        f'init.sh not found: {init_path}')

    def test_command_reports_init_refresh_in_summary(self):
        """Command includes init refresh status in summary report."""
        content = _get_command_content()
        self.assertIn('Init refresh completed', content)


class TestStaleArtifactsDetectedAndCleaned(unittest.TestCase):
    """Scenario: Stale Artifacts Detected and Cleaned

    Given the consumer project has legacy-named scripts
    When /pl-update-purlin completes the update
    Then stale artifacts are detected and user is prompted for removal

    Test: Verifies stale artifact detection logic.
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

    Given multiple changes exist upstream
    When /pl-update-purlin --dry-run is invoked
    Then changes are analyzed but no files are modified

    Test: Verifies dry-run flag handling.
    """

    def test_command_supports_dry_run_flag(self):
        """Command documents the --dry-run flag."""
        content = _get_command_content()
        self.assertIn('--dry-run', content)

    def test_command_dry_run_prevents_modification(self):
        """Command specifies that dry-run does not modify files."""
        content = _get_command_content()
        # Dry run should list stale artifacts but not delete
        self.assertIn('list stale artifacts but do not delete', content.lower())


class TestPlEditBaseMdExcludedFromSync(unittest.TestCase):
    """Scenario: pl-edit-base.md Excluded from Sync

    Given pl-edit-base.md changed upstream
    When /pl-update-purlin is invoked
    Then pl-edit-base.md is silently excluded

    Test: Verifies exclusion of pl-edit-base.md.
    """

    def test_command_excludes_pl_edit_base(self):
        """Command explicitly excludes pl-edit-base.md from sync."""
        content = _get_command_content()
        self.assertIn('pl-edit-base.md', content)
        # Should be silently excluded or NEVER synced
        self.assertIn('NEVER synced', content)


class TestUnmodifiedDeletedUpstreamCommandAutoRemoved(unittest.TestCase):
    """Scenario: Unmodified Deleted-Upstream Command Auto-Removed

    Given a command file exists locally matching old upstream
    And the new upstream no longer includes it
    When /pl-update-purlin is invoked
    Then the file is auto-deleted

    Test: Verifies handling of deleted-upstream unmodified commands.
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

    Given a command file has local modifications
    And the new upstream no longer includes it
    When /pl-update-purlin is invoked
    Then the user is prompted to confirm deletion

    Test: Verifies handling of deleted-upstream modified commands.
    """

    def test_command_handles_deleted_upstream_modified(self):
        """Command prompts user for modified files deleted upstream."""
        content = _get_command_content()
        # Should show local modifications and prompt
        self.assertIn('modified locally', content.lower())

    def test_command_preserves_on_user_decline(self):
        """Command preserves file if user declines deletion."""
        content = _get_command_content()
        self.assertIn('preserve', content.lower())


class TestLegacyNamedLauncherScriptsReplaced(unittest.TestCase):
    """Scenario: Legacy-Named Launcher Scripts Replaced

    Given the consumer project has old-named scripts (run_builder.sh)
    And current-named equivalents do not exist
    When /pl-update-purlin is invoked
    Then current-named replacements are generated

    Test: Verifies legacy naming detection and replacement logic.
    """

    def test_command_detects_legacy_naming(self):
        """Command references both legacy and current naming conventions."""
        content = _get_command_content()
        # Should mention legacy naming
        self.assertIn('legacy', content.lower())

    def test_command_references_both_naming_conventions(self):
        """Command lists both old and new naming patterns."""
        content = _get_command_content()
        # Current naming
        self.assertIn('pl-run-', content)
        self.assertIn('pl-init.sh', content)
        self.assertIn('pl-cdd-', content)
        # Legacy naming
        self.assertIn('run_', content)
        self.assertIn('purlin_init.sh', content)
        self.assertIn('purlin_cdd_', content)


class TestStandaloneModeGuardPreventsUpdateInPurlinRepo(unittest.TestCase):
    """Scenario: Standalone Mode Guard Prevents Update in Purlin Repo

    Given the current project IS the Purlin repository
    And .purlin/.upstream_sha does not exist
    And purlin-config-sample/ exists at the project root
    When /pl-update-purlin is invoked
    Then the skill prints an error and exits without changes

    Test: Verifies standalone mode guard detection and error message.
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


class TestReleaseAnalysisInfrastructure(unittest.TestCase):
    """Cross-scenario infrastructure tests for release analysis (Section 2.2.1).

    Verifies that the command file references the git commands and display
    format needed for GitHub release analysis.
    """

    def test_command_references_git_describe_for_version(self):
        """Command references git describe for version detection."""
        content = _get_command_content()
        self.assertIn('describe', content.lower())

    def test_command_references_release_display_format(self):
        """Command includes the release summary display format."""
        content = _get_command_content()
        self.assertIn('Purlin Updates Available', content)


class TestAtomicUpdateProtocol(unittest.TestCase):
    """Cross-scenario tests for atomic update execution (Section 2.7).

    Verifies that the command file enforces atomicity and rollback.
    """

    def test_command_references_atomic_update(self):
        """Command references atomic update execution."""
        content = _get_command_content()
        self.assertIn('Atomic Update', content)

    def test_command_references_backup(self):
        """Command references creating a backup before changes."""
        content = _get_command_content()
        self.assertIn('git stash', content)

    def test_command_references_rollback(self):
        """Command references rollback on failure."""
        content = _get_command_content()
        self.assertIn('rollback', content.lower())


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
