#!/usr/bin/env python3
"""Tests for the /pl-resume agent command (Purlin unified agent model).

Covers unit test scenarios from features/pl_session_resume.md:
- Checkpoint file path is correct
- Legacy checkpoint files are recognized

Also validates checkpoint format and mode-specific fields per spec Section 2.2.
"""
import os
import re
import shutil
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-resume.md')

# ISO 8601 pattern
ISO_8601_PATTERN = re.compile(
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})')

VALID_MODES = {'engineer', 'pm', 'qa', 'none'}
LEGACY_ROLES = {'architect', 'builder', 'qa', 'pm'}
LEGACY_ROLE_TO_MODE = {
    'builder': 'engineer',
    'architect': 'engineer',
    'qa': 'qa',
    'pm': 'pm',
}

# Sample checkpoint for the Purlin unified model
SAMPLE_CHECKPOINT_ENGINEER = """# Session Checkpoint

**Mode:** engineer
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Running local tests after implementation commit

### Done
- Read anchor nodes and prerequisites
- Implemented data layer with test harness
- Committed implementation: abc1234

### Next
1. Run tests -- verify tests/project_init/tests.json shows PASS
2. Commit status tag: [Ready for Verification]

## Engineer Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** Phase 2 of 3 -- IN_PROGRESS
**Work Queue:**
1. [HIGH] pl_spec_code_audit.md
**Pending Decisions:** None

## Uncommitted Changes
None

## Notes
Font-size decision needs PM review.
"""

SAMPLE_CHECKPOINT_QA = """# Session Checkpoint

**Mode:** qa
**Timestamp:** 2026-03-05T11:00:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Verifying QA scenarios

### Done
- Verified 5 of 8 scenarios

### Next
1. Verify scenario 6: Status badge updates

## QA Context
**Scenario Progress:** 5 of 8 scenarios completed
**Current Scenario:** Status badge updates
**Discoveries:** None
**Verification Queue:** 3 features remaining

## Uncommitted Changes
None

## Notes
None
"""

SAMPLE_CHECKPOINT_PM = """# Session Checkpoint

**Mode:** pm
**Timestamp:** 2026-03-10T09:00:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Drafting visual specification

### Done
- Read existing feature spec
- Reviewed Figma designs

### Next
1. Complete Visual Specification section

## PM Context
**Spec Drafts:** project_init.md requirements in progress
**Figma Context:** None

## Uncommitted Changes
None

## Notes
None
"""

# Legacy checkpoint (old role-scoped format)
SAMPLE_LEGACY_BUILDER = """# Session Checkpoint

**Role:** builder
**Timestamp:** 2026-02-28T15:30:00Z
**Branch:** main

## Current Work

**Feature:** features/project_init.md
**In Progress:** Running local tests

### Done
- Implemented feature

### Next
1. Run tests

## Engineer Context
**Protocol Step:** 3 -- Verify Locally
**Delivery Plan:** No delivery plan
**Work Queue:**
1. [HIGH] pl_spec_code_audit.md
**Pending Decisions:** None

## Uncommitted Changes
None

## Notes
None
"""


def _pid_scoped_checkpoint_path(tmpdir, pid):
    """Return a PID-scoped checkpoint path."""
    return os.path.join(
        tmpdir, '.purlin', 'cache', f'session_checkpoint_{pid}.md')


def _unscoped_checkpoint_path(tmpdir):
    """Return the unscoped (legacy migration) checkpoint path."""
    return os.path.join(
        tmpdir, '.purlin', 'cache', 'session_checkpoint_purlin.md')


def _legacy_checkpoint_path(tmpdir, role):
    """Return a legacy role-scoped checkpoint path."""
    return os.path.join(
        tmpdir, '.purlin', 'cache', f'session_checkpoint_{role}.md')


def _make_cache_dir(tmpdir):
    """Create the .purlin/cache/ directory structure."""
    cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _write_pid_scoped_checkpoint(tmpdir, pid, content=None):
    """Write a PID-scoped checkpoint file."""
    if content is None:
        content = SAMPLE_CHECKPOINT_ENGINEER
    cache_dir = _make_cache_dir(tmpdir)
    path = os.path.join(cache_dir, f'session_checkpoint_{pid}.md')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _write_unscoped_checkpoint(tmpdir, content=None):
    """Write the unscoped (legacy migration) checkpoint file."""
    if content is None:
        content = SAMPLE_CHECKPOINT_ENGINEER
    cache_dir = _make_cache_dir(tmpdir)
    path = os.path.join(cache_dir, 'session_checkpoint_purlin.md')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _write_legacy_checkpoint(tmpdir, role='builder', content=None):
    """Write a legacy role-scoped checkpoint file."""
    if content is None:
        content = SAMPLE_LEGACY_BUILDER
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


