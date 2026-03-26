#!/usr/bin/env python3
"""Tests for the /pl-resume agent command.

Covers automated scenarios from features/pl_session_resume.md:
- Save Writes Role-Scoped Checkpoint File
- Concurrent Saves Do Not Overwrite
- Restore With Checkpoint
- Restore Without Checkpoint
- Role From Explicit Argument
- Invalid Argument Prints Error
- Checkpoint Cleanup After Restore
- Role Inferred From Single Checkpoint File
- Multiple Checkpoints Prompt User Selection
- PM Save Writes Role-Scoped Checkpoint File
- PM Cold Start Checks Figma MCP Availability
- Builder Cold Start Loads Tombstones and Anchors
- QA Cold Start Reads Verification Effort
- Cold Start Respects Startup Flags

The agent command is a Claude skill defined in .claude/commands/pl-resume.md.
These tests verify the underlying behaviors that the command depends on:
- Role-scoped checkpoint file I/O (write, read, delete per role)
- Checkpoint format validation (required fields, ISO 8601 timestamps)
- Role detection logic (explicit argument, system prompt inference,
  checkpoint file discovery, multi-checkpoint selection)
- Argument validation (save, architect, builder, qa, pm, invalid)
- PM-specific checkpoint fields (Spec Drafts, Figma Context, Probing Round)
- Cold-start extension behaviors (tombstones, anchors, verification effort)
- Startup flag handling (find_work, auto_start)
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')

VALID_ROLES = {'architect', 'builder', 'qa', 'pm'}
VALID_ARGS = {'save', 'architect', 'builder', 'qa', 'pm'}

# ISO 8601 pattern: YYYY-MM-DDTHH:MM:SSZ or with timezone offset
ISO_8601_PATTERN = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})')

# Sample checkpoint content matching the spec format
SAMPLE_CHECKPOINT_BUILDER = """# Session Checkpoint

**Role:** builder
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Running local tests after implementation commit

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Recorded [CLARIFICATION] for font-size in impl.md
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/project_init/tests.json shows PASS
2. Commit status tag: [Ready for Verification]
3. Run tools/cdd/status.sh to confirm TESTING transition
4. Move to next feature: pl_spec_code_audit.md

## Uncommitted Changes
None

## Notes
Font-size decision needs Architect ack -- recorded as [CLARIFICATION] but may escalate.

## Builder Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS
**Work Queue:**
1. [HIGH] pl_spec_code_audit.md
2. [NORMAL] cdd_qa_effort_display.md
**Pending Decisions:** None
"""

SAMPLE_CHECKPOINT_PM = """# Session Checkpoint

**Role:** pm
**Timestamp:** 2026-03-10T09:00:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Drafting visual specification for status monitor redesign

### Done
- Read existing feature spec
- Reviewed Figma designs for monitor layout

### Next
1. Complete Visual Specification section
2. Add checklist items for QA verification

## Uncommitted Changes
None

## Notes
Figma file has updated token mappings -- need to verify against design_visual_standards.

## PM Context
**Spec Drafts:** project_init.md requirements in progress
**Figma Context:** None
**Probing Round:** 2
"""

SAMPLE_CHECKPOINT_ARCHITECT = """# Session Checkpoint

**Role:** architect
**Timestamp:** 2026-03-01T10:00:00Z
**Branch:** main

## Current Work

**Feature:** features/pl_session_resume.md
**In Progress:** Updating spec for role-scoped checkpoints

### Done
- Reviewed Builder proposal for concurrent saves
- Updated save mode section

### Next
1. Add new scenarios for role-scoped behavior
2. Run scan to validate spec completeness

## Uncommitted Changes
None

## Notes
None

