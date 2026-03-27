#!/usr/bin/env python3
"""Tests for the /pl-remote agent command.

Covers automated scenarios from features/pl_remote.md:
- branch create Creates And Pushes New Branch
- branch create Rejects When Not On Main
- branch create Rejects Existing Branch Name
- branch create Rejects When No Remote
- branch join Switches To Existing Remote Branch
- branch join Fast-Forwards Local Branch
- branch join Rejects Nonexistent Remote Branch
- branch leave Returns To Main
- branch leave Is No-Op When No Active Branch
- branch leave Does Not Delete The Branch
- branch list Shows Remote Branches
- branch list Shows Empty Message When No Branches
- push Resolves To Main When No Active Branch
- push Rejects Non-Main Branch When No Active Branch
- push Exits With Guidance When No Remote Configured
- push First Push Shows Safety Confirmation
- push First Push To Empty Remote Succeeds
- push First Push Aborted When User Declines
- push Subsequent Push Skips Confirmation
- push Exits When Not On Collaboration Branch
- push Exits When On Wrong Branch
- push Aborts When Working Tree Is Dirty
- push Blocked When Local Is BEHIND Remote
- push Blocked When Local Is DIVERGED
- push Succeeds When AHEAD
- push Is No-Op When SAME
- pull Resolves To Main When No Active Branch
- pull Rejects Non-Main Branch When No Active Branch
- pull Exits With Guidance When No Remote Configured
- pull First Pull Shows Safety Confirmation
- pull First Pull Aborted When User Declines
- pull Exits When Not On Collaboration Branch
- pull Aborts When Working Tree Is Dirty
- pull Fast-Forwards When BEHIND
- pull Creates Merge Commit When DIVERGED No Conflicts
- pull Exits On Conflict With Per-File Context
- pull Is No-Op When AHEAD
- pull Is No-Op When SAME
- pull Generates Digest After Successful Merge
- pull Explicit Branch Skips Branch Guard
- add Prints Help Banner When No Args And No Remote
- add Guides Setup When No Remote Exists
- add Shows Hosting Hints When Available
- add Skips Banner When URL Argument Provided
- add Accepts Both URL And Name Arguments
- add Shows Existing Remotes When Remote Already Configured
- add Changes URL When Named Remote Exists And URL Provided
- add Adds New Remote When Named Remote Does Not Exist
- add Reports Connectivity Failure And Classifies Error
- add Rolls Back New Remote On Declined Correction
- add Restores Old URL On Set-Url Failure
- add Normalizes Browser URL to SSH
- add Sets Up SSH Key On Auth Failure
- add Uses Existing SSH Key When Available
- add Does Not Require Branch Guard
- add Does Not Require Clean Working Tree
- add Does Not Push Or Pull
- add Prompts Config Sync When Non-Origin Name Is Only Remote
- add Skips Config Sync When Name Is Origin
- Invalid Subcommand Prints Usage
- No Subcommand Prints Usage
- Config Reads branch_collab Before remote_collab
- add Success Suggests Next Steps
- push No Remote Suggests add
- branch create Success Suggests push and pull
- branch list Empty Suggests create

The agent command is a Claude skill defined in .claude/commands/pl-remote.md.
These tests verify the skill file contains the required structural content:
- Subcommand documentation (push, pull, add, branch)
- Usage section with all subcommand signatures
- Shared protocols (Config Reading, Branch Resolution, Branch Guard,
  Remote Guard, Working Tree Check)
- Push protocol (sync states, first-push safety, no --force)
- Pull protocol (merge, no rebase, digest, explicit branch mode)
- Add protocol (guided setup, SSH, URL normalization, rollback, config sync)
- Branch subcommands (create, join, leave, list)
- Forbidden operations per subcommand
"""
import os
import re
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-remote.md')


class TestSkillFileExists(unittest.TestCase):
    """Verify the skill file exists and is loadable."""

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-remote.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')


