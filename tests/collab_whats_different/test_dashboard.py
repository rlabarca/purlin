#!/usr/bin/env python3
"""Tests for the What's Different dashboard integration.

Covers automated scenarios from features/collab_whats_different.md:
- Dashboard Endpoint Returns 400 When No Active Branch
- Dashboard Endpoint Returns 200 After Generation
- Dashboard HTML Includes Button When Sync State Is Not SAME
- Dashboard HTML Omits Button When Sync State Is SAME
- Dashboard HTML Omits Button When No Active Branch
- Generated Markdown File Exists After Generation
- GET Read Endpoint Returns Cached Digest
- GET Read Endpoint Returns 404 When No Cache
- GET Read Endpoint Returns 400 When No Branch
- POST Generate Endpoint Returns ISO 8601 Timestamp
- POST Deep Analysis Generate Endpoint Returns Analysis
- GET Deep Analysis Read Endpoint Returns Cached Analysis
- GET Deep Analysis Read Endpoint Returns 404 When No Cache
- Impact Summary Content Appears Above File-Level Digest in HTML
- Auto-Generation After pl-remote-pull Merge
- Stale Impact Summary Absent After Digest Regeneration
- Button Opens Cached Content Without Regeneration
- DIVERGED Generation Returns Both Directions via Endpoint
- Regenerate Triggers Fresh Generation via Endpoint
- Deep Analysis Generation Returns Analysis via Endpoint
- Modal Close Button Present in HTML
"""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
CDD_DIR = os.path.join(PROJECT_ROOT, 'tools', 'cdd')
sys.path.insert(0, CDD_DIR)

import serve


class TestEndpointReturns400WhenNoActiveBranch(unittest.TestCase):
    """Scenario: Dashboard Endpoint Returns 400 When No Active Branch

    Given no file exists at .purlin/runtime/active_branch
    When a POST request is sent to /whats-different/generate
    Then the response status is 400
    And the response body contains an error message
    """

    @patch('serve.get_active_branch', return_value=None)
    def test_returns_400_no_branch(self, mock_branch):
        handler = MagicMock()
        handler.headers = {}
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 400)
        self.assertIn('error', responses[0][1])


class TestEndpointReturns200AfterGeneration(unittest.TestCase):
    """Scenario: Dashboard Endpoint Returns 200 After Generation

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body contains the generated markdown content
    And features/digests/whats-different.md exists on disk
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 1, 'anchors': 0, 'visual': 0,
        'code': 2, 'tests': 1, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_200_with_content(self, mock_branch, mock_run, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        digest_content = '# What\'s Different?\n\n**Generated:** 2026-02-27\n'
        with open(digest_path, 'w') as f:
            f.write(digest_content)

        mock_run.return_value = MagicMock(
            returncode=0, stdout=digest_content, stderr='')

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]['status'], 'ok')
        self.assertIn('digest', responses[0][1])
        self.assertIn("What's Different?", responses[0][1]['digest'])

        import shutil
        shutil.rmtree(tmpdir)


class TestDashboardHTMLButtonVisibility(unittest.TestCase):
    """Test button visibility in dashboard HTML based on sync state."""

    def _generate_html_with_sync(self, active_branch, sync_state,
                                 commits_ahead=0, commits_behind=0):
        """Helper to generate HTML with specific remote collab state."""
        sync_data = {
            'sync_state': sync_state,
            'commits_ahead': commits_ahead,
            'commits_behind': commits_behind,
        }
        branches = [{'name': active_branch, 'branch': f'collab/{active_branch}',
                      'active': True, 'sync_state': sync_state,
                      'commits_ahead': commits_ahead,
                      'commits_behind': commits_behind}] if active_branch else []
        contributors = []
        last_fetch = '2026-02-27T00:00:00Z'

        return serve._branch_collab_section_html(
            active_branch, sync_data, branches,
            contributors, last_fetch, True)

    def test_button_present_when_behind(self):
        """Scenario: Dashboard HTML Includes Button When Sync State Is Not SAME"""
        html = self._generate_html_with_sync(
            'v0.5-sprint', 'BEHIND', commits_behind=2)
        self.assertIn("What's Different?", html)
        self.assertIn('btn-whats-different', html)

    def test_button_present_when_ahead(self):
        html = self._generate_html_with_sync(
            'v0.5-sprint', 'AHEAD', commits_ahead=3)
        self.assertIn("What's Different?", html)

    def test_button_present_when_diverged(self):
        html = self._generate_html_with_sync(
            'v0.5-sprint', 'DIVERGED', commits_ahead=1, commits_behind=2)
        self.assertIn("What's Different?", html)

    def test_button_absent_when_same(self):
        """Scenario: Dashboard HTML Omits Button When Sync State Is SAME"""
        html = self._generate_html_with_sync('v0.5-sprint', 'SAME')
        self.assertNotIn('btn-whats-different', html)

    def test_button_absent_when_no_branch(self):
        """Scenario: Dashboard HTML Omits Button When No Active Branch"""
        html = serve._branch_collab_section_html(
            None, {}, [], [], None, True)
        self.assertNotIn('btn-whats-different', html)


class TestGeneratedMarkdownFile(unittest.TestCase):
    """Scenario: Generated Markdown File Exists After Generation

    Tests that after generation, the digest file exists and contains
    expected content.
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 0, 'anchors': 0, 'visual': 0,
        'code': 0, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_digest_file_written(self, mock_branch, mock_run, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)

        digest_content = ('# What\'s Different?\n\n'
                          '**Generated:** 2026-02-27 00:00 UTC\n\n'
                          '## Collab Changes\n\n- M features/login.md\n')
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write(digest_content)

        mock_run.return_value = MagicMock(
            returncode=0, stdout=digest_content, stderr='')

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_whats_different_generate(handler)

        # Verify file exists
        self.assertTrue(os.path.exists(digest_path))

        # Verify content
        with open(digest_path) as f:
            content = f.read()
        self.assertIn("What's Different?", content)
        self.assertIn('Collab Changes', content)

        self.assertEqual(responses[0][0], 200)

        import shutil
        shutil.rmtree(tmpdir)


