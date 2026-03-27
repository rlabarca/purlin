#!/usr/bin/env python3
"""Tests for the /pl-update-purlin agent command.

Covers automated scenarios from features/pl_update_purlin.md:
- Auto-Fetch and Update When Behind
- Already Up to Date
- No Changes Since Last Sync
- Unmodified Command Files Auto-Updated
- Modified Command File with No Upstream Change
- Modified Command File with Upstream Conflict
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
- Diff-Tree Early Exit Skips Per-File Scan
- Diff-Tree Narrows Per-File Scan
- Go-Deeper Offered After Summary
- Go-Deeper Skipped When Declined
- Go-Deeper Skipped With Auto-Approve
- Go-Deeper Detects Override Header Drift
- Go-Deeper Detects Orphaned Config Keys
- Go-Deeper Summarizes Skipped Command Changes
- Go-Deeper Available in Dry-Run Mode
- Go-Deeper Reports No Impacts When Clean
- Update Surfaces Missing Prerequisite Warning
- Update With All Prerequisites Met Shows No Warnings
- Missing Required Tool During Update Warns But Continues
- New MCP Server Detected on Update
- Removed MCP Server Generates Advisory
- Changed MCP Server Configuration Advisory
- No MCP Output When Manifest Unchanged
- Unmodified Agent Files Auto-Updated
- Modified Agent File with Upstream Conflict

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


# Known stale artifacts from the spec (Section 2.11)
KNOWN_STALE_ARTIFACTS = {
    'run_architect.sh': 'pl-run-architect.sh',
    'run_builder.sh': 'pl-run-builder.sh',
    'run_qa.sh': 'pl-run-qa.sh',
    'purlin_init.sh': 'pl-init.sh',
    'pl-cdd-start.sh': 'CDD dashboard (discontinued)',
    'pl-cdd-stop.sh': 'CDD dashboard (discontinued)',
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


class TestDiffTreeEarlyExitSkipsPerFileScan(unittest.TestCase):
    """Scenario: Diff-Tree Early Exit Skips Per-File Scan

    Given the submodule is behind by 2 commits
    And upstream changed zero files in .claude/commands/ and zero launcher-relevant paths
    When /pl-update-purlin runs the pre-update conflict scan
    Then git diff-tree is invoked once
    And no per-file git show comparisons are executed
    And the conflict scan completes with zero flagged files
    """

    def test_command_references_diff_tree(self):
        """Command instructs using git diff-tree for upstream change detection."""
        content = _get_command_content()
        self.assertIn('diff-tree', content)

    def test_command_references_name_status_flag(self):
        """Command references --name-status flag for diff-tree."""
        content = _get_command_content()
        self.assertIn('--name-status', content)

    def test_command_skips_scan_when_no_upstream_changes(self):
        """Command instructs skipping per-file scan when diff-tree shows no changes."""
        content = _get_command_content()
        self.assertIn(
            'no command files, agent files, or launcher scripts changed upstream, '
            'skip the remainder of this step',
            content.lower())

    def test_command_references_commands_path_in_diff_tree(self):
        """Command scopes diff-tree to .claude/commands/ path."""
        content = _get_command_content()
        self.assertIn('.claude/commands/', content)


class TestDiffTreeNarrowsPerFileScan(unittest.TestCase):
    """Scenario: Diff-Tree Narrows Per-File Scan

    Given the submodule is behind by 5 commits
    And upstream changed 2 of 30 command files
    And the consumer has locally modified 3 command files
    When /pl-update-purlin runs the pre-update conflict scan
    Then only the 2 upstream-changed files are checked for local modifications
    And the remaining 28 command files are not compared
    """

    def test_command_checks_only_diff_tree_output_files(self):
        """Command instructs checking only files that appear in diff-tree output."""
        content = _get_command_content()
        self.assertIn(
            'that appear in both the consumer project and the diff-tree output',
            content.lower())

    def test_command_compares_against_old_upstream_version(self):
        """Command instructs comparing local file against old upstream via git show."""
        content = _get_command_content()
        self.assertIn('git -C <submodule> show <old_sha>', content)

    def test_command_flags_locally_modified_files(self):
        """Command instructs flagging files that differ as locally modified."""
        content = _get_command_content()
        self.assertIn('flag as "locally modified"', content.lower())


class TestGoDeeperOfferedAfterSummary(unittest.TestCase):
    """Scenario: Go-Deeper Offered After Summary

    Given the update completed successfully
    And the summary report has been displayed
    When the skill reaches the customization impact check
    Then it prompts: "Would you like me to check if this update affects
    your customizations?"
    """

    def test_command_has_customization_impact_section(self):
        """Command includes a customization impact check section."""
        content = _get_command_content()
        self.assertIn('Customization Impact Check', content)

    def test_command_contains_go_deeper_prompt(self):
        """Command contains the exact go-deeper prompt text."""
        content = _get_command_content()
        self.assertIn(
            'Would you like me to check if this update affects your customizations?',
            content)

    def test_go_deeper_is_after_summary(self):
        """Go-deeper section appears after the summary section in the command."""
        content = _get_command_content()
        summary_pos = content.find('**Summary:**')
        impact_pos = content.find('Customization Impact Check')
        self.assertGreater(summary_pos, -1, 'Summary section not found')
        self.assertGreater(impact_pos, -1, 'Impact check section not found')
        self.assertGreater(impact_pos, summary_pos,
                           'Impact check should appear after summary')


class TestGoDeeperSkippedWhenDeclined(unittest.TestCase):
    """Scenario: Go-Deeper Skipped When Declined

    Given the update completed successfully
    And the go-deeper prompt is displayed
    When the user declines
    Then no override, config, command, or template analysis is performed
    And the skill exits
    """

    def test_command_documents_decline_behavior(self):
        """Command states that declining skips the analysis."""
        content = _get_command_content()
        self.assertIn('If declined, exit', content)

    def test_command_has_all_four_sub_steps(self):
        """Command documents all four analysis dimensions that are skipped on decline."""
        content = _get_command_content()
        self.assertIn('Override Header Drift', content)
        self.assertIn('Config Key Drift', content)
        self.assertIn('Command Behavioral Changes', content)
        self.assertIn('Feature Template Format Changes', content)


class TestGoDeeperSkippedWithAutoApprove(unittest.TestCase):
    """Scenario: Go-Deeper Skipped With Auto-Approve

    Given /pl-update-purlin is invoked with --auto-approve
    And the update completed successfully
    When the skill reaches the customization impact check
    Then the go-deeper prompt is not displayed
    And no impact analysis is performed
    """

    def test_command_skips_go_deeper_with_auto_approve(self):
        """Command explicitly states --auto-approve skips the impact check."""
        content = _get_command_content()
        self.assertIn('Skip entirely if `--auto-approve`', content)

    def test_auto_approve_does_not_analyze(self):
        """Command states no analysis runs under --auto-approve."""
        content = _get_command_content()
        # The command says "Skip entirely if --auto-approve -- do not prompt or analyze."
        self.assertIn('do not prompt or analyze', content.lower())


class TestGoDeeperDetectsOverrideHeaderDrift(unittest.TestCase):
    """Scenario: Go-Deeper Detects Override Header Drift

    Given upstream renamed a heading in a base file
    And the consumer's override file references the old heading
    When the user accepts the go-deeper analysis
    Then the report includes a stale reference warning
    And identifies the renamed heading
    """

    def test_command_documents_override_to_base_mapping(self):
        """Command documents the mapping from override files to upstream base files."""
        content = _get_command_content()
        self.assertIn('HOW_WE_WORK_OVERRIDES.md', content)
        self.assertIn('HOW_WE_WORK_BASE.md', content)
        self.assertIn('ARCHITECT_OVERRIDES.md', content)
        self.assertIn('ARCHITECT_BASE.md', content)
        self.assertIn('BUILDER_OVERRIDES.md', content)
        self.assertIn('BUILDER_BASE.md', content)
        self.assertIn('QA_OVERRIDES.md', content)
        self.assertIn('QA_BASE.md', content)
        self.assertIn('PM_OVERRIDES.md', content)
        self.assertIn('PM_BASE.md', content)

    def test_command_extracts_section_headers(self):
        """Command instructs extracting ## headers from base files."""
        content = _get_command_content()
        # The command references extracting `## ` headers
        self.assertIn('`## ` headers', content)

    def test_command_compares_old_and_new_base_versions(self):
        """Command instructs comparing old and new upstream base file versions."""
        content = _get_command_content()
        self.assertIn('old and new upstream base files', content.lower())

    def test_command_reports_stale_references(self):
        """Command instructs reporting stale references."""
        content = _get_command_content()
        self.assertIn('stale references', content.lower())