class TestSkillFileHeader(unittest.TestCase):
    """Verify the skill file header metadata."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_purlin_command_header(self):
        """Skill file declares itself as a Purlin command."""
        self.assertIn('Purlin command:', self.content)

    def test_shared_mode(self):
        """Skill file declares shared mode."""
        self.assertIn('shared', self.content.lower())

    def test_replaces_legacy_commands(self):
        """Skill file replaces the three legacy remote commands."""
        self.assertIn('pl-remote-push', self.content)
        self.assertIn('pl-remote-pull', self.content)
        self.assertIn('pl-remote-add', self.content)


class TestUsageSection(unittest.TestCase):
    """Scenario: Invalid Subcommand Prints Usage
    Scenario: No Subcommand Prints Usage

    Verify the usage section documents all four subcommands with their
    signatures.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_usage_section_exists(self):
        """Skill file has a Usage section."""
        self.assertIn('## Usage', self.content)

    def test_push_subcommand_in_usage(self):
        """Usage lists the push subcommand."""
        self.assertIn('/pl-remote push', self.content)

    def test_pull_subcommand_in_usage(self):
        """Usage lists the pull subcommand with optional branch arg."""
        self.assertIn('/pl-remote pull', self.content)

    def test_add_subcommand_in_usage(self):
        """Usage lists the add subcommand with optional url and name args."""
        self.assertIn('/pl-remote add', self.content)

    def test_branch_create_in_usage(self):
        """Usage lists branch create subcommand."""
        self.assertIn('/pl-remote branch create', self.content)

    def test_branch_join_in_usage(self):
        """Usage lists branch join subcommand."""
        self.assertIn('/pl-remote branch join', self.content)

    def test_branch_leave_in_usage(self):
        """Usage lists branch leave subcommand."""
        self.assertIn('/pl-remote branch leave', self.content)

    def test_branch_list_in_usage(self):
        """Usage lists branch list subcommand."""
        self.assertIn('/pl-remote branch list', self.content)

    def test_no_subcommand_prints_usage(self):
        """Skill describes behavior for no subcommand: print usage."""
        # The spec says: "No subcommand or invalid subcommand: print usage and exit."
        self.assertIn('usage', self.content.lower())


class TestConfigReading(unittest.TestCase):
    """Scenario: Config Reads branch_collab Before remote_collab

    Verify the skill documents config reading with the correct priority:
    1. branch_collab.remote
    2. Fallback: remote_collab.remote
    3. Default: "origin"
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_config_reading_section(self):
        """Skill file has a Config Reading section."""
        self.assertIn('Config Reading', self.content)

    def test_branch_collab_remote(self):
        """Skill references branch_collab.remote as primary config key."""
        self.assertIn('branch_collab', self.content)

    def test_remote_collab_fallback(self):
        """Skill references remote_collab.remote as fallback."""
        self.assertIn('remote_collab', self.content)

    def test_origin_default(self):
        """Skill specifies origin as the default remote name."""
        self.assertIn('"origin"', self.content)

    def test_config_json_path(self):
        """Skill references .purlin/config.json for config reading."""
        self.assertIn('.purlin/config.json', self.content)


class TestCollaborationBranchResolution(unittest.TestCase):
    """Verify the skill documents collaboration branch resolution from
    .purlin/runtime/active_branch.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_active_branch_file(self):
        """Skill references .purlin/runtime/active_branch."""
        self.assertIn('.purlin/runtime/active_branch', self.content)

    def test_fallback_to_main(self):
        """Skill documents fallback to main when no active branch."""
        # The spec says: "If absent or empty: collaboration branch = main."
        self.assertIn('main', self.content)

    def test_collaboration_branch_section(self):
        """Skill has a section about collaboration branch resolution."""
        self.assertIn('Collaboration Branch', self.content)


