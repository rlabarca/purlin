#!/usr/bin/env python3
"""Tests for release audit automation scripts.

Covers all 14 automated scenarios from features/release_audit_automation.md.
Uses local fixture state (temp directories) rather than fixture repo tags.
Outputs test results to tests/release_audit_automation/tests.json.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

# Import the scripts under test
from tools.release.verify_dependency_integrity import main as verify_deps_main
from tools.release.verify_zero_queue import main as verify_zero_main
from tools.release.submodule_safety_audit import main as submodule_safety_main
from tools.release.critic_consistency_check import main as critic_consistency_main
from tools.release.doc_consistency_check import main as doc_consistency_main
from tools.release.instruction_audit import main as instruction_audit_main


def create_fixture(structure):
    """Create a temp directory with the given file structure.

    Args:
        structure: dict mapping relative paths to file content strings.

    Returns:
        Path to the temp directory.
    """
    root = tempfile.mkdtemp(prefix="release-audit-test-")
    for rel_path, content in structure.items():
        full_path = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    return root


# ===================================================================
# Scenario: Dependency integrity script detects cycle
# ===================================================================

class TestDepIntegrityCycle(unittest.TestCase):
    """Scenario: Dependency integrity script detects cycle"""

    def setUp(self):
        self.root = create_fixture({
            "features/feature_a.md": (
                '# Feature A\n'
                '> Label: "Feature A"\n'
                '> Category: "Test"\n'
                '> Prerequisite: features/feature_b.md\n'
            ),
            "features/feature_b.md": (
                '# Feature B\n'
                '> Label: "Feature B"\n'
                '> Category: "Test"\n'
                '> Prerequisite: features/feature_a.md\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_cycle(self):
        result = verify_deps_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        cycle_findings = [
            f for f in result["findings"] if f["category"] == "cycle"
        ]
        self.assertGreater(len(cycle_findings), 0, "Should find cycle")
        self.assertEqual(cycle_findings[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: Dependency integrity script passes on clean graph
# ===================================================================

class TestDepIntegrityClean(unittest.TestCase):
    """Scenario: Dependency integrity script passes on clean graph"""

    def setUp(self):
        self.root = create_fixture({
            "features/feature_a.md": (
                '# Feature A\n'
                '> Label: "Feature A"\n'
                '> Category: "Test"\n'
            ),
            "features/feature_b.md": (
                '# Feature B\n'
                '> Label: "Feature B"\n'
                '> Category: "Test"\n'
                '> Prerequisite: features/feature_a.md\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_clean_graph(self):
        result = verify_deps_main(self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["findings"]), 0)


# ===================================================================
# Scenario: Dependency integrity detects broken prerequisite link
# ===================================================================

class TestDepIntegrityBrokenLink(unittest.TestCase):
    """Scenario: Dependency integrity detects broken prerequisite link"""

    def setUp(self):
        self.root = create_fixture({
            "features/feature_a.md": (
                '# Feature A\n'
                '> Label: "Feature A"\n'
                '> Category: "Test"\n'
                '> Prerequisite: features/nonexistent.md\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_broken_link(self):
        result = verify_deps_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        broken = [f for f in result["findings"] if f["category"] == "broken_link"]
        self.assertGreater(len(broken), 0, "Should detect broken link")
        self.assertEqual(broken[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: Dependency integrity detects reverse reference
# ===================================================================

class TestDepIntegrityReverseRef(unittest.TestCase):
    """Scenario: Dependency integrity detects reverse reference"""

    def setUp(self):
        self.root = create_fixture({
            "features/parent.md": (
                '# Parent\n'
                '> Label: "Parent"\n'
                '> Category: "Test"\n'
                '\nThis feature uses child.md for something.\n'
            ),
            "features/child.md": (
                '# Child\n'
                '> Label: "Child"\n'
                '> Category: "Test"\n'
                '> Prerequisite: features/parent.md\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_reverse_reference(self):
        result = verify_deps_main(self.root)
        rev = [f for f in result["findings"] if f["category"] == "reverse_reference"]
        self.assertGreater(len(rev), 0, "Should detect reverse reference")
        self.assertEqual(rev[0]["severity"], "CRITICAL")
        # Should identify parent and child
        self.assertIn("parent", rev[0]["file"])


# ===================================================================
# Scenario: Zero queue script reports blocking features
# ===================================================================

class TestZeroQueueBlocking(unittest.TestCase):
    """Scenario: Zero queue script reports blocking features"""

    def setUp(self):
        self.root = create_fixture({
            "tests/feature_a/critic.json": json.dumps({
                "role_status": {
                    "architect": "DONE",
                    "builder": "TODO",
                    "qa": "N/A",
                }
            }),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_reports_blocking(self):
        result = verify_zero_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        blocking = [f for f in result["findings"] if f["category"] == "blocking_feature"]
        self.assertGreater(len(blocking), 0)
        self.assertIn("builder: TODO", blocking[0]["message"])


# ===================================================================
# Scenario: Zero queue script passes when all features are done
# ===================================================================

class TestZeroQueueClean(unittest.TestCase):
    """Scenario: Zero queue script passes when all features are done"""

    def setUp(self):
        self.root = create_fixture({
            "tests/feature_a/critic.json": json.dumps({
                "role_status": {
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                }
            }),
            "tests/feature_b/critic.json": json.dumps({
                "role_status": {
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "N/A",
                }
            }),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_all_clean(self):
        result = verify_zero_main(self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("2", result["summary"])  # total count


# ===================================================================
# Scenario: Submodule safety detects missing env var check
# ===================================================================

class TestSubmoduleSafetyMissingEnv(unittest.TestCase):
    """Scenario: Submodule safety detects missing env var check"""

    def setUp(self):
        self.root = create_fixture({
            "tools/bad_tool/scanner.py": (
                'import os\n'
                'import sys\n'
                'SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))\n'
                'PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_missing_env(self):
        result = submodule_safety_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        env_findings = [
            f for f in result["findings"] if f["category"] == "missing_env_check"
        ]
        self.assertGreater(len(env_findings), 0)
        self.assertEqual(env_findings[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: Submodule safety detects artifact written inside tools
# ===================================================================

class TestSubmoduleSafetyArtifactInTools(unittest.TestCase):
    """Scenario: Submodule safety detects artifact written inside tools"""

    def setUp(self):
        self.root = create_fixture({
            "tools/bad_tool/server.py": (
                'import os\n'
                'SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))\n'
                'PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT", SCRIPT_DIR)\n'
                'pid_file = os.path.join(SCRIPT_DIR, "server.pid")\n'
                'with open(pid_file, "w") as f:\n'
                '    f.write(str(os.getpid()))\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_artifact_in_tools(self):
        result = submodule_safety_main(self.root)
        artifact_findings = [
            f for f in result["findings"] if f["category"] == "artifact_in_tools"
        ]
        self.assertGreater(len(artifact_findings), 0)
        self.assertEqual(artifact_findings[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: Submodule safety passes on clean codebase
# ===================================================================

class TestSubmoduleSafetyClean(unittest.TestCase):
    """Scenario: Submodule safety passes on clean codebase"""

    def setUp(self):
        self.root = create_fixture({
            "tools/good_tool/scanner.py": (
                'import os\n'
                'import sys\n'
                'import json\n'
                'SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))\n'
                '_env_root = os.environ.get("PURLIN_PROJECT_ROOT", "")\n'
                'if _env_root and os.path.isdir(_env_root):\n'
                '    PROJECT_ROOT = _env_root\n'
                'else:\n'
                '    PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))\n'
                'try:\n'
                '    with open("config.json") as f:\n'
                '        data = json.load(f)\n'
                'except (json.JSONDecodeError, IOError, OSError):\n'
                '    data = {}\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_clean(self):
        result = submodule_safety_main(self.root)
        self.assertEqual(result["status"], "PASS")


# ===================================================================
# Scenario: Critic consistency detects deprecated terminology
# ===================================================================

class TestCriticConsistencyDeprecated(unittest.TestCase):
    """Scenario: Critic consistency detects deprecated terminology"""

    def setUp(self):
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Purpose\n'
                'The quality gate validates all features.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Critic\n'
                'The Critic is the coordination engine.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_deprecated_term(self):
        result = critic_consistency_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        term_findings = [
            f for f in result["findings"] if f["category"] == "deprecated_term"
        ]
        self.assertGreater(len(term_findings), 0)
        self.assertIn("quality gate", term_findings[0]["message"])


# ===================================================================
# Scenario: Doc consistency detects stale reference
# ===================================================================

class TestDocConsistencyStaleRef(unittest.TestCase):
    """Scenario: Doc consistency detects stale reference"""

    def setUp(self):
        self.root = create_fixture({
            "README.md": (
                '# Project\n'
                'See `tools/deleted_tool/run.py` for details.\n'
            ),
            "features/feature_a.md": '# Feature A\n',
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_stale_reference(self):
        result = doc_consistency_main(self.root)
        stale = [f for f in result["findings"] if f["category"] == "stale_reference"]
        self.assertGreater(len(stale), 0)
        self.assertIn("deleted_tool", stale[0]["message"])


# ===================================================================
# Scenario: Instruction audit detects contradiction
# ===================================================================

class TestInstructionAuditContradiction(unittest.TestCase):
    """Scenario: Instruction audit detects contradiction"""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/HOW_WE_WORK_OVERRIDES.md": (
                '# Overrides\n'
                'The Builder MUST NOT commit implementation code.\n'
            ),
            ".purlin/ARCHITECT_OVERRIDES.md": '# Architect Overrides\n',
            ".purlin/BUILDER_OVERRIDES.md": '# Builder Overrides\n',
            ".purlin/QA_OVERRIDES.md": '# QA Overrides\n',
            "instructions/BUILDER_BASE.md": (
                '# Builder Instructions\n'
                'The Builder MUST commit implementation code after each feature.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_contradiction(self):
        result = instruction_audit_main(self.root)
        contrad = [
            f for f in result["findings"] if f["category"] == "contradiction"
        ]
        self.assertGreater(len(contrad), 0, "Should detect contradiction")
        self.assertEqual(contrad[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: Instruction audit detects stale path
# ===================================================================

class TestInstructionAuditStalePath(unittest.TestCase):
    """Scenario: Instruction audit detects stale path"""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/HOW_WE_WORK_OVERRIDES.md": '# Overrides\n',
            ".purlin/ARCHITECT_OVERRIDES.md": '# Architect Overrides\n',
            ".purlin/BUILDER_OVERRIDES.md": (
                '# Builder Overrides\n'
                'See `tools/deleted_tool/scanner.py` for details.\n'
            ),
            ".purlin/QA_OVERRIDES.md": '# QA Overrides\n',
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_stale_path(self):
        result = instruction_audit_main(self.root)
        stale = [f for f in result["findings"] if f["category"] == "stale_path"]
        self.assertGreater(len(stale), 0, "Should detect stale path")
        self.assertIn("deleted_tool", stale[0]["message"])


# ===================================================================
# Scenario: All scripts produce valid JSON output
# ===================================================================

class TestAllScriptsValidJSON(unittest.TestCase):
    """Scenario: All scripts produce valid JSON output"""

    def setUp(self):
        self.root = create_fixture({
            "features/feature_a.md": (
                '# Feature A\n'
                '> Label: "Feature A"\n'
                '> Category: "Test"\n'
            ),
            "tests/feature_a/critic.json": json.dumps({
                "role_status": {
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                }
            }),
            "README.md": "# Project\n",
            ".purlin/HOW_WE_WORK_OVERRIDES.md": "# Overrides\n",
            ".purlin/ARCHITECT_OVERRIDES.md": "# Overrides\n",
            ".purlin/BUILDER_OVERRIDES.md": "# Overrides\n",
            ".purlin/QA_OVERRIDES.md": "# Overrides\n",
            ".purlin/config.json": '{}',
            "instructions/HOW_WE_WORK_BASE.md": "# HWW\n",
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def _assert_valid_output(self, result):
        """Assert result is valid audit output with required keys."""
        # Verify it's JSON-serializable
        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        self.assertIn("step", parsed)
        self.assertIn("status", parsed)
        self.assertIn("findings", parsed)
        self.assertIn("summary", parsed)
        self.assertIn(parsed["status"], ("PASS", "FAIL", "WARNING"))

    def test_verify_dependency_integrity(self):
        self._assert_valid_output(verify_deps_main(self.root))

    def test_verify_zero_queue(self):
        self._assert_valid_output(verify_zero_main(self.root))

    def test_submodule_safety_audit(self):
        self._assert_valid_output(submodule_safety_main(self.root))

    def test_critic_consistency_check(self):
        self._assert_valid_output(critic_consistency_main(self.root))

    def test_doc_consistency_check(self):
        self._assert_valid_output(doc_consistency_main(self.root))

    def test_instruction_audit(self):
        self._assert_valid_output(instruction_audit_main(self.root))


# ===================================================================
# Test result output
# ===================================================================

class JsonTestResult(unittest.TextTestResult):
    """Custom result that collects pass/fail for JSON output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results.append({"test": str(test), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results.append({
            "test": str(test), "status": "FAIL", "message": str(err[1]),
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append({
            "test": str(test), "status": "ERROR", "message": str(err[1]),
        })


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "release_audit_automation")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "tests.json")

        all_passed = len(result.failures) == 0 and len(result.errors) == 0
        failed = len(result.failures) + len(result.errors)
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if all_passed else "FAIL",
                    "passed": result.testsRun - failed,
                    "failed": failed,
                    "total": result.testsRun,
                    "test_file": "tools/release/test_release_audit.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