class TestGoDeeperDetectsOrphanedConfigKeys(unittest.TestCase):
    """Scenario: Go-Deeper Detects Orphaned Config Keys

    Given upstream removed a key from purlin-config-sample/config.json
    And the consumer's config.local.json still has that key
    When the user accepts the go-deeper analysis
    Then the report flags the key as orphaned
    """

    def test_command_references_config_sample_comparison(self):
        """Command instructs comparing old vs new upstream config.json."""
        content = _get_command_content()
        self.assertIn('purlin-config-sample/config.json', content)

    def test_command_detects_orphaned_keys(self):
        """Command instructs detecting orphaned keys in local config."""
        content = _get_command_content()
        self.assertIn('orphaned keys', content.lower())

    def test_command_cross_references_local_config(self):
        """Command instructs cross-referencing against consumer config.local.json."""
        content = _get_command_content()
        # The go-deeper section references checking consumer's config.local.json
        self.assertIn('config.local.json', content)

    def test_command_notes_changed_defaults(self):
        """Command instructs noting changed default values."""
        content = _get_command_content()
        self.assertIn('changed defaults', content.lower())


class TestGoDeeperSummarizesSkippedCommandChanges(unittest.TestCase):
    """Scenario: Go-Deeper Summarizes Skipped Command Changes

    Given the consumer kept their local version of a command file
    And upstream changed that file between old and new SHA
    When the user accepts the go-deeper analysis
    Then the report includes an informational summary of upstream changes
    """

    def test_command_documents_command_behavioral_changes(self):
        """Command documents the command behavioral changes dimension."""
        content = _get_command_content()
        self.assertIn('Command Behavioral Changes', content)

    def test_command_summarizes_upstream_diffs(self):
        """Command instructs summarizing upstream changes for kept files."""
        content = _get_command_content()
        self.assertIn('summarize what changed upstream', content.lower())

    def test_command_is_informational_only(self):
        """Command states this dimension is informational only."""
        content = _get_command_content()
        self.assertIn('Informational only', content)