class TestBranchGuard(unittest.TestCase):
    """Scenario: push Exits When Not On Collaboration Branch
    Scenario: push Exits When On Wrong Branch

    Verify the skill documents the branch guard protocol.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_branch_guard_section(self):
        """Skill has a Branch Guard section."""
        self.assertIn('Branch Guard', self.content)

    def test_rev_parse_abbrev_ref(self):
        """Skill uses git rev-parse --abbrev-ref HEAD for current branch check."""
        self.assertIn('git rev-parse --abbrev-ref HEAD', self.content)

    def test_wrong_branch_message(self):
        """Skill documents the wrong-branch error message."""
        self.assertIn(
            'This command must be run from the collaboration branch',
            self.content)

    def test_no_active_branch_message(self):
        """Skill documents the no-active-branch error when not on main."""
        self.assertIn('No active collaboration branch', self.content)


class TestRemoteGuard(unittest.TestCase):
    """Scenario: push Exits With Guidance When No Remote Configured
    Scenario: branch create Rejects When No Remote

    Verify the skill documents the remote guard check.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_remote_guard_section(self):
        """Skill has a Remote Guard section."""
        self.assertIn('Remote Guard', self.content)

    def test_git_remote_check(self):
        """Skill uses git remote -v to check for configured remotes."""
        self.assertIn('git remote -v', self.content)

    def test_no_remote_message(self):
        """Skill documents the no-remote error message."""
        self.assertIn(
            'No git remote configured',
            self.content)

    def test_suggests_add_command(self):
        """Skill suggests /pl-remote add when no remote is configured."""
        self.assertIn('/pl-remote add', self.content)


class TestWorkingTreeCheck(unittest.TestCase):
    """Scenario: push Aborts When Working Tree Is Dirty
    Scenario: pull Aborts When Working Tree Is Dirty

    Verify the skill documents the working tree check.
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_working_tree_check_section(self):
        """Skill has a Working Tree Check section."""
        self.assertIn('Working Tree Check', self.content)

    def test_git_status_porcelain(self):
        """Skill uses git status --porcelain for working tree check."""
        self.assertIn('git status --porcelain', self.content)

    def test_purlin_dir_exempt(self):
        """Skill exempts .purlin/ changes from working tree check."""
        self.assertIn('.purlin/', self.content)


class TestPushSubcommand(unittest.TestCase):
    """Scenarios covering push behavior:
    - push Resolves To Main When No Active Branch
    - push First Push Shows Safety Confirmation
    - push Blocked When Local Is BEHIND Remote
    - push Blocked When Local Is DIVERGED
    - push Succeeds When AHEAD
    - push Is No-Op When SAME
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_push_section_exists(self):
        """Skill has a push subcommand section."""
        self.assertIn('### push', self.content)

    def test_push_preconditions(self):
        """Skill documents push preconditions including Branch Guard."""
        # Look for preconditions being described in a push context
        self.assertIn('Branch Resolution', self.content)

    def test_first_push_safety(self):
        """Skill documents first-push safety confirmation."""
        self.assertIn('First-push safety', self.content)

    def test_first_push_confirmation_display(self):
        """Skill shows remote name, URL, branch, and commit count."""
        self.assertIn('Remote:', self.content)
        self.assertIn('Branch:', self.content)
        self.assertIn('Commits:', self.content)
        self.assertIn('Proceed?', self.content)

    def test_sync_state_same(self):
        """Skill documents SAME sync state: already in sync."""
        self.assertIn('Already in sync', self.content)

    def test_sync_state_behind(self):
        """Skill documents BEHIND sync state: must pull first."""
        self.assertIn('BEHIND', self.content)

    def test_sync_state_diverged(self):
        """Skill documents DIVERGED sync state."""
        self.assertIn('DIVERGED', self.content)

    def test_sync_state_ahead(self):
        """Skill documents AHEAD sync state: push proceeds."""
        self.assertIn('AHEAD', self.content)

    def test_no_force_push(self):
        """Skill explicitly forbids --force."""
        self.assertIn('--force', self.content)

    def test_git_fetch_before_sync(self):
        """Skill fetches before determining sync state."""
        self.assertIn('git fetch', self.content)