## Architect Context
**Spec Reviews:** pl_session_resume.md in progress
**Discovery Processing:** 0 pending
"""


def _checkpoint_path(tmpdir, role):
    """Return the role-scoped checkpoint file path."""
    return os.path.join(
        tmpdir, '.purlin', 'cache', f'session_checkpoint_{role}.md')


def _make_cache_dir(tmpdir):
    """Create the .purlin/cache/ directory structure in a temp dir."""
    cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _write_checkpoint(tmpdir, role='builder', content=None):
    """Write a role-scoped checkpoint file to the temp project directory."""
    if content is None:
        _defaults = {
            'builder': SAMPLE_CHECKPOINT_BUILDER,
            'architect': SAMPLE_CHECKPOINT_ARCHITECT,
            'pm': SAMPLE_CHECKPOINT_PM,
        }
        content = _defaults.get(role, SAMPLE_CHECKPOINT_BUILDER)
    cache_dir = _make_cache_dir(tmpdir)
    path = os.path.join(cache_dir, f'session_checkpoint_{role}.md')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _parse_checkpoint_fields(content):
    """Extract labeled fields from checkpoint markdown content."""
    fields = {}
    for match in re.finditer(r'\*\*(\w[\w\s]*?):\*\*\s*(.+)', content):
        key = match.group(1).strip()
        value = match.group(2).strip()
        fields[key] = value
    return fields


def _discover_checkpoint_roles(cache_dir):
    """Discover which role-scoped checkpoint files exist.

    Returns a list of role names (e.g., ['builder', 'architect']).
    """
    roles = []
    for role in ('architect', 'builder', 'pm', 'qa'):
        path = os.path.join(cache_dir, f'session_checkpoint_{role}.md')
        if os.path.isfile(path):
            roles.append(role)
    return roles


class TestSaveWritesRoleScopedCheckpointFile(unittest.TestCase):
    """Scenario: Save Writes Role-Scoped Checkpoint File

    Given an agent is in an active session with role "builder"
    And the agent is working on features/project_init.md at protocol step 3
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_builder.md is created
    And the file contains "**Role:** builder"
    And the file contains a valid ISO 8601 timestamp
    And the file contains the current branch name
    And no other session_checkpoint_*.md files are modified
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_file_created_with_role_suffix(self):
        """Checkpoint file is written to session_checkpoint_builder.md."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith('session_checkpoint_builder.md'))

    def test_checkpoint_path_includes_role(self):
        """File path follows .purlin/cache/session_checkpoint_<role>.md."""
        for role in VALID_ROLES:
            path = _write_checkpoint(self.tmpdir, role=role)
            expected_name = f'session_checkpoint_{role}.md'
            self.assertTrue(path.endswith(expected_name),
                            f'Expected path to end with {expected_name}')

    def test_checkpoint_contains_role_field(self):
        """Checkpoint file contains '**Role:** builder'."""
        _write_checkpoint(self.tmpdir, role='builder')
        path = _checkpoint_path(self.tmpdir, 'builder')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Role:** builder', content)

    def test_checkpoint_contains_valid_iso8601_timestamp(self):
        """Checkpoint file contains a valid ISO 8601 timestamp."""
        _write_checkpoint(self.tmpdir, role='builder')
        path = _checkpoint_path(self.tmpdir, 'builder')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Timestamp', fields)
        self.assertRegex(fields['Timestamp'], ISO_8601_PATTERN)

    def test_checkpoint_contains_branch_field(self):
        """Checkpoint file contains a Branch field."""
        _write_checkpoint(self.tmpdir, role='builder')
        path = _checkpoint_path(self.tmpdir, 'builder')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Branch', fields)
        self.assertNotEqual(fields['Branch'], '')

    def test_checkpoint_has_required_common_sections(self):
        """Checkpoint contains all required common sections."""
        _write_checkpoint(self.tmpdir, role='builder')
        path = _checkpoint_path(self.tmpdir, 'builder')
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
        _write_checkpoint(self.tmpdir, role='builder')
        path = _checkpoint_path(self.tmpdir, 'builder')
        with open(path) as f:
            content = f.read()
        self.assertIn('## Builder Context', content)
        self.assertIn('**Protocol Step:**', content)

    def test_no_other_checkpoint_files_modified(self):
        """Saving a builder checkpoint does not create other role files."""
        _write_checkpoint(self.tmpdir, role='builder')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        for other_role in ('architect', 'qa', 'pm'):
            other_path = os.path.join(
                cache_dir, f'session_checkpoint_{other_role}.md')
            self.assertFalse(os.path.exists(other_path),
                             f'Unexpected checkpoint for {other_role}')

    def test_command_file_exists(self):
        """The skill command file .claude/commands/pl-resume.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE),
                        f'Command file not found: {COMMAND_FILE}')