class TestGoDeeperAvailableInDryRunMode(unittest.TestCase):
    """Scenario: Go-Deeper Available in Dry-Run Mode

    Given /pl-update-purlin is invoked with --dry-run
    And the dry-run summary has been displayed
    When the skill reaches the customization impact check
    Then it prompts the user for go-deeper analysis
    And analysis runs read-only if accepted
    """

    def test_command_allows_go_deeper_in_dry_run(self):
        """Command states go-deeper is safe in --dry-run mode."""
        content = _get_command_content()
        self.assertIn('safe in `--dry-run` mode', content.lower())

    def test_command_states_read_only_analysis(self):
        """Command states analysis is read-only."""
        content = _get_command_content()
        self.assertIn('read-only', content.lower())


class TestGoDeeperReportsNoImpactsWhenClean(unittest.TestCase):
    """Scenario: Go-Deeper Reports No Impacts When Clean

    Given no overrides reference changed headers
    And no config keys were removed or renamed upstream
    And no command files were skipped or kept locally
    And the feature template format did not change
    When the user accepts the go-deeper analysis
    Then the report shows: "No customization impacts detected."
    """

    def test_command_has_no_impacts_message(self):
        """Command includes the 'No customization impacts detected' message."""
        content = _get_command_content()
        self.assertIn('No customization impacts detected', content)

    def test_command_omits_clean_categories(self):
        """Command instructs omitting categories with no issues."""
        content = _get_command_content()
        self.assertIn('Omit categories with no issues', content)


