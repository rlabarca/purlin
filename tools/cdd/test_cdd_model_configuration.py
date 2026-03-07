"""Tests for CDD Dashboard Agent Configuration (cdd_agent_configuration.md).

Tests the Agents section rendering, badge logic, API endpoints,
and HTML structure. Produces tests/cdd_agent_configuration/tests.json.
"""
import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure serve module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve


class TestModelsBadgeGrouping(unittest.TestCase):
    """Scenario: Collapsed Badge Shows Grouped Model Summary"""

    def test_uniform_badge(self):
        """All agents same model -> '3x Sonnet 4.6'"""
        config = {
            'models': [
                {'id': 'claude-sonnet-4-6', 'label': 'Sonnet 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {
                'architect': {'model': 'claude-sonnet-4-6'},
                'builder': {'model': 'claude-sonnet-4-6'},
                'qa': {'model': 'claude-sonnet-4-6'},
            }
        }
        from collections import Counter
        models_list = config['models']
        agents = config['agents']
        roles = ['architect', 'builder', 'qa']
        labels = []
        for role in roles:
            acfg = agents.get(role, {})
            mid = acfg.get('model', '')
            lbl = next((m.get('label', mid) for m in models_list if m.get('id') == mid), mid or '?')
            labels.append(lbl)
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '3x Sonnet 4.6')

    def test_grouped_badge(self):
        """Two groups -> '2x Sonnet 4.6 | 1x Opus 4.6'"""
        from collections import Counter
        labels = ['Opus 4.6', 'Sonnet 4.6', 'Sonnet 4.6']
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '2x Sonnet 4.6 | 1x Opus 4.6')

    def test_all_different_badge(self):
        """Three different -> sorted by count desc then alpha"""
        from collections import Counter
        labels = ['Opus 4.6', 'Sonnet 4.6', 'Haiku 4.5']
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '1x Haiku 4.5 | 1x Opus 4.6 | 1x Sonnet 4.6')