def _detect_legacy_checkpoints(cache_dir):
    """Discover legacy role-scoped checkpoint files.

    Returns list of (role, path) tuples.
    """
    found = []
    for role in LEGACY_ROLES:
        path = os.path.join(cache_dir, f'session_checkpoint_{role}.md')
        if os.path.isfile(path):
            found.append((role, path))
    return found


def _map_legacy_role_to_mode(role):
    """Map a legacy role name to a Purlin mode."""
    return LEGACY_ROLE_TO_MODE.get(role, 'engineer')


# =========================================================================
# Scenario 1: Checkpoint file path is correct
# =========================================================================

class TestCheckpointFilePath(unittest.TestCase):
    """Scenario: Checkpoint file path is PID-scoped

    Given the Purlin agent
    And PURLIN_SESSION_ID is set
    When determining the checkpoint file path
    Then the path is .purlin/cache/session_checkpoint_${PURLIN_SESSION_ID}.md
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_pid_scoped_checkpoint_path_format(self):
        """PID-scoped path contains the session PID."""
        path = _pid_scoped_checkpoint_path(self.tmpdir, '46946')
        self.assertTrue(path.endswith(
            os.path.join('.purlin', 'cache', 'session_checkpoint_46946.md')))

    def test_unscoped_fallback_path_format(self):
        """Unscoped fallback path ends with session_checkpoint_purlin.md."""
        path = _unscoped_checkpoint_path(self.tmpdir)
        self.assertTrue(path.endswith(
            os.path.join('.purlin', 'cache', 'session_checkpoint_purlin.md')))

    def test_pid_scoped_checkpoint_created_at_correct_path(self):
        """Writing a PID-scoped checkpoint creates the file at the expected path."""
        path = _write_pid_scoped_checkpoint(self.tmpdir, '46946')
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(path, _pid_scoped_checkpoint_path(self.tmpdir, '46946'))

    def test_concurrent_terminals_produce_distinct_files(self):
        """Two different PIDs produce two distinct checkpoint files."""
        path_a = _write_pid_scoped_checkpoint(self.tmpdir, '11111')
        path_b = _write_pid_scoped_checkpoint(self.tmpdir, '22222')
        self.assertNotEqual(path_a, path_b)
        self.assertTrue(os.path.isfile(path_a))
        self.assertTrue(os.path.isfile(path_b))
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        checkpoint_files = sorted(f for f in os.listdir(cache_dir)
                                  if f.startswith('session_checkpoint_'))
        self.assertEqual(len(checkpoint_files), 2)
        self.assertIn('session_checkpoint_11111.md', checkpoint_files)
        self.assertIn('session_checkpoint_22222.md', checkpoint_files)


# =========================================================================
# Scenario 2: Legacy checkpoint files are recognized
# =========================================================================

class TestLegacyCheckpointRecognition(unittest.TestCase):
    """Scenario: Legacy checkpoint files are recognized

    Given .purlin/cache/session_checkpoint_builder.md exists
    And no PID-scoped or unscoped checkpoint exists
    When the agent checks for checkpoints
    Then the legacy builder checkpoint is found
    And the mode is mapped to "engineer"
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_legacy_builder_detected_when_no_higher_priority(self):
        """Legacy builder checkpoint is found when no PID-scoped or unscoped exists."""
        _write_legacy_checkpoint(self.tmpdir, role='builder')
        unscoped = _unscoped_checkpoint_path(self.tmpdir)
        self.assertFalse(os.path.exists(unscoped))
        cache_dir = os.path.join(self.tmpdir, '.purlin', 'cache')
        legacy = _detect_legacy_checkpoints(cache_dir)
        self.assertEqual(len(legacy), 1)
        self.assertEqual(legacy[0][0], 'builder')

    def test_builder_role_maps_to_engineer_mode(self):
        """Legacy 'builder' role maps to 'engineer' mode."""
        self.assertEqual(_map_legacy_role_to_mode('builder'), 'engineer')

    def test_architect_role_maps_to_engineer_mode(self):
        """Legacy 'architect' role maps to 'engineer' mode."""
        self.assertEqual(_map_legacy_role_to_mode('architect'), 'engineer')

    def test_qa_role_maps_to_qa_mode(self):
        """Legacy 'qa' role maps to 'qa' mode."""
        self.assertEqual(_map_legacy_role_to_mode('qa'), 'qa')

    def test_pm_role_maps_to_pm_mode(self):
        """Legacy 'pm' role maps to 'pm' mode."""
        self.assertEqual(_map_legacy_role_to_mode('pm'), 'pm')

    def test_pid_scoped_takes_precedence_over_unscoped(self):
        """PID-scoped checkpoint takes precedence over unscoped."""
        _write_pid_scoped_checkpoint(self.tmpdir, '46946')
        _write_unscoped_checkpoint(self.tmpdir)
        pid_path = _pid_scoped_checkpoint_path(self.tmpdir, '46946')
        self.assertTrue(os.path.isfile(pid_path))

    def test_pid_scoped_takes_precedence_over_legacy(self):
        """PID-scoped checkpoint takes precedence over legacy."""
        _write_pid_scoped_checkpoint(self.tmpdir, '46946')
        _write_legacy_checkpoint(self.tmpdir, role='builder')
        pid_path = _pid_scoped_checkpoint_path(self.tmpdir, '46946')
        self.assertTrue(os.path.isfile(pid_path))

    def test_unscoped_takes_precedence_over_legacy(self):
        """Unscoped checkpoint takes precedence over legacy."""
        _write_unscoped_checkpoint(self.tmpdir)
        _write_legacy_checkpoint(self.tmpdir, role='builder')
        unscoped_path = _unscoped_checkpoint_path(self.tmpdir)
        self.assertTrue(os.path.isfile(unscoped_path))

    def test_legacy_checkpoint_contains_role_field(self):
        """Legacy checkpoint uses **Role:** instead of **Mode:**."""
        _write_legacy_checkpoint(self.tmpdir, role='builder')
        path = _legacy_checkpoint_path(self.tmpdir, 'builder')
        with open(path) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Role', fields)
        self.assertEqual(fields['Role'], 'builder')