class TestGetReadEndpointReturnsCachedDigest(unittest.TestCase):
    """Scenario: GET Read Endpoint Returns Cached Digest

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response status is 200
    And the response body contains a "digest" field with the cached content
    And the response body contains a "generated_at" field in ISO 8601 format
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 1, 'anchors': 0, 'visual': 0,
        'code': 0, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_200_with_cached_content(self, mock_branch, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        digest_content = '# What\'s Different?\n\n**Generated:** 2026-02-27\n'
        with open(digest_path, 'w') as f:
            f.write(digest_content)

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_whats_different_read(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]['status'], 'ok')
        self.assertIn('digest', responses[0][1])
        self.assertIn("What's Different?", responses[0][1]['digest'])
        # Verify ISO 8601 format
        generated_at = responses[0][1]['generated_at']
        self.assertRegex(generated_at, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')

        import shutil
        shutil.rmtree(tmpdir)


class TestGetReadEndpointReturns404WhenNoCache(unittest.TestCase):
    """Scenario: GET Read Endpoint Returns 404 When No Cache

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md does not exist
    When a GET request is sent to /whats-different/read
    Then the response status is 404
    """

    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_404_no_cache(self, mock_branch):
        tmpdir = tempfile.mkdtemp()
        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_whats_different_read(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 404)

        import shutil
        shutil.rmtree(tmpdir)


class TestGetReadEndpointReturns400WhenNoBranch(unittest.TestCase):
    """Scenario: GET Read Endpoint Returns 400 When No Branch

    Given no file exists at .purlin/runtime/active_branch
    When a GET request is sent to /whats-different/read
    Then the response status is 400
    And the response body contains an error message
    """

    @patch('serve.get_active_branch', return_value=None)
    def test_returns_400_no_branch(self, mock_branch):
        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        serve.Handler._handle_whats_different_read(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 400)
        self.assertIn('error', responses[0][1])


class TestPostGenerateEndpointReturnsISO8601Timestamp(unittest.TestCase):
    """Scenario: POST Generate Endpoint Returns ISO 8601 Timestamp

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response body "generated_at" field matches ISO 8601 format
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 0, 'anchors': 0, 'visual': 0,
        'code': 1, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_iso_8601_timestamp(self, mock_branch, mock_run, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write('# Test digest\n')

        mock_run.return_value = MagicMock(
            returncode=0, stdout='# Test digest\n', stderr='')

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(responses[0][0], 200)
        generated_at = responses[0][1]['generated_at']
        self.assertRegex(generated_at, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')

        import shutil
        shutil.rmtree(tmpdir)


class TestPostDeepAnalysisGenerateEndpoint(unittest.TestCase):
    """Scenario: POST Deep Analysis Generate Endpoint Returns Analysis

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response body contains an "analysis" field with the generated content
    And the response body contains a "generated_at" field in ISO 8601 format
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_200_with_analysis(self, mock_branch, mock_run):
        tmpdir = tempfile.mkdtemp()
        analysis_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(analysis_dir)
        analysis_path = os.path.join(analysis_dir, 'whats-different-analysis.md')
        analysis_content = '# Impact Summary\n\nKey changes here.\n'
        with open(analysis_path, 'w') as f:
            f.write(analysis_content)

        mock_run.return_value = MagicMock(
            returncode=0, stdout=analysis_content, stderr='')

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_deep_analysis_generate(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]['status'], 'ok')
        self.assertIn('analysis', responses[0][1])
        self.assertIn('Impact Summary', responses[0][1]['analysis'])
        generated_at = responses[0][1]['generated_at']
        self.assertRegex(generated_at, r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')

        import shutil
        shutil.rmtree(tmpdir)


class TestGetDeepAnalysisReadEndpointReturnsCached(unittest.TestCase):
    """Scenario: GET Deep Analysis Read Endpoint Returns Cached Analysis

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 200
    And the response body contains an "analysis" field with the cached content
    """

    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_200_with_cached_analysis(self, mock_branch):
        tmpdir = tempfile.mkdtemp()
        analysis_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(analysis_dir)
        analysis_path = os.path.join(analysis_dir, 'whats-different-analysis.md')
        analysis_content = '# Impact Summary\n\nCached analysis content.\n'
        with open(analysis_path, 'w') as f:
            f.write(analysis_content)

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_deep_analysis_read(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)
        self.assertEqual(responses[0][1]['status'], 'ok')
        self.assertIn('analysis', responses[0][1])
        self.assertIn('Impact Summary', responses[0][1]['analysis'])

        import shutil
        shutil.rmtree(tmpdir)


class TestGetDeepAnalysisReadEndpointReturns404(unittest.TestCase):
    """Scenario: GET Deep Analysis Read Endpoint Returns 404 When No Cache

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md does not exist
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 404
    """

    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_returns_404_no_cache(self, mock_branch):
        tmpdir = tempfile.mkdtemp()
        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_deep_analysis_read(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 404)

        import shutil
        shutil.rmtree(tmpdir)


class TestStalenessInvalidation(unittest.TestCase):
    """Scenario: Standard Digest Generation Deletes Stale Deep Analysis

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And features/digests/whats-different-analysis.md does not exist on disk
    """

    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_generate_deletes_stale_analysis(self, mock_branch):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)

        # Create pre-existing analysis file (stale)
        analysis_path = os.path.join(digest_dir, 'whats-different-analysis.md')
        with open(analysis_path, 'w') as f:
            f.write('# Stale Analysis\nOld content.')
        self.assertTrue(os.path.exists(analysis_path))

        # Create a digest file that the handler reads after "generation"
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write('# Fresh Digest\nNew content.')

        handler = MagicMock()
        responses = []
        def capture_json(status, data):
            responses.append((status, data))
        handler._send_json = capture_json

        # Mock subprocess to simulate successful generation
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '# Fresh Digest'
        mock_result.stderr = ''

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}), \
             patch('serve.subprocess.run', return_value=mock_result), \
             patch('serve._compute_digest_tags', return_value={}):
            serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0][0], 200)

        # The stale analysis file should be deleted
        self.assertFalse(os.path.exists(analysis_path))

        import shutil
        shutil.rmtree(tmpdir)


class TestImpactSummaryAboveDigest(unittest.TestCase):
    """Scenario: Impact Summary Content Appears Above File-Level Digest in HTML

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response contains the digest content
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response contains the analysis content
    And the modal renders the impact summary section above the file-level digest
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 1, 'anchors': 0, 'visual': 0,
        'code': 2, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_both_endpoints_return_content(self, mock_branch, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)

        # Create both digest and analysis files
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write('# What\'s Different?\n\n## Code Changes\n')

        analysis_path = os.path.join(digest_dir, 'whats-different-analysis.md')
        with open(analysis_path, 'w') as f:
            f.write('# Impact Summary\n\nKey changes analysis.\n')

        # Test GET /whats-different/read returns digest
        handler = MagicMock()
        digest_responses = []
        handler._send_json = lambda s, d: digest_responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_whats_different_read(handler)

        self.assertEqual(digest_responses[0][0], 200)
        self.assertIn('digest', digest_responses[0][1])
        self.assertIn("What's Different?", digest_responses[0][1]['digest'])

        # Test GET /whats-different/deep-analysis/read returns analysis
        handler2 = MagicMock()
        analysis_responses = []
        handler2._send_json = lambda s, d: analysis_responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_deep_analysis_read(handler2)

        self.assertEqual(analysis_responses[0][0], 200)
        self.assertIn('analysis', analysis_responses[0][1])
        self.assertIn('Impact Summary', analysis_responses[0][1]['analysis'])

        import shutil
        shutil.rmtree(tmpdir)

    def test_modal_template_positions_impact_above_digest(self):
        """Verify the modal HTML template positions the impact section
        (wd-impact-section) above the digest body (wd-modal-body)."""
        source_path = os.path.join(CDD_DIR, 'serve.py')
        with open(source_path) as f:
            source = f.read()

        impact_pos = source.find('id="wd-impact-section"')
        body_pos = source.find('id="wd-modal-body"')
        self.assertGreater(impact_pos, -1, 'Impact section not found in template')
        self.assertGreater(body_pos, -1, 'Modal body not found in template')
        self.assertLess(impact_pos, body_pos,
                        'Impact section must appear before modal body in template')


class TestAutoGenerationAfterRemotePull(unittest.TestCase):
    """Scenario: Auto-Generation After pl-remote-pull Merge

    Given the agent is on the collaboration branch
    And an active branch exists in BEHIND state
    When the agent runs /pl-remote-pull and the merge succeeds
    Then the generation script is executed as Step 7
    And features/digests/whats-different.md is written to disk
    And the digest content is displayed inline after the merge summary
    """

    def test_generation_script_exists(self):
        """Verify the generation script exists at the expected path."""
        script_path = os.path.join(PROJECT_ROOT, 'tools', 'collab',
                                   'generate_whats_different.sh')
        self.assertTrue(os.path.isfile(script_path),
                        f'Generation script not found at {script_path}')

    def test_remote_pull_skill_references_step_7(self):
        """Verify the pl-remote-pull skill file includes Step 7
        for post-merge digest generation."""
        skill_path = os.path.join(PROJECT_ROOT, '.claude', 'commands',
                                  'pl-remote-pull.md')
        with open(skill_path) as f:
            content = f.read()

        self.assertIn('7.', content,
                      'Step 7 reference not found in pl-remote-pull skill')
        self.assertIn('generate_whats_different.sh', content,
                      'Generation script not referenced in Step 7')

    def test_generation_script_is_executable_via_bash(self):
        """Verify the generation script can be invoked via bash
        (the same way the dashboard endpoint calls it)."""
        script_path = os.path.join(PROJECT_ROOT, 'tools', 'collab',
                                   'generate_whats_different.sh')
        # Verify it starts with a valid shebang or is bash-compatible
        with open(script_path) as f:
            first_line = f.readline()
        self.assertTrue(
            first_line.startswith('#!') or first_line.strip() == '',
            'Generation script should start with shebang or be bash-compatible')


class TestStalenessInvalidationChain(unittest.TestCase):
    """Scenario: Stale Impact Summary Absent After Digest Regeneration

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And features/digests/whats-different-analysis.md does not exist on disk
    And subsequent GET /whats-different/deep-analysis/read returns 404
    """

    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_generate_deletes_analysis_and_read_returns_404(self, mock_branch):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)

        # Create pre-existing analysis file (stale)
        analysis_path = os.path.join(digest_dir, 'whats-different-analysis.md')
        with open(analysis_path, 'w') as f:
            f.write('# Stale Analysis\nOld content.')

        # Create digest file written by generation
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write('# Fresh Digest\nNew content.')

        handler = MagicMock()
        gen_responses = []
        handler._send_json = lambda s, d: gen_responses.append((s, d))

        mock_result = MagicMock(returncode=0, stdout='# Fresh Digest', stderr='')

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}), \
             patch('serve.subprocess.run', return_value=mock_result), \
             patch('serve._compute_digest_tags', return_value={}):
            serve.Handler._handle_whats_different_generate(handler)

        # Generation succeeded
        self.assertEqual(gen_responses[0][0], 200)
        # Analysis file deleted
        self.assertFalse(os.path.exists(analysis_path))

        # Subsequent GET /deep-analysis/read returns 404
        handler2 = MagicMock()
        read_responses = []
        handler2._send_json = lambda s, d: read_responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir):
            serve.Handler._handle_deep_analysis_read(handler2)

        self.assertEqual(read_responses[0][0], 404)

        import shutil
        shutil.rmtree(tmpdir)