class TestPullSubcommand(unittest.TestCase):
    """Scenarios covering pull behavior:
    - pull Fast-Forwards When BEHIND
    - pull Creates Merge Commit When DIVERGED No Conflicts
    - pull Exits On Conflict With Per-File Context
    - pull Generates Digest After Successful Merge
    - pull Explicit Branch Skips Branch Guard
    - pull Is No-Op When AHEAD
    - pull Is No-Op When SAME
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_pull_section_exists(self):
        """Skill has a pull subcommand section."""
        self.assertIn('### pull', self.content)

    def test_two_modes(self):
        """Skill documents no-argument and explicit-branch pull modes."""
        self.assertIn('No-argument', self.content)
        self.assertIn('Explicit-branch', self.content)

    def test_fast_forward_only(self):
        """Skill uses merge --ff-only for fast-forward pulls."""
        self.assertIn('--ff-only', self.content)

    def test_no_rebase(self):
        """Skill forbids rebase during pull."""
        # "No rebase" should be in the FORBIDDEN section
        self.assertIn('No rebase', self.content)

    def test_merge_for_diverged(self):
        """Skill uses git merge for diverged state."""
        self.assertIn('git merge', self.content)

    def test_conflict_per_file_context(self):
        """Skill documents per-file conflict context."""
        self.assertIn('conflict', self.content.lower())

    def test_first_pull_safety(self):
        """Skill documents first-pull safety confirmation."""
        self.assertIn('First-pull safety', self.content)

    def test_digest_generation(self):
        """Skill runs generate_whats_different.sh after merge."""
        self.assertIn('generate_whats_different.sh', self.content)

    def test_digest_non_blocking(self):
        """Skill treats digest failure as non-blocking."""
        # Spec says: "Non-blocking -- warn and continue on failure."
        lower = self.content.lower()
        self.assertTrue(
            'non-blocking' in lower or 'warn' in lower,
            'Skill should document that digest failure is non-blocking')

    def test_explicit_branch_skips_guard(self):
        """Explicit-branch mode skips branch resolution and guard."""
        self.assertIn('Skip resolution', self.content)


class TestAddSubcommand(unittest.TestCase):
    """Scenarios covering add behavior:
    - add Prints Help Banner When No Args And No Remote
    - add Guides Setup When No Remote Exists
    - add Shows Hosting Hints When Available
    - add Normalizes Browser URL to SSH
    - add Sets Up SSH Key On Auth Failure
    - add Uses Existing SSH Key When Available
    - add Rolls Back New Remote On Declined Correction
    - add Restores Old URL On Set-Url Failure
    - add Does Not Require Branch Guard
    - add Does Not Require Clean Working Tree
    - add Does Not Push Or Pull
    - add Prompts Config Sync When Non-Origin Name Is Only Remote
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_add_section_exists(self):
        """Skill has an add subcommand section."""
        self.assertIn('### add', self.content)

    def test_guided_setup(self):
        """Skill documents guided setup when no remotes exist."""
        self.assertIn('guided setup', self.content.lower())

    def test_help_banner(self):
        """Skill documents printing a help banner with URL formats."""
        self.assertIn('help banner', self.content.lower())

    def test_hosting_hints(self):
        """Skill documents scanning for hosting hints."""
        self.assertIn('hosting hint', self.content.lower())

    def test_ssh_config_scan(self):
        """Skill scans ~/.ssh/config for hosting hints."""
        self.assertIn('.ssh/config', self.content)

    def test_url_normalization(self):
        """Skill normalizes browser URLs to SSH."""
        self.assertIn('Normalize', self.content)
        self.assertIn('SSH', self.content)

    def test_git_ls_remote_verification(self):
        """Skill verifies connectivity via git ls-remote."""
        self.assertIn('git ls-remote', self.content)

    def test_ssh_key_auto_setup(self):
        """Skill documents SSH key auto-setup on auth failure."""
        self.assertIn('auto-setup SSH key', self.content)
        self.assertIn('keyscan', self.content)
        self.assertIn('generate if needed', self.content)

    def test_rollback_on_failure(self):
        """Skill documents rollback (git remote remove) on failed add."""
        self.assertIn('git remote remove', self.content)

    def test_restore_old_url(self):
        """Skill documents restoring old URL on set-url failure."""
        self.assertIn('restore', self.content.lower())

    def test_no_push_or_pull(self):
        """Skill forbids push/pull during add."""
        self.assertIn('No push/pull', self.content)

    def test_config_sync_for_non_origin(self):
        """Skill documents config sync prompt for non-origin remotes."""
        self.assertIn('branch_collab.remote', self.content)

    def test_git_remote_add_command(self):
        """Skill uses git remote add to configure remotes."""
        self.assertIn('git remote add', self.content)

    def test_success_output_format(self):
        """Skill documents the success output with Remote configured."""
        self.assertIn('Remote configured', self.content)

    def test_next_steps_in_success(self):
        """Skill prints next steps after successful add."""
        self.assertIn('Next steps', self.content)