# =========================================================================
# Checkpoint format validation
# =========================================================================

class TestCheckpointFormat(unittest.TestCase):
    """Validate checkpoint format per spec Section 2.2.5."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_checkpoint_contains_mode_field(self):
        """Purlin checkpoint has **Mode:** field (not Role)."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999')
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        fields = _parse_checkpoint_fields(content)
        self.assertIn('Mode', fields)
        self.assertIn(fields['Mode'], VALID_MODES)

    def test_checkpoint_mode_is_engineer(self):
        """Engineer checkpoint has mode=engineer."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_ENGINEER)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertEqual(fields['Mode'], 'engineer')

    def test_checkpoint_contains_iso8601_timestamp(self):
        """Checkpoint has a valid ISO 8601 timestamp."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999')
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Timestamp', fields)
        self.assertRegex(fields['Timestamp'], ISO_8601_PATTERN)

    def test_checkpoint_contains_branch(self):
        """Checkpoint has a Branch field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999')
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Branch', fields)
        self.assertEqual(fields['Branch'], 'main')

    def test_checkpoint_has_required_sections(self):
        """Checkpoint contains all required sections."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999')
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        for section in ['# Session Checkpoint', '## Current Work',
                        '### Done', '### Next', '## Uncommitted Changes']:
            self.assertIn(section, content, f'Missing section: {section}')

    def test_checkpoint_has_feature_field(self):
        """Checkpoint has a Feature field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999')
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Feature', fields)
        self.assertTrue(fields['Feature'].startswith('features/'))


# =========================================================================
# Mode-specific fields
# =========================================================================

class TestEngineerModeFields(unittest.TestCase):
    """Validate Engineer-specific checkpoint fields per spec 2.2.2."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_engineer_checkpoint_has_context_section(self):
        """Engineer checkpoint has ## Engineer Context section."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_ENGINEER)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        self.assertIn('## Engineer Context', content)

    def test_engineer_has_protocol_step(self):
        """Engineer checkpoint has Protocol Step field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_ENGINEER)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Protocol Step', fields)
        self.assertIn('Verify Locally', fields['Protocol Step'])

    def test_engineer_has_delivery_plan(self):
        """Engineer checkpoint has Delivery Plan field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_ENGINEER)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Delivery Plan', fields)

    def test_engineer_has_work_queue(self):
        """Engineer checkpoint has Work Queue section."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_ENGINEER)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        self.assertIn('**Work Queue:**', content)
        self.assertIn('pl_spec_code_audit.md', content)


