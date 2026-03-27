#!/usr/bin/env python3
"""Tests for the /pl-merge agent command.

Covers automated scenarios from features/pl_merge.md:
- Merge succeeds and cleans up
- Cleanup runs as single command to avoid CWD invalidation
- Not in a worktree

The agent command is a Claude skill defined in .claude/commands/pl-merge.md,
backed by a SessionEnd hook at tools/hooks/merge-worktrees.sh.
These tests verify structural properties of both files:
- Skill file: role guard, worktree detection, merge protocol steps, cleanup
- Hook file: worktree detection, branch filtering, merge lock, safe-file
  auto-resolve, breadcrumb writing, single-command cleanup
"""
import json
import os
import re
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-merge.md')
HOOK_FILE = os.path.join(
    PROJECT_ROOT, 'tools', 'hooks', 'merge-worktrees.sh')


def _read_file(path):
    """Read and return the contents of a file."""
    with open(path) as f:
        return f.read()


# =============================================================================
# Scenario: Merge succeeds and cleans up
# =============================================================================

class TestMergeSucceedsAndCleansUp(unittest.TestCase):
    """Scenario: Merge succeeds and cleans up

    Given the agent is in a purlin worktree with committed work
    When /pl-merge is invoked
    Then the worktree branch is merged to the source branch
    And the worktree directory is removed
    And the branch is deleted
    And the iTerm badge shows the current mode on the source branch

    Tests: Structural verification that the skill file and hook contain
    the required merge protocol steps.
    """

    def test_skill_file_exists(self):
        """The skill command file .claude/commands/pl-merge.md exists."""
        self.assertTrue(
            os.path.isfile(COMMAND_FILE),
            f'Command file not found: {COMMAND_FILE}')

    def test_hook_file_exists(self):
        """The hook file tools/hooks/merge-worktrees.sh exists."""
        self.assertTrue(
            os.path.isfile(HOOK_FILE),
            f'Hook file not found: {HOOK_FILE}')

    def test_skill_file_contains_merge_no_edit(self):
        """Skill file instructs merge with --no-edit flag."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('--no-edit', content)

    def test_hook_contains_merge_no_edit(self):
        """Hook performs git merge with --no-edit."""
        content = _read_file(HOOK_FILE)
        self.assertIn('--no-edit', content)

    def test_skill_file_contains_worktree_remove(self):
        """Skill file instructs worktree removal."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('worktree remove', content)

    def test_hook_contains_worktree_remove(self):
        """Hook performs git worktree remove."""
        content = _read_file(HOOK_FILE)
        self.assertIn('worktree remove', content)

    def test_skill_file_contains_branch_delete(self):
        """Skill file instructs branch deletion after merge."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('branch -d', content)

    def test_hook_contains_branch_delete(self):
        """Hook deletes the worktree branch after merge."""
        content = _read_file(HOOK_FILE)
        self.assertIn('branch -d', content)

    def test_skill_file_references_identity_update(self):
        """Skill file instructs updating terminal identity after merge."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('identity.sh', content)

    def test_hook_references_identity_on_failure(self):
        """Hook sets iTerm badge on merge failure."""
        content = _read_file(HOOK_FILE)
        self.assertIn('identity.sh', content)

    def test_skill_file_contains_merge_lock(self):
        """Skill file references the merge lock mechanism."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('merge.lock', content)

    def test_hook_contains_merge_lock(self):
        """Hook implements the merge lock mechanism."""
        content = _read_file(HOOK_FILE)
        self.assertIn('merge.lock', content)

    def test_skill_file_contains_source_branch(self):
        """Skill file identifies the source branch (main)."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('SOURCE_BRANCH', content)

    def test_hook_contains_source_branch(self):
        """Hook identifies the source branch."""
        content = _read_file(HOOK_FILE)
        self.assertIn('SOURCE_BRANCH', content)

    def test_skill_file_contains_session_lock_cleanup(self):
        """Skill file removes .purlin_session.lock during cleanup."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('.purlin_session.lock', content)

    def test_hook_contains_session_lock_cleanup(self):
        """Hook removes .purlin_session.lock during cleanup."""
        content = _read_file(HOOK_FILE)
        self.assertIn('.purlin_session.lock', content)


# =============================================================================
# Scenario: Cleanup runs as single command to avoid CWD invalidation
# =============================================================================

class TestCleanupSingleCommand(unittest.TestCase):
    """Scenario: Cleanup runs as single command to avoid CWD invalidation

    Given the agent is in a purlin worktree
    And the merge to the source branch succeeds
    When cleanup executes
    Then worktree removal, branch deletion, and lock release run in a single
         Bash call starting with cd to the main project root
    And no subsequent Bash calls depend on the worktree path existing

    Tests: Structural verification that the skill file documents single-command
    cleanup and the hook implements it correctly.
    """

    def test_skill_file_documents_single_bash_call(self):
        """Skill file explicitly warns about single Bash call requirement."""
        content = _read_file(COMMAND_FILE)
        # The skill file emphasizes "SINGLE Bash call" or "single chained command"
        self.assertTrue(
            'SINGLE Bash call' in content or 'single Bash call' in content
            or 'single chained command' in content,
            'Skill file must document the single Bash call requirement')

    def test_skill_file_cleanup_starts_with_cd_main_root(self):
        """Skill file cleanup command starts with cd to MAIN_ROOT."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('cd "$MAIN_ROOT"', content)

    def test_skill_file_documents_cwd_invalidation_risk(self):
        """Skill file explains why single command is needed (CWD deletion)."""
        content = _read_file(COMMAND_FILE)
        # The skill file explains the CWD invalidation problem
        self.assertTrue(
            'CWD' in content or 'cwd' in content
            or 'working directory' in content
            or 'Path does not exist' in content,
            'Skill file must explain the CWD invalidation risk')

    def test_hook_cleanup_on_success_is_sequential(self):
        """Hook cleanup after successful merge chains commands together."""
        content = _read_file(HOOK_FILE)
        # After a successful merge, the hook runs cleanup steps in sequence
        # (worktree remove, branch -d, lock release) within the same block
        # Verify all cleanup operations appear after the merge success block
        success_block_match = re.search(
            r'if git merge.*?--no-edit.*?then\s*\n(.*?)(?=\nelse)',
            content, re.DOTALL)
        self.assertIsNotNone(
            success_block_match,
            'Hook must have a success block after git merge')
        success_block = success_block_match.group(1)
        self.assertIn('worktree remove', success_block)
        self.assertIn('branch -d', success_block)
        self.assertIn('_release_merge_lock', success_block)

    def test_hook_changes_to_main_dir_before_merge(self):
        """Hook cds to main directory before performing the merge."""
        content = _read_file(HOOK_FILE)
        self.assertIn('cd "$MAIN_DIR"', content)

    def test_skill_file_cleanup_includes_all_steps(self):
        """Skill file cleanup command includes all required steps."""
        content = _read_file(COMMAND_FILE)
        # The cleanup command must include: session lock removal, worktree
        # removal, worktree prune, branch deletion, merge lock release
        cleanup_pattern = re.search(
            r'cd "\$MAIN_ROOT".*?worktree remove.*?branch -d.*?merge\.lock',
            content, re.DOTALL)
        self.assertIsNotNone(
            cleanup_pattern,
            'Skill file cleanup must chain cd, worktree remove, '
            'branch -d, and merge.lock release')