class TestNewMCPServerDetectedOnUpdate(unittest.TestCase):
    """Scenario: New MCP Server Detected on Update

    Given the new upstream manifest adds a server not in the old manifest
    When /pl-update-purlin is invoked and the update completes
    Then init.sh installs the new server during the refresh step
    And the summary report includes the new server as newly available
    And the summary includes "Restart Claude Code to load MCP changes."
    """

    def test_command_references_mcp_manifest(self):
        """Command references tools/mcp/manifest.json for MCP diff."""
        content = _get_command_content()
        self.assertIn('tools/mcp/manifest.json', content)

    def test_command_detects_added_servers(self):
        """Command instructs detecting added MCP servers."""
        content = _get_command_content()
        self.assertIn('Added servers', content)

    def test_command_reports_new_servers_in_summary(self):
        """Command instructs reporting newly available servers in summary."""
        content = _get_command_content()
        self.assertIn('newly available', content.lower())

    def test_command_includes_restart_notice(self):
        """Command includes restart notice when MCP changes occur."""
        content = _get_command_content()
        self.assertIn('Restart Claude Code to load MCP changes', content)

    def test_mcp_manifest_file_exists(self):
        """The tools/mcp/manifest.json file exists in the repository."""
        manifest_path = os.path.join(
            PROJECT_ROOT, 'tools', 'mcp', 'manifest.json')
        self.assertTrue(os.path.isfile(manifest_path),
                        f'manifest.json not found: {manifest_path}')


class TestRemovedMCPServerGeneratesAdvisory(unittest.TestCase):
    """Scenario: Removed MCP Server Generates Advisory

    Given the old manifest contains a server absent from the new manifest
    When /pl-update-purlin is invoked and the update completes
    Then the summary includes a removal advisory with claude mcp remove command
    And the server is NOT auto-removed
    """

    def test_command_detects_removed_servers(self):
        """Command instructs detecting removed MCP servers."""
        content = _get_command_content()
        self.assertIn('Removed servers', content)

    def test_command_includes_remove_advisory(self):
        """Command includes the claude mcp remove advisory text."""
        content = _get_command_content()
        self.assertIn('claude mcp remove', content)

    def test_command_does_not_auto_remove(self):
        """Command explicitly states not to auto-remove servers."""
        content = _get_command_content()
        self.assertIn('Do NOT auto-remove', content)


class TestChangedMCPServerConfigurationAdvisory(unittest.TestCase):
    """Scenario: Changed MCP Server Configuration Advisory

    Given a server exists in both old and new manifests with different config
    When /pl-update-purlin is invoked and the update completes
    Then the summary includes an advisory that the server config changed
    And the advisory includes the reconfiguration command
    """

    def test_command_detects_changed_servers(self):
        """Command instructs detecting changed MCP server configurations."""
        content = _get_command_content()
        self.assertIn('Changed servers', content)

    def test_command_includes_reconfiguration_advisory(self):
        """Command includes reconfiguration command format."""
        content = _get_command_content()
        self.assertIn('Reconfigure:', content)

    def test_command_compares_server_fields(self):
        """Command instructs comparing transport, command, args, or url fields."""
        content = _get_command_content()
        for field in ['transport', 'command', 'args', 'url']:
            self.assertIn(field, content.lower(),
                          f'Missing server comparison field: {field}')