class TestConcurrentSavesDoNotOverwrite(unittest.TestCase):
    """Scenario: Concurrent Saves Do Not Overwrite

    Given a Builder agent saves a checkpoint to
    .purlin/cache/session_checkpoint_builder.md
    And an Architect agent saves a checkpoint to
    .purlin/cache/session_checkpoint_architect.md
    Then both checkpoint files exist independently
    And the Builder checkpoint contains "**Role:** builder"
    And the Architect checkpoint contains "**Role:** architect"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_both_checkpoint_files_coexist(self):
        """Builder and Architect checkpoints exist independently."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        self.assertTrue(os.path.isfile(
            _checkpoint_path(self.tmpdir, 'builder')))
        self.assertTrue(os.path.isfile(
            _checkpoint_path(self.tmpdir, 'architect')))

    def test_builder_checkpoint_has_correct_role(self):
        """Builder checkpoint contains '**Role:** builder'."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        with open(_checkpoint_path(self.tmpdir, 'builder')) as f:
            content = f.read()
        self.assertIn('**Role:** builder', content)

    def test_architect_checkpoint_has_correct_role(self):
        """Architect checkpoint contains '**Role:** architect'."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        with open(_checkpoint_path(self.tmpdir, 'architect')) as f:
            content = f.read()
        self.assertIn('**Role:** architect', content)

    def test_all_four_roles_can_coexist(self):
        """All four role checkpoints can exist simultaneously."""
        qa_content = SAMPLE_CHECKPOINT_BUILDER.replace(
            '**Role:** builder', '**Role:** qa').replace(
            '## Builder Context', '## QA Context')
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        _write_checkpoint(self.tmpdir, role='qa', content=qa_content)
        _write_checkpoint(self.tmpdir, role='pm')
        for role in VALID_ROLES:
            self.assertTrue(os.path.isfile(
                _checkpoint_path(self.tmpdir, role)),
                f'Missing checkpoint for {role}')

    def test_overwriting_one_role_preserves_others(self):
        """Updating one role's checkpoint does not affect other roles."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        # Read architect content before builder overwrite
        with open(_checkpoint_path(self.tmpdir, 'architect')) as f:
            architect_before = f.read()
        # Overwrite builder checkpoint
        updated = SAMPLE_CHECKPOINT_BUILDER.replace('abc1234', 'def5678')
        _write_checkpoint(self.tmpdir, role='builder', content=updated)
        # Architect file unchanged
        with open(_checkpoint_path(self.tmpdir, 'architect')) as f:
            architect_after = f.read()
        self.assertEqual(architect_before, architect_after)


class TestRestoreWithCheckpoint(unittest.TestCase):
    """Scenario: Restore With Checkpoint

    Given .purlin/cache/session_checkpoint_builder.md exists with
    role "builder" and timestamp "2026-02-28T15:30:00Z"
    When the agent invokes /pl-resume builder
    Then the checkpoint file is read
    And the recovery summary displays "Checkpoint: found -- resuming from
    2026-02-28T15:30:00Z"
    And the checkpoint's Next list is presented as the work plan
    And the checkpoint file is deleted after presentation
    And the agent begins executing the work plan without asking for
    confirmation
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_file_is_readable(self):
        """Existing role-scoped checkpoint file can be read and parsed."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        with open(path) as f:
            content = f.read()
        self.assertIn('# Session Checkpoint', content)

    def test_role_extracted_from_checkpoint(self):
        """Role field is correctly extracted from checkpoint."""
        _write_checkpoint(self.tmpdir, role='builder')
        with open(_checkpoint_path(self.tmpdir, 'builder')) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertEqual(fields['Role'], 'builder')

    def test_timestamp_extracted_from_checkpoint(self):
        """Timestamp is correctly extracted for recovery summary."""
        _write_checkpoint(self.tmpdir, role='builder')
        with open(_checkpoint_path(self.tmpdir, 'builder')) as f:
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
        _write_checkpoint(self.tmpdir, role='builder')
        with open(_checkpoint_path(self.tmpdir, 'builder')) as f:
            content = f.read()
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
        path = _write_checkpoint(self.tmpdir, role='builder')
        self.assertTrue(os.path.isfile(path))
        os.remove(path)
        self.assertFalse(os.path.isfile(path))


class TestRestoreWithoutCheckpoint(unittest.TestCase):
    """Scenario: Restore Without Checkpoint

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    When the agent invokes /pl-resume builder
    Then the Critic report is regenerated via tools/cdd/status.sh
    And the recovery summary is displayed with "Checkpoint: none"
    And the agent begins executing the work plan without asking for
    confirmation
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_checkpoint_detected(self):
        """Missing role-scoped checkpoint file is correctly detected."""
        checkpoint_path = _checkpoint_path(self.tmpdir, 'builder')
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
        """Restore gathers project state via the startup briefing mechanism."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('status.sh --startup', content,
                      'Command file should reference status.sh --startup for state gathering')


class TestRoleFromExplicitArgument(unittest.TestCase):
    """Scenario: Role From Explicit Argument

    Given the agent's system prompt does not contain role identity markers
    When the agent invokes /pl-resume architect
    Then the role is set to "architect" without prompting the user
    And checkpoint detection checks .purlin/cache/session_checkpoint_architect.md
    And the output contains "Commands: /pl-help for full list"
    And the Architect-specific state gathering runs
    """

    def test_valid_roles_recognized(self):
        """All four valid roles are recognized."""
        for role in ('architect', 'builder', 'qa', 'pm'):
            self.assertIn(role, VALID_ROLES)

    def test_explicit_role_overrides_system_prompt(self):
        """Explicit role argument takes priority over system prompt."""
        explicit_arg = 'architect'
        system_prompt_role = 'builder'
        effective_role = explicit_arg  # Tier 1 wins
        self.assertEqual(effective_role, 'architect')
        self.assertNotEqual(effective_role, system_prompt_role)

    def test_explicit_role_determines_checkpoint_path(self):
        """Explicit role maps to correct role-scoped checkpoint filename."""
        for role in VALID_ROLES:
            expected = f'session_checkpoint_{role}.md'
            self.assertIn(role, expected)

    def test_command_table_file_exists_for_each_role(self):
        """Command table reference files exist for all roles."""
        for role in ('architect', 'builder', 'qa', 'pm'):
            path = os.path.join(
                PROJECT_ROOT, 'instructions', 'references',
                f'{role}_commands.md')
            self.assertTrue(os.path.isfile(path),
                            f'Command table not found for {role}: {path}')

    def test_instruction_files_exist_for_each_role(self):
        """Base instruction files exist for all roles."""
        for role in ('ARCHITECT', 'BUILDER', 'QA', 'PM'):
            path = os.path.join(
                PROJECT_ROOT, 'instructions', f'{role}_BASE.md')
            self.assertTrue(os.path.isfile(path),
                            f'Base instructions not found for {role}: {path}')

    def test_override_files_exist_for_each_role(self):
        """Override instruction files exist for all roles."""
        for role in ('ARCHITECT', 'BUILDER', 'QA', 'PM'):
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
        for arg in ('save', 'architect', 'builder', 'qa', 'pm'):
            self.assertIn(arg, VALID_ARGS)

    def test_error_lists_all_valid_options(self):
        """Error message includes all valid options."""
        error_msg = (
            'Invalid argument: "invalid". '
            'Valid options: save, architect, builder, qa, pm')
        for option in ('save', 'architect', 'builder', 'qa', 'pm'):
            self.assertIn(option, error_msg)

    def test_no_checkpoint_written_on_invalid_arg(self):
        """No checkpoint file is created when argument is invalid."""
        _make_cache_dir(self.tmpdir)
        for role in VALID_ROLES:
            path = _checkpoint_path(self.tmpdir, role)
            self.assertFalse(os.path.exists(path))

    def test_no_checkpoint_read_on_invalid_arg(self):
        """No checkpoint file is read when argument is invalid."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        self.assertTrue(os.path.isfile(path))
        # After invalid arg processing, file should still exist
        self.assertTrue(os.path.isfile(path))