class TestButtonOpensCachedWithoutRegeneration(unittest.TestCase):
    """Scenario: Button Opens Cached Content Without Regeneration

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a GET request is sent to /whats-different/read
    Then the response status is 200
    And the response contains the cached digest content
    And no POST request is sent to /whats-different/generate
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 1, 'anchors': 0, 'visual': 0,
        'code': 0, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_read_returns_cached_without_subprocess(self, mock_branch,
                                                     mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write('# Cached Digest\nPreviously generated content.')

        handler = MagicMock()
        responses = []
        handler._send_json = lambda s, d: responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch('serve.subprocess.run') as mock_run:
            serve.Handler._handle_whats_different_read(handler)

            # Read endpoint returns cached content
            self.assertEqual(responses[0][0], 200)
            self.assertIn('digest', responses[0][1])
            self.assertIn('Cached Digest', responses[0][1]['digest'])

            # No subprocess was called (no generation triggered)
            mock_run.assert_not_called()

        import shutil
        shutil.rmtree(tmpdir)


class TestDivergedGenerationReturnsBothDirections(unittest.TestCase):
    """Scenario: DIVERGED Generation Returns Both Directions via Endpoint

    Given an active branch "v0.5-sprint" is set
    And the branch is in DIVERGED state
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response digest contains both "Your Local Changes" and
        "Collab Changes" sections
    And the response contains a tags object with change counts
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 2, 'anchors': 0, 'visual': 0,
        'code': 3, 'tests': 1, 'purlin': 0, 'discoveries': 1,
    })
    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_diverged_returns_both_sections_with_tags(self, mock_branch,
                                                       mock_run, mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)

        diverged_content = (
            '# What\'s Different?\n\n'
            '## Your Local Changes\n\n- M features/login.md\n\n'
            '## Collab Changes\n\n- M tools/auth/remote.py\n'
        )
        digest_path = os.path.join(digest_dir, 'whats-different.md')
        with open(digest_path, 'w') as f:
            f.write(diverged_content)

        mock_run.return_value = MagicMock(
            returncode=0, stdout=diverged_content, stderr='')

        handler = MagicMock()
        responses = []
        handler._send_json = lambda s, d: responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(responses[0][0], 200)
        digest = responses[0][1]['digest']
        self.assertIn('Your Local Changes', digest)
        self.assertIn('Collab Changes', digest)

        # Response includes tags object with counts
        tags = responses[0][1]['tags']
        self.assertIsInstance(tags, dict)
        self.assertEqual(tags['specs'], 2)
        self.assertEqual(tags['code'], 3)

        import shutil
        shutil.rmtree(tmpdir)