class TestQAModeFields(unittest.TestCase):
    """Validate QA-specific checkpoint fields per spec 2.2.3."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_qa_checkpoint_has_context_section(self):
        """QA checkpoint has ## QA Context section."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_QA)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        self.assertIn('## QA Context', content)

    def test_qa_has_scenario_progress(self):
        """QA checkpoint has Scenario Progress field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_QA)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Scenario Progress', fields)
        self.assertIn('5 of 8', fields['Scenario Progress'])

    def test_qa_has_verification_queue(self):
        """QA checkpoint has Verification Queue field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_QA)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Verification Queue', fields)

    def test_qa_mode_value(self):
        """QA checkpoint has mode=qa."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_QA)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertEqual(fields['Mode'], 'qa')


class TestPMModeFields(unittest.TestCase):
    """Validate PM-specific checkpoint fields per spec 2.2.4."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_pm_checkpoint_has_context_section(self):
        """PM checkpoint has ## PM Context section."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_PM)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            content = f.read()
        self.assertIn('## PM Context', content)

    def test_pm_has_spec_drafts(self):
        """PM checkpoint has Spec Drafts field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_PM)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Spec Drafts', fields)

    def test_pm_has_figma_context(self):
        """PM checkpoint has Figma Context field."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_PM)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertIn('Figma Context', fields)

    def test_pm_mode_value(self):
        """PM checkpoint has mode=pm."""
        _write_pid_scoped_checkpoint(self.tmpdir, '99999', SAMPLE_CHECKPOINT_PM)
        with open(_pid_scoped_checkpoint_path(self.tmpdir, '99999')) as f:
            fields = _parse_checkpoint_fields(f.read())
        self.assertEqual(fields['Mode'], 'pm')


# =========================================================================
# Skill file validation
# =========================================================================

class TestSkillFile(unittest.TestCase):
    """Validate the skill file matches the updated spec."""

    def test_command_file_exists(self):
        """The skill file .claude/commands/pl-resume.md exists."""
        self.assertTrue(os.path.isfile(COMMAND_FILE))

    def test_command_file_references_pid_scoped_checkpoint(self):
        """Skill file references PID-scoped checkpoint pattern."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('session_checkpoint_${PURLIN_SESSION_ID}', content)

    def test_command_file_references_unscoped_fallback(self):
        """Skill file references unscoped checkpoint as fallback."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('session_checkpoint_purlin.md', content)

    def test_command_file_uses_mode_not_role_in_format(self):
        """Skill file checkpoint format uses **Mode:** not **Role:**."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        # The checkpoint format section should show **Mode:**
        self.assertIn('**Mode:**', content)

    def test_command_file_has_engineer_context(self):
        """Skill file documents Engineer Context section."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('## Engineer Context', content)

    def test_command_file_has_qa_context(self):
        """Skill file documents QA Context section."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('## QA Context', content)

    def test_command_file_has_pm_context(self):
        """Skill file documents PM Context section."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('## PM Context', content)

    def test_command_file_has_merge_recovery(self):
        """Skill file documents merge-recovery mode."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('merge-recovery', content)

    def test_command_file_valid_args(self):
        """Skill file lists save and merge-recovery as valid options."""
        with open(COMMAND_FILE) as f:
            content = f.read()
        self.assertIn('save', content)
        self.assertIn('merge-recovery', content)


if __name__ == '__main__':
    # Custom runner that writes tests.json
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Write results
    import json
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    status = 'PASS' if failed == 0 else 'FAIL'
    tests_dir = os.path.join(PROJECT_ROOT, 'tests', 'pl_session_resume')
    os.makedirs(tests_dir, exist_ok=True)
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': status,
            'passed': passed,
            'failed': failed,
            'total': total,
            'test_file': 'tests/pl_session_resume/test_command.py',
        }, f)
    print(f'\ntests.json: {status} ({passed}/{total})')