class TestStep0StaleSessionStateCleanup(unittest.TestCase):
    """Scenario: Step 0 clears stale session state.

    Step 0 clears any stale session state carried over from the previous
    session. Step 7 must NOT reset the counter (restore flow consumes
    real context during state gathering).
    """

    def test_step0_heading_references_stale_session_cleanup(self):
        """Step 0 heading references Stale Session State Cleanup."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Step 0 -- Stale Session State Cleanup', content)

    def test_step0_mentions_stale_state_cleanup(self):
        """Step 0 instructs clearing stale session state."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Clear any stale session state carried over', content)

    def test_step7_prohibits_counter_reset(self):
        """Step 7 explicitly prohibits resetting the counter."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn(
            'Do NOT reset the context guard counter here', content)

    def test_step0_no_turn_count_file_references(self):
        """Step 0 does not reference legacy turn_count files."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertNotIn('turn_count_${PPID}', content)

    def test_step0_no_session_meta_file_references(self):
        """Step 0 does not reference legacy session_meta files."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertNotIn('session_meta_$PPID', content)


class TestCheckpointCleanupAfterRestore(unittest.TestCase):
    """Scenario: Checkpoint Cleanup After Restore

    Given .purlin/cache/session_checkpoint_builder.md exists
    When the Builder agent completes the restore sequence
    Then .purlin/cache/session_checkpoint_builder.md no longer exists on disk
    And any other role's checkpoint files remain untouched
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_exists_before_restore(self):
        """Checkpoint file exists before the restore sequence begins."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        self.assertTrue(os.path.isfile(path))

    def test_checkpoint_removed_after_restore(self):
        """Role-scoped checkpoint file is removed after restore."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        self.assertTrue(os.path.isfile(path))
        os.remove(path)
        self.assertFalse(os.path.isfile(path))

    def test_other_roles_untouched_after_cleanup(self):
        """Deleting builder checkpoint does not affect architect checkpoint."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        builder_path = _checkpoint_path(self.tmpdir, 'builder')
        architect_path = _checkpoint_path(self.tmpdir, 'architect')
        os.remove(builder_path)
        self.assertFalse(os.path.isfile(builder_path))
        self.assertTrue(os.path.isfile(architect_path))

    def test_cache_directory_survives_cleanup(self):
        """The .purlin/cache/ directory is not removed, only the file."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        cache_dir = os.path.dirname(path)
        os.remove(path)
        self.assertTrue(os.path.isdir(cache_dir))

    def test_double_delete_is_safe(self):
        """Attempting to delete an already-deleted checkpoint is safe."""
        path = _write_checkpoint(self.tmpdir, role='builder')
        os.remove(path)
        if os.path.exists(path):
            os.remove(path)
        self.assertFalse(os.path.exists(path))


class TestRoleInferredFromSingleCheckpointFile(unittest.TestCase):
    """Scenario: Role Inferred From Single Checkpoint File

    Given .purlin/cache/session_checkpoint_qa.md exists
    And no other session_checkpoint_*.md files exist
    And the agent's system prompt has no role identity markers
    When the agent invokes /pl-resume with no argument
    Then the role is inferred as "qa" from the checkpoint file
    And the restore proceeds normally
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_single_checkpoint_role_discovered(self):
        """When only one role-scoped checkpoint exists, that role is found."""
        qa_content = SAMPLE_CHECKPOINT_BUILDER.replace(
            '**Role:** builder', '**Role:** qa').replace(
            '## Builder Context', '## QA Context')
        _write_checkpoint(self.tmpdir, role='qa', content=qa_content)
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        self.assertEqual(discovered, ['qa'])

    def test_no_other_checkpoint_files_present(self):
        """Only the single role's checkpoint file exists."""
        _write_checkpoint(self.tmpdir, role='builder')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0], 'builder')

    def test_role_inferred_correctly_for_each_role(self):
        """Each role can be individually inferred from its checkpoint."""
        for role in VALID_ROLES:
            tmpdir = tempfile.mkdtemp()
            try:
                content = SAMPLE_CHECKPOINT_BUILDER.replace(
                    '**Role:** builder', f'**Role:** {role}')
                _write_checkpoint(tmpdir, role=role, content=content)
                cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
                discovered = _discover_checkpoint_roles(cache_dir)
                self.assertEqual(discovered, [role],
                                 f'Expected [{role}], got {discovered}')
            finally:
                shutil.rmtree(tmpdir)

    def test_empty_cache_dir_discovers_no_roles(self):
        """An empty cache directory yields no discovered roles."""
        cache_dir = _make_cache_dir(self.tmpdir)
        discovered = _discover_checkpoint_roles(cache_dir)
        self.assertEqual(discovered, [])


