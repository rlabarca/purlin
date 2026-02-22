"""Tests for CDD Dashboard Model Configuration (cdd_model_configuration.md).

Tests the Models section rendering, badge logic, API endpoints,
and HTML structure. Produces tests/cdd_model_configuration/tests.json.
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
        self.assertIn('models-section', html)
        self.assertIn('models-rows', html)
        # Detect Providers button should NOT exist
        self.assertNotIn('Detect Providers', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_has_chevron(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('models-section-chevron', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_badge(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('models-section-badge', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_models_section_collapsed_by_default(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The models section body should have 'collapsed' class
        self.assertIn('class="section-body collapsed" id="models-section"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_heading_says_models(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('<h3>Models</h3>', html)

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
        self.assertIn('> YOLO', html)
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
        self.assertIn('diffUpdateModelRows', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_init_models_section_does_diff_check(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # initModelsSection should compare JSON before deciding to render
        self.assertIn('JSON.stringify(cfg.agents)', html)
        self.assertIn('configChanged', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_init_models_section_restores_from_cache(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # initModelsSection should synchronously restore from modelsConfig cache
        # when DOM is empty (after innerHTML replacement)
        self.assertIn("modelsConfig && !document.getElementById('agent-model-architect')", html)


class TestConfigModelsEndpoint(unittest.TestCase):
    """Scenario: Config Changes Persist via API"""

    def _make_handler(self, body_dict):
        from serve import Handler
        handler = Handler.__new__(Handler)
        body = json.dumps(body_dict).encode('utf-8')
        handler.path = '/config/models'
        handler.requestline = 'POST /config/models HTTP/1.1'
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
        # The models section should be included in localStorage persistence
        self.assertIn("'models-section'", html)
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
        # diffUpdateModelRows should check pendingWrites before updating each control
        self.assertIn("pendingWrites.has(role + '.model')", html)
        self.assertIn("pendingWrites.has(role + '.effort')", html)
        self.assertIn("pendingWrites.has(role + '.bypass_permissions')", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_save_clears_pending_writes(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # saveModelConfig must clear pendingWrites on success and error
        self.assertIn('pendingWrites.clear()', html)

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
        # applyPendingWrites must exist and be called after renderModelsRows
        self.assertIn('function applyPendingWrites()', html)
        # Must be called in both sync and async render paths of initModelsSection
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


# =============================================================================
# Test runner: writes results to tests/cdd_model_configuration/tests.json
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
    tests_dir = os.path.join(project_root, 'tests', 'cdd_model_configuration')
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