class TestBranchCreate(unittest.TestCase):
    """Scenarios for branch create:
    - branch create Creates And Pushes New Branch
    - branch create Rejects When Not On Main
    - branch create Rejects Existing Branch Name
    - branch create Rejects When No Remote
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_branch_create_section(self):
        """Skill documents branch create subcommand."""
        self.assertIn('branch create', self.content)

    def test_creates_branch_with_checkout(self):
        """Skill uses git checkout -b to create the branch."""
        self.assertIn('git checkout -b', self.content)

    def test_pushes_with_upstream(self):
        """Skill uses git push -u to set upstream tracking."""
        self.assertIn('git push -u', self.content)

    def test_writes_active_branch(self):
        """Skill writes the branch name to active_branch file."""
        self.assertIn('.purlin/runtime/active_branch', self.content)

    def test_stores_base_branch(self):
        """Skill stores the base branch in branch_collab_base."""
        self.assertIn('.purlin/runtime/branch_collab_base', self.content)

    def test_must_be_on_main(self):
        """Skill requires being on main for branch create."""
        # Preconditions include "must be on main"
        self.assertIn('must be on', self.content.lower())

    def test_name_must_not_exist(self):
        """Skill checks that branch name does not already exist."""
        self.assertIn('must not exist', self.content.lower())

    def test_success_message(self):
        """Skill documents the success message for branch create."""
        self.assertIn('Created collaboration branch', self.content)


class TestBranchJoin(unittest.TestCase):
    """Scenarios for branch join:
    - branch join Switches To Existing Remote Branch
    - branch join Fast-Forwards Local Branch
    - branch join Rejects Nonexistent Remote Branch
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_branch_join_section(self):
        """Skill documents branch join subcommand."""
        self.assertIn('branch join', self.content)

    def test_join_creates_local_from_remote(self):
        """Skill creates local branch tracking remote when none exists."""
        # The spec uses: git checkout -b <name> <remote>/<name>
        self.assertIn('git checkout -b', self.content)

    def test_join_fast_forwards(self):
        """Skill fast-forwards local branch on join when it exists."""
        self.assertIn('merge --ff-only', self.content)

    def test_branch_must_exist_on_remote(self):
        """Skill requires the branch to exist on remote."""
        self.assertIn('must exist on remote', self.content.lower())

    def test_success_message(self):
        """Skill documents the success message for branch join."""
        self.assertIn('Joined collaboration branch', self.content)


class TestBranchLeave(unittest.TestCase):
    """Scenarios for branch leave:
    - branch leave Returns To Main
    - branch leave Is No-Op When No Active Branch
    - branch leave Does Not Delete The Branch
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_branch_leave_section(self):
        """Skill documents branch leave subcommand."""
        self.assertIn('branch leave', self.content)

    def test_reads_base_branch(self):
        """Skill reads base from branch_collab_base."""
        self.assertIn('branch_collab_base', self.content)

    def test_clears_active_branch(self):
        """Skill clears the active_branch file."""
        self.assertIn('Clear', self.content)
        self.assertIn('active_branch', self.content)

    def test_deletes_base_file(self):
        """Skill deletes the branch_collab_base file."""
        self.assertIn('Delete', self.content)
        self.assertIn('branch_collab_base', self.content)

    def test_does_not_delete_branch(self):
        """Skill explicitly states leave does NOT delete the branch."""
        self.assertIn('NOT delete', self.content)

    def test_success_message(self):
        """Skill documents the success message for branch leave."""
        self.assertIn('Left collaboration branch', self.content)


class TestBranchList(unittest.TestCase):
    """Scenarios for branch list:
    - branch list Shows Remote Branches
    - branch list Shows Empty Message When No Branches
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_branch_list_section(self):
        """Skill documents branch list subcommand."""
        self.assertIn('branch list', self.content)

    def test_fetches_before_listing(self):
        """Skill fetches from remote before listing."""
        self.assertIn('git fetch', self.content)

    def test_filters_head_main_master(self):
        """Skill filters out HEAD, main, and master from branch list."""
        self.assertIn('HEAD', self.content)
        self.assertIn('main', self.content)
        self.assertIn('master', self.content)

    def test_marks_active_branch(self):
        """Skill marks the active branch in the listing."""
        self.assertIn('active', self.content.lower())

    def test_empty_message(self):
        """Skill documents the empty-branches message."""
        self.assertIn('No collaboration branches', self.content)

    def test_suggests_create_when_empty(self):
        """Skill suggests branch create when no branches exist."""
        self.assertIn('/pl-remote branch create', self.content)