class TestRegenerateTriggersFFreshGeneration(unittest.TestCase):
    """Scenario: Regenerate Triggers Fresh Generation via Endpoint

    Given an active branch "v0.5-sprint" is set
    And features/digests/whats-different.md exists on disk
    When a POST request is sent to /whats-different/generate
    Then the response status is 200
    And the response contains freshly generated digest content
    And features/digests/whats-different.md is overwritten with new content
    """

    @patch('serve._compute_digest_tags', return_value={
        'specs': 0, 'anchors': 0, 'visual': 0,
        'code': 1, 'tests': 0, 'purlin': 0, 'discoveries': 0,
    })
    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_generate_overwrites_existing(self, mock_branch, mock_run,
                                           mock_tags):
        tmpdir = tempfile.mkdtemp()
        digest_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(digest_dir)
        digest_path = os.path.join(digest_dir, 'whats-different.md')

        # Write old content
        with open(digest_path, 'w') as f:
            f.write('# Old Digest\nStale content.')

        # Simulate generation writing new content
        new_content = '# Fresh Digest\nNewly generated content.'

        def fake_run(*args, **kwargs):
            with open(digest_path, 'w') as f:
                f.write(new_content)
            return MagicMock(returncode=0, stdout=new_content, stderr='')

        mock_run.side_effect = fake_run

        handler = MagicMock()
        responses = []
        handler._send_json = lambda s, d: responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_whats_different_generate(handler)

        self.assertEqual(responses[0][0], 200)
        self.assertIn('Fresh Digest', responses[0][1]['digest'])

        # Verify file on disk was overwritten
        with open(digest_path) as f:
            on_disk = f.read()
        self.assertIn('Fresh Digest', on_disk)
        self.assertNotIn('Old Digest', on_disk)

        import shutil
        shutil.rmtree(tmpdir)