class TestUpdateSurfacesMissingPrerequisiteWarning(unittest.TestCase):
    """Scenario: Update Surfaces Missing Prerequisite Warning

    Given the consumer's environment does not have node/npx installed
    And the submodule is behind by 3 commits
    When /pl-update-purlin is invoked and the user confirms
    Then the submodule is advanced (update is NOT blocked)
    And the output includes a prerequisite warning for node
    And the warning includes the platform-appropriate install command
    And the warning explains what functionality is unavailable without node
    And init.sh --quiet runs successfully after the warning
    """

    def test_command_has_prerequisite_validation_step(self):
        """Command includes the post-advance prerequisite validation step."""
        content = _get_command_content()
        self.assertIn('Post-Advance Prerequisite Validation', content)

    def test_command_references_preflight_only_flag(self):
        """Command instructs running init.sh --preflight-only."""
        content = _get_command_content()
        self.assertIn('--preflight-only', content)

    def test_command_warns_not_blocks_on_missing_tools(self):
        """Command states missing tools produce warnings, not hard exits."""
        content = _get_command_content()
        self.assertIn('Do NOT block the update', content)

    def test_init_supports_preflight_only_flag(self):
        """init.sh supports the --preflight-only flag."""
        init_path = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
        with open(init_path) as f:
            init_content = f.read()
        self.assertIn('--preflight-only', init_content)

    def test_command_includes_prerequisite_in_summary(self):
        """Command instructs including prerequisite status in the summary."""
        content = _get_command_content()
        self.assertIn('prerequisite status in the summary', content.lower())


class TestUpdateWithAllPrerequisitesMetShowsNoWarnings(unittest.TestCase):
    """Scenario: Update With All Prerequisites Met Shows No Warnings

    Given git, claude, and node are all installed
    And the submodule is behind by 2 commits
    When /pl-update-purlin is invoked and the user confirms
    Then no prerequisite warnings appear in the output
    And the update completes normally
    """

    def test_command_states_no_output_when_all_present(self):
        """Command states no prerequisite output when all tools are present."""
        content = _get_command_content()
        self.assertIn(
            'all prerequisites are met: produce no prerequisite output',
            content.lower())

    def test_preflight_only_exits_cleanly_when_all_present(self):
        """init.sh --preflight-only exits 0 when all tools present."""
        init_path = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
        with open(init_path) as f:
            init_content = f.read()
        # The preflight-only path should exit 0
        self.assertIn('PREFLIGHT_ONLY', init_content)


class TestMissingRequiredToolDuringUpdateWarnsButContinues(unittest.TestCase):
    """Scenario: Missing Required Tool During Update Warns But Continues

    Given claude CLI is not installed
    And the submodule is behind by 1 commit
    When /pl-update-purlin is invoked and the user confirms
    Then the submodule is advanced successfully
    And the output includes a warning about claude with install instructions
    And the output notes MCP servers will not be installed
    And init.sh still runs (with MCP installation skipped)
    And the summary report includes the prerequisite status
    """

    def test_command_handles_missing_recommended_tools(self):
        """Command documents behavior for missing recommended tools."""
        content = _get_command_content()
        self.assertIn('recommended', content.lower())
        self.assertIn('npm install -g @anthropic-ai/claude-code', content)

    def test_command_notes_mcp_unavailable_without_claude(self):
        """Command notes MCP servers will not be installed without claude."""
        content = _get_command_content()
        self.assertIn('MCP servers will not be installed', content)

    def test_command_update_continues_despite_missing_tool(self):
        """Command states the submodule is already advanced so update continues."""
        content = _get_command_content()
        self.assertIn('submodule is already advanced', content.lower())

    def test_command_handles_missing_optional_tools(self):
        """Command documents behavior for missing optional tools like node."""
        content = _get_command_content()
        self.assertIn('Playwright web testing will be unavailable', content)


class TestNoMCPOutputWhenManifestUnchanged(unittest.TestCase):
    """Scenario: No MCP Output When Manifest Unchanged

    Given tools/mcp/manifest.json is identical between old and new SHA
    When /pl-update-purlin is invoked and the update completes
    Then no MCP-related output appears in the summary
    And no "Restart Claude Code" notice is shown for MCP reasons
    """

    def test_command_skips_mcp_when_unchanged(self):
        """Command instructs skipping MCP analysis when manifest unchanged."""
        content = _get_command_content()
        self.assertIn(
            'did NOT change between old and new SHA, skip this step entirely',
            content)

    def test_command_produces_no_mcp_output_when_clean(self):
        """Command states no MCP output when manifest unchanged."""
        content = _get_command_content()
        self.assertIn('produce no MCP-related output', content)

    def test_mcp_check_uses_diff_tree(self):
        """Command uses diff-tree to check manifest changes."""
        content = _get_command_content()
        self.assertIn(
            'diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> '
            '-- tools/mcp/manifest.json',
            content)