class TestModelsSectionHtmlStructure(unittest.TestCase):
    """Scenario: Models Section Displays Current Config"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_exists(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('agents-section', html)
        self.assertIn('agents-rows', html)
        # Detect Providers button should NOT exist
        self.assertNotIn('Detect Providers', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_has_chevron(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('agents-section-chevron', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_badge(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('agents-section-badge', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_collapsed_by_default(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The agents section body should have 'collapsed' class
        self.assertIn('class="section-body collapsed" id="agents-section"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_heading_says_models(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('<h3>Agent Config ', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_no_provider_select(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertNotIn('agent-provider-', html)


class TestModelsCssGrid(unittest.TestCase):
    """Scenario: Column Alignment via CSS Grid"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_grid_layout(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('display:grid', html)
        self.assertIn('grid-template-columns', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_agent_label_uses_primary_color(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('.agent-lbl', html)
        self.assertIn('color:var(--purlin-primary)', html)
        # Must NOT use accent for agent labels
        import re
        agent_lbl_rule = re.search(r'\.agent-lbl\{[^}]+\}', html)
        self.assertIsNotNone(agent_lbl_rule)
        self.assertIn('--purlin-primary', agent_lbl_rule.group())
        self.assertNotIn('--purlin-accent', agent_lbl_rule.group())


class TestYoloCheckbox(unittest.TestCase):
    """Scenario: YOLO checkbox label and direct mapping logic"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_yolo_label_in_js(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # YOLO label appears in column header, not as an inline label
        self.assertIn('YOLO', html)
        self.assertNotIn('> Bypass<', html)
        self.assertNotIn('Ask Permission', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_direct_bypass_logic_in_save(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # YOLO checked = bypass_permissions: true (direct, no inversion)
        self.assertIn('bypassChk.checked', html)
        self.assertNotIn('!bypassChk.checked', html)


class TestVisibilityHiddenForCapabilityGating(unittest.TestCase):
    """Scenario: Capability-Aware Control Visibility"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_visibility_hidden_in_js(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # syncCapabilityControls should use visibility not display
        self.assertIn("visibility = caps.effort ? 'visible' : 'hidden'", html)
        self.assertIn("visibility = caps.permissions ? 'visible' : 'hidden'", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_initial_html_uses_visibility_hidden(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # buildAgentRowHtml should use visibility:hidden not display:none
        self.assertIn("style=\"visibility:hidden\"", html)
        self.assertNotIn("style=\"display:none\"", html.split('agent-effort')[1].split('</select>')[0])


class TestFlickerFreeRefresh(unittest.TestCase):
    """Scenario: Flicker-free updates via diff-based rendering"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_diff_function_exists(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('diffUpdateAgentRows', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_init_models_section_does_diff_check(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # initAgentsSection should compare JSON before deciding to render
        self.assertIn('JSON.stringify(cfg.agents)', html)
        self.assertIn('configChanged', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_init_models_section_restores_from_cache(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # initAgentsSection should synchronously restore from agentsConfig cache
        # when DOM is empty (after innerHTML replacement)
        self.assertIn("agentsConfig && !document.getElementById('agent-model-architect')", html)


class TestConfigModelsEndpoint(unittest.TestCase):
    """Scenario: Config Changes Persist via API"""

    def _make_handler(self, body_dict):
        from serve import Handler
        handler = Handler.__new__(Handler)
        body = json.dumps(body_dict).encode('utf-8')
        handler.path = '/config/agents'
        handler.requestline = 'POST /config/agents HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        headers_sent = []
        def mock_send_header(key, value):
            headers_sent.append((key, value))
        handler.send_response = MagicMock()
        handler.send_header = mock_send_header
        handler.end_headers = MagicMock()
        return handler, headers_sent

    @patch('serve.CONFIG_PATH', '/tmp/test_cdd_model_cfg.json')
    def test_valid_agent_update(self):
        # Pre-seed config file with flat models array
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cdd_model_cfg.json', 'w') as f:
            json.dump(config, f)

        handler, _ = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6',
                'effort': 'high', 'bypass_permissions': False
            },
            'builder': {
                'model': 'claude-opus-4-6',
                'effort': 'high', 'bypass_permissions': True
            },
            'qa': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(200)
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertIn('agents', data)
        self.assertEqual(data['agents']['architect']['model'], 'claude-opus-4-6')
        # Response should NOT contain llm_providers
        self.assertNotIn('llm_providers', data)

        # Cleanup
        os.remove('/tmp/test_cdd_model_cfg.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_cdd_model_cfg_partial.json')
    def test_partial_payload_rejected(self):
        """Completeness check: payload missing roles returns 400."""
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cdd_model_cfg_partial.json', 'w') as f:
            json.dump(config, f)

        handler, _ = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6',
                'effort': 'high', 'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(400)
        body = handler.wfile.getvalue()
        data = json.loads(body)
        self.assertIn('all three roles', data.get('error', ''))

        os.remove('/tmp/test_cdd_model_cfg_partial.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_cdd_model_cfg2.json')
    def test_invalid_effort_returns_400(self):
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cdd_model_cfg2.json', 'w') as f:
            json.dump(config, f)

        handler, _ = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6',
                'effort': 'extreme', 'bypass_permissions': False
            },
            'builder': {
                'model': 'claude-opus-4-6',
                'effort': 'high', 'bypass_permissions': True
            },
            'qa': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(400)

        os.remove('/tmp/test_cdd_model_cfg2.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_cdd_model_cfg3.json')
    def test_unknown_model_returns_400(self):
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cdd_model_cfg3.json', 'w') as f:
            json.dump(config, f)

        handler, _ = self._make_handler({
            'architect': {
                'model': 'nonexistent-model',
                'effort': 'high', 'bypass_permissions': False
            },
            'builder': {
                'model': 'claude-opus-4-6',
                'effort': 'high', 'bypass_permissions': True
            },
            'qa': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(400)

        os.remove('/tmp/test_cdd_model_cfg3.json')


class TestSectionPersistence(unittest.TestCase):
    """Scenario: Models Section State Persists Across Reloads"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_localstorage_section_persistence(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The agents section should be included in localStorage persistence
        self.assertIn("'agents-section'", html)
        self.assertIn('purlin-section-states', html)


class TestPendingWriteLock(unittest.TestCase):
    """Scenario: Pending Change is Not Overwritten by Auto-Refresh"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_pending_writes_map_exists(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('var pendingWrites = new Map()', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_diff_update_checks_pending_writes(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # diffUpdateAgentRows should check pendingWrites before updating each control
        self.assertIn("pendingWrites.has(role + '.model')", html)
        self.assertIn("pendingWrites.has(role + '.effort')", html)
        self.assertIn("pendingWrites.has(role + '.bypass_permissions')", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_save_releases_sent_pending_writes(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # saveAgentConfig must release only sent keys (per-request lock association)
        self.assertIn('sentKeys.forEach', html)
        self.assertIn('pendingWrites.delete(k)', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_event_handlers_store_values_in_pending_writes(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # Event handlers should store values via Map.set()
        self.assertIn("pendingWrites.set(role + '.model',", html)
        self.assertIn("pendingWrites.set(role + '.bypass_permissions',", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_apply_pending_writes_restores_after_render(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # applyPendingWrites must exist and be called after renderAgentsRows
        self.assertIn('function applyPendingWrites()', html)
        # Must be called in both sync and async render paths of initAgentsSection
        import re
        calls = [m.start() for m in re.finditer(r'applyPendingWrites\(\)', html)]
        # At least 3: function def + sync path + async path
        self.assertGreaterEqual(len(calls), 3)


class TestSectionVisualSeparation(unittest.TestCase):
    """Scenario: Models Section is Visually Separated from Workspace"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_section_heading_has_border(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # section-hdr h3 must have border-bottom
        import re
        h3_rule = re.search(r'\.section-hdr h3\{[^}]+\}', html)
        self.assertIsNotNone(h3_rule)
        self.assertIn('border-bottom', h3_rule.group())


class TestContextGuardCountersEndpoint(unittest.TestCase):
    """Scenario: GET /context-guard/counters returns per-role arrays"""

    def _make_handler(self):
        """Create a Handler instance with mocked socket internals."""
        handler = serve.Handler.__new__(serve.Handler)
        handler.wfile = io.BytesIO()
        handler._headers_buffer = []
        handler.request_version = 'HTTP/1.1'
        handler.requestline = 'GET /context-guard/counters HTTP/1.1'
        return handler

    @patch('serve.get_isolation_worktrees', return_value=[])
    def test_returns_per_role_arrays(self, mock_wt):
        """Live agents grouped by role with counts sorted ascending."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = os.path.join(tmpdir, '.purlin', 'runtime')
            os.makedirs(runtime)

            # Create turn_count and session_meta for current PID (guaranteed alive)
            pid = os.getpid()
            with open(os.path.join(runtime, f'turn_count_{pid}'), 'w') as f:
                f.write('5')
            with open(os.path.join(runtime, f'session_meta_{pid}'), 'w') as f:
                f.write(f'uuid-123\narchitect\n2026-01-01\n')

            with patch.object(serve, 'PROJECT_ROOT', tmpdir):
                handler = self._make_handler()
                handler._handle_context_guard_counters()

            handler.wfile.seek(0)
            raw = handler.wfile.read().decode('utf-8')
            # Extract JSON body (after headers)
            body = raw.split('\r\n\r\n', 1)[1]
            data = json.loads(body)
            self.assertEqual(data['architect'], [5])
            self.assertEqual(data['builder'], [])
            self.assertEqual(data['qa'], [])

    @patch('serve.get_isolation_worktrees', return_value=[])
    def test_dead_process_excluded(self, mock_wt):
        """Dead process counters excluded from response."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = os.path.join(tmpdir, '.purlin', 'runtime')
            os.makedirs(runtime)

            # Use PID 99999999 — almost certainly not running
            with open(os.path.join(runtime, 'turn_count_99999999'), 'w') as f:
                f.write('42')
            with open(os.path.join(runtime, 'session_meta_99999999'), 'w') as f:
                f.write('uuid\nbuilder\n2026-01-01\n')

            with patch.object(serve, 'PROJECT_ROOT', tmpdir):
                handler = self._make_handler()
                handler._handle_context_guard_counters()

            handler.wfile.seek(0)
            body = handler.wfile.read().decode('utf-8').split('\r\n\r\n', 1)[1]
            data = json.loads(body)
            self.assertEqual(data['builder'], [])

    @patch('serve.get_isolation_worktrees', return_value=[])
    def test_missing_session_meta_excluded(self, mock_wt):
        """Counter without session_meta is excluded."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = os.path.join(tmpdir, '.purlin', 'runtime')
            os.makedirs(runtime)

            pid = os.getpid()
            with open(os.path.join(runtime, f'turn_count_{pid}'), 'w') as f:
                f.write('10')
            # No session_meta file

            with patch.object(serve, 'PROJECT_ROOT', tmpdir):
                handler = self._make_handler()
                handler._handle_context_guard_counters()

            handler.wfile.seek(0)
            body = handler.wfile.read().decode('utf-8').split('\r\n\r\n', 1)[1]
            data = json.loads(body)
            # No role should contain 10
            for counts in data.values():
                self.assertNotIn(10, counts)

    @patch('serve.get_isolation_worktrees')
    def test_worktree_counters_included(self, mock_wt):
        """Worktree agent counters included in response."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Main runtime
            runtime = os.path.join(tmpdir, '.purlin', 'runtime')
            os.makedirs(runtime)
            pid = os.getpid()
            with open(os.path.join(runtime, f'turn_count_{pid}'), 'w') as f:
                f.write('20')
            with open(os.path.join(runtime, f'session_meta_{pid}'), 'w') as f:
                f.write(f'uuid\nbuilder\n2026-01-01\n')

            # Worktree runtime (same PID for simplicity — already alive)
            wt_runtime = os.path.join(tmpdir, '.worktrees', 'team-a',
                                      '.purlin', 'runtime')
            os.makedirs(wt_runtime)
            with open(os.path.join(wt_runtime, f'turn_count_{pid}'), 'w') as f:
                f.write('7')
            with open(os.path.join(wt_runtime, f'session_meta_{pid}'), 'w') as f:
                f.write(f'uuid2\nbuilder\n2026-01-01\n')

            mock_wt.return_value = [{'name': 'team-a'}]

            with patch.object(serve, 'PROJECT_ROOT', tmpdir):
                handler = self._make_handler()
                handler._handle_context_guard_counters()

            handler.wfile.seek(0)
            body = handler.wfile.read().decode('utf-8').split('\r\n\r\n', 1)[1]
            data = json.loads(body)
            self.assertEqual(data['builder'], [7, 20])  # sorted ascending

    @patch('serve.get_isolation_worktrees', return_value=[])
    def test_multiple_roles_sorted(self, mock_wt):
        """Multiple agents across roles, counts sorted ascending."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime = os.path.join(tmpdir, '.purlin', 'runtime')
            os.makedirs(runtime)

            pid = os.getpid()
            # Use current PID for one, parent PID for another (both alive)
            ppid = os.getppid()
            with open(os.path.join(runtime, f'turn_count_{pid}'), 'w') as f:
                f.write('30')
            with open(os.path.join(runtime, f'session_meta_{pid}'), 'w') as f:
                f.write(f'uuid\nbuilder\n2026-01-01\n')
            with open(os.path.join(runtime, f'turn_count_{ppid}'), 'w') as f:
                f.write('5')
            with open(os.path.join(runtime, f'session_meta_{ppid}'), 'w') as f:
                f.write(f'uuid2\nbuilder\n2026-01-01\n')

            with patch.object(serve, 'PROJECT_ROOT', tmpdir):
                handler = self._make_handler()
                handler._handle_context_guard_counters()

            handler.wfile.seek(0)
            body = handler.wfile.read().decode('utf-8').split('\r\n\r\n', 1)[1]
            data = json.loads(body)
            self.assertEqual(data['builder'], [5, 30])


class TestContextGuardCounterFrontend(unittest.TestCase):
    """Frontend JS for live counter display."""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_counter_span_in_agent_row(self, mock_run, mock_status):
        """Counter span exists in agent row HTML (JS template)."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # buildAgentRowHtml generates spans dynamically: 'agent-cg-counter-' + role
        self.assertIn("agent-cg-counter-' + role + '", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_refresh_function_exists(self, mock_run, mock_status):
        """refreshContextGuardCounters function is defined."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("function refreshContextGuardCounters()", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_refresh_interval_set(self, mock_run, mock_status):
        """5-second refresh interval is configured."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("setInterval(refreshContextGuardCounters, 5000)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_counter_fetches_endpoint(self, mock_run, mock_status):
        """Refresh function fetches /context-guard/counters."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("fetch('/context-guard/counters')", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_counter_styling(self, mock_run, mock_status):
        """Counter span has correct monospace styling."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("font-family:monospace", html)
        self.assertIn("font-size:10px", html)


class TestCounterColorThresholds(unittest.TestCase):
    """Scenario: Counter Values Colored by Threshold Proximity"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_get_counter_color_function_exists(self, mock_run, mock_status):
        """getCounterColor helper function is defined in JS."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("function getCounterColor(count, role)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_render_colored_counts_function_exists(self, mock_run, mock_status):
        """renderColoredCounts helper function is defined in JS."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("function renderColoredCounts(counts, role)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_warning_threshold_at_80_percent(self, mock_run, mock_status):
        """Color logic uses 0.80 threshold for warning."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("threshold * 0.80", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_critical_threshold_at_92_percent(self, mock_run, mock_status):
        """Color logic uses 0.92 threshold for critical."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("threshold * 0.92", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_warning_uses_status_warning_token(self, mock_run, mock_status):
        """Warning zone uses --purlin-status-warning color."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("--purlin-status-warning", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_critical_uses_status_error_token(self, mock_run, mock_status):
        """Critical zone uses --purlin-status-error color."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("--purlin-status-error", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_disabled_guard_uses_muted(self, mock_run, mock_status):
        """Disabled context guard always returns --purlin-muted."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("context_guard === false", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_counter_uses_innerhtml_for_colored_spans(self, mock_run, mock_status):
        """Counter span updated via innerHTML (not textContent) for colored spans."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("span.innerHTML = renderColoredCounts(counts, role)", html)


class TestCollapsedContextGuardSummary(unittest.TestCase):
    """Scenario: Collapsed Summary Shows Active Agent Counts"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_span_exists(self, mock_run, mock_status):
        """agents-cg-summary span exists in HTML."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('id="agents-cg-summary"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_between_heading_and_badge(self, mock_run, mock_status):
        """Summary span appears before the badge span."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        summary_pos = html.find('agents-cg-summary')
        badge_pos = html.find('agents-section-badge')
        self.assertGreater(summary_pos, 0)
        self.assertGreater(badge_pos, summary_pos)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_update_function_exists(self, mock_run, mock_status):
        """updateCollapsedCgSummary function is defined."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("function updateCollapsedCgSummary(data)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_called_from_refresh(self, mock_run, mock_status):
        """refreshContextGuardCounters calls updateCollapsedCgSummary."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("updateCollapsedCgSummary(data)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_hidden_when_expanded(self, mock_run, mock_status):
        """toggleSection hides agents-cg-summary when section is expanded."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("agents-cg-summary", html)
        # Check that toggleSection handles cgSummary display
        self.assertIn("cgSummary) cgSummary.style.display = 'none'", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_uses_role_primary_color(self, mock_run, mock_status):
        """Role names in summary use --purlin-primary color."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("var(--purlin-primary)", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_summary_omits_empty_roles(self, mock_run, mock_status):
        """Summary logic checks counts.length === 0 to skip roles."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("counts.length === 0) return", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_apply_section_states_handles_summary(self, mock_run, mock_status):
        """applySectionStates also handles agents-cg-summary visibility."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("cgSum) cgSum.style.display = 'none'", html)


# =============================================================================
# Test runner: writes results to tests/cdd_agent_configuration/tests.json
# =============================================================================
if __name__ == '__main__':
    # Discover project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '../..'))
    env_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
    if env_root and os.path.isdir(env_root):
        project_root = env_root

    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    tests_dir = os.path.join(project_root, 'tests', 'cdd_agent_configuration')
    os.makedirs(tests_dir, exist_ok=True)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    status = 'PASS' if failed == 0 else 'FAIL'
    with open(os.path.join(tests_dir, 'tests.json'), 'w') as f:
        json.dump({
            'status': status,
            'passed': passed,
            'failed': failed,
            'total': result.testsRun
        }, f)
    print(f"\ntests.json: {status}")
