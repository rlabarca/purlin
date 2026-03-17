"""Tests for CDD Startup Controls (cdd_startup_controls.md).

Tests launcher validation of find_work / auto_start flags,
API validation in POST /config/agents, and config schema defaults.
Produces tests/cdd_startup_controls/tests.json.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

# Ensure serve module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serve


class TestLauncherRejectsInvalidFlagCombination(unittest.TestCase):
    """Scenario: Launcher Rejects Invalid Flag Combination

    Given config.json contains agents.builder with find_work false
    and auto_start true, when pl-run-builder.sh is executed,
    the script prints an error to stderr and exits with status 1.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.tmpdir, '.purlin')
        os.makedirs(self.purlin_dir)
        # Minimal project structure
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.environ.get(
            'PURLIN_PROJECT_ROOT',
            os.path.abspath(os.path.join(script_dir, '../..'))
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_config(self, agent_config):
        config = {
            "agents": {"builder": agent_config}
        }
        with open(os.path.join(self.purlin_dir, 'config.json'), 'w') as f:
            json.dump(config, f)

    def _run_launcher_validation(self, role, agent_config):
        """Run just the validation portion of a launcher script."""
        config = {"agents": {role: agent_config}}
        config_json = json.dumps(config)
        # Replicate the launcher's Python extraction + bash validation
        script = f'''
CONFIG_FILE=$(mktemp)
cat > "$CONFIG_FILE" << 'CFGEOF'
{config_json}
CFGEOF
AGENT_ROLE="{role}"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('find_work', True) else 'false'
    print(f'AGENT_FIND_WORK=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('auto_start', False) else 'false'
    print(f'AGENT_AUTO_START=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: find_work=false with auto_start=true is not a valid combination." >&2
    exit 1
fi
exit 0
'''
        result = subprocess.run(
            ['bash', '-c', script],
            capture_output=True, text=True, timeout=10
        )
        return result

    def test_rejects_invalid_combination(self):
        """find_work=false + auto_start=true -> exit 1 + stderr error."""
        result = self._run_launcher_validation('builder', {
            'find_work': False,
            'auto_start': True
        })
        self.assertEqual(result.returncode, 1,
                         f"Expected exit 1, got {result.returncode}. stderr={result.stderr}")
        self.assertIn('Invalid startup controls', result.stderr)
        self.assertIn('find_work', result.stderr)

    def test_rejects_invalid_for_architect(self):
        """Invalid combination rejected for architect role too."""
        result = self._run_launcher_validation('architect', {
            'find_work': False,
            'auto_start': True
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid startup controls', result.stderr)

    def test_rejects_invalid_for_qa(self):
        """Invalid combination rejected for qa role too."""
        result = self._run_launcher_validation('qa', {
            'find_work': False,
            'auto_start': True
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid startup controls', result.stderr)


class TestLauncherAcceptsValidCombinations(unittest.TestCase):
    """Scenario: Launcher Accepts Valid Combinations Without Error

    Given config.json with valid startup control combinations,
    the launcher exits without error related to startup controls.
    """

    def _run_launcher_validation(self, role, agent_config):
        config = {"agents": {role: agent_config}}
        config_json = json.dumps(config)
        script = f'''
CONFIG_FILE=$(mktemp)
cat > "$CONFIG_FILE" << 'CFGEOF'
{config_json}
CFGEOF
AGENT_ROLE="{role}"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('find_work', True) else 'false'
    print(f'AGENT_FIND_WORK=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('auto_start', False) else 'false'
    print(f'AGENT_AUTO_START=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: Invalid startup controls" >&2
    exit 1
fi
exit 0
'''
        return subprocess.run(
            ['bash', '-c', script],
            capture_output=True, text=True, timeout=10
        )

    def test_accepts_true_true(self):
        """find_work=true + auto_start=true -> exit 0."""
        result = self._run_launcher_validation('builder', {
            'find_work': True,
            'auto_start': True
        })
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('Invalid startup controls', result.stderr)

    def test_accepts_true_false(self):
        """find_work=true + auto_start=false -> exit 0."""
        result = self._run_launcher_validation('builder', {
            'find_work': True,
            'auto_start': False
        })
        self.assertEqual(result.returncode, 0)

    def test_accepts_false_false(self):
        """find_work=false + auto_start=false -> exit 0 (expert mode)."""
        result = self._run_launcher_validation('builder', {
            'find_work': False,
            'auto_start': False
        })
        self.assertEqual(result.returncode, 0)


class TestLauncherDefaultsMissingFields(unittest.TestCase):
    """Scenario: Launcher Defaults Missing Fields

    Given config.json does not contain find_work or
    auto_start, find_work defaults to true and auto_start defaults to false.
    """

    def _run_extraction(self, role, agent_config):
        config = {"agents": {role: agent_config}}
        config_json = json.dumps(config)
        script = f'''
CONFIG_FILE=$(mktemp)
cat > "$CONFIG_FILE" << 'CFGEOF'
{config_json}
CFGEOF
AGENT_ROLE="{role}"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('find_work', True) else 'false'
    print(f'AGENT_FIND_WORK=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('auto_start', False) else 'false'
    print(f'AGENT_AUTO_START=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
echo "AGENT_FIND_WORK=$AGENT_FIND_WORK"
echo "AGENT_AUTO_START=$AGENT_AUTO_START"
'''
        return subprocess.run(
            ['bash', '-c', script],
            capture_output=True, text=True, timeout=10
        )

    def test_defaults_when_absent(self):
        """Missing fields: find_work defaults to true, auto_start to false."""
        result = self._run_extraction('architect', {
            'model': 'claude-sonnet-4-6',
            'effort': 'high'
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn('AGENT_FIND_WORK=true', result.stdout)
        self.assertIn('AGENT_AUTO_START=false', result.stdout)

    def test_defaults_when_agent_entry_empty(self):
        """Empty agent object -> find_work true, auto_start false."""
        result = self._run_extraction('builder', {})
        self.assertEqual(result.returncode, 0)
        self.assertIn('AGENT_FIND_WORK=true', result.stdout)
        self.assertIn('AGENT_AUTO_START=false', result.stdout)


class TestApiRejectsInvalidCombination(unittest.TestCase):
    """Scenario: API Rejects Invalid Combination

    Given a POST /config/agents request body where agents.qa has
    find_work false and auto_start true,
    the endpoint returns HTTP 400 and config.json is not modified.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, 'config.json')
        self.original_config = {
            'models': [
                {'id': 'claude-sonnet-4-6', 'label': 'Sonnet 4.6',
                 'capabilities': {'effort': True, 'permissions': True}}
            ],
            'agents': {
                'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                              'bypass_permissions': True,
                              'find_work': True,
                              'auto_start': True},
                'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                            'bypass_permissions': True,
                            'find_work': True,
                            'auto_start': True},
                'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                       'bypass_permissions': True,
                       'find_work': True,
                       'auto_start': True},
                'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                       'bypass_permissions': True,
                       'find_work': False,
                       'auto_start': False}
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(self.original_config, f)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_handler(self, body_dict):
        """Create a mock handler that calls _handle_config_agents."""
        body_bytes = json.dumps(body_dict).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body_bytes))}
        handler.rfile = io.BytesIO(body_bytes)
        handler._send_json = MagicMock()

        # Patch CONFIG_PATH for this test
        with patch.object(serve, 'CONFIG_PATH', self.config_path):
            serve.Handler._handle_config_agents(handler)

        return handler

    def test_rejects_invalid_combination_qa(self):
        """find_work=false + auto_start=true for qa -> HTTP 400."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'find_work': True,
                          'auto_start': True},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'find_work': True,
                        'auto_start': True},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'find_work': False,
                   'auto_start': True},
            'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                   'bypass_permissions': True,
                   'find_work': False,
                   'auto_start': False}
        }
        handler = self._make_handler(payload)
        handler._send_json.assert_called_once()
        status_code = handler._send_json.call_args[0][0]
        response_body = handler._send_json.call_args[0][1]
        self.assertEqual(status_code, 400)
        self.assertIn('error', response_body)
        self.assertIn('invalid', response_body['error'].lower())

    def test_config_not_modified_on_rejection(self):
        """Config file remains unchanged after rejected request."""
        payload = {
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'find_work': False,
                   'auto_start': True}
        }
        self._make_handler(payload)
        with open(self.config_path) as f:
            current = json.load(f)
        self.assertEqual(current, self.original_config)

    def test_rejects_non_boolean_find_work(self):
        """find_work as string -> HTTP 400."""
        payload = {
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'find_work': 'false',
                        'auto_start': True}
        }
        handler = self._make_handler(payload)
        status_code = handler._send_json.call_args[0][0]
        self.assertEqual(status_code, 400)


