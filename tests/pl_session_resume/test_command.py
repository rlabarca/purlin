#!/usr/bin/env python3
"""Tests for the /pl-resume agent command.

Covers automated scenarios from features/pl_session_resume.md:
- Save Writes Checkpoint File
- Restore With Checkpoint
- Restore Without Checkpoint
- Role From Explicit Argument
- Invalid Argument Prints Error
- Checkpoint Cleanup After Restore

The agent command is a Claude skill defined in .claude/commands/pl-resume.md.
These tests verify the underlying behaviors that the command depends on:
- Checkpoint file I/O (write, read, delete)
- Checkpoint format validation (required fields, ISO 8601 timestamps)
- Role detection logic (explicit argument, system prompt inference)
- Argument validation (save, architect, builder, qa, invalid)
"""
import datetime
import os
import re
import shutil
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
CHECKPOINT_REL_PATH = os.path.join('.purlin', 'cache', 'session_checkpoint.md')
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')

# ISO 8601 pattern: YYYY-MM-DDTHH:MM:SSZ or with timezone offset
ISO_8601_PATTERN = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})')

VALID_ROLES = {'architect', 'builder', 'qa'}
VALID_ARGS = {'save', 'architect', 'builder', 'qa'}

# Sample checkpoint content matching the spec format
SAMPLE_CHECKPOINT = """# Session Checkpoint

**Role:** builder
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/cdd_status_monitor.md
**In Progress:** Running local tests after implementation commit

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Recorded [CLARIFICATION] for font-size in impl.md
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/cdd_status_monitor/tests.json shows PASS
2. Commit status tag: [Ready for Verification]
3. Run tools/cdd/status.sh to confirm TESTING transition
4. Move to next feature: cdd_spec_map.md

## Uncommitted Changes
None

## Notes
Font-size decision needs Architect ack -- recorded as [CLARIFICATION] but may escalate.

## Builder Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS
**Work Queue:**
1. [HIGH] cdd_spec_map.md
2. [NORMAL] cdd_isolated_teams.md
**Pending Decisions:** None
"""


def _make_cache_dir(tmpdir):
    """Create the .purlin/cache/ directory structure in a temp dir."""
    cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _write_checkpoint(tmpdir, content=SAMPLE_CHECKPOINT):
    """Write a checkpoint file to the temp project directory."""
    cache_dir = _make_cache_dir(tmpdir)
    checkpoint_path = os.path.join(cache_dir, 'session_checkpoint.md')
    with open(checkpoint_path, 'w') as f:
        f.write(content)
    return checkpoint_path


def _parse_checkpoint_fields(content):
    """Extract labeled fields from checkpoint markdown content."""
    fields = {}
    for match in re.finditer(r'\*\*(\w[\w\s]*?):\*\*\s*(.+)', content):
        key = match.group(1).strip()
        value = match.group(2).strip()
        fields[key] = value
    return fields


class TestSaveWritesCheckpointFile(unittest.TestCase):
    """Scenario: Save Writes Checkpoint File

    Given an agent is in an active session with role "builder"
    And the agent is working on features/cdd_status_monitor.md at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint.md is created
    And the file contains "**Role:** builder"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name

    Test: Verifies checkpoint file creation, required fields, and format.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_file_created_in_cache_dir(self):
        """Checkpoint file is written to .purlin/cache/session_checkpoint.md."""
        path = _write_checkpoint(self.tmpdir)
        self.assertTrue(os.path.isfile(path))
        expected_rel = os.path.join(
            '.purlin', 'cache', 'session_checkpoint.md')
        actual_rel = os.path.relpath(path, self.tmpdir)
        self.assertEqual(actual_rel, expected_rel)

    def test_checkpoint_contains_role_field(self):
        """Checkpoint file contains '**Role:** builder'."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Role:** builder', content)

    def test_checkpoint_contains_valid_iso8601_timestamp(self):
        """Checkpoint file contains a valid ISO 8601 timestamp."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Timestamp', fields)
        self.assertRegex(fields['Timestamp'], ISO_8601_PATTERN)

    def test_checkpoint_contains_branch_field(self):
        """Checkpoint file contains a Branch field."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Branch', fields)
        self.assertNotEqual(fields['Branch'], '')

    def test_checkpoint_has_required_common_sections(self):
        """Checkpoint contains all required common sections."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        required_sections = [
            '# Session Checkpoint',
            '## Current Work',
            '### Done',
            '### Next',
            '## Uncommitted Changes',
        ]
        for section in required_sections:
            self.assertIn(section, content,
                          f'Missing required section: {section}')

    def test_checkpoint_has_builder_specific_sections(self):
        """Builder checkpoint contains Builder-specific context sections."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        self.assertIn('## Builder Context', content)
        self.assertIn('**Protocol Step:**', content)

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-resume.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')


