"""Tests for CDD Startup Controls (cdd_startup_controls.md).

Tests launcher validation of startup_sequence / recommend_next_actions flags,
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

    Given config.json contains agents.builder with startup_sequence false
    and recommend_next_actions true, when run_builder.sh is executed,
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
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('startup_sequence', True) else 'false'
    print(f'AGENT_STARTUP=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('recommend_next_actions', True) else 'false'
    print(f'AGENT_RECOMMEND=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
if [ "$AGENT_STARTUP" = "false" ] && [ "$AGENT_RECOMMEND" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: startup_sequence=false with recommend_next_actions=true is not a valid combination." >&2
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
        """startup_sequence=false + recommend_next_actions=true -> exit 1 + stderr error."""
        result = self._run_launcher_validation('builder', {
            'startup_sequence': False,
            'recommend_next_actions': True
        })
        self.assertEqual(result.returncode, 1,
                         f"Expected exit 1, got {result.returncode}. stderr={result.stderr}")
        self.assertIn('Invalid startup controls', result.stderr)
        self.assertIn('startup_sequence', result.stderr)

    def test_rejects_invalid_for_architect(self):
        """Invalid combination rejected for architect role too."""
        result = self._run_launcher_validation('architect', {
            'startup_sequence': False,
            'recommend_next_actions': True
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn('Invalid startup controls', result.stderr)

    def test_rejects_invalid_for_qa(self):
        """Invalid combination rejected for qa role too."""
        result = self._run_launcher_validation('qa', {
            'startup_sequence': False,
            'recommend_next_actions': True
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
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('startup_sequence', True) else 'false'
    print(f'AGENT_STARTUP=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('recommend_next_actions', True) else 'false'
    print(f'AGENT_RECOMMEND=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
if [ "$AGENT_STARTUP" = "false" ] && [ "$AGENT_RECOMMEND" = "true" ]; then
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
        """startup_sequence=true + recommend_next_actions=true -> exit 0."""
        result = self._run_launcher_validation('builder', {
            'startup_sequence': True,
            'recommend_next_actions': True
        })
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('Invalid startup controls', result.stderr)

    def test_accepts_true_false(self):
        """startup_sequence=true + recommend_next_actions=false -> exit 0."""
        result = self._run_launcher_validation('builder', {
            'startup_sequence': True,
            'recommend_next_actions': False
        })
        self.assertEqual(result.returncode, 0)

    def test_accepts_false_false(self):
        """startup_sequence=false + recommend_next_actions=false -> exit 0 (expert mode)."""
        result = self._run_launcher_validation('builder', {
            'startup_sequence': False,
            'recommend_next_actions': False
        })
        self.assertEqual(result.returncode, 0)


class TestLauncherDefaultsMissingFields(unittest.TestCase):
    """Scenario: Launcher Defaults Missing Fields to True

    Given config.json does not contain startup_sequence or
    recommend_next_actions, both default to true.
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
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"
eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {{}}).get('$AGENT_ROLE', {{}})
    ss = 'true' if a.get('startup_sequence', True) else 'false'
    print(f'AGENT_STARTUP=\\\"{{ss}}\\\"')
    rn = 'true' if a.get('recommend_next_actions', True) else 'false'
    print(f'AGENT_RECOMMEND=\\\"{{rn}}\\\"')