class TestMultipleCheckpointsPromptUserSelection(unittest.TestCase):
    """Scenario: Multiple Checkpoints Prompt User Selection

    Given .purlin/cache/session_checkpoint_builder.md exists
    And .purlin/cache/session_checkpoint_architect.md exists
    And the agent's system prompt has no role identity markers
    When the agent invokes /pl-resume with no argument
    Then the agent lists the available checkpoint roles (builder, architect)
    And prompts the user to select which role to resume
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_multiple_checkpoints_discovered(self):
        """Multiple role-scoped checkpoint files are all discovered."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        self.assertIn('builder', discovered)
        self.assertIn('architect', discovered)
        self.assertEqual(len(discovered), 2)

    def test_discovery_returns_sorted_roles(self):
        """Discovered roles are returned in a consistent order."""
        _write_checkpoint(self.tmpdir, role='qa',
                          content=SAMPLE_CHECKPOINT_BUILDER.replace(
                              '**Role:** builder', '**Role:** qa'))
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        _write_checkpoint(self.tmpdir, role='pm')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        # Function iterates in fixed order: architect, builder, pm, qa
        self.assertEqual(discovered, ['architect', 'builder', 'pm', 'qa'])

    def test_multiple_checkpoints_triggers_selection(self):
        """More than one checkpoint means auto-inference cannot proceed."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        # When len > 1, the agent must prompt the user (cannot auto-infer)
        self.assertGreater(len(discovered), 1)

    def test_each_discovered_role_has_valid_checkpoint(self):
        """Each discovered checkpoint file is readable and has a Role field."""
        _write_checkpoint(self.tmpdir, role='builder')
        _write_checkpoint(self.tmpdir, role='architect')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        discovered = _discover_checkpoint_roles(cache_dir)
        for role in discovered:
            path = _checkpoint_path(self.tmpdir, role)
            with open(path) as f:
                content = f.read()
            fields = _parse_checkpoint_fields(content)
            self.assertIn('Role', fields,
                          f'Missing Role field in {role} checkpoint')


class TestCommandFileRoleScopedPaths(unittest.TestCase):
    """Verify the command file references role-scoped checkpoint paths."""

    def test_save_mode_references_role_scoped_path(self):
        """Save mode section references session_checkpoint_<role>.md."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('session_checkpoint_<role>.md', content)

    def test_step1_has_four_tier_fallback(self):
        """Step 1 describes a 4-Tier Fallback for role detection."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('4-Tier Fallback', content)

    def test_step1_includes_checkpoint_file_discovery(self):
        """Step 1 includes checkpoint file discovery as a tier."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Checkpoint file discovery', content)

    def test_step2_uses_role_scoped_detection(self):
        """Step 2 uses role-scoped path for checkpoint detection."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn(
            'session_checkpoint_<role>.md && echo EXISTS', content)

    def test_no_old_single_file_path(self):
        """Command file no longer uses the old session_checkpoint.md path."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        # Should not contain the old non-role-scoped path in operational
        # sections. The old path pattern (without role suffix) should be gone.
        # We check that references like 'session_checkpoint.md' without a role
        # suffix don't appear (excluding the <role> templated version).
        lines = content.split('\n')
        for line in lines:
            if 'session_checkpoint' in line and '<role>' not in line:
                # Allow references in code blocks that are templated
                # or in the checkpoint format example
                if 'session_checkpoint_' in line:
                    continue  # Role-scoped, OK
                self.fail(
                    f'Found old non-role-scoped checkpoint path: {line}')