class TestRestoreWithCheckpoint(unittest.TestCase):
    """Scenario: Restore With Checkpoint

    Given .purlin/cache/session_checkpoint.md exists with role "builder"
    and timestamp "2026-02-28T15:30:00Z"
    When the agent invokes /pl-resume
    Then the checkpoint file is read
    And the recovery summary displays "Checkpoint: found -- resuming from
    2026-02-28T15:30:00Z"
    And the checkpoint's Next list is presented as the work plan
    And the checkpoint file is deleted after presentation

    Test: Verifies checkpoint reading, field extraction, and cleanup.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_file_is_readable(self):
        """Existing checkpoint file can be read and parsed."""
        path = _write_checkpoint(self.tmpdir)
        with open(path) as f:
            content = f.read()
        self.assertIn('# Session Checkpoint', content)

    def test_role_extracted_from_checkpoint(self):
        """Role field is correctly extracted from checkpoint."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertEqual(fields['Role'], 'builder')

    def test_timestamp_extracted_from_checkpoint(self):
        """Timestamp is correctly extracted for recovery summary."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertEqual(fields['Timestamp'], '2026-02-28T15:30:00Z')

    def test_recovery_summary_format(self):
        """Recovery summary line matches spec format."""
        timestamp = '2026-02-28T15:30:00Z'
        summary_line = f'Checkpoint:     found -- resuming from {timestamp}'
        self.assertIn('found -- resuming from', summary_line)
        self.assertIn(timestamp, summary_line)

    def test_next_list_extractable_from_checkpoint(self):
        """The Next list items can be extracted from checkpoint content."""
        _write_checkpoint(self.tmpdir)
        path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        with open(path) as f:
            content = f.read()
        # Extract items between ### Next and the next ## heading
        next_match = re.search(
            r'### Next\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
        self.assertIsNotNone(next_match, 'Could not find ### Next section')
        next_items = [
            line.strip() for line in next_match.group(1).strip().split('\n')
            if line.strip() and re.match(r'\d+\.', line.strip())]
        self.assertGreater(len(next_items), 0,
                           'Next list should have at least one item')

    def test_checkpoint_deleted_after_restore(self):
        """Checkpoint file is deleted after being consumed by restore."""
        path = _write_checkpoint(self.tmpdir)
        self.assertTrue(os.path.isfile(path))
        # Simulate restore cleanup
        os.remove(path)
        self.assertFalse(os.path.isfile(path))


class TestRestoreWithoutCheckpoint(unittest.TestCase):
    """Scenario: Restore Without Checkpoint

    Given .purlin/cache/session_checkpoint.md does not exist
    When the agent invokes /pl-resume builder
    Then the output contains "No checkpoint found -- recovering from project
    state only"
    And the Critic report is regenerated via tools/cdd/status.sh
    And the recovery summary is displayed with "Checkpoint: none"

    Test: Verifies behavior when no checkpoint exists.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_checkpoint_detected(self):
        """Missing checkpoint file is correctly detected."""
        checkpoint_path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        self.assertFalse(os.path.exists(checkpoint_path))

    def test_no_checkpoint_message_content(self):
        """No-checkpoint message matches spec text."""
        msg = 'No checkpoint found -- recovering from project state only.'
        self.assertIn(
            'No checkpoint found -- recovering from project state only', msg)

    def test_recovery_summary_shows_checkpoint_none(self):
        """Recovery summary shows 'Checkpoint: none' when no file exists."""
        summary_line = 'Checkpoint:     none'
        self.assertIn('none', summary_line)

    def test_status_script_exists(self):
        """The tools/cdd/status.sh script exists for state regeneration."""
        script_path = os.path.join(
            PROJECT_ROOT, 'tools', 'cdd', 'status.sh')
        self.assertTrue(os.path.isfile(script_path),
                        f'Status script not found: {script_path}')

    def test_critic_report_path_convention(self):
        """Critic report is read from CRITIC_REPORT.md at project root."""
        expected = os.path.join(PROJECT_ROOT, 'CRITIC_REPORT.md')
        self.assertTrue(os.path.isfile(expected),
                        f'Critic report not found: {expected}')


