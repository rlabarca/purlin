"""Unit tests for Builder QA Mode feature.

Covers the 6 automated scenarios from features/builder_qa_mode.md.
Outputs test results to tests/builder_qa_mode/tests.json.
"""

import unittest
from unittest.mock import patch
import os
import json
import sys
import tempfile

from serve import (
    generate_startup_briefing,
    extract_category,
)


def _make_qa_mode_env(tmpdir, features=None, config=None):
    """Create a temp environment for QA mode tests.

    Each feature dict may include 'category' to write a > Category: line.
    """
    features_dir = os.path.join(tmpdir, "features")
    tests_dir = os.path.join(tmpdir, "tests")
    cache_dir = os.path.join(tmpdir, ".purlin", "cache")
    os.makedirs(features_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    features = features or {}
    for stem, cfg in features.items():
        fpath = os.path.join(features_dir, f"{stem}.md")
        scenarios = cfg.get("scenarios", [])
        category = cfg.get("category", "")
        with open(fpath, 'w') as f:
            f.write(f'# Feature: {stem}\n\n')
            f.write(f'> Label: "{cfg.get("label", stem)}"\n')
            if category:
                f.write(f'> Category: "{category}"\n')
            f.write('\n')
            for s in scenarios:
                f.write(f'#### Scenario: {s}\n\n')

        tdir = os.path.join(tests_dir, stem)
        os.makedirs(tdir, exist_ok=True)
        role_status = cfg.get("role_status", {
            "architect": "DONE", "builder": "TODO",
            "qa": "N/A", "pm": "N/A"})
        cdata = {
            "role_status": role_status,
            "action_items": {
                "architect": [],
                "builder": [{"feature": stem, "priority": "HIGH",
                             "description": f"Implement {stem}"}],
                "qa": [], "pm": [],
            },
            "implementation_gate": {
                "checks": {"policy_adherence": {
                    "status": "PASS", "violations": []}}},
            "verification_effort": {
                "summary": "no QA items", "total_auto": 0, "total_manual": 0},
        }
        with open(os.path.join(tdir, "critic.json"), 'w') as f:
            json.dump(cdata, f)

    graph_data = {"features": [], "cycles": [], "orphans": []}
    with open(os.path.join(cache_dir, "dependency_graph.json"), 'w') as f:
        json.dump(graph_data, f)

    resolved_config = config or {
        "agents": {
            "builder": {"find_work": True, "auto_start": True,
                        "model": "test-model", "effort": "high"},
            "qa": {"find_work": True, "auto_start": False,
                   "model": "test-model", "effort": "medium"},
            "architect": {"find_work": False, "auto_start": False,
                          "model": "test-model", "effort": "high"},
            "pm": {"find_work": False, "auto_start": False,
                   "model": "test-model", "effort": "high"},
        }
    }

    return {
        "features_dir": features_dir,
        "tests_dir": tests_dir,
        "cache_dir": cache_dir,
        "config": resolved_config,
        "project_root": tmpdir,
    }


def _run_briefing(env, config_override=None, env_vars=None):
    """Run generate_startup_briefing with patched environment."""
    config = config_override if config_override else env["config"]
    env_patches = env_vars or {}

    with patch('serve.FEATURES_ABS', env["features_dir"]), \
         patch('serve.FEATURES_REL', 'features'), \
         patch('serve.TESTS_DIR', env["tests_dir"]), \
         patch('serve.CACHE_DIR', env["cache_dir"]), \
         patch('serve.DEPENDENCY_GRAPH_PATH',
               os.path.join(env["cache_dir"], "dependency_graph.json")), \
         patch('serve.CONFIG', config), \
         patch('serve.PROJECT_ROOT', env["project_root"]), \
         patch('serve.build_status_commit_cache', return_value={}), \
         patch.dict(os.environ, env_patches, clear=False), \
         patch('serve.run_command') as mock_cmd:
        mock_cmd.side_effect = lambda c: {
            "git rev-parse --abbrev-ref HEAD": "main",
            "git status --porcelain": "",
        }.get(c.strip(), "")
        return generate_startup_briefing("builder")


# --- Ten features: 8 normal, 2 Test Infrastructure ---
_MIXED_FEATURES = {
    "app_auth": {
        "label": "App Auth",
        "category": "Agent Skills",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_dashboard": {
        "label": "App Dashboard",
        "category": "CDD Dashboard",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_settings": {
        "label": "App Settings",
        "category": "Install, Update & Scripts",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_release": {
        "label": "App Release",
        "category": "Release Process",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_design": {
        "label": "App Design",
        "category": "Common Design Standards",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_lifecycle": {
        "label": "App Lifecycle",
        "category": "Coordination & Lifecycle",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_remote": {
        "label": "App Remote",
        "category": "Agent Skills",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "app_misc": {
        "label": "App Misc",
        "category": "Uncategorized",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "test_fixture_repo": {
        "label": "Test Fixture Repo",
        "category": "Test Infrastructure",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
    "regression_harness": {
        "label": "Regression Harness",
        "category": "Test Infrastructure",
        "role_status": {"architect": "DONE", "builder": "TODO",
                        "qa": "N/A", "pm": "N/A"},
        "scenarios": ["S1"],
    },
}


class TestDefaultModeHidesTestInfrastructure(unittest.TestCase):
    """Scenario: Default mode hides test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And PURLIN_BUILDER_QA is not set
    When the Builder runs startup find_work
    Then 8 features appear in the work plan
    And the 2 Test Infrastructure features are not listed
    """

    def test_default_mode_excludes_test_infra(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        features = result["features"]
        feature_labels = [f["label"] for f in features]

        # 8 normal features visible
        self.assertEqual(len(features), 8)

        # Test Infrastructure features NOT listed
        self.assertNotIn("Test Fixture Repo", feature_labels)
        self.assertNotIn("Regression Harness", feature_labels)

        # Normal features ARE listed
        self.assertIn("App Auth", feature_labels)
        self.assertIn("App Dashboard", feature_labels)

    def test_default_mode_filters_action_items(self):
        """Action items for Test Infrastructure features are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        action_features = {item.get("feature") for item in result["action_items"]}
        self.assertNotIn("test_fixture_repo", action_features)
        self.assertNotIn("regression_harness", action_features)

    def test_in_scope_features_also_filtered(self):
        """in_scope_features mirrors the filtered features list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        in_scope_labels = [f["label"] for f in result["in_scope_features"]]
        self.assertEqual(len(in_scope_labels), 8)
        self.assertNotIn("Test Fixture Repo", in_scope_labels)


class TestQaFlagShowsOnlyTestInfrastructure(unittest.TestCase):
    """Scenario: -qa flag shows only test infrastructure features

    Given the project has 10 features, 2 in "Test Infrastructure" category
    And PURLIN_BUILDER_QA=true is set (via -qa flag)
    When the Builder runs startup find_work
    Then only the 2 Test Infrastructure features appear in the work plan
    And the 8 non-test features are not listed
    """

    def test_qa_flag_includes_only_test_infra(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env,
                                   env_vars={"PURLIN_BUILDER_QA": "true"})

        features = result["features"]
        feature_labels = [f["label"] for f in features]

        # Only 2 Test Infrastructure features visible
        self.assertEqual(len(features), 2)
        self.assertIn("Test Fixture Repo", feature_labels)
        self.assertIn("Regression Harness", feature_labels)

        # Normal features NOT listed
        self.assertNotIn("App Auth", feature_labels)
        self.assertNotIn("App Dashboard", feature_labels)

    def test_qa_flag_filters_action_items_to_test_infra(self):
        """Only Test Infrastructure action items are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env,
                                   env_vars={"PURLIN_BUILDER_QA": "true"})

        action_features = {item.get("feature") for item in result["action_items"]}
        # Only test infra features should have action items
        for f in action_features:
            if f:  # skip feature-less items
                self.assertIn(f, {"test_fixture_repo", "regression_harness"})


class TestQaFlagPrintsHeaderIndicator(unittest.TestCase):
    """Scenario: -qa flag prints header indicator

    Given PURLIN_BUILDER_QA=true is set
    When the Builder prints its startup command table
    Then the header includes "[QA Builder Mode]"

    Implementation: qa_mode is returned in the config block so the
    Builder agent can prepend [QA Builder Mode] to its header.
    """

    def test_config_block_includes_qa_mode_true_via_env_var(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env,
                                   env_vars={"PURLIN_BUILDER_QA": "true"})

        self.assertIn("qa_mode", result["config"])
        self.assertTrue(result["config"]["qa_mode"])

    def test_config_block_includes_qa_mode_false_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        self.assertIn("qa_mode", result["config"])
        self.assertFalse(result["config"]["qa_mode"])


class TestNormalModeShowsTestInfrastructurePendingCount(unittest.TestCase):
    """Scenario: Normal mode shows test_infrastructure_pending count

    Given the project has 3 Test Infrastructure features in TODO state
    And PURLIN_BUILDER_QA is not set
    When the Builder reads the startup briefing
    Then test_infrastructure_pending is 3
    """

    def test_test_infrastructure_pending_count(self):
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "regression_harness": {
                "label": "Regression Harness",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_quality": {
                "label": "Test Quality",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env)

        self.assertIn("test_infrastructure_pending", result)
        self.assertEqual(result["test_infrastructure_pending"], 3)

    def test_completed_test_infra_not_counted(self):
        """Test Infrastructure features with DONE status are not counted."""
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "regression_harness": {
                "label": "Regression Harness",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "DONE",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env)

        # Only test_fixture_repo is TODO; regression_harness is DONE
        self.assertEqual(result["test_infrastructure_pending"], 1)

    def test_pending_count_with_mixed_features(self):
        """Standard 10-feature set has 2 pending test infra features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        self.assertEqual(result["test_infrastructure_pending"], 2)


class TestNormalModeRecommendsQaAfterZeroTodo(unittest.TestCase):
    """Scenario: Normal mode recommends -qa after zero TODO

    Given the Builder has completed all non-Test-Infrastructure TODO features
    And test_infrastructure_pending is 2
    When the Builder presents the work plan
    Then the plan includes a recommendation:
      "2 Test Infrastructure features pending.
       Use ./pl-run-builder.sh -qa for a focused session."
    """

    def test_recommendation_when_all_normal_done(self):
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "DONE",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "app_dashboard": {
                "label": "App Dashboard",
                "category": "CDD Dashboard",
                "role_status": {"architect": "DONE", "builder": "DONE",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "regression_harness": {
                "label": "Regression Harness",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env)

        self.assertIn("qa_mode_recommendation", result)
        expected = ("2 Test Infrastructure features pending. "
                    "Use ./pl-run-builder.sh -qa for a focused session.")
        self.assertEqual(result["qa_mode_recommendation"], expected)

    def test_no_recommendation_when_normal_todo_remains(self):
        """No recommendation when normal features still have TODO work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=_MIXED_FEATURES)
            result = _run_briefing(env)

        # Normal features still TODO, so no recommendation
        self.assertNotIn("qa_mode_recommendation", result)

    def test_no_recommendation_when_no_test_infra_pending(self):
        """No recommendation when test infra count is zero."""
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "DONE",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env)

        self.assertNotIn("qa_mode_recommendation", result)
        self.assertEqual(result["test_infrastructure_pending"], 0)


class TestQaFlagComposesWithContinuousMode(unittest.TestCase):
    """Scenario: -qa flag composes with continuous mode

    Given PURLIN_BUILDER_QA=true is set
    And the continuous phase flag is active
    And there are 4 Test Infrastructure features in TODO state
    When the Builder creates a delivery plan
    Then the plan contains only Test Infrastructure features
    And phase analysis operates on the filtered set

    Implementation: The startup briefing returns only Test Infrastructure
    features when PURLIN_BUILDER_QA=true. The continuous phase builder
    consumes this filtered list to create the delivery plan. We verify the
    briefing output is correctly filtered with 4 TI features.
    """

    def test_qa_flag_with_multiple_test_infra_features(self):
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "app_dashboard": {
                "label": "App Dashboard",
                "category": "CDD Dashboard",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1", "S2"],
            },
            "regression_harness": {
                "label": "Regression Harness",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1", "S2", "S3"],
            },
            "agent_behavior": {
                "label": "Agent Behavior Tests",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_quality": {
                "label": "Test Quality",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env,
                                   env_vars={"PURLIN_BUILDER_QA": "true"})

        # Only Test Infrastructure features visible
        visible = result["features"]
        self.assertEqual(len(visible), 4)
        labels = {f["label"] for f in visible}
        self.assertEqual(labels, {"Test Fixture Repo", "Regression Harness",
                                  "Agent Behavior Tests", "Test Quality"})

        # in_scope_features matches
        in_scope = result["in_scope_features"]
        self.assertEqual(len(in_scope), 4)

        # phasing_recommended should work on the filtered set
        # (4 features >= 3 threshold)
        self.assertTrue(result.get("phasing_recommended", False))

    def test_qa_flag_excludes_non_test_features_from_scope(self):
        """Non-test features are fully excluded from in_scope_features."""
        features = {
            "app_auth": {
                "label": "App Auth",
                "category": "Agent Skills",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
            "test_fixture_repo": {
                "label": "Test Fixture Repo",
                "category": "Test Infrastructure",
                "role_status": {"architect": "DONE", "builder": "TODO",
                                "qa": "N/A", "pm": "N/A"},
                "scenarios": ["S1"],
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            env = _make_qa_mode_env(tmpdir, features=features)
            result = _run_briefing(env,
                                   env_vars={"PURLIN_BUILDER_QA": "true"})

        in_scope_labels = [f["label"] for f in result["in_scope_features"]]
        self.assertEqual(len(in_scope_labels), 1)
        self.assertIn("Test Fixture Repo", in_scope_labels)
        self.assertNotIn("App Auth", in_scope_labels)


class TestExtractCategory(unittest.TestCase):
    """Additional tests for the extract_category helper."""

    def test_extracts_category_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Feature\n\n> Label: "Test"\n> Category: "Test Infrastructure"\n')
            f.flush()
            result = extract_category(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "Test Infrastructure")

    def test_returns_uncategorized_when_missing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                         delete=False) as f:
            f.write('# Feature\n\n> Label: "Test"\n')
            f.flush()
            result = extract_category(f.name)
        os.unlink(f.name)
        self.assertEqual(result, "Uncategorized")

    def test_returns_uncategorized_for_nonexistent_file(self):
        result = extract_category("/nonexistent/path.md")
        self.assertEqual(result, "Uncategorized")


# ===================================================================
# Test runner with output to tests/builder_qa_mode/tests.json
# ===================================================================

if __name__ == '__main__':
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../'))
    tests_out_dir = os.path.join(project_root, "tests", "builder_qa_mode")
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, "tests.json")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = "PASS" if result.wasSuccessful() else "FAIL"
    failed = len(result.failures) + len(result.errors)
    report = {
        "status": status,
        "passed": result.testsRun - failed,
        "failed": failed,
        "total": result.testsRun,
        "test_file": "tools/cdd/test_builder_qa_mode.py"
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