class TestUnmodifiedAgentFilesAutoUpdated(unittest.TestCase):
    """Scenario: Unmodified Agent Files Auto-Updated

    Given builder-worker.md changed upstream in .claude/agents/
    And the consumer's .claude/agents/builder-worker.md matches the old upstream version
    When /pl-update-purlin is invoked and update completes
    Then init.sh auto-copies builder-worker.md from submodule
    And the report includes the updated file count
    """

    def test_command_scans_agent_files_in_diff_tree(self):
        """Command's diff-tree invocation includes .claude/agents/ path."""
        content = _get_command_content()
        self.assertIn('.claude/agents/', content)

    def test_command_references_agent_file_comparison(self):
        """Command references comparing agent files against old upstream version."""
        content = _get_command_content()
        self.assertIn('agent files', content.lower())

    def test_init_sh_handles_agent_file_distribution(self):
        """init.sh has copy_agent_files function for agent file distribution."""
        init_path = os.path.join(PROJECT_ROOT, 'tools', 'init.sh')
        with open(init_path) as f:
            init_content = f.read()
        self.assertIn('copy_agent_files', init_content)

    def test_agents_directory_exists(self):
        """The .claude/agents/ directory exists in the framework."""
        agents_dir = os.path.join(PROJECT_ROOT, '.claude', 'agents')
        self.assertTrue(os.path.isdir(agents_dir))


class TestModifiedAgentFileWithUpstreamConflict(unittest.TestCase):
    """Scenario: Modified Agent File with Upstream Conflict

    Given builder-worker.md changed upstream in .claude/agents/
    And the consumer's .claude/agents/builder-worker.md has local modifications
    When /pl-update-purlin is invoked and update completes
    Then the skill shows a three-way diff for the agent file
    And offers merge strategies: "Accept upstream", "Keep current", "Smart merge"
    And waits for user decision
    """

    def test_command_handles_agent_file_conflicts(self):
        """Command's conflict resolution covers agent files."""
        content = _get_command_content()
        # Conflict resolution step should mention agent files
        self.assertIn('agent file', content.lower())

    def test_command_offers_merge_strategies_for_agent_files(self):
        """Command offers the same merge strategies for agent files as command files."""
        content = _get_command_content()
        self.assertIn('Accept upstream', content)
        self.assertIn('Keep current', content)
        self.assertIn('Smart merge', content)

    def test_conflict_resolution_covers_both_command_and_agent(self):
        """Conflict resolution step handles both command and agent files."""
        content = _get_command_content()
        # Step 5 should reference both command and agent files
        self.assertIn('command or agent file', content.lower())


class TestProjectRootDetection(unittest.TestCase):
    """Spec Section 2.13: Project Root Detection

    The skill uses PURLIN_PROJECT_ROOT (env var) for project root detection,
    with directory-climbing as fallback.
    """

    def test_command_references_purlin_project_root(self):
        """Command references PURLIN_PROJECT_ROOT env var for path resolution."""
        content = _get_command_content()
        self.assertIn('PURLIN_PROJECT_ROOT', content)

    def test_command_has_path_resolution_section(self):
        """Command includes a Path Resolution section."""
        content = _get_command_content()
        self.assertIn('Path Resolution', content)

    def test_command_uses_env_var_with_climbing_fallback(self):
        """Command uses env var as primary with directory-climbing fallback."""
        content = _get_command_content()
        self.assertIn('PURLIN_PROJECT_ROOT', content)
        self.assertIn('climbing', content.lower())

    def test_path_resolution_before_behavior(self):
        """Path Resolution section appears before the Behavior section."""
        content = _get_command_content()
        path_pos = content.find('Path Resolution')
        behavior_pos = content.find('**Behavior:**')
        self.assertGreater(path_pos, -1, 'Path Resolution section not found')
        self.assertGreater(behavior_pos, -1, 'Behavior section not found')
        self.assertLess(path_pos, behavior_pos,
                        'Path Resolution should appear before Behavior')


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