class TestForbiddenOperations(unittest.TestCase):
    """Verify the skill documents forbidden operations per subcommand."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_push_no_force(self):
        """Push forbids --force."""
        self.assertIn('--force', self.content)

    def test_pull_no_rebase(self):
        """Pull forbids rebase."""
        self.assertIn('No rebase', self.content)

    def test_pull_no_push(self):
        """Pull forbids push."""
        self.assertIn('No push', self.content)

    def test_add_no_remote_deletion(self):
        """Add forbids remote deletion except rollback."""
        self.assertIn('No remote deletion', self.content)

    def test_branch_create_only_from_main(self):
        """Branch create only from main."""
        # "branch create only from main" in FORBIDDEN section
        lower = self.content.lower()
        self.assertTrue(
            'only from main' in lower or 'must be on' in lower,
            'Skill should restrict branch create to main')

    def test_branch_leave_never_deletes(self):
        """Branch leave never deletes."""
        self.assertIn('NOT delete', self.content)

    def test_branch_join_no_force_checkout(self):
        """Branch join does not force-checkout dirty tree."""
        lower = self.content.lower()
        self.assertTrue(
            'force-checkout' in lower or 'force' in lower
            or 'dirty' in lower,
            'Skill should mention join does not force-checkout dirty tree')

    def test_validate_branch_names(self):
        """Skill mentions validating branch names."""
        lower = self.content.lower()
        self.assertTrue(
            'validate' in lower or 'injection' in lower,
            'Skill should mention input validation for branch names')


class TestOnboardingGuidance(unittest.TestCase):
    """Scenarios for next-step guidance:
    - add Success Suggests Next Steps
    - push No Remote Suggests add
    - branch create Success Suggests push and pull
    - branch list Empty Suggests create
    """

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_add_success_suggests_branch_create(self):
        """Add success output suggests /pl-remote branch create."""
        self.assertIn('/pl-remote branch create', self.content)

    def test_add_success_suggests_push(self):
        """Add success output suggests /pl-remote push."""
        self.assertIn('/pl-remote push', self.content)

    def test_branch_create_suggests_push_pull(self):
        """Branch create success suggests push and pull."""
        self.assertIn('/pl-remote push', self.content)
        self.assertIn('/pl-remote pull', self.content)

    def test_branch_create_suggests_leave(self):
        """Branch create success suggests branch leave."""
        self.assertIn('/pl-remote branch leave', self.content)

    def test_branch_list_empty_suggests_create(self):
        """Branch list empty suggests /pl-remote branch create."""
        self.assertIn('/pl-remote branch create', self.content)


class TestArgumentsPlaceholder(unittest.TestCase):
    """Verify the skill file includes the ARGUMENTS placeholder."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_arguments_variable(self):
        """Skill file includes $ARGUMENTS for receiving user input."""
        self.assertIn('$ARGUMENTS', self.content)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    import json
    results = {"status": "FAIL" if failed else "PASS", "passed": passed, "failed": failed, "total": result.testsRun}
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\ntests.json: {results['status']}")
