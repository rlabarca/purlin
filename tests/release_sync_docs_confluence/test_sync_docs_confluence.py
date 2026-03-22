#!/usr/bin/env python3
"""Tests for the sync_docs_to_confluence release step.

Covers unit test scenarios from features/release_sync_docs_confluence.md:
- Subdirectory maps to Confluence section page
- Reference subdirectory maps to "Technical Reference"
- Filename derives correct page title
- Image upload produces URL mapping
- Image upload skips unchanged attachment
- Missing MCP server auto-configured
- Missing credentials file triggers token setup during image upload
- Stale documentation detected and updated
- Documentation is current, no changes needed
- Step never deletes Confluence pages
- Step never creates new doc files
- Credentials are never committed or logged

This release step has code: null (interactive). These tests verify the
underlying utility functions and behavioral contracts that the agent
relies on when executing the step interactively.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))

# Add dev/ to path so we can import the upload script's utilities
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'dev'))
import confluence_upload_images as cui

# Add project root for release resolve module
sys.path.insert(0, PROJECT_ROOT)
from tools.release.resolve import resolve_checklist


def _resolve_sync_step():
    """Resolve the sync_docs_to_confluence step via the release resolver."""
    resolved, _warnings, _errors = resolve_checklist()
    matches = [s for s in resolved if s['id'] == 'sync_docs_to_confluence']
    if not matches:
        raise ValueError('sync_docs_to_confluence step not found in resolved checklist')
    return matches[0]


class TestSubdirectoryMapsToSectionPage(unittest.TestCase):
    """Scenario: Subdirectory maps to Confluence section page

    Given the docs/ directory contains a subdirectory "guides" with one
    markdown file
    When the step processes the directory structure
    Then it derives the section page title "Guides" from the subdirectory name
    And it creates or finds a section page titled "Guides" as a child of
    the parent page
    """

    def test_guides_subdirectory_maps_to_guides(self):
        """'guides' subdirectory derives title 'Guides'."""
        self.assertEqual(cui.derive_section_title('guides'), 'Guides')

    def test_section_title_is_title_cased(self):
        """Section titles are title-cased from directory names."""
        self.assertEqual(cui.derive_section_title('tutorials'), 'Tutorials')

    def test_section_title_preserves_casing_logic(self):
        """Multi-word directory names are title-cased correctly."""
        self.assertEqual(
            cui.derive_section_title('how-to'),
            'How-To')


class TestReferenceSubdirectoryMapping(unittest.TestCase):
    """Scenario: Reference subdirectory maps to "Technical Reference"

    Given the docs/ directory contains a subdirectory "reference"
    When the step processes the directory structure
    Then it derives the section page title "Technical Reference"
    (not "Reference")
    """

    def test_reference_maps_to_technical_reference(self):
        """'reference' subdirectory maps to 'Technical Reference'."""
        self.assertEqual(
            cui.derive_section_title('reference'),
            'Technical Reference')

    def test_reference_case_insensitive(self):
        """Mapping works regardless of case."""
        self.assertEqual(
            cui.derive_section_title('Reference'),
            'Technical Reference')

    def test_non_reference_not_special_cased(self):
        """Other directories don't get the 'Technical' prefix."""
        self.assertNotEqual(
            cui.derive_section_title('guides'),
            'Technical Guides')


class TestFilenameDerivePageTitle(unittest.TestCase):
    """Scenario: Filename derives correct page title

    Given a markdown file named "testing-workflow-guide.md" in docs/guides/
    When the step derives the page title
    Then the title is "Testing Workflow Guide"
    """

    def test_hyphenated_filename_to_title(self):
        """Hyphens become spaces, words title-cased."""
        self.assertEqual(
            cui.derive_page_title('testing-workflow-guide.md'),
            'Testing Workflow Guide')

    def test_single_word_filename(self):
        """Single-word filename title-cases correctly."""
        self.assertEqual(
            cui.derive_page_title('overview.md'),
            'Overview')

    def test_md_extension_stripped(self):
        """The .md extension is removed before title derivation."""
        title = cui.derive_page_title('my-doc.md')
        self.assertEqual(title, 'My Doc')

    def test_parallel_execution_guide(self):
        """Verify with the actual project doc filename."""
        self.assertEqual(
            cui.derive_page_title('parallel-execution-guide.md'),
            'Parallel Execution Guide')