# =============================================================================
# Scenario: Not in a worktree
# =============================================================================

class TestNotInWorktree(unittest.TestCase):
    """Scenario: Not in a worktree

    Given the agent is not running in a worktree
    When /pl-merge is invoked
    Then it responds "Not in a worktree"

    Tests: Structural verification that both skill file and hook have
    worktree detection and the correct early-exit message.
    """

    def test_skill_file_contains_worktree_guard_message(self):
        """Skill file has the 'Not in a worktree' guard message."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('Not in a worktree', content)

    def test_skill_file_contains_worktree_detection(self):
        """Skill file uses git rev-parse --git-common-dir for detection."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('git-common-dir', content)

    def test_hook_contains_worktree_detection(self):
        """Hook checks GIT_COMMON_DIR vs GIT_DIR for worktree detection."""
        content = _read_file(HOOK_FILE)
        self.assertIn('GIT_COMMON_DIR', content)
        self.assertIn('GIT_DIR', content)

    def test_hook_exits_cleanly_when_not_in_worktree(self):
        """Hook exits 0 when not in a worktree (non-blocking)."""
        content = _read_file(HOOK_FILE)
        # The hook has an early exit when GIT_COMMON_DIR == GIT_DIR
        pattern = re.search(
            r'GIT_COMMON_DIR.*==.*GIT_DIR.*exit 0',
            content, re.DOTALL)
        self.assertIsNotNone(
            pattern,
            'Hook must exit 0 when not in a worktree')

    def test_hook_only_processes_purlin_branches(self):
        """Hook only merges branches matching the purlin- prefix."""
        content = _read_file(HOOK_FILE)
        self.assertIn('purlin-', content)