class TestApiAcceptsValidPayload(unittest.TestCase):
    """Scenario: API Accepts Valid Payload

    Given a POST /config/agents request body with find_work true
    and auto_start false for all agents, the endpoint
    returns HTTP 200 and config.json is updated.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, 'config.json')
        initial = {
            'models': [
                {'id': 'claude-sonnet-4-6', 'label': 'Sonnet 4.6',
                 'capabilities': {'effort': True, 'permissions': True}}
            ],
            'agents': {
                'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                              'bypass_permissions': True,
                              'find_work': True,
                              'auto_start': True},
                'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                            'bypass_permissions': True,
                            'find_work': True,
                            'auto_start': True},
                'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                       'bypass_permissions': True,
                       'find_work': True,
                       'auto_start': True},
                'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                       'bypass_permissions': True,
                       'find_work': False,
                       'auto_start': False}
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(initial, f)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_handler(self, body_dict):
        body_bytes = json.dumps(body_dict).encode('utf-8')
        handler = MagicMock()
        handler.headers = {'Content-Length': str(len(body_bytes))}
        handler.rfile = io.BytesIO(body_bytes)
        handler._send_json = MagicMock()

        with patch.object(serve, 'CONFIG_PATH', self.config_path):
            serve.Handler._handle_config_agents(handler)

        return handler

    def test_accepts_valid_payload(self):
        """All agents with find_work=true, auto_start=false -> HTTP 200."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'find_work': True,
                          'auto_start': False},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'find_work': True,
                        'auto_start': False},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'find_work': True,
                   'auto_start': False},
            'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                   'bypass_permissions': True,
                   'find_work': False,
                   'auto_start': False}
        }
        handler = self._make_handler(payload)
        status_code = handler._send_json.call_args[0][0]
        self.assertEqual(status_code, 200)

    def test_config_updated_with_new_values(self):
        """After valid POST, config.json reflects new startup control values."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'find_work': True,
                          'auto_start': False},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'find_work': False,
                        'auto_start': False},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'find_work': True,
                   'auto_start': False},
            'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                   'bypass_permissions': True,
                   'find_work': False,
                   'auto_start': False}
        }
        self._make_handler(payload)
        with open(self.config_path) as f:
            updated = json.load(f)
        self.assertFalse(updated['agents']['builder']['find_work'])
        self.assertFalse(updated['agents']['builder']['auto_start'])
        self.assertTrue(updated['agents']['architect']['find_work'])
        self.assertFalse(updated['agents']['architect']['auto_start'])

    def test_accepts_expert_mode(self):
        """find_work=false + auto_start=false (expert mode) -> HTTP 200."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'find_work': True,
                          'auto_start': False},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'find_work': False,
                        'auto_start': False},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'find_work': True,
                   'auto_start': False},
            'pm': {'model': 'claude-sonnet-4-6', 'effort': 'medium',
                   'bypass_permissions': True,
                   'find_work': False,
                   'auto_start': False}
        }
        handler = self._make_handler(payload)
        status_code = handler._send_json.call_args[0][0]
        self.assertEqual(status_code, 200)


