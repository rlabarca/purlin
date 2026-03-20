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
        """All agents same model -> '4x Sonnet 4.6'"""
        config = {
            'models': [
                {'id': 'claude-sonnet-4-6', 'label': 'Sonnet 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {
                'architect': {'model': 'claude-sonnet-4-6'},
                'builder': {'model': 'claude-sonnet-4-6'},
                'qa': {'model': 'claude-sonnet-4-6'},
                'pm': {'model': 'claude-sonnet-4-6'},
            }
        }
        from collections import Counter
        models_list = config['models']
        agents = config['agents']
        roles = ['architect', 'builder', 'qa', 'pm']
        labels = []
        for role in roles:
            acfg = agents.get(role, {})
            mid = acfg.get('model', '')
            lbl = next((m.get('label', mid) for m in models_list if m.get('id') == mid), mid or '?')
            labels.append(lbl)
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '4x Sonnet 4.6')

    def test_grouped_badge(self):
        """Two groups -> '3x Sonnet 4.6 | 1x Opus 4.6'"""
        from collections import Counter
        labels = ['Opus 4.6', 'Sonnet 4.6', 'Sonnet 4.6', 'Sonnet 4.6']
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '3x Sonnet 4.6 | 1x Opus 4.6')

    def test_all_different_badge(self):
        """Four different -> sorted by count desc then alpha"""
        from collections import Counter
        labels = ['Opus 4.6', 'Sonnet 4.6', 'Haiku 4.5', 'Sonnet 4.6']
        counts = Counter(labels)
        segments = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        badge = ' | '.join(f'{c}x {lbl}' for lbl, c in segments)
        self.assertEqual(badge, '2x Sonnet 4.6 | 1x Haiku 4.5 | 1x Opus 4.6')


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