# =============================================================================
# Additional structural tests: Merge lock protocol
# =============================================================================

class TestMergeLockProtocol(unittest.TestCase):
    """Structural tests for the merge lock protocol (Requirement 2.1.1).

    The merge lock prevents concurrent merges from multiple worktrees.
    """

    def test_skill_file_documents_pid_and_timestamp(self):
        """Skill file documents that the lock contains PID + timestamp."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('PID', content)
        self.assertIn('timestamp', content)

    def test_hook_writes_pid_to_lock(self):
        """Hook writes PID to the merge lock file."""
        content = _read_file(HOOK_FILE)
        # The hook writes JSON with pid field (escaped quotes in bash echo)
        self.assertTrue(
            "'pid'" in content or '"pid"' in content
            or '\\"pid\\"' in content,
            'Hook must write pid to the merge lock file')

    def test_hook_checks_stale_lock(self):
        """Hook checks for stale locks (PID dead) and removes them."""
        content = _read_file(HOOK_FILE)
        # kill -0 is the standard check for whether a PID is alive
        self.assertIn('kill -0', content)

    def test_hook_retries_on_blocked_lock(self):
        """Hook retries up to 3 times when lock is held."""
        content = _read_file(HOOK_FILE)
        self.assertIn('retries', content)
        self.assertIn('sleep 2', content)

    def test_hook_releases_lock_on_success(self):
        """Hook releases the merge lock after successful merge."""
        content = _read_file(HOOK_FILE)
        self.assertIn('_release_merge_lock', content)

    def test_hook_releases_lock_on_conflict(self):
        """Hook releases the merge lock even on merge conflict."""
        content = _read_file(HOOK_FILE)
        # After merge --abort, the lock must be released
        lines = content.split('\n')
        found_abort_then_release = False
        for i, line in enumerate(lines):
            if 'merge --abort' in line:
                # Check subsequent lines for lock release
                for j in range(i + 1, min(i + 10, len(lines))):
                    if '_release_merge_lock' in lines[j]:
                        found_abort_then_release = True
                        break
                break
        self.assertTrue(
            found_abort_then_release,
            'Hook must release merge lock after merge --abort')


# =============================================================================
# Additional structural tests: Safe-file auto-resolution
# =============================================================================

class TestSafeFileAutoResolution(unittest.TestCase):
    """Structural tests for safe-file auto-resolution (Requirement 2.1.5).

    Safe files (.purlin/cache/*, .purlin/delivery_plan.md) are auto-resolved
    by keeping main's version. Code/spec conflicts are presented to the user.
    """

    def test_skill_file_lists_safe_files(self):
        """Skill file identifies the safe file patterns."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('.purlin/delivery_plan.md', content)
        self.assertIn('.purlin/cache/', content)

    def test_hook_identifies_safe_files(self):
        """Hook checks conflict files against safe-file patterns."""
        content = _read_file(HOOK_FILE)
        self.assertIn('.purlin/delivery_plan.md', content)
        self.assertIn('.purlin/cache/', content)

    def test_hook_uses_checkout_ours_for_safe_files(self):
        """Hook auto-resolves safe files with checkout --ours."""
        content = _read_file(HOOK_FILE)
        self.assertIn('checkout --ours', content)

    def test_skill_file_does_not_auto_resolve_code(self):
        """Skill file states code/spec conflicts are NOT auto-resolved."""
        content = _read_file(COMMAND_FILE)
        # The skill file should mention presenting conflicts to the user
        self.assertTrue(
            'present' in content.lower() or 'resolution' in content.lower()
            or 'conflict' in content.lower(),
            'Skill file must address code/spec conflict handling')


# =============================================================================
# Additional structural tests: Breadcrumb writing on failure
# =============================================================================

class TestBreadcrumbOnFailure(unittest.TestCase):
    """Structural tests for breadcrumb writing on merge failure.

    Per Requirement 2.1 (last paragraph), on merge failure the hook writes
    a breadcrumb for recovery by the next Purlin session.
    """

    def test_hook_writes_breadcrumb_on_conflict(self):
        """Hook writes a breadcrumb JSON file when merge has conflicts."""
        content = _read_file(HOOK_FILE)
        self.assertIn('merge_pending', content)
        self.assertIn('.json', content)

    def test_hook_breadcrumb_contains_branch_info(self):
        """Hook breadcrumb includes branch and worktree path."""
        content = _read_file(HOOK_FILE)
        # The breadcrumb JSON includes branch, worktree_path, source_branch
        self.assertIn('"branch"', content)
        self.assertIn('"worktree_path"', content)
        self.assertIn('"source_branch"', content)

    def test_hook_breadcrumb_contains_reason(self):
        """Hook breadcrumb includes a reason field."""
        content = _read_file(HOOK_FILE)
        self.assertIn('"reason"', content)

    def test_hook_aborts_merge_on_unsafe_conflict(self):
        """Hook aborts the merge when conflicts involve non-safe files."""
        content = _read_file(HOOK_FILE)
        self.assertIn('merge --abort', content)

    def test_hook_displays_merge_failed_warning(self):
        """Hook displays a prominent MERGE FAILED warning on conflict."""
        content = _read_file(HOOK_FILE)
        self.assertIn('MERGE FAILED', content)


# =============================================================================
# Additional structural tests: Hook configuration
# =============================================================================

class TestHookConfiguration(unittest.TestCase):
    """Structural tests for hook script configuration."""

    def test_hook_is_bash_script(self):
        """Hook file starts with a bash shebang."""
        content = _read_file(HOOK_FILE)
        self.assertTrue(
            content.startswith('#!/bin/bash'),
            'Hook must start with #!/bin/bash')

    def test_hook_does_not_use_set_e(self):
        """Hook does NOT use set -e (must complete all steps)."""
        content = _read_file(HOOK_FILE)
        # The hook explicitly avoids set -e
        self.assertNotIn('set -e\n', content)
        self.assertIn('Do NOT use set -e', content)

    def test_hook_always_exits_zero(self):
        """Hook always exits 0 to avoid blocking agent exit."""
        content = _read_file(HOOK_FILE)
        # The last line should be exit 0
        lines = [l.strip() for l in content.strip().split('\n') if l.strip()]
        self.assertEqual(
            lines[-1], 'exit 0',
            'Hook must end with exit 0')

    def test_hook_commits_pending_work(self):
        """Hook auto-commits uncommitted changes before merge."""
        content = _read_file(HOOK_FILE)
        self.assertIn('auto-commit on session exit', content)

    def test_skill_file_is_shared_mode(self):
        """Skill file declares shared mode (usable by all roles)."""
        content = _read_file(COMMAND_FILE)
        self.assertIn('shared', content.lower())


# =============================================================================
# Test runner: writes results to tests/pl_merge/tests.json
# =============================================================================
if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    results = {
        "status": "FAIL" if failed else "PASS",
        "passed": passed,
        "failed": failed,
        "total": result.testsRun
    }
    results_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\ntests.json: {results['status']}")