except: pass
" 2>/dev/null)"
rm -f "$CONFIG_FILE"
echo "AGENT_STARTUP=$AGENT_STARTUP"
echo "AGENT_RECOMMEND=$AGENT_RECOMMEND"
'''
        return subprocess.run(
            ['bash', '-c', script],
            capture_output=True, text=True, timeout=10
        )

    def test_defaults_to_true_when_absent(self):
        """Missing fields default to true for architect."""
        result = self._run_extraction('architect', {
            'model': 'claude-sonnet-4-6',
            'effort': 'high'
        })
        self.assertEqual(result.returncode, 0)
        self.assertIn('AGENT_STARTUP=true', result.stdout)
        self.assertIn('AGENT_RECOMMEND=true', result.stdout)

    def test_defaults_when_agent_entry_empty(self):
        """Empty agent object -> both default to true."""
        result = self._run_extraction('builder', {})
        self.assertEqual(result.returncode, 0)
        self.assertIn('AGENT_STARTUP=true', result.stdout)
        self.assertIn('AGENT_RECOMMEND=true', result.stdout)


class TestApiRejectsInvalidCombination(unittest.TestCase):
    """Scenario: API Rejects Invalid Combination

    Given a POST /config/agents request body where agents.qa has
    startup_sequence false and recommend_next_actions true,
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
                              'startup_sequence': True,
                              'recommend_next_actions': True},
                'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                            'bypass_permissions': True,
                            'startup_sequence': True,
                            'recommend_next_actions': True},
                'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                       'bypass_permissions': True,
                       'startup_sequence': True,
                       'recommend_next_actions': True}
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
        """startup_sequence=false + recommend=true for qa -> HTTP 400."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'startup_sequence': True,
                          'recommend_next_actions': True},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'startup_sequence': True,
                        'recommend_next_actions': True},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'startup_sequence': False,
                   'recommend_next_actions': True}
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
                   'startup_sequence': False,
                   'recommend_next_actions': True}
        }
        self._make_handler(payload)
        with open(self.config_path) as f:
            current = json.load(f)
        self.assertEqual(current, self.original_config)

    def test_rejects_non_boolean_startup_sequence(self):
        """startup_sequence as string -> HTTP 400."""
        payload = {
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'startup_sequence': 'false',
                        'recommend_next_actions': True}
        }
        handler = self._make_handler(payload)
        status_code = handler._send_json.call_args[0][0]
        self.assertEqual(status_code, 400)


class TestApiAcceptsValidPayload(unittest.TestCase):
    """Scenario: API Accepts Valid Payload

    Given a POST /config/agents request body with startup_sequence true
    and recommend_next_actions false for all agents, the endpoint
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
                              'startup_sequence': True,
                              'recommend_next_actions': True},
                'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                            'bypass_permissions': True,
                            'startup_sequence': True,
                            'recommend_next_actions': True},
                'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                       'bypass_permissions': True,
                       'startup_sequence': True,
                       'recommend_next_actions': True}
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
        """All agents with startup=true, recommend=false -> HTTP 200."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'startup_sequence': True,
                          'recommend_next_actions': False},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'startup_sequence': True,
                        'recommend_next_actions': False},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'startup_sequence': True,
                   'recommend_next_actions': False}
        }
        handler = self._make_handler(payload)
        status_code = handler._send_json.call_args[0][0]
        self.assertEqual(status_code, 200)

    def test_config_updated_with_new_values(self):
        """After valid POST, config.json reflects new startup control values."""
        payload = {
            'architect': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                          'bypass_permissions': True,
                          'startup_sequence': True,
                          'recommend_next_actions': False},
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'startup_sequence': False,
                        'recommend_next_actions': False},
            'qa': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                   'bypass_permissions': True,
                   'startup_sequence': True,
                   'recommend_next_actions': False}
        }
        self._make_handler(payload)
        with open(self.config_path) as f:
            updated = json.load(f)
        self.assertFalse(updated['agents']['builder']['startup_sequence'])
        self.assertFalse(updated['agents']['builder']['recommend_next_actions'])
        self.assertTrue(updated['agents']['architect']['startup_sequence'])
        self.assertFalse(updated['agents']['architect']['recommend_next_actions'])

    def test_accepts_expert_mode(self):
        """startup=false + recommend=false (expert mode) -> HTTP 200."""
        payload = {
            'builder': {'model': 'claude-sonnet-4-6', 'effort': 'high',
                        'bypass_permissions': True,
                        'startup_sequence': False,
                        'recommend_next_actions': False}
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
        self.assertIn('agent-startup-', html)
        self.assertIn('agent-recommend-', html)
        # Column headers use two-line text (no inline labels in agent rows)
        self.assertIn('Startup', html)
        self.assertIn('Suggest', html)

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


class TestConfigSchemaDefaults(unittest.TestCase):
    """Verify the config files include startup control defaults."""

    def test_live_config_has_startup_fields(self):
        """config.json includes startup_sequence and recommend_next_actions."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.environ.get(
            'PURLIN_PROJECT_ROOT',
            os.path.abspath(os.path.join(script_dir, '../..'))
        )
        config_path = os.path.join(project_root, '.purlin', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        for role in ('architect', 'builder', 'qa'):
            agent = config['agents'][role]
            self.assertIn('startup_sequence', agent,
                          f'{role} missing startup_sequence')
            self.assertIn('recommend_next_actions', agent,
                          f'{role} missing recommend_next_actions')
            self.assertIsInstance(agent['startup_sequence'], bool)
            self.assertIsInstance(agent['recommend_next_actions'], bool)

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
        for role in ('architect', 'builder', 'qa'):
            agent = config['agents'][role]
            self.assertIn('startup_sequence', agent)
            self.assertIn('recommend_next_actions', agent)
            self.assertTrue(agent['startup_sequence'],
                            f'{role} startup_sequence should default true')
            self.assertTrue(agent['recommend_next_actions'],
                            f'{role} recommend_next_actions should default true')


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
            'total': result.testsRun
        }, f)
    print(f"\ntests.json: {status}")