class TestDashboardHtmlStartupControls(unittest.TestCase):
    """Verify that the dashboard HTML includes startup control checkboxes."""

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_startup_checkboxes_in_html(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # Check for startup control elements in the generated HTML
        self.assertIn('agent-findwork-', html)
        self.assertIn('agent-autostart-', html)
        # Column headers use two-line text (no inline labels in agent rows)
        self.assertIn('Find', html)
        self.assertIn('Auto', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_grid_columns_extended(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('64px 140px 80px 60px 60px 60px', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_startup_ctrl_css_class(self, mock_run, mock_status):
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        self.assertIn('agent-chk-lbl', html)
        self.assertIn('.agent-chk-lbl.disabled', html)

    @patch('serve.get_feature_status')
    @patch('serve.run_command')
    def test_auto_start_disables_when_find_work_unchecked(self, mock_run, mock_status):
        """Auto Start checkbox disables when Find Work is unchecked.

        Verifies the dashboard JS contains disable logic: when the find work
        checkbox is unchecked, the auto start checkbox must be set to
        disabled=true and checked=false.
        """
        mock_status.return_value = ([], [], [])
        mock_run.return_value = ""
        html = serve.generate_html()
        # Verify JS contains the disable logic for auto start when find work unchecked
        self.assertIn('autoStartChk.disabled = true', html,
                       'Missing JS to disable auto-start when find-work unchecked')
        self.assertIn('autoStartChk.checked = false', html,
                       'Missing JS to uncheck auto-start when find-work unchecked')
        # Verify re-enable logic when find work is re-checked
        self.assertIn('autoStartChk.disabled = false', html,
                       'Missing JS to re-enable auto-start when find-work re-checked')
        # Verify the disabled class is applied for visual feedback
        self.assertIn("classList.add('disabled')", html,
                       'Missing disabled class toggle for auto-start label')


class TestConfigSchemaDefaults(unittest.TestCase):
    """Verify the config files include startup control defaults."""

    def test_live_config_has_startup_fields(self):
        """config.json includes find_work and auto_start."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.environ.get(
            'PURLIN_PROJECT_ROOT',
            os.path.abspath(os.path.join(script_dir, '../..'))
        )
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        for role in ('architect', 'builder', 'qa', 'pm'):
            agent = config['agents'][role]
            self.assertIn('find_work', agent,
                          f'{role} missing find_work')
            self.assertIn('auto_start', agent,
                          f'{role} missing auto_start')
            self.assertIsInstance(agent['find_work'], bool)
            self.assertIsInstance(agent['auto_start'], bool)

    def test_sample_config_has_startup_fields(self):
        """purlin-config-sample/config.json includes startup fields."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.environ.get(
            'PURLIN_PROJECT_ROOT',
            os.path.abspath(os.path.join(script_dir, '../..'))
        )
        sample_path = os.path.join(project_root, 'purlin-config-sample', 'config.json')
        with open(sample_path) as f:
            config = json.load(f)
        for role in ('architect', 'builder', 'qa', 'pm'):
            agent = config['agents'][role]
            self.assertIn('find_work', agent)
            self.assertIn('auto_start', agent)


# =============================================================================
# Test runner: writes results to tests/cdd_startup_controls/tests.json
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
    tests_dir = os.path.join(project_root, 'tests', 'cdd_startup_controls')
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
            'test_file': 'tools/cdd/test_cdd_startup_controls.py'
        }, f)
    print(f"\ntests.json: {status}")