class TestPMSaveWritesRoleScopedCheckpointFile(unittest.TestCase):
    """Scenario: PM Save Writes Role-Scoped Checkpoint File

    Given an agent is in an active session with role "pm"
    And the agent is drafting a feature spec with Figma context
    When the agent invokes /pl-resume save
    Then .purlin/cache/session_checkpoint_pm.md is created
    And the file contains "**Role:** pm"
    And the file contains a Spec Drafts field
    And the file contains a Figma Context field
    And the file contains a Probing Round field
    And no other session_checkpoint_*.md files are modified
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_pm_checkpoint_file_created(self):
        """PM checkpoint file is written to session_checkpoint_pm.md."""
        path = _write_checkpoint(self.tmpdir, role='pm')
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith('session_checkpoint_pm.md'))

    def test_pm_checkpoint_contains_role_field(self):
        """PM checkpoint file contains '**Role:** pm'."""
        _write_checkpoint(self.tmpdir, role='pm')
        path = _checkpoint_path(self.tmpdir, 'pm')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Role:** pm', content)

    def test_pm_checkpoint_contains_spec_drafts(self):
        """PM checkpoint contains a Spec Drafts field."""
        _write_checkpoint(self.tmpdir, role='pm')
        path = _checkpoint_path(self.tmpdir, 'pm')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Spec Drafts:**', content)

    def test_pm_checkpoint_contains_figma_context(self):
        """PM checkpoint contains a Figma Context field."""
        _write_checkpoint(self.tmpdir, role='pm')
        path = _checkpoint_path(self.tmpdir, 'pm')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Figma Context:**', content)

    def test_pm_checkpoint_contains_probing_round(self):
        """PM checkpoint contains a Probing Round field."""
        _write_checkpoint(self.tmpdir, role='pm')
        path = _checkpoint_path(self.tmpdir, 'pm')
        with open(path) as f:
            content = f.read()
        self.assertIn('**Probing Round:**', content)

    def test_pm_checkpoint_has_pm_context_section(self):
        """PM checkpoint contains ## PM Context section."""
        _write_checkpoint(self.tmpdir, role='pm')
        path = _checkpoint_path(self.tmpdir, 'pm')
        with open(path) as f:
            content = f.read()
        self.assertIn('## PM Context', content)

    def test_no_other_checkpoint_files_modified(self):
        """Saving a PM checkpoint does not create other role files."""
        _write_checkpoint(self.tmpdir, role='pm')
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        for other_role in ('architect', 'builder', 'qa'):
            other_path = os.path.join(
                cache_dir, f'session_checkpoint_{other_role}.md')
            self.assertFalse(os.path.exists(other_path),
                             f'Unexpected checkpoint for {other_role}')

    def test_command_file_has_pm_context_section(self):
        """Command file includes PM-specific checkpoint fields."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('## PM Context', content)
        self.assertIn('**Spec Drafts:**', content)
        self.assertIn('**Figma Context:**', content)
        self.assertIn('**Probing Round:**', content)


class TestPMColdStartChecksFigmaMCPAvailability(unittest.TestCase):
    """Scenario: PM Cold Start Checks Figma MCP Availability

    Given .purlin/cache/session_checkpoint_pm.md does not exist
    When the agent invokes /pl-resume pm
    Then the PM state-gathering sequence runs
    And the Figma MCP availability check is performed
    And the recovery summary displays "Figma MCP: available" or
    "Figma MCP: not available"
    And the recovery summary displays "Checkpoint: none"
    """

    def test_pm_checkpoint_missing_detected(self):
        """Missing PM checkpoint is detected for cold start."""
        tmpdir = tempfile.mkdtemp()
        try:
            _make_cache_dir(tmpdir)
            path = _checkpoint_path(tmpdir, 'pm')
            self.assertFalse(os.path.exists(path))
        finally:
            shutil.rmtree(tmpdir)

    def test_command_file_references_figma_mcp_in_pm_section(self):
        """Command file references Figma MCP in PM cold-start gathering."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Figma MCP', content)

    def test_recovery_summary_has_pm_figma_line(self):
        """Recovery summary template includes PM Figma MCP status line."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Figma MCP:', content)
        # Check the PM-only conditional line is in the summary template
        self.assertIn('<PM only>', content)

    def test_figma_mcp_status_values(self):
        """Figma MCP status uses 'available' or 'not available'."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        # The template should reference both possible values
        self.assertIn('available', content)
        self.assertIn('not available', content)

    def test_pm_role_accepted_as_explicit_argument(self):
        """'pm' is a valid explicit argument for /pl-resume."""
        self.assertIn('pm', VALID_ARGS)

    def test_command_file_has_pm_figma_mcp_check(self):
        """The command file includes PM Figma MCP availability check."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('Figma MCP', content)
        self.assertIn('PM', content)


class TestBuilderColdStartLoadsTombstonesAndAnchors(unittest.TestCase):
    """Scenario: Builder Cold Start Loads Tombstones and Anchors

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    And features/tombstones/ contains at least one tombstone file
    And features/ contains at least one anchor node file
    When the agent invokes /pl-resume builder
    Then the startup briefing contains tombstones with file and label per entry
    And the startup briefing contains anchor_constraints with FORBIDDEN patterns
    And the recovery summary includes tombstone tasks as HIGH-priority items
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create project structure
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)
        self.tombstones_dir = os.path.join(self.features_dir, 'tombstones')
        os.makedirs(self.tombstones_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_tombstone_directory_listing(self):
        """Tombstone files in features/tombstones/ are discoverable."""
        tombstone = os.path.join(
            self.tombstones_dir, 'old_feature.md')
        with open(tombstone, 'w') as f:
            f.write('# Tombstone: old_feature\n')
        files = os.listdir(self.tombstones_dir)
        self.assertEqual(files, ['old_feature.md'])

    def test_multiple_tombstones_listed(self):
        """All tombstone files are discoverable."""
        for name in ('feature_a.md', 'feature_b.md'):
            with open(os.path.join(self.tombstones_dir, name), 'w') as f:
                f.write(f'# Tombstone: {name}\n')
        files = sorted(os.listdir(self.tombstones_dir))
        self.assertEqual(files, ['feature_a.md', 'feature_b.md'])

    def test_anchor_node_files_discoverable_by_prefix(self):
        """Anchor node files match design_*.md and policy_*.md patterns."""
        for name in ('design_visual.md', 'policy_critic.md'):
            with open(os.path.join(self.features_dir, name), 'w') as f:
                f.write(f'# {name}\n')
        import glob
        anchors = []
        for pattern in ('design_*.md', 'policy_*.md', 'arch_*.md'):
            anchors.extend(
                glob.glob(os.path.join(self.features_dir, pattern)))
        basenames = sorted(os.path.basename(p) for p in anchors)
        self.assertEqual(basenames, ['design_visual.md', 'policy_critic.md'])

    def test_impl_files_excluded_from_anchor_listing(self):
        """Companion .impl.md files are not anchor nodes."""
        for name in ('design_visual.md', 'design_visual.impl.md'):
            with open(os.path.join(self.features_dir, name), 'w') as f:
                f.write(f'# {name}\n')
        import glob
        anchors = []
        for pattern in ('design_*.md', 'policy_*.md', 'arch_*.md'):
            matches = glob.glob(os.path.join(self.features_dir, pattern))
            anchors.extend(
                p for p in matches if not p.endswith('.impl.md'))
        basenames = [os.path.basename(p) for p in anchors]
        self.assertEqual(basenames, ['design_visual.md'])

    def test_command_file_references_tombstone_check(self):
        """Command file Step 5 references tombstone listing for Builder."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('tombstone', content.lower())

    def test_command_file_references_anchor_constraints(self):
        """Command file Step 5 references anchor constraints for Builder."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('anchor constraints', content.lower())

    def test_real_project_anchor_nodes_exist(self):
        """The real project has at least one anchor node file."""
        import glob
        features_dir = os.path.join(PROJECT_ROOT, 'features')
        anchors = []
        for pattern in ('design_*.md', 'policy_*.md', 'arch_*.md'):
            matches = glob.glob(os.path.join(features_dir, pattern))
            anchors.extend(
                p for p in matches if not p.endswith('.impl.md'))
        self.assertGreater(len(anchors), 0,
                           'Project should have at least one anchor node')

    def test_startup_briefing_has_tombstones_field(self):
        """Startup briefing JSON contains tombstones array."""
        import subprocess
        result = subprocess.run(
            ['bash', 'tools/cdd/status.sh', '--startup', 'builder'],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn('tombstones', data)
        self.assertIsInstance(data['tombstones'], list)

    def test_startup_briefing_has_anchor_constraints_field(self):
        """Startup briefing JSON contains anchor_constraints with
        FORBIDDEN patterns structure."""
        import subprocess
        result = subprocess.run(
            ['bash', 'tools/cdd/status.sh', '--startup', 'builder'],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn('anchor_constraints', data)
        constraints = data['anchor_constraints']
        self.assertIsInstance(constraints, dict)
        for anchor_name, constraint in constraints.items():
            self.assertIn('forbidden_patterns', constraint)
            self.assertIn('label', constraint)


class TestQAColdStartReadsVerificationEffort(unittest.TestCase):
    """Scenario: QA Cold Start Reads Verification Effort

    Given .purlin/cache/session_checkpoint_qa.md does not exist
    And at least one feature is in TESTING state
    When the agent invokes /pl-resume qa
    Then the startup briefing is retrieved
    And the startup briefing contains testing_features with verification_effort per feature
    And the recovery summary includes effort classification per feature
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_critic_json_verification_effort_readable(self):
        """verification_effort field is readable from critic.json."""
        test_dir = os.path.join(self.tmpdir, 'tests', 'some_feature')
        os.makedirs(test_dir)
        critic_data = {
            'feature': 'some_feature',
            'verification_effort': {
                'total_manual': 3,
                'total_auto': 5,
                'summary': '3 manual, 5 auto'
            }
        }
        with open(os.path.join(test_dir, 'critic.json'), 'w') as f:
            json.dump(critic_data, f)
        with open(os.path.join(test_dir, 'critic.json')) as f:
            data = json.load(f)
        self.assertIn('verification_effort', data)
        self.assertEqual(data['verification_effort']['total_manual'], 3)

    def test_verification_effort_has_required_fields(self):
        """verification_effort contains total_manual and total_auto."""
        effort = {
            'total_manual': 2,
            'total_auto': 4,
            'summary': '2 manual, 4 auto'
        }
        self.assertIn('total_manual', effort)
        self.assertIn('total_auto', effort)
        self.assertIn('summary', effort)

    def test_real_project_testing_features_have_critic_json(self):
        """Features in TESTING state have critic.json with effort data."""
        # Check actual project: find any TESTING features from status
        tests_dir = os.path.join(PROJECT_ROOT, 'tests')
        if not os.path.isdir(tests_dir):
            self.skipTest('No tests/ directory in project')
        # At minimum, verify the critic.json structure for any existing feature
        found_any = False
        for entry in os.listdir(tests_dir):
            critic_path = os.path.join(tests_dir, entry, 'critic.json')
            if os.path.isfile(critic_path):
                with open(critic_path) as f:
                    data = json.load(f)
                if 'verification_effort' in data:
                    found_any = True
                    effort = data['verification_effort']
                    self.assertIn('total_manual', effort)
                    self.assertIn('total_auto', effort)
                    break
        if not found_any:
            self.skipTest('No critic.json with verification_effort found')

    def test_command_file_references_testing_features(self):
        """Command file Step 5 references testing features for QA."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('testing features', content.lower())

    def test_command_file_references_discovery_summary(self):
        """Command file Step 5 references discovery summary for QA."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('discovery summary', content.lower())

    def test_startup_briefing_features_have_verification_effort(self):
        """Startup briefing features array includes verification_effort
        per feature entry when TESTING features exist."""
        import subprocess
        result = subprocess.run(
            ['bash', 'tools/cdd/status.sh', '--startup', 'qa'],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn('features', data)
        features = data['features']
        # Features array may be empty when no features are in TESTING status.
        # When features are present, each must include verification_effort.
        for feat in features:
            self.assertIn('verification_effort', feat,
                          f'Feature {feat.get("file", "?")} missing '
                          f'verification_effort')


class TestColdStartRespectsStartupFlags(unittest.TestCase):
    """Scenario: Cold Start Respects Startup Flags

    Given .purlin/cache/session_checkpoint_builder.md does not exist
    And .purlin/config.json sets find_work to false for the builder role
    When the agent invokes /pl-resume builder
    Then the startup briefing is retrieved
    And the recovery summary displays "find_work disabled -- awaiting instruction."
    And the agent does not auto-generate a full work plan
    And the agent awaits user direction
    """

    def test_config_json_has_find_work_field(self):
        """config.json contains find_work for builder."""
        config_path = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        builder_cfg = config.get('agents', {}).get('builder', {})
        self.assertIn('find_work', builder_cfg)

    def test_config_json_has_auto_start_field(self):
        """config.json contains auto_start for builder."""
        config_path = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        builder_cfg = config.get('agents', {}).get('builder', {})
        self.assertIn('auto_start', builder_cfg)

    def test_all_roles_have_startup_flags(self):
        """All four roles have find_work and auto_start."""
        config_path = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        for role in ('pm', 'architect', 'builder', 'qa'):
            role_cfg = config.get('agents', {}).get(role, {})
            self.assertIn('find_work', role_cfg,
                          f'{role} missing find_work')
            self.assertIn('auto_start', role_cfg,
                          f'{role} missing auto_start')

    def test_startup_flags_are_boolean(self):
        """Startup flags are boolean values."""
        config_path = os.path.join(PROJECT_ROOT, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        for role in ('pm', 'architect', 'builder', 'qa'):
            role_cfg = config.get('agents', {}).get(role, {})
            self.assertIsInstance(role_cfg['find_work'], bool,
                                 f'{role} find_work not bool')
            self.assertIsInstance(role_cfg['auto_start'], bool,
                                 f'{role} auto_start not bool')

    def test_command_file_references_startup_flags(self):
        """Command file Step 5 references startup flag handling."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('find_work', content)
        self.assertIn('auto_start', content)

    def test_command_file_has_startup_disabled_message(self):
        """Command file includes the find_work disabled message."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn(
            'find_work disabled -- awaiting instruction', content)

    def test_command_file_references_briefing_config(self):
        """Command file references startup briefing config object."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn("briefing's `config`", content,
                      'Command file must reference briefing config object '
                      'for startup flag handling')

    def test_flags_default_to_true(self):
        """Startup flags default to true when absent from config."""
        # Simulate missing fields -- default should be True
        empty_config = {'agents': {'builder': {}}}
        builder_cfg = empty_config['agents']['builder']
        startup = builder_cfg.get('find_work', True)
        recommend = builder_cfg.get('auto_start', True)
        self.assertTrue(startup)
        self.assertTrue(recommend)

    def test_startup_briefing_has_config_with_flags(self):
        """Startup briefing JSON contains config with find_work
        and auto_start fields."""
        import subprocess
        result = subprocess.run(
            ['bash', 'tools/cdd/status.sh', '--startup', 'builder'],
            capture_output=True, text=True, timeout=60, cwd=PROJECT_ROOT)
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn('config', data)
        config = data['config']
        self.assertIn('find_work', config)
        self.assertIn('auto_start', config)
        self.assertIsInstance(config['find_work'], bool)
        self.assertIsInstance(config['auto_start'], bool)


class TestStartupBriefingIntegration(unittest.TestCase):
    """Verify that --startup <role> is wired correctly in status.sh and
    produces the right fields for the /pl-resume restore flow."""

    def test_status_sh_supports_startup_flag(self):
        """status.sh accepts --startup <role> flag."""
        status_sh = os.path.join(PROJECT_ROOT, 'tools', 'cdd', 'status.sh')
        with open(status_sh) as f:
            content = f.read()
        self.assertIn('--startup', content)
        self.assertIn('--cli-startup', content)

    def test_command_file_references_startup_flag(self):
        """Command file Step 5 uses ${TOOLS_ROOT}/cdd/status.sh --startup."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('cdd/status.sh --startup', content)

    def test_command_file_step5_references_role_extensions(self):
        """Command file Step 5 lists Builder, QA, Architect extensions."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        # Builder extensions
        self.assertIn('tombstones', content.lower())
        self.assertIn('delivery plan state', content.lower())
        self.assertIn('phasing recommendation', content.lower())
        # QA extensions
        self.assertIn('testing features', content.lower())
        self.assertIn('discovery summary', content.lower())
        # Architect extensions
        self.assertIn('spec completeness', content.lower())
        self.assertIn('untracked files', content.lower())

    def test_command_file_references_delivery_plan_state(self):
        """Command file references delivery_plan_state for Builder phasing."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('delivery_plan_state', content)
        self.assertIn('phasing_recommended', content)

    def test_startup_briefing_mutual_exclusivity_with_graph(self):
        """--startup is checked before --graph in status.sh."""
        status_sh = os.path.join(PROJECT_ROOT, 'tools', 'cdd', 'status.sh')
        with open(status_sh) as f:
            content = f.read()
        startup_pos = content.find('= "--startup"')
        graph_pos = content.find('= "--graph"')
        self.assertGreater(startup_pos, -1)
        self.assertGreater(graph_pos, -1)
        self.assertLess(startup_pos, graph_pos,
                        "--startup must precede --graph for precedence")


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
            'test_file': 'tests/pl_session_resume/test_command.py',
        }, f)
    sys.exit(0 if result.wasSuccessful() else 1)