class TestCapabilityGatedControlsHiddenInHTML(unittest.TestCase):
    """Scenario: Capability-Gated Controls Hidden in HTML When Capabilities Are False"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_capability_gated_controls_use_visibility_hidden(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # syncCapabilityControls should use visibility not display
        self.assertIn("visibility = caps.effort ? 'visible' : 'hidden'", html)
        self.assertIn("visibility = caps.permissions ? 'visible' : 'hidden'", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_capability_false_hides_controls_in_initial_html(self, mock_run, mock_status):
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
            },
            'pm': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': True
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
        self.assertIn('all four roles', data.get('error', ''))

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
            },
            'pm': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': True
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
            },
            'pm': {
                'model': 'claude-opus-4-6',
                'effort': 'medium', 'bypass_permissions': True
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


class TestFourAgentRowsInSpecOrder(unittest.TestCase):
    """Scenario: Agents Section Displays Four Agent Rows in Spec Order"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_js_roles_array_in_spec_order(self, mock_run, mock_status):
        """The JS roles array lists agents in spec order: PM, Architect, Builder, QA."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("['pm', 'architect', 'builder', 'qa']", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_js_builds_agent_row_with_model_effort_bypass(self, mock_run, mock_status):
        """buildAgentRowHtml creates model dropdown, effort dropdown, and bypass checkbox."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("'agent-model-' + role", html)
        self.assertIn("'agent-effort-' + role", html)
        self.assertIn("'agent-bypass-' + role", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_role_table_includes_pm_column(self, mock_run, mock_status):
        """The role status table header includes a PM column."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('>PM</th>', html)


class TestSectionVisualSeparation(unittest.TestCase):
    """Scenario: Agents Section Has Visual Separator in HTML"""

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

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_agents_section_has_16px_gap_from_workspace(self, mock_run, mock_status):
        """Visual gap of at least 16px separates Workspace from Agents section."""
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        import re
        # Find the ctx div wrapping the agents section
        match = re.search(r'<div class="ctx" style="margin-top:(\d+)px">\s*<div class="section-hdr" onclick="toggleSection\(\'agents-section\'\)">', html)
        self.assertIsNotNone(match, "Agents section wrapper not found")
        gap_px = int(match.group(1))
        self.assertGreaterEqual(gap_px, 16, f"Gap is {gap_px}px, expected at least 16px")


class TestModelWarningModalShown(unittest.TestCase):
    """Scenario: Selecting Model With Warning Shows Confirmation Modal"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_warning_modal_overlay_exists(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('id="mw-overlay"', html)
        self.assertIn('class="mw-overlay"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_warning_modal_has_title_and_body(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('Model Warning', html)
        self.assertIn('id="mw-body"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_warning_modal_has_buttons(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('I Understand', html)
        self.assertIn('Cancel', html)
        self.assertIn('id="mw-confirm"', html)
        self.assertIn('id="mw-cancel"', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_model_change_checks_warning(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The model change handler should check for warnings via getModelObj
        self.assertIn('getModelObj(newModel)', html)
        self.assertIn('showModelWarningModal', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_model_change_stores_prev_model(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('dataset.prevModel', html)


class TestModelWarningConfirm(unittest.TestCase):
    """Scenario: Modal 'I Understand' Commits Selection and Acknowledges Warning"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_confirm_posts_acknowledge(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn("'/config/acknowledge-warning'", html)
        self.assertIn('confirmModelWarning', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_confirm_schedules_save(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # After confirm, should commit the model change
        import re
        # confirmModelWarning should call scheduleAgentSave
        confirm_fn = re.search(r'function confirmModelWarning\(\)\s*\{.*?\n\}', html, re.DOTALL)
        self.assertIsNotNone(confirm_fn)
        self.assertIn('scheduleAgentSave()', confirm_fn.group())

    @patch('serve.CONFIG_PATH', '/tmp/test_ack_warning.json')
    def test_acknowledge_endpoint_adds_to_array(self):
        """POST /config/acknowledge-warning adds model ID to acknowledged_warnings."""
        config = {
            'models': [
                {'id': 'claude-opus-4-6[1m]', 'label': 'Opus 4.6 [1M]',
                 'warning': 'Extended context costs extra.',
                 'warning_dismissible': True,
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_ack_warning.json', 'w') as f:
            json.dump(config, f)

        handler = serve.Handler.__new__(serve.Handler)
        body = json.dumps({'model_id': 'claude-opus-4-6[1m]'}).encode('utf-8')
        handler.path = '/config/acknowledge-warning'
        handler.requestline = 'POST /config/acknowledge-warning HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        with patch('serve._resolve_config', return_value=config):
            handler.do_POST()
        handler.send_response.assert_called_with(200)
        response = json.loads(handler.wfile.getvalue())
        self.assertIn('claude-opus-4-6[1m]', response['acknowledged_warnings'])

        # Verify persisted to disk
        with open('/tmp/test_ack_warning.json') as f:
            saved = json.load(f)
        self.assertIn('claude-opus-4-6[1m]', saved.get('acknowledged_warnings', []))

        os.remove('/tmp/test_ack_warning.json')


class TestModelWarningCancel(unittest.TestCase):
    """Scenario: Modal 'Cancel' Reverts Model Selection"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_cancel_reverts_dropdown(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        import re
        cancel_fn = re.search(r'function cancelModelWarning\(\)\s*\{.*?\n\}', html, re.DOTALL)
        self.assertIsNotNone(cancel_fn)
        # Should revert to previous model value
        self.assertIn('mwPrevModelId', cancel_fn.group())
        self.assertIn('.value = mwPrevModelId', cancel_fn.group())

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_cancel_does_not_save(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        import re
        cancel_fn = re.search(r'function cancelModelWarning\(\)\s*\{.*?\n\}', html, re.DOTALL)
        self.assertIsNotNone(cancel_fn)
        # Cancel must NOT call scheduleAgentSave or pendingWrites.set
        self.assertNotIn('scheduleAgentSave', cancel_fn.group())
        self.assertNotIn('pendingWrites.set', cancel_fn.group())


class TestModelWarningAcknowledgedSkipsModal(unittest.TestCase):
    """Scenario: Acknowledged Model Does Not Trigger Modal on Reselection"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_isModelAcknowledged_function_exists(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('function isModelAcknowledged(modelId)', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_acknowledged_check_in_change_handler(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # Change handler should check isModelAcknowledged before showing modal
        self.assertIn('isModelAcknowledged(newModel)', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_acknowledged_checks_config_array(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # isModelAcknowledged should read from agentsConfig.acknowledged_warnings
        self.assertIn('acknowledged_warnings', html)


class TestNonDismissibleWarningShowsEveryTime(unittest.TestCase):
    """Scenario: Non-Dismissible Model Warning Shows Modal on Every Selection"""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_non_dismissible_uses_continue_button(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # confirmBtn.textContent should change based on dismissible flag
        self.assertIn("'Continue'", html)
        self.assertIn("'I Understand'", html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_non_dismissible_check_in_handler(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # The change handler should check warning_dismissible
        self.assertIn('warning_dismissible', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_non_dismissible_skips_acknowledge_post(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        import re
        confirm_fn = re.search(r'function confirmModelWarning\(\)\s*\{.*?\n\}', html, re.DOTALL)
        self.assertIsNotNone(confirm_fn)
        # Should conditionally post acknowledge only when dismissible
        self.assertIn('mwIsDismissible', confirm_fn.group())


class TestAcknowledgeWarningRejectsNonDismissible(unittest.TestCase):
    """Scenario: POST /config/acknowledge-warning Rejects Non-Dismissible Model Warnings"""

    @patch('serve.CONFIG_PATH', '/tmp/test_ack_nondismiss.json')
    def test_non_dismissible_returns_400(self):
        config = {
            'models': [
                {'id': 'claude-special', 'label': 'Special',
                 'warning': 'Always warn.',
                 'warning_dismissible': False,
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_ack_nondismiss.json', 'w') as f:
            json.dump(config, f)

        handler = serve.Handler.__new__(serve.Handler)
        body = json.dumps({'model_id': 'claude-special'}).encode('utf-8')
        handler.path = '/config/acknowledge-warning'
        handler.requestline = 'POST /config/acknowledge-warning HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        with patch('serve._resolve_config', return_value=config):
            handler.do_POST()
        handler.send_response.assert_called_with(400)

        # acknowledged_warnings should not be modified
        with open('/tmp/test_ack_nondismiss.json') as f:
            saved = json.load(f)
        self.assertNotIn('acknowledged_warnings', saved)

        os.remove('/tmp/test_ack_nondismiss.json')

    @patch('serve.CONFIG_PATH', '/tmp/test_ack_unknown.json')
    def test_unknown_model_returns_400(self):
        config = {
            'models': [
                {'id': 'claude-opus-4-6', 'label': 'Opus 4.6',
                 'capabilities': {'effort': True, 'permissions': True}},
            ],
            'agents': {}
        }
        with open('/tmp/test_ack_unknown.json', 'w') as f:
            json.dump(config, f)

        handler = serve.Handler.__new__(serve.Handler)
        body = json.dumps({'model_id': 'nonexistent'}).encode('utf-8')
        handler.path = '/config/acknowledge-warning'
        handler.requestline = 'POST /config/acknowledge-warning HTTP/1.1'
        handler.request_version = 'HTTP/1.1'
        handler.command = 'POST'
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        with patch('serve._resolve_config', return_value=config):
            handler.do_POST()
        handler.send_response.assert_called_with(400)

        os.remove('/tmp/test_ack_unknown.json')


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
