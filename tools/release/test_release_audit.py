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
import time
import unittest
from unittest import mock

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_framework_root = os.path.abspath(os.path.join(SCRIPT_DIR, '../../'))
if _framework_root not in sys.path:
    sys.path.insert(0, _framework_root)

from tools.release.audit_common import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)

# Import the scripts under test
from tools.release.verify_dependency_integrity import (
    main as verify_deps_main, ensure_cache_fresh,
)
from tools.release.verify_zero_queue import (
    main as verify_zero_main,
    load_feature_status as verify_zero_load_status,
)
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
            ".purlin/config.json": '{}',
        })
        # Status data in status.sh JSON output format
        self.status_data = {
            "features": [
                {
                    "file": "features/feature_a.md",
                    "label": "Feature A",
                    "category": "Test",
                    "architect": "DONE",
                    "builder": "TODO",
                    "qa": "N/A",
                }
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_reports_blocking(self):
        result = verify_zero_main(self.root, status_data=self.status_data)
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
            ".purlin/config.json": '{}',
        })
        self.status_data = {
            "features": [
                {
                    "file": "features/feature_a.md",
                    "label": "Feature A",
                    "category": "Test",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                },
                {
                    "file": "features/feature_b.md",
                    "label": "Feature B",
                    "category": "Test",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "N/A",
                },
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_all_clean(self):
        result = verify_zero_main(self.root, status_data=self.status_data)
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
            "purlin-config-sample/gitignore.purlin": (
                '.purlin/cache/\n'
                '.purlin/runtime/\n'
                '.purlin/config.local.json\n'
                'CRITIC_REPORT.md\n'
                'tests/*/critic.json\n'
            ),
            "tools/init.sh": (
                '#!/bin/bash\n'
                '# Read from gitignore.purlin template\n'
                'TEMPLATE="purlin-config-sample/gitignore.purlin"\n'
                '# Refresh mode: sync gitignore from template\n'
                'if [ "$MODE" = "refresh" ]; then\n'
                '    # gitignore additive merge\n'
                '    cat "$TEMPLATE" >> .gitignore\n'
                'fi\n'
            ),
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_clean(self):
        result = submodule_safety_main(self.root)
        self.assertEqual(result["status"], "PASS")


# ===================================================================
# Scenario: WARNING finding -- generated artifact not covered by
# gitignore template (auto-test-only)
# ===================================================================

class TestSubmoduleSafetyGitignoreUncoveredArtifact(unittest.TestCase):
    """Scenario: WARNING finding -- generated artifact not covered by gitignore template"""

    def setUp(self):
        self.root = create_fixture({
            "tools/reporter/report_gen.py": (
                'import os\n'
                'SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))\n'
                'PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT", SCRIPT_DIR)\n'
                'with open("custom_output.dat", "w") as f:\n'
                '    f.write("data")\n'
            ),
            "purlin-config-sample/gitignore.purlin": (
                '.purlin/cache/\n'
                '.purlin/runtime/\n'
                '.purlin/config.local.json\n'
                'CRITIC_REPORT.md\n'
                'tests/*/critic.json\n'
            ),
            "tools/init.sh": (
                '#!/bin/bash\n'
                '# Read from gitignore.purlin template\n'
                'TEMPLATE="purlin-config-sample/gitignore.purlin"\n'
                '# Refresh mode: sync gitignore from template\n'
                'if [ "$MODE" = "refresh" ]; then\n'
                '    # gitignore additive merge\n'
                '    cat "$TEMPLATE" >> .gitignore\n'
                'fi\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_uncovered_artifact(self):
        result = submodule_safety_main(self.root)
        uncovered = [
            f for f in result["findings"]
            if f["category"] == "gitignore_uncovered_artifact"
        ]
        self.assertGreater(len(uncovered), 0, "Should detect uncovered artifact")
        self.assertEqual(uncovered[0]["severity"], "WARNING")
        self.assertIn("custom_output.dat", uncovered[0]["message"])


# ===================================================================
# Scenario: CRITICAL finding -- init.sh uses hardcoded gitignore
# array (auto-test-only)
# ===================================================================

class TestSubmoduleSafetyGitignoreHardcodedArray(unittest.TestCase):
    """Scenario: CRITICAL finding -- init.sh uses hardcoded gitignore array"""

    def setUp(self):
        self.root = create_fixture({
            "purlin-config-sample/gitignore.purlin": (
                '.purlin/cache/\n'
                '.purlin/runtime/\n'
                '.purlin/config.local.json\n'
                'CRITIC_REPORT.md\n'
                'tests/*/critic.json\n'
            ),
            "tools/init.sh": (
                '#!/bin/bash\n'
                '# Hardcoded ignores instead of reading template\n'
                'RECOMMENDED_IGNORES=(\n'
                '    ".purlin/cache/"\n'
                '    ".purlin/runtime/"\n'
                '    "CRITIC_REPORT.md"\n'
                ')\n'
                'for pattern in "${RECOMMENDED_IGNORES[@]}"; do\n'
                '    echo "$pattern" >> .gitignore\n'
                'done\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_hardcoded_array(self):
        result = submodule_safety_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        hardcoded = [
            f for f in result["findings"]
            if f["category"] == "gitignore_hardcoded_array"
        ]
        self.assertGreater(len(hardcoded), 0, "Should detect hardcoded array")
        self.assertEqual(hardcoded[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: CRITICAL finding -- refresh mode skips gitignore sync
# (auto-test-only)
# ===================================================================

class TestSubmoduleSafetyGitignoreRefreshSkip(unittest.TestCase):
    """Scenario: CRITICAL finding -- refresh mode skips gitignore sync"""

    def setUp(self):
        self.root = create_fixture({
            "purlin-config-sample/gitignore.purlin": (
                '.purlin/cache/\n'
                '.purlin/runtime/\n'
                '.purlin/config.local.json\n'
                'CRITIC_REPORT.md\n'
                'tests/*/critic.json\n'
            ),
            "tools/init.sh": (
                '#!/bin/bash\n'
                '# Read from gitignore.purlin template\n'
                'TEMPLATE="purlin-config-sample/gitignore.purlin"\n'
                '# Fresh install: apply gitignore from template\n'
                'cat "$TEMPLATE" >> .gitignore\n'
                '# Refresh mode: only update launchers\n'
                'if [ "$ALREADY_INITIALIZED" = "true" ]; then\n'
                '    # refresh mode — update launcher scripts only\n'
                '    echo "Refreshing launchers..."\n'
                'fi\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_refresh_skips_gitignore(self):
        result = submodule_safety_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        refresh_skip = [
            f for f in result["findings"]
            if f["category"] == "gitignore_refresh_skip"
        ]
        self.assertGreater(len(refresh_skip), 0,
                           "Should detect refresh mode skipping gitignore")
        self.assertEqual(refresh_skip[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: CRITICAL finding — missing nested-project disambiguation
# ===================================================================

class TestSubmoduleSafetyMissingDisambiguation(unittest.TestCase):
    """Scenario: Climbing fallback without .git type disambiguation"""

    def setUp(self):
        self.root = create_fixture({
            "tools/bad_tool/climber.py": (
                'import os\n'
                'SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))\n'
                'PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT", "")\n'
                'if not PROJECT_ROOT:\n'
                '    further = os.path.abspath(os.path.join(SCRIPT_DIR, "../../../"))\n'
                '    nearer = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))\n'
                '    if os.path.isdir(os.path.join(further, ".purlin")):\n'
                '        PROJECT_ROOT = further\n'
                '    elif os.path.isdir(os.path.join(nearer, ".purlin")):\n'
                '        PROJECT_ROOT = nearer\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_missing_disambiguation(self):
        result = submodule_safety_main(self.root)
        disambig_findings = [
            f for f in result["findings"]
            if f["category"] == "missing_git_disambiguation"
        ]
        self.assertGreater(len(disambig_findings), 0,
                           "Should detect missing .git disambiguation")
        self.assertEqual(disambig_findings[0]["severity"], "CRITICAL")


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
# Scenario: Zero queue script reports QA blocking features
# ===================================================================

class TestZeroQueueQABlocking(unittest.TestCase):
    """Scenario: Feature with open QA discoveries"""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/config.json": '{}',
        })
        self.status_data = {
            "features": [
                {
                    "file": "features/feature_a.md",
                    "label": "Feature A",
                    "category": "Test",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "TODO",
                }
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_reports_qa_blocking(self):
        result = verify_zero_main(self.root, status_data=self.status_data)
        self.assertEqual(result["status"], "FAIL")
        blocking = [f for f in result["findings"] if f["category"] == "blocking_feature"]
        self.assertGreater(len(blocking), 0)
        self.assertIn("qa: TODO", blocking[0]["message"])


# ===================================================================
# Scenario: Zero queue script reports architect blocking features
# ===================================================================

class TestZeroQueueArchitectBlocking(unittest.TestCase):
    """Scenario: Feature with outstanding Architect work"""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/config.json": '{}',
        })
        self.status_data = {
            "features": [
                {
                    "file": "features/feature_a.md",
                    "label": "Feature A",
                    "category": "Test",
                    "architect": "TODO",
                    "builder": "TODO",
                    "qa": "N/A",
                }
            ],
        }

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_reports_architect_blocking(self):
        result = verify_zero_main(self.root, status_data=self.status_data)
        self.assertEqual(result["status"], "FAIL")
        blocking = [f for f in result["findings"] if f["category"] == "blocking_feature"]
        self.assertGreater(len(blocking), 0)
        self.assertIn("architect: TODO", blocking[0]["message"])


# ===================================================================
# Scenario: Critic consistency detects routing rule inconsistency
# ===================================================================

class TestCriticConsistencyRouting(unittest.TestCase):
    """Scenario: Routing rule inconsistency found"""

    def setUp(self):
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Routing\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Critic\n'
                'The Critic coordinates.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_routing_inconsistency(self):
        result = critic_consistency_main(self.root)
        routing = [f for f in result["findings"] if f["category"] == "routing_inconsistency"]
        self.assertGreater(len(routing), 0)
        self.assertEqual(routing[0]["severity"], "CRITICAL")


# ===================================================================
# Scenario: WARNING-level finding does not produce FAIL status
# ===================================================================

class TestCriticConsistencyWarningLevel(unittest.TestCase):
    """Scenario: WARNING-level finding does not halt

    Uses a README with '## The Critic' section in wrong order (after
    '## Setup & Configuration') to produce a WARNING without any CRITICAL.
    Routing rules are consistent (both files present) so no CRITICAL is
    triggered, and Phase 2 ordering check emits a WARNING.
    """

    def setUp(self):
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Routing\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Coordination\n'
                'The coordination engine handles routing.\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "README.md": (
                '# Project\n'
                '## The Agents\n'
                'Agent info.\n'
                '## Setup & Configuration\n'
                'Setup info.\n'
                '## The Critic\n'
                'Critic info.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_warning_status_not_fail(self):
        result = critic_consistency_main(self.root)
        # With only WARNING-level findings (ordering), status should be WARNING, not FAIL
        self.assertNotEqual(result["status"], "FAIL")
        if result["findings"]:
            self.assertEqual(result["status"], "WARNING")


# ===================================================================
# Scenario: Phase 2 README — missing Critic section detected
# ===================================================================

class TestCriticConsistencyReadmeMissing(unittest.TestCase):
    """Scenario: Phase 2 detects missing '## The Critic' section in README"""

    def setUp(self):
        # Clean Phase 1 (consistent routing, no deprecated terms) but
        # README has no '## The Critic' heading.
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Routing\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Coordination\n'
                'The coordination engine handles routing.\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "README.md": (
                '# Project\n'
                '## The Agents\n'
                'Agent info.\n'
                '## Setup & Configuration\n'
                'Setup info.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_missing_critic_section(self):
        result = critic_consistency_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        missing = [
            f for f in result["findings"]
            if f["category"] == "readme_missing_critic_section"
        ]
        self.assertGreater(len(missing), 0)
        self.assertEqual(missing[0]["severity"], "CRITICAL")
        self.assertIn("The Critic", missing[0]["message"])


# ===================================================================
# Scenario: Phase 2 README — Critic section present and ordered
# ===================================================================

class TestCriticConsistencyReadmeClean(unittest.TestCase):
    """Scenario: Clean audit -- README updated (Phase 2 passes)"""

    def setUp(self):
        # Clean Phase 1 and clean Phase 2: Critic section in correct position
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Routing\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Coordination\n'
                'The coordination engine handles routing.\n'
                'BUG entries are routed to the Builder.\n'
                'DISCOVERY entries are routed to the Architect.\n'
                'INTENT_DRIFT entries are routed to the Architect.\n'
                'SPEC_DISPUTE entries are routed to the Architect.\n'
            ),
            "README.md": (
                '# Project\n'
                '## The Agents\n'
                'Agent info.\n'
                '## The Critic\n'
                'The Critic is the coordination engine.\n'
                '## Setup & Configuration\n'
                'Setup info.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_clean_audit_passes(self):
        result = critic_consistency_main(self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["findings"]), 0)


# ===================================================================
# Scenario: Phase 2 skipped when Phase 1 has CRITICAL findings
# ===================================================================

class TestCriticConsistencyPhase2Skipped(unittest.TestCase):
    """Scenario: Phase 2 is skipped when Phase 1 has CRITICAL findings"""

    def setUp(self):
        # Deprecated term triggers CRITICAL in Phase 1; Phase 2 should be skipped
        # even though README is missing the Critic section
        self.root = create_fixture({
            "features/policy_critic.md": (
                '# Policy: Critic\n'
                '## Purpose\n'
                'The quality gate validates all features.\n'
            ),
            "instructions/HOW_WE_WORK_BASE.md": (
                '# How We Work\n'
                '## Critic\n'
                'The coordination engine.\n'
            ),
            "README.md": (
                '# Project\n'
                '## The Agents\n'
                'Agent info.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_phase2_skipped_on_critical(self):
        result = critic_consistency_main(self.root)
        self.assertEqual(result["status"], "FAIL")
        # Should have deprecated term finding but NOT readme_missing_critic_section
        deprecated = [
            f for f in result["findings"] if f["category"] == "deprecated_term"
        ]
        readme_missing = [
            f for f in result["findings"]
            if f["category"] == "readme_missing_critic_section"
        ]
        self.assertGreater(len(deprecated), 0, "Phase 1 should find deprecated term")
        self.assertEqual(len(readme_missing), 0,
                         "Phase 2 should be skipped when Phase 1 has CRITICAL")


# ===================================================================
# Scenario: Doc consistency — fully consistent (clean state)
# ===================================================================

class TestDocConsistencyClean(unittest.TestCase):
    """Scenario: Documentation is fully consistent"""

    def setUp(self):
        self.root = create_fixture({
            "README.md": (
                '# Project\n'
                'This project includes my_feature.\n'
            ),
            "features/my_feature.md": '# My Feature\n',
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_passes_clean(self):
        result = doc_consistency_main(self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["findings"]), 0)


# ===================================================================
# Scenario: Doc consistency detects coverage gap
# ===================================================================

class TestDocConsistencyCoverageGap(unittest.TestCase):
    """Scenario: Stale feature description corrected"""

    def setUp(self):
        self.root = create_fixture({
            "README.md": (
                '# Project\n'
                'This project has features.\n'
            ),
            "features/my_feature.md": '# My Feature\n',
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_coverage_gap(self):
        result = doc_consistency_main(self.root)
        gap = [f for f in result["findings"] if f["category"] == "coverage_gap"]
        self.assertGreater(len(gap), 0)
        self.assertIn("my_feature", gap[0]["file"])


# ===================================================================
# Scenario: Doc consistency detects tombstone reference
# ===================================================================

class TestDocConsistencyTombstone(unittest.TestCase):
    """Scenario: Reference to removed functionality corrected"""

    def setUp(self):
        self.root = create_fixture({
            "README.md": (
                '# Project\n'
                'The old_feature module handles legacy logic.\n'
            ),
            "features/tombstones/old_feature.md": '# Tombstone: old_feature\n',
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_detects_tombstone_reference(self):
        result = doc_consistency_main(self.root)
        tombstone = [f for f in result["findings"] if f["category"] == "tombstone_reference"]
        self.assertGreater(len(tombstone), 0)
        self.assertIn("old_feature", tombstone[0]["message"])


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
            "README.md": "# Project\n",
            ".purlin/HOW_WE_WORK_OVERRIDES.md": "# Overrides\n",
            ".purlin/ARCHITECT_OVERRIDES.md": "# Overrides\n",
            ".purlin/BUILDER_OVERRIDES.md": "# Overrides\n",
            ".purlin/QA_OVERRIDES.md": "# Overrides\n",
            ".purlin/config.json": '{}',
            "instructions/HOW_WE_WORK_BASE.md": "# HWW\n",
        })
        self.zero_queue_status = {
            "features": [
                {
                    "file": "features/feature_a.md",
                    "label": "Feature A",
                    "category": "Test",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                }
            ],
        }

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
        self._assert_valid_output(
            verify_zero_main(self.root, status_data=self.zero_queue_status)
        )

    def test_submodule_safety_audit(self):
        self._assert_valid_output(submodule_safety_main(self.root))

    def test_critic_consistency_check(self):
        self._assert_valid_output(critic_consistency_main(self.root))

    def test_doc_consistency_check(self):
        self._assert_valid_output(doc_consistency_main(self.root))

    def test_instruction_audit(self):
        self._assert_valid_output(instruction_audit_main(self.root))


# ===================================================================
# Scenario: Graph file is stale -- triggers regeneration (H10 fix)
# ===================================================================

class TestDepIntegrityStaleCacheRegeneration(unittest.TestCase):
    """Scenario: Graph file is stale or absent -- triggers cache regeneration."""

    def setUp(self):
        self.root = create_fixture({
            "features/feature_a.md": (
                '# Feature A\n'
                '> Label: "Feature A"\n'
                '> Category: "Test"\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    @mock.patch(
        "tools.release.verify_dependency_integrity.run_full_generation"
    )
    def test_absent_cache_triggers_regeneration(self, mock_regen):
        """When dependency_graph.json is absent, ensure_cache_fresh regenerates."""
        features_dir = os.path.join(self.root, "features")
        result = ensure_cache_fresh(self.root, features_dir)
        self.assertTrue(result, "Should return True when cache was regenerated")
        mock_regen.assert_called_once_with(features_dir)

    @mock.patch(
        "tools.release.verify_dependency_integrity.run_full_generation"
    )
    def test_stale_cache_triggers_regeneration(self, mock_regen):
        """When dependency_graph.json is older than a feature file, regenerate."""
        features_dir = os.path.join(self.root, "features")
        cache_dir = os.path.join(self.root, ".purlin", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "dependency_graph.json")
        # Create a cache file with old timestamp
        with open(cache_file, "w") as f:
            json.dump({"features": []}, f)
        # Set cache mtime to 1 hour in the past
        old_time = time.time() - 3600
        os.utime(cache_file, (old_time, old_time))
        # Touch a feature file to make it newer
        feature_file = os.path.join(features_dir, "feature_a.md")
        os.utime(feature_file, None)  # sets to current time

        result = ensure_cache_fresh(self.root, features_dir)
        self.assertTrue(result, "Should return True when cache was regenerated")
        mock_regen.assert_called_once_with(features_dir)

    @mock.patch(
        "tools.release.verify_dependency_integrity.run_full_generation"
    )
    def test_fresh_cache_skips_regeneration(self, mock_regen):
        """When dependency_graph.json is newer than all feature files, skip."""
        features_dir = os.path.join(self.root, "features")
        cache_dir = os.path.join(self.root, ".purlin", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "dependency_graph.json")
        # Set feature file mtime to 1 hour in the past
        feature_file = os.path.join(features_dir, "feature_a.md")
        old_time = time.time() - 3600
        os.utime(feature_file, (old_time, old_time))
        # Create cache file now (newer than feature)
        with open(cache_file, "w") as f:
            json.dump({"features": []}, f)

        result = ensure_cache_fresh(self.root, features_dir)
        self.assertFalse(result, "Should return False when cache is fresh")
        mock_regen.assert_not_called()


# ===================================================================
# M41: verify_zero_queue uses status.sh instead of critic.json
# ===================================================================

class TestZeroQueueUsesStatusSh(unittest.TestCase):
    """M41 fix: verify_zero_queue parses status.sh JSON output format."""

    def test_load_feature_status_from_status_data(self):
        """load_feature_status correctly parses status.sh format."""
        status_data = {
            "features": [
                {
                    "file": "features/alpha.md",
                    "label": "Alpha",
                    "category": "Core",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                },
                {
                    "file": "features/beta.md",
                    "label": "Beta",
                    "category": "Core",
                    "architect": "TODO",
                    "builder": "TODO",
                    "qa": "N/A",
                },
            ],
        }
        statuses = verify_zero_load_status("/tmp/fake", status_data=status_data)
        self.assertEqual(len(statuses), 2)
        self.assertEqual(statuses[0]["feature"], "alpha")
        self.assertEqual(statuses[0]["architect"], "DONE")
        self.assertEqual(statuses[1]["feature"], "beta")
        self.assertEqual(statuses[1]["builder"], "TODO")

    def test_load_feature_status_skips_tombstones(self):
        """Tombstone entries in status.sh output are excluded."""
        status_data = {
            "features": [
                {
                    "file": "features/active.md",
                    "label": "Active",
                    "category": "Core",
                    "architect": "DONE",
                    "builder": "DONE",
                    "qa": "CLEAN",
                },
                {
                    "file": "features/tombstones/old.md",
                    "label": "Old",
                    "category": "Core",
                },
            ],
        }
        statuses = verify_zero_load_status("/tmp/fake", status_data=status_data)
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0]["feature"], "active")

    def test_load_feature_status_empty_data(self):
        """Empty status data returns empty list."""
        statuses = verify_zero_load_status("/tmp/fake", status_data=None)
        self.assertEqual(statuses, [])

    def test_finding_uses_file_path_from_status(self):
        """Findings reference file path from status.sh, not constructed path."""
        status_data = {
            "features": [
                {
                    "file": "features/my_feature.md",
                    "label": "My Feature",
                    "category": "Core",
                    "architect": "DONE",
                    "builder": "TODO",
                    "qa": "N/A",
                }
            ],
        }
        result = verify_zero_main("/tmp/fake", status_data=status_data)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["findings"][0]["file"], "features/my_feature.md")


# ===================================================================
# M42: Structural contradiction detection in instruction_audit
# ===================================================================

class TestInstructionAuditStructuralContradiction(unittest.TestCase):
    """M42 fix: Structural analysis detects contradictions by section match."""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/HOW_WE_WORK_OVERRIDES.md": (
                '# Overrides\n'
                '## Commit Protocol\n'
                'The Builder MUST NOT push to remote after commit.\n'
            ),
            ".purlin/ARCHITECT_OVERRIDES.md": '# Architect Overrides\n',
            ".purlin/BUILDER_OVERRIDES.md": '# Builder Overrides\n',
            ".purlin/QA_OVERRIDES.md": '# QA Overrides\n',
            "instructions/BUILDER_BASE.md": (
                '# Builder Instructions\n'
                '## Commit Protocol\n'
                'The Builder MUST push to remote after commit.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_structural_section_contradiction(self):
        """Contradictions within matching sections are detected."""
        result = instruction_audit_main(self.root)
        contrad = [
            f for f in result["findings"] if f["category"] == "contradiction"
        ]
        self.assertGreater(len(contrad), 0,
                           "Should detect structural contradiction")
        self.assertEqual(contrad[0]["severity"], "CRITICAL")


class TestInstructionAuditStructuralNoFalsePositive(unittest.TestCase):
    """M42 fix: Structural analysis does not produce false positives
    when override and base rules are in unrelated sections with
    minimal word overlap (fewer than 2 shared context words)."""

    def setUp(self):
        self.root = create_fixture({
            ".purlin/HOW_WE_WORK_OVERRIDES.md": (
                '# Overrides\n'
                '## Linting\n'
                'Validators MUST NOT skip formatting checks.\n'
            ),
            ".purlin/ARCHITECT_OVERRIDES.md": '# Architect Overrides\n',
            ".purlin/BUILDER_OVERRIDES.md": '# Builder Overrides\n',
            ".purlin/QA_OVERRIDES.md": '# QA Overrides\n',
            "instructions/BUILDER_BASE.md": (
                '# Builder Instructions\n'
                '## Deployment\n'
                'Agents MUST push artifacts to remote after staging.\n'
            ),
            ".purlin/config.json": '{}',
        })

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_no_false_positive_across_sections(self):
        """Different sections with different subjects are not flagged."""
        result = instruction_audit_main(self.root)
        contrad = [
            f for f in result["findings"] if f["category"] == "contradiction"
        ]
        self.assertEqual(len(contrad), 0,
                         "Should not flag contradiction across unrelated sections")


class TestInstructionAuditStructuralDeduplicate(unittest.TestCase):
    """M42 fix: Heuristic and structural findings are deduplicated."""

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

    def test_no_duplicate_findings(self):
        """Same contradiction found by both methods is reported only once."""
        result = instruction_audit_main(self.root)
        contrad = [
            f for f in result["findings"] if f["category"] == "contradiction"
        ]
        # The same override line should only appear once in findings
        lines_reported = [f["line"] for f in contrad]
        self.assertEqual(len(lines_reported), len(set(lines_reported)),
                         "Each contradiction line should appear only once")


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


# ===================================================================
# Per-feature result distribution
# ===================================================================

# Maps test class name -> list of feature directory names in tests/
CLASS_FEATURE_MAP = {
    "TestDepIntegrityCycle": ["release_verify_dependency_integrity"],
    "TestDepIntegrityClean": ["release_verify_dependency_integrity"],
    "TestDepIntegrityBrokenLink": ["release_verify_dependency_integrity"],
    "TestDepIntegrityReverseRef": ["release_verify_dependency_integrity"],
    "TestDepIntegrityStaleCacheRegeneration": ["release_verify_dependency_integrity"],
    "TestZeroQueueBlocking": ["release_verify_zero_queue"],
    "TestZeroQueueClean": ["release_verify_zero_queue"],
    "TestZeroQueueQABlocking": ["release_verify_zero_queue"],
    "TestZeroQueueArchitectBlocking": ["release_verify_zero_queue"],
    "TestSubmoduleSafetyMissingEnv": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyArtifactInTools": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyClean": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyGitignoreUncoveredArtifact": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyGitignoreHardcodedArray": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyGitignoreRefreshSkip": ["release_submodule_safety_audit"],
    "TestSubmoduleSafetyMissingDisambiguation": ["release_submodule_safety_audit"],
    "TestCriticConsistencyDeprecated": ["release_critic_consistency_check"],
    "TestCriticConsistencyRouting": ["release_critic_consistency_check"],
    "TestCriticConsistencyWarningLevel": ["release_critic_consistency_check"],
    "TestCriticConsistencyReadmeMissing": ["release_critic_consistency_check"],
    "TestCriticConsistencyReadmeClean": ["release_critic_consistency_check"],
    "TestCriticConsistencyPhase2Skipped": ["release_critic_consistency_check"],
    "TestDocConsistencyStaleRef": ["release_doc_consistency_check",
                                   "release_framework_doc_consistency"],
    "TestDocConsistencyCoverageGap": ["release_doc_consistency_check"],
    "TestDocConsistencyTombstone": ["release_doc_consistency_check"],
    "TestInstructionAuditContradiction": ["instruction_audit",
                                          "release_framework_doc_consistency"],
    "TestInstructionAuditStalePath": ["instruction_audit",
                                      "release_framework_doc_consistency"],
    "TestZeroQueueUsesStatusSh": ["release_verify_zero_queue"],
    "TestInstructionAuditStructuralContradiction": ["instruction_audit",
                                                     "release_framework_doc_consistency"],
    "TestInstructionAuditStructuralNoFalsePositive": ["instruction_audit",
                                                       "release_framework_doc_consistency"],
    "TestInstructionAuditStructuralDeduplicate": ["instruction_audit",
                                                   "release_framework_doc_consistency"],
}

# TestAllScriptsValidJSON sub-tests map by method name
VALID_JSON_METHOD_MAP = {
    "test_verify_dependency_integrity": ["release_verify_dependency_integrity"],
    "test_verify_zero_queue": ["release_verify_zero_queue"],
    "test_submodule_safety_audit": ["release_submodule_safety_audit"],
    "test_critic_consistency_check": ["release_critic_consistency_check"],
    "test_doc_consistency_check": ["release_doc_consistency_check",
                                    "release_framework_doc_consistency"],
    "test_instruction_audit": ["instruction_audit",
                                "release_framework_doc_consistency"],
}


def _extract_class_name(test_str):
    """Extract class name from test result string like
    'test_foo (module.ClassName.test_foo)'."""
    import re
    match = re.search(r'\.(\w+)\.\w+\)', test_str)
    return match.group(1) if match else None


def _extract_method_name(test_str):
    """Extract method name from test result string."""
    import re
    match = re.search(r'\.(\w+)\)', test_str)
    return match.group(1) if match else None


def distribute_results(results, project_root):
    """Write per-feature tests.json based on CLASS_FEATURE_MAP."""
    feature_results = {}  # feature_name -> list of test result dicts

    for entry in results:
        class_name = _extract_class_name(entry["test"])
        if not class_name:
            continue

        features = []
        if class_name == "TestAllScriptsValidJSON":
            method = _extract_method_name(entry["test"])
            features = VALID_JSON_METHOD_MAP.get(method, [])
        else:
            features = CLASS_FEATURE_MAP.get(class_name, [])

        for feat in features:
            feature_results.setdefault(feat, []).append(entry)

    for feat, entries in feature_results.items():
        out_dir = os.path.join(project_root, "tests", feat)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "tests.json")

        passed = sum(1 for e in entries if e["status"] == "PASS")
        failed = len(entries) - passed
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if failed == 0 else "FAIL",
                    "passed": passed,
                    "failed": failed,
                    "total": len(entries),
                    "test_file": "tools/release/test_release_audit.py",
                    "details": entries,
                },
                f,
                indent=2,
            )
        print(f"  {feat}: {passed}/{len(entries)} passed")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write aggregate tests.json
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
        print(f"\nAggregate results written to {out_file}")

        # Distribute per-feature results
        print("\nPer-feature distribution:")
        distribute_results(result.results, PROJECT_ROOT)

    sys.exit(0 if result.wasSuccessful() else 1)
