#!/usr/bin/env python3
"""Tests for the What's Different dashboard integration.

Covers automated scenarios from features/collab_whats_different.md:
- Dashboard Endpoint Returns 400 When No Active Session
- Dashboard Endpoint Returns 200 After Generation
- Dashboard HTML Includes Button When Sync State Is Not SAME
- Dashboard HTML Omits Button When Sync State Is SAME
- Dashboard HTML Omits Button When No Active Session
- Generated Markdown File Exists After Generation
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


if __name__ == '__main__':
    unittest.main()
