#!/usr/bin/env python3
"""Tests for the record_version_notes project tool.

Covers data integrity and agent_instructions alignment:
- Tool metadata (friendly_name, description, code, agent_instructions)
- Agent instructions contain prepend ordering (most recent first)
- Agent instructions cover all spec requirements
- Tag discovery command
- Commit candidate collection command
- README.md entry format

The tool was originally purlin.record_version_notes in global_steps.json,
now record_version_notes in .purlin/toolbox/project_tools.json.
"""
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))


def _load_project_tools():
    """Load the project tools JSON file."""
    path = os.path.join(PROJECT_ROOT, '.purlin', 'toolbox', 'project_tools.json')
    with open(path) as f:
        return json.load(f)


def _get_record_version_notes_tool():
    """Extract the record_version_notes tool definition."""
    data = _load_project_tools()
    for tool in data['tools']:
        if tool['id'] == 'record_version_notes':
            return tool
    raise AssertionError('record_version_notes not found in project_tools.json')


def _git(args, cwd):
    """Run a git command, returning (returncode, stdout, stderr)."""
    result = subprocess.run(
        ['git'] + args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _git_check(args, cwd):
    """Run a git command, raising on failure. Returns stdout."""
    rc, stdout, stderr = _git(args, cwd)
    if rc != 0:
        raise RuntimeError(f'git {" ".join(args)} failed: {stderr}')
    return stdout


class TestStepMetadata(unittest.TestCase):
    """Verify step metadata matches spec Section 2.6."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()

    def test_tool_id(self):
        """Tool ID is record_version_notes."""
        self.assertEqual(self.tool['id'], 'record_version_notes')

    def test_friendly_name(self):
        """Friendly name matches expected value."""
        self.assertEqual(
            self.tool['friendly_name'],
            'Record Version & Release Notes')

    def test_code_is_null(self):
        """Code field is null (agent-interactive tool)."""
        self.assertIsNone(self.tool['code'])

    def test_agent_instructions_present(self):
        """Agent instructions field is non-null and non-empty."""
        self.assertIsNotNone(self.tool['agent_instructions'])
        self.assertTrue(len(self.tool['agent_instructions']) > 0)

    def test_description_present(self):
        """Description field is non-empty."""
        self.assertIsNotNone(self.tool.get('description'))
        self.assertTrue(len(self.tool['description']) > 0)


class TestPrependOrder(unittest.TestCase):
    """Verify agent_instructions specify prepend ordering (most recent first).

    The spec (Section 2.5) requires: "New entries are prepended at the top
    of the ## Releases section (most recent first)."

    This was the BUG: the original agent_instructions said "Insert" without
    specifying prepend order.
    """

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_prepend_keyword_present(self):
        """Agent instructions contain 'Prepend' or 'prepend'."""
        self.assertTrue(
            'prepend' in self.instructions.lower(),
            'agent_instructions must contain "prepend" to specify insertion order')

    def test_most_recent_first_present(self):
        """Agent instructions specify 'most recent first' ordering."""
        self.assertIn(
            'most recent first',
            self.instructions.lower(),
            'agent_instructions must specify "most recent first" ordering')

    def test_top_of_releases_section(self):
        """Agent instructions mention insertion at the top of the section."""
        self.assertIn(
            'top of',
            self.instructions.lower(),
            'agent_instructions must specify "top of" the Releases section')

    def test_not_just_insert(self):
        """Agent instructions do not use ambiguous 'Insert' without qualifier."""
        # The fix should use "Prepend" not "Insert" for the recording instruction
        # Verify step 6 says "Prepend" not "Insert"
        # JSON newlines are real \n chars when loaded
        lines = self.instructions.split('\n')
        step6_lines = [line for line in lines if line.strip().startswith('6.')]
        self.assertTrue(len(step6_lines) > 0, 'Step 6 must exist in instructions')
        step6 = step6_lines[0]
        self.assertNotIn(
            'Insert a new entry',
            step6,
            'Step 6 should say "Prepend" not "Insert a new entry"')


class TestTagDiscovery(unittest.TestCase):
    """Verify agent_instructions cover tag discovery per spec Section 2.1."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_git_tag_command_present(self):
        """Instructions include the git tag discovery command."""
        self.assertIn(
            'git tag --sort=-v:refname',
            self.instructions,
            'Must include the tag discovery command from Section 2.1')

    def test_no_tags_fallback(self):
        """Instructions handle the no-tags case."""
        self.assertIn(
            'no tags exist',
            self.instructions.lower(),
            'Must handle the no-tags case per Section 2.1')


class TestCommitCandidateCollection(unittest.TestCase):
    """Verify agent_instructions cover commit collection per spec Section 2.2."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_git_log_command_present(self):
        """Instructions include the git log command pattern."""
        self.assertIn(
            'git log',
            self.instructions,
            'Must include git log command per Section 2.2')

    def test_oneline_format(self):
        """Instructions specify --oneline format."""
        self.assertIn(
            '--oneline',
            self.instructions,
            'Must use --oneline flag per Section 2.2')

    def test_no_merges_filter(self):
        """Instructions specify --no-merges filter."""
        self.assertIn(
            '--no-merges',
            self.instructions,
            'Must use --no-merges flag per Section 2.2')


class TestSuggestionSynthesis(unittest.TestCase):
    """Verify agent_instructions cover suggestion synthesis per spec Section 2.3."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_grouping_by_theme(self):
        """Instructions mention grouping by theme."""
        self.assertIn(
            'grouping by theme',
            self.instructions,
            'Must mention grouping by theme per Section 2.3')


class TestUserConfirmation(unittest.TestCase):
    """Verify agent_instructions cover user confirmation per spec Section 2.4."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_version_number_request(self):
        """Instructions ask for the version number."""
        self.assertIn(
            'version number',
            self.instructions.lower(),
            'Must ask for version number per Section 2.4')

    def test_free_text_option(self):
        """Instructions allow free text release notes."""
        self.assertIn(
            'free text',
            self.instructions,
            'Must allow free text notes per Section 2.4')


class TestReadmeRecording(unittest.TestCase):
    """Verify agent_instructions cover README recording per spec Section 2.5."""

    def setUp(self):
        self.tool = _get_record_version_notes_tool()
        self.instructions = self.tool['agent_instructions']

    def test_releases_heading(self):
        """Instructions reference the ## Releases heading."""
        self.assertIn(
            'Releases',
            self.instructions,
            'Must reference ## Releases heading per Section 2.5')

    def test_create_heading_if_absent(self):
        """Instructions mention creating the heading if absent."""
        self.assertIn(
            'if absent',
            self.instructions.lower(),
            'Must handle missing ## Releases heading per Section 2.5')

    def test_entry_format(self):
        """Instructions specify the entry format with version and date."""
        self.assertIn(
            '### <version>',
            self.instructions,
            'Must specify entry format per Section 2.5')
        self.assertIn(
            '<YYYY-MM-DD>',
            self.instructions,
            'Must include date format per Section 2.5')


class TestToolInProjectToolbox(unittest.TestCase):
    """Verify tool is registered in the project toolbox."""

    def test_tool_in_project_tools(self):
        """record_version_notes is listed in .purlin/toolbox/project_tools.json."""
        data = _load_project_tools()
        tool_ids = [t['id'] for t in data['tools']]
        self.assertIn('record_version_notes', tool_ids)


class TestGitNoTags(unittest.TestCase):
    """Verify tag discovery returns empty when no tags exist."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        _git_check(['init'], cls.tmpdir)
        _git_check(['config', 'user.email', 'test@test.com'], cls.tmpdir)
        _git_check(['config', 'user.name', 'Test'], cls.tmpdir)
        with open(os.path.join(cls.tmpdir, 'init.txt'), 'w') as f:
            f.write('init')
        _git_check(['add', '.'], cls.tmpdir)
        _git_check(['commit', '-m', 'initial commit'], cls.tmpdir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_no_tags_returns_empty(self):
        """git tag --sort=-v:refname returns empty when no tags exist."""
        rc, stdout, stderr = _git(
            ['tag', '--sort=-v:refname'], self.tmpdir)
        self.assertEqual(rc, 0)
        self.assertEqual(stdout, '')


class TestGitTagDiscoveryWithTags(unittest.TestCase):
    """Verify tag discovery and log-since-tag work correctly."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        _git_check(['init'], cls.tmpdir)
        _git_check(['config', 'user.email', 'test@test.com'], cls.tmpdir)
        _git_check(['config', 'user.name', 'Test'], cls.tmpdir)
        # Initial commit with v0.1.0 tag
        with open(os.path.join(cls.tmpdir, 'init.txt'), 'w') as f:
            f.write('init')
        _git_check(['add', '.'], cls.tmpdir)
        _git_check(['commit', '-m', 'initial commit'], cls.tmpdir)
        _git_check(['tag', 'v0.1.0'], cls.tmpdir)
        # Second commit with v0.2.0 tag
        with open(os.path.join(cls.tmpdir, 'v2.txt'), 'w') as f:
            f.write('v2')
        _git_check(['add', '.'], cls.tmpdir)
        _git_check(['commit', '-m', 'second commit'], cls.tmpdir)
        _git_check(['tag', 'v0.2.0'], cls.tmpdir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_tag_discovery_returns_most_recent_first(self):
        """git tag --sort=-v:refname returns the most recent tag first."""
        rc, stdout, stderr = _git(
            ['tag', '--sort=-v:refname'], self.tmpdir)
        self.assertEqual(rc, 0)
        tags = stdout.strip().splitlines()
        self.assertEqual(tags[0], 'v0.2.0',
                         'Most recent tag should be first')

    def test_git_log_since_tag(self):
        """git log <tag>..HEAD --oneline --no-merges returns commits since tag."""
        rc, stdout, stderr = _git(
            ['log', 'v0.1.0..HEAD', '--oneline', '--no-merges'],
            self.tmpdir)
        self.assertEqual(rc, 0)
        self.assertTrue(len(stdout.strip()) > 0,
                        'Should have commits since v0.1.0')


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