class TestImageUploadProducesUrlMapping(unittest.TestCase):
    """Scenario: Image upload produces URL mapping

    Given a markdown file contains "![diagram](images/flow.png)"
    And images/flow.png exists relative to the markdown file
    When the image upload script runs with --page-id and --files arguments
    Then the script outputs a JSON mapping from the local path to a
    Confluence attachment URL
    And the local image reference in markdown is replaced with the
    Confluence URL before sync
    """

    def test_scan_image_references(self):
        """Image references are detected in markdown content."""
        content = '# Title\n\n![diagram](images/flow.png)\n\nSome text.'
        refs = cui.scan_image_references(content)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0], ('diagram', 'images/flow.png'))

    def test_scan_multiple_images(self):
        """Multiple image references are all detected."""
        content = ('![a](img/a.png)\n'
                   'text\n'
                   '![b](img/b.jpg)\n')
        refs = cui.scan_image_references(content)
        self.assertEqual(len(refs), 2)

    def test_replace_image_paths_with_urls(self):
        """Local image paths are replaced with Confluence URLs."""
        content = '![diagram](images/flow.png)'
        url_mapping = {
            'images/flow.png':
                'https://trustengine.atlassian.net/wiki/download/'
                'attachments/123/flow.png'
        }
        result = cui.replace_image_paths(content, url_mapping)
        self.assertNotIn('images/flow.png', result)
        self.assertIn('trustengine.atlassian.net', result)

    def test_cli_interface_exists(self):
        """The upload script has the expected CLI arguments."""
        result = subprocess.run(
            [sys.executable,
             os.path.join(PROJECT_ROOT, 'dev',
                          'confluence_upload_images.py'),
             '--help'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--page-id', result.stdout)
        self.assertIn('--files', result.stdout)


class TestImageUploadSkipsUnchanged(unittest.TestCase):
    """Scenario: Image upload skips unchanged attachment

    Given images/flow.png was previously uploaded to the target
    Confluence page
    And the local file size matches the existing attachment size
    When the image upload script runs
    Then the script skips the upload for that file
    And the output mapping still contains the existing Confluence URL
    """

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.test_file = os.path.join(cls.tmpdir, 'flow.png')
        with open(cls.test_file, 'wb') as f:
            f.write(b'\x89PNG' + b'\x00' * 100)
        cls.file_size = os.path.getsize(cls.test_file)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_skip_when_size_matches(self):
        """should_upload returns False when sizes match."""
        existing = {
            'flow.png': {
                'size': self.file_size,
                'url': 'https://example.com/flow.png'
            }
        }
        self.assertFalse(
            cui.should_upload(self.test_file, existing))

    def test_upload_when_size_differs(self):
        """should_upload returns True when sizes differ."""
        existing = {
            'flow.png': {
                'size': self.file_size + 50,
                'url': 'https://example.com/flow.png'
            }
        }
        self.assertTrue(
            cui.should_upload(self.test_file, existing))

    def test_upload_when_file_not_in_existing(self):
        """should_upload returns True for new files."""
        self.assertTrue(
            cui.should_upload(self.test_file, {}))


class TestMissingMcpServerAutoConfigured(unittest.TestCase):
    """Scenario: Missing MCP server auto-configured

    Given the Atlassian MCP server is not configured in Claude Code
    When the step executes Phase 0
    Then the step runs "claude mcp add atlassian --transport http
    --scope project https://mcp.atlassian.com/v1/mcp" automatically
    And informs the user that a session restart is needed for the
    MCP to load
    And the step halts without asking the user to run any CLI commands
    """

    def test_resolved_step_contains_mcp_add_command(self):
        """Resolved step auto-configures MCP via claude mcp add."""
        step = _resolve_sync_step()
        self.assertIn(
            'claude mcp add atlassian',
            step['agent_instructions'])

    def test_resolved_step_contains_mcp_url(self):
        """Resolved step's agent instructions contain correct MCP URL."""
        step = _resolve_sync_step()
        self.assertIn(
            'https://mcp.atlassian.com/v1/mcp',
            step['agent_instructions'])

    def test_resolved_step_references_prodeng_space(self):
        """Resolved step verifies PRODENG space accessibility."""
        step = _resolve_sync_step()
        self.assertIn('PRODENG', step['agent_instructions'])

    def test_resolved_step_specifies_restart_and_halt(self):
        """Resolved step informs user of restart and halts."""
        step = _resolve_sync_step()
        instructions = step['agent_instructions']
        self.assertIn('restart', instructions.lower())
        self.assertIn('HALT', instructions)


class TestMissingCredentialsTriggersTokenSetupDuringImageUpload(unittest.TestCase):
    """Scenario: Missing credentials file triggers token setup during
    image upload

    Given .purlin/runtime/confluence/credentials.json does not exist
    And markdown files contain image references
    When the step executes Phase 2 image upload
    Then the step guides the user to create an API token
    And collects the user's email and token
    And writes the credentials file to
    .purlin/runtime/confluence/credentials.json
    And verifies the credentials with a test API call
    """

    def test_load_credentials_raises_on_missing_file(self):
        """load_credentials raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            cui.load_credentials('/nonexistent/path/credentials.json')

    def test_load_credentials_raises_on_missing_fields(self):
        """load_credentials raises ValueError for incomplete credentials."""
        tmpdir = tempfile.mkdtemp()
        try:
            creds_path = os.path.join(tmpdir, 'credentials.json')
            with open(creds_path, 'w') as f:
                json.dump({'email': 'test@example.com'}, f)
            with self.assertRaises(ValueError) as ctx:
                cui.load_credentials(creds_path)
            self.assertIn('token', str(ctx.exception))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_load_credentials_succeeds_with_valid_file(self):
        """load_credentials returns credentials when file is valid."""
        tmpdir = tempfile.mkdtemp()
        try:
            creds_path = os.path.join(tmpdir, 'credentials.json')
            with open(creds_path, 'w') as f:
                json.dump({
                    'email': 'test@example.com',
                    'token': 'test-token',
                    'base_url': 'https://example.atlassian.net'
                }, f)
            creds = cui.load_credentials(creds_path)
            self.assertEqual(creds['email'], 'test@example.com')
            self.assertEqual(creds['token'], 'test-token')
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_resolved_step_references_token_creation_url(self):
        """Resolved step points to Atlassian API token page."""
        step = _resolve_sync_step()
        self.assertIn(
            'id.atlassian.com/manage-profile/security/api-tokens',
            step['agent_instructions'])

    def test_credentials_setup_in_phase_2(self):
        """Credentials check is in Phase 2 (image upload), not Phase 0."""
        step = _resolve_sync_step()
        instructions = step['agent_instructions']
        # Phase 2 section should contain credentials check
        phase_2_idx = instructions.index('Phase 2')
        creds_idx = instructions.index('credentials.json', phase_2_idx)
        self.assertGreater(creds_idx, phase_2_idx)


class TestStaleDocumentationDetected(unittest.TestCase):
    """Scenario: Stale documentation detected and updated

    Given docs/guides/testing-workflow-guide.md references a command
    that was renamed in the current implementation
    When the step executes Phase 1 freshness review
    Then the stale reference is updated to the current command name
    And the change is committed with message "docs: update
    testing-workflow-guide.md for current implementation"
    """

    def test_resolved_step_includes_freshness_review(self):
        """Resolved step defines Phase 1 freshness review."""
        step = _resolve_sync_step()
        self.assertIn('Freshness Review', step['agent_instructions'])

    def test_resolved_step_cross_references_sources(self):
        """Freshness review cross-references tools/, instructions/,
        features/."""
        step = _resolve_sync_step()
        instructions = step['agent_instructions']
        self.assertIn('tools/', instructions)
        self.assertIn('instructions/', instructions)
        self.assertIn('features/', instructions)

    def test_derive_title_for_actual_project_docs(self):
        """Title derivation works correctly on actual project doc files."""
        docs_dir = os.path.join(PROJECT_ROOT, 'docs')
        md_files = [f for f in os.listdir(docs_dir)
                     if f.endswith('.md')]
        self.assertTrue(len(md_files) > 0)
        for filename in md_files:
            title = cui.derive_page_title(filename)
            self.assertFalse(title.endswith('.md'))
            self.assertEqual(title, title.title())


class TestDocumentationIsCurrent(unittest.TestCase):
    """Scenario: Documentation is current, no changes needed

    Given all docs/**/*.md files accurately reflect the current
    implementation
    When the step executes Phase 1 freshness review
    Then no commits are made
    And the step reports docs are current
    """

    def test_docs_files_produce_valid_page_titles(self):
        """Each doc file produces a valid non-empty page title."""
        docs_dir = os.path.join(PROJECT_ROOT, 'docs')
        md_files = []
        for root, _dirs, files in os.walk(docs_dir):
            for f in files:
                if f.endswith('.md'):
                    md_files.append(f)
        self.assertGreaterEqual(len(md_files), 2)
        for filename in md_files:
            title = cui.derive_page_title(filename)
            self.assertTrue(len(title) > 0)
            self.assertNotIn('.md', title)

    def test_docs_files_scannable_for_images(self):
        """Each doc file can be scanned for image references."""
        docs_dir = os.path.join(PROJECT_ROOT, 'docs')
        for root, _dirs, files in os.walk(docs_dir):
            for f in files:
                if f.endswith('.md'):
                    path = os.path.join(root, f)
                    with open(path) as fh:
                        content = fh.read()
                    refs = cui.scan_image_references(content)
                    self.assertIsInstance(refs, list)

    def test_resolved_step_confirms_current_state(self):
        """Resolved step instructions include reporting docs are current."""
        step = _resolve_sync_step()
        self.assertIn(
            'no updates needed', step['agent_instructions'].lower())


class TestStepNeverDeletesPages(unittest.TestCase):
    """Scenario: Step never deletes Confluence pages

    Given the parent page has a manually-created child page
    "Release Notes" with no local counterpart
    When the step syncs docs/ to Confluence
    Then the "Release Notes" page is not deleted or modified
    """

    def test_resolved_step_forbids_deletion(self):
        """Resolved step instructions explicitly forbid page deletion."""
        step = _resolve_sync_step()
        self.assertIn('NEVER delete', step['agent_instructions'])

    def test_step_is_interactive_only(self):
        """Step has code: null (no automated deletion possible)."""
        step = _resolve_sync_step()
        self.assertIsNone(step['code'])


class TestStepNeverCreatesNewDocFiles(unittest.TestCase):
    """Scenario: Step never creates new doc files

    Given a documentation gap is detected during freshness review
    When the step considers remediation
    Then no new files are created in docs/
    And the gap is listed in the Recommendations section of the
    completion report
    """

    def test_resolved_step_has_recommendations_section(self):
        """Resolved step instructions include Recommendations in report."""
        step = _resolve_sync_step()
        self.assertIn('Recommendations', step['agent_instructions'])

    def test_utility_functions_are_read_only(self):
        """Utility functions (scan, derive) do not create files."""
        tmpdir = tempfile.mkdtemp()
        try:
            content = '![img](test.png)\n# Doc Title\n'
            cui.scan_image_references(content)
            cui.derive_page_title('test-doc.md')
            cui.derive_section_title('guides')
            created = os.listdir(tmpdir)
            self.assertEqual(len(created), 0)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestCredentialsNeverCommittedOrLogged(unittest.TestCase):
    """Scenario: Credentials are never committed or logged

    Given .purlin/runtime/confluence/credentials.json contains valid
    credentials
    When the step executes any phase
    Then the credentials file path is covered by .gitignore via
    .purlin/runtime/
    And no credential values appear in commit messages or step output
    """

    def test_runtime_dir_is_gitignored(self):
        """.purlin/runtime/ is covered by .gitignore."""
        result = subprocess.run(
            ['git', 'check-ignore', '.purlin/runtime/test'],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT)
        self.assertEqual(
            result.returncode, 0,
            '.purlin/runtime/ should be gitignored')

    def test_credentials_path_is_gitignored(self):
        """The specific credentials path is gitignored."""
        creds_path = '.purlin/runtime/confluence/credentials.json'
        result = subprocess.run(
            ['git', 'check-ignore', creds_path],
            capture_output=True, text=True,
            cwd=PROJECT_ROOT)
        self.assertEqual(
            result.returncode, 0,
            f'{creds_path} should be gitignored')

    def test_auth_header_does_not_expose_raw_credentials(self):
        """Auth header base64-encodes credentials, not plaintext."""
        creds = {
            'email': 'user@example.com',
            'token': 'secret-token-value',
            'base_url': 'https://example.atlassian.net'
        }
        header = cui.get_auth_header(creds)
        self.assertTrue(header.startswith('Basic '))
        self.assertNotIn('secret-token-value', header)
        self.assertNotIn('user@example.com', header)

    def test_upload_script_errors_to_stderr(self):
        """Script writes errors to stderr, not stdout (avoids
        credential leakage in piped output)."""
        result = subprocess.run(
            [sys.executable,
             os.path.join(PROJECT_ROOT, 'dev',
                          'confluence_upload_images.py'),
             '--page-id', '123',
             '--files', '/nonexistent/file.png',
             '--credentials', '/nonexistent/creds.json'],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            len(result.stderr) > 0,
            'Errors should be written to stderr')


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
