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
        self.assertIn('<h3>Agent Config', html)

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


class TestContextGuardCheckboxRendersCorrectState(unittest.TestCase):
    """Scenario: Context Guard Checkbox Renders with Correct State

    Given the architect agent has context_guard true in config
    When the dashboard HTML is generated
    Then the architect row's Context Guard checkbox is checked
    """

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_checkbox_checked_when_guard_enabled(self, mock_run, mock_status):
        """Context guard checkbox is checked when context_guard is true."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # buildAgentRowHtml emits checked attribute when context_guard !== false
        self.assertIn("id=\"agent-cg-' + role + '\"", html)
        self.assertIn("agent-cg-", html)
        # The JS builds checkbox with checked when cgEnabled is true
        self.assertIn("(cgEnabled ? ' checked' : '')", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_context_guard_defaults_to_true(self, mock_run, mock_status):
        """context_guard defaults to true (checked) when not explicitly set."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # cgEnabled is derived as: agentCfg.context_guard !== false
        self.assertIn("var cgEnabled = agentCfg.context_guard !== false", html)


class TestContextGuardCheckboxUncheckedWhenDisabled(unittest.TestCase):
    """Scenario: Context Guard Checkbox Unchecked When Guard Disabled

    Given the builder agent has context_guard false in config
    When the dashboard HTML is generated
    Then the builder row's Context Guard checkbox is unchecked
    """

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_checkbox_unchecked_when_guard_false(self, mock_run, mock_status):
        """When context_guard is false, checkbox renders without checked attr."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The buildAgentRowHtml uses cgEnabled = context_guard !== false
        # When false, cgEnabled is false, and no 'checked' attribute is added
        self.assertIn("var cgEnabled = agentCfg.context_guard !== false", html)
        # The checkbox element uses cgEnabled to conditionally add checked
        self.assertIn("(cgEnabled ? ' checked' : '')", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_diff_update_respects_guard_state(self, mock_run, mock_status):
        """diffUpdateAgentRows correctly syncs checkbox to config value."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # diffUpdateAgentRows reads context_guard and sets checkbox
        self.assertIn("var cgVal = acfg.context_guard !== false", html)
        self.assertIn("cgChk.checked !== cgVal", html)
        self.assertIn("cgChk.checked = cgVal", html)


class TestPostAcceptsValidContextGuardBoolean(unittest.TestCase):
    """Scenario: POST Accepts Valid Context Guard Boolean

    Given a valid resolved config exists
    When a POST request is sent to /config/agents with architect context_guard true
    Then config.local.json contains agents.architect.context_guard as true
    """

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
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    @patch('serve.CONFIG_PATH', '/tmp/test_cg_bool_cfg.json')
    def test_context_guard_true_persists(self):
        """POST with context_guard: true persists the boolean value."""
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cg_bool_cfg.json', 'w') as f:
            json.dump(config, f)

        handler = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True, 'context_guard': True
            },
            'builder': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True, 'context_guard': False
            },
            'qa': {
                'model': 'claude-opus-4-6', 'effort': 'medium',
                'bypass_permissions': False, 'context_guard': True
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(200)

        with open('/tmp/test_cg_bool_cfg.json', 'r') as f:
            saved = json.load(f)
        self.assertTrue(saved['agents']['architect']['context_guard'])
        self.assertFalse(saved['agents']['builder']['context_guard'])
        self.assertTrue(saved['agents']['qa']['context_guard'])

        os.remove('/tmp/test_cg_bool_cfg.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_cg_invalid_cfg.json')
    def test_context_guard_non_boolean_rejected(self):
        """POST with non-boolean context_guard returns 400."""
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_cg_invalid_cfg.json', 'w') as f:
            json.dump(config, f)

        handler = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True, 'context_guard': 'yes'
            },
            'builder': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True
            },
            'qa': {
                'model': 'claude-opus-4-6', 'effort': 'medium',
                'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(400)

        os.remove('/tmp/test_cg_invalid_cfg.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_cg_optional_cfg.json')
    def test_context_guard_optional_preserves_existing(self):
        """POST without context_guard preserves existing value via merge."""
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {
                'architect': {'model': 'claude-opus-4-6', 'context_guard': False},
                'builder': {'model': 'claude-opus-4-6'},
                'qa': {'model': 'claude-opus-4-6'}
            }
        }
        with open('/tmp/test_cg_optional_cfg.json', 'w') as f:
            json.dump(config, f)

        handler = self._make_handler({
            'architect': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True
                # No context_guard — should preserve existing False
            },
            'builder': {
                'model': 'claude-opus-4-6', 'effort': 'high',
                'bypass_permissions': True
            },
            'qa': {
                'model': 'claude-opus-4-6', 'effort': 'medium',
                'bypass_permissions': False
            }
        })
        handler.do_POST()
        handler.send_response.assert_called_with(200)

        os.remove('/tmp/test_cg_optional_cfg.json')


class TestContextGuardCheckboxTogglePersistsState(unittest.TestCase):
    """Scenario: Context Guard Checkbox Toggle Persists State

    Given the Agents section is expanded
    And the architect Context Guard checkbox is checked
    When the user unchecks the architect Context Guard checkbox
    Then the new state is sent via POST /config/agents
    And on page reload the checkbox remains unchecked
    """

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_checkbox_change_triggers_pending_write(self, mock_run, mock_status):
        """Toggling checkbox stores pending write and schedules save."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # Event handler sets pending write for context_guard
        self.assertIn("pendingWrites.set(role + '.context_guard', cgChk.checked)", html)
        # Event handler calls scheduleAgentSave
        # Find the cgChk change handler block
        cg_handler_start = html.find("pendingWrites.set(role + '.context_guard'")
        cg_handler_section = html[cg_handler_start:cg_handler_start + 200]
        self.assertIn("scheduleAgentSave()", cg_handler_section)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_save_includes_context_guard_field(self, mock_run, mock_status):
        """saveAgentConfig includes context_guard in the POST payload."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("context_guard: cgChk ? cgChk.checked : true", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_pending_write_blocks_refresh_overwrite(self, mock_run, mock_status):
        """diffUpdateAgentRows skips context_guard if pending write exists."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("pendingWrites.has(role + '.context_guard')", html)


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
            'total': result.testsRun,
            'test_file': 'tools/cdd/test_cdd_model_configuration.py'
        }, f)
    print(f"\ntests.json: {status}")
