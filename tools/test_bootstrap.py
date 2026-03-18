#!/usr/bin/env python3
"""Tests for the shared bootstrap module (tools/bootstrap.py).

Covers all 10 automated scenarios from features/tools_bootstrap_module.md.
Outputs test results to tests/tools_bootstrap_module/tests.json.
"""

import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, PROJECT_ROOT)

from tools.bootstrap import detect_project_root, load_config, atomic_write


class TestDetectProjectRootEnvVar(unittest.TestCase):
    """Scenario: Detect Project Root via Environment Variable"""

    def test_returns_env_var_when_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'PURLIN_PROJECT_ROOT': tmpdir}):
                result = detect_project_root('/some/random/dir')
                self.assertEqual(result, os.path.abspath(tmpdir))

    def test_climbing_not_executed_when_env_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a .purlin dir that climbing would find
            purlin_dir = os.path.join(tmpdir, 'project', '.purlin')
            os.makedirs(purlin_dir)
            script_dir = os.path.join(tmpdir, 'project', 'tools', 'mod')
            os.makedirs(script_dir)
            env_root = os.path.join(tmpdir, 'override')
            os.makedirs(env_root)
            with patch.dict(os.environ, {'PURLIN_PROJECT_ROOT': env_root}):
                result = detect_project_root(script_dir)
                self.assertEqual(result, os.path.abspath(env_root))
                self.assertNotEqual(result, os.path.join(tmpdir, 'project'))


class TestDetectProjectRootClimbing(unittest.TestCase):
    """Scenario: Detect Project Root via Climbing Fallback"""

    def test_finds_purlin_dir_above_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Layout: tmpdir/project/.purlin/ and tmpdir/project/tools/mod/
            project = os.path.join(tmpdir, 'project')
            os.makedirs(os.path.join(project, '.purlin'))
            script_dir = os.path.join(project, 'tools', 'mod')
            os.makedirs(script_dir)
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
                result = detect_project_root(script_dir)
                self.assertEqual(result, project)

    def test_returns_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project = os.path.join(tmpdir, 'project')
            os.makedirs(os.path.join(project, '.purlin'))
            script_dir = os.path.join(project, 'tools', 'mod')
            os.makedirs(script_dir)
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
                result = detect_project_root(script_dir)
                self.assertTrue(os.path.isabs(result))


class TestDetectProjectRootSubmodule(unittest.TestCase):
    """Scenario: Climbing Fallback Prefers Further Path for Submodule"""

    def test_prefers_consumer_root_over_submodule_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Submodule layout:
            #   tmpdir/consumer/.purlin/     (consumer project root)
            #   tmpdir/consumer/purlin/.purlin/  (submodule root)
            #   tmpdir/consumer/purlin/tools/mod/  (script)
            consumer = os.path.join(tmpdir, 'consumer')
            submodule = os.path.join(consumer, 'purlin')
            os.makedirs(os.path.join(consumer, '.purlin'))
            os.makedirs(os.path.join(submodule, '.purlin'))
            script_dir = os.path.join(submodule, 'tools', 'mod')
            os.makedirs(script_dir)
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
                result = detect_project_root(script_dir)
                self.assertEqual(result, consumer)
                self.assertNotEqual(result, submodule)


class TestAtomicWriteBasic(unittest.TestCase):
    """Scenario: Atomic Write Creates File Atomically"""

    def test_creates_file_with_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'output.txt')
            atomic_write(path, 'hello world')
            with open(path) as f:
                self.assertEqual(f.read(), 'hello world')

    def test_no_temp_files_remain(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'output.txt')
            atomic_write(path, 'data')
            files = os.listdir(tmpdir)
            self.assertEqual(files, ['output.txt'])


class TestAtomicWriteParentDirs(unittest.TestCase):
    """Scenario: Atomic Write Creates Parent Directories"""

    def test_creates_missing_parents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'a', 'b', 'c', 'file.txt')
            atomic_write(path, 'nested')
            with open(path) as f:
                self.assertEqual(f.read(), 'nested')