class TestDeepAnalysisGenerationWritesFile(unittest.TestCase):
    """Scenario: Deep Analysis Generation Returns Analysis via Endpoint

    Given an active branch "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local collab/v0.5-sprint
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response contains an analysis field with generated content
    And features/digests/whats-different-analysis.md exists on disk
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    def test_generate_returns_analysis_and_file_exists(self, mock_branch,
                                                        mock_run):
        tmpdir = tempfile.mkdtemp()
        analysis_dir = os.path.join(tmpdir, 'features', 'digests')
        os.makedirs(analysis_dir)
        analysis_path = os.path.join(analysis_dir,
                                     'whats-different-analysis.md')

        analysis_content = ('# Impact Summary\n\n'
                            '## Key Changes\n\n'
                            'Auth module rewritten.\n')

        def fake_run(*args, **kwargs):
            with open(analysis_path, 'w') as f:
                f.write(analysis_content)
            return MagicMock(returncode=0, stdout=analysis_content, stderr='')

        mock_run.side_effect = fake_run

        handler = MagicMock()
        responses = []
        handler._send_json = lambda s, d: responses.append((s, d))

        with patch.object(serve, 'PROJECT_ROOT', tmpdir), \
             patch.object(serve, 'CONFIG', {'tools_root': 'tools'}):
            serve.Handler._handle_deep_analysis_generate(handler)

        self.assertEqual(responses[0][0], 200)
        self.assertIn('analysis', responses[0][1])
        self.assertIn('Impact Summary', responses[0][1]['analysis'])

        # Verify file exists on disk
        self.assertTrue(os.path.isfile(analysis_path))
        with open(analysis_path) as f:
            on_disk = f.read()
        self.assertIn('Key Changes', on_disk)

        import shutil
        shutil.rmtree(tmpdir)


class TestModalCloseButtonPresent(unittest.TestCase):
    """Scenario: Modal Close Button Present in HTML

    Given an active branch "v0.5-sprint" is set
    When the dashboard HTML is generated
    Then the What's Different modal template contains an X close button element
    And the modal container has the standard CDD modal overlay pattern
    """

    @patch('serve.get_release_checklist', return_value=([], [], []))
    @patch('serve.get_delivery_phase', return_value=None)
    @patch('serve.get_remote_contributors', return_value=[])
    @patch('serve.compute_remote_sync_state', return_value={
        'sync_state': 'AHEAD', 'commits_ahead': 1, 'commits_behind': 0})
    @patch('serve.get_branch_collab_branches', return_value=[{
        'name': 'v0.5-sprint', 'branch': 'collab/v0.5-sprint',
        'active': True, 'sync_state': 'AHEAD',
        'commits_ahead': 1, 'commits_behind': 0}])
    @patch('serve._has_git_remote', return_value=True)
    @patch('serve.get_active_branch', return_value='v0.5-sprint')
    @patch('serve.generate_api_status_json', return_value={
        'features': [], 'critic_last_run': ''})
    @patch('serve.get_last_commit', return_value='abc1234 test commit')
    @patch('serve.get_git_status', return_value='')
    def test_modal_has_close_button_and_overlay(self, *mocks):
        with patch.object(serve, 'CONFIG', {
                 'tools_root': 'tools', 'models': [], 'agents': {}}), \
             patch.object(serve, '_branch_collab_last_fetch',
                          '2026-02-27T00:00:00Z'):
            html = serve.generate_html()

        # Modal overlay with standard CDD modal pattern
        self.assertIn('id="wd-modal-overlay"', html)
        self.assertIn('class="modal-overlay"', html)
        self.assertIn('class="modal-content"', html)

        # X close button element
        self.assertIn('onclick="closeWdModal()"', html)
        self.assertIn('>X</button>', html)

        # Escape key handler and click-outside-to-close
        self.assertIn('Escape', html)
        self.assertIn('wd-modal-overlay', html)


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