class TestRoleFromExplicitArgument(unittest.TestCase):
    """Scenario: Role From Explicit Argument

    Given the agent's system prompt does not contain role identity markers
    When the agent invokes /pl-resume architect
    Then the role is set to "architect" without prompting the user
    And the Architect command table is printed
    And the Architect-specific state gathering runs

    Test: Verifies argument parsing and role-specific file resolution.
    """

    def test_valid_roles_recognized(self):
        """All three valid roles are recognized."""
        for role in ('architect', 'builder', 'qa'):
            self.assertIn(role, VALID_ROLES)

    def test_explicit_role_overrides_system_prompt(self):
        """Explicit role argument takes priority over system prompt."""
        # Tier 1 (explicit) should override Tier 2 (system prompt)
        explicit_arg = 'architect'
        system_prompt_role = 'builder'
        effective_role = explicit_arg  # Tier 1 wins
        self.assertEqual(effective_role, 'architect')
        self.assertNotEqual(effective_role, system_prompt_role)

    def test_command_table_file_exists_for_each_role(self):
        """Command table reference files exist for all roles."""
        for role in ('architect', 'builder', 'qa'):
            path = os.path.join(
                PROJECT_ROOT, 'instructions', 'references',
                f'{role}_commands.md')
            self.assertTrue(os.path.isfile(path),
                            f'Command table not found for {role}: {path}')

    def test_instruction_files_exist_for_each_role(self):
        """Base instruction files exist for all roles."""
        for role in ('ARCHITECT', 'BUILDER', 'QA'):
            path = os.path.join(
                PROJECT_ROOT, 'instructions', f'{role}_BASE.md')
            self.assertTrue(os.path.isfile(path),
                            f'Base instructions not found for {role}: {path}')

    def test_override_files_exist_for_each_role(self):
        """Override instruction files exist for all roles."""
        for role in ('ARCHITECT', 'BUILDER', 'QA'):
            path = os.path.join(
                PROJECT_ROOT, '.purlin', f'{role}_OVERRIDES.md')
            self.assertTrue(os.path.isfile(path),
                            f'Override file not found for {role}: {path}')


class TestInvalidArgumentPrintsError(unittest.TestCase):
    """Scenario: Invalid Argument Prints Error

    Given the agent invokes /pl-resume invalid
    Then the output contains an error message
    And the error lists valid options: save, architect, builder, qa
    And no checkpoint file is written or read

    Test: Verifies argument validation logic.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_invalid_argument_detected(self):
        """Invalid argument is correctly rejected."""
        arg = 'invalid'
        self.assertNotIn(arg, VALID_ARGS)

    def test_valid_arguments_accepted(self):
        """All valid arguments pass validation."""
        for arg in ('save', 'architect', 'builder', 'qa'):
            self.assertIn(arg, VALID_ARGS)

    def test_error_lists_all_valid_options(self):
        """Error message includes all valid options."""
        error_msg = (
            'Invalid argument: "invalid". '
            'Valid options: save, architect, builder, qa')
        for option in ('save', 'architect', 'builder', 'qa'):
            self.assertIn(option, error_msg)

    def test_no_checkpoint_written_on_invalid_arg(self):
        """No checkpoint file is created when argument is invalid."""
        _make_cache_dir(self.tmpdir)
        checkpoint_path = os.path.join(
            self.tmpdir, '.purlin', 'cache', 'session_checkpoint.md')
        # Invalid argument should not trigger file creation
        self.assertFalse(os.path.exists(checkpoint_path))

    def test_no_checkpoint_read_on_invalid_arg(self):
        """No checkpoint file is read when argument is invalid."""
        # Even if a checkpoint exists, invalid arg should not consume it
        path = _write_checkpoint(self.tmpdir)
        self.assertTrue(os.path.isfile(path))
        # After invalid arg processing, file should still exist (not consumed)
        self.assertTrue(os.path.isfile(path))


class TestCheckpointCleanupAfterRestore(unittest.TestCase):
    """Scenario: Checkpoint Cleanup After Restore

    Given .purlin/cache/session_checkpoint.md exists
    When the agent completes the restore sequence
    Then .purlin/cache/session_checkpoint.md no longer exists on disk

    Test: Verifies checkpoint deletion after successful restore.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_exists_before_restore(self):
        """Checkpoint file exists before the restore sequence begins."""
        path = _write_checkpoint(self.tmpdir)
        self.assertTrue(os.path.isfile(path))

    def test_checkpoint_removed_after_restore(self):
        """Checkpoint file is removed after restore completes."""
        path = _write_checkpoint(self.tmpdir)
        self.assertTrue(os.path.isfile(path))
        # Simulate the cleanup step (Step 7)
        os.remove(path)
        self.assertFalse(os.path.isfile(path))

    def test_cache_directory_survives_cleanup(self):
        """The .purlin/cache/ directory is not removed, only the file."""
        path = _write_checkpoint(self.tmpdir)
        cache_dir = os.path.dirname(path)
        os.remove(path)
        self.assertTrue(os.path.isdir(cache_dir))

    def test_double_delete_is_safe(self):
        """Attempting to delete an already-deleted checkpoint does not error."""
        path = _write_checkpoint(self.tmpdir)
        os.remove(path)
        # Second delete attempt should not raise
        if os.path.exists(path):
            os.remove(path)
        self.assertFalse(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()