class TestAtomicWriteJson(unittest.TestCase):
    """Scenario: Atomic Write JSON Mode"""

    def test_writes_json_with_indent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'data.json')
            data = {"key": "value", "count": 42}
            atomic_write(path, data, as_json=True)
            with open(path) as f:
                content = f.read()
            self.assertTrue(content.endswith('\n'))
            parsed = json.loads(content)
            self.assertEqual(parsed, data)
            # Verify indent=2 formatting
            self.assertIn('  "key"', content)


class TestAtomicWriteFailure(unittest.TestCase):
    """Scenario: Atomic Write Cleans Up on Failure"""

    def test_cleans_up_temp_on_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a read-only directory to cause os.replace to fail
            target_dir = os.path.join(tmpdir, 'readonly')
            os.makedirs(target_dir)
            target = os.path.join(target_dir, 'file.txt')
            # Write initial file then make dir read-only
            with open(target, 'w') as f:
                f.write('original')
            os.chmod(target_dir, stat.S_IRUSR | stat.S_IXUSR)
            try:
                with self.assertRaises(OSError):
                    atomic_write(target, 'new content')
                # Verify no .tmp files remain
                os.chmod(target_dir, stat.S_IRWXU)
                tmp_files = [f for f in os.listdir(target_dir) if f.endswith('.tmp')]
                self.assertEqual(tmp_files, [])
            finally:
                os.chmod(target_dir, stat.S_IRWXU)


class TestLoadConfigValid(unittest.TestCase):
    """Scenario: Config Loading with Valid Config"""

    def test_loads_config_from_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            config = {"tools_root": "tools", "key": "value"}
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump(config, f)
            result = load_config(tmpdir)
            self.assertIsInstance(result, dict)
            self.assertEqual(result.get('tools_root'), 'tools')
            self.assertEqual(result.get('key'), 'value')


class TestLoadConfigMissing(unittest.TestCase):
    """Scenario: Config Loading Falls Back on Missing Config"""

    def test_returns_empty_dict_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_config(tmpdir)
            self.assertIsInstance(result, dict)
            self.assertEqual(result, {})

    def test_no_exception_raised(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Should not raise even with no .purlin directory
            result = load_config(tmpdir)
            self.assertEqual(result, {})


class TestMigratedCallsitesPreserveBehavior(unittest.TestCase):
    """Scenario: Migrated Callsites Preserve Behavior

    Verifies that all existing tests pass with the migrated imports.
    This is tested implicitly by running the full test suite after migration.
    Here we verify the bootstrap module is importable and functional from
    the standard tool directory layout.
    """

    def test_standard_depth_finds_project_root(self):
        """Verify bootstrap works from tools/<module>/ depth (standard layout)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = os.path.join(tmpdir, 'project')
            os.makedirs(os.path.join(project, '.purlin'))
            script_dir = os.path.join(project, 'tools', 'cdd')
            os.makedirs(script_dir)
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
                result = detect_project_root(script_dir)
                self.assertEqual(result, project)

    def test_fallback_when_no_purlin_found(self):
        """Verify 2-levels-up fallback when no .purlin/ exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_dir = os.path.join(tmpdir, 'a', 'b', 'c')
            os.makedirs(script_dir)
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop('PURLIN_PROJECT_ROOT', None)
                result = detect_project_root(script_dir)
                expected = os.path.abspath(os.path.join(script_dir, '../..'))
                self.assertEqual(result, expected)


# --- Test runner with JSON output ---

def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stderr)
    result = runner.run(suite)

    details = []
    for test, _ in result.failures + result.errors:
        details.append({"test": str(test), "status": "FAIL",
                        "detail": "See stderr for traceback"})
    for test in result.successes if hasattr(result, 'successes') else []:
        details.append({"test": str(test), "status": "PASS"})

    passed = result.testsRun - len(result.failures) - len(result.errors)
    output = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "passed": passed,
        "failed": len(result.failures) + len(result.errors),
        "total": result.testsRun,
        "test_file": "tools/test_bootstrap.py",
    }

    out_dir = os.path.join(PROJECT_ROOT, 'tests', 'tools_bootstrap_module')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'tests.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
        f.write('\n')

    print(json.dumps(output, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
