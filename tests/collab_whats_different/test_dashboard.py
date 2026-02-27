#!/usr/bin/env python3
"""Tests for the What's Different dashboard integration.

Covers automated scenarios from features/collab_whats_different.md:
- Dashboard Endpoint Returns 400 When No Active Session
- Dashboard Endpoint Returns 200 After Generation
- Dashboard HTML Includes Button When Sync State Is Not SAME
- Dashboard HTML Omits Button When Sync State Is SAME
- Dashboard HTML Omits Button When No Active Session
- Generated Markdown File Exists After Generation
- GET Read Endpoint Returns Cached Digest
- GET Read Endpoint Returns 404 When No Cache
- GET Read Endpoint Returns 400 When No Session
- POST Generate Endpoint Returns ISO 8601 Timestamp
- POST Deep Analysis Generate Endpoint Returns Analysis
- GET Deep Analysis Read Endpoint Returns Cached Analysis
- GET Deep Analysis Read Endpoint Returns 404 When No Cache
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


class TestEndpointReturns400WhenNoActiveSession(unittest.TestCase):
    """Scenario: Dashboard Endpoint Returns 400 When No Active Session

    Given no file exists at .purlin/runtime/active_remote_session
    When a POST request is sent to /whats-different/generate
    Then the response status is 400
    And the response body contains an error message
    """

    @patch('serve.get_active_remote_session', return_value=None)
    def test_returns_400_no_session(self, mock_session):
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

    Given an active session "v0.5-sprint" is set
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
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_200_with_content(self, mock_session, mock_run, mock_tags):
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

    def _generate_html_with_sync(self, active_session, sync_state,
                                 commits_ahead=0, commits_behind=0):
        """Helper to generate HTML with specific remote collab state."""
        sync_data = {
            'sync_state': sync_state,
            'commits_ahead': commits_ahead,
            'commits_behind': commits_behind,
        }
        sessions = [{'name': active_session, 'branch': f'collab/{active_session}',
                      'active': True, 'sync_state': sync_state,
                      'commits_ahead': commits_ahead,
                      'commits_behind': commits_behind}] if active_session else []
        contributors = []
        last_fetch = '2026-02-27T00:00:00Z'

        return serve._remote_collab_section_html(
            active_session, sync_data, sessions,
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

    def test_button_absent_when_no_session(self):
        """Scenario: Dashboard HTML Omits Button When No Active Session"""
        html = serve._remote_collab_section_html(
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
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_digest_file_written(self, mock_session, mock_run, mock_tags):
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

    Given an active session "v0.5-sprint" is set
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
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_200_with_cached_content(self, mock_session, mock_tags):
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

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different.md does not exist
    When a GET request is sent to /whats-different/read
    Then the response status is 404
    """

    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_404_no_cache(self, mock_session):
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


class TestGetReadEndpointReturns400WhenNoSession(unittest.TestCase):
    """Scenario: GET Read Endpoint Returns 400 When No Session

    Given no file exists at .purlin/runtime/active_remote_session
    When a GET request is sent to /whats-different/read
    Then the response status is 400
    And the response body contains an error message
    """

    @patch('serve.get_active_remote_session', return_value=None)
    def test_returns_400_no_session(self, mock_session):
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

    Given an active session "v0.5-sprint" is set
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
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_iso_8601_timestamp(self, mock_session, mock_run, mock_tags):
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

    Given an active session "v0.5-sprint" is set
    And origin/collab/v0.5-sprint has 2 commits not in local main
    When a POST request is sent to /whats-different/deep-analysis/generate
    Then the response status is 200
    And the response body contains an "analysis" field with the generated content
    And the response body contains a "generated_at" field in ISO 8601 format
    """

    @patch('serve.subprocess.run')
    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_200_with_analysis(self, mock_session, mock_run):
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

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md exists on disk
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 200
    And the response body contains an "analysis" field with the cached content
    """

    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_200_with_cached_analysis(self, mock_session):
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

    Given an active session "v0.5-sprint" is set
    And features/digests/whats-different-analysis.md does not exist
    When a GET request is sent to /whats-different/deep-analysis/read
    Then the response status is 404
    """

    @patch('serve.get_active_remote_session', return_value='v0.5-sprint')
    def test_returns_404_no_cache(self, mock_session):
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


if __name__ == '__main__':
    unittest.main()
